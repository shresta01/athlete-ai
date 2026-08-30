import os
import sys
import time
import socket
import shutil
import subprocess
import webbrowser
from pathlib import Path


# ============================================================
# FITNESS GEN-AI — ONE COMMAND LAUNCHER
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable

# ============================================================
# CONFIGURATION
# ============================================================

UI_PORT = 8501

SERVICES = [
    {
        "name": "Central AI Orchestrator",
        "script": "athlete_orchestrator.py",
        "port": 8000,
    },
    {
        "name": "Biomechanics Agent",
        "script": "trainers/biomechanics_trainer.py",
        "port": 8001,
    },
    {
        "name": "Nutrition RAG Agent",
        "script": "trainers/nutrition_trainer.py",
        "port": 8002,
    },
    {
        "name": "Progressive Overload Agent",
        "script": "trainers/overload_trainer.py",
        "port": 8003,
    },
]

processes = []


# ============================================================
# COLORS
# ============================================================

class C:
    RESET = "\033[0m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BLUE = "\033[94m"


def log(message, color=C.WHITE):
    print(f"{color}{message}{C.RESET}")


# ============================================================
# PORT CHECK
# ============================================================

def port_open(host, port):
    """Check whether a TCP port is accepting connections."""

    try:
        with socket.create_connection(
            (host, port),
            timeout=0.5
        ):
            return True

    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


def wait_for_port(
    port,
    name,
    timeout=30
):
    """
    Wait only until the service is actually ready.
    No unnecessary fixed sleeps.
    """

    start = time.time()

    while time.time() - start < timeout:

        if port_open("127.0.0.1", port):

            elapsed = time.time() - start

            log(
                f"   ✓ {name} ready "
                f"({elapsed:.1f}s)",
                C.GREEN
            )

            return True

        time.sleep(0.25)

    log(
        f"   ✗ {name} did not start on port {port}",
        C.RED
    )

    return False


# ============================================================
# FIND OLLAMA
# ============================================================

def find_ollama():

    # First try PATH
    ollama = shutil.which("ollama")

    if ollama:
        return ollama

    # Windows common locations
    username = os.environ.get("USERNAME", "")

    possible_paths = [

        Path(
            f"C:/Users/{username}/AppData/Local/Programs/Ollama/ollama.exe"
        ),

        Path(
            "C:/Program Files/Ollama/ollama.exe"
        ),

    ]

    for path in possible_paths:

        if path.exists():
            return str(path)

    return None


# ============================================================
# OLLAMA
# ============================================================

def start_ollama():

    log("\n🧠 Checking Ollama...", C.CYAN)

    # Ollama already running?
    if port_open("127.0.0.1", 11434):

        log(
            "   ✓ Ollama already running",
            C.GREEN
        )

        return

    ollama = find_ollama()

    if not ollama:

        log(
            "   ⚠ Ollama executable not found.",
            C.YELLOW
        )

        return

    try:

        log(
            "   🚀 Starting Ollama...",
            C.CYAN
        )

        process = subprocess.Popen(
            [ollama, "serve"],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            ),
        )

        processes.append(
            ("Ollama", process)
        )

        if wait_for_port(
            11434,
            "Ollama",
            timeout=20
        ):
            return

    except Exception as e:

        log(
            f"   ⚠ Could not start Ollama: {e}",
            C.YELLOW
        )


# ============================================================
# START PYTHON SERVICE
# ============================================================

def start_service(service):

    name = service["name"]
    script = BASE_DIR / service["script"]
    port = service["port"]

    log(
        f"\n🚀 Starting {name}...",
        C.CYAN
    )

    # --------------------------------------------------------
    # Check script
    # --------------------------------------------------------

    if not script.exists():

        log(
            f"   ✗ File not found: {script}",
            C.RED
        )

        return False

    # --------------------------------------------------------
    # Don't start if already running
    # --------------------------------------------------------

    if port_open(
        "127.0.0.1",
        port
    ):

        log(
            f"   ✓ {name} already running on {port}",
            C.GREEN
        )

        return True

    # --------------------------------------------------------
    # Start process
    # --------------------------------------------------------

    try:

        process = subprocess.Popen(
            [
                PYTHON,
                str(script)
            ],
            cwd=BASE_DIR,
        )

        processes.append(
            (name, process)
        )

    except Exception as e:

        log(
            f"   ✗ Failed to start {name}: {e}",
            C.RED
        )

        return False

    # --------------------------------------------------------
    # Wait for REAL readiness
    # --------------------------------------------------------

    return wait_for_port(
        port,
        name,
        timeout=30
    )


# ============================================================
# START STREAMLIT
# ============================================================

def start_ui():

    log(
        "\n💻 Starting Athlete AI dashboard...",
        C.CYAN
    )

    # Already running?
    if port_open(
        "127.0.0.1",
        UI_PORT
    ):

        log(
            f"   ✓ Dashboard already running on {UI_PORT}",
            C.GREEN
        )

        return True

    command = [
        PYTHON,
        "-m",
        "streamlit",
        "run",
        str(
            BASE_DIR / "athlete_ui.py"
        ),
        "--server.address",
        "0.0.0.0",
        "--server.port",
        str(UI_PORT),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    try:

        process = subprocess.Popen(
            command,
            cwd=BASE_DIR,
        )

        processes.append(
            ("Streamlit UI", process)
        )

    except Exception as e:

        log(
            f"   ✗ Failed to start Streamlit: {e}",
            C.RED
        )

        return False

    return wait_for_port(
        UI_PORT,
        "Athlete AI Dashboard",
        timeout=30
    )


# ============================================================
# OPEN BROWSER
# ============================================================

def open_dashboard():

    url = f"http://localhost:{UI_PORT}"

    log(
        f"\n🌐 Opening {url}",
        C.GREEN
    )

    time.sleep(0.5)

    try:
        webbrowser.open(url)

    except Exception:
        pass


# ============================================================
# SYSTEM STATUS
# ============================================================

def show_status():

    print()
    print("=" * 70)

    log(
        "        🏋️ FITNESS GEN-AI ATHLETE PLATFORM",
        C.CYAN
    )

    print("=" * 70)

    print()

    services_status = [

        (
            "🧠 Ollama",
            11434
        ),

        (
            "🤖 Central AI Orchestrator",
            8000
        ),

        (
            "🦴 Biomechanics Agent",
            8001
        ),

        (
            "🍎 Nutrition RAG Agent",
            8002
        ),

        (
            "📈 Progressive Overload Agent",
            8003
        ),

        (
            "💻 Athlete AI Dashboard",
            8501
        ),

    ]

    for name, port in services_status:

        if port_open(
            "127.0.0.1",
            port
        ):

            log(
                f"   ✓ {name:<35} : {port}",
                C.GREEN
            )

        else:

            log(
                f"   ✗ {name:<35} : {port}",
                C.RED
            )

    print()

    print("=" * 70)

    log(
        "        🚀 FITNESS GEN-AI SYSTEM ONLINE",
        C.GREEN
    )

    print("=" * 70)

    print()

    log(
        "🌐 Dashboard:",
        C.CYAN
    )

    print(
        "   http://localhost:8501"
    )

    print()

    log(
        "🧠 AI Backend:",
        C.CYAN
    )

    print(
        "   http://localhost:8000"
    )

    print()

    log(
        "Press CTRL+C to stop everything.",
        C.YELLOW
    )

    print()


# ============================================================
# CLEANUP
# ============================================================

def cleanup():

    print()

    log(
        "🛑 Shutting down Fitness Gen-AI...",
        C.YELLOW
    )

    for name, process in reversed(processes):

        try:

            if process.poll() is None:

                log(
                    f"   Stopping {name}...",
                    C.YELLOW
                )

                if os.name == "nt":

                    subprocess.run(
                        [
                            "taskkill",
                            "/F",
                            "/T",
                            "/PID",
                            str(process.pid),
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

                else:

                    process.terminate()

        except Exception:
            pass

    print()

    log(
        "✓ All launcher-managed services stopped.",
        C.GREEN
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    log(
        "🏋️ FITNESS GEN-AI",
        C.CYAN
    )

    log(
        "Starting complete AI athlete platform...",
        C.WHITE
    )

    print()

    try:

        # ----------------------------------------------------
        # 1. Ollama
        # ----------------------------------------------------

        start_ollama()

        # ----------------------------------------------------
        # 2. AI backend services
        # ----------------------------------------------------

        successful = 0

        for service in SERVICES:

            if start_service(service):

                successful += 1

        # ----------------------------------------------------
        # 3. Streamlit
        # ----------------------------------------------------

        ui_started = start_ui()

        # ----------------------------------------------------
        # 4. Final status
        # ----------------------------------------------------

        show_status()

        # ----------------------------------------------------
        # 5. Open browser
        # ----------------------------------------------------

        if ui_started:

            open_dashboard()

        # ----------------------------------------------------
        # 6. Keep launcher alive
        # ----------------------------------------------------

        while True:

            time.sleep(2)

            # Detect crashed processes

            for name, process in processes:

                if process.poll() is not None:

                    log(
                        f"⚠ {name} stopped "
                        f"(exit code {process.returncode})",
                        C.RED
                    )

    except KeyboardInterrupt:

        log(
            "\n\n🛑 Shutdown requested.",
            C.YELLOW
        )

    finally:

        cleanup()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()