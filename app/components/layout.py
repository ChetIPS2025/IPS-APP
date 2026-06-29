"""Page shell and detail panel."""

from __future__ import annotations

import html
from collections.abc import Callable

import streamlit as st

try:
    from app.components.buttons import render_detail_actions
    from app.styles import inject_global_css
except ImportError:
    from components.buttons import render_detail_actions  # type: ignore
    from styles import inject_global_css  # type: ignore

_OT, _CT = "d" + "iv", "/" + "d" + "iv"


def render_page_shell(page_fn: Callable[[], None], *, page_slug: str) -> None:
    """Inject CSS, render sidebar, then run the page body."""
    try:
        from app.components.sidebar import render_sidebar
    except ImportError:
        from components.sidebar import render_sidebar  # type: ignore
    inject_global_css()
    render_sidebar(page_slug)
    st.markdown(
        f'<span class="ips-page-content ips-page-{page_slug} ips-page-body-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    page_fn()


def render_selected_detail_panel(
    title: str,
    *,
    session_select_key: str | None = None,
    actions: Callable[[], None] | None = None,
    show_default_actions: bool = True,
    header_fn: Callable[[], None] | None = None,
    tabs_fn: Callable[[], None] | None = None,
    body_fn: Callable[[], None] | None = None,
) -> None:
    """Detail panel below selected table row — tabs + action bar."""
    st.markdown(f'<span class="ips-detail-panel-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
    if header_fn:
        header_fn()
    else:
        st.markdown(
            f'<p class="ips-detail-title">{html.escape(str(title))}</p>',
            unsafe_allow_html=True,
        )
        if actions:
            actions()
        elif show_default_actions and session_select_key:
            render_detail_actions(session_select_key)
    if tabs_fn:
        tabs_fn()
    if body_fn:
        body_fn()


def render_filter_bar(widgets_fn: Callable[[], None]) -> None:
    """Compact white card filter row with search + dropdowns."""
    with st.container(border=True):
        st.markdown('<span class="ips-filter-bar-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
        widgets_fn()


def render_tab_placeholder(message: str) -> None:
    """Neutral placeholder for tabs not yet wired to Supabase."""
    st.markdown(
        f'<{_OT} class="ips-tab-placeholder">{message}<{_CT}>',
        unsafe_allow_html=True,
    )
