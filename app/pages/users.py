"""Users / employees — same module as ``employees`` (unified people management)."""

from __future__ import annotations

try:
    from app.pages.employees import render
except ImportError:
    from pages.employees import render  # type: ignore

__all__ = ["render"]
