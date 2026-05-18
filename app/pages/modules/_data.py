"""Load module data from Supabase with demo fallbacks."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

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
        "status": "Scheduled",
        "start_date": "2025-06-01",
        "end_date": "2025-10-30",
        "progress": 0,
        "description": "Replace aging piping and valves in tank farm area.",
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
]


def _fetch_table(name: str, *, order_by: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    try:
        try:
            from app.db import fetch_table
        except ImportError:
            from db import fetch_table  # type: ignore
        return fetch_table(name, limit=limit, order_by=order_by) or []
    except Exception:
        return []


def _normalize_job(row: dict[str, Any]) -> dict[str, Any]:
    jid = str(row.get("id") or row.get("job_id") or "").strip()
    num = str(row.get("job_number") or row.get("number") or jid[:8] or "—")
    return {
        "id": jid or num,
        "job_number": num,
        "job_name": str(row.get("job_name") or row.get("name") or row.get("description") or "—"),
        "customer": str(row.get("customer_name") or row.get("customer") or "—"),
        "estimate_number": str(row.get("estimate_number") or row.get("quote_number") or "—"),
        "supervisor": str(row.get("supervisor") or row.get("supervisor_name") or "—"),
        "status": str(row.get("status") or "Draft"),
        "start_date": str(row.get("start_date") or "")[:10],
        "end_date": str(row.get("end_date") or "")[:10],
        "progress": int(row.get("progress") or row.get("percent_complete") or 0),
        "description": str(row.get("notes") or row.get("description") or ""),
    }


def load_jobs() -> list[dict[str, Any]]:
    try:
        from app.services.phase2_modules_service import list_jobs
    except ImportError:
        from services.phase2_modules_service import list_jobs  # type: ignore
    rows, _ = list_jobs(demo=list(_DEMO_JOBS))
    return rows


def load_dashboard_kpis() -> dict[str, Any]:
    estimates = _fetch_table("estimates", limit=200)
    jobs = load_jobs()
    if estimates or jobs:
        open_est = sum(1 for e in estimates if str(e.get("status", "")).lower() in {"draft", "sent", "pending"})
        active_jobs = sum(1 for j in jobs if str(j.get("status", "")).lower() in {"active", "in progress"})
        return {
            "total_sales": 245680.50,
            "open_invoices": 125430.25,
            "active_jobs": active_jobs or len([j for j in jobs if j.get("status")]),
            "open_estimates": open_est or len(estimates),
            "inventory_value": 98765.30,
        }
    return {
        "total_sales": 245680.50,
        "open_invoices": 125430.25,
        "active_jobs": 18,
        "open_estimates": 14,
        "inventory_value": 98765.30,
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


def demo_deadlines() -> list[dict[str, str]]:
    today = date.today()
    return [
        {"title": "J26047 — Rough-in inspection", "date": (today + timedelta(days=3)).isoformat(), "badge": "3 days", "level": "danger"},
        {"title": "E-10244 — Estimate expiration", "date": (today + timedelta(days=8)).isoformat(), "badge": "8 days", "level": "warn"},
        {"title": "J26048 — Mobilization", "date": (today + timedelta(days=14)).isoformat(), "badge": "14 days", "level": "ok"},
    ]


def demo_recent_jobs(limit: int = 5) -> list[dict[str, Any]]:
    return load_jobs()[:limit]


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


def _normalize_estimate(row: dict[str, Any]) -> dict[str, Any]:
    eid = str(row.get("id") or "").strip()
    num = str(row.get("quote_number") or row.get("estimate_number") or eid[:8] or "—")
    return {
        "id": eid or num,
        "estimate_number": num,
        "project_name": str(row.get("project_name") or row.get("job_name") or row.get("title") or "—"),
        "customer": str(row.get("customer_name") or row.get("customer") or "—"),
        "estimate_date": str(row.get("estimate_date") or row.get("created_at") or "")[:10],
        "expiration_date": str(row.get("expiration_date") or row.get("valid_through") or "")[:10],
        "total": float(row.get("total") or row.get("grand_total") or 0),
        "status": str(row.get("status") or "Draft"),
        "created_by": str(row.get("created_by") or row.get("prepared_by") or "—"),
        "job_number": str(row.get("job_number") or "—"),
        "description": str(row.get("description") or row.get("notes") or ""),
        "subtotal": float(row.get("subtotal") or row.get("total") or 0),
        "tax": float(row.get("tax") or 0),
        "markup": float(row.get("markup") or 0),
    }


def load_estimates() -> list[dict[str, Any]]:
    try:
        from app.services.phase2_modules_service import list_estimates
    except ImportError:
        from services.phase2_modules_service import list_estimates  # type: ignore
    rows, _ = list_estimates(demo=list(_DEMO_ESTIMATES))
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
        from app.services.phase2_modules_service import list_estimate_materials
    except ImportError:
        from services.phase2_modules_service import list_estimate_materials  # type: ignore
    rows, _ = list_estimate_materials(eid, demo=list(_DEMO_MATERIALS))
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


def _normalize_inventory(row: dict[str, Any]) -> dict[str, Any]:
    iid = str(row.get("id") or "").strip()
    sku = str(row.get("sku") or row.get("item_number") or iid[:8])
    return {
        "id": iid or sku,
        "sku": sku,
        "name": str(row.get("name") or row.get("description") or "—"),
        "category": str(row.get("category") or "—"),
        "location": str(row.get("location") or "—"),
        "department": str(row.get("department") or "—"),
        "status": str(row.get("status") or "In Stock"),
        "qty_on_hand": int(row.get("qty_on_hand") or row.get("quantity") or 0),
        "reorder_point": int(row.get("reorder_point") or 0),
        "unit_cost": float(row.get("unit_cost") or 0),
        "vendor": str(row.get("vendor") or "—"),
    }


def load_inventory() -> list[dict[str, Any]]:
    try:
        from app.services.phase2_modules_service import list_inventory
    except ImportError:
        from services.phase2_modules_service import list_inventory  # type: ignore
    rows, _ = list_inventory(demo=list(_DEMO_INVENTORY))
    return rows


def _normalize_asset(row: dict[str, Any]) -> dict[str, Any]:
    aid = str(row.get("id") or "").strip()
    num = str(row.get("asset_number") or row.get("tag") or aid[:8])
    return {
        "id": aid or num,
        "asset_number": num,
        "asset_name": str(row.get("asset_name") or row.get("name") or "—"),
        "category": str(row.get("category") or "—"),
        "location": str(row.get("location") or "—"),
        "department": str(row.get("department") or "—"),
        "status": str(row.get("status") or "In Service"),
        "acquired_date": str(row.get("acquired_date") or "")[:10],
        "value": float(row.get("value") or row.get("current_value") or 0),
        "serial_number": str(row.get("serial_number") or "—"),
        "manufacturer": str(row.get("manufacturer") or "—"),
        "model": str(row.get("model") or "—"),
        "operator": str(row.get("operator") or row.get("assigned_to") or "—"),
        "description": str(row.get("description") or row.get("notes") or ""),
    }


def load_assets() -> list[dict[str, Any]]:
    try:
        from app.services.phase2_modules_service import list_assets
    except ImportError:
        from services.phase2_modules_service import list_assets  # type: ignore
    rows, _ = list_assets(demo=list(_DEMO_ASSETS))
    return rows


ACTIVE_EMPLOYEE_KEY = "ips_active_employee_id"

_DEMO_EMPLOYEES: list[dict[str, Any]] = [
    {
        "id": "emp-chance",
        "name": "Chance Burgess",
        "email": "chance.burgess@industrialplantsolution.com",
        "role": "Field Employee",
        "department": "Field Operations",
        "status": "Active",
        "last_login": "2025-05-18 08:12",
        "phone": "(337) 555-0142",
        "username": "cburgess",
        "member_since": "2021-03-15",
    },
    {
        "id": "emp-mark",
        "name": "Mark Johnson",
        "email": "mark.johnson@industrialplantsolution.com",
        "role": "Supervisor",
        "department": "Field Operations",
        "status": "Active",
        "last_login": "2025-05-18 07:45",
        "phone": "(337) 555-0198",
        "username": "mjohnson",
        "member_since": "2019-06-01",
    },
    {
        "id": "emp-leland",
        "name": "Leland Daigle",
        "email": "leland@industrialplantsolution.com",
        "role": "Administrator",
        "department": "Administration",
        "status": "Active",
        "last_login": "2025-05-18 09:01",
        "phone": "(337) 555-0100",
        "username": "ldaigle",
        "member_since": "2015-01-10",
    },
    {
        "id": "emp-sarah",
        "name": "Sarah Chen",
        "email": "sarah.chen@industrialplantsolution.com",
        "role": "Project Manager",
        "department": "Project Management",
        "status": "Active",
        "last_login": "2025-05-17 16:22",
        "phone": "(337) 555-0165",
        "username": "schen",
        "member_since": "2020-08-20",
    },
    {
        "id": "emp-inactive",
        "name": "James Ortiz",
        "email": "jortiz@industrialplantsolution.com",
        "role": "Field Employee",
        "department": "Field Operations",
        "status": "Inactive",
        "last_login": "2025-02-01 11:00",
        "phone": "(337) 555-0133",
        "username": "jortiz",
        "member_since": "2018-11-05",
    },
]

_DEMO_CERTIFICATIONS: list[dict[str, Any]] = [
    {"id": "cert1", "employee_id": "emp-chance", "cert_type": "TWIC", "cert_number": "TWIC-88421", "issuer": "TSA", "issue_date": "2023-01-15", "expiration_date": "2028-01-14", "status": "Active", "notes": ""},
    {"id": "cert2", "employee_id": "emp-chance", "cert_type": "OSHA 30", "cert_number": "OSHA-9921", "issuer": "OSHA", "issue_date": "2022-06-01", "expiration_date": "2025-06-15", "status": "Expiring Soon", "notes": "Renewal scheduled"},
    {"id": "cert3", "employee_id": "emp-mark", "cert_type": "Forklift", "cert_number": "FL-4412", "issuer": "IPS Safety", "issue_date": "2021-03-10", "expiration_date": "2024-03-09", "status": "Expired", "notes": "Retest required"},
    {"id": "cert4", "employee_id": "emp-leland", "cert_type": "First Aid / CPR", "cert_number": "FA-2201", "issuer": "Red Cross", "issue_date": "2024-01-20", "expiration_date": "2026-01-19", "status": "Active", "notes": ""},
]

_DEMO_EMPLOYEE_DOCUMENTS: list[dict[str, Any]] = [
    {"id": "doc1", "employee_id": "emp-chance", "doc_type": "Driver's License", "upload_date": "2024-08-01", "uploaded_by": "HR Admin", "expiration_date": "2027-08-01", "is_restricted": False, "file_name": "license_chance.pdf"},
    {"id": "doc2", "employee_id": "emp-chance", "doc_type": "OSHA Card", "upload_date": "2022-06-05", "uploaded_by": "HR Admin", "expiration_date": "2025-06-01", "is_restricted": False, "file_name": "osha_chance.pdf"},
    {"id": "doc3", "employee_id": "emp-mark", "doc_type": "HR Document", "upload_date": "2023-02-10", "uploaded_by": "HR Admin", "expiration_date": "", "is_restricted": True, "file_name": "performance_review.pdf"},
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
        from app.services.phase2_modules_service import list_employees
    except ImportError:
        from services.phase2_modules_service import list_employees  # type: ignore
    rows, _ = list_employees(demo=list(_DEMO_EMPLOYEES))
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
        from app.services.phase2_modules_service import list_certifications
    except ImportError:
        from services.phase2_modules_service import list_certifications  # type: ignore
    demo = [c for c in _DEMO_CERTIFICATIONS if c.get("employee_id") == eid]
    if not demo and eid:
        demo = [c for c in _DEMO_CERTIFICATIONS if eid == "emp-chance"][:2]
    rows, _ = list_certifications(eid, demo=demo or list(_DEMO_CERTIFICATIONS)[:2])
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
        from app.services.phase2_modules_service import list_documents_hub
    except ImportError:
        from services.phase2_modules_service import list_documents_hub  # type: ignore
    rows, _ = list_documents_hub(role=role, demo=list(_DEMO_DOCUMENTS_HUB))
    return rows


def load_company_updates(*, category: str = "All Updates") -> list[dict[str, Any]]:
    try:
        from app.services.phase2_modules_service import list_company_updates
    except ImportError:
        from services.phase2_modules_service import list_company_updates  # type: ignore
    rows, _ = list_company_updates(category=category, demo=list(_DEMO_COMPANY_UPDATES))
    return rows


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
        from app.services.phase2_modules_service import list_all_certifications
    except ImportError:
        from services.phase2_modules_service import list_all_certifications  # type: ignore
    employees = load_employees()
    demo = []
    for c in _DEMO_CERTIFICATIONS:
        emp = get_employee(str(c.get("employee_id") or "")) or {}
        demo.append({**c, "employee_name": str(emp.get("name") or "—")})
    rows, _ = list_all_certifications(demo=demo, employees=employees)
    return rows


def certification_alerts(certs: list[dict[str, Any]]) -> tuple[int, int]:
    expired = sum(1 for c in certs if str(c.get("status", "")).lower() == "expired")
    expiring = sum(1 for c in certs if str(c.get("status", "")).lower() == "expiring soon")
    return expired, expiring


def job_options_for_timekeeping() -> list[str]:
    jobs = load_jobs()
    opts = ["— No job —"]
    for j in jobs:
        num = str(j.get("job_number") or "")
        name = str(j.get("job_name") or "")
        if num:
            opts.append(f"{num} — {name}")
    if len(opts) == 1:
        opts.append("J26047 — Maintenance Shop Bathroom Remodel")
    return opts


def load_tasks() -> list[dict[str, Any]]:
    try:
        from app.services.phase2_modules_service import list_tasks
    except ImportError:
        from services.phase2_modules_service import list_tasks  # type: ignore
    rows, _ = list_tasks(demo=list(_DEMO_TASKS))
    return rows


def get_task(task_id: str) -> dict[str, Any] | None:
    tid = str(task_id or "").strip()
    for t in load_tasks():
        if str(t.get("id")) == tid:
            return t
    return None


def load_timekeeping_summaries(week_start: date) -> list[dict[str, Any]]:
    try:
        from app.services.phase2_modules_service import list_timekeeping_summaries
    except ImportError:
        from services.phase2_modules_service import list_timekeeping_summaries  # type: ignore
    demo = [
        {"id": "emp-chance", "name": "Chance Burgess", "department": "Field Operations", "week_start": week_start.isoformat(), "st_total": 38.5, "ot_total": 4.0, "dt_total": 0.0, "status": "Pending"},
        {"id": "emp-mark", "name": "Mark Johnson", "department": "Field Operations", "week_start": week_start.isoformat(), "st_total": 40.0, "ot_total": 2.5, "dt_total": 0.0, "status": "Approved"},
        {"id": "emp-sarah", "name": "Sarah Chen", "department": "Project Management", "week_start": week_start.isoformat(), "st_total": 32.0, "ot_total": 0.0, "dt_total": 0.0, "status": "Approved"},
        {"id": "emp-leland", "name": "Leland Daigle", "department": "Administration", "week_start": week_start.isoformat(), "st_total": 40.0, "ot_total": 0.0, "dt_total": 0.0, "status": "Approved"},
    ]
    rows, _ = list_timekeeping_summaries(week_start, demo=demo)
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
            "job": default_job if i < 5 else "— No job —",
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
        name = str(e.get("name") or e.get("title") or "")
        if num:
            opts.append(f"{num} — {name}")
    return opts


def task_assignee_options() -> list[str]:
    return [str(e.get("name") or "") for e in load_employees() if e.get("name")]


def demo_report_job_profitability() -> list[dict[str, Any]]:
    return [
        {"job_number": "J26047", "job_name": "Maintenance Shop Bathroom Remodel", "revenue": 185000, "cost": 142500, "margin_pct": 23.0},
        {"job_number": "J26012", "job_name": "Tank Farm Piping", "revenue": 420000, "cost": 358200, "margin_pct": 14.7},
        {"job_number": "J25988", "job_name": "Warehouse LED Retrofit", "revenue": 96000, "cost": 71200, "margin_pct": 25.8},
    ]


def demo_report_labor_by_job() -> list[dict[str, Any]]:
    return [
        {"job_number": "J26047", "st_hours": 312.5, "ot_hours": 28.0, "dt_hours": 0.0, "total_hours": 340.5},
        {"job_number": "J26012", "st_hours": 890.0, "ot_hours": 112.5, "dt_hours": 16.0, "total_hours": 1018.5},
        {"job_number": "J25988", "st_hours": 156.0, "ot_hours": 8.0, "dt_hours": 0.0, "total_hours": 164.0},
    ]


def demo_report_labor_by_employee() -> list[dict[str, Any]]:
    return [
        {"employee": "Chance Burgess", "st_hours": 38.5, "ot_hours": 4.0, "dt_hours": 0.0, "total_hours": 42.5},
        {"employee": "Mark Johnson", "st_hours": 40.0, "ot_hours": 2.5, "dt_hours": 0.0, "total_hours": 42.5},
        {"employee": "Sarah Chen", "st_hours": 32.0, "ot_hours": 0.0, "dt_hours": 0.0, "total_hours": 32.0},
    ]


def demo_report_inventory_value() -> list[dict[str, Any]]:
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


def persist_job(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    try:
        from app.services.phase2_modules_service import save_job
    except ImportError:
        from services.phase2_modules_service import save_job  # type: ignore
    return _persist_result(save_job(ui, row_id=row_id), success="Job saved.")


def persist_estimate(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    try:
        from app.services.phase2_modules_service import save_estimate
    except ImportError:
        from services.phase2_modules_service import save_estimate  # type: ignore
    return _persist_result(save_estimate(ui, row_id=row_id), success="Estimate saved.")


def persist_inventory(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    try:
        from app.services.phase2_modules_service import save_inventory_item
    except ImportError:
        from services.phase2_modules_service import save_inventory_item  # type: ignore
    return _persist_result(save_inventory_item(ui, row_id=row_id), success="Inventory item saved.")


def persist_asset(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    try:
        from app.services.phase2_modules_service import save_asset
    except ImportError:
        from services.phase2_modules_service import save_asset  # type: ignore
    return _persist_result(save_asset(ui, row_id=row_id), success="Asset saved.")


def persist_employee(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    try:
        from app.services.phase2_modules_service import save_employee
    except ImportError:
        from services.phase2_modules_service import save_employee  # type: ignore
    return _persist_result(save_employee(ui, row_id=row_id), success="Employee saved.")


def persist_certification(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    try:
        from app.services.phase2_modules_service import save_certification
    except ImportError:
        from services.phase2_modules_service import save_certification  # type: ignore
    return _persist_result(save_certification(ui, row_id=row_id), success="Certification saved.")


def persist_document(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    try:
        from app.services.phase2_modules_service import save_document_hub
    except ImportError:
        from services.phase2_modules_service import save_document_hub  # type: ignore
    return _persist_result(save_document_hub(ui, row_id=row_id), success="Document saved.")


def persist_company_update(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    try:
        from app.services.phase2_modules_service import save_company_update
    except ImportError:
        from services.phase2_modules_service import save_company_update  # type: ignore
    return _persist_result(save_company_update(ui, row_id=row_id), success="Update published.")


def persist_task(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    try:
        from app.services.phase2_modules_service import save_task
    except ImportError:
        from services.phase2_modules_service import save_task  # type: ignore
    return _persist_result(save_task(ui, row_id=row_id), success="Task saved.")


def persist_timekeeping_week(employee_id: str, week_start: date, summary: dict[str, Any]) -> tuple[bool, str]:
    try:
        from app.services.phase2_modules_service import save_timekeeping_week
    except ImportError:
        from services.phase2_modules_service import save_timekeeping_week  # type: ignore
    return _persist_result(
        save_timekeeping_week(employee_id, week_start, summary),
        success="Timekeeping saved.",
    )
