"""
Local/dev launcher: install PWA static-route patch, then start Streamlit.

Use this instead of bare ``streamlit run`` so ``/app/static/sw.js`` and
``manifest.json`` are served with correct MIME types (not SPA index.html).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from app.streamlit_pwa_static_patch import install

    install()

    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    from streamlit.web import cli as stcli

    port = os.environ.get("STREAMLIT_SERVER_PORT", "8501")
    sys.argv = [
        "streamlit",
        "run",
        str(root / "app" / "main.py"),
        "--server.headless=true",
        f"--server.port={port}",
    ]
    stcli.main()


if __name__ == "__main__":
    main()
