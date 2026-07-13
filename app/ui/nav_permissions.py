"""Role-based sidebar page access checks (UI hiding + routing validation)."""

from __future__ import annotations

_NAV_PRIMARY: tuple[str, ...] = ("Dashboard", "Field Dashboard", "Company Updates")

_NAV_JOBS_ROUTES: tuple[str, ...] = (
    "Job Database",
    "Daily Reports",
    "Crew Time",
    "Assign Tasks (PM)",
    "Work & Plan (Supervisor)",
    "Estimates",
    "Pricing Guide",
    "Estimate Materials",
    "Customers",
)
_NAV_ASSET_ROUTES: tuple[str, ...] = ("Asset Database", "Who Has What", "Tool Trailer Audits")
_NAV_RESOURCES: tuple[str, ...] = ("Inventory",)

_ROLE_ALLOWED_PAGES: dict[str, frozenset[str]] = {
    "admin": frozenset(
        {
            *_NAV_PRIMARY,
            *_NAV_JOBS_ROUTES,
            *_NAV_ASSET_ROUTES,
            *_NAV_RESOURCES,
            "Admin",
            "Users",
            "Asset Detail",
            "Asset Manager",
            "Scan Inventory",
            "Inventory Usage",
            "Time Tracking",
            "Weekly Timesheet",
            "PO / Expenses",
            "People",
            "Employees",
            "Employee Toolbox",
            "PM Matrix Time Entry",
            "Labor",
            "Asset Scanner",
            "Customers",
            "Assign Tasks (PM)",
            "Work & Plan (Supervisor)",
            "Field Dashboard",
            "Daily Reports",
            "Crew Time",
        }
    ),
    "manager": frozenset(
        {
            "Dashboard",
            "Field Dashboard",
            "Company Updates",
            "Job Database",
            "Daily Reports",
            "Crew Time",
            "Assign Tasks (PM)",
            "Work & Plan (Supervisor)",
            "Estimates",
            "Pricing Guide",
            "Estimate Materials",
            "Inventory",
            "Scan Inventory",
            "Inventory Usage",
            "Who Has What",
            "Asset Database",
            "Tool Trailer Audits",
        }
    ),
    "employee": frozenset(
        {
            "Dashboard",
            "Field Dashboard",
            "Company Updates",
            "Daily Reports",
            "Crew Time",
            "Work & Plan (Supervisor)",
            "Time Tracking",
            "Asset Database",
            "Scan Inventory",
            "Who Has What",
            "Tool Trailer Audits",
            "Employee Toolbox",
        }
    ),
    "viewer": frozenset({"Dashboard", "Company Updates", "Inventory Usage", "Who Has What", "Asset Database"}),
}


def role_can_open_page(role: str, page: str) -> bool:
    r = str(role or "viewer").strip().lower()
    if r in {"pm", "estimator"}:
        r = "manager"
    allowed = _ROLE_ALLOWED_PAGES.get(r)
    if allowed is None:
        allowed = _ROLE_ALLOWED_PAGES.get("viewer", frozenset())
    return str(page or "").strip() in allowed


__all__ = ["role_can_open_page"]
