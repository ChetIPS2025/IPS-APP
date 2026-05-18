"""
Data aggregation and business-logic services for the Reports module.
Combines cached query results into ready-to-render report payloads.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from .calculations import (
    asset_utilization,
    equipment_total_by_job,
    estimate_amount_for_job,
    gross_profit,
    inventory_issued_units,
    inventory_on_hand_value,
    inventory_usage_by_item,
    labor_cost_by_job,
    labor_hours_by_job,
    low_stock_count,
    margin_percentage,
    material_total_by_job,
    open_closed_job_counts,
)
from .queries import (
    fetch_asset_assignments,
    fetch_assets,
    fetch_employees,
    fetch_estimates,
    fetch_inventory_items,
    fetch_inventory_transactions,
    fetch_job_equipment,
    fetch_job_materials,
    fetch_jobs,
    fetch_time_entries,
)
from .utils import safe_float


def _job_label(job: dict[str, Any]) -> str:
    try:
        from app.services.job_service import job_row_select_label
    except ImportError:
        from services.job_service import job_row_select_label  # type: ignore
    return job_row_select_label(job)


def build_job_labels(jobs: list[dict[str, Any]]) -> dict[str, str]:
    return {str(j.get("id") or ""): _job_label(j) for j in jobs}


def load_financial_report_data(
    *,
    admin: bool,
    date_start: date | None = None,
    date_end: date | None = None,
) -> dict[str, Any]:
    """Load all data needed for the Financial / Job Costing report tab."""
    jobs = fetch_jobs(admin=admin)
    estimates = fetch_estimates(admin=admin)
    employees = fetch_employees()
    time_entries = fetch_time_entries(date_start=date_start, date_end=date_end, admin=admin)
    job_materials = fetch_job_materials(admin=admin)
    job_equipment = fetch_job_equipment(admin=admin)

    estimates_by_id = {str(e.get("id") or ""): e for e in estimates}
    employees_by_id = {str(e.get("id") or ""): e for e in employees}
    job_labels = build_job_labels(jobs)

    labor_by_job = labor_cost_by_job(time_entries, employees_by_id)
    material_by_job = material_total_by_job(job_materials)
    equipment_by_job = equipment_total_by_job(job_equipment)

    total_cost_by_job = {
        jid: safe_float(labor_by_job.get(jid)) + safe_float(material_by_job.get(jid)) + safe_float(equipment_by_job.get(jid))
        for jid in {*labor_by_job, *material_by_job, *equipment_by_job}
    }

    return {
        "jobs": jobs,
        "estimates_by_id": estimates_by_id,
        "employees_by_id": employees_by_id,
        "job_labels": job_labels,
        "labor_by_job": labor_by_job,
        "material_by_job": material_by_job,
        "equipment_by_job": equipment_by_job,
        "total_cost_by_job": total_cost_by_job,
    }


def load_labor_report_data(
    *,
    admin: bool,
    date_start: date | None = None,
    date_end: date | None = None,
) -> dict[str, Any]:
    """Load all data needed for the Labor / Time report tab."""
    jobs = fetch_jobs(admin=admin)
    employees = fetch_employees()
    time_entries = fetch_time_entries(date_start=date_start, date_end=date_end, admin=admin)

    employees_by_id = {str(e.get("id") or ""): e for e in employees}
    job_labels = build_job_labels(jobs)

    hours_by_job = labor_hours_by_job(time_entries)
    cost_by_job = labor_cost_by_job(time_entries, employees_by_id)

    return {
        "jobs": jobs,
        "employees": employees,
        "employees_by_id": employees_by_id,
        "time_entries": time_entries,
        "job_labels": job_labels,
        "hours_by_job": hours_by_job,
        "cost_by_job": cost_by_job,
        "total_hours": sum(hours_by_job.values()),
        "total_cost": sum(cost_by_job.values()),
    }


def load_inventory_report_data(
    *,
    admin: bool,
    date_start: date | None = None,
    date_end: date | None = None,
) -> dict[str, Any]:
    """Load all data needed for the Inventory / Materials report tab."""
    items = fetch_inventory_items(admin=admin)
    transactions = fetch_inventory_transactions(date_start=date_start, date_end=date_end, admin=admin)
    jobs = fetch_jobs(admin=admin)

    item_by_id = {str(r.get("id") or ""): r for r in items}
    job_labels = build_job_labels(jobs)
    usage = inventory_usage_by_item(transactions)

    return {
        "items": items,
        "item_by_id": item_by_id,
        "transactions": transactions,
        "job_labels": job_labels,
        "usage_by_item": usage,
        "on_hand_value": inventory_on_hand_value(items),
        "low_stock_count": low_stock_count(items),
        "issued_units": inventory_issued_units(transactions),
        "active_items": sum(1 for r in items if bool(r.get("is_active", True))),
    }


def load_asset_report_data(*, admin: bool) -> dict[str, Any]:
    """Load all data needed for the Asset report tab."""
    assets = fetch_assets(admin=admin)
    assignments = fetch_asset_assignments(admin=admin)
    jobs = fetch_jobs(admin=admin)
    job_labels = build_job_labels(jobs)
    utilization = asset_utilization(assets, assignments)

    return {
        "assets": assets,
        "assignments": assignments,
        "job_labels": job_labels,
        "utilization": utilization,
    }


def load_jobs_report_data(*, admin: bool) -> dict[str, Any]:
    """Load all data needed for the Job Summary report tab."""
    jobs = fetch_jobs(admin=admin)
    counts = open_closed_job_counts(jobs)
    job_labels = build_job_labels(jobs)

    return {
        "jobs": jobs,
        "job_labels": job_labels,
        "counts": counts,
    }
