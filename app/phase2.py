"""Phase 2 slug-based module router."""

from __future__ import annotations

import streamlit as st

try:
    from app.pages.modules import assets, dashboard, estimate_materials, estimates, inventory, jobs
    from app.pages.modules._session import clear_all_module_selections, nav_slug
    from app.utils.constants import SESSION_NAV_KEY
    from app.utils.permissions import role_can_access_page
except ImportError:
    from pages.modules import assets, dashboard, estimate_materials, estimates, inventory, jobs  # type: ignore
    from pages.modules._session import clear_all_module_selections, nav_slug  # type: ignore
    from utils.constants import SESSION_NAV_KEY  # type: ignore
    from utils.permissions import role_can_access_page  # type: ignore

try:
    from app.auth import current_role
except ImportError:
    from auth import current_role  # type: ignore

BUILT_MODULES: dict[str, object] = {
    "dashboard": dashboard.render,
    "jobs": jobs.render,
    "estimates": estimates.render,
    "estimate_materials": estimate_materials.render,
    "inventory": inventory.render,
    "assets": assets.render,
}

COMING_SOON_LABELS: dict[str, str] = {
    "timekeeping": "Timekeeping",
    "employees": "Employees",
    "company_updates": "Company Updates",
    "tasks": "Tasks",
    "documents": "Documents",
    "reports": "Reports",
    "admin": "Admin",
    "settings": "Settings",
}


def ensure_nav_defaults() -> None:
    st.session_state.setdefault(SESSION_NAV_KEY, "dashboard")


def on_nav_change(prev_slug: str, new_slug: str) -> None:
    if prev_slug != new_slug:
        clear_all_module_selections()


def render_module(slug: str | None = None) -> None:
    active = str(slug or nav_slug() or "dashboard")
    role = current_role()
    if not role_can_access_page(role, active):
        st.error("You do not have access to this page.")
        return
    fn = BUILT_MODULES.get(active)
    if fn:
        fn()  # type: ignore[operator]
        return
    label = COMING_SOON_LABELS.get(active, active.replace("_", " ").title())
    try:
        from app.styles import inject_global_css
        from app.components.headers import render_page_header
    except ImportError:
        from styles import inject_global_css  # type: ignore
        from components.headers import render_page_header  # type: ignore
    inject_global_css()
    render_page_header(label, "This module is next in the Phase 2 rollout.")
    st.markdown(
        f'<p class="ips-module-placeholder">Coming soon — built with the IPS foundation components.</p>',
        unsafe_allow_html=True,
    )
