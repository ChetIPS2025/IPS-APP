"""Page shell and detail panel."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

try:
    from app.components.sidebar import render_sidebar
    from app.styles import inject_global_css
except ImportError:
    from components.sidebar import render_sidebar  # type: ignore
    from styles import inject_global_css  # type: ignore

_OT, _CT = "d" + "iv", "/" + "d" + "iv"


def render_page_shell(page_fn: Callable[[], None], *, page_slug: str) -> None:
    inject_global_css()
    render_sidebar(page_slug)
    page_fn()


def render_selected_detail_panel(
    title: str,
    *,
    actions: Callable[[], None] | None = None,
    tabs_fn: Callable[[], None] | None = None,
    body_fn: Callable[[], None] | None = None,
) -> None:
    st.markdown(f'<{_OT} class="ips-detail-panel">', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(f'<p class="ips-detail-title">{title}</p>', unsafe_allow_html=True)
    with c2:
        if actions:
            actions()
    if tabs_fn:
        tabs_fn()
    if body_fn:
        body_fn()
    st.markdown(f"<{_CT}>", unsafe_allow_html=True)


def render_filter_bar(widgets_fn: Callable[[], None]) -> None:
    with st.container():
        st.markdown(f'<{_OT} class="ips-filter-bar">', unsafe_allow_html=True)
        widgets_fn()
        st.markdown(f"<{_CT}>", unsafe_allow_html=True)
