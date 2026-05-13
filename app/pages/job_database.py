from __future__ import annotations

import contextlib
import html
import logging
from typing import Any

_LOG = logging.getLogger(__name__)

import pandas as pd
import streamlit as st

from auth import current_role
from branding import render_header
from db import (
    fetch_by_match,
    fetch_by_match_admin,
    fetch_jobs_with_order_fallback,
    fetch_one,
    fetch_table,
    fetch_table_admin,
    insert_row,
    insert_row_admin,
    update_rows_admin,
)

try:
    from table_actions import (
        IPS_PENDING_DELETE,
        TABLE_KEY_JOBS,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        set_selected_ids,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_JOBS,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        set_selected_ids,
    )

try:
    from app.ips_crud_list_styles import (
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )
except ImportError:
    from ips_crud_list_styles import (  # type: ignore
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )

try:
    from app.ui.field_light_theme import inject_field_light_theme
except ImportError:
    from ui.field_light_theme import inject_field_light_theme  # type: ignore

try:
    from app.mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected
except ImportError:
    from mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected  # type: ignore

try:
    from services.customer_contacts import (
        contact_none_option_label,
        contact_option_label,
        inject_contact_picker_styles,
        render_contact_detail_preview,
        render_contact_quick_add_when_empty,
    )
except ImportError:
    from app.services.customer_contacts import (  # type: ignore
        contact_none_option_label,
        contact_option_label,
        inject_contact_picker_styles,
        render_contact_detail_preview,
        render_contact_quick_add_when_empty,
    )

try:
    from services.job_from_estimate import create_job_from_estimate
    from services.job_schema import (
        JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER,
        fetch_jobs_for_job_database,
    )
    from services.job_service import (
        job_number_display,
        job_row_select_label,
        next_job_number,
        sort_jobs_by_name,
        sort_jobs_by_number_then_name,
    )
except ImportError:
    from app.services.job_from_estimate import create_job_from_estimate  # type: ignore
    from app.services.job_schema import (  # type: ignore
        JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER,
        fetch_jobs_for_job_database,
    )
    from app.services.job_service import (  # type: ignore
        job_number_display,
        job_row_select_label,
        next_job_number,
        sort_jobs_by_name,
        sort_jobs_by_number_then_name,
    )

from app.utils.formatters import job_display_label

try:
    from services.delete_safety import delete_job_row_if_no_costing
except ImportError:
    from app.services.delete_safety import delete_job_row_if_no_costing  # type: ignore

try:
    from app.db import create_signed_url
    from app.services.job_weekly_timesheets import generate_unsigned_timesheet_for_job_week
except ImportError:
    from db import create_signed_url  # type: ignore
    from services.job_weekly_timesheets import generate_unsigned_timesheet_for_job_week  # type: ignore


def _job_db_cell_str(val: Any) -> str:
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    s = str(val).strip()
    if s.lower() == "nan":
        return ""
    return s


def _render_job_db_job_name_cell(container: Any, raw: Any, *, max_len: int = 40) -> None:
    """Single-line job name with ellipsis; full value in native tooltip (max_len reserved)."""
    _ = max_len
    full = _job_db_cell_str(raw)
    if not full:
        container.markdown(
            '<span class="ips-job-list-cell" style="color:#111827;">—</span>',
            unsafe_allow_html=True,
        )
        return
    container.markdown(
        f'<span class="ips-job-list-cell" title="{html.escape(full, quote=True)}" '
        f'style="color:#111827;">{html.escape(full)}</span>',
        unsafe_allow_html=True,
    )


def _render_short_cell_with_tooltip(container: Any, value: Any, max_len: int = 20) -> None:
    """Single-line text with ellipsis; full value in native tooltip (max_len kept for call sites)."""
    _ = max_len
    txt = str(value or "").strip()
    if not txt:
        container.markdown(
            '<span class="ips-job-list-cell" style="color:#111827;">—</span>',
            unsafe_allow_html=True,
        )
        return
    container.markdown(
        f'<span class="ips-job-list-cell" title="{html.escape(txt, quote=True)}" '
        f'style="color:#111827;">{html.escape(txt)}</span>',
        unsafe_allow_html=True,
    )


def _job_db_money_cell(v: Any) -> str:
    try:
        if v is None or str(v).strip() == "":
            return ""
        fv = float(v)
        if fv == 0:
            return ""
        return f"${fv:,.0f}"
    except Exception:
        return ""


def _job_db_card_text(v: Any, fallback: str = "—") -> str:
    s = _job_db_cell_str(v)
    return s if s else fallback


_JOB_STATUS_COLORS: dict[str, str] = {
    "complete": "#16a34a",
    "completed": "#16a34a",
    "closed": "#16a34a",
    "in progress": "#f59e0b",
    "scheduled": "#f59e0b",
    "awarded": "#f59e0b",
    "blocked": "#dc2626",
    "on hold": "#dc2626",
    "not started": "#64748b",
    "draft": "#64748b",
    "electrical": "#7c3aed",
    "electrical / other trade": "#7c3aed",
    "duplicate": "#64748b",
    "waiting on customer": "#0891b2",
}


def _job_status_badge_html(status: Any) -> str:
    label = _job_db_card_text(status)
    color = _JOB_STATUS_COLORS.get(label.strip().lower(), "#64748b")
    return (
        '<span class="ips-status-badge" '
        f'style="--ips-status-color:{html.escape(color)};">{html.escape(label)}</span>'
    )


JOB_STATUSES = [
    "Draft",
    "Quoted",
    "Submitted",
    "Approved",
    "Awarded",
    "Scheduled",
    "In Progress",
    "On Hold",
    "Completed",
    "Closed",
]

HIDDEN_COLUMNS: frozenset[str] = frozenset(
    {
        "source_type",
        "project_manager",
        "supervisor",
        "start_date",
        "target_completion_date",
        "completed_date",
        "notes",
    }
)

JOB_DB_RESPONSIVE_STYLES_KEY = "job_db_responsive_styles_injected_v12"
JOB_DB_DETAIL_VIEW_CSS_KEY = "job_db_detail_view_css_v1"

# Shown in the Job Database grid; kept on the DataFrame for filters / search / logic.
_JOB_DB_COLUMNS_HIDDEN_FROM_TABLE: frozenset[str] = frozenset(
    {"customer_id", "estimate_label", "Source"}
) | HIDDEN_COLUMNS


def _job_db_visible_table_columns(columns: list[str]) -> list[str]:
    return [c for c in columns if c not in _JOB_DB_COLUMNS_HIDDEN_FROM_TABLE]


def _inject_job_database_responsive_styles() -> None:
    """Jobs page tablet/mobile layout overrides. Keeps desktop split/table unchanged."""
    if st.session_state.get(JOB_DB_RESPONSIVE_STYLES_KEY):
        return
    st.session_state[JOB_DB_RESPONSIVE_STYLES_KEY] = True
    st.markdown(
        """
        <style>
        .ips-job-card-title {
            color: #111827 !important;
            font-size: 1rem;
            font-weight: 700;
            line-height: 1.25;
            margin: 0 0 0.1rem 0;
            overflow-wrap: anywhere;
        }
        .ips-job-card-meta {
            color: #4b5563 !important;
            font-size: 0.88rem;
            line-height: 1.45;
            margin: 0.15rem 0 0.4rem;
            overflow-wrap: anywhere;
        }
        .ips-job-card-pill {
            display: inline-flex;
            align-items: center;
            border: 1px solid #cbd5e1;
            border-radius: 999px;
            color: #334155 !important;
            background: #f8fafc;
            font-size: 0.78rem;
            font-weight: 650;
            line-height: 1;
            margin: 0.2rem 0.25rem 0.1rem 0;
            max-width: 100%;
            padding: 0.35rem 0.55rem;
            overflow-wrap: anywhere;
        }
        .ips-status-badge {
            align-items: center;
            background: color-mix(in srgb, var(--ips-status-color) 12%, white);
            border: 1px solid color-mix(in srgb, var(--ips-status-color) 38%, white);
            border-radius: 999px;
            color: var(--ips-status-color);
            display: inline-flex;
            font-size: 0.78rem;
            font-weight: 700;
            line-height: 1;
            margin: 0.2rem 0.25rem 0.1rem 0;
            padding: 0.35rem 0.55rem;
            white-space: nowrap;
        }
        /*
         * Job overview: Streamlit theme is base=dark (light text tokens). List rows sit on white
         * bordered cards, so themed body text is effectively invisible. Force readable ink.
         */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="column"] .stMarkdown,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="column"] .stMarkdown p,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="column"] .stMarkdown span,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="column"] [data-testid="stText"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="column"] pre {
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="stCaptionContainer"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="stCaptionContainer"] p {
            color: #4b5563 !important;
        }
        /* Job desktop table: flex columns clip instead of overlapping; inner host scrolls horizontally. */
        div[data-testid="stVerticalBlock"]:has(.ips-job-table-scroll-anchor),
        div[data-testid="element-container"]:has(.ips-job-table-scroll-anchor) {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
            max-width: 100%;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            align-items: center !important;
            column-gap: 0.75rem !important;
            width: 100% !important;
            min-width: 1260px !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            min-width: 0 !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) {
            flex: 0 0 auto !important;
            min-width: 44px !important;
            max-width: 56px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
            min-width: 76px !important;
            max-width: 110px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) {
            min-width: 160px !important;
            max-width: 280px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(4) {
            min-width: 140px !important;
            max-width: 220px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(5) {
            min-width: 120px !important;
            max-width: 200px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(6) {
            min-width: 120px !important;
            max-width: 200px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(7) {
            min-width: 100px !important;
            max-width: 150px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(8) {
            min-width: 120px !important;
            max-width: 200px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(9) {
            min-width: 100px !important;
            max-width: 180px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(10) {
            min-width: 88px !important;
            max-width: 120px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(11) {
            flex: 0 0 auto !important;
            min-width: 52px !important;
            max-width: 76px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(12) {
            flex: 0 0 auto !important;
            min-width: 52px !important;
            max-width: 72px !important;
            position: relative !important;
            z-index: 2 !important;
            isolation: isolate !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) .ips-job-list-cell {
            display: block;
            box-sizing: border-box;
            width: 100%;
            max-width: 100%;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) .ips-job-money-cell {
            text-align: right;
            font-variant-numeric: tabular-nums;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"] .stMarkdown {
            min-width: 0 !important;
            overflow: hidden !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] [data-testid="column"] p:has(.ips-job-list-cell) {
            margin: 0 !important;
            min-width: 0 !important;
            overflow: hidden !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stCaptionContainer"] p {
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            min-width: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-list-anchor) h5,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-list-anchor) .stMarkdown,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-list-anchor) .stMarkdown p,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) .stMarkdown,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) .stMarkdown p {
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) {
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 12px !important;
            margin-bottom: 0.65rem !important;
            padding: 0.75rem !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) .stButton > button,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) .stButton > button,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) .stButton > button {
            min-height: 48px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="input"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="base-input"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) textarea,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="input"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="base-input"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stFileUploader"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) textarea {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            color: #111827 !important;
        }
        /* Select chrome is global (ips_app_shell); keep inner wrappers flat here too. */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] > div > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] > div > div {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] span,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] span,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] input {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] *,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] *,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stFileUploader"] * {
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) textarea {
            max-width: 100% !important;
            min-height: 42px !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) {
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 12px !important;
            color: #111827 !important;
            padding: 0.75rem !important;
            margin-top: 0.5rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) h3,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) h4 {
            color: #111827 !important;
        }
        /* Job detail: iPad-style segmented tabs (override global stMain tab chrome) */
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"],
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            align-items: center !important;
            gap: 6px !important;
            padding: 6px !important;
            margin: 0 0 0.75rem 0 !important;
            background: #d1d5db !important;
            border: none !important;
            border-bottom: none !important;
            border-radius: 10px !important;
            box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.05) !important;
            overflow-x: auto !important;
            overflow-y: visible !important;
            scrollbar-width: thin;
            -webkit-overflow-scrolling: touch !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"] {
            flex: 0 1 auto !important;
            min-height: 0 !important;
            height: auto !important;
            min-width: 0 !important;
            margin: 0 !important;
            padding: 8px 14px !important;
            border-radius: 10px !important;
            white-space: nowrap !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            box-shadow: none !important;
            color: #111827 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"] p {
            color: #111827 !important;
            font-weight: 500 !important;
            margin: 0 !important;
            overflow: visible !important;
            text-overflow: clip !important;
            white-space: nowrap !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button[aria-selected="true"],
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button[aria-selected="true"],
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-bottom-color: #cbd5e1 !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04) !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button[aria-selected="true"] p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button[aria-selected="true"] p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"][aria-selected="true"] p {
            color: #111827 !important;
            font-weight: 600 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button:hover:not(:disabled):not([aria-selected="true"]),
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button:hover:not(:disabled):not([aria-selected="true"]),
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) {
            background: rgba(255, 255, 255, 0.42) !important;
        }
        /* Job overview: estimate summary (grey tray + white inner card) */
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) {
            background: #d1d5db !important;
            border: 1px solid #c4c4cc !important;
            border-radius: 12px !important;
            padding: 0.65rem 0.75rem 0.75rem !important;
            margin: 0 0 0.85rem 0 !important;
            box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.04) !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) h4 {
            color: #111827 !important;
            font-weight: 700 !important;
            margin: 0 0 0.5rem 0 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) .stCaption,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) .stCaption p {
            color: #374151 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) .ips-jes-card {
            background: #ffffff !important;
            border-radius: 10px !important;
            padding: 0.65rem 0.85rem !important;
            margin: 0 0 0.5rem 0 !important;
            border: 1px solid #e5e7eb !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) .ips-jes-grid {
            display: grid !important;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)) !important;
            gap: 0.45rem 1rem !important;
            color: #111827 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) .ips-jes-lbl {
            display: block !important;
            font-weight: 700 !important;
            font-size: 0.78rem !important;
            color: #374151 !important;
            margin-bottom: 0.12rem !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) .ips-jes-val {
            display: block !important;
            font-weight: 600 !important;
            font-size: 0.92rem !important;
            color: #111827 !important;
            line-height: 1.35 !important;
            overflow-wrap: anywhere !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="column"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-testid="column"] {
            min-width: 0 !important;
        }
        /* Tablet / iPad: job detail full-width (list layout is chosen via View mode, not duplicate DOM). */
        @media (max-width: 1260px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor)
                div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 0.65rem !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor)
                div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 calc(50% - 0.65rem) !important;
                max-width: calc(50% - 0.35rem) !important;
                min-width: min(260px, 100%) !important;
                width: calc(50% - 0.35rem) !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor)
                div[data-testid="stTabs"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 calc(50% - 0.65rem) !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor)
                [data-testid="stWidgetLabel"] p {
                font-size: 0.9rem !important;
            }
        }
        /* Filters & search: full-width stack under 1100px */
        @media (max-width: 1100px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor)
                div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 0.75rem !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor)
                div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
                width: 100% !important;
            }
        }
        @media (max-width: 640px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor)
                div[data-testid="stHorizontalBlock"] > div[data-testid="column"],
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor)
                div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex-basis: 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
                width: 100% !important;
            }
            section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button,
            section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button,
            section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"] {
                font-size: 0.86rem !important;
                padding: 7px 12px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _job_db_admin_read() -> bool:
    """Admin / manager (PM) use service-role reads so linked estimate/customer rows stay visible under RLS."""
    return current_role() in {"admin", "manager"}


def _fetch_customers_for_job_db() -> list[dict[str, Any]]:
    if _job_db_admin_read():
        try:
            return fetch_table_admin("customers", limit=5000, order_by="customer_name")
        except Exception:
            return fetch_table("customers", limit=5000, order_by="customer_name")
    return fetch_table("customers", limit=5000, order_by="customer_name")


def _fetch_estimates_for_job_db() -> list[dict[str, Any]]:
    """Columns for labels + overview card; fall back if a column is missing."""
    if _job_db_admin_read():
        for cols in (
            "id,quote_number,customer_id,customer_contact_id,proposal_total,final_bid,status,job_id,scope_of_work,po_amount,po_number,estimate_description",
            "id,quote_number,customer_id,proposal_total,final_bid,status,job_id,scope_of_work,po_amount",
            "id,quote_number,customer_id,proposal_total,status,job_id,scope_of_work",
            "id,quote_number,customer_id,proposal_total,status,job_id",
        ):
            try:
                return fetch_table_admin(
                    "estimates",
                    columns=cols,
                    limit=5000,
                    order_by="quote_number",
                )
            except Exception:
                continue
        try:
            return fetch_table_admin("estimates", limit=5000, order_by="quote_number")
        except Exception:
            return fetch_table("estimates", limit=5000, order_by="quote_number")
    for cols in (
        "id,quote_number,customer_id,customer_contact_id,proposal_total,final_bid,status,job_id,scope_of_work,po_amount,po_number,estimate_description",
        "id,quote_number,customer_id,proposal_total,final_bid,status,job_id,scope_of_work,po_amount",
        "id,quote_number,customer_id,proposal_total,status,job_id,scope_of_work",
        "id,quote_number,customer_id,proposal_total,status,job_id",
    ):
        try:
            return fetch_table(
                "estimates",
                columns=cols,
                limit=5000,
                order_by="quote_number",
            )
        except Exception:
            continue
    return fetch_table("estimates", limit=5000, order_by="quote_number")


def _fetch_contacts_for_job_database(
    customer_id: str,
    customer_location_id: str | None = None,
) -> list[dict[str, Any]]:
    """Contacts for job form; scoped by job site when set (matches Estimates editor)."""
    try:
        from services.customer_contacts import fetch_contacts_for_customer_scope
    except ImportError:
        from app.services.customer_contacts import fetch_contacts_for_customer_scope  # type: ignore

    admin_read = current_role() in {"admin", "manager"}
    cid = str(customer_id or "").strip()
    if not cid:
        return []
    loc = str(customer_location_id or "").strip() or None
    return fetch_contacts_for_customer_scope(
        cid,
        loc,
        admin_read=admin_read,
        include_inactive=False,
    )


def _fetch_estimate_row_by_id(estimate_id: str) -> dict[str, Any] | None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    if _job_db_admin_read():
        try:
            rows = fetch_by_match_admin("estimates", {"id": eid}, limit=1)
            return rows[0] if rows else None
        except Exception:
            pass
    try:
        rows = fetch_by_match("estimates", {"id": eid}, limit=1)
        return rows[0] if rows else None
    except Exception:
        return None


def _contact_row_by_id(contact_id: str) -> dict[str, Any] | None:
    cid = str(contact_id or "").strip()
    if not cid:
        return None
    if _job_db_admin_read():
        try:
            rows = fetch_by_match_admin("customer_contacts", {"id": cid}, limit=1)
            return rows[0] if rows else None
        except Exception:
            pass
    try:
        rows = fetch_by_match("customer_contacts", {"id": cid}, limit=1)
        return rows[0] if rows else None
    except Exception:
        return None


def _customer_display_name_for_id(
    customer_id: str | None,
    customers: list[dict[str, Any]],
    name_by_id: dict[str, str],
) -> str:
    cid = str(customer_id or "").strip()
    if not cid:
        return ""
    n = name_by_id.get(cid)
    if n:
        return str(n).strip()
    for c in customers:
        if str(c.get("id") or "").strip() == cid:
            return str(c.get("customer_name") or "").strip()
    return ""


def _text_snippet(text: str, *, max_len: int = 600) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _safe_date_value(value):
    if value is None or str(value).strip() == "":
        return None
    return value


def _clear_job_mode() -> None:
    st.session_state["job_view_mode"] = "list"
    st.session_state["selected_job_id"] = None
    st.session_state.pop("job_mode", None)
    st.session_state.pop("job_edit_id", None)
    st.session_state.pop("job_number_manual_input", None)


def _sync_job_mode_from_view_state() -> None:
    """Keep legacy ``job_mode`` / ``job_edit_id`` aligned with ``job_view_mode`` for the add/edit panel."""
    jvm = str(st.session_state.get("job_view_mode") or "list").strip().lower()
    sid = str(st.session_state.get("selected_job_id") or "").strip()
    can_edit = current_role() in {"admin", "manager"}
    if jvm == "create" and can_edit:
        st.session_state["job_mode"] = "add"
        st.session_state.pop("job_edit_id", None)
    elif jvm == "edit" and sid and (can_edit or current_role() == "employee"):
        st.session_state["job_mode"] = "edit"
        st.session_state["job_edit_id"] = sid
    elif jvm in ("list", "view"):
        st.session_state.pop("job_mode", None)
        st.session_state.pop("job_edit_id", None)


def _migrate_job_view_mode_from_legacy_session() -> None:
    """Older flows set ``job_mode`` only; promote to ``job_view_mode`` + ``selected_job_id``."""
    jvm = str(st.session_state.get("job_view_mode") or "list").strip().lower()
    if jvm != "list":
        return
    jm = st.session_state.get("job_mode")
    je = str(st.session_state.get("job_edit_id") or "").strip()
    if jm == "edit" and je:
        st.session_state["job_view_mode"] = "edit"
        st.session_state["selected_job_id"] = je
    elif jm == "add":
        st.session_state["job_view_mode"] = "create"
        st.session_state["selected_job_id"] = None


def _inject_job_detail_view_page_css() -> None:
    if st.session_state.get(JOB_DB_DETAIL_VIEW_CSS_KEY):
        return
    st.session_state[JOB_DB_DETAIL_VIEW_CSS_KEY] = True
    st.markdown(
        """
        <style>
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-detail-sticky-host) {
            position: sticky;
            top: 0.5rem;
            z-index: 50;
            background: linear-gradient(180deg, #f8fafc 92%, transparent);
            padding-bottom: 0.35rem;
            margin-bottom: 0.25rem;
        }
        .ips-job-detail-hero {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 1.1rem 1.25rem;
            margin: 0.5rem 0 1rem 0;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
        }
        .ips-job-detail-hero h1 {
            font-size: 1.55rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0 0 0.35rem 0;
            line-height: 1.2;
        }
        .ips-job-detail-meta {
            color: #475569;
            font-size: 0.95rem;
            line-height: 1.5;
        }
        .ips-job-detail-section-title {
            font-size: 1.12rem;
            font-weight: 750;
            color: #0f172a;
            margin: 0 0 0.5rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _job_detail_display_number(row: dict[str, Any] | None, *, has_job_number_column: bool) -> str:
    """Human-facing job # for detail header (matches list/table logic)."""
    if not row:
        return ""
    if has_job_number_column:
        jn = str(row.get("job_number") or "").strip()
        if jn:
            return jn
    for k in ("job_id", "id"):
        v = str(row.get(k) or "").strip()
        if v:
            return v
    return ""


def _jobs_table_has_customer_location_column() -> bool:
    try:
        fetch_table("jobs", columns="id,customer_location_id", limit=1)
        return True
    except Exception:
        return False


def _job_form_linked_estimate_id(estimate_options: dict[str, Any], linked_label: str) -> str | None:
    """Map the Linked estimate select label to an estimate UUID, or ``None`` for a standalone job."""
    if not str(linked_label or "").strip():
        return None
    raw = estimate_options.get(linked_label)
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def _build_job_form_estimate_options(
    *,
    estimates: list[dict[str, Any]],
    estimate_label_map: dict[str, str],
    selected_job: dict[str, Any] | None,
    estimate_detail: dict[str, Any] | None,
    customers: list[dict[str, Any]],
    customer_name_by_id: dict[str, str],
) -> dict[str, Any]:
    """Label → estimate id for the job form (includes current link even if filtered out of list)."""
    estimate_options: dict[str, Any] = {"": None}
    for e in estimates:
        eid = str(e.get("id") or "").strip()
        if not eid:
            continue
        lab = estimate_label_map.get(eid)
        if lab:
            estimate_options[lab] = eid
    if selected_job and selected_job.get("estimate_id"):
        _leid = str(selected_job.get("estimate_id"))
        existing_ids = {str(v) for v in estimate_options.values() if v is not None}
        if _leid not in existing_ids:
            lab = estimate_label_map.get(_leid)
            if not lab and estimate_detail:
                qn = str(estimate_detail.get("quote_number") or "").strip()
                cn = _customer_display_name_for_id(
                    estimate_detail.get("customer_id"),
                    customers,
                    customer_name_by_id,
                )
                _est_status_lbl = str(estimate_detail.get("status") or "").strip()
                lab = (
                    f"{qn} | {cn} | {_est_status_lbl}"
                    if qn or cn or _est_status_lbl
                    else f"Estimate ({_leid[:8]}…)"
                )
            elif not lab:
                lab = f"Estimate ({_leid[:8]}…)"
            estimate_options[lab] = _leid
    return estimate_options


def _job_db_money_detail(v: Any) -> str:
    """Currency for job overview estimate card (2 decimals, $0.00 shows as $0.00)."""
    try:
        if v is None or str(v).strip() == "":
            return "—"
        fv = float(v)
        return f"${fv:,.2f}"
    except Exception:
        return "—"


def _estimate_row_money_for_total(row: dict[str, Any]) -> str:
    """Prefer proposal total, then final bid (same idea as Job Costing)."""
    for key in ("proposal_total", "final_bid"):
        if key not in row:
            continue
        raw = row.get(key)
        if raw is None or str(raw).strip() == "":
            continue
        try:
            fv = float(raw)
            if fv != 0 or key == "proposal_total":
                return _job_db_money_detail(fv)
        except Exception:
            continue
    return "—"


def _merge_estimate_detail_for_display(
    *,
    estimate_id: str,
    estimate_detail: dict[str, Any] | None,
) -> dict[str, Any]:
    """DB row plus list row overlay (display only; list wins on overlapping keys)."""
    full = _fetch_estimate_row_by_id(estimate_id) or {}
    base = dict(estimate_detail or {})
    return {**full, **base}


def _estimate_contact_display(det: dict[str, Any]) -> str:
    cid = str(det.get("customer_contact_id") or "").strip()
    if not cid:
        return "—"
    row = _contact_row_by_id(cid)
    if not row:
        return f"Contact id `{cid[:8]}…`"
    try:
        from services.customer_contacts import contact_option_label
    except ImportError:
        from app.services.customer_contacts import contact_option_label  # type: ignore
    return str(contact_option_label(row)).strip() or "—"


def _render_job_estimate_summary_overview(
    *,
    selected_job: dict[str, Any],
    estimate_options: dict[str, Any],
    estimate_detail: dict[str, Any] | None,
    estimate_label_map: dict[str, str],
    estimate_quote_by_id: dict[str, str],
    customers: list[dict[str, Any]],
    customer_name_by_id: dict[str, str],
    can_edit: bool,
) -> str:
    """
    Overview-only estimate block: summary + link / open / unlink (returns linked-estimate widget value).
    """
    try:
        from app.ui import IPS_NAV_PENDING_KEY
    except ImportError:
        from ui import IPS_NAV_PENDING_KEY  # type: ignore

    jid = str(selected_job.get("id") or "").strip()
    eid = str(selected_job.get("estimate_id") or "").strip()

    with st.container(border=True):
        st.markdown('<span class="ips-job-estimate-summary-host"></span>', unsafe_allow_html=True)
        st.markdown("#### Estimate Summary")

        if not eid:
            st.markdown(
                "<p style='margin:0 0 0.5rem 0;font-weight:700;color:#111827;'>No estimate linked to this job.</p>",
                unsafe_allow_html=True,
            )
            st.caption("Pick a quote below, then click **Update Job** to save the link.")
        else:
            det = _merge_estimate_detail_for_display(estimate_id=eid, estimate_detail=estimate_detail)
            qn = str(
                estimate_quote_by_id.get(eid)
                or det.get("quote_number")
                or ""
            ).strip()
            name_hint = str(det.get("estimate_description") or "").strip()
            title_line = html.escape(qn) if qn else f"Estimate `{html.escape(eid[:8])}…`"
            if name_hint and len(name_hint) <= 120:
                title_line += f" · <span style='font-weight:600'>{html.escape(name_hint)}</span>"
            elif name_hint:
                title_line += f" · <span style='font-weight:600'>{html.escape(name_hint[:117])}…</span>"
            st_t = str(det.get("status") or "").strip()
            cust = _customer_display_name_for_id(det.get("customer_id"), customers, customer_name_by_id)
            po_amt = _job_db_money_detail(det.get("po_amount"))
            po_num = str(det.get("po_number") or "").strip()
            po_lbl = f"PO amount ({html.escape(po_num)})" if po_num else "PO / quote amount"
            prop = _job_db_money_detail(det.get("proposal_total")) if det.get("proposal_total") not in (None, "") else "—"
            fin = _job_db_money_detail(det.get("final_bid")) if det.get("final_bid") not in (None, "") else "—"
            tot = _estimate_row_money_for_total(det)
            awarded = _job_db_money_detail(selected_job.get("awarded_amount"))
            contact_disp = html.escape(_estimate_contact_display(det))
            card_html = (
                f"<div class='ips-jes-card'>"
                f"<p style='margin:0 0 0.65rem 0;font-size:0.95rem;color:#111827;'><strong>Linked quote</strong> · {title_line}</p>"
                f"<div class='ips-jes-grid'>"
                f"<div><span class='ips-jes-lbl'>Status</span><span class='ips-jes-val'>{html.escape(st_t) if st_t else '—'}</span></div>"
                f"<div><span class='ips-jes-lbl'>Estimate total</span><span class='ips-jes-val'>{html.escape(tot)}</span></div>"
                f"<div><span class='ips-jes-lbl'>Proposal</span><span class='ips-jes-val'>{html.escape(prop)}</span></div>"
                f"<div><span class='ips-jes-lbl'>Final bid</span><span class='ips-jes-val'>{html.escape(fin)}</span></div>"
                f"<div><span class='ips-jes-lbl'>{po_lbl}</span><span class='ips-jes-val'>{html.escape(po_amt)}</span></div>"
                f"<div><span class='ips-jes-lbl'>Awarded (job)</span><span class='ips-jes-val'>{html.escape(awarded)}</span></div>"
                f"<div><span class='ips-jes-lbl'>Customer</span><span class='ips-jes-val'>{html.escape(cust) if cust else '—'}</span></div>"
                f"<div><span class='ips-jes-lbl'>Contact (on quote)</span><span class='ips-jes-val'>{contact_disp}</span></div>"
                f"</div></div>"
            )
            st.markdown(card_html, unsafe_allow_html=True)

        b_open, b_rm = st.columns([1, 1], gap="small")
        with b_open:
            if eid and st.button("Open estimate", type="primary", use_container_width=True, key=f"job_ov_open_est_{jid}"):
                try:
                    from app.pages import estimates as _estimates_page
                except ImportError:
                    import pages.estimates as _estimates_page  # type: ignore
                _estimates_page._load_estimate_into_session(eid)
                if str(st.session_state.get("loaded_estimate_id") or "").strip() == eid:
                    st.session_state["estimates_view"] = "edit"
                    st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
                    st.rerun()
                st.warning("Could not open that estimate (missing or no access).")
        with b_rm:
            if eid and can_edit:
                with st.popover("Unlink estimate", use_container_width=True):
                    st.caption("Removes the link from this job only. The estimate is **not** deleted.")
                    if st.button("Remove linked estimate", type="primary", key=f"job_ov_unlink_est_{jid}"):
                        update_rows_admin("jobs", {"estimate_id": None}, {"id": selected_job["id"]})
                        st.success("Link removed. You can attach a different quote below.")
                        st.rerun()

        estimate_labels = [""] + [k for k in estimate_options.keys() if k]
        current_estimate_label = ""
        if selected_job.get("estimate_id"):
            _seid = str(selected_job.get("estimate_id"))
            current_estimate_label = estimate_label_map.get(_seid, "")
            if not current_estimate_label:
                for lab, eid_opt in estimate_options.items():
                    if lab and str(eid_opt) == _seid:
                        current_estimate_label = lab
                        break
        _lbl = "Link estimate" if not eid else "Linked estimate (change)"
        linked_estimate = st.selectbox(
            _lbl,
            estimate_labels,
            index=estimate_labels.index(current_estimate_label) if current_estimate_label in estimate_labels else 0,
            disabled=not can_edit,
            key="job_form_linked_estimate",
            help="Leave blank for a standalone job. Pick a quote to link this job to an estimate.",
        )
        if not eid:
            if st.button("Link estimate", type="secondary", use_container_width=True, key=f"job_ov_link_hint_{jid}"):
                st.info("Choose a quote in **Link estimate** above, then click **Update Job** at the bottom of the form.")

    return linked_estimate


def _render_job_form_panel(
    *,
    mode: str,
    can_edit: bool,
    selected_job: dict | None,
    jobs: list[dict],
    has_job_number_column: bool,
    has_customer_location_column: bool,
    customers: list[dict],
    estimates: list[dict],
    customer_name_by_id: dict[str, str],
    estimate_label_map: dict[str, str],
    estimate_quote_by_id: dict[str, str],
    estimate_detail: dict[str, Any] | None = None,
    show_main_heading: bool = True,
) -> None:
    """Full-width job detail card: add/edit form and tabs (list view uses a separate header)."""
    with st.container(border=True):
        st.markdown('<span class="ips-job-edit-panel-anchor"></span>', unsafe_allow_html=True)
        if show_main_heading:
            title = "Add Job" if mode == "add" else "Edit Job"
            st.markdown(f"### {title}")
        if mode == "add":
            st.caption(
                "Standalone job — **no estimate required**. Leave **Linked estimate** empty, "
                "or pick a quote only if you are attaching this job to an existing estimate."
            )

        use_job_tabs = mode == "edit" and bool(selected_job)
        tab_overview_ctx = contextlib.nullcontext()
        if use_job_tabs and selected_job:
            edit_jid = str(selected_job.get("id") or "").strip()
            jl = job_row_select_label(selected_job)
            admin_rd = _job_db_admin_read()
            can_tasks = can_edit or (current_role() == "employee")
            try:
                from app.pages.job_database_job_tasks import (
                    render_job_cost_tab,
                    render_job_tasks_tab,
                )
            except ImportError:
                from pages.job_database_job_tasks import (  # type: ignore
                    render_job_cost_tab,
                    render_job_tasks_tab,
                )
            t_ov, t_ts, t_co = st.tabs(["Overview", "Tasks", "Cost"])
            with t_ts:
                render_job_tasks_tab(job_id=edit_jid, job_label=jl, can_edit_tasks=can_tasks, admin_read=admin_rd)
            with t_co:
                render_job_cost_tab(job_id=edit_jid, job_row=selected_job)
            tab_overview_ctx = t_ov
        with tab_overview_ctx:
            linked_estimate = ""
            estimate_options = _build_job_form_estimate_options(
                estimates=estimates,
                estimate_label_map=estimate_label_map,
                selected_job=selected_job,
                estimate_detail=estimate_detail,
                customers=customers,
                customer_name_by_id=customer_name_by_id,
            )
            if use_job_tabs and selected_job:
                linked_estimate = _render_job_estimate_summary_overview(
                    selected_job=selected_job,
                    estimate_options=estimate_options,
                    estimate_detail=estimate_detail,
                    estimate_label_map=estimate_label_map,
                    estimate_quote_by_id=estimate_quote_by_id,
                    customers=customers,
                    customer_name_by_id=customer_name_by_id,
                    can_edit=can_edit,
                )

            customer_options: dict[str, str] = {}
            for c in customers:
                nm = str(c.get("customer_name") or "").strip()
                cid = str(c.get("id") or "").strip()
                if nm and cid:
                    customer_options[nm] = cid

            def current_value(field_name, default=""):
                if selected_job:
                    value = selected_job.get(field_name, default)
                    return "" if value is None else value
                return default
    
            _ro = not can_edit
    
            st.markdown("#### Customer & job")
            c1, c2 = st.columns(2, gap="small")
            cust_keys = [""] + sorted(customer_options.keys())
            selected_cust_name = ""
            if selected_job:
                scid = str(selected_job.get("customer_id") or "").strip()
                if scid:
                    selected_cust_name = _customer_display_name_for_id(
                        scid,
                        customers,
                        customer_name_by_id,
                    )
                    if selected_cust_name and selected_cust_name not in customer_options:
                        customer_options[selected_cust_name] = scid
                        cust_keys = [""] + sorted(customer_options.keys())
            cust_index = cust_keys.index(selected_cust_name) if selected_cust_name in cust_keys else 0
            customer_name = c1.selectbox("Customer", cust_keys, index=cust_index, disabled=_ro, key="job_form_customer")
            job_name = c2.text_input("Job Name", value=current_value("job_name"), disabled=_ro, key="job_form_job_name")
    
            selected_contact_id: str | None = None
            selected_customer_location_id: str | None = None
            cust_uuid = customer_options.get(customer_name) if customer_name else None
    
            if has_customer_location_column:
                try:
                    from services.customer_locations import fetch_locations_for_customer, location_option_label
                except ImportError:
                    from app.services.customer_locations import fetch_locations_for_customer, location_option_label  # type: ignore
    
                if cust_uuid:
                    loc_rows = fetch_locations_for_customer(
                        str(cust_uuid),
                        admin_read=_job_db_admin_read(),
                        include_inactive=False,
                    )
                    cur_lid = str(current_value("customer_location_id") or "").strip()
                    if cur_lid:
                        have = {str(r.get("id") or "") for r in loc_rows}
                        if cur_lid not in have:
                            orphan = fetch_one("customer_locations", {"id": cur_lid})
                            if orphan:
                                loc_rows = [orphan] + list(loc_rows)
                    labels = ["(none)"] + [location_option_label(r) for r in loc_rows]
                    lids: list[str | None] = [None] + [str(r["id"]) for r in loc_rows if r.get("id")]
                    try:
                        lix = lids.index(cur_lid) if cur_lid else 0
                    except ValueError:
                        lix = 0
                    lix = min(max(lix, 0), len(labels) - 1)
                    loc_pick = st.selectbox(
                        "Job site",
                        options=list(range(len(labels))),
                        index=lix,
                        format_func=lambda i: labels[i],
                        disabled=_ro,
                        key=f"job_form_custloc_{cust_uuid}",
                        help="Optional: saved customer site from the Customers tab. Contacts are filtered by site.",
                    )
                    selected_customer_location_id = lids[int(loc_pick)]
                else:
                    st.caption("Select a customer to choose a job site.")
    
            if cust_uuid:
                inject_contact_picker_styles()
                loc_scope = str(selected_customer_location_id or "").strip() or None
                contacts = _fetch_contacts_for_job_database(str(cust_uuid), loc_scope)
                cur_ct = str(current_value("customer_contact_id") or "").strip()
                if cur_ct:
                    cids = {str(c.get("id") or "") for c in contacts}
                    if cur_ct not in cids:
                        orphan = _contact_row_by_id(cur_ct)
                        if orphan:
                            contacts = [orphan] + contacts
                if not contacts:
                    st.caption("No contacts found for this customer / site.")
                    render_contact_quick_add_when_empty(
                        customer_id=str(cust_uuid),
                        key_prefix="job",
                        disabled=_ro,
                        customer_location_id=loc_scope,
                    )
                    selected_contact_id = None
                else:
                    cur_ct = str(current_value("customer_contact_id") or "").strip()
                    by_id = {str(c.get("id") or ""): c for c in contacts}
                    chosen_id: str | None = cur_ct if cur_ct in by_id else None
                    if chosen_id is None:
                        primary = next((c for c in contacts if c.get("is_primary")), None)
                        if primary and primary.get("id"):
                            chosen_id = str(primary["id"])
                        elif len(contacts) == 1 and contacts[0].get("id"):
                            chosen_id = str(contacts[0]["id"])
    
                    labels = ["(none)"] + [contact_option_label(c) for c in contacts]
                    ct_ids: list[str | None] = [None] + [str(c["id"]) for c in contacts]
                    try:
                        ct_idx = ct_ids.index(str(chosen_id)) if chosen_id else 0
                    except ValueError:
                        ct_idx = 0
                        chosen_id = None
                    ct_idx = min(max(ct_idx, 0), len(labels) - 1)
                    loc_key = loc_scope or "none"
                    ct_sel = st.selectbox(
                        "Contact",
                        options=list(range(len(labels))),
                        index=ct_idx,
                        format_func=lambda i: labels[i],
                        disabled=_ro,
                        key=f"job_form_contact_{cust_uuid}_{loc_key}",
                        help="Optional: primary contact for this job (site + company-wide contacts).",
                    )
                    selected_contact_id = ct_ids[int(ct_sel)]
                    render_contact_detail_preview(by_id.get(str(selected_contact_id or "")))
            else:
                st.caption("Select a customer to choose a contact.")
    
            st.markdown("#### Job #")
            if has_job_number_column and selected_job:
                st.text_input(
                    "Job #",
                    value=str(current_value("job_number") or ""),
                    disabled=True,
                    help="Assigned when the job was created.",
                    key="job_form_job_number",
                )
            elif has_job_number_column and mode == "add":
                suggested_jn = next_job_number()
                st.caption("Suggested job number is prefilled. You can override it.")
                st.caption(f"Suggested: **{suggested_jn}**")
                if "job_number_manual_input" not in st.session_state:
                    st.session_state["job_number_manual_input"] = suggested_jn
                st.text_input(
                    "Job #",
                    key="job_number_manual_input",
                    help="Leave the suggested value or type a custom job number.",
                    label_visibility="collapsed",
                )
    
            # Site/address: use Job site above (customer_location_id). Preserve legacy jobs.location on edit only.
            location = str(current_value("location") or "").strip()
    
            if use_job_tabs and selected_job:
                st.markdown("#### Status")
            else:
                st.markdown("#### Status & linked estimate")
                if mode == "add":
                    st.caption("*Linked estimate* is optional — leave the first row selected for a job with no quote.")
            status_options = list(JOB_STATUSES)
            current_status = str(current_value("status", "Draft") or "Draft").strip() or "Draft"
            if current_status not in status_options:
                status_options = status_options + [current_status]
            status_idx = status_options.index(current_status)
            if use_job_tabs and selected_job:
                status = st.selectbox(
                    "Status",
                    status_options,
                    index=status_idx,
                    disabled=_ro,
                    key="job_form_status",
                )
            else:
                c5, c6 = st.columns(2, gap="small")
                status = c5.selectbox(
                    "Status",
                    status_options,
                    index=status_idx,
                    disabled=_ro,
                    key="job_form_status",
                )
                estimate_labels = [""] + [k for k in estimate_options.keys() if k]
                current_estimate_label = ""
                if selected_job and selected_job.get("estimate_id"):
                    _seid = str(selected_job.get("estimate_id"))
                    current_estimate_label = estimate_label_map.get(_seid, "")
                    if not current_estimate_label:
                        for lab, eid in estimate_options.items():
                            if lab and str(eid) == _seid:
                                current_estimate_label = lab
                                break
                _link_lbl = "Linked estimate (optional)" if mode == "add" else "Linked estimate"
                linked_estimate = c6.selectbox(
                    _link_lbl,
                    estimate_labels,
                    index=estimate_labels.index(current_estimate_label) if current_estimate_label in estimate_labels else 0,
                    disabled=_ro,
                    key="job_form_linked_estimate",
                    help="Leave blank for a standalone job. Pick a row only when this job should reference an estimate.",
                )
    
            st.markdown("#### Awarded amount")
            awarded_amount = st.number_input(
                "Awarded Amount",
                min_value=0.0,
                value=float(current_value("awarded_amount", 0) or 0),
                step=100.0,
                format="%.2f",
                disabled=_ro,
                key="job_form_awarded_amount",
            )
    
            st.markdown("#### Notes")
            notes = st.text_area(
                "Notes",
                value=current_value("notes"),
                disabled=_ro,
                height=80,
                key="job_form_notes",
            )
    
            if not can_edit:
                if mode == "add":
                    st.info("Only office roles can create jobs.")
                    return
                st.caption("View only — contact the office to change job details.")
    
            b1, b2 = st.columns(2, gap="small")
            if mode == "add":
                if b1.button("Create Job", type="primary", use_container_width=True, disabled=_ro, key="job_form_create"):
                    if not customer_name:
                        st.error("Customer required")
                        st.stop()
                    if not job_name.strip():
                        st.error("Job Name required")
                        st.stop()
                    linked_eid = _job_form_linked_estimate_id(estimate_options, linked_estimate)
                    # source_type omitted until jobs schema includes that column (sql/022); linkage is estimate_id.
                    payload = {
                        "customer_id": customer_options[customer_name],
                        "customer_contact_id": selected_contact_id,
                        "job_name": job_name.strip(),
                        "location": location.strip(),
                        "status": status,
                        "estimate_id": linked_eid,
                        "awarded_amount": float(awarded_amount or 0),
                        "notes": notes.strip(),
                    }
                    if has_customer_location_column:
                        payload["customer_location_id"] = selected_customer_location_id
                    if has_job_number_column:
                        final_job_number = str(st.session_state.get("job_number_manual_input") or "").strip()
                        if not final_job_number:
                            st.error("Enter a job number.")
                            st.stop()
                        try:
                            dup = fetch_by_match_admin(
                                "jobs",
                                {"job_number": final_job_number},
                                columns="id,job_number",
                                limit=1,
                            )
                        except Exception:
                            dup = fetch_by_match(
                                "jobs",
                                {"job_number": final_job_number},
                                columns="id,job_number",
                                limit=1,
                            )
                        if dup:
                            st.error("Job number already exists.")
                            st.stop()
                        payload["job_number"] = final_job_number
                    insert_row_admin("jobs", payload)
                    _clear_job_mode()
                    st.success("Job created.")
                    st.rerun()
            else:
                if b1.button("Update Job", type="primary", use_container_width=True, disabled=_ro, key="job_form_update"):
                    if not selected_job:
                        st.error("Select a job first.")
                        st.stop()
                    if not customer_name:
                        st.error("Customer required")
                        st.stop()
                    if not job_name.strip():
                        st.error("Job Name required")
                        st.stop()
                    linked_eid = _job_form_linked_estimate_id(estimate_options, linked_estimate)
                    # source_type omitted until jobs schema includes that column (sql/022); linkage is estimate_id.
                    payload = {
                        "customer_id": customer_options[customer_name],
                        "customer_contact_id": selected_contact_id,
                        "job_name": job_name.strip(),
                        "location": location.strip(),
                        "status": status,
                        "estimate_id": linked_eid,
                        "awarded_amount": float(awarded_amount or 0),
                        "notes": notes.strip(),
                    }
                    if has_customer_location_column:
                        payload["customer_location_id"] = selected_customer_location_id
                    update_rows_admin("jobs", payload, {"id": selected_job["id"]})
                    _clear_job_mode()
                    st.success("Job updated.")
                    st.rerun()
        
            if b2.button("Cancel", use_container_width=True, key="job_form_cancel"):
                _clear_job_mode()
                st.rerun()
        
            # --- Weekly Timesheets (customer signature workflow) ---
            if mode == "edit" and selected_job:
                # --- Email notification settings (per job) ---
                with st.expander("Email settings", expanded=False):
                    st.caption("Configure customer/internal recipients and enable automatic updates for this job.")
                    try:
                        from app.services.email_notifications import (
                            fetch_job_email_settings_row,
                            upsert_job_email_settings,
                        )
                    except ImportError:
                        from services.email_notifications import (  # type: ignore
                            fetch_job_email_settings_row,
                            upsert_job_email_settings,
                        )
        
                    jid = str(selected_job.get("id") or "").strip()
                    row = fetch_job_email_settings_row(jid, admin=_job_db_admin_read()) or {}
                    cust = row.get("customer_recipients") or []
                    internal = row.get("internal_recipients") or []
                    cc = row.get("cc_recipients") or []
        
                    c1, c2 = st.columns(2, gap="small")
                    with c1:
                        cust_in = st.text_area(
                            "Customer recipients",
                            value=", ".join([str(x) for x in (cust or []) if str(x).strip()]),
                            height=68,
                            placeholder="email1@customer.com, email2@customer.com",
                            key=f"job_email_cust_{jid}",
                        )
                        internal_in = st.text_area(
                            "Internal IPS recipients",
                            value=", ".join([str(x) for x in (internal or []) if str(x).strip()]),
                            height=68,
                            placeholder="ops@ips.com, pm@ips.com",
                            key=f"job_email_internal_{jid}",
                        )
                    with c2:
                        cc_in = st.text_area(
                            "CC recipients",
                            value=", ".join([str(x) for x in (cc or []) if str(x).strip()]),
                            height=68,
                            placeholder="optional CC list",
                            key=f"job_email_cc_{jid}",
                        )
                        notes_email = st.text_area(
                            "Email notes",
                            value=str(row.get("notes") or ""),
                            height=68,
                            placeholder="Optional",
                            key=f"job_email_notes_{jid}",
                        )
        
                    t1, t2 = st.columns(2, gap="small")
                    with t1:
                        enable_daily = st.checkbox(
                            "Enable daily update emails",
                            value=bool(row.get("enable_daily_update_emails", False)),
                            key=f"job_email_enable_daily_{jid}",
                        )
                        enable_weekly = st.checkbox(
                            "Enable weekly Friday update emails",
                            value=bool(row.get("enable_weekly_friday_update_emails", False)),
                            key=f"job_email_enable_weekly_{jid}",
                        )
                    with t2:
                        enable_safety = st.checkbox(
                            "Enable safety item update emails",
                            value=bool(row.get("enable_safety_item_update_emails", False)),
                            key=f"job_email_enable_safety_{jid}",
                            help="Framework toggle (requires safety status source to be configured).",
                        )
                        enable_budget = st.checkbox(
                            "Enable budget/PO alerts",
                            value=bool(row.get("enable_budget_po_alerts", False)),
                            key=f"job_email_enable_budget_{jid}",
                        )
                    is_active = st.checkbox(
                        "Email settings active",
                        value=bool(row.get("is_active", True)),
                        key=f"job_email_is_active_{jid}",
                    )
        
                    if st.button(
                        "Save email settings",
                        type="primary",
                        use_container_width=True,
                        key=f"job_email_save_{jid}",
                        disabled=not can_edit,
                    ):
                        try:
                            upsert_job_email_settings(
                                jid,
                                customer_recipients=cust_in,
                                internal_recipients=internal_in,
                                cc_recipients=cc_in,
                                enable_daily=enable_daily,
                                enable_weekly_friday=enable_weekly,
                                enable_safety=enable_safety,
                                enable_budget_po_alerts=enable_budget,
                                is_active=is_active,
                                notes=notes_email,
                            )
                        except Exception as exc:
                            st.error(f"Could not save: {exc}")
                        else:
                            st.success("Saved.")
                            st.rerun()
        
                with st.expander("Weekly Timesheets", expanded=False):
                    st.caption("Generate a customer-facing weekly timesheet PDF and share a secure signing link.")
                    jid = str(selected_job.get("id") or "").strip()
                    if not jid:
                        st.caption("Select a job.")
                    else:
                        # Week picker (Monday start)
                        from datetime import date as _date, timedelta as _td
        
                        today = _date.today()
                        default_ws = today - _td(days=today.weekday() + 7)  # last week Monday
                        week_start = st.date_input("Week start (Mon)", value=default_ws, key=f"jwt_week_{jid}")
                        summary = st.text_area(
                            "Work summary / notes (optional)",
                            key=f"jwt_summary_{jid}",
                            height=72,
                            placeholder="Optional summary shown on the PDF.",
                        )
                        if st.button(
                            "Generate unsigned PDF",
                            type="primary",
                            use_container_width=True,
                            disabled=not can_edit,
                            key=f"jwt_gen_{jid}",
                        ):
                            try:
                                row = generate_unsigned_timesheet_for_job_week(
                                    job_id=jid,
                                    week_start=week_start,
                                    work_summary=str(summary or "").strip(),
                                )
                            except Exception as exc:
                                st.error(f"Could not generate: {exc}")
                                st.stop()
                            st.success("Generated.")
                            st.session_state[f"jwt_last_row_{jid}"] = row
                            st.rerun()
        
                        try:
                            rows = fetch_by_match_admin(
                                "job_weekly_timesheets",
                                {"job_id": jid},
                                columns="id,week_start,week_end,status,unsigned_pdf_url,signed_pdf_url,sent_at,signed_at,sign_token,sign_token_expires_at",
                                limit=200,
                            )
                        except Exception:
                            rows = []
        
                        if not rows:
                            st.caption("No weekly timesheets yet. Run migration `sql/031_job_weekly_timesheets.sql`.")
                        else:
                            rows = sorted(rows, key=lambda r: str(r.get("week_start") or ""), reverse=True)
                            latest = rows[0]
                            st.markdown("**Latest**")
                            up = str(latest.get("unsigned_pdf_url") or "").strip()
                            sp = str(latest.get("signed_pdf_url") or "").strip()
                            token = str(latest.get("sign_token") or "").strip()
                            unsigned_link = create_signed_url(up, expires_in=3600) if up else ""
                            signed_link = create_signed_url(sp, expires_in=3600) if sp else ""
                            sign_link = f"?tsign={token}" if token else ""
                            st.caption(
                                f"Week {str(latest.get('week_start') or '')} → {str(latest.get('week_end') or '')} · "
                                f"Status **{str(latest.get('status') or '')}**"
                            )
                            a1, a2, a3 = st.columns(3, gap="small")
                            with a1:
                                if unsigned_link:
                                    st.link_button("Open unsigned", unsigned_link, use_container_width=True)
                                else:
                                    st.button("Open unsigned", use_container_width=True, disabled=True)
                            with a2:
                                if sign_link:
                                    st.link_button("Open sign page", sign_link, use_container_width=True)
                                else:
                                    st.button("Open sign page", use_container_width=True, disabled=True)
                            with a3:
                                if signed_link:
                                    st.link_button("Open signed", signed_link, use_container_width=True)
                                else:
                                    st.button("Open signed", use_container_width=True, disabled=True)
        
                            st.markdown("**History**")
                            table = []
                            for r in rows[:30]:
                                token = str(r.get("sign_token") or "").strip()
                                table.append(
                                    {
                                        "Week": f"{str(r.get('week_start') or '')} → {str(r.get('week_end') or '')}",
                                        "Status": str(r.get("status") or ""),
                                        "Sent": str(r.get("sent_at") or "")[:19],
                                        "Signed": str(r.get("signed_at") or "")[:19],
                                        "Sign link": (f"?tsign={token}" if token else "—"),
                                        "Token expires": str(r.get("sign_token_expires_at") or "")[:19],
                                    }
                                )
                            st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
                            st.caption("Use **Open sign page** above, or copy any **Sign link** into an email.")
    
def _build_jobs_overview_dataframe(
    jobs_df: pd.DataFrame,
    *,
    customer_name_by_id: dict[str, str],
    estimate_label_map: dict[str, str],
    estimate_quote_by_id: dict[str, str],
    contact_label_by_id: dict[str, str],
    location_by_id: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Augment jobs rows for overview (customer name, estimate labels, Source from ``estimate_id``, linked-quote copy)."""
    if jobs_df.empty:
        return jobs_df
    out = jobs_df.copy()
    if "customer_id" in out.columns:

        def _cust_name_cell(v) -> str:
            if v is None:
                return ""
            try:
                if pd.isna(v):
                    return ""
            except Exception:
                pass
            return customer_name_by_id.get(str(v).strip(), "")

        out["customer_name"] = out["customer_id"].map(_cust_name_cell)
    else:
        out["customer_name"] = ""
    if "estimate_id" in out.columns:

        def _est_label_cell(v) -> str:
            if v is None:
                return ""
            try:
                if pd.isna(v):
                    return ""
            except Exception:
                pass
            return estimate_label_map.get(str(v).strip(), "")

        out["estimate_label"] = out["estimate_id"].map(_est_label_cell)

        def _quote_for_estimate_cell(v) -> str:
            if v is None or str(v).strip() == "":
                return ""
            q = estimate_quote_by_id.get(str(v), "")
            return f"Estimate {q}" if q else ""

        out["Quote (estimate)"] = out["estimate_id"].map(_quote_for_estimate_cell)

        def _source_cell(v) -> str:
            if v is None:
                return "—"
            try:
                if pd.isna(v):
                    return "—"
            except Exception:
                pass
            eid = str(v).strip()
            if not eid:
                return "—"
            q = estimate_quote_by_id.get(eid, "")
            return f"From estimate: {q}" if q else "From estimate"

        out["Source"] = out["estimate_id"].map(_source_cell)
    else:
        out["estimate_label"] = ""
        out["Quote (estimate)"] = ""
        out["Source"] = "—"

    if "customer_contact_id" in out.columns:

        def _contact_cell(v) -> str:
            if v is None:
                return ""
            try:
                if pd.isna(v):
                    return ""
            except Exception:
                pass
            return contact_label_by_id.get(str(v).strip(), "")

        out["Contact"] = out["customer_contact_id"].map(_contact_cell)
    else:
        out["Contact"] = ""

    try:
        from services.customer_locations import location_display_name_city_state
    except ImportError:
        from app.services.customer_locations import location_display_name_city_state  # type: ignore

    if "customer_location_id" in out.columns:

        def _loc_cell(v) -> str:
            if v is None:
                return ""
            try:
                if pd.isna(v):
                    return ""
            except Exception:
                pass
            lid = str(v).strip()
            if not lid:
                return ""
            row = location_by_id.get(lid)
            return location_display_name_city_state(row) if row else ""

        out["Location"] = out["customer_location_id"].map(_loc_cell)
    else:
        out["Location"] = ""

    # User-facing estimate link; ``Source`` is retained for the Source filter and search.
    if "Source" in out.columns:
        out["Linked estimate"] = out["Source"].astype(str)
    else:
        out["Linked estimate"] = "—"
    return out


def _render_job_card_list(
    *,
    df_display: pd.DataFrame,
    job_num_col: str,
    can_edit: bool,
) -> None:
    """Card layout only (mutually exclusive with the desktop table). Tap **Open** to view/edit a job."""
    st.markdown('<span class="ips-job-card-list-anchor"></span>', unsafe_allow_html=True)

    if df_display.empty:
        st.caption("No jobs match these filters.")
        return

    allow_open = bool(can_edit or current_role() == "employee")

    for _, row in df_display.iterrows():
        jid = str(row.get("id") or "").strip()
        if not jid:
            continue
        with st.container(border=True):
            st.markdown('<span class="ips-job-card-anchor"></span>', unsafe_allow_html=True)
            job_num = _job_db_card_text(row.get(job_num_col), "No job #")
            job_name = _job_db_card_text(row.get("job_name"), "Untitled job")
            customer = _job_db_card_text(row.get("customer_name"))
            status = _job_db_card_text(row.get("status"))
            quote = _job_db_card_text(row.get("Quote (estimate)"), "")
            awarded = _job_db_money_cell(row.get("awarded_amount"))
            amount = quote or awarded
            amount_html = (
                f'<span class="ips-job-card-pill">Quote / PO: {html.escape(amount)}</span>'
                if amount
                else ""
            )
            st.markdown(
                f'<p class="ips-job-card-title">{html.escape(job_name)}</p>'
                f'<p class="ips-job-card-meta">'
                f'<strong>Job #</strong> {html.escape(job_num)} &nbsp; '
                f'<strong>Customer</strong> {html.escape(customer)}</p>'
                f"{_job_status_badge_html(status)}"
                f"{amount_html}",
                unsafe_allow_html=True,
            )

            b1, b2, b3 = st.columns([2.2, 1.0, 1.0], gap="small")
            with b1:
                if st.button(
                    "👁 View",
                    key=f"job_card_view_{jid}",
                    use_container_width=True,
                ):
                    clear_selected_ids(TABLE_KEY_JOBS)
                    st.session_state["job_view_mode"] = "view"
                    st.session_state["selected_job_id"] = jid
                    st.session_state.pop("job_mode", None)
                    st.session_state.pop("job_edit_id", None)
                    st.rerun()
            with b2:
                if st.button(
                    "Open",
                    key=f"job_card_open_{jid}",
                    type="primary",
                    use_container_width=True,
                    disabled=not allow_open,
                    help=None if allow_open else "You do not have access to open this job.",
                ):
                    clear_selected_ids(TABLE_KEY_JOBS)
                    st.session_state["job_view_mode"] = "edit"
                    st.session_state["selected_job_id"] = jid
                    st.session_state["job_mode"] = "edit"
                    st.session_state["job_edit_id"] = jid
                    st.session_state.pop("job_number_manual_input", None)
                    st.rerun()
            with b3:
                del_help = (
                    "Only admin or pm can delete jobs."
                    if not can_edit
                    else "Delete this job (blocked if costing data exists)."
                )
                if st.button(
                    "🗑",
                    key=f"job_card_del_{jid}",
                    disabled=not can_edit,
                    use_container_width=True,
                    help=del_help,
                ):
                    pending = st.session_state.get(IPS_PENDING_DELETE)
                    if not isinstance(pending, dict):
                        pending = {}
                        st.session_state[IPS_PENDING_DELETE] = pending
                    pending[TABLE_KEY_JOBS] = [jid]
                    st.rerun()


def _filter_jobs_overview_dataframe(
    filtered: pd.DataFrame,
    *,
    selected_customer: str,
    selected_status: str,
    selected_source: str,
    search: str,
    bypass: bool,
) -> pd.DataFrame:
    """Apply customer/status/source/search filters (matches Source cell text for estimate-linked rows)."""
    out = filtered.copy()
    if not bypass:
        if selected_customer != "All" and "customer_name" in out.columns:
            out = out[out["customer_name"].astype(str) == selected_customer]

        if selected_status != "All" and "status" in out.columns:
            out = out[out["status"].astype(str) == selected_status]

        if selected_source != "All" and "Source" in out.columns:
            src_series = out["Source"].astype(str)
            is_from_estimate = src_series.str.contains("From estimate", case=False, na=False)
            if selected_source == "Estimate":
                out = out[is_from_estimate]
            elif selected_source == "Other":
                out = out[~is_from_estimate]

    if search.strip():
        s = search.strip().lower()
        mask = out.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
        out = out[mask.any(axis=1)]
    return out


def _render_job_db_top_bar(
    *,
    can_edit: bool,
    estimates: list[dict[str, Any]],
    estimate_label_map: dict[str, str],
) -> None:
    """Primary actions: create job, refresh, convert from estimate (same rhythm as Estimates top bar)."""
    with st.container(border=True):
        st.markdown(
            '<span class="ips-list-top-anchor ips-job-topbar"></span>',
            unsafe_allow_html=True,
        )
        st.caption(
            "**Create New Job** — standalone work (no estimate). "
            "**Create job from estimate** — converts an approved quote and links the new job."
        )
        c1, c2, c3 = st.columns([1.0, 1.0, 1.45], gap="small")
        with c1:
            if st.button(
                "Create New Job",
                type="primary",
                use_container_width=True,
                disabled=not can_edit,
                key="job_top_create",
            ):
                st.session_state["job_view_mode"] = "create"
                st.session_state["selected_job_id"] = None
                st.session_state["job_mode"] = "add"
                st.session_state.pop("job_edit_id", None)
                st.session_state.pop("job_number_manual_input", None)
                st.rerun()
        with c2:
            if st.button("Refresh", type="secondary", use_container_width=True, key="job_top_refresh"):
                st.rerun()
        with c3:
            if not can_edit:
                st.caption("Sign in as admin or estimator to convert estimates.")
            else:
                ecandidates = [e for e in estimates if e.get("id") is not None and not str(e.get("job_id") or "").strip()]
                if not ecandidates:
                    st.caption("No estimates without a linked job.")
                else:
                    labels = [estimate_label_map.get(str(e.get("id")), str(e.get("id"))) for e in ecandidates]
                    idx_opts = list(range(len(ecandidates)))
                    pick = st.selectbox(
                        "Convert estimate → job",
                        idx_opts,
                        format_func=lambda i: labels[int(i)],
                        key="job_conv_est",
                        label_visibility="visible",
                    )
                    if st.button(
                        "Create job from estimate",
                        type="secondary",
                        use_container_width=True,
                        key="job_conv_go",
                    ):
                        eid = str(ecandidates[int(pick)].get("id") or "")
                        res = create_job_from_estimate(eid)
                        if res.ok:
                            st.success(res.message)
                            st.rerun()
                        else:
                            st.error(res.message)


def _render_job_db_debug_expander(*, jobs: list[dict[str, Any]], admin_read: bool) -> None:
    with st.expander("Database debug & checklist", expanded=False):
        st.write("DEBUG - Job Count:", len(jobs))
        preview = jobs[:12] if jobs else []
        st.write("DEBUG - Jobs Raw (first rows):", preview)
        st.checkbox(
            "Bypass customer / status / source filters (search still applies)",
            key="job_db_bypass_filters",
        )
        try:
            from app.config import settings

            url = (getattr(settings, "supabase_url", "") or "").strip()
            pk = (
                (getattr(settings, "supabase_publishable_key", "") or "").strip()
                or (getattr(settings, "supabase_anon_key", "") or "").strip()
            )
            st.caption(
                f"Supabase URL set: {bool(url)} · Public key set: {bool(pk)} · "
                f"Admin/service reads for this page: {admin_read} · Table: public.jobs"
            )
        except Exception:
            st.caption("Could not read local settings for debug summary.")

        st.caption(
            "If the count is zero but Supabase shows rows: check RLS policies for `authenticated`, "
            "or ensure `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_SECRET_KEY` is set for admin/pm reads."
        )


def render() -> None:
    render_header("Job Database")
    inject_ips_crud_list_styles()
    inject_table_action_styles()
    _inject_job_database_responsive_styles()

    can_edit = current_role() in {"admin", "manager"}
    st.session_state.setdefault("job_db_bypass_filters", True)

    customers: list[dict[str, Any]] = []
    estimates: list[dict[str, Any]] = []
    try:
        customers = list(_fetch_customers_for_job_db() or [])
    except Exception as exc:
        _LOG.exception("Job Database: could not load customers")
        st.error(f"Database error (customers): {exc}")
    try:
        estimates = list(_fetch_estimates_for_job_db() or [])
    except Exception as exc:
        _LOG.exception("Job Database: could not load estimates")
        st.error(f"Database error (estimates): {exc}")

    admin_read = _job_db_admin_read()
    jobs: list[dict[str, Any]] = []
    has_job_number_column = False
    try:
        jobs, has_job_number_column = fetch_jobs_for_job_database(limit=5000, admin_read=admin_read)
    except Exception as exc:
        _LOG.exception("Job Database: fetch_jobs_for_job_database failed")
        st.error(f"Database error (jobs): {exc}")
        try:
            jobs = list(fetch_jobs_with_order_fallback(limit=5000, use_admin=admin_read) or [])
            has_job_number_column = bool(jobs) and any("job_number" in (r or {}) for r in jobs)
            if jobs:
                st.info("Loaded jobs using a relaxed query (typed column list failed).")
        except Exception as exc2:
            _LOG.exception("Job Database: fetch_jobs_with_order_fallback failed")
            st.error(f"Database error (jobs fallback): {exc2}")
            jobs = []
            has_job_number_column = False

    if has_job_number_column:
        jobs = sort_jobs_by_number_then_name(jobs)
    else:
        jobs = sort_jobs_by_name(jobs)

    customer_name_by_id: dict[str, str] = {}
    for c in customers:
        cid = str(c.get("id") or "").strip()
        if cid:
            customer_name_by_id[cid] = str(c.get("customer_name") or "").strip()

    estimate_label_map: dict[str, str] = {}
    for e in estimates:
        eid = str(e.get("id") or "").strip()
        if not eid:
            continue
        ecust = str(e.get("customer_id") or "").strip()
        cn = customer_name_by_id.get(ecust, "")
        estimate_label_map[eid] = f"{e.get('quote_number', '')} | {cn} | {e.get('status', '')}"

    estimate_quote_by_id = {
        str(e.get("id")): str(e.get("quote_number") or "").strip()
        for e in estimates
        if e.get("id") is not None
    }

    contact_label_by_id: dict[str, str] = {}
    try:
        if admin_read:
            ct_rows = fetch_table_admin("customer_contacts", limit=10000, order_by=None)
        else:
            ct_rows = fetch_table("customer_contacts", limit=10000, order_by=None)
        for cr in ct_rows or []:
            rid = str(cr.get("id") or "").strip()
            if rid:
                contact_label_by_id[rid] = contact_option_label(cr)
    except Exception:
        pass

    has_customer_location_column = _jobs_table_has_customer_location_column()
    location_by_id: dict[str, dict[str, Any]] = {}
    if has_customer_location_column:
        try:
            from services.customer_locations import fetch_all_locations_indexed
        except ImportError:
            from app.services.customer_locations import fetch_all_locations_indexed  # type: ignore

        location_by_id = fetch_all_locations_indexed(admin_read=admin_read)

    jobs_df = pd.DataFrame(jobs)

    if "job_view_mode" not in st.session_state:
        st.session_state["job_view_mode"] = "list"
    if "selected_job_id" not in st.session_state:
        st.session_state["selected_job_id"] = None
    _migrate_job_view_mode_from_legacy_session()

    jvm_route = str(st.session_state.get("job_view_mode") or "list").strip().lower()
    sid_route = str(st.session_state.get("selected_job_id") or "").strip()

    if jvm_route == "edit" and not sid_route:
        _clear_job_mode()
        st.rerun()

    if jvm_route == "view" and sid_route:
        job_row = next((j for j in jobs if str(j.get("id")) == sid_route), None)
        if not job_row:
            st.error("That job could not be found.")
            _clear_job_mode()
            st.rerun()
        est_row: dict[str, Any] | None = None
        if job_row.get("estimate_id"):
            eid_est = str(job_row.get("estimate_id"))
            est_row = next((e for e in estimates if str(e.get("id")) == eid_est), None)
            if not est_row:
                est_row = _fetch_estimate_row_by_id(eid_est)
        _inject_job_detail_view_page_css()
        try:
            from app.pages.job_database_detail_view import render_job_database_detail_view_page as _render_jd_detail
        except ImportError:
            from pages.job_database_detail_view import render_job_database_detail_view_page as _render_jd_detail  # type: ignore

        def _clear_job_detail_view() -> None:
            st.session_state["job_view_mode"] = "list"
            st.session_state["selected_job_id"] = None
            st.session_state.pop("job_mode", None)
            st.session_state.pop("job_edit_id", None)

        def _goto_job_edit_from_detail(jid: str) -> None:
            st.session_state["job_view_mode"] = "edit"
            st.session_state["selected_job_id"] = str(jid)
            st.session_state["job_mode"] = "edit"
            st.session_state["job_edit_id"] = str(jid)
            st.session_state.pop("job_number_manual_input", None)

        _render_jd_detail(
            job_row=job_row,
            has_job_number_column=has_job_number_column,
            has_customer_location_column=has_customer_location_column,
            customers=customers,
            customer_name_by_id=customer_name_by_id,
            estimate_label_map=estimate_label_map,
            estimate_quote_by_id=estimate_quote_by_id,
            estimate_detail=est_row,
            location_by_id=location_by_id,
            contact_label_by_id=contact_label_by_id,
            can_edit=can_edit,
            admin_read=admin_read,
            on_clear_view=_clear_job_detail_view,
            on_sync_edit=_goto_job_edit_from_detail,
        )
        st.stop()

    _sync_job_mode_from_view_state()

    jvm_panel = str(st.session_state.get("job_view_mode") or "list").strip().lower()
    sid_panel = str(st.session_state.get("selected_job_id") or st.session_state.get("job_edit_id") or "").strip()
    panel_open = bool(
        (jvm_panel == "create" and can_edit)
        or (jvm_panel == "edit" and (can_edit or current_role() == "employee") and sid_panel)
    )

    if panel_open:
        st.markdown('<span class="ips-job-detail-view-anchor"></span>', unsafe_allow_html=True)
        mode = "add" if jvm_panel == "create" else "edit"
        selected_job: dict[str, Any] | None = None
        estimate_detail: dict[str, Any] | None = None
        if mode == "edit":
            edit_id = st.session_state.get("selected_job_id") or st.session_state.get("job_edit_id")
            if edit_id:
                selected_job = next((j for j in jobs if str(j.get("id")) == str(edit_id)), None)
            if not selected_job:
                st.error("Selected job could not be loaded. It may have been deleted.")
                _clear_job_mode()
                st.rerun()
            if selected_job is not None and selected_job.get("estimate_id"):
                eid_est = str(selected_job.get("estimate_id"))
                estimate_detail = next(
                    (e for e in estimates if str(e.get("id")) == eid_est),
                    None,
                )
                if not estimate_detail:
                    estimate_detail = _fetch_estimate_row_by_id(eid_est)

        if st.button("← Back to Jobs", type="secondary", key="job_db_back_to_list"):
            _clear_job_mode()
            st.rerun()

        if mode == "add":
            st.markdown("## Add job", unsafe_allow_html=True)
            st.caption("Standalone or estimate-linked — use the form below.")
        elif selected_job:
            jt = str(selected_job.get("job_name") or "").strip() or "Untitled job"
            jn = _job_detail_display_number(selected_job, has_job_number_column=has_job_number_column)
            st.markdown(
                f"<h2 style='margin:0 0 0.25rem 0;color:#111827;'>{html.escape(jt)}</h2>",
                unsafe_allow_html=True,
            )
            if jn:
                st.caption(f"Job # {jn}")

        _render_job_form_panel(
            mode=str(mode),
            can_edit=can_edit,
            selected_job=selected_job,
            jobs=jobs,
            has_job_number_column=has_job_number_column,
            has_customer_location_column=has_customer_location_column,
            customers=customers,
            estimates=estimates,
            customer_name_by_id=customer_name_by_id,
            estimate_label_map=estimate_label_map,
            estimate_quote_by_id=estimate_quote_by_id,
            estimate_detail=estimate_detail,
            show_main_heading=False,
        )
        return

    render_crud_list_subtitle(
        "Search and maintain jobs — standalone or estimate-linked — and keep customer contacts aligned."
    )
    st.caption(
        "**Standalone jobs** use **Create New Job** (no quote). **Estimate-linked jobs** use **Convert estimate → job** "
        "or **Job Received** on the Estimates list once the quote is customer-approved."
    )

    _render_job_db_top_bar(can_edit=can_edit, estimates=estimates, estimate_label_map=estimate_label_map)
    _render_job_db_debug_expander(jobs=jobs, admin_read=admin_read)

    st.markdown("### Jobs overview")
    st.caption(
        "**Source** shows estimate links; **Quote (estimate)**, **customer**, **Contact**, and **Location** summarize linked data."
    )

    with st.container():
        if jobs_df.empty:
            st.warning("No jobs found in database.")
            if can_edit and not panel_open:
                with st.container(border=True):
                    st.markdown(
                        '<span class="ips-list-top-anchor ips-job-topbar"></span>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Create New Job",
                        key="job_add_btn_empty",
                        type="primary",
                        use_container_width=True,
                    ):
                        st.session_state["job_view_mode"] = "create"
                        st.session_state["selected_job_id"] = None
                        st.session_state["job_mode"] = "add"
                        st.session_state.pop("job_edit_id", None)
                        st.session_state.pop("job_number_manual_input", None)
                        st.rerun()
                return
            if not panel_open:
                return

            st.caption("Use **Create New Job** in the top bar, or **Convert estimate → job**.")
        else:
            jobs_df = _build_jobs_overview_dataframe(
                jobs_df,
                customer_name_by_id=customer_name_by_id,
                estimate_label_map=estimate_label_map,
                estimate_quote_by_id=estimate_quote_by_id,
                contact_label_by_id=contact_label_by_id,
                location_by_id=location_by_id,
            )

            with st.container(border=True):
                st.markdown(
                    '<span class="ips-list-top-anchor ips-job-filter-anchor"></span>',
                    unsafe_allow_html=True,
                )
                st.markdown("##### Filters & search")
                f1, f2, f3, f4 = st.columns([1.05, 1.05, 2.35, 1.0], gap="small")
                customer_names = sorted(
                    [c.get("customer_name", "") for c in customers if str(c.get("customer_name", "")).strip()]
                )
                with f1:
                    selected_customer = st.selectbox(
                        "Filter Customer",
                        ["All"] + customer_names,
                        disabled="customer_id" not in jobs_df.columns,
                        key="job_filt_customer",
                    )
                with f2:
                    selected_status = st.selectbox(
                        "Filter Status",
                        ["All"] + JOB_STATUSES,
                        disabled="status" not in jobs_df.columns,
                        key="job_filt_status",
                    )
                with f3:
                    _search_hint = (
                        "Source, quote, contact, location, job_number, job_name, customer, status, …"
                        if has_job_number_column
                        else "Source, quote, contact, location, job_name, customer, status, …"
                    )
                    search = st.text_input(
                        "Search Jobs",
                        placeholder=_search_hint,
                        key="job_filt_search",
                    )
                with f4:
                    selected_source = st.selectbox(
                        "Source",
                        ["All", "Estimate", "Other"],
                        disabled="Source" not in jobs_df.columns,
                        help="Estimate = rows linked to an estimate (same rule as the **Linked estimate** column).",
                        key="job_filt_source",
                    )

            bypass = st.session_state.get("job_db_bypass_filters", True)
            filtered = _filter_jobs_overview_dataframe(
                jobs_df,
                selected_customer=selected_customer,
                selected_status=selected_status,
                selected_source=selected_source,
                search=search,
                bypass=bypass,
            )

            show_cols: list[str] = []
            if has_job_number_column and "job_number" in filtered.columns:
                show_cols.append("job_number")
            for c in (
                "Linked estimate",
                "job_name",
                "customer_name",
                "Location",
                "source_type",
                "Quote (estimate)",
                "Contact",
                "status",
            ):
                if c in filtered.columns and c not in show_cols:
                    show_cols.append(c)
            show_cols.extend(
                [c for c in JOBS_JOB_DATABASE_OVERVIEW_DISPLAY_ORDER if c in filtered.columns and c not in show_cols]
            )
            df_display = filtered.copy()
            df_display = df_display.drop(columns=[c for c in HIDDEN_COLUMNS if c in df_display.columns], errors="ignore")
            visible_cols = _job_db_visible_table_columns([c for c in show_cols if c in df_display.columns])

            ensure_narrow_viewport_detected()
            if "job_db_view_mode_radio" not in st.session_state:
                st.session_state["job_db_view_mode_radio"] = (
                    "Cards" if st.session_state.get(IPS_VIEWPORT_NARROW_KEY) else "Table"
                )

            picked: list[str] = []
            job_num_col = "job_number" if has_job_number_column and "job_number" in df_display.columns else "job_id"
            if job_num_col not in df_display.columns:
                job_num_col = "id"

            with st.container(border=True):
                st.markdown(
                    '<span class="ips-list-top-anchor ips-job-joblist-section-anchor"></span>',
                    unsafe_allow_html=True,
                )
                st.markdown("##### Job list")
                st.radio(
                    "View mode",
                    ["Table", "Cards"],
                    horizontal=True,
                    key="job_db_view_mode_radio",
                    help="**Table** — checkboxes and row delete. **Cards** — tap Open on a job (better on tablet/phone).",
                )
                use_table = st.session_state.get("job_db_view_mode_radio", "Table") == "Table"
                if use_table:
                    st.caption(
                        "Checkbox on the **left**; **👁** opens read-only job details; **Del** deletes one job (same rules as bulk). "
                        "Jobs with labor, materials, equipment, or PO expenses cannot be deleted."
                    )
                else:
                    st.caption(
                        "**View** — read-only job portal. **Open** — edit job (admin/manager/employee). "
                        "Use **🗑** on a card for a single-job delete, or switch to **Table** for checkbox selection."
                    )

                if "id" not in df_display.columns:
                    st.dataframe(df_display[visible_cols], use_container_width=True, hide_index=True)
                elif use_table:
                    st.markdown(
                        '<span class="ips-job-desktop-table-anchor"></span>',
                        unsafe_allow_html=True,
                    )
                    inject_table_action_styles()
                    with st.container():
                        st.markdown(
                            '<span class="ips-job-table-scroll-anchor"></span>',
                            unsafe_allow_html=True,
                        )
                        # Match Estimates table rhythm: fixed columns + explicit weights.

                        # Visible order (exact):
                        # Blank | Job Number | Job Name | Customer | Location | Contact | Status | Linked Estimate | Quote/PO | Awarded | View | Del
                        col_weights = [
                            0.40,  # checkbox
                            1.00,  # job number
                            2.30,  # job name
                            1.70,  # customer
                            1.25,  # location
                            1.25,  # contact
                            0.95,  # status
                            1.10,  # linked estimate
                            1.00,  # quote/po
                            1.05,  # awarded amount
                            0.48,  # view
                            0.50,  # delete
                        ]

                        head = st.columns(col_weights, gap="medium")
                        with head[0]:
                            st.caption(" ")
                        with head[1]:
                            st.caption("Job #")
                        with head[2]:
                            st.caption("Job Name")
                        with head[3]:
                            st.caption("Customer")
                        with head[4]:
                            st.caption("Location")
                        with head[5]:
                            st.caption("Contact")
                        with head[6]:
                            st.caption("Status")
                        with head[7]:
                            st.caption("Linked Estimate")
                        with head[8]:
                            st.caption("Quote / PO")
                        with head[9]:
                            st.caption("Awarded")
                        with head[10]:
                            st.caption("View")
                        with head[11]:
                            st.caption("Del")

                        for _, row in df_display.iterrows():
                            jid = str(row.get("id") or "").strip()
                            if not jid:
                                continue
                            rc = st.columns(col_weights, gap="medium")
                            with rc[0]:
                                ck = f"job_list_pick_{jid}"
                                if ck not in st.session_state:
                                    st.session_state[ck] = jid in get_selected_ids(TABLE_KEY_JOBS)
                                if st.checkbox("", key=ck, label_visibility="collapsed"):
                                    picked.append(jid)
                            with rc[1]:
                                _render_short_cell_with_tooltip(rc[1], row.get(job_num_col), max_len=14)
                            with rc[2]:
                                _render_job_db_job_name_cell(rc[2], row.get("job_name"))
                            with rc[3]:
                                _render_short_cell_with_tooltip(rc[3], row.get("customer_name"), max_len=28)
                            with rc[4]:
                                _render_short_cell_with_tooltip(rc[4], row.get("Location"), max_len=24)
                            with rc[5]:
                                _render_short_cell_with_tooltip(rc[5], row.get("Contact"), max_len=24)
                            with rc[6]:
                                _render_short_cell_with_tooltip(rc[6], row.get("status"), max_len=18)
                            with rc[7]:
                                _render_short_cell_with_tooltip(rc[7], row.get("Linked estimate"), max_len=18)
                            with rc[8]:
                                # Quote (estimate) is the current visible “quote/po” signal in this UI.
                                _render_short_cell_with_tooltip(rc[8], row.get("Quote (estimate)"), max_len=18)
                            with rc[9]:
                                raw_aw = row.get("awarded_amount")
                                amt = _job_db_money_cell(raw_aw)
                                aw_title = ""
                                if raw_aw is not None and str(raw_aw).strip() != "":
                                    aw_title = f' title="{html.escape(str(raw_aw).strip(), quote=True)}"'
                                rc[9].markdown(
                                    f'<span class="ips-job-list-cell ips-job-money-cell"{aw_title} '
                                    f'style="color:#111827;">{html.escape(amt)}</span>',
                                    unsafe_allow_html=True,
                                )

                            with rc[10]:
                                if st.button(
                                    "👁",
                                    key=f"job_row_view_{jid}",
                                    use_container_width=True,
                                    help="View job details",
                                ):
                                    clear_selected_ids(TABLE_KEY_JOBS)
                                    st.session_state["job_view_mode"] = "view"
                                    st.session_state["selected_job_id"] = jid
                                    st.session_state.pop("job_mode", None)
                                    st.session_state.pop("job_edit_id", None)
                                    st.rerun()

                            del_help = (
                                "Only admin or pm can delete jobs."
                                if not can_edit
                                else "Delete this job (blocked if costing data exists)."
                            )
                            with rc[11]:
                                if st.button(
                                    "🗑",
                                    key=f"job_row_del_{jid}",
                                    disabled=not can_edit,
                                    use_container_width=True,
                                    help=del_help,
                                ):
                                    pending = st.session_state.get(IPS_PENDING_DELETE)
                                    if not isinstance(pending, dict):
                                        pending = {}
                                        st.session_state[IPS_PENDING_DELETE] = pending
                                    pending[TABLE_KEY_JOBS] = [jid]
                                    st.rerun()
                    set_selected_ids(TABLE_KEY_JOBS, picked)
                else:
                    clear_selected_ids(TABLE_KEY_JOBS)
                    _render_job_card_list(
                        df_display=df_display,
                        job_num_col=job_num_col,
                        can_edit=can_edit,
                    )

            use_table = st.session_state.get("job_db_view_mode_radio", "Table") == "Table"
            sel_ids = picked if ("id" in filtered.columns and use_table) else []
            n_sel = len(sel_ids)
            one = n_sel == 1
            none = n_sel == 0

            if "id" in filtered.columns and use_table:
                with st.container(border=True):
                    st.markdown(
                        '<span class="ips-ta-bar-anchor ips-job-action-bar-anchor"></span>',
                        unsafe_allow_html=True,
                    )
                    left, b1, b2 = st.columns([1.35, 1, 1], gap="small")
                    with left:
                        st.markdown(
                            f'<span class="ips-ta-summary"><span class="ips-ta-num">{n_sel}</span> selected</span>',
                            unsafe_allow_html=True,
                        )
                    with b1:
                        if st.button(
                            "Edit",
                            key="job_edit_btn",
                            type="secondary",
                            use_container_width=True,
                            disabled=not (can_edit or current_role() == "employee"),
                        ):
                            if not one:
                                if none:
                                    st.warning("Please select a job first.")
                                else:
                                    st.warning("Please select exactly one job to edit.")
                            else:
                                st.session_state["job_view_mode"] = "edit"
                                st.session_state["selected_job_id"] = str(sel_ids[0])
                                st.session_state["job_mode"] = "edit"
                                st.session_state["job_edit_id"] = str(sel_ids[0])
                                st.session_state.pop("job_number_manual_input", None)
                                st.rerun()
                    with b2:
                        if st.button(
                            "Delete",
                            key="job_delete_btn",
                            type="secondary",
                            use_container_width=True,
                            disabled=not can_edit,
                        ):
                            if none:
                                st.warning("Please select a job first.")
                            else:
                                pending = st.session_state.get(IPS_PENDING_DELETE)
                                if not isinstance(pending, dict):
                                    pending = {}
                                    st.session_state[IPS_PENDING_DELETE] = pending
                                pending[TABLE_KEY_JOBS] = list(sel_ids)
                                st.rerun()

            pend = st.session_state.get(IPS_PENDING_DELETE) or {}
            if isinstance(pend, dict) and pend.get(TABLE_KEY_JOBS):
                pend_ids = [str(x) for x in pend.get(TABLE_KEY_JOBS) or [] if str(x).strip()]
                if pend_ids:
                    with st.container(border=True):
                        st.warning(
                            f"Delete **{len(pend_ids)}** job(s)? This cannot be undone. "
                            "Jobs with **costing data** (time, materials, equipment, or PO expenses) cannot be deleted."
                        )
                        dc1, dc2 = st.columns(2, gap="small")
                        with dc1:
                            if st.button(
                                "Confirm delete",
                                type="primary",
                                use_container_width=True,
                                key="job_db_confirm_delete",
                            ):
                                n_ok = 0
                                for jid in pend_ids:
                                    try:
                                        delete_job_row_if_no_costing(str(jid), admin_read=admin_read)
                                        n_ok += 1
                                    except RuntimeError as re:
                                        st.error(f"{str(jid)[:8]}… — {re!s}")
                                    except Exception as exc:
                                        st.error(f"Could not delete job {jid}: {exc}")
                                pend.pop(TABLE_KEY_JOBS, None)
                                clear_selected_ids(TABLE_KEY_JOBS)
                                _clear_job_mode()
                                if n_ok:
                                    st.success(f"Deleted {n_ok} job(s).")
                                st.rerun()
                        with dc2:
                            if st.button("Cancel", use_container_width=True, key="job_db_cancel_delete"):
                                pend.pop(TABLE_KEY_JOBS, None)
                                st.rerun()
