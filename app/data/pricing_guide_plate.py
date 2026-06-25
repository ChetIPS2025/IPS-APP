"""Pricing Guide seed data for plate materials."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

PLATE_CATEGORY = "Plate"
# Default material unit when source data does not specify a unit.
PLATE_UNIT = "EA"

# Material group labels stored in ``subcategory`` (US spelling for aluminum group).
_SUBCATEGORY_BY_GROUP: dict[str, str] = {
    "Stainless Steel": "Stainless Steel",
    "Aluminium": "Aluminum",
    "Carbon Steel": "Carbon Steel",
}

_ITEM_CODE_PREFIX = "PLATE"

# (description, material_group, price, item_code_suffix, duplicate_source_record)
_PLATE_SOURCE: tuple[tuple[str, str, str, str, bool], ...] = (
    ('4\' X 8\' X 1/8" PLATE (316 S.S.)', "Stainless Steel", "708.50", "SS-4X8-18-316", False),
    ('4\' X 8\' X 3/16" PLATE (316 S.S.)', "Stainless Steel", "1150.50", "SS-4X8-316-316", False),
    ('4\' X 8\' X 1/2" PLATE (304H S.S.)', "Stainless Steel", "3639.20", "SS-4X8-12-304H", False),
    ('4\' X 8\' X 3/4" PLATE (304H S.S.)', "Stainless Steel", "5164.04", "SS-4X8-34-304H", False),
    ('4\' X 8\' X 3/8" PLATE (316 S.S.)', "Stainless Steel", "1922.40", "SS-4X8-38-316", False),
    ('4\' X 8\' X 1/2" PLATE (316 S.S.)', "Stainless Steel", "2538.91", "SS-4X8-12-316", False),
    ('4\' X 8\' X 3/4" PLATE (316 S.S.)', "Stainless Steel", "4111.76", "SS-4X8-34-316", False),
    ('4\' X 8\' X 3/8" PLATE (304 S.S.)', "Stainless Steel", "1375.37", "SS-4X8-38-304", False),
    ('4\' X 8\' X 1" PLATE (316 S.S.)', "Stainless Steel", "5461.13", "SS-4X8-1-316", False),
    ('4\' X 8\' X 1-1/2" PLATE (316 S.S.)', "Stainless Steel", "10133.75", "SS-4X8-1-12-316", False),
    ('4\' X 8\' X 2" PLATE (316 S.S.)', "Stainless Steel", "11187.50", "SS-4X8-2-316", False),
    ('5\' X 10\' X 1" (304L) S.S. PLATE', "Stainless Steel", "6480.05", "SS-5X10-1-304L", False),
    ('5\' X 10\' X 1/2" (304) S.S. PLATE', "Stainless Steel", "3368.25", "SS-5X10-12-304", False),
    ('5\' X 10\' X 3/4" (304) S.S. PLATE', "Stainless Steel", "5420.76", "SS-5X10-34-304", False),
    ('5\' X 10\' X 1/4" (304) S.S. PLATE', "Stainless Steel", "1362.15", "SS-5X10-14-304", False),
    ('4\' X 8\' X 1/4" PLATE (304 S.S.)', "Stainless Steel", "872.78", "SS-4X8-14-304", False),
    ('5\' X 10\' X 3/16" (304) S.S. PLATE', "Stainless Steel", "1127.25", "SS-5X10-316-304", False),
    ('4\' X 8\' X 1/8" (ALUMINIUM) PLATE', "Aluminium", "291.06", "AL-4X8-18", False),
    ('5\' X 10\' X 1/8" (ALUMINIUM) PLATE', "Aluminium", "318.00", "AL-5X10-18", False),
    ('5\' X 10\' X 1/4" (ALUMINIUM) PLATE', "Aluminium", "683.60", "AL-5X10-14", False),
    ('5\' X 10\' X 1/8" (ALUMINIUM) PLATE', "Aluminium", "519.52", "AL-5X10-18", True),
    ('4\' X 8\' X 3/16" (ALUMINIUM) PLATE', "Aluminium", "278.00", "AL-4X8-316", False),
    ('4\' X 8\' X 1/4" (ALUMINIUM) PLATE', "Aluminium", "434.57", "AL-4X8-14", False),
    ('4\' X 8\' X 3/8" (ALUMINIUM) PLATE', "Aluminium", "685.80", "AL-4X8-38", False),
    ('4\' X 8\' X 1/2" (ALUMINIUM) PLATE', "Aluminium", "1147.50", "AL-4X8-12", False),
    ('5\' X 10\' X 3/16" (ALUMINIUM) PLATE', "Aluminium", "660.00", "AL-5X10-316", False),
    ('4\' X 8\' X 1-1/2" (C.S.) PLATE', "Carbon Steel", "1545.00", "CS-4X8-1-12", False),
    ('8\' X 10\' X 1" (C.S.) PLATE', "Carbon Steel", "2964.70", "CS-8X10-1", False),
    ('8\' X 10\' X 7/8" (C.S.) PLATE', "Carbon Steel", "2006.75", "CS-8X10-78", False),
    ('8\' X 10\' X 5/8" (C.S.) PLATE', "Carbon Steel", "1857.25", "CS-8X10-58", False),
    ('4\' X 8\' X 3/8" (C.S.) PLATE', "Carbon Steel", "318.81", "CS-4X8-38", False),
    ('5\' X 10\' X 1" (C.S.) PLATE', "Carbon Steel", "1850.29", "CS-5X10-1", False),
    ('5\' X 10\' X 1/2" (C.S.) PLATE', "Carbon Steel", "814.76", "CS-5X10-12", False),
    ('4\' X 8\' X 1" (C.S.) PLATE', "Carbon Steel", "1241.17", "CS-4X8-1", False),
    ('4\' X 8\' X 1/2" (C.S.) PLATE', "Carbon Steel", "403.08", "CS-4X8-12", False),
    ('4\' X 8\' X 3/4" (C.S.) PLATE', "Carbon Steel", "861.01", "CS-4X8-34", False),
    ('4\' X 8\' X 1/4" (C.S.) PLATE', "Carbon Steel", "244.48", "CS-4X8-14", False),
    ('5\' X 10\' X 1/4" (C.S.) PLATE', "Carbon Steel", "373.44", "CS-5X10-14", False),
    ('5\' X 10\' X 1/8" (C.S.) PLATE', "Carbon Steel", "215.18", "CS-5X10-18", False),
    ('5\' X 10\' X 3/4" (C.S.) PLATE', "Carbon Steel", "1238.44", "CS-5X10-34", False),
    ('5\' X 10\' X 3/16" (C.S.) PLATE', "Carbon Steel", "249.06", "CS-5X10-316", False),
    ('5\' X 10\' X 1/8" (C.S.) DECK PLATE', "Carbon Steel", "295.28", "CS-5X10-18-DECK", False),
    ('5\' X 10\' X 5/8" (C.S.) PLATE', "Carbon Steel", "1258.75", "CS-5X10-58", False),
    ('5\' X 10\' X 3/8" (C.S.) PLATE', "Carbon Steel", "611.27", "CS-5X10-38", False),
)

PLATE_SOURCE_ROW_COUNT = len(_PLATE_SOURCE)


def _material_grade(description: str, material_group: str) -> str:
    if "304H S.S." in description or "(304H" in description:
        return "304H Stainless Steel"
    if "304L" in description:
        return "304L Stainless Steel"
    if "(304) S.S." in description or "304 S.S." in description:
        return "304 Stainless Steel"
    if "316 S.S." in description or "(316" in description:
        return "316 Stainless Steel"
    if "(ALUMINIUM)" in description:
        return "Aluminum"
    if "(C.S.)" in description:
        return "Carbon Steel"
    return _SUBCATEGORY_BY_GROUP.get(material_group, material_group)


def _product_type(description: str) -> str:
    if "DECK PLATE" in description.upper():
        return "Deck Plate"
    return "Plate"


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _item_code(suffix: str) -> str:
    return f"{_ITEM_CODE_PREFIX}-{suffix}"


def _base_notes() -> str:
    return f"Plate catalog item; unit {PLATE_UNIT} (default material unit; unit not supplied in source data)."


def _duplicate_note(alternate_price: Decimal) -> str:
    return (
        f"Import review: duplicate source record with price ${_price_to_float(alternate_price):.2f} "
        f"(not used as active catalog price)."
    )


def plate_duplicate_price_review() -> list[dict[str, Any]]:
    """Catalog items with alternate source prices preserved in notes."""
    review: list[dict[str, Any]] = []
    for item in plate_catalog_items():
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


def plate_catalog_items() -> list[dict[str, Any]]:
    """
    43 unique pricing rows consolidated from 44 source records.

    Duplicate descriptions keep the first-listed price as active; later duplicate
    source prices are stored in ``notes`` and ``_alternate_source_prices``.
    """
    by_code: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for description, material_group, price_raw, suffix, is_duplicate in _PLATE_SOURCE:
        code = _item_code(suffix)
        price = _decimal_price(price_raw)
        subcategory = _SUBCATEGORY_BY_GROUP[material_group]
        grade = _material_grade(description, material_group)
        product_type = _product_type(description)

        if code not in by_code:
            notes = _base_notes()
            if is_duplicate:
                notes = f"{notes} {_duplicate_note(price)}"
            by_code[code] = {
                "item_code": code,
                "item_type": "Material",
                "item_class": "Non-Inventory",
                "description": description,
                "category": PLATE_CATEGORY,
                "subcategory": subcategory,
                "unit": PLATE_UNIT,
                "default_cost": _price_to_float(price),
                "default_markup_percent": 0.0,
                "default_sell_price": _price_to_float(price),
                "taxable": True,
                "is_active": True,
                "product_type": product_type,
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


def plate_source_row_count() -> int:
    return PLATE_SOURCE_ROW_COUNT
