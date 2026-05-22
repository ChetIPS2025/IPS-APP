"""Settings page — delegates to admin module with settings context."""

from __future__ import annotations

try:
    from app.pages.modules import admin
except ImportError:
    from pages.modules import admin  # type: ignore


def render() -> None:
    admin.render()
