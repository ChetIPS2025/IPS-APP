"""Action button helpers."""

from __future__ import annotations

import streamlit as st


def render_action_buttons(
    actions: list[tuple[str, str, str]],
    *,
    key_prefix: str,
) -> None:
    """Render compact action buttons: (label, key_suffix, kind). kind: primary|secondary."""
    cols = st.columns(len(actions))
    for col, (label, suffix, kind) in zip(cols, actions):
        with col:
            btn_type = "primary" if kind == "primary" else "secondary"
            if st.button(label, key=f"{key_prefix}_{suffix}", type=btn_type, use_container_width=True):
                st.session_state[f"{key_prefix}_action"] = suffix
