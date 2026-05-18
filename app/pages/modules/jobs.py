"""Jobs module (Phase 2) — list + detail panel."""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.layout import render_selected_detail_panel
    from app.components.status import status_pill_html
    from app.components.tables import render_data_table
    from app.components.tabs import render_tabs
    from app.pages.modules._data import load_jobs, lookup_options
    from app.pages.modules._session import select_key, tab_key
    from app.styles import inject_global_css
    from app.utils.formatting import fmt_date
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.layout import render_selected_detail_panel  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._data import load_jobs, lookup_options  # type: ignore
    from pages.modules._session import select_key, tab_key  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.formatting import fmt_date  # type: ignore

_SEL = select_key("jobs")
_TAB = tab_key("jobs")


def _filter_jobs(rows: list[dict], *, q: str, status: str, customer: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            r
            for r in out
            if ql in str(r.get("job_number", "")).lower()
            or ql in str(r.get("job_name", "")).lower()
            or ql in str(r.get("customer", "")).lower()
        ]
    if status and status != "All Statuses":
        out = [r for r in out if str(r.get("status", "")) == status]
    if customer and customer != "All Customers":
        out = [r for r in out if str(r.get("customer", "")) == customer]
    return out


def _render_detail(job: dict) -> None:
    jn = str(job.get("job_number") or "")
    title = f"{jn} — {job.get('job_name') or ''}"

    def _tabs() -> None:
        tab = render_tabs(
            ["Overview", "Scope", "Financials", "Schedule", "Documents", "Notes", "Activity"],
            session_key=_TAB,
            default="Overview",
        )
        st.caption(f"Viewing **{tab}**")

    def _body() -> None:
        ot = "d" + "iv"
        st.markdown(
            f'<{ot} class="ips-detail-meta-row">'
            f"<span>Status<br>{status_pill_html(str(job.get('status') or ''))}</span>"
            f"<span>Supervisor<br><strong>{html.escape(str(job.get('supervisor') or '—'))}</strong></span>"
            f"<span>Customer<br><strong>{html.escape(str(job.get('customer') or '—'))}</strong></span>"
            f"</{ot}>",
            unsafe_allow_html=True,
        )
        tab = str(st.session_state.get(_TAB) or "Overview")
        if tab != "Overview":
            st.info(f"{tab} content will connect to Supabase in a later phase.")
            return
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Job Information**")
            st.markdown(
                f'<dl class="ips-info-grid">'
                f"<dt>Job Number</dt><dd>{html.escape(jn)}</dd>"
                f"<dt>Customer</dt><dd>{html.escape(str(job.get('customer') or '—'))}</dd>"
                f"<dt>Supervisor</dt><dd>{html.escape(str(job.get('supervisor') or '—'))}</dd>"
                f"<dt>Status</dt><dd>{status_pill_html(str(job.get('status') or ''))}</dd>"
                f"<dt>Estimate #</dt><dd>{html.escape(str(job.get('estimate_number') or '—'))}</dd>"
                f"<dt>Description</dt><dd>{html.escape(str(job.get('description') or '—'))}</dd>"
                f"</dl>",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown("**Schedule**")
            st.markdown(
                f'<dl class="ips-info-grid">'
                f"<dt>Start Date</dt><dd>{html.escape(fmt_date(job.get('start_date')))}</dd>"
                f"<dt>End Date</dt><dd>{html.escape(fmt_date(job.get('end_date')))}</dd>"
                f"<dt>Progress</dt><dd>{int(job.get('progress') or 0)}%</dd>"
                f"</dl>",
                unsafe_allow_html=True,
            )
        st.markdown("**Summary**")
        st.caption("Labor, material, and equipment totals will load from job costing when connected.")

    render_selected_detail_panel(str(job.get("job_name") or title), tabs_fn=_tabs, body_fn=_body)


def render() -> None:
    inject_global_css()
    all_jobs = load_jobs()
    customers = sorted({str(j.get("customer") or "") for j in all_jobs if j.get("customer")})

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Jobs", "Manage active projects, schedules, and job details.")
    with act_r:
        st.button("Export", key="jobs_export", use_container_width=True)
        st.button("+ New Job", key="jobs_new", type="primary", use_container_width=True)

    def _filters() -> None:
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 0.7])
        with c1:
            st.text_input("Search", placeholder="Search jobs…", key="jobs_search", label_visibility="collapsed")
        with c2:
            st.selectbox(
                "Status",
                ["All Statuses", *lookup_options("job_statuses")],
                key="jobs_filter_status",
                label_visibility="collapsed",
            )
        with c3:
            st.selectbox(
                "Customer",
                ["All Customers", *customers],
                key="jobs_filter_customer",
                label_visibility="collapsed",
            )
        with c4:
            st.date_input(
                "Range",
                value=(date.today().replace(day=1), date.today()),
                key="jobs_filter_dates",
                label_visibility="collapsed",
            )
        with c5:
            if st.button("Clear", key="jobs_clear_filters", use_container_width=True):
                st.session_state["jobs_search"] = ""
                st.session_state["jobs_filter_status"] = "All Statuses"
                st.session_state["jobs_filter_customer"] = "All Customers"
                st.rerun()

    layout_filter_bar(_filters)

    filtered = _filter_jobs(
        all_jobs,
        q=str(st.session_state.get("jobs_search") or "").strip(),
        status=str(st.session_state.get("jobs_filter_status") or "All Statuses"),
        customer=str(st.session_state.get("jobs_filter_customer") or "All Customers"),
    )

    selected_id = str(st.session_state.get(_SEL) or "")
    if selected_id and not any(str(j.get("id")) == selected_id for j in filtered):
        st.session_state.pop(_SEL, None)
        selected_id = ""

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "job_number":
            return f'<span style="color:#2563eb;font-weight:600">{html.escape(str(row.get("job_number") or ""))}</span>'
        return html.escape(str(row.get(field) or "—"))

    sel = render_data_table(
        filtered,
        [
            ("job_number", "JOB #"),
            ("job_name", "PROJECT / DESCRIPTION"),
            ("customer", "CUSTOMER"),
            ("estimate_number", "ESTIMATE #"),
            ("supervisor", "SUPERVISOR"),
            ("status", "STATUS"),
            ("start_date", "START DATE"),
            ("end_date", "END DATE"),
        ],
        row_id_key="id",
        selected_id=selected_id or None,
        session_select_key=_SEL,
        col_fr=["0.85fr", "1.5fr", "1.1fr", "0.85fr", "1fr", "0.85fr", "0.85fr", "0.85fr"],
        cell_renderer=_cell,
    )

    if sel:
        job = next((j for j in filtered if str(j.get("id")) == sel), None)
        if job:
            _render_detail(job)
