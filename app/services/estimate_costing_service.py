"""Estimate costing CRUD, rollups, and bundle reads (no Streamlit)."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.services.repository import (
    ServiceResult,
    clear_all_data_caches,
    delete_row,
    fetch_rows,
    insert_row,
    update_row,
)
from app.utils.estimate_calculations import (
    TRAVEL_TYPES,
    calc_equipment_line,
    calc_labor_line,
    calc_material_line,
    calc_simple_line,
    calc_totals,
    calc_travel_line,
)

LABOR_ROLE_TYPES = [
    "Superintendent",
    "Supervisor",
    "Foreman",
    "Skilled Labor",
    "General Labor",
    "Welder",
    "Pipefitter",
    "Electrician",
    "Operator",
    "Helper",
    "Admin / PM",
    "Other",
]

DURATION_UNITS = ("Hours", "Days", "Weeks")


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    return str(value).lower() in ("1", "true", "yes", "y", "on")


def _str(value: Any, default: str = "") -> str:
    return str(value or default).strip()


def normalize_material_line(row: dict[str, Any], estimate_id: str = "") -> dict[str, Any]:
    qty = _num(row.get("qty") or row.get("quantity"))
    unit_cost = _num(row.get("unit_cost"))
    markup_percent = _num(row.get("markup_percent"))
    calc = calc_material_line(qty, unit_cost, markup_percent)
    return {
        "id": _str(row.get("id")),
        "estimate_id": _str(row.get("estimate_id") or estimate_id),
        "inventory_item_id": _str(row.get("inventory_item_id")) or None,
        "sku": _str(row.get("sku") or row.get("item_number")),
        "item_number": _str(row.get("item_number") or row.get("sku")),
        "description": _str(row.get("description")),
        "category": _str(row.get("category")),
        "vendor_id": _str(row.get("vendor_id")) or None,
        "vendor": _str(row.get("vendor")),
        "quantity": qty,
        "qty": qty,
        "unit": _str(row.get("unit") or "EA"),
        "unit_cost": unit_cost,
        "cost_total": _num(row.get("cost_total") or row.get("total_cost"), calc["cost_total"]),
        "markup_percent": markup_percent,
        "markup_amount": _num(row.get("markup_amount"), calc["markup_amount"]),
        "price_total": _num(row.get("price_total"), calc["price_total"]),
        "taxable": _bool(row.get("taxable"), True),
        "notes": _str(row.get("notes")),
        "sort_order": int(row.get("sort_order") or 0),
    }


def normalize_labor_line(row: dict[str, Any], estimate_id: str = "") -> dict[str, Any]:
    st_h = _num(row.get("st_hours") or row.get("hours"))
    ot_h = _num(row.get("ot_hours"))
    dt_h = _num(row.get("dt_hours"))
    st_r = _num(row.get("st_rate") or row.get("rate"))
    ot_r = _num(row.get("ot_rate"))
    dt_r = _num(row.get("dt_rate"))
    markup_percent = _num(row.get("markup_percent"))
    calc = calc_labor_line(st_h, ot_h, dt_h, st_r, ot_r, dt_r, markup_percent)
    role = _str(row.get("role_name") or row.get("labor_type") or row.get("description"))
    return {
        "id": _str(row.get("id")),
        "estimate_id": _str(row.get("estimate_id") or estimate_id),
        "labor_type": _str(row.get("labor_type") or role or "Other"),
        "role_name": role,
        "employee_id": _str(row.get("employee_id")) or None,
        "description": _str(row.get("description") or role),
        "st_hours": st_h,
        "ot_hours": ot_h,
        "dt_hours": dt_h,
        "st_rate": st_r,
        "ot_rate": ot_r,
        "dt_rate": dt_r,
        "cost_total": _num(row.get("cost_total") or row.get("total"), calc["cost_total"]),
        "markup_percent": markup_percent,
        "markup_amount": _num(row.get("markup_amount"), calc["markup_amount"]),
        "price_total": _num(row.get("price_total"), calc["price_total"]),
        "notes": _str(row.get("notes")),
        "sort_order": int(row.get("sort_order") or 0),
    }


def normalize_equipment_line(row: dict[str, Any], estimate_id: str = "") -> dict[str, Any]:
    qty = _num(row.get("quantity"), 1.0)
    duration = _num(row.get("duration"))
    cost_rate = _num(row.get("cost_rate"))
    markup_percent = _num(row.get("markup_percent"))
    calc = calc_equipment_line(qty, duration, cost_rate, markup_percent)
    return {
        "id": _str(row.get("id")),
        "estimate_id": _str(row.get("estimate_id") or estimate_id),
        "asset_id": _str(row.get("asset_id")) or None,
        "equipment_name": _str(row.get("equipment_name")),
        "equipment_type": _str(row.get("equipment_type")),
        "quantity": qty,
        "duration": duration,
        "duration_unit": _str(row.get("duration_unit") or "Hours"),
        "cost_rate": cost_rate,
        "cost_total": _num(row.get("cost_total"), calc["cost_total"]),
        "markup_percent": markup_percent,
        "markup_amount": _num(row.get("markup_amount"), calc["markup_amount"]),
        "price_total": _num(row.get("price_total"), calc["price_total"]),
        "notes": _str(row.get("notes")),
        "sort_order": int(row.get("sort_order") or 0),
    }


def normalize_subcontractor_line(row: dict[str, Any], estimate_id: str = "") -> dict[str, Any]:
    cost = _num(row.get("cost_total"))
    markup_percent = _num(row.get("markup_percent"))
    calc = calc_simple_line(cost, markup_percent)
    return {
        "id": _str(row.get("id")),
        "estimate_id": _str(row.get("estimate_id") or estimate_id),
        "vendor_id": _str(row.get("vendor_id")) or None,
        "subcontractor_name": _str(row.get("subcontractor_name")),
        "description": _str(row.get("description")),
        "cost_total": _num(row.get("cost_total"), calc["cost_total"]),
        "markup_percent": markup_percent,
        "markup_amount": _num(row.get("markup_amount"), calc["markup_amount"]),
        "price_total": _num(row.get("price_total"), calc["price_total"]),
        "notes": _str(row.get("notes")),
        "sort_order": int(row.get("sort_order") or 0),
    }


def normalize_travel_line(row: dict[str, Any], estimate_id: str = "") -> dict[str, Any]:
    data = {
        "travel_type": _str(row.get("travel_type") or "Mileage"),
        "miles": row.get("miles"),
        "mileage_rate": row.get("mileage_rate"),
        "trips": row.get("trips"),
        "people": row.get("people"),
        "travel_hours": row.get("travel_hours"),
        "hourly_rate": row.get("hourly_rate"),
        "nights": row.get("nights"),
        "lodging_rate": row.get("lodging_rate"),
        "per_diem_days": row.get("per_diem_days"),
        "per_diem_rate": row.get("per_diem_rate"),
        "airfare_cost": row.get("airfare_cost"),
        "rental_vehicle_cost": row.get("rental_vehicle_cost"),
        "fuel_cost": row.get("fuel_cost"),
        "parking_tolls_cost": row.get("parking_tolls_cost"),
        "other_cost": row.get("other_cost"),
        "markup_percent": row.get("markup_percent"),
    }
    calc = calc_travel_line(data)
    return {
        "id": _str(row.get("id")),
        "estimate_id": _str(row.get("estimate_id") or estimate_id),
        "travel_type": data["travel_type"],
        "description": _str(row.get("description")),
        "origin": _str(row.get("origin")),
        "destination": _str(row.get("destination")),
        "miles": _num(row.get("miles")),
        "mileage_rate": _num(row.get("mileage_rate")),
        "trips": _num(row.get("trips"), 1.0),
        "people": _num(row.get("people"), 1.0),
        "travel_hours": _num(row.get("travel_hours")),
        "hourly_rate": _num(row.get("hourly_rate")),
        "nights": _num(row.get("nights")),
        "lodging_rate": _num(row.get("lodging_rate")),
        "per_diem_days": _num(row.get("per_diem_days")),
        "per_diem_rate": _num(row.get("per_diem_rate")),
        "airfare_cost": _num(row.get("airfare_cost")),
        "rental_vehicle_cost": _num(row.get("rental_vehicle_cost")),
        "fuel_cost": _num(row.get("fuel_cost")),
        "parking_tolls_cost": _num(row.get("parking_tolls_cost")),
        "other_cost": _num(row.get("other_cost")),
        "cost_total": _num(row.get("cost_total"), calc["cost_total"]),
        "markup_percent": _num(row.get("markup_percent")),
        "markup_amount": _num(row.get("markup_amount"), calc["markup_amount"]),
        "price_total": _num(row.get("price_total"), calc["price_total"]),
        "taxable": _bool(row.get("taxable"), False),
        "notes": _str(row.get("notes")),
        "sort_order": int(row.get("sort_order") or 0),
    }


def normalize_other_cost_line(row: dict[str, Any], estimate_id: str = "") -> dict[str, Any]:
    cost = _num(row.get("cost_total"))
    markup_percent = _num(row.get("markup_percent"))
    calc = calc_simple_line(cost, markup_percent)
    return {
        "id": _str(row.get("id")),
        "estimate_id": _str(row.get("estimate_id") or estimate_id),
        "description": _str(row.get("description")),
        "category": _str(row.get("category")),
        "cost_total": _num(row.get("cost_total"), calc["cost_total"]),
        "markup_percent": markup_percent,
        "markup_amount": _num(row.get("markup_amount"), calc["markup_amount"]),
        "price_total": _num(row.get("price_total"), calc["price_total"]),
        "taxable": _bool(row.get("taxable"), False),
        "notes": _str(row.get("notes")),
        "sort_order": int(row.get("sort_order") or 0),
    }


def _filter_estimate_rows(rows: list[dict[str, Any]], estimate_id: str) -> list[dict[str, Any]]:
    eid = _str(estimate_id)
    return [r for r in rows if _str(r.get("estimate_id")) == eid]


def get_estimate_materials(estimate_id: str, *, demo: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], bool]:
    eid = _str(estimate_id)
    rows, err = fetch_rows("estimate_line_items", limit=500, order_by="sort_order")
    if err:
        demo_rows = [normalize_material_line(r, eid) for r in (demo or []) if _str(r.get("estimate_id")) == eid]
        return demo_rows, True
    return [normalize_material_line(r, eid) for r in _filter_estimate_rows(rows, eid)], False


def get_estimate_labor(estimate_id: str, *, demo: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], bool]:
    eid = _str(estimate_id)
    rows, err = fetch_rows("estimate_labor_lines", limit=500, order_by="sort_order")
    if err:
        return [], True
    return [normalize_labor_line(r, eid) for r in _filter_estimate_rows(rows, eid)], False


def get_estimate_equipment(estimate_id: str) -> tuple[list[dict[str, Any]], bool]:
    eid = _str(estimate_id)
    rows, err = fetch_rows("estimate_equipment", limit=500, order_by="sort_order")
    if err:
        return [], True
    return [normalize_equipment_line(r, eid) for r in _filter_estimate_rows(rows, eid)], False


def get_estimate_subcontractors(estimate_id: str) -> tuple[list[dict[str, Any]], bool]:
    eid = _str(estimate_id)
    rows, err = fetch_rows("estimate_subcontractors", limit=500, order_by="sort_order")
    if err:
        return [], True
    return [normalize_subcontractor_line(r, eid) for r in _filter_estimate_rows(rows, eid)], False


def get_estimate_other_costs(estimate_id: str) -> tuple[list[dict[str, Any]], bool]:
    eid = _str(estimate_id)
    rows, err = fetch_rows("estimate_other_costs", limit=500, order_by="sort_order")
    if err:
        return [], True
    return [normalize_other_cost_line(r, eid) for r in _filter_estimate_rows(rows, eid)], False


def get_estimate_travel(estimate_id: str) -> tuple[list[dict[str, Any]], bool]:
    eid = _str(estimate_id)
    rows, err = fetch_rows("estimate_travel", limit=500, order_by="sort_order")
    if err:
        return [], True
    return [normalize_travel_line(r, eid) for r in _filter_estimate_rows(rows, eid)], False


def clear_estimate_cache() -> None:
    clear_all_data_caches()


def get_estimate_bundle(estimate_id: str, *, demo_materials: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    eid = _str(estimate_id)
    materials, _ = get_estimate_materials(eid, demo=demo_materials)
    labor, _ = get_estimate_labor(eid)
    equipment, _ = get_estimate_equipment(eid)
    travel, _ = get_estimate_travel(eid)
    subcontractors, _ = get_estimate_subcontractors(eid)
    other_costs, _ = get_estimate_other_costs(eid)
    return {
        "materials": materials,
        "labor": labor,
        "equipment": equipment,
        "travel": travel,
        "subcontractors": subcontractors,
        "other_costs": other_costs,
    }


def calculate_estimate_totals(
    estimate_id: str,
    *,
    tax_rate: float | None = None,
    demo_materials: list[dict[str, Any]] | None = None,
) -> dict[str, float]:
    bundle = get_estimate_bundle(estimate_id, demo_materials=demo_materials)
    rate = tax_rate
    if rate is None:
        rows, _ = fetch_rows("estimates", limit=1)
        for row in rows:
            if _str(row.get("id")) == _str(estimate_id):
                rate = _num(row.get("tax_rate"))
                break
        if rate is None:
            rate = 0.0
    return calc_totals(
        bundle["materials"],
        bundle["labor"],
        bundle["equipment"],
        bundle["subcontractors"],
        bundle["other_costs"],
        travel=bundle["travel"],
        tax_rate=rate,
    )


def recalculate_and_save_estimate_totals(estimate_id: str) -> ServiceResult:
    eid = _str(estimate_id)
    if not eid:
        return ServiceResult(ok=False, error="Estimate id is required.")
    totals = calculate_estimate_totals(eid)
    payload = {
        **totals,
        "subtotal": totals["total_cost"],
        "material_total": totals["material_cost"],
        "labor_total": totals["labor_cost"],
        "equipment_total": totals["equipment_cost"],
        "travel_cost": totals["travel_cost"],
        "travel_markup": totals["travel_markup"],
        "travel_price": totals["travel_price"],
        "markup": totals["total_markup"],
        "tax": totals["tax_amount"],
        "total": totals["customer_price"],
        "updated_at": date.today().isoformat(),
    }
    result = update_row("estimates", payload, {"id": eid})
    if result.ok:
        clear_all_data_caches()
    return result


def _next_sort_order(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    return max(int(r.get("sort_order") or 0) for r in rows) + 1


def add_estimate_material(estimate_id: str, data: dict[str, Any]) -> ServiceResult:
    eid = _str(estimate_id)
    existing, _ = get_estimate_materials(eid)
    qty = _num(data.get("quantity") or data.get("qty"))
    unit_cost = _num(data.get("unit_cost"))
    markup_percent = _num(data.get("markup_percent"))
    calc = calc_material_line(qty, unit_cost, markup_percent)
    payload = {
        "estimate_id": eid,
        "inventory_item_id": data.get("inventory_item_id") or None,
        "item_number": _str(data.get("item_number") or data.get("sku")),
        "sku": _str(data.get("sku") or data.get("item_number")),
        "description": _str(data.get("description")),
        "category": _str(data.get("category")),
        "vendor_id": data.get("vendor_id") or None,
        "vendor": _str(data.get("vendor")),
        "qty": qty,
        "unit": _str(data.get("unit") or "EA"),
        "unit_cost": unit_cost,
        "total_cost": calc["cost_total"],
        "cost_total": calc["cost_total"],
        "markup_percent": markup_percent,
        "markup_amount": calc["markup_amount"],
        "price_total": calc["price_total"],
        "taxable": _bool(data.get("taxable"), True),
        "notes": _str(data.get("notes")),
        "sort_order": _next_sort_order(existing),
    }
    result = insert_row("estimate_line_items", payload)
    if result.ok:
        recalculate_and_save_estimate_totals(eid)
    return result


def update_estimate_material(line_id: str, data: dict[str, Any]) -> ServiceResult:
    rid = _str(line_id)
    qty = _num(data.get("quantity") or data.get("qty"))
    unit_cost = _num(data.get("unit_cost"))
    markup_percent = _num(data.get("markup_percent"))
    calc = calc_material_line(qty, unit_cost, markup_percent)
    payload = {
        "inventory_item_id": data.get("inventory_item_id") or None,
        "item_number": _str(data.get("item_number") or data.get("sku")),
        "sku": _str(data.get("sku") or data.get("item_number")),
        "description": _str(data.get("description")),
        "category": _str(data.get("category")),
        "vendor_id": data.get("vendor_id") or None,
        "vendor": _str(data.get("vendor")),
        "qty": qty,
        "unit": _str(data.get("unit") or "EA"),
        "unit_cost": unit_cost,
        "total_cost": calc["cost_total"],
        "cost_total": calc["cost_total"],
        "markup_percent": markup_percent,
        "markup_amount": calc["markup_amount"],
        "price_total": calc["price_total"],
        "taxable": _bool(data.get("taxable"), True),
        "notes": _str(data.get("notes")),
    }
    result = update_row("estimate_line_items", payload, {"id": rid})
    eid = _str(data.get("estimate_id"))
    if result.ok and eid:
        recalculate_and_save_estimate_totals(eid)
    return result


def delete_estimate_material(line_id: str, *, estimate_id: str = "") -> ServiceResult:
    result = delete_row("estimate_line_items", {"id": _str(line_id)})
    eid = _str(estimate_id)
    if result.ok and eid:
        recalculate_and_save_estimate_totals(eid)
    return result


def add_estimate_labor(estimate_id: str, data: dict[str, Any]) -> ServiceResult:
    eid = _str(estimate_id)
    existing, _ = get_estimate_labor(eid)
    calc = calc_labor_line(
        data.get("st_hours"),
        data.get("ot_hours"),
        data.get("dt_hours"),
        data.get("st_rate"),
        data.get("ot_rate"),
        data.get("dt_rate"),
        data.get("markup_percent"),
    )
    role = _str(data.get("role_name") or data.get("labor_type"))
    payload = {
        "estimate_id": eid,
        "labor_type": _str(data.get("labor_type") or role or "Other"),
        "role_name": role,
        "employee_id": data.get("employee_id") or None,
        "description": _str(data.get("description") or role),
        "st_hours": _num(data.get("st_hours")),
        "ot_hours": _num(data.get("ot_hours")),
        "dt_hours": _num(data.get("dt_hours")),
        "st_rate": _num(data.get("st_rate")),
        "ot_rate": _num(data.get("ot_rate")),
        "dt_rate": _num(data.get("dt_rate")),
        "hours": _num(data.get("st_hours")),
        "rate": _num(data.get("st_rate")),
        "total": calc["cost_total"],
        "cost_total": calc["cost_total"],
        "markup_percent": _num(data.get("markup_percent")),
        "markup_amount": calc["markup_amount"],
        "price_total": calc["price_total"],
        "notes": _str(data.get("notes")),
        "sort_order": _next_sort_order(existing),
    }
    result = insert_row("estimate_labor_lines", payload)
    if result.ok:
        recalculate_and_save_estimate_totals(eid)
    return result


def update_estimate_labor(line_id: str, data: dict[str, Any]) -> ServiceResult:
    calc = calc_labor_line(
        data.get("st_hours"),
        data.get("ot_hours"),
        data.get("dt_hours"),
        data.get("st_rate"),
        data.get("ot_rate"),
        data.get("dt_rate"),
        data.get("markup_percent"),
    )
    role = _str(data.get("role_name") or data.get("labor_type"))
    payload = {
        "labor_type": _str(data.get("labor_type") or role or "Other"),
        "role_name": role,
        "employee_id": data.get("employee_id") or None,
        "description": _str(data.get("description") or role),
        "st_hours": _num(data.get("st_hours")),
        "ot_hours": _num(data.get("ot_hours")),
        "dt_hours": _num(data.get("dt_hours")),
        "st_rate": _num(data.get("st_rate")),
        "ot_rate": _num(data.get("ot_rate")),
        "dt_rate": _num(data.get("dt_rate")),
        "hours": _num(data.get("st_hours")),
        "rate": _num(data.get("st_rate")),
        "total": calc["cost_total"],
        "cost_total": calc["cost_total"],
        "markup_percent": _num(data.get("markup_percent")),
        "markup_amount": calc["markup_amount"],
        "price_total": calc["price_total"],
        "notes": _str(data.get("notes")),
    }
    result = update_row("estimate_labor_lines", payload, {"id": _str(line_id)})
    eid = _str(data.get("estimate_id"))
    if result.ok and eid:
        recalculate_and_save_estimate_totals(eid)
    return result


def delete_estimate_labor(line_id: str, *, estimate_id: str = "") -> ServiceResult:
    result = delete_row("estimate_labor_lines", {"id": _str(line_id)})
    if result.ok and estimate_id:
        recalculate_and_save_estimate_totals(_str(estimate_id))
    return result


def _add_line(table: str, estimate_id: str, payload: dict[str, Any], *, recalc: bool = True) -> ServiceResult:
    payload = {**payload, "estimate_id": _str(estimate_id)}
    result = insert_row(table, payload)
    if result.ok and recalc:
        recalculate_and_save_estimate_totals(_str(estimate_id))
    return result


def _update_line(table: str, line_id: str, payload: dict[str, Any], *, estimate_id: str = "") -> ServiceResult:
    result = update_row(table, payload, {"id": _str(line_id)})
    if result.ok and estimate_id:
        recalculate_and_save_estimate_totals(_str(estimate_id))
    return result


def _delete_line(table: str, line_id: str, *, estimate_id: str = "") -> ServiceResult:
    result = delete_row(table, {"id": _str(line_id)})
    if result.ok and estimate_id:
        recalculate_and_save_estimate_totals(_str(estimate_id))
    return result


def add_estimate_equipment(estimate_id: str, data: dict[str, Any]) -> ServiceResult:
    existing, _ = get_estimate_equipment(estimate_id)
    calc = calc_equipment_line(data.get("quantity"), data.get("duration"), data.get("cost_rate"), data.get("markup_percent"))
    payload = {
        "asset_id": data.get("asset_id") or None,
        "equipment_name": _str(data.get("equipment_name")),
        "equipment_type": _str(data.get("equipment_type")),
        "quantity": _num(data.get("quantity"), 1.0),
        "duration": _num(data.get("duration")),
        "duration_unit": _str(data.get("duration_unit") or "Hours"),
        "cost_rate": _num(data.get("cost_rate")),
        "cost_total": calc["cost_total"],
        "markup_percent": _num(data.get("markup_percent")),
        "markup_amount": calc["markup_amount"],
        "price_total": calc["price_total"],
        "notes": _str(data.get("notes")),
        "sort_order": _next_sort_order(existing),
    }
    return _add_line("estimate_equipment", estimate_id, payload)


def update_estimate_equipment(line_id: str, data: dict[str, Any]) -> ServiceResult:
    calc = calc_equipment_line(data.get("quantity"), data.get("duration"), data.get("cost_rate"), data.get("markup_percent"))
    payload = {
        "asset_id": data.get("asset_id") or None,
        "equipment_name": _str(data.get("equipment_name")),
        "equipment_type": _str(data.get("equipment_type")),
        "quantity": _num(data.get("quantity"), 1.0),
        "duration": _num(data.get("duration")),
        "duration_unit": _str(data.get("duration_unit") or "Hours"),
        "cost_rate": _num(data.get("cost_rate")),
        "cost_total": calc["cost_total"],
        "markup_percent": _num(data.get("markup_percent")),
        "markup_amount": calc["markup_amount"],
        "price_total": calc["price_total"],
        "notes": _str(data.get("notes")),
    }
    return _update_line("estimate_equipment", line_id, payload, estimate_id=_str(data.get("estimate_id")))


def delete_estimate_equipment(line_id: str, *, estimate_id: str = "") -> ServiceResult:
    return _delete_line("estimate_equipment", line_id, estimate_id=estimate_id)


def add_estimate_subcontractor(estimate_id: str, data: dict[str, Any]) -> ServiceResult:
    existing, _ = get_estimate_subcontractors(estimate_id)
    calc = calc_simple_line(data.get("cost_total"), data.get("markup_percent"))
    payload = {
        "vendor_id": data.get("vendor_id") or None,
        "subcontractor_name": _str(data.get("subcontractor_name")),
        "description": _str(data.get("description")),
        "cost_total": calc["cost_total"],
        "markup_percent": _num(data.get("markup_percent")),
        "markup_amount": calc["markup_amount"],
        "price_total": calc["price_total"],
        "notes": _str(data.get("notes")),
        "sort_order": _next_sort_order(existing),
    }
    return _add_line("estimate_subcontractors", estimate_id, payload)


def update_estimate_subcontractor(line_id: str, data: dict[str, Any]) -> ServiceResult:
    calc = calc_simple_line(data.get("cost_total"), data.get("markup_percent"))
    payload = {
        "vendor_id": data.get("vendor_id") or None,
        "subcontractor_name": _str(data.get("subcontractor_name")),
        "description": _str(data.get("description")),
        "cost_total": calc["cost_total"],
        "markup_percent": _num(data.get("markup_percent")),
        "markup_amount": calc["markup_amount"],
        "price_total": calc["price_total"],
        "notes": _str(data.get("notes")),
    }
    return _update_line("estimate_subcontractors", line_id, payload, estimate_id=_str(data.get("estimate_id")))


def delete_estimate_subcontractor(line_id: str, *, estimate_id: str = "") -> ServiceResult:
    return _delete_line("estimate_subcontractors", line_id, estimate_id=estimate_id)


def add_estimate_other_cost(estimate_id: str, data: dict[str, Any]) -> ServiceResult:
    existing, _ = get_estimate_other_costs(estimate_id)
    calc = calc_simple_line(data.get("cost_total"), data.get("markup_percent"))
    payload = {
        "description": _str(data.get("description")),
        "category": _str(data.get("category")),
        "cost_total": calc["cost_total"],
        "markup_percent": _num(data.get("markup_percent")),
        "markup_amount": calc["markup_amount"],
        "price_total": calc["price_total"],
        "taxable": _bool(data.get("taxable"), False),
        "notes": _str(data.get("notes")),
        "sort_order": _next_sort_order(existing),
    }
    return _add_line("estimate_other_costs", estimate_id, payload)


def update_estimate_other_cost(line_id: str, data: dict[str, Any]) -> ServiceResult:
    calc = calc_simple_line(data.get("cost_total"), data.get("markup_percent"))
    payload = {
        "description": _str(data.get("description")),
        "category": _str(data.get("category")),
        "cost_total": calc["cost_total"],
        "markup_percent": _num(data.get("markup_percent")),
        "markup_amount": calc["markup_amount"],
        "price_total": calc["price_total"],
        "taxable": _bool(data.get("taxable"), False),
        "notes": _str(data.get("notes")),
    }
    return _update_line("estimate_other_costs", line_id, payload, estimate_id=_str(data.get("estimate_id")))


def delete_estimate_other_cost(line_id: str, *, estimate_id: str = "") -> ServiceResult:
    return _delete_line("estimate_other_costs", line_id, estimate_id=estimate_id)


def _travel_payload(data: dict[str, Any]) -> dict[str, Any]:
    calc = calc_travel_line(data)
    return {
        "travel_type": _str(data.get("travel_type") or "Mileage"),
        "description": _str(data.get("description")),
        "origin": _str(data.get("origin")),
        "destination": _str(data.get("destination")),
        "miles": _num(data.get("miles")),
        "mileage_rate": _num(data.get("mileage_rate")),
        "trips": _num(data.get("trips"), 1.0),
        "people": _num(data.get("people"), 1.0),
        "travel_hours": _num(data.get("travel_hours")),
        "hourly_rate": _num(data.get("hourly_rate")),
        "nights": _num(data.get("nights")),
        "lodging_rate": _num(data.get("lodging_rate")),
        "per_diem_days": _num(data.get("per_diem_days")),
        "per_diem_rate": _num(data.get("per_diem_rate")),
        "airfare_cost": _num(data.get("airfare_cost")),
        "rental_vehicle_cost": _num(data.get("rental_vehicle_cost")),
        "fuel_cost": _num(data.get("fuel_cost")),
        "parking_tolls_cost": _num(data.get("parking_tolls_cost")),
        "other_cost": _num(data.get("other_cost")),
        "cost_total": calc["cost_total"],
        "markup_percent": _num(data.get("markup_percent")),
        "markup_amount": calc["markup_amount"],
        "price_total": calc["price_total"],
        "taxable": _bool(data.get("taxable"), False),
        "notes": _str(data.get("notes")),
    }


def add_estimate_travel(estimate_id: str, data: dict[str, Any]) -> ServiceResult:
    existing, _ = get_estimate_travel(estimate_id)
    payload = {**_travel_payload(data), "sort_order": _next_sort_order(existing)}
    return _add_line("estimate_travel", estimate_id, payload)


def update_estimate_travel(line_id: str, data: dict[str, Any]) -> ServiceResult:
    payload = _travel_payload(data)
    return _update_line("estimate_travel", line_id, payload, estimate_id=_str(data.get("estimate_id")))


def delete_estimate_travel(line_id: str, *, estimate_id: str = "") -> ServiceResult:
    return _delete_line("estimate_travel", line_id, estimate_id=estimate_id)


def get_default_terms() -> str:
    rows, err = fetch_rows("estimate_terms", limit=20)
    if err or not rows:
        return (
            "Payment terms: Net 30 from invoice date. Proposal valid through expiration date shown above. "
            "Work performed per IPS safety standards and applicable codes."
        )
    defaults = [r for r in rows if r.get("is_default")]
    row = defaults[0] if defaults else rows[0]
    return _str(row.get("terms_text"))
