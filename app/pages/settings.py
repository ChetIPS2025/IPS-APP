"""Settings page — same admin module with settings context."""

from __future__ import annotations

try:
    from app.pages.admin import render
except ImportError:
    from pages.admin import render  # type: ignore
