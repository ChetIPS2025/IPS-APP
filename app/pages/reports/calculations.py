"""
Pure calculation functions for the Reports module.
No Streamlit or DB calls — only Python logic on plain data structures.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from .utils import safe_float, parse_iso_date


# ── Labor ──────────────────────────────────────────────────────────────────────


def labor_hours_by_job(
    time_entries: list[dict[str, Any]],
) -> dict[str, float]:
    """Sum hours per job_id from time_entries rows."""
    out: dict[str, float] = defaultdict(float)
    for te in time_entries:
        jid = str(te.get("job_id") or "").strip()
        if jid:
            out[jid] += safe_float(te.get("hours"))
    return dict(out)


def labor_cost_by_job(
    time_entries: list[dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """Sum (hours × hourly_rate) per job_id."""
    out: dict[str, float] = defaultdict(float)
    for te in time_entries:
        jid = str(te.get("job_id") or "").strip()
        if not jid:
            continue
        emp = employees_by_id.get(str(te.get("employee_id") or ""), {})
        rate = safe_float(emp.get("hourly_rate"))
        out[jid] += safe_float(te.get("hours")) * rate
    return dict(out)


def labor_hours_by_employee(
    time_entries: list[dict[str, Any]],
) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for te in time_entries:
        eid = str(te.get("employee_id") or "").strip()
        if eid:
            out[eid] += safe_float(te.get("hours"))
    return dict(out)


def labor_total(time_entries: list[dict[str, Any]], employees_by_id: dict[str, dict[str, Any]]) -> float:
    return sum(
        safe_float(te.get("hours")) * safe_float((employees_by_id.get(str(te.get("employee_id") or ""), {})).get("hourly_rate"))
        for te in time_entries
    )


# ── Materials ──────────────────────────────────────────────────────────────────


def _material_line_total(row: dict[str, Any]) -> float:
    for key in ("total_cost", "line_total"):
        if row.get(key) is not None and str(row.get(key)).strip() != "":
            return safe_float(row.get(key))
    qty = safe_float(row.get("qty") if row.get("qty") is not None else row.get("quantity"))
    uc = safe_float(row.get("unit_cost"))
    return qty * uc


def material_total(job_materials: list[dict[str, Any]]) -> float:
    return sum(_material_line_total(r) for r in job_materials)


def material_total_by_job(job_materials: list[dict[str, Any]]) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for r in job_materials:
        jid = str(r.get("job_id") or "").strip()
        if jid:
            out[jid] += _material_line_total(r)
    return dict(out)


# ── Equipment ──────────────────────────────────────────────────────────────────


def _equipment_line_total(row: dict[str, Any]) -> float:
    for key in ("total_cost", "line_total"):
        if row.get(key) is not None and str(row.get(key)).strip() != "":
            return safe_float(row.get(key))
    if row.get("qty") is not None:
        qty = safe_float(row.get("qty"))
        rate = safe_float(row.get("rate"))
        return qty * rate
    d = safe_float(row.get("usage_days"))
    h = safe_float(row.get("usage_hours"))
    rd = safe_float(row.get("rate_per_day"))
    rh = safe_float(row.get("rate_per_hour"))
    return d * rd + h * rh


def equipment_total(job_equipment: list[dict[str, Any]]) -> float:
    return sum(_equipment_line_total(r) for r in job_equipment)


def equipment_total_by_job(job_equipment: list[dict[str, Any]]) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for r in job_equipment:
        jid = str(r.get("job_id") or "").strip()
        if jid:
            out[jid] += _equipment_line_total(r)
    return dict(out)


# ── Job Costing ────────────────────────────────────────────────────────────────


def job_cost_totals(
    *,
    labor_by_job: dict[str, float],
    material_by_job: dict[str, float],
    equipment_by_job: dict[str, float],
    job_id: str,
) -> dict[str, float]:
    labor = safe_float(labor_by_job.get(job_id))
    mat = safe_float(material_by_job.get(job_id))
    eq = safe_float(equipment_by_job.get(job_id))
    total = labor + mat + eq
    return {"labor": labor, "materials": mat, "equipment": eq, "total": total}


def gross_profit(*, revenue: float, total_cost: float) -> float:
    return revenue - total_cost


def margin_percentage(*, revenue: float, total_cost: float) -> float | None:
    if revenue <= 0:
        return None
    return ((revenue - total_cost) / revenue) * 100.0


def estimate_amount_for_job(job: dict[str, Any], estimates_by_id: dict[str, dict[str, Any]]) -> float | None:
    eid = str(job.get("estimate_id") or "").strip()
    if not eid:
        return None
    est = estimates_by_id.get(eid) or {}
    for key in ("proposal_total", "final_bid"):
        raw = est.get(key)
        if raw is not None and str(raw).strip() != "":
            v = safe_float(raw)
            if v != 0 or key == "proposal_total":
                return v
    return None


# ── Inventory ──────────────────────────────────────────────────────────────────


def low_stock_count(inventory_items: list[dict[str, Any]]) -> int:
    count = 0
    for r in inventory_items:
        if not bool(r.get("is_active", True)):
            continue
        try:
            q = float(r.get("quantity_on_hand") or 0)
            rp = float(r.get("reorder_point") or 0)
        except (TypeError, ValueError):
            continue
        if q <= rp:
            count += 1
    return count


def inventory_on_hand_value(inventory_items: list[dict[str, Any]]) -> float:
    total = 0.0
    for r in inventory_items:
        if not bool(r.get("is_active", True)):
            continue
        q = safe_float(r.get("quantity_on_hand"))
        uc = safe_float(r.get("unit_cost"))
        total += q * uc
    return total


def inventory_issued_units(transactions: list[dict[str, Any]]) -> float:
    """Total units issued (negative qty = outbound)."""
    return sum(abs(safe_float(t.get("qty"))) for t in transactions if safe_float(t.get("qty")) < 0)


def inventory_usage_by_item(transactions: list[dict[str, Any]]) -> dict[str, float]:
    """Qty issued per inventory_item_id."""
    out: dict[str, float] = defaultdict(float)
    for t in transactions:
        if safe_float(t.get("qty")) >= 0:
            continue
        iid = str(t.get("inventory_item_id") or "").strip()
        if iid:
            out[iid] += abs(safe_float(t.get("qty")))
    return dict(out)


# ── Jobs ───────────────────────────────────────────────────────────────────────


def open_closed_job_counts(jobs: list[dict[str, Any]]) -> dict[str, int]:
    _ACTIVE_STATUSES = frozenset({"active", "in progress", "in_progress", "open", "awarded"})
    _CLOSED_STATUSES = frozenset({"complete", "completed", "closed", "done", "inactive"})
    active = sum(1 for j in jobs if str(j.get("status") or "").strip().lower() in _ACTIVE_STATUSES)
    closed = sum(1 for j in jobs if str(j.get("status") or "").strip().lower() in _CLOSED_STATUSES)
    return {"open": active, "closed": closed, "total": len(jobs)}


# ── Assets ─────────────────────────────────────────────────────────────────────


def asset_utilization(assets: list[dict[str, Any]], assignments: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute simple asset utilization counts."""
    total = len(assets)
    assigned_ids = {str(a.get("asset_id") or "") for a in assignments if a.get("asset_id") and not a.get("returned_date")}
    assigned = len(assigned_ids)
    available = total - assigned
    by_status: dict[str, int] = defaultdict(int)
    for asset in assets:
        s = str(asset.get("status") or "unknown").strip().lower()
        by_status[s] += 1
    return {
        "total": total,
        "assigned": assigned,
        "available": max(0, available),
        "by_status": dict(by_status),
    }
