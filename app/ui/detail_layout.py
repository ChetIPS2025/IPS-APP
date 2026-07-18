"""Shared IPS detail page layout components."""

from __future__ import annotations

import html
from collections.abc import Callable

import streamlit as st

from app.components.record_modal import render_modal_header, render_modal_meta_grid
from app.components.tabs import render_tabs
from app.ui.status_badge import render_status_badge, status_badge_html
_ActionFn = Callable[[], None]


def render_detail_header(
    title: str,
    *,
    subtitle: str | None = None,
    status: str | None = None,
    metadata: list[tuple[str, str]] | None = None,
    actions: list[_ActionFn] | None = None,
) -> None:
    """Compact detail page header with optional status and metadata grid."""
    with st.container(key="ips_detail_header"):
        st.markdown(
            '<span class="ips-detail-header ips-detail-header-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        title_row_left, title_row_right = st.columns([4, 1], gap="small", vertical_alignment="center")
        with title_row_left:
            st.markdown(
                f'<h2 class="ips-detail-header-title">{html.escape(str(title))}</h2>'
                + (
                    f'<p class="ips-detail-header-subtitle">{html.escape(str(subtitle))}</p>'
                    if subtitle
                    else ""
                ),
                unsafe_allow_html=True,
            )
        with title_row_right:
            if status:
                render_status_badge(status)

        if metadata:
            meta_html = "".join(
                f'<div class="ips-detail-meta-item">'
                f'<div class="ips-detail-meta-label">{html.escape(str(label))}</div>'
                f'<div class="ips-detail-meta-value">{html.escape(str(value))}</div>'
                f"</div>"
                for label, value in metadata
            )
            st.markdown(
                f'<div class="ips-detail-meta-grid">{meta_html}</div>',
                unsafe_allow_html=True,
            )

        if actions:
            action_cols = st.columns(len(actions), gap="small")
            for col, action in zip(action_cols, actions):
                with col:
                    action()


def render_detail_tabs(
    tabs: list[str],
    *,
    selected_tab: str | None = None,
    session_key: str,
) -> str:
    """Consistent horizontal tab bar for detail pages."""
    return render_tabs(tabs, session_key=session_key, default=selected_tab)


def render_detail_modal_header(
    title: str,
    *,
    subtitle: str | None = None,
    status: str | None = None,
) -> None:
    """Detail header inside a modal — delegates to record modal shell."""
    render_modal_header(title=title, subtitle=subtitle or "", status=status or "")


def render_detail_metadata_grid(items: list[tuple[str, str]]) -> None:
    """Metadata grid for detail modals."""
    render_modal_meta_grid(items)


__all__ = [
    "render_detail_header",
    "render_detail_tabs",
    "render_detail_modal_header",
    "render_detail_metadata_grid",
    "status_badge_html",
]
