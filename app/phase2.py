"""Module registry for the unified IPS operations platform."""

from __future__ import annotations

import logging

import streamlit as st

try:
    from app.auth import current_role
    from app.pages import (
        admin,
        assets,
        company_updates,
        customers,
        dashboard,
        documents,
        employee_certifications,
        employee_documents,
        employees,
        estimate_materials,
        pricing_guide,
        estimates,
        inventory,
        job_costing,
        jobs,
        reports,
        settings,
        tasks,
        timekeeping,
    )
    from app.pages._core._session import clear_all_module_selections, nav_slug
    from app.utils.constants import SESSION_NAV_KEY
    from app.utils.permissions import role_can_access_page
except ImportError:
    from auth import current_role  # type: ignore
    from pages import (  # type: ignore
        admin,
        assets,
        company_updates,
        customers,
        dashboard,
        documents,
        employee_certifications,
        employee_documents,
        employees,
        estimate_materials,
        pricing_guide,
        estimates,
        inventory,
        job_costing,
        jobs,
        reports,
        settings,
        tasks,
        timekeeping,
    )
    from pages._core._session import clear_all_module_selections, nav_slug  # type: ignore
    from utils.constants import SESSION_NAV_KEY  # type: ignore
    from utils.permissions import role_can_access_page  # type: ignore

BUILT_MODULES: dict[str, object] = {
    "dashboard": dashboard.render,
    "jobs": jobs.render,
    "job_costing": job_costing.render,
    "customers": customers.render,
    "estimates": estimates.render,
    "pricing_guide": pricing_guide.render,
    "estimate_materials": estimate_materials.render,
    "inventory": inventory.render,
    "assets": assets.render,
    "timekeeping": timekeeping.render,
    "employees": employees.render,
    "users": employees.render,
    "employee_certifications": employee_certifications.render,
    "employee_documents": employee_documents.render,
    "company_updates": company_updates.render,
    "documents": documents.render,
    "tasks": tasks.render,
    "reports": reports.render,
    "admin": admin.render,
    "settings": settings.render,
}


def ensure_nav_defaults() -> None:
    st.session_state.setdefault(SESSION_NAV_KEY, "dashboard")


def on_nav_change(prev_slug: str, new_slug: str) -> None:
    if prev_slug != new_slug:
        clear_all_module_selections()


def render_module(slug: str | None = None) -> None:
    try:
        from app.navigation import normalize_nav_slug
    except ImportError:
        from navigation import normalize_nav_slug  # type: ignore

    active = normalize_nav_slug(slug or nav_slug() or "dashboard")
    role = current_role()
    if not role_can_access_page(role, active):
        st.error("You do not have access to this page.")
        return

    try:
        from app.pages._core._access import clear_demo_flag, end_module, show_demo_banner_if_needed
    except ImportError:
        from pages._core._access import clear_demo_flag, end_module, show_demo_banner_if_needed  # type: ignore

    clear_demo_flag()
    fn = BUILT_MODULES.get(active)
    if fn:
        try:
            fn()  # type: ignore[operator]
        except Exception as exc:
            st.error(f"This page encountered an error: {exc}")
            logging.getLogger(__name__).exception("module %s failed", active)
        finally:
            end_module()
        show_demo_banner_if_needed()
        return

    try:
        from app.components.headers import render_page_header
        from app.styles import inject_global_css
    except ImportError:
        from components.headers import render_page_header  # type: ignore
        from styles import inject_global_css  # type: ignore

    inject_global_css()
    label = active.replace("_", " ").title()
    render_page_header(label, "This module is not available yet.")
    st.markdown('<p class="ips-module-placeholder">Module not found.</p>', unsafe_allow_html=True)
