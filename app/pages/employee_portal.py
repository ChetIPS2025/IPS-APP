"""IPS Employee Portal — mobile-first workforce home."""

from __future__ import annotations

import html
from datetime import date
from typing import Any

import streamlit as st

from app.auth import current_profile, effective_role
from app.components.company_updates_feed import (
    _mark_dashboard_update_read,
    _is_update_unread,
)
from app.navigation import set_nav_slug
from app.pages._core._access import begin_module
from app.components.scheduling_portal import render_employee_upcoming_schedule
from app.pages._core._data import load_jobs
from app.services.certification_attachments_service import cert_has_attachment
from app.services.certification_helpers import cert_status_pill_html, resolve_logged_in_employee_id
from app.services.employee_portal_service import (
    list_active_jobs_for_employee,
    list_bidding_estimates_for_employee,
    list_employee_portal_updates,
    list_my_certifications_for_portal,
    list_portal_dashboard_jobs,
    portal_employee_avatar_html,
    portal_employee_title,
    portal_greeting_name,
    portal_greeting_period,
)
from app.services.employees_service import get_certification_attachment_url
from app.styles import inject_employee_portal_css
from app.utils.formatting import fmt_date
from app.utils.permissions import role_can_access_page
_PORTAL_UPDATE_KEY = "ips_portal_selected_update"
_PORTAL_JOB_KEY = "ips_portal_selected_job"
_PORTAL_BID_KEY = "ips_portal_selected_bid"
_SHOW_ALL_JOBS_KEY = "ips_ep_show_all_jobs"


def _quick_actions_view_mode() -> str:
    from app.utils.view_as import is_view_as_active, view_as_mode
    if is_view_as_active():
        return f"preview_{view_as_mode()}"
    return "employee"


def _quick_action_button_key(action_id: str, *, employee_id: str, view_mode: str) -> str:
    eid = str(employee_id or "none").strip() or "none"
    return f"ep_quick_{action_id}_{view_mode}_{eid}"


def build_employee_portal_quick_actions(role: str) -> list[dict[str, object]]:
    """Quick-action definitions; ``action_id`` is unique per button (nav slug may repeat)."""
    upload_slug = "scan_asset" if role_can_access_page(role, "scan_asset") else "employee_qr_scan"
    return [
        {
            "icon": "📷",
            "label": "Scan QR Code",
            "nav_slug": "employee_qr_scan",
            "enabled": True,
            "action_id": "qr_scan",
            "primary": True,
        },
        {
            "icon": "💼",
            "label": "My Jobs",
            "nav_slug": "__my_jobs__",
            "enabled": True,
            "action_id": "my_jobs",
            "primary": False,
        },
        {
            "icon": "⏱",
            "label": "Timekeeping",
            "nav_slug": "timekeeping",
            "enabled": role_can_access_page(role, "timekeeping"),
            "action_id": "timekeeping",
            "primary": False,
        },
        {
            "icon": "📸",
            "label": "Upload Photo",
            "nav_slug": upload_slug,
            "enabled": True,
            "action_id": "upload_photo",
            "primary": False,
        },
        {
            "icon": "📄",
            "label": "Documents",
            "nav_slug": "employee_resources",
            "enabled": role_can_access_page(role, "employee_resources"),
            "action_id": "documents",
            "primary": False,
        },
    ]


def _status_pill(label: str, tone: str = "neutral") -> str:
    text = html.escape(str(label or "—"))
    return f'<span class="ips-ep-status ips-ep-status-{tone}">{text}</span>'


def _render_welcome_card(
    profile: dict[str, Any],
    employee: dict[str, Any] | None,
    role: str,
) -> None:
    name = portal_greeting_name(profile)
    period = portal_greeting_period()
    today = fmt_date(date.today().isoformat())
    title = html.escape(portal_employee_title(profile, employee, role=role))
    role_label = html.escape(str(role or "Employee").replace("_", " ").title())
    avatar_html = portal_employee_avatar_html(profile, employee)
    st.markdown(
        f"""
<div class="ips-ep-welcome-card">
  <div class="ips-ep-welcome-top">
    {avatar_html}
    <div class="ips-ep-welcome-text">
      <p class="ips-ep-greeting">{html.escape(period)}, {html.escape(name)}</p>
      <p class="ips-ep-date">{html.escape(today)}</p>
      <p class="ips-ep-role">{title}</p>
      <p class="ips-ep-role-sub">{role_label}</p>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_quick_actions(role: str, *, employee_id: str = "") -> None:
    st.markdown('<h3 class="ips-ep-section-title">Quick Actions</h3>', unsafe_allow_html=True)
    view_mode = _quick_actions_view_mode()
    actions = [a for a in build_employee_portal_quick_actions(role) if a.get("enabled")]
    if not actions:
        return

    cols = st.columns(min(len(actions), 3))
    for idx, action in enumerate(actions):
        icon = str(action.get("icon") or "")
        label = str(action.get("label") or "")
        slug = str(action.get("nav_slug") or "")
        action_id = str(action.get("action_id") or f"action_{idx}")
        with cols[idx % len(cols)]:
            if st.button(
                f"{icon}  {label}",
                key=_quick_action_button_key(
                    action_id,
                    employee_id=employee_id,
                    view_mode=view_mode,
                ),
                use_container_width=True,
                type="primary" if action.get("primary") else "secondary",
            ):
                if slug == "__my_jobs__":
                    st.session_state[_SHOW_ALL_JOBS_KEY] = True
                else:
                    set_nav_slug(slug)
                st.rerun()


def _render_updates_section(role: str) -> None:
    st.markdown('<h3 class="ips-ep-section-title">Company Updates</h3>', unsafe_allow_html=True)
    updates = list_employee_portal_updates(role=role)
    if not updates:
        st.markdown('<p class="ips-ep-empty">No company updates right now.</p>', unsafe_allow_html=True)
        return

    selected = st.session_state.get(_PORTAL_UPDATE_KEY)
    for row in updates[:8]:
        uid = str(row.get("id") or "")
        unread = _is_update_unread(row)
        badge = _status_pill("New", "warn") if unread else _status_pill("Read", "neutral")
        title = html.escape(str(row.get("title") or "Untitled"))
        snippet = html.escape(str(row.get("body") or "")[:140])
        posted = html.escape(fmt_date(str(row.get("date") or row.get("created_at") or "")[:10]))
        st.markdown(
            f"""
<div class="ips-ep-card ips-ep-update-card">
  <div class="ips-ep-card-head">
    <strong>{title}</strong>
    {badge}
  </div>
  <p class="ips-ep-muted">{snippet}</p>
  <p class="ips-ep-meta">{posted}</p>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button(f"Open — {row.get('title', 'Update')}", key=f"ep_upd_{uid}", use_container_width=True):
            st.session_state[_PORTAL_UPDATE_KEY] = uid
            _mark_dashboard_update_read(uid)
            st.rerun()

    if selected:
        detail = next((u for u in updates if str(u.get("id")) == str(selected)), None)
        if detail:
            with st.expander(str(detail.get("title") or "Update"), expanded=True):
                st.markdown(str(detail.get("body") or ""))
                if st.button("Close update", key="ep_upd_close"):
                    st.session_state.pop(_PORTAL_UPDATE_KEY, None)
                    st.rerun()


def _render_certifications_section(employee_id: str) -> None:
    st.markdown('<h3 class="ips-ep-section-title">My Certifications</h3>', unsafe_allow_html=True)
    certs = list_my_certifications_for_portal(employee_id)
    if not certs:
        st.markdown('<p class="ips-ep-empty">No certifications on file.</p>', unsafe_allow_html=True)
        return

    for cert in certs:
        cid = str(cert.get("id") or cert.get("cert_type") or "")
        name = str(cert.get("cert_type") or cert.get("certification_type") or "Certification")
        exp = fmt_date(str(cert.get("expiration_date") or "")[:10]) if cert.get("expiration_date") else "No expiration"
        status = str(cert.get("status") or "Active")
        st.markdown(
            f"""
<div class="ips-ep-card ips-ep-cert-card">
  <div class="ips-ep-card-head"><strong>{html.escape(name)}</strong>{cert_status_pill_html(status)}</div>
  <p class="ips-ep-meta">Expires: {html.escape(exp)}</p>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button(f"Open {name}", key=f"ep_cert_{cid}", use_container_width=True):
            if cert_has_attachment(cert):
                url = get_certification_attachment_url(cert)
                if url:
                    st.link_button("Open certificate document", url, use_container_width=True)
                else:
                    st.info("Could not open the attached document right now.")
            else:
                st.info("No document is attached to this certification yet.")


def _compact_job_row(
    row: dict[str, Any],
    *,
    prefix: str,
    session_key: str,
    assigned: bool = False,
) -> None:
    rid = str(row.get("id") or "")
    title = html.escape(str(row.get("job_name") or row.get("project_name") or "—"))
    customer = html.escape(str(row.get("customer") or "—"))
    location = html.escape(str(row.get("location") or row.get("location_name") or "—"))
    status = html.escape(str(row.get("status") or "—"))
    supervisor = html.escape(str(row.get("supervisor") or row.get("created_by") or "—"))
    start = fmt_date(str(row.get("start_date") or row.get("estimate_date") or "")[:10])
    end_raw = str(row.get("end_date") or row.get("expiration_date") or "")[:10]
    end = fmt_date(end_raw) if end_raw else "—"
    assigned_badge = _status_pill("Assigned", "info") if assigned else ""
    st.markdown(
        f"""
<div class="ips-ep-list-row">
  <div class="ips-ep-list-main">
    <strong>{title}</strong>
    <span>{customer}</span>
    <span>{location}</span>
  </div>
  <div class="ips-ep-list-meta">
    {assigned_badge}
    {_status_pill(status, "info")}
    <span>Supervisor: {supervisor}</span>
    <span>{start} → {html.escape(end)}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    if st.button(f"Details › {title[:40]}", key=f"{prefix}_{rid}", use_container_width=True):
        st.session_state[session_key] = rid
        st.rerun()


def _render_job_detail(job: dict[str, Any], *, close_key: str, session_key: str) -> None:
    with st.expander(str(job.get("job_name") or job.get("project_name") or "Job"), expanded=True):
        st.markdown(f"**Customer:** {job.get('customer', '—')}")
        st.markdown(f"**Location:** {job.get('location') or job.get('location_name') or '—'}")
        st.markdown(f"**Status:** {job.get('status', '—')}")
        st.markdown(f"**Supervisor:** {job.get('supervisor') or job.get('created_by') or '—'}")
        start_raw = str(job.get("start_date") or job.get("estimate_date") or "")[:10]
        end_raw = str(job.get("end_date") or job.get("expiration_date") or "")[:10]
        st.markdown(f"**Start:** {fmt_date(start_raw) or '—'}")
        st.markdown(f"**End:** {fmt_date(end_raw) or '—'}")
        notes = str(job.get("description") or job.get("notes") or job.get("scope_of_work") or "").strip()
        if notes:
            st.markdown("**Scope**")
            st.markdown(notes)
        if st.button("Close job", key=close_key):
            st.session_state.pop(session_key, None)
            st.rerun()


def _render_recent_jobs_section(employee_id: str) -> None:
    st.markdown('<h3 class="ips-ep-section-title">Recent Jobs</h3>', unsafe_allow_html=True)
    jobs = list_portal_dashboard_jobs(employee_id, limit=4)
    if not jobs:
        st.markdown('<p class="ips-ep-empty">No jobs to show right now.</p>', unsafe_allow_html=True)
    else:
        for job in jobs:
            _compact_job_row(
                job,
                prefix="ep_job",
                session_key=_PORTAL_JOB_KEY,
                assigned=bool(job.get("_portal_assigned")),
            )
        selected = st.session_state.get(_PORTAL_JOB_KEY)
        if selected:
            detail = next((j for j in jobs if str(j.get("id")) == str(selected)), None)
            if detail:
                _render_job_detail(detail, close_key="ep_job_close", session_key=_PORTAL_JOB_KEY)

    if st.button("View All Jobs", key="ep_view_all_jobs", use_container_width=True, type="primary"):
        st.session_state[_SHOW_ALL_JOBS_KEY] = True
        st.rerun()


def _render_all_jobs_section() -> None:
    if st.button("← Back to Dashboard", key="ep_back_dashboard", use_container_width=True):
        st.session_state.pop(_SHOW_ALL_JOBS_KEY, None)
        st.session_state.pop(_PORTAL_JOB_KEY, None)
        st.session_state.pop(_PORTAL_BID_KEY, None)
        st.rerun()

    st.markdown('<h3 class="ips-ep-section-title">Active Jobs</h3>', unsafe_allow_html=True)
    jobs = list_active_jobs_for_employee()
    if not jobs:
        st.markdown('<p class="ips-ep-empty">No active jobs to show.</p>', unsafe_allow_html=True)
    else:
        for job in jobs:
            _compact_job_row(job, prefix="ep_job_all", session_key=_PORTAL_JOB_KEY)
        selected = st.session_state.get(_PORTAL_JOB_KEY)
        if selected:
            detail = next((j for j in jobs if str(j.get("id")) == str(selected)), None)
            if detail:
                _render_job_detail(detail, close_key="ep_job_close", session_key=_PORTAL_JOB_KEY)

    st.markdown('<h3 class="ips-ep-section-title">Jobs We Are Bidding</h3>', unsafe_allow_html=True)
    bids = list_bidding_estimates_for_employee()
    if not bids:
        st.markdown('<p class="ips-ep-empty">No open bids right now.</p>', unsafe_allow_html=True)
    else:
        for est in bids:
            _compact_job_row(est, prefix="ep_bid", session_key=_PORTAL_BID_KEY)
        selected_bid = st.session_state.get(_PORTAL_BID_KEY)
        if selected_bid:
            detail = next((e for e in bids if str(e.get("id")) == str(selected_bid)), None)
            if detail:
                with st.expander(str(detail.get("project_name") or "Bid"), expanded=True):
                    st.markdown(f"**Customer:** {detail.get('customer', '—')}")
                    st.markdown(f"**Location:** {detail.get('location') or '—'}")
                    st.markdown(f"**Status:** {detail.get('status', '—')}")
                    st.markdown(f"**Due:** {fmt_date(str(detail.get('expiration_date') or '')[:10]) or '—'}")
                    st.markdown(f"**Estimator:** {detail.get('created_by', '—')}")
                    desc = str(detail.get("description") or detail.get("scope_of_work") or "").strip()
                    if desc:
                        st.markdown("**Scope**")
                        st.markdown(desc)
                    if st.button("Close bid", key="ep_bid_close"):
                        st.session_state.pop(_PORTAL_BID_KEY, None)
                        st.rerun()


def render() -> None:
    if not begin_module("employee_portal"):
        return
    inject_employee_portal_css()
    st.markdown(
        '<span class="ips-employee-portal-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    profile = current_profile() or {}
    role = effective_role()
    employee_id = resolve_logged_in_employee_id(profile)
    employee = get_employee(employee_id) if employee_id else None
    show_all_jobs = bool(st.session_state.get(_SHOW_ALL_JOBS_KEY))

    _render_welcome_card(profile, employee, role)
    if not show_all_jobs:
        _render_quick_actions(role, employee_id=employee_id)
        _render_updates_section(role)
        if employee_id:
            jobs_by_id = {
                str(j.get("id") or "").strip(): j
                for j in load_jobs()
                if str(j.get("id") or "").strip()
            }
            employees_by_id = {employee_id: employee} if employee else {}
            render_employee_upcoming_schedule(
                employee_id,
                employees_by_id=employees_by_id,
                jobs_by_id=jobs_by_id,
            )
        _render_certifications_section(employee_id)
        _render_recent_jobs_section(employee_id)
    else:
        _render_all_jobs_section()
