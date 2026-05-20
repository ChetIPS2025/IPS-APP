"""
Hosting launcher for the unified IPS Streamlit app.

Runs the same entry point as local dev: ``streamlit run app/main.py``.
Used by Render (see render.yaml). Not a separate application.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def main() -> None:
    root = _project_root()
    os.chdir(root)

    main_py = root / "app" / "main.py"
    if not main_py.is_file():
        print(f"Missing entry script: {main_py}", file=sys.stderr)
        sys.exit(1)

    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from app.streamlit_pwa_static_patch import install

    install()

    from streamlit.web import cli as stcli

    port = os.environ.get("PORT", "10000")
    print(f"Starting Streamlit on port: {port}")

    sys.argv = [
        "streamlit",
        "run",
        str(main_py),
        "--global.developmentMode=false",
        "--server.address=0.0.0.0",
        f"--server.port={port}",
    ]
    stcli.main()


if __name__ == "__main__":
    main()