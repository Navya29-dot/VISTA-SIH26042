from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DOWNLOADS_DIR = Path.home() / "Downloads"

BACKEND_DIR = Path(os.getenv("VISTA_BACKEND_DIR", PROJECT_ROOT))
MAIN_UI_DIR = Path(
    os.getenv("VISTA_MAIN_UI_DIR", PROJECT_ROOT / "frontend")
)

API_PORT = os.getenv("VISTA_API_PORT", "8000")
MAIN_UI_PORT = os.getenv("VISTA_MAIN_UI_PORT", "5173")


def main() -> int:
    _print_banner()
    _check_folder(BACKEND_DIR, "backend")
    _check_folder(MAIN_UI_DIR, "main UI")

    print("[setup] Seeding local SQLite curriculum data...")
    _run_with_retry([sys.executable, "-m", "backend.seed_database"], BACKEND_DIR)

    processes = [
       _start(
    "api",
    [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        API_PORT
    ],
    BACKEND_DIR
)
    ]

    print("\nVISTA is starting. Open these URLs:")
    print(f"  API:        http://127.0.0.1:{API_PORT}")
    print(f"  Main UI:    http://127.0.0.1:{MAIN_UI_PORT}")
    print("\nPress Ctrl+C here to stop everything.\n")

    try:
        while all(process.poll() is None for process in processes):
            signal.pause() if hasattr(signal, "pause") else threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\n[stop] Closing VISTA services...")
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()

    return 0


def _print_banner() -> None:
    print("VISTA - Vernacular Intelligence for Smart Teaching & Adaptation")
    print("Starting backend and the judge-facing frontend from one file.\n")


def _check_folder(path: Path, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Missing {label} folder: {path}")


def _run_once(command: list[str], cwd: Path, required: bool) -> None:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if completed.returncode != 0:
        if not required:
            print("[setup] Optional setup command did not finish. Continuing with your configured database.")
            return
        print("[setup] Database setup could not finish.")
        details = (completed.stderr or completed.stdout).strip()
        if details:
            print(details)
        print("[setup] Check DATABASE_URL or POSTGRES_* values in the backend .env file.")
        print("[setup] Example: postgresql+psycopg://postgres:vista@localhost:5432/Vista")
        raise SystemExit(1)


def _run_with_retry(command: list[str], cwd: Path, attempts: int = 10) -> None:
    for attempt in range(attempts):
        completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        if completed.returncode == 0:
            return
        if attempt < attempts - 1:
            time.sleep(1)
            continue

        print("[setup] Database setup could not finish.")
        details = (completed.stderr or completed.stdout).strip()
        if details:
            print(details)
        print("[setup] Check DATABASE_URL or POSTGRES_* values in the backend .env file.")
        print("[setup] Example: postgresql+psycopg://postgres:vista@localhost:5433/Vista")
        raise SystemExit(1)


def _start(label: str, command: list[str], cwd: Path) -> subprocess.Popen:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    threading.Thread(target=_pipe_output, args=(label, process), daemon=True).start()
    return process


def _pipe_output(label: str, process: subprocess.Popen) -> None:
    if not process.stdout:
        return

    for line in process.stdout:
        print(f"[{label}] {line}", end="")


if __name__ == "__main__":
    raise SystemExit(main())
