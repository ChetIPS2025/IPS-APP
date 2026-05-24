"""
Unified IPS app navigation — single shell, slug-based modules.

All authenticated business areas (Jobs, Estimates, Inventory, etc.) are **modules**
inside one Streamlit app. They are not separate apps.

Entry flow:
  ``app/main.py`` → auth gate → ``render_sidebar()`` → ``render_module(slug)``

Session key: ``ips_nav_page`` (see ``utils.constants.SESSION_NAV_KEY``).
"""

from __future__ import annotations

import streamlit as st

try:
    from app.utils.constants import SESSION_NAV_KEY
except ImportError:
    from utils.constants import SESSION_NAV_KEY  # type: ignore

# Slugs registered in the rebuilt router (``phase2.BUILT_MODULES``).
ACTIVE_MODULE_SLUGS: frozenset[str] = frozenset(
    {
        "dashboard",
        "jobs",
        "customers",
        "estimates",
        "pricing_guide",
        "estimate_materials",
        "inventory",
        "assets",
        "timekeeping",
        "employees",
        "users",  # alias → employees
        "employee_certifications",
        "employee_documents",
        "company_updates",
        "tasks",
        "documents",
        "reports",
        "job_costing",
        "admin",
        "settings",
    }
)

# Legacy sidebar / deep-link labels from ``app.ui`` → rebuilt module slugs.
LEGACY_PAGE_LABEL_TO_SLUG: dict[str, str] = {
    "Dashboard": "dashboard",
    "Field Dashboard": "dashboard",
    "Company Updates": "company_updates",
    "Jobs": "jobs",
    "Job Database": "jobs",
    "Customers": "customers",
    "Customer Database": "customers",
    "Estimates": "estimates",
    "Estimate Database": "estimates",
    "Pricing Guide": "pricing_guide",
    "Materials Catalog": "pricing_guide",
    "Material Catalog": "pricing_guide",
    "Estimate Materials": "estimate_materials",
    "Materials": "pricing_guide",
    "Inventory": "inventory",
    "Scan Inventory": "inventory",
    "Assets": "assets",
    "Asset Database": "assets",
    "Asset Manager": "assets",
    "Asset Detail": "assets",
    "Timekeeping": "timekeeping",
    "Time Tracking": "timekeeping",
    "Weekly Timesheet": "timekeeping",
    "PM Matrix Time Entry": "timekeeping",
    "People": "employees",
    "Users": "employees",
    "Employees": "employees",
    "Employee Toolbox": "employees",
    "Tasks": "tasks",
    "Documents": "documents",
    "Reports": "reports",
    "Admin": "admin",
    "Settings": "settings",
    "PO / Expenses": "reports",
    "Labor": "reports",
    "Job Costing": "job_costing",
    "Customers / Jobs": "customers",
}


def normalize_nav_slug(raw: str | None) -> str:
    """
    Resolve ``ips_nav_page`` to a rebuilt module slug.

    Accepts modern slugs (``jobs``) and legacy labels (``Job Database``).
    """
    s = str(raw or "").strip()
    if not s:
        return "dashboard"
    if s in ACTIVE_MODULE_SLUGS:
        return "employees" if s == "users" else s
    mapped = LEGACY_PAGE_LABEL_TO_SLUG.get(s)
    if mapped:
        return mapped
    slug = s.lower().replace(" ", "_").replace("-", "_")
    if slug in ACTIVE_MODULE_SLUGS:
        return "employees" if slug == "users" else slug
    return slug


def current_nav_slug() -> str:
    return normalize_nav_slug(str(st.session_state.get(SESSION_NAV_KEY) or "dashboard"))


def set_nav_slug(slug: str) -> None:
    st.session_state[SESSION_NAV_KEY] = normalize_nav_slug(slug)


try:
    from app.phase2 import BUILT_MODULES, ensure_nav_defaults, on_nav_change, render_module
except ImportError:
    from phase2 import BUILT_MODULES, ensure_nav_defaults, on_nav_change, render_module  # type: ignore

__all__ = [
    "ACTIVE_MODULE_SLUGS",
    "BUILT_MODULES",
    "LEGACY_PAGE_LABEL_TO_SLUG",
    "current_nav_slug",
    "ensure_nav_defaults",
    "normalize_nav_slug",
    "on_nav_change",
    "render_module",
    "set_nav_slug",
]
