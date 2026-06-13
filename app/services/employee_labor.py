"""Labor cost from employee hourly / overtime rates (time entries, job costing)."""

from __future__ import annotations

from typing import Any


def effective_overtime_rate(employee: dict[str, Any]) -> float:
    hr = float(employee.get("hourly_rate") or 0)
    ot = employee.get("overtime_rate")
    if ot is None or ot == "":
        return hr * 1.5
    return float(ot or 0)


def burden_multiplier(employee: dict[str, Any] | None) -> float:
    if not employee:
        return 1.0
    explicit = employee.get("burdened_hourly_rate")
    if explicit is not None and str(explicit).strip() != "":
        return 1.0
    mult = employee.get("burden_multiplier")
    if mult is None or str(mult).strip() == "":
        return 1.35
    try:
        return max(0.0, float(mult))
    except (TypeError, ValueError):
        return 1.35


def burdened_hourly_rate(employee: dict[str, Any] | None) -> float:
    if not employee:
        return 0.0
    explicit = employee.get("burdened_hourly_rate")
    if explicit is not None and str(explicit).strip() != "":
        try:
            return float(explicit)
        except (TypeError, ValueError):
            pass
    hr = float(employee.get("hourly_rate") or 0)
    return hr * burden_multiplier(employee)


def burdened_overtime_rate(employee: dict[str, Any] | None) -> float:
    if not employee:
        return 0.0
    explicit = employee.get("burdened_hourly_rate")
    if explicit is not None and str(explicit).strip() != "":
        try:
            return float(explicit) * 1.5
        except (TypeError, ValueError):
            pass
    return effective_overtime_rate(employee) * burden_multiplier(employee)


def burdened_doubletime_rate(employee: dict[str, Any] | None) -> float:
    return burdened_hourly_rate(employee) * 2.0


def compute_burdened_labor_cost(
    employee: dict[str, Any] | None,
    straight_time_hours: float,
    overtime_hours: float,
    doubletime_hours: float = 0.0,
) -> float:
    st_h = float(straight_time_hours or 0)
    ot_h = float(overtime_hours or 0)
    dt_h = float(doubletime_hours or 0)
    return (
        st_h * burdened_hourly_rate(employee)
        + ot_h * burdened_overtime_rate(employee)
        + dt_h * burdened_doubletime_rate(employee)
    )


def time_entry_burdened_cost(
    entry: dict[str, Any],
    employee: dict[str, Any] | None,
) -> tuple[float, float]:
    """Return (unit_cost, total_cost) for a time_entries row using burdened rates."""
    hours = float(entry.get("hours") or 0)
    if hours <= 0:
        return 0.0, 0.0
    tt = str(entry.get("time_type") or "ST").strip().upper()
    if tt in {"OT", "O/T", "O-T"}:
        rate = burdened_overtime_rate(employee)
    elif tt in {"DT", "D/T", "D-T"}:
        rate = burdened_doubletime_rate(employee)
    else:
        rate = burdened_hourly_rate(employee)
    total = round(hours * rate, 2)
    return rate, total


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
