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
open_job_detail_dialog(job_id) / show_job_detail_dialog_if_pending()
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
    from app.ui.clean_table import inject_clean_table_css
except ImportError:
    from ui.clean_table import inject_clean_table_css  # type: ignore

try:
    from table_actions import IPS_PENDING_DELETE, TABLE_KEY_JOBS
except ImportError:
    from app.table_actions import IPS_PENDING_DELETE, TABLE_KEY_JOBS  # type: ignore

JOB_DB_DETAIL_DIALOG_KEY = "job_db_detail_dialog_job_id"
JOB_DB_TABLE_BY_ID_KEY = "job_db_table_jobs_by_id"


def _clear_job_db_detail_dialog() -> None:
    st.session_state.pop(JOB_DB_DETAIL_DIALOG_KEY, None)


def set_job_db_dialog_context(
    *,
    jobs: list[dict[str, Any]],
    can_edit: bool,
    admin_read: bool = False,
) -> None:
    """Cache job rows for the detail dialog (table + card layouts)."""
    st.session_state[JOB_DB_TABLE_BY_ID_KEY] = {
        str(j.get("id") or ""): j for j in jobs if j.get("id")
    }
    st.session_state["_job_db_dialog_can_edit"] = can_edit
    st.session_state["_job_db_dialog_admin_read"] = admin_read


def open_job_detail_dialog(job_id: str) -> None:
    """Select a job row and open the detail dialog on the next rerun."""
    jid = str(job_id or "").strip()
    if not jid:
        return
    st.session_state["selected_job_id"] = jid
    st.session_state[JOB_DB_DETAIL_DIALOG_KEY] = jid


def show_job_detail_dialog_if_pending() -> None:
    """Open the job detail dialog when ``JOB_DB_DETAIL_DIALOG_KEY`` is set."""
    if str(st.session_state.get(JOB_DB_DETAIL_DIALOG_KEY) or "").strip():
        show_job_detail_dialog()


@st.dialog("Job Details", width="large", on_dismiss=_clear_job_db_detail_dialog)
def show_job_detail_dialog() -> None:
    by_id = st.session_state.get(JOB_DB_TABLE_BY_ID_KEY)
    if not isinstance(by_id, dict):
        by_id = {}
    jid = str(st.session_state.get(JOB_DB_DETAIL_DIALOG_KEY) or "").strip()
    job_row = by_id.get(jid) if jid else None
    if not job_row:
        st.warning("That job could not be loaded.")
        if st.button("Close", key="job_dlg_missing_close"):
            _clear_job_db_detail_dialog()
            st.rerun()
        return

    can_edit = bool(st.session_state.get("_job_db_dialog_can_edit"))
    admin_read = bool(st.session_state.get("_job_db_dialog_admin_read"))

    def _goto_full_view() -> None:
        st.session_state.update({"job_view_mode": "view", "selected_job_id": jid})
        st.session_state.pop("job_mode", None)
        st.session_state.pop("job_edit_id", None)
        _clear_job_db_detail_dialog()
        st.rerun()

    def _goto_edit() -> None:
        st.session_state.update({
            "job_view_mode": "edit",
            "selected_job_id": jid,
            "job_mode": "edit",
            "job_edit_id": jid,
        })
        st.session_state.pop("job_number_manual_input", None)
        _clear_job_db_detail_dialog()
        st.rerun()

    def _close() -> None:
        st.session_state.pop("selected_job_id", None)
        _clear_job_db_detail_dialog()
        st.rerun()

    render_job_detail_panel(
        job_row=job_row,
        can_edit=can_edit,
        admin_read=admin_read,
        on_view=_goto_full_view,
        on_edit=_goto_edit,
        on_collapse=_close,
    )

_CSS_KEY = "jdb_modern_v19"

# Shared grid template for header + data rows
_JDB_GRID_COLS = "100px 2fr 1.4fr 1fr 1.2fr 1fr 1fr 1fr 120px"

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


def _job_row_grid_html(
    *,
    jid: str,
    jnum: str,
    name: str,
    cust: str,
    est: str,
    sup: str,
    stat: Any,
    sd: str,
    ed: str,
    is_selected: bool,
) -> str:
    """Single HTML grid row — matches ``.job-row`` / ``.job-row.selected`` CSS."""
    row_cls = (
        "job-row ips-clean-row selected"
        if is_selected
        else "job-row ips-clean-row"
    )
    jid_attr = html.escape(jid, quote=True)
    return (
        f'<div class="{row_cls}" data-jid="{jid_attr}" data-row-id="{jid_attr}" role="button" tabindex="0">'
        f'<span class="job-number" title="{html.escape(jnum, quote=True)}">{html.escape(jnum)}</span>'
        f'<span class="job-project jdb-cell" title="{html.escape(name, quote=True)}">{html.escape(name)}</span>'
        f'<span class="jdb-cell jdb-cell-muted" title="{html.escape(cust, quote=True)}">{html.escape(cust)}</span>'
        f'<span class="jdb-cell jdb-cell-muted">{html.escape(est)}</span>'
        f'<span class="jdb-cell jdb-cell-muted" title="{html.escape(sup, quote=True)}">{html.escape(sup)}</span>'
        f'<span class="jdb-cell jdb-cell-stat">{_pill(stat, sm=True)}</span>'
        f'<span class="jdb-cell jdb-cell-muted">{html.escape(sd)}</span>'
        f'<span class="jdb-cell jdb-cell-muted">{html.escape(ed)}</span>'
        f'<span class="job-row-act-slot"></span>'
        f"</div>"
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
    inject_clean_table_css()
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

/* ── Table header + data rows (CSS grid) ───────────── */
.jdb-thead {
    display: grid;
    grid-template-columns: 100px 2fr 1.4fr 1fr 1.2fr 1fr 1fr 1fr 120px;
    align-items: center;
    min-height: 2.5rem;
    padding: 0 14px;
    gap: 0 10px;
    background: #ffffff;
    border-bottom: 1px solid #e5eaf2;
    font-size: 0.67rem;
    font-weight: 700;
    color: #6b7280;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    user-select: none;
}
.jdb-thead > span { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.jdb-th-act { text-align: right; }

.job-row {
    display: grid;
    grid-template-columns: 100px 2fr 1.4fr 1fr 1.2fr 1fr 1fr 1fr 120px;
    align-items: center;
    gap: 0 10px;
    min-height: 60px;
    padding: 10px 14px;
    background: #ffffff;
    border-bottom: 1px solid #e5eaf2;
    border-left: 4px solid transparent;
    cursor: pointer;
    box-sizing: border-box;
    transition: background 0.12s ease, border-color 0.12s ease;
}
div[data-testid="stVerticalBlock"]:has(.job-row-wrap):hover .job-row:not(.selected) {
    background: #f8fbff;
}
.job-row.selected {
    background: #eef5ff;
    border-left: 4px solid #2563eb;
}
.job-number {
    color: #2563eb;
    font-weight: 700;
    font-size: 0.84rem;
    background: transparent;
    border: none;
    padding: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.job-project {
    font-weight: 700;
    white-space: normal;
    line-height: 1.35;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.jdb-cell {
    font-size: 0.84rem;
    color: #111827;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    line-height: 1.4;
    min-width: 0;
}
.jdb-cell-muted { color: #6b7280; font-size: 0.8rem; }
.job-row-act-slot { min-height: 1px; }

/* ── Streamlit row host (HTML row + compact action overlay only) ─ */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host)) {
    position: relative !important;
    min-height: 60px !important;
    margin: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host))
    > [data-testid="stElementContainer"] {
    margin: 0 !important;
    padding: 0 !important;
    min-height: 0 !important;
}
/* Invisible full-row open button (Streamlit click target) */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host))
    > [data-testid="stElementContainer"]:has(.jdb-row-select-btn)
    + [data-testid="stElementContainer"]:has(.stButton) {
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 96px !important;
    bottom: 0 !important;
    z-index: 1 !important;
    height: 60px !important;
    max-height: 60px !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    pointer-events: auto !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host))
    > [data-testid="stElementContainer"]:has(.jdb-row-select-btn)
    + [data-testid="stElementContainer"]:has(.stButton) .stButton,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host))
    > [data-testid="stElementContainer"]:has(.jdb-row-select-btn)
    + [data-testid="stElementContainer"]:has(.stButton) .stButton > button {
    width: 100% !important;
    height: 60px !important;
    min-height: 60px !important;
    max-height: 60px !important;
    margin: 0 !important;
    padding: 0 !important;
    opacity: 0 !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    cursor: pointer !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host))
    > [data-testid="stElementContainer"]:has(.jdb-row-actions)
    + [data-testid="stElementContainer"] {
    position: absolute !important;
    top: 0 !important;
    right: 10px !important;
    width: 86px !important;
    height: 60px !important;
    max-height: 60px !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    z-index: 3 !important;
    pointer-events: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host))
    > [data-testid="stElementContainer"]:has(.jdb-row-actions)
    + [data-testid="stElementContainer"] [data-testid="stHorizontalBlock"] {
    height: 60px !important;
    align-items: center !important;
    justify-content: flex-end !important;
    gap: 0.4rem !important;
    min-height: 0 !important;
    background: transparent !important;
    pointer-events: auto !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host))
    > [data-testid="stElementContainer"]:has(.jdb-row-actions)
    + [data-testid="stElementContainer"] [data-testid="column"] {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 0 !important;
    padding: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host))
    > [data-testid="stElementContainer"]:has(.jdb-row-actions)
    + [data-testid="stElementContainer"] .stButton,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host))
    > [data-testid="stElementContainer"]:has(.jdb-row-actions)
    + [data-testid="stElementContainer"] [data-testid="stButton"] {
    margin: 0 !important;
    padding: 0 !important;
    background: transparent !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host))
    > [data-testid="stElementContainer"]:has(.jdb-row-actions)
    + [data-testid="stElementContainer"] .stButton > button {
    width: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
    max-width: 38px !important;
    min-height: 38px !important;
    max-height: 38px !important;
    padding: 0 !important;
    font-size: 0.95rem !important;
    line-height: 1 !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    background: #ffffff !important;
    color: #374151 !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host))
    > [data-testid="stElementContainer"]:has(.jdb-row-actions)
    + [data-testid="stElementContainer"] .stButton > button:hover {
    background: #f8fafc !important;
    border-color: #cbd5e1 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    div[data-testid="stVerticalBlock"]:has(.job-row-wrap):not(:has(.jdb-tbl-host))
    > [data-testid="stElementContainer"]:has(.jdb-row-actions)
    + [data-testid="stElementContainer"] .stButton > button:disabled {
    opacity: 0.38 !important;
}
/* Table row-click bridge iframe — zero layout footprint */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host)
    [data-testid="stElementContainer"]:has(.jdb-click-bridge) {
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    border: none !important;
    background: transparent !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host) .stMarkdown,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.jdb-tbl-host) .stMarkdown p {
    margin: 0 !important;
}

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
.job-row-wrap, .jdb-row-select-btn, .jdb-row-actions, .jdb-click-bridge, .jdb-ph-btns { display:none !important; }
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
                if st.button("✕", key=f"jpan_close_{jid}",
                             use_container_width=True, help="Close"):
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
    on_row_click: Any,
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

    st.markdown('<span class="job-row-wrap ips-clean-row-wrap" aria-hidden="true"></span>', unsafe_allow_html=True)
    st.markdown(
        _job_row_grid_html(
            jid=jid,
            jnum=jnum,
            name=name,
            cust=cust,
            est=est,
            sup=sup,
            stat=stat,
            sd=sd,
            ed=ed,
            is_selected=is_selected,
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        '<span class="jdb-row-select-btn ips-clean-row-select-btn" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    if st.button(
        " ",
        key=f"job_row_click_{jid}",
        help=f"Open job {jnum}",
    ):
        on_row_click()

    st.markdown('<span class="jdb-row-actions ips-clean-actions" aria-hidden="true"></span>', unsafe_allow_html=True)
    a1, a2 = st.columns(2, gap="small")
    with a1:
        if st.button("👁", key=f"jrow_view_{jid}", help="View job details"):
            on_view()
    with a2:
        if st.button(
            "🗑",
            key=f"jrow_del_{jid}",
            disabled=not can_edit,
            help="Delete job" if can_edit else "Admin/manager only",
        ):
            on_delete()


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
        str(j.get("id") or ""): dict(j) for j in jobs if j.get("id")
    }
    sel = str(st.session_state.get("selected_job_id") or "").strip()

    with st.container(border=True):
        # Marker on the outer card — used by CSS to scope all inner selectors
        st.markdown('<span class="jdb-tbl-host ips-clean-table"></span>', unsafe_allow_html=True)

        st.markdown(
            '<div class="jdb-thead">'
            '<span>Job #</span>'
            '<span>Project / Description</span>'
            '<span>Customer</span>'
            '<span>Estimate #</span>'
            '<span>Supervisor</span>'
            '<span>Status</span>'
            '<span>Start Date</span>'
            '<span>End Date</span>'
            '<span class="jdb-th-act">Actions</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<span class="jdb-tbody-anchor" aria-hidden="true"></span>', unsafe_allow_html=True)

        for _, row in df_display.iterrows():
            jid = str(row.get("id") or "").strip()
            if not jid:
                continue
            full_row = _merge_job_row(by_id.get(jid, {}), row, customer_name_by_id)
            by_id[jid] = full_row
            is_selected = jid == sel

            # ── Per-row container — REQUIRED for CSS :has() to work per row ──
            with st.container():
                def _open_dialog(j=jid):
                    open_job_detail_dialog(j)
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
                    on_row_click=_open_dialog,
                    on_view=_open_dialog, on_delete=_del,
                )

    st.session_state[JOB_DB_TABLE_BY_ID_KEY] = by_id
    st.session_state["_job_db_dialog_can_edit"] = can_edit
    st.session_state["_job_db_dialog_admin_read"] = admin_read
    show_job_detail_dialog_if_pending()
