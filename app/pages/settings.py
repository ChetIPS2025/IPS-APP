"""Settings page — same admin module with settings context."""

from __future__ import annotations

from app.pages.admin import render_settings_page


def render() -> None:
    render_settings_page()
