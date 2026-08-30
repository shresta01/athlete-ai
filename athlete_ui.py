import streamlit as st
import requests
import time
from textwrap import dedent


# ============================================================
# ATHLETE AI — FITNESS GEN-AI UI
# Complete replacement for athlete_ui.py
#
# IMPORTANT:
# All custom HTML is passed through render_html().
# This prevents Streamlit from displaying HTML as plain text.
#
# Backend contract:
# POST http://127.0.0.1:8000/chat
#
# {
#   "profile_id": "...",
#   "message": "..."
# }
#
# Expected response:
# {
#   "response": "..."
# }
# ============================================================


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Athlete AI",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# HTML RENDER HELPER
# ============================================================
#
# DO NOT use st.markdown("""...HTML...""") directly elsewhere.
# Every custom HTML block goes through this function.
#
# dedent() removes the COMMON leading whitespace shared by all
# lines. That alone is NOT enough here: nested <div> blocks are
# indented relative to each other, so after dedent() most lines
# still start with 4+ spaces. Streamlit's markdown parser treats
# any line indented 4+ spaces as a code block, which is exactly
# why nested HTML was rendering as plain/monospace text even
# with unsafe_allow_html=True.
#
# Fix: after dedent+strip, also strip leading whitespace from
# EVERY individual line. HTML doesn't care about whitespace
# between tags (nothing here uses <pre>/whitespace-sensitive
# content), so this is safe and keeps Markdown from treating
# any line as an indented code block.
# ============================================================

def render_html(html_content: str):
    text = dedent(html_content).strip()
    cleaned = "\n".join(line.lstrip() for line in text.split("\n"))
    st.markdown(
        cleaned,
        unsafe_allow_html=True,
    )


# ============================================================
# GLOBAL CSS
# ============================================================

render_html(
    """
    <style>
        :root {
            --bg: #070a11;
            --panel: #101520;
            --panel2: #141a27;
            --border: rgba(255,255,255,.08);
            --muted: #8992a6;
            --text: #f5f7fb;
            --accent: #7c8cff;
            --green: #54e39a;
            --orange: #ffad42;
        }

        .stApp {
            background:
                radial-gradient(
                    circle at 85% 0%,
                    rgba(124,140,255,.13),
                    transparent 28%
                ),
                radial-gradient(
                    circle at 10% 100%,
                    rgba(54,211,153,.05),
                    transparent 25%
                ),
                linear-gradient(
                    135deg,
                    #060810 0%,
                    #0a0e17 50%,
                    #070910 100%
                );
            color: var(--text);
        }

        .main .block-container {
            max-width: 1480px;
            padding: 2.2rem 2.4rem 5rem;
        }

        section[data-testid="stSidebar"] {
            background: #080b12;
            border-right: 1px solid var(--border);
        }

        section[data-testid="stSidebar"] .block-container {
            padding: 2rem 1.15rem;
        }

        /* ----------------------------------------------------
           BRAND
        ---------------------------------------------------- */

        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.25rem;
            font-weight: 800;
            color: #fff;
        }

        .brand-icon {
            width: 34px;
            height: 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 11px;
            background: linear-gradient(
                135deg,
                #7c8cff,
                #5967ff
            );
            box-shadow: 0 8px 24px rgba(92,108,255,.25);
        }

        .brand-sub {
            color: var(--muted);
            font-size: .78rem;
            margin-top: 6px;
        }

        /* ----------------------------------------------------
           HERO
        ---------------------------------------------------- */

        .hero {
            padding: 28px 30px;
            border: 1px solid var(--border);
            border-radius: 24px;
            background:
                radial-gradient(
                    circle at 90% 0%,
                    rgba(124,140,255,.18),
                    transparent 35%
                ),
                linear-gradient(
                    145deg,
                    #151b29,
                    #0d111a
                );
            box-shadow: 0 18px 60px rgba(0,0,0,.18);
            margin-bottom: 22px;
        }

        .eyebrow {
            color: #98a4ff;
            font-size: .76rem;
            font-weight: 800;
            letter-spacing: .12em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .hero-title {
            font-size: 2.35rem;
            font-weight: 850;
            letter-spacing: -.04em;
            color: #fff;
            margin: 0;
        }

        .hero-sub {
            color: #929bad;
            margin-top: 8px;
            font-size: 1rem;
        }

        .status {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            margin-top: 18px;
            padding: 7px 12px;
            border-radius: 999px;
            background: rgba(84,227,154,.08);
            border: 1px solid rgba(84,227,154,.20);
            color: #66e9a5;
            font-size: .76rem;
            font-weight: 800;
        }

        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #54e39a;
            box-shadow: 0 0 10px #54e39a;
        }

        /* ----------------------------------------------------
           METRICS
        ---------------------------------------------------- */

        .metric {
            min-height: 145px;
            padding: 20px;
            border: 1px solid var(--border);
            border-radius: 18px;
            background:
                linear-gradient(
                    145deg,
                    rgba(21,26,38,.96),
                    rgba(12,16,24,.96)
                );
            box-shadow: 0 12px 35px rgba(0,0,0,.16);
        }

        .metric-label {
            color: #7f899d;
            font-size: .70rem;
            font-weight: 800;
            letter-spacing: .12em;
            text-transform: uppercase;
        }

        .metric-value {
            color: #fff;
            font-size: 2rem;
            line-height: 1;
            font-weight: 850;
            margin-top: 14px;
        }

        .metric-change {
            color: #8b95a8;
            font-size: .78rem;
            margin-top: 9px;
        }

        /* ----------------------------------------------------
           SECTIONS
        ---------------------------------------------------- */

        .section-title {
            color: #fff;
            font-size: 1.55rem;
            font-weight: 800;
            letter-spacing: -.025em;
            margin: 4px 0 4px;
        }

        .section-sub {
            color: #8b95a8;
            margin-bottom: 18px;
        }

        /* ----------------------------------------------------
           CARDS
        ---------------------------------------------------- */

        .card {
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 22px;
            background:
                linear-gradient(
                    145deg,
                    #121824,
                    #0d111a
                );
            box-shadow: 0 12px 40px rgba(0,0,0,.14);
        }

        .coach-card {
            min-height: 260px;
            border: 1px solid rgba(124,140,255,.18);
            border-radius: 20px;
            padding: 24px;
            background:
                radial-gradient(
                    circle at 100% 0%,
                    rgba(124,140,255,.16),
                    transparent 42%
                ),
                linear-gradient(
                    145deg,
                    #141a28,
                    #0e131d
                );
        }

        /* ----------------------------------------------------
           EXERCISES
        ---------------------------------------------------- */

        .exercise {
            padding: 16px 0;
            border-bottom: 1px solid rgba(255,255,255,.06);
        }

        .exercise:last-child {
            border-bottom: 0;
        }

        .exercise-name {
            color: #fff;
            font-weight: 750;
            font-size: 1rem;
        }

        .exercise-meta {
            color: #8992a6;
            font-size: .82rem;
            margin-top: 5px;
        }

        /* ----------------------------------------------------
           QUICK CARDS
        ---------------------------------------------------- */

        .quick {
            min-height: 82px;
        }

        .mini-label {
            color: #7e889c;
            font-size: .70rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .1em;
        }

        .big-number {
            color: #fff;
            font-size: 1.8rem;
            font-weight: 850;
            margin-top: 6px;
        }

        /* ----------------------------------------------------
           TIPS
        ---------------------------------------------------- */

        .tip {
            border-left: 3px solid #7c8cff;
            padding: 12px 16px;
            border-radius: 0 12px 12px 0;
            background: rgba(124,140,255,.06);
            color: #c6ccda;
            margin: 10px 0;
        }

        /* ----------------------------------------------------
           BUTTONS
        ---------------------------------------------------- */

        .stButton > button {
            min-height: 44px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,.08);
            background: rgba(255,255,255,.035);
            color: #eef1f7;
            font-weight: 700;
            transition: .18s ease;
        }

        .stButton > button:hover {
            border-color: rgba(124,140,255,.55);
            background: rgba(124,140,255,.12);
            transform: translateY(-1px);
        }

        .stButton > button[kind="primary"] {
            background:
                linear-gradient(
                    135deg,
                    #6878ff,
                    #5364ef
                );
            border-color: rgba(255,255,255,.12);
        }

        .stButton > button:disabled {
            opacity: .45;
            cursor: not-allowed;
            transform: none;
        }

        /* ----------------------------------------------------
           INPUTS
        ---------------------------------------------------- */

        .stTextInput input,
        .stNumberInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div {
            background: #0d121c !important;
            color: #f4f6fa !important;
            border-color: rgba(255,255,255,.10) !important;
            border-radius: 11px !important;
        }

        /* ----------------------------------------------------
           CHAT
        ---------------------------------------------------- */

        [data-testid="stChatMessage"] {
            border: 1px solid rgba(255,255,255,.055);
            border-radius: 18px;
            padding: 4px 8px;
            margin-bottom: 10px;
            background: rgba(255,255,255,.018);
        }

        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] li,
        [data-testid="stChatMessage"] span,
        [data-testid="stChatMessage"] div {
            color: var(--text) !important;
            opacity: 1 !important;
        }

        [data-testid="stChatInput"] {
            padding-bottom: 8px;
        }

        /* ----------------------------------------------------
           BUTTON LABEL TEXT
           Streamlit wraps button labels in their own <p>/<div>,
           which can end up dimmer than the button color set
           above. Force full brightness explicitly.
        ---------------------------------------------------- */

        .stButton > button p,
        .stButton > button div,
        .stButton > button span {
            color: inherit !important;
            opacity: 1 !important;
        }

        /* ----------------------------------------------------
           STALE-ELEMENT FADE
           Streamlit tags widgets data-stale="true" while a
           rerun is catching up and fades their opacity. On
           this app almost everything reruns on every click/
           chat submission, so most of the UI can look dim
           even after the response has already loaded. Force
           full opacity so content never looks washed out.
        ---------------------------------------------------- */

        [data-stale="true"] {
            opacity: 1 !important;
            transition: none !important;
        }

        /* ----------------------------------------------------
           WIDGET LABELS
           Streamlit's default label color (a muted gray meant
           for its own lighter dark theme) is too dim against
           this app's near-black background — "Username",
           "Password", and the Login/Sign Up radio text were
           barely legible. Force full-brightness text on every
           label, radio option, and checkbox across the app.
        ---------------------------------------------------- */

        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label,
        [data-testid="stWidgetLabel"] span,
        .stRadio label,
        .stRadio p,
        .stRadio span,
        .stCheckbox label,
        .stCheckbox p,
        .stCheckbox span,
        .stSelectbox label,
        .stTextInput label,
        .stNumberInput label,
        .stTextArea label {
            color: #f5f7fb !important;
            opacity: 1 !important;
        }

        /* Radio option text specifically sits in a nested div
           that the selectors above don't always reach depending
           on Streamlit version — belt-and-suspenders catch-all
           scoped to just the radio group so it can't leak into
           unrelated dark-on-dark text elsewhere. */
        div[role="radiogroup"] * {
            color: #f5f7fb !important;
            opacity: 1 !important;
        }

        /* ----------------------------------------------------
           SIDEBAR
        ---------------------------------------------------- */

        .sidebar-section {
            color: #737d92;
            font-size: .72rem;
            font-weight: 800;
            letter-spacing: .1em;
            text-transform: uppercase;
            margin: 16px 0 8px;
        }

        /* ----------------------------------------------------
           STREAMLIT UI
        ---------------------------------------------------- */

        #MainMenu,
        footer {
            visibility: hidden;
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        /* ----------------------------------------------------
           MOBILE
        ---------------------------------------------------- */

        @media (max-width: 900px) {
            .main .block-container {
                padding: 1.2rem .85rem 4rem;
            }

            .hero-title {
                font-size: 1.8rem;
            }

            .metric {
                min-height: 120px;
            }

            .metric-value {
                font-size: 1.55rem;
            }
        }
    </style>
    """
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "page": "Dashboard",
    # profile_id is now set from the logged-in username rather
    # than typed in manually — see the login gate below. It stays
    # in session_state under the same key so every existing call
    # site (ask_ai, load_profile_facts, /profile/update, etc.)
    # keeps working unchanged.
    "profile_id": None,
    "authenticated": False,
    "display_name": None,
    "auth_mode": "Login",
    "auth_error": None,
    "backend_url": "http://127.0.0.1:8000/chat",
    "chat_history": [],
    "workout_started": False,
    "workout_logs": [],
    "weight": 82.4,
    "goal": "Muscle Gain / Bulking",
    "experience_level": "Beginner",
    "last_ai_duration": None,
    # True while a request to the AI backend is in flight.
    # Used to disable buttons so a slow/dimmed rerun can't be
    # double-clicked into sending duplicate messages.
    "busy": False,
    # Which profile's history is currently reflected in
    # chat_history. Starts as None so the first script run always
    # loads the default profile's real saved history from the
    # backend instead of showing an empty/local chat that could
    # be mistaken for a shared conversation.
    "loaded_profile_id": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# BACKEND
# ============================================================

@st.cache_resource
def get_http_session():
    return requests.Session()


def get_api_root():
    """
    backend_url is typically '.../chat'. /chat/history/{id} is
    nested under that and can just append a path segment (see
    load_profile_history above) — but /profile/update and
    /profile/{id} are top-level routes on the orchestrator, not
    nested under /chat, so they need the '/chat' suffix stripped
    off first.
    """

    url = st.session_state.backend_url.rstrip("/")

    if url.endswith("/chat"):
        return url[: -len("/chat")]

    return url


def auth_request(path: str, username: str, password: str, display_name: str = None):
    """
    Calls /auth/signup or /auth/login on the orchestrator.

    Returns (status, payload) where status is "ok" or "error".
    On any network/backend failure, returns ("error", {message}) —
    never raises — so the login form can always show something
    useful instead of crashing the whole app.
    """

    body = {
        "username": username,
        "password": password,
    }

    if display_name is not None:
        body["display_name"] = display_name

    try:
        response = get_http_session().post(
            get_api_root() + path,
            json=body,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        return data.get("status", "error"), data

    except requests.exceptions.ConnectionError:
        return "error", {
            "message": (
                "Can't reach the AI backend. Make sure the "
                "orchestrator is running on port 8000."
            )
        }

    except Exception as exc:
        return "error", {"message": f"Backend error: {exc}"}


def load_profile_facts(profile_id: str):
    """
    Fetch this profile's saved weight/experience level/goal from
    the backend (athlete_profile table), so switching Athlete ID
    also pre-fills the Nutrition page with that athlete's own
    saved facts instead of leaving whatever the previous profile
    had entered.

    Returns {} (never raises) on any failure or if nothing has
    been saved for this profile yet.
    """

    try:

        profile_url = (
            get_api_root()
            + "/profile/"
            + profile_id
        )

        response = get_http_session().get(
            profile_url,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        return data.get("facts", {})

    except Exception as e:

        print(
            f"[load_profile_facts] "
            f"Could not load facts for "
            f"{profile_id!r}: {e}"
        )

        return {}


def load_profile_history(profile_id: str):
    """
    Fetch this profile's real saved conversation from the backend
    (athlete_memory.db, scoped by profile_id there already).

    Without this, switching the Athlete ID in the sidebar left
    chat_history showing whatever was previously in the browser's
    local session state — the backend was already isolating
    profiles correctly, but the UI wasn't reflecting that, so
    switching IDs looked like profiles were sharing context when
    really the UI just hadn't asked the backend for the new
    profile's actual history yet.

    Returns [] (never raises) on any failure — a fresh/unreachable
    backend should behave like "no history yet", not break the UI.
    """

    try:

        history_url = (
            st.session_state.backend_url.rstrip("/")
            + "/history/"
            + profile_id
        )

        response = get_http_session().get(
            history_url,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        return data.get("messages", [])

    except Exception as e:

        print(
            f"[load_profile_history] "
            f"Could not load history for "
            f"{profile_id!r}: {e}"
        )

        return []


def log_workout_backend(profile_id: str, exercise: str, sets: int, reps: int, weight_kg: float):
    """
    Persists one logged exercise to workout_logs via the backend.
    Returns (success, message) — never raises, so a down backend
    shows a clean error instead of crashing the Workout page.
    """

    try:
        response = get_http_session().post(
            get_api_root() + "/workouts/log",
            json={
                "profile_id": profile_id,
                "exercise": exercise,
                "sets": sets,
                "reps": reps,
                "weight_kg": weight_kg,
            },
            timeout=10,
        )

        response.raise_for_status()

        return True, None

    except Exception as e:
        return False, str(e)


def load_workout_logs_backend(profile_id: str):
    """
    Fetches this athlete's real logged exercises. Returns []
    (never raises) on any failure — a fresh/unreachable backend
    should behave like "no logs yet," not break the page.
    """

    try:
        response = get_http_session().get(
            get_api_root() + "/workouts/" + profile_id,
            timeout=10,
        )

        response.raise_for_status()

        return response.json().get("logs", [])

    except Exception as e:
        print(f"[load_workout_logs_backend] {e}")
        return []


def delete_workout_log_backend(profile_id: str, log_id: int):
    try:
        response = get_http_session().delete(
            get_api_root() + f"/workouts/{profile_id}/{log_id}",
            timeout=10,
        )

        response.raise_for_status()

        return True

    except Exception as e:
        print(f"[delete_workout_log_backend] {e}")
        return False


def load_workout_progress_backend(profile_id: str):
    """
    Fetches the aggregated data the Progress page charts: weekly
    training volume, body-weight history, and current/next-target
    working weights per tracked lift — all computed from real
    logs. Returns an empty-but-well-formed dict on failure so the
    page can render its "log something to see this" empty state
    instead of crashing.
    """

    empty = {
        "weekly_volume": [],
        "weight_history": [],
        "strength_targets": [],
    }

    try:
        response = get_http_session().get(
            get_api_root() + f"/workouts/{profile_id}/progress",
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        return {
            "weekly_volume": data.get("weekly_volume", []),
            "weight_history": data.get("weight_history", []),
            "strength_targets": data.get("strength_targets", []),
        }

    except Exception as e:
        print(f"[load_workout_progress_backend] {e}")
        return empty


def ask_ai(message: str):
    """
    Call the existing FastAPI/LangGraph orchestrator.
    """

    started = time.perf_counter()

    try:
        response = get_http_session().post(
            st.session_state.backend_url,
            json={
                "profile_id": st.session_state.profile_id,
                "message": message,
            },
            timeout=120,
        )

        response.raise_for_status()

        duration = time.perf_counter() - started
        data = response.json()

        answer = data.get("response")

        if not answer:
            answer = (
                "The AI backend responded, but no coaching "
                "response was returned."
            )

        st.session_state.last_ai_duration = duration

        return answer, duration, None

    except requests.exceptions.ConnectionError:
        return (
            "⚠️ I can't reach the AI backend. "
            "Make sure the orchestrator is running on port 8000.",
            0,
            "connection",
        )

    except requests.exceptions.Timeout:
        return (
            "⏳ The AI service is taking too long. "
            "Check whether Ollama has finished loading the model.",
            0,
            "timeout",
        )

    except requests.exceptions.HTTPError as exc:
        return (
            f"⚠️ AI backend returned an HTTP error: {exc}",
            0,
            "http",
        )

    except Exception as exc:
        return (
            f"⚠️ Backend error: {exc}",
            0,
            "error",
        )


def send_to_coach(prompt: str):
    """
    Add a user message, call the AI, then store the answer.

    Wrapped with the busy flag so buttons across the app stay
    disabled for the full round-trip, protecting against a
    double click landing before the previous request resolves.
    """

    st.session_state.busy = True

    st.session_state.chat_history.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    answer, duration, error = ask_ai(prompt)

    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )

    st.session_state.busy = False

    return answer, duration, error


def open_page(page: str):
    st.session_state.page = page
    st.rerun()


# ============================================================
# LOGIN / SIGN UP GATE
#
# Nothing below this point (sidebar, pages, chat) renders until
# an account is authenticated. profile_id is set to the logged-
# in username on success, so every existing backend call keeps
# working unchanged — the app just never lets someone pick an
# arbitrary profile_id anymore, they have to own it via login.
# ============================================================

def login_gate():

    page_left, page_mid, page_right = st.columns(
        [1, 1.3, 1]
    )

    with page_mid:

        render_html(
            """
            <div class="brand" style="justify-content:center; margin-bottom:6px;">
                <div class="brand-icon">🏋️</div>
                <div>Athlete AI</div>
            </div>

            <div class="brand-sub" style="text-align:center; margin-bottom:22px;">
                Sign in to load your training, nutrition and
                progress — or create an account to get started.
            </div>
            """
        )

        render_html('<div class="card">')

        mode = st.radio(
            "Mode",
            ["Login", "Sign Up"],
            index=(
                0 if st.session_state.auth_mode == "Login" else 1
            ),
            horizontal=True,
            label_visibility="collapsed",
        )

        st.session_state.auth_mode = mode
        st.session_state.auth_error = None

        with st.form(
            key=f"auth_form_{mode}",
            clear_on_submit=False,
        ):

            username = st.text_input(
                "Username",
                key="auth_username",
            ).strip().lower()

            display_name = None

            if mode == "Sign Up":

                display_name = st.text_input(
                    "Display name (optional)",
                    key="auth_display_name",
                ).strip()

            password = st.text_input(
                "Password",
                type="password",
                key="auth_password",
            )

            confirm_password = None

            if mode == "Sign Up":

                confirm_password = st.text_input(
                    "Confirm password",
                    type="password",
                    key="auth_password_confirm",
                )

            submitted = st.form_submit_button(
                "Log In" if mode == "Login" else "Create Account",
                type="primary",
                use_container_width=True,
            )

        if submitted:

            if not username or not password:
                st.session_state.auth_error = (
                    "Please enter both a username and password."
                )

            elif mode == "Sign Up" and password != confirm_password:
                st.session_state.auth_error = (
                    "Passwords don't match."
                )

            elif mode == "Sign Up":

                status, data = auth_request(
                    "/auth/signup",
                    username,
                    password,
                    display_name or username,
                )

                if status == "ok":

                    st.session_state.authenticated = True
                    st.session_state.profile_id = data["username"]
                    st.session_state.display_name = data["display_name"]
                    st.session_state.auth_error = None
                    st.rerun()

                else:
                    st.session_state.auth_error = data.get(
                        "message", "Sign up failed."
                    )

            else:

                status, data = auth_request(
                    "/auth/login",
                    username,
                    password,
                )

                if status == "ok":

                    st.session_state.authenticated = True
                    st.session_state.profile_id = data["username"]
                    st.session_state.display_name = data["display_name"]
                    st.session_state.auth_error = None
                    st.rerun()

                else:
                    st.session_state.auth_error = data.get(
                        "message", "Login failed."
                    )

        if st.session_state.auth_error:
            st.error(st.session_state.auth_error)

        render_html("</div>")


if not st.session_state.authenticated:
    login_gate()
    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    render_html(
        """
        <div class="brand">
            <div class="brand-icon">🏋️</div>
            <div>Athlete AI</div>
        </div>

        <div class="brand-sub">
            Your intelligent fitness companion
        </div>
        """
    )

    st.divider()

    render_html(
        """
        <div class="sidebar-section">
            Navigation
        </div>
        """
    )

    nav_items = [
        ("🏠", "Dashboard"),
        ("🤖", "AI Coach"),
        ("🏋️", "Workout"),
        ("🥗", "Nutrition"),
        ("📊", "Progress"),
    ]

    for icon, page in nav_items:

        if st.button(
            f"{icon}  {page}",
            key=f"nav_{page}",
            use_container_width=True,
            disabled=st.session_state.busy,
        ):
            open_page(page)

    st.divider()

    render_html(
        """
        <div class="sidebar-section">
            Athlete
        </div>
        """
    )

    render_html(
        f"""
        <div style="color:#f5f7fb; font-weight:750; font-size:1rem;">
            👤 {st.session_state.display_name or st.session_state.profile_id}
        </div>
        <div style="color:#7e889c; font-size:.78rem; margin-top:2px;">
            Signed in as {st.session_state.profile_id}
        </div>
        """
    )

    if st.button(
        "🚪 Log out",
        use_container_width=True,
        disabled=st.session_state.busy,
    ):

        for key in DEFAULTS:
            st.session_state[key] = DEFAULTS[key]

        st.rerun()

    st.session_state.backend_url = st.text_input(
        "AI Backend",
        value=st.session_state.backend_url,
    )

    # --------------------------------------------------------
    # Load the selected profile's REAL saved conversation
    # whenever the Athlete ID changes (including the first run,
    # since loaded_profile_id starts as None). This is what
    # keeps different athlete IDs from appearing to share
    # context — the backend already scopes history by
    # profile_id, this just makes the UI reflect that instead
    # of continuing to show whatever was left in local session
    # state from a previously-selected profile.
    # --------------------------------------------------------

    if (
        st.session_state.profile_id
        != st.session_state.loaded_profile_id
    ):

        st.session_state.chat_history = load_profile_history(
            st.session_state.profile_id
        )

        facts = load_profile_facts(
            st.session_state.profile_id
        )

        # Only overwrite fields this profile actually has saved
        # — an athlete who's never used the Nutrition page yet
        # should keep the app's defaults, not get blanked out.
        if "weight_kg" in facts:
            st.session_state.weight = facts["weight_kg"]

        if "experience_level" in facts:
            st.session_state.experience_level = facts["experience_level"]

        if "goal" in facts:
            st.session_state.goal = facts["goal"]

        st.session_state.loaded_profile_id = (
            st.session_state.profile_id
        )

    st.divider()

    render_html(
        """
        <div
            style="
                color:#8b95a8;
                font-size:.82rem;
                line-height:1.9;
            "
        >
            ⚡ Local AI inference<br>
            🧠 RAG powered<br>
            🔒 Private athlete context
        </div>
        """
    )

    if st.session_state.busy:

        st.caption("⏳ Coach is thinking...")

    elif st.session_state.last_ai_duration:

        st.caption(
            f"Last AI response: "
            f"{st.session_state.last_ai_duration:.2f}s"
        )


# ============================================================
# SHARED UI
# ============================================================

def page_header(title, subtitle, icon="🤖"):

    render_html(
        f"""
        <div class="hero">

            <div class="eyebrow">
                {icon} ATHLETE AI
            </div>

            <div class="hero-title">
                {title}
            </div>

            <div class="hero-sub">
                {subtitle}
            </div>

            <div class="status">
                <span class="status-dot"></span>
                AI SYSTEM ONLINE
            </div>

        </div>
        """
    )


def metric_card(label, value, change):

    render_html(
        f"""
        <div class="metric">

            <div class="metric-label">
                {label}
            </div>

            <div class="metric-value">
                {value}
            </div>

            <div class="metric-change">
                {change}
            </div>

        </div>
        """
    )


# ============================================================
# DASHBOARD
# ============================================================

def dashboard_page():

    page_header(
        f"Good evening, {st.session_state.display_name or 'Athlete'} 👋",
        "Your personal performance command center.",
        "🏆",
    )

    render_html(
        """
        <div class="section-title">
            Today's Overview
        </div>

        <div class="section-sub">
            A quick snapshot of your current training state.
        </div>
        """
    )

    m1, m2, m3, m4 = st.columns(4)

    # Real data for the two metrics we actually persist now.
    # Protein and Training Streak stay static placeholders —
    # they'd need a nutrition-intake log and a streak-tracking
    # table respectively, neither of which exists yet. Flagging
    # that here rather than quietly leaving stale-looking but
    # "real" numbers in their place.
    _dashboard_progress = load_workout_progress_backend(
        st.session_state.profile_id
    )
    _weight_history = _dashboard_progress["weight_history"]
    _weekly_volume = _dashboard_progress["weekly_volume"]

    with m1:

        if _weight_history:

            current_weight = _weight_history[-1]["weight_kg"]

            if len(_weight_history) >= 2:
                delta = current_weight - _weight_history[-2]["weight_kg"]
                change_text = f"{delta:+.1f} kg vs last entry"
            else:
                change_text = "first entry logged"

            metric_card(
                "Body Weight",
                f"{current_weight:g} kg",
                change_text,
            )

        else:

            metric_card(
                "Body Weight",
                "—",
                "Save your weight on Nutrition",
            )

    with m2:

        if _weekly_volume:

            current_volume = _weekly_volume[-1]["volume_kg"]

            if len(_weekly_volume) >= 2:
                prev_volume = _weekly_volume[-2]["volume_kg"]
                if prev_volume:
                    pct = (current_volume - prev_volume) / prev_volume * 100
                    change_text = f"{pct:+.1f}% vs last week"
                else:
                    change_text = "this week"
            else:
                change_text = "this week"

            metric_card(
                "Weekly Volume",
                f"{current_volume:,.0f} kg",
                change_text,
            )

        else:

            metric_card(
                "Weekly Volume",
                "—",
                "Log a set on Workout",
            )

    with m3:
        metric_card(
            "Protein",
            "142 g",
            "165 g daily target",
        )

    with m4:
        metric_card(
            "Training Streak",
            "12 🔥",
            "days active",
        )

    st.write("")

    left, right = st.columns(
        [1.55, 1],
        gap="large",
    )

    with left:

        render_html(
            """
            <div class="card">

                <div class="section-title">
                    🏋️ Today's Workout
                </div>

                <div class="section-sub">
                    Push • Hypertrophy
                </div>

                <div class="exercise">

                    <div class="exercise-name">
                        Bench Press
                    </div>

                    <div class="exercise-meta">
                        4 × 8 @ 80 kg
                    </div>

                </div>

                <div class="exercise">

                    <div class="exercise-name">
                        Overhead Press
                    </div>

                    <div class="exercise-meta">
                        3 × 8 @ 40 kg
                    </div>

                </div>

                <div class="exercise">

                    <div class="exercise-name">
                        Incline Dumbbell Press
                    </div>

                    <div class="exercise-meta">
                        3 × 10
                    </div>

                </div>

            </div>
            """
        )

        st.write("")

        b1, b2 = st.columns(2)

        with b1:

            if st.button(
                "🚀 Start Workout",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.busy,
            ):
                st.session_state.workout_started = True
                open_page("Workout")

        with b2:

            if st.button(
                "🤖 Talk to AI Coach",
                use_container_width=True,
                disabled=st.session_state.busy,
            ):
                open_page("AI Coach")

    with right:

        render_html(
            """
            <div class="coach-card">

                <div class="section-title">
                    🤖 AI Coach Insight
                </div>

                <div class="section-sub">
                    Based on your current training trend
                </div>

                <div class="tip">
                    Your weekly training volume is up
                    <b>8.2%</b>.
                </div>

                <div class="tip">
                    Your progression is currently within target.
                </div>

                <div class="tip">
                    Bench press is ready for a controlled
                    progression next session.
                </div>

            </div>
            """
        )

        st.write("")

        if st.button(
            "💬 Ask about my training",
            use_container_width=True,
            disabled=st.session_state.busy,
        ):
            open_page("AI Coach")


# ============================================================
# AI COACH
# ============================================================

def ai_coach_page():

    page_header(
        "AI Coach",
        (
            "Ask your personal performance intelligence system "
            "anything about training, nutrition or progress."
        ),
        "🤖",
    )

    render_html(
        """
        <div class="section-title">
            Quick Actions
        </div>

        <div class="section-sub">
            One tap sends a focused request to your fitness agents.
        </div>
        """
    )

    q1, q2, q3, q4 = st.columns(4)

    quick_prompt = None

    with q1:

        if st.button(
            "🏋️ Optimize Workout",
            key="quick_workout",
            use_container_width=True,
            disabled=st.session_state.busy,
        ):
            quick_prompt = (
                "Analyze my current workout and suggest how I can "
                "optimize it for hypertrophy while managing recovery "
                "and progressive overload."
            )

    with q2:

        if st.button(
            "🥗 Nutrition Plan",
            key="quick_nutrition",
            use_container_width=True,
            disabled=st.session_state.busy,
        ):
            quick_prompt = (
                "Create a practical nutrition plan for muscle growth "
                "based on my current training, including calories, "
                "protein and meal examples."
            )

    with q3:

        if st.button(
            "📈 Analyze Progress",
            key="quick_progress",
            use_container_width=True,
            disabled=st.session_state.busy,
        ):
            quick_prompt = (
                "Analyze my recent training progress. Tell me what "
                "is improving, what needs attention, and whether I "
                "should increase load, maintain it, or consider a deload."
            )

    with q4:

        if st.button(
            "🔥 Next Session",
            key="quick_next",
            use_container_width=True,
            disabled=st.session_state.busy,
        ):
            quick_prompt = (
                "Based on my current performance, what should my next "
                "training session look like? Include exercises, sets, "
                "reps and progression."
            )

    st.divider()

    if quick_prompt:

        with st.spinner(
            "⚡ Coach is analyzing your athlete context..."
        ):
            _, duration, error = send_to_coach(
                quick_prompt
            )

        if error:
            st.error(
                st.session_state.chat_history[-1]["content"]
            )
        else:
            st.success(
                f"Coach response ready • {duration:.2f}s"
            )

        st.rerun()

    if not st.session_state.chat_history:

        render_html(
            """
            <div class="card">

                <div class="section-title">
                    👋 Your AI Coach is ready
                </div>

                <div class="section-sub">
                    Ask a natural-language question or use one
                    of the quick actions above.
                </div>

                <div class="tip">
                    Try:
                    <b>
                        "I did bench press 4 sets of 8 reps at
                        80 kg. Should I increase the weight next session?"
                    </b>
                </div>

                <div class="tip">
                    Try:
                    <b>
                        "How can I improve my push workout without
                        increasing recovery time?"
                    </b>
                </div>

            </div>
            """
        )

    for message in st.session_state.chat_history:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_message = st.chat_input(
        "Ask your AI Coach about training, nutrition, recovery or progress...",
        disabled=st.session_state.busy,
    )

    if user_message:

        st.session_state.busy = True

        with st.chat_message("user"):
            st.markdown(user_message)

        with st.chat_message("assistant"):

            with st.spinner("⚡ Analyzing..."):

                answer, duration, error = ask_ai(
                    user_message
                )

            st.markdown(answer)

            if duration > 0:
                st.caption(
                    f"⚡ Generated in {duration:.2f}s"
                )

        st.session_state.chat_history.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        st.session_state.chat_history.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        st.session_state.busy = False
        st.rerun()

    if st.session_state.chat_history:

        st.write("")

        if st.button(
            "🗑️ Clear conversation",
            key="clear_chat",
            disabled=st.session_state.busy,
        ):

            try:

                clear_url = (
                    st.session_state.backend_url.rstrip("/")
                    + "/clear"
                )

                get_http_session().post(
                    clear_url,
                    json={
                        "profile_id":
                            st.session_state.profile_id
                    },
                    timeout=10,
                )

            except Exception:
                pass

            st.session_state.chat_history = []
            st.rerun()


# ============================================================
# WORKOUT
# ============================================================

def workout_page():

    page_header(
        "Workout",
        (
            "Log your training and turn every session "
            "into structured athlete data."
        ),
        "🏋️",
    )

    if not st.session_state.workout_started:

        render_html(
            """
            <div class="card">

                <div class="section-title">
                    Ready to train?
                </div>

                <div class="section-sub">
                    Start today's session and record your
                    exercises, sets, reps and load.
                </div>

            </div>
            """
        )

        st.write("")

        if st.button(
            "🚀 Start Today's Workout",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.busy,
        ):

            st.session_state.workout_started = True
            st.rerun()

        return

    render_html(
        """
        <div class="section-title">
            🔥 Active Session
        </div>

        <div class="section-sub">
            Every logged exercise is saved to your account —
            it'll still be here next time you log in.
        </div>
        """
    )

    # ------------------------------------------------------
    # Always pull the real, persisted log for this athlete
    # rather than trusting whatever's left in session_state —
    # that's what makes "Remove" and cross-session logging
    # actually correct instead of just a local illusion.
    # ------------------------------------------------------

    st.session_state.workout_logs = load_workout_logs_backend(
        st.session_state.profile_id
    )

    exercise = st.selectbox(
        "Exercise",
        [
            "Bench Press",
            # "Squat" (not "Squats") to match the name the
            # Progress page's strength-target lookup and the
            # overload specialist both key on.
            "Squat",
            "Deadlift",
            "Overhead Press",
            "Incline Dumbbell Press",
            "Barbell Row",
            "Pull Ups",
        ],
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        sets = st.number_input(
            "Sets",
            min_value=1,
            max_value=20,
            value=4,
            step=1,
        )

    with c2:

        reps = st.number_input(
            "Reps",
            min_value=1,
            max_value=50,
            value=8,
            step=1,
        )

    with c3:

        load = st.number_input(
            "Weight (kg)",
            min_value=0.0,
            max_value=500.0,
            value=80.0,
            step=2.5,
        )

    volume = int(
        sets * reps * load
    )

    render_html(
        f"""
        <div class="metric">

            <div class="metric-label">
                Current Exercise Volume
            </div>

            <div class="metric-value">
                {volume:,} kg
            </div>

            <div class="metric-change">
                {sets} sets × {reps} reps × {load:g} kg
            </div>

        </div>
        """
    )

    st.write("")

    if st.button(
        "✅ Log Exercise",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.busy,
    ):

        success, error = log_workout_backend(
            st.session_state.profile_id,
            exercise,
            int(sets),
            int(reps),
            float(load),
        )

        if success:
            st.success(f"{exercise} logged.")
        else:
            st.error(f"Couldn't save that log: {error}")

        st.rerun()

    if st.session_state.workout_logs:

        st.divider()

        render_html(
            """
            <div class="section-title">
                📋 Your Logged Sets
            </div>
            """
        )

        total = 0

        for log in st.session_state.workout_logs:

            total += log["volume_kg"]

            c1, c2 = st.columns([5, 1])

            with c1:

                render_html(
                    f"""
                    <div class="exercise">

                        <div class="exercise-name">
                            {log["exercise"]}
                        </div>

                        <div class="exercise-meta">
                            {log["sets"]} × {log["reps"]}
                            @ {log["weight_kg"]:g} kg
                            • {log["volume_kg"]:,.0f} kg volume
                        </div>

                    </div>
                    """
                )

            with c2:

                if st.button(
                    "Remove",
                    key=f"remove_log_{log['id']}",
                    use_container_width=True,
                    disabled=st.session_state.busy,
                ):

                    delete_workout_log_backend(
                        st.session_state.profile_id,
                        log["id"],
                    )

                    st.rerun()

        render_html(
            f"""
            <div class="metric">

                <div class="metric-label">
                    Total Logged Volume
                </div>

                <div class="metric-value">
                    {total:,.0f} kg
                </div>

                <div class="metric-change">
                    {len(st.session_state.workout_logs)}
                    exercises logged
                </div>

            </div>
            """
        )

        st.write("")

        if st.button(
            "🤖 Ask AI to Analyze This Workout",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.busy,
        ):

            summary = ", ".join(
                (
                    f'{x["exercise"]}: '
                    f'{x["sets"]}x{x["reps"]}'
                    f'@{x["weight_kg"]:g}kg'
                )
                for x in st.session_state.workout_logs
            )

            prompt = (
                f"Analyze my current workout: {summary}. "
                "Evaluate training volume, progressive overload, "
                "exercise balance and recovery. Give me concrete "
                "recommendations for my next session."
            )

            with st.spinner("🤖 Coach is analyzing your workout..."):
                send_to_coach(prompt)

            open_page("AI Coach")

        st.write("")

        if st.button(
            "🏁 Finish Workout",
            use_container_width=True,
            disabled=st.session_state.busy,
        ):

            st.session_state.workout_started = False

            st.success(
                "Workout completed. Your logged sets are saved "
                "to your account and available anytime."
            )


# ============================================================
# NUTRITION
# ============================================================

def nutrition_page():

    page_header(
        "Nutrition",
        (
            "Personalized nutrition calculations plus your "
            "RAG-powered AI nutrition coach."
        ),
        "🥗",
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        weight = st.number_input(
            "Body weight (kg)",
            min_value=30.0,
            max_value=250.0,
            value=float(
                st.session_state.weight
            ),
            step=0.1,
        )

    goal_options = [
        "Muscle Gain / Bulking",
        "Fat Loss / Cutting",
        "Maintenance",
    ]

    level_options = [
        "Beginner",
        "Intermediate",
        "Advanced",
    ]

    with c2:

        goal = st.selectbox(
            "Goal",
            goal_options,
            index=goal_options.index(
                st.session_state.goal
            ),
        )

    with c3:

        activity = st.selectbox(
            "Training Level",
            level_options,
            index=level_options.index(
                st.session_state.experience_level
            ),
        )

    st.session_state.weight = weight
    st.session_state.goal = goal
    st.session_state.experience_level = activity

    # Preserve existing project formula.
    maintenance = weight * 33

    if goal == "Muscle Gain / Bulking":

        calories = maintenance + 400
        protein = weight * 2.0

    elif goal == "Fat Loss / Cutting":

        calories = maintenance - 500
        protein = weight * 2.4

    else:

        calories = maintenance
        protein = weight * 2.0

    fat_calories = calories * 0.225
    fat = fat_calories / 9

    protein_calories = protein * 4

    carb_calories = max(
        calories
        - protein_calories
        - fat_calories,
        0,
    )

    carbs = carb_calories / 4

    st.write("")

    m1, m2, m3, m4 = st.columns(4)

    with m1:

        metric_card(
            "Daily Calories",
            f"{calories:,.0f}",
            "estimated target",
        )

    with m2:

        metric_card(
            "Protein",
            f"{protein:.0f} g",
            "daily target",
        )

    with m3:

        metric_card(
            "Carbohydrates",
            f"{carbs:.0f} g",
            "estimated target",
        )

    with m4:

        metric_card(
            "Fat",
            f"{fat:.0f} g",
            "estimated target",
        )

    st.write("")

    if st.button(
        "💾 Save Profile",
        use_container_width=True,
        disabled=st.session_state.busy,
    ):

        try:

            profile_url = (
                get_api_root()
                + "/profile/update"
            )

            get_http_session().post(
                profile_url,
                json={
                    "profile_id": st.session_state.profile_id,
                    "weight_kg": weight,
                    "experience_level": activity,
                    "goal": goal,
                },
                timeout=10,
            )

            st.success(
                "Profile saved — the AI Coach will use these "
                "facts on every future turn for this athlete."
            )

        except Exception as e:

            st.error(
                f"Could not save profile: {e}"
            )

    st.divider()

    render_html(
        """
        <div class="section-title">
            🤖 AI Nutrition Coach
        </div>

        <div class="section-sub">
            Generate a practical plan using your nutrition
            agent and knowledge base.
        </div>
        """
    )

    if st.button(
        "✨ Generate Personalized Nutrition Plan",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.busy,
    ):

        prompt = (
            f"I weigh {weight} kg. "
            f"My goal is {goal}. "
            f"My training level is {activity}. "
            "Create a practical daily nutrition plan with "
            "calories, protein, carbohydrates, fats and meal "
            "examples. Use the nutrition knowledge base. "
            f"My calculated calorie target is approximately "
            f"{calories:.0f} kcal and protein target is "
            f"approximately {protein:.0f} g."
        )

        with st.spinner(
            "🥗 Building your nutrition plan..."
        ):

            send_to_coach(prompt)

        open_page("AI Coach")


# ============================================================
# PROGRESS
# ============================================================

def progress_page():

    page_header(
        "Progress",
        (
            "See your performance trends and ask AI "
            "to interpret the data."
        ),
        "📊",
    )

    progress = load_workout_progress_backend(
        st.session_state.profile_id
    )

    weight_history = progress["weight_history"]
    weekly_volume = progress["weekly_volume"]
    strength_targets = progress["strength_targets"]

    left, right = st.columns(
        2,
        gap="large",
    )

    with left:

        render_html(
            """
            <div class="section-title">
                Body Weight
            </div>
            """
        )

        if len(weight_history) >= 2:

            st.line_chart(
                {
                    "Body Weight (kg)": [
                        entry["weight_kg"]
                        for entry in weight_history
                    ]
                },
                height=280,
            )

        else:

            render_html(
                """
                <div class="tip">
                    Save your weight on the Nutrition page a
                    couple of times to start seeing a trend here.
                </div>
                """
            )

    with right:

        render_html(
            """
            <div class="section-title">
                Weekly Training Volume
            </div>
            """
        )

        if weekly_volume:

            st.bar_chart(
                {
                    "Volume": [
                        entry["volume_kg"]
                        for entry in weekly_volume
                    ]
                },
                height=280,
            )

        else:

            render_html(
                """
                <div class="tip">
                    Log a set on the Workout page to start
                    building your weekly volume trend.
                </div>
                """
            )

    st.divider()

    render_html(
        """
        <div class="section-title">
            💪 Strength Progress
        </div>

        <div class="section-sub">
            Heaviest logged set per lift, and a suggested next target.
        </div>
        """
    )

    if strength_targets:

        st.dataframe(
            {
                "Exercise": [
                    t["exercise"] for t in strength_targets
                ],
                "Current": [
                    f"{t['current_kg']:g} kg"
                    for t in strength_targets
                ],
                "Next Target": [
                    f"{t['next_target_kg']:g} kg"
                    for t in strength_targets
                ],
            },
            use_container_width=True,
            hide_index=True,
        )

    else:

        render_html(
            """
            <div class="tip">
                Log Bench Press, Squat, Deadlift, or Overhead
                Press on the Workout page to see targets here.
            </div>
            """
        )

    st.write("")

    has_any_data = bool(
        weight_history or weekly_volume or strength_targets
    )

    if st.button(
        "🤖 Ask AI to Analyze My Progress",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.busy,
    ):

        if has_any_data:

            prompt_parts = [
                "Analyze my recent fitness progress using the "
                "following real data."
            ]

            if weight_history:
                prompt_parts.append(
                    f"My body weight is currently "
                    f"{weight_history[-1]['weight_kg']:g} kg."
                )

            if weekly_volume:
                latest_week = weekly_volume[-1]["volume_kg"]
                prompt_parts.append(
                    f"My most recent weekly training volume is "
                    f"{latest_week:g} kg."
                )

            if strength_targets:
                targets_text = ", ".join(
                    f"{t['exercise']} {t['current_kg']:g} kg"
                    for t in strength_targets
                )
                prompt_parts.append(
                    f"My current working weights are: {targets_text}."
                )

            prompt_parts.append(
                "Tell me what is progressing, what I should "
                "improve, and whether I should increase training "
                "load, maintain it, or consider a deload."
            )

            prompt = " ".join(prompt_parts)

        else:

            prompt = (
                "I haven't logged any workouts or weight yet. "
                "Give me a short, encouraging explanation of what "
                "I should start logging and why it'll help you "
                "coach me better."
            )

        with st.spinner(
            "📊 Analyzing your progress..."
        ):

            send_to_coach(prompt)

        open_page("AI Coach")


# ============================================================
# ROUTER
# ============================================================

if st.session_state.page == "Dashboard":

    dashboard_page()

elif st.session_state.page == "AI Coach":

    ai_coach_page()

elif st.session_state.page == "Workout":

    workout_page()

elif st.session_state.page == "Nutrition":

    nutrition_page()

elif st.session_state.page == "Progress":

    progress_page()