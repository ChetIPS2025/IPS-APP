"""
Timekeeping -- professional weekly time entry, light-theme design.
Matches reference screenshot: white cards, table + detail panel.
"""
from __future__ import annotations

import html
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Service imports (fallbacks for both run modes)
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
_NO_ENTRY_LABEL = "Select a job (optional)"

# Session state keys
_TK_EMP  = "selected_timekeeping_employee_id"
_TK_WEEK = "selected_timekeeping_week_start"
_TK_VIEW = "timekeeping_view_mode"
_TK_EDIT = "timekeeping_edit_mode"

# ---------------------------------------------------------------------------
# Light-theme CSS  (forces white/light palette over Streamlit dark theme)
# ---------------------------------------------------------------------------
_CSS = """
<style>
/* ============================================================
   Timekeeping page  --  light-theme professional UI
   ============================================================ */

/* Page background */
[data-testid="stMain"] > div { background: #f1f4f9 !important; }
.block-container { padding-top: 1rem !important; }

/* ---- Global overrides for all TK containers ---- */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tks) {
    background: #ffffff !important;
    border: 1px solid #e5eaf2 !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 6px rgba(15,23,42,.07) !important;
    padding: 18px 22px !important;
    margin-bottom: 12px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tks) p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tks) span,
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tks) label {
    color: #1e293b !important;
}

/* ---- Inputs: light theme ---- */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tks) input,
div[data-testid="stHorizontalBlock"]:has(span.tki) input {
    background: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 6px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tks) [data-baseweb="select"] > div,
div[data-testid="stHorizontalBlock"]:has(span.tki) [data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 6px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tks) [data-baseweb="select"] svg,
div[data-testid="stHorizontalBlock"]:has(span.tki) [data-baseweb="select"] svg {
    fill: #64748b !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tks) [data-testid="stWidgetLabel"],
div[data-testid="stHorizontalBlock"]:has(span.tki) [data-testid="stWidgetLabel"] {
    display: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tks) [data-testid="stElementContainer"],
div[data-testid="stHorizontalBlock"]:has(span.tki) [data-testid="stElementContainer"] {
    margin-bottom: 0 !important;
}

/* ---- Header card ---- */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-hdr-card) {
    padding: 14px 22px 12px !important;
    margin-bottom: 10px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-hdr-card) button {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    color: #374151 !important;
    border-radius: 7px !important;
    min-height: 1.85rem !important;
    padding: 0.18rem 0.9rem !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,.06) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-hdr-card) button:hover {
    background: #f8fafc !important;
    border-color: #3b82f6 !important;
    color: #3b82f6 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-hdr-card) [data-testid="stWidgetLabel"] {
    display: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-hdr-card) [data-testid="stElementContainer"] {
    margin-bottom: 0 !important;
}

/* ---- Filter bar ---- */
div[data-testid="stHorizontalBlock"]:has(span.tk-filter) {
    background: #ffffff !important;
    border: 1px solid #e5eaf2 !important;
    border-radius: 10px !important;
    padding: 8px 16px !important;
    margin-bottom: 12px !important;
    align-items: center !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.05) !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-filter) input {
    background: #f8fafc !important;
    color: #1e293b !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 6px !important;
    min-height: 1.85rem !important;
    font-size: 0.84rem !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-filter) [data-baseweb="select"] > div {
    background: #f8fafc !important;
    color: #1e293b !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 6px !important;
    min-height: 1.85rem !important;
    font-size: 0.84rem !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-filter) [data-testid="stWidgetLabel"] { display: none !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-filter) [data-testid="stElementContainer"] { margin-bottom: 0 !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-filter) button {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    color: #374151 !important;
    border-radius: 7px !important;
    min-height: 1.85rem !important;
    padding: 0.15rem 0.9rem !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}

/* ---- Table container ---- */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-tbl) {
    padding: 0 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    margin-bottom: 0 !important;
}
/* Table header row */
div[data-testid="stHorizontalBlock"]:has(span.tk-th) {
    background: #f8fafc !important;
    border-bottom: 1px solid #e5eaf2 !important;
    padding: 7px 16px !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-th) > div[data-testid="column"] {
    padding: 0 5px !important;
}
/* Table data rows */
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) {
    padding: 0 16px !important;
    border-bottom: 1px solid #f1f5f9 !important;
    align-items: center !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tr.rven) { background: #ffffff !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-tr.rodd) { background: #f8fafc !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-tr):hover { background: #f0f7ff !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-tr.rsel) {
    background: #eff6ff !important;
    border-left: 3px solid #3b82f6 !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) > div[data-testid="column"] {
    padding: 6px 5px !important;
    align-self: center !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) button {
    background: transparent !important;
    border: 1px solid #e2e8f0 !important;
    color: #64748b !important;
    border-radius: 6px !important;
    min-height: 1.6rem !important;
    max-height: 1.8rem !important;
    padding: 0.05rem 0.4rem !important;
    font-size: 0.74rem !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) button:hover {
    border-color: #3b82f6 !important;
    color: #3b82f6 !important;
    background: #eff6ff !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) [data-testid="stWidgetLabel"] { display: none !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) p {
    font-size: 0.84rem !important;
    color: #1e293b !important;
    margin: 0 !important;
    line-height: 1.3 !important;
}
/* Table footer */
div[data-testid="stHorizontalBlock"]:has(span.tk-tf) {
    background: #f8fafc !important;
    border-top: 1px solid #e5eaf2 !important;
    padding: 6px 16px !important;
    border-radius: 0 0 12px 12px !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tf) p {
    font-size: 0.78rem !important;
    color: #64748b !important;
    margin: 0 !important;
}

/* ---- Detail panel ---- */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-dp) {
    padding: 18px 22px 18px !important;
    border-radius: 0 12px 12px 12px !important;
    border-left: 4px solid #3b82f6 !important;
    border-top: 1px solid #e5eaf2 !important;
    border-right: 1px solid #e5eaf2 !important;
    border-bottom: 1px solid #e5eaf2 !important;
    box-shadow: 0 2px 12px rgba(59,130,246,.08) !important;
    margin-top: 0 !important;
}
/* Detail action buttons */
div[data-testid="stHorizontalBlock"]:has(span.tk-dact) button {
    border-radius: 7px !important;
    min-height: 2rem !important;
    padding: 0.18rem 0.9rem !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
}
/* Detail: Edit Week button */
div[data-testid="stHorizontalBlock"]:has(span.tk-dact) button[kind="secondary"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    color: #374151 !important;
}
/* Detail: Save Changes button (primary) */
div[data-testid="stHorizontalBlock"]:has(span.tk-dact) button[kind="primaryFormSubmit"],
div[data-testid="stHorizontalBlock"]:has(span.tk-dact) button[data-testid="stBaseButton-primary"] {
    background: #3b82f6 !important;
    color: #ffffff !important;
    border: none !important;
}

/* ---- Daily rows header ---- */
div[data-testid="stHorizontalBlock"]:has(span.tk-dh) {
    background: #f8fafc !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 5px 4px !important;
    border-bottom: 1px solid #e5eaf2 !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-dh) p {
    font-size: 10px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: .06em !important;
    color: #64748b !important;
    margin: 0 !important;
}
/* Daily data rows */
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) {
    border-bottom: 1px solid #f1f5f9 !important;
    padding: 2px 4px !important;
    align-items: center !important;
    background: #ffffff !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-dr.dr-today) {
    background: #f0f7ff !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tki) {
    align-items: center !important;
}
/* Compact inputs inside daily rows */
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) input,
div[data-testid="stHorizontalBlock"]:has(span.tki) input {
    min-height: 1.6rem !important;
    font-size: 0.82rem !important;
    padding: 0.05rem 0.3rem !important;
    background: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 5px !important;
    text-align: center !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) [data-baseweb="select"] > div,
div[data-testid="stHorizontalBlock"]:has(span.tki) [data-baseweb="select"] > div {
    min-height: 1.6rem !important;
    font-size: 0.82rem !important;
    background: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 5px !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) [data-testid="stWidgetLabel"],
div[data-testid="stHorizontalBlock"]:has(span.tki) [data-testid="stWidgetLabel"] { display: none !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) [data-testid="stElementContainer"],
div[data-testid="stHorizontalBlock"]:has(span.tki) [data-testid="stElementContainer"] { margin-bottom: 0 !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) p {
    font-size: 0.82rem !important;
    color: #1e293b !important;
    margin: 0 !important;
}
/* Checkbox-style comment button */
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) button {
    background: transparent !important;
    border: 1px solid #e2e8f0 !important;
    color: #94a3b8 !important;
    border-radius: 4px !important;
    min-height: 1.4rem !important;
    max-height: 1.6rem !important;
    padding: 0.02rem 0.25rem !important;
    font-size: 0.72rem !important;
    min-width: 1.4rem !important;
}

/* ---- Typography ---- */
.tk-page-title    { font-size:1.4rem;font-weight:800;color:#111827;margin:0;letter-spacing:-.01em; }
.tk-page-sub      { font-size:.78rem;color:#6b7280;margin:.1rem 0 0; }
.tk-wk-range      { font-size:1rem;font-weight:700;color:#111827;margin:0;text-align:right; }
.tk-wk-num        { font-size:.73rem;color:#6b7280;margin:0;text-align:right; }
.tk-th-lbl        { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#6b7280;margin:0; }
.tk-th-lbl-sort   { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#6b7280;margin:0; }
.tk-td-name       { font-size:.86rem;font-weight:600;color:#111827;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.tk-td-name-sel   { color:#3b82f6 !important; }
.tk-td            { font-size:.84rem;color:#374151;margin:0; }
.tk-td-num        { font-size:.84rem;color:#374151;font-variant-numeric:tabular-nums;margin:0; }
.tk-td-num-ot     { font-size:.84rem;color:#d97706;font-weight:600;font-variant-numeric:tabular-nums;margin:0; }
.tk-ft-lbl        { font-size:.76rem;font-weight:600;color:#64748b;margin:0; }
.tk-det-name      { font-size:1.1rem;font-weight:800;color:#111827;margin:0; }
.tk-det-dept      { font-size:.77rem;color:#6b7280;margin:.1rem 0 0; }
.tk-met-lbl       { font-size:.68rem;text-transform:uppercase;letter-spacing:.05em;color:#6b7280;margin:0; }
.tk-met-val       { font-size:1.05rem;font-weight:700;color:#111827;margin:0;font-variant-numeric:tabular-nums; }
.tk-met-val-ot    { font-size:1.05rem;font-weight:700;color:#d97706;margin:0;font-variant-numeric:tabular-nums; }
.tk-day-lbl       { font-size:.83rem;font-weight:600;color:#374151;margin:0; }
.tk-day-today     { color:#3b82f6 !important; }
.tk-day-date      { font-size:.81rem;color:#6b7280;margin:0; }
.tk-row-total     { font-size:.82rem;font-weight:600;color:#374151;font-variant-numeric:tabular-nums;margin:0;text-align:center; }
.tk-dash          { font-size:.82rem;color:#94a3b8;margin:0; }
.tk-footer-note   { font-size:.72rem;color:#94a3b8;font-style:italic;margin:.6rem 0 0; }
.tk-hint          { font-size:.84rem;color:#9ca3af;font-style:italic;text-align:center;padding:1.4rem 0; }
.tk-no-emp        { font-size:.84rem;color:#9ca3af;text-align:center;padding:.8rem 0; }
/* Status badges */
.tkb { display:inline-block;font-size:.7rem;font-weight:600;padding:2px 9px;border-radius:20px;white-space:nowrap;letter-spacing:.02em; }
.tkb-approved { background:#d1fae5;color:#065f46; }
.tkb-pending  { background:#fef3c7;color:#92400e; }
.tkb-draft    { background:#f1f5f9;color:#64748b; }
.tkb-rejected { background:#fee2e2;color:#991b1b; }
/* Wk-nav "current week" outline-primary */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-hdr-card) button[kind="primary"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-hdr-card) button[data-testid="stBaseButton-primary"] {
    background: #eff6ff !important;
    border: 1px solid #3b82f6 !important;
    color: #3b82f6 !important;
}
/* Responsive */
@media(max-width:768px) {
    .tk-page-title { font-size:1.05rem !important; }
    div[data-testid="stHorizontalBlock"]:has(span.tk-tr) button { min-height:2.1rem !important; }
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
    fn = fetch_table_admin if role in ("admin", "manager") else fetch_table
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


def _build_job_options(jobs: list[dict]) -> tuple[list[str], dict[str, str]]:
    _, lbl_to_id, sorted_labels = build_job_dropdown_label_maps(jobs)
    nj_labels = [f"NON-JOB -- {c}" for c in NON_JOB_CATEGORY_OPTIONS]
    all_labels = [_NO_ENTRY_LABEL] + sorted_labels + nj_labels
    return all_labels, lbl_to_id


def _resolve_job(label: str, lbl_to_id: dict[str, str]) -> tuple[str | None, str | None]:
    if not label or label == _NO_ENTRY_LABEL:
        return None, None
    if label.startswith("NON-JOB -- "):
        code = label[len("NON-JOB -- "):].strip()
        return None, code or None
    jid = str(lbl_to_id.get(label) or "").strip()
    return jid or None, None


def _tt(ent: dict) -> str:
    s = str(ent.get("time_type") or "").strip().upper()
    return "OT" if s in ("OT", "O/T") else "ST"


def _week_summary(eid: str, days: list[date], idx: dict) -> tuple[float, float]:
    st_h = ot_h = 0.0
    for d in days:
        for e in idx.get((eid, d.isoformat()), []):
            h = float(e.get("hours") or 0)
            (ot_h := ot_h + h) if _tt(e) == "OT" else (st_h := st_h + h)  # noqa: walrus
    return st_h, ot_h


def _week_summary2(eid: str, days: list[date], idx: dict) -> tuple[float, float]:
    """Non-walrus fallback for Python < 3.8."""
    st_h = ot_h = 0.0
    for d in days:
        for e in idx.get((eid, d.isoformat()), []):
            h = float(e.get("hours") or 0)
            if _tt(e) == "OT":
                ot_h += h
            else:
                st_h += h
    return st_h, ot_h


def _status(st_h: float, ot_h: float) -> str:
    return "draft" if st_h + ot_h == 0 else "pending"


def _badge(status: str) -> str:
    css = {"approved": "tkb-approved", "pending": "tkb-pending", "rejected": "tkb-rejected"}.get(status, "tkb-draft")
    return f'<span class="tkb {css}">{html.escape(status.title())}</span>'


def _fmt_week(ws: date) -> str:
    we = ws + timedelta(days=6)
    return f"{ws.strftime('%b %-d')} \u2013 {we.strftime('%b %-d, %Y')}"


def _fmt_week_win(ws: date) -> str:
    """strftime without %-d for Windows."""
    we = ws + timedelta(days=6)
    return f"{ws.strftime('%b')} {ws.day} \u2013 {we.strftime('%b')} {we.day}, {we.year}"


def _wlabel(ws: date) -> str:
    try:
        return _fmt_week(ws)
    except ValueError:
        return _fmt_week_win(ws)


def _wnum(ws: date) -> int:
    return ws.isocalendar()[1]


def _rk(eid: str, day_iso: str, week_iso: str, field: str) -> str:
    return f"tk_{eid[:8]}_{day_iso}_{week_iso.replace('-','')}_{field}"


def _clear_state(eid: str, days: list[date], week_start: date) -> None:
    w = week_start.isoformat()
    for d in days:
        for f in ("job", "st", "ot", "notes"):
            st.session_state.pop(_rk(eid, d.isoformat(), w, f), None)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
def _save_week(eid: str, days: list[date], week_start: date, lbl_to_id: dict[str, str], uid: Any) -> list[str]:
    ts = datetime.now(timezone.utc).isoformat()
    w = week_start.isoformat()
    errs: list[str] = []
    for d in days:
        di = d.isoformat()
        jlbl = str(st.session_state.get(_rk(eid, di, w, "job"), "") or "").strip()
        sth  = float(st.session_state.get(_rk(eid, di, w, "st"),  0.0) or 0.0)
        oth  = float(st.session_state.get(_rk(eid, di, w, "ot"),  0.0) or 0.0)
        notes = str(st.session_state.get(_rk(eid, di, w, "notes"), "") or "").strip()
        if not jlbl or jlbl == _NO_ENTRY_LABEL:
            continue
        jid, nj = _resolve_job(jlbl, lbl_to_id)
        if not jid and not nj:
            continue
        for hrs, ttype in ((sth, "ST"), (oth, "OT")):
            if hrs > 0:
                try:
                    upsert_time_entry(
                        employee_id=eid, job_id=jid, work_date=d,
                        hours=hrs, notes=notes, created_by=uid,
                        updated_at_iso=ts, non_job_code=nj, time_type=ttype,
                    )
                except Exception as exc:
                    errs.append(f"{d.strftime('%a')}/{ttype}: {exc}")
    return errs


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def _render_header(week_start: date) -> None:
    with st.container(border=True):
        st.markdown('<span class="tks tk-hdr-card" aria-hidden="true"></span>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2.2, 3.0, 2.0], gap="small")
        with c1:
            st.markdown(
                '<p class="tk-page-title">\u23f0&nbsp; Timekeeping</p>'
                '<p class="tk-page-sub">View and edit employee weekly time entries.</p>',
                unsafe_allow_html=True,
            )
        with c2:
            n1, n2, n3 = st.columns(3, gap="small")
            with n1:
                if st.button("\u2039 Previous Week", key="tk_prev", use_container_width=True):
                    st.session_state[_TK_WEEK] = (week_start - timedelta(days=7)).isoformat()
                    st.rerun()
            with n2:
                if st.button("\U0001f4c5 Current Week", key="tk_cur", type="primary", use_container_width=True):
                    st.session_state[_TK_WEEK] = monday_of_week(date.today()).isoformat()
                    st.rerun()
            with n3:
                if st.button("Next Week \u203a", key="tk_next", use_container_width=True):
                    st.session_state[_TK_WEEK] = (week_start + timedelta(days=7)).isoformat()
                    st.rerun()
        with c3:
            wl = _wlabel(week_start)
            wn = _wnum(week_start)
            st.markdown(
                f'<p class="tk-wk-range">\U0001f4c5&nbsp; {html.escape(wl)}</p>'
                f'<p class="tk-wk-num">Week {wn}</p>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Filter bar
# ---------------------------------------------------------------------------
def _render_filter_bar(all_emps: list[dict]) -> tuple[str, str, bool]:
    depts = sorted({str(e.get("department") or "").strip() for e in all_emps if str(e.get("department") or "").strip()})
    opts  = ["All Departments"] + depts

    c1, c2, _sp, c3 = st.columns([2.6, 2.0, 3.0, 0.8], gap="small")
    with c1:
        st.markdown('<span class="tk-filter" aria-hidden="true"></span>', unsafe_allow_html=True)
        q = st.text_input("Search", placeholder="Search employee...", key="tk_q", label_visibility="collapsed")
    with c2:
        dept = st.selectbox("Dept", opts, key="tk_dept", label_visibility="collapsed")
    with c3:
        clicked = st.button("\u2913 Export", key="tk_export", use_container_width=True)
    return str(q or "").strip().lower(), str(dept or "All Departments"), clicked


# ---------------------------------------------------------------------------
# Employee table
# ---------------------------------------------------------------------------
# col weights: name, dept, week-start, st, ot, total, status, actions
_TC = [2.3, 1.15, 1.05, 0.82, 0.82, 0.82, 0.9, 0.52]
_TH = ["Employee \u21d5", "Department \u21d5", "Week Start \u21d5", "S/T Total (Hrs) \u21d5",
       "O/T Total (Hrs) \u21d5", "Total Hours \u21d5", "Status \u21d5", "Actions"]


def _render_table(visible: list[dict], days: list[date], week_start: date, idx: dict) -> str | None:
    sel = str(st.session_state.get(_TK_EMP) or "")
    new_sel: str | None = sel or None

    with st.container(border=True):
        st.markdown('<span class="tks tk-tbl" aria-hidden="true"></span>', unsafe_allow_html=True)

        # Header
        hcols = st.columns(_TC, gap="small")
        with hcols[0]:
            st.markdown('<span class="tk-th" aria-hidden="true"></span>', unsafe_allow_html=True)
        for lbl, col in zip(_TH, hcols):
            with col:
                st.markdown(f'<p class="tk-th-lbl">{html.escape(lbl)}</p>', unsafe_allow_html=True)

        # Rows
        for ri, emp in enumerate(visible):
            eid  = str(emp.get("id"))
            nm   = str(emp.get("name") or "").strip() or "—"
            dept = str(emp.get("department") or "").strip() or "—"
            is_sel = eid == sel
            sth, oth = _week_summary2(eid, days, idx)
            tot = sth + oth
            over = tot > _OT_THRESHOLD
            z = "rven" if ri % 2 == 0 else "rodd"
            rc = " rsel" if is_sel else ""

            rcols = st.columns(_TC, gap="small")
            with rcols[0]:
                ncls = "tk-td-name" + (" tk-td-name-sel" if is_sel else "")
                st.markdown(
                    f'<span class="tk-tr {z}{rc}" aria-hidden="true"></span>'
                    f'<p class="{ncls}">{html.escape(nm)}</p>',
                    unsafe_allow_html=True,
                )
            with rcols[1]:
                st.markdown(f'<p class="tk-td">{html.escape(dept)}</p>', unsafe_allow_html=True)
            with rcols[2]:
                wlbl = week_start.strftime("%b %-d, %Y") if hasattr(date, "strftime") else week_start.strftime("%b %d, %Y")
                try:
                    wlbl = week_start.strftime("%b %-d, %Y")
                except ValueError:
                    wlbl = f"{week_start.strftime('%b')} {week_start.day}, {week_start.year}"
                st.markdown(f'<p class="tk-td">{html.escape(wlbl)}</p>', unsafe_allow_html=True)
            with rcols[3]:
                st.markdown(f'<p class="tk-td-num">{sth:.2f}</p>', unsafe_allow_html=True)
            with rcols[4]:
                oc = "tk-td-num-ot" if oth > 0 else "tk-td-num"
                st.markdown(f'<p class="{oc}">{oth:.2f}</p>', unsafe_allow_html=True)
            with rcols[5]:
                tc = "tk-td-num-ot" if over else "tk-td-num"
                st.markdown(f'<p class="{tc}">{tot:.2f}</p>', unsafe_allow_html=True)
            with rcols[6]:
                st.markdown(_badge(_status(sth, oth)), unsafe_allow_html=True)
            with rcols[7]:
                if st.button("\U0001f441", key=f"tkv_{eid}_{week_start.isoformat()}", use_container_width=True,
                             help=f"{'Close' if is_sel else 'View'} {nm}"):
                    new_sel = None if is_sel else eid

        # Footer
        ft_st  = sum(_week_summary2(str(e.get("id")), days, idx)[0] for e in visible)
        ft_ot  = sum(_week_summary2(str(e.get("id")), days, idx)[1] for e in visible)
        ft_tot = ft_st + ft_ot
        fc = st.columns(_TC, gap="small")
        with fc[0]:
            st.markdown(
                f'<span class="tk-tf" aria-hidden="true"></span>'
                f'<p class="tk-ft-lbl">{len(visible)} employee{"s" if len(visible) != 1 else ""}</p>',
                unsafe_allow_html=True,
            )
        with fc[3]:
            st.markdown(f'<p class="tk-ft-lbl">{ft_st:.2f}</p>', unsafe_allow_html=True)
        with fc[4]:
            st.markdown(f'<p class="tk-ft-lbl">{ft_ot:.2f}</p>', unsafe_allow_html=True)
        with fc[5]:
            st.markdown(f'<p class="tk-ft-lbl">{ft_tot:.2f}</p>', unsafe_allow_html=True)

    # Apply selection change
    if new_sel != (sel or None):
        if new_sel:
            st.session_state[_TK_EMP]  = new_sel
            st.session_state[_TK_VIEW] = "detail"
            st.session_state[_TK_EDIT] = True
        else:
            st.session_state.pop(_TK_EMP, None)
            st.session_state[_TK_VIEW] = "table"
            st.session_state[_TK_EDIT] = False
        st.rerun()

    return sel or None


# ---------------------------------------------------------------------------
# Daily rows (inside detail panel)
# ---------------------------------------------------------------------------
# col weights: day, date, job/desc, st, ot, total, notes, chk
_DC = [0.65, 0.72, 3.2, 0.85, 0.85, 0.8, 2.2, 0.38]
_DH = ["Day", "Date", "Job / Description", "S/T (Hrs)", "O/T (Hrs)", "Total (Hrs)", "Notes", ""]


def _render_daily(eid: str, days: list[date], week_start: date, idx: dict,
                  jopts: list[str], lbl_to_id: dict[str, str]) -> None:
    today = date.today()
    w = week_start.isoformat()

    # Header row
    hc = st.columns(_DC, gap="small")
    with hc[0]:
        st.markdown('<span class="tk-dh" aria-hidden="true"></span>', unsafe_allow_html=True)
    for lbl, col in zip(_DH, hc):
        with col:
            st.markdown(f'<p style="font-size:10px;font-weight:700;text-transform:uppercase;'
                        f'letter-spacing:.06em;color:#6b7280;margin:0">{html.escape(lbl)}</p>',
                        unsafe_allow_html=True)

    for d in days:
        di    = d.isoformat()
        is_today = d == today
        tc    = " dr-today" if is_today else ""

        ents   = idx.get((eid, di), [])
        st_ent = next((e for e in ents if _tt(e) == "ST"), None)
        ot_ent = next((e for e in ents if _tt(e) == "OT"), None)
        prim   = st_ent or ot_ent

        # Resolve current job label
        def _jlbl(ent: dict | None) -> str:
            if not ent:
                return _NO_ENTRY_LABEL
            jid = str(ent.get("job_id") or "").strip()
            nj  = str(ent.get("non_job_code") or "").strip()
            if jid:
                for lbl, lid in lbl_to_id.items():
                    if str(lid) == jid:
                        return lbl
            if nj:
                return f"NON-JOB -- {nj}"
            return _NO_ENTRY_LABEL

        ex_jlbl  = _jlbl(prim)
        ex_st    = float(st_ent.get("hours") or 0) if st_ent else 0.0
        ex_ot    = float(ot_ent.get("hours") or 0) if ot_ent else 0.0
        ex_notes = str((prim or {}).get("notes") or "").strip()

        jk  = _rk(eid, di, w, "job")
        stk = _rk(eid, di, w, "st")
        otk = _rk(eid, di, w, "ot")
        nk  = _rk(eid, di, w, "notes")

        j_idx = jopts.index(ex_jlbl) if ex_jlbl in jopts else 0

        # Day label style
        dlc = "tk-day-lbl" + (" tk-day-today" if is_today else "")
        dtc = "tk-day-date" + (" tk-day-today" if is_today else "")

        dc = st.columns(_DC, gap="small")
        with dc[0]:
            st.markdown(
                f'<span class="tk-dr{tc}" aria-hidden="true"></span>'
                f'<p class="{dlc}">{d.strftime("%a")}</p>',
                unsafe_allow_html=True,
            )
        with dc[1]:
            try:
                dlbl = f"{d.strftime('%b')} {d.day}"
            except Exception:
                dlbl = d.isoformat()
            st.markdown(f'<p class="{dtc}">{html.escape(dlbl)}</p>', unsafe_allow_html=True)
        with dc[2]:
            st.markdown('<span class="tki" aria-hidden="true"></span>', unsafe_allow_html=True)
            sel_job = st.selectbox("Job", jopts, index=j_idx, key=jk, label_visibility="collapsed")
        with dc[3]:
            new_st = st.number_input("ST", min_value=0.0, max_value=24.0, value=ex_st,
                                     step=0.25, format="%.2f", key=stk, label_visibility="collapsed")
        with dc[4]:
            new_ot = st.number_input("OT", min_value=0.0, max_value=24.0, value=ex_ot,
                                     step=0.25, format="%.2f", key=otk, label_visibility="collapsed")
        with dc[5]:
            row_tot = float(new_st) + float(new_ot)
            st.markdown(f'<p class="tk-row-total">{row_tot:.2f}</p>', unsafe_allow_html=True)
        with dc[6]:
            placeholder = "Add notes..." if ex_jlbl == _NO_ENTRY_LABEL else (ex_notes or "—")
            ph_arg = "Add notes..." if ex_jlbl == _NO_ENTRY_LABEL else "Add notes..."
            st.text_input("Notes", value=ex_notes, key=nk,
                          label_visibility="collapsed", placeholder=ph_arg)
        with dc[7]:
            has_entry = bool(st_ent or ot_ent)
            chk_lbl = "\u2611" if has_entry else "\u2610"
            if st.button(chk_lbl, key=f"tkchk_{eid[:8]}_{di}", help=ex_notes or "No notes"):
                pass


# ---------------------------------------------------------------------------
# Detail panel
# ---------------------------------------------------------------------------
def _render_detail(eid: str, all_emps: list[dict], days: list[date], week_start: date,
                   idx: dict, jopts: list[str], lbl_to_id: dict[str, str],
                   uid: Any, can_edit: bool) -> None:
    emp = next((e for e in all_emps if str(e.get("id")) == eid), None)
    if not emp:
        st.session_state.pop(_TK_EMP, None)
        return

    nm    = str(emp.get("name") or "").strip() or "—"
    dept  = str(emp.get("department") or "").strip() or "—"
    sth, oth = _week_summary2(eid, days, idx)
    tot = sth + oth
    over = tot > _OT_THRESHOLD
    stat = _status(sth, oth)

    # Last-updated metadata
    all_ents: list[dict] = []
    for d in days:
        all_ents.extend(idx.get((eid, d.isoformat()), []))
    lu_str = "—"
    lu_by  = "—"
    if all_ents:
        latest = max(all_ents, key=lambda e: str(e.get("updated_at") or ""))
        raw = str(latest.get("updated_at") or "")
        if raw:
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                lu_str = dt.strftime("%b %-d, %Y %-I:%M %p")
            except ValueError:
                try:
                    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    lu_str = f"{dt.strftime('%b')} {dt.day}, {dt.year} {dt.strftime('%I:%M %p').lstrip('0')}"
                except Exception:
                    lu_str = raw[:19]
        lu_by = str(latest.get("created_by") or "—")

    with st.container(border=True):
        st.markdown('<span class="tks tk-dp" aria-hidden="true"></span>', unsafe_allow_html=True)

        # -- Panel header --
        d1, d2, d3 = st.columns([2.4, 3.8, 2.0], gap="small")

        with d1:
            st.markdown(
                f'<p class="tk-det-name">{html.escape(nm)}&nbsp;&nbsp;{_badge(stat)}</p>'
                f'<p class="tk-det-dept">{html.escape(dept)}</p>',
                unsafe_allow_html=True,
            )

        with d2:
            wl = _wlabel(week_start)
            st.markdown(
                f'<p class="tk-met-lbl">\U0001f4c5 Week</p>'
                f'<p style="font-size:.82rem;color:#374151;margin:0 0 .4rem">{html.escape(wl)}</p>',
                unsafe_allow_html=True,
            )
            m1, m2, m3 = st.columns(3, gap="small")
            with m1:
                st.markdown(f'<p class="tk-met-lbl">S/T Total</p>'
                            f'<p class="tk-met-val">{sth:.2f} hrs</p>', unsafe_allow_html=True)
            with m2:
                vc = "tk-met-val-ot" if oth > 0 else "tk-met-val"
                st.markdown(f'<p class="tk-met-lbl">O/T Total</p>'
                            f'<p class="{vc}">{oth:.2f} hrs</p>', unsafe_allow_html=True)
            with m3:
                over_flag = " \u26a0" if over else ""
                st.markdown(f'<p class="tk-met-lbl">Total Hours{over_flag}</p>'
                            f'<p class="tk-met-val">{tot:.2f} hrs</p>', unsafe_allow_html=True)

        with d3:
            st.markdown('<span class="tk-dact" aria-hidden="true"></span>', unsafe_allow_html=True)
            if can_edit:
                if st.button("\u270f\ufe0f Edit Week", key=f"tkedit_{eid[:8]}", use_container_width=True):
                    pass  # Editing is inline in the rows below
                if st.button("\U0001f4be Save Changes", key=f"tksave_{eid[:8]}_{week_start.isoformat()}",
                             type="primary", use_container_width=True):
                    errs = _save_week(eid, days, week_start, lbl_to_id, uid)
                    if errs:
                        st.error("Saved with errors:\n" + "\n".join(errs))
                    else:
                        _clear_state(eid, days, week_start)
                        try:
                            st.cache_data.clear()
                        except Exception:
                            pass
                        st.success("Week saved successfully!")
                        st.rerun()
            if st.button("\u2303 Collapse", key="tkclose", type="secondary", use_container_width=True):
                st.session_state.pop(_TK_EMP, None)
                st.session_state[_TK_VIEW] = "table"
                st.session_state[_TK_EDIT] = False
                st.rerun()

        st.divider()

        # -- Daily rows --
        _render_daily(eid, days, week_start, idx, jopts, lbl_to_id)

        # -- Footer --
        st.markdown(
            f'<p class="tk-footer-note">Last updated: {html.escape(lu_str)}'
            f'&nbsp; &middot; &nbsp;by {html.escape(lu_by)}</p>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def _do_export(visible: list[dict], days: list[date], idx: dict, id_to_lbl: dict[str, str]) -> None:
    rows: list[dict] = []
    for emp in visible:
        eid = str(emp.get("id"))
        nm  = str(emp.get("name") or "")
        for d in days:
            for ent in idx.get((eid, d.isoformat()), []):
                jid  = str(ent.get("job_id") or "").strip()
                nj   = str(ent.get("non_job_code") or "").strip()
                jlbl = id_to_lbl.get(jid, jid) if jid else (f"NON-JOB -- {nj}" if nj else "")
                rows.append({
                    "Employee": nm, "Date": d.isoformat(),
                    "Job": jlbl, "Type": _tt(ent),
                    "Hours": float(ent.get("hours") or 0),
                    "Notes": str(ent.get("notes") or ""),
                })
    if not rows:
        st.info("No entries to export for this week.")
        return
    csv = pd.DataFrame(rows).to_csv(index=False)
    st.download_button("Download CSV", csv, file_name="timekeeping_export.csv", mime="text/csv", key="tkdl")


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------
def render() -> None:
    today = date.today()
    _inject_styles()

    role     = current_role()
    can_edit = role in TT_EDIT_ROLES

    # Week state
    if _TK_WEEK not in st.session_state:
        st.session_state[_TK_WEEK] = monday_of_week(today).isoformat()
    try:
        week_start = date.fromisoformat(str(st.session_state[_TK_WEEK]))
    except (ValueError, TypeError):
        week_start = monday_of_week(today)
        st.session_state[_TK_WEEK] = week_start.isoformat()
    if week_start.weekday() != 0:
        week_start = monday_of_week(week_start)
        st.session_state[_TK_WEEK] = week_start.isoformat()

    days     = week_dates(week_start)
    week_end = days[-1]

    # Header
    _render_header(week_start)

    # Data
    all_emps = _load_employees()
    jobs_raw = _load_jobs()
    jopts, lbl_to_id = _build_job_options(jobs_raw)
    id_to_lbl = {str(v): k for k, v in lbl_to_id.items()}

    try:
        grid = fetch_time_entries_between(week_start, week_end)
    except Exception as exc:
        grid = []
        st.error(f"Could not load time entries: {exc}")
    idx = index_by_employee_date(grid)

    if not all_emps:
        st.warning("No active employees found. Add employees under **Employees** in the sidebar.")
        return

    # Filter bar
    q, dept_f, export_clicked = _render_filter_bar(all_emps)

    visible = all_emps
    if q:
        visible = [e for e in visible if q in str(e.get("name") or "").lower()]
    if dept_f != "All Departments":
        visible = [e for e in visible if str(e.get("department") or "").strip() == dept_f]

    if export_clicked:
        _do_export(visible, days, idx, id_to_lbl)

    if not visible:
        st.markdown('<p class="tk-no-emp">No employees match the current filter.</p>',
                    unsafe_allow_html=True)
        return

    if not can_edit:
        st.info("View-only mode. Sign in as admin, manager, pm, or employee to log time.")

    # Employee table
    sel_eid = _render_table(visible, days, week_start, idx)

    # Detail panel
    if sel_eid:
        uid = current_profile().get("id")
        _render_detail(sel_eid, all_emps, days, week_start, idx, jopts, lbl_to_id, uid, can_edit)
    else:
        st.markdown(
            '<p class="tk-hint">\u25b6\ufe0e&nbsp; Click an employee row to view and edit their weekly timecard.</p>',
            unsafe_allow_html=True,
        )

    # Week summary caption
    wst = sum(_week_summary2(str(e.get("id")), days, idx)[0] for e in visible)
    wot = sum(_week_summary2(str(e.get("id")), days, idx)[1] for e in visible)
    st.caption(
        f"Week {week_start.strftime('%b')} {week_start.day} \u2013 "
        f"{week_end.strftime('%b')} {week_end.day}  \u00b7  "
        f"S/T: **{wst:.1f} h**  \u00b7  O/T: **{wot:.1f} h**  \u00b7  Total: **{wst+wot:.1f} h**"
    )
