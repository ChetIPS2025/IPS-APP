"""Load module data from Supabase with demo fallbacks."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import streamlit as st

CATALOG_CACHE_TTL = 300
_CATALOG_SESSION_KEY = "_ips_catalog_datasets"


def _catalog_session_get(name: str, loader):
    """Mirror cached catalog rows in session for fast reuse within a user session."""
    store = st.session_state.setdefault(_CATALOG_SESSION_KEY, {})
    if name not in store:
        store[name] = loader()
    return store[name]


def clear_catalog_session_datasets() -> None:
    st.session_state.pop(_CATALOG_SESSION_KEY, None)


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
        "status": "Active",
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
        "status": "Active",
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
        "status": "Active",
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
        "status": "Active",
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
            from app.pages._core._access import mark_demo_data, show_db_error
        except ImportError:
            from pages._core._access import mark_demo_data, show_db_error  # type: ignore
        mark_demo_data()
        show_db_error(name, err)
    return rows


def _mark_if_demo(used: bool) -> None:
    if used:
        try:
            from app.pages._core._access import mark_demo_data
        except ImportError:
            from pages._core._access import mark_demo_data  # type: ignore
        mark_demo_data()


def load_jobs() -> list[dict[str, Any]]:
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    def _load() -> list[dict[str, Any]]:
        rows, used = _cached_jobs_rows()
        _mark_if_demo(used)
        return list(rows)

    with perf_span("data.load_jobs"):
        return _catalog_session_get("jobs", _load)


@st.cache_data(ttl=CATALOG_CACHE_TTL, show_spinner=False)
def _cached_jobs_rows() -> tuple[tuple[dict[str, Any], ...], bool]:
    try:
        from app.services.jobs_service import list_jobs
    except ImportError:
        from services.jobs_service import list_jobs  # type: ignore
    rows, used = list_jobs(demo=list(_DEMO_JOBS))
    return tuple(rows), used


def load_dashboard_kpis() -> dict[str, Any]:
    try:
        from app.services.job_service import dashboard_job_metrics
    except ImportError:
        from services.job_service import dashboard_job_metrics  # type: ignore

    estimates = load_estimates()
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
        "pending_jobs": 0,
        "draft_jobs": 0,
        "on_hold_jobs": 0,
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
    try:
        from app.services.jobs_service import normalize_job_status
    except ImportError:
        from services.jobs_service import normalize_job_status  # type: ignore
    jobs = load_jobs()
    counts: dict[str, int] = {}
    for j in jobs:
        if bool(j.get("is_deleted")):
            continue
        st_label = normalize_job_status(j.get("status"))
        counts[st_label] = counts.get(st_label, 0) + 1
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
    return [
        {
            "scanned_at": "2026-05-30T14:30:00Z",
            "qr_value": "INV-WIRE-220",
            "item_name": "THHN wire 12 AWG",
            "item_type": "Inventory",
            "result": "Opened",
            "job_shop": "—",
            "scanned_by": "Chris Ortiz",
            "device_source": "Android · mobile_qr_scan",
            "action_taken": "—",
        },
        {
            "scanned_at": "2026-05-30T14:22:00Z",
            "qr_value": "INV-AB12CD34",
            "item_name": "PVC cement 8 oz",
            "item_type": "Inventory",
            "result": "Success",
            "job_shop": "J26047 · Riverside TI",
            "scanned_by": "Alex Rivera",
            "device_source": "iPhone · QR scan",
            "action_taken": "Used on job",
        },
        {
            "scanned_at": "2026-05-30T13:05:00Z",
            "qr_value": "AST-M18-0042",
            "item_name": "Milwaukee M18 impact",
            "item_type": "Asset / Tool",
            "result": "Success",
            "job_shop": "J26047 · Riverside TI",
            "scanned_by": "Maria Chen",
            "device_source": "QR scan",
            "action_taken": "Checked out",
        },
        {
            "scanned_at": "2026-05-30T11:48:00Z",
            "qr_value": "INV-FF009911",
            "item_name": "Wire nuts (yellow)",
            "item_type": "Inventory",
            "result": "Success",
            "job_shop": "Shop",
            "scanned_by": "Chris Ortiz",
            "device_source": "Shop cart A · QR scan",
            "action_taken": "Used in shop",
        },
        {
            "scanned_at": "2026-05-30T10:15:00Z",
            "qr_value": "UNKNOWN-QR-9921",
            "item_name": "Unknown item",
            "item_type": "Inventory",
            "result": "Unknown item",
            "job_shop": "—",
            "scanned_by": "Field scanner",
            "device_source": "Android · QR scan",
            "action_taken": "—",
        },
        {
            "scanned_at": "2026-05-29T16:40:00Z",
            "qr_value": "AST-HILTI-018",
            "item_name": "Hilti rotary hammer",
            "item_type": "Asset / Tool",
            "result": "Success",
            "job_shop": "—",
            "scanned_by": "Maria Chen",
            "device_source": "QR scan",
            "action_taken": "Checked in",
        },
        {
            "scanned_at": "2026-05-29T14:10:00Z",
            "qr_value": "INV-CONDUIT-3",
            "item_name": "EMT conduit 3/4 in",
            "item_type": "Inventory",
            "result": "Opened",
            "job_shop": "—",
            "scanned_by": "Alex Rivera",
            "device_source": "Android · QR scan",
            "action_taken": "—",
        },
        {
            "scanned_at": "2026-05-29T11:22:00Z",
            "qr_value": "INV-JBOX-8821",
            "item_name": "4x4 junction box",
            "item_type": "Inventory",
            "result": "Success",
            "job_shop": "J26045 · Oak Park",
            "scanned_by": "Chris Ortiz",
            "device_source": "iPhone · mobile_qr_scan",
            "action_taken": "Used on job",
        },
        {
            "scanned_at": "2026-05-28T17:55:00Z",
            "qr_value": "AST-DEWALT-991",
            "item_name": "DeWalt circular saw",
            "item_type": "Asset / Tool",
            "result": "Success",
            "job_shop": "Shop",
            "scanned_by": "Maria Chen",
            "device_source": "QR scan",
            "action_taken": "Checked out",
        },
        {
            "scanned_at": "2026-05-28T09:30:00Z",
            "qr_value": "INV-LABEL-404",
            "item_name": "Wire labels (roll)",
            "item_type": "Inventory",
            "result": "Opened",
            "job_shop": "—",
            "scanned_by": "Field scanner",
            "device_source": "Shop cart B · QR scan",
            "action_taken": "—",
        },
    ]


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


def _job_awarded_date(job: dict[str, Any]) -> str:
    for key in ("start_date", "created_at"):
        val = str(job.get(key) or "").strip()
        if val:
            return val[:10]
    return ""


def load_awarded_jobs() -> list[dict[str, Any]]:
    """Live active jobs for dashboard lists (legacy name retained for callers)."""
    try:
        from app.services.job_service import normalize_job_status_for_filter, sort_jobs_by_number_then_name
    except ImportError:
        from services.job_service import normalize_job_status_for_filter, sort_jobs_by_number_then_name  # type: ignore

    active = [
        job
        for job in load_jobs()
        if not bool(job.get("is_deleted"))
        and normalize_job_status_for_filter(job.get("status")) == "Active"
    ]
    rows: list[dict[str, Any]] = []
    for job in sort_jobs_by_number_then_name(active):
        row = dict(job)
        row["awarded_date"] = _job_awarded_date(job)
        rows.append(row)
    return rows


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
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    def _load() -> list[dict[str, Any]]:
        rows, used = _cached_estimates_rows()
        _mark_if_demo(used)
        return list(rows)

    with perf_span("data.load_estimates"):
        return _catalog_session_get("estimates", _load)


@st.cache_data(ttl=CATALOG_CACHE_TTL, show_spinner=False)
def _cached_estimates_rows() -> tuple[tuple[dict[str, Any], ...], bool]:
    try:
        from app.services.estimates_service import list_estimates
    except ImportError:
        from services.estimates_service import list_estimates  # type: ignore
    rows, used = list_estimates(demo=list(_DEMO_ESTIMATES))
    return tuple(rows), used


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


def clear_inventory_list_cache() -> None:
    _cached_inventory_rows.clear()


def clear_assets_list_cache() -> None:
    _cached_assets_rows.clear()


def clear_jobs_list_cache() -> None:
    _cached_jobs_rows.clear()


def clear_customers_list_cache() -> None:
    _cached_customers_rows.clear()


def clear_employees_list_cache() -> None:
    _cached_employees_rows.clear()


def clear_estimates_list_cache() -> None:
    _cached_estimates_rows.clear()


def clear_user_profiles_cache() -> None:
    _cached_user_profiles.clear()


def clear_tasks_list_cache() -> None:
    _cached_tasks_rows.clear()


def clear_labor_rates_cache() -> None:
    _cached_labor_rates_rows.clear()


def clear_all_catalog_list_caches() -> None:
    """Invalidate Streamlit catalog caches after mutations."""
    clear_catalog_session_datasets()
    clear_inventory_list_cache()
    clear_assets_list_cache()
    clear_jobs_list_cache()
    clear_customers_list_cache()
    clear_employees_list_cache()
    clear_estimates_list_cache()
    clear_user_profiles_cache()
    clear_labor_rates_cache()
    clear_tasks_list_cache()
    try:
        from app.services.pricing_guide_service import clear_pricing_guide_cache
    except ImportError:
        from services.pricing_guide_service import clear_pricing_guide_cache  # type: ignore
    clear_pricing_guide_cache()


@st.cache_data(ttl=CATALOG_CACHE_TTL, show_spinner=False)
def _cached_inventory_rows() -> tuple[tuple[dict[str, Any], ...], bool]:
    try:
        from app.services.inventory_service import list_inventory
    except ImportError:
        from services.inventory_service import list_inventory  # type: ignore
    rows, used = list_inventory(demo=list(_DEMO_INVENTORY))
    return tuple(rows), used


@st.cache_data(ttl=CATALOG_CACHE_TTL, show_spinner=False)
def _cached_assets_rows() -> tuple[tuple[dict[str, Any], ...], bool]:
    try:
        from app.services.assets_service import list_assets
    except ImportError:
        from services.assets_service import list_assets  # type: ignore
    rows, used = list_assets(demo=list(_DEMO_ASSETS))
    return tuple(rows), used


def load_inventory() -> list[dict[str, Any]]:
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    def _load() -> list[dict[str, Any]]:
        rows, used = _cached_inventory_rows()
        _mark_if_demo(used)
        return list(rows)

    with perf_span("data.load_inventory"):
        return _catalog_session_get("inventory", _load)


def load_assets() -> list[dict[str, Any]]:
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    def _load() -> list[dict[str, Any]]:
        rows, used = _cached_assets_rows()
        _mark_if_demo(used)
        return list(rows)

    with perf_span("data.load_assets"):
        return _catalog_session_get("assets", _load)


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
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    def _load() -> list[dict[str, Any]]:
        rows, used = _cached_employees_rows()
        _mark_if_demo(used)
        return list(rows)

    with perf_span("data.load_employees"):
        return _catalog_session_get("employees", _load)


@st.cache_data(ttl=CATALOG_CACHE_TTL, show_spinner=False)
def _cached_employees_rows() -> tuple[tuple[dict[str, Any], ...], bool]:
    try:
        from app.services.employees_service import list_employees
    except ImportError:
        from services.employees_service import list_employees  # type: ignore
    rows, used = list_employees(demo=list(_DEMO_EMPLOYEES))
    return tuple(rows), used


def is_workforce_employee(emp: dict[str, Any]) -> bool:
    """True when the user should appear in employee/timekeeping pickers."""
    raw = emp.get("is_employee")
    if raw is None:
        return True
    return bool(raw)


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
    try:
        from app.services.certification_helpers import certification_alerts_counts
    except ImportError:
        from services.certification_helpers import certification_alerts_counts  # type: ignore
    return certification_alerts_counts(certs)


def job_options_for_timekeeping() -> list[str]:
    """Same assignable job list as Timekeeping allocation dropdowns."""
    try:
        from app.pages.timekeeping import _assignment_options_for_timekeeping

        return _assignment_options_for_timekeeping()
    except ImportError:
        from pages.timekeeping import _assignment_options_for_timekeeping  # type: ignore

        return _assignment_options_for_timekeeping()


def load_tasks() -> list[dict[str, Any]]:
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    def _load() -> list[dict[str, Any]]:
        rows, used = _cached_tasks_rows()
        _mark_if_demo(used)
        return list(rows)

    with perf_span("data.load_tasks"):
        return _catalog_session_get("tasks", _load)


@st.cache_data(ttl=CATALOG_CACHE_TTL, show_spinner=False)
def _cached_tasks_rows() -> tuple[tuple[dict[str, Any], ...], bool]:
    try:
        from app.services.phase2_modules_service import list_tasks
    except ImportError:
        from services.phase2_modules_service import list_tasks  # type: ignore
    rows, used = list_tasks(demo=list(_DEMO_TASKS))
    return tuple(rows), used


def get_task(task_id: str) -> dict[str, Any] | None:
    tid = str(task_id or "").strip()
    for t in load_tasks():
        if str(t.get("id")) == tid:
            return t
    return None


def _active_employees() -> list[dict[str, Any]]:
    """Employees eligible for timekeeping (Active status in Users)."""
    return [
        e
        for e in load_employees()
        if str(e.get("status") or "Active") == "Active"
        and str(e.get("id") or "").strip()
        and is_workforce_employee(e)
    ]


_DEMO_TIMEKEEPING_BY_EMP: dict[str, dict[str, Any]] = {
    "emp-chance": {"st_total": 38.5, "ot_total": 4.0, "dt_total": 0.0, "status": "Pending"},
    "emp-mark": {"st_total": 40.0, "ot_total": 2.5, "dt_total": 0.0, "status": "Approved"},
    "emp-sarah": {"st_total": 32.0, "ot_total": 0.0, "dt_total": 0.0, "status": "Approved"},
    "emp-leland": {"st_total": 40.0, "ot_total": 0.0, "dt_total": 0.0, "status": "Approved"},
}

# Default weekly ST hours (Mon=0 … Sun=6) when a day has no saved timekeeping row.
AMANDA_ROBICHEAUX_EMPLOYEE_NUMBER = "IPS5320"


def _timekeeping_summary_for_employee(
    emp: dict[str, Any],
    week_start: date,
    tk_row: dict[str, Any] | None,
) -> dict[str, Any]:
    eid = str(emp.get("id") or "").strip()
    if tk_row:
        return {
            **tk_row,
            "id": eid,
            "name": str(emp.get("name") or tk_row.get("name") or ""),
            "department": str(emp.get("department") or tk_row.get("department") or ""),
            "week_start": str(tk_row.get("week_start") or week_start.isoformat())[:10],
        }
    demo = _DEMO_TIMEKEEPING_BY_EMP.get(eid, {})
    return {
        "id": eid,
        "name": str(emp.get("name") or ""),
        "department": str(emp.get("department") or ""),
        "week_start": week_start.isoformat(),
        "st_total": float(demo.get("st_total") or 0),
        "ot_total": float(demo.get("ot_total") or 0),
        "dt_total": float(demo.get("dt_total") or 0),
        "status": "Draft",
    }


def _demo_timekeeping_summaries(week_start: date) -> list[dict[str, Any]]:
    return [_timekeeping_summary_for_employee(e, week_start, None) for e in _active_employees()]


def load_timekeeping_summaries(week_start: date) -> list[dict[str, Any]]:
    try:
        from app.services.timekeeping_service import list_timekeeping_summaries
    except ImportError:
        from services.timekeeping_service import list_timekeeping_summaries  # type: ignore

    employees = _active_employees()
    employee_ids = {str(e.get("id") or "").strip() for e in employees}
    rows, used = list_timekeeping_summaries(week_start, demo=_demo_timekeeping_summaries(week_start))
    _mark_if_demo(used)

    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        rid = str(row.get("id") or "").strip()
        if rid and rid in employee_ids:
            by_id[rid] = row

    return [
        _timekeeping_summary_for_employee(emp, week_start, by_id.get(str(emp.get("id") or "").strip()))
        for emp in employees
    ]


def _normalize_timekeeping_assignment(label: str) -> str:
    raw = str(label or "").strip()
    if not raw:
        return raw
    legacy = {
        "ips shop": "Shop",
        "administrator": "Administrative",
        "admin": "Administrative",
        "— no job —": "— Select assignment —",
        "no job": "— Select assignment —",
    }
    return legacy.get(raw.casefold(), raw)


def _employee_for_timekeeping(employee_id: str) -> dict[str, Any]:
    eid = str(employee_id or "").strip()
    if not eid:
        return {}
    for emp in _active_employees():
        if str(emp.get("id") or "").strip() == eid:
            return emp
    return {}


def _is_amanda_robicheaux(employee: dict[str, Any]) -> bool:
    num = str(employee.get("employee_number") or "").strip().upper()
    if num == AMANDA_ROBICHEAUX_EMPLOYEE_NUMBER:
        return True
    name = (
        employee.get("name")
        or employee.get("full_name")
        or employee.get("display_name")
        or ""
    ).strip().lower()
    return name == "amanda m. robicheaux"


def _default_hours_for_employee_day(employee: dict[str, Any], day_index: int) -> float:
    """
    Default ST hours when no saved row exists for that date.

    day_index: 0=Monday … 6=Sunday.
    Amanda M. Robicheaux: 8.0 Mon–Fri, 0.0 Sat–Sun (40.0/wk).
    All other employees: 10.0 Mon–Thu, 0.0 Fri–Sun (40.0/wk).
    """
    if day_index < 0 or day_index > 6:
        return 0.0
    if _is_amanda_robicheaux(employee):
        return 8.0 if day_index in {0, 1, 2, 3, 4} else 0.0
    return 10.0 if day_index in {0, 1, 2, 3} else 0.0


def default_weekly_grid(employee_id: str, week_start: date) -> list[dict[str, Any]]:
    days = week_dates(week_start)
    job_opts = job_options_for_timekeeping()
    default_job = job_opts[0] if job_opts else "— Select assignment —"
    emp = _employee_for_timekeeping(employee_id)
    grid = []
    for i, d in enumerate(days):
        grid.append({
            "day": d.strftime("%A"),
            "date": d.isoformat(),
            "job": default_job,
            "st": _default_hours_for_employee_day(emp, i),
            "ot": 0.0,
            "dt": 0.0,
            "notes": "",
            "status": "Draft",
        })
    if employee_id == "emp-mark" and len(grid) > 4:
        grid[4]["ot"] = 2.5
    return grid


def load_timekeeping_grid(employee_id: str, week_start: date) -> list[dict[str, Any]]:
    """Build the weekly grid from saved day rows, or schedule defaults for missing days."""
    eid = str(employee_id or "").strip()
    try:
        from app.services.timekeeping_service import list_timekeeping_days
    except ImportError:
        from services.timekeeping_service import list_timekeeping_days  # type: ignore

    saved_rows = list_timekeeping_days(eid, week_start) if eid else []
    if not saved_rows:
        return default_weekly_grid(eid, week_start)

    emp = _employee_for_timekeeping(eid)
    days = week_dates(week_start)
    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in saved_rows:
        iso = str(row.get("work_date") or "")[:10]
        if iso:
            by_date.setdefault(iso, []).append(row)
    job_opts = job_options_for_timekeeping()
    default_job = job_opts[0] if job_opts else "— Select assignment —"
    grid: list[dict[str, Any]] = []
    for i, day in enumerate(days):
        iso = day.isoformat()
        saved_list = by_date.get(iso) or []
        # Any saved row for this date (including 0.0 hours) — do not apply schedule defaults.
        if saved_list:
            primary = saved_list[0]
            for candidate in saved_list:
                hrs = float(candidate.get("st_hours") or 0) + float(candidate.get("ot_hours") or 0)
                if hrs > 0:
                    primary = candidate
                    break
            st_total = sum(float(r.get("st_hours") or 0) for r in saved_list)
            ot_total = sum(float(r.get("ot_hours") or 0) for r in saved_list)
            dt_total = sum(float(r.get("dt_hours") or 0) for r in saved_list)
            statuses = [str(r.get("status") or "Draft").strip().capitalize() for r in saved_list]
            day_status = "Draft"
            if statuses and all(s == "Approved" for s in statuses):
                day_status = "Approved"
            elif any(s == "Rejected" for s in statuses):
                day_status = "Rejected"
            elif any(s == "Pending" for s in statuses):
                day_status = "Pending"
            grid.append({
                "day_id": str(primary.get("id") or ""),
                "day": day.strftime("%A"),
                "date": iso,
                "job": _normalize_timekeeping_assignment(str(primary.get("job_label") or default_job)),
                "st": st_total,
                "ot": ot_total,
                "dt": dt_total,
                "notes": str(primary.get("notes") or ""),
                "status": day_status,
            })
        else:
            grid.append({
                "day": day.strftime("%A"),
                "date": iso,
                "job": default_job,
                "st": _default_hours_for_employee_day(emp, i),
                "ot": 0.0,
                "dt": 0.0,
                "notes": "",
                "status": "Draft",
            })
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
        "job_id": "demo-j26047",
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
        return [
            str(e.get("name") or "")
            for e in load_employees()
            if e.get("name") and is_workforce_employee(e)
        ]
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
        from app.pages._core._crud import is_demo_id
    except ImportError:
        from pages._core._crud import is_demo_id  # type: ignore
    return is_demo_id(row_id)


def employee_options(*, include_blank: bool = True) -> list[str]:
    names = sorted(
        {
            str(e.get("name") or "")
            for e in load_employees()
            if e.get("name") and is_workforce_employee(e)
        }
    )
    if include_blank:
        return ["— Select —", *names]
    return names


_DEMO_CUSTOMERS: list[dict[str, Any]] = [
    {
        "id": "demo-c-birla",
        "customer_name": "Orion Engineered Carbons",
        "customer_number": "C-1001",
        "address": "123 Industrial Park Rd",
        "city": "Alexandria",
        "state": "LA",
        "zip": "71301",
        "website": "https://orioncarbons.example",
        "main_phone": "(318) 555-0100",
        "main_email": "info@orioncarbons.example",
        "billing_email": "ap@orioncarbons.example",
        "is_active": True,
        "status": "Active",
        "notes": "Primary petrochemical account with multiple sites.",
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
        "location_name": "Franklin Plant",
        "site_name": "Franklin Plant",
        "location_type": "Plant",
        "address_line_1": "123 Industrial Park Rd",
        "address": "123 Industrial Park Rd",
        "city": "Alexandria",
        "state": "LA",
        "zip": "71301",
        "is_primary": True,
        "is_billing": False,
        "is_shipping": False,
        "is_active": True,
        "status": "Active",
    },
    {
        "id": "demo-loc-2",
        "customer_id": "demo-c-birla",
        "location_name": "Maintenance Office",
        "site_name": "Maintenance Office",
        "location_type": "Office",
        "address_line_1": "125 Industrial Park Rd",
        "address": "125 Industrial Park Rd",
        "city": "Alexandria",
        "state": "LA",
        "zip": "71301",
        "is_primary": False,
        "is_active": True,
        "status": "Active",
    },
    {
        "id": "demo-loc-3",
        "customer_id": "demo-c-birla",
        "location_name": "Billing Office",
        "site_name": "Billing Office",
        "location_type": "Billing",
        "address_line_1": "400 Commerce St",
        "address": "400 Commerce St",
        "city": "Alexandria",
        "state": "LA",
        "zip": "71301",
        "is_primary": False,
        "is_billing": True,
        "is_active": True,
        "status": "Active",
    },
    {
        "id": "demo-loc-4",
        "customer_id": "demo-c-birla",
        "location_name": "Shipping/Receiving Gate",
        "site_name": "Shipping/Receiving Gate",
        "location_type": "Shipping",
        "address_line_1": "Gate 3, Plant Rd",
        "address": "Gate 3, Plant Rd",
        "city": "Alexandria",
        "state": "LA",
        "zip": "71301",
        "is_primary": False,
        "is_shipping": True,
        "is_active": True,
        "status": "Active",
    },
    {
        "id": "demo-loc-acme",
        "customer_id": "demo-c-acme",
        "location_name": "Acme Construction Main Location",
        "site_name": "Acme Construction Main Location",
        "location_type": "Office",
        "address_line_1": "4500 Commerce Blvd",
        "address": "4500 Commerce Blvd",
        "city": "Lake Charles",
        "state": "LA",
        "zip": "70601",
        "is_primary": True,
        "is_active": True,
        "status": "Active",
    },
]

_DEMO_CUSTOMER_CONTACTS: list[dict[str, Any]] = [
    {
        "id": "demo-cc-1",
        "customer_id": "demo-c-birla",
        "customer_location_id": "demo-loc-1",
        "location_id": "demo-loc-1",
        "full_name": "Sarah Chen",
        "contact_name": "Sarah Chen",
        "title": "Plant Manager",
        "role_type": "Site Contact",
        "email": "sarah.chen@example.com",
        "phone": "(318) 555-0101",
        "mobile": "(318) 555-1101",
        "is_site_contact": True,
        "is_active": True,
        "is_primary": True,
        "status": "Active",
    },
    {
        "id": "demo-cc-2",
        "customer_id": "demo-c-birla",
        "customer_location_id": "demo-loc-1",
        "location_id": "demo-loc-1",
        "full_name": "Mike Torres",
        "contact_name": "Mike Torres",
        "title": "Safety Coordinator",
        "role_type": "Safety Contact",
        "email": "mike.torres@example.com",
        "phone": "(318) 555-0102",
        "is_safety_contact": True,
        "is_active": True,
        "is_primary": False,
        "status": "Active",
    },
    {
        "id": "demo-cc-3",
        "customer_id": "demo-c-birla",
        "customer_location_id": "demo-loc-3",
        "location_id": "demo-loc-3",
        "full_name": "Lisa Nguyen",
        "contact_name": "Lisa Nguyen",
        "title": "Accounts Payable",
        "role_type": "Billing Contact",
        "email": "ap@orioncarbons.example",
        "phone": "(318) 555-0103",
        "is_billing_contact": True,
        "is_active": True,
        "is_primary": True,
        "status": "Active",
    },
    {
        "id": "demo-cc-4",
        "customer_id": "demo-c-birla",
        "customer_location_id": "demo-loc-4",
        "location_id": "demo-loc-4",
        "full_name": "James Reed",
        "contact_name": "James Reed",
        "title": "Shipping Coordinator",
        "role_type": "Shipping Contact",
        "email": "shipping@orioncarbons.example",
        "phone": "(318) 555-0104",
        "is_active": True,
        "is_primary": True,
        "status": "Active",
    },
]


def load_customers() -> list[dict[str, Any]]:
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    def _load() -> list[dict[str, Any]]:
        rows, used = _cached_customers_rows()
        _mark_if_demo(used)
        return list(rows)

    with perf_span("data.load_customers"):
        return _catalog_session_get("customers", _load)


@st.cache_data(ttl=CATALOG_CACHE_TTL, show_spinner=False)
def _cached_customers_rows() -> tuple[tuple[dict[str, Any], ...], bool]:
    try:
        from app.services.customers_service import list_customers
    except ImportError:
        from services.customers_service import list_customers  # type: ignore
    rows, used = list_customers(demo=list(_DEMO_CUSTOMERS))
    return tuple(rows), used


def load_user_profiles(*, limit: int = 200) -> list[dict[str, Any]]:
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    def _load() -> list[dict[str, Any]]:
        return list(_cached_user_profiles(limit))

    with perf_span("data.load_user_profiles"):
        return _catalog_session_get(f"users_{limit}", _load)


@st.cache_data(ttl=CATALOG_CACHE_TTL, show_spinner=False)
def _cached_user_profiles(limit: int) -> tuple[dict[str, Any], ...]:
    try:
        from app.services.users_service import list_profiles
    except ImportError:
        from services.users_service import list_profiles  # type: ignore
    return tuple(list_profiles(limit=limit))


def load_labor_rates(*, active_only: bool = False) -> list[dict[str, Any]]:
    try:
        from app.perf_debug import perf_span
    except ImportError:
        from perf_debug import perf_span  # type: ignore

    def _load() -> list[dict[str, Any]]:
        return list(_cached_labor_rates_rows(active_only))

    with perf_span("data.load_labor_rates"):
        return _catalog_session_get(f"labor_rates_{active_only}", _load)


@st.cache_data(ttl=CATALOG_CACHE_TTL, show_spinner=False)
def _cached_labor_rates_rows(active_only: bool) -> tuple[dict[str, Any], ...]:
    try:
        from app.services.labor_rates_service import list_labor_rates
    except ImportError:
        from services.labor_rates_service import list_labor_rates  # type: ignore
    return tuple(list_labor_rates(active_only=active_only))


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


def load_locations_for_customer(customer_id: str) -> list[dict[str, Any]]:
    """Customer locations for estimate/job forms (same source as Customers module)."""
    return load_customer_locations(customer_id)


def load_customer_contacts(customer_id: str, location_id: str | None = None) -> list[dict[str, Any]]:
    try:
        from app.services.customers_service import get_customer_contacts
    except ImportError:
        from services.customers_service import get_customer_contacts  # type: ignore
    return get_customer_contacts(customer_id, location_id=location_id)


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


def customer_filter_options(*, include_names: set[str] | None = None) -> list[str]:
    """Active customer company names from the directory (for forms and filters)."""
    opts = {
        str(c.get("customer_name") or "").strip()
        for c in load_customers()
        if str(c.get("customer_name") or "").strip()
        and str(c.get("status") or "Active") == "Active"
    }
    if include_names:
        opts.update(str(n).strip() for n in include_names if str(n).strip())
    return sorted(opts)


def customer_id_for_name(customer_name: str) -> str:
    """Resolve directory customer id from company name."""
    needle = str(customer_name or "").strip().lower()
    if not needle:
        return ""
    for c in load_customers():
        for key in ("customer_name", "company_name"):
            val = str(c.get(key) or "").strip().lower()
            if val and val == needle:
                return str(c.get("id") or "").strip()
    return ""


def customer_location_select_options(customer_id: str) -> list[tuple[str, str]]:
    """Customer locations as (label, location_id), matching Customers contacts/locations tabs."""
    cid = str(customer_id or "").strip()
    if not cid:
        return []
    try:
        from app.services.customers_service import get_customer_location_options
    except ImportError:
        from services.customers_service import get_customer_location_options  # type: ignore
    return get_customer_location_options(cid, active_only=False)


def customer_contact_select_options(
    customer_id: str,
    location_id: str | None = None,
) -> list[tuple[str, str]]:
    """Active contacts scoped to customer/location as (label, contact_id)."""
    cid = str(customer_id or "").strip()
    if not cid:
        return []
    try:
        from app.services.customers_service import get_customer_contact_options
    except ImportError:
        from services.customers_service import get_customer_contact_options  # type: ignore
    return get_customer_contact_options(cid, location_id, active_only=False)


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


def persist_customer_contact(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    cust_id = str(ui.get("customer_id") or "").strip()
    if _demo_blocked(row_id) or _demo_blocked(cust_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.customers_service import save_customer_contact
    except ImportError:
        from services.customers_service import save_customer_contact  # type: ignore
    msg = "Contact updated." if row_id else "Contact added."
    return _persist_result(save_customer_contact(ui, row_id=row_id), success=msg)


def delete_customer_contact_row(row_id: str) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.customers_service import delete_customer_contact
    except ImportError:
        from services.customers_service import delete_customer_contact  # type: ignore
    return _persist_result(delete_customer_contact(row_id), success="Contact removed.")


def persist_customer_location(ui: dict[str, Any], *, row_id: str | None = None) -> tuple[bool, str]:
    cust_id = str(ui.get("customer_id") or "").strip()
    if _demo_blocked(row_id) or _demo_blocked(cust_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.customers_service import save_customer_location
    except ImportError:
        from services.customers_service import save_customer_location  # type: ignore
    msg = "Location updated." if row_id else "Location added."
    return _persist_result(save_customer_location(ui, row_id=row_id), success=msg)


def delete_customer_location_row(row_id: str) -> tuple[bool, str]:
    if _demo_blocked(row_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.customers_service import delete_customer_location
    except ImportError:
        from services.customers_service import delete_customer_location  # type: ignore
    return _persist_result(delete_customer_location(row_id), success="Location removed.")


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
    *,
    only_work_date: str | None = None,
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
    target_date = str(only_work_date or "")[:10] or None
    saved_ids_by_date: dict[str, set[str]] = {}
    try:
        from app.services.jobs_service import resolve_job_id_from_label
    except ImportError:
        from services.jobs_service import resolve_job_id_from_label  # type: ignore
    try:
        from app.services.timekeeping_service import clear_timekeeping_day_rows
    except ImportError:
        from services.timekeeping_service import clear_timekeeping_day_rows  # type: ignore
    for row in grid:
        work_date = str(row.get("date") or "")[:10]
        if not work_date:
            continue
        if target_date and work_date != target_date:
            continue
        day_total = (
            float(row.get("st") or 0)
            + float(row.get("ot") or 0)
            + float(row.get("dt") or 0)
        )
        day_id = str(row.get("day_id") or "").strip() or None
        if day_total <= 0.001:
            clear_timekeeping_day_rows(employee_id, work_date, keep_day_id=day_id)
            continue
        job_label = str(row.get("job") or "")
        ui = {
            "employee_id": employee_id,
            "week_start": ws,
            "work_date": work_date,
            "job_id": resolve_job_id_from_label(job_label),
            "job_label": job_label,
            "st_hours": row.get("st") or 0,
            "ot_hours": row.get("ot") or 0,
            "dt_hours": row.get("dt") or 0,
            "notes": row.get("notes") or "",
            "status": str(row.get("status") or "Draft"),
        }
        res = save_timekeeping_day(ui, row_id=day_id)
        err = _persist_result(res, success="")
        if err[0] is False and err[1]:
            errors.append(err[1])
            continue
        saved_id = day_id
        if res.ok and isinstance(res.data, dict):
            saved_id = str(res.data.get("id") or day_id or "").strip() or None
        if not saved_id and res.ok:
            try:
                from app.services.timekeeping_service import _find_timekeeping_day_row
            except ImportError:
                from services.timekeeping_service import _find_timekeeping_day_row  # type: ignore
            found = _find_timekeeping_day_row(
                employee_id,
                work_date,
                ui.get("job_id"),
                job_label=job_label,
            )
            if found:
                saved_id = str(found.get("id") or "").strip() or None
        if saved_id:
            saved_ids_by_date.setdefault(work_date, set()).add(saved_id)
    if errors:
        return False, errors[0]
    for wd, keep_ids in saved_ids_by_date.items():
        clear_timekeeping_day_rows(employee_id, wd, keep_day_ids=keep_ids)
    try:
        from app.services.timekeeping_service import sync_timekeeping_week_from_days
    except ImportError:
        from services.timekeeping_service import sync_timekeeping_week_from_days  # type: ignore
    sync_timekeeping_week_from_days(employee_id, week_start)
    return True, "Daily entries saved."


def persist_timekeeping_day_submit(day_id: str, employee_id: str, week_start: date) -> tuple[bool, str]:
    if _demo_blocked(employee_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.timekeeping_service import submit_timekeeping_day, sync_timekeeping_week_from_days
    except ImportError:
        from services.timekeeping_service import submit_timekeeping_day, sync_timekeeping_week_from_days  # type: ignore
    ok, msg = _persist_result(submit_timekeeping_day(day_id), success="Day submitted for approval.")
    if ok:
        sync_timekeeping_week_from_days(employee_id, week_start)
    return ok, msg


def persist_timekeeping_day_approve(
    day_id: str,
    employee_id: str,
    week_start: date,
    *,
    approved_by: str,
) -> tuple[bool, str]:
    if _demo_blocked(employee_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.timekeeping_service import approve_timekeeping_day, sync_timekeeping_week_from_days
    except ImportError:
        from services.timekeeping_service import approve_timekeeping_day, sync_timekeeping_week_from_days  # type: ignore
    ok, msg = _persist_result(
        approve_timekeeping_day(day_id, approved_by=approved_by),
        success="Day approved.",
    )
    if ok:
        sync_timekeeping_week_from_days(employee_id, week_start)
    return ok, msg


def persist_timekeeping_day_submit_for_date(
    employee_id: str,
    week_start: date,
    work_date: str,
) -> tuple[bool, str]:
    if _demo_blocked(employee_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.timekeeping_service import submit_timekeeping_days_for_work_date
    except ImportError:
        from services.timekeeping_service import submit_timekeeping_days_for_work_date  # type: ignore
    return _persist_result(
        submit_timekeeping_days_for_work_date(employee_id, week_start, work_date),
        success="Day submitted for approval.",
    )


def persist_timekeeping_day_approve_for_date(
    employee_id: str,
    week_start: date,
    work_date: str,
    *,
    approved_by: str,
) -> tuple[bool, str]:
    if _demo_blocked(employee_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.timekeeping_service import approve_timekeeping_days_for_work_date
    except ImportError:
        from services.timekeeping_service import approve_timekeeping_days_for_work_date  # type: ignore
    return _persist_result(
        approve_timekeeping_days_for_work_date(
            employee_id,
            week_start,
            work_date,
            approved_by=approved_by,
        ),
        success="Day approved.",
    )


def persist_timekeeping_day_reject_for_date(
    employee_id: str,
    week_start: date,
    work_date: str,
    *,
    approved_by: str,
) -> tuple[bool, str]:
    if _demo_blocked(employee_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.timekeeping_service import reject_timekeeping_days_for_work_date
    except ImportError:
        from services.timekeeping_service import reject_timekeeping_days_for_work_date  # type: ignore
    return _persist_result(
        reject_timekeeping_days_for_work_date(
            employee_id,
            week_start,
            work_date,
            approved_by=approved_by,
        ),
        success="Day rejected.",
    )


def persist_timekeeping_day_reject(
    day_id: str,
    employee_id: str,
    week_start: date,
    *,
    approved_by: str,
) -> tuple[bool, str]:
    if _demo_blocked(employee_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.timekeeping_service import reject_timekeeping_day, sync_timekeeping_week_from_days
    except ImportError:
        from services.timekeeping_service import reject_timekeeping_day, sync_timekeeping_week_from_days  # type: ignore
    ok, msg = _persist_result(
        reject_timekeeping_day(day_id, approved_by=approved_by),
        success="Day rejected.",
    )
    if ok:
        sync_timekeeping_week_from_days(employee_id, week_start)
    return ok, msg


def persist_timekeeping_submit(employee_id: str, week_start: date) -> tuple[bool, str]:
    if _demo_blocked(employee_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.timekeeping_service import submit_timekeeping_week
    except ImportError:
        from services.timekeeping_service import submit_timekeeping_week  # type: ignore
    return _persist_result(submit_timekeeping_week(employee_id, week_start), success="Submitted for approval.")


def persist_timekeeping_approve(
    employee_id: str,
    week_start: date,
    *,
    approved_by: str,
) -> tuple[bool, str]:
    if _demo_blocked(employee_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.timekeeping_service import approve_timekeeping_week
    except ImportError:
        from services.timekeeping_service import approve_timekeeping_week  # type: ignore
    return _persist_result(
        approve_timekeeping_week(employee_id, week_start, approved_by=approved_by),
        success="Timecard approved.",
    )


def persist_timekeeping_reject(
    employee_id: str,
    week_start: date,
    *,
    approved_by: str,
    notes: str = "",
) -> tuple[bool, str]:
    if _demo_blocked(employee_id):
        return False, _DEMO_SAVE_MSG
    try:
        from app.services.timekeeping_service import reject_timekeeping_week
    except ImportError:
        from services.timekeeping_service import reject_timekeeping_week  # type: ignore
    return _persist_result(
        reject_timekeeping_week(employee_id, week_start, approved_by=approved_by, notes=notes),
        success="Timecard rejected.",
    )
