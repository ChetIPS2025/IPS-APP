#!/usr/bin/env python3
"""
IPS desktop shell: run the Streamlit app locally and show it in a PyWebView window.

Development: activate the project venv, then ``python desktop_launcher.py``.
Packaged: build with PyInstaller (see ``IPS_App.spec`` / ``docs/desktop_build.md``).
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

DEFAULT_PORT = 8501
HOST = "127.0.0.1"
STARTUP_TIMEOUT_SEC = 120.0
POLL_INTERVAL_SEC = 0.35


def _repo_root() -> Path:
    """Project root (contains ``app/``, ``assets/``, ``static/``)."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        internal = exe_dir / "_internal"
        for base in (internal, exe_dir):
            if (base / "app" / "main.py").is_file():
                return base
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass and (Path(meipass) / "app" / "main.py").is_file():
            return Path(meipass)
        return exe_dir
    return Path(__file__).resolve().parent


def _main_py(root: Path) -> Path:
    return root / "app" / "main.py"


def _pick_port(preferred: int = DEFAULT_PORT) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((HOST, port))
                return port
            except OSError:
                continue
    return preferred


def _http_ok(url: str) -> bool:
    base = url.rstrip("/")
    for path in ("/_stcore/health", "/"):
        try:
            with urlopen(f"{base}{path}", timeout=2) as resp:
                if 200 <= int(resp.status) < 500:
                    return True
        except (URLError, HTTPError, OSError, TimeoutError, ValueError):
            continue
    return False


def _wait_for_streamlit(url: str, timeout: float = STARTUP_TIMEOUT_SEC) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _http_ok(url):
            return True
        time.sleep(POLL_INTERVAL_SEC)
    return False


def _streamlit_python() -> str:
    """Interpreter to run ``python -m streamlit`` (override when frozen if needed)."""
    override = (os.environ.get("IPS_STREAMLIT_PYTHON") or "").strip()
    if override:
        return override
    return sys.executable


def _streamlit_cmd(repo_root: Path, main_py: Path, port: int) -> list[str]:
    return [
        _streamlit_python(),
        "-m",
        "streamlit",
        "run",
        str(main_py),
        f"--server.port={port}",
        f"--server.address={HOST}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]


def _creationflags() -> int:
    if sys.platform != "win32":
        return 0
    # Hide extra console for Streamlit child when packaged (optional in dev)
    if os.environ.get("IPS_LAUNCHER_STREAMLIT_CONSOLE", "").lower() in ("1", "true", "yes"):
        return 0
    if getattr(sys, "frozen", False):
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _drain_streamlit_output(proc: subprocess.Popen, log: Callable[[str], None]) -> None:
    if proc.stdout is None:
        return
    try:
        while True:
            line = proc.stdout.readline()
            if line == "" and proc.poll() is not None:
                break
            if line:
                log(line.rstrip())
    except Exception:
        pass


def _show_fatal(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("IPS App", message)
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)


def _terminate_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main() -> int:
    repo_root = _repo_root()
    main_py = _main_py(repo_root)
    if not main_py.is_file():
        _show_fatal(f"Cannot find Streamlit entry:\n{main_py}\n\n(Reinstall or rebuild the desktop bundle.)")
        return 1

    port = _pick_port(DEFAULT_PORT)
    url = f"http://{HOST}:{port}"
    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = str(port)
    env.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    cmd = _streamlit_cmd(repo_root, main_py, port)
    creationflags = _creationflags()
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(repo_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )
    except OSError as exc:
        _show_fatal(f"Could not start Streamlit:\n{exc}\n\nCommand: {' '.join(cmd)}")
        return 1

    log_lines: list[str] = []

    def _log(line: str) -> None:
        log_lines.append(line)
        if os.environ.get("IPS_LAUNCHER_DEBUG", "").lower() in ("1", "true", "yes"):
            print(line, file=sys.stderr)

    threading.Thread(target=_drain_streamlit_output, args=(proc, _log), daemon=True).start()

    if not _wait_for_streamlit(url):
        _terminate_process(proc)
        tail = "\n".join(log_lines[-40:]) if log_lines else "(no output captured)"
        hint = ""
        if getattr(sys, "frozen", False):
            hint = (
                "\n\nIf the packaged EXE cannot start Streamlit, set environment variable\n"
                "IPS_STREAMLIT_PYTHON to a full path of a Python executable that has\n"
                "streamlit installed (same version as the app), then relaunch."
            )
        _show_fatal(
            f"Streamlit did not become ready at {url} within {int(STARTUP_TIMEOUT_SEC)}s.\n\n"
            f"Last log lines:\n{tail}{hint}"
        )
        return 1

    try:
        import webview
    except ImportError:
        _terminate_process(proc)
        _show_fatal(
            "PyWebView is not installed.\n\n"
            "Install with: pip install pywebview\n"
            "Then run: python desktop_launcher.py"
        )
        return 1

    base_kw: dict = {
        "title": "IPS App",
        "url": url,
        "width": 1440,
        "height": 900,
        "resizable": True,
    }
    window = None
    for extra in (
        {"confirm_close": True, "background_color": "#031633"},
        {"confirm_close": True},
        {},
    ):
        try:
            window = webview.create_window(**base_kw, **extra)
            break
        except TypeError:
            continue
    if window is None:
        window = webview.create_window(**base_kw)

    def _on_closed() -> None:
        _terminate_process(proc)

    try:
        ev = getattr(window, "events", None)
        if ev is not None and hasattr(ev, "closed"):
            ev.closed += _on_closed
    except Exception:
        pass

    try:
        if sys.platform == "win32":
            try:
                webview.start(gui="edgechromium", debug=False)
            except Exception:
                webview.start(debug=False)
        else:
            webview.start(debug=False)
    except TypeError:
        webview.start(debug=False)
    finally:
        _terminate_process(proc)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
