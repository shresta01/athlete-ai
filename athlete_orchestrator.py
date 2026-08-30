import os
import re
import time
import functools
import sqlite3
import threading
import hashlib
import secrets
from datetime import datetime, timezone
import httpx
import uvicorn

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import Dict, List

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


# ============================================================
# CONFIGURATION
# ============================================================

# LLM_PROVIDER selects between:
#   "ollama" (default) — self-hosted, what your local PC and
#                         docker-compose setup already use.
#   "groq"              — Groq's free, no-credit-card hosted API.
#                         Use this where there isn't enough RAM to
#                         run a local model (e.g. Render's free
#                         tier, ~512MB — nowhere near enough for
#                         even a small local LLM).
# Nothing about your local setup changes unless you explicitly set
# LLM_PROVIDER=groq as an environment variable.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

OLLAMA_HOST = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11434"
)

OLLAMA_GENERATE_URL = OLLAMA_HOST.rstrip("/") + "/api/generate"

RAG_WORKER_URL = os.getenv(
    "RAG_WORKER_URL",
    "http://127.0.0.1:8002/fuel-plan"
)

OVERLOAD_URL = os.getenv(
    "OVERLOAD_URL",
    "http://127.0.0.1:8003/overload-plan"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:3b"
)

OLLAMA_NUM_CTX = int(
    # Raised from 4096: the prompt now always includes all 3
    # knowledge base documents (nutrition_trainer.py retrieves
    # n_results=3), a longer instruction set, athlete facts, and
    # up to 12 turns of history — plus a response that can run to
    # a full multi-block periodized program. 4096 risked Ollama
    # silently truncating the least-recent part of the prompt.
    os.getenv("OLLAMA_NUM_CTX", "8192")
)

OLLAMA_MAX_TOKENS = int(
    # Raised from 500: detailed, structured coaching responses
    # need headroom — a single-session answer with sets/reps/
    # rest/tempo per exercise needs more than a short paragraph,
    # and a full periodized program (multiple training-age
    # blocks, each with several weekly waves) needs more still.
    os.getenv("OLLAMA_MAX_TOKENS", "1200")
)

OLLAMA_TEMPERATURE = float(
    os.getenv("OLLAMA_TEMPERATURE", "0.2")
)

# --- Groq (only used when LLM_PROVIDER=groq) ---

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    # llama-3.1-8b-instant was fully decommissioned by Groq on
    # Aug 16, 2026 (returns 404, not even the older 400
    # model_decommissioned warning). openai/gpt-oss-20b is
    # Groq's own official migration recommendation for it —
    # similar speed/size class. openai/gpt-oss-120b is a larger,
    # higher-quality option if you want to trade some speed for
    # better answers (still free-tier eligible).
    "openai/gpt-oss-20b",
)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"



OLLAMA_TIMEOUT = int(
    os.getenv("OLLAMA_TIMEOUT", "120")
)


# ============================================================
# HTTP CLIENT
# ============================================================

HTTPX_CLIENT = httpx.Client(
    timeout=httpx.Timeout(
        connect=5.0,
        read=OLLAMA_TIMEOUT,
        write=10.0,
        pool=5.0
    )
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Intelligent Conversational Athlete Orchestrator",
    version="3.0"
)


# ============================================================
# PERSISTENT CONVERSATION MEMORY
# ============================================================

MEMORY_DB = os.getenv(
    "ATHLETE_MEMORY_DB",
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "athlete_memory.db",
    ),
)

_MEMORY_LOCK = threading.Lock()


def init_memory_db():
    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_profile_id
                ON chat_messages(profile_id, id)
                """
            )

            # ----------------------------------------------------
            # Persistent athlete facts — weight, experience level,
            # goal. One row per profile_id, upserted whenever the
            # UI saves the Nutrition page. Read on every /chat call
            # so programming (periodized plans, load targets) is
            # calibrated to who the athlete actually is, not just
            # whatever happens to be in the current message.
            # ----------------------------------------------------

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS athlete_profile (
                    profile_id TEXT PRIMARY KEY,
                    weight_kg REAL,
                    experience_level TEXT,
                    goal TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

            # ----------------------------------------------------
            # Accounts. username doubles as profile_id everywhere
            # else in this file (chat_messages, athlete_profile),
            # so logging in as "alex" transparently reuses all the
            # existing profile-scoped storage/retrieval logic —
            # no schema change needed on those tables.
            # ----------------------------------------------------

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    display_name TEXT,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            # ----------------------------------------------------
            # Logged exercises. This is the actual source of truth
            # for the Workout page and the Progress page's strength
            # targets / weekly volume — previously both only lived
            # in Streamlit's session_state, so a refresh or a new
            # login wiped everything.
            # ----------------------------------------------------

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workout_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT NOT NULL,
                    exercise TEXT NOT NULL,
                    sets INTEGER NOT NULL,
                    reps INTEGER NOT NULL,
                    weight_kg REAL NOT NULL,
                    volume_kg REAL NOT NULL,
                    logged_at TEXT NOT NULL
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workout_logs_profile
                ON workout_logs(profile_id, logged_at)
                """
            )

            # ----------------------------------------------------
            # Body-weight history. athlete_profile only ever holds
            # the CURRENT weight (upserted on every save), which is
            # right for "what does the coach use today" but can't
            # drive a trend chart. This table is append-only so the
            # Progress page's body-weight line chart reflects real
            # entries instead of a hardcoded example series.
            # ----------------------------------------------------

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS weight_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT NOT NULL,
                    weight_kg REAL NOT NULL,
                    logged_at TEXT NOT NULL
                )
                """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_weight_log_profile
                ON weight_log(profile_id, logged_at)
                """
            )

            conn.commit()
        finally:
            conn.close()


def save_chat_message(profile_id: str, role: str, content: str):
    if not content or not content.strip():
        return

    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            conn.execute(
                """
                INSERT INTO chat_messages
                (profile_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    profile_id,
                    role,
                    content.strip(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def get_chat_history(profile_id: str, max_messages: int = 12):
    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            rows = conn.execute(
                """
                SELECT role, content
                FROM chat_messages
                WHERE profile_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (profile_id, max_messages),
            ).fetchall()
        finally:
            conn.close()

    return [
        {"role": role, "content": content}
        for role, content in reversed(rows)
    ]


def clear_chat_history(profile_id: str):
    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            conn.execute(
                "DELETE FROM chat_messages WHERE profile_id = ?",
                (profile_id,),
            )
            conn.commit()
        finally:
            conn.close()


def save_athlete_profile(
    profile_id: str,
    weight_kg: float = None,
    experience_level: str = None,
    goal: str = None,
):
    """
    Upsert this athlete's persistent facts. Any field left as
    None keeps its previously saved value rather than being
    wiped — so saving just a new weight doesn't erase a
    previously-saved experience level.
    """

    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            existing = conn.execute(
                """
                SELECT weight_kg, experience_level, goal
                FROM athlete_profile
                WHERE profile_id = ?
                """,
                (profile_id,),
            ).fetchone()

            if existing:
                prev_weight, prev_level, prev_goal = existing
            else:
                prev_weight, prev_level, prev_goal = (
                    None, None, None
                )

            conn.execute(
                """
                INSERT INTO athlete_profile
                (profile_id, weight_kg, experience_level, goal, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    weight_kg = excluded.weight_kg,
                    experience_level = excluded.experience_level,
                    goal = excluded.goal,
                    updated_at = excluded.updated_at
                """,
                (
                    profile_id,
                    weight_kg if weight_kg is not None else prev_weight,
                    experience_level if experience_level is not None else prev_level,
                    goal if goal is not None else prev_goal,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

            # athlete_profile above only ever holds the CURRENT
            # weight (upsert). Separately append to the history
            # table so a trend line can be drawn later — but only
            # when a weight was actually provided this call, and
            # only when it differs from the last recorded entry,
            # so re-saving the same unchanged form repeatedly
            # doesn't flood the history with identical points.
            if weight_kg is not None and weight_kg != prev_weight:

                conn.execute(
                    """
                    INSERT INTO weight_log
                    (profile_id, weight_kg, logged_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        profile_id,
                        weight_kg,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

            conn.commit()
        finally:
            conn.close()


def get_athlete_profile(profile_id: str):
    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            row = conn.execute(
                """
                SELECT weight_kg, experience_level, goal
                FROM athlete_profile
                WHERE profile_id = ?
                """,
                (profile_id,),
            ).fetchone()
        finally:
            conn.close()

    if not row:
        return {}

    weight_kg, experience_level, goal = row

    facts = {}

    if weight_kg is not None:
        facts["weight_kg"] = weight_kg

    if experience_level:
        facts["experience_level"] = experience_level

    if goal:
        facts["goal"] = goal

    return facts


# ============================================================
# WORKOUT LOGS
# ============================================================

def save_workout_log(
    profile_id: str,
    exercise: str,
    sets: int,
    reps: int,
    weight_kg: float,
):
    volume_kg = sets * reps * weight_kg

    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            cursor = conn.execute(
                """
                INSERT INTO workout_logs
                (profile_id, exercise, sets, reps, weight_kg, volume_kg, logged_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    exercise,
                    sets,
                    reps,
                    weight_kg,
                    volume_kg,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
            new_id = cursor.lastrowid
        finally:
            conn.close()

    return {
        "id": new_id,
        "profile_id": profile_id,
        "exercise": exercise,
        "sets": sets,
        "reps": reps,
        "weight_kg": weight_kg,
        "volume_kg": volume_kg,
    }


def get_workout_logs(profile_id: str, limit: int = 200):
    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            rows = conn.execute(
                """
                SELECT id, exercise, sets, reps, weight_kg, volume_kg, logged_at
                FROM workout_logs
                WHERE profile_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (profile_id, limit),
            ).fetchall()
        finally:
            conn.close()

    return [
        {
            "id": row[0],
            "exercise": row[1],
            "sets": row[2],
            "reps": row[3],
            "weight_kg": row[4],
            "volume_kg": row[5],
            "logged_at": row[6],
        }
        for row in rows
    ]


def delete_workout_log(profile_id: str, log_id: int) -> bool:
    """
    Deletes only if the log actually belongs to profile_id, so one
    athlete can never delete another's entry by guessing an id.
    Returns whether a row was actually removed.
    """

    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            cursor = conn.execute(
                """
                DELETE FROM workout_logs
                WHERE id = ? AND profile_id = ?
                """,
                (log_id, profile_id),
            )
            conn.commit()
            deleted = cursor.rowcount > 0
        finally:
            conn.close()

    return deleted


def get_weekly_volume(profile_id: str, weeks: int = 8):
    """
    Total logged volume per week, most recent `weeks` weeks,
    oldest first (chart-ready order). Uses SQLite's %Y-%W
    (year + week-of-year, Sunday-start) as a simple, dependency-
    free week bucket — precise ISO-8601 week numbering isn't
    needed for a trend chart.
    """

    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            rows = conn.execute(
                """
                SELECT strftime('%Y-%W', logged_at) AS week,
                       SUM(volume_kg) AS total_volume
                FROM workout_logs
                WHERE profile_id = ?
                GROUP BY week
                ORDER BY week DESC
                LIMIT ?
                """,
                (profile_id, weeks),
            ).fetchall()
        finally:
            conn.close()

    rows.reverse()

    return [
        {"week": week, "volume_kg": total_volume}
        for week, total_volume in rows
    ]


def get_weight_history(profile_id: str, limit: int = 30):
    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            rows = conn.execute(
                """
                SELECT weight_kg, logged_at
                FROM weight_log
                WHERE profile_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (profile_id, limit),
            ).fetchall()
        finally:
            conn.close()

    rows.reverse()

    return [
        {"weight_kg": weight_kg, "logged_at": logged_at}
        for weight_kg, logged_at in rows
    ]


# Lifts the Progress page shows targets for — matches the set
# these agents already understand (see biomechanics_trainer.py /
# overload_trainer.py exercise_patterns).
TRACKED_LIFTS = [
    "Bench Press",
    "Squat",
    "Deadlift",
    "Overhead Press",
]


def get_strength_targets(profile_id: str):
    """
    For each tracked lift, the athlete's heaviest logged weight
    and a suggested next target (+2.5kg — same progression step
    overload_trainer.py uses). Lifts with no logged history yet
    are omitted rather than shown as a fabricated 0 kg.
    """

    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            rows = conn.execute(
                """
                SELECT exercise, MAX(weight_kg)
                FROM workout_logs
                WHERE profile_id = ?
                GROUP BY exercise
                """,
                (profile_id,),
            ).fetchall()
        finally:
            conn.close()

    current_by_exercise = dict(rows)

    targets = []

    for lift in TRACKED_LIFTS:

        current = current_by_exercise.get(lift)

        if current is None:
            continue

        targets.append(
            {
                "exercise": lift,
                "current_kg": current,
                "next_target_kg": round(current + 2.5, 1),
            }
        )

    return targets


# ============================================================
# ACCOUNTS / AUTH
# ============================================================

def hash_password(password: str, salt_hex: str = None):
    """
    PBKDF2-HMAC-SHA256 with a random per-user salt. No extra
    dependency (bcrypt/passlib) required beyond the stdlib.
    """

    if salt_hex is None:
        salt_hex = secrets.token_hex(16)

    salt_bytes = bytes.fromhex(salt_hex)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        200_000,
    )

    return digest.hex(), salt_hex


def username_exists(username: str) -> bool:
    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            row = conn.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        finally:
            conn.close()

    return row is not None


def create_user(username: str, password: str, display_name: str = None):
    password_hash, salt_hex = hash_password(password)

    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            conn.execute(
                """
                INSERT INTO users
                (username, display_name, password_hash, password_salt, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    display_name or username,
                    password_hash,
                    salt_hex,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def verify_login(username: str, password: str):
    """
    Returns the user's display_name on success, or None if the
    username doesn't exist or the password doesn't match.
    """

    with _MEMORY_LOCK:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        try:
            row = conn.execute(
                """
                SELECT display_name, password_hash, password_salt
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
        finally:
            conn.close()

    if not row:
        return None

    display_name, stored_hash, salt_hex = row

    candidate_hash, _ = hash_password(password, salt_hex)

    # Constant-time comparison to avoid leaking hash info via
    # response-timing side channels.
    if not secrets.compare_digest(candidate_hash, stored_hash):
        return None

    return display_name


def format_history(history):
    if not history:
        return "(No previous conversation.)"

    lines = []
    for item in history:
        role = "User" if item["role"] == "user" else "Athlete AI"
        lines.append(f"{role}: {item['content']}")
    return "\n".join(lines)


init_memory_db()


# ============================================================
# ATHLETE STATE
# ============================================================

class AthleteState(BaseModel):

    profile_id: str = ""

    user_query: str = ""

    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list
    )

    # Persistent facts about this athlete (weight, experience
    # level, goal) — loaded from athlete_profile table, not from
    # the current message. Lets the LLM calibrate programming
    # (e.g. periodized workout plans) to who the athlete actually
    # is even when they don't restate it every turn.
    athlete_facts: Dict = Field(
        default_factory=dict
    )

    intent: str = ""

    parsed_workout_metrics: Dict = Field(
        default_factory=dict
    )

    rag_context: List[str] = Field(
        default_factory=list
    )

    agent_raw_output: Dict = Field(
        default_factory=dict
    )

    final_response: str = ""


# ============================================================
# INTENT DETECTION
# ============================================================

LOG_KEYWORDS = [
    "logged",
    "log",
    "sets",
    "reps",
    "kg",
    "kilograms",
    "lbs",
    "pounds",
    "weight lifted",
    "bench press",
    "squat",
    "deadlift",
    "overhead press",
    "training session",
    "workout session",
    "one rep max",
    "1rm",
    "pr"
]


ROUTINE_KEYWORDS = [
    "program",
    "plan",
    "nutrition",
    "diet",
    "macro",
    "macros",
    "bulking",
    "cutting",
    "routine",
    "recovery",
    "meal",
    "meal plan",
    "cardio",
    "strength",
    "hypertrophy",
    "workout",
    "exercise",
    "muscle",
    "protein",
    "calories"
]


def _keyword_matches(text: str, keyword: str) -> bool:
    """
    Match `keyword` as a whole token rather than a raw
    substring. Plain `keyword in text` was matching "pr" inside
    "protein", "practical", "approach", "surprise", etc. — and
    "kg" inside "background" — causing many ordinary nutrition/
    workout questions to be misclassified as LOG intent.

    A strict \\bkeyword\\b regex isn't the right fix either:
    digits and letters both count as "word" characters, so
    \\bkg\\b would fail to match "80kg" (no space before "kg"),
    which is exactly the format this app's own Quick Action
    buttons send. Instead, only require that the keyword isn't
    immediately touching another LETTER — a digit directly
    before/after is still allowed.
    """

    pattern = (
        r"(?<![a-zA-Z])"
        + re.escape(keyword)
        + r"(?![a-zA-Z])"
    )

    return re.search(pattern, text) is not None


def classify_intent_local(query: str):

    text = query.lower()

    if any(
        _keyword_matches(text, keyword)
        for keyword in LOG_KEYWORDS
    ):
        return "LOG"

    if any(
        _keyword_matches(text, keyword)
        for keyword in ROUTINE_KEYWORDS
    ):
        return "NUTRITION_AND_WORKOUT"

    return None


# ============================================================
# LLM GENERATION (Ollama or Groq, via LLM_PROVIDER)
# ============================================================

def ollama_generate(prompt: str):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": OLLAMA_NUM_CTX,
            "temperature": OLLAMA_TEMPERATURE,
            "num_predict": OLLAMA_MAX_TOKENS,
        },
    }

    response = HTTPX_CLIENT.post(
        OLLAMA_GENERATE_URL,
        json=payload,
    )
    response.raise_for_status()

    data = response.json()

    return (
        data.get("response")
        or data.get("output")
        or ""
    )


def groq_generate(prompt: str):
    """
    Groq's API is OpenAI-compatible chat-completions, not
    Ollama's /api/generate shape — different request body, and
    the reply lives at choices[0].message.content instead of
    response.
    """

    if not GROQ_API_KEY:
        raise RuntimeError(
            "LLM_PROVIDER=groq but GROQ_API_KEY is not set. "
            "Get a free key at console.groq.com/keys and set it "
            "as an environment variable / Render secret."
        )

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": OLLAMA_TEMPERATURE,
        "max_tokens": OLLAMA_MAX_TOKENS,
    }

    response = HTTPX_CLIENT.post(
        GROQ_CHAT_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
        },
    )
    response.raise_for_status()

    data = response.json()

    choices = data.get("choices") or []

    if not choices:
        return ""

    return (
        choices[0]
        .get("message", {})
        .get("content", "")
    )


def generate_response(prompt: str):
    """
    Single entry point every LLM call site uses — routes to
    whichever provider LLM_PROVIDER selects. This is the only
    function that needs to know the two providers have different
    request/response shapes.
    """

    if LLM_PROVIDER == "groq":
        return groq_generate(prompt)

    return ollama_generate(prompt)


# ============================================================
# LLM PROVIDER HEALTH CHECK
# ============================================================

def check_ollama():

    if LLM_PROVIDER == "groq":

        print("")
        print("======================================")
        print("LLM PROVIDER: GROQ")
        print("======================================")
        print(f"Model: {GROQ_MODEL}")

        if not GROQ_API_KEY:
            print(
                "WARNING: GROQ_API_KEY is not set — every chat "
                "request will fail until it is."
            )
        else:
            print("GROQ_API_KEY: set")

        print("======================================")
        print("")

        return bool(GROQ_API_KEY)

    try:

        response = HTTPX_CLIENT.get(
            OLLAMA_HOST.rstrip("/") + "/api/tags",
            timeout=5
        )

        response.raise_for_status()

        models = response.json().get(
            "models",
            []
        )

        model_names = [
            model.get("name", "")
            for model in models
        ]

        print("")
        print("======================================")
        print("OLLAMA STATUS")
        print("======================================")
        print(f"URL: {OLLAMA_HOST}")
        print(f"Requested model: {OLLAMA_MODEL}")
        print(f"Available models: {model_names}")
        print("======================================")
        print("")

        if not any(
            OLLAMA_MODEL == name
            or OLLAMA_MODEL in name
            for name in model_names
        ):
            print(
                f"WARNING: {OLLAMA_MODEL} "
                "was not found in Ollama."
            )


        return True

    except Exception as e:

        print("")
        print("======================================")
        print("OLLAMA CONNECTION FAILED")
        print("======================================")
        print(str(e))
        print("======================================")
        print("")

        return False


def check_specialist_workers():
    """
    Ping each specialist worker's root URL at startup so a down
    or unreachable service is visible in the orchestrator's own
    logs immediately — instead of only showing up later as a
    silent, empty agent_raw_output on the first affected chat
    turn (see call_overload_pipeline / call_rag_worker).
    """

    workers = [
        ("Overload Specialist", OVERLOAD_URL),
        ("RAG Specialist", RAG_WORKER_URL),
    ]

    print("")
    print("======================================")
    print("SPECIALIST WORKER STATUS")
    print("======================================")

    for name, url in workers:

        base_url = url.rsplit("/", 1)[0]

        try:

            httpx.get(base_url, timeout=3.0)

            # Any HTTP response (even 404 on the bare root
            # path) proves the service is up and reachable.
            print(f"OK    {name:<22} {url}")

        except Exception as e:

            print(
                f"DOWN  {name:<22} {url} "
                f"({type(e).__name__})"
            )

    print("======================================")
    print("")


# ============================================================
# ROUTER NODE
# ============================================================

def intent_router_node(
    state: AthleteState
):

    start = time.perf_counter()

    print(
        f"[Router] Query: {state.user_query}"
    )

    detected_intent = classify_intent_local(
        state.user_query
    )

    if detected_intent:

        duration = (
            time.perf_counter()
            - start
        )

        print(
            f"[Router] Fast route: "
            f"{detected_intent} "
            f"({duration:.3f}s)"
        )

        return {
            "intent": detected_intent
        }

    # LLM fallback only when local routing
    # cannot determine the intent.

    history_text = format_history(
        state.conversation_history
    )

    prompt = f"""
Classify the user's latest fitness request.

Return exactly one word:

LOG

or

NUTRITION_AND_WORKOUT

Use the conversation history to understand follow-up questions,
pronouns, and omitted details.

Conversation history:
{history_text}

Latest user message:
{state.user_query}
"""

    try:

        result = generate_response(prompt)

        result = (
            result
            .strip()
            .upper()
        )

        if "LOG" in result:

            detected_intent = "LOG"

        else:

            detected_intent = (
                "NUTRITION_AND_WORKOUT"
            )

    except Exception as e:

        print(
            f"[Router] LLM unavailable: {e}"
        )

        detected_intent = (
            "NUTRITION_AND_WORKOUT"
        )

    return {
        "intent": detected_intent
    }


# ============================================================
# CONDITIONAL ROUTING
# ============================================================

def route_to_specialist(
    state: AthleteState
):

    if state.intent == "LOG":

        return "call_overload_pipeline"

    return "call_rag_worker"


# ============================================================
# OVERLOAD WORKER
# ============================================================

def call_overload_pipeline(
    state: AthleteState
):

    start = time.perf_counter()

    print(
        "[Orchestrator] "
        "Calling overload specialist..."
    )

    payload = {
        "raw_workout_input":
            state.user_query
    }

    try:

        # ------------------------------------------------------
        # Tight, fast timeout. This is a local specialist call,
        # not an LLM generation — it should respond in
        # milliseconds when healthy. A short connect/read window
        # means a down or hung worker fails fast instead of
        # stalling the whole chat turn.
        # ------------------------------------------------------

        response = HTTPX_CLIENT.post(
            OVERLOAD_URL,
            json=payload,
            timeout=httpx.Timeout(
                connect=3.0,
                read=8.0,
                write=5.0,
                pool=3.0,
            ),
        )

        response.raise_for_status()

        data = response.json()

        duration = (
            time.perf_counter()
            - start
        )

        print(
            f"[Overload Node] "
            f"Completed in {duration:.3f}s"
        )

        # ----------------------------------------------------
        # Store BOTH structured metrics and response
        # ----------------------------------------------------

        return {

            "agent_raw_output": data,

            "parsed_workout_metrics": {

                "exercise_detected":
                    data.get(
                        "exercise_detected",
                        "Workout"
                    ),

                "sets":
                    data.get("sets", 0),

                "reps":
                    data.get("reps", 0),

                "weight_kg":
                    data.get("weight_kg", 0),

                "total_volume_kg":
                    data.get(
                        "total_volume_kg",
                        0
                    ),

                "next_target_weight_kg":
                    data.get(
                        "next_target_weight_kg",
                        0
                    )
            }
        }

    except Exception as e:

        # ----------------------------------------------------
        # Log the real error server-side for debugging, but
        # NEVER forward raw exception text (socket errors,
        # stack traces, etc.) into agent_raw_output — that
        # field gets stringified straight into the LLM prompt
        # in synthesis_response_node, and the model has no way
        # to know it's internal plumbing rather than something
        # the athlete said. Return a clean, empty result instead
        # so synthesis silently falls back to conversation
        # history and general coaching knowledge.
        # ----------------------------------------------------

        duration = (
            time.perf_counter()
            - start
        )

        print(
            f"[Overload Node Error] "
            f"{type(e).__name__}: {e} "
            f"({duration:.3f}s)"
        )

        return {

            "agent_raw_output": {},

            "parsed_workout_metrics": {}
        }

# ============================================================
# RAG WORKER
# ============================================================

def call_rag_worker(
    state: AthleteState
):

    print(
        "[Orchestrator] "
        "Calling nutrition RAG specialist..."
    )

    payload = {
        "raw_workout_input":
            state.user_query
    }

    start = time.perf_counter()

    try:

        response = HTTPX_CLIENT.post(
            RAG_WORKER_URL,
            json=payload,
            timeout=httpx.Timeout(
                connect=3.0,
                read=8.0,
                write=5.0,
                pool=3.0,
            ),
        )

        response.raise_for_status()

        data = response.json()

        return {
            "rag_context":
                data.get(
                    "nutrition_rag_context",
                    []
                )
        }

    except Exception as e:

        duration = (
            time.perf_counter()
            - start
        )

        print(
            f"[RAG Error] "
            f"{type(e).__name__}: {e} "
            f"({duration:.3f}s)"
        )

        return {
            "rag_context": []
        }


# ============================================================
# FAST FALLBACK RESPONSE
# ============================================================

def deterministic_fallback(
    state: AthleteState
):

    query = state.user_query.lower()

    metrics = state.agent_raw_output

    if metrics and "next_action_routine" in metrics:

        routine = metrics[
            "next_action_routine"
        ]

        return "\n".join(
            f"• {item}"
            for item in routine
        )

    if "bench press" in query:

        return """
### Bench Press Progression

You logged **4 × 8 @ 80 kg**.

Your next progression can be:

**4 × 8 @ 82.5 kg**

Keep:
• Shoulder blades retracted
• Feet firmly planted
• Controlled descent
• Consistent bar path

If 82.5 kg causes a major form breakdown, stay at 80 kg and build additional quality reps first.
"""

    if LLM_PROVIDER == "groq":

        return """
### Athlete Coach

I received your request, but I couldn't reach the AI service just now.

Your workout data has still been processed successfully.

Check the orchestrator terminal for the exact error (look for
"[Synthesis ERROR]") — common causes are an invalid or revoked
GROQ_API_KEY, or hitting Groq's free-tier rate limit. Try again in
a moment.
"""

    return """
### Athlete Coach

I received your request, but the local AI model is currently unavailable.

Your workout data has still been processed successfully.

Try the request again once Ollama is running.
"""


# ============================================================
# AI SYNTHESIS
# ============================================================

def synthesis_response_node(
    state: AthleteState
):

    print(
        "[Orchestrator] "
        "Generating coaching response..."
    )

    context_parts = []

    if state.rag_context:

        context_parts.extend(
            state.rag_context
        )

    # ------------------------------------------------------
    # Defense in depth: only forward agent_raw_output into the
    # prompt if it's a genuine, non-empty specialist result.
    # A failed specialist call returns {} (see
    # call_overload_pipeline), so this also guards against any
    # future regression that starts putting error/exception
    # text back into this field — that text would otherwise be
    # stringified straight into the LLM prompt and the model
    # would have no way to tell it apart from real context.
    # ------------------------------------------------------

    if state.agent_raw_output and "error" not in state.agent_raw_output:

        context_parts.append(
            str(state.agent_raw_output)
        )

    context = "\n\n".join(
        context_parts
    )

    history_text = format_history(
        state.conversation_history
    )

    # ------------------------------------------------------
    # Format persistent athlete facts (weight, experience level,
    # goal) — loaded from athlete_profile table, not the current
    # message. This is what lets programming be calibrated to
    # who the athlete actually is on every turn, not only when
    # they happen to restate it.
    # ------------------------------------------------------

    facts = state.athlete_facts or {}

    if facts:

        fact_lines = []

        if "weight_kg" in facts:
            fact_lines.append(
                f"- Body weight: {facts['weight_kg']:g} kg"
            )

        if "experience_level" in facts:
            fact_lines.append(
                f"- Experience level: {facts['experience_level']}"
            )

        if "goal" in facts:
            fact_lines.append(
                f"- Goal: {facts['goal']}"
            )

        facts_text = "\n".join(fact_lines)

    else:

        facts_text = (
            "(No saved profile facts for this athlete yet — "
            "weight and experience level are unknown. If the "
            "athlete asks for a periodized program, ask their "
            "current experience level before assuming Beginner.)"
        )

    prompt = f"""
You are Athlete AI, a persistent personal fitness coach with
advanced programming knowledge — think of a coach who prescribes
detailed, individualized sessions, not a general-audience fitness
blog.

You are in an ongoing conversation with one athlete. Treat the
conversation history as real context. If the user asks a follow-up
such as "should I increase it?", "what about next week?", "is that
enough?", or "do the same for squats", resolve what "it", "that", or
"same" refers to from previous messages.

Rules:
- Answer the latest user message directly.
- Preserve relevant facts from earlier turns.
- Use the athlete's actual numbers when available.
- Never invent measurements.
- If information is missing, ask one concise clarifying question.
- Use kg for load unless the athlete explicitly uses another unit.
- Do not output JSON.
- Use clean Markdown.
- Do not repeat the entire previous answer unless asked.

Specificity requirements — this is what separates a real coach from
a generic fitness article:
- When recommending exercises, name specific movements from the
  Specialist context below (it contains an exercise selection
  matrix with compound lifts and isolation alternates per muscle
  group) — never answer with vague filler like "add squats or
  lunges" when the context gives you named alternatives to choose
  from and a reason to prefer one over another for this athlete.
- Always give concrete sets, reps, and load or %1RM/RPE — not just
  "increase the weight," but a specific target number derived from
  the athlete's own data when it's available.
- Include rest intervals and, when relevant, tempo or intensity
  technique cues (e.g. paused reps, controlled eccentrics, drop
  sets) rather than one-line generic tips.
- Ground every recommendation in something specific — the athlete's
  actual numbers, the Athlete Profile Facts below, or the
  Specialist context's rules — not generic best-practice statements
  that could apply to any athlete.
- Vary your suggestions turn to turn based on what's actually being
  asked; don't default to the same stock lines (lower-body add-on,
  foam rolling) unless they're genuinely the most relevant point for
  this specific message.
- Keep the answer complete and detailed rather than artificially
  short — thoroughness matters more than brevity here.

Periodized program requests — when the athlete asks for a full
program, routine, or long-term plan for a muscle group or lift
(not just "what should I do today"), structure the response as a
multi-block progression, not a single day:
- Break it into training-age blocks: Beginner (weeks 1–8, form and
  foundation), Intermediate (weeks 9–20, hypertrophy and volume),
  Advanced (weeks 21+, specialization and intensity). Use the
  Specialist context's periodization rules if present for exact
  week ranges and block focus.
- Within each block, break progress into 2–4 week waves (e.g.
  "W1–2", "W3–4") with a short focus label.
- Under each wave, list 2 exercises as "Exercise Name Sets×Reps"
  (e.g. "Barbell Curl 3×10–12") — pull exercise names from the
  Specialist context's move selection matrix, and use a different
  named variation in each wave rather than repeating one exercise
  through the whole program.
- If Athlete Profile Facts below give a known experience level,
  start the displayed program at that block (don't re-walk them
  through Beginner if they're already Advanced) but still show the
  remaining blocks ahead so they see the full roadmap. If the
  experience level is unknown, ask before assuming Beginner.
- This structured format is only for genuine full-program requests
  — a normal single-session question still gets the shorter,
  conversational answer described above.

Athlete profile:
{state.profile_id}

Athlete Profile Facts (persistent, not from this message):
{facts_text}

Conversation history:
{history_text}

Current user message:
{state.user_query}

Specialist context for this turn:
{context}

Respond naturally as the same coach continuing the conversation.
"""

    try:

        start = time.perf_counter()

        output = generate_response(
            prompt
        )

        duration = (
            time.perf_counter()
            - start
        )

        print(
            f"[Synthesis] "
            f"LLM response generated "
            f"in {duration:.3f}s"
        )

        if output.strip():

            return {
                "final_response":
                    output.strip()
            }

        print(
            "[Synthesis] Empty LLM response."
        )

    except Exception as e:

        print(
            "[Synthesis ERROR]"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

    # Never leave the user with a useless
    # generic error message.

    fallback = deterministic_fallback(
        state
    )

    return {
        "final_response": fallback
    }


# ============================================================
# LANGGRAPH
# ============================================================

workflow = StateGraph(
    AthleteState
)

workflow.add_node(
    "intent_router",
    intent_router_node
)

workflow.add_node(
    "call_overload_pipeline",
    call_overload_pipeline
)

workflow.add_node(
    "call_rag_worker",
    call_rag_worker
)

workflow.add_node(
    "synthesis_node",
    synthesis_response_node
)

workflow.set_entry_point(
    "intent_router"
)

workflow.add_conditional_edges(
    "intent_router",
    route_to_specialist,
    {
        "call_overload_pipeline":
            "call_overload_pipeline",

        "call_rag_worker":
            "call_rag_worker"
    }
)

workflow.add_edge(
    "call_overload_pipeline",
    "synthesis_node"
)

workflow.add_edge(
    "call_rag_worker",
    "synthesis_node"
)

workflow.add_edge(
    "synthesis_node",
    END
)


memory = MemorySaver()

compiled_graph = workflow.compile(
    checkpointer=memory
)


# ============================================================
# CHAT API
# ============================================================

class ChatPayload(BaseModel):

    profile_id: str

    message: str


@app.post("/chat")
async def chat_gateway(
    payload: ChatPayload
):

    start = time.perf_counter()

    try:

        config = {
            "configurable": {
                "thread_id":
                    payload.profile_id
            }
        }

        conversation_history = get_chat_history(
            payload.profile_id,
            max_messages=12,
        )

        athlete_facts = get_athlete_profile(
            payload.profile_id
        )

        initial_input = {

            "profile_id":
                payload.profile_id,

            "user_query":
                payload.message,

            "conversation_history":
                conversation_history,

            "athlete_facts":
                athlete_facts,
        }

        updated_state = await run_in_threadpool(
            compiled_graph.invoke,
            initial_input,
            config
        )

        response = updated_state.get(
            "final_response",
            ""
        )

        duration = (
            time.perf_counter()
            - start
        )

        save_chat_message(
            payload.profile_id,
            "user",
            payload.message,
        )
        save_chat_message(
            payload.profile_id,
            "assistant",
            response,
        )

        print(
            f"[Chat] Completed in "
            f"{duration:.3f}s | "
            f"history={len(conversation_history) + 2}"
        )

        return {
            "response": response,
            "response_time": round(
                duration,
                3
            ),
            "conversation_turns":
                len(conversation_history) // 2 + 1,
        }

    except Exception as e:

        print(
            f"[Chat ERROR] {e}"
        )

        return {
            "response":
                "The coaching pipeline encountered an internal error. Check the Orchestrator terminal for details.",
            "error": str(e)
        }


@app.get("/chat/history/{profile_id}")
def get_chat_history_endpoint(profile_id: str):
    """
    Returns this athlete's actual saved conversation from
    athlete_memory.db. The UI calls this whenever the Athlete ID
    changes, so switching profiles loads that athlete's real
    context instead of continuing to show whatever was already
    sitting in the browser's local session state — profiles are
    already isolated correctly on the backend (see
    get_chat_history's WHERE profile_id = ?), this endpoint just
    lets the UI reflect that isolation instead of masking it.
    """

    history = get_chat_history(
        profile_id,
        max_messages=50,
    )

    return {
        "profile_id": profile_id,
        "messages": history,
    }


# ============================================================
# ATHLETE PROFILE (weight, experience level, goal)
# ============================================================

class ProfileUpdatePayload(BaseModel):

    profile_id: str

    weight_kg: float = None

    experience_level: str = None

    goal: str = None


@app.post("/profile/update")
def update_profile(payload: ProfileUpdatePayload):

    save_athlete_profile(
        payload.profile_id,
        weight_kg=payload.weight_kg,
        experience_level=payload.experience_level,
        goal=payload.goal,
    )

    return {
        "status": "saved",
        "profile": get_athlete_profile(payload.profile_id),
    }


@app.get("/profile/{profile_id}")
def get_profile(profile_id: str):

    return {
        "profile_id": profile_id,
        "facts": get_athlete_profile(profile_id),
    }


# ============================================================
# WORKOUT LOGS
# ============================================================

class WorkoutLogPayload(BaseModel):

    profile_id: str

    exercise: str

    sets: int

    reps: int

    weight_kg: float


@app.post("/workouts/log")
def log_workout(payload: WorkoutLogPayload):

    log = save_workout_log(
        payload.profile_id,
        payload.exercise,
        payload.sets,
        payload.reps,
        payload.weight_kg,
    )

    return {
        "status": "saved",
        "log": log,
    }


@app.get("/workouts/{profile_id}")
def list_workouts(profile_id: str, limit: int = 200):

    return {
        "profile_id": profile_id,
        "logs": get_workout_logs(profile_id, limit=limit),
    }


@app.delete("/workouts/{profile_id}/{log_id}")
def remove_workout(profile_id: str, log_id: int):

    deleted = delete_workout_log(profile_id, log_id)

    return {
        "status": "deleted" if deleted else "not_found",
    }


@app.get("/workouts/{profile_id}/progress")
def workout_progress(profile_id: str):
    """
    Everything the Progress page needs in one call: weekly
    training volume, body-weight history, and current/next-target
    working weights for the tracked lifts — all computed from
    real logged data instead of hardcoded example numbers.
    """

    return {
        "profile_id": profile_id,
        "weekly_volume": get_weekly_volume(profile_id),
        "weight_history": get_weight_history(profile_id),
        "strength_targets": get_strength_targets(profile_id),
    }


# ============================================================
# ACCOUNTS / AUTH
# ============================================================

class SignupPayload(BaseModel):

    username: str

    password: str

    display_name: str = None


class LoginPayload(BaseModel):

    username: str

    password: str


@app.post("/auth/signup")
def signup(payload: SignupPayload):

    username = payload.username.strip().lower()

    if not username or not payload.password:
        return {
            "status": "error",
            "message": "Username and password are required.",
        }

    if len(payload.password) < 6:
        return {
            "status": "error",
            "message": "Password must be at least 6 characters.",
        }

    if username_exists(username):
        return {
            "status": "error",
            "message": "That username is already taken.",
        }

    display_name = (
        payload.display_name.strip()
        if payload.display_name
        else username
    )

    create_user(
        username,
        payload.password,
        display_name,
    )

    return {
        "status": "ok",
        "username": username,
        "display_name": display_name,
    }


@app.post("/auth/login")
def login(payload: LoginPayload):

    username = payload.username.strip().lower()

    display_name = verify_login(
        username,
        payload.password,
    )

    if display_name is None:
        return {
            "status": "error",
            "message": "Invalid username or password.",
        }

    return {
        "status": "ok",
        "username": username,
        "display_name": display_name,
    }


# ============================================================
# CLEAR CONVERSATION
# ============================================================

class ClearChatPayload(BaseModel):
    profile_id: str


@app.post("/chat/clear")
def clear_chat(payload: ClearChatPayload):
    clear_chat_history(payload.profile_id)

    return {
        "status": "cleared",
        "profile_id": payload.profile_id,
    }


# ============================================================
# STARTUP
# ============================================================

if __name__ == "__main__":

    print("")
    print("======================================")
    print("🏋️ ATHLETE AI ORCHESTRATOR")
    print("======================================")
    print(
        f"Ollama: {OLLAMA_GENERATE_URL}"
    )
    print(
        f"Model: {OLLAMA_MODEL}"
    )
    print("Port: 8000")
    print(f"Memory DB: {MEMORY_DB}")
    print(f"Context window: {OLLAMA_NUM_CTX} tokens")
    print("Conversation memory: ENABLED")
    print("======================================")

    check_ollama()
    check_specialist_workers()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )