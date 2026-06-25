"""Pricing Guide seed data for solid round bar materials."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

SOLID_ROUND_BAR_CATEGORY = "Solid Round Bar"
# Default material unit when source data does not specify a unit.
SOLID_ROUND_BAR_UNIT = "EA"

_SUBCATEGORY_BY_GROUP: dict[str, str] = {
    "Stainless Steel": "Stainless Steel",
    "Aluminum": "Aluminum",
    "Aluminium": "Aluminum",
    "Carbon Steel": "Carbon Steel",
}

_ITEM_CODE_PREFIX = "SRBAR"

# (description, material_group, diameter, price, suffix, source_description)
_SOLID_ROUND_BAR_SOURCE: tuple[tuple[str, str, str, str, str, str], ...] = (
    ('1/2" SOLID ROUND BAR (ALUMINUM)', "Aluminum", '1/2"', "22.60", "AL-12", '1/2" SOLID ROUND BAR(ALUMINUM)'),
    ('1" SOLID ROUND BAR (ALUMINUM)', "Aluminum", '1"', "85.63", "AL-1", ""),
    ('1/4" SOLID ROUND BAR (ALUMINUM)', "Aluminum", '1/4"', "3.25", "AL-14", '1/4" SOLID ROUND BAR(ALUMINUM)'),
    ('3/4" SOLID ROUND BAR (ALUMINUM)', "Aluminum", '3/4"', "48.45", "AL-34", ""),
    ('3/8" SOLID ROUND BAR (ALUMINUM)', "Aluminum", '3/8"', "12.07", "AL-38", '3/8" SOLID ROUND BAR(ALUMINUM)'),
    ('1-7/16" SOLID ROUND BAR (C.S.)', "Carbon Steel", '1-7/16"', "130.24", "CS-1-716", ""),
    ('1/2" S.S. ROUND BAR (304)', "Stainless Steel", '1/2"', "35.00", "SS-12-304", ""),
    ('5/8" S.S. ROUND BAR (304)', "Stainless Steel", '5/8"', "53.20", "SS-58-304", ""),
    ('3/4" S.S. ROUND BAR (304)', "Stainless Steel", '3/4"', "81.20", "SS-34-304", ""),
)

SOLID_ROUND_BAR_SOURCE_ROW_COUNT = len(_SOLID_ROUND_BAR_SOURCE)


def _material_grade(description: str, material_group: str) -> str:
    if "(304)" in description or "304" in description:
        return "304 Stainless Steel"
    if "ALUMINUM" in description.upper():
        return "Aluminum"
    if "(C.S.)" in description or "C.S." in description:
        return "Carbon Steel"
    return _SUBCATEGORY_BY_GROUP.get(material_group, material_group)


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _item_code(suffix: str) -> str:
    return f"{_ITEM_CODE_PREFIX}-{suffix}"


def _base_notes() -> str:
    return (
        f"Solid round bar catalog item; unit {SOLID_ROUND_BAR_UNIT} "
        f"(default material unit; bar length not supplied in source data)."
    )


def solid_round_bar_catalog_items() -> list[dict[str, Any]]:
    """9 pricing rows: aluminum, carbon steel, and 304 stainless solid round bar."""
    out: list[dict[str, Any]] = []
    for description, material_group, diameter, price_raw, suffix, source_description in _SOLID_ROUND_BAR_SOURCE:
        price = _decimal_price(price_raw)
        subcategory = _SUBCATEGORY_BY_GROUP[material_group]
        notes = _base_notes()
        if source_description:
            notes = f"{notes} Source description: {source_description}."

        out.append(
            {
                "item_code": _item_code(suffix),
                "item_type": "Material",
                "item_class": "Non-Inventory",
                "description": description,
                "category": SOLID_ROUND_BAR_CATEGORY,
                "subcategory": subcategory,
                "unit": SOLID_ROUND_BAR_UNIT,
                "default_cost": _price_to_float(price),
                "default_markup_percent": 0.0,
                "default_sell_price": _price_to_float(price),
                "taxable": True,
                "is_active": True,
                "product_type": "Solid Round Bar",
                "pipe_size": diameter,
                "body_shape": "Round",
                "material_grade": _material_grade(description, material_group),
                "notes": notes.strip(),
            }
        )
    return out


def solid_round_bar_source_row_count() -> int:
    return SOLID_ROUND_BAR_SOURCE_ROW_COUNT
