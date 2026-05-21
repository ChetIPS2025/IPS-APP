#!/usr/bin/env python3
"""Write app/static/manifest.json from app.pwa.build_web_manifest (dev fallback only)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "static" / "manifest.json"


def main() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from app.pwa import manifest_json_bytes
    except ImportError as exc:
        print(f"sync_pwa_manifest: import failed: {exc}", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(manifest_json_bytes(indent=2))
    print(f"Wrote {OUT} (runtime still uses build_web_manifest(); file is optional fallback).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
