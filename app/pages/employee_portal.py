"""IPS Employee Portal — mobile-first workforce home."""

from __future__ import annotations

import streamlit as st

from app.auth import current_profile, effective_role
from app.components.employee_portal.certifications import (
    capture_portal_certificate_query,
    render_certifications_section,
)
from app.components.employee_portal.jobs import (
    capture_portal_bid_query,
    capture_portal_job_query,
    render_all_jobs_view,
    render_bid_detail_panel,
    render_job_detail_panel,
    render_recent_jobs_section,
)
from app.components.employee_portal.quick_actions import (
    quick_action_button_key,
    render_quick_actions,
)
from app.components.employee_portal.schedule import render_schedule_section
from app.components.employee_portal.updates import (
    capture_portal_update_query,
    render_update_detail_panel,
    render_updates_section,
)
from app.components.employee_portal.welcome import render_welcome_card
from app.pages._core._access import begin_module
from app.services.certification_helpers import resolve_logged_in_employee_id
from app.services.employee_portal_service import (
    build_employee_portal_context,
    load_employee_portal_snapshot,
)
from app.services.employees_service import get_employee
from app.styles import inject_employee_portal_css
from app.ui.streamlit_perf import fragment

_SHOW_ALL_JOBS_KEY = "ips_ep_show_all_jobs"
_PORTAL_VIEW_QUERY = "portal_view"
_DETAIL_QUERY_KEYS = ("portal_update", "portal_job", "portal_bid", "portal_certificate")


def _quick_actions_view_mode() -> str:
    from app.utils.view_as import is_view_as_active, view_as_mode

    if is_view_as_active():
        return f"preview_{view_as_mode()}"
    return "employee"


def _quick_action_button_key(action_id: str, *, employee_id: str, view_mode: str) -> str:
    return quick_action_button_key(action_id, employee_id=employee_id, view_mode=view_mode)


def build_employee_portal_quick_actions(role: str) -> list[dict[str, object]]:
    from app.utils.permissions import role_can_access_page

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


def _portal_view_is_jobs() -> bool:
    if str(st.query_params.get(_PORTAL_VIEW_QUERY) or "").strip().lower() == "jobs":
        return True
    return bool(st.session_state.get(_SHOW_ALL_JOBS_KEY))


def _active_detail_query() -> str | None:
    for key in _DETAIL_QUERY_KEYS:
        if str(st.query_params.get(key) or "").strip():
            return key
    return None


@fragment
def _render_dashboard_sections(ctx, snapshot) -> None:
    render_quick_actions(ctx)
    for warning in snapshot.warnings:
        st.warning(warning)
    render_updates_section(ctx, snapshot.updates)
    if ctx.employee_id:
        render_schedule_section(snapshot.upcoming_schedule)
        render_certifications_section(ctx, snapshot.certifications)
        render_recent_jobs_section(ctx, snapshot.recent_jobs)


def render() -> None:
    from app.perf_debug import perf_span

    if not begin_module("employee_portal"):
        return

    with perf_span("employee_portal.page_shell"):
        inject_employee_portal_css()
        st.markdown(
            '<span class="ips-employee-portal-page ips-page-shell-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        with perf_span("employee_portal.context"):
            profile = current_profile() or {}
            role = effective_role()
            employee_id = resolve_logged_in_employee_id(profile)
            employee = get_employee(employee_id) if employee_id else None
            ctx = build_employee_portal_context(
                profile,
                role=role,
                employee_id=employee_id,
                employee=employee,
            )

        render_welcome_card(ctx)

        detail_key = _active_detail_query()
        if detail_key == "portal_update":
            render_update_detail_panel(capture_portal_update_query(ctx))
            return
        if detail_key == "portal_job":
            render_job_detail_panel(capture_portal_job_query(ctx))
            return
        if detail_key == "portal_bid":
            render_bid_detail_panel(capture_portal_bid_query(ctx))
            return
        if detail_key == "portal_certificate":
            capture_portal_certificate_query(ctx)
            return

        if _portal_view_is_jobs():
            render_all_jobs_view(ctx)
            return

        with perf_span("employee_portal.snapshot"):
            snapshot = load_employee_portal_snapshot(
                employee_id=ctx.employee_id,
                role=ctx.role,
                user_id=ctx.user_id,
            )
        _render_dashboard_sections(ctx, snapshot)


__all__ = [
    "build_employee_portal_quick_actions",
    "render",
    "_quick_action_button_key",
    "_quick_actions_view_mode",
]
