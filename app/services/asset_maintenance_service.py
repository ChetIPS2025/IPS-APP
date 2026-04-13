from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except Exception:
        return None


def calculate_next_service(
    service_date: Any,
    hour_meter: Any,
    mileage: Any,
    rule: dict | None,
) -> dict:
    rule = rule or {}
    base_date = parse_date(service_date)
    base_hours = to_float(hour_meter)
    base_mileage = to_float(mileage)

    interval_days = int(rule.get("interval_days") or 0)
    interval_hours = to_float(rule.get("interval_hours"))
    interval_miles = to_float(rule.get("interval_miles"))

    return {
        "next_service_date": (base_date + timedelta(days=interval_days)).isoformat() if base_date and interval_days > 0 else None,
        "next_service_hours": round(base_hours + interval_hours, 2) if interval_hours > 0 else 0,
        "next_service_mileage": round(base_mileage + interval_miles, 2) if interval_miles > 0 else 0,
    }


def maintenance_due_status(asset: dict, latest_maintenance: dict | None) -> str:
    if not latest_maintenance:
        return "No History"

    today = date.today()
    next_date = parse_date(latest_maintenance.get("next_service_date"))
    next_hours = to_float(latest_maintenance.get("next_service_hours"))
    next_miles = to_float(latest_maintenance.get("next_service_mileage"))

    asset_hours = to_float(asset.get("hour_meter"))
    asset_miles = to_float(asset.get("mileage"))

    overdue = False
    due_soon = False

    if next_date:
        if today > next_date:
            overdue = True
        elif (next_date - today).days <= 14:
            due_soon = True

    if next_hours > 0:
        if asset_hours >= next_hours:
            overdue = True
        elif asset_hours >= next_hours - 25:
            due_soon = True

    if next_miles > 0:
        if asset_miles >= next_miles:
            overdue = True
        elif asset_miles >= next_miles - 250:
            due_soon = True

    if overdue:
        return "Overdue"
    if due_soon:
        return "Due Soon"
    return "OK"
