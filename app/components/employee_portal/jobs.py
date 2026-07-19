"""Employee Portal jobs and bids directories."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlencode

import streamlit as st

from app.components.table_pagination import (
    page_key,
    page_size_key,
    render_table_pagination_footer,
    render_table_pagination_header,
)
from app.components.tabs import render_tabs
from app.services.employee_portal_detail_service import (
    get_employee_portal_bid_detail,
    get_employee_portal_job_detail,
)
from app.services.employee_portal_service import (
    EmployeePortalContext,
    list_active_jobs_for_employee_page,
    list_bidding_estimates_for_employee_page,
)
from app.ui.streamlit_perf import fragment, fragment_rerun, ips_app_rerun
from app.utils.formatting import fmt_date

_NAV_QUERY = "ips_nav"
_JOB_QUERY = "portal_job"
_BID_QUERY = "portal_bid"
_JOBS_TABLE_KEY = "employee_portal_active_jobs"
_BIDS_TABLE_KEY = "employee_portal_bids"
_JOBS_TAB_KEY = "ips_ep_jobs_tab"
_SHOW_ALL_JOBS_KEY = "ips_ep_show_all_jobs"
_JOBS_SEARCH_KEY = "ips_ep_jobs_search"
_BIDS_SEARCH_KEY = "ips_ep_bids_search"


def portal_job_query_key() -> str:
    return _JOB_QUERY


def portal_bid_query_key() -> str:
    return _BID_QUERY


def portal_job_href(job_id: str) -> str:
    return "?" + urlencode({_NAV_QUERY: "employee_portal", _JOB_QUERY: str(job_id or "").strip()})


def portal_bid_href(estimate_id: str) -> str:
    return "?" + urlencode({_NAV_QUERY: "employee_portal", _BID_QUERY: str(estimate_id or "").strip()})


def _status_pill(label: str, tone: str = "neutral") -> str:
    text = html.escape(str(label or "—"))
    return f'<span class="ips-ep-status ips-ep-status-{tone}">{text}</span>'


def _job_row_html(row: dict[str, Any], *, href: str, assigned: bool = False) -> str:
    title = html.escape(str(row.get("job_name") or row.get("project_name") or "—"))
    customer = html.escape(str(row.get("customer") or "—"))
    location = html.escape(str(row.get("location") or row.get("location_name") or "—"))
    status = html.escape(str(row.get("status") or "—"))
    supervisor = html.escape(str(row.get("supervisor") or row.get("created_by") or "—"))
    start = fmt_date(str(row.get("start_date") or row.get("estimate_date") or "")[:10])
    end_raw = str(row.get("end_date") or row.get("expiration_date") or "")[:10]
    end = fmt_date(end_raw) if end_raw else "—"
    assigned_badge = _status_pill("Assigned", "info") if assigned else ""
    link = html.escape(href, quote=True)
    return f"""
<div class="ips-ep-list-row">
  <div class="ips-ep-list-main">
    <strong><a class="ips-ep-open-link" href="{link}" target="_self">{title}</a></strong>
    <span>{customer}</span>
    <span>{location}</span>
  </div>
  <div class="ips-ep-list-meta">
    {assigned_badge}
    {_status_pill(status, "info")}
    <span>Supervisor: {supervisor}</span>
    <span>{html.escape(start or "—")} → {html.escape(end)}</span>
  </div>
</div>
"""


def build_job_list_html(rows: list[dict[str, Any]], *, assigned_field: str = "_portal_assigned") -> str:
    return "".join(
        _job_row_html(
            row,
            href=portal_job_href(str(row.get("id") or "")),
            assigned=bool(row.get(assigned_field)),
        )
        for row in rows
    )


def build_bid_list_html(rows: list[dict[str, Any]]) -> str:
    return "".join(
        _job_row_html(row, href=portal_bid_href(str(row.get("id") or "")))
        for row in rows
    )


@fragment
def render_recent_jobs_section(ctx: EmployeePortalContext, jobs: list[dict[str, Any]]) -> None:
    from app.perf_debug import perf_span

    st.markdown('<h3 class="ips-ep-section-title">Recent Jobs</h3>', unsafe_allow_html=True)
    if not jobs:
        st.markdown('<p class="ips-ep-empty">No jobs to show right now.</p>', unsafe_allow_html=True)
    else:
        with perf_span("employee_portal.cards_html"):
            st.markdown(build_job_list_html(jobs), unsafe_allow_html=True)
    if st.button("View All Jobs", key="ep_view_all_jobs", use_container_width=True, type="primary"):
        st.session_state[_SHOW_ALL_JOBS_KEY] = True
        st.query_params["portal_view"] = "jobs"
        ips_app_rerun()


def render_job_detail_panel(job: dict[str, Any] | None) -> None:
    if not job:
        st.error("This job is not available.")
    else:
        st.markdown(f"### {html.escape(str(job.get('job_name') or job.get('project_name') or 'Job'))}")
        st.markdown(f"**Customer:** {html.escape(str(job.get('customer') or '—'))}")
        st.markdown(f"**Location:** {html.escape(str(job.get('location') or job.get('location_name') or '—'))}")
        st.markdown(f"**Status:** {html.escape(str(job.get('status') or '—'))}")
        st.markdown(f"**Supervisor:** {html.escape(str(job.get('supervisor') or job.get('created_by') or '—'))}")
        start_raw = str(job.get("start_date") or job.get("estimate_date") or "")[:10]
        end_raw = str(job.get("end_date") or job.get("expiration_date") or "")[:10]
        st.markdown(f"**Start:** {fmt_date(start_raw) or '—'}")
        st.markdown(f"**End:** {fmt_date(end_raw) or '—'}")
        notes = str(job.get("description") or job.get("notes") or job.get("scope_of_work") or "").strip()
        if notes:
            st.markdown("**Scope**")
            st.markdown(notes)
    if st.button("← Back", key="ep_job_detail_back", use_container_width=True):
        for key in (_JOB_QUERY, _BID_QUERY):
            if key in st.query_params:
                del st.query_params[key]
        fragment_rerun()


def render_bid_detail_panel(bid: dict[str, Any] | None) -> None:
    if not bid:
        st.error("This bid is not available.")
    else:
        st.markdown(f"### {html.escape(str(bid.get('project_name') or 'Bid'))}")
        st.markdown(f"**Customer:** {html.escape(str(bid.get('customer') or '—'))}")
        st.markdown(f"**Location:** {html.escape(str(bid.get('location') or '—'))}")
        st.markdown(f"**Status:** {html.escape(str(bid.get('status') or '—'))}")
        st.markdown(f"**Due:** {fmt_date(str(bid.get('expiration_date') or '')[:10]) or '—'}")
        st.markdown(f"**Estimator:** {html.escape(str(bid.get('created_by') or '—'))}")
        desc = str(bid.get("description") or bid.get("scope_of_work") or "").strip()
        if desc:
            st.markdown("**Scope**")
            st.markdown(desc)
    if st.button("← Back", key="ep_bid_detail_back", use_container_width=True):
        for key in (_JOB_QUERY, _BID_QUERY):
            if key in st.query_params:
                del st.query_params[key]
        fragment_rerun()


def capture_portal_job_query(ctx: EmployeePortalContext) -> dict[str, Any] | None:
    jid = str(st.query_params.get(_JOB_QUERY) or "").strip()
    if not jid:
        return None
    from app.perf_debug import perf_span

    with perf_span("employee_portal.job_detail"):
        detail = get_employee_portal_job_detail(jid, employee_id=ctx.employee_id, role=ctx.role)
    if _JOB_QUERY in st.query_params:
        del st.query_params[_JOB_QUERY]
    return detail


def capture_portal_bid_query(ctx: EmployeePortalContext) -> dict[str, Any] | None:
    eid = str(st.query_params.get(_BID_QUERY) or "").strip()
    if not eid:
        return None
    from app.perf_debug import perf_span

    with perf_span("employee_portal.bid_detail"):
        detail = get_employee_portal_bid_detail(eid, employee_id=ctx.employee_id, role=ctx.role)
    if _BID_QUERY in st.query_params:
        del st.query_params[_BID_QUERY]
    return detail


@fragment
def render_all_jobs_view(ctx: EmployeePortalContext) -> None:
    if st.button("← Back to Dashboard", key="ep_back_dashboard", use_container_width=True):
        st.session_state.pop(_SHOW_ALL_JOBS_KEY, None)
        if "portal_view" in st.query_params:
            del st.query_params["portal_view"]
        ips_app_rerun()

    active_tab = render_tabs(
        ["Active Jobs", "Jobs We Are Bidding"],
        session_key=_JOBS_TAB_KEY,
        default="Active Jobs",
    )

    if active_tab == "Active Jobs":
        search = str(st.session_state.get(_JOBS_SEARCH_KEY) or "").strip()
        st.text_input("Search jobs", key=_JOBS_SEARCH_KEY, placeholder="Job, customer, location…")
        page = max(1, int(st.session_state.get(page_key(_JOBS_TABLE_KEY), 1)))
        page_size = max(10, min(100, int(st.session_state.get(page_size_key(_JOBS_TABLE_KEY), 25))))
        directory = list_active_jobs_for_employee_page(
            employee_id=ctx.employee_id,
            role=ctx.role,
            search=search,
            page=page,
            page_size=page_size,
        )
        page, page_size, _ = render_table_pagination_header(
            directory.total_count,
            _JOBS_TABLE_KEY,
            default_page_size=25,
            item_label="job",
        )
        if page != directory.page:
            directory = list_active_jobs_for_employee_page(
                employee_id=ctx.employee_id,
                role=ctx.role,
                search=search,
                page=page,
                page_size=page_size,
            )
        st.markdown('<h3 class="ips-ep-section-title">Active Jobs</h3>', unsafe_allow_html=True)
        if not directory.rows:
            st.markdown('<p class="ips-ep-empty">No active jobs to show.</p>', unsafe_allow_html=True)
        else:
            st.markdown(build_job_list_html(directory.rows, assigned_field="_portal_assigned"), unsafe_allow_html=True)
        render_table_pagination_footer(directory.total_count, _JOBS_TABLE_KEY)
    else:
        search = str(st.session_state.get(_BIDS_SEARCH_KEY) or "").strip()
        st.text_input("Search bids", key=_BIDS_SEARCH_KEY, placeholder="Project, customer, status…")
        page = max(1, int(st.session_state.get(page_key(_BIDS_TABLE_KEY), 1)))
        page_size = max(10, min(100, int(st.session_state.get(page_size_key(_BIDS_TABLE_KEY), 25))))
        directory = list_bidding_estimates_for_employee_page(
            employee_id=ctx.employee_id,
            role=ctx.role,
            search=search,
            page=page,
            page_size=page_size,
        )
        page, page_size, _ = render_table_pagination_header(
            directory.total_count,
            _BIDS_TABLE_KEY,
            default_page_size=25,
            item_label="bid",
        )
        if page != directory.page:
            directory = list_bidding_estimates_for_employee_page(
                employee_id=ctx.employee_id,
                role=ctx.role,
                search=search,
                page=page,
                page_size=page_size,
            )
        st.markdown('<h3 class="ips-ep-section-title">Jobs We Are Bidding</h3>', unsafe_allow_html=True)
        if not directory.rows:
            st.markdown('<p class="ips-ep-empty">No open bids right now.</p>', unsafe_allow_html=True)
        else:
            st.markdown(build_bid_list_html(directory.rows), unsafe_allow_html=True)
        render_table_pagination_footer(directory.total_count, _BIDS_TABLE_KEY)
