"""Inventory — stock, transactions, detail panel."""

from __future__ import annotations

try:
    from app.pages._import_render import load_render
except ImportError:
    from pages._import_render import load_render  # type: ignore

render = load_render("inventory")

__all__ = ["render"]
