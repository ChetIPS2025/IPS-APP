"""
Timekeeping -- professional weekly timecard page.
Exactly mirrors the reference screenshot UI.
"""
from __future__ import annotations

import html
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Service imports (with fallbacks)
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
TT_EDIT_ROLES       = frozenset({"admin", "manager", "pm", "employee"})
NON_JOB_CATEGORIES  = ["SHOP", "ADMIN", "TRAINING", "SAFETY", "PTO", "HOLIDAY", "TRAVEL"]
_JOB_PLACEHOLDER    = "Select a job (optional)"
_CLOSED_STATUSES    = frozenset({"closed","complete","completed","cancelled","archived","close","done"})
_OT_THRESHOLD       = 40.0

# Stable session-state keys (never rename these)
_TK_EMP  = "selected_timekeeping_employee_id"
_TK_WEEK = "selected_timekeeping_week_start"
_TK_VIEW = "timekeeping_view_mode"
_TK_EDIT = "timekeeping_edit_mode"

# ---------------------------------------------------------------------------
# CSS  — light-theme to match screenshot exactly
# ---------------------------------------------------------------------------
_CSS = """
<style>
/* ==========================================================
   Timekeeping  —  light professional theme
   ========================================================== */

/* 1. Page background ---------------------------------------- */
[data-testid="stAppViewContainer"] { background: #f3f4f6 !important; }
[data-testid="stMain"]              { background: #f3f4f6 !important; }
section[data-testid="stMain"] > div.block-container {
    background: transparent !important;
    padding-top: 0.75rem !important;
}

/* 2. Force light text colour for all TK markdown ------------ */
div[data-testid="stMarkdownContainer"] p { color: #111827 !important; }
div[data-testid="stMarkdownContainer"] span { color: inherit !important; }

/* 3. Inputs global light override --------------------------- */
input, textarea {
    background: #ffffff !important;
    color: #111827 !important;
    border: 1px solid #d1d5db !important;
    border-radius: 6px !important;
}
input:focus, textarea:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 2px rgba(37,99,235,.15) !important;
    outline: none !important;
}
[data-baseweb="select"] > div {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 6px !important;
    color: #111827 !important;
}
[data-baseweb="select"] li { background: #ffffff !important; color: #111827 !important; }
[data-baseweb="select"] li:hover { background: #eff6ff !important; }
[data-baseweb="popover"]   { background: #ffffff !important; }

/* 4. Widget labels hidden inside TK blocks ------------------ */
div[data-testid="stHorizontalBlock"]:has(span.tk-scope) [data-testid="stWidgetLabel"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-scope) [data-testid="stWidgetLabel"] {
    display: none !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-scope) [data-testid="stElementContainer"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-scope) [data-testid="stElementContainer"] {
    margin-bottom: 0 !important;
}

/* ============================================================
   HEADER CARD
   ============================================================ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-header) {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.07) !important;
    padding: 16px 24px 14px !important;
    margin-bottom: 14px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-header) [data-testid="stWidgetLabel"] {
    display: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-header) [data-testid="stElementContainer"] {
    margin-bottom: 0 !important;
}
/* Week nav buttons — outlined grey */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-header) button {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    color: #374151 !important;
    border-radius: 8px !important;
    min-height: 1.9rem !important;
    padding: 0.15rem 0.85rem !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,.05) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-header) button:hover {
    border-color: #2563eb !important;
    color: #2563eb !important;
    background: #eff6ff !important;
}
/* Current week = outlined-primary */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-header) button[kind="primary"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-header) button[data-testid="stBaseButton-primary"] {
    background: #eff6ff !important;
    border: 1px solid #2563eb !important;
    color: #2563eb !important;
}

/* ============================================================
   FILTER BAR
   ============================================================ */
div[data-testid="stHorizontalBlock"]:has(span.tk-filter) {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 10px !important;
    padding: 8px 16px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.04) !important;
    align-items: center !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-filter) [data-testid="stWidgetLabel"] { display: none !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-filter) [data-testid="stElementContainer"] { margin-bottom: 0 !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-filter) input {
    background: #f9fafb !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 7px !important;
    min-height: 1.85rem !important;
    font-size: 0.84rem !important;
    color: #374151 !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-filter) [data-baseweb="select"] > div {
    background: #f9fafb !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 7px !important;
    min-height: 1.85rem !important;
    font-size: 0.84rem !important;
    color: #374151 !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-filter) button {
    background: #f9fafb !important;
    border: 1px solid #e5e7eb !important;
    color: #374151 !important;
    border-radius: 7px !important;
    min-height: 1.85rem !important;
    padding: 0.12rem 0.85rem !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
}

/* ============================================================
   EMPLOYEE TABLE CONTAINER
   ============================================================ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-tbl) {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.06) !important;
    padding: 0 !important;
    overflow: hidden !important;
    margin-bottom: 2px !important;
}
/* Table header */
div[data-testid="stHorizontalBlock"]:has(span.tk-th) {
    background: #f9fafb !important;
    border-bottom: 1px solid #e5e7eb !important;
    padding: 7px 18px !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-th) > div[data-testid="column"] { padding: 0 5px !important; }
/* Table data rows */
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) {
    padding: 0 18px !important;
    border-bottom: 1px solid #f3f4f6 !important;
    align-items: center !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tr.r0) { background: #ffffff !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-tr.r1) { background: #f9fafb !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-tr):hover { background: #f0f7ff !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-tr.rs) {
    background: #eff6ff !important;
    border-left: 3px solid #2563eb !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) > div[data-testid="column"] {
    padding: 7px 5px !important;
    align-self: center !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) [data-testid="stWidgetLabel"] { display: none !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) [data-testid="stElementContainer"] { margin-bottom: 0 !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) p {
    font-size: 0.855rem !important;
    color: #374151 !important;
    margin: 0 !important;
    line-height: 1.3 !important;
}
/* Eye icon button in table */
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) button {
    background: transparent !important;
    border: 1px solid #e5e7eb !important;
    color: #9ca3af !important;
    border-radius: 6px !important;
    min-height: 1.6rem !important;
    max-height: 1.8rem !important;
    padding: 0.05rem 0.42rem !important;
    font-size: 0.78rem !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tr) button:hover {
    border-color: #2563eb !important;
    color: #2563eb !important;
    background: #eff6ff !important;
}
/* Table footer */
div[data-testid="stHorizontalBlock"]:has(span.tk-tf) {
    background: #f9fafb !important;
    border-top: 1px solid #e5e7eb !important;
    padding: 6px 18px !important;
    border-radius: 0 0 12px 12px !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-tf) p {
    font-size: 0.78rem !important;
    color: #6b7280 !important;
    margin: 0 !important;
}

/* ============================================================
   DETAIL PANEL
   ============================================================ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-dp) {
    background: #ffffff !important;
    border-top: 1px solid #e5e7eb !important;
    border-right: 1px solid #e5e7eb !important;
    border-bottom: 1px solid #e5e7eb !important;
    border-left: 4px solid #2563eb !important;
    border-radius: 0 12px 12px 12px !important;
    box-shadow: 0 2px 10px rgba(37,99,235,.08) !important;
    padding: 18px 22px 16px !important;
    margin-top: 0 !important;
}
/* Detail panel inputs */
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-dp) [data-testid="stWidgetLabel"] { display: none !important; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-dp) [data-testid="stElementContainer"] { margin-bottom: 0.06rem !important; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-dp) input {
    background: #ffffff !important;
    color: #111827 !important;
    border: 1px solid #d1d5db !important;
    border-radius: 5px !important;
    min-height: 1.6rem !important;
    font-size: 0.82rem !important;
    padding: 0.04rem 0.3rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(span.tk-dp) [data-baseweb="select"] > div {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 5px !important;
    min-height: 1.6rem !important;
    font-size: 0.82rem !important;
    color: #111827 !important;
}
/* Detail action buttons */
div[data-testid="stHorizontalBlock"]:has(span.tk-da) button {
    border-radius: 8px !important;
    min-height: 1.9rem !important;
    padding: 0.14rem 0.85rem !important;
    font-size: 0.83rem !important;
    font-weight: 600 !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-da) button[kind="secondary"] {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    color: #374151 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,.05) !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-da) button[kind="secondary"]:hover {
    border-color: #2563eb !important;
    color: #2563eb !important;
    background: #eff6ff !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-da) button[kind="primary"],
div[data-testid="stHorizontalBlock"]:has(span.tk-da) button[data-testid="stBaseButton-primary"] {
    background: #2563eb !important;
    border: 1px solid #2563eb !important;
    color: #ffffff !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-da) button[kind="primary"]:hover,
div[data-testid="stHorizontalBlock"]:has(span.tk-da) button[data-testid="stBaseButton-primary"]:hover {
    background: #1d4ed8 !important;
    border-color: #1d4ed8 !important;
}
/* Collapse button tiny */
div[data-testid="stHorizontalBlock"]:has(span.tk-da) button[data-testid="stBaseButton-secondary"]:last-child {
    padding: 0.05rem 0.4rem !important;
    min-height: 1.6rem !important;
    font-size: 0.82rem !important;
}

/* Daily rows header */
div[data-testid="stHorizontalBlock"]:has(span.tk-dh) {
    background: #f9fafb !important;
    border-radius: 7px 7px 0 0 !important;
    padding: 5px 8px !important;
    border-bottom: 1px solid #e5e7eb !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-dh) p {
    font-size: 10px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: .055em !important;
    color: #6b7280 !important;
    margin: 0 !important;
}
/* Daily data rows */
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) {
    background: #ffffff !important;
    border-bottom: 1px solid #f3f4f6 !important;
    padding: 1px 8px !important;
    align-items: center !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-dr.today-row) {
    background: #f0f7ff !important;
    border-left: 2px solid rgba(37,99,235,.4) !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) [data-testid="stWidgetLabel"] { display: none !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) [data-testid="stElementContainer"] { margin-bottom: 0 !important; }
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) p {
    font-size: 0.84rem !important;
    color: #374151 !important;
    margin: 0 !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) input {
    background: #ffffff !important;
    color: #111827 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 5px !important;
    min-height: 1.55rem !important;
    font-size: 0.82rem !important;
    padding: 0.03rem 0.28rem !important;
    text-align: center !important;
}
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) [data-baseweb="select"] > div {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 5px !important;
    min-height: 1.55rem !important;
    font-size: 0.82rem !important;
    color: #374151 !important;
}
/* Checkbox-style button */
div[data-testid="stHorizontalBlock"]:has(span.tk-dr) button {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    color: #d1d5db !important;
    border-radius: 4px !important;
    min-height: 1.3rem !important;
    max-height: 1.45rem !important;
    padding: 0 !important;
    font-size: 0.72rem !important;
    min-width: 1.3rem !important;
    max-width: 1.45rem !important;
}

/* ============================================================
   Typography classes
   ============================================================ */
.tk-t { font-size:1.45rem;font-weight:800;color:#111827;margin:0;letter-spacing:-.01em; }
.tk-s { font-size:.78rem;color:#6b7280;margin:.08rem 0 0; }
.tk-wr { font-size:1.0rem;font-weight:700;color:#111827;margin:0;text-align:right; }
.tk-wn { font-size:.72rem;color:#9ca3af;margin:0;text-align:right; }
.tk-h  { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.055em;color:#6b7280;margin:0; }
.tk-n  { font-size:.875rem;font-weight:600;color:#111827;margin:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
.tk-ns { color:#2563eb !important; }  /* selected name */
.tk-c  { font-size:.855rem;color:#374151;margin:0; }
.tk-nu { font-size:.855rem;color:#374151;font-variant-numeric:tabular-nums;margin:0; }
.tk-no { font-size:.855rem;color:#d97706;font-weight:600;font-variant-numeric:tabular-nums;margin:0; }
.tk-fl { font-size:.78rem;font-weight:600;color:#6b7280;margin:0; }
/* Detail panel */
.tk-dn { font-size:1.15rem;font-weight:800;color:#111827;margin:0; }
.tk-dd { font-size:.76rem;color:#6b7280;margin:.12rem 0 0; }
.tk-ml { font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#9ca3af;margin:0; }
.tk-mv { font-size:1.05rem;font-weight:700;color:#111827;margin:0;font-variant-numeric:tabular-nums; }
.tk-mo { font-size:1.05rem;font-weight:700;color:#d97706;margin:0;font-variant-numeric:tabular-nums; }
.tk-wl { font-size:.83rem;color:#374151;margin:.08rem 0 0; }
/* Daily row */
.tk-dy { font-size:.845rem;font-weight:600;color:#374151;margin:0; }
.tk-dt { font-size:.82rem;color:#6b7280;margin:0; }
.tk-dy.is-today { color:#2563eb; }
.tk-rt { font-size:.845rem;font-weight:600;color:#374151;font-variant-numeric:tabular-nums;margin:0;text-align:center; }
.tk-fn { font-size:.71rem;color:#9ca3af;font-style:italic;margin:.55rem 0 0; }
.tk-hi { font-size:.84rem;color:#9ca3af;font-style:italic;text-align:center;padding:1.2rem 0; }
/* Status badges */
.tkb { display:inline-block;font-size:.73rem;font-weight:600;padding:2px 9px;border-radius:20px;white-space:nowrap; }
.tkb-a { background:#d1fae5;color:#065f46; }
.tkb-p { background:#fef3c7;color:#92400e; }
.tkb-d { background:#f3f4f6;color:#6b7280; }
.tkb-r { background:#fee2e2;color:#991b1b; }

@media(max-width:768px){
    .tk-t { font-size:1.1rem !important; }
    div[data-testid="stHorizontalBlock"]:has(span.tk-tr) button { min-height:2rem !important; }
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
    fn = fetch_table_admin if current_role() in ("admin", "manager") else fetch_table
    for ob in ("job_number", "job_name", None):
        try:
            rows = list(fn("jobs", columns="*", limit=5000, order_by=ob) or [])
            if rows:
                return sort_jobs_by_number_then_name(rows)
        except Exception:
            pass
    try:
        return sort_jobs_by_number_then_name(list(fetch_jobs_with_order_fallback(limit=5000) or []))
    except Exception:
        return []


def _build_job_opts(jobs: list[dict]) -> tuple[list[str], dict[str, str]]:
    _, lbl_to_id, sorted_labels = build_job_dropdown_label_maps(jobs)
    nj = [f"NON-JOB -- {c}" for c in NON_JOB_CATEGORIES]
    return [_JOB_PLACEHOLDER] + sorted_labels + nj, lbl_to_id


def _resolve(label: str, lbl_to_id: dict[str, str]) -> tuple[str | None, str | None]:
    if not label or label == _JOB_PLACEHOLDER:
        return None, None
    if label.startswith("NON-JOB -- "):
        return None, label[len("NON-JOB -- "):].strip() or None
    return str(lbl_to_id.get(label) or "").strip() or None, None


def _ttype(e: dict) -> str:
    return "OT" if str(e.get("time_type") or "").upper() in ("OT", "O/T") else "ST"


def _week_hrs(eid: str, days: list[date], idx: dict) -> tuple[float, float]:
    s = o = 0.0
    for d in days:
        for e in idx.get((eid, d.isoformat()), []):
            h = float(e.get("hours") or 0)
            if _ttype(e) == "OT":
                o += h
            else:
                s += h
    return s, o


def _status(s: float, o: float) -> str:
    return "draft" if s + o == 0 else "pending"


def _badge(status: str) -> str:
    css = {"approved": "tkb-a", "pending": "tkb-p", "rejected": "tkb-r"}.get(status, "tkb-d")
    return f'<span class="tkb {css}">{html.escape(status.title())}</span>'


def _dstr(d: date) -> str:
    """Windows-safe short date: 'May 12'"""
    return f"{d.strftime('%b')} {d.day}"


def _wlabel(ws: date) -> str:
    we = ws + timedelta(days=6)
    return f"{_dstr(ws)} \u2013 {_dstr(we)}, {we.year}"


def _rk(eid: str, di: str, wi: str, f: str) -> str:
    return f"tk_{eid[:8]}_{di}_{wi.replace('-','')}_{f}"


def _clear_state(eid: str, days: list[date], ws: date) -> None:
    w = ws.isoformat()
    for d in days:
        for f in ("job", "st", "ot", "notes"):
            st.session_state.pop(_rk(eid, d.isoformat(), w, f), None)


# ---------------------------------------------------------------------------
# Save logic
# ---------------------------------------------------------------------------
def _save(eid: str, days: list[date], ws: date, lbl_to_id: dict[str, str], uid: Any) -> list[str]:
    ts   = datetime.now(timezone.utc).isoformat()
    w    = ws.isoformat()
    errs : list[str] = []
    for d in days:
        di = d.isoformat()
        jl = str(st.session_state.get(_rk(eid, di, w, "job"), "") or "").strip()
        sh = float(st.session_state.get(_rk(eid, di, w, "st"),  0.0) or 0.0)
        oh = float(st.session_state.get(_rk(eid, di, w, "ot"),  0.0) or 0.0)
        no = str(st.session_state.get(_rk(eid, di, w, "notes"), "") or "").strip()
        # Skip "—" placeholder note
        if no == "\u2014":
            no = ""
        if not jl or jl == _JOB_PLACEHOLDER:
            continue
        jid, nj = _resolve(jl, lbl_to_id)
        if not jid and not nj:
            continue
        for hrs, tt in ((sh, "ST"), (oh, "OT")):
            if hrs > 0:
                try:
                    upsert_time_entry(employee_id=eid, job_id=jid, work_date=d,
                                      hours=hrs, notes=no, created_by=uid,
                                      updated_at_iso=ts, non_job_code=nj, time_type=tt)
                except Exception as exc:
                    errs.append(f"{d.strftime('%a')}/{tt}: {exc}")
    return errs


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def _render_header(ws: date) -> None:
    with st.container(border=True):
        st.markdown('<span class="tk-header" aria-hidden="true"></span>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2.0, 3.2, 2.0], gap="small")
        with c1:
            st.markdown(
                '<p class="tk-t">\u23f0\u00a0 Timekeeping</p>'
                '<p class="tk-s">View and edit employee weekly time entries.</p>',
                unsafe_allow_html=True,
            )
        with c2:
            n1, n2, n3 = st.columns(3, gap="small")
            with n1:
                if st.button("\u2039 Previous Week", key="tk_prev", use_container_width=True):
                    st.session_state[_TK_WEEK] = (ws - timedelta(days=7)).isoformat()
                    st.rerun()
            with n2:
                if st.button("\U0001f4c5 Current Week", key="tk_cur", type="primary", use_container_width=True):
                    st.session_state[_TK_WEEK] = monday_of_week(date.today()).isoformat()
                    st.rerun()
            with n3:
                if st.button("Next Week \u203a", key="tk_next", use_container_width=True):
                    st.session_state[_TK_WEEK] = (ws + timedelta(days=7)).isoformat()
                    st.rerun()
        with c3:
            wl = _wlabel(ws)
            wn = ws.isocalendar()[1]
            st.markdown(
                f'<p class="tk-wr">\U0001f4c5\u00a0 {html.escape(wl)}</p>'
                f'<p class="tk-wn">Week {wn}</p>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Filter bar
# ---------------------------------------------------------------------------
def _render_filter(all_emps: list[dict]) -> tuple[str, str, bool]:
    depts = sorted({str(e.get("department") or "").strip()
                    for e in all_emps if str(e.get("department") or "").strip()})
    opts  = ["All Departments"] + depts
    # layout: search | dept | spacer | export
    c1, c2, _sp, c3 = st.columns([2.5, 1.8, 3.2, 0.85], gap="small")
    with c1:
        st.markdown('<span class="tk-filter" aria-hidden="true"></span>', unsafe_allow_html=True)
        q = st.text_input("s", placeholder="Search employee...", key="tk_q", label_visibility="collapsed")
    with c2:
        dept = st.selectbox("d", opts, key="tk_dept", label_visibility="collapsed")
    with c3:
        clicked = st.button("\u2913\u00a0 Export", key="tk_exp", use_container_width=True)
    return str(q or "").strip().lower(), str(dept or "All Departments"), clicked


# ---------------------------------------------------------------------------
# Employee table
# ---------------------------------------------------------------------------
# col widths: name | dept | week-start | st | ot | total | status | actions
_TC = [2.25, 1.15, 1.05, 0.80, 0.80, 0.80, 0.90, 0.52]
_TH_LBLS = [
    "Employee \u21c5", "Department \u21c5", "Week Start \u21c5",
    "S/T Total (Hrs) \u21c5", "O/T Total (Hrs) \u21c5", "Total Hours \u21c5",
    "Status \u21c5", "Actions",
]


def _render_table(visible: list[dict], days: list[date], ws: date, idx: dict) -> str | None:
    sel     = str(st.session_state.get(_TK_EMP) or "")
    new_sel : str | None = sel or None

    with st.container(border=True):
        st.markdown('<span class="tk-tbl" aria-hidden="true"></span>', unsafe_allow_html=True)

        # -- Header row
        hc = st.columns(_TC, gap="small")
        with hc[0]:
            st.markdown('<span class="tk-th" aria-hidden="true"></span>', unsafe_allow_html=True)
        for lbl, col in zip(_TH_LBLS, hc):
            with col:
                st.markdown(f'<p class="tk-h">{html.escape(lbl)}</p>', unsafe_allow_html=True)

        # -- Data rows
        for ri, emp in enumerate(visible):
            eid  = str(emp.get("id"))
            nm   = str(emp.get("name") or "").strip() or "\u2014"
            dept = str(emp.get("department") or "").strip() or "\u2014"
            s, o = _week_hrs(eid, days, idx)
            tot  = s + o
            over = tot > _OT_THRESHOLD
            is_sel = eid == sel
            z  = "r0" if ri % 2 == 0 else "r1"
            rc = " rs" if is_sel else ""

            rc2 = st.columns(_TC, gap="small")
            with rc2[0]:
                ncls = "tk-n" + (" tk-ns" if is_sel else "")
                wdt  = _dstr(ws)
                st.markdown(
                    f'<span class="tk-tr {z}{rc}" aria-hidden="true"></span>'
                    f'<p class="{ncls}">{html.escape(nm)}</p>',
                    unsafe_allow_html=True,
                )
            with rc2[1]:
                st.markdown(f'<p class="tk-c">{html.escape(dept)}</p>', unsafe_allow_html=True)
            with rc2[2]:
                st.markdown(f'<p class="tk-c">{html.escape(_dstr(ws))}, {ws.year}</p>', unsafe_allow_html=True)
            with rc2[3]:
                st.markdown(f'<p class="tk-nu">{s:.2f}</p>', unsafe_allow_html=True)
            with rc2[4]:
                oc = "tk-no" if o > 0 else "tk-nu"
                st.markdown(f'<p class="{oc}">{o:.2f}</p>', unsafe_allow_html=True)
            with rc2[5]:
                tc = "tk-no" if over else "tk-nu"
                st.markdown(f'<p class="{tc}">{tot:.2f}</p>', unsafe_allow_html=True)
            with rc2[6]:
                st.markdown(_badge(_status(s, o)), unsafe_allow_html=True)
            with rc2[7]:
                if st.button("\U0001f441\ufe0f", key=f"tkv_{eid}_{ws.isoformat()}",
                             use_container_width=True, help=f"{'Close' if is_sel else 'View'} {nm}"):
                    new_sel = None if is_sel else eid

        # -- Footer
        fs = sum(_week_hrs(str(e.get("id")), days, idx)[0] for e in visible)
        fo = sum(_week_hrs(str(e.get("id")), days, idx)[1] for e in visible)
        fc = st.columns(_TC, gap="small")
        with fc[0]:
            st.markdown(
                f'<span class="tk-tf" aria-hidden="true"></span>'
                f'<p class="tk-fl">{len(visible)} employee{"s" if len(visible) != 1 else ""}</p>',
                unsafe_allow_html=True,
            )
        with fc[3]: st.markdown(f'<p class="tk-fl">{fs:.2f}</p>', unsafe_allow_html=True)
        with fc[4]: st.markdown(f'<p class="tk-fl">{fo:.2f}</p>', unsafe_allow_html=True)
        with fc[5]: st.markdown(f'<p class="tk-fl">{fs+fo:.2f}</p>', unsafe_allow_html=True)

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
# Daily rows
# ---------------------------------------------------------------------------
# col widths: day | date | job/desc | st | ot | total | notes | chk
_DC = [0.60, 0.70, 3.20, 0.82, 0.82, 0.76, 2.20, 0.36]
_DH = ["Day", "Date", "Job / Description", "S/T (Hrs)", "O/T (Hrs)", "Total (Hrs)", "Notes", ""]


def _render_daily(eid: str, days: list[date], ws: date, idx: dict,
                  jopts: list[str], lbl_to_id: dict[str, str]) -> None:
    today = date.today()
    w     = ws.isoformat()

    # Header
    hc = st.columns(_DC, gap="small")
    with hc[0]:
        st.markdown('<span class="tk-dh" aria-hidden="true"></span>', unsafe_allow_html=True)
    for lbl, col in zip(_DH, hc):
        with col:
            st.markdown(
                f'<p style="font-size:10px;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:.055em;color:#6b7280;margin:0">{html.escape(lbl)}</p>',
                unsafe_allow_html=True,
            )

    for d in days:
        di    = d.isoformat()
        is_td = d == today
        tc    = " today-row" if is_td else ""

        ents   = idx.get((eid, di), [])
        st_ent = next((e for e in ents if _ttype(e) == "ST"), None)
        ot_ent = next((e for e in ents if _ttype(e) == "OT"), None)
        prim   = st_ent or ot_ent

        def _jlbl(ent: dict | None) -> str:
            if not ent:
                return _JOB_PLACEHOLDER
            jid = str(ent.get("job_id") or "").strip()
            nj  = str(ent.get("non_job_code") or "").strip()
            if jid:
                for lb, lid in lbl_to_id.items():
                    if str(lid) == jid:
                        return lb
            if nj:
                return f"NON-JOB -- {nj}"
            return _JOB_PLACEHOLDER

        ex_jlbl  = _jlbl(prim)
        ex_st    = float(st_ent.get("hours") or 0) if st_ent else 0.0
        ex_ot    = float(ot_ent.get("hours") or 0) if ot_ent else 0.0
        ex_notes = str((prim or {}).get("notes") or "").strip()

        # Notes display value: "—" for entry with no notes, "Add notes..." placeholder for empty row
        notes_val = ex_notes if ex_notes else ("\u2014" if prim else "")
        notes_ph  = "Add notes..." if not prim else "Add notes..."

        jk = _rk(eid, di, w, "job")
        sk = _rk(eid, di, w, "st")
        ok = _rk(eid, di, w, "ot")
        nk = _rk(eid, di, w, "notes")

        j_idx = jopts.index(ex_jlbl) if ex_jlbl in jopts else 0

        dlc = "tk-dy" + (" is-today" if is_td else "")
        dtc = "tk-dt" + (" is-today" if is_td else "")

        dc = st.columns(_DC, gap="small")
        with dc[0]:
            st.markdown(
                f'<span class="tk-dr{tc}" aria-hidden="true"></span>'
                f'<p class="{dlc}">{d.strftime("%a")}</p>',
                unsafe_allow_html=True,
            )
        with dc[1]:
            st.markdown(f'<p class="{dtc}">{html.escape(_dstr(d))}</p>', unsafe_allow_html=True)
        with dc[2]:
            sel_job = st.selectbox("J", jopts, index=j_idx, key=jk, label_visibility="collapsed")
        with dc[3]:
            new_st = st.number_input("ST", min_value=0.0, max_value=24.0, value=ex_st,
                                     step=0.25, format="%.2f", key=sk, label_visibility="collapsed")
        with dc[4]:
            new_ot = st.number_input("OT", min_value=0.0, max_value=24.0, value=ex_ot,
                                     step=0.25, format="%.2f", key=ok, label_visibility="collapsed")
        with dc[5]:
            row_tot = float(new_st) + float(new_ot)
            st.markdown(f'<p class="tk-rt">{row_tot:.2f}</p>', unsafe_allow_html=True)
        with dc[6]:
            st.text_input("N", value=notes_val, key=nk,
                          label_visibility="collapsed", placeholder=notes_ph)
        with dc[7]:
            # Checkbox: checked if entry exists
            chk = "\u2611" if prim else "\u2610"
            st.button(chk, key=f"tkchk_{eid[:8]}_{di}",
                      help=ex_notes or "No notes for this day")


# ---------------------------------------------------------------------------
# Detail panel
# ---------------------------------------------------------------------------
def _render_detail(eid: str, all_emps: list[dict], days: list[date], ws: date,
                   idx: dict, jopts: list[str], lbl_to_id: dict[str, str],
                   uid: Any, can_edit: bool) -> None:
    emp = next((e for e in all_emps if str(e.get("id")) == eid), None)
    if not emp:
        st.session_state.pop(_TK_EMP, None)
        return

    nm   = str(emp.get("name") or "").strip() or "\u2014"
    dept = str(emp.get("department") or "").strip() or "\u2014"
    s, o = _week_hrs(eid, days, idx)
    tot  = s + o
    over = tot > _OT_THRESHOLD
    stat = _status(s, o)

    # Last-updated metadata
    all_e: list[dict] = []
    for d in days:
        all_e.extend(idx.get((eid, d.isoformat()), []))
    lu = "\u2014"
    lb = "\u2014"
    if all_e:
        latest = max(all_e, key=lambda e: str(e.get("updated_at") or ""))
        raw = str(latest.get("updated_at") or "")
        if raw:
            try:
                dt  = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                mo  = dt.strftime("%b")
                lu  = f"{mo} {dt.day}, {dt.year} {dt.hour % 12 or 12}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"
            except Exception:
                lu = raw[:16]
        lb = str(latest.get("created_by") or "\u2014")

    with st.container(border=True):
        st.markdown('<span class="tk-dp" aria-hidden="true"></span>', unsafe_allow_html=True)

        # ---- Panel header (3 sections) ----
        d1, d2, d3 = st.columns([2.3, 4.2, 2.1], gap="small")

        with d1:
            st.markdown(
                f'<p class="tk-dn">{html.escape(nm)}&nbsp;&nbsp;{_badge(stat)}</p>'
                f'<p class="tk-dd">{html.escape(dept)}</p>',
                unsafe_allow_html=True,
            )

        with d2:
            wl = _wlabel(ws)
            st.markdown(
                f'<p class="tk-ml">\U0001f4c5\u00a0 Week</p>'
                f'<p class="tk-wl">{html.escape(wl)}</p>',
                unsafe_allow_html=True,
            )
            m1, m2, m3 = st.columns(3, gap="small")
            with m1:
                st.markdown(f'<p class="tk-ml">S/T Total</p>'
                            f'<p class="tk-mv">{s:.2f} hrs</p>', unsafe_allow_html=True)
            with m2:
                vc = "tk-mo" if o > 0 else "tk-mv"
                st.markdown(f'<p class="tk-ml">O/T Total</p>'
                            f'<p class="{vc}">{o:.2f} hrs</p>', unsafe_allow_html=True)
            with m3:
                ov = f' \u26a0' if over else ""
                st.markdown(f'<p class="tk-ml">Total Hours{ov}</p>'
                            f'<p class="tk-mv">{tot:.2f} hrs</p>', unsafe_allow_html=True)

        with d3:
            st.markdown('<span class="tk-da" aria-hidden="true"></span>', unsafe_allow_html=True)
            if can_edit:
                ba, bb, bc = st.columns([1.1, 1.5, 0.5], gap="small")
                with ba:
                    st.button("\u270f\ufe0f Edit Week", key=f"tked_{eid[:8]}", type="secondary")
                with bb:
                    if st.button("\U0001f4be Save Changes", key=f"tksv_{eid[:8]}_{ws.isoformat()}",
                                 type="primary", use_container_width=True):
                        errs = _save(eid, days, ws, lbl_to_id, uid)
                        if errs:
                            st.error("Saved with errors:\n" + "\n".join(errs))
                        else:
                            _clear_state(eid, days, ws)
                            try:
                                st.cache_data.clear()
                            except Exception:
                                pass
                            st.success("Week saved!")
                            st.rerun()
                with bc:
                    if st.button("\u2303", key="tkco", type="secondary", use_container_width=True,
                                 help="Collapse panel"):
                        st.session_state.pop(_TK_EMP, None)
                        st.session_state[_TK_VIEW] = "table"
                        st.session_state[_TK_EDIT] = False
                        st.rerun()
            else:
                if st.button("\u2303 Close", key="tkco2", type="secondary", use_container_width=True):
                    st.session_state.pop(_TK_EMP, None)
                    st.rerun()

        st.divider()

        # ---- Daily rows ----
        _render_daily(eid, days, ws, idx, jopts, lbl_to_id)

        # ---- Footer ----
        st.markdown(
            f'<p class="tk-fn">Last updated: {html.escape(lu)}'
            f'\u00a0\u00b7\u00a0by {html.escape(lb)}</p>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def _do_export(visible: list[dict], days: list[date], idx: dict,
               id_to_lbl: dict[str, str]) -> None:
    rows: list[dict] = []
    for emp in visible:
        eid = str(emp.get("id"))
        nm  = str(emp.get("name") or "")
        for d in days:
            for e in idx.get((eid, d.isoformat()), []):
                jid  = str(e.get("job_id") or "").strip()
                nj   = str(e.get("non_job_code") or "").strip()
                jlbl = id_to_lbl.get(jid, jid) if jid else (f"NON-JOB -- {nj}" if nj else "")
                rows.append({"Employee": nm, "Date": d.isoformat(), "Job": jlbl,
                             "Type": _ttype(e), "Hours": float(e.get("hours") or 0),
                             "Notes": str(e.get("notes") or "")})
    if not rows:
        st.info("No entries to export for this week.")
        return
    st.download_button("Download CSV", pd.DataFrame(rows).to_csv(index=False),
                       "timekeeping_export.csv", "text/csv", key="tkdl")


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
        ws = date.fromisoformat(str(st.session_state[_TK_WEEK]))
    except (ValueError, TypeError):
        ws = monday_of_week(today)
        st.session_state[_TK_WEEK] = ws.isoformat()
    if ws.weekday() != 0:
        ws = monday_of_week(ws)
        st.session_state[_TK_WEEK] = ws.isoformat()

    days = week_dates(ws)
    we   = days[-1]

    # Header
    _render_header(ws)

    # Load data
    all_emps = _load_employees()
    jobs_raw = _load_jobs()
    jopts, lbl_to_id = _build_job_opts(jobs_raw)
    id_to_lbl = {str(v): k for k, v in lbl_to_id.items()}

    try:
        grid = fetch_time_entries_between(ws, we)
    except Exception as exc:
        grid = []
        st.error(f"Could not load time entries: {exc}")
    idx = index_by_employee_date(grid)

    if not all_emps:
        st.warning("No active employees. Add employees under **Employees** in the sidebar.")
        return

    # Filter bar
    q, dept_f, exported = _render_filter(all_emps)

    visible = all_emps
    if q:
        visible = [e for e in visible if q in str(e.get("name") or "").lower()]
    if dept_f != "All Departments":
        visible = [e for e in visible if str(e.get("department") or "").strip() == dept_f]

    if exported:
        _do_export(visible, days, idx, id_to_lbl)

    if not visible:
        st.info("No employees match the current filter.")
        return

    if not can_edit:
        st.info("View-only mode. Sign in as admin, manager, pm, or employee to log time.")

    # Employee table
    sel_eid = _render_table(visible, days, ws, idx)

    # Detail panel
    if sel_eid:
        uid = current_profile().get("id")
        _render_detail(sel_eid, all_emps, days, ws, idx, jopts, lbl_to_id, uid, can_edit)
    else:
        st.markdown(
            '<p class="tk-hi">\u25b6\ufe0e\u00a0 Click an employee row to view their weekly timecard.</p>',
            unsafe_allow_html=True,
        )

    # Week summary
    wst = sum(_week_hrs(str(e.get("id")), days, idx)[0] for e in visible)
    wot = sum(_week_hrs(str(e.get("id")), days, idx)[1] for e in visible)
    st.caption(
        f"{_dstr(ws)} \u2013 {_dstr(we)}, {we.year}  \u00b7  "
        f"S/T: **{wst:.1f} h**  \u00b7  O/T: **{wot:.1f} h**  \u00b7  Total: **{wst+wot:.1f} h**"
    )
