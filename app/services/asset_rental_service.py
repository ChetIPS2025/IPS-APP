"""Rental rate helpers for assets and estimate equipment lines."""

from __future__ import annotations

from typing import Any

RENTAL_RATE_UNITS: tuple[str, ...] = ("Hours", "Days", "Weeks")


def normalize_rental_rate_unit(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw.startswith("hour"):
        return "Hours"
    if raw.startswith("week"):
        return "Weeks"
    if raw.startswith("day"):
        return "Days"
    return "Days"


def primary_rental_rate_from_asset(row: dict[str, Any] | None) -> float:
    """Rate amount for the asset's configured rental_rate_unit."""
    if not row:
        return 0.0
    unit = normalize_rental_rate_unit(row.get("rental_rate_unit"))
    if unit == "Hours":
        return float(row.get("hourly_rate") or 0)
    if unit == "Weeks":
        return float(row.get("rental_weekly_rate") or row.get("weekly_rate") or 0)
    return float(row.get("rental_daily_rate") or row.get("daily_rate") or 0)


def rental_rates_payload(*, rate: Any, unit: Any) -> dict[str, Any]:
    """Map a single rental rate + unit into assets table rate columns."""
    u = normalize_rental_rate_unit(unit)
    try:
        amount = float(rate or 0)
    except (TypeError, ValueError):
        amount = 0.0
    if amount < 0:
        amount = 0.0
    out: dict[str, Any] = {
        "rental_rate_unit": u,
        "hourly_rate": 0,
        "daily_rate": 0,
        "weekly_rate": 0,
        "rental_daily_rate": 0,
        "rental_weekly_rate": 0,
    }
    if amount <= 0:
        return out
    if u == "Hours":
        out["hourly_rate"] = amount
    elif u == "Weeks":
        out["weekly_rate"] = amount
        out["rental_weekly_rate"] = amount
    else:
        out["daily_rate"] = amount
        out["rental_daily_rate"] = amount
    return out


def apply_rental_ui_to_payload(payload: dict[str, Any], ui: dict[str, Any]) -> None:
    """Merge rental pricing fields from an asset form into a Supabase assets payload."""
    if "is_rentable" in ui:
        payload["is_rentable"] = bool(ui.get("is_rentable"))
    if "rental_notes" in ui:
        payload["rental_notes"] = str(ui.get("rental_notes") or "").strip()
    if "rental_default_markup_percent" in ui:
        try:
            payload["rental_default_markup_percent"] = float(
                ui.get("rental_default_markup_percent") or 0
            )
        except (TypeError, ValueError):
            payload["rental_default_markup_percent"] = 0.0
    if "rental_rate" in ui or "rental_rate_unit" in ui:
        payload.update(
            rental_rates_payload(
                rate=ui.get("rental_rate"),
                unit=ui.get("rental_rate_unit"),
            )
        )
