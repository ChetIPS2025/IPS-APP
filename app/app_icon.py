"""Official IPS app icon paths (favicon, Streamlit page icon, PWA)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BRANDING_DIR = ROOT_DIR / "assets" / "branding"
APP_STATIC_DIR = ROOT_DIR / "app" / "static"
STREAMLIT_STATIC_DIR = ROOT_DIR / ".streamlit" / "static"
DESKTOP_STATIC_DIR = ROOT_DIR / "static"

_SOURCE_CANDIDATES = (
    BRANDING_DIR / "ips_app_icon_source.png",
    BRANDING_DIR / "ips_app_icon_source.jpg",
    BRANDING_DIR / "ips_app_icon_source.jpeg",
    ROOT_DIR / "assets" / "IPS Icon.png",
)


def app_icon_source_path() -> Path | None:
    """Branding source image used to regenerate favicon/PWA assets."""
    for path in _SOURCE_CANDIDATES:
        if path.is_file():
            return path
    return None


def app_static_dir() -> Path:
    return APP_STATIC_DIR


@lru_cache(maxsize=1)
def page_icon_path() -> str | None:
    """Path for Streamlit ``page_icon`` (prefer small PNG favicon)."""
    for name in ("favicon.png", "icon-192.png", "icon-512.png"):
        path = APP_STATIC_DIR / name
        if path.is_file():
            return str(path)
    source = app_icon_source_path()
    return str(source) if source else None


def static_icon_url(filename: str) -> str:
    """URL path segment for icons served from ``app/static``."""
    return f"/app/static/{filename}"
