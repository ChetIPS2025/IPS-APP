from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

def _is_missing_number(v) -> bool:
    return v is None or v == ""


def _num0(v) -> float:
    try:
        if _is_missing_number(v):
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


_D0 = Decimal("0")
_CENT = Decimal("0.01")


def _dec(v) -> Decimal:
    """
    Decimal-safe conversion for money math.
    - always uses Decimal(str(v)) to avoid binary float artifacts
    - treats None/"" as 0
    """
    if v is None or v == "":
        return _D0
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _q2(v) -> Decimal:
    """Quantize to cents with HALF_UP rounding."""
    return _dec(v).quantize(_CENT, rounding=ROUND_HALF_UP)


def money_db(v) -> str:
    """DB-safe numeric string with exactly 2 decimals (Postgres numeric accepts strings)."""
    return f"{_q2(v):.2f}"


def money_str(v) -> str:
    """Two decimal places, no currency symbol (for tables/captions that add their own prefix)."""
    return f"{_q2(v):.2f}"


def money(v) -> str:
    """Display formatter: always 2 decimals, comma grouped."""
    return f"${_q2(v):,.2f}"


def compute_totals(est: dict, materials_catalog: list[dict], labor_rates: list[dict], equipment_pricing: list[dict]) -> dict:
    # Local import avoids circular dependency with :mod:`app.estimate.defaults`.
    from app.estimate.defaults import ensure_numeric_defaults

    ensure_numeric_defaults(est)
    material_map = {m["item_key"]: m for m in materials_catalog if m.get("item_key")}
    labor_map = {r["classification"]: r for r in labor_rates}
    equipment_map = {e["equipment_item"]: e for e in equipment_pricing}

    controls = est.get("controls", {})
    material_markup = _dec(controls.get("material_markup_pct", 0) or 0)
    overhead_pct = _dec(controls.get("overhead_pct", 0) or 0)
    profit_pct = _dec(controls.get("profit_pct", 0) or 0)
    contingency_pct = _dec(controls.get("contingency_pct", 0) or 0)
    sales_tax_pct = _dec(controls.get("sales_tax_pct", 0) or 0)

    material_sell_basis = _D0
    for row in est.get("materials", []):
        item = material_map.get(row.get("item"))
        if not item:
            continue
        qty = _dec(row.get("qty", 0) or 0)
        purchase = _dec(item.get("purchase_price", 0) or 0)
        sell = _dec(item.get("sell_price", 0) or 0)
        base_sell = sell if sell > _D0 else purchase * (Decimal("1") + material_markup)
        material_sell_basis += qty * base_sell

    labor_total = _D0
    for row in est.get("labor", []):
        item = labor_map.get(row.get("classification"))
        if not item:
            continue
        headcount = _dec(row.get("headcount", 0) or 0)
        st_hrs = _dec(row.get("st_hours_per_day", 0) or 0)
        ot_hrs = _dec(row.get("ot_hours_per_day", 0) or 0)
        days = _dec(row.get("days", 0) or 0)
        st_rate = _dec(item.get("st_rate", 0) or 0)
        ot_rate = _dec(item.get("ot_rate", 0) or 0)
        labor_total += headcount * days * ((st_hrs * st_rate) + (ot_hrs * ot_rate))

    equipment_total = _D0
    for row in est.get("equipment", []):
        item = equipment_map.get(row.get("equipment_item"))
        if not item:
            continue
        qty = _dec(row.get("qty", 0) or 0)
        basis = row.get("basis", "Day")
        duration = _dec(row.get("duration", 0) or 0)
        rate = {
            "Day": _dec(item.get("daily_rate", 0) or 0),
            "Week": _dec(item.get("weekly_rate", 0) or 0),
            "Month": _dec(item.get("monthly_rate", 0) or 0),
        }.get(basis, _D0)
        equipment_total += qty * duration * rate

    travel = est.get("travel", {})
    miles_total = _dec(travel.get("round_trip_miles")) * _dec(travel.get("mileage_rate"))
    per_diem_total = _dec(travel.get("per_diem_per_person_per_day"))
    hotel_total = _dec(travel.get("hotel_nights")) * _dec(travel.get("hotel_rate_per_room_per_night"))
    travel_total = (
        miles_total
        + per_diem_total
        + hotel_total
        + _dec(travel.get("airfare"))
        + _dec(travel.get("rental_car"))
        + _dec(travel.get("fuel"))
    )
    lt = _dec(travel.get("line_total"))
    if lt > _D0 and travel_total <= _D0:
        travel_total = lt

    direct_sell = material_sell_basis + labor_total + equipment_total + travel_total
    overhead_total = direct_sell * overhead_pct
    contingency_total = direct_sell * contingency_pct
    subtotal_before_profit = direct_sell + overhead_total + contingency_total
    profit_total = subtotal_before_profit * profit_pct
    sales_tax_total = material_sell_basis * sales_tax_pct
    final_bid = subtotal_before_profit + profit_total + sales_tax_total
    final_bid_q = _q2(final_bid)
    # Proposal total matches final bid (cent-quantized); no rounding to whole dollars.
    proposal_total = final_bid_q

    return {
        "material_sell_basis": _q2(material_sell_basis),
        "labor_total": _q2(labor_total),
        "equipment_total": _q2(equipment_total),
        "travel_total": _q2(travel_total),
        "overhead_total": _q2(overhead_total),
        "profit_total": _q2(profit_total),
        "contingency_total": _q2(contingency_total),
        "sales_tax_total": _q2(sales_tax_total),
        "final_bid": final_bid_q,
        "proposal_total": _q2(proposal_total),
    }
