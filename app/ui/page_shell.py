"""
IPS dashboard page shell — shared headers, sections, action bars, cards, tables, and global layout CSS.

Inject once from ``main`` via :func:`inject_ips_dashboard_layout`.
"""

from __future__ import annotations

import html
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import pandas as pd
import streamlit as st

IPS_DASHBOARD_LAYOUT_KEY = "ips_dashboard_layout_injected_v7"

# Re-export column hiding standard (catalog / inventory / materials tables).
try:
    from app.ui.catalog_inventory_display import (
        HIDDEN_SYSTEM_COLUMNS,
        drop_hidden_system_columns,
        prepare_catalog_inventory_display_df,
    )
except ImportError:
    from ui.catalog_inventory_display import (  # type: ignore
        HIDDEN_SYSTEM_COLUMNS,
        drop_hidden_system_columns,
        prepare_catalog_inventory_display_df,
    )


def inject_ips_dashboard_layout() -> None:
    """Global compact industrial dashboard chrome."""
    if st.session_state.get(IPS_DASHBOARD_LAYOUT_KEY):
        return
    st.session_state[IPS_DASHBOARD_LAYOUT_KEY] = True
    try:
        from app.ui.streamlit_perf import inject_scroll_preserve
    except ImportError:
        from ui.streamlit_perf import inject_scroll_preserve  # type: ignore
    inject_scroll_preserve("ips_app")
    try:
        from app.ui.compact_forms import inject_compact_form_styles
    except ImportError:
        from ui.compact_forms import inject_compact_form_styles  # type: ignore
    inject_compact_form_styles()
    st.markdown(
        """
        <style>
        /* App canvas background: see theme.apply_global_app_styles() */
        section[data-testid="stMain"]:has(.ips-page-shell-marker) .block-container {
            padding-top: 0.08rem !important;
            padding-bottom: 0.7rem !important;
            max-width: 1680px !important;
        }
        section[data-testid="stMain"]:has(.ips-page-shell-marker) [data-testid="stElementContainer"] {
            margin-bottom: 0.1rem !important;
        }

        /* ----- Typography ----- */
        p.ips-section-title, .ips-jdb-section-title {
            color: #111827 !important;
            font-size: 0.98rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em;
            margin: 0 0 0.25rem 0 !important;
            padding: 0 !important;
            line-height: 1.25 !important;
        }
        p.ips-section-desc, p.ips-crud-page-subtitle, .ips-jdb-section-desc {
            color: #4b5563 !important;
            font-size: 0.8125rem !important;
            font-weight: 500 !important;
            margin: 0 0 0.38rem 0 !important;
            padding: 0 !important;
            line-height: 1.4 !important;
            max-width: 960px;
        }
        p.ips-section-desc-only { margin-top: -0.12rem !important; }
        p.ips-muted, .ips-jdb-muted {
            color: #6b7280 !important;
            font-size: 0.78rem !important;
            font-weight: 500 !important;
            margin: 0.2rem 0 0 0 !important;
        }

        /* ----- Surfaces: subtle cards (modern flat) ----- */
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #ffffff !important;
            border: 1px solid #E5EAF2 !important;
            border-radius: 14px !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 0.42rem 0.55rem 0.48rem !important;
        }
        /* Flat sections: no boxed chrome (quick actions, toolbars, filter strips) */
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-flat-section),
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-action-bar-anchor) {
            background: #ffffff !important;
            border: none !important;
            box-shadow: none !important;
            border-radius: 0 !important;
            margin-bottom: 0.28rem !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-flat-section) > div,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-action-bar-anchor) > div {
            padding: 0 0 0.18rem 0 !important;
        }
        /* List / filter panels: light separation, not heavy boxes */
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor):not(:has(.ips-surface-card)) {
            background: #ffffff !important;
            border: none !important;
            border-bottom: 1px solid #E5EAF2 !important;
            box-shadow: none !important;
            border-radius: 0 !important;
            margin-bottom: 0.32rem !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor):not(:has(.ips-surface-card)) > div {
            padding: 0.12rem 0 0.38rem 0 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-surface-card),
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-content-card-anchor) {
            padding: 0.38rem 0.5rem 0.44rem !important;
            margin-bottom: 0.32rem !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-toolbar-root) {
            background: #ffffff !important;
            border: 1px solid #E5EAF2 !important;
            box-shadow: none !important;
            border-radius: 14px !important;
            padding: 0.32rem 0.45rem 0.38rem !important;
            margin-bottom: 0.3rem !important;
        }
        /* Soft surface marker (no Streamlit border wrapper) */
        section[data-testid="stMain"] .ips-surface-soft {
            display: block;
            margin: 0 0 0.32rem 0;
            padding: 0 0 0.28rem 0;
            border-bottom: 1px solid rgba(15, 23, 42, 0.06);
        }
        p.ips-action-bar-title {
            color: #111827 !important;
            font-size: 0.88rem !important;
            font-weight: 700 !important;
            margin: 0 0 0.32rem 0 !important;
        }

        /* ----- KPI metrics ----- */
        section[data-testid="stMain"] div[data-testid="metric-container"],
        section[data-testid="stMain"] div[data-testid="stMetric"] {
            background: #ffffff !important;
            border: 1px solid #E5EAF2 !important;
            border-radius: 14px !important;
            padding: 0.34rem 0.46rem !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        }
        section[data-testid="stMain"] div[data-testid="stMetric"] label {
            font-size: 0.76rem !important;
            font-weight: 600 !important;
            color: #4b5563 !important;
        }
        section[data-testid="stMain"] div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 1.32rem !important;
            font-weight: 700 !important;
            color: #111827 !important;
        }

        /* ----- Buttons: compact, blue primary, no wrap ----- */
        section[data-testid="stMain"] .stButton > button,
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button,
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button {
            white-space: nowrap !important;
            border-radius: 10px !important;
            min-height: 2.35rem !important;
            padding: 0.38rem 0.72rem !important;
            font-size: 0.875rem !important;
            font-weight: 600 !important;
        }
        section[data-testid="stMain"] .stButton > button p,
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button p {
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
            margin: 0 !important;
        }
        section[data-testid="stMain"] .stButton > button[kind="primary"],
        section[data-testid="stMain"] .stButton > button[data-testid="baseButton-primary"],
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: #2563eb !important;
            border: 1px solid #2563eb !important;
            color: #ffffff !important;
            box-shadow: none !important;
        }
        section[data-testid="stMain"] .stButton > button[kind="primary"]:hover,
        section[data-testid="stMain"] .stButton > button[data-testid="baseButton-primary"]:hover {
            background: #1d4ed8 !important;
            border-color: #1d4ed8 !important;
        }
        section[data-testid="stMain"] .stButton > button[kind="secondary"],
        section[data-testid="stMain"] .stButton > button[data-testid="baseButton-secondary"] {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            color: #111827 !important;
        }

        /* ----- Filters ----- */
        section[data-testid="stMain"] div[data-testid="stHorizontalBlock"]:has([data-testid="stSelectbox"]) {
            gap: 0.4rem !important;
            align-items: flex-end !important;
        }
        section[data-testid="stMain"] [data-testid="stWidgetLabel"] p {
            font-size: 0.76rem !important;
            margin-bottom: 0.06rem !important;
        }

        /* ----- Tables / dataframes ----- */
        section[data-testid="stMain"] [data-testid="stDataFrame"],
        section[data-testid="stMain"] [data-testid="stDataEditor"] {
            border: 1px solid rgba(15, 23, 42, 0.08) !important;
            border-radius: 8px !important;
            background: #ffffff !important;
            box-shadow: none !important;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] thead tr th {
            position: sticky !important;
            top: 0 !important;
            z-index: 2 !important;
            background: #ffffff !important;
            color: #111827 !important;
            font-size: 0.76rem !important;
            font-weight: 700 !important;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] tbody tr:hover td {
            background: #F8FAFC !important;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] td {
            font-size: 0.8125rem !important;
            padding: 6px 8px !important;
            max-width: 280px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        section[data-testid="stMain"] [data-testid="stCaptionContainer"] p {
            font-size: 0.76rem !important;
            color: #6b7280 !important;
        }
        section[data-testid="stMain"] [data-testid="stExpander"] details {
            border: 1px solid rgba(15, 23, 42, 0.08) !important;
            border-radius: 8px !important;
            background: #ffffff !important;
            box-shadow: none !important;
        }
        section[data-testid="stMain"] [data-testid="stExpander"] summary {
            padding: 0.32rem 0.5rem !important;
            font-size: 0.875rem !important;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def compact_button_css() -> None:
    """Ensure button nowrap rules are active (calls layout inject)."""
    inject_ips_dashboard_layout()


def hide_internal_columns(
    df: pd.DataFrame,
    *,
    extra_hidden: frozenset[str] | None = None,
    keep: frozenset[str] | None = None,
) -> pd.DataFrame:
    """Drop system/internal columns from a table DataFrame."""
    return drop_hidden_system_columns(df, extra_hidden=extra_hidden, keep=keep)


def prepare_display_table(
    data: pd.DataFrame | list[dict[str, Any]] | None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Viewer-safe dataframe (hide internal cols, friendly headers)."""
    return prepare_catalog_inventory_display_df(data, **kwargs)


def render_page_header(
    title: str,
    subtitle: str,
    *,
    help_text: str | None = None,
    logo_width: int = 180,
) -> None:
    """Small logo + title + one-line subtitle."""
    inject_ips_dashboard_layout()
    st.markdown('<span class="ips-page-shell-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
    try:
        from app.branding import render_header
    except ImportError:
        from branding import render_header  # type: ignore
    render_header(title, subtitle=subtitle, help_text=help_text, logo_width=logo_width)


def render_section_header(title: str, description: str | None = None) -> None:
    inject_ips_dashboard_layout()
    t = str(title or "").strip()
    if t:
        st.markdown(f'<p class="ips-section-title">{html.escape(t)}</p>', unsafe_allow_html=True)
    d = str(description or "").strip()
    if d:
        st.markdown(f'<p class="ips-section-desc">{html.escape(d)}</p>', unsafe_allow_html=True)


def render_section_desc_only(text: str) -> None:
    inject_ips_dashboard_layout()
    t = str(text or "").strip()
    if t:
        st.markdown(
            f'<p class="ips-section-desc ips-section-desc-only">{html.escape(t)}</p>',
            unsafe_allow_html=True,
        )


@contextmanager
def render_card(*, title: str | None = None, bordered: bool = False) -> Iterator[None]:
    """Content section; default is flat (subtle divider), optional bordered card."""
    inject_ips_dashboard_layout()
    if bordered:
        with st.container(border=True):
            st.markdown('<span class="ips-content-card-anchor ips-surface-card"></span>', unsafe_allow_html=True)
            if title:
                render_section_header(title)
            yield
    else:
        st.markdown('<span class="ips-content-card-anchor ips-surface-soft"></span>', unsafe_allow_html=True)
        if title:
            render_section_header(title)
        yield


@contextmanager
def action_bar_card(*, title: str | None = "Quick Actions") -> Iterator[None]:
    """Compact horizontal action row — flat, no heavy bordered box."""
    inject_ips_dashboard_layout()
    st.markdown(
        '<span class="ips-action-bar-anchor ips-flat-section"></span>',
        unsafe_allow_html=True,
    )
    if title:
        st.markdown(
            f'<p class="ips-action-bar-title">{html.escape(str(title))}</p>',
            unsafe_allow_html=True,
        )
    yield


def render_action_bar(
    specs: list[dict[str, Any]],
    *,
    title: str | None = "Quick Actions",
    columns: int | None = None,
) -> None:
    """
    Render a row of action buttons inside :func:`action_bar_card`.

    Each spec: ``label``, ``key``, optional ``type`` (primary|secondary), ``disabled``, ``help``.
    Returns nothing — inspect ``st.session_state`` or use button return values in caller if needed.

    For side effects, use explicit ``if st.button`` in the page after calling with empty specs
  or pass buttons via context manager instead.
    """
    n = columns or max(1, len(specs))
    with action_bar_card(title=title):
        cols = st.columns(n, gap="small")
        for i, spec in enumerate(specs):
            with cols[i % n]:
                st.button(
                    str(spec.get("label", "Action")),
                    key=str(spec["key"]),
                    type=str(spec.get("type", "secondary")),
                    disabled=bool(spec.get("disabled", False)),
                    help=spec.get("help"),
                    use_container_width=True,
                )


def render_filter_row(
    specs: list[dict[str, Any]],
    *,
    gap: str = "small",
    clear_key: str | None = None,
    on_clear: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Horizontal filters; optional Clear button as last column."""
    inject_ips_dashboard_layout()
    try:
        from app.ui.compact_forms import field_marker
    except ImportError:
        from ui.compact_forms import field_marker  # type: ignore
    if clear_key:
        weights = [float(s.get("width", 1)) for s in specs] + [0.45]
        cols = st.columns(weights, gap=gap)
        spec_cols = cols[:-1]
        clear_col = cols[-1]
    else:
        weights = [float(s.get("width", 1)) for s in specs]
        cols = st.columns(weights, gap=gap)
        spec_cols = cols
        clear_col = None

    out: dict[str, Any] = {}
    for col, spec in zip(spec_cols, specs):
        key = str(spec["key"])
        label = str(spec.get("label", ""))
        wtype = str(spec.get("widget", "selectbox"))
        fkind = str(spec.get("field", "search" if wtype == "text_input" else "medium"))
        with col:
            field_marker(fkind)
            if wtype == "text_input":
                st.text_input(label, key=key, placeholder=str(spec.get("placeholder", "")))
                out[key] = st.session_state.get(key, "")
            else:
                st.selectbox(label, list(spec.get("options", [])), key=key)
                out[key] = st.session_state.get(key)
    if clear_col is not None and clear_key:
        with clear_col:
            st.markdown(
                '<div aria-hidden="true" style="display:block;height:1.55rem"></div>',
                unsafe_allow_html=True,
            )
            if st.button("Clear", key=clear_key, use_container_width=False):
                if on_clear:
                    on_clear()
    return out


def render_table(
    df: pd.DataFrame,
    *,
    height: int | None = None,
    hide_internal: bool = True,
    column_config: dict[str, Any] | None = None,
    **dataframe_kwargs: Any,
) -> None:
    """Display a professional dataframe with optional internal column stripping."""
    inject_ips_dashboard_layout()
    st.markdown('<span class="ips-table-surface" aria-hidden="true"></span>', unsafe_allow_html=True)
    disp = hide_internal_columns(df) if hide_internal else df
    kwargs: dict[str, Any] = {"use_container_width": True, "hide_index": True}
    kwargs.update(dataframe_kwargs)
    if height is not None:
        kwargs["height"] = height
    if column_config:
        kwargs["column_config"] = column_config
    st.dataframe(disp, **kwargs)


def ensure_modal_styles() -> None:
    """Delegate to IPS modal styling (dialogs)."""
    try:
        from app.ui.modal import ensure_modal_styles as _ems
    except ImportError:
        from ui.modal import ensure_modal_styles as _ems  # type: ignore
    _ems()


# Backward-compatible alias
render_modal = ensure_modal_styles


def apply_global_css() -> None:
    """Design-system entry: theme tokens, layout, tables, density."""
    try:
        from app.ui.theme import apply_global_css as _apply
    except ImportError:
        from ui.theme import apply_global_css as _apply  # type: ignore
    _apply()


def render_filters(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Alias for :func:`render_filter_row`."""
    return render_filter_row(*args, **kwargs)
