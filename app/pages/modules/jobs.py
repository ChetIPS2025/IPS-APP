"""Jobs module (Phase 2) — list + detail panel."""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.layout import render_tab_placeholder
    from app.components.modals import render_record_detail_dialog
    from app.components.status import status_pill_html
    from app.components.tables import render_clickable_table
    from app.components.tabs import render_tabs
    from app.pages.modules._data import customer_filter_options, load_jobs, lookup_options, persist_job
    from app.pages.modules._crud import apply_persist_feedback, is_demo_id
    from app.pages.modules._session import select_key, tab_key
    from app.utils.formatting import fmt_date
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.layout import render_tab_placeholder  # type: ignore
    from components.modals import render_record_detail_dialog  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_clickable_table  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._data import customer_filter_options, load_jobs, lookup_options, persist_job  # type: ignore
    from pages.modules._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages.modules._session import select_key, tab_key  # type: ignore
    from utils.formatting import fmt_date  # type: ignore

_SEL = select_key("jobs")
_TAB = tab_key("jobs")
_JOB_TABS = [
    "Overview",
    "Scope",
    "Financials",
    "Schedule",
    "Documents",
    "Photos",
    "Daily Updates",
    "Notes",
    "Activity",
]


def _clear_jobs_filters() -> None:
    """Reset filter widgets (must run via button ``on_click``, not after widgets render)."""
    st.session_state["jobs_search"] = ""
    st.session_state["jobs_filter_status"] = "All Statuses"
    st.session_state["jobs_filter_customer"] = "All Customers"


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
        render_tabs(_JOB_TABS, session_key=_TAB, default="Overview")

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
            render_tab_placeholder(f"{tab} content will connect to Supabase in a later phase.")
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
        jid = str(job.get("id") or "")
        if not is_demo_id(jid):
            with st.expander("Edit job", expanded=False):
                ec1, ec2 = st.columns(2)
                with ec1:
                    st.text_input("Job number", value=str(job.get("job_number") or ""), key=f"job_edit_num_{jid}")
                    st.text_input("Job name", value=str(job.get("job_name") or ""), key=f"job_edit_name_{jid}")
                    st.selectbox(
                        "Customer",
                        customer_filter_options(),
                        index=0,
                        key=f"job_edit_cust_{jid}",
                    )
                    st.selectbox(
                        "Status",
                        lookup_options("job_statuses"),
                        index=max(0, lookup_options("job_statuses").index(str(job.get("status") or "Draft")))
                        if str(job.get("status") or "") in lookup_options("job_statuses")
                        else 0,
                        key=f"job_edit_status_{jid}",
                    )
                with ec2:
                    st.text_input("Supervisor", value=str(job.get("supervisor") or ""), key=f"job_edit_sup_{jid}")
                    st.date_input("Start date", value=job.get("start_date") or None, key=f"job_edit_start_{jid}")
                    st.date_input("End date", value=job.get("end_date") or None, key=f"job_edit_end_{jid}")
                    st.slider("Progress %", 0, 100, int(job.get("progress") or 0), key=f"job_edit_prog_{jid}")
                st.text_area("Description", value=str(job.get("description") or ""), key=f"job_edit_desc_{jid}")
                if st.button("Save job", key=f"job_save_{jid}", type="primary"):
                    ui = {
                        "job_number": st.session_state.get(f"job_edit_num_{jid}"),
                        "job_name": st.session_state.get(f"job_edit_name_{jid}"),
                        "customer": st.session_state.get(f"job_edit_cust_{jid}"),
                        "status": st.session_state.get(f"job_edit_status_{jid}"),
                        "supervisor": st.session_state.get(f"job_edit_sup_{jid}"),
                        "start_date": st.session_state.get(f"job_edit_start_{jid}"),
                        "end_date": st.session_state.get(f"job_edit_end_{jid}"),
                        "progress": st.session_state.get(f"job_edit_prog_{jid}"),
                        "description": st.session_state.get(f"job_edit_desc_{jid}"),
                    }
                    ok, msg = persist_job(ui, row_id=jid)
                    apply_persist_feedback(ok, msg)
                    if ok:
                        st.rerun()

    render_record_detail_dialog(
        f"{title} — Job Details",
        module_name="jobs",
        session_select_key=_SEL,
        tab_labels=_JOB_TABS,
        tab_session_key=_TAB,
        tabs_fn=_tabs,
        body_fn=_body,
    )


def render() -> None:
    try:
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
    if not begin_module("jobs"):
        return
    all_jobs = load_jobs()
    customers = customer_filter_options()

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Jobs", "Manage active projects, schedules, and job details.")
    with act_r:
        st.button("Export", key="jobs_export", use_container_width=True)
        if st.button("+ New Job", key="jobs_new", type="primary", use_container_width=True):
            st.session_state["ips_job_form"] = True

    if st.session_state.get("ips_job_form"):
        with st.expander("New job", expanded=True):
            nc1, nc2 = st.columns(2)
            with nc1:
                st.text_input("Job number", key="job_new_num")
                st.text_input("Job name", key="job_new_name")
                st.selectbox("Customer", customer_filter_options(), key="job_new_cust")
                st.selectbox("Status", lookup_options("job_statuses"), key="job_new_status")
            with nc2:
                st.text_input("Supervisor", key="job_new_sup")
                st.date_input("Start date", key="job_new_start", value=None)
                st.date_input("End date", key="job_new_end", value=None)
            st.text_area("Description", key="job_new_desc")
            sb1, sb2 = st.columns(2)
            with sb1:
                if st.button("Save job", key="job_save_new", type="primary"):
                    ok, msg = persist_job(
                        {
                            "job_number": st.session_state.get("job_new_num"),
                            "job_name": st.session_state.get("job_new_name"),
                            "customer": st.session_state.get("job_new_cust"),
                            "status": st.session_state.get("job_new_status"),
                            "supervisor": st.session_state.get("job_new_sup"),
                            "start_date": st.session_state.get("job_new_start"),
                            "end_date": st.session_state.get("job_new_end"),
                            "description": st.session_state.get("job_new_desc"),
                        }
                    )
                    if apply_persist_feedback(ok, msg, clear_keys=("ips_job_form",)):
                        st.rerun()
            with sb2:
                if st.button("Cancel", key="job_cancel_new"):
                    st.session_state.pop("ips_job_form", None)
                    st.rerun()

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
            st.button(
                "Clear",
                key="jobs_clear_filters",
                use_container_width=True,
                on_click=_clear_jobs_filters,
            )

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

    def _plain_cell(field: str, row: dict) -> str:
        if field in ("start_date", "end_date"):
            return fmt_date(row.get(field))
        return str(row.get(field) or "—")

    def _html_cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "job_number":
            return (
                f'<span style="color:#2563eb;font-weight:600">'
                f'{html.escape(str(row.get("job_number") or ""))}</span>'
            )
        return html.escape(_plain_cell(field, row))

    sel = render_clickable_table(
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
        "jobs_list",
        row_id_key="id",
        session_select_key=_SEL,
        selected_id=selected_id or None,
        html_cell=_html_cell,
        col_fr=["0.75fr", "1.4fr", "1fr", "0.85fr", "1fr", "0.85fr", "0.85fr", "0.85fr"],
    )

    if sel:
        job = next((j for j in filtered if str(j.get("id")) == sel), None)
        if job:
            _render_detail(job)
