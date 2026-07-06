"""IPS Employee Portal — mobile-first workforce home."""

from __future__ import annotations

import html
from datetime import date
from typing import Any

import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.components.company_updates_feed import (
        _mark_dashboard_update_read,
        _is_update_unread,
    )
    from app.config import ROOT_DIR
    from app.navigation import set_nav_slug
    from app.pages._core._access import begin_module
    from app.services.certification_attachments_service import cert_has_attachment
    from app.services.certification_helpers import cert_status_pill_html, resolve_logged_in_employee_id
    from app.services.employee_portal_service import (
        list_active_jobs_for_employee,
        list_bidding_estimates_for_employee,
        list_employee_portal_updates,
        list_my_certifications_for_portal,
        portal_greeting_name,
        portal_greeting_period,
    )
    from app.services.employees_service import get_certification_attachment_url
    from app.styles import inject_employee_portal_css, inject_global_css
    from app.utils.formatting import fmt_date
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from components.company_updates_feed import (  # type: ignore
        _mark_dashboard_update_read,
        _is_update_unread,
    )
    from config import ROOT_DIR  # type: ignore
    from navigation import set_nav_slug  # type: ignore
    from pages._core._access import begin_module  # type: ignore
    from services.certification_attachments_service import cert_has_attachment  # type: ignore
    from services.certification_helpers import cert_status_pill_html, resolve_logged_in_employee_id  # type: ignore
    from services.employee_portal_service import (  # type: ignore
        list_active_jobs_for_employee,
        list_bidding_estimates_for_employee,
        list_employee_portal_updates,
        list_my_certifications_for_portal,
        portal_greeting_name,
        portal_greeting_period,
    )
    from services.employees_service import get_certification_attachment_url  # type: ignore
    from styles import inject_employee_portal_css, inject_global_css  # type: ignore
    from utils.formatting import fmt_date  # type: ignore

_PORTAL_UPDATE_KEY = "ips_portal_selected_update"
_PORTAL_JOB_KEY = "ips_portal_selected_job"
_PORTAL_BID_KEY = "ips_portal_selected_bid"


def _logo_path():
    for name in ("ips_logo_header.png", "IPS Icon.png", "company_logo.png", "ips_logo_round.png"):
        p = ROOT_DIR / "assets" / name
        if p.is_file():
            return p
    return None


def _status_pill(label: str, tone: str = "neutral") -> str:
    text = html.escape(str(label or "—"))
    return f'<span class="ips-ep-status ips-ep-status-{tone}">{text}</span>'


def _render_portal_header(profile: dict[str, Any], role: str) -> None:
    name = portal_greeting_name(profile)
    period = portal_greeting_period()
    today = fmt_date(date.today().isoformat())
    role_label = html.escape(str(role or "Employee").replace("_", " ").title())
    logo = _logo_path()
    logo_html = ""
    if logo:
        import base64

        b64 = base64.b64encode(logo.read_bytes()).decode("ascii")
        logo_html = (
            f'<img class="ips-ep-logo" src="data:image/png;base64,{b64}" alt="IPS logo" />'
        )
    st.markdown(
        f"""
<div class="ips-ep-header">
  <div class="ips-ep-header-top">
    {logo_html}
    <div class="ips-ep-header-text">
      <p class="ips-ep-greeting">{html.escape(period)}, {html.escape(name)}</p>
      <p class="ips-ep-date">{html.escape(today)}</p>
      <p class="ips-ep-role">{role_label}</p>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_qr_scan_button() -> None:
    if st.button("📷  Scan QR Code", key="ep_qr_scan_main", type="primary", use_container_width=True):
        set_nav_slug("employee_qr_scan")
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


def _compact_job_row(row: dict[str, Any], *, prefix: str, session_key: str) -> None:
    rid = str(row.get("id") or "")
    title = html.escape(str(row.get("job_name") or row.get("project_name") or "—"))
    customer = html.escape(str(row.get("customer") or "—"))
    location = html.escape(str(row.get("location") or row.get("location_name") or "—"))
    status = html.escape(str(row.get("status") or "—"))
    supervisor = html.escape(str(row.get("supervisor") or row.get("created_by") or "—"))
    start = fmt_date(str(row.get("start_date") or row.get("estimate_date") or "")[:10])
    end_raw = str(row.get("end_date") or row.get("expiration_date") or "")[:10]
    end = fmt_date(end_raw) if end_raw else "—"
    st.markdown(
        f"""
<div class="ips-ep-list-row">
  <div class="ips-ep-list-main">
    <strong>{title}</strong>
    <span>{customer}</span>
    <span>{location}</span>
  </div>
  <div class="ips-ep-list-meta">
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


def _render_active_jobs_section() -> None:
    st.markdown('<h3 class="ips-ep-section-title">Active Jobs</h3>', unsafe_allow_html=True)
    jobs = list_active_jobs_for_employee()
    if not jobs:
        st.markdown('<p class="ips-ep-empty">No active jobs to show.</p>', unsafe_allow_html=True)
        return
    for job in jobs[:12]:
        _compact_job_row(job, prefix="ep_job", session_key=_PORTAL_JOB_KEY)
    selected = st.session_state.get(_PORTAL_JOB_KEY)
    if selected:
        detail = next((j for j in jobs if str(j.get("id")) == str(selected)), None)
        if detail:
            with st.expander(str(detail.get("job_name") or "Job"), expanded=True):
                st.markdown(f"**Customer:** {detail.get('customer', '—')}")
                st.markdown(f"**Location:** {detail.get('location') or detail.get('location_name') or '—'}")
                st.markdown(f"**Status:** {detail.get('status', '—')}")
                st.markdown(f"**Supervisor:** {detail.get('supervisor', '—')}")
                st.markdown(f"**Start:** {fmt_date(str(detail.get('start_date') or '')[:10]) or '—'}")
                st.markdown(f"**End:** {fmt_date(str(detail.get('end_date') or '')[:10]) or '—'}")
                notes = str(detail.get("description") or detail.get("notes") or "").strip()
                if notes:
                    st.markdown("**Scope**")
                    st.markdown(notes)
                if st.button("Close job", key="ep_job_close"):
                    st.session_state.pop(_PORTAL_JOB_KEY, None)
                    st.rerun()


def _render_bidding_section() -> None:
    st.markdown('<h3 class="ips-ep-section-title">Jobs We Are Bidding</h3>', unsafe_allow_html=True)
    bids = list_bidding_estimates_for_employee()
    if not bids:
        st.markdown('<p class="ips-ep-empty">No open bids right now.</p>', unsafe_allow_html=True)
        return
    for est in bids[:12]:
        _compact_job_row(est, prefix="ep_bid", session_key=_PORTAL_BID_KEY)
    selected = st.session_state.get(_PORTAL_BID_KEY)
    if selected:
        detail = next((e for e in bids if str(e.get("id")) == str(selected)), None)
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


def _render_resources_preview() -> None:
    st.markdown('<h3 class="ips-ep-section-title">Employee Resources</h3>', unsafe_allow_html=True)
    if st.button("Open Employee Resources", key="ep_resources_link", use_container_width=True):
        set_nav_slug("employee_resources")
        st.rerun()


def render() -> None:
    if not begin_module("employee_portal"):
        return
    inject_global_css()
    inject_employee_portal_css()
    st.markdown(
        '<span class="ips-employee-portal-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    profile = current_profile() or {}
    role = current_role()
    employee_id = resolve_logged_in_employee_id(profile)

    _render_portal_header(profile, role)
    _render_qr_scan_button()
    _render_updates_section(role)
    _render_certifications_section(employee_id)
    _render_active_jobs_section()
    _render_bidding_section()
    _render_resources_preview()
