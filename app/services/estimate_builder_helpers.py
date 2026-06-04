"""Option builders and predetermined pricing helpers for estimate cost builder."""

from __future__ import annotations

from typing import Any

try:
    from app.pages._core._data import load_assets, load_inventory
    from app.services.repository import fetch_rows
    from app.utils.estimate_calculations import (
        calc_equipment_line,
        calc_labor_line,
        calc_material_line,
        calc_simple_line,
    )
except ImportError:
    from pages._core._data import load_assets, load_inventory  # type: ignore
    from services.repository import fetch_rows  # type: ignore
    from utils.estimate_calculations import (  # type: ignore
        calc_equipment_line,
        calc_labor_line,
        calc_material_line,
        calc_simple_line,
    )

DEFAULT_LABOR_RATES: dict[str, float] = {
    "Superintendent": 75.0,
    "Supervisor": 65.0,
    "Foreman": 58.0,
    "Skilled Labor": 48.0,
    "General Labor": 38.0,
    "Welder": 62.0,
    "Pipefitter": 52.0,
    "Electrician": 54.0,
    "Operator": 55.0,
    "Helper": 32.0,
    "Admin / PM": 75.0,
    "Other": 45.0,
}

OT_MULTIPLIER = 1.5
DT_MULTIPLIER = 2.0

TRAVEL_DEFAULTS: dict[str, float] = {
    "mileage_rate": 0.67,
    "per_diem_rate": 75.0,
    "lodging_rate": 150.0,
    "hourly_travel_rate": 45.0,
}


def _dedupe_label(base: str, seen: dict[str, int], suffix: str) -> str:
    key = base.strip().lower()
    if not key:
        return base
    count = seen.get(key, 0) + 1
    seen[key] = count
    if count == 1:
        return base
    detail = suffix.strip()
    return f"{base} — {detail}" if detail else f"{base} ({count})"


def _inventory_row_to_option(row: dict[str, Any]) -> dict[str, Any]:
    description = str(
        row.get("description")
        or row.get("name")
        or row.get("item_name")
        or "—"
    ).strip()
    sku = str(row.get("sku") or "").strip()
    category = str(row.get("category") or "").strip()
    unit = str(row.get("unit") or "EA").strip() or "EA"
    unit_cost = float(row.get("unit_cost") or 0)
    vendor_name = str(row.get("vendor") or row.get("vendor_name") or "").strip()
    vendor_id = row.get("vendor_id")
    taxable = row.get("taxable")
    if taxable is None:
        taxable = True
    return {
        "id": str(row.get("id") or ""),
        "description": description,
        "sku": sku,
        "category": category,
        "unit": unit,
        "unit_cost": unit_cost,
        "vendor_id": str(vendor_id) if vendor_id else None,
        "vendor_name": vendor_name,
        "vendor": vendor_name,
        "taxable": bool(taxable),
    }


def get_inventory_options_for_estimate() -> list[dict[str, Any]]:
    """Build inventory picker rows with clean description-only labels."""
    seen: dict[str, int] = {}
    out: list[dict[str, Any]] = []
    for row in load_inventory():
        opt = _inventory_row_to_option(row)
        suffix = opt["category"] if opt["category"] and opt["category"] != "—" else "Inventory"
        label = _dedupe_label(opt["description"], seen, suffix)
        opt["label"] = label
        out.append(opt)
    return out


def inventory_options_as_select() -> list[tuple[str, dict[str, Any]]]:
    return [(opt["label"], opt) for opt in get_inventory_options_for_estimate()]


def _catalog_row_to_option(row: dict[str, Any]) -> dict[str, Any]:
    purchase = float(row.get("purchase_price") or 0)
    sell_raw = row.get("sell_price")
    if sell_raw not in (None, ""):
        sell = float(sell_raw)
    else:
        sell = round(purchase * 1.25, 2) if purchase else 0.0
    markup = round(((sell - purchase) / purchase) * 100.0, 2) if purchase else float(row.get("markup_pct") or 0)
    description = str(row.get("description") or row.get("item_key") or "—").strip()
    return {
        "id": str(row.get("id") or row.get("item_key") or ""),
        "item_key": str(row.get("item_key") or ""),
        "description": description,
        "sku": str(row.get("vendor_item_number") or row.get("item_key") or ""),
        "category": str(row.get("category") or "Pricing Guide"),
        "unit": str(row.get("unit") or "EA"),
        "unit_cost": purchase,
        "markup_pct": markup,
        "sell_price": sell,
        "vendor": str(row.get("vendor_item_number") or row.get("vendor") or ""),
        "vendor_name": str(row.get("vendor_item_number") or row.get("vendor") or ""),
        "taxable": True,
    }


def get_pricing_guide_options_for_estimate() -> list[dict[str, Any]]:
    return get_unified_pricing_options_for_estimate()


def get_unified_pricing_options_for_estimate() -> list[dict[str, Any]]:
    """All active pricing guide items for estimate builder (DESCRIPTION — TYPE labels)."""
    try:
        from app.services.pricing_guide_service import (
            cached_pricing_guide_rows,
            pricing_item_to_estimate_option,
        )
    except ImportError:
        from services.pricing_guide_service import (  # type: ignore
            cached_pricing_guide_rows,
            pricing_item_to_estimate_option,
        )
    seen: dict[str, int] = {}
    out: list[dict[str, Any]] = []
    for row in cached_pricing_guide_rows(include_inactive=False):
        opt = pricing_item_to_estimate_option(row)
        base_label = f"{opt['description']} — {opt['item_type']}"
        opt["label"] = _dedupe_label(base_label, seen, opt["item_type"])
        out.append(opt)
    if out:
        return out

    try:
        from app.services.estimate_materials_catalog import cached_estimate_materials_catalog_rows
    except ImportError:
        from services.estimate_materials_catalog import cached_estimate_materials_catalog_rows  # type: ignore
    for row in cached_estimate_materials_catalog_rows():
        opt = _catalog_row_to_option(row)
        suffix = opt["category"] if opt["category"] and opt["category"] != "—" else "Pricing Guide"
        label = _dedupe_label(opt["description"], seen, suffix)
        opt["label"] = label
        opt["item_type"] = str(row.get("item_type") or "Material")
        out.append(opt)
    return out


def pricing_guide_options_as_select() -> list[tuple[str, dict[str, Any]]]:
    return [(opt["label"], opt) for opt in get_unified_pricing_options_for_estimate()]


def unified_pricing_options_as_select() -> list[tuple[str, dict[str, Any]]]:
    return pricing_guide_options_as_select()


def _asset_row_to_option(row: dict[str, Any]) -> dict[str, Any]:
    asset_name = str(row.get("asset_name") or row.get("name") or "—").strip()
    asset_number = str(row.get("asset_number") or "").strip()
    category = str(row.get("category") or row.get("asset_type") or "").strip()
    rental_daily = float(row.get("rental_daily_rate") or row.get("daily_rate") or 0)
    rental_weekly = float(row.get("rental_weekly_rate") or row.get("weekly_rate") or 0)
    hourly = float(row.get("hourly_rate") or 0)
    if not hourly and rental_daily:
        hourly = rental_daily / 8.0
    daily = rental_daily or (hourly * 8.0 if hourly else 0.0)
    weekly = rental_weekly or (daily * 5.0 if daily else 0.0)
    cost_rate = hourly or daily or weekly
    return {
        "id": str(row.get("id") or ""),
        "asset_number": asset_number,
        "asset_name": asset_name,
        "category": category,
        "hourly_rate": hourly,
        "daily_rate": daily,
        "weekly_rate": weekly,
        "rental_daily_rate": rental_daily,
        "rental_weekly_rate": rental_weekly,
        "cost_rate": cost_rate,
    }


def get_asset_options_for_estimate() -> list[dict[str, Any]]:
    seen: dict[str, int] = {}
    out: list[dict[str, Any]] = []
    for row in load_assets():
        opt = _asset_row_to_option(row)
        suffix = opt["category"] if opt["category"] and opt["category"] != "—" else "Equipment"
        label = _dedupe_label(opt["asset_name"], seen, suffix)
        opt["label"] = label
        out.append(opt)
    return out


def asset_options_as_select() -> list[tuple[str, dict[str, Any]]]:
    return [(opt["label"], opt) for opt in get_asset_options_for_estimate()]


def _normalize_labor_classification(name: str) -> str:
    return str(name or "").strip()


def get_labor_rate_options() -> list[dict[str, Any]]:
    """Labor roles with ST/OT/DT rates from labor_rates table or defaults."""
    by_role: dict[str, dict[str, Any]] = {}
    try:
        rows, _ = fetch_rows("labor_rates", order_by="classification")
        for row in rows or []:
            if row.get("is_active") is False:
                continue
            role = _normalize_labor_classification(row.get("classification"))
            if not role:
                continue
            st_rate = float(row.get("st_rate") or 0)
            ot_rate = float(row.get("ot_rate") or 0)
            if not ot_rate and st_rate:
                ot_rate = st_rate * OT_MULTIPLIER
            dt_rate = float(row.get("dt_rate") or 0)
            if not dt_rate and st_rate:
                dt_rate = st_rate * DT_MULTIPLIER
            ot_mult = float(row.get("ot_multiplier") or OT_MULTIPLIER)
            dt_mult = float(row.get("dt_multiplier") or DT_MULTIPLIER)
            by_role[role.lower()] = {
                "role_name": role,
                "label": role,
                "st_rate": st_rate,
                "ot_rate": ot_rate or st_rate * ot_mult,
                "dt_rate": dt_rate or st_rate * dt_mult,
                "ot_multiplier": ot_mult,
                "dt_multiplier": dt_mult,
            }
    except Exception:
        pass

    for role, st_rate in DEFAULT_LABOR_RATES.items():
        key = role.lower()
        if key not in by_role:
            by_role[key] = {
                "role_name": role,
                "label": role,
                "st_rate": st_rate,
                "ot_rate": st_rate * OT_MULTIPLIER,
                "dt_rate": st_rate * DT_MULTIPLIER,
                "ot_multiplier": OT_MULTIPLIER,
                "dt_multiplier": DT_MULTIPLIER,
            }

    return sorted(by_role.values(), key=lambda r: r["role_name"].lower())


def labor_options_as_select() -> list[tuple[str, dict[str, Any]]]:
    return [(opt["label"], opt) for opt in get_labor_rate_options()]


def resolve_equipment_cost_rate(asset: dict[str, Any] | None, duration_unit: str) -> float:
    if not asset:
        return 0.0
    unit = str(duration_unit or "Hours").strip().lower()
    hourly = float(asset.get("hourly_rate") or 0)
    daily = float(asset.get("daily_rate") or asset.get("rental_daily_rate") or 0)
    weekly = float(asset.get("weekly_rate") or asset.get("rental_weekly_rate") or 0)
    if not hourly and daily:
        hourly = daily / 8.0
    if unit.startswith("week"):
        if weekly:
            return weekly
        if daily:
            return daily * 5.0
    if unit.startswith("day"):
        if daily:
            return daily
        if hourly:
            return hourly * 8.0
    if hourly:
        return hourly
    if daily:
        return daily
    if weekly:
        return weekly / 40.0 if weekly else 0.0
    return float(asset.get("cost_rate") or 0)


def material_line_totals(qty: float, unit_cost: float, markup_percent: float) -> dict[str, float]:
    return calc_material_line(qty, unit_cost, markup_percent)


def labor_line_totals(
    st_hours: float,
    ot_hours: float,
    st_rate: float,
    ot_rate: float,
    markup_percent: float,
) -> dict[str, float]:
    return calc_labor_line(st_hours, ot_hours, 0, st_rate, ot_rate, 0, markup_percent)


def equipment_line_totals(
    quantity: float,
    duration: float,
    cost_rate: float,
    markup_percent: float,
) -> dict[str, float]:
    return calc_equipment_line(quantity, duration, cost_rate, markup_percent)


def simple_line_totals(cost_total: float, markup_percent: float) -> dict[str, float]:
    return calc_simple_line(cost_total, markup_percent)


def travel_defaults() -> dict[str, float]:
    return dict(TRAVEL_DEFAULTS)
