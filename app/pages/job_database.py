from __future__ import annotations

import contextlib
import html
import logging
from typing import Any

_LOG = logging.getLogger(__name__)

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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


def short_text(val: Any, max_len: int = 40) -> str:
    txt = str(val or "").strip()
    return txt[:max_len] + ("…" if len(txt) > max_len else "")


def _render_job_db_job_name_cell(container: Any, raw: Any, *, max_len: int = 40) -> None:
    """Truncate long job names for the overview table; full value in tooltip (display only)."""
    full = _job_db_cell_str(raw)
    display = short_text(full, max_len=max_len)
    if not full:
        container.markdown(
            '<span class="ips-job-list-cell" style="color:#111827;">—</span>',
            unsafe_allow_html=True,
        )
    elif len(full) > max_len:
        container.markdown(
            f'<span class="ips-job-list-cell" title="{html.escape(full, quote=True)}" '
            f'style="color:#111827;">{html.escape(display)}</span>',
            unsafe_allow_html=True,
        )
    else:
        container.markdown(
            f'<span class="ips-job-list-cell" style="color:#111827;">{html.escape(display)}</span>',
            unsafe_allow_html=True,
        )


def _render_short_cell_with_tooltip(container: Any, value: Any, max_len: int = 20) -> None:
    txt = str(value or "").strip()
    short = txt[:max_len] + ("…" if len(txt) > max_len else "")
    if not txt:
        container.markdown(
            '<span class="ips-job-list-cell" style="color:#111827;">—</span>',
            unsafe_allow_html=True,
        )
        return
    container.markdown(
        f"<span class='ips-job-list-cell' title='{html.escape(txt, quote=True)}' "
        "style='color:#111827;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"
        f"{html.escape(short)}</span>",
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

JOB_DB_RESPONSIVE_STYLES_KEY = "job_db_responsive_styles_injected_v7"
JOB_DB_TABLET_MOBILE_BREAKPOINT_PX = 1100
JOB_DB_TABLET_MOBILE_KEY = "job_db_is_tablet_or_mobile"
JOB_DB_VIEWPORT_QUERY_PARAM = "ips_job_vp"
JOB_DB_OPEN_QUERY_PARAM = "job_open_id"
_JOB_DB_VIEWPORT_SCRIPT_SENT_KEY = "_job_db_viewport_detect_script_sent"

# Shown in the Job Database grid; kept on the DataFrame for filters / search / logic.
_JOB_DB_COLUMNS_HIDDEN_FROM_TABLE: frozenset[str] = frozenset(
    {"customer_id", "estimate_label", "Source"}
) | HIDDEN_COLUMNS


def _job_db_visible_table_columns(columns: list[str]) -> list[str]:
    return [c for c in columns if c not in _JOB_DB_COLUMNS_HIDDEN_FROM_TABLE]


def _job_db_width_is_tablet_or_mobile(width: Any) -> bool:
    try:
        return int(float(str(width).strip())) <= JOB_DB_TABLET_MOBILE_BREAKPOINT_PX
    except Exception:
        return False


def _ensure_job_db_viewport_detected() -> bool:
    """Classify this page at the 1100px job-list breakpoint for Python rendering."""
    try:
        if JOB_DB_VIEWPORT_QUERY_PARAM in st.query_params:
            raw = st.query_params.get(JOB_DB_VIEWPORT_QUERY_PARAM, "0")
            if isinstance(raw, list):
                raw = raw[0] if raw else "0"
            st.session_state[JOB_DB_TABLET_MOBILE_KEY] = str(raw).strip() == "1"
            try:
                del st.query_params[JOB_DB_VIEWPORT_QUERY_PARAM]
            except Exception:
                pass
    except Exception:
        pass

    current_flag = st.session_state.get(JOB_DB_TABLET_MOBILE_KEY)
    if current_flag is None or not st.session_state.get(_JOB_DB_VIEWPORT_SCRIPT_SENT_KEY):
        st.session_state[_JOB_DB_VIEWPORT_SCRIPT_SENT_KEY] = True
        known = "unknown" if current_flag is None else ("1" if bool(current_flag) else "0")
        components.html(
            f"""
<script>
(function () {{
  try {{
    var topWindow = window.top || window;
    var url = new URL(topWindow.location.href);
    if (url.searchParams.get("{JOB_DB_VIEWPORT_QUERY_PARAM}") != null) return;
    var width = topWindow.innerWidth || window.innerWidth || 1200;
    var next = width <= {JOB_DB_TABLET_MOBILE_BREAKPOINT_PX} ? "1" : "0";
    if ("{known}" !== "unknown" && "{known}" === next) return;
    url.searchParams.set("{JOB_DB_VIEWPORT_QUERY_PARAM}", next);
    topWindow.location.replace(url.toString());
  }} catch (e) {{}}
}})();
</script>
            """,
            height=0,
        )

    return bool(st.session_state.get(JOB_DB_TABLET_MOBILE_KEY, False))


def _consume_job_card_open_request(*, jobs: list[dict[str, Any]], can_open: bool) -> None:
    try:
        raw = st.query_params.get(JOB_DB_OPEN_QUERY_PARAM)
        if isinstance(raw, list):
            raw = raw[0] if raw else ""
        jid = str(raw or "").strip()
        if JOB_DB_OPEN_QUERY_PARAM in st.query_params:
            del st.query_params[JOB_DB_OPEN_QUERY_PARAM]
    except Exception:
        jid = ""
    if not jid or not can_open:
        return
    valid_ids = {str(j.get("id") or "").strip() for j in jobs}
    if jid not in valid_ids:
        return
    _open_job_detail(jid)


def _inject_job_database_responsive_styles() -> None:
    """Jobs page tablet/mobile layout overrides. Keeps desktop split/table unchanged."""
    if st.session_state.get(JOB_DB_RESPONSIVE_STYLES_KEY):
        return
    st.session_state[JOB_DB_RESPONSIVE_STYLES_KEY] = True
    st.markdown(
        """
        <style>
        .ips-job-card-list-note {
            color: #64748b !important;
            font-size: 0.82rem;
            margin: 0.15rem 0 0.45rem;
        }
        .ips-job-card-title {
            color: #111827 !important;
            display: block;
            font-size: 1.05rem;
            font-weight: 700;
            line-height: 1.25;
            margin: 0 0 0.1rem 0;
            overflow-wrap: anywhere;
        }
        .ips-job-card-meta {
            color: #4b5563 !important;
            display: block;
            font-size: 0.92rem;
            line-height: 1.45;
            margin: 0.15rem 0 0.4rem;
            overflow-wrap: anywhere;
        }
        .ips-job-card-open {
            color: inherit !important;
            cursor: pointer;
            display: block;
            min-height: 92px;
            padding: 0;
            text-decoration: none !important;
            -webkit-tap-highlight-color: rgba(37, 99, 235, 0.12);
        }
        .ips-job-card-open:active,
        .ips-job-card-open:focus,
        .ips-job-card-open:hover {
            text-decoration: none !important;
        }
        .ips-job-card-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.3rem;
            margin-top: 0.35rem;
        }
        .ips-job-card-open-hint {
            color: #2563eb !important;
            display: block;
            font-size: 0.82rem;
            font-weight: 700;
            margin-top: 0.55rem;
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
        .ips-job-card-open:focus-visible {
            border-radius: 10px;
            outline: 3px solid #93c5fd;
            outline-offset: 4px;
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
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-list-anchor) h5,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-list-anchor) .stMarkdown,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-list-anchor) .stMarkdown p,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) .stMarkdown,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) .stMarkdown p {
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-list-anchor) {
            display: none;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) {
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 12px !important;
            cursor: pointer;
            margin-bottom: 0.65rem !important;
            padding: 1rem !important;
            position: relative !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
            transition: background-color 160ms ease, border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor):hover,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor):focus-within,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor):has(.stButton > button[kind="primary"]:active) {
            background: #eff6ff !important;
            border-color: #2563eb !important;
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.16) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor):has(.stButton > button[kind="primary"]:active) {
            transform: scale(0.995);
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) .stButton > button[kind="primary"] {
            cursor: pointer !important;
            height: 100% !important;
            inset: 0 !important;
            min-height: 100% !important;
            opacity: 0 !important;
            position: absolute !important;
            width: 100% !important;
            z-index: 2 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) .stButton > button[kind="secondary"] {
            position: relative !important;
            z-index: 3 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) .stButton > button,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) .stButton > button,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) .stButton > button {
            min-height: 48px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="input"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="base-input"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) textarea,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="input"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="base-input"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stFileUploader"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) textarea {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] *,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] *,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stFileUploader"] * {
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) textarea,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] > div {
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
            color: inherit !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"] p {
            color: #374151 !important;
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
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="column"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-testid="column"] {
            min-width: 0 !important;
        }
        /* Tablet / iPad: list uses cards; job detail is a separate full-width view (no split layout). */
        @media (max-width: 1100px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) {
                display: none !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-list-anchor) {
                display: block !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-action-bar-anchor) {
                display: none !important;
            }
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
    """Columns for labels + optional scope; fall back if a column is missing."""
    if _job_db_admin_read():
        for cols in (
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
    st.session_state.pop("job_mode", None)
    st.session_state.pop("job_edit_id", None)
    st.session_state.pop("selected_job_id", None)
    if st.session_state.get("page") == "job_detail":
        st.session_state.pop("page", None)
    st.session_state.pop("job_number_manual_input", None)


def _open_job_detail(job_id: str) -> None:
    jid = str(job_id or "").strip()
    if not jid:
        return
    st.session_state["selected_job_id"] = jid
    st.session_state["page"] = "job_detail"
    st.session_state["job_mode"] = "edit"
    st.session_state["job_edit_id"] = jid
    st.session_state.pop("job_number_manual_input", None)
    st.rerun()


def _sync_job_detail_route() -> None:
    if st.session_state.get("page") != "job_detail":
        return
    jid = str(st.session_state.get("selected_job_id") or "").strip()
    if not jid:
        return
    st.session_state["job_mode"] = "edit"
    st.session_state["job_edit_id"] = jid


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
            if mode == "edit" and selected_job and selected_job.get("estimate_id"):
                st.markdown("#### Estimate source")
                _eid = str(selected_job.get("estimate_id"))
                _eq = str(
                    estimate_quote_by_id.get(_eid)
                    or (estimate_detail or {}).get("quote_number")
                    or ""
                ).strip()
                _est = estimate_detail or {}
                _st = str(_est.get("status") or "").strip()
                _cust = _customer_display_name_for_id(
                    _est.get("customer_id"),
                    customers,
                    customer_name_by_id,
                )
                _scope = _text_snippet(str(_est.get("scope_of_work") or ""))
                with st.container(border=True):
                    st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
                    line_parts: list[str] = []
                    if _eq:
                        line_parts.append(f"Source estimate **{_eq}**")
                    else:
                        line_parts.append(f"Source estimate id `{_eid[:8]}…`")
                    if _st:
                        line_parts.append(f"estimate status **{_st}**")
                    if _cust:
                        line_parts.append(f"customer **{_cust}**")
                    st.markdown("**Source** · " + " · ".join(line_parts), unsafe_allow_html=True)
                    st.caption("This job originated from an estimate (jobs.estimate_id is set).")
                    if _scope:
                        st.caption("Scope (from estimate)")
                        st.markdown(
                            f"<div style='white-space:pre-wrap;font-size:0.88rem'>{html.escape(_scope)}</div>",
                            unsafe_allow_html=True,
                        )
    
            customer_options: dict[str, str] = {}
            for c in customers:
                nm = str(c.get("customer_name") or "").strip()
                cid = str(c.get("id") or "").strip()
                if nm and cid:
                    customer_options[nm] = cid
    
            estimate_options: dict[str, Any] = {"": None}
            for e in estimates:
                eid = str(e.get("id") or "").strip()
                if not eid:
                    continue
                lab = estimate_label_map.get(eid)
                if lab:
                    estimate_options[lab] = eid
            if mode == "edit" and selected_job and selected_job.get("estimate_id"):
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
    
            st.markdown("#### Status & linked estimate")
            if mode == "add":
                st.caption("*Linked estimate* is optional — leave the first row selected for a job with no quote.")
            c5, c6 = st.columns(2, gap="small")
            status_options = list(JOB_STATUSES)
            current_status = str(current_value("status", "Draft") or "Draft").strip() or "Draft"
            if current_status not in status_options:
                status_options = status_options + [current_status]
            status_idx = status_options.index(current_status)
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
    can_open: bool,
    can_delete: bool,
) -> None:
    st.markdown('<span class="ips-job-card-list-anchor"></span>', unsafe_allow_html=True)
    st.markdown("##### Job list")
    st.markdown(
        '<p class="ips-job-card-list-note">Tap a job card to open details. Delete is a separate action.</p>',
        unsafe_allow_html=True,
    )

    if df_display.empty:
        st.caption("No jobs match these filters.")
        return

    for _, row in df_display.iterrows():
        jid = str(row.get("id") or "").strip()
        if not jid:
            continue
        with st.container(border=True):
            st.markdown(
                '<span class="ips-job-card-anchor"></span>',
                unsafe_allow_html=True,
            )
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
                f'<div class="ips-job-card-open" '
                f'aria-label="Open job {html.escape(job_num, quote=True)} {html.escape(job_name, quote=True)}">'
                f'<span class="ips-job-card-title">{html.escape(job_name)}</span>'
                f'<span class="ips-job-card-meta">'
                f'<strong>Job #</strong> {html.escape(job_num)} &nbsp; '
                f'<strong>Customer</strong> {html.escape(customer)}</span>'
                f'<span class="ips-job-card-badges">{_job_status_badge_html(status)}{amount_html}</span>'
                f'<span class="ips-job-card-open-hint">Tap to open</span>'
                "</div>",
                unsafe_allow_html=True,
            )
            if st.button(
                f"Open {job_name}",
                key=f"open_{jid}",
                type="primary",
                use_container_width=True,
                disabled=not can_open,
                help=f"Open {job_name}",
            ):
                _open_job_detail(jid)
            if can_delete:
                if st.button(
                    "Delete",
                    key=f"job_card_del_{jid}",
                    type="secondary",
                    use_container_width=False,
                    help="Delete this job (blocked if costing data exists).",
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
    is_tablet_or_mobile = _ensure_job_db_viewport_detected()

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

    _consume_job_card_open_request(
        jobs=jobs,
        can_open=can_edit or current_role() == "employee",
    )
    _sync_job_detail_route()

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

    mode = st.session_state.get("job_mode")
    panel_open = bool(
        mode in ("add", "edit") and (can_edit or (mode == "edit" and current_role() == "employee"))
    )

    if panel_open:
        st.markdown('<span class="ips-job-detail-view-anchor"></span>', unsafe_allow_html=True)
        selected_job: dict[str, Any] | None = None
        estimate_detail: dict[str, Any] | None = None
        if mode == "edit":
            edit_id = st.session_state.get("job_edit_id")
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

            picked: list[str] = []
            if not is_tablet_or_mobile:
                with st.container(border=True):
                    st.markdown(
                        '<span class="ips-list-top-anchor ips-job-desktop-table-anchor"></span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown("##### Job list")
                    st.caption(
                        "Checkbox on the **left**; **Del** deletes one job (same rules as bulk). "
                        "Jobs with labor, materials, equipment, or PO expenses cannot be deleted."
                    )
                    if "id" not in df_display.columns:
                        st.dataframe(df_display[visible_cols], use_container_width=True, hide_index=True)
                    else:
                        inject_table_action_styles()
                        # Match Estimates table rhythm: fixed columns + explicit weights.
                        job_num_col = (
                            "job_number" if has_job_number_column and "job_number" in df_display.columns else "job_id"
                        )
                        if job_num_col not in df_display.columns:
                            job_num_col = "id"

                        # Visible order (exact):
                        # Blank | Job Number | Job Name | Customer | Location | Contact | Status | Linked Estimate | Quote/PO | Awarded | Del
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
                            0.50,  # delete
                        ]

                        head = st.columns(col_weights)
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
                            st.caption("Del")

                        for _, row in df_display.iterrows():
                            jid = str(row.get("id") or "").strip()
                            if not jid:
                                continue
                            rc = st.columns(col_weights)
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
                                # Quote (estimate) is the current visible quote/po signal in this UI.
                                _render_short_cell_with_tooltip(rc[8], row.get("Quote (estimate)"), max_len=18)
                            with rc[9]:
                                amt = _job_db_money_cell(row.get("awarded_amount"))
                                rc[9].markdown(
                                    f'<span class="ips-job-list-cell" style="color:#111827;">{html.escape(amt)}</span>',
                                    unsafe_allow_html=True,
                                )

                            del_help = (
                                "Only admin or pm can delete jobs."
                                if not can_edit
                                else "Delete this job (blocked if costing data exists)."
                            )
                            with rc[10]:
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

            if is_tablet_or_mobile:
                if "id" not in df_display.columns:
                    st.warning("Job cards require job IDs; reload after the jobs table finishes syncing.")
                else:
                    with st.container(border=True):
                        job_num_col = (
                            "job_number" if has_job_number_column and "job_number" in df_display.columns else "job_id"
                        )
                        if job_num_col not in df_display.columns:
                            job_num_col = "id"
                        _render_job_card_list(
                            df_display=df_display,
                            job_num_col=job_num_col,
                            can_open=can_edit or current_role() == "employee",
                            can_delete=can_edit,
                        )

            sel_ids = picked if "id" in filtered.columns else []
            n_sel = len(sel_ids)
            one = n_sel == 1
            none = n_sel == 0

            if not is_tablet_or_mobile:
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
