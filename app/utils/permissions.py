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
            ("job_costing",),
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
            ("admin",),
            ("settings",),
        ]
    ),
    "supervisor": frozenset(
        {
            "dashboard",
            "jobs",
            "job_costing",
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
            "settings",
        }
    ),
    "project manager": frozenset(
        {
            "dashboard",
            "jobs",
            "job_costing",
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


def can_approve_timekeeping(role: str) -> bool:
    """Approve or reject employee weekly timecards."""
    return can_manage_weekly_timesheets(role)


def filter_nav_for_role(
    nav: Iterable[tuple[str, str, str]], role: str
) -> list[tuple[str, str, str]]:
    return [item for item in nav if role_can_access_page(role, item[0])]
