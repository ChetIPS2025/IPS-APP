"""Module registry for the unified IPS operations platform."""

from __future__ import annotations

import logging

import streamlit as st

from app.auth import current_role, effective_role
from app.pages import (
    admin,
    assets,
    company_updates,
    coupling_inspection,
    customers,
    dashboard,
    documents,
    employee_certifications,
    employee_documents,
    employee_portal,
    employee_profile,
    employee_qr_scan,
    employee_resources,
    employees,
    estimate_materials,
    pricing_guide,
    estimates,
    field_crew_time,
    field_daily_reports,
    field_dashboard,
    field_day,
    inventory,
    jobs,
    pipeline,
    rental_equipment,
    rental_equipment_inspection,
    reports,
    settings,
    tasks,
    timekeeping,
    weekly_timesheets,
)
from app.pages._core._session import clear_all_module_selections, nav_slug
from app.utils.constants import SESSION_NAV_KEY
from app.utils.permissions import role_can_access_page
BUILT_MODULES: dict[str, object] = {
    "dashboard": dashboard.render,
    "jobs": jobs.render,
    "pipeline": pipeline.render,
    "customers": customers.render,
    "estimates": estimates.render,
    "pricing_guide": pricing_guide.render,
    "estimate_materials": estimate_materials.render,
    "inventory": inventory.render,
    "assets": assets.render,
    "timekeeping": timekeeping.render,
    "weekly_timesheets": weekly_timesheets.render,
    "employees": employees.render,
    "users": employees.render,
    "employee_certifications": employee_certifications.render,
    "employee_documents": employee_documents.render,
    "employee_portal": employee_portal.render,
    "employee_profile": employee_profile.render,
    "employee_qr_scan": employee_qr_scan.render,
    "employee_resources": employee_resources.render,
    "company_updates": company_updates.render,
    "documents": documents.render,
    "tasks": tasks.render,
    "reports": reports.render,
    "admin": admin.render,
    "settings": settings.render,
    "field_dashboard": field_dashboard.render,
    "field_day": field_day.render,
    "field_daily_reports": field_daily_reports.render,
    "field_crew_time": field_crew_time.render,
    "coupling_inspection": coupling_inspection.render,
    "rental_equipment": rental_equipment.render,
    "rental_equipment_inspection": rental_equipment_inspection.render,
}


def ensure_nav_defaults() -> None:
    from app.utils.permissions import role_default_nav_slug
    default = role_default_nav_slug(
        effective_role(),
        field_mode=bool(st.session_state.get("ips_field_mode")),
    )
    st.session_state.setdefault(SESSION_NAV_KEY, default)


def on_nav_change(prev_slug: str, new_slug: str) -> None:
    if prev_slug != new_slug:
        clear_all_module_selections()


def render_module(slug: str | None = None) -> None:
    from app.navigation import normalize_nav_slug
    active = normalize_nav_slug(slug or nav_slug() or "dashboard")
    role = effective_role()
    if not role_can_access_page(role, active):
        from app.navigation import default_nav_slug, set_nav_slug
        fallback = default_nav_slug()
        if active != fallback and role_can_access_page(role, fallback):
            set_nav_slug(fallback)
            st.rerun()
            return
        st.error("You do not have access to this page.")
        return

    from app.pages._core._access import clear_demo_flag, end_module, show_demo_banner_if_needed
    clear_demo_flag()
    fn = BUILT_MODULES.get(active)
    if fn:
        try:
            from app.perf_debug import perf_span
            from app.auth import current_role
            from app.utils.permissions import normalize_role
            from app.utils.view_as import is_view_as_active, render_view_as_page_shell
            def _render_module() -> None:
                with perf_span(f"module.render:{active}"):
                    fn()  # type: ignore[operator]

            if normalize_role(current_role()) == "admin" and is_view_as_active():
                render_view_as_page_shell(_render_module)
            else:
                _render_module()
        except Exception as exc:
            st.error(f"This page encountered an error: {exc}")
            logging.getLogger(__name__).exception("module %s failed", active)
        finally:
            end_module()
        show_demo_banner_if_needed()
        return

    from app.components.headers import render_page_header
    st.markdown('<p class="ips-module-placeholder">Module not found.</p>', unsafe_allow_html=True)
