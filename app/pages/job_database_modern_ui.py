"""Modern Job Database UI — pixel-accurate match to reference screenshot.

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

_CSS_KEY = "jdb_modern_v8"

# ─────────────────────────────────────────────────────────────────────────────
# Status pill colours  (text, background)
# ─────────────────────────────────────────────────────────────────────────────
_PILL: dict[str, tuple[str, str]] = {
    "active":                    ("#166534", "#dcfce7"),
    "complete":                  ("#166534", "#dcfce7"),
    "completed":                 ("#166534", "#dcfce7"),
    "closed":                    ("#166534", "#dcfce7"),
    "approved":                  ("#166534", "#dcfce7"),
    "in progress":               ("#92400e", "#fef3c7"),
    "awarded":                   ("#92400e", "#fef3c7"),
    "on hold":                   ("#92400e", "#fef3c7"),
    "scheduled":                 ("#1e40af", "#dbeafe"),
    "blocked":                   ("#991b1b", "#fee2e2"),
    "cancelled":                 ("#991b1b", "#fee2e2"),
    "draft":                     ("#374151", "#f3f4f6"),
    "not started":               ("#374151", "#f3f4f6"),
    "quoted":                    ("#374151", "#f3f4f6"),
    "submitted":                 ("#374151", "#f3f4f6"),
    "duplicate":                 ("#374151", "#f3f4f6"),
    "waiting on customer":       ("#0e7490", "#e0f2fe"),
    "electrical":                ("#5b21b6", "#ede9fe"),
    "electrical / other trade":  ("#5b21b6", "#ede9fe"),
}
_PILL_DEFAULT = ("#374151", "#f3f4f6")


def _s(v: Any, fb: str = "—") -> str:
    val = str(v or "").strip()
    return val if val and val.lower() not in ("none", "nan", "") else fb


def _dt(v: Any) -> str:
    raw = str(v or "").strip()
    if not raw or raw.lower() in ("none", "nan", ""):
        return "—"
    # Parse "YYYY-MM-DD ..." → "Mon DD, YYYY" display
    try:
        from datetime import datetime as _datetime
        d = _datetime.fromisoformat(raw[:10])
        return d.strftime("%b %-d, %Y")
    except Exception:
        return raw[:10] if len(raw) > 10 else raw


def _pill(status: Any, *, sm: bool = False) -> str:
    label = _s(status)
    fg, bg = _PILL.get(label.lower(), _PILL_DEFAULT)
    fs   = "0.69rem" if sm else "0.72rem"
    pad  = "0.18rem 0.5rem" if sm else "0.25rem 0.6rem"
    return (
        f'<span style="display:inline-flex;align-items:center;border-radius:999px;'
        f'font-size:{fs};font-weight:700;line-height:1;padding:{pad};'
        f'white-space:nowrap;color:{fg};background:{bg};">'
        f"{html.escape(label)}</span>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CSS — injected once per session
# ─────────────────────────────────────────────────────────────────────────────

def inject_modern_jobs_css() -> None:
    if st.session_state.get(_CSS_KEY):
        return
    st.session_state[_CSS_KEY] = True
    st.markdown(r"""
<style>
/* ═══════════════════════════════════════════════════════
   RESET HELPERS
═══════════════════════════════════════════════════════ */
.jdb-hide { display: none !important; }

/* ═══════════════════════════════════════════════════════
   TABLE HOST CARD
═══════════════════════════════════════════════════════ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host) {
    background: #ffffff !important;
    border: 1px solid #e5eaf2 !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 4px rgba(15,23,42,0.06) !important;
    padding: 0 !important;
    overflow: hidden !important;
}

/* ── HTML thead ─────────────────────────────────────── */
.jdb-thead {
    display: flex; align-items: center;
    padding: 0 1rem; height: 2.5rem;
    background: #f8fafc;
    border-bottom: 1px solid #e5eaf2;
    font-size: 0.68rem; font-weight: 700;
    color: #6b7280; letter-spacing: 0.07em;
    text-transform: uppercase; user-select: none;
}
.jdb-th {
    overflow: hidden; white-space: nowrap;
    text-overflow: ellipsis; padding-right: 0.5rem;
}
/* Column widths mirror Streamlit column weights [0.7,2,1.4,.85,1.1,.85,.8,.8,.8] */
.jdb-th-num  { flex: 0.70; }
.jdb-th-name { flex: 2.00; }
.jdb-th-cust { flex: 1.40; }
.jdb-th-est  { flex: 0.85; }
.jdb-th-sup  { flex: 1.10; }
.jdb-th-stat { flex: 0.85; }
.jdb-th-sd   { flex: 0.80; }
.jdb-th-ed   { flex: 0.80; }
.jdb-th-act  { flex: 0.80; text-align: right; padding-right: 0; }

/* ── Row wrapper ────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(> .jdb-row) {
    position: relative !important;
    border-bottom: 1px solid #f1f5f9 !important;
    transition: background 0.1s ease !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(> .jdb-row):last-child {
    border-bottom: none !important;
}
/* hover */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(> .jdb-row):hover {
    background: #f8fafc !important;
}
/* selected */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(> .jdb-row-sel) {
    background: #eff6ff !important;
    box-shadow: inset 3px 0 0 #2563eb !important;
}

/* ── Row inner padding & column alignment ─────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(> .jdb-row) {
    padding: 0 1rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(> .jdb-row)
    [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 0.5rem !important;
    min-height: 3rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(> .jdb-row)
    [data-testid="stElementContainer"] {
    margin: 0 !important; padding: 0 !important;
}

/* ── Force dark text ──────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .stMarkdown, 
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .stMarkdown p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .stMarkdown span {
    color: #111827 !important;
}

/* ── Cell text styles ─────────────────────────────────── */
.jdb-cell {
    font-size: 0.82rem; color: #374151;
    white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; display: block; line-height: 1.4;
}
.jdb-cell-muted { color: #6b7280 !important; font-size: 0.78rem !important; }
.jdb-cell-wrap  { white-space: normal !important; line-height: 1.35 !important; }

/* ── Job-number as blue text button ───────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .jdb-numcol .stButton > button {
    background: transparent !important;
    border: none !important; box-shadow: none !important;
    color: #2563eb !important;
    font-size: 0.82rem !important; font-weight: 700 !important;
    padding: 0 !important;
    min-height: unset !important; height: auto !important;
    line-height: 1.4 !important;
    display: inline !important;
    text-align: left !important; justify-content: flex-start !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .jdb-numcol .stButton > button:hover {
    color: #1d4ed8 !important; background: transparent !important;
    text-decoration: underline !important;
}
/* Bold when selected */
div[data-testid="stVerticalBlock"]:has(> .jdb-row-sel)
    .jdb-numcol .stButton > button {
    font-weight: 800 !important; color: #1d4ed8 !important;
}

/* ── Action icon buttons ──────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .jdb-actcol .stButton > button {
    min-width: 1.9rem !important; max-width: 1.9rem !important;
    min-height: 1.9rem !important; height: 1.9rem !important;
    padding: 0 !important; font-size: 0.85rem !important;
    border: 1px solid #e5eaf2 !important; border-radius: 6px !important;
    background: #ffffff !important; color: #374151 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    line-height: 1 !important; display: flex !important;
    align-items: center !important; justify-content: center !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .jdb-actcol .stButton > button:hover {
    background: #f3f4f6 !important; border-color: #d1d5db !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .jdb-actcol .stButton > button:disabled { opacity: 0.35 !important; }

/* ═══════════════════════════════════════════════════════
   DETAIL PANEL
═══════════════════════════════════════════════════════ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host) {
    background: #ffffff !important;
    border: 1.5px solid #2563eb !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 20px rgba(37,99,235,0.10) !important;
    padding: 1.25rem 1.5rem 1rem !important;
    margin: 0.4rem 0 0.75rem !important;
}

/* panel header text */
.jdb-ph-num {
    font-size: 1rem; font-weight: 800; color: #111827;
    margin: 0 0 0.15rem; line-height: 1.2;
}
.jdb-ph-title {
    font-size: 1.25rem; font-weight: 800; color: #111827;
    line-height: 1.2; margin: 0 0 0.2rem; word-break: break-word;
}
.jdb-ph-cust { font-size: 0.875rem; color: #6b7280; margin: 0; }
.jdb-ph-meta {
    display: flex; flex-wrap: wrap; gap: 0.3rem 1.2rem;
    font-size: 0.78rem; color: #6b7280;
    align-items: center; margin-top: 0.6rem;
}
.jdb-ph-meta-lbl { font-weight: 600; color: #374151; margin-right: 0.2rem; }

/* panel header buttons */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    .jdb-ph-btns .stButton > button {
    min-height: 2rem !important; height: 2rem !important;
    padding: 0 0.75rem !important; font-size: 0.8rem !important;
    font-weight: 600 !important; border-radius: 8px !important;
    line-height: 1 !important; white-space: nowrap !important;
}

/* ── Tabs ─────────────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    [data-testid="stTabs"] [role="tablist"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important; padding: 0 !important;
    border-radius: 0 !important; box-shadow: none !important;
    gap: 0 !important; border-bottom: 1.5px solid #e5eaf2 !important;
    margin-bottom: 1.1rem !important; overflow-x: auto !important;
    scrollbar-width: thin;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    [data-testid="stTabs"] [role="tab"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    [data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important; border: none !important;
    border-bottom: 2.5px solid transparent !important;
    border-radius: 0 !important; box-shadow: none !important;
    padding: 0.55rem 1rem !important; margin-bottom: -1.5px !important;
    font-size: 0.82rem !important; font-weight: 500 !important;
    color: #6b7280 !important; white-space: nowrap !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    [data-testid="stTabs"] [role="tab"][aria-selected="true"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    border-bottom-color: #2563eb !important;
    color: #2563eb !important; font-weight: 700 !important;
    background: transparent !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    [data-testid="stTabs"] [role="tab"] p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    [data-testid="stTabs"] [data-baseweb="tab"] p {
    color: inherit !important; font-weight: inherit !important; margin: 0 !important;
}

/* ── Info cards ───────────────────────────────────────── */
.jdb-card {
    background: #ffffff; border: 1px solid #e5eaf2;
    border-radius: 10px; padding: 1rem 1.1rem;
}
.jdb-card-title {
    font-size: 0.75rem; font-weight: 700; color: #374151;
    letter-spacing: 0; margin: 0 0 0.75rem;
}
.jdb-kv {
    display: flex; gap: 0; align-items: baseline;
    margin-bottom: 0.45rem; font-size: 0.83rem;
}
.jdb-kv-lbl {
    color: #6b7280; font-size: 0.78rem; font-weight: 400;
    min-width: 100px; flex-shrink: 0;
}
.jdb-kv-val { color: #111827; font-weight: 500; word-break: break-word; }

/* ── Summary — flat 4-column grid ────────────────────── */
.jdb-sum-wrap {
    display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 0;
    border-top: 1px solid #f1f5f9; margin-top: 0.65rem; padding-top: 0.65rem;
}
.jdb-sum-col { padding: 0 0.75rem 0 0; }
.jdb-sum-col:first-child { padding-left: 0; }
.jdb-sum-lbl {
    font-size: 0.72rem; color: #6b7280; font-weight: 400; margin-bottom: 0.2rem;
}
.jdb-sum-val {
    font-size: 0.92rem; font-weight: 700; color: #111827;
    font-variant-numeric: tabular-nums;
}

/* ── Activity feed ────────────────────────────────────── */
.jdb-act-row {
    display: flex; gap: 0.55rem; align-items: flex-start;
    padding: 0.32rem 0; border-bottom: 1px solid #f1f5f9; font-size: 0.78rem;
}
.jdb-act-row:last-child { border-bottom: none; }
.jdb-act-dot {
    width: 7px; height: 7px; border-radius: 50%;
    flex-shrink: 0; margin-top: 0.33rem;
}
.jdb-act-ts  { color: #9ca3af; font-size: 0.7rem; }
.jdb-act-txt { color: #374151; line-height: 1.4; }

/* ── Panel inner text fix ─────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    .stMarkdown,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    .stMarkdown p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    .stMarkdown span { color: #111827 !important; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    [data-testid="stCaptionContainer"] p { color: #6b7280 !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Leaf components
# ─────────────────────────────────────────────────────────────────────────────

def render_activity_feed(job_row: dict[str, Any]) -> None:
    created = _dt(job_row.get("created_at"))
    updated = _dt(job_row.get("updated_at"))
    status  = _s(job_row.get("status"))
    jname   = _s(job_row.get("job_name"), "this job")
    items: list[tuple[str, str, str]] = []
    if updated and updated != "—" and updated != created:
        items.append((updated, "#2563eb", "Job record updated"))
    if status and status != "—":
        items.append((created, "#16a34a", f"Status set to {status}"))
    items.append((created, "#9ca3af", f"Job created — {jname}"))
    if not items:
        st.markdown('<p style="font-size:.8rem;color:#9ca3af;margin:0">No recent activity.</p>',
                    unsafe_allow_html=True)
        return
    lines = [
        f'<div class="jdb-act-row">'
        f'<span class="jdb-act-dot" style="background:{c}"></span>'
        f'<div><span class="jdb-act-txt">{html.escape(t)}</span>'
        f'<br><span class="jdb-act-ts">{html.escape(ts)}</span></div></div>'
        for ts, c, t in items[:6]
    ]
    st.markdown("\n".join(lines), unsafe_allow_html=True)


def render_job_summary_cards(job_row: dict[str, Any]) -> None:
    """Flat 4-column summary row: Labor · Material · Equipment · Total."""
    awarded = _s(job_row.get("awarded_amount"))
    try:
        if awarded != "—":
            awarded = f"${float(awarded):,.0f}"
    except Exception:
        awarded = "—"
    cols_data = [
        ("Labor Total",     "—"),
        ("Material Total",  "—"),
        ("Equipment Total", "—"),
        ("Total",           awarded),
    ]
    items_html = "".join(
        f'<div class="jdb-sum-col">'
        f'<div class="jdb-sum-lbl">{html.escape(l)}</div>'
        f'<div class="jdb-sum-val">{html.escape(v)}</div></div>'
        for l, v in cols_data
    )
    st.markdown(f'<div class="jdb-sum-wrap">{items_html}</div>', unsafe_allow_html=True)


def render_job_overview_tab(job_row: dict[str, Any], can_edit: bool = False) -> None:  # noqa: ARG001
    jnum   = _s(job_row.get("job_number") or job_row.get("job_id") or job_row.get("id"))
    cust   = _s(job_row.get("customer_name"))
    sup    = _s(job_row.get("supervisor") or job_row.get("project_manager"))
    status = _s(job_row.get("status"))
    est    = _s(job_row.get("Quote (estimate)") or job_row.get("quote_number"))
    desc   = _s(job_row.get("description") or job_row.get("job_name") or job_row.get("scope"),
                "No description provided.")
    start  = _dt(job_row.get("start_date"))
    end    = _dt(job_row.get("target_completion_date") or job_row.get("due_date"))
    dur    = "—"
    try:
        from datetime import datetime as _D
        if start != "—" and end != "—":
            raw_s = str(job_row.get("start_date") or "")[:10]
            raw_e = str(job_row.get("target_completion_date") or job_row.get("due_date") or "")[:10]
            d = (_D.fromisoformat(raw_e) - _D.fromisoformat(raw_s)).days
            dur = f"{d} days" if d >= 0 else "—"
    except Exception:
        pass

    col_l, col_r = st.columns([1, 1], gap="medium")

    # ── Job Information ─────────────────────────────────────────────────────
    with col_l:
        kvrows = [
            ("Job Number",  jnum),
            ("Customer",    cust),
            ("Supervisor",  sup),
            ("Status",      None),   # rendered as pill
            ("Estimate #",  est),
            ("Description", desc),
        ]
        kv_html = ""
        for lbl, val in kvrows:
            if lbl == "Status":
                v_part = _pill(status)
            elif lbl == "Description":
                v_part = (f'<span class="jdb-kv-val" style="white-space:pre-wrap">'
                          f'{html.escape(val)}</span>')
            else:
                v_part = f'<span class="jdb-kv-val">{html.escape(_s(val))}</span>'
            kv_html += (
                f'<div class="jdb-kv">'
                f'<span class="jdb-kv-lbl">{html.escape(lbl)}</span>'
                f"{v_part}</div>"
            )
        st.markdown(
            f'<div class="jdb-card"><div class="jdb-card-title">Job Information</div>'
            f"{kv_html}</div>",
            unsafe_allow_html=True,
        )

    # ── Schedule ─────────────────────────────────────────────────────────────
    with col_r:
        sched = [("Start Date", start), ("End Date", end), ("Duration", dur)]
        s_html = "".join(
            f'<div class="jdb-kv"><span class="jdb-kv-lbl">{html.escape(l)}</span>'
            f'<span class="jdb-kv-val">{html.escape(v)}</span></div>'
            for l, v in sched
        )
        st.markdown(
            f'<div class="jdb-card"><div class="jdb-card-title">Schedule</div>'
            f"{s_html}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:.65rem'></div>", unsafe_allow_html=True)

    # ── Summary + Recent Activity ─────────────────────────────────────────
    col_s, col_a = st.columns([1, 1], gap="medium")
    with col_s:
        st.markdown('<div class="jdb-card"><div class="jdb-card-title">Summary</div>',
                    unsafe_allow_html=True)
        render_job_summary_cards(job_row)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_a:
        st.markdown('<div class="jdb-card"><div class="jdb-card-title">Recent Activity</div>',
                    unsafe_allow_html=True)
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
        st.markdown('<span class="jdb-panel-host jdb-hide"></span>', unsafe_allow_html=True)

        jid     = str(job_row.get("id") or "").strip()
        jnum    = _s(job_row.get("job_number") or job_row.get("job_id") or jid[:8])
        jname   = _s(job_row.get("job_name"), "Untitled Job")
        cust    = _s(job_row.get("customer_name"))
        status  = _s(job_row.get("status"))
        sup     = _s(job_row.get("supervisor") or job_row.get("project_manager"))
        created = _dt(job_row.get("created_at"))
        updated = _dt(job_row.get("updated_at"))

        # ── Header ────────────────────────────────────────────────────────
        hdr_info, hdr_meta, hdr_btns = st.columns([2.2, 3.0, 1.8], gap="small")

        with hdr_info:
            st.markdown(
                f'<div class="jdb-ph-num">{html.escape(jnum)}</div>'
                f'<div class="jdb-ph-title">{html.escape(jname)}</div>'
                f'<div class="jdb-ph-cust">{html.escape(cust)}</div>',
                unsafe_allow_html=True,
            )

        with hdr_meta:
            meta_html = (
                f'<div class="jdb-ph-meta">'
                f"{_pill(status)}"
                f'<span><span class="jdb-ph-meta-lbl">Supervisor</span>{html.escape(sup)}</span>'
                f'<span><span class="jdb-ph-meta-lbl">Created</span>{html.escape(created)}</span>'
                f'<span><span class="jdb-ph-meta-lbl">Last Updated</span>{html.escape(updated)}</span>'
                f"</div>"
            )
            st.markdown(meta_html, unsafe_allow_html=True)

        with hdr_btns:
            st.markdown('<span class="jdb-ph-btns jdb-hide"></span>', unsafe_allow_html=True)
            b1, b2, b3 = st.columns([1, 1.4, 0.6], gap="small")
            with b1:
                if st.button("✏ Edit", key=f"jpan_edit_{jid}",
                             use_container_width=True, disabled=not can_edit):
                    on_edit()
            with b2:
                if st.button("📄 View / Details", key=f"jpan_view_{jid}",
                             type="primary", use_container_width=True):
                    on_view()
            with b3:
                if st.button("∧", key=f"jpan_close_{jid}",
                             use_container_width=True, help="Collapse panel"):
                    on_collapse()

        st.divider()

        # ── Tabs ──────────────────────────────────────────────────────────
        t_overview, t_scope, t_fin, t_sched, t_docs, t_notes, t_act = st.tabs([
            "⊞ Overview", "≡ Scope", "$ Financials",
            "📅 Schedule", "📄 Documents", "📝 Notes", "⚡ Activity",
        ])

        with t_overview:
            render_job_overview_tab(job_row, can_edit=can_edit)

        with t_scope:
            scope = _s(job_row.get("scope") or job_row.get("description"), "No scope defined.")
            notes = _s(job_row.get("notes"), "No notes.")
            st.markdown(
                f'<div class="jdb-card" style="margin-bottom:.75rem">'
                f'<div class="jdb-card-title">Scope of Work</div>'
                f'<p style="font-size:.84rem;color:#111827;white-space:pre-wrap;margin:0">'
                f"{html.escape(scope)}</p></div>"
                f'<div class="jdb-card">'
                f'<div class="jdb-card-title">Notes</div>'
                f'<p style="font-size:.84rem;color:#111827;white-space:pre-wrap;margin:0">'
                f"{html.escape(notes)}</p></div>",
                unsafe_allow_html=True,
            )

        with t_fin:
            awarded = _s(job_row.get("awarded_amount"))
            try:
                if awarded != "—":
                    awarded = f"${float(awarded):,.2f}"
            except Exception:
                pass
            fin_kvs = [
                ("Awarded Amount", awarded),
                ("Estimate / Quote #", _s(job_row.get("Quote (estimate)") or job_row.get("quote_number"))),
                ("Linked Estimate",   _s(job_row.get("Linked estimate"))),
            ]
            f_html = "".join(
                f'<div class="jdb-kv"><span class="jdb-kv-lbl">{html.escape(l)}</span>'
                f'<span class="jdb-kv-val">{html.escape(v)}</span></div>'
                for l, v in fin_kvs
            )
            st.markdown(
                f'<div class="jdb-card"><div class="jdb-card-title">Financial Overview</div>'
                f"{f_html}</div>",
                unsafe_allow_html=True,
            )
            st.caption("Open **View / Details** for full labor, materials, and equipment costing.")

        with t_sched:
            raw_s = str(job_row.get("start_date") or "")
            raw_e = str(job_row.get("target_completion_date") or job_row.get("due_date") or "")
            start = _dt(raw_s); end = _dt(raw_e)
            comp  = _dt(job_row.get("completed_date"))
            dur   = "—"
            try:
                from datetime import datetime as _D
                if start != "—" and end != "—":
                    d = (_D.fromisoformat(raw_e[:10]) - _D.fromisoformat(raw_s[:10])).days
                    dur = f"{d} days" if d >= 0 else "—"
            except Exception:
                pass
            s_html = "".join(
                f'<div class="jdb-kv"><span class="jdb-kv-lbl">{html.escape(l)}</span>'
                f'<span class="jdb-kv-val">{html.escape(v)}</span></div>'
                for l, v in [("Start Date", start), ("End Date", end),
                              ("Completed", comp), ("Duration", dur)]
            )
            st.markdown(
                f'<div class="jdb-card"><div class="jdb-card-title">Schedule</div>'
                f"{s_html}</div>",
                unsafe_allow_html=True,
            )

        with t_docs:
            st.caption("Reference attachments and documents are available in the full detail view.")
            if st.button("Open Full View →", key=f"jpan_docs_{jid}"):
                on_view()

        with t_notes:
            notes = _s(job_row.get("notes"), "No notes recorded for this job.")
            st.markdown(
                f'<div class="jdb-card"><div class="jdb-card-title">Job Notes</div>'
                f'<p style="font-size:.84rem;color:#111827;white-space:pre-wrap;margin:0">'
                f"{html.escape(notes)}</p></div>",
                unsafe_allow_html=True,
            )

        with t_act:
            st.markdown('<div style="font-size:.75rem;font-weight:700;color:#374151;'
                        'margin-bottom:.65rem">Activity Log</div>', unsafe_allow_html=True)
            render_activity_feed(job_row)


# ─────────────────────────────────────────────────────────────────────────────
# Row
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

    # CSS class marker — drives :has() selectors
    st.markdown(
        f'<span class="{"jdb-row-sel" if is_selected else "jdb-row"} jdb-hide"></span>',
        unsafe_allow_html=True,
    )

    # Columns: job# | name | customer | est# | supervisor | status | start | end | actions
    weights = [0.70, 2.0, 1.40, 0.85, 1.10, 0.85, 0.80, 0.80, 0.80]
    cols = st.columns(weights, gap="small")

    jnum = _s(row.get(job_num_col) or full_row.get(job_num_col) or full_row.get("job_number"))
    name = _s(row.get("job_name") or full_row.get("job_name"), "Untitled")
    cust = _s(row.get("customer_name") or full_row.get("customer_name"))
    est  = _s(row.get("Quote (estimate)") or full_row.get("Quote (estimate)") or full_row.get("quote_number"))
    sup  = _s(full_row.get("supervisor") or full_row.get("project_manager"))
    stat = row.get("status") or full_row.get("status")
    sd   = _dt(full_row.get("start_date"))
    ed   = _dt(full_row.get("target_completion_date") or full_row.get("due_date"))

    # Job number — blue text button triggers expand
    with cols[0]:
        st.markdown('<span class="jdb-numcol jdb-hide"></span>', unsafe_allow_html=True)
        if st.button(jnum, key=f"jrow_num_{jid}", use_container_width=True, help="Expand details"):
            on_select()

    # Project / description
    with cols[1]:
        st.markdown(
            f'<span class="jdb-cell jdb-cell-wrap" title="{html.escape(name, quote=True)}">'
            f"{html.escape(name)}</span>",
            unsafe_allow_html=True,
        )

    # Customer
    with cols[2]:
        st.markdown(
            f'<span class="jdb-cell jdb-cell-muted" title="{html.escape(cust, quote=True)}">'
            f"{html.escape(cust)}</span>",
            unsafe_allow_html=True,
        )

    # Estimate #
    with cols[3]:
        st.markdown(
            f'<span class="jdb-cell jdb-cell-muted">{html.escape(est)}</span>',
            unsafe_allow_html=True,
        )

    # Supervisor
    with cols[4]:
        st.markdown(
            f'<span class="jdb-cell jdb-cell-muted" title="{html.escape(sup, quote=True)}">'
            f"{html.escape(sup)}</span>",
            unsafe_allow_html=True,
        )

    # Status pill
    with cols[5]:
        st.markdown(_pill(stat, sm=True), unsafe_allow_html=True)

    # Start date
    with cols[6]:
        st.markdown(f'<span class="jdb-cell jdb-cell-muted">{html.escape(sd)}</span>',
                    unsafe_allow_html=True)

    # End date
    with cols[7]:
        st.markdown(f'<span class="jdb-cell jdb-cell-muted">{html.escape(ed)}</span>',
                    unsafe_allow_html=True)

    # Actions: two bordered square icon buttons
    with cols[8]:
        st.markdown('<span class="jdb-actcol jdb-hide"></span>', unsafe_allow_html=True)
        a1, a2 = st.columns(2, gap="small")
        with a1:
            if st.button("👁", key=f"jrow_view_{jid}", use_container_width=True, help="View job"):
                on_view()
        with a2:
            if st.button("🗑", key=f"jrow_del_{jid}", use_container_width=True,
                         disabled=not can_edit,
                         help="Delete job" if can_edit else "Admin/manager only"):
                on_delete()


# ─────────────────────────────────────────────────────────────────────────────
# Table
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
    """Full replacement for the legacy checkbox table in job_database.py."""
    inject_modern_jobs_css()

    by_id: dict[str, dict[str, Any]] = {
        str(j.get("id") or ""): j for j in jobs if j.get("id")
    }
    sel = str(st.session_state.get("selected_job_id") or "").strip()

    with st.container(border=True):
        st.markdown('<span class="jdb-tbl-host jdb-hide"></span>', unsafe_allow_html=True)

        # HTML header row (mirrors Streamlit column weights)
        st.markdown(
            '<div class="jdb-thead">'
            '<span class="jdb-th jdb-th-num">Job #</span>'
            '<span class="jdb-th jdb-th-name">Project / Description</span>'
            '<span class="jdb-th jdb-th-cust">Customer</span>'
            '<span class="jdb-th jdb-th-est">Estimate #</span>'
            '<span class="jdb-th jdb-th-sup">Supervisor</span>'
            '<span class="jdb-th jdb-th-stat">Status</span>'
            '<span class="jdb-th jdb-th-sd">Start Date</span>'
            '<span class="jdb-th jdb-th-ed">End Date</span>'
            '<span class="jdb-th jdb-th-act">Actions</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        for _, row in df_display.iterrows():
            jid = str(row.get("id") or "").strip()
            if not jid:
                continue
            full_row    = by_id.get(jid, dict(row))
            is_selected = jid == sel

            def _toggle(j=jid):
                st.session_state["selected_job_id"] = (
                    None if st.session_state.get("selected_job_id") == j else j
                )
                st.rerun()

            def _open_view(j=jid):
                st.session_state["job_view_mode"]   = "view"
                st.session_state["selected_job_id"] = j
                st.session_state.pop("job_mode",    None)
                st.session_state.pop("job_edit_id", None)
                st.rerun()

            def _trigger_delete(j=jid):
                pend = st.session_state.get(IPS_PENDING_DELETE)
                if not isinstance(pend, dict):
                    pend = {}
                    st.session_state[IPS_PENDING_DELETE] = pend
                pend[TABLE_KEY_JOBS] = [j]
                st.rerun()

            render_job_row(
                row=row, full_row=full_row, job_num_col=job_num_col,
                can_edit=can_edit, is_selected=is_selected,
                on_select=_toggle, on_view=_open_view, on_delete=_trigger_delete,
            )

            if is_selected:
                def _panel_view(j=jid):
                    st.session_state["job_view_mode"]   = "view"
                    st.session_state["selected_job_id"] = j
                    st.session_state.pop("job_mode",    None)
                    st.session_state.pop("job_edit_id", None)
                    st.rerun()

                def _panel_edit(j=jid):
                    st.session_state["job_view_mode"] = "edit"
                    st.session_state["selected_job_id"] = j
                    st.session_state["job_mode"]     = "edit"
                    st.session_state["job_edit_id"]  = j
                    st.session_state.pop("job_number_manual_input", None)
                    st.rerun()

                def _panel_collapse():
                    st.session_state["selected_job_id"] = None
                    st.rerun()

                render_job_detail_panel(
                    job_row=full_row, can_edit=can_edit, admin_read=admin_read,
                    on_view=_panel_view, on_edit=_panel_edit, on_collapse=_panel_collapse,
                )
