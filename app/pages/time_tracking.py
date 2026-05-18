"""
Timekeeping page -- professional weekly time entry management.
Header card + week nav + employee table + expandable detail panel.
"""
from __future__ import annotations

import html
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Service imports with fallbacks
# ---------------------------------------------------------------------------
try:
    from mobile_ui import ensure_narrow_viewport_detected
except ImportError:
    try:
        from app.mobile_ui import ensure_narrow_viewport_detected  # type: ignore
    except ImportError:
        def ensure_narrow_viewport_detected() -> None:  # type: ignore
            pass

from auth import current_profile, current_role
from db import delete_rows, fetch_one, fetch_table, fetch_table_admin, insert_row, update_rows

try:
    from db import fetch_jobs_with_order_fallback
except ImportError:
    from app.db import fetch_jobs_with_order_fallback  # type: ignore

try:
    from services.job_service import build_job_dropdown_label_maps, sort_jobs_by_number_then_name
except ImportError:
    from app.services.job_service import (  # type: ignore
        build_job_dropdown_label_maps,
        sort_jobs_by_number_then_name,
    )

try:
    from services.time_grid_service import (
        fetch_time_entries_between,
        index_by_employee_date,
        monday_of_week,
        upsert_time_entry,
        week_dates,
    )
except ImportError:
    from app.services.time_grid_service import (  # type: ignore
        fetch_time_entries_between,
        index_by_employee_date,
        monday_of_week,
        upsert_time_entry,
        week_dates,
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TT_EDIT_ROLES = frozenset({"admin", "manager", "pm", "employee"})
NON_JOB_CATEGORY_OPTIONS = ["SHOP", "ADMIN", "TRAINING", "SAFETY", "PTO", "HOLIDAY", "TRAVEL"]
_OT_THRESHOLD = 40.0
_CLOSED_STATUSES = frozenset({"closed", "complete", "completed", "cancelled", "archived", "close", "done"})
_NO_ENTRY_LABEL = "(No entry -- skip)"

# Stable session-state keys
_TK_EMP = "selected_timekeeping_employee_id"
_TK_WEEK = "selected_timekeeping_week_start"
_TK_VIEW = "timekeeping_view_mode"
_TK_EDIT = "timekeeping_edit_mode"

# ---------------------------------------------------------------------------
# CSS  (dark-professional / IPS brand palette)
# ---------------------------------------------------------------------------
_CSS = """
<style>
/* ======================================================
   Timekeeping page  -- scoped via span marker classes
   ====================================================== */

/* ---- Header card ---------------------------------------- */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-header) {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    border: 1px solid rgba(148,163,184,.22) !important;
    border-radius: 14px !important;
    padding: 18px 22px 16px 22px !important;
    margin-bottom: 14px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,.35) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-header) label[data-testid="stWidgetLabel"] {
    display: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-header) [data-testid="stElementContainer"] {
    margin-bottom: 0 !important;
}
/* Week nav buttons */
div[data-testid="stHorizontalBlock"]:has(span.tk-week-nav) button {
    min-height: 1.7rem !important;
    padding: 0.12rem 0.8rem !important;
    font-size: 0.8rem !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
}
/* Filter bar */
div[data-testid="stHorizontalBlock"]:has(span.tk-filter-bar) {
    background: #1e293b !important;
    border: 1px solid rgba(148,163,184,.18) !important;
    border-radius: 10px !important;
    padding: 8px 14px !important;
    margin-bottom: 10px !important;
    align-items: center !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-filter-bar) label[data-testid="stWidgetLabel"] {
    display: none !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-filter-bar) button {
    min-height: 1.7rem !important;
    padding: 0.1rem 0.8rem !important;
    font-size: 0.8rem !important;
    border-radius: 7px !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-filter-bar) [data-testid="stTextInput"] input,
div[data-testid="stHorizontalBlock"]:has(span.tk-filter-bar) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    min-height: 1.7rem !important;
    font-size: 0.82rem !important;
}
/* ---- Employee table container ----------------------- */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-table-wrap) {
    background: #1e293b !important;
    border: 1px solid rgba(148,163,184,.2) !important;
    border-radius: 12px !important;
    padding: 0 !important;
    overflow: hidden !important;
    margin-bottom: 2px !important;
}
/* Table header row */
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-hdr) {
    background: rgba(15,23,42,.9) !important;
    padding: 5px 14px !important;
    border-bottom: 1px solid rgba(148,163,184,.2) !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-hdr) > div[data-testid="column"] {
    padding: 3px 5px !important;
}
/* Table data rows */
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-row) {
    padding: 2px 14px !important;
    border-bottom: 1px solid rgba(71,85,105,.28) !important;
    align-items: center !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-row.tk-even) {
    background: rgba(30,41,59,.65) !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-row.tk-odd) {
    background: rgba(22,32,48,.65) !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-row):hover {
    background: rgba(59,130,246,.10) !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-row.tk-sel) {
    background: rgba(59,130,246,.15) !important;
    border-left: 3px solid #3b82f6 !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-row) > div[data-testid="column"] {
    padding: 5px 5px !important;
    align-self: center !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-row) button {
    min-height: 1.5rem !important;
    max-height: 1.75rem !important;
    padding: 0.05rem 0.45rem !important;
    font-size: 0.74rem !important;
    border-radius: 6px !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-row) label[data-testid="stWidgetLabel"] {
    display: none !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-row) p {
    font-size: 0.82rem !important;
    margin: 0 !important;
    line-height: 1.3 !important;
}
/* Table footer */
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-footer) {
    background: rgba(15,23,42,.6) !important;
    padding: 5px 14px !important;
    border-top: 1px solid rgba(71,85,105,.35) !important;
    border-radius: 0 0 12px 12px !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-footer) p {
    font-size: 0.77rem !important;
    margin: 0 !important;
}
/* ---- Detail panel ----------------------------------- */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-detail) {
    background: #1e293b !important;
    border: 1px solid #3b82f6 !important;
    border-left: 4px solid #3b82f6 !important;
    border-radius: 0 12px 12px 12px !important;
    padding: 18px 20px 20px 20px !important;
    margin-top: 0 !important;
    box-shadow: 0 4px 20px rgba(59,130,246,.10) !important;
}
/* Detail panel compact inputs */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-detail) [data-testid="stNumberInput"] input {
    min-height: 1.5rem !important;
    font-size: 0.82rem !important;
    padding: 0.04rem 0.28rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-detail) [data-testid="stTextInput"] input {
    min-height: 1.5rem !important;
    font-size: 0.82rem !important;
    padding: 0.04rem 0.28rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-detail) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    min-height: 1.5rem !important;
    font-size: 0.82rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-detail) label[data-testid="stWidgetLabel"] {
    display: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-detail) [data-testid="stElementContainer"] {
    margin-bottom: 0.07rem !important;
}
/* Detail action buttons */
div[data-testid="stHorizontalBlock"]:has(span.tk-detail-actions) button {
    border-radius: 7px !important;
    font-size: 0.8rem !important;
    min-height: 1.75rem !important;
    font-weight: 600 !important;
}
/* Daily rows header */
div[data-testid="stHorizontalBlock"]:has(span.tk-day-hdr) {
    background: rgba(15,23,42,.55) !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 4px 4px !important;
    border-bottom: 1px solid rgba(71,85,105,.5) !important;
}
/* Daily rows */
div[data-testid="stHorizontalBlock"]:has(span.tk-day-row) {
    border-bottom: 1px solid rgba(71,85,105,.22) !important;
    padding: 2px 4px !important;
    align-items: center !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-day-row.tk-today-row) {
    background: rgba(59,130,246,.07) !important;
    border-left: 2px solid rgba(56,189,248,.5) !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-day-row) p {
    font-size: 0.82rem !important;
    margin: 0 !important;
    line-height: 1.3 !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-day-row) [data-testid="stNumberInput"] input {
    min-height: 1.45rem !important;
    font-size: 0.8rem !important;
    padding: 0.03rem 0.25rem !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-day-row) [data-testid="stTextInput"] input {
    min-height: 1.45rem !important;
    font-size: 0.8rem !important;
    padding: 0.03rem 0.25rem !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-day-row) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    min-height: 1.45rem !important;
    font-size: 0.8rem !important;
}
/* ---- Typography helpers ----------------------------- */
.tk-title { font-size:1.45rem;font-weight:800;color:#f1f5f9;margin:0;letter-spacing:-0.01em; }
.tk-subtitle { font-size:0.78rem;color:#94a3b8;margin:0.1rem 0 0 0; }
.tk-week-range { font-size:1rem;font-weight:700;color:#e2e8f0;margin:0; }
.tk-week-num { font-size:0.72rem;color:#64748b;margin:0; }
.tk-hdr { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#64748b;margin:0;padding:0; }
.tk-cell { font-size:0.82rem;color:#cbd5e1;margin:0; }
.tk-cell-name { font-size:0.86rem;font-weight:600;color:#f1f5f9;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.tk-cell-name-sel { color:#93c5fd !important; }
.tk-num { font-size:0.82rem;color:#e2e8f0;font-variant-numeric:tabular-nums;margin:0; }
.tk-num-warn { color:#fbbf24 !important;font-weight:700 !important; }
.tk-ft-total { font-size:0.78rem;font-weight:700;color:#94a3b8;margin:0; }
.tk-emp-name { font-size:1.1rem;font-weight:800;color:#f1f5f9;margin:0; }
.tk-emp-dept { font-size:0.76rem;color:#94a3b8;margin:0; }
.tk-metric-lbl { font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin:0; }
.tk-metric-val { font-size:1.1rem;font-weight:700;color:#f1f5f9;font-variant-numeric:tabular-nums;margin:0; }
.tk-day-lbl { font-size:0.82rem;font-weight:700;color:#cbd5e1;margin:0; }
.tk-day-date { font-size:0.73rem;color:#64748b;margin:0; }
.tk-day-today { color:#38bdf8 !important; }
.tk-total-val { font-size:0.82rem;font-weight:600;color:#e2e8f0;font-variant-numeric:tabular-nums;margin:0; }
.tk-footer-note { font-size:0.71rem;color:#475569;font-style:italic;margin:0.5rem 0 0 0; }
.tk-hint { font-size:0.82rem;color:#475569;font-style:italic;text-align:center;padding:1.2rem 0; }
/* Status pill badges */
.tk-badge {
    display:inline-block;font-size:10px;font-weight:700;
    padding:2px 9px;border-radius:20px;letter-spacing:.04em;white-space:nowrap;
}
.tk-draft    { background:rgba(100,116,139,.2);color:#94a3b8;border:1px solid rgba(100,116,139,.3); }
.tk-pending  { background:rgba(251,191,36,.15);color:#fbbf24;border:1px solid rgba(251,191,36,.3); }
.tk-approved { background:rgba(34,197,94,.15);color:#4ade80;border:1px solid rgba(34,197,94,.25); }
.tk-rejected { background:rgba(248,113,113,.15);color:#f87171;border:1px solid rgba(248,113,113,.25); }
/* Responsive */
@media(max-width:768px) {
    .tk-title { font-size:1.1rem !important; }
    div[data-testid="stHorizontalBlock"]:has(span.tk-tbl-row) button { min-height:2rem !important; }
}
</style>
"""


def _inject_styles() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def _load_employees() -> list[dict]:
    try:
        rows = list(fetch_table("employees", limit=2000, order_by="name") or [])
    except Exception:
        rows = []
    return [e for e in rows if e.get("is_active", True) is not False and e.get("id")]


def _load_jobs() -> list[dict]:
    role = current_role()
    prefer_admin = role in ("admin", "manager")
    fn = fetch_table_admin if prefer_admin else fetch_table
    for ob in ("job_number", "job_name", None):
        try:
            rows = list(fn("jobs", columns="*", limit=5000, order_by=ob) or [])
            if rows:
                return sort_jobs_by_number_then_name(rows)
        except Exception:
            pass
    try:
        return sort_jobs_by_number_then_name(
            list(fetch_jobs_with_order_fallback(limit=5000) or [])
        )
    except Exception:
        return []


def _is_active_job(j: dict) -> bool:
    s = str(j.get("status") or j.get("job_status") or "").strip().lower()
    return not s or s not in _CLOSED_STATUSES


def _build_job_options(jobs: list[dict]) -> tuple[list[str], dict[str, str]]:
    """Return (sorted_labels, label_to_id)."""
    _, lbl_to_id, sorted_labels = build_job_dropdown_label_maps(jobs)
    # Add non-job categories
    nj_labels = [f"NON-JOB -- {c}" for c in NON_JOB_CATEGORY_OPTIONS]
    all_labels = [_NO_ENTRY_LABEL] + sorted_labels + nj_labels
    return all_labels, lbl_to_id


def _resolve_job_label(label: str, lbl_to_id: dict[str, str]) -> tuple[str | None, str | None]:
    """Label -> (job_id, non_job_code)."""
    if not label or label == _NO_ENTRY_LABEL:
        return None, None
    if label.startswith("NON-JOB -- "):
        code = label[len("NON-JOB -- "):].strip()
        return None, code or None
    jid = str(lbl_to_id.get(label) or "").strip()
    return jid or None, None


def _time_type(ent: dict) -> str:
    s = str(ent.get("time_type") or "").strip().upper()
    return "OT" if s in ("OT", "O/T") else "ST"


def _emp_week_summary(eid: str, days: list[date], idx: dict) -> tuple[float, float]:
    """Return (st_hours, ot_hours) for the week."""
    st_h = ot_h = 0.0
    for d in days:
        for ent in idx.get((eid, d.isoformat()), []):
            h = float(ent.get("hours") or 0)
            if _time_type(ent) == "OT":
                ot_h += h
            else:
                st_h += h
    return st_h, ot_h


def _compute_status(st_h: float, ot_h: float) -> str:
    total = st_h + ot_h
    if total == 0:
        return "draft"
    if total < 32:
        return "pending"
    return "pending"


def _status_badge_html(status: str) -> str:
    label = status.title()
    css = {"draft": "tk-draft", "pending": "tk-pending", "approved": "tk-approved", "rejected": "tk-rejected"}.get(status, "tk-draft")
    return f'<span class="tk-badge {css}">{html.escape(label)}</span>'


def _week_label(week_start: date) -> str:
    end = week_start + timedelta(days=6)
    if week_start.month == end.month:
        return f"{week_start.strftime('%b %d')} \u2013 {end.strftime('%d, %Y')}"
    return f"{week_start.strftime('%b %d')} \u2013 {end.strftime('%b %d, %Y')}"


def _week_number(week_start: date) -> int:
    return week_start.isocalendar()[1]


# ---------------------------------------------------------------------------
# Row-level session state key helpers
# ---------------------------------------------------------------------------
def _rk(eid: str, day_iso: str, week_iso: str, field: str) -> str:
    """Stable widget key: tk_{eid8}_{day}_{week}_{field}"""
    return f"tk_{eid[:8]}_{day_iso}_{week_iso.replace('-','')}_{field}"


def _clear_row_state(eid: str, days: list[date], week_start: date) -> None:
    week_iso = week_start.isoformat()
    for d in days:
        for f in ("job", "st", "ot", "notes"):
            st.session_state.pop(_rk(eid, d.isoformat(), week_iso, f), None)


# ---------------------------------------------------------------------------
# Save logic
# ---------------------------------------------------------------------------
def _save_all_rows(
    eid: str,
    days: list[date],
    week_start: date,
    lbl_to_id: dict[str, str],
    uid: Any,
) -> list[str]:
    """Upsert all non-empty rows for this employee/week. Returns list of error strings."""
    ts_now = datetime.now(timezone.utc).isoformat()
    week_iso = week_start.isoformat()
    errors: list[str] = []
    for d in days:
        day_iso = d.isoformat()
        job_lbl = str(st.session_state.get(_rk(eid, day_iso, week_iso, "job"), "") or "").strip()
        st_hrs = float(st.session_state.get(_rk(eid, day_iso, week_iso, "st"), 0.0) or 0.0)
        ot_hrs = float(st.session_state.get(_rk(eid, day_iso, week_iso, "ot"), 0.0) or 0.0)
        notes = str(st.session_state.get(_rk(eid, day_iso, week_iso, "notes"), "") or "").strip()

        if not job_lbl or job_lbl == _NO_ENTRY_LABEL:
            continue

        job_id, nj_code = _resolve_job_label(job_lbl, lbl_to_id)
        if not job_id and not nj_code:
            continue

        for hrs, ttype in [(st_hrs, "ST"), (ot_hrs, "OT")]:
            if hrs > 0:
                try:
                    upsert_time_entry(
                        employee_id=eid,
                        job_id=job_id,
                        work_date=d,
                        hours=hrs,
                        notes=notes,
                        created_by=uid,
                        updated_at_iso=ts_now,
                        non_job_code=nj_code,
                        time_type=ttype,
                    )
                except Exception as exc:
                    errors.append(f"{d.strftime('%a')}/{ttype}: {exc}")

    return errors


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def _render_header(week_start: date, days: list[date]) -> None:
    with st.container(border=True):
        st.markdown('<span class="tk-header" aria-hidden="true"></span>', unsafe_allow_html=True)
        left, center, right = st.columns([2.2, 2.8, 2.0], gap="small")

        with left:
            st.markdown(
                '<p class="tk-title">&#x23F0; Timekeeping</p>'
                '<p class="tk-subtitle">View and edit employee weekly time entries.</p>',
                unsafe_allow_html=True,
            )

        with center:
            st.markdown('<span class="tk-week-nav" aria-hidden="true"></span>', unsafe_allow_html=True)
            n1, n2, n3 = st.columns(3, gap="small")
            with n1:
                if st.button("\u25c0 Prev", key="tk_prev_week", use_container_width=True):
                    st.session_state[_TK_WEEK] = (week_start - timedelta(days=7)).isoformat()
                    st.rerun()
            with n2:
                if st.button("This Week", key="tk_this_week", use_container_width=True, type="primary"):
                    st.session_state[_TK_WEEK] = monday_of_week(date.today()).isoformat()
                    st.rerun()
            with n3:
                if st.button("Next \u25ba", key="tk_next_week", use_container_width=True):
                    st.session_state[_TK_WEEK] = (week_start + timedelta(days=7)).isoformat()
                    st.rerun()

        with right:
            wnum = _week_number(week_start)
            st.markdown(
                f'<p class="tk-week-range">{html.escape(_week_label(week_start))}</p>'
                f'<p class="tk-week-num">Week {wnum}</p>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Filter bar
# ---------------------------------------------------------------------------
def _render_filter_bar(all_emps: list[dict]) -> tuple[str, list[str]]:
    """Returns (search_query, selected_dept_list)."""
    # Collect distinct departments
    depts = sorted({str(e.get("department") or "").strip() for e in all_emps if e.get("department")})
    dept_opts = ["All Departments"] + depts

    f1, f2, f3 = st.columns([3.0, 1.8, 0.85], gap="small")
    with f1:
        st.markdown('<span class="tk-filter-bar" aria-hidden="true"></span>', unsafe_allow_html=True)
        q = st.text_input(
            "Search",
            placeholder="Search employee...",
            key="tk_search",
            label_visibility="collapsed",
        )
    with f2:
        dept = st.selectbox(
            "Department",
            dept_opts,
            key="tk_dept_filter",
            label_visibility="collapsed",
        )
    with f3:
        export_clicked = st.button("Export", key="tk_export_btn", use_container_width=True)

    return str(q or "").strip().lower(), str(dept or "All Departments"), export_clicked


# ---------------------------------------------------------------------------
# Employee summary table
# ---------------------------------------------------------------------------
# Column weights: emp, dept, week-start, st, ot, total, status, action
_TBL_COLS = [2.3, 1.0, 0.9, 0.75, 0.75, 0.75, 0.85, 0.55]


def _render_employee_table(
    visible_emps: list[dict],
    days: list[date],
    week_start: date,
    idx: dict,
    can_edit: bool,
) -> str | None:
    """Render the employee summary table. Returns selected employee_id or None."""
    selected_eid = str(st.session_state.get(_TK_EMP) or "")

    with st.container(border=True):
        st.markdown('<span class="tk-table-wrap" aria-hidden="true"></span>', unsafe_allow_html=True)

        # -- Header row --
        hcols = st.columns(_TBL_COLS, gap="small")
        labels = ["Employee", "Department", "Week Start", "S/T (Hrs)", "O/T (Hrs)", "Total Hrs", "Status", ""]
        with hcols[0]:
            st.markdown('<span class="tk-tbl-hdr" aria-hidden="true"></span>', unsafe_allow_html=True)
        for lbl, col in zip(labels, hcols):
            with col:
                st.markdown(f'<p class="tk-hdr">{html.escape(lbl)}</p>', unsafe_allow_html=True)

        # -- Data rows --
        new_sel: str | None = selected_eid or None
        for ri, emp in enumerate(visible_emps):
            eid = str(emp.get("id"))
            nm = str(emp.get("name") or "").strip() or "—"
            dept = str(emp.get("department") or "").strip() or "—"
            is_sel = eid == selected_eid
            is_over = False
            zebra = "tk-even" if ri % 2 == 0 else "tk-odd"
            sel_cls = " tk-sel" if is_sel else ""

            st_h, ot_h = _emp_week_summary(eid, days, idx)
            total_h = st_h + ot_h
            is_over = total_h > _OT_THRESHOLD
            status = _compute_status(st_h, ot_h)

            rcols = st.columns(_TBL_COLS, gap="small")
            with rcols[0]:
                name_cls = "tk-cell-name" + (" tk-cell-name-sel" if is_sel else "")
                st.markdown(
                    f'<span class="tk-tbl-row {zebra}{sel_cls}" aria-hidden="true"></span>'
                    f'<p class="{name_cls}" title="{html.escape(nm, quote=True)}">'
                    f'{html.escape(nm)}</p>',
                    unsafe_allow_html=True,
                )
            with rcols[1]:
                st.markdown(f'<p class="tk-cell">{html.escape(dept)}</p>', unsafe_allow_html=True)
            with rcols[2]:
                st.markdown(f'<p class="tk-cell">{week_start.strftime("%m/%d/%Y")}</p>', unsafe_allow_html=True)
            with rcols[3]:
                st.markdown(f'<p class="tk-num">{st_h:.1f}</p>', unsafe_allow_html=True)
            with rcols[4]:
                ot_cls = "tk-num tk-num-warn" if is_over and ot_h > 0 else "tk-num"
                st.markdown(f'<p class="{ot_cls}">{ot_h:.1f}</p>', unsafe_allow_html=True)
            with rcols[5]:
                tot_cls = "tk-num tk-num-warn" if is_over else "tk-num"
                st.markdown(f'<p class="{tot_cls}">{total_h:.1f}</p>', unsafe_allow_html=True)
            with rcols[6]:
                st.markdown(_status_badge_html(status), unsafe_allow_html=True)
            with rcols[7]:
                btn_lbl = "\u25bc Open" if is_sel else "\u25b6 View"
                btn_tp = "primary" if is_sel else "secondary"
                if st.button(
                    btn_lbl,
                    key=f"tk_view_{eid}_{week_start.isoformat()}",
                    type=btn_tp,
                    use_container_width=True,
                ):
                    new_sel = None if is_sel else eid

        # -- Footer totals row --
        total_st = sum(_emp_week_summary(str(e.get("id")), days, idx)[0] for e in visible_emps)
        total_ot = sum(_emp_week_summary(str(e.get("id")), days, idx)[1] for e in visible_emps)
        fcols = st.columns(_TBL_COLS, gap="small")
        with fcols[0]:
            st.markdown(
                '<span class="tk-tbl-footer" aria-hidden="true"></span>'
                f'<p class="tk-ft-total">{len(visible_emps)} employee{"s" if len(visible_emps) != 1 else ""}</p>',
                unsafe_allow_html=True,
            )
        with fcols[3]:
            st.markdown(f'<p class="tk-ft-total">{total_st:.1f}</p>', unsafe_allow_html=True)
        with fcols[4]:
            st.markdown(f'<p class="tk-ft-total">{total_ot:.1f}</p>', unsafe_allow_html=True)
        with fcols[5]:
            st.markdown(f'<p class="tk-ft-total">{total_st + total_ot:.1f}</p>', unsafe_allow_html=True)

    # Apply selection change after all buttons rendered
    if new_sel != (selected_eid or None):
        if new_sel:
            st.session_state[_TK_EMP] = new_sel
            st.session_state[_TK_VIEW] = "detail"
            st.session_state[_TK_EDIT] = True
        else:
            st.session_state.pop(_TK_EMP, None)
            st.session_state[_TK_VIEW] = "table"
            st.session_state[_TK_EDIT] = False
        st.rerun()

    return selected_eid or None


# ---------------------------------------------------------------------------
# Daily time rows (inside detail panel)
# ---------------------------------------------------------------------------
# Column weights: day, date, job, st, ot, total, notes, comment
_DAY_COLS = [0.75, 0.72, 3.3, 0.82, 0.82, 0.68, 2.0, 0.42]


def _render_daily_rows(
    eid: str,
    days: list[date],
    week_start: date,
    idx: dict,
    job_options: list[str],
    lbl_to_id: dict[str, str],
) -> None:
    today = date.today()
    week_iso = week_start.isoformat()

    # Day table header
    hcols = st.columns(_DAY_COLS, gap="small")
    with hcols[0]:
        st.markdown('<span class="tk-day-hdr" aria-hidden="true"></span>', unsafe_allow_html=True)
    for lbl, col in zip(["Day", "Date", "Job / Description", "S/T", "O/T", "Total", "Notes", ""], hcols):
        with col:
            st.markdown(f'<p class="tk-hdr">{html.escape(lbl)}</p>', unsafe_allow_html=True)

    for d in days:
        day_iso = d.isoformat()
        is_today = d == today
        today_cls = " tk-today-row" if is_today else ""

        # Existing entries for this day (pick first ST and first OT)
        entries = idx.get((eid, day_iso), [])
        st_ent = next((e for e in entries if _time_type(e) == "ST"), None)
        ot_ent = next((e for e in entries if _time_type(e) == "OT"), None)

        # Determine primary job label from existing entry
        def _label_for_entry(ent: dict | None) -> str:
            if not ent:
                return _NO_ENTRY_LABEL
            jid = str(ent.get("job_id") or "").strip()
            nj = str(ent.get("non_job_code") or "").strip()
            if jid:
                for lbl, lid in lbl_to_id.items():
                    if str(lid) == jid:
                        return lbl
                return _NO_ENTRY_LABEL
            if nj:
                return f"NON-JOB -- {nj}"
            return _NO_ENTRY_LABEL

        primary_ent = st_ent or ot_ent
        existing_job_lbl = _label_for_entry(primary_ent)
        existing_st = float(st_ent.get("hours") or 0) if st_ent else 0.0
        existing_ot = float(ot_ent.get("hours") or 0) if ot_ent else 0.0
        existing_notes = str((primary_ent or {}).get("notes") or "").strip()

        # Widget keys
        jk = _rk(eid, day_iso, week_iso, "job")
        stk = _rk(eid, day_iso, week_iso, "st")
        otk = _rk(eid, day_iso, week_iso, "ot")
        nk = _rk(eid, day_iso, week_iso, "notes")

        # Safe default job index
        if existing_job_lbl in job_options:
            j_idx = job_options.index(existing_job_lbl)
        else:
            j_idx = 0

        dcols = st.columns(_DAY_COLS, gap="small")
        with dcols[0]:
            day_lbl_cls = "tk-day-lbl" + (" tk-day-today" if is_today else "")
            st.markdown(
                f'<span class="tk-day-row{today_cls}" aria-hidden="true"></span>'
                f'<p class="{day_lbl_cls}">{d.strftime("%a")}</p>',
                unsafe_allow_html=True,
            )
        with dcols[1]:
            date_lbl_cls = "tk-day-date" + (" tk-day-today" if is_today else "")
            st.markdown(f'<p class="{date_lbl_cls}">{d.strftime("%m/%d")}</p>', unsafe_allow_html=True)
        with dcols[2]:
            sel_job = st.selectbox(
                "Job",
                job_options,
                index=j_idx,
                key=jk,
                label_visibility="collapsed",
            )
        with dcols[3]:
            new_st = st.number_input(
                "S/T", min_value=0.0, max_value=24.0,
                value=existing_st, step=0.25, format="%.2f",
                key=stk, label_visibility="collapsed",
            )
        with dcols[4]:
            new_ot = st.number_input(
                "O/T", min_value=0.0, max_value=24.0,
                value=existing_ot, step=0.25, format="%.2f",
                key=otk, label_visibility="collapsed",
            )
        with dcols[5]:
            row_total = float(new_st) + float(new_ot)
            st.markdown(
                f'<p class="tk-total-val">{row_total:.1f}</p>',
                unsafe_allow_html=True,
            )
        with dcols[6]:
            st.text_input(
                "Notes", value=existing_notes, key=nk,
                label_visibility="collapsed", placeholder="Notes...",
            )
        with dcols[7]:
            has_entry = bool(st_ent or ot_ent)
            if has_entry:
                if st.button(
                    "\U0001f4ac",
                    key=f"tk_cmt_{eid[:8]}_{day_iso}",
                    help=f"Notes: {existing_notes or 'none'}",
                ):
                    pass  # comment icon -- no-op display


# ---------------------------------------------------------------------------
# Detail panel
# ---------------------------------------------------------------------------
def _render_detail_panel(
    eid: str,
    all_emps: list[dict],
    days: list[date],
    week_start: date,
    idx: dict,
    job_options: list[str],
    lbl_to_id: dict[str, str],
    uid: Any,
    can_edit: bool,
) -> None:
    emp = next((e for e in all_emps if str(e.get("id")) == eid), None)
    if not emp:
        st.warning("Selected employee not found.")
        st.session_state.pop(_TK_EMP, None)
        return

    nm = str(emp.get("name") or "").strip() or "—"
    dept = str(emp.get("department") or "").strip() or "—"
    st_h, ot_h = _emp_week_summary(eid, days, idx)
    total_h = st_h + ot_h
    status = _compute_status(st_h, ot_h)
    over = total_h > _OT_THRESHOLD

    # Last updated metadata from most recent entry
    entries_all: list[dict] = []
    for d in days:
        entries_all.extend(idx.get((eid, d.isoformat()), []))
    last_updated_str = "—"
    last_by = "—"
    if entries_all:
        latest = max(entries_all, key=lambda e: str(e.get("updated_at") or ""))
        raw_ts = str(latest.get("updated_at") or "")
        if raw_ts:
            try:
                dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                last_updated_str = dt.strftime("%b %d, %Y %I:%M %p")
            except Exception:
                last_updated_str = raw_ts[:19]
        last_by = str(latest.get("created_by") or "—")[:20]

    with st.container(border=True):
        st.markdown('<span class="tk-detail" aria-hidden="true"></span>', unsafe_allow_html=True)

        # ---- Detail panel header -------------------------------------------
        d1, d2, d3 = st.columns([2.5, 3.5, 2.0], gap="small")

        with d1:
            st.markdown(
                f'<p class="tk-emp-name">{html.escape(nm)}'
                f'&nbsp;&nbsp;{_status_badge_html(status)}</p>'
                f'<p class="tk-emp-dept">{html.escape(dept)}</p>',
                unsafe_allow_html=True,
            )

        with d2:
            over_note = f"  \u26a0 >{_OT_THRESHOLD:g}h" if over else ""
            st.markdown(
                f'<p class="tk-metric-lbl">\U0001f4c5 Week</p>'
                f'<p class="tk-cell">{html.escape(_week_label(week_start))}</p>',
                unsafe_allow_html=True,
            )
            mc1, mc2, mc3 = st.columns(3, gap="small")
            with mc1:
                st.markdown(f'<p class="tk-metric-lbl">S/T Total</p><p class="tk-metric-val">{st_h:.1f}h</p>', unsafe_allow_html=True)
            with mc2:
                ot_cls = "tk-metric-val tk-num-warn" if over else "tk-metric-val"
                st.markdown(f'<p class="tk-metric-lbl">O/T Total</p><p class="{ot_cls}">{ot_h:.1f}h</p>', unsafe_allow_html=True)
            with mc3:
                st.markdown(f'<p class="tk-metric-lbl">Total{over_note}</p><p class="tk-metric-val">{total_h:.1f}h</p>', unsafe_allow_html=True)

        with d3:
            st.markdown('<span class="tk-detail-actions" aria-hidden="true"></span>', unsafe_allow_html=True)
            if can_edit:
                if st.button(
                    "\U0001f4be Save Changes",
                    key=f"tk_save_{eid[:8]}_{week_start.isoformat()}",
                    type="primary",
                    use_container_width=True,
                ):
                    errs = _save_all_rows(eid, days, week_start, lbl_to_id, uid)
                    if errs:
                        st.error("Saved with errors:\n" + "\n".join(errs))
                    else:
                        _clear_row_state(eid, days, week_start)
                        try:
                            st.cache_data.clear()
                        except Exception:
                            pass
                        st.success("Week saved!")
                        st.rerun()
            if st.button(
                "\u2715 Close",
                key="tk_close_panel",
                type="secondary",
                use_container_width=True,
            ):
                st.session_state.pop(_TK_EMP, None)
                st.session_state[_TK_VIEW] = "table"
                st.session_state[_TK_EDIT] = False
                st.rerun()

        st.divider()

        # ---- Daily time rows -----------------------------------------------
        _render_daily_rows(eid, days, week_start, idx, job_options, lbl_to_id)

        # ---- Footer metadata -----------------------------------------------
        st.markdown(
            f'<p class="tk-footer-note">Last updated: {html.escape(last_updated_str)}'
            f' &nbsp;\u00b7\u00a0 by {html.escape(last_by)}</p>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Export helper
# ---------------------------------------------------------------------------
def _do_export(visible_emps: list[dict], days: list[date], idx: dict, job_id_to_lbl: dict[str, str]) -> None:
    rows: list[dict] = []
    for emp in visible_emps:
        eid = str(emp.get("id"))
        nm = str(emp.get("name") or "")
        for d in days:
            for ent in idx.get((eid, d.isoformat()), []):
                jid = str(ent.get("job_id") or "").strip()
                nj = str(ent.get("non_job_code") or "").strip()
                job_lbl = job_id_to_lbl.get(jid, jid) if jid else (f"NON-JOB -- {nj}" if nj else "")
                rows.append({
                    "Employee": nm,
                    "Date": d.isoformat(),
                    "Job": job_lbl,
                    "Type": _time_type(ent),
                    "Hours": float(ent.get("hours") or 0),
                    "Notes": str(ent.get("notes") or ""),
                })
    if rows:
        csv_data = pd.DataFrame(rows).to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv_data,
            file_name=f"timekeeping_export.csv",
            mime="text/csv",
            key="tk_dl_csv",
        )
    else:
        st.info("No entries to export for this week.")


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------
def render() -> None:
    today = date.today()

    # Inject styles once
    _inject_styles()

    # Auth check
    role = current_role()
    can_edit = role in TT_EDIT_ROLES

    # Initialise week state
    if _TK_WEEK not in st.session_state:
        st.session_state[_TK_WEEK] = monday_of_week(today).isoformat()
    try:
        week_start = date.fromisoformat(str(st.session_state[_TK_WEEK]))
    except (ValueError, TypeError):
        week_start = monday_of_week(today)
        st.session_state[_TK_WEEK] = week_start.isoformat()
    # Snap to Monday
    if week_start.weekday() != 0:
        week_start = monday_of_week(week_start)
        st.session_state[_TK_WEEK] = week_start.isoformat()

    days = week_dates(week_start)
    week_end = days[-1]

    # -- Page header
    _render_header(week_start, days)

    # -- Load data
    all_emps = _load_employees()
    jobs_raw = _load_jobs()
    job_options, lbl_to_id = _build_job_options(jobs_raw)
    job_id_to_lbl = {str(v): k for k, v in lbl_to_id.items()}

    try:
        grid_rows = fetch_time_entries_between(week_start, week_end)
    except Exception as exc:
        grid_rows = []
        st.error(f"Could not load time entries: {exc}")
    idx = index_by_employee_date(grid_rows)

    if not all_emps:
        st.warning("No active employees found. Add employees under **Employees** in the sidebar.")
        return

    # -- Filter bar
    q, dept_filter, export_clicked = _render_filter_bar(all_emps)

    # Apply filters
    visible_emps = all_emps
    if q:
        visible_emps = [e for e in visible_emps if q in str(e.get("name") or "").lower()]
    if dept_filter != "All Departments":
        visible_emps = [e for e in visible_emps if str(e.get("department") or "").strip() == dept_filter]

    if not visible_emps:
        st.info("No employees match the current filter.")
        return

    # Export handling
    if export_clicked:
        _do_export(visible_emps, days, idx, job_id_to_lbl)

    # -- Employee table
    if not can_edit:
        st.info("View-only mode. Sign in as admin, manager, pm, or employee to log time.")
    selected_eid = _render_employee_table(visible_emps, days, week_start, idx, can_edit)

    # -- Detail panel
    if selected_eid:
        uid = current_profile().get("id")
        _render_detail_panel(
            eid=selected_eid,
            all_emps=all_emps,
            days=days,
            week_start=week_start,
            idx=idx,
            job_options=job_options,
            lbl_to_id=lbl_to_id,
            uid=uid,
            can_edit=can_edit,
        )
    else:
        st.markdown(
            '<p class="tk-hint">\u25b6 Click an employee row to view and edit their weekly timecard.</p>',
            unsafe_allow_html=True,
        )

    # -- Week totals caption
    week_st = sum(_emp_week_summary(str(e.get("id")), days, idx)[0] for e in visible_emps)
    week_ot = sum(_emp_week_summary(str(e.get("id")), days, idx)[1] for e in visible_emps)
    st.caption(
        f"Week {week_start.strftime('%b %d')} \u2013 {week_end.strftime('%b %d')}  \u00b7  "
        f"S/T: **{week_st:.1f} h**  \u00b7  O/T: **{week_ot:.1f} h**  \u00b7  "
        f"Total: **{week_st + week_ot:.1f} h**"
    )
