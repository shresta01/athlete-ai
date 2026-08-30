import os
import sys
import time
import socket
import signal
import shutil
import subprocess
import webbrowser
import urllib.request

# ============================================================
# 🏋️ FITNESS GEN-AI — SINGLE COMMAND LAUNCHER
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

processes = []


# ============================================================
# CONFIGURATION
# ============================================================

STREAMLIT_PORT = 8501

BACKEND_PORTS = {
    "Central AI Orchestrator": 8000,
    "Biomechanics Agent": 8001,
    "Nutrition RAG Agent": 8002,
    "Progressive Overload Agent": 8003,
}

OLLAMA_PORT = 11434


# ============================================================
# FIND OLLAMA
# ============================================================

def find_ollama():

    ollama = shutil.which("ollama")

    if ollama:
        return ollama

    possible_paths = [
        os.path.expandvars(
            r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
        ),
        r"C:\Program Files\Ollama\ollama.exe",
    ]

    for path in possible_paths:

        if os.path.exists(path):
            return path

    return None


OLLAMA_EXE = find_ollama()


# ============================================================
# PRINT HELPERS
# ============================================================

def log(message=""):
    print(message, flush=True)


def banner():

    print()
    print("=" * 70)
    print("          🏋️ FITNESS GEN-AI ATHLETE PLATFORM")
    print("=" * 70)
    print()


# ============================================================
# PORT CHECK
# ============================================================

def port_open(port, host="127.0.0.1"):

    try:

        with socket.create_connection(
            (host, port),
            timeout=0.5
        ):

            return True

    except OSError:

        return False


def wait_for_port(
    name,
    port,
    timeout=15
):

    log(f"⏳ Waiting for {name} on port {port}...")

    start = time.time()

    while time.time() - start < timeout:

        if port_open(port):

            log(f"   ✅ {name} is ready")

            return True

        time.sleep(0.25)

    log(
        f"   ⚠️ {name} did not become ready "
        f"within {timeout}s"
    )

    return False


# ============================================================
# START PROCESS
# ============================================================

def start_process(
    name,
    command
):

    log(f"🚀 Starting {name}...")

    try:

        process = subprocess.Popen(
            command,
            cwd=BASE_DIR,
            stdout=None,
            stderr=None,
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt"
                else 0
            )
        )

        processes.append(
            (name, process)
        )

        return process

    except Exception as e:

        log(
            f"❌ Failed to start {name}: {e}"
        )

        return None


# ============================================================
# OLLAMA
# ============================================================

def ollama_running():

    return port_open(
        OLLAMA_PORT
    )


def start_ollama():

    # --------------------------------------------------------
    # Already running?
    # --------------------------------------------------------

    if ollama_running():

        log(
            "🧠 Ollama is already running."
        )

        return None

    # --------------------------------------------------------
    # Find executable
    # --------------------------------------------------------

    if not OLLAMA_EXE:

        log(
            "⚠️ Ollama executable was not found."
        )

        log(
            "   Install Ollama or start it manually."
        )

        return None

    # --------------------------------------------------------
    # Start Ollama
    # --------------------------------------------------------

    log(
        "🧠 Starting Ollama..."
    )

    try:

        process = subprocess.Popen(
            [
                OLLAMA_EXE,
                "serve"
            ],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt"
                else 0
            )
        )

        processes.append(
            ("Ollama", process)
        )

        wait_for_port(
            "Ollama",
            OLLAMA_PORT,
            timeout=15
        )

        return process

    except Exception as e:

        log(
            f"⚠️ Could not start Ollama: {e}"
        )

        return None


# ============================================================
# BACKEND SERVICES
# ============================================================

SERVICES = [

    {
        "name": "Biomechanics Agent",
        "port": 8001,
        "cmd": [
            PYTHON,
            os.path.join(
                BASE_DIR,
                "trainers",
                "biomechanics_trainer.py"
            )
        ]
    },

    {
        "name": "Nutrition RAG Agent",
        "port": 8002,
        "cmd": [
            PYTHON,
            os.path.join(
                BASE_DIR,
                "trainers",
                "nutrition_trainer.py"
            )
        ]
    },

    {
        "name": "Progressive Overload Agent",
        "port": 8003,
        "cmd": [
            PYTHON,
            os.path.join(
                BASE_DIR,
                "trainers",
                "overload_trainer.py"
            )
        ]
    },

    {
        "name": "Central AI Orchestrator",
        "port": 8000,
        "cmd": [
            PYTHON,
            os.path.join(
                BASE_DIR,
                "athlete_orchestrator.py"
            )
        ]
    }
]


def start_backends():

    log()
    log("🤖 Starting AI services...")
    log()

    for service in SERVICES:

        # ----------------------------------------------------
        # If port is already occupied, don't start duplicate
        # ----------------------------------------------------

        if port_open(service["port"]):

            log(
                f"♻️ {service['name']} "
                f"is already running on "
                f"port {service['port']}"
            )

            continue

        start_process(
            service["name"],
            service["cmd"]
        )

    # --------------------------------------------------------
    # Wait for services in parallel-ish startup order
    # --------------------------------------------------------

    log()
    log("🔎 Checking AI services...")
    log()

    for service in SERVICES:

        wait_for_port(
            service["name"],
            service["port"],
            timeout=15
        )


# ============================================================
# STREAMLIT
# ============================================================

def start_ui():

    log()
    log("💻 Starting Athlete AI dashboard...")

    command = [

        PYTHON,

        "-m",
        "streamlit",

        "run",

        os.path.join(
            BASE_DIR,
            "athlete_ui.py"
        ),

        "--server.address",
        "0.0.0.0",

        "--server.port",
        str(STREAMLIT_PORT),

        "--server.headless",
        "true",

        "--browser.gatherUsageStats",
        "false",

        "--server.runOnSave",
        "true",
    ]

    process = start_process(
        "Streamlit UI",
        command
    )

    return process


# ============================================================
# OPEN BROWSER
# ============================================================

def open_dashboard():

    url = (
        f"http://localhost:{STREAMLIT_PORT}"
    )

    log()
    log("🌐 Dashboard:")
    log(f"   {url}")
    log()

    # Give Streamlit a moment to bind
    time.sleep(1)

    try:

        webbrowser.open(
            url
        )

        log(
            "🌐 Dashboard opened in browser."
        )

    except Exception:

        log(
            "⚠️ Could not automatically "
            "open the browser."
        )


# ============================================================
# SYSTEM STATUS
# ============================================================

def print_status():

    log()
    log("=" * 70)
    log("             ✅ FITNESS GEN-AI ONLINE")
    log("=" * 70)
    log()

    log(
        f"🌐 Dashboard       : "
        f"http://localhost:8501"
    )

    log(
        f"🧠 AI Orchestrator : "
        f"http://localhost:8000"
    )

    log(
        f"🦴 Biomechanics    : "
        f"http://localhost:8001"
    )

    log(
        f"🍎 Nutrition RAG   : "
        f"http://localhost:8002"
    )

    log(
        f"📈 Overload Agent  : "
        f"http://localhost:8003"
    )

    log()
    log(
        "⚡ All services are running."
    )

    log(
        "Press CTRL+C to stop everything."
    )

    log()


# ============================================================
# MONITOR PROCESSES
# ============================================================

def monitor():

    while True:

        for name, process in processes:

            if process.poll() is not None:

                log()
                log(
                    f"⚠️ {name} stopped."
                )

                log(
                    f"   Exit code: "
                    f"{process.returncode}"
                )

        time.sleep(2)


# ============================================================
# CLEANUP
# ============================================================

def cleanup():

    print()
    print()
    print(
        "🛑 Shutting down "
        "Fitness Gen-AI system..."
    )

    for name, process in reversed(processes):

        if process.poll() is not None:
            continue

        print(
            f"   Stopping {name}..."
        )

        try:

            if os.name == "nt":

                subprocess.run(
                    [
                        "taskkill",
                        "/F",
                        "/T",
                        "/PID",
                        str(process.pid)
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            else:

                process.terminate()

        except Exception:

            try:
                process.terminate()

            except Exception:
                pass

    print()
    print(
        "✅ All services stopped."
    )
    print()


# ============================================================
# MAIN
# ============================================================

def main():

    banner()

    try:

        # ====================================================
        # 1. OLLAMA
        # ====================================================

        start_ollama()

        # ====================================================
        # 2. AI BACKENDS
        # ====================================================

        start_backends()

        # ====================================================
        # 3. STREAMLIT
        # ====================================================

        start_ui()

        # ====================================================
        # 4. STATUS
        # ====================================================

        print_status()

        # ====================================================
        # 5. OPEN DASHBOARD
        # ====================================================

        open_dashboard()

        # ====================================================
        # 6. KEEP LAUNCHER ALIVE
        # ====================================================

        monitor()

    except KeyboardInterrupt:

        log()
        log(
            "🛑 Shutdown requested."
        )

    except Exception as e:

        log()
        log(
            f"❌ Launcher error: {e}"
        )

    finally:

        cleanup()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()