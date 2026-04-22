"""Roll up job costing (labor, materials, equipment, expenses) keyed by ``job_id``."""

from __future__ import annotations

from typing import Any

try:
    from services.employee_labor import entry_labor_dollars
except ImportError:
    from app.services.employee_labor import entry_labor_dollars  # type: ignore

try:
    from services.job_service import job_display_primary
except ImportError:
    from app.services.job_service import job_display_primary  # type: ignore

try:
    from services.time_grid_service import grid_labor_cost_dollars
except ImportError:
    from app.services.time_grid_service import grid_labor_cost_dollars  # type: ignore


def estimate_proposal_value(estimate: dict[str, Any] | None) -> float:
    """Display / profit baseline from linked estimate (proposal first, then final bid)."""
    if not estimate:
        return 0.0
    pt = estimate.get("proposal_total")
    if pt is not None and str(pt).strip() != "":
        try:
            return float(pt)
        except (TypeError, ValueError):
            pass
    fb = estimate.get("final_bid")
    if fb is not None and str(fb).strip() != "":
        try:
            return float(fb)
        except (TypeError, ValueError):
            pass
    return 0.0


def awarded_or_proposal_amount(job: dict[str, Any], estimate: dict[str, Any] | None) -> float:
    """Contract-style value: job.awarded_amount, else estimate proposal/final."""
    aw = float(job.get("awarded_amount", 0) or 0)
    if aw > 0:
        return aw
    return estimate_proposal_value(estimate or {})


def material_line_total(quantity: float, unit_cost: float) -> float:
    return float(quantity or 0) * float(unit_cost or 0)


def equipment_rates_from_asset(asset: dict[str, Any] | None) -> tuple[float, float]:
    """
    Default daily rate from ``rental_daily_rate``; hourly defaults to daily/8 when no explicit hourly.
    """
    if not asset:
        return 0.0, 0.0
    day = float(asset.get("rental_daily_rate") or 0)
    hour = day / 8.0 if day else 0.0
    return hour, day


def equipment_line_total(
    usage_hours: float,
    usage_days: float,
    rate_per_hour: float,
    rate_per_day: float,
) -> float:
    return float(usage_days or 0) * float(rate_per_day or 0) + float(usage_hours or 0) * float(rate_per_hour or 0)


def _entry_employee_display(t: dict, employees_by_id: dict[str, dict[str, Any]]) -> str:
    eid = t.get("employee_id")
    if eid and str(eid) in employees_by_id:
        nm = str(employees_by_id[str(eid)].get("name") or "").strip()
        if nm:
            return nm
    return str(t.get("employee_name", "") or "").strip() or "—"


def build_labor_slice_for_job(
    job: dict[str, Any],
    *,
    customer_name_by_id: dict[Any, str],
    time_entries: list[dict[str, Any]],
    all_grid_te: list[dict[str, Any]],
    labor_rate_map: dict[str, dict[str, float]],
    employees_by_id: dict[str, dict[str, Any]],
) -> tuple[float, list[dict[str, Any]]]:
    """Returns (actual_labor_dollars, labor_detail_rows)."""
    job_id = job.get("id")
    labor_detail_rows: list[dict[str, Any]] = []
    actual_labor = 0.0
    customer_id = job.get("customer_id")

    job_time_entries = [
        t
        for t in time_entries
        if t.get("job_id") == job_id and str(t.get("status", "")).strip() == "Approved"
    ]
    for t in job_time_entries:
        st_hours = float(t.get("straight_time_hours", 0) or 0)
        ot_hours = float(t.get("overtime_hours", 0) or 0)
        line_cost = entry_labor_dollars(t, labor_rate_map, employees_by_id)
        actual_labor += line_cost
        labor_detail_rows.append(
            {
                "job_number": job_display_primary(job),
                "job_name": job.get("job_name", ""),
                "customer_name": customer_name_by_id.get(customer_id, ""),
                "job_status": job.get("status", ""),
                "employee": _entry_employee_display(t, employees_by_id),
                "straight_time_hours": st_hours,
                "overtime_hours": ot_hours,
                "labor_cost": line_cost,
                "source": "Time entry (legacy)",
            }
        )

    for te in all_grid_te:
        if not te.get("job_id"):
            continue
        if str(te.get("job_id")) != str(job_id):
            continue
        hours = float(te.get("hours", 0) or 0)
        emp = employees_by_id.get(str(te.get("employee_id")))
        line_cost = grid_labor_cost_dollars(hours, emp)
        actual_labor += line_cost
        ename = str(emp.get("name", "")).strip() if emp else "—"
        labor_detail_rows.append(
            {
                "job_number": job_display_primary(job),
                "job_name": job.get("job_name", ""),
                "customer_name": customer_name_by_id.get(customer_id, ""),
                "job_status": job.get("status", ""),
                "employee": ename,
                "straight_time_hours": hours,
                "overtime_hours": 0.0,
                "labor_cost": line_cost,
                "source": "Weekly grid",
            }
        )

    return actual_labor, labor_detail_rows


def sum_job_materials_lines(rows: list[dict[str, Any]], job_id: Any) -> float:
    total = 0.0
    for r in rows:
        if r.get("job_id") != job_id:
            continue
        total += float(r.get("line_total", 0) or 0)
    return total


def sum_job_equipment_lines(rows: list[dict[str, Any]], job_id: Any) -> float:
    total = 0.0
    for r in rows:
        if r.get("job_id") != job_id:
            continue
        total += float(r.get("line_total", 0) or 0)
    return total


def build_expense_slices_for_job(
    job_id: Any,
    job_expenses: list[dict[str, Any]],
) -> tuple[float, float, float, float]:
    """
    Returns (materials_from_expenses, travel_bucket, other_expenses, all_approved_non_rejected).

    Approved/Paid only; materials category split for backward-compatible rollups.
    """
    approved = [
        e
        for e in job_expenses
        if e.get("job_id") == job_id and str(e.get("status", "")).strip() in {"Approved", "Paid"}
    ]
    materials_x = 0.0
    travel_x = 0.0
    other_x = 0.0
    for e in approved:
        amt = float(e.get("amount", 0) or 0)
        cat = str(e.get("category", "")).strip()
        if cat == "Materials":
            materials_x += amt
        elif cat in {"Travel", "Fuel", "Lodging", "Meals", "Freight"}:
            travel_x += amt
        else:
            other_x += amt
    expenses_combined = travel_x + other_x
    return materials_x, travel_x, other_x, expenses_combined


def build_job_summary_row(
    job: dict[str, Any],
    *,
    customer_name_by_id: dict[Any, str],
    estimate_by_id: dict[Any, dict[str, Any]],
    labor_rate_map: dict[str, dict[str, float]],
    employees_by_id: dict[str, dict[str, Any]],
    time_entries: list[dict[str, Any]],
    all_grid_te: list[dict[str, Any]],
    asset_usage_logs: list[dict[str, Any]],
    job_expenses: list[dict[str, Any]],
    job_materials: list[dict[str, Any]],
    job_equipment: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    One overview row (for the all-jobs dataframe) plus labor detail lines for this job.

    Totals include: legacy labor, ``time_entries`` grid, ``asset_usage_logs``,
    ``job_materials`` / ``job_equipment`` lines, and categorized ``job_expenses``.
    """
    job_id = job.get("id")
    customer_id = job.get("customer_id")
    estimate_id = job.get("estimate_id")
    estimate = estimate_by_id.get(estimate_id, {}) if estimate_id else {}

    estimated_labor = float(estimate.get("labor_total", 0) or 0)
    estimated_equipment = float(estimate.get("equipment_total", 0) or 0)
    estimated_materials = float(estimate.get("material_sell_basis", 0) or 0)
    estimated_travel = float(estimate.get("travel_total", 0) or 0)
    estimated_total = float(estimate.get("final_bid", 0) or 0)

    awarded_amount = awarded_or_proposal_amount(job, estimate)

    actual_labor, labor_detail_rows = build_labor_slice_for_job(
        job,
        customer_name_by_id=customer_name_by_id,
        time_entries=time_entries,
        all_grid_te=all_grid_te,
        labor_rate_map=labor_rate_map,
        employees_by_id=employees_by_id,
    )

    jm_sum = sum_job_materials_lines(job_materials, job_id)
    mat_from_exp, travel_x, other_x, expenses_combined = build_expense_slices_for_job(job_id, job_expenses)
    actual_materials = jm_sum + mat_from_exp

    je_sum = sum_job_equipment_lines(job_equipment, job_id)
    job_asset_usage = [u for u in asset_usage_logs if u.get("job_id") == job_id]
    actual_equipment_logs = 0.0
    for u in job_asset_usage:
        usage_days = float(u.get("usage_days", 0) or 0)
        rate_per_day = float(u.get("rate_per_day", 0) or 0)
        usage_hours = float(u.get("usage_hours", 0) or 0)
        rate_per_hour = float(u.get("rate_per_hour", 0) or 0)
        actual_equipment_logs += (usage_days * rate_per_day) + (usage_hours * rate_per_hour)
    actual_equipment = je_sum + actual_equipment_logs

    actual_travel = travel_x
    actual_other = other_x

    actual_total_cost = actual_labor + actual_equipment + actual_materials + actual_travel + actual_other
    gross_profit = awarded_amount - actual_total_cost
    gross_margin_pct = (gross_profit / awarded_amount * 100) if awarded_amount else 0.0

    row = {
        "job_number": job_display_primary(job),
        "job_name": job.get("job_name", ""),
        "customer_name": customer_name_by_id.get(customer_id, ""),
        "status": job.get("status", ""),
        "project_manager": job.get("project_manager", ""),
        "supervisor": job.get("supervisor", ""),
        "awarded_amount": awarded_amount,
        "estimated_total": estimated_total,
        "estimated_labor": estimated_labor,
        "estimated_equipment": estimated_equipment,
        "estimated_materials": estimated_materials,
        "estimated_travel": estimated_travel,
        "actual_labor": actual_labor,
        "actual_equipment": actual_equipment,
        "actual_materials": actual_materials,
        "actual_travel": actual_travel,
        "actual_other": actual_other,
        "actual_total_cost": actual_total_cost,
        "gross_profit": gross_profit,
        "gross_margin_pct": gross_margin_pct,
        # Extra buckets for job-detail panel (non-table)
        "_jm_lines": jm_sum,
        "_je_lines": je_sum,
        "_expenses_combined": expenses_combined,
        "_proposal_value": estimate_proposal_value(estimate),
    }
    return row, labor_detail_rows
