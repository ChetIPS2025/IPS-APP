"""Application constants and dropdown option lists."""

from __future__ import annotations

ROLES = (
    "Admin",
    "Supervisor",
    "Project Manager",
    "Employee",
    "Viewer",
)

JOB_STATUSES = (
    "Planning",
    "Active",
    "On Hold",
    "Completed",
    "Cancelled",
)

ESTIMATE_STATUSES = (
    "Draft",
    "Sent",
    "Pending",
    "Approved",
    "Rejected",
    "Awarded",
)

TASK_STATUSES = ("Open", "In Progress", "Blocked", "Done", "Cancelled")
TASK_PRIORITIES = ("Low", "Medium", "High", "Urgent")

LABOR_TYPES = ("ST", "OT", "DT")

INVENTORY_STATUSES = ("In Stock", "Low Stock", "Out of Stock", "Discontinued")
ASSET_STATUSES = ("Active", "In Service", "Maintenance", "Retired", "Disposed")

CERTIFICATION_TYPES = (
    "TWIC",
    "OSHA 10",
    "OSHA 30",
    "NCCER",
    "Forklift",
    "Aerial Lift",
    "Confined Space",
    "First Aid / CPR",
    "Site Orientation",
    "Fire Watch",
    "Hot Work",
    "Driver's License",
    "Medical Clearance",
    "Other",
)

DOCUMENT_TYPES = (
    "Driver's License",
    "TWIC Card",
    "OSHA Card",
    "NCCER",
    "Site Orientation",
    "Medical Clearance",
    "Training Record",
    "Resume",
    "Employment Form",
    "Safety Document",
    "HR Document",
    "Other",
)

UPDATE_CATEGORIES = (
    "All Updates",
    "Announcements",
    "Safety Alerts",
    "Events",
    "HR Updates",
    "Project Updates",
)

DEPARTMENTS = (
    "Field Operations",
    "Project Management",
    "Estimating",
    "Warehouse",
    "Safety",
    "Administration",
    "HR",
)

UNITS = ("EA", "FT", "LF", "SF", "CY", "GAL", "LB", "TON", "HR", "DAY")

NAV_PAGES: list[tuple[str, str, str]] = [
    ("dashboard", "Dashboard", "layout-dashboard"),
    ("jobs", "Jobs", "briefcase"),
    ("estimates", "Estimates", "file-text"),
    ("inventory", "Inventory", "package"),
    ("assets", "Assets", "truck"),
    ("timekeeping", "Timekeeping", "clock"),
    ("employees", "Employees", "users"),
    ("company_updates", "Company Updates", "megaphone"),
    ("tasks", "Tasks", "check-square"),
    ("documents", "Documents", "folder"),
    ("reports", "Reports", "bar-chart-2"),
    ("admin", "Admin", "settings"),
    ("settings", "Settings", "sliders"),
]

FIELD_NAV_PAGES: list[tuple[str, str]] = [
    ("jobs", "My Jobs"),
    ("timekeeping", "Log Time"),
    ("assets", "Assets"),
    ("employee_certifications", "Certifications"),
]

SESSION_NAV_KEY = "ips_nav_page"
SESSION_SELECTED_PREFIX = "ips_sel_"
SESSION_DETAIL_TAB_PREFIX = "ips_tab_"
