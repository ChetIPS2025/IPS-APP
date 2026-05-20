"""Action button helpers."""

from __future__ import annotations

import streamlit as st


def render_action_buttons(
    actions: list[tuple[str, str, str]],
    *,
    key_prefix: str,
) -> None:
    """Render compact action buttons: (label, key_suffix, kind). kind: primary|secondary."""
    if not actions:
        return
    cols = st.columns(len(actions))
    for col, (label, suffix, kind) in zip(cols, actions):
        with col:
            btn_type = "primary" if kind == "primary" else "secondary"
            if st.button(label, key=f"{key_prefix}_{suffix}", type=btn_type, use_container_width=True):
                st.session_state[f"{key_prefix}_action"] = suffix


def render_detail_actions(
    session_select_key: str,
    *,
    key_prefix: str | None = None,
    show_edit: bool = True,
    show_details: bool = True,
) -> None:
    """
    Standard detail panel actions: Edit, Details, More, Collapse.

    Collapse clears ``session_select_key`` and closes the detail panel.
    """
    prefix = key_prefix or f"ips_detail_{session_select_key}"
    actions: list[tuple[str, str, str]] = []
    if show_edit:
        actions.append(("Edit", "edit", "secondary"))
    if show_details:
        actions.append(("Details", "details", "secondary"))
    actions.extend([("More", "more", "secondary"), ("Collapse", "collapse", "secondary")])
    render_action_buttons(actions, key_prefix=prefix)
    if st.session_state.get(f"{prefix}_action") == "collapse":
        st.session_state.pop(session_select_key, None)
        st.session_state.pop(f"{prefix}_action", None)
        st.rerun()


def render_modal_header_actions(
    session_select_key: str,
    *,
    key_prefix: str | None = None,
    show_edit: bool = True,
) -> None:
    """Compact modal actions: View, Edit, More, Close."""
    prefix = key_prefix or f"ips_modal_{session_select_key}"
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.button("View", key=f"{prefix}_view", use_container_width=True)
    with c2:
        if show_edit:
            st.button("Edit", key=f"{prefix}_edit", use_container_width=True)
    with c3:
        st.button("More", key=f"{prefix}_more", use_container_width=True)
    with c4:
        if st.button("Close", key=f"{prefix}_close", use_container_width=True):
            st.session_state.pop(session_select_key, None)
            st.rerun()
