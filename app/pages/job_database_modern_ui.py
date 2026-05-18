"""Modern Job Database UI — pixel-accurate match to reference screenshot.

Architecture note
─────────────────
Each table row is wrapped in ``with st.container():`` so Streamlit creates a
dedicated ``stVerticalBlock`` per row.  The CSS ``div:has(.jdb-row)`` selector
then targets ONLY that per-row block, not the outer table card.

Public API
──────────
inject_job_database_root_canvas()
inject_modern_jobs_css()
render_jobs_table(df_display, job_num_col, can_edit, jobs, admin_read, customer_name_by_id)
render_job_detail_panel(job_row, can_edit, admin_read, on_view, on_edit, on_collapse)
render_job_overview_tab(job_row)
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

_CSS_KEY = "jdb_modern_v14"

# ── Status pill colours ─────────────────────────────────────────────────────
_PILL: dict[str, tuple[str, str]] = {
    "active":                   ("#166534", "#dcfce7"),
    "complete":                 ("#166534", "#dcfce7"),
    "completed":                ("#166534", "#dcfce7"),
    "closed":                   ("#166534", "#dcfce7"),
    "approved":                 ("#166534", "#dcfce7"),
    "in progress":              ("#92400e", "#fef3c7"),
    "awarded":                  ("#92400e", "#fef3c7"),
    "on hold":                  ("#92400e", "#fef3c7"),
    "scheduled":                ("#1e40af", "#dbeafe"),
    "blocked":                  ("#991b1b", "#fee2e2"),
    "cancelled":                ("#991b1b", "#fee2e2"),
    "draft":                    ("#374151", "#f3f4f6"),
    "not started":              ("#374151", "#f3f4f6"),
    "quoted":                   ("#374151", "#f3f4f6"),
    "submitted":                ("#374151", "#f3f4f6"),
    "duplicate":                ("#374151", "#f3f4f6"),
    "waiting on customer":      ("#0e7490", "#e0f2fe"),
    "electrical":               ("#5b21b6", "#ede9fe"),
    "electrical / other trade": ("#5b21b6", "#ede9fe"),
}
_PILL_DF = ("#374151", "#f3f4f6")


# ── Value helpers ────────────────────────────────────────────────────────────

def _v(val: Any, fb: str = "—") -> str:
    s = str(val or "").strip()
    return s if s and s.lower() not in ("none", "nan", "") else fb


def _date_table(val: Any) -> str:
    """MM/DD/YYYY for table cells."""
    raw = str(val or "").strip()
    if not raw or raw.lower() in ("none", "nan", ""):
        return "—"
    try:
        from datetime import datetime as _D
        d = _D.fromisoformat(raw[:10])
        return d.strftime("%m/%d/%Y")
    except Exception:
        return raw[:10] if len(raw) > 10 else raw


def _date_panel(val: Any) -> str:
    """Month D, YYYY for detail panel."""
    raw = str(val or "").strip()
    if not raw or raw.lower() in ("none", "nan", ""):
        return "—"
    try:
        from datetime import datetime as _D
        d = _D.fromisoformat(raw[:10])
        return d.strftime("%b %-d, %Y")
    except Exception:
        try:
            from datetime import datetime as _D
            d = _D.fromisoformat(raw[:10])
            return d.strftime("%b %d, %Y").replace(" 0", " ")
        except Exception:
            return raw[:10] if len(raw) > 10 else raw


def _merge_job_row(
    full: dict[str, Any],
    display: Any,
    customer_name_by_id: dict[str, str] | None,
) -> dict[str, Any]:
    """Overlay overview DataFrame fields onto the canonical jobs row."""
    out = dict(full or {})
    disp = display.to_dict() if hasattr(display, "to_dict") else dict(display or {})
    for k, v in disp.items():
        if v is not None and str(v).strip().lower() not in ("", "none", "nan"):
            out[k] = v
    cid = str(out.get("customer_id") or "").strip()
    if customer_name_by_id and cid and not str(out.get("customer_name") or "").strip():
        out["customer_name"] = customer_name_by_id.get(cid, "")
    return out


def _pill(status: Any, sm: bool = False) -> str:
    label = _v(status)
    fg, bg = _PILL.get(label.lower(), _PILL_DF)
    fs  = "0.69rem" if sm else "0.73rem"
    pad = "0.2rem 0.5rem" if sm else "0.26rem 0.62rem"
    return (
        f'<span style="display:inline-flex;align-items:center;'
        f'border-radius:999px;font-size:{fs};font-weight:700;line-height:1;'
        f'padding:{pad};white-space:nowrap;color:{fg};background:{bg};">'
        f"{html.escape(label)}</span>"
    )


# ── CSS ──────────────────────────────────────────────────────────────────────

def inject_job_database_root_canvas() -> None:
    """Force the Job Database page root/background to clean white."""
    st.markdown(
        """
        <style id="ips-job-db-root-canvas">
        html:has(.ips-job-db-page),
        body:has(.ips-job-db-page),
        .stApp:has(.ips-job-db-page) {
            --ips-bg-main: #ffffff !important;
            background: #ffffff !important;
            background-color: #ffffff !important;
        }
        html:has(.ips-job-db-page),
        body:has(.ips-job-db-page),
        .stApp:has(.ips-job-db-page),
        .stApp:has(.ips-job-db-page) [data-testid="stAppViewContainer"],
        .stApp:has(.ips-job-db-page) [data-testid="stMain"],
        .stApp:has(.ips-job-db-page) [data-testid="stMainBlockContainer"],
        .stApp:has(.ips-job-db-page) section.main,
        .stApp:has(.ips-job-db-page) main,
        .stApp:has(.ips-job-db-page) .block-container {
            background: #ffffff !important;
            background-color: #ffffff !important;
        }
        .ips-job-db-page,
        .jobs-page,
        .jobs-shell,
        .jobs-container,
        .ips-page,
        .ips-shell,
        .job-table-card,
        .job-detail-panel,
        .job-overview-card,
        .job-summary-card,
        .jdb-tbl-host,
        .jdb-panel-host,
        .jdb-panel-outer,
        .jdb-card {
            background: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_modern_jobs_css() -> None:
    if st.session_state.get(_CSS_KEY):
        return
    st.session_state[_CSS_KEY] = True
    st.markdown("""
<style>
/* Page shell: see inject_job_database_root_canvas() for .stApp / body overrides */
.stApp:has(.ips-job-db-page) section[data-testid="stMain"] .block-container {
    max-width: 1680px !important;
    padding-top: 0.35rem !important;
}
/* Flatten gray nested Streamlit borders on list/filter chrome (keep jdb table + panel) */
section[data-testid="stMain"]:has(.ips-job-db-page)
    div[data-testid="stVerticalBlockBorderWrapper"]:not(:has(.jdb-tbl-host)):not(:has(.jdb-panel-host)):not(:has(.jdb-panel-outer)) {
    background: #ffffff !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}
section[data-testid="stMain"]:has(.ips-job-db-page)
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-joblist-section-anchor),
section[data-testid="stMain"]:has(.ips-job-db-page)
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}
section[data-testid="stMain"]:has(.ips-job-db-page) .ips-surface-soft {
    border-bottom: 1px solid #e5eaf2 !important;
    margin-bottom: 0.5rem !important;
    padding-bottom: 0.35rem !important;
}
section[data-testid="stMain"]:has(.ips-job-db-page) p.ips-section-title,
section[data-testid="stMain"]:has(.ips-job-db-page) .ips-jdb-section-title {
    color: #111827 !important;
}
section[data-testid="stMain"]:has(.ips-job-db-page) p.ips-section-desc,
section[data-testid="stMain"]:has(.ips-job-db-page) .ips-jdb-section-desc {
    color: #4b5563 !important;
}

/* ═══════════════════════════════════════════════════
   TABLE CARD  (outer stVerticalBlockBorderWrapper)
═══════════════════════════════════════════════════ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host) {
    background: #ffffff !important;
    border: 1px solid #e5eaf2 !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05) !important;
    padding: 0 !important;
    overflow: hidden !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host) > div {
    padding: 0 !important;
    gap: 0 !important;
}
/* Nested BorderWrappers inside table → flat rows (not cards) */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlockBorderWrapper"]:not(:has(.jdb-tbl-host)) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlockBorderWrapper"]:not(:has(.jdb-tbl-host)) > div {
    padding: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

/* ── HTML header row ─────────────────────────────── */
.jdb-thead {
    display: flex;
    align-items: center;
    height: 2.5rem;
    padding: 0 1rem;
    gap: 0.5rem;          /* matches st.columns gap="small" */
    background: #ffffff;
    border-bottom: 1px solid #e5eaf2;
    font-size: 0.67rem;
    font-weight: 700;
    color: #6b7280;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    user-select: none;
}
/* flex values mirror column weights [.65,2,.35,1.35,.75,1,.85,.9,.9,.9] */
.jdb-th       { overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.jdb-th-num   { flex: 0.65; }
.jdb-th-name  { flex: 2.00; }
.jdb-th-cust  { flex: 1.35; }
.jdb-th-est   { flex: 0.75; }
.jdb-th-sup   { flex: 1.00; }
.jdb-th-stat  { flex: 0.85; }
.jdb-th-sd    { flex: 0.90; }
.jdb-th-ed    { flex: 0.90; }
.jdb-th-act   { flex: 0.90; text-align:right; padding-right:0; }

/* ═══════════════════════════════════════════════════
   PER-ROW CONTAINER  (stVerticalBlock that has .jdb-row)
   :not(:has(.jdb-tbl-host)) prevents matching the outer wrapper
═══════════════════════════════════════════════════ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row):not(:has(.jdb-tbl-host)) {
    display: block !important;
    width: 100% !important;
    background: #ffffff !important;
    border: none !important;
    border-bottom: 1px solid #e5eaf2 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    margin: 0 !important;
    padding: 0 1rem !important;
    transition: background 0.12s ease !important;
    position: relative !important;
    gap: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row):not(:has(.jdb-tbl-host)):last-child {
    border-bottom: none !important;
}
/* hover */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row):not(:has(.jdb-tbl-host)):hover {
    background: #f0f9ff !important;
    cursor: pointer !important;
}
/* selected */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row-sel):not(:has(.jdb-tbl-host)) {
    background: #eff6ff !important;
    box-shadow: inset 4px 0 0 #2563eb !important;
    cursor: pointer !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row-sel):not(:has(.jdb-tbl-host)):hover {
    background: #eff6ff !important;
}

/* ── Row column alignment ──────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row):not(:has(.jdb-tbl-host))
    [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 0.5rem !important;
    min-height: 3rem !important;
    position: relative !important;
    z-index: 2 !important;
    pointer-events: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row):not(:has(.jdb-tbl-host))
    [data-testid="stElementContainer"] {
    margin: 0 !important;
    padding: 0 !important;
    min-height: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row):not(:has(.jdb-tbl-host))
    [data-testid="stElementContainer"]:empty {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row) .jdb-actcol,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row) .jdb-actcol [data-testid="stElementContainer"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row) .jdb-actcol .stButton {
    pointer-events: auto !important;
}

/* ── Force dark text inside table ──────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .stMarkdown,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .stMarkdown p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .stMarkdown span { color: #111827 !important; }

/* ── Cell text ─────────────────────────────────────── */
.jdb-cell {
    font-size: 0.83rem; color: #111827;
    overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; display: block; line-height: 1.4;
}
.jdb-cell-name { white-space: normal !important; line-height: 1.35 !important; }
.jdb-cell-muted { color: #6b7280 !important; font-size: 0.79rem !important; }

/* ── Job # as blue text (not a button) ─────────────── */
.jdb-cell-num {
    color: #2563eb !important;
    font-weight: 700 !important;
    font-size: 0.83rem !important;
}
div[data-testid="stVerticalBlock"]:has(.jdb-row-sel) .jdb-cell-num {
    color: #1d4ed8 !important;
    font-weight: 800 !important;
}

/* ── Invisible full-row select (rendered after columns; out of flow) ─ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row)
    > div[data-testid="stElementContainer"]:has(.stButton) {
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 5.75rem !important;
    bottom: 0 !important;
    z-index: 1 !important;
    height: 100% !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    pointer-events: auto !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row)
    > div[data-testid="stElementContainer"]:has(.stButton) .stButton {
    width: 100% !important;
    height: 100% !important;
    min-height: 3rem !important;
    margin: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row)
    > div[data-testid="stElementContainer"]:has(.stButton) .stButton > button {
    width: 100% !important;
    height: 100% !important;
    min-height: 3rem !important;
    opacity: 0 !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    cursor: pointer !important;
    padding: 0 !important;
    margin: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row)
    > div[data-testid="stElementContainer"]:has(.stButton) .stButton > button:hover,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.jdb-row)
    > div[data-testid="stElementContainer"]:has(.stButton) .stButton > button:focus {
    opacity: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* ── Action icon buttons  (two square bordered icons) ─ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .jdb-actcol .stButton > button {
    min-width: 2rem !important; max-width: 2rem !important;
    min-height: 2rem !important; height: 2rem !important;
    padding: 0 !important; font-size: 0.9rem !important;
    border: 1px solid #e2e8f0 !important; border-radius: 6px !important;
    background: #ffffff !important; color: #374151 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    display: flex !important; align-items: center !important;
    justify-content: center !important; line-height: 1 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .jdb-actcol .stButton > button:hover {
    background: #F8FAFC !important; border-color: #E5EAF2 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    .jdb-actcol .stButton > button:disabled { opacity: 0.38 !important; }

/* ═══════════════════════════════════════════════════
   DETAIL PANEL
═══════════════════════════════════════════════════ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-outer) {
    background: #ffffff !important;
    border: 1px solid #2563eb !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.06) !important;
    padding: 1.25rem 1.4rem 1rem !important;
    margin: 0.75rem 0 1rem !important;
}

/* panel header typography */
.jdb-ph-headline {
    font-size: 1.3rem; font-weight: 800; color: #111827; margin: 0 0 0.18rem;
    word-break: break-word; line-height: 1.2;
}
.jdb-ph-cust  { font-size:.875rem; color:#6b7280; margin:0; }

/* inline meta row (pill + supervisor + created + updated) */
.jdb-ph-meta {
    display: flex; flex-wrap: wrap; align-items: center;
    gap: 0.4rem 1.25rem; font-size: 0.78rem; color: #6b7280;
    margin-top: 0.55rem;
}
.jdb-ph-mlbl { font-size:0.72rem; color:#9ca3af; display:block; margin-bottom:0.05rem; }
.jdb-ph-mval { color:#374151; font-weight:500; }

/* panel header buttons */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host) .jdb-ph-btns .stButton > button,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-outer) .jdb-ph-btns .stButton > button {
    min-height: 2rem !important; height: 2rem !important;
    padding: 0 0.75rem !important; font-size: 0.8rem !important;
    font-weight: 600 !important; border-radius: 8px !important;
    line-height: 1 !important; white-space: nowrap !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    .jdb-ph-btns [data-testid="stButton"]:first-of-type button,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-outer)
    .jdb-ph-btns [data-testid="stButton"]:first-of-type button {
    background: #ffffff !important;
    color: #2563eb !important;
    border: 1.5px solid #2563eb !important;
    box-shadow: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    .jdb-ph-btns [data-testid="stButton"]:nth-of-type(2) button,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-outer)
    .jdb-ph-btns [data-testid="stButton"]:nth-of-type(2) button {
    background: #2563eb !important;
    color: #ffffff !important;
    border: 1px solid #2563eb !important;
}

/* tabs */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-outer)
    [data-testid="stTabs"] [role="tablist"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    [data-testid="stTabs"] [data-baseweb="tab-list"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-outer)
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important; padding: 0 !important;
    border-radius: 0 !important; box-shadow: none !important; gap: 0 !important;
    border-bottom: 1.5px solid #e5eaf2 !important;
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

/* info card shells */
.jdb-card {
    background: #ffffff; border: 1px solid #e5eaf2;
    border-radius: 10px; padding: 1rem 1.15rem; height: 100%;
    box-shadow: none;
}
.jdb-card-title {
    font-size: 0.88rem; font-weight: 700; color: #111827; margin: 0 0 0.8rem;
}
.jdb-kv { display:flex; align-items:baseline; margin-bottom:.42rem; font-size:.83rem; }
.jdb-kv-lbl { color:#6b7280; font-size:.78rem; min-width:100px; flex-shrink:0; }
.jdb-kv-val { color:#111827; font-weight:500; word-break:break-word; }

/* Summary flat 4-col grid */
.jdb-sum-grid {
    display: grid; grid-template-columns: 1fr 1fr 1fr 1fr;
    gap: 0; padding-top: 0.6rem; margin-top: 0.6rem;
    border-top: 1px solid #f1f5f9;
}
.jdb-sum-lbl { font-size:.72rem; color:#6b7280; margin-bottom:.22rem; }
.jdb-sum-val { font-size:.92rem; font-weight:700; color:#111827; font-variant-numeric:tabular-nums; }

/* Activity feed */
.jdb-act-item {
    display:flex; gap:.55rem; align-items:flex-start;
    padding:.3rem 0; border-bottom:1px solid #f1f5f9; font-size:.78rem;
}
.jdb-act-item:last-child { border-bottom:none; }
.jdb-act-dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; margin-top:.32rem; }
.jdb-act-ts  { color:#9ca3af; font-size:.7rem; }
.jdb-act-txt { color:#374151; line-height:1.4; }

/* Panel inner text */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    .stMarkdown,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    .stMarkdown p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    .stMarkdown span { color:#111827 !important; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-panel-host)
    [data-testid="stCaptionContainer"] p { color:#6b7280 !important; }

/* hide helper markers */
.jdb-tbl-host, .jdb-tbody-anchor, .jdb-panel-host, .jdb-panel-outer,
.jdb-row, .jdb-row-sel, .jdb-actcol, .jdb-ph-btns { display:none !important; }
</style>
""", unsafe_allow_html=True)


# ── Leaf components ──────────────────────────────────────────────────────────

def render_activity_feed(job_row: dict[str, Any]) -> None:
    created = _date_panel(job_row.get("created_at"))
    updated = _date_panel(job_row.get("updated_at"))
    status  = _v(job_row.get("status"))
    jname   = _v(job_row.get("job_name"), "this job")
    items: list[tuple[str, str, str]] = []
    if updated and updated != "—" and updated != created:
        items.append((updated, "#2563eb", "Job record updated"))
    if status and status != "—":
        items.append((created, "#16a34a", f"Status set to {status}"))
    items.append((created, "#9ca3af", f"Job created — {jname}"))
    if not items:
        st.markdown(
            '<p style="font-size:.8rem;color:#9ca3af;margin:0">No recent activity.</p>',
            unsafe_allow_html=True,
        )
        return
    lines = [
        f'<div class="jdb-act-item">'
        f'<span class="jdb-act-dot" style="background:{c}"></span>'
        f'<div><span class="jdb-act-txt">{html.escape(t)}</span>'
        f'<br><span class="jdb-act-ts">{html.escape(ts)}</span></div></div>'
        for ts, c, t in items[:6]
    ]
    st.markdown("".join(lines), unsafe_allow_html=True)


def render_job_summary_cards(job_row: dict[str, Any]) -> None:
    """Flat 4-column grid: Labor | Material | Equipment | Total."""
    awarded = _v(job_row.get("awarded_amount"))
    try:
        if awarded != "—":
            awarded = f"${float(awarded):,.0f}"
    except Exception:
        awarded = "—"
    tiles = [
        ("Labor Total",     "—"),
        ("Material Total",  "—"),
        ("Equipment Total", "—"),
        ("Total",           awarded),
    ]
    cells = "".join(
        f'<div>'
        f'<div class="jdb-sum-lbl">{html.escape(l)}</div>'
        f'<div class="jdb-sum-val">{html.escape(v)}</div>'
        f'</div>'
        for l, v in tiles
    )
    st.markdown(f'<div class="jdb-sum-grid">{cells}</div>', unsafe_allow_html=True)


def render_job_overview_tab(job_row: dict[str, Any]) -> None:
    jnum = _v(job_row.get("job_number") or job_row.get("job_id") or job_row.get("id"))
    cust = _v(job_row.get("customer_name"))
    sup  = _v(job_row.get("supervisor") or job_row.get("project_manager"))
    stat = _v(job_row.get("status"))
    est  = _v(job_row.get("Quote (estimate)") or job_row.get("quote_number"))
    desc = _v(job_row.get("description") or job_row.get("job_name") or job_row.get("scope"),
              "No description provided.")
    start_raw = str(job_row.get("start_date") or "")
    end_raw   = str(job_row.get("target_completion_date") or job_row.get("due_date") or "")
    start = _date_panel(start_raw)
    end   = _date_panel(end_raw)
    dur   = "—"
    try:
        from datetime import datetime as _D
        if start != "—" and end != "—":
            d = (_D.fromisoformat(end_raw[:10]) - _D.fromisoformat(start_raw[:10])).days
            dur = f"{d} days" if d >= 0 else "—"
    except Exception:
        pass

    col_l, col_r = st.columns([1, 1], gap="medium")

    with col_l:
        kv_rows = [
            ("Job Number",  jnum,  False),
            ("Customer",    cust,  False),
            ("Supervisor",  sup,   False),
            ("Status",      None,  True),   # rendered as pill
            ("Estimate #",  est,   False),
            ("Description", desc,  False),
        ]
        kv_html = ""
        for lbl, val, is_pill in kv_rows:
            if is_pill:
                v_html = _pill(stat)
            elif lbl == "Description":
                v_html = (f'<span class="jdb-kv-val" style="white-space:pre-wrap">'
                          f'{html.escape(_v(val))}</span>')
            else:
                v_html = f'<span class="jdb-kv-val">{html.escape(_v(val))}</span>'
            kv_html += (
                f'<div class="jdb-kv">'
                f'<span class="jdb-kv-lbl">{html.escape(lbl)}</span>'
                f"{v_html}</div>"
            )
        st.markdown(
            f'<div class="jdb-card">'
            f'<div class="jdb-card-title">Job Information</div>'
            f"{kv_html}</div>",
            unsafe_allow_html=True,
        )

    with col_r:
        sched_html = "".join(
            f'<div class="jdb-kv"><span class="jdb-kv-lbl">{html.escape(l)}</span>'
            f'<span class="jdb-kv-val">{html.escape(v)}</span></div>'
            for l, v in [("Start Date", start), ("End Date", end), ("Duration", dur)]
        )
        st.markdown(
            f'<div class="jdb-card">'
            f'<div class="jdb-card-title">Schedule</div>'
            f"{sched_html}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:.65rem'></div>", unsafe_allow_html=True)

    col_s, col_a = st.columns([1, 1], gap="medium")
    with col_s:
        st.markdown(
            '<div class="jdb-card">'
            '<div class="jdb-card-title">Summary</div>',
            unsafe_allow_html=True,
        )
        render_job_summary_cards(job_row)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_a:
        st.markdown(
            '<div class="jdb-card">'
            '<div class="jdb-card-title">Recent Activity</div>',
            unsafe_allow_html=True,
        )
        render_activity_feed(job_row)
        st.markdown("</div>", unsafe_allow_html=True)


# ── Detail panel ─────────────────────────────────────────────────────────────

def render_job_detail_panel(
    *,
    job_row:     dict[str, Any],
    can_edit:    bool,
    admin_read:  bool,  # noqa: ARG001
    on_view:     Any,
    on_edit:     Any,
    on_collapse: Any,
) -> None:
    with st.container(border=True):
        st.markdown(
            '<span class="jdb-panel-host"></span><span class="jdb-panel-outer"></span>',
            unsafe_allow_html=True,
        )

        jid     = str(job_row.get("id") or "").strip()
        jnum    = _v(job_row.get("job_number") or job_row.get("job_id") or jid[:8])
        jname   = _v(job_row.get("job_name"), "Untitled Job")
        cust    = _v(job_row.get("customer_name"))
        status  = _v(job_row.get("status"))
        sup     = _v(job_row.get("supervisor") or job_row.get("project_manager"))
        created = _date_panel(job_row.get("created_at"))
        updated = _date_panel(job_row.get("updated_at"))

        # ── Header: 3 columns ─────────────────────────────────────────────
        col_info, col_meta, col_btns = st.columns([2.2, 2.8, 1.8], gap="small")

        with col_info:
            st.markdown(
                f'<div class="jdb-ph-headline">{html.escape(jnum)} — {html.escape(jname)}</div>'
                f'<div class="jdb-ph-cust">{html.escape(cust)}</div>',
                unsafe_allow_html=True,
            )

        with col_meta:
            # Status pill + Supervisor + Created + Last Updated — all inline
            meta_html = (
                f'<div class="jdb-ph-meta">'
                f"{_pill(status)}"
                f'<span style="display:flex;flex-direction:column;">'
                f'<span class="jdb-ph-mlbl">Supervisor</span>'
                f'<span class="jdb-ph-mval">{html.escape(sup)}</span>'
                f'</span>'
                f'<span style="display:flex;flex-direction:column;">'
                f'<span class="jdb-ph-mlbl">Created</span>'
                f'<span class="jdb-ph-mval">{html.escape(created)}</span>'
                f'</span>'
                f'<span style="display:flex;flex-direction:column;">'
                f'<span class="jdb-ph-mlbl">Last Updated</span>'
                f'<span class="jdb-ph-mval">{html.escape(updated)}</span>'
                f'</span>'
                f'</div>'
            )
            st.markdown(meta_html, unsafe_allow_html=True)

        with col_btns:
            st.markdown('<span class="jdb-ph-btns"></span>', unsafe_allow_html=True)
            b1, b2, b3 = st.columns([1, 1.5, 0.6], gap="small")
            with b1:
                if st.button("✏ Edit", key=f"jpan_edit_{jid}", type="secondary",
                             use_container_width=True, disabled=not can_edit):
                    on_edit()
            with b2:
                if st.button("📄 View / Details", key=f"jpan_view_{jid}",
                             type="primary", use_container_width=True):
                    on_view()
            with b3:
                if st.button("∧", key=f"jpan_close_{jid}",
                             use_container_width=True, help="Collapse"):
                    on_collapse()

        st.divider()

        # ── Tabs ─────────────────────────────────────────────────────────
        (t_ov, t_sc, t_fi, t_sh, t_do, t_no, t_ac) = st.tabs([
            "⊞ Overview", "≡ Scope", "$ Financials",
            "📅 Schedule", "📄 Documents", "📝 Notes", "⚡ Activity",
        ])

        with t_ov:
            render_job_overview_tab(job_row)

        with t_sc:
            scope = _v(job_row.get("scope") or job_row.get("description"),
                       "No scope defined.")
            notes = _v(job_row.get("notes"), "No notes.")
            st.markdown(
                f'<div class="jdb-card" style="margin-bottom:.75rem">'
                f'<div class="jdb-card-title">Scope of Work</div>'
                f'<p style="font-size:.84rem;color:#111827;white-space:pre-wrap;margin:0">'
                f'{html.escape(scope)}</p></div>'
                f'<div class="jdb-card"><div class="jdb-card-title">Notes</div>'
                f'<p style="font-size:.84rem;color:#111827;white-space:pre-wrap;margin:0">'
                f'{html.escape(notes)}</p></div>',
                unsafe_allow_html=True,
            )

        with t_fi:
            awarded = _v(job_row.get("awarded_amount"))
            try:
                if awarded != "—":
                    awarded = f"${float(awarded):,.2f}"
            except Exception:
                pass
            fin_rows = [
                ("Awarded Amount",    awarded),
                ("Estimate / Quote #", _v(job_row.get("Quote (estimate)") or job_row.get("quote_number"))),
                ("Linked Estimate",   _v(job_row.get("Linked estimate"))),
            ]
            f_html = "".join(
                f'<div class="jdb-kv"><span class="jdb-kv-lbl">{html.escape(l)}</span>'
                f'<span class="jdb-kv-val">{html.escape(v)}</span></div>'
                for l, v in fin_rows
            )
            st.markdown(
                f'<div class="jdb-card"><div class="jdb-card-title">Financial Overview</div>'
                f'{f_html}</div>',
                unsafe_allow_html=True,
            )
            st.caption("Open **View / Details** for full costing breakdown.")

        with t_sh:
            raw_s = str(job_row.get("start_date") or "")
            raw_e = str(job_row.get("target_completion_date") or job_row.get("due_date") or "")
            start = _date_panel(raw_s); end = _date_panel(raw_e)
            comp  = _date_panel(job_row.get("completed_date"))
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
                f'{s_html}</div>',
                unsafe_allow_html=True,
            )

        with t_do:
            st.caption("Reference attachments available in the full detail view.")
            if st.button("Open Full View →", key=f"jpan_docs_{jid}"):
                on_view()

        with t_no:
            notes = _v(job_row.get("notes"), "No notes recorded.")
            st.markdown(
                f'<div class="jdb-card"><div class="jdb-card-title">Job Notes</div>'
                f'<p style="font-size:.84rem;color:#111827;white-space:pre-wrap;margin:0">'
                f'{html.escape(notes)}</p></div>',
                unsafe_allow_html=True,
            )

        with t_ac:
            st.markdown(
                '<p style="font-size:.8rem;font-weight:700;color:#111827;margin:0 0 .65rem">Activity Log</p>',
                unsafe_allow_html=True,
            )
            render_activity_feed(job_row)


# ── Row (called inside a per-row st.container()) ─────────────────────────────

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

    jnum = _v(row.get(job_num_col) or full_row.get(job_num_col) or full_row.get("job_number"))
    name = _v(row.get("job_name") or full_row.get("job_name"), "Untitled")
    cust = _v(row.get("customer_name") or full_row.get("customer_name"))
    est  = _v(row.get("Quote (estimate)") or full_row.get("Quote (estimate)") or full_row.get("quote_number"))
    sup  = _v(full_row.get("supervisor") or full_row.get("project_manager"))
    stat = row.get("status") or full_row.get("status")
    sd   = _date_table(full_row.get("start_date"))
    ed   = _date_table(full_row.get("target_completion_date") or full_row.get("due_date"))

    # Row marker (CSS targets parent stVerticalBlock for flat table row chrome)
    st.markdown(
        f'<span class="{"jdb-row-sel" if is_selected else "jdb-row"}"></span>',
        unsafe_allow_html=True,
    )

    # Columns: job# | name | customer | est# | supervisor | status | start | end | actions
    weights = [0.65, 2.0, 1.35, 0.75, 1.0, 0.85, 0.9, 0.9, 0.9]
    cols = st.columns(weights, gap="small")

    # Job # — blue text only (row click selects)
    with cols[0]:
        st.markdown(
            f'<span class="jdb-cell jdb-cell-num" title="{html.escape(jnum, quote=True)}">'
            f'{html.escape(jnum)}</span>',
            unsafe_allow_html=True,
        )

    # Project / Description
    with cols[1]:
        st.markdown(
            f'<span class="jdb-cell jdb-cell-name" title="{html.escape(name, quote=True)}">'
            f'{html.escape(name)}</span>',
            unsafe_allow_html=True,
        )

    # Customer
    with cols[2]:
        st.markdown(
            f'<span class="jdb-cell jdb-cell-muted" title="{html.escape(cust, quote=True)}">'
            f'{html.escape(cust)}</span>',
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
            f'{html.escape(sup)}</span>',
            unsafe_allow_html=True,
        )

    # Status pill
    with cols[5]:
        st.markdown(_pill(stat, sm=True), unsafe_allow_html=True)

    # Start date
    with cols[6]:
        st.markdown(
            f'<span class="jdb-cell jdb-cell-muted">{html.escape(sd)}</span>',
            unsafe_allow_html=True,
        )

    # End date
    with cols[7]:
        st.markdown(
            f'<span class="jdb-cell jdb-cell-muted">{html.escape(ed)}</span>',
            unsafe_allow_html=True,
        )

    # Actions: two bordered square icon buttons side-by-side
    with cols[8]:
        st.markdown('<span class="jdb-actcol"></span>', unsafe_allow_html=True)
        a1, a2 = st.columns(2, gap="small")
        with a1:
            if st.button("👁", key=f"jrow_view_{jid}",
                         use_container_width=True, help="View full job details"):
                on_view()
        with a2:
            if st.button("🗑", key=f"jrow_del_{jid}",
                         use_container_width=True, disabled=not can_edit,
                         help="Delete job" if can_edit else "Admin/manager only"):
                on_delete()

    # Invisible row select — after columns so it does not create a gray bar above the row
    if st.button("\u200b", key=f"jrow_sel_{jid}", use_container_width=True, help=f"Select {jnum}"):
        on_select()


# ── Main table ───────────────────────────────────────────────────────────────

def render_jobs_table(
    *,
    df_display:          Any,
    job_num_col:         str,
    can_edit:            bool,
    jobs:                list[dict[str, Any]],
    admin_read:          bool = False,
    customer_name_by_id: dict[str, str] | None = None,
) -> None:
    inject_modern_jobs_css()

    by_id: dict[str, dict[str, Any]] = {
        str(j.get("id") or ""): j for j in jobs if j.get("id")
    }
    sel = str(st.session_state.get("selected_job_id") or "").strip()
    panel_row: dict[str, Any] | None = None

    with st.container(border=True):
        # Marker on the outer card — used by CSS to scope all inner selectors
        st.markdown('<span class="jdb-tbl-host"></span>', unsafe_allow_html=True)

        # HTML header (flex values mirror column weights above)
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

        st.markdown('<span class="jdb-tbody-anchor" aria-hidden="true"></span>', unsafe_allow_html=True)

        for _, row in df_display.iterrows():
            jid = str(row.get("id") or "").strip()
            if not jid:
                continue
            full_row = _merge_job_row(by_id.get(jid, {}), row, customer_name_by_id)
            is_selected = jid == sel

            # ── Per-row container — REQUIRED for CSS :has() to work per row ──
            with st.container():
                def _toggle(j=jid):
                    st.session_state["selected_job_id"] = (
                        None if st.session_state.get("selected_job_id") == j else j
                    )
                    st.rerun()

                def _open_view(j=jid):
                    st.session_state.update({
                        "job_view_mode":   "view",
                        "selected_job_id": j,
                    })
                    st.session_state.pop("job_mode", None)
                    st.session_state.pop("job_edit_id", None)
                    st.rerun()

                def _del(j=jid):
                    pend = st.session_state.get(IPS_PENDING_DELETE)
                    if not isinstance(pend, dict):
                        pend = {}
                        st.session_state[IPS_PENDING_DELETE] = pend
                    pend[TABLE_KEY_JOBS] = [j]
                    st.rerun()

                render_job_row(
                    row=row, full_row=full_row, job_num_col=job_num_col,
                    can_edit=can_edit, is_selected=is_selected,
                    on_select=_toggle, on_view=_open_view, on_delete=_del,
                )

            if is_selected:
                panel_row = full_row
    if sel and panel_row:
        def _pv():
            st.session_state.update({"job_view_mode": "view", "selected_job_id": sel})
            st.session_state.pop("job_mode", None)
            st.session_state.pop("job_edit_id", None)
            st.rerun()

        def _pe():
            st.session_state.update({
                "job_view_mode": "edit",
                "selected_job_id": sel,
                "job_mode": "edit",
                "job_edit_id": sel,
            })
            st.session_state.pop("job_number_manual_input", None)
            st.rerun()

        def _pc():
            st.session_state["selected_job_id"] = None
            st.rerun()

        render_job_detail_panel(
            job_row=panel_row,
            can_edit=can_edit,
            admin_read=admin_read,
            on_view=_pv,
            on_edit=_pe,
            on_collapse=_pc,
        )
