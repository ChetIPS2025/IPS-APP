"""Professional empty states."""

from __future__ import annotations

import html

import streamlit as st


def render_empty_state(
    title: str,
    message: str,
    *,
    icon: str = "📋",
    action_label: str | None = None,
    action_key: str | None = None,
) -> bool:
    """Render empty state with optional action button. Returns True if action clicked."""
    st.markdown(
        (
            '<div class="ips-empty-state">'
            f'<div class="ips-empty-icon">{html.escape(icon)}</div>'
            f'<p class="ips-empty-title">{html.escape(title)}</p>'
            f'<p class="ips-empty-msg">{html.escape(message)}</p>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if action_label and action_key:
        c1, _, _ = st.columns([1, 2, 2])
        with c1:
            return bool(st.button(action_label, key=action_key, type="primary", use_container_width=True))
    return False
