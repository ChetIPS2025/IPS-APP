"""Pricing Guide seed data for square and rectangular tubing."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

SQUARE_TUBING_CATEGORY = "Square Tubing"
# Default material unit when source data does not specify a unit.
SQUARE_TUBING_UNIT = "EA"

_SUBCATEGORY_BY_GROUP: dict[str, str] = {
    "Stainless Steel": "Stainless Steel",
    "Aluminium": "Aluminum",
    "Carbon Steel": "Carbon Steel",
}

_ITEM_CODE_PREFIX = "SQTB"

# (description, material_group, shape, price, item_code_suffix)
_SQUARE_TUBING_SOURCE: tuple[tuple[str, str, str, str, str], ...] = (
    ('TS4"X4"X3/8" SQUARE TUBING (CS)', "Carbon Steel", "Square", "331.24", "CS-TS-4X4-38"),
    ('TS3"X3"X1/4" SQUARE TUBING (CS)', "Carbon Steel", "Square", "171.44", "CS-TS-3X3-14"),
    ('2"X6"X3/16" RECTANGULAR TUBING (CS)', "Carbon Steel", "Rectangular", "157.46", "CS-2X6-316-RECT"),
    ('2" X 2" X 1/8" (C.S.) SQUARE TUBING', "Carbon Steel", "Square", "74.45", "CS-2X2-18"),
    ('1" X 1" X 1/8" (C.S.) SQUARE TUBING', "Carbon Steel", "Square", "47.45", "CS-1X1-18"),
    ('2"X3"X1/8" RECTANGULAR TUBING (C.S.)', "Carbon Steel", "Rectangular", "123.65", "CS-2X3-18-RECT"),
    ('2"X3"X3/16" RECTANGULAR TUBING (C.S.)', "Carbon Steel", "Rectangular", "172.80", "CS-2X3-316-RECT"),
    ('2"X4"X1/8" RECTANGULAR TUBING (C.S.)', "Carbon Steel", "Rectangular", "156.73", "CS-2X4-18-RECT"),
    ('2"X2"X1/8" SQUARE TUBING (ALUMINIUM)', "Aluminium", "Square", "109.84", "AL-2X2-18"),
    ('2"X2"X3/16" SQUARE TUBING (ALUMINIUM)', "Aluminium", "Square", "123.42", "AL-2X2-316"),
    ('2"X2"X1/4" SQUARE TUBING (ALUMINIUM)', "Aluminium", "Square", "157.91", "AL-2X2-14"),
    ('1"X2"X1/8" RECTANGULAR TUBING (ALUMINIUM)', "Aluminium", "Rectangular", "79.70", "AL-1X2-18-RECT"),
    ('1"X3"X1/8" RECTANGULAR TUBING (ALUMINIUM)', "Aluminium", "Rectangular", "92.93", "AL-1X3-18-RECT"),
    ('1"X1"X1/8" SQUARE TUBING (S.S.)', "Stainless Steel", "Square", "216.00", "SS-1X1-18"),
)

SQUARE_TUBING_SOURCE_ROW_COUNT = len(_SQUARE_TUBING_SOURCE)


def _material_grade(description: str, material_group: str) -> str:
    if "S.S." in description.upper():
        return "Stainless Steel"
    if "ALUMINIUM" in description.upper():
        return "Aluminum"
    if "(CS)" in description.upper() or "(C.S.)" in description or "C.S." in description:
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
        f"Square/rectangular tubing catalog item; unit {SQUARE_TUBING_UNIT} "
        f"(default material unit; length not supplied in source data)."
    )


def square_tubing_catalog_items() -> list[dict[str, Any]]:
    """14 pricing rows: square and rectangular tubing across CS, aluminum, and SS."""
    out: list[dict[str, Any]] = []
    for description, material_group, shape, price_raw, suffix in _SQUARE_TUBING_SOURCE:
        price = _decimal_price(price_raw)
        subcategory = _SUBCATEGORY_BY_GROUP[material_group]
        out.append(
            {
                "item_code": _item_code(suffix),
                "item_type": "Material",
                "item_class": "Non-Inventory",
                "description": description,
                "category": SQUARE_TUBING_CATEGORY,
                "subcategory": subcategory,
                "unit": SQUARE_TUBING_UNIT,
                "default_cost": _price_to_float(price),
                "default_markup_percent": 0.0,
                "default_sell_price": _price_to_float(price),
                "taxable": True,
                "is_active": True,
                "product_type": "Tubing",
                "body_shape": shape,
                "material_grade": _material_grade(description, material_group),
                "notes": _base_notes(),
            }
        )
    return out


def square_tubing_source_row_count() -> int:
    return SQUARE_TUBING_SOURCE_ROW_COUNT
