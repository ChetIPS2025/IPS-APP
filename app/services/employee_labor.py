"""Labor cost from employee hourly / overtime rates (time entries, job costing)."""

from __future__ import annotations

from typing import Any


def effective_overtime_rate(employee: dict[str, Any]) -> float:
    hr = float(employee.get("hourly_rate") or 0)
    ot = employee.get("overtime_rate")
    if ot is None or ot == "":
        return hr * 1.5
    return float(ot or 0)


def compute_labor_cost_from_employee(
    employee: dict[str, Any],
    straight_time_hours: float,
    overtime_hours: float,
) -> float:
    st_h = float(straight_time_hours or 0)
    ot_h = float(overtime_hours or 0)
    hr = float(employee.get("hourly_rate") or 0)
    return st_h * hr + ot_h * effective_overtime_rate(employee)


def entry_labor_dollars(
    entry: dict[str, Any],
    labor_rate_map: dict[str, dict[str, float]],
    employees_by_id: dict[str, dict[str, Any]],
) -> float:
    """
    Cost for one time entry: prefer stored labor_cost; else employee rates; else labor classification (legacy).
    """
    lc = entry.get("labor_cost")
    if lc is not None and str(lc).strip() != "":
        try:
            return float(lc)
        except (TypeError, ValueError):
            pass

    eid = entry.get("employee_id")
    if eid:
        emp = employees_by_id.get(str(eid))
        if emp:
            return compute_labor_cost_from_employee(
                emp,
                float(entry.get("straight_time_hours", 0) or 0),
                float(entry.get("overtime_hours", 0) or 0),
            )

    classification = str(entry.get("labor_classification", "")).strip()
    rate_info = labor_rate_map.get(classification, {"st_rate": 0.0, "ot_rate": 0.0})
    st_hours = float(entry.get("straight_time_hours", 0) or 0)
    ot_hours = float(entry.get("overtime_hours", 0) or 0)
    return (st_hours * rate_info["st_rate"]) + (ot_hours * rate_info["ot_rate"])
