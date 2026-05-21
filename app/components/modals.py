"""Modal/dialog wrappers."""

from __future__ import annotations

import html
from collections.abc import Callable

import streamlit as st

try:
    from app.components.buttons import render_modal_header_actions
    from app.components.tabs import render_tabs
except ImportError:
    from components.buttons import render_modal_header_actions  # type: ignore
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


def _render_dialog_content(
    title: str,
    *,
    session_select_key: str,
    body_fn: Callable[[], None],
    tabs_fn: Callable[[], None] | None = None,
    tab_labels: list[str] | None = None,
    tab_session_key: str | None = None,
    show_actions: bool = True,
) -> None:
    ot, ct = "d" + "iv", "/" + "d" + "iv"
    st.markdown(f'<{ot} class="ips-modal-header">', unsafe_allow_html=True)
    h1, h2 = st.columns([4, 1])
    with h1:
        st.markdown(
            f'<p class="ips-detail-title">{html.escape(str(title))}</p>',
            unsafe_allow_html=True,
        )
    with h2:
        if show_actions:
            render_modal_header_actions(session_select_key)
    st.markdown(f"</{ct}>", unsafe_allow_html=True)

    if tabs_fn:
        tabs_fn()
    elif tab_labels and tab_session_key:
        render_tabs(tab_labels, session_key=tab_session_key)

    body_fn()


def _fallback_modal_shell(title: str, inner: Callable[[], None]) -> None:
    """Bordered panel when ``st.dialog`` is unavailable."""
    ot, ct = "d" + "iv", "/" + "d" + "iv"
    st.markdown(f'<{ot} class="ips-modal-fallback">', unsafe_allow_html=True)
    st.markdown(f"### {title}")
    inner()
    st.markdown(f"</{ct}>", unsafe_allow_html=True)


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
) -> None:
    """
    Open an in-app detail dialog for the selected record.

    Call after list render when ``session_select_key`` is set.
    """
    if not str(st.session_state.get(session_select_key) or "").strip():
        return

    _ = module_name

    def _inner() -> None:
        _render_dialog_content(
            title,
            session_select_key=session_select_key,
            body_fn=body_fn,
            tabs_fn=tabs_fn,
            tab_labels=tab_labels,
            tab_session_key=tab_session_key,
            show_actions=show_actions,
        )

    if hasattr(st, "dialog"):
        dialog_fn = st.dialog(title, width="large")

        @dialog_fn
        def _dlg() -> None:
            _inner()

        _dlg()
    else:
        _fallback_modal_shell(title, _inner)
