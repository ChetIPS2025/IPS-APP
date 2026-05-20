"""Documents hub — cross-module file registry."""

from __future__ import annotations

try:
    from app.pages._import_render import load_render
except ImportError:
    from pages._import_render import load_render  # type: ignore

render = load_render("documents")

__all__ = ["render"]
