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

CUSTOMERS = (
    "Acme Industrial",
    "Bayou Petrochemical",
    "Coastal Refining",
    "Gulf Coast Fabricators",
    "IPS Internal",
)

VENDORS = (
    "Grainger",
    "Ferguson Supply",
    "Louisiana Welding Supply",
    "Sunbelt Rentals",
    "Local Hardware Co.",
)

LOCATIONS = (
    "Main Warehouse",
    "Yard 1",
    "Yard 2",
    "Shop Office",
    "Tool Trailer A",
)

CREWS = (
    "Crew A — Field Ops",
    "Crew B — Field Ops",
    "Crew C — Maintenance",
    "PM Support",
)

INVENTORY_CATEGORIES = (
    "Electrical",
    "Plumbing",
    "Fasteners",
    "Safety",
    "Consumables",
    "Tools",
)

ASSET_CATEGORIES = (
    "Vehicle",
    "Trailer",
    "Heavy Equipment",
    "Tool",
    "Lift",
    "Generator",
)

PERMISSION_GROUPS = (
    "Full Access",
    "Operations",
    "Field Only",
    "Read Only",
    "HR Restricted",
)

DOCUMENT_LINK_MODULES = (
    "All Modules",
    "Jobs",
    "Estimates",
    "Assets",
    "Employees",
    "Certifications",
    "Inventory",
    "Company Updates",
)

LOOKUP_TABLES = (
    "Customers",
    "Vendors",
    "Departments",
    "Locations",
    "Crews",
    "Job Statuses",
    "Estimate Statuses",
    "Inventory Categories",
    "Asset Categories",
    "Certification Types",
    "Document Types",
    "User Roles",
    "Permission Groups",
)

NAV_PAGES: list[tuple[str, str, str]] = [
    ("dashboard", "Dashboard", "layout-dashboard"),
    ("jobs", "Jobs", "briefcase"),
    ("job_costing", "Job Costing", "calculator"),
    ("customers", "Customers", "building"),
    ("estimates", "Estimates", "file-text"),
    ("inventory", "Inventory", "package"),
    ("assets", "Assets", "truck"),
    ("timekeeping", "Timekeeping", "clock"),
    ("employees", "Users", "users"),
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
