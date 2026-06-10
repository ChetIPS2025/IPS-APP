"""Load module data from Supabase with demo fallbacks."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

try:
    from app.utils.dates import week_dates
except ImportError:
    from utils.dates import week_dates  # type: ignore

_DEMO_JOBS: list[dict[str, Any]] = [
    {
        "id": "demo-j26047",
        "job_number": "J26047",
        "job_name": "Maintenance Shop Bathroom Remodel",
        "customer": "Birla Carbons - USA",
        "estimate_number": "E-10244",
        "supervisor": "Leland Daigle",
        "status": "Active",
        "start_date": "2025-05-01",
        "end_date": "2025-08-15",
        "progress": 65,
        "description": "Bathroom remodel in maintenance shop including fixtures and tile.",
    },
    {
        "id": "demo-j26048",
        "job_number": "J26048",
        "job_name": "Tank Farm Piping Upgrade",
        "customer": "Acme Construction",
        "estimate_number": "E-10238",
        "supervisor": "Mark Johnson",
        "status": "Estimate Pending",
        "start_date": "",
        "end_date": "",
        "progress": 0,
        "description": "Awaiting customer approval on tank farm piping estimate.",
    },
    {
        "id": "demo-j26049",
        "job_number": "J26049",
        "job_name": "Warehouse LED Retrofit",
        "customer": "Gulf Coast Industrial",
        "estimate_number": "E-10230",
        "supervisor": "Leland Daigle",
        "status": "Draft",
        "start_date": "",
        "end_date": "",
        "progress": 0,
        "description": "LED lighting retrofit across warehouse bays 1–4.",
    },
    {
        "id": "demo-j26050",
        "job_number": "J26050",
        "job_name": "Office Building Renovation",
        "customer": "Acme Construction",
        "estimate_number": "E-10244",
        "supervisor": "Sarah Chen",
        "status": "On Hold",
        "start_date": "2025-04-10",
        "end_date": "2025-12-01",
        "progress": 22,
        "description": "Interior renovation of office building floors 2–3.",
    },
    {
        "id": "demo-j26070",
        "job_number": "J26070",
        "job_name": "Orange Turnaround Extra Work",
        "customer": "Birla Carbons - USA",
        "estimate_number": "E-10250",
        "supervisor": "Leland Daigle",
        "status": "Awarded",
        "start_date": "2025-06-01",
        "end_date": "2025-09-30",
        "progress": 0,
        "description": "Additional turnaround scope awarded from estimate.",
    },
    {
        "id": "demo-j26071",
        "job_number": "J26071",
        "job_name": "Front Office A/C Drain Line",
        "customer": "Gulf Coast Industrial",
        "estimate_number": "E-10251",
        "supervisor": "Mark Johnson",
        "status": "Awarded",
        "start_date": "2025-06-15",
        "end_date": "2025-07-31",
        "progress": 0,
        "description": "A/C drain line replacement — awarded, pending start.",
    },
    {
        "id": "demo-j26045",
        "job_number": "J26045",
        "job_name": "Boiler House Valve Replacement",
        "customer": "Acme Construction",
        "estimate_number": "E-10220",
        "supervisor": "Sarah Chen",
        "status": "Completed",
        "start_date": "2025-01-10",
        "end_date": "2025-03-28",
        "progress": 100,
        "description": "Completed valve replacement scope.",
    },
]


def _fetch_table(name: str, *, order_by: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    try:
        from app.services.repository import fetch_rows
    except ImportError:
        from services.repository import fetch_rows  # type: ignore
    rows, err = fetch_rows(name, limit=limit, order_by=order_by)
    if err:
        try:
            from app.pages.modules._access import mark_demo_data, show_db_error
        except ImportError:
            from pages.modules._access import mark_demo_data, show_db_error  # type: ignore
        mark_demo_data()
        show_db_error(name, err)
    return rows


def _mark_if_demo(used: bool) -> None:
    if used:
        try:
            from app.pages.modules._access import mark_demo_data
        except ImportError:
            from pages.modules._access import mark_demo_data  # type: ignore
        mark_demo_data()


def load_jobs() -> list[dict[str, Any]]:
    try:
        from app.services.jobs_service import list_jobs
    except ImportError:
        from services.jobs_service import list_jobs  # type: ignore
    rows, used = list_jobs(demo=list(_DEMO_JOBS))
    _mark_if_demo(used)
    return rows


def load_dashboard_kpis() -> dict[str, Any]:
    try:
        from app.services.job_service import dashboard_job_metrics
    except ImportError:
        from services.job_service import dashboard_job_metrics  # type: ignore

    estimates = _fetch_table("estimates", limit=200)
    jobs = load_jobs()
    if estimates or jobs:
        open_est = sum(1 for e in estimates if str(e.get("status", "")).lower() in {"draft", "sent", "pending"})
        return {
            "total_sales": 245680.50,
            "open_invoices": 125430.25,
            "open_estimates": open_est or len(estimates),
            "inventory_value": 98765.30,
            **dashboard_job_metrics(jobs),
        }
    return {
        "total_sales": 245680.50,
        "open_invoices": 125430.25,
        "open_estimates": 14,
        "inventory_value": 98765.30,
        "jobs_awarded": 2,
        "active_jobs": 1,
        "estimate_pending_jobs": 1,
        "complete_jobs": 1,
    }


def demo_sales_series() -> tuple[list[str], dict[str, list[float]]]:
    labels = ["May 1", "May 8", "May 15", "May 22", "May 29"]
    return labels, {
        "This Period": [42000, 51000, 48000, 62000, 58000],
        "Last Period": [38000, 45000, 50000, 52000, 49000],
    }


def demo_sales_categories() -> dict[str, float]:
    return {"Labor": 98272.0, "Materials": 73704.0, "Equipment": 49136.0, "Other": 24568.0}


def demo_job_status() -> dict[str, int]:
    jobs = load_jobs()
    counts: dict[str, int] = {}
    for j in jobs:
        st = str(j.get("status") or "Draft")
        counts[st] = counts.get(st, 0) + 1
    if not counts:
        return {"Not Started": 4, "In Progress": 9, "On Hold": 2, "Completed": 3}
    return counts


def demo_activities() -> list[dict[str, str]]:
    return [
        {"icon": "💰", "bg": "#dcfce7", "text": "Invoice #INV-1005 paid", "time": "2h ago"},
        {"icon": "📄", "bg": "#dbeafe", "text": "Estimate E-10244 sent to customer", "time": "4h ago"},
        {"icon": "🔧", "bg": "#ffedd5", "text": "Job J26047 marked In Progress", "time": "Yesterday"},
        {"icon": "📦", "bg": "#f3e8ff", "text": "Inventory item SKU-442 restocked", "time": "Yesterday"},
        {"icon": "👷", "bg": "#e0f2fe", "text": "Timesheet approved for Week 20", "time": "2d ago"},
    ]


def demo_item_activities() -> list[dict[str, str]]:
    return [
        {"icon": "📦", "icon_bg": "#f3e8ff", "title": "Used on job · PVC cement (4 EA)", "meta": "J26047 · 2h ago"},
        {"icon": "🔧", "icon_bg": "#ffedd5", "title": "Checked out · Milwaukee M18 impact", "meta": "J26047 · Alex · 3h ago"},
        {"icon": "📦", "icon_bg": "#f3e8ff", "title": "Used in shop · Wire nuts (50 EA)", "meta": "Shop · 5h ago"},
        {"icon": "🔧", "icon_bg": "#dcfce7", "title": "Checked in · Hilti rotary hammer", "meta": "Maria · Yesterday"},
        {"icon": "🔧", "icon_bg": "#e0f2fe", "title": "Assigned · DeWalt circular saw", "meta": "Trailer 2 · Yesterday"},
        {"icon": "📦", "icon_bg": "#f3e8ff", "title": "Used on job · THHN wire (200 FT)", "meta": "J26048 · 2d ago"},
        {"icon": "🔧", "icon_bg": "#dbeafe", "title": "Returned · Fluke multimeter", "meta": "J26047 · 2d ago"},
        {"icon": "📦", "icon_bg": "#f3e8ff", "title": "Used on job · EMT connectors (12 EA)", "meta": "J26049 · 3d ago"},
        {"icon": "🔧", "icon_bg": "#ffedd5", "title": "Checked out · Greenlee bender", "meta": "J26048 · Chris · 3d ago"},
        {"icon": "📦", "icon_bg": "#f3e8ff", "title": "Used in shop · Electrical tape (6 EA)", "meta": "Shop · 4d ago"},
    ]


def load_recent_item_activity(*, limit: int = 10) -> list[dict[str, str]]:
    try:
        from app.services.dashboard_item_activity_service import recent_item_activity_feed
    except ImportError:
        from services.dashboard_item_activity_service import recent_item_activity_feed  # type: ignore
    items = recent_item_activity_feed(limit=limit)
    if items:
        return items
    return demo_item_activities()[:limit]


def demo_qr_scans() -> list[dict[str, str]]:
    try:
        from app.pages._core._data import demo_qr_scans as _demo
    except ImportError:
        from pages._core._data import demo_qr_scans as _demo  # type: ignore
    return _demo()


def load_recent_qr_scans(*, limit: int = 25, inventory_item_id: str | None = None) -> list[dict[str, str]]:
    try:
        from app.services.qr_scan_log_service import recent_qr_scans
    except ImportError:
        from services.qr_scan_log_service import recent_qr_scans  # type: ignore
    rows = recent_qr_scans(limit=limit, inventory_item_id=inventory_item_id)
    if rows:
        return rows
    return demo_qr_scans()[:limit]


def demo_deadlines() -> list[dict[str, str]]:
    today = date.today()
    return [
        {"title": "J26047 — Rough-in inspection", "date": (today + timedelta(days=3)).isoformat(), "badge": "3 days", "level": "danger"},
        {"title": "E-10244 — Estimate expiration", "date": (today + timedelta(days=8)).isoformat(), "badge": "8 days", "level": "warn"},
        {"title": "J26048 — Mobilization", "date": (today + timedelta(days=14)).isoformat(), "badge": "14 days", "level": "ok"},
    ]


def demo_recent_jobs(limit: int = 5) -> list[dict[str, Any]]:
    return load_jobs()[:limit]


def load_awarded_jobs() -> list[dict[str, Any]]:
    try:
        from app.pages._core._data import load_awarded_jobs as _load
    except ImportError:
        from pages._core._data import load_awarded_jobs as _load  # type: ignore
    return _load()


ACTIVE_ESTIMATE_KEY = "ips_active_estimate_id"

_DEMO_ESTIMATES: list[dict[str, Any]] = [
    {
        "id": "demo-e10244",
        "estimate_number": "E-10244",
        "project_name": "Maintenance Shop Bathroom Remodel",
        "customer": "Birla Carbons - USA",
        "estimate_date": "2025-05-10",
        "expiration_date": "2025-06-09",
        "total": 48765.30,
        "status": "Draft",
        "created_by": "Leland Daigle",
        "job_number": "J26047",
        "description": "Bathroom remodel scope per customer walkthrough.",
        "subtotal": 45000.0,
        "tax": 3765.30,
        "markup": 6500.0,
    },
    {
        "id": "demo-e10243",
        "estimate_number": "E-10243",
        "project_name": "Tank Farm Valve Replacement",
        "customer": "Acme Construction",
        "estimate_date": "2025-05-08",
        "expiration_date": "2025-06-07",
        "total": 128400.00,
        "status": "Approved",
        "created_by": "Mark Johnson",
        "job_number": "J26048",
        "description": "Replace valves and gaskets on tank farm lines 3–6.",
        "subtotal": 118500.0,
        "tax": 9900.0,
        "markup": 12000.0,
    },
    {
        "id": "demo-e10242",
        "estimate_number": "E-10242",
        "project_name": "Warehouse LED Retrofit",
        "customer": "Gulf Coast Industrial",
        "estimate_date": "2025-05-05",
        "expiration_date": "2025-06-04",
        "total": 67200.50,
        "status": "Sent",
        "created_by": "Leland Daigle",
        "job_number": "J26049",
        "description": "LED fixture replacement and controls.",
        "subtotal": 62000.0,
        "tax": 5200.50,
        "markup": 8000.0,
    },
    {
        "id": "demo-e10241",
        "estimate_number": "E-10241",
        "project_name": "Office Building Renovation",
        "customer": "Acme Construction",
        "estimate_date": "2025-04-28",
        "expiration_date": "2025-05-28",
        "total": 245680.50,
        "status": "Pending",
        "created_by": "Sarah Chen",
        "job_number": "J26050",
        "description": "Floors 2–3 interior renovation.",
        "subtotal": 226000.0,
        "tax": 19680.50,
        "markup": 28000.0,
    },
]

_DEMO_MATERIALS: list[dict[str, Any]] = [
    {"id": "m1", "estimate_id": "demo-e10244", "item_number": "MAT-1001", "description": "2x4x8 Pressure Treated Lumber", "category": "Lumber", "qty": 120, "unit": "EA", "unit_cost": 8.45, "total_cost": 1014.00},
    {"id": "m2", "estimate_id": "demo-e10244", "item_number": "MAT-1002", "description": "1/2\" Drywall Sheet 4x8", "category": "Drywall", "qty": 48, "unit": "EA", "unit_cost": 14.25, "total_cost": 684.00},
    {"id": "m3", "estimate_id": "demo-e10244", "item_number": "MAT-1003", "description": "PVC Pipe 2\" x 10ft", "category": "Plumbing", "qty": 24, "unit": "EA", "unit_cost": 18.90, "total_cost": 453.60},
    {"id": "m4", "estimate_id": "demo-e10244", "item_number": "MAT-1004", "description": "Ceramic Floor Tile 12x12", "category": "Tile", "qty": 200, "unit": "SF", "unit_cost": 3.25, "total_cost": 650.00},
    {"id": "m5", "estimate_id": "demo-e10244", "item_number": "MAT-1005", "description": "Toilet - Standard Grade", "category": "Fixtures", "qty": 2, "unit": "EA", "unit_cost": 285.00, "total_cost": 570.00},
]

_DEMO_INVENTORY: list[dict[str, Any]] = [
    {"id": "inv1", "sku": "SKU-442", "name": "2x4x8 PT Lumber", "category": "Lumber", "location": "Warehouse A", "department": "Field Operations", "status": "In Stock", "qty_on_hand": 240, "reorder_point": 80, "unit_cost": 8.45, "vendor": "ABC Supply"},
    {"id": "inv2", "sku": "SKU-118", "name": "1/2\" Drywall 4x8", "category": "Drywall", "location": "Warehouse A", "department": "Field Operations", "status": "Low Stock", "qty_on_hand": 32, "reorder_point": 40, "unit_cost": 14.25, "vendor": "ABC Supply"},
    {"id": "inv3", "sku": "SKU-901", "name": "PVC Cement 32oz", "category": "Plumbing", "location": "Warehouse B", "department": "Warehouse", "status": "In Stock", "qty_on_hand": 18, "reorder_point": 6, "unit_cost": 12.50, "vendor": "Industrial Pipe"},
    {"id": "inv4", "sku": "SKU-220", "name": "THHN 12 AWG Wire", "category": "Electrical", "location": "Warehouse B", "department": "Field Operations", "status": "Out of Stock", "qty_on_hand": 0, "reorder_point": 500, "unit_cost": 0.42, "vendor": "Wire World"},
]

_DEMO_ASSETS: list[dict[str, Any]] = [
    {
        "id": "ast4",
        "asset_number": "AST-1004",
        "asset_name": "Trailer - Utility 14ft",
        "category": "Trailers",
        "location": "Yard 2",
        "department": "Field Operations",
        "status": "In Service",
        "acquired_date": "2022-03-15",
        "value": 4200.00,
        "serial_number": "TRL-88421",
        "manufacturer": "Big Tex",
        "model": "14LP",
        "operator": "Chance Burgess",
        "description": "Utility trailer for material haul.",
    },
    {
        "id": "ast1",
        "asset_number": "AST-1001",
        "asset_name": "Ford F-250 Super Duty",
        "category": "Vehicles",
        "location": "Yard 1",
        "department": "Field Operations",
        "status": "In Service",
        "acquired_date": "2021-08-01",
        "value": 38500.00,
        "serial_number": "1FTFW1E85MFA12345",
        "manufacturer": "Ford",
        "model": "F-250",
        "operator": "Mark Johnson",
        "description": "Crew truck with tool boxes.",
    },
    {
        "id": "ast2",
        "asset_number": "AST-1002",
        "asset_name": "Miller Multimatic 220",
        "category": "Welding",
        "location": "Shop",
        "department": "Field Operations",
        "status": "Maintenance",
        "acquired_date": "2020-11-20",
        "value": 2800.00,
        "serial_number": "MLR-220-9921",
        "manufacturer": "Miller",
        "model": "Multimatic 220",
        "operator": "—",
        "description": "Multi-process welder.",
    },
    {
        "id": "ast3",
        "asset_number": "AST-1003",
        "asset_name": "Genie GS-1930 Scissor Lift",
        "category": "Lifts",
        "location": "Job J26047",
        "department": "Field Operations",
        "status": "In Service",
        "acquired_date": "2019-05-10",
        "value": 12500.00,
        "serial_number": "GEN-1930-4412",
        "manufacturer": "Genie",
        "model": "GS-1930",
        "operator": "Field Crew",
        "description": "19ft electric scissor lift.",
    },
]


def load_estimates() -> list[dict[str, Any]]:
    try:
        from app.services.estimates_service import list_estimates
    except ImportError:
        from services.estimates_service import list_estimates  # type: ignore
    rows, used = list_estimates(demo=list(_DEMO_ESTIMATES))
    _mark_if_demo(used)
    return rows


def get_estimate(estimate_id: str) -> dict[str, Any] | None:
    eid = str(estimate_id or "").strip()
    for e in load_estimates():
        if str(e.get("id")) == eid or str(e.get("estimate_number")) == eid:
            return e
    return None


def load_estimate_materials(estimate_id: str) -> list[dict[str, Any]]:
    eid = str(estimate_id or "").strip()
    try:
        from app.services.estimates_service import list_estimate_materials
    except ImportError:
        from services.estimates_service import list_estimate_materials  # type: ignore
    rows, used = list_estimate_materials(eid, demo=list(_DEMO_MATERIALS))
    _mark_if_demo(used)
    return rows


def materials_summary(materials: list[dict[str, Any]]) -> dict[str, float]:
    material_total = sum(float(m.get("total_cost") or 0) for m in materials)
    freight = material_total * 0.02
    tax = (material_total + freight) * 0.0825
    markup_pct = 0.14
    markup_amt = material_total * markup_pct
    return {
        "material_total": material_total,
        "freight": freight,
        "tax": tax,
        "total": material_total + freight + tax,
        "markup_pct": markup_pct,
        "markup_amt": markup_amt,
        "with_markup": material_total + freight + tax + markup_amt,
    }


def load_inventory() -> list[dict[str, Any]]:
    try:
        from app.services.inventory_service import list_inventory
    except ImportError:
        from services.inventory_service import list_inventory  # type: ignore
    rows, used = list_inventory(demo=list(_DEMO_INVENTORY))
    _mark_if_demo(used)
    return rows


def load_assets() -> list[dict[str, Any]]:
    try:
        from app.services.assets_service import list_assets
    except ImportError:
        from services.assets_service import list_assets  # type: ignore
    rows, used = list_assets(demo=list(_DEMO_ASSETS))
    _mark_if_demo(used)
    return rows


ACTIVE_EMPLOYEE_KEY = "ips_active_employee_id"

_DEMO_EMPLOYEES: list[dict[str, Any]] = [
    {
        "id": "emp-chance",
        "name": "Chance Burgess",
        "employee_number": "IPS0878",
        "email": "chance.burgess@industrialplantsolution.com",
        "role": "Supervisor",
        "position": "Supervisor",
        "trade": "Supervisor",
        "department": "Field Operations",
        "status": "Active",
        "is_employee": True,
        "phone": "337-578-4324",
        "hire_date": "2021-05-13",
        "member_since": "2021-05-13",
        "username": "cburgess",
        "last_login": "—",
    },
    {
        "id": "emp-chet",
        "name": "Chet Breaux",
        "employee_number": "IPS5197",
        "email": "chet.breaux@industrialplantsolution.com",
        "role": "Supervisor",
        "position": "Supervisor",
        "trade": "Supervisor",
        "department": "Field Operations",
        "status": "Active",
        "is_employee": True,
        "phone": "337-577-3944",
        "hire_date": "2020-07-26",
        "member_since": "2020-07-26",
        "username": "cbreaux",
        "last_login": "—",
    },
    {
        "id": "emp-titus",
        "name": "Titus Guilbeaux",
        "employee_number": "IPS9417",
        "email": "gkaylym@gmail.com",
        "role": "General Laborer",
        "position": "General Laborer",
        "trade": "General Laborer",
        "department": "Field Operations",
        "status": "Active",
        "is_employee": True,
        "phone": "337-241-2924",
        "hire_date": "2023-05-15",
        "member_since": "2023-05-15",
        "username": "tguilbeaux",
        "last_login": "—",
    },
    {
        "id": "emp-leland",
        "name": "Leland Daigle",
        "employee_number": "IPS0001",
        "email": "leland@industrialplantsolution.com",
        "role": "Administrator",
        "position": "Administrator",
        "trade": "Office",
        "department": "Administration",
        "status": "Active",
        "is_employee": False,
        "phone": "(337) 555-0100",
        "hire_date": "2015-01-10",
        "member_since": "2015-01-10",
        "username": "ldaigle",
        "last_login": "2025-05-18 09:01",
    },
]

_DEMO_CERTIFICATIONS: list[dict[str, Any]] = [
    {"id": "cert1", "employee_id": "emp-chance", "cert_type": "TWIC", "cert_number": "TWIC-88421", "issuer": "TSA", "issue_date": "2023-01-15", "expiration_date": "2028-01-14", "status": "Active", "notes": ""},
    {"id": "cert2", "employee_id": "emp-chance", "cert_type": "OSHA 30", "cert_number": "OSHA-9921", "issuer": "OSHA", "issue_date": "2022-06-01", "expiration_date": "2025-06-15", "status": "Expiring Soon", "notes": "Renewal scheduled"},
    {"id": "cert3", "employee_id": "emp-chet", "cert_type": "Forklift", "cert_number": "FL-4412", "issuer": "IPS Safety", "issue_date": "2021-03-10", "expiration_date": "2024-03-09", "status": "Expired", "notes": "Retest required"},
    {"id": "cert4", "employee_id": "emp-leland", "cert_type": "First Aid / CPR", "cert_number": "FA-2201", "issuer": "Red Cross", "issue_date": "2024-01-20", "expiration_date": "2026-01-19", "status": "Active", "notes": ""},
]

_DEMO_EMPLOYEE_DOCUMENTS: list[dict[str, Any]] = [
    {"id": "doc1", "employee_id": "emp-chance", "doc_type": "Driver's License", "upload_date": "2024-08-01", "uploaded_by": "HR Admin", "expiration_date": "2027-08-01", "is_restricted": False, "file_name": "license_chance.pdf"},
    {"id": "doc2", "employee_id": "emp-chance", "doc_type": "OSHA Card", "upload_date": "2022-06-05", "uploaded_by": "HR Admin", "expiration_date": "2025-06-01", "is_restricted": False, "file_name": "osha_chance.pdf"},
    {"id": "doc3", "employee_id": "emp-chet", "doc_type": "HR Document", "upload_date": "2023-02-10", "uploaded_by": "HR Admin", "expiration_date": "", "is_restricted": True, "file_name": "performance_review.pdf"},
    {"id": "doc4", "employee_id": "emp-leland", "doc_type": "Employment Form", "upload_date": "2015-01-10", "uploaded_by": "HR Admin", "expiration_date": "", "is_restricted": True, "file_name": "i9_leland.pdf"},
]

_DEMO_COMPANY_UPDATES: list[dict[str, Any]] = [
    {"id": "cu1", "category": "HR Updates", "title": "New Health Insurance Coverage Effective June 1", "body": "Updated medical plan options and enrollment deadlines.", "date": "2025-05-15", "pinned": True, "is_new": True},
    {"id": "cu2", "category": "Safety Alerts", "title": "Heat Stress Prevention Reminder", "body": "Mandatory hydration breaks when heat index exceeds 90°F.", "date": "2025-05-14", "pinned": True, "is_new": True},
    {"id": "cu3", "category": "Events", "title": "Company BBQ — May 20", "body": "Join us at the shop at 5 PM. Families welcome.", "date": "2025-05-12", "pinned": False, "is_new": False},
    {"id": "cu4", "category": "Announcements", "title": "Q2 Safety Award Winners", "body": "Congratulations to the Field Operations crew.", "date": "2025-05-10", "pinned": False, "is_new": False},
    {"id": "cu5", "category": "Project Updates", "title": "J26047 Milestone Complete", "body": "Rough-in inspection passed on schedule.", "date": "2025-05-08", "pinned": False, "is_new": False},
]

_DEMO_EVENTS: list[dict[str, Any]] = [
    {"id": "ev1", "title": "Company BBQ", "date": "2025-05-20", "time": "5:00 PM", "location": "IPS Shop"},
    {"id": "ev2", "title": "Safety Stand-down", "date": "2025-05-22", "time": "7:00 AM", "location": "Yard 1"},
]


def load_employees() -> list[dict[str, Any]]:
    try:
        from app.services.employees_service import list_employees
    except ImportError:
        from services.employees_service import list_employees  # type: ignore
    rows, used = list_employees(demo=list(_DEMO_EMPLOYEES))
    _mark_if_demo(used)
    return rows


def get_employee(employee_id: str) -> dict[str, Any] | None:
    eid = str(employee_id or "").strip()
    for e in load_employees():
        if str(e.get("id")) == eid:
            return e
    return None


def load_certifications(employee_id: str) -> list[dict[str, Any]]:
    eid = str(employee_id or "").strip()
    try:
        from app.services.employees_service import list_certifications
    except ImportError:
        from services.employees_service import list_certifications  # type: ignore
    demo = [c for c in _DEMO_CERTIFICATIONS if c.get("employee_id") == eid]
    if not demo and eid:
        demo = [c for c in _DEMO_CERTIFICATIONS if eid == "emp-chance"][:2]
    rows, used = list_certifications(eid, demo=demo or list(_DEMO_CERTIFICATIONS)[:2])
    _mark_if_demo(used)
    return rows


def load_employee_documents(employee_id: str, *, role: str = "admin") -> list[dict[str, Any]]:
    eid = str(employee_id or "").strip()
    rows = _fetch_table("employee_documents", limit=500)
    out: list[dict[str, Any]] = []
    if rows:
        out = [r for r in rows if str(r.get("employee_id") or "") == eid]
    if not out:
        out = [d for d in _DEMO_EMPLOYEE_DOCUMENTS if d.get("employee_id") == eid]
        if not out and eid:
            out = [d for d in _DEMO_EMPLOYEE_DOCUMENTS if d.get("employee_id") == "emp-chance"]
    if role != "admin":
        out = [d for d in out if not bool(d.get("is_restricted"))]
    return out


def load_documents_hub(*, role: str = "admin") -> list[dict[str, Any]]:
    try:
        from app.services.documents_service import list_documents_hub
    except ImportError:
        from services.documents_service import list_documents_hub  # type: ignore
    rows, used = list_documents_hub(role=role, demo=list(_DEMO_DOCUMENTS_HUB))
    _mark_if_demo(used)
    return rows


def load_company_updates(*, category: str = "All Updates") -> list[dict[str, Any]]:
    try:
        from app.services.updates_service import list_company_updates
    except ImportError:
        from services.updates_service import list_company_updates  # type: ignore
    rows, used = list_company_updates(category=category, demo=list(_DEMO_COMPANY_UPDATES))
    _mark_if_demo(used)
    try:
        from app.components.install_share import with_welcome_install_update
    except ImportError:
        from components.install_share import with_welcome_install_update  # type: ignore
    return with_welcome_install_update(rows)


def load_recent_company_updates(*, limit: int = 5) -> list[dict[str, Any]]:
    """Human company announcements for the Dashboard (not system activity events)."""
    try:
        from app.components.company_updates_feed import (
            dashboard_update_visible,
            sort_dashboard_updates,
        )
    except ImportError:
        from components.company_updates_feed import (  # type: ignore
            dashboard_update_visible,
            sort_dashboard_updates,
        )
    visible = [row for row in load_company_updates() if dashboard_update_visible(row)]
    return sort_dashboard_updates(visible)[: max(1, int(limit))]


def demo_update_metrics() -> dict[str, int]:
    updates = load_company_updates()
    return {
        "unread": sum(1 for u in updates if u.get("is_new")),
        "pinned": sum(1 for u in updates if u.get("pinned")),
        "events": len(load_upcoming_events()),
        "all": len(updates),
    }


def load_upcoming_events() -> list[dict[str, Any]]:
    rows = _fetch_table("company_events", limit=50)
    if rows:
        return rows
    return list(_DEMO_EVENTS)


def load_all_certifications() -> list[dict[str, Any]]:
    try:
        from app.services.employees_service import list_all_certifications
    except ImportError:
        from services.employees_service import list_all_certifications  # type: ignore
    employees = load_employees()
    demo = []
    for c in _DEMO_CERTIFICATIONS:
        emp = get_employee(str(c.get("employee_id") or "")) or {}
        demo.append({**c, "employee_name": str(emp.get("name") or "—")})
    rows, used = list_all_certifications(demo=demo, employees=employees)
    _mark_if_demo(used)
    return rows


def certification_alerts(certs: list[dict[str, Any]]) -> tuple[int, int]:
    expired = sum(1 for c in certs if str(c.get("status", "")).lower() == "expired")
    expiring = sum(1 for c in certs if str(c.get("status", "")).lower() == "expiring soon")
    return expired, expiring


def job_options_for_timekeeping() -> list[str]:
    try:
        from app.pages.timekeeping import _assignment_options_for_timekeeping

        return _assignment_options_for_timekeeping()
    except ImportError:
        from pages.timekeeping import _assignment_options_for_timekeeping  # type: ignore

        return _assignment_options_for_timekeeping()


def load_tasks() -> list[dict[str, Any]]:
    try:
        from app.services.tasks_service import list_tasks
    except ImportError:
        from services.tasks_service import list_tasks  # type: ignore
    rows, used = list_tasks(demo=list(_DEMO_TASKS))
    _mark_if_demo(used)
    return rows


def get_task(task_id: str) -> dict[str, Any] | None:
    tid = str(task_id or "").strip()
    for t in load_tasks():
        if str(t.get("id")) == tid:
            return t
    return None


def load_timekeeping_summaries(week_start: date) -> list[dict[str, Any]]:
    try:
        from app.services.timekeeping_service import list_timekeeping_summaries
    except ImportError:
        from services.timekeeping_service import list_timekeeping_summaries  # type: ignore
    demo = [
        {"id": "emp-chance", "name": "Chance Burgess", "department": "Field Operations", "week_start": week_start.isoformat(), "st_total": 38.5, "ot_total": 4.0, "dt_total": 0.0, "status": "Pending"},
        {"id": "emp-mark", "name": "Mark Johnson", "department": "Field Operations", "week_start": week_start.isoformat(), "st_total": 40.0, "ot_total": 2.5, "dt_total": 0.0, "status": "Approved"},
        {"id": "emp-sarah", "name": "Sarah Chen", "department": "Project Management", "week_start": week_start.isoformat(), "st_total": 32.0, "ot_total": 0.0, "dt_total": 0.0, "status": "Approved"},
        {"id": "emp-leland", "name": "Leland Daigle", "department": "Administration", "week_start": week_start.isoformat(), "st_total": 40.0, "ot_total": 0.0, "dt_total": 0.0, "status": "Approved"},
    ]
    rows, used = list_timekeeping_summaries(week_start, demo=demo)
    _mark_if_demo(used)
    return rows


def default_weekly_grid(employee_id: str, week_start: date) -> list[dict[str, Any]]:
    days = week_dates(week_start)
    job_opts = job_options_for_timekeeping()
    default_job = job_opts[1] if len(job_opts) > 1 else job_opts[0]
    grid = []
    for i, d in enumerate(days):
        grid.append({
            "day": d.strftime("%A"),
            "date": d.isoformat(),
            "job": default_job if i < 5 else "— Select assignment —",
            "st": 8.0 if i < 5 else 0.0,
            "ot": 0.0 if i < 4 else (4.0 if i == 4 else 0.0),
            "dt": 0.0,
            "notes": "" if i != 0 else "Shop mobilization",
        })
    if employee_id == "emp-mark":
        grid[4]["ot"] = 2.5
    return grid


_DEMO_DOCUMENTS_HUB: list[dict[str, Any]] = [
    {
        "id": "dh1",
        "file_name": "J26047_Contract_Signed.pdf",
        "doc_type": "Contract",
        "linked_module": "Jobs",
        "linked_ref": "J26047 — Maintenance Shop Bathroom Remodel",
        "upload_date": "2025-04-01",
        "uploaded_by": "Sarah Chen",
        "expiration_date": "",
        "is_restricted": False,
    },
    {
        "id": "dh2",
        "file_name": "EST-24018_Proposal.pdf",
        "doc_type": "Specification",
        "linked_module": "Estimates",
        "linked_ref": "EST-24018 — Bayou Tank Farm",
        "upload_date": "2025-03-12",
        "uploaded_by": "Leland Daigle",
        "expiration_date": "",
        "is_restricted": False,
    },
    {
        "id": "dh3",
        "file_name": "Forklift_Inspection_A042.pdf",
        "doc_type": "Safety Document",
        "linked_module": "Assets",
        "linked_ref": "A-042 — Toyota Forklift",
        "upload_date": "2025-05-01",
        "uploaded_by": "Mark Johnson",
        "expiration_date": "2026-05-01",
        "is_restricted": False,
    },
    {
        "id": "dh4",
        "file_name": "license_chance.pdf",
        "doc_type": "Driver's License",
        "linked_module": "Employees",
        "linked_ref": "Chance Burgess",
        "upload_date": "2024-08-01",
        "uploaded_by": "HR Admin",
        "expiration_date": "2027-08-01",
        "is_restricted": False,
    },
    {
        "id": "dh5",
        "file_name": "TWIC-88421.pdf",
        "doc_type": "TWIC Card",
        "linked_module": "Certifications",
        "linked_ref": "Chance Burgess — TWIC",
        "upload_date": "2023-01-15",
        "uploaded_by": "HR Admin",
        "expiration_date": "2028-01-14",
        "is_restricted": False,
    },
    {
        "id": "dh6",
        "file_name": "SKU-8842_MSDS.pdf",
        "doc_type": "Safety Document",
        "linked_module": "Inventory",
        "linked_ref": "SKU-8842 — PVC Cement",
        "upload_date": "2024-11-20",
        "uploaded_by": "Warehouse",
        "expiration_date": "",
        "is_restricted": False,
    },
    {
        "id": "dh7",
        "file_name": "Heat_Stress_Policy.pdf",
        "doc_type": "HR Document",
        "linked_module": "Company Updates",
        "linked_ref": "Heat Stress Prevention Reminder",
        "upload_date": "2025-05-14",
        "uploaded_by": "Safety",
        "expiration_date": "",
        "is_restricted": True,
    },
    {
        "id": "dh8",
        "file_name": "performance_review.pdf",
        "doc_type": "HR Document",
        "linked_module": "Employees",
        "linked_ref": "Mark Johnson",
        "upload_date": "2023-02-10",
        "uploaded_by": "HR Admin",
        "expiration_date": "",
        "is_restricted": True,
    },
]

_DEMO_TASKS: list[dict[str, Any]] = [
    {
        "id": "task1",
        "title": "Approve weekly timekeeping — Field Ops",
        "status": "Open",
        "priority": "High",
        "assigned_to": "Mark Johnson",
        "linked_job": "J26047 — Maintenance Shop Bathroom Remodel",
        "linked_estimate": "— None —",
        "due_date": "2025-05-20",
        "description": "Review and approve pending timecards for the week ending May 18.",
        "activity": [
            {"when": "2025-05-18 09:00", "who": "System", "note": "Task created from timekeeping workflow."},
        ],
    },
    {
        "id": "task2",
        "title": "Order materials for EST-24018",
        "status": "In Progress",
        "priority": "Medium",
        "assigned_to": "Sarah Chen",
        "linked_job": "— None —",
        "linked_estimate": "EST-24018 — Bayou Tank Farm",
        "due_date": "2025-05-22",
        "description": "Release PO for long-lead electrical items on estimate.",
        "activity": [
            {"when": "2025-05-17 14:30", "who": "Sarah Chen", "note": "Vendor quote received from Ferguson."},
        ],
    },
    {
        "id": "task3",
        "title": "Forklift annual inspection",
        "status": "Blocked",
        "priority": "Urgent",
        "assigned_to": "Chance Burgess",
        "linked_job": "— None —",
        "linked_estimate": "— None —",
        "due_date": "2025-05-19",
        "description": "Schedule inspection before asset returns to service.",
        "activity": [
            {"when": "2025-05-16 11:00", "who": "Mark Johnson", "note": "Waiting on vendor availability."},
        ],
    },
    {
        "id": "task4",
        "title": "Update safety orientation deck",
        "status": "Done",
        "priority": "Low",
        "assigned_to": "Leland Daigle",
        "linked_job": "— None —",
        "linked_estimate": "— None —",
        "due_date": "2025-05-10",
        "description": "Refresh site orientation slides for Q2.",
        "activity": [
            {"when": "2025-05-10 16:00", "who": "Leland Daigle", "note": "Published to document hub."},
        ],
    },
]


def task_job_options() -> list[str]:
    opts = ["— None —"]
    for j in load_jobs():
        num = str(j.get("job_number") or "")
        name = str(j.get("job_name") or "")
        if num:
            opts.append(f"{num} — {name}")
    return opts


def task_estimate_options() -> list[str]:
    opts = ["— None —"]
    for e in load_estimates():
        num = str(e.get("estimate_number") or e.get("number") or "")
        name = str(e.get("project_name") or e.get("name") or e.get("title") or "")
        if num:
            opts.append(f"{num} — {name}")
    return opts


def document_link_ref_options(module: str) -> list[str]:
    """Linked-record dropdown options for the documents hub."""
    mod = str(module or "").strip()
    if mod == "Jobs":
        return [f"{j.get('job_number')} — {j.get('job_name')}" for j in load_jobs() if j.get("job_number")]
    if mod == "Estimates":
        return [
            f"{e.get('estimate_number')} — {e.get('project_name')}"
            for e in load_estimates()
            if e.get("estimate_number")
        ]
    if mod == "Assets":
        return [
            f"{a.get('asset_number')} — {a.get('asset_name')}"
            for a in load_assets()
            if a.get("asset_number")
        ]
    if mod == "Employees":
        return [str(e.get("name") or "") for e in load_employees() if e.get("name")]
    if mod == "Certifications":
        out: list[str] = []
        for c in load_all_certifications():
            name = str(c.get("employee_name") or "").strip()
            cert_type = str(c.get("cert_type") or "").strip()
            if name and cert_type:
                out.append(f"{name} — {cert_type}")
        return out
    if mod == "Inventory":
        return [f"{i.get('sku')} — {i.get('name')}" for i in load_inventory() if i.get("sku")]
    if mod == "Company Updates":
        return [str(u.get("title") or "") for u in load_company_updates(category="All Updates") if u.get("title")]
    return []


def task_assignee_options() -> list[str]:
    return [str(e.get("name") or "") for e in load_employees() if e.get("name")]


def demo_report_job_profitability() -> list[dict[str, Any]]:
    jobs = load_jobs()
    if jobs:
        rows = []
        for j in jobs[:12]:
            rev = float(j.get("awarded_amount") or j.get("revenue") or 0)
            if not rev:
                rev = float(j.get("progress") or 0) * 1000
            cost = rev * 0.78 if rev else 0
            margin = ((rev - cost) / rev * 100) if rev else 0
            rows.append(
                {
                    "job_number": j.get("job_number"),
                    "job_name": j.get("job_name"),
                    "revenue": rev or 85000,
                    "cost": cost or 66000,
                    "margin_pct": round(margin, 1) if rev else 22.0,
                }
            )
        if rows:
            return rows
    return [
        {"job_number": "J26047", "job_name": "Maintenance Shop Bathroom Remodel", "revenue": 185000, "cost": 142500, "margin_pct": 23.0},
        {"job_number": "J26012", "job_name": "Tank Farm Piping", "revenue": 420000, "cost": 358200, "margin_pct": 14.7},
        {"job_number": "J25988", "job_name": "Warehouse LED Retrofit", "revenue": 96000, "cost": 71200, "margin_pct": 25.8},
    ]


def demo_report_labor_by_job() -> list[dict[str, Any]]:
    jobs = load_jobs()
    if jobs:
        return [
            {
                "job_number": j.get("job_number"),
                "st_hours": 40.0 + (int(j.get("progress") or 0) % 20) * 5,
                "ot_hours": 4.0,
                "dt_hours": 0.0,
                "total_hours": 44.0 + (int(j.get("progress") or 0) % 20) * 5,
            }
            for j in jobs[:10]
            if j.get("job_number")
        ]
    return [
        {"job_number": "J26047", "st_hours": 312.5, "ot_hours": 28.0, "dt_hours": 0.0, "total_hours": 340.5},
        {"job_number": "J26012", "st_hours": 890.0, "ot_hours": 112.5, "dt_hours": 16.0, "total_hours": 1018.5},
        {"job_number": "J25988", "st_hours": 156.0, "ot_hours": 8.0, "dt_hours": 0.0, "total_hours": 164.0},
    ]


def demo_report_labor_by_employee() -> list[dict[str, Any]]:
    from datetime import date as _date

    summaries = load_timekeeping_summaries(_date.today())
    if summaries:
        return [
            {
                "employee": s.get("name"),
                "st_hours": float(s.get("st_total") or 0),
                "ot_hours": float(s.get("ot_total") or 0),
                "dt_hours": float(s.get("dt_total") or 0),
                "total_hours": float(s.get("st_total") or 0)
                + float(s.get("ot_total") or 0)
                + float(s.get("dt_total") or 0),
            }
            for s in summaries
        ]
    return [
        {"employee": "Chance Burgess", "st_hours": 38.5, "ot_hours": 4.0, "dt_hours": 0.0, "total_hours": 42.5},
        {"employee": "Mark Johnson", "st_hours": 40.0, "ot_hours": 2.5, "dt_hours": 0.0, "total_hours": 42.5},
        {"employee": "Sarah Chen", "st_hours": 32.0, "ot_hours": 0.0, "dt_hours": 0.0, "total_hours": 32.0},
    ]


def demo_report_inventory_value() -> list[dict[str, Any]]:
    inv = load_inventory()
    if inv:
        by_cat: dict[str, dict[str, Any]] = {}
        for item in inv:
            cat = str(item.get("category") or "Uncategorized")
            bucket = by_cat.setdefault(cat, {"category": cat, "sku_count": 0, "on_hand_value": 0.0})
            bucket["sku_count"] += 1
            bucket["on_hand_value"] += float(item.get("qty_on_hand") or 0) * float(item.get("unit_cost") or 0)
        return list(by_cat.values())
    return [
        {"category": "Electrical", "sku_count": 142, "on_hand_value": 48200.0},
        {"category": "Plumbing", "sku_count": 98, "on_hand_value": 31500.0},
        {"category": "Safety", "sku_count": 56, "on_hand_value": 12800.0},
    ]


def demo_report_low_stock() -> list[dict[str, Any]]:
    inv = load_inventory()
    low = [i for i in inv if str(i.get("status", "")).lower() == "low stock"]
    if low:
        return [
            {"sku": i.get("sku"), "name": i.get("name"), "qty_on_hand": i.get("qty_on_hand"), "reorder_point": i.get("reorder_point", 10)}
            for i in low
        ]
    return [
        {"sku": "SKU-4421", "name": "3/4\" EMT Conduit", "qty_on_hand": 8, "reorder_point": 25},
        {"sku": "SKU-8842", "name": "PVC Cement", "qty_on_hand": 3, "reorder_point": 12},
    ]


def demo_report_asset_maintenance() -> list[dict[str, Any]]:
    return [
        {"asset_number": "A-042", "name": "Toyota Forklift", "next_service": "2025-05-25", "status": "Scheduled"},
        {"asset_number": "T-018", "name": "Tool Trailer A", "next_service": "2025-06-01", "status": "Due Soon"},
    ]


def demo_report_certs_expiring() -> list[dict[str, Any]]:
    certs = load_all_certifications()
    exp = [c for c in certs if str(c.get("status", "")).lower() in {"expired", "expiring soon"}]
    if exp:
        return [
            {
                "employee_name": c.get("employee_name"),
                "cert_type": c.get("cert_type"),
                "expiration_date": c.get("expiration_date"),
                "status": c.get("status"),
            }
            for c in exp
        ]
    return [
        {"employee_name": "Chance Burgess", "cert_type": "OSHA 30", "expiration_date": "2025-06-15", "status": "Expiring Soon"},
        {"employee_name": "Mark Johnson", "cert_type": "Forklift", "expiration_date": "2024-03-09", "status": "Expired"},
    ]


def demo_report_open_estimates() -> list[dict[str, Any]]:
    est = load_estimates()
    open_est = [e for e in est if str(e.get("status", "")) in {"Draft", "Sent", "Pending"}]
    if open_est:
        return [
            {
                "estimate_number": e.get("estimate_number") or e.get("number"),
                "customer": e.get("customer"),
                "status": e.get("status"),
                "total": e.get("total") or e.get("amount"),
            }
            for e in open_est[:8]
        ]
    return [
        {"estimate_number": "EST-24018", "customer": "Bayou Petrochemical", "status": "Pending", "total": 285000},
        {"estimate_number": "EST-24022", "customer": "Coastal Refining", "status": "Sent", "total": 142500},
    ]


def demo_report_completed_jobs() -> list[dict[str, Any]]:
    jobs = load_jobs()
    done = [j for j in jobs if str(j.get("status", "")).lower() == "completed"]
    if done:
        return [
            {"job_number": j.get("job_number"), "job_name": j.get("job_name"), "end_date": j.get("end_date"), "customer": j.get("customer")}
            for j in done
        ]
    return [
        {"job_number": "J25801", "job_name": "Office HVAC Upgrade", "end_date": "2025-03-30", "customer": "IPS Internal"},
    ]


def demo_report_timekeeping_summary() -> list[dict[str, Any]]:
    from datetime import date as _date

    return load_timekeeping_summaries(_date.today())


def persist_lookup_table(table_label: str, values: list[str]) -> tuple[bool, str]:
    """Save admin lookup table values (Supabase with session fallback)."""
    try:
        from app.services.lookup_service import save_lookup_for_label
    except ImportError:
        from services.lookup_service import save_lookup_for_label  # type: ignore
    return save_lookup_for_label(table_label, values)


def lookup_options(slug: str) -> list[str]:
    """Dropdown values from Supabase lookup tables with constants fallback."""
    try:
        from app.services.lookup_service import load_lookup_values
    except ImportError:
        from services.lookup_service import load_lookup_values  # type: ignore
    values, _ = load_lookup_values(slug)
    return values


def _persist_result(result: Any, *, success: str) -> tuple[bool, str]:
    """Return (ok, message) for UI feedback."""
    try:
        from app.services.repository import user_facing_error
    except ImportError:
        from services.repository import user_facing_error  # type: ignore
    err = user_facing_error(result)
    if err:
        return False, err
    return True, success


_DEMO_SAVE_MSG = "Cannot save demo data to Supabase. Create a new record instead."


def _demo_blocked(row_id: str | None) -> bool:
    try:
        from app.pages.modules._crud import is_demo_id
    except ImportError:
        from pages.modules._crud import is_demo_id  # type: ignore
    return is_demo_id(row_id)


def employee_options(*, include_blank: bool = True) -> list[str]:
    names = sorted({str(e.get("name") or "") for e in load_employees() if e.get("name")})
    if include_blank:
        return ["— Select —", *names]
    return names


_DEMO_CUSTOMERS: list[dict[str, Any]] = [
    {
        "id": "demo-c-birla",
        "customer_name": "Birla Carbons - USA",
        "address": "123 Industrial Park Rd",
        "city": "Alexandria",
        "state": "LA",
        "zip": "71301",
        "is_active": True,
        "notes": "Primary petrochemical account.",
    },
    {
        "id": "demo-c-acme",
        "customer_name": "Acme Construction",
        "address": "4500 Commerce Blvd",
        "city": "Lake Charles",
        "state": "LA",
        "zip": "70601",
        "is_active": True,
        "notes": "",
    },
    {
        "id": "demo-c-gulf",
        "customer_name": "Gulf Coast Industrial",
        "address": "800 Harbor Way",
        "city": "Houma",
        "state": "LA",
        "zip": "70360",
        "is_active": True,
        "notes": "",
    },
    {
        "id": "demo-c-bayou",
        "customer_name": "Bayou Petrochemical",
        "address": "2100 Plant Rd",
        "city": "Baton Rouge",
        "state": "LA",
        "zip": "70802",
        "is_active": False,
        "notes": "Inactive — reactivate when contract renews.",
    },
]

_DEMO_CUSTOMER_LOCATIONS: list[dict[str, Any]] = [
    {
        "id": "demo-loc-1",
        "customer_id": "demo-c-birla",
        "site_name": "Main Plant",
        "address_line1": "123 Industrial Park Rd",
        "city": "Alexandria",
        "state": "LA",
        "zip": "71301",
        "is_active": True,
    },
]

_DEMO_CUSTOMER_CONTACTS: list[dict[str, Any]] = [
    {
        "id": "demo-cc-1",
        "customer_id": "demo-c-birla",
        "contact_name": "Sarah Chen",
        "title": "Project Manager",
        "email": "sarah.chen@example.com",
        "phone": "(318) 555-0101",
        "is_active": True,
        "is_primary": True,
    },
]


def load_customers() -> list[dict[str, Any]]:
    try:
        from app.services.customers_service import list_customers
    except ImportError:
        from services.customers_service import list_customers  # type: ignore
    rows, used = list_customers(demo=list(_DEMO_CUSTOMERS))
    _mark_if_demo(used)
    return rows


def get_customer(customer_id: str) -> dict[str, Any] | None:
    cid = str(customer_id or "").strip()
    return next((c for c in load_customers() if str(c.get("id")) == cid), None)


def load_customer_locations(customer_id: str) -> list[dict[str, Any]]:
    try:
        from app.services.customers_service import list_customer_locations
    except ImportError:
        from services.customers_service import list_customer_locations  # type: ignore
    rows, used = list_customer_locations(customer_id, demo=list(_DEMO_CUSTOMER_LOCATIONS))
    if used:
        _mark_if_demo(True)
    return rows


def load_customer_contacts(customer_id: str) -> list[dict[str, Any]]:
    try:
        from app.services.customers_service import list_customer_contacts
    except ImportError:
        from services.customers_service import list_customer_contacts  # type: ignore
    rows, used = list_customer_contacts(customer_id, demo=list(_DEMO_CUSTOMER_CONTACTS))
    if used:
        _mark_if_demo(True)
    return rows


def jobs_for_customer(customer_name: str) -> list[dict[str, Any]]:
    name = str(customer_name or "").strip().lower()
    if not name:
        return []
    return [j for j in load_jobs() if str(j.get("customer") or "").strip().lower() == name]


def estimates_for_customer(customer_name: str) -> list[dict[str, Any]]:
    name = str(customer_name or "").strip().lower()
    if not name:
        return []
    return [e for e in load_estimates() if str(e.get("customer") or "").strip().lower() == name]


def customer_filter_options() -> list[str]:
    """Customers for filters — directory plus lookup seeds."""
    opts = {str(c.get("customer_name") or "").strip() for c in load_customers() if c.get("customer_name")}
    opts.update(lookup_options("customers"))
    return sorted(opts)


def persist_customer(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.customers_service import save_customer
    except ImportError:
        from services.customers_service import save_customer  # type: ignore
    return _persist_result(save_customer(ui, row_id=row_id), success="Customer saved.")


def delete_customer_row(row_id: str) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.customers_service import delete_customer
    except ImportError:
        from services.customers_service import delete_customer  # type: ignore
    return _persist_result(delete_customer(row_id), success="Customer removed.")


def persist_job(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.jobs_service import save_job
    except ImportError:
        from services.jobs_service import save_job  # type: ignore
    return _persist_result(save_job(ui, row_id=row_id), success="Job saved.")


def persist_estimate(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.estimates_service import save_estimate
    except ImportError:
        from services.estimates_service import save_estimate  # type: ignore
    return _persist_result(save_estimate(ui, row_id=row_id), success="Estimate saved.")


def persist_estimate_material(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.estimates_service import save_estimate_line_item
    except ImportError:
        from services.estimates_service import save_estimate_line_item  # type: ignore
    return _persist_result(save_estimate_line_item(ui, row_id=row_id), success="Material line saved.")


def delete_estimate_material(row_id: str) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.estimates_service import delete_estimate_line_item
    except ImportError:
        from services.estimates_service import delete_estimate_line_item  # type: ignore
    return _persist_result(delete_estimate_line_item(row_id), success="Material line removed.")


def persist_inventory(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.inventory_service import save_inventory_item
    except ImportError:
        from services.inventory_service import save_inventory_item  # type: ignore
    return _persist_result(save_inventory_item(ui, row_id=row_id), success="Inventory item saved.")


def persist_asset(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.assets_service import save_asset
    except ImportError:
        from services.assets_service import save_asset  # type: ignore
    return _persist_result(save_asset(ui, row_id=row_id), success="Asset saved.")


def persist_employee(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.employees_service import save_employee
    except ImportError:
        from services.employees_service import save_employee  # type: ignore
    return _persist_result(save_employee(ui, row_id=row_id), success="Employee saved.")


def persist_certification(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.employees_service import save_certification
    except ImportError:
        from services.employees_service import save_certification  # type: ignore
    return _persist_result(save_certification(ui, row_id=row_id), success="Certification saved.")


def persist_document(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.documents_service import save_document_hub
    except ImportError:
        from services.documents_service import save_document_hub  # type: ignore
    return _persist_result(save_document_hub(ui, row_id=row_id), success="Document saved.")


def persist_company_update(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.updates_service import save_company_update
    except ImportError:
        from services.updates_service import save_company_update  # type: ignore
    return _persist_result(save_company_update(ui, row_id=row_id), success="Update published.")


def persist_task(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.tasks_service import save_task
    except ImportError:
        from services.tasks_service import save_task  # type: ignore
    return _persist_result(save_task(ui, row_id=row_id), success="Task saved.")


def delete_job(row_id: str) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.jobs_service import delete_job as _del
    except ImportError:
        from services.jobs_service import delete_job as _del  # type: ignore
    return _persist_result(_del(row_id), success="Job deleted.")


def delete_estimate(row_id: str) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.estimates_service import delete_estimate as _del
    except ImportError:
        from services.estimates_service import delete_estimate as _del  # type: ignore
    return _persist_result(_del(row_id), success="Estimate deleted.")


def delete_inventory(row_id: str) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.inventory_service import delete_inventory_item as _del
    except ImportError:
        from services.inventory_service import delete_inventory_item as _del  # type: ignore
    return _persist_result(_del(row_id), success="Item deleted.")


def delete_asset(row_id: str) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.assets_service import delete_asset as _del
    except ImportError:
        from services.assets_service import delete_asset as _del  # type: ignore
    return _persist_result(_del(row_id), success="Asset deleted.")


def delete_company_update(row_id: str) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.updates_service import delete_company_update as _del
    except ImportError:
        from services.updates_service import delete_company_update as _del  # type: ignore
    return _persist_result(_del(row_id), success="Update removed.")


def persist_timekeeping_week(employee_id: str, week_start: date, summary: dict[str, Any]) -> tuple[bool, str]:
    if _demo_blocked(employee_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.timekeeping_service import save_timekeeping_week
    except ImportError:
        from services.timekeeping_service import save_timekeeping_week  # type: ignore
    return _persist_result(
        save_timekeeping_week(employee_id, week_start, summary),
        success="Timekeeping saved.",
    )


def persist_timekeeping_days(
    employee_id: str,
    week_start: date,
    grid: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Upsert daily rows after week summary save."""
    if _demo_blocked(employee_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.timekeeping_service import save_timekeeping_day
    except ImportError:
        from services.timekeeping_service import save_timekeeping_day  # type: ignore
    ws = week_start.isoformat()
    errors: list[str] = []
    for row in grid:
        work_date = str(row.get("date") or "")[:10]
        if not work_date:
            continue
        ui = {
            "employee_id": employee_id,
            "week_start": ws,
            "work_date": work_date,
            "job_label": row.get("job") or "",
            "st_hours": row.get("st") or 0,
            "ot_hours": row.get("ot") or 0,
            "dt_hours": row.get("dt") or 0,
            "notes": row.get("notes") or "",
        }
        res = save_timekeeping_day(ui, row_id=str(row.get("day_id") or "") or None)
        err = _persist_result(res, success="")
        if err[0] is False and err[1]:
            errors.append(err[1])
    if errors:
        return False, errors[0]
    return True, "Daily entries saved."
