"""Centralized estimate costing math (no UI, no DB)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

_D0 = Decimal("0")
_CENT = Decimal("0.01")


def _dec(value: Any) -> Decimal:
    if value is None or value == "":
        return _D0
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return _D0


def _q2(value: Any) -> Decimal:
    return _dec(value).quantize(_CENT, rounding=ROUND_HALF_UP)


def to_float(value: Any) -> float:
    return float(_q2(value))


def calc_markup(cost: Any, markup_percent: Any) -> Decimal:
    cost_d = _q2(cost)
    pct = _dec(markup_percent)
    if pct <= _D0:
        return _D0
    return _q2(cost_d * pct / Decimal("100"))


def calc_line_price(cost: Any, markup_percent: Any) -> Decimal:
    cost_d = _q2(cost)
    return _q2(cost_d + calc_markup(cost_d, markup_percent))


def calc_material_line(
    quantity: Any,
    unit_cost: Any,
    markup_percent: Any,
) -> dict[str, float]:
    qty = _dec(quantity)
    unit = _dec(unit_cost)
    cost_total = _q2(qty * unit)
    markup_amount = calc_markup(cost_total, markup_percent)
    price_total = _q2(cost_total + markup_amount)
    return {
        "cost_total": to_float(cost_total),
        "markup_amount": to_float(markup_amount),
        "price_total": to_float(price_total),
    }


def calc_labor_line(
    st_hours: Any,
    ot_hours: Any,
    dt_hours: Any,
    st_rate: Any,
    ot_rate: Any,
    dt_rate: Any,
    markup_percent: Any,
) -> dict[str, float]:
    _ = (dt_hours, dt_rate)  # DT not used in estimate builder labor costing
    cost_total = _q2(
        _dec(st_hours) * _dec(st_rate) + _dec(ot_hours) * _dec(ot_rate)
    )
    markup_amount = calc_markup(cost_total, markup_percent)
    price_total = _q2(cost_total + markup_amount)
    return {
        "cost_total": to_float(cost_total),
        "markup_amount": to_float(markup_amount),
        "price_total": to_float(price_total),
    }


def calc_equipment_line(
    quantity: Any,
    duration: Any,
    cost_rate: Any,
    markup_percent: Any,
) -> dict[str, float]:
    cost_total = _q2(_dec(quantity) * _dec(duration) * _dec(cost_rate))
    markup_amount = calc_markup(cost_total, markup_percent)
    price_total = _q2(cost_total + markup_amount)
    return {
        "cost_total": to_float(cost_total),
        "markup_amount": to_float(markup_amount),
        "price_total": to_float(price_total),
    }


def calc_simple_line(cost_total: Any, markup_percent: Any) -> dict[str, float]:
    cost = _q2(cost_total)
    markup_amount = calc_markup(cost, markup_percent)
    price_total = _q2(cost + markup_amount)
    return {
        "cost_total": to_float(cost),
        "markup_amount": to_float(markup_amount),
        "price_total": to_float(price_total),
    }


TRAVEL_TYPES = (
    "Mileage",
    "Drive Time",
    "Lodging",
    "Per Diem",
    "Airfare",
    "Rental Vehicle",
    "Fuel",
    "Parking / Tolls",
    "Other Travel",
)


def calc_travel_line(data: dict[str, Any]) -> dict[str, float]:
    travel_type = str(data.get("travel_type") or "Mileage").strip()
    markup_percent = data.get("markup_percent")

    miles = _dec(data.get("miles"))
    mileage_rate = _dec(data.get("mileage_rate"))
    trips = _dec(data.get("trips")) or Decimal("1")
    people = _dec(data.get("people")) or Decimal("1")
    travel_hours = _dec(data.get("travel_hours"))
    hourly_rate = _dec(data.get("hourly_rate"))
    nights = _dec(data.get("nights"))
    lodging_rate = _dec(data.get("lodging_rate"))
    per_diem_days = _dec(data.get("per_diem_days"))
    per_diem_rate = _dec(data.get("per_diem_rate"))
    airfare_cost = _dec(data.get("airfare_cost"))
    rental_vehicle_cost = _dec(data.get("rental_vehicle_cost"))
    fuel_cost = _dec(data.get("fuel_cost"))
    parking_tolls_cost = _dec(data.get("parking_tolls_cost"))
    other_cost_val = _dec(data.get("other_cost"))

    if travel_type == "Mileage":
        cost_total = miles * mileage_rate * trips
    elif travel_type == "Drive Time":
        cost_total = travel_hours * hourly_rate * people
    elif travel_type == "Lodging":
        cost_total = nights * lodging_rate * people
    elif travel_type == "Per Diem":
        cost_total = per_diem_days * per_diem_rate * people
    elif travel_type == "Airfare":
        cost_total = airfare_cost * people
    elif travel_type == "Rental Vehicle":
        cost_total = rental_vehicle_cost
    elif travel_type == "Fuel":
        cost_total = fuel_cost
    elif travel_type == "Parking / Tolls":
        cost_total = parking_tolls_cost
    else:
        cost_total = other_cost_val

    cost_total = _q2(cost_total)
    markup_amount = calc_markup(cost_total, markup_percent)
    price_total = _q2(cost_total + markup_amount)
    return {
        "cost_total": to_float(cost_total),
        "markup_amount": to_float(markup_amount),
        "price_total": to_float(price_total),
    }


def calc_travel_total(travel_lines: list[dict[str, Any]]) -> dict[str, float]:
    cost = sum((_line_cost(r) for r in travel_lines), _D0)
    markup = sum((_line_markup(r) for r in travel_lines), _D0)
    price = sum((_line_price(r) for r in travel_lines), _D0)
    return {
        "travel_cost": to_float(cost),
        "travel_markup": to_float(markup),
        "travel_price": to_float(price),
    }


def _line_cost(row: dict[str, Any]) -> Decimal:
    return _q2(row.get("cost_total") or row.get("total_cost") or 0)


def _line_markup(row: dict[str, Any]) -> Decimal:
    return _q2(row.get("markup_amount") or 0)


def _line_price(row: dict[str, Any]) -> Decimal:
    price = row.get("price_total")
    if price not in (None, ""):
        return _q2(price)
    return calc_line_price(_line_cost(row), row.get("markup_percent"))


def calc_totals(
    materials: list[dict[str, Any]],
    labor: list[dict[str, Any]],
    equipment: list[dict[str, Any]],
    subcontractors: list[dict[str, Any]],
    other_costs: list[dict[str, Any]],
    *,
    travel: list[dict[str, Any]] | None = None,
    tax_rate: Any = 0,
) -> dict[str, float]:
    travel_lines = travel or []
    material_cost = sum((_line_cost(r) for r in materials), _D0)
    labor_cost = sum((_line_cost(r) for r in labor), _D0)
    equipment_cost = sum((_line_cost(r) for r in equipment), _D0)
    travel_cost = sum((_line_cost(r) for r in travel_lines), _D0)
    subcontractor_cost = sum((_line_cost(r) for r in subcontractors), _D0)
    other_cost = sum((_line_cost(r) for r in other_costs), _D0)

    material_markup = sum((_line_markup(r) for r in materials), _D0)
    labor_markup = sum((_line_markup(r) for r in labor), _D0)
    equipment_markup = sum((_line_markup(r) for r in equipment), _D0)
    travel_markup = sum((_line_markup(r) for r in travel_lines), _D0)
    subcontractor_markup = sum((_line_markup(r) for r in subcontractors), _D0)
    other_markup = sum((_line_markup(r) for r in other_costs), _D0)

    material_price = sum((_line_price(r) for r in materials), _D0)
    labor_price = sum((_line_price(r) for r in labor), _D0)
    equipment_price = sum((_line_price(r) for r in equipment), _D0)
    travel_price = sum((_line_price(r) for r in travel_lines), _D0)
    subcontractor_price = sum((_line_price(r) for r in subcontractors), _D0)
    other_price = sum((_line_price(r) for r in other_costs), _D0)

    total_cost = _q2(
        material_cost + labor_cost + equipment_cost + travel_cost + subcontractor_cost + other_cost
    )
    total_markup = _q2(
        material_markup + labor_markup + equipment_markup + travel_markup + subcontractor_markup + other_markup
    )
    subtotal_before_tax = _q2(
        material_price + labor_price + equipment_price + travel_price + subcontractor_price + other_price
    )

    taxable_subtotal = _D0
    for row in materials:
        if row.get("taxable", True):
            taxable_subtotal += _line_price(row)
    for row in travel_lines:
        if row.get("taxable"):
            taxable_subtotal += _line_price(row)
    for row in other_costs:
        if row.get("taxable"):
            taxable_subtotal += _line_price(row)
    taxable_subtotal = _q2(taxable_subtotal)

    rate = _dec(tax_rate)
    tax_amount = _q2(taxable_subtotal * rate / Decimal("100")) if rate > _D0 else _D0
    customer_price = _q2(subtotal_before_tax + tax_amount)
    gross_profit = _q2(customer_price - total_cost)
    gross_margin_percent = _D0
    if customer_price > _D0:
        gross_margin_percent = _q2(gross_profit / customer_price * Decimal("100"))

    return {
        "material_cost": to_float(material_cost),
        "labor_cost": to_float(labor_cost),
        "equipment_cost": to_float(equipment_cost),
        "travel_cost": to_float(travel_cost),
        "subcontractor_cost": to_float(subcontractor_cost),
        "other_cost": to_float(other_cost),
        "total_cost": to_float(total_cost),
        "material_markup": to_float(material_markup),
        "labor_markup": to_float(labor_markup),
        "equipment_markup": to_float(equipment_markup),
        "travel_markup": to_float(travel_markup),
        "subcontractor_markup": to_float(subcontractor_markup),
        "other_markup": to_float(other_markup),
        "travel_price": to_float(travel_price),
        "total_markup": to_float(total_markup),
        "subtotal_before_tax": to_float(subtotal_before_tax),
        "taxable_subtotal": to_float(taxable_subtotal),
        "tax_amount": to_float(tax_amount),
        "customer_price": to_float(customer_price),
        "gross_profit": to_float(gross_profit),
        "gross_margin_percent": to_float(gross_margin_percent),
    }


def margin_warning_class(margin_percent: Any) -> str:
    margin = to_float(margin_percent)
    if margin < 10:
        return "danger"
    if margin <= 20:
        return "warning"
    return "ok"
