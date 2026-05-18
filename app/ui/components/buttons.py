"""Button helpers and toast notifications."""

from __future__ import annotations

import streamlit as st

try:
    from app.ui.page_shell import render_action_bar
except ImportError:
    from ui.page_shell import render_action_bar  # type: ignore

__all__ = ["render_action_bar", "toast_success", "toast_error", "toast_warning", "toast_info"]


def toast_success(message: str, *, icon: str = "✓") -> None:
    st.toast(str(message), icon=icon)


def toast_error(message: str, *, icon: str = "✕") -> None:
    st.toast(str(message), icon=icon)


def toast_warning(message: str, *, icon: str = "⚠") -> None:
    st.toast(str(message), icon=icon)


def toast_info(message: str, *, icon: str = "ℹ") -> None:
    st.toast(str(message), icon=icon)
