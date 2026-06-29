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
        "pipeline",
        "customers",
        "estimates",
        "pricing_guide",
        "estimate_materials",
        "inventory",
        "assets",
        "timekeeping",
        "weekly_timesheets",
        "employees",
        "users",  # alias → employees
        "employee_certifications",
        "employee_documents",
        "company_updates",
        "tasks",
        "documents",
        "reports",
        "admin",
        "settings",
        "field_dashboard",
        "field_day",
        "field_daily_reports",
        "field_crew_time",
        "coupling_inspection",
    }
)

# Session keys aligned with ``app.pages.jobs`` for Job Details deep-links.
JOBS_DETAIL_FOCUS_TAB_KEY = "jobs_detail_focus_tab"
_JOBS_MODAL_SESSION_KEY = "ips_jobs_detail_modal_id"
_JOBS_SELECTED_KEY = "selected_job_id"
_JOBS_SHOW_MODAL_KEY = "show_job_detail_modal"

# Legacy sidebar / deep-link labels from ``app.ui`` → rebuilt module slugs.
LEGACY_PAGE_LABEL_TO_SLUG: dict[str, str] = {
    "Dashboard": "dashboard",
    "Field Dashboard": "field_dashboard",
    "Company Updates": "company_updates",
    "Jobs": "jobs",
    "Job Database": "jobs",
    "Pipeline": "pipeline",
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
    "Daily Reports": "field_daily_reports",
    "Crew Time": "field_crew_time",
    "Time Tracking": "timekeeping",
    "Weekly Timesheets": "weekly_timesheets",
    "Weekly Timesheet": "weekly_timesheets",
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
    "Job Costing": "jobs",
    "Customers / Jobs": "customers",
    "Work & Plan (Supervisor)": "tasks",
    "Assign Tasks (PM)": "tasks",
    "Who Has What": "assets",
    "Tool Trailer Audits": "assets",
    "Asset Scanner": "assets",
    "Scan Asset": "assets",
    "Certifications": "employee_certifications",
    "Employee Documents": "employee_documents",
}

# Deferred cross-page jumps (legacy labels + slugs). Consumed in ``apply_pending_navigation()``.
IPS_NAV_PENDING_KEY = "ips_nav_pending"
_INVENTORY_SCAN_SESSION_KEY = "_ips_inventory_scan_page"
_ASSET_SCAN_SESSION_KEY = "_ips_asset_scan_page"

PENDING_NAV_ALIASES: dict[str, str] = {
    "Tool Checkout": "Scan Inventory",
    "Planning & Goals": "Work & Plan (Supervisor)",
    "Daily Tasks": "Work & Plan (Supervisor)",
    "Daily Reports": "field_daily_reports",
    "Daily crew report": "field_daily_reports",
    "Supervisor Daily Reports": "field_daily_reports",
    "Crew Time": "field_crew_time",
    "Materials Catalog": "Pricing Guide",
    "Material Catalog": "Pricing Guide",
    "Materials": "Pricing Guide",
    "PM Matrix Time Entry": "Timekeeping",
    "Job Costing": "Jobs",
}


def redirect_to_jobs_job_costing(*, job_id: str = "") -> None:
    """Open Jobs module with Job Details on the Job Costing tab."""
    jid = str(job_id or st.session_state.pop("jc_focus_job_id", "") or "").strip()
    set_nav_slug("jobs")
    if jid:
        st.session_state[JOBS_DETAIL_FOCUS_TAB_KEY] = "Job Costing"
        st.session_state[_JOBS_SELECTED_KEY] = jid
        st.session_state[_JOBS_SHOW_MODAL_KEY] = True
        st.session_state[_JOBS_MODAL_SESSION_KEY] = jid

_SCAN_INVENTORY_LABELS = frozenset({"Scan Inventory", "Inventory Scan"})
_SCAN_ASSET_LABELS = frozenset({"Asset Scanner", "Scan Asset", "Asset Scan"})


def queue_pending_nav(label_or_slug: str) -> None:
    """Queue a sidebar/page change for the next ``main()`` run (before the sidebar renders)."""
    label = str(label_or_slug or "").strip()
    if label:
        st.session_state[IPS_NAV_PENDING_KEY] = label


def apply_pending_navigation() -> None:
    """
    Apply deferred navigation from ``IPS_NAV_PENDING_KEY``.

    Maps legacy sidebar labels to rebuilt module slugs and arms dedicated scan routes.
    """
    pending = st.session_state.pop(IPS_NAV_PENDING_KEY, None)
    if not pending:
        return

    label = PENDING_NAV_ALIASES.get(str(pending).strip(), str(pending).strip())
    if not label:
        return

    if label in _SCAN_INVENTORY_LABELS:
        st.session_state[_INVENTORY_SCAN_SESSION_KEY] = True
        return
    if label in _SCAN_ASSET_LABELS:
        st.session_state[_ASSET_SCAN_SESSION_KEY] = True
        return
    if label in {"Asset Detail", "Asset Manager"}:
        set_nav_slug("assets")
        return
    if label in {"Users", "Employees", "People", "Employee Toolbox"}:
        set_nav_slug("employees")
        return
    if label in {"Job Costing", "Jobs"} and str(st.session_state.get("jc_focus_job_id") or "").strip():
        redirect_to_jobs_job_costing()
        return
    if label == "Job Costing":
        redirect_to_jobs_job_costing()
        return

    set_nav_slug(label)


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
    if s == "job_costing":
        return "jobs"
    mapped = LEGACY_PAGE_LABEL_TO_SLUG.get(s)
    if mapped:
        return mapped
    slug = s.lower().replace(" ", "_").replace("-", "_")
    if slug == "job_costing":
        return "jobs"
    if slug in ACTIVE_MODULE_SLUGS:
        return "employees" if slug == "users" else slug
    return slug


def current_nav_slug() -> str:
    return normalize_nav_slug(str(st.session_state.get(SESSION_NAV_KEY) or "dashboard"))


def set_nav_slug(slug: str) -> None:
    raw = str(slug or "").strip()
    if raw == "scan_inventory":
        st.session_state[_INVENTORY_SCAN_SESSION_KEY] = True
        return
    if raw == "scan_asset":
        st.session_state[_ASSET_SCAN_SESSION_KEY] = True
        return
    st.session_state[SESSION_NAV_KEY] = normalize_nav_slug(raw)


try:
    from app.phase2 import BUILT_MODULES, ensure_nav_defaults, on_nav_change, render_module
except ImportError:
    from phase2 import BUILT_MODULES, ensure_nav_defaults, on_nav_change, render_module  # type: ignore

__all__ = [
    "ACTIVE_MODULE_SLUGS",
    "BUILT_MODULES",
    "IPS_NAV_PENDING_KEY",
    "JOBS_DETAIL_FOCUS_TAB_KEY",
    "LEGACY_PAGE_LABEL_TO_SLUG",
    "PENDING_NAV_ALIASES",
    "apply_pending_navigation",
    "current_nav_slug",
    "ensure_nav_defaults",
    "normalize_nav_slug",
    "on_nav_change",
    "queue_pending_nav",
    "redirect_to_jobs_job_costing",
    "render_module",
    "set_nav_slug",
]
