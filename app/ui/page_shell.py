"""
IPS dashboard page shell — shared headers, sections, action bars, and global layout CSS.

Inject once from ``main`` via :func:`inject_ips_dashboard_layout`.
Pages should use :func:`render_page_header` instead of long captions + default company subtitle.
"""

from __future__ import annotations

import html
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import streamlit as st

IPS_DASHBOARD_LAYOUT_KEY = "ips_dashboard_layout_injected_v1"


def inject_ips_dashboard_layout() -> None:
    """Global compact dashboard chrome (cards, tables, headers, action bars)."""
    if st.session_state.get(IPS_DASHBOARD_LAYOUT_KEY):
        return
    st.session_state[IPS_DASHBOARD_LAYOUT_KEY] = True
    st.markdown(
        """
        <style>
        /* ----- Page shell marker ----- */
        section[data-testid="stMain"]:has(.ips-page-shell-marker) .block-container {
            padding-top: 0.12rem !important;
        }
        section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stElementContainer"] {
            margin-bottom: 0.16rem !important;
        }

        /* ----- Section typography ----- */
        p.ips-section-title,
        .ips-jdb-section-title {
            color: #111827 !important;
            font-size: 0.98rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em;
            margin: 0 0 0.28rem 0 !important;
            padding: 0 !important;
            line-height: 1.25 !important;
        }
        p.ips-section-desc,
        p.ips-crud-page-subtitle,
        .ips-jdb-section-desc {
            color: #4b5563 !important;
            font-size: 0.8125rem !important;
            font-weight: 500 !important;
            margin: 0 0 0.42rem 0 !important;
            padding: 0 !important;
            line-height: 1.4 !important;
            max-width: 960px;
        }
        p.ips-section-desc-only {
            margin-top: -0.15rem !important;
        }
        p.ips-muted,
        .ips-jdb-muted {
            color: #6b7280 !important;
            font-size: 0.78rem !important;
            font-weight: 500 !important;
            margin: 0.2rem 0 0 0 !important;
            line-height: 1.35 !important;
        }

        /* ----- Compact cards (bordered containers) ----- */
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #d1d5db !important;
            border-radius: 12px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor),
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-action-bar-anchor),
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-toolbar-root) {
            padding: 0.5rem 0.65rem 0.55rem !important;
            margin-bottom: 0.45rem !important;
        }

        p.ips-action-bar-title {
            color: #111827 !important;
            font-size: 0.88rem !important;
            font-weight: 700 !important;
            margin: 0 0 0.35rem 0 !important;
        }

        /* ----- KPI / metric blocks ----- */
        section[data-testid="stMain"] div[data-testid="stMetric"] {
            background: #ffffff !important;
            border: 1px solid #e5e7eb !important;
            border-radius: 10px !important;
            padding: 0.45rem 0.55rem !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
        }
        section[data-testid="stMain"] div[data-testid="stMetric"] label {
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            color: #4b5563 !important;
        }
        section[data-testid="stMain"] div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 1.35rem !important;
            font-weight: 700 !important;
            color: #111827 !important;
        }

        /* ----- Compact action buttons in toolbars ----- */
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor) .stButton > button,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-action-bar-anchor) .stButton > button,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-toolbar-root) .stButton > button,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ta-bar-anchor) .stButton > button {
            min-height: 2.35rem !important;
            padding: 0.4rem 0.75rem !important;
            font-size: 0.875rem !important;
            border-radius: 10px !important;
            white-space: nowrap !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor) .stButton > button p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-action-bar-anchor) .stButton > button p {
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
        }

        /* ----- Filters: tighter horizontal rows ----- */
        section[data-testid="stMain"] div[data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"]) {
            gap: 0.45rem !important;
            align-items: flex-end !important;
        }
        section[data-testid="stMain"] [data-testid="stWidgetLabel"] p {
            font-size: 0.78rem !important;
            margin-bottom: 0.08rem !important;
        }

        /* ----- Dataframes / tables ----- */
        section[data-testid="stMain"] [data-testid="stDataFrame"],
        section[data-testid="stMain"] [data-testid="stDataEditor"] {
            border: 1px solid #e5e7eb !important;
            border-radius: 10px !important;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] thead tr th {
            position: sticky !important;
            top: 0 !important;
            z-index: 2 !important;
            background: #f8fafc !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            padding-top: 8px !important;
            padding-bottom: 8px !important;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] tbody tr:hover td {
            background: #f1f5f9 !important;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] td {
            font-size: 0.8125rem !important;
            padding-top: 7px !important;
            padding-bottom: 7px !important;
        }

        /* ----- Reduce default caption noise ----- */
        section[data-testid="stMain"] [data-testid="stCaptionContainer"] p {
            font-size: 0.78rem !important;
            color: #6b7280 !important;
        }

        /* ----- Expanders: compact ----- */
        section[data-testid="stMain"] [data-testid="stExpander"] details {
            border-radius: 10px !important;
        }
        section[data-testid="stMain"] [data-testid="stExpander"] summary {
            padding: 0.45rem 0.65rem !important;
            font-size: 0.875rem !important;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(
    title: str,
    subtitle: str,
    *,
    help_text: str | None = None,
    logo_width: int = 180,
) -> None:
    """Standard page header: small logo, title, one-line subtitle (no long help blocks)."""
    inject_ips_dashboard_layout()
    st.markdown('<span class="ips-page-shell-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
    try:
        from app.branding import render_header
    except ImportError:
        from branding import render_header  # type: ignore
    render_header(title, subtitle=subtitle, help_text=help_text, logo_width=logo_width)


def render_section_header(title: str, description: str | None = None) -> None:
    """Bold section title + optional one-line description."""
    inject_ips_dashboard_layout()
    t = str(title or "").strip()
    if t:
        st.markdown(f'<p class="ips-section-title">{html.escape(t)}</p>', unsafe_allow_html=True)
    d = str(description or "").strip()
    if d:
        st.markdown(f'<p class="ips-section-desc">{html.escape(d)}</p>', unsafe_allow_html=True)


def render_section_desc_only(text: str) -> None:
    """Muted one-line section description (legacy ``render_crud_list_subtitle``)."""
    inject_ips_dashboard_layout()
    t = str(text or "").strip()
    if not t:
        return
    st.markdown(
        f'<p class="ips-section-desc ips-section-desc-only">{html.escape(t)}</p>',
        unsafe_allow_html=True,
    )


@contextmanager
def action_bar_card(*, title: str | None = "Quick Actions") -> Iterator[None]:
    """Compact bordered card for horizontal action buttons."""
    inject_ips_dashboard_layout()
    with st.container(border=True):
        st.markdown(
            '<span class="ips-list-top-anchor ips-action-bar-anchor"></span>',
            unsafe_allow_html=True,
        )
        if title:
            st.markdown(
                f'<p class="ips-action-bar-title">{html.escape(str(title))}</p>',
                unsafe_allow_html=True,
            )
        yield


def render_filter_row(specs: list[dict[str, Any]], *, gap: str = "small") -> dict[str, Any]:
    """
    Render a horizontal filter row. Each spec: ``label``, ``widget`` (``selectbox``|``text_input``),
    ``options`` (for select), ``key``, optional ``width`` weight.

    Returns dict of current values read from session state keys.
    """
    inject_ips_dashboard_layout()
    weights = [float(s.get("width", 1)) for s in specs]
    cols = st.columns(weights, gap=gap)
    out: dict[str, Any] = {}
    for col, spec in zip(cols, specs):
        key = str(spec["key"])
        label = str(spec.get("label", ""))
        wtype = str(spec.get("widget", "selectbox"))
        with col:
            if wtype == "text_input":
                st.text_input(label, key=key, placeholder=str(spec.get("placeholder", "")))
                out[key] = st.session_state.get(key, "")
            else:
                st.selectbox(label, list(spec.get("options", [])), key=key)
                out[key] = st.session_state.get(key)
    return out
