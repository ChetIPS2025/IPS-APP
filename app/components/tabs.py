"""Tab navigation for detail panels."""

from __future__ import annotations

import streamlit as st

_TABS_WRAP_KEY_PREFIX = "ips_tabs_wrap_"


def tabs_wrap_key(session_key: str) -> str:
    """Streamlit container key used to scope tab-bar CSS in dialogs."""
    return f"{_TABS_WRAP_KEY_PREFIX}{session_key}"


def render_tabs(
    tab_labels: list[str],
    *,
    session_key: str,
    default: str | None = None,
) -> str:
    if session_key not in st.session_state:
        st.session_state[session_key] = default or tab_labels[0]
    with st.container(key=tabs_wrap_key(session_key)):
        choice = st.radio(
            "Section",
            tab_labels,
            horizontal=True,
            key=session_key,
            label_visibility="collapsed",
        )
    return str(choice)
