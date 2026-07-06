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
        "employee_portal",
        "employee_profile",
        "employee_qr_scan",
        "employee_resources",
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
        "rental_equipment",
        "rental_equipment_inspection",
    }
)

# Session keys aligned with ``app.pages.jobs`` for Job Details deep-links.
JOBS_DETAIL_FOCUS_TAB_KEY = "jobs_detail_focus_tab"
_JOBS_MODAL_SESSION_KEY = "ips_jobs_detail_modal_id"
_JOBS_SELECTED_KEY = "selected_job_id"
_JOBS_SHOW_MODAL_KEY = "show_job_detail_modal"
JC_FOCUS_JOB_KEY = "jc_focus_job_id"
WJT_PREFILL_JOB_KEY = "wjt_prefill_job_id"
WJT_PREFILL_WEEK_KEY = "wjt_prefill_week_start"
TK_PREFILL_JOB_KEY = "tk_prefill_job_id"
TK_PREFILL_WEEK_KEY = "tk_prefill_week_start"
INVENTORY_SCAN_EMBED_KEY = "_ips_inventory_scan_embed"
ASSET_SCAN_EMBED_KEY = "_ips_asset_scan_embed"

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
    "Estimate Materials": "estimates",
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
    "To-Do": "tasks",
    "To Do": "tasks",
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
    "Office To-Do": "tasks",
    "Who Has What": "assets",
    "Tool Trailer Audits": "assets",
    "Asset Scanner": "assets",
    "Scan Asset": "assets",
    "Certifications": "employee_certifications",
    "Employee Documents": "employee_documents",
}

# Deferred cross-page jumps (legacy labels + slugs). Consumed in ``apply_pending_navigation()``.
IPS_NAV_PENDING_KEY = "ips_nav_pending"
ESTIMATE_DETAIL_TAB_KEY = "est_detail_active_tab"
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


def open_jobs_job_costing(*, job_id: str = "") -> None:
    """Open Jobs module with Job Details on the Job Costing tab."""
    jid = str(job_id or "").strip()
    if jid:
        st.session_state[JC_FOCUS_JOB_KEY] = jid
        st.session_state[_JOBS_SELECTED_KEY] = jid
        st.session_state[_JOBS_SHOW_MODAL_KEY] = True
        st.session_state[_JOBS_MODAL_SESSION_KEY] = jid
    st.session_state[JOBS_DETAIL_FOCUS_TAB_KEY] = "Job Costing"
    set_nav_slug("jobs")


def open_jobs_weekly_timesheets(*, job_id: str = "", week_start: str | None = None) -> None:
    """Open Jobs module with Job Details on the Weekly Timesheets tab."""
    jid = str(job_id or "").strip()
    ws = str(week_start or "").strip()[:10]
    if ws:
        st.session_state[WJT_PREFILL_WEEK_KEY] = ws
    if jid:
        st.session_state[_JOBS_SELECTED_KEY] = jid
        st.session_state[_JOBS_SHOW_MODAL_KEY] = True
        st.session_state[_JOBS_MODAL_SESSION_KEY] = jid
    st.session_state[JOBS_DETAIL_FOCUS_TAB_KEY] = "Weekly Timesheets"
    set_nav_slug("jobs")


def redirect_to_jobs_job_costing(*, job_id: str = "") -> None:
    """Open Jobs module with Job Details on the Job Costing tab."""
    jid = str(job_id or "").strip()
    if not jid:
        jid = str(st.session_state.pop(JC_FOCUS_JOB_KEY, "") or "").strip()
    open_jobs_job_costing(job_id=jid)


def navigate_to_estimate_materials(estimate_id: str) -> None:
    """Open estimate detail on the Materials tab (legacy entry point)."""
    navigate_to_estimate_detail(estimate_id, tab="Materials")


def navigate_to_estimate_detail(estimate_id: str, *, tab: str = "Details") -> None:
    """Open Estimates module with the estimate detail modal focused."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    try:
        from app.pages._core._data import ACTIVE_ESTIMATE_KEY
    except ImportError:
        from pages._core._data import ACTIVE_ESTIMATE_KEY  # type: ignore
    st.session_state[ACTIVE_ESTIMATE_KEY] = eid
    st.session_state["selected_estimate_id"] = eid
    st.session_state["show_estimate_detail_modal"] = True
    st.session_state[ESTIMATE_DETAIL_TAB_KEY] = str(tab or "Details").strip() or "Details"
    set_nav_slug("estimates")


def navigate_to_weekly_timesheet(*, job_id: str = "", week_start: str | None = None) -> None:
    """Open Job Detail Weekly Timesheets tab with optional job and week prefill."""
    open_jobs_weekly_timesheets(job_id=job_id, week_start=week_start)


def navigate_to_timekeeping(*, job_id: str = "", week_start: str | None = None) -> None:
    """Open Timekeeping with optional job and week prefill (single source of truth for hours)."""
    jid = str(job_id or "").strip()
    ws = str(week_start or "").strip()[:10]
    if jid:
        st.session_state[TK_PREFILL_JOB_KEY] = jid
        try:
            from app.utils.field_context import set_field_job_id
        except ImportError:
            from utils.field_context import set_field_job_id  # type: ignore
        set_field_job_id(jid)
    if ws:
        st.session_state[TK_PREFILL_WEEK_KEY] = ws
    set_nav_slug("timekeeping")

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
        set_nav_slug("scan_inventory")
        return
    if label in _SCAN_ASSET_LABELS:
        set_nav_slug("scan_asset")
        return
    if label in {"Asset Detail", "Asset Manager"}:
        set_nav_slug("assets")
        return
    if label in {"Users", "Employees", "People", "Employee Toolbox"}:
        set_nav_slug("employees")
        return
    if label in {"Job Costing", "Jobs"} and str(st.session_state.get(JC_FOCUS_JOB_KEY) or "").strip():
        redirect_to_jobs_job_costing()
        return
    if label == "Job Costing":
        redirect_to_jobs_job_costing()
        return

    set_nav_slug(label)


def default_nav_slug() -> str:
    """Safe fallback when ``ips_nav_page`` cannot be resolved to a built module."""
    try:
        from app.auth import current_role
        from app.utils.permissions import role_default_nav_slug
    except ImportError:
        from auth import current_role  # type: ignore
        from utils.permissions import role_default_nav_slug  # type: ignore
    return role_default_nav_slug(
        current_role(),
        field_mode=bool(st.session_state.get("ips_field_mode")),
    )


def normalize_nav_slug(raw: str | None) -> str:
    """
    Resolve ``ips_nav_page`` to a rebuilt module slug.

    Accepts modern slugs (``jobs``) and legacy labels (``Job Database``).
    Unknown values fall back to :func:`default_nav_slug` so stale session keys
    cannot strand the user on an access-denied blank page.
    """
    s = str(raw or "").strip()
    if not s:
        return default_nav_slug()
    if s in {"scan_inventory", "scan_asset"}:
        return "inventory" if s == "scan_inventory" else "assets"
    if s == "estimate_materials":
        return "estimates"
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
    if slug in {"scan_inventory", "scan_asset"}:
        return "inventory" if slug == "scan_inventory" else "assets"
    if slug == "estimate_materials":
        return "estimates"
    if slug in ACTIVE_MODULE_SLUGS:
        return "employees" if slug == "users" else slug
    return default_nav_slug()


def current_nav_slug() -> str:
    return normalize_nav_slug(str(st.session_state.get(SESSION_NAV_KEY) or "dashboard"))


def set_nav_slug(slug: str) -> None:
    raw = str(slug or "").strip()
    if raw == "scan_inventory":
        st.session_state[SESSION_NAV_KEY] = "inventory"
        st.session_state[INVENTORY_SCAN_EMBED_KEY] = True
        st.session_state.pop(_INVENTORY_SCAN_SESSION_KEY, None)
        return
    if raw == "scan_asset":
        st.session_state[SESSION_NAV_KEY] = "assets"
        st.session_state[ASSET_SCAN_EMBED_KEY] = True
        st.session_state.pop(_ASSET_SCAN_SESSION_KEY, None)
        return
    st.session_state.pop(INVENTORY_SCAN_EMBED_KEY, None)
    st.session_state.pop(ASSET_SCAN_EMBED_KEY, None)
    st.session_state[SESSION_NAV_KEY] = normalize_nav_slug(raw)


def ensure_nav_defaults() -> None:
    try:
        from app.phase2 import ensure_nav_defaults as _impl
    except ImportError:
        from phase2 import ensure_nav_defaults as _impl  # type: ignore
    _impl()


def on_nav_change(prev_slug: str, new_slug: str) -> None:
    try:
        from app.phase2 import on_nav_change as _impl
    except ImportError:
        from phase2 import on_nav_change as _impl  # type: ignore
    _impl(prev_slug, new_slug)


def render_module(slug: str | None = None) -> None:
    try:
        from app.phase2 import render_module as _impl
    except ImportError:
        from phase2 import render_module as _impl  # type: ignore
    _impl(slug)


def __getattr__(name: str):
    if name == "BUILT_MODULES":
        try:
            from app.phase2 import BUILT_MODULES
        except ImportError:
            from phase2 import BUILT_MODULES  # type: ignore
        return BUILT_MODULES
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ACTIVE_MODULE_SLUGS",
    "ASSET_SCAN_EMBED_KEY",
    "BUILT_MODULES",
    "INVENTORY_SCAN_EMBED_KEY",
    "ESTIMATE_DETAIL_TAB_KEY",
    "IPS_NAV_PENDING_KEY",
    "JC_FOCUS_JOB_KEY",
    "JOBS_DETAIL_FOCUS_TAB_KEY",
    "LEGACY_PAGE_LABEL_TO_SLUG",
    "PENDING_NAV_ALIASES",
    "WJT_PREFILL_JOB_KEY",
    "WJT_PREFILL_WEEK_KEY",
    "TK_PREFILL_JOB_KEY",
    "TK_PREFILL_WEEK_KEY",
    "apply_pending_navigation",
    "current_nav_slug",
    "default_nav_slug",
    "ensure_nav_defaults",
    "navigate_to_estimate_detail",
    "navigate_to_estimate_materials",
    "navigate_to_timekeeping",
    "navigate_to_weekly_timesheet",
    "normalize_nav_slug",
    "on_nav_change",
    "open_jobs_job_costing",
    "open_jobs_weekly_timesheets",
    "queue_pending_nav",
    "redirect_to_jobs_job_costing",
    "render_module",
    "set_nav_slug",
]
