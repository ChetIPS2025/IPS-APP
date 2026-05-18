"""Modern Job Database UI — clean SaaS/enterprise dashboard style.

Provides a replacement table + inline detail panel for job_database.py.

Public API
----------
inject_modern_jobs_css()
render_jobs_table(df_display, job_num_col, can_edit, jobs, admin_read, customer_name_by_id)
render_job_row(row, full_row, job_num_col, can_edit, is_selected, on_select, on_view, on_delete)
render_job_detail_panel(job_row, can_edit, admin_read, on_view, on_edit, on_collapse)
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

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_CSS_KEY = "jdb_modern_ui_css_v5"

_STATUS_STYLES: dict[str, tuple[str, str]] = {
    # status_lower: (text_color, bg_color)
    "active":           ("#166534", "#dcfce7"),
    "complete":         ("#166534", "#dcfce7"),
    "completed":        ("#166534", "#dcfce7"),
    "closed":           ("#166534", "#dcfce7"),
    "approved":         ("#166534", "#dcfce7"),
    "in progress":      ("#92400e", "#fef3c7"),
    "awarded":          ("#92400e", "#fef3c7"),
    "on hold":          ("#92400e", "#fef3c7"),
    "scheduled":        ("#1e40af", "#dbeafe"),
    "blocked":          ("#991b1b", "#fee2e2"),
    "cancelled":        ("#991b1b", "#fee2e2"),
    "not started":      ("#374151", "#f3f4f6"),
    "draft":            ("#374151", "#f3f4f6"),
    "quoted":           ("#374151", "#f3f4f6"),
    "submitted":        ("#374151", "#f3f4f6"),
    "duplicate":        ("#374151", "#f3f4f6"),
    "waiting on customer": ("#0e7490", "#e0f2fe"),
    "electrical":       ("#5b21b6", "#ede9fe"),
    "electrical / other trade": ("#5b21b6", "#ede9fe"),
}
_STATUS_DEFAULT = ("#374151", "#f3f4f6")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _s(v: Any, fallback: str = "—") -> str:
    val = str(v or "").strip()
    return val if val and val.lower() != "none" else fallback


def _money(v: Any) -> str:
    try:
        if v is None or str(v).strip() in ("", "None"):
            return "—"
        f = float(v)
        return "—" if f == 0 else f"${f:,.0f}"
    except Exception:
        return "—"


def _date(v: Any) -> str:
    raw = str(v or "").strip()
    if not raw or raw.lower() in ("none", "nan", ""):
        return "—"
    return raw[:10] if len(raw) > 10 else raw


def _status_pill(status: Any, *, small: bool = False) -> str:
    label = _s(status)
    fg, bg = _STATUS_STYLES.get(label.lower(), _STATUS_DEFAULT)
    sz = "0.68rem" if small else "0.72rem"
    pad = "0.2rem 0.45rem" if small else "0.28rem 0.6rem"
    return (
        f'<span style="display:inline-flex;align-items:center;'
        f'border-radius:999px;font-size:{sz};font-weight:700;line-height:1;'
        f'padding:{pad};white-space:nowrap;'
        f'color:{fg};background:{bg};">'
        f"{html.escape(label)}</span>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CSS injection
# ─────────────────────────────────────────────────────────────────────────────

def inject_modern_jobs_css() -> None:
    """Inject all modern-jobs CSS once per session."""
    if st.session_state.get(_CSS_KEY):
        return
    st.session_state[_CSS_KEY] = True
    st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════
   JOB DATABASE — MODERN TABLE
═══════════════════════════════════════════════════════════════ */

/* ── Table host card ───────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host) {
    background: #ffffff !important;
    border: 1px solid #e5eaf2 !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 4px rgba(15,23,42,0.05) !important;
    padding: 0 !important;
    overflow: hidden !important;
}

/* ── HTML header row ───────────────────────────────────────── */
.jmod-thead {
    display: grid;
    grid-template-columns: 7% 18% 14% 9% 10% 9% 9% 9% 9% 6%;
    align-items: center;
    padding: 0 1rem;
    height: 2.4rem;
    background: #f8fafc;
    border-bottom: 1px solid #e5eaf2;
    font-size: 0.7rem;
    font-weight: 700;
    color: #6b7280;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    user-select: none;
}
.jmod-th { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }

/* ── Row container (wraps Streamlit columns) ───────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    div[data-testid="stVerticalBlock"]:has(> .jmod-row) {
    position: relative !important;
    transition: background 0.1s !important;
    border-bottom: 1px solid #f1f5f9 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    div[data-testid="stVerticalBlock"]:has(> .jmod-row):last-child {
    border-bottom: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    div[data-testid="stVerticalBlock"]:has(> .jmod-row):hover {
    background: #f8fafc !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    div[data-testid="stVerticalBlock"]:has(> .jmod-row-selected) {
    background: #eff6ff !important;
    box-shadow: inset 3px 0 0 #2563eb !important;
}

/* ── Padding / column alignment inside rows ────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    div[data-testid="stVerticalBlock"]:has(> .jmod-row) {
    padding: 0 0.75rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    div[data-testid="stVerticalBlock"]:has(> .jmod-row)
    [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 0.4rem !important;
    min-height: 2.75rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    div[data-testid="stVerticalBlock"]:has(> .jmod-row)
    [data-testid="stElementContainer"] {
    margin: 0 !important; padding: 0 !important;
}

/* ── Force dark text inside table ──────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    .stMarkdown, 
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    .stMarkdown p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    .stMarkdown span {
    color: #111827 !important;
}

/* ── Cell base styles ──────────────────────────────────────── */
.jmod-cell {
    font-size: 0.8rem; color: #374151;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    display: block; line-height: 1.35;
}
.jmod-cell-num {
    font-size: 0.8rem; font-weight: 700; color: #2563eb !important;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    display: block; cursor: pointer;
}
.jmod-cell-bold { font-weight: 700; color: #111827 !important; }
.jmod-cell-muted { font-size: 0.75rem; color: #6b7280 !important; }
.jmod-cell-money {
    text-align: right; font-variant-numeric: tabular-nums;
    font-weight: 600; color: #1e3a5f !important;
}

/* ── Chevron / toggle button ───────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    .jmod-chev .stButton > button {
    min-height: 1.5rem !important; height: 1.5rem !important;
    padding: 0 0.3rem !important; font-size: 0.75rem !important;
    border: none !important; background: transparent !important;
    color: #9ca3af !important; box-shadow: none !important;
    border-radius: 4px !important; line-height: 1 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    .jmod-chev .stButton > button:hover {
    background: #e5e7eb !important; color: #2563eb !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    .jmod-chev-on .stButton > button {
    color: #2563eb !important;
}

/* ── Action (View / Delete) buttons ────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    .jmod-act .stButton > button {
    min-height: 1.65rem !important; height: 1.65rem !important;
    padding: 0 0.4rem !important; font-size: 0.7rem !important;
    font-weight: 600 !important; border-radius: 6px !important;
    border: 1px solid #e5e7eb !important;
    background: #ffffff !important; color: #374151 !important;
    box-shadow: none !important; line-height: 1 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    .jmod-act .stButton > button:hover {
    background: #f3f4f6 !important; border-color: #d1d5db !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-table-host)
    .jmod-act .stButton > button:disabled { opacity: 0.35 !important; }

/* ═══════════════════════════════════════════════════════════════
   JOB DATABASE — DETAIL PANEL
═══════════════════════════════════════════════════════════════ */

div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host) {
    background: #ffffff !important;
    border: 1.5px solid #2563eb !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 16px rgba(37,99,235,0.10) !important;
    padding: 1.25rem 1.5rem 1rem !important;
    margin: 0.35rem 0 0.75rem !important;
}

/* Panel header */
.jmod-panel-num {
    font-size: 0.78rem; font-weight: 800; color: #2563eb;
    letter-spacing: 0.06em; text-transform: uppercase; margin: 0 0 0.18rem;
}
.jmod-panel-title {
    font-size: 1.3rem; font-weight: 800; color: #0f172a;
    line-height: 1.2; margin: 0 0 0.2rem; word-break: break-word;
}
.jmod-panel-customer {
    font-size: 0.85rem; color: #475569; margin: 0 0 0.45rem;
}
.jmod-panel-meta {
    display: flex; flex-wrap: wrap; gap: 0.5rem 1.25rem;
    align-items: center; font-size: 0.78rem; color: #64748b;
}
.jmod-panel-meta-lbl { font-weight: 700; color: #374151; margin-right: 0.2rem; }

/* Panel header action buttons */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    .jmod-hdr-btn .stButton > button {
    min-height: 1.85rem !important; height: 1.85rem !important;
    padding: 0 0.7rem !important; font-size: 0.78rem !important;
    font-weight: 600 !important; border-radius: 8px !important;
    line-height: 1 !important;
}

/* Tabs inside panel */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    [data-testid="stTabs"] [role="tablist"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0 !important; border-radius: 0 !important; box-shadow: none !important;
    background: transparent !important; padding: 0 !important;
    border-bottom: 2px solid #e5eaf2 !important;
    margin-bottom: 1rem !important; overflow-x: auto !important;
    scrollbar-width: thin;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    [data-testid="stTabs"] [role="tab"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    [data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important; border: none !important;
    border-bottom: 2.5px solid transparent !important; border-radius: 0 !important;
    box-shadow: none !important; padding: 0.5rem 1rem !important;
    margin-bottom: -2px !important; font-size: 0.82rem !important;
    font-weight: 500 !important; color: #64748b !important;
    white-space: nowrap !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    [data-testid="stTabs"] [role="tab"][aria-selected="true"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    border-bottom-color: #2563eb !important;
    color: #1d4ed8 !important; font-weight: 700 !important;
    background: transparent !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    [data-testid="stTabs"] [role="tab"] p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    [data-testid="stTabs"] [data-baseweb="tab"] p {
    color: inherit !important; font-weight: inherit !important; margin: 0 !important;
}

/* Info cards inside panel */
.jmod-card {
    background: #f8fafc; border: 1px solid #e5eaf2;
    border-radius: 10px; padding: 0.9rem 1.1rem; height: 100%;
}
.jmod-card-title {
    font-size: 0.7rem; font-weight: 700; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.06em; margin: 0 0 0.7rem;
}
.jmod-kv { display: flex; gap: 0; margin-bottom: 0.42rem; font-size: 0.82rem; }
.jmod-kv-lbl {
    color: #94a3b8; font-size: 0.73rem; font-weight: 600;
    min-width: 98px; flex-shrink: 0;
}
.jmod-kv-val { color: #1e293b; font-weight: 500; word-break: break-word; }

/* Summary grid */
.jmod-sum-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;
}
.jmod-sum-item {
    background: #ffffff; border: 1px solid #e5eaf2;
    border-radius: 8px; padding: 0.6rem 0.75rem;
}
.jmod-sum-lbl {
    font-size: 0.68rem; color: #9ca3af; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.15rem;
}
.jmod-sum-val {
    font-size: 1.05rem; font-weight: 800; color: #0f172a;
    font-variant-numeric: tabular-nums;
}
.jmod-sum-val-primary { color: #1d4ed8 !important; }

/* Activity feed */
.jmod-act-item {
    display: flex; gap: 0.55rem; align-items: flex-start;
    padding: 0.32rem 0; border-bottom: 1px solid #f1f5f9; font-size: 0.78rem;
}
.jmod-act-item:last-child { border-bottom: none; }
.jmod-act-dot {
    width: 7px; height: 7px; border-radius: 50%;
    flex-shrink: 0; margin-top: 0.32rem;
}
.jmod-act-ts { color: #94a3b8; font-size: 0.7rem; }
.jmod-act-text { color: #374151; line-height: 1.4; }

/* Inner text colour fix */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    .stMarkdown,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    .stMarkdown p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    .stMarkdown span {
    color: #1e293b !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jmod-panel-host)
    [data-testid="stCaptionContainer"] p { color: #64748b !important; }

/* Hide helper markers */
.jmod-table-host, .jmod-panel-host, .jmod-row, .jmod-row-selected,
.jmod-chev, .jmod-chev-on, .jmod-act { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Activity feed
# ─────────────────────────────────────────────────────────────────────────────

def render_activity_feed(job_row: dict[str, Any]) -> None:
    created = _date(job_row.get("created_at"))
    updated = _date(job_row.get("updated_at"))
    status  = _s(job_row.get("status"))
    jname   = _s(job_row.get("job_name"), "this job")
    items: list[tuple[str, str, str]] = []
    if updated and updated != "—" and updated != created:
        items.append((updated, "#2563eb", "Job record updated"))
    if status and status != "—":
        items.append((created, "#16a34a", f"Status set to {status}"))
    items.append((created, "#64748b", f"Job created — {jname}"))
    lines = [
        f'<div class="jmod-act-item">'
        f'<span class="jmod-act-dot" style="background:{c};"></span>'
        f'<div><span class="jmod-act-text">{html.escape(t)}</span>'
        f'<br><span class="jmod-act-ts">{html.escape(ts)}</span></div></div>'
        for ts, c, t in items[:6]
    ]
    st.markdown("\n".join(lines) if lines else "<p style='color:#64748b;font-size:.8rem;'>No recent activity.</p>",
                unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Summary cards
# ─────────────────────────────────────────────────────────────────────────────

def render_job_summary_cards(job_row: dict[str, Any]) -> None:
    awarded  = _money(job_row.get("awarded_amount"))
    start    = _date(job_row.get("start_date"))
    end      = _date(job_row.get("target_completion_date") or job_row.get("due_date"))
    duration = "—"
    try:
        from datetime import datetime as _dt
        if start != "—" and end != "—":
            d = (_dt.fromisoformat(end[:10]) - _dt.fromisoformat(start[:10])).days
            if d >= 0:
                duration = f"{d}d"
    except Exception:
        pass
    tiles = [
        ("Awarded",   awarded,  True),
        ("Start",     start,    False),
        ("End",       end,      False),
        ("Duration",  duration, False),
    ]
    html_parts = "".join(
        f'<div class="jmod-sum-item">'
        f'<div class="jmod-sum-lbl">{html.escape(l)}</div>'
        f'<div class="jmod-sum-val{"  jmod-sum-val-primary" if p else ""}">{html.escape(v)}</div>'
        f"</div>"
        for l, v, p in tiles
    )
    st.markdown(f'<div class="jmod-sum-grid">{html_parts}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Overview tab
# ─────────────────────────────────────────────────────────────────────────────

def render_job_overview_tab(job_row: dict[str, Any], can_edit: bool = False) -> None:  # noqa: ARG001
    jnum       = _s(job_row.get("job_number") or job_row.get("job_id") or job_row.get("id"))
    jname      = _s(job_row.get("job_name"), "Untitled Job")
    customer   = _s(job_row.get("customer_name"))
    supervisor = _s(job_row.get("supervisor") or job_row.get("project_manager"))
    status     = _s(job_row.get("status"))
    est_num    = _s(job_row.get("Quote (estimate)") or job_row.get("quote_number"))
    desc       = _s(job_row.get("description") or job_row.get("scope"), "No description provided.")
    start      = _date(job_row.get("start_date"))
    end        = _date(job_row.get("target_completion_date") or job_row.get("due_date"))
    duration   = "—"
    try:
        from datetime import datetime as _dt
        if start != "—" and end != "—":
            d = (_dt.fromisoformat(end[:10]) - _dt.fromisoformat(start[:10])).days
            if d >= 0:
                duration = f"{d} days"
    except Exception:
        pass

    left_col, right_col = st.columns([1, 1], gap="medium")

    # ── Job Information card ──────────────────────────────────────────────
    with left_col:
        kvs = [
            ("Job Number",  jnum),
            ("Customer",    customer),
            ("Supervisor",  supervisor),
            ("Status",      None),
            ("Estimate #",  est_num),
        ]
        rows_html = ""
        for lbl, val in kvs:
            if lbl == "Status":
                v_html = _status_pill(status)
            else:
                v_html = f'<span class="jmod-kv-val">{html.escape(_s(val))}</span>'
            rows_html += (
                f'<div class="jmod-kv">'
                f'<span class="jmod-kv-lbl">{html.escape(lbl)}</span>'
                f"{v_html}</div>"
            )
        desc_html = (
            f'<div class="jmod-kv" style="flex-direction:column;gap:.15rem;margin-top:.35rem;">'
            f'<span class="jmod-kv-lbl">Description</span>'
            f'<span class="jmod-kv-val" style="white-space:pre-wrap;">'
            f"{html.escape(desc)}</span></div>"
        )
        st.markdown(
            f'<div class="jmod-card">'
            f'<div class="jmod-card-title">Job Information</div>'
            f"{rows_html}{desc_html}</div>",
            unsafe_allow_html=True,
        )

    # ── Schedule card ────────────────────────────────────────────────────
    with right_col:
        sched_kvs = [("Start Date", start), ("End Date", end), ("Duration", duration)]
        sched_html = "".join(
            f'<div class="jmod-kv">'
            f'<span class="jmod-kv-lbl">{html.escape(l)}</span>'
            f'<span class="jmod-kv-val">{html.escape(v)}</span></div>'
            for l, v in sched_kvs
        )
        st.markdown(
            f'<div class="jmod-card">'
            f'<div class="jmod-card-title">Schedule</div>'
            f"{sched_html}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)

    # ── Bottom row: Summary + Activity ───────────────────────────────────
    sum_col, act_col = st.columns([1, 1], gap="medium")
    with sum_col:
        st.markdown(
            '<div class="jmod-card">'
            '<div class="jmod-card-title">Summary</div>',
            unsafe_allow_html=True,
        )
        render_job_summary_cards(job_row)
        st.markdown("</div>", unsafe_allow_html=True)

    with act_col:
        st.markdown(
            '<div class="jmod-card">'
            '<div class="jmod-card-title">Recent Activity</div>',
            unsafe_allow_html=True,
        )
        render_activity_feed(job_row)
        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Detail panel
# ─────────────────────────────────────────────────────────────────────────────

def render_job_detail_panel(
    *,
    job_row:    dict[str, Any],
    can_edit:   bool,
    admin_read: bool,  # noqa: ARG001
    on_view:    Any,
    on_edit:    Any,
    on_collapse: Any,
) -> None:
    with st.container(border=True):
        st.markdown('<span class="jmod-panel-host" aria-hidden="true"></span>', unsafe_allow_html=True)

        jid      = str(job_row.get("id") or "").strip()
        jnum     = _s(job_row.get("job_number") or job_row.get("job_id") or jid[:8])
        jname    = _s(job_row.get("job_name"), "Untitled Job")
        customer = _s(job_row.get("customer_name"))
        status   = _s(job_row.get("status"))
        sup      = _s(job_row.get("supervisor") or job_row.get("project_manager"))
        created  = _date(job_row.get("created_at"))
        updated  = _date(job_row.get("updated_at"))

        # ── Header ───────────────────────────────────────────────────────
        hdr_l, hdr_r = st.columns([3, 1.1], gap="medium")
        with hdr_l:
            st.markdown(
                f'<div class="jmod-panel-num">Job #{html.escape(jnum)}</div>'
                f'<div class="jmod-panel-title">{html.escape(jname)}</div>'
                f'<div class="jmod-panel-customer">{html.escape(customer)}</div>'
                f'<div class="jmod-panel-meta">'
                f"{_status_pill(status)}"
                f'<span><span class="jmod-panel-meta-lbl">Supervisor:</span>{html.escape(sup)}</span>'
                f'<span><span class="jmod-panel-meta-lbl">Created:</span>{html.escape(created)}</span>'
                f'<span><span class="jmod-panel-meta-lbl">Updated:</span>{html.escape(updated)}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
        with hdr_r:
            st.markdown('<span class="jmod-hdr-btn" aria-hidden="true"></span>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3, gap="small")
            with c1:
                if st.button("Edit", key=f"jpan_edit_{jid}", type="primary",
                             use_container_width=True, disabled=not can_edit):
                    on_edit()
            with c2:
                if st.button("View", key=f"jpan_view_{jid}",
                             use_container_width=True):
                    on_view()
            with c3:
                if st.button("✕", key=f"jpan_close_{jid}",
                             use_container_width=True, help="Collapse panel"):
                    on_collapse()

        st.divider()

        # ── Tabs ─────────────────────────────────────────────────────────
        tab_labels = ["Overview", "Scope", "Financials", "Schedule", "Documents", "Notes", "Activity"]
        tabs = st.tabs(tab_labels)

        # Overview
        with tabs[0]:
            render_job_overview_tab(job_row, can_edit=can_edit)

        # Scope
        with tabs[1]:
            scope = _s(job_row.get("scope") or job_row.get("description"), "No scope defined.")
            notes = _s(job_row.get("notes"), "No notes.")
            st.markdown(
                f'<div class="jmod-card" style="margin-bottom:.75rem">'
                f'<div class="jmod-card-title">Scope of Work</div>'
                f'<p style="font-size:.84rem;color:#1e293b;white-space:pre-wrap;margin:0">'
                f"{html.escape(scope)}</p></div>"
                f'<div class="jmod-card">'
                f'<div class="jmod-card-title">Notes</div>'
                f'<p style="font-size:.84rem;color:#1e293b;white-space:pre-wrap;margin:0">'
                f"{html.escape(notes)}</p></div>",
                unsafe_allow_html=True,
            )

        # Financials
        with tabs[2]:
            awarded   = _money(job_row.get("awarded_amount"))
            quote_num = _s(job_row.get("Quote (estimate)") or job_row.get("quote_number"))
            linked    = _s(job_row.get("Linked estimate"))
            fin_kvs   = [
                ("Awarded Amount", awarded),
                ("Estimate / Quote #", quote_num),
                ("Linked Estimate", linked),
            ]
            fin_html = "".join(
                f'<div class="jmod-kv"><span class="jmod-kv-lbl">{html.escape(l)}</span>'
                f'<span class="jmod-kv-val">{html.escape(v)}</span></div>'
                for l, v in fin_kvs
            )
            st.markdown(
                f'<div class="jmod-card"><div class="jmod-card-title">Financial Overview</div>'
                f"{fin_html}</div>",
                unsafe_allow_html=True,
            )
            st.info("Open **View** for full labor, material, and equipment costing detail.")

        # Schedule
        with tabs[3]:
            start     = _date(job_row.get("start_date"))
            end       = _date(job_row.get("target_completion_date") or job_row.get("due_date"))
            completed = _date(job_row.get("completed_date"))
            duration  = "—"
            try:
                from datetime import datetime as _dt
                if start != "—" and end != "—":
                    d = (_dt.fromisoformat(end[:10]) - _dt.fromisoformat(start[:10])).days
                    duration = f"{d} days" if d >= 0 else "—"
            except Exception:
                pass
            sched_kvs = [
                ("Start Date",    start),
                ("End Date",      end),
                ("Completed",     completed),
                ("Duration",      duration),
            ]
            sched_html = "".join(
                f'<div class="jmod-kv"><span class="jmod-kv-lbl">{html.escape(l)}</span>'
                f'<span class="jmod-kv-val">{html.escape(v)}</span></div>'
                for l, v in sched_kvs
            )
            st.markdown(
                f'<div class="jmod-card"><div class="jmod-card-title">Schedule</div>'
                f"{sched_html}</div>",
                unsafe_allow_html=True,
            )

        # Documents
        with tabs[4]:
            st.caption("Reference attachments and documents are available in the full detail view.")
            if st.button("Open Full View →", key=f"jpan_docs_{jid}"):
                on_view()

        # Notes
        with tabs[5]:
            notes = _s(job_row.get("notes"), "No notes recorded for this job.")
            st.markdown(
                f'<div class="jmod-card"><div class="jmod-card-title">Job Notes</div>'
                f'<p style="font-size:.84rem;color:#1e293b;white-space:pre-wrap;margin:0">'
                f"{html.escape(notes)}</p></div>",
                unsafe_allow_html=True,
            )

        # Activity
        with tabs[6]:
            st.markdown('<div class="jmod-card-title">Activity Log</div>', unsafe_allow_html=True)
            render_activity_feed(job_row)


# ─────────────────────────────────────────────────────────────────────────────
# Row renderer
# ─────────────────────────────────────────────────────────────────────────────

def render_job_row(
    *,
    row:         Any,
    full_row:    dict[str, Any],
    job_num_col: str,
    can_edit:    bool,
    is_selected: bool,
    on_select:   Any,
    on_view:     Any,
    on_delete:   Any,
) -> None:
    jid = str(row.get("id") or full_row.get("id") or "").strip()

    # Marker drives CSS :has() selectors
    marker = "jmod-row-selected" if is_selected else "jmod-row"
    st.markdown(
        f'<span class="{marker}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    # Columns: chev | job# | name | customer | est# | supervisor | status | start | end | actions
    weights = [0.28, 0.75, 2.0, 1.35, 0.85, 1.0, 0.85, 0.8, 0.8, 0.75]
    cols = st.columns(weights, gap="small")

    jnum       = _s(row.get(job_num_col) or full_row.get(job_num_col) or full_row.get("job_number"))
    jname      = _s(row.get("job_name") or full_row.get("job_name"), "Untitled")
    customer   = _s(row.get("customer_name") or full_row.get("customer_name"))
    est_num    = _s(row.get("Quote (estimate)") or full_row.get("Quote (estimate)") or full_row.get("quote_number"))
    supervisor = _s(full_row.get("supervisor") or full_row.get("project_manager"))
    status     = row.get("status") or full_row.get("status")
    start      = _date(full_row.get("start_date"))
    end        = _date(full_row.get("target_completion_date") or full_row.get("due_date"))

    # ── Chevron ──────────────────────────────────────────────────────────
    with cols[0]:
        chev_cls = "jmod-chev-on" if is_selected else "jmod-chev"
        st.markdown(f'<span class="{chev_cls}" aria-hidden="true"></span>', unsafe_allow_html=True)
        if st.button("▾" if is_selected else "▸", key=f"jrow_chev_{jid}",
                     use_container_width=True, help="Expand / collapse details"):
            on_select()

    # ── Job # (blue clickable) ────────────────────────────────────────────
    with cols[1]:
        bold = "jmod-cell-num jmod-cell-bold" if is_selected else "jmod-cell-num"
        st.markdown(
            f'<span class="{bold}" title="{html.escape(jnum, quote=True)}">{html.escape(jnum)}</span>',
            unsafe_allow_html=True,
        )

    # ── Project name ──────────────────────────────────────────────────────
    with cols[2]:
        name_cls = "jmod-cell jmod-cell-bold" if is_selected else "jmod-cell"
        st.markdown(
            f'<span class="{name_cls}" title="{html.escape(jname, quote=True)}">{html.escape(jname)}</span>',
            unsafe_allow_html=True,
        )

    # ── Customer ──────────────────────────────────────────────────────────
    with cols[3]:
        st.markdown(
            f'<span class="jmod-cell jmod-cell-muted" title="{html.escape(customer, quote=True)}">{html.escape(customer)}</span>',
            unsafe_allow_html=True,
        )

    # ── Estimate # ────────────────────────────────────────────────────────
    with cols[4]:
        st.markdown(
            f'<span class="jmod-cell jmod-cell-muted">{html.escape(est_num)}</span>',
            unsafe_allow_html=True,
        )

    # ── Supervisor ────────────────────────────────────────────────────────
    with cols[5]:
        st.markdown(
            f'<span class="jmod-cell jmod-cell-muted" title="{html.escape(supervisor, quote=True)}">{html.escape(supervisor)}</span>',
            unsafe_allow_html=True,
        )

    # ── Status pill ───────────────────────────────────────────────────────
    with cols[6]:
        st.markdown(_status_pill(status, small=True), unsafe_allow_html=True)

    # ── Start date ────────────────────────────────────────────────────────
    with cols[7]:
        st.markdown(f'<span class="jmod-cell jmod-cell-muted">{html.escape(start)}</span>', unsafe_allow_html=True)

    # ── End date ──────────────────────────────────────────────────────────
    with cols[8]:
        st.markdown(f'<span class="jmod-cell jmod-cell-muted">{html.escape(end)}</span>', unsafe_allow_html=True)

    # ── Actions ───────────────────────────────────────────────────────────
    with cols[9]:
        st.markdown('<span class="jmod-act" aria-hidden="true"></span>', unsafe_allow_html=True)
        a1, a2 = st.columns(2, gap="small")
        with a1:
            if st.button("👁", key=f"jrow_view_{jid}", use_container_width=True, help="View full job details"):
                on_view()
        with a2:
            if st.button("🗑", key=f"jrow_del_{jid}", use_container_width=True,
                         disabled=not can_edit,
                         help="Delete job" if can_edit else "Admin/manager only"):
                on_delete()


# ─────────────────────────────────────────────────────────────────────────────
# Main table renderer
# ─────────────────────────────────────────────────────────────────────────────

def render_jobs_table(
    *,
    df_display:          Any,
    job_num_col:         str,
    can_edit:            bool,
    jobs:                list[dict[str, Any]],
    admin_read:          bool = False,
    customer_name_by_id: dict[str, str] | None = None,
) -> None:
    """Render the modern jobs table with inline expand/collapse detail panels.

    Selected row stored in ``st.session_state.selected_job_id``.
    Replaces the legacy checkbox + st.columns table.
    """
    inject_modern_jobs_css()

    jobs_by_id: dict[str, dict[str, Any]] = {
        str(j.get("id") or ""): j for j in jobs if j.get("id")
    }
    selected_jid = str(st.session_state.get("selected_job_id") or "").strip()

    with st.container(border=True):
        st.markdown('<span class="jmod-table-host" aria-hidden="true"></span>', unsafe_allow_html=True)

        # HTML table header
        st.markdown(
            '<div class="jmod-thead">'
            '<span class="jmod-th" style="grid-column:1"></span>'
            '<span class="jmod-th">Job #</span>'
            '<span class="jmod-th">Project / Description</span>'
            '<span class="jmod-th">Customer</span>'
            '<span class="jmod-th">Estimate #</span>'
            '<span class="jmod-th">Supervisor</span>'
            '<span class="jmod-th">Status</span>'
            '<span class="jmod-th">Start Date</span>'
            '<span class="jmod-th">End Date</span>'
            '<span class="jmod-th" style="text-align:right">Actions</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Rows
        for _, row in df_display.iterrows():
            jid = str(row.get("id") or "").strip()
            if not jid:
                continue
            full_row = jobs_by_id.get(jid, dict(row))
            is_selected = jid == selected_jid

            def _on_select(j=jid):
                st.session_state["selected_job_id"] = None if st.session_state.get("selected_job_id") == j else j
                st.rerun()

            def _on_view(j=jid):
                st.session_state["job_view_mode"]  = "view"
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
                row=row, full_row=full_row, job_num_col=job_num_col,
                can_edit=can_edit, is_selected=is_selected,
                on_select=_on_select, on_view=_on_view, on_delete=_on_delete,
            )

            # Inline detail panel below selected row
            if is_selected:
                def _detail_view(j=jid):
                    st.session_state["job_view_mode"]  = "view"
                    st.session_state["selected_job_id"] = j
                    st.session_state.pop("job_mode", None)
                    st.session_state.pop("job_edit_id", None)
                    st.rerun()

                def _detail_edit(j=jid):
                    st.session_state["job_view_mode"] = "edit"
                    st.session_state["selected_job_id"] = j
                    st.session_state["job_mode"]    = "edit"
                    st.session_state["job_edit_id"] = j
                    st.session_state.pop("job_number_manual_input", None)
                    st.rerun()

                def _detail_collapse():
                    st.session_state["selected_job_id"] = None
                    st.rerun()

                render_job_detail_panel(
                    job_row=full_row, can_edit=can_edit, admin_read=admin_read,
                    on_view=_detail_view, on_edit=_detail_edit, on_collapse=_detail_collapse,
                )
