"""Stable session keys across reruns and navigation."""

from __future__ import annotations

import streamlit as st

try:
    from app.utils.constants import SESSION_DETAIL_TAB_PREFIX, SESSION_NAV_KEY, SESSION_SELECTED_PREFIX
except ImportError:
    from utils.constants import SESSION_DETAIL_TAB_PREFIX, SESSION_NAV_KEY, SESSION_SELECTED_PREFIX  # type: ignore


def nav_slug() -> str:
    return str(st.session_state.get(SESSION_NAV_KEY) or "dashboard")


def select_key(module: str) -> str:
    return f"{SESSION_SELECTED_PREFIX}{module}"


def tab_key(module: str) -> str:
    return f"{SESSION_DETAIL_TAB_PREFIX}{module}"


def clear_module_state(module: str) -> None:
    st.session_state.pop(select_key(module), None)
    st.session_state.pop(tab_key(module), None)


def clear_all_module_selections() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith(SESSION_SELECTED_PREFIX) or key.startswith(SESSION_DETAIL_TAB_PREFIX):
            st.session_state.pop(key, None)
