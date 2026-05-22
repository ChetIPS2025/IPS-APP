"""Jobs module (Phase 2) — list + detail panel."""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.clickable_table import close_modal_and_clear_selection, render_clickable_table
    from app.pages._core._data import customer_filter_options, load_jobs, lookup_options, persist_job
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
    from app.styles import inject_jobs_module_css
    from app.utils.formatting import fmt_date
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.clickable_table import close_modal_and_clear_selection, render_clickable_table  # type: ignore
    from pages._core._data import customer_filter_options, load_jobs, lookup_options, persist_job  # type: ignore
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from styles import inject_jobs_module_css  # type: ignore
    from utils.formatting import fmt_date  # type: ignore

_SEL = select_key("jobs")
_JOBS_MODAL_KEY = "ips_jobs_detail_modal_id"
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


def _default_jobs_date_range() -> tuple[date, date]:
    today = date.today()
    return today.replace(day=1), today


def _clear_jobs_filters() -> None:
    """Reset filter widgets (must run via button ``on_click``, not after widgets render)."""
    st.session_state["jobs_search"] = ""
    st.session_state["jobs_filter_status"] = "All Statuses"
    st.session_state["jobs_filter_customer"] = "All Customers"
    st.session_state["jobs_filter_dates"] = _default_jobs_date_range()


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


def _clear_jobs_detail_modal() -> None:
    close_modal_and_clear_selection(
        table_key="jobs_list",
        session_select_key=_SEL,
        modal_key=_JOBS_MODAL_KEY,
    )


def _open_jobs_detail_modal(job_id: str, _job: dict | None = None) -> None:
    jid = str(job_id or "").strip()
    if not jid:
        return
    st.session_state[_SEL] = jid
    st.session_state[_JOBS_MODAL_KEY] = jid


def _show_jobs_detail_modal_if_pending() -> None:
    if str(st.session_state.get(_JOBS_MODAL_KEY) or "").strip():
        _show_jobs_detail_modal()


def _safe_value(value: object, fallback: str = "—") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _safe_key(value: object) -> str:
    return html.escape(_safe_value(value, ""))


def _status_class(status: object) -> str:
    raw = _safe_value(status, "").lower()
    aliases = {
        "draft": "draft",
        "active": "active",
        "awarded": "awarded",
        "approved": "approved",
        "completed": "completed",
        "complete": "completed",
        "pending": "pending",
        "scheduled": "scheduled",
        "on hold": "pending",
        "cancelled": "danger",
        "canceled": "danger",
        "closed": "completed",
    }
    slug = aliases.get(raw, "draft")
    return f"ips-pill ips-pill-{slug}"


def _status_pill(status: object) -> str:
    label = _safe_value(status)
    return f'<span class="{_status_class(status)}">{html.escape(label)}</span>'


def _detail_field(label: str, value: object, *, html_value: str | None = None) -> str:
    rendered = html_value if html_value is not None else html.escape(_safe_value(value))
    return (
        f'<div class="ips-detail-field">'
        f'<span class="ips-detail-label">{html.escape(label)}</span>'
        f'<span class="ips-detail-value">{rendered}</span>'
        f"</div>"
    )


def _dialog_meta_card(label: str, value: object) -> str:
    return (
        f'<div class="ips-dialog-meta-card">'
        f'<div class="ips-dialog-meta-label">{html.escape(label)}</div>'
        f'<div class="ips-dialog-meta-value">{html.escape(_safe_value(value))}</div>'
        f"</div>"
    )


def _dialog_card(title: str, body_html: str) -> str:
    return (
        f'<div class="ips-dialog-card">'
        f'<div class="ips-dialog-card-title">{html.escape(title)}</div>'
        f"{body_html}"
        f"</div>"
    )


def _schedule_summary(job: dict) -> str:
    start = fmt_date(job.get("start_date"))
    end = fmt_date(job.get("end_date"))
    if start == "—" and end == "—":
        return "—"
    if end == "—":
        return start
    if start == "—":
        return end
    return f"{start} – {end}"


def _currency_value(value: object) -> str:
    if value in (None, ""):
        return "—"
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return _safe_value(value)


def _render_dialog_placeholder(message: str) -> None:
    st.markdown(
        f'<div class="ips-dialog-placeholder">{html.escape(message)}</div>',
        unsafe_allow_html=True,
    )


def render_job_detail_dialog(job: dict) -> None:
    """Professional Job Details modal body (opened via row selection)."""
    jn = _safe_value(job.get("job_number"))
    jname = _safe_value(job.get("job_name"))
    status = _safe_value(job.get("status"))
    customer = _safe_value(job.get("customer"))
    supervisor = _safe_value(job.get("supervisor"))
    estimate_no = _safe_value(job.get("estimate_number"))
    schedule = _schedule_summary(job)

    st.markdown(
        '<span class="ips-dialog-shell ips-modal-wide" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="ips-dialog-header">'
        f'<div class="ips-dialog-title-row">'
        f"<div>"
        f'<h2 class="ips-dialog-title">{html.escape(jn)}</h2>'
        f'<p class="ips-dialog-subtitle">{html.escape(jname)}</p>'
        f"</div>"
        f"<div>{_status_pill(status)}</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<span class="ips-dialog-actions" aria-hidden="true"></span>', unsafe_allow_html=True)
    act1, act2, act3, act4 = st.columns([1, 1, 1, 1], gap="small")
    with act1:
        st.button("View", key="jobs_modal_view")
    with act2:
        st.button("Edit", key="jobs_modal_edit")
    with act3:
        st.button("More", key="jobs_modal_more")
    with act4:
        if st.button("Close", key="jobs_modal_close"):
            _clear_jobs_detail_modal()
            st.rerun()

    st.markdown(
        f'<div class="ips-dialog-meta-grid">'
        f"{_dialog_meta_card('Customer', customer)}"
        f"{_dialog_meta_card('Supervisor', supervisor)}"
        f"{_dialog_meta_card('Estimate #', estimate_no)}"
        f"{_dialog_meta_card('Schedule', schedule)}"
        f"</div>",
        unsafe_allow_html=True,
    )

    (
        tab_overview,
        tab_scope,
        tab_financials,
        tab_schedule,
        tab_documents,
        tab_photos,
        tab_daily,
        tab_notes,
        tab_activity,
    ) = st.tabs(_JOB_TABS)

    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{_detail_field('Job Number', jn)}"
            f"{_detail_field('Project', jname)}"
            f"{_detail_field('Customer', customer)}"
            f'{_detail_field("Status", status, html_value=_status_pill(status))}'
            f"{_detail_field('Supervisor', supervisor)}"
            f"{_detail_field('Project Manager', job.get('project_manager'))}"
            f"{_detail_field('Location', job.get('location'))}"
            f"{_detail_field('Estimate #', estimate_no)}"
            f"</div>"
        )
        st.markdown(_dialog_card("Overview", overview_html), unsafe_allow_html=True)

        jid = str(job.get("id") or "")
        if jid and not is_demo_id(jid):
            with st.expander("Edit job", expanded=False):
                ec1, ec2 = st.columns(2)
                with ec1:
                    st.text_input("Job number", value=str(job.get("job_number") or ""), key=f"job_edit_num_{jid}")
                    st.text_input("Job name", value=str(job.get("job_name") or ""), key=f"job_edit_name_{jid}")
                    cust_opts = customer_filter_options(include_names={str(job.get("customer") or "")})
                    cur_cust = str(job.get("customer") or "")
                    cust_idx = cust_opts.index(cur_cust) if cur_cust in cust_opts else 0
                    st.selectbox(
                        "Customer",
                        cust_opts,
                        index=cust_idx,
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

    with tab_scope:
        scope_text = _safe_value(job.get("scope") or job.get("description"), "No scope defined.")
        scope_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(scope_text)}"
            f"</p>"
        )
        st.markdown(_dialog_card("Scope of Work", scope_html), unsafe_allow_html=True)

    with tab_financials:
        fin_html = (
            f'<div class="ips-detail-grid">'
            f"{_detail_field('Labor Total', _currency_value(job.get('labor_total')))}"
            f"{_detail_field('Material Total', _currency_value(job.get('material_total')))}"
            f"{_detail_field('Equipment Total', _currency_value(job.get('equipment_total')))}"
            f"{_detail_field('Total', _currency_value(job.get('total') or job.get('awarded_amount')))}"
            f"</div>"
        )
        st.markdown(_dialog_card("Financial Summary", fin_html), unsafe_allow_html=True)

    with tab_schedule:
        sched_html = (
            f'<div class="ips-detail-grid">'
            f"{_detail_field('Start Date', fmt_date(job.get('start_date')))}"
            f"{_detail_field('End Date', fmt_date(job.get('end_date')))}"
            f"{_detail_field('Location', job.get('location'))}"
            f"</div>"
        )
        st.markdown(_dialog_card("Schedule", sched_html), unsafe_allow_html=True)

    with tab_documents:
        _render_dialog_placeholder("Job documents will appear here when connected to Supabase.")

    with tab_photos:
        _render_dialog_placeholder("Job photos will appear here when connected to Supabase.")

    with tab_daily:
        _render_dialog_placeholder("Daily field updates will appear here when connected to Supabase.")

    with tab_notes:
        notes_text = _safe_value(job.get("notes") or job.get("description"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(_dialog_card("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        _render_dialog_placeholder("Job activity history will appear here when connected to Supabase.")


@st.dialog("Job Details", width="large", on_dismiss=_clear_jobs_detail_modal)
def _show_jobs_detail_modal() -> None:
    sel = str(st.session_state.get(_JOBS_MODAL_KEY) or st.session_state.get(_SEL) or "").strip()
    jobs_by_id = st.session_state.get("_ips_jobs_modal_by_id")
    job = jobs_by_id.get(sel) if isinstance(jobs_by_id, dict) and sel else None
    if not job:
        st.warning("That job could not be loaded.")
        if st.button("Close", key="jobs_modal_missing_close"):
            _clear_jobs_detail_modal()
            st.rerun()
        return

    render_job_detail_dialog(job)


def _jobs_display_cell(field: str, row: dict) -> str:
    if field in ("start_date", "end_date"):
        return fmt_date(row.get(field))
    val = row.get(field)
    return str(val).strip() if val is not None and str(val).strip() else "—"


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("jobs"):
        return
    st.markdown(
        '<span class="ips-jobs-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    inject_jobs_module_css()
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
                value=_default_jobs_date_range(),
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

    st.caption(f"{len(filtered)} job(s)")

    st.session_state["_ips_jobs_modal_by_id"] = {
        str(job.get("id") or "").strip(): job
        for job in filtered
        if str(job.get("id") or "").strip()
    }

    render_clickable_table(
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
        format_cell=_jobs_display_cell,
        click_caption="Click a row to open details.",
        on_row_selected=_open_jobs_detail_modal,
    )

    _show_jobs_detail_modal_if_pending()
