from __future__ import annotations

import html
from datetime import date, datetime, timedelta, timezone
from typing import NamedTuple

import pandas as pd
import streamlit as st

try:
    from mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected
except ImportError:
    from app.mobile_ui import IPS_VIEWPORT_NARROW_KEY, ensure_narrow_viewport_detected  # type: ignore

from auth import current_profile, current_role
from branding import render_header
from db import delete_rows, fetch_one, fetch_table, insert_row, update_rows

try:
    from table_actions import (
        IPS_PENDING_DELETE,
        TABLE_KEY_TIME_ENTRIES,
        clear_selected_ids,
        render_selectable_dataframe,
        render_selection_action_bar,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_TIME_ENTRIES,
        clear_selected_ids,
        render_selectable_dataframe,
        render_selection_action_bar,
    )

try:
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore

try:
    from services.time_grid_service import (
        copy_employee_day_to_day,
        copy_employee_previous_week_to_current,
        delete_employee_week,
        fetch_time_entries_between,
        fill_employee_job_across_week,
        index_by_employee_date,
        monday_of_week,
        sum_employee_week_hours,
        week_dates,
    )
except ImportError:
    from app.services.time_grid_service import (  # type: ignore
        copy_employee_day_to_day,
        copy_employee_previous_week_to_current,
        delete_employee_week,
        fetch_time_entries_between,
        fill_employee_job_across_week,
        index_by_employee_date,
        monday_of_week,
        sum_employee_week_hours,
        week_dates,
    )

TT_EDIT_ROLES = frozenset({"admin", "estimator", "project_manager"})

_OT_THRESHOLD_DEFAULT = 40.0

# Fast entry / autosave session keys (stable across reruns)
TT_AUTOSAVE_KEY = "tt_autosave_enabled"
TT_DEFAULT_HOURS_KEY = "tt_default_hours_for_new_rows"
TT_JOB_LABEL_TO_ID_KEY = "_tt_job_label_to_id_for_callbacks"
TT_EDIT_ID_KEY = "tt_entry_edit_id"
TT_FAST_ENTRY_KEY = "tt_fast_entry_mode"
# Single Quick Actions surface per page: which employee row has the panel expanded
TT_OPEN_EMP_PANEL_KEY = "tt_open_employee_panel"

# Non-job time (no job_id): category list + selectbox sentinel
TT_NON_JOB_SENTINEL = "(Non-job — category below)"
NON_JOB_CATEGORY_OPTIONS = ["", "SHOP", "ADMIN", "TRAINING", "SAFETY", "PTO", "HOLIDAY", "TRAVEL"]
NON_JOB_CODE_COLORS: dict[str, str] = {
    "SHOP": "#64748b",
    "ADMIN": "#2563eb",
    "TRAINING": "#9333ea",
    "SAFETY": "#ea580c",
    "PTO": "#16a34a",
    "HOLIDAY": "#0d9488",
    "TRAVEL": "#ca8a04",
}


class _TTFiltersResult(NamedTuple):
    show_emp_ids: set[str]
    default_job_label: str | None
    ot_threshold: float
    active_employees: list[dict]
    job_label_to_id: dict[str, str]
    job_labels_sorted: list[str]
    job_id_to_label: dict[str, str]


class _TTWeekDataResult(NamedTuple):
    grid_rows: list
    idx: dict
    visible_emps: list[dict]
    week_total: float
    emp_id_to_name: dict[str, str]


def _tt_fast_entry() -> bool:
    return bool(st.session_state.get(TT_FAST_ENTRY_KEY, False))


def _tt_qa_day_key(eid: str) -> str:
    return f"tt_qa_day_{eid}"


def _tt_init_qa_day(eid: str, days: list[date], today: date) -> None:
    k = _tt_qa_day_key(eid)
    if k not in st.session_state:
        st.session_state[k] = (today if today in days else days[0]).isoformat()


def _tt_render_qa_context_heading(emp_name: str, d: date, today: date) -> None:
    if d == today:
        day_part = f"Today — {d.strftime('%a %m/%d')}"
    else:
        day_part = d.strftime("%a %m/%d")
    safe_n = html.escape(str(emp_name or "—").strip())
    safe_d = html.escape(day_part)
    st.markdown(
        f'<p class="ips-tt-qa-context"><strong>Editing:</strong> {safe_n} — {safe_d}</p>',
        unsafe_allow_html=True,
    )


def _render_qa_toggle_button(eid: str) -> None:
    st.markdown(
        '<span class="ips-tt-quick-actions-col ips-time-controls" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    open_e = st.session_state.get(TT_OPEN_EMP_PANEL_KEY)
    label = "▼ Actions" if open_e == eid else "⚡ Quick Actions"
    if st.button(
        label,
        key=f"tt_qa_toggle_{eid}",
        use_container_width=True,
        type="secondary",
        help="Open or close Quick Actions for this employee",
    ):
        if open_e == eid:
            st.session_state.pop(TT_OPEN_EMP_PANEL_KEY, None)
        else:
            st.session_state[TT_OPEN_EMP_PANEL_KEY] = eid
        st.rerun()


def _week_grid_column_ratios(*, fast: bool) -> list[float]:
    """9 columns: wider employee name column + Mon–Sun + Σ (ratios are relative weights)."""
    if fast:
        return [2.6] + [1.1] * 7 + [0.32]
    return [2.6] + [1.05] * 7 + [0.34]


def _employee_name_display_html(nm: str) -> str:
    """First line / second line at first space; no mid-word breaks (CSS keep-all). HTML-escaped."""
    raw = str(nm or "").strip()
    if not raw:
        return ""
    parts = raw.split(" ", 1)
    esc = html.escape
    if len(parts) == 2:
        a, b = parts[0].strip(), parts[1].strip()
        body = f"{esc(a)}<br>{esc(b)}"
    else:
        body = esc(raw)
    return f'<div class="ips-tt-emp-name-inner">{body}</div>'


def _hours_step(*, fast: bool) -> float:
    """Whole-hour steps in fast mode for quicker keyboard / spinner entry."""
    return 1.0 if fast else 0.5


def _inject_tt_fast_compact_css() -> None:
    """Extra squeeze in Fast Entry Mode (stacked on base dense styles)."""
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-fast-toolbar-scope) {
            padding: 2px 5px 4px 5px !important;
            margin-bottom: 4px !important;
        }
        .ips-tt-new-row { padding: 2px 4px 4px 4px !important; margin-top: 1px !important; margin-bottom: 1px !important; }
        .ips-tt-entry-gap { height: 2px !important; min-height: 2px !important; }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stNumberInput"] input {
            min-height: 1.15rem !important;
        }
        .ips-tt-day-head { font-size: 10px !important; margin-bottom: 1px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _tt_default_hours() -> float:
    v = st.session_state.get(TT_DEFAULT_HOURS_KEY, 8.0)
    try:
        h = float(v)
    except (TypeError, ValueError):
        return 8.0
    return max(0.0, min(24.0, h))


def _job_label_for_id(job_label_to_id: dict[str, str], job_id: str) -> str | None:
    jid = str(job_id or "")
    for lb, j in job_label_to_id.items():
        if str(j) == jid:
            return lb
    return None


def _persist_time_entry_row(te_id: str, job_label_to_id: dict[str, str]) -> tuple[bool, str | None]:
    """Read widget state for one entry and update DB. Returns (ok, error_message)."""
    jk, hk, nk, njk = f"tt_job_{te_id}", f"tt_h_{te_id}", f"tt_n_{te_id}", f"tt_nj_{te_id}"
    if jk not in st.session_state:
        return False, None
    job_label = st.session_state.get(jk)
    if not isinstance(job_label, str):
        return False, "Invalid job selection."
    nj = str(st.session_state.get(njk) or "").strip()
    hrs = float(st.session_state.get(hk) or 0)
    note = str(st.session_state.get(nk) or "").strip()
    if job_label and job_label != TT_NON_JOB_SENTINEL:
        new_jid = job_label_to_id.get(job_label)
        if not new_jid:
            return False, "Pick a valid job."
        payload = {
            "job_id": new_jid,
            "non_job_code": None,
            "hours": hrs,
            "notes": note,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        if not nj:
            return False, "Pick a job or select a non-job category."
        payload = {
            "job_id": None,
            "non_job_code": nj,
            "hours": hrs,
            "notes": note,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    try:
        update_rows("time_entries", payload, {"id": te_id})
    except Exception as exc:
        return False, str(exc)
    snap_k = f"tt_row_snap_{te_id}"
    st.session_state[snap_k] = (job_label, nj, hrs, note)
    return True, None


def _maybe_autosave_entry(te_id: str) -> None:
    if not st.session_state.get(TT_AUTOSAVE_KEY):
        return
    jm = st.session_state.get(TT_JOB_LABEL_TO_ID_KEY)
    if not isinstance(jm, dict):
        return
    jk = f"tt_job_{te_id}"
    hk = f"tt_h_{te_id}"
    nk = f"tt_n_{te_id}"
    njk = f"tt_nj_{te_id}"
    if jk not in st.session_state:
        return
    job_label = st.session_state.get(jk)
    hrs = float(st.session_state.get(hk) or 0)
    note = str(st.session_state.get(nk) or "").strip()
    nj = str(st.session_state.get(njk) or "").strip()
    if not isinstance(job_label, str):
        return
    candidate = (job_label, nj, hrs, note)
    snap_k = f"tt_row_snap_{te_id}"
    if st.session_state.get(snap_k) == candidate:
        return
    ok, err = _persist_time_entry_row(te_id, jm)
    if ok:
        try:
            st.toast("Saved", icon="✓")
        except Exception:
            pass
    elif err:
        try:
            st.toast(err, icon="⚠")
        except Exception:
            pass


def _autosave_callback_factory(te_id: str):
    def _cb() -> None:
        _maybe_autosave_entry(te_id)

    return _cb


def _init_row_snap_from_ent(
    te_id: str,
    ent: dict,
    job_label_snap: str,
    non_job_snap: str,
) -> None:
    snap_k = f"tt_row_snap_{te_id}"
    if snap_k not in st.session_state:
        st.session_state[snap_k] = (
            job_label_snap,
            str(non_job_snap or "").strip(),
            float(ent.get("hours", 0) or 0),
            str(ent.get("notes") or "").strip(),
        )


def _clear_row_snap(te_id: str) -> None:
    st.session_state.pop(f"tt_row_snap_{te_id}", None)


# Consistent badge colors on dark theme (WCAG-friendly saturation)
_BADGE_PALETTE = [
    "#2563eb",
    "#16a34a",
    "#ca8a04",
    "#9333ea",
    "#db2777",
    "#0d9488",
    "#ea580c",
    "#4f46e5",
    "#0891b2",
    "#c026d3",
]


def _ordered_job_ids_for_badges(job_labels_sorted: list[str], job_label_to_id: dict[str, str]) -> list[str]:
    return [job_label_to_id[lb] for lb in job_labels_sorted if lb in job_label_to_id]


def _job_badge_color(job_id: str, ordered_ids: list[str]) -> str:
    jid = str(job_id)
    if jid in ordered_ids:
        i = ordered_ids.index(jid)
    else:
        i = abs(hash(jid)) % len(_BADGE_PALETTE)
    return _BADGE_PALETTE[i % len(_BADGE_PALETTE)]


def _job_badge_html(job_label: str, job_id: str, ordered_ids: list[str]) -> str:
    c = _job_badge_color(job_id, ordered_ids)
    lab = html.escape(job_label[:42] + ("…" if len(job_label) > 42 else ""))
    return f'<span class="ips-tt-job-badge" style="background:{c};border-color:{c}">{lab}</span>'


def _non_job_badge_html(code: str) -> str:
    c = NON_JOB_CODE_COLORS.get(str(code).strip(), "#64748b")
    lab = html.escape(str(code).strip()[:24])
    return f'<span class="ips-tt-job-badge" style="background:{c};border-color:{c}">{lab}</span>'


def _inject_tt_styles() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlock"]:has(> div.ips-tt-wrap) {
            background: rgba(15, 23, 42, 0.65);
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 10px;
            padding: 8px 10px 11px 10px;
            margin-bottom: 6px;
        }
        .ips-tt-wrap { }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            min-width: 0 !important;
        }
        div[data-testid="stHorizontalBlock"] button p {
            white-space: nowrap !important;
        }
        div[data-testid="stHorizontalBlock"] button {
            white-space: nowrap !important;
        }
        .ips-tt-entry-gap {
            display: block;
            height: 4px;
            min-height: 4px;
        }
        hr.ips-tt-entry-sep {
            border: none;
            border-top: 1px solid rgba(100, 116, 139, 0.35);
            margin: 0.2rem 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-fast-toolbar-scope) {
            border: 1px solid rgba(71, 85, 105, 0.45) !important;
            border-radius: 8px !important;
            padding: 4px 6px 6px 6px !important;
            margin-bottom: 6px !important;
            background: rgba(15, 23, 42, 0.55) !important;
        }
        .ips-tt-new-row {
            border: 1px dashed rgba(100, 116, 139, 0.55);
            border-radius: 6px;
            padding: 3px 5px 5px 5px;
            margin-top: 2px;
            margin-bottom: 2px;
            background: rgba(30, 41, 59, 0.35);
        }
        .ips-tt-new-block {
            margin-top: 2px;
            padding-top: 4px;
            border-top: 1px dashed rgba(100, 116, 139, 0.4);
        }
        .ips-tt-row-over {
            border-left: 4px solid #f87171 !important;
            background: rgba(248, 113, 113, 0.12) !important;
            border-radius: 6px;
            padding-left: 6px !important;
        }
        .ips-tt-day-head {
            color: #cbd5e1 !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            text-align: center !important;
            margin-bottom: 0 !important;
            letter-spacing: 0.03em;
        }
        .ips-tt-day-sum {
            text-align: center !important;
            font-size: 10px !important;
            color: #94a3b8 !important;
            margin-bottom: 4px !important;
            font-variant-numeric: tabular-nums !important;
        }
        .ips-tt-qa-context {
            font-size: 0.95rem !important;
            margin: 0.15rem 0 0.65rem 0 !important;
            color: #e2e8f0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-selected) {
            border-color: rgba(56, 189, 248, 0.65) !important;
            box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.28);
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) {
            padding: 4px 5px 5px 5px !important;
        }
        /* Day cell row actions — compact, single-line labels */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) button {
            min-height: 1.35rem !important;
            max-height: 1.75rem !important;
            padding: 0.08rem 0.35rem !important;
            font-size: 0.72rem !important;
            border-radius: 5px !important;
            line-height: 1.1 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) button p {
            white-space: nowrap !important;
            font-size: 0.72rem !important;
            line-height: 1.1 !important;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) p {
            word-break: break-word;
        }
        /* Dense inputs: Job / Hours / Notes inside day cards */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stSelectbox"] label,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stNumberInput"] label,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stTextInput"] label {
            min-height: 0 !important;
            padding-bottom: 0 !important;
            margin-bottom: 0 !important;
            font-size: 0.68rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 1.35rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stNumberInput"] input {
            min-height: 1.32rem !important;
            height: 1.32rem !important;
            padding: 0.06rem 0.28rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stTextInput"] input {
            min-height: 1.32rem !important;
            padding: 0.06rem 0.28rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stVerticalBlock"] > div {
            gap: 0.1rem 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-card) [data-testid="stHorizontalBlock"] {
            gap: 0.2rem !important;
            flex-wrap: nowrap !important;
        }
        /* Flat edit panel — same density */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) {
            padding: 6px 8px 8px 8px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 1.35rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) [data-testid="stNumberInput"] input {
            min-height: 1.32rem !important;
            padding: 0.06rem 0.28rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) [data-testid="stTextInput"] input {
            min-height: 1.32rem !important;
            padding: 0.06rem 0.28rem !important;
            font-size: 0.78rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) button {
            min-height: 1.35rem !important;
            max-height: 1.75rem !important;
            padding: 0.08rem 0.35rem !important;
            font-size: 0.72rem !important;
            border-radius: 5px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) button p {
            white-space: nowrap !important;
            font-size: 0.72rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-flat-panel) [data-testid="stHorizontalBlock"] {
            gap: 0.25rem !important;
        }
        /* Top nav row — span lives in first column of same horizontal block */
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-nav-scope) [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-nav-scope) [data-testid="stMultiSelect"] button {
            min-height: 1.4rem !important;
            font-size: 0.8rem !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-nav-scope) label[data-testid="stWidgetLabel"] {
            font-size: 0.72rem !important;
            margin-bottom: 0 !important;
        }
        div[data-testid="stExpanderDetails"]:has(span.ips-tt-week-options) [data-testid="stNumberInput"] input {
            min-height: 1.35rem !important;
            font-size: 0.8rem !important;
            padding: 0.08rem 0.35rem !important;
        }
        /* Toolbar (marker span + widgets in same vertical block) */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-fast-toolbar-scope) [data-testid="stNumberInput"] input,
        div[data-testid="stVerticalBlock"]:has(span.ips-tt-fast-toolbar-scope) [data-testid="stNumberInput"] input {
            min-height: 1.32rem !important;
            font-size: 0.78rem !important;
            padding: 0.06rem 0.3rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-fast-toolbar-scope) label[data-testid="stWidgetLabel"],
        div[data-testid="stVerticalBlock"]:has(span.ips-tt-fast-toolbar-scope) label[data-testid="stWidgetLabel"] {
            font-size: 0.72rem !important;
            margin-bottom: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-fast-toolbar-scope) [data-testid="stHorizontalBlock"] {
            gap: 0.2rem !important;
        }
        .ips-tt-flat-title {
            font-size: 0.92rem !important;
            font-weight: 600 !important;
            margin: 0 0 0.2rem 0 !important;
            color: #e2e8f0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-ot-scope) [data-testid="stNumberInput"] input,
        div[data-testid="stVerticalBlock"]:has(span.ips-tt-ot-scope) [data-testid="stNumberInput"] input {
            min-height: 1.32rem !important;
            font-size: 0.8rem !important;
            padding: 0.06rem 0.3rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-ot-scope) label[data-testid="stWidgetLabel"],
        div[data-testid="stVerticalBlock"]:has(span.ips-tt-ot-scope) label[data-testid="stWidgetLabel"] {
            font-size: 0.72rem !important;
            margin-bottom: 0 !important;
        }
        /* Quick actions — small trigger, tight panel */
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) {
            max-width: 20rem !important;
            padding: 0.35rem 0.5rem 0.5rem 0.5rem !important;
        }
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) [data-testid="stVerticalBlock"] > div {
            gap: 0.25rem !important;
        }
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) button {
            min-height: 1.3rem !important;
            max-height: 1.65rem !important;
            padding: 0.06rem 0.35rem !important;
            font-size: 0.7rem !important;
            border-radius: 4px !important;
        }
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 1.28rem !important;
            font-size: 0.75rem !important;
        }
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) [data-testid="stNumberInput"] input,
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) [data-testid="stTextInput"] input {
            min-height: 1.25rem !important;
            font-size: 0.75rem !important;
            padding: 0.05rem 0.25rem !important;
        }
        div[data-testid="stPopoverBody"]:has(span.ips-tt-qa-panel) label[data-testid="stWidgetLabel"] {
            font-size: 0.68rem !important;
            margin-bottom: 0 !important;
        }
        button[data-testid="stBaseButton-popover"][kind="tertiary"],
        button[kind="tertiary"][data-testid="stBaseButton-popover"] {
            min-height: 1.35rem !important;
            max-height: 1.55rem !important;
            padding: 0.1rem 0.35rem !important;
            font-size: 0.75rem !important;
            opacity: 0.92;
        }
        .ips-tt-field-label {
            font-size: 9px !important;
            font-weight: 600 !important;
            color: #94a3b8 !important;
            margin: 0 !important;
            line-height: 1.05 !important;
            padding: 0 !important;
        }
        .ips-tt-metric {
            color: #e2e8f0 !important;
            font-size: 12px !important;
            font-weight: 600 !important;
        }
        .ips-tt-job-badge {
            display: inline-block;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.02em;
            color: #f8fafc !important;
            background: var(--badge, #334155);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 5px;
            padding: 2px 6px;
            margin-bottom: 3px;
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .ips-tt-nj-sep {
            color: #64748b !important;
            font-size: 10px !important;
            font-weight: 600 !important;
            margin: 0.2rem 0 0.3rem 0 !important;
            letter-spacing: 0.08em;
        }
        .ips-tt-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            align-items: center;
        }
        .ips-tt-week-hdr-cell, .ips-tt-week-hdr-day, .ips-tt-week-hdr-sum {
            text-align: center;
            color: #94a3b8 !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            padding: 2px 0 4px 0;
        }
        .ips-tt-week-hdr-emp { text-align: left !important; }
        .ips-tt-week-hdr-title { display: block; color: #cbd5e1 !important; font-size: 10px !important; }
        .ips-tt-wh-dow { display: block; color: #e2e8f0 !important; font-size: 11px !important; }
        .ips-tt-wh-date { display: block; font-size: 10px !important; font-weight: 600 !important; opacity: 0.9; }
        .ips-tt-emp-cell {
            padding: 4px 4px 6px 2px;
            line-height: 1.25;
            min-width: 0;
        }
        .ips-tt-emp-name {
            font-size: 0.92rem !important;
            font-weight: 700 !important;
            color: #f1f5f9 !important;
            margin: 0 0 4px 0 !important;
            line-height: 1.2 !important;
            max-width: 100% !important;
        }
        .ips-tt-emp-name .ips-tt-emp-name-inner {
            max-width: 100%;
            white-space: normal;
            word-break: keep-all;
            overflow-wrap: normal;
            line-height: 1.2;
        }
        .ips-tt-emp-total {
            font-size: 0.72rem !important;
            font-weight: 500 !important;
            color: #94a3b8 !important;
            margin: 0 !important;
            line-height: 1.3 !important;
        }
        /* Employee header: name column + quick-actions column (scoped — do not target the 9-col week row) */
        div[data-testid="column"]:has(span.ips-tt-emp-header-scope) {
            min-width: 0 !important;
        }
        div[data-testid="column"]:has(span.ips-tt-quick-actions-col) {
            display: flex !important;
            justify-content: flex-end !important;
            align-items: flex-start !important;
            padding-top: 2px !important;
            min-width: 0 !important;
        }
        div[data-testid="column"]:has(span.ips-tt-quick-actions-col) button[data-testid="stBaseButton-popover"] {
            min-height: 2rem !important;
            min-width: 2rem !important;
        }

        /* Full-width employee cards (narrow / stacked layout) */
        .ips-time-card {
            width: 100%;
            box-sizing: border-box;
        }
        .ips-time-row {
            display: block;
            width: 100%;
        }
        .ips-time-controls {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
            justify-content: flex-end;
        }

        @media (max-width: 768px) {
            .ips-time-row,
            .ips-time-card {
                width: 100%;
                display: block;
            }
            .ips-tt-sheet-narrow .ips-tt-emp-name,
            .ips-time-name {
                font-size: 16px !important;
                white-space: normal !important;
                overflow: visible !important;
                text-overflow: clip !important;
            }
            .ips-tt-sheet-narrow .ips-tt-emp-name .ips-tt-emp-name-inner {
                word-break: keep-all !important;
                overflow-wrap: normal !important;
            }
            div[data-testid="column"]:has(span.ips-tt-quick-actions-col) {
                justify-content: flex-start !important;
                margin-top: 4px;
                padding-top: 0 !important;
            }
            [data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) .stButton > button,
            [data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-empty) .stButton > button {
                min-height: 44px !important;
                padding: 0.4rem 0.65rem !important;
                font-size: 0.85rem !important;
            }
            [data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) [data-testid="stNumberInput"] input,
            [data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) [data-testid="stTextInput"] input {
                min-height: 44px !important;
            }
        }

        /* —— Spreadsheet / Excel-like weekly grid (IPS dark theme) —— */
        span.ips-tt-sheet-row { display: none !important; }

        /* Header row: strong band + grid lines */
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) {
            background: linear-gradient(180deg, rgba(51, 65, 85, 0.92) 0%, rgba(30, 41, 59, 0.88) 100%) !important;
            border: 1px solid rgba(148, 163, 184, 0.5) !important;
            border-radius: 3px 3px 0 0 !important;
            margin-bottom: 0 !important;
            padding: 0 !important;
            box-shadow: inset 0 -2px 0 rgba(15, 23, 42, 0.5);
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) > div[data-testid="column"] {
            border-right: 1px solid rgba(71, 85, 105, 0.75) !important;
            padding: 6px 5px 7px 5px !important;
            align-self: stretch !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) > div[data-testid="column"]:first-child {
            background: rgba(15, 23, 42, 0.35) !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) > div[data-testid="column"]:last-child {
            border-right: none !important;
            background: rgba(15, 23, 42, 0.28) !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) .ips-tt-week-hdr-day,
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) .ips-tt-week-hdr-sum {
            color: #f1f5f9 !important;
            font-weight: 800 !important;
            letter-spacing: 0.06em !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) .ips-tt-wh-dow {
            color: #cbd5e1 !important;
            font-size: 10px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-hdr-corner) .ips-tt-wh-date {
            color: #e2e8f0 !important;
            font-size: 11px !important;
        }

        /* Data rows: zebra + hover + column lines + sticky employee/total tint */
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-row.ips-tt-zebra-0) {
            background: rgba(22, 32, 48, 0.72) !important;
            border-left: 1px solid rgba(71, 85, 105, 0.65) !important;
            border-right: 1px solid rgba(71, 85, 105, 0.65) !important;
            margin-top: -1px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-row.ips-tt-zebra-1) {
            background: rgba(17, 26, 39, 0.78) !important;
            border-left: 1px solid rgba(71, 85, 105, 0.65) !important;
            border-right: 1px solid rgba(71, 85, 105, 0.65) !important;
            margin-top: -1px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-row):hover {
            background: rgba(59, 130, 246, 0.14) !important;
            box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.35) !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-row) > div[data-testid="column"] {
            border-right: 1px solid rgba(71, 85, 105, 0.55) !important;
            padding: 4px 4px 5px 4px !important;
            align-self: stretch !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-row) > div[data-testid="column"]:first-child {
            background: rgba(30, 41, 59, 0.65) !important;
            border-right: 1px solid rgba(100, 116, 139, 0.45) !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-row) > div[data-testid="column"]:last-child {
            background: rgba(30, 41, 59, 0.5) !important;
            border-right: none !important;
            border-left: 1px solid rgba(100, 116, 139, 0.35) !important;
        }

        /* Remove heavy “card” chrome around whole employee row */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-sheet-row) {
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
            padding: 0 !important;
            margin-bottom: 0 !important;
        }

        /* Footer totals row */
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-footer-row) {
            background: rgba(51, 65, 85, 0.55) !important;
            border: 1px solid rgba(148, 163, 184, 0.45) !important;
            border-top: 2px solid rgba(100, 116, 139, 0.55) !important;
            border-radius: 0 0 3px 3px !important;
            margin-top: -1px !important;
            padding: 2px 0 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-footer-row) > div[data-testid="column"] {
            border-right: 1px solid rgba(71, 85, 105, 0.55) !important;
            padding: 5px 4px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-footer-row) > div[data-testid="column"]:first-child {
            background: rgba(15, 23, 42, 0.4) !important;
            font-weight: 700 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(span.ips-tt-sheet-footer-row) > div[data-testid="column"]:last-child {
            border-right: none !important;
            background: rgba(15, 23, 42, 0.35) !important;
        }

        /* Day sub-header (sum line) — spreadsheet sublabel */
        .ips-tt-day-head {
            background: rgba(15, 23, 42, 0.45) !important;
            border: 1px solid rgba(71, 85, 105, 0.4) !important;
            border-radius: 2px 2px 0 0 !important;
            padding: 3px 4px !important;
            margin-bottom: 0 !important;
        }
        .ips-tt-day-sum {
            background: rgba(15, 23, 42, 0.35) !important;
            border: 1px solid rgba(71, 85, 105, 0.4) !important;
            border-top: none !important;
            border-radius: 0 0 2px 2px !important;
            padding: 2px 4px 3px 4px !important;
            margin-bottom: 4px !important;
            font-variant-numeric: tabular-nums !important;
        }

        /* Day “cells”: flat, grid-like, not floating cards */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) {
            border-radius: 2px !important;
            border: 1px solid rgba(71, 85, 105, 0.65) !important;
            background: rgba(15, 23, 42, 0.55) !important;
            box-shadow: none !important;
            padding: 4px 4px 5px 4px !important;
            margin-top: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell):focus-within {
            box-shadow: inset 0 0 0 2px rgba(59, 130, 246, 0.65) !important;
            background: rgba(15, 23, 42, 0.75) !important;
            border-color: rgba(96, 165, 250, 0.45) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) input:focus,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) textarea:focus,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-cell) [data-baseweb="select"]:focus-within {
            outline: 2px solid rgba(59, 130, 246, 0.9) !important;
            outline-offset: 0px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-empty) {
            background: rgba(15, 23, 42, 0.25) !important;
            border: 1px dashed rgba(100, 116, 139, 0.45) !important;
            min-height: 2.75rem !important;
            text-align: center !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-day-empty) button {
            font-size: 0.76rem !important;
            min-height: 1.45rem !important;
            padding: 0.15rem 0.45rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-sheet-narrow.ips-tt-zebra-0) {
            background: rgba(22, 32, 48, 0.5) !important;
            border: 1px solid rgba(71, 85, 105, 0.5) !important;
            border-radius: 3px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-sheet-narrow.ips-tt-zebra-1) {
            background: rgba(17, 26, 39, 0.55) !important;
            border: 1px solid rgba(71, 85, 105, 0.5) !important;
            border-radius: 3px !important;
        }
        /* Spacing between full-width employee week rows (desktop sheet) */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-tt-sheet-emp-card) {
            margin-bottom: 10px !important;
            padding: 8px 10px 10px 10px !important;
            border-radius: 8px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _parse_date_key(s: str) -> date:
    return date.fromisoformat(s[:10])


def _tt_flat_entry_rows(
    grid_rows: list,
    show_emp_ids: set,
    fj_id: str | None,
    emp_id_to_name: dict[str, str],
    job_id_to_label: dict[str, str],
) -> list[dict]:
    out: list[dict] = []
    for e in grid_rows:
        eid = str(e.get("employee_id") or "")
        if show_emp_ids and eid not in show_emp_ids:
            continue
        jid = str(e.get("job_id") or "").strip()
        nj = str(e.get("non_job_code") or "").strip()
        if fj_id and jid != fj_id:
            continue
        tid = e.get("id")
        if not tid:
            continue
        if jid:
            job_disp = job_id_to_label.get(jid, jid[:8] + "…" if len(jid) > 8 else jid)
        elif nj:
            job_disp = nj
        else:
            job_disp = "—"
        out.append(
            {
                "id": tid,
                "employee": emp_id_to_name.get(eid, eid[:8] + "…" if len(eid) > 8 else eid),
                "work_date": str(e.get("work_date") or "")[:10],
                "job": job_disp,
                "hours": float(e.get("hours") or 0),
                "notes": str(e.get("notes") or ""),
            }
        )
    return out


def _render_employee_name_cell(*, nm: str, tot_s: str, over: bool, ot_threshold: float) -> None:
    """Employee name (first line / remainder at first space; no mid-word breaks) and muted weekly hours."""
    title_attr = html.escape(nm, quote=True)
    over_cls = " ips-tt-row-over" if over else ""
    name_inner = _employee_name_display_html(nm)
    if over:
        tot_line = html.escape(f"{tot_s} · over {ot_threshold:g} h")
    else:
        tot_line = html.escape(tot_s)
    st.markdown(
        f'<div class="ips-tt-emp-cell">'
        f'<div class="ips-tt-emp-name ips-time-name{over_cls}" title="{title_attr}">{name_inner}</div>'
        f'<p class="ips-tt-emp-total">{tot_line}</p></div>',
        unsafe_allow_html=True,
    )


def _render_employee_time_header(
    *,
    nm: str,
    tot_s: str,
    over: bool,
    ot_threshold: float,
    eid: str,
) -> None:
    """Name + weekly hours (left) and Quick Actions toggle (right); used for narrow cards and desktop sheet first column."""
    c1, c2 = st.columns([1, 0.34], gap="small")
    with c1:
        st.markdown(
            '<span class="ips-tt-emp-header-scope" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        _render_employee_name_cell(nm=nm, tot_s=tot_s, over=over, ot_threshold=ot_threshold)
    with c2:
        _render_qa_toggle_button(eid)


def _render_week_header_row(*, grid_ratios: list[float], days: list[date]) -> None:
    """One row aligned to the grid: Employee + Mon–Sun + Σ (spreadsheet header band)."""
    h0, *hday, hlast = st.columns(grid_ratios)
    with h0:
        st.markdown(
            '<span class="ips-tt-sheet-hdr-corner" aria-hidden="true"></span>'
            '<div class="ips-tt-week-hdr-cell ips-tt-week-hdr-emp">'
            '<span class="ips-tt-week-hdr-title">Employee</span></div>',
            unsafe_allow_html=True,
        )
    for di, d in enumerate(days):
        with hday[di]:
            st.markdown(
                f'<div class="ips-tt-week-hdr-day ips-tt-sheet-hdr-day">'
                f'<span class="ips-tt-wh-dow">{d.strftime("%a")}</span>'
                f'<span class="ips-tt-wh-date">{d.strftime("%b %d")}</span></div>',
                unsafe_allow_html=True,
            )
    with hlast:
        st.markdown(
            '<div class="ips-tt-week-hdr-sum ips-tt-sheet-hdr-sum">Σ</div>',
            unsafe_allow_html=True,
        )


def _tt_render_header_section() -> tuple[bool, bool]:
    """Branding, styles, viewport, Fast Entry. Returns (can_edit, fast)."""
    render_header("Time Tracking", subtitle="Weekly timesheet — by employee and job")

    _inject_tt_styles()
    ensure_narrow_viewport_detected()

    role = current_role()
    can_edit = role in TT_EDIT_ROLES

    if can_edit:
        st.session_state.setdefault(TT_FAST_ENTRY_KEY, False)
        st.checkbox(
            "Fast Entry Mode",
            key=TT_FAST_ENTRY_KEY,
            help="Denser grid and controls; same data and filters.",
        )

    fast = _tt_fast_entry()
    if fast:
        _inject_tt_fast_compact_css()

    return can_edit, fast


def _tt_render_toolbar_section(today: date) -> tuple[date, list[date], date]:
    """PM Matrix shortcut + week navigation. Returns (week_start, days, week_end)."""
    try:
        from ui import IPS_NAV_PENDING_KEY
    except ImportError:
        from app.ui import IPS_NAV_PENDING_KEY  # type: ignore

    fast = _tt_fast_entry()
    pm_row1, pm_row2 = st.columns([4, 1])
    with pm_row1:
        if not fast:
            st.caption("One-day crew grid: **PM Matrix Time Entry** (sidebar).")
    with pm_row2:
        if st.button("PM Matrix", key="tt_open_pm_matrix", use_container_width=True):
            st.session_state[IPS_NAV_PENDING_KEY] = "PM Matrix Time Entry"
            st.rerun()

    st.session_state.setdefault("tt_week_start", monday_of_week(today))

    week_start: date = st.session_state["tt_week_start"]
    if week_start.weekday() != 0:
        week_start = monday_of_week(week_start)
        st.session_state["tt_week_start"] = week_start

    days = week_dates(week_start)
    week_end = days[-1]

    st.markdown('<span class="ips-tt-nav-scope" aria-hidden="true"></span>', unsafe_allow_html=True)
    w1, w2, w3 = st.columns([1, 1, 1])
    with w1:
        if st.button("◀ Prev week", use_container_width=True, help="Previous week"):
            st.session_state["tt_week_start"] = week_start - timedelta(days=7)
            st.rerun()
    with w2:
        if st.button("Next week ▶", use_container_width=True, help="Next week"):
            st.session_state["tt_week_start"] = week_start + timedelta(days=7)
            st.rerun()
    with w3:
        if st.button("This week", use_container_width=True, help="Jump to this week"):
            st.session_state["tt_week_start"] = monday_of_week(today)
            st.rerun()

    return week_start, days, week_end


def _tt_render_filters_section(*, fast: bool) -> _TTFiltersResult:
    """Employee / job filters and week options (OT threshold)."""
    try:
        all_employees = fetch_table("employees", limit=5000, order_by="name")
    except Exception:
        all_employees = []
    active_employees = [e for e in all_employees if e.get("is_active", True) is not False]

    jobs = sort_jobs_by_number_then_name(fetch_table("jobs", limit=5000, order_by="job_number"))
    job_label_to_id = {
        job_row_select_label(j): str(j.get("id"))
        for j in jobs
        if j.get("id") and job_row_select_label(j) and job_row_select_label(j) != "—"
    }
    job_labels_sorted = sorted(job_label_to_id.keys(), key=str.casefold)
    job_id_to_label = {v: k for k, v in job_label_to_id.items()}
    st.session_state[TT_JOB_LABEL_TO_ID_KEY] = job_label_to_id

    emp_choices = {f"{e.get('name', '')} ({str(e.get('id'))[:8]})": str(e.get("id")) for e in active_employees if e.get("id")}
    emp_label_list = sorted(emp_choices.keys(), key=str.casefold)
    f1, f2 = st.columns(2, gap="small")
    with f1:
        filt_emp = st.multiselect(
            "Filter employees",
            options=emp_label_list,
            default=emp_label_list,
            help=None if fast else "Restrict which rows are shown.",
        )
    with f2:
        job_opts = ["(All jobs)"] + job_labels_sorted
        filt_job = st.selectbox(
            "Filter job (new entries default)",
            options=job_opts,
            index=0,
            help=None
            if fast
            else "When not “All”, new time lines default to this job; existing lines for other jobs still show.",
        )
    show_emp_ids = {emp_choices[lb] for lb in filt_emp} if filt_emp else set(emp_choices.values())
    default_job_label = None if filt_job == "(All jobs)" else filt_job

    with st.expander("Week options", expanded=False):
        st.markdown(
            '<span class="ips-tt-week-options ips-tt-ot-scope" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        ot_threshold = st.number_input(
            "Weekly OT highlight (hours)" if fast else "Weekly hours threshold (overtime highlight)",
            min_value=0.0,
            max_value=120.0,
            value=float(st.session_state.get("tt_ot_threshold", _OT_THRESHOLD_DEFAULT)),
            step=1.0 if fast else 0.5,
            key="tt_ot_threshold_input",
        )
    st.session_state["tt_ot_threshold"] = ot_threshold

    return _TTFiltersResult(
        show_emp_ids=show_emp_ids,
        default_job_label=default_job_label,
        ot_threshold=float(ot_threshold),
        active_employees=active_employees,
        job_label_to_id=job_label_to_id,
        job_labels_sorted=job_labels_sorted,
        job_id_to_label=job_id_to_label,
    )


def _tt_render_summary_section(
    week_start: date,
    week_end: date,
    filt: _TTFiltersResult,
) -> _TTWeekDataResult | None:
    """Load week rows, OT summary strip, job legend. Returns None if no visible employees."""
    try:
        grid_rows = fetch_time_entries_between(week_start, week_end)
    except Exception as exc:
        grid_rows = []
        st.error(f"Could not load time_entries: {exc}. Run `sql/009_time_entries.sql` in Supabase.")
    idx = index_by_employee_date(grid_rows)

    visible_emps = [e for e in filt.active_employees if str(e.get("id")) in filt.show_emp_ids]
    if not visible_emps:
        st.warning("No employees match the filter. Adjust filters or add employees (**Users** → Employees).")
        return None

    def _in_week(x: dict) -> bool:
        try:
            wd = _parse_date_key(str(x.get("work_date")))
            return week_start <= wd <= week_end
        except Exception:
            return False

    week_total = sum(float(x.get("hours", 0) or 0) for x in grid_rows if _in_week(x))
    st.caption(
        f"Week **{week_start.isoformat()}** → **{week_end.isoformat()}** · "
        f"{week_total:.2f} h in loaded data"
    )

    ordered_job_ids = _ordered_job_ids_for_badges(filt.job_labels_sorted, filt.job_label_to_id)
    with st.expander("Job color key", expanded=False):
        parts = [
            _job_badge_html(lb, filt.job_label_to_id[lb], ordered_job_ids)
            for lb in filt.job_labels_sorted[:60]
            if lb in filt.job_label_to_id
        ]
        st.markdown(
            '<div class="ips-tt-legend">' + "".join(parts) + "</div>",
            unsafe_allow_html=True,
        )
        if len(filt.job_labels_sorted) > 60:
            st.caption("Showing first 60 jobs; colors repeat by job order.")

    fast = _tt_fast_entry()
    if not fast:
        st.caption(
            "Each **employee × job × day** is unique. Hours save to **time_entries**. "
            "Approved rows in **employee_time_entries** (legacy) are still included in Job Costing."
        )

    emp_id_to_name = {
        str(e.get("id")): str(e.get("name") or "").strip() or "—"
        for e in filt.active_employees
        if e.get("id")
    }

    return _TTWeekDataResult(
        grid_rows=grid_rows,
        idx=idx,
        visible_emps=visible_emps,
        week_total=week_total,
        emp_id_to_name=emp_id_to_name,
    )


def _tt_render_grid_section(
    *,
    can_edit: bool,
    fast: bool,
    today: date,
    week_start: date,
    days: list[date],
    week_end: date,
    filt: _TTFiltersResult,
    week_data: _TTWeekDataResult,
) -> tuple[list[float], list[float]] | None:
    """Flat table, edit toolbars, weekly sheet (or read-only pivot). Returns footer inputs or None."""
    fj_id = filt.job_label_to_id.get(filt.default_job_label) if filt.default_job_label else None
    flat_rows = _tt_flat_entry_rows(
        week_data.grid_rows,
        filt.show_emp_ids,
        fj_id,
        week_data.emp_id_to_name,
        filt.job_id_to_label,
    )
    entries_df = pd.DataFrame(flat_rows)

    if can_edit:
        st.session_state.setdefault(TT_DEFAULT_HOURS_KEY, 8.0)
        st.session_state.setdefault(TT_AUTOSAVE_KEY, False)
        with st.container(border=True):
            st.markdown(
                '<span class="ips-tt-fast-toolbar-scope" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            tb1, tb2, tb3 = st.columns([1.25, 1.0, 2.8], gap="small")
            with tb1:
                dh = st.number_input(
                    "Def. hrs" if fast else "Default hrs",
                    min_value=0.0,
                    max_value=24.0,
                    value=float(_tt_default_hours()),
                    step=_hours_step(fast=fast),
                    key="tt_toolbar_default_hrs",
                    help=None if fast else "Prefills new-line hours for each day.",
                )
                st.session_state[TT_DEFAULT_HOURS_KEY] = float(dh)
            with tb2:
                st.checkbox(
                    "Auto-save",
                    key=TT_AUTOSAVE_KEY,
                    help="When on, job / hours / notes save on change; **Save** still commits explicitly.",
                )
            with tb3:
                if not fast:
                    st.caption(
                        "One **employee × job × day** line; edit in each row’s **Quick Actions** panel or via the table below."
                    )

    tv_id = st.session_state.get("tt_entry_view_id")
    if tv_id:
        vr = fetch_one("time_entries", {"id": tv_id})
        if not vr:
            st.session_state.pop("tt_entry_view_id", None)
        else:
            st.subheader("Time entry detail")
            e_nm = week_data.emp_id_to_name.get(str(vr.get("employee_id") or ""), "—")
            j_nm = filt.job_id_to_label.get(str(vr.get("job_id") or ""), "—")
            st.markdown(f"**Employee:** {e_nm}")
            st.markdown(f"**Work date:** {vr.get('work_date') or '—'}")
            st.markdown(f"**Job:** {j_nm}")
            st.markdown(f"**Hours:** {float(vr.get('hours') or 0):.2f}")
            st.markdown(f"**Notes:** {vr.get('notes') or '—'}")
            if st.button("← Week", use_container_width=True, key="tt_entry_view_back", help="Back to week grid"):
                st.session_state.pop("tt_entry_view_id", None)
                st.rerun()
            st.divider()

    if not entries_df.empty and "id" in entries_df.columns:
        st.subheader("Time entries (this week)")
        if not _tt_fast_entry():
            st.caption(
                "Action bar above the grid. Checkbox on the **left**; selection: **selected_time_entries_ids**."
            )
        show_flat = [c for c in ["employee", "work_date", "job", "hours", "notes"] if c in entries_df.columns]
        bar_ph = st.empty()
        _, sel = render_selectable_dataframe(
            entries_df,
            table_key=TABLE_KEY_TIME_ENTRIES,
            id_column="id",
            columns=show_flat,
            editor_key="tt_flat_sel_editor",
        )
        with bar_ph.container():
            actions = render_selection_action_bar(
                TABLE_KEY_TIME_ENTRIES,
                sel,
                can_view=True,
                can_edit=can_edit,
                can_delete=can_edit,
                export_df=entries_df,
                visible_df=entries_df,
                id_column="id",
                export_filename="time_entries_week_export.csv",
                view_label="View Entry",
                edit_label="Edit Entry",
                delete_label="Delete Entry",
                delete_selected_label="Delete Selected",
            )
        if actions.get("view") and sel and len(sel) == 1:
            st.session_state["tt_entry_view_id"] = str(sel[0])
            st.session_state.pop(TT_EDIT_ID_KEY, None)
            st.rerun()
        if actions.get("edit") and sel and len(sel) == 1 and can_edit:
            er = fetch_one("time_entries", {"id": str(sel[0])})
            if er:
                eid_e = str(er.get("employee_id") or "")
                wd_e = str(er.get("work_date") or "")[:10]
                if eid_e and wd_e:
                    st.session_state[TT_OPEN_EMP_PANEL_KEY] = eid_e
                    st.session_state[_tt_qa_day_key(eid_e)] = wd_e
                    st.session_state.pop(f"tt_qa_dpick_{eid_e}", None)
            st.session_state[TT_EDIT_ID_KEY] = str(sel[0])
            st.session_state.pop("tt_entry_view_id", None)
            st.rerun()
        pend = st.session_state.get(IPS_PENDING_DELETE) or {}
        if actions.get("confirm_delete") and pend.get(TABLE_KEY_TIME_ENTRIES) and can_edit:
            for tid in pend[TABLE_KEY_TIME_ENTRIES]:
                try:
                    delete_rows("time_entries", {"id": tid})
                except Exception as exc:
                    st.error(f"Could not delete {tid}: {exc}")
            pend.pop(TABLE_KEY_TIME_ENTRIES, None)
            clear_selected_ids(TABLE_KEY_TIME_ENTRIES)
            st.success("Delete completed where permitted.")
            st.rerun()

    if not can_edit:
        st.info("View-only mode. Sign in as admin, estimator, or project manager to log time.")
        _render_readonly_pivot(week_data.visible_emps, days, week_data.idx, filt.job_id_to_label)
        return None

    # —— Editable grid —— weekly timesheet: header + employee rows (wide) or stacked days (narrow)
    day_col_totals = [0.0] * 7
    uid = current_profile().get("id")
    ts_now = datetime.now(timezone.utc).isoformat()
    grid_ratios = _week_grid_column_ratios(fast=fast)
    is_narrow = bool(st.session_state.get(IPS_VIEWPORT_NARROW_KEY))

    if not is_narrow:
        _render_week_header_row(grid_ratios=grid_ratios, days=days)

    for ri, emp in enumerate(week_data.visible_emps):
        eid = str(emp.get("id"))
        row_h = sum_employee_week_hours(week_data.grid_rows, eid, days)
        over = row_h > filt.ot_threshold
        nm = str(emp.get("name", "") or "—")
        tot_s = f"{row_h:.1f} h" if fast else f"{row_h:.1f} h / week"
        zebra = ri % 2

        if is_narrow:
            with st.container(border=True):
                st.markdown(
                    f'<span class="ips-tt-sheet-narrow ips-tt-zebra-{zebra} ips-time-card" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                _render_employee_time_header(
                    nm=nm,
                    tot_s=tot_s,
                    over=over,
                    ot_threshold=filt.ot_threshold,
                    eid=eid,
                )
                for di, d in enumerate(days):
                    ds = _render_day_column_body(
                        d=d,
                        eid=eid,
                        idx=week_data.idx,
                        fj_id=fj_id,
                        job_id_to_label=filt.job_id_to_label,
                        show_day_heading=True,
                    )
                    day_col_totals[di] += ds
                st.markdown(
                    f'<p class="ips-tt-metric" style="text-align:right;margin-top:0.35rem;">Week Σ · {row_h:.1f} h</p>',
                    unsafe_allow_html=True,
                )
                if st.session_state.get(TT_OPEN_EMP_PANEL_KEY) == eid:
                    _render_quick_actions_panel(
                        eid=eid,
                        emp_name=nm,
                        days=days,
                        week_start=week_start,
                        week_end=week_end,
                        today=today,
                        idx=week_data.idx,
                        fj_id=fj_id,
                        job_labels_sorted=filt.job_labels_sorted,
                        job_label_to_id=filt.job_label_to_id,
                        default_job_label=filt.default_job_label,
                        fast=fast,
                        user_id=uid,
                        ts_iso=ts_now,
                    )
        else:
            row_container = st.container(border=True)
            with row_container:
                st.markdown(
                    '<span class="ips-tt-sheet-emp-card ips-time-card" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                h0, *hday, hlast = st.columns(grid_ratios)
                with h0:
                    st.markdown(
                        f'<span class="ips-tt-sheet-row ips-tt-zebra-{zebra}" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                    _render_employee_time_header(
                        nm=nm,
                        tot_s=tot_s,
                        over=over,
                        ot_threshold=filt.ot_threshold,
                        eid=eid,
                    )
                for di, d in enumerate(days):
                    with hday[di]:
                        ds = _render_day_column_body(
                            d=d,
                            eid=eid,
                            idx=week_data.idx,
                            fj_id=fj_id,
                            job_id_to_label=filt.job_id_to_label,
                            show_day_heading=False,
                        )
                        day_col_totals[di] += ds
                with hlast:
                    st.caption("Σ")
                    st.markdown(f'<p class="ips-tt-metric">{row_h:.1f}</p>', unsafe_allow_html=True)
                if st.session_state.get(TT_OPEN_EMP_PANEL_KEY) == eid:
                    _render_quick_actions_panel(
                        eid=eid,
                        emp_name=nm,
                        days=days,
                        week_start=week_start,
                        week_end=week_end,
                        today=today,
                        idx=week_data.idx,
                        fj_id=fj_id,
                        job_labels_sorted=filt.job_labels_sorted,
                        job_label_to_id=filt.job_label_to_id,
                        default_job_label=filt.default_job_label,
                        fast=fast,
                        user_id=uid,
                        ts_iso=ts_now,
                    )

    return day_col_totals, grid_ratios


def _tt_render_footer_section(day_col_totals: list[float], days: list[date], grid_ratios: list[float]) -> None:
    """Week totals row aligned to the grid (compact on narrow viewport)."""
    st.caption("Week totals")
    narrow = bool(st.session_state.get(IPS_VIEWPORT_NARROW_KEY))
    total_h = sum(day_col_totals)
    if narrow:
        st.markdown(
            f'<p class="ips-tt-metric" style="margin:0 0 0.35rem 0;">Week <strong>{total_h:.1f}</strong> h</p>',
            unsafe_allow_html=True,
        )
        with st.expander("Day totals (Mon–Sun)", expanded=False):
            for di, d in enumerate(days):
                st.markdown(f"**{d.strftime('%a %m/%d')}:** {day_col_totals[di]:.1f} h")
        return

    f0, *fday, fl = st.columns(grid_ratios)
    with f0:
        st.markdown('<span class="ips-tt-sheet-footer-row" aria-hidden="true"></span>', unsafe_allow_html=True)
        st.markdown("**Day Σ**")
    for di, d in enumerate(days):
        with fday[di]:
            st.markdown(f'<p class="ips-tt-metric">{day_col_totals[di]:.1f} h</p>', unsafe_allow_html=True)
    with fl:
        st.markdown(f'<p class="ips-tt-metric">{total_h:.1f}</p>', unsafe_allow_html=True)


def render() -> None:
    today = date.today()
    can_edit, fast = _tt_render_header_section()
    week_start, days, week_end = _tt_render_toolbar_section(today)
    filt = _tt_render_filters_section(fast=fast)
    week_data = _tt_render_summary_section(week_start, week_end, filt)
    if week_data is None:
        return
    footer = _tt_render_grid_section(
        can_edit=can_edit,
        fast=fast,
        today=today,
        week_start=week_start,
        days=days,
        week_end=week_end,
        filt=filt,
        week_data=week_data,
    )
    if footer is not None:
        day_col_totals, grid_ratios = footer
        _tt_render_footer_section(day_col_totals, days, grid_ratios)


def _render_quick_actions_panel(
    *,
    eid: str,
    emp_name: str,
    days: list[date],
    week_start: date,
    week_end: date,
    today: date,
    idx: dict,
    fj_id: str | None,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    default_job_label: str | None,
    fast: bool,
    user_id,
    ts_iso: str,
) -> None:
    """Single editing surface per employee: day context, bulk actions, and per-day entry editors."""
    st.markdown(
        '<span class="ips-tt-qa-panel ips-tt-quick-actions-col ips-time-controls" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    _tt_init_qa_day(eid, days, today)
    wd_key = _tt_qa_day_key(eid)
    try:
        cur_from_state = date.fromisoformat(str(st.session_state.get(wd_key) or "")[:10])
    except ValueError:
        cur_from_state = today if today in days else days[0]
    if cur_from_state not in days:
        cur_from_state = today if today in days else days[0]
        st.session_state[wd_key] = cur_from_state.isoformat()
    ix = days.index(cur_from_state)

    def _fmt_di(i: int) -> str:
        dd = days[i]
        if dd == today:
            return f"Today — {dd.strftime('%a %m/%d')}"
        return dd.strftime("%a %m/%d")

    with st.container(border=True):
        st.markdown("#### Quick Actions")
        st.caption("Pick a day on the grid with **Use this day**, or choose the working day below.")
        picked_ix = st.selectbox(
            "Working day",
            list(range(len(days))),
            index=ix,
            format_func=_fmt_di,
            key=f"tt_qa_dpick_{eid}",
            help="Entries and Add below apply to this day.",
        )
        cur_d = days[int(picked_ix)]
        st.session_state[wd_key] = cur_d.isoformat()
        wd_work = cur_d.isoformat()
        _tt_render_qa_context_heading(emp_name, cur_d, today)

        st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)
        st.caption("Copy the previous calendar day into the working day selected above.")
        if st.button(
            "Copy previous day → working day",
            key=f"tt_cpday_{eid}",
            use_container_width=True,
            help="Copy previous calendar day into the selected working day",
        ):
            dest_date = cur_d
            from_date = dest_date - timedelta(days=1)
            try:
                copy_employee_day_to_day(
                    employee_id=eid,
                    from_date=from_date,
                    to_date=dest_date,
                    created_by=user_id,
                    updated_at_iso=ts_iso,
                )
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)
        if st.button(
            "Copy prev week",
            key=f"tt_cpw_{eid}",
            use_container_width=True,
            help="Copy entire previous calendar week into this week (replaces)",
        ):
            try:
                copy_employee_previous_week_to_current(
                    employee_id=eid,
                    dest_week_start=week_start,
                    created_by=user_id,
                    updated_at_iso=ts_iso,
                )
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)
        st.markdown('<p class="ips-tt-field-label">Fill week (Mon–Sun)</p>', unsafe_allow_html=True)
        fill_j = st.selectbox("Job", job_labels_sorted, key=f"tt_fillj_{eid}", label_visibility="collapsed")
        fh1, fh2 = st.columns(2, gap="small")
        with fh1:
            st.markdown('<p class="ips-tt-field-label">Hrs/d</p>', unsafe_allow_html=True)
            fill_h = st.number_input(
                "Hours per day",
                0.0,
                24.0,
                8.0,
                step=0.5,
                key=f"tt_fillh_{eid}",
                label_visibility="collapsed",
            )
        with fh2:
            st.markdown('<p class="ips-tt-field-label">Notes</p>', unsafe_allow_html=True)
            fill_n = st.text_input("Notes (optional)", "", key=f"tt_filln_{eid}", label_visibility="collapsed")
        if st.button(
            "Fill week",
            key=f"tt_fill_{eid}",
            use_container_width=True,
            help="Fill selected job across Mon–Sun (upserts hours per day)",
        ):
            jid = job_label_to_id.get(fill_j)
            if not jid:
                st.error("Pick a job.")
            else:
                try:
                    fill_employee_job_across_week(
                        employee_id=eid,
                        job_id=jid,
                        week_dates=days,
                        hours_per_day=float(fill_h),
                        notes=str(fill_n).strip(),
                        created_by=user_id,
                        updated_at_iso=ts_iso,
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)
        confirm = st.checkbox("Clear all entries this week", key=f"tt_clr_{eid}")
        if st.button(
            "Clear week",
            key=f"tt_clrb_{eid}",
            disabled=not confirm,
            use_container_width=True,
            help="Delete all time entries for this employee this week",
        ):
            try:
                delete_employee_week(eid, week_start, week_end)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        st.markdown('<hr class="ips-tt-entry-sep"/>', unsafe_allow_html=True)
        st.subheader("Entries for this day")
        ents_all = idx.get((eid, wd_work), [])
        ents_show = [e for e in ents_all if not fj_id or str(e.get("job_id")) == fj_id]
        if not ents_show:
            st.caption("No lines yet for this day — add below.")
        for ent in ents_show:
            _render_entry_editor(
                ent,
                job_labels_sorted,
                job_label_to_id,
                fast=fast,
                from_table_panel=True,
            )
            st.markdown('<div class="ips-tt-entry-gap"></div>', unsafe_allow_html=True)
        st.markdown('<p class="ips-tt-field-label">Add line</p>', unsafe_allow_html=True)
        _render_new_entry_form(
            eid,
            wd_work,
            job_labels_sorted,
            job_label_to_id,
            default_job_label,
            ents_show,
            fast=fast,
        )


def _render_entry_editor(
    ent: dict,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    *,
    fast: bool,
    from_table_panel: bool = False,
) -> None:
    te_id = str(ent.get("id"))
    cur_jid = str(ent.get("job_id") or "").strip()
    cur_nj = str(ent.get("non_job_code") or "").strip()
    job_options = [TT_NON_JOB_SENTINEL] + list(job_labels_sorted)
    if cur_nj and not cur_jid:
        j_ix = 0
        job_label_snap = TT_NON_JOB_SENTINEL
    elif cur_jid:
        cur_label = next(
            (lb for lb, j in job_label_to_id.items() if j == cur_jid),
            job_labels_sorted[0] if job_labels_sorted else "",
        )
        j_ix = 1 + job_labels_sorted.index(cur_label) if cur_label in job_labels_sorted else 1
        job_label_snap = cur_label
    else:
        j_ix = 0
        job_label_snap = TT_NON_JOB_SENTINEL
    j_ix = min(max(j_ix, 0), len(job_options) - 1)
    nj_ix = NON_JOB_CATEGORY_OPTIONS.index(cur_nj) if cur_nj in NON_JOB_CATEGORY_OPTIONS else 0
    _init_row_snap_from_ent(te_id, ent, job_label_snap, cur_nj)

    autosave = bool(st.session_state.get(TT_AUTOSAVE_KEY))
    acb = _autosave_callback_factory(te_id)
    ch_as = {"on_change": acb} if autosave else {}

    hstep = _hours_step(fast=fast)
    del_label = "Clear" if fast else "Delete"
    del_help = "Remove this time entry" if fast else "Delete this time entry"

    def _save_del_row() -> None:
        n_action = 3 if from_table_panel else 2
        cols = st.columns(n_action, gap="small")
        with cols[0]:
            if st.button(
                "Save",
                key=f"tt_sv_{te_id}",
                use_container_width=True,
                help="Save this row",
            ):
                ok, err = _persist_time_entry_row(te_id, job_label_to_id)
                if ok:
                    st.success("Updated.")
                    if from_table_panel:
                        st.session_state.pop(TT_EDIT_ID_KEY, None)
                    st.rerun()
                elif err:
                    if err.startswith("Pick a job"):
                        st.warning(err)
                    else:
                        st.error(err)
        with cols[1]:
            if st.button(
                del_label,
                key=f"tt_del_{te_id}",
                use_container_width=True,
                help=del_help,
            ):
                try:
                    delete_rows("time_entries", {"id": te_id})
                    _clear_row_snap(te_id)
                    if from_table_panel:
                        st.session_state.pop(TT_EDIT_ID_KEY, None)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Delete failed: {exc}")
        if from_table_panel:
            with cols[2]:
                if st.button(
                    "Close",
                    key=f"tt_close_{te_id}",
                    use_container_width=True,
                    help="Leave edit panel without navigating away",
                ):
                    st.session_state.pop(TT_EDIT_ID_KEY, None)
                    st.rerun()

    st.markdown('<p class="ips-tt-field-label">Job</p>', unsafe_allow_html=True)
    st.selectbox(
        "Job",
        job_options,
        index=j_ix,
        key=f"tt_job_{te_id}",
        label_visibility="collapsed",
        **ch_as,
    )
    st.markdown(
        '<p class="ips-tt-nj-sep">— or —</p><p class="ips-tt-field-label">Non-job category</p>',
        unsafe_allow_html=True,
    )
    st.selectbox(
        "Non-job category",
        NON_JOB_CATEGORY_OPTIONS,
        index=nj_ix,
        key=f"tt_nj_{te_id}",
        label_visibility="collapsed",
        **ch_as,
    )
    _nj = str(st.session_state.get(f"tt_nj_{te_id}") or "").strip()
    if _nj:
        st.markdown(_non_job_badge_html(_nj), unsafe_allow_html=True)
    ch, cn = st.columns([0.45, 1.0], gap="small")
    with ch:
        st.markdown('<p class="ips-tt-field-label">Hrs</p>', unsafe_allow_html=True)
        st.number_input(
            "Hours",
            min_value=0.0,
            max_value=24.0,
            value=float(ent.get("hours", 0) or 0),
            step=hstep,
            format="%.2f",
            key=f"tt_h_{te_id}",
            label_visibility="collapsed",
            **ch_as,
        )
    with cn:
        st.markdown('<p class="ips-tt-field-label">Notes</p>', unsafe_allow_html=True)
        st.text_input(
            "Notes",
            value=str(ent.get("notes") or ""),
            key=f"tt_n_{te_id}",
            label_visibility="collapsed",
            placeholder="Notes",
            **ch_as,
        )
    _save_del_row()


def _render_new_entry_form(
    employee_id: str,
    work_date_iso: str,
    job_labels_sorted: list[str],
    job_label_to_id: dict[str, str],
    default_job_label: str | None,
    entries_for_day: list[dict],
    *,
    fast: bool,
) -> None:
    job_options = [TT_NON_JOB_SENTINEL] + list(job_labels_sorted)
    d0 = 0
    if default_job_label and default_job_label in job_labels_sorted:
        d0 = 1 + job_labels_sorted.index(default_job_label)
    d0 = min(max(d0, 0), len(job_options) - 1)

    def_h = _tt_default_hours()
    hstep = _hours_step(fast=fast)
    dup_label = "Dup" if fast else "Duplicate"
    _k_j = f"tt_newj_{employee_id}_{work_date_iso}"
    _k_nj = f"tt_newnj_{employee_id}_{work_date_iso}"
    _k_h = f"tt_newh_{employee_id}_{work_date_iso}"
    _k_n = f"tt_newn_{employee_id}_{work_date_iso}"

    def _on_add() -> None:
        job_pick = st.session_state.get(_k_j)
        nj = str(st.session_state.get(_k_nj) or "").strip()
        hrs = float(st.session_state.get(_k_h) or 0)
        note = str(st.session_state.get(_k_n) or "").strip()
        if not isinstance(job_pick, str):
            st.error("Invalid job selection.")
            st.stop()
        if job_pick and job_pick != TT_NON_JOB_SENTINEL:
            jid = job_label_to_id.get(job_pick)
            if not jid:
                st.error("Invalid job.")
                st.stop()
            payload = {
                "employee_id": employee_id,
                "job_id": jid,
                "non_job_code": None,
                "work_date": work_date_iso[:10],
                "hours": float(hrs),
                "notes": note,
                "created_by": current_profile().get("id"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            if not nj:
                st.warning("Pick a job or select a non-job category.")
                st.stop()
            payload = {
                "employee_id": employee_id,
                "job_id": None,
                "non_job_code": nj,
                "work_date": work_date_iso[:10],
                "hours": float(hrs),
                "notes": note,
                "created_by": current_profile().get("id"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        if hrs <= 0:
            st.error("Enter hours greater than zero.")
            st.stop()
        try:
            insert_row("time_entries", payload)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not add (duplicate for this day?): {exc}")

    def _on_dup() -> None:
        src = entries_for_day[-1] if entries_for_day else None
        if src:
            sjid = str(src.get("job_id") or "").strip()
            snj = str(src.get("non_job_code") or "").strip()
            hrs = float(src.get("hours") or 0) or def_h
            note = str(src.get("notes") or "").strip()
            if sjid:
                slabel = _job_label_for_id(job_label_to_id, sjid)
                if not slabel:
                    st.error("Could not resolve job for duplicate.")
                    st.stop()
                jid = job_label_to_id.get(slabel)
                if not jid:
                    st.error("Invalid job on source row.")
                    st.stop()
                payload = {
                    "employee_id": employee_id,
                    "job_id": jid,
                    "non_job_code": None,
                    "work_date": work_date_iso[:10],
                    "hours": float(hrs),
                    "notes": note,
                    "created_by": current_profile().get("id"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            elif snj:
                payload = {
                    "employee_id": employee_id,
                    "job_id": None,
                    "non_job_code": snj,
                    "work_date": work_date_iso[:10],
                    "hours": float(hrs),
                    "notes": note,
                    "created_by": current_profile().get("id"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                st.error("Invalid source row.")
                st.stop()
        else:
            if default_job_label and default_job_label in job_label_to_id:
                jid = job_label_to_id[default_job_label]
                hrs = float(def_h)
                note = ""
                payload = {
                    "employee_id": employee_id,
                    "job_id": jid,
                    "non_job_code": None,
                    "work_date": work_date_iso[:10],
                    "hours": float(hrs),
                    "notes": note,
                    "created_by": current_profile().get("id"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                st.error("No line to copy — pick a filter job, add a row, or use non-job category.")
                st.stop()
        if hrs <= 0:
            st.error("Hours must be greater than zero.")
            st.stop()
        try:
            insert_row("time_entries", payload)
            st.rerun()
        except Exception as exc:
            st.error(f"Duplicate not added (same line this day?): {exc}")

    st.markdown('<div class="ips-tt-new-block">', unsafe_allow_html=True)
    st.markdown('<p class="ips-tt-field-label">Job</p>', unsafe_allow_html=True)
    st.selectbox(
        "Job",
        job_options,
        index=d0,
        key=_k_j,
        label_visibility="collapsed",
    )
    st.markdown(
        '<p class="ips-tt-nj-sep">— or —</p><p class="ips-tt-field-label">Non-job category</p>',
        unsafe_allow_html=True,
    )
    st.selectbox(
        "Non-job category",
        NON_JOB_CATEGORY_OPTIONS,
        index=0,
        key=_k_nj,
        label_visibility="collapsed",
    )
    r1, r2 = st.columns([0.45, 1.0], gap="small")
    with r1:
        st.markdown('<p class="ips-tt-field-label">Hrs</p>', unsafe_allow_html=True)
        st.number_input(
            "Hours",
            min_value=0.0,
            max_value=24.0,
            value=float(def_h),
            step=hstep,
            key=_k_h,
            label_visibility="collapsed",
        )
    with r2:
        st.markdown('<p class="ips-tt-field-label">Notes</p>', unsafe_allow_html=True)
        st.text_input(
            "Notes",
            value="",
            key=_k_n,
            label_visibility="collapsed",
            placeholder="Notes",
        )
    ba, bd = st.columns(2, gap="small")
    with ba:
        if st.button(
            "Add",
            key=f"tt_add_{employee_id}_{work_date_iso}",
            use_container_width=True,
            help="Add time entry",
        ):
            _on_add()
    with bd:
        dup_key = f"tt_dup_{employee_id}_{work_date_iso}"
        if st.button(
            dup_label,
            key=dup_key,
            use_container_width=True,
            help="Copy last line this day (or filter job + default hours)",
        ):
            _on_dup()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_day_column_body(
    *,
    d: date,
    eid: str,
    idx: dict,
    fj_id: str | None,
    job_id_to_label: dict[str, str],
    show_day_heading: bool,
) -> float:
    """Day cell: hours subtotal, compact job summary, and control to set Quick Actions day context."""
    wd = d.isoformat()
    ents_all = idx.get((eid, wd), [])
    ents_show = [e for e in ents_all if not fj_id or str(e.get("job_id")) == fj_id]
    day_sum = sum(float(e.get("hours", 0) or 0) for e in ents_show)

    sel_k = _tt_qa_day_key(eid)
    sel_wd = str(st.session_state.get(sel_k) or "")[:10]
    is_sel = sel_wd == wd and str(st.session_state.get(TT_OPEN_EMP_PANEL_KEY) or "") == eid

    if show_day_heading:
        st.markdown(
            f'<div class="ips-tt-day-head">{d.strftime("%a %m/%d")}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="ips-tt-day-sum">{day_sum:.1f} h</div>',
        unsafe_allow_html=True,
    )

    parts: list[str] = []
    for e in ents_show[:6]:
        h = float(e.get("hours", 0) or 0)
        jid = str(e.get("job_id") or "").strip()
        nj = str(e.get("non_job_code") or "").strip()
        if jid:
            lab = str(job_id_to_label.get(jid) or "?")
            short = lab[:18] + ("…" if len(lab) > 18 else "")
            parts.append(f"{short} {h:.1f}h")
        elif nj:
            parts.append(f"{nj} {h:.1f}h")
    summary = " · ".join(parts) if parts else ""
    if summary:
        st.caption(summary[:260] + ("…" if len(summary) > 260 else ""))

    span_cls = "ips-tt-day-cell ips-tt-day-summary"
    if is_sel:
        span_cls += " ips-tt-day-selected"

    with st.container(border=True):
        st.markdown(f'<span class="{span_cls}" aria-hidden="true"></span>', unsafe_allow_html=True)
        btn_label = "Selected for Quick Actions" if is_sel else "Use this day"
        if st.button(
            btn_label,
            key=f"tt_selday_{eid}_{wd}",
            use_container_width=True,
            type="primary" if is_sel else "secondary",
        ):
            st.session_state[sel_k] = wd
            st.session_state[TT_OPEN_EMP_PANEL_KEY] = eid
            st.session_state.pop(f"tt_qa_dpick_{eid}", None)
            st.rerun()

    return day_sum


def _render_readonly_pivot(
    visible_emps: list[dict],
    days: list[date],
    idx: dict[tuple[str, str], list[dict]],
    job_id_to_label: dict[str, str],
) -> None:
    rows = []
    for emp in visible_emps:
        eid = str(emp.get("id"))
        r: dict = {"Employee": emp.get("name", "")}
        total = 0.0
        for d in days:
            wd = d.isoformat()
            ents = idx.get((eid, wd), [])
            h = sum(float(e.get("hours", 0) or 0) for e in ents)
            _labels: set[str] = set()
            for e in ents:
                jid = str(e.get("job_id") or "").strip()
                if jid:
                    _labels.add(job_id_to_label.get(jid, "?"))
                else:
                    nj = str(e.get("non_job_code") or "").strip()
                    if nj:
                        _labels.add(nj)
            jobs = ", ".join(sorted(_labels))
            r[d.strftime("%a %m/%d")] = f"{h:.1f} h" + (f" ({jobs})" if jobs else "")
            total += h
        r["Σ Week"] = f"{total:.1f}"
        rows.append(r)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
