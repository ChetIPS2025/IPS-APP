"""Settings — company profile and preferences."""

from __future__ import annotations

try:
    from app.pages._import_render import load_render
except ImportError:
    from pages._import_render import load_render  # type: ignore

render = load_render("settings")

__all__ = ["render"]
