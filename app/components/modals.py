"""Modal/dialog wrappers — detail panels render inline below list tables."""

from __future__ import annotations

import html
from collections.abc import Callable

import streamlit as st

try:
    from app.components.buttons import render_detail_actions
    from app.components.layout import render_selected_detail_panel
    from app.components.tabs import render_tabs
except ImportError:
    from components.buttons import render_detail_actions  # type: ignore
    from components.layout import render_selected_detail_panel  # type: ignore
    from components.tabs import render_tabs  # type: ignore


def confirm_dialog(title: str, message: str, on_confirm: Callable[[], None], *, key: str) -> None:
    _ = title
    if st.session_state.get(key):
        st.warning(message)
        c1, c2 = st.columns(2)
        if c1.button("Confirm", key=f"{key}_yes", type="primary"):
            on_confirm()
            st.session_state[key] = False
            st.rerun()
        if c2.button("Cancel", key=f"{key}_no"):
            st.session_state[key] = False
            st.rerun()


def render_record_detail_dialog(
    title: str,
    *,
    module_name: str,
    session_select_key: str,
    body_fn: Callable[[], None],
    tabs_fn: Callable[[], None] | None = None,
    tab_labels: list[str] | None = None,
    tab_session_key: str | None = None,
    show_actions: bool = True,
    header_fn: Callable[[], None] | None = None,
) -> None:
    """
    Inline detail panel below the selected table row (not a modal dialog).

    Call when ``session_select_key`` is set after list render.
    """
    if not str(st.session_state.get(session_select_key) or "").strip():
        return

    _ = module_name

    def _actions() -> None:
        if show_actions:
            render_detail_actions(session_select_key)

    def _tabs_wrapper() -> None:
        if tabs_fn:
            tabs_fn()
        elif tab_labels and tab_session_key:
            render_tabs(tab_labels, session_key=tab_session_key)

    render_selected_detail_panel(
        title,
        session_select_key=session_select_key,
        actions=_actions if show_actions and not header_fn else None,
        show_default_actions=show_actions and not header_fn,
        header_fn=header_fn,
        tabs_fn=_tabs_wrapper if (tabs_fn or tab_labels) else None,
        body_fn=body_fn,
    )


def render_modal_header_actions(
    session_select_key: str,
    *,
    key_prefix: str | None = None,
    show_edit: bool = True,
) -> None:
    """Compact header actions for legacy modal callers."""
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
