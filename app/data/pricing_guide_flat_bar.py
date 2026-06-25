"""Pricing Guide seed data for flat bar materials."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

FLAT_BAR_CATEGORY = "Flat Bar"
# Default material unit when source data does not specify length or unit.
FLAT_BAR_UNIT = "EA"

# Material group labels stored in ``subcategory`` (US spelling for aluminum group).
_SUBCATEGORY_BY_GROUP: dict[str, str] = {
    "Stainless Steel": "Stainless Steel",
    "Aluminium": "Aluminum",
    "Carbon Steel": "Carbon Steel",
}

_ITEM_CODE_PREFIX = "FLATBAR"

# (description, material_group, price, item_code_suffix, duplicate_source_record)
_FLAT_BAR_SOURCE: tuple[tuple[str, str, str, str, bool], ...] = (
    ('3/16" X 4" (304) S.S. FLAT BAR', "Stainless Steel", "143.51", "SS-316X4-304", False),
    ('1/4" X 4" (304) S.S. FLAT BAR', "Stainless Steel", "158.20", "SS-14X4-304", False),
    ('1/4" X 6" (304) S.S. FLAT BAR', "Stainless Steel", "299.70", "SS-14X6-304", False),
    ('1/4" X 6" (316) S.S. FLAT BAR', "Stainless Steel", "441.98", "SS-14X6-316", False),
    ('3/16" X 4" (304) S.S. FLAT BAR', "Stainless Steel", "128.80", "SS-316X4-304", True),
    ('3/16" X 6" (304) S.S. FLAT BAR', "Stainless Steel", "240.98", "SS-316X6-304", False),
    ('1/2" X 2" (316) S.S. FLAT BAR', "Stainless Steel", "325.15", "SS-12X2-316", False),
    ('1/4" X 1" (ALUMINIUM) FLAT BAR', "Aluminium", "22.05", "AL-14X1", False),
    ('1/4" X 4" (ALUMINIUM) FLAT BAR', "Aluminium", "94.50", "AL-14X4", False),
    ('3/8" X 1" (ALUMINIUM) FLAT BAR', "Aluminium", "36.37", "AL-38X1", False),
    ('1/2" X 4" (ALUMINIUM) FLAT BAR', "Aluminium", "185.06", "AL-12X4", False),
    ('1/4" X 2" (ALUMINIUM) FLAT BAR', "Aluminium", "46.38", "AL-14X2", False),
    ('1/4" X 2" (ALUMINIUM) FLAT BAR', "Aluminium", "42.76", "AL-14X2", True),
    ('3/16" X 4" (ALUMINIUM) FLAT BAR', "Aluminium", "71.28", "AL-316X4", False),
    ('3/16" X 3" (ALUMINIUM) FLAT BAR', "Aluminium", "53.46", "AL-316X3", False),
    ('1/4" X 1" (C.S.) FLAT BAR', "Carbon Steel", "17.79", "CS-14X1", False),
    ('1/4" X 2" (C.S.) FLAT BAR', "Carbon Steel", "27.23", "CS-14X2", False),
    ('1/4" X 4" (C.S.) FLAT BAR', "Carbon Steel", "54.04", "CS-14X4", False),
    ('3/8" X 2-1/2" (C.S.) FLAT BAR', "Carbon Steel", "60.00", "CS-38X2-12", False),
    ('3/8" X 2" (C.S.) FLAT BAR', "Carbon Steel", "50.00", "CS-38X2", False),
    ('3/8" X 3" (C.S.) FLAT BAR', "Carbon Steel", "70.00", "CS-38X3", False),
    ('1/2" X 4" (C.S.) FLAT BAR', "Carbon Steel", "113.40", "CS-12X4", False),
    ('3/8" X 4" (C.S.) FLAT BAR', "Carbon Steel", "84.29", "CS-38X4", False),
    ('3/8" X 6" (C.S.) FLAT BAR', "Carbon Steel", "131.00", "CS-38X6", False),
    ('1/2" X 3" (C.S.) FLAT BAR', "Carbon Steel", "88.48", "CS-12X3", False),
    ('1/8" X 2" (C.S.) FLAT BAR', "Carbon Steel", "17.86", "CS-18X2", False),
    ('1/2" X 2" (C.S.) FLAT BAR', "Carbon Steel", "64.20", "CS-12X2", False),
    ('3/16" X 2" (C.S.) FLAT BAR', "Carbon Steel", "24.68", "CS-316X2", False),
)

FLAT_BAR_SOURCE_ROW_COUNT = len(_FLAT_BAR_SOURCE)


def _material_grade(description: str, material_group: str) -> str:
    if "(304)" in description:
        return "304 Stainless Steel"
    if "(316)" in description:
        return "316 Stainless Steel"
    if "(ALUMINIUM)" in description:
        return "Aluminum"
    if "(C.S.)" in description:
        return "Carbon Steel"
    return _SUBCATEGORY_BY_GROUP.get(material_group, material_group)


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _item_code(suffix: str) -> str:
    return f"{_ITEM_CODE_PREFIX}-{suffix}"


def _base_notes() -> str:
    return f"Flat bar catalog item; unit {FLAT_BAR_UNIT} (default material unit; length not supplied)."


def _duplicate_note(alternate_price: Decimal) -> str:
    return (
        f"Import review: duplicate source record with price ${_price_to_float(alternate_price):.2f} "
        f"(not used as active catalog price)."
    )


def flat_bar_duplicate_price_review() -> list[dict[str, Any]]:
    """Catalog items with alternate source prices preserved in notes."""
    review: list[dict[str, Any]] = []
    for item in flat_bar_catalog_items():
        alt = item.get("_alternate_source_prices") or []
        if alt:
            review.append(
                {
                    "item_code": item["item_code"],
                    "description": item["description"],
                    "active_price": item["default_cost"],
                    "alternate_source_prices": list(alt),
                }
            )
    return review


def flat_bar_catalog_items() -> list[dict[str, Any]]:
    """
    26 unique pricing rows consolidated from 28 source records.

    Duplicate descriptions keep the first-listed price as active; later duplicate
    source prices are stored in ``notes`` and ``_alternate_source_prices``.
    """
    by_code: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for description, material_group, price_raw, suffix, is_duplicate in _FLAT_BAR_SOURCE:
        code = _item_code(suffix)
        price = _decimal_price(price_raw)
        subcategory = _SUBCATEGORY_BY_GROUP[material_group]
        grade = _material_grade(description, material_group)

        if code not in by_code:
            notes = _base_notes()
            if is_duplicate:
                notes = f"{notes} {_duplicate_note(price)}"
            by_code[code] = {
                "item_code": code,
                "item_type": "Material",
                "item_class": "Non-Inventory",
                "description": description,
                "category": FLAT_BAR_CATEGORY,
                "subcategory": subcategory,
                "unit": FLAT_BAR_UNIT,
                "default_cost": _price_to_float(price),
                "default_markup_percent": 0.0,
                "default_sell_price": _price_to_float(price),
                "taxable": True,
                "is_active": True,
                "product_type": "Flat Bar",
                "material_grade": grade,
                "notes": notes.strip(),
                "_alternate_source_prices": [str(price)] if is_duplicate else [],
                "_source_row_count": 1,
            }
            order.append(code)
            continue

        row = by_code[code]
        row["_source_row_count"] = int(row.get("_source_row_count") or 1) + 1
        alt_prices: list[str] = list(row.get("_alternate_source_prices") or [])
        alt_prices.append(str(price))
        row["_alternate_source_prices"] = alt_prices
        if is_duplicate:
            row["notes"] = f"{row['notes']} {_duplicate_note(price)}".strip()
        elif not re.search(r"duplicate source record", row["notes"], re.I):
            row["notes"] = f"{row['notes']} {_duplicate_note(price)}".strip()

    out = [by_code[code] for code in order]
    for row in out:
        row.pop("_source_row_count", None)
    return out


def flat_bar_source_row_count() -> int:
    return FLAT_BAR_SOURCE_ROW_COUNT
