"""Role-based page and document access."""

from __future__ import annotations

from typing import Iterable

# Maps normalized role -> allowed page slugs
_ROLE_PAGES: dict[str, frozenset[str]] = {
    "admin": frozenset(
        p[0]
        for p in [
            ("dashboard",),
            ("jobs",),
            ("customers",),
            ("estimates",),
            ("pricing_guide",),
            ("estimate_materials",),
            ("inventory",),
            ("assets",),
            ("timekeeping",),
            ("weekly_timesheets",),
            ("employees",),
            ("employee_certifications",),
            ("employee_documents",),
            ("company_updates",),
            ("tasks",),
            ("documents",),
            ("reports",),
            ("field_dashboard",),
            ("field_day",),
            ("field_daily_reports",),
            ("field_crew_time",),
            ("coupling_inspection",),
            ("admin",),
            ("settings",),
        ]
    ),
    "supervisor": frozenset(
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
            "weekly_timesheets",
            "employees",
            "employee_certifications",
            "employee_documents",
            "company_updates",
            "tasks",
            "documents",
            "reports",
            "field_dashboard",
            "field_day",
            "field_daily_reports",
            "field_crew_time",
            "coupling_inspection",
            "settings",
        }
    ),
    "project manager": frozenset(
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
            "weekly_timesheets",
            "employees",
            "employee_certifications",
            "employee_documents",
            "company_updates",
            "tasks",
            "documents",
            "reports",
            "field_dashboard",
            "field_day",
            "field_daily_reports",
            "field_crew_time",
            "coupling_inspection",
            "settings",
        }
    ),
    "employee": frozenset(
        {
            "dashboard",
            "jobs",
            "timekeeping",
            "employee_certifications",
            "company_updates",
            "tasks",
            "documents",
            "field_dashboard",
            "field_day",
            "coupling_inspection",
            "settings",
        }
    ),
    "viewer": frozenset({"dashboard", "company_updates", "reports", "settings"}),
}


def normalize_role(raw: str) -> str:
    r = str(raw or "viewer").strip().lower()
    aliases = {
        "admin": "admin",
        "supervisor": "supervisor",
        "manager": "project manager",
        "viewer": "viewer",
        "employee": "employee",
        "pm": "project manager",
        "project manager": "project manager",
        "project_manager": "project manager",
        "estimator": "project manager",
    }
    return aliases.get(r, "viewer")


def role_can_access_page(role: str, page_slug: str) -> bool:
    norm = normalize_role(role)
    allowed = _ROLE_PAGES.get(norm, _ROLE_PAGES["viewer"])
    return page_slug in allowed


def can_view_hr_documents(role: str) -> bool:
    return normalize_role(role) == "admin"


def can_view_field_certifications(role: str) -> bool:
    return normalize_role(role) in {"admin", "supervisor", "project manager"}


def can_view_own_documents_only(role: str) -> bool:
    return normalize_role(role) == "employee"


def can_manage_weekly_timesheets(role: str) -> bool:
    """Generate, edit, approve, and void weekly job timesheets."""
    return normalize_role(role) in {"admin", "supervisor", "project manager"}


def can_submit_timekeeping(role: str) -> bool:
    """Enter hours and submit timecards for approval (supervisors and above)."""
    return can_manage_weekly_timesheets(role)


def can_approve_timekeeping(role: str) -> bool:
    """Approve or reject submitted timecards (administrators only)."""
    return normalize_role(role) == "admin"


def can_admin_edit_approved_timekeeping(role: str) -> bool:
    """Administrators may correct hours after a day or week is approved."""
    return normalize_role(role) == "admin"


def filter_field_nav_for_role(nav: Iterable[tuple[str, str]], role: str) -> list[tuple[str, str]]:
    """Field-mode sidebar items, including scan shortcuts gated by underlying module access."""
    scan_targets = {"scan_inventory": "inventory", "scan_asset": "assets"}
    out: list[tuple[str, str]] = []
    for slug, label in nav:
        target = scan_targets.get(slug, slug)
        if role_can_access_page(role, target):
            out.append((slug, label))
    return out


def filter_nav_for_role(
    nav: Iterable[tuple[str, str, str]], role: str
) -> list[tuple[str, str, str]]:
    return [item for item in nav if role_can_access_page(role, item[0])]
