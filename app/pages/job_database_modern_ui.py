"""Modern Jobs table UI components — clean SaaS/field-management dashboard style.

Public API
----------
inject_modern_jobs_css()
render_jobs_table(df_display, job_num_col, can_edit, jobs, ...)
render_job_row(row, full_row, job_num_col, can_edit, is_selected)
render_job_detail_panel(job_row, can_edit, admin_read, ...)
render_job_overview_tab(job_row, can_edit)
render_job_summary_cards(job_row)
render_activity_feed(job_row)
"""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from table_actions import IPS_PENDING_DELETE, TABLE_KEY_JOBS
except ImportError:
    from app.table_actions import IPS_PENDING_DELETE, TABLE_KEY_JOBS  # type: ignore

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

_MODERN_JOBS_CSS_KEY = "job_db_modern_ui_css_v3"

_STATUS_COLORS: dict[str, str] = {
    "active": "#16a34a",
    "complete": "#16a34a",
    "completed": "#16a34a",
    "closed": "#16a34a",
    "in progress": "#f59e0b",
    "awarded": "#f59e0b",
    "blocked": "#dc2626",
    "on hold": "#dc2626",
    "not started": "#64748b",
    "draft": "#94a3b8",
    "quoted": "#64748b",
    "submitted": "#64748b",
    "approved": "#22c55e",
    "scheduled": "#2563eb",
    "duplicate": "#64748b",
    "waiting on customer": "#0891b2",
    "electrical": "#7c3aed",
    "electrical / other trade": "#7c3aed",
}

_STATUS_BG_COLORS: dict[str, str] = {
    "active": "#dcfce7",
    "complete": "#dcfce7",
    "completed": "#dcfce7",
    "closed": "#dcfce7",
    "in progress": "#fef3c7",
    "awarded": "#fef3c7",
    "blocked": "#fee2e2",
    "on hold": "#fee2e2",
    "not started": "#f1f5f9",
    "draft": "#f8fafc",
    "quoted": "#f1f5f9",
    "submitted": "#f1f5f9",
    "approved": "#dcfce7",
    "scheduled": "#dbeafe",
    "duplicate": "#f1f5f9",
    "waiting on customer": "#e0f2fe",
    "electrical": "#f3e8ff",
    "electrical / other trade": "#f3e8ff",
}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _disp(v: Any, fallback: str = "—") -> str:
    s = str(v or "").strip()
    return s if s else fallback


def _money(v: Any) -> str:
    try:
        if v is None or str(v).strip() == "":
            return "—"
        fv = float(v)
        if fv == 0:
            return "—"
        return f"${fv:,.0f}"
    except Exception:
        return "—"


def _status_pill_html(status: Any) -> str:
    label = _disp(status)
    key = label.lower()
    color = _STATUS_COLORS.get(key, "#64748b")
    bg = _STATUS_BG_COLORS.get(key, "#f1f5f9")
    return (
        f'<span class="ips-mod-status-pill" '
        f'style="color:{color};background:{bg};border-color:{color}40;">'
        f"{html.escape(label)}</span>"
    )


def _date_disp(v: Any) -> str:
    raw = str(v or "").strip()
    if not raw or raw == "None":
        return "—"
    # Trim to date portion if it's a datetime string
    return raw[:10] if len(raw) > 10 else raw


# ──────────────────────────────────────────────────────────────────────────────
# CSS injection
# ──────────────────────────────────────────────────────────────────────────────

def inject_modern_jobs_css() -> None:
    """Inject all CSS for the modern jobs table UI. Idempotent."""
    if st.session_state.get(_MODERN_JOBS_CSS_KEY):
        return
    st.session_state[_MODERN_JOBS_CSS_KEY] = True
    st.markdown(
        """
<style>
/* ─── MODERN JOBS TABLE ─────────────────────────────────────────────────── */

/* Table wrapper card: remove default Streamlit border / shadow overrides */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor) {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 4px rgba(15,23,42,0.06) !important;
    padding: 0 !important;
    overflow: hidden !important;
}

/* Table header row */
.ips-mod-table-header {
    display: flex;
    align-items: center;
    padding: 0.55rem 1rem 0.55rem 1rem;
    background: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
    font-size: 0.72rem;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    user-select: none;
    gap: 0;
}
.ips-mod-th { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.ips-mod-th-num  { flex: 0 0 7%;  min-width: 64px; }
.ips-mod-th-name { flex: 1 1 22%; min-width: 140px; }
.ips-mod-th-cust { flex: 1 1 16%; min-width: 100px; }
.ips-mod-th-loc  { flex: 0 0 13%; min-width: 80px; }
.ips-mod-th-stat { flex: 0 0 11%; min-width: 80px; }
.ips-mod-th-amt  { flex: 0 0 9%;  min-width: 72px; text-align: right; }
.ips-mod-th-acts { flex: 0 0 7%;  min-width: 64px; }

/* ─── ROW OUTER WRAPPER ─────────────────────────────────────────────────── */
.ips-mod-row-outer {
    display: block;
    border-bottom: 1px solid #f1f5f9;
    transition: background 0.1s ease;
}
.ips-mod-row-outer:last-child { border-bottom: none; }

/* Row hover state */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    div[data-testid="stVerticalBlock"]:has(.ips-mod-row-marker):hover {
    background: #f8fafc !important;
    cursor: pointer;
}

/* Selected row: left blue accent border + slightly darker bg */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    div[data-testid="stVerticalBlock"]:has(.ips-mod-row-selected) {
    background: #eff6ff !important;
    box-shadow: inset 3px 0 0 #3b82f6 !important;
}

/* Force row containers to have consistent padding */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    div[data-testid="stVerticalBlock"]:has(.ips-mod-row-marker) {
    padding: 0.1rem 0.75rem 0.1rem 0.75rem !important;
    position: relative !important;
}

/* Reduce per-element margins inside rows for compact spacing */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    div[data-testid="stVerticalBlock"]:has(.ips-mod-row-marker)
    [data-testid="stElementContainer"] {
    margin-bottom: 0 !important;
    margin-top: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}

/* Row columns: no wrap, compact */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    div[data-testid="stVerticalBlock"]:has(.ips-mod-row-marker)
    [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 0.5rem !important;
    min-height: 2.8rem !important;
}

/* Force all text in table to dark ink */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    .stMarkdown, 
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    .stMarkdown p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    .stMarkdown span {
    color: #111827 !important;
}

/* ─── ROW CELL STYLES ──────────────────────────────────────────────────── */
.ips-mod-cell {
    display: block;
    font-size: 0.825rem;
    color: #374151;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.35;
}
.ips-mod-cell-bold {
    font-weight: 700;
    color: #1e3a5f !important;
}
.ips-mod-cell-muted {
    font-size: 0.75rem;
    color: #6b7280 !important;
}
.ips-mod-money-cell {
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    color: #1e3a5f !important;
}

/* ─── STATUS PILL ──────────────────────────────────────────────────────── */
.ips-mod-status-pill {
    display: inline-flex;
    align-items: center;
    border: 1px solid;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    line-height: 1;
    padding: 0.28rem 0.55rem;
    white-space: nowrap;
}

/* ─── ROW CHEVRON BUTTON ───────────────────────────────────────────────── */
/* Make the expand/toggle chevron button tiny and unobtrusive */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    .ips-mod-chevron-col .stButton > button {
    min-height: 1.6rem !important;
    height: 1.6rem !important;
    padding: 0 0.3rem !important;
    font-size: 0.8rem !important;
    border: none !important;
    background: transparent !important;
    color: #94a3b8 !important;
    box-shadow: none !important;
    border-radius: 4px !important;
    line-height: 1 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    .ips-mod-chevron-col .stButton > button:hover {
    background: #e2e8f0 !important;
    color: #3b82f6 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    .ips-mod-chevron-col-selected .stButton > button {
    color: #3b82f6 !important;
}

/* ─── ACTION BUTTONS ───────────────────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    .ips-mod-action-col .stButton > button {
    min-height: 1.7rem !important;
    height: 1.7rem !important;
    padding: 0 0.45rem !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    border: 1px solid #e2e8f0 !important;
    background: #ffffff !important;
    color: #374151 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    line-height: 1 !important;
    white-space: nowrap !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    .ips-mod-action-col .stButton > button:hover {
    background: #f1f5f9 !important;
    border-color: #cbd5e1 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-jobs-table-anchor)
    .ips-mod-action-col .stButton > button:disabled {
    opacity: 0.35 !important;
}

/* ─── DETAIL PANEL ─────────────────────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor) {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(15,23,42,0.08) !important;
    padding: 1rem 1.25rem !important;
    margin: 0.25rem 0 0.5rem 0 !important;
}

/* Detail panel header */
.ips-mod-detail-header {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
}
.ips-mod-detail-title-block { flex: 1 1 auto; min-width: 0; }
.ips-mod-detail-job-num {
    font-size: 0.8rem;
    font-weight: 700;
    color: #3b82f6;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin: 0 0 0.2rem 0;
}
.ips-mod-detail-job-title {
    font-size: 1.35rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0 0 0.2rem 0;
    line-height: 1.2;
    word-break: break-word;
}
.ips-mod-detail-customer {
    font-size: 0.875rem;
    color: #475569;
    margin: 0 0 0.4rem 0;
}
.ips-mod-detail-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1.5rem;
    font-size: 0.8rem;
    color: #64748b;
    align-items: center;
}
.ips-mod-detail-meta-item { display: flex; gap: 0.3rem; align-items: center; }
.ips-mod-detail-meta-label { font-weight: 600; color: #374151; }

/* Detail panel header buttons */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    .ips-mod-detail-hdr-btns .stButton > button {
    min-height: 1.9rem !important;
    height: 1.9rem !important;
    padding: 0 0.75rem !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    line-height: 1 !important;
}

/* Soft cards inside detail panel */
.ips-mod-soft-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.75rem;
}
.ips-mod-soft-card-title {
    font-size: 0.75rem;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 0.65rem 0;
}
.ips-mod-kv-row {
    display: flex;
    gap: 0.4rem;
    margin-bottom: 0.4rem;
    align-items: baseline;
    font-size: 0.825rem;
    line-height: 1.35;
}
.ips-mod-kv-label {
    color: #94a3b8;
    font-size: 0.75rem;
    font-weight: 600;
    min-width: 90px;
    flex-shrink: 0;
}
.ips-mod-kv-value {
    color: #1e293b;
    font-weight: 500;
    word-break: break-word;
}

/* Summary totals in detail panel */
.ips-mod-summary-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
}
.ips-mod-summary-item {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.6rem 0.75rem;
}
.ips-mod-summary-label {
    font-size: 0.7rem;
    color: #94a3b8;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.2rem;
}
.ips-mod-summary-value {
    font-size: 1.05rem;
    font-weight: 700;
    color: #0f172a;
    font-variant-numeric: tabular-nums;
}
.ips-mod-summary-value-total {
    color: #1d4ed8 !important;
}

/* Activity feed */
.ips-mod-activity-item {
    display: flex;
    gap: 0.6rem;
    align-items: flex-start;
    padding: 0.35rem 0;
    border-bottom: 1px solid #f1f5f9;
    font-size: 0.78rem;
    line-height: 1.4;
}
.ips-mod-activity-item:last-child { border-bottom: none; }
.ips-mod-activity-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #3b82f6;
    flex-shrink: 0;
    margin-top: 0.35rem;
}
.ips-mod-activity-ts { color: #94a3b8; font-size: 0.72rem; }
.ips-mod-activity-text { color: #374151; }

/* Detail panel Streamlit tab styling */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    [data-testid="stTabs"] [role="tablist"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0 !important;
    border-bottom: 2px solid #e2e8f0 !important;
    background: transparent !important;
    padding: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    margin-bottom: 1rem !important;
    overflow-x: auto !important;
    scrollbar-width: thin;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    [data-testid="stTabs"] [role="tab"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    [data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 0.5rem 0.85rem !important;
    margin-bottom: -2px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: #64748b !important;
    white-space: nowrap !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    [data-testid="stTabs"] [role="tab"][aria-selected="true"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    border-bottom-color: #3b82f6 !important;
    color: #1d4ed8 !important;
    font-weight: 700 !important;
    background: transparent !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    [data-testid="stTabs"] [role="tab"] p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    [data-testid="stTabs"] [data-baseweb="tab"] p {
    color: inherit !important;
    font-weight: inherit !important;
    margin: 0 !important;
}

/* Detail panel inner text color fixes */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    .stMarkdown,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    .stMarkdown p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    .stMarkdown span {
    color: #1e293b !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-mod-detail-panel-anchor)
    [data-testid="stCaptionContainer"] p {
    color: #64748b !important;
}

/* ─── MISC: Remove bottom margin from hidden markers ─────────────────── */
.ips-mod-row-marker, .ips-mod-detail-panel-anchor, .ips-mod-jobs-table-anchor {
    display: none !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Activity feed
# ──────────────────────────────────────────────────────────────────────────────

def render_activity_feed(job_row: dict[str, Any]) -> None:
    """Recent activity feed based on job timestamps and status."""
    items: list[tuple[str, str, str]] = []  # (ts, color, text)

    created = _date_disp(job_row.get("created_at"))
    updated = _date_disp(job_row.get("updated_at"))
    status = _disp(job_row.get("status"))
    jname = _disp(job_row.get("job_name"))
    cust = _disp(job_row.get("customer_name"))

    if updated and updated != "—" and updated != created:
        items.append((updated, "#3b82f6", f"Job record updated"))
    if status and status != "—":
        items.append((created, "#22c55e", f"Status: {status}"))
    if cust and cust != "—":
        items.append((created, "#94a3b8", f"Customer: {cust}"))
    if created and created != "—":
        items.append((created, "#94a3b8", f"Job created — {jname}"))

    if not items:
        st.caption("No activity recorded yet.")
        return

    lines = []
    for ts, color, text in items[:8]:
        lines.append(
            f'<div class="ips-mod-activity-item">'
            f'<span class="ips-mod-activity-dot" style="background:{color};"></span>'
            f'<div><span class="ips-mod-activity-text">{html.escape(text)}</span>'
            f'<br/><span class="ips-mod-activity-ts">{html.escape(ts)}</span></div>'
            f"</div>"
        )
    st.markdown("\n".join(lines), unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Summary cards
# ──────────────────────────────────────────────────────────────────────────────

def render_job_summary_cards(job_row: dict[str, Any]) -> None:
    """Labor / Material / Equipment / Total summary tiles (uses awarded_amount if no cost detail)."""
    awarded = _money(job_row.get("awarded_amount"))
    start = _date_disp(job_row.get("start_date"))
    end = _date_disp(job_row.get("target_completion_date") or job_row.get("due_date"))

    items = [
        ("Awarded", awarded, False),
        ("Start Date", start, False),
        ("Target Date", end, False),
    ]

    tiles = "".join(
        f'<div class="ips-mod-summary-item">'
        f'<div class="ips-mod-summary-label">{html.escape(lbl)}</div>'
        f'<div class="ips-mod-summary-value{"  ips-mod-summary-value-total" if is_total else ""}">'
        f"{html.escape(val)}</div></div>"
        for lbl, val, is_total in items
    )
    st.markdown(
        f'<div class="ips-mod-summary-grid">{tiles}</div>',
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Overview tab
# ──────────────────────────────────────────────────────────────────────────────

def render_job_overview_tab(job_row: dict[str, Any], can_edit: bool = False) -> None:  # noqa: ARG001
    """2-column card layout for the Overview tab of the detail panel."""
    jnum = _disp(job_row.get("job_number") or job_row.get("job_id") or job_row.get("id"))
    jname = _disp(job_row.get("job_name"))
    cust = _disp(job_row.get("customer_name"))
    supervisor = _disp(job_row.get("supervisor") or job_row.get("project_manager"))
    status = _disp(job_row.get("status"))
    estimate_num = _disp(job_row.get("Quote (estimate)") or job_row.get("quote_number"))
    description = _disp(job_row.get("description") or job_row.get("scope"), "No description provided.")
    start = _date_disp(job_row.get("start_date"))
    end = _date_disp(job_row.get("target_completion_date") or job_row.get("due_date"))
    awarded = _money(job_row.get("awarded_amount"))

    # ── Duration display ──────────────────────────────────────────────────
    duration = "—"
    try:
        from datetime import datetime as _dt
        if start != "—" and end != "—":
            d1 = _dt.fromisoformat(start[:10])
            d2 = _dt.fromisoformat(end[:10])
            days = (d2 - d1).days
            if days >= 0:
                duration = f"{days} days"
    except Exception:
        pass

    left_col, right_col = st.columns([1, 1], gap="medium")

    with left_col:
        left_rows = [
            ("Job Number", jnum),
            ("Customer", cust),
            ("Supervisor", supervisor),
            ("Status", None),  # rendered as pill
            ("Estimate #", estimate_num),
        ]
        kv_lines = []
        for lbl, val in left_rows:
            if lbl == "Status":
                rendered_val = _status_pill_html(status)
            else:
                rendered_val = (
                    f'<span class="ips-mod-kv-value">{html.escape(_disp(val))}</span>'
                )
            kv_lines.append(
                f'<div class="ips-mod-kv-row">'
                f'<span class="ips-mod-kv-label">{html.escape(lbl)}</span>'
                f"{rendered_val}</div>"
            )
        desc_html = (
            f'<div class="ips-mod-kv-row" style="flex-direction:column;gap:0.2rem;">'
            f'<span class="ips-mod-kv-label">Description</span>'
            f'<span class="ips-mod-kv-value" style="white-space:pre-wrap;">'
            f"{html.escape(description)}</span></div>"
        )
        st.markdown(
            f'<div class="ips-mod-soft-card">'
            f'<div class="ips-mod-soft-card-title">Job Details</div>'
            f'{"".join(kv_lines)}'
            f"{desc_html}"
            f"</div>",
            unsafe_allow_html=True,
        )

    with right_col:
        schedule_rows = [
            ("Start Date", start),
            ("End Date", end),
            ("Duration", duration),
            ("Awarded", awarded),
        ]
        sched_lines = "".join(
            f'<div class="ips-mod-kv-row">'
            f'<span class="ips-mod-kv-label">{html.escape(lbl)}</span>'
            f'<span class="ips-mod-kv-value">{html.escape(val)}</span></div>'
            for lbl, val in schedule_rows
        )
        st.markdown(
            f'<div class="ips-mod-soft-card">'
            f'<div class="ips-mod-soft-card-title">Schedule</div>'
            f"{sched_lines}"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="ips-mod-soft-card-title" style="margin-top:0.5rem;">Summary Totals</div>',
            unsafe_allow_html=True,
        )
        render_job_summary_cards(job_row)

    # ── Activity feed ─────────────────────────────────────────────────────
    st.markdown(
        '<div class="ips-mod-soft-card-title" style="margin-top:0.75rem;">Recent Activity</div>',
        unsafe_allow_html=True,
    )
    with st.container():
        render_activity_feed(job_row)


# ──────────────────────────────────────────────────────────────────────────────
# Detail panel
# ──────────────────────────────────────────────────────────────────────────────

def render_job_detail_panel(
    *,
    job_row: dict[str, Any],
    can_edit: bool,
    admin_read: bool,  # noqa: ARG001
    on_view: Any,
    on_edit: Any,
    on_collapse: Any,
) -> None:
    """Inline detail panel rendered directly below a selected table row."""
    with st.container(border=True):
        st.markdown(
            '<span class="ips-mod-detail-panel-anchor" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        jnum = _disp(job_row.get("job_number") or job_row.get("job_id") or job_row.get("id"))
        jname = _disp(job_row.get("job_name"), "Untitled Job")
        cust = _disp(job_row.get("customer_name"))
        status = _disp(job_row.get("status"))
        supervisor = _disp(job_row.get("supervisor") or job_row.get("project_manager"))
        created = _date_disp(job_row.get("created_at"))
        updated = _date_disp(job_row.get("updated_at"))

        # ── Header ─────────────────────────────────────────────────────────
        hdr_left, hdr_right = st.columns([3, 1], gap="medium")
        with hdr_left:
            st.markdown(
                f'<div class="ips-mod-detail-job-num">Job #{html.escape(jnum)}</div>'
                f'<div class="ips-mod-detail-job-title">{html.escape(jname)}</div>'
                f'<div class="ips-mod-detail-customer">{html.escape(cust)}</div>'
                f'<div class="ips-mod-detail-meta-row">'
                f"{_status_pill_html(status)}"
                f'<span class="ips-mod-detail-meta-item">'
                f'<span class="ips-mod-detail-meta-label">Supervisor:</span> {html.escape(supervisor)}</span>'
                f'<span class="ips-mod-detail-meta-item">'
                f'<span class="ips-mod-detail-meta-label">Created:</span> {html.escape(created)}</span>'
                f'<span class="ips-mod-detail-meta-item">'
                f'<span class="ips-mod-detail-meta-label">Updated:</span> {html.escape(updated)}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
        with hdr_right:
            st.markdown('<div class="ips-mod-detail-hdr-btns">', unsafe_allow_html=True)
            hb1, hb2, hb3 = st.columns(3, gap="small")
            with hb1:
                if st.button(
                    "Edit",
                    key=f"jdet_edit_{job_row.get('id')}",
                    use_container_width=True,
                    type="primary",
                    disabled=not can_edit,
                ):
                    on_edit()
            with hb2:
                if st.button(
                    "View",
                    key=f"jdet_view_{job_row.get('id')}",
                    use_container_width=True,
                ):
                    on_view()
            with hb3:
                if st.button(
                    "✕",
                    key=f"jdet_collapse_{job_row.get('id')}",
                    use_container_width=True,
                    help="Collapse this panel",
                ):
                    on_collapse()
            st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        # ── Tabs ───────────────────────────────────────────────────────────
        tabs = st.tabs(
            ["Overview", "Scope", "Financials", "Schedule", "Documents", "Notes", "Activity"]
        )

        # ── Overview ───────────────────────────────────────────────────────
        with tabs[0]:
            render_job_overview_tab(job_row, can_edit=can_edit)

        # ── Scope ──────────────────────────────────────────────────────────
        with tabs[1]:
            scope = _disp(job_row.get("scope") or job_row.get("description"), "No scope defined.")
            notes = _disp(job_row.get("notes"), "No notes.")
            st.markdown(
                f'<div class="ips-mod-soft-card">'
                f'<div class="ips-mod-soft-card-title">Scope of Work</div>'
                f'<p style="font-size:0.85rem;color:#1e293b;white-space:pre-wrap;margin:0;">'
                f"{html.escape(scope)}</p></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="ips-mod-soft-card">'
                f'<div class="ips-mod-soft-card-title">Notes</div>'
                f'<p style="font-size:0.85rem;color:#1e293b;white-space:pre-wrap;margin:0;">'
                f"{html.escape(notes)}</p></div>",
                unsafe_allow_html=True,
            )

        # ── Financials ─────────────────────────────────────────────────────
        with tabs[2]:
            awarded = _money(job_row.get("awarded_amount"))
            quote_num = _disp(job_row.get("Quote (estimate)") or job_row.get("quote_number"))
            fin_rows = [
                ("Awarded Amount", awarded),
                ("Estimate / Quote #", quote_num),
                ("Linked Estimate", _disp(job_row.get("Linked estimate"))),
            ]
            fin_lines = "".join(
                f'<div class="ips-mod-kv-row">'
                f'<span class="ips-mod-kv-label">{html.escape(lbl)}</span>'
                f'<span class="ips-mod-kv-value">{html.escape(val)}</span></div>'
                for lbl, val in fin_rows
            )
            st.markdown(
                f'<div class="ips-mod-soft-card">'
                f'<div class="ips-mod-soft-card-title">Financial Overview</div>'
                f"{fin_lines}"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.info("Open **View** for full labor, materials, and equipment costing detail.")

        # ── Schedule ───────────────────────────────────────────────────────
        with tabs[3]:
            start = _date_disp(job_row.get("start_date"))
            end = _date_disp(job_row.get("target_completion_date") or job_row.get("due_date"))
            completed = _date_disp(job_row.get("completed_date"))
            duration = "—"
            try:
                from datetime import datetime as _dt
                if start != "—" and end != "—":
                    d1 = _dt.fromisoformat(start[:10])
                    d2 = _dt.fromisoformat(end[:10])
                    days = (d2 - d1).days
                    if days >= 0:
                        duration = f"{days} days"
            except Exception:
                pass
            sched_data = [
                ("Start Date", start),
                ("End Date", end),
                ("Completed Date", completed),
                ("Duration", duration),
            ]
            sched_lines = "".join(
                f'<div class="ips-mod-kv-row">'
                f'<span class="ips-mod-kv-label">{html.escape(lbl)}</span>'
                f'<span class="ips-mod-kv-value">{html.escape(val)}</span></div>'
                for lbl, val in sched_data
            )
            st.markdown(
                f'<div class="ips-mod-soft-card">'
                f'<div class="ips-mod-soft-card-title">Schedule</div>'
                f"{sched_lines}"
                f"</div>",
                unsafe_allow_html=True,
            )

        # ── Documents ─────────────────────────────────────────────────────
        with tabs[4]:
            st.caption("Reference attachments and documents are available in the full detail view.")
            if st.button("Open Full View →", key=f"jdet_docs_open_{job_row.get('id')}"):
                on_view()

        # ── Notes ─────────────────────────────────────────────────────────
        with tabs[5]:
            notes = _disp(job_row.get("notes"), "No notes recorded.")
            st.markdown(
                f'<div class="ips-mod-soft-card">'
                f'<div class="ips-mod-soft-card-title">Job Notes</div>'
                f'<p style="font-size:0.85rem;color:#1e293b;white-space:pre-wrap;margin:0;">'
                f"{html.escape(notes)}</p></div>",
                unsafe_allow_html=True,
            )

        # ── Activity ──────────────────────────────────────────────────────
        with tabs[6]:
            st.markdown(
                '<div class="ips-mod-soft-card-title">Activity Log</div>',
                unsafe_allow_html=True,
            )
            render_activity_feed(job_row)


# ──────────────────────────────────────────────────────────────────────────────
# Row renderer
# ──────────────────────────────────────────────────────────────────────────────

def render_job_row(
    *,
    row: Any,
    full_row: dict[str, Any],
    job_num_col: str,
    can_edit: bool,
    is_selected: bool,
    on_select: Any,
    on_view: Any,
    on_delete: Any,
) -> None:
    """Render a single clickable job table row.

    Parameters
    ----------
    row        : DataFrame row (display columns only)
    full_row   : Full job dict from the jobs list (includes hidden columns)
    is_selected: Whether this row is currently expanded
    on_select  : Callable() — toggle expand/collapse
    on_view    : Callable() — open full view page
    on_delete  : Callable() — trigger delete flow
    """
    jid = str(row.get("id") or full_row.get("id") or "").strip()

    # Marker span — invisible, used for CSS :has() selectors
    marker_class = "ips-mod-row-marker " + (
        "ips-mod-row-selected" if is_selected else "ips-mod-row-unselected"
    )
    st.markdown(
        f'<span class="{marker_class}" data-jid="{html.escape(jid)}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    # Column weights:
    # chevron | job# | name | customer | location | status | amount | view | del
    col_w = [0.28, 0.75, 2.0, 1.5, 1.1, 0.95, 0.85, 0.42, 0.38]
    cols = st.columns(col_w, gap="small")

    job_num = _disp(row.get(job_num_col) or full_row.get(job_num_col) or full_row.get("job_number"))
    job_name = _disp(row.get("job_name") or full_row.get("job_name"), "Untitled")
    customer = _disp(row.get("customer_name") or full_row.get("customer_name"))
    location = _disp(row.get("Location") or full_row.get("Location") or full_row.get("location"))
    status = row.get("status") or full_row.get("status")
    amount = _money(row.get("awarded_amount") or full_row.get("awarded_amount"))

    # ── Chevron toggle ──────────────────────────────────────────────────
    with cols[0]:
        chevron = "▾" if is_selected else "▸"
        st.markdown(
            f'<span class="ips-mod-chevron-col{"  ips-mod-chevron-col-selected" if is_selected else ""}" '
            f'aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        if st.button(
            chevron,
            key=f"jrow_chev_{jid}",
            use_container_width=True,
            help="Expand / collapse job details",
        ):
            on_select()

    # ── Job number ──────────────────────────────────────────────────────
    with cols[1]:
        num_style = "ips-mod-cell ips-mod-cell-bold" if is_selected else "ips-mod-cell"
        st.markdown(
            f'<span class="{num_style}" title="{html.escape(job_num, quote=True)}">'
            f"{html.escape(job_num)}</span>",
            unsafe_allow_html=True,
        )

    # ── Job name ────────────────────────────────────────────────────────
    with cols[2]:
        st.markdown(
            f'<span class="ips-mod-cell" title="{html.escape(job_name, quote=True)}">'
            f"{html.escape(job_name)}</span>",
            unsafe_allow_html=True,
        )

    # ── Customer ────────────────────────────────────────────────────────
    with cols[3]:
        st.markdown(
            f'<span class="ips-mod-cell ips-mod-cell-muted" title="{html.escape(customer, quote=True)}">'
            f"{html.escape(customer)}</span>",
            unsafe_allow_html=True,
        )

    # ── Location ────────────────────────────────────────────────────────
    with cols[4]:
        st.markdown(
            f'<span class="ips-mod-cell ips-mod-cell-muted" title="{html.escape(location, quote=True)}">'
            f"{html.escape(location)}</span>",
            unsafe_allow_html=True,
        )

    # ── Status pill ────────────────────────────────────────────────────
    with cols[5]:
        st.markdown(_status_pill_html(status), unsafe_allow_html=True)

    # ── Awarded amount ─────────────────────────────────────────────────
    with cols[6]:
        st.markdown(
            f'<span class="ips-mod-cell ips-mod-money-cell">{html.escape(amount)}</span>',
            unsafe_allow_html=True,
        )

    # ── View button ────────────────────────────────────────────────────
    with cols[7]:
        st.markdown('<span class="ips-mod-action-col" aria-hidden="true"></span>', unsafe_allow_html=True)
        if st.button("View", key=f"jrow_view_{jid}", use_container_width=True, help="Open full job view"):
            on_view()

    # ── Delete button ──────────────────────────────────────────────────
    with cols[8]:
        st.markdown('<span class="ips-mod-action-col" aria-hidden="true"></span>', unsafe_allow_html=True)
        del_help = (
            "Only admin or manager can delete jobs."
            if not can_edit
            else "Delete this job (blocked if costing data exists)."
        )
        if st.button(
            "🗑",
            key=f"jrow_del_{jid}",
            use_container_width=True,
            disabled=not can_edit,
            help=del_help,
        ):
            on_delete()


# ──────────────────────────────────────────────────────────────────────────────
# Main table renderer
# ──────────────────────────────────────────────────────────────────────────────

def render_jobs_table(
    *,
    df_display: Any,
    job_num_col: str,
    can_edit: bool,
    jobs: list[dict[str, Any]],
    admin_read: bool = False,
    customer_name_by_id: dict[str, str] | None = None,
) -> None:
    """Render the modern jobs table with inline expand/collapse detail panels.

    Replaces the checkbox-based ``st.columns`` table.  Selected row stored in
    ``st.session_state.selected_job_id``.
    """
    inject_modern_jobs_css()

    jobs_by_id: dict[str, dict[str, Any]] = {
        str(j.get("id") or ""): j for j in jobs if j.get("id")
    }

    selected_jid = str(st.session_state.get("selected_job_id") or "").strip()

    with st.container(border=True):
        st.markdown(
            '<span class="ips-mod-jobs-table-anchor" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        # ── Table header ───────────────────────────────────────────────────
        st.markdown(
            '<div class="ips-mod-table-header">'
            '<span class="ips-mod-th" style="flex:0 0 3%;min-width:32px;"></span>'
            '<span class="ips-mod-th ips-mod-th-num">Job #</span>'
            '<span class="ips-mod-th ips-mod-th-name">Job Name</span>'
            '<span class="ips-mod-th ips-mod-th-cust">Customer</span>'
            '<span class="ips-mod-th ips-mod-th-loc">Location</span>'
            '<span class="ips-mod-th ips-mod-th-stat">Status</span>'
            '<span class="ips-mod-th ips-mod-th-amt">Awarded</span>'
            '<span class="ips-mod-th ips-mod-th-acts" style="text-align:right;">Actions</span>'
            "</div>",
            unsafe_allow_html=True,
        )

        # ── Rows ───────────────────────────────────────────────────────────
        for _, row in df_display.iterrows():
            jid = str(row.get("id") or "").strip()
            if not jid:
                continue

            full_row = jobs_by_id.get(jid, dict(row))
            is_selected = jid == selected_jid

            # ── Render row ────────────────────────────────────────────────
            def _on_select(j=jid):
                if st.session_state.get("selected_job_id") == j:
                    st.session_state["selected_job_id"] = None
                else:
                    st.session_state["selected_job_id"] = j
                    # Clear edit/view mode so we stay in list
                    st.session_state.setdefault("job_view_mode", "list")
                st.rerun()

            def _on_view(j=jid):
                st.session_state["job_view_mode"] = "view"
                st.session_state["selected_job_id"] = j
                st.session_state.pop("job_mode", None)
                st.session_state.pop("job_edit_id", None)
                st.rerun()

            def _on_delete(j=jid):
                pending = st.session_state.get(IPS_PENDING_DELETE)
                if not isinstance(pending, dict):
                    pending = {}
                    st.session_state[IPS_PENDING_DELETE] = pending
                pending[TABLE_KEY_JOBS] = [j]
                st.rerun()

            render_job_row(
                row=row,
                full_row=full_row,
                job_num_col=job_num_col,
                can_edit=can_edit,
                is_selected=is_selected,
                on_select=_on_select,
                on_view=_on_view,
                on_delete=_on_delete,
            )

            # ── Inline detail panel ───────────────────────────────────────
            if is_selected:
                def _on_detail_view(j=jid):
                    st.session_state["job_view_mode"] = "view"
                    st.session_state["selected_job_id"] = j
                    st.session_state.pop("job_mode", None)
                    st.session_state.pop("job_edit_id", None)
                    st.rerun()

                def _on_detail_edit(j=jid):
                    st.session_state["job_view_mode"] = "edit"
                    st.session_state["selected_job_id"] = j
                    st.session_state["job_mode"] = "edit"
                    st.session_state["job_edit_id"] = j
                    st.session_state.pop("job_number_manual_input", None)
                    st.rerun()

                def _on_detail_collapse():
                    st.session_state["selected_job_id"] = None
                    st.rerun()

                render_job_detail_panel(
                    job_row=full_row,
                    can_edit=can_edit,
                    admin_read=admin_read,
                    on_view=_on_detail_view,
                    on_edit=_on_detail_edit,
                    on_collapse=_on_detail_collapse,
                )
