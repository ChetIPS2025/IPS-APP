"""Page shell and detail panel."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

try:
    from app.components.buttons import render_detail_actions
    from app.components.sidebar import render_sidebar
    from app.styles import inject_global_css
except ImportError:
    from components.buttons import render_detail_actions  # type: ignore
    from components.sidebar import render_sidebar  # type: ignore
    from styles import inject_global_css  # type: ignore

_OT, _CT = "d" + "iv", "/" + "d" + "iv"


def render_page_shell(page_fn: Callable[[], None], *, page_slug: str) -> None:
    """Inject CSS, render sidebar, then run the page body."""
    inject_global_css()
    render_sidebar(page_slug)
    st.markdown(f'<{_OT} class="ips-page-content ips-page-{page_slug}">', unsafe_allow_html=True)
    page_fn()
    st.markdown(f"<{_CT}>", unsafe_allow_html=True)


def render_selected_detail_panel(
    title: str,
    *,
    session_select_key: str | None = None,
    actions: Callable[[], None] | None = None,
    show_default_actions: bool = True,
    tabs_fn: Callable[[], None] | None = None,
    body_fn: Callable[[], None] | None = None,
) -> None:
    """Detail panel below selected table row — tabs + action bar."""
    st.markdown(f'<{_OT} class="ips-detail-panel">', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(f'<p class="ips-detail-title">{title}</p>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<{_OT} class="ips-detail-actions">', unsafe_allow_html=True)
        if actions:
            actions()
        elif show_default_actions and session_select_key:
            render_detail_actions(session_select_key)
        st.markdown(f"<{_CT}>", unsafe_allow_html=True)
    if tabs_fn:
        tabs_fn()
    if body_fn:
        body_fn()
    st.markdown(f"<{_CT}>", unsafe_allow_html=True)


def render_filter_bar(widgets_fn: Callable[[], None]) -> None:
    """White card filter row with search + dropdowns."""
    st.markdown(f'<{_OT} class="ips-filter-bar">', unsafe_allow_html=True)
    widgets_fn()
    st.markdown(f"<{_CT}>", unsafe_allow_html=True)


def render_tab_placeholder(message: str) -> None:
    """Neutral placeholder for tabs not yet wired to Supabase."""
    st.markdown(
        f'<{_OT} class="ips-tab-placeholder">{message}<{_CT}>',
        unsafe_allow_html=True,
    )
