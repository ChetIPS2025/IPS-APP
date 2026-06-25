"""Pricing Guide seed data for pipe materials."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

PIPE_CATEGORY = "Pipe"
# Default material unit when source data does not specify a unit.
PIPE_UNIT = "EA"

_SUBCATEGORY_BY_GROUP: dict[str, str] = {
    "Stainless Steel": "Stainless Steel",
    "Aluminium": "Aluminum",
    "Carbon Steel": "Carbon Steel",
}

_ITEM_CODE_PREFIX = "PIPE"

# (description, material_group, price or None, item_code_suffix, duplicate_source_record, requires_price_review)
_PIPE_SOURCE: tuple[tuple[str, str, str | None, str, bool, bool], ...] = (
    ('24" PIPE STD WALL (304 S.S.)', "Stainless Steel", "443.75", "SS-24-STD-304", False, False),
    ('24" PIPE STD WALL (316 S.S.)', "Stainless Steel", "622.55", "SS-24-STD-316", False, False),
    ('2" PIPE SCH40 SEAMLESS (304 S.S.)', "Stainless Steel", "17.77", "SS-2-SCH40-SEAM-304", False, False),
    ('1-1/2" PIPE SCH80 SEAMLESS (304 S.S.)', "Stainless Steel", "17.85", "SS-1-12-SCH80-SEAM-304", False, False),
    ('1-1/2" PIPE SCH40 SEAMLESS (304 S.S.)', "Stainless Steel", "13.45", "SS-1-12-SCH40-SEAM-304", False, False),
    ('1" PIPE SCH80 SEAMLESS (304 S.S.)', "Stainless Steel", "10.30", "SS-1-SCH80-SEAM-304", False, False),
    ('1" PIPE SCH40 SEAMLESS (304 S.S.)', "Stainless Steel", "10.85", "SS-1-SCH40-SEAM-304", False, False),
    ('3/4" PIPE SCH40 SEAMLESS (304 S.S.)', "Stainless Steel", "6.51", "SS-34-SCH40-SEAM-304", False, False),
    ('1/2" PIPE SCH40 SEAMLESS (304 S.S.)', "Stainless Steel", "5.15", "SS-12-SCH40-SEAM-304", False, False),
    ('1/2" PIPE SCH80 SEAMLESS (304 S.S.)', "Stainless Steel", "6.62", "SS-12-SCH80-SEAM-304", False, False),
    ('1/2" PIPE SCH40 (C.S.)', "Carbon Steel", None, "CS-12-SCH40", False, True),
    ('1/2" PIPE SCH80 (C.S.)', "Carbon Steel", None, "CS-12-SCH80", False, True),
    ('3/4" PIPE SCH40 (C.S.)', "Carbon Steel", None, "CS-34-SCH40", False, True),
    ('3/4" PIPE SCH80 (C.S.)', "Carbon Steel", "5.47", "CS-34-SCH80", False, False),
    ('1" PIPE SCH40 (C.S.)', "Carbon Steel", None, "CS-1-SCH40", False, True),
    ('1" PIPE SCH80 (C.S.)', "Carbon Steel", "4.34", "CS-1-SCH80", False, False),
    ('1 1/2" PIPE SCH40 (C.S.)', "Carbon Steel", "2.65", "CS-1-12-SCH40", False, False),
    ('1 1/2" PIPE SCH80 (C.S.)', "Carbon Steel", "11.70", "CS-1-12-SCH80", False, False),
    ('2" PIPE SCH40 (C.S.)', "Carbon Steel", "103.95", "CS-2-SCH40", False, False),
    ('2" PIPE SCH80 (C.S.)', "Carbon Steel", "8.70", "CS-2-SCH80", False, False),
    ('2 1/2" PIPE SCH80 (C.S.)', "Carbon Steel", "7.55", "CS-2-12-SCH80", False, False),
    ('3" PIPE SCH40 (C.S.)', "Carbon Steel", "13.83", "CS-3-SCH40", False, False),
    ('4" PIPE SCH40 (C.S.)', "Carbon Steel", "16.97", "CS-4-SCH40", False, False),
    ('6" PIPE SCH40 (C.S.)', "Carbon Steel", "360.78", "CS-6-SCH40", False, False),
    ('8" PIPE SCH20 (C.S.)', "Carbon Steel", "30.46", "CS-8-SCH20", False, False),
    ('10" PIPE SCH20 (C.S.)', "Carbon Steel", "57.85", "CS-10-SCH20", False, False),
    ('12" PIPE SCH20 (C.S.)', "Carbon Steel", "67.87", "CS-12-SCH20", False, False),
    ('12" PIPE SCH120 (C.S.)', "Carbon Steel", "231.88", "CS-12-SCH120", False, False),
    ('48" X 7/8" X 10\' LONG C.S.', "Carbon Steel", "6825.75", "CS-48-78-10FT", False, False),
    ('48" X 1" X 10\' LONG C.S.', "Carbon Steel", "5067.50", "CS-48-1-10FT", False, False),
    ('48" X 7/8" X 8\' LONG C.S.', "Carbon Steel", "5531.00", "CS-48-78-8FT", False, False),
    ('36" X 5/8" X 10\' LONG C.S.', "Carbon Steel", "2864.00", "CS-36-58-10FT", False, False),
    ('42" X 3/8" WALL CARBON STEEL PIPE', "Carbon Steel", "239.00", "CS-42-38WALL", False, False),
    ('1" PIPE SCH40 SEAMLESS (ALUMINIUM)', "Aluminium", "91.48", "AL-1-SCH40-SEAM", False, False),
    ('1" PIPE SCH80 SEAMLESS (ALUMINIUM)', "Aluminium", "126.11", "AL-1-SCH80-SEAM", False, False),
    ('1" PIPE SCH40 SEAMLESS (ALUMINIUM)', "Aluminium", "42.18", "AL-1-SCH40-SEAM", True, False),
    ('1-1/4" PIPE SCH40 SEAMLESS (ALUMINIUM)', "Aluminium", "56.07", "AL-1-14-SCH40-SEAM", False, False),
    ('2" PIPE SCH40 SEAMLESS (ALUMINIUM)', "Aluminium", "99.23", "AL-2-SCH40-SEAM", False, False),
    ('1-1/2" PIPE SCH40 SEAMLESS (ALUMINIUM)', "Aluminium", "74.03", "AL-1-12-SCH40-SEAM", False, False),
)

PIPE_SOURCE_ROW_COUNT = len(_PIPE_SOURCE)

_PRICE_REVIEW_NOTE = (
    "Import review: price not supplied in source data — item inactive until catalog price is entered. "
    "Database default_cost is not an estimate price."
)


def _material_grade(description: str, material_group: str) -> str:
    if "304 S.S." in description or "(304" in description:
        return "304 Stainless Steel"
    if "316 S.S." in description or "(316" in description:
        return "316 Stainless Steel"
    if "ALUMINIUM" in description.upper():
        return "Aluminum"
    if "(C.S.)" in description or "C.S." in description or "CARBON STEEL" in description.upper():
        return "Carbon Steel"
    return _SUBCATEGORY_BY_GROUP.get(material_group, material_group)


def _pipe_size(description: str) -> str:
    match = re.match(r'^(\d+(?:\s+\d+/\d+|-\d+/\d+|\d+/\d+)?)"', description.strip())
    if match:
        return match.group(1).replace(" ", "-")
    return ""


def _pressure_class(description: str) -> str:
    upper = description.upper()
    if "STD WALL" in upper:
        return "STD WALL"
    match = re.search(r"SCH(\d+)", upper)
    if match:
        return f"SCH{match.group(1)}"
    if "WALL CARBON STEEL PIPE" in upper:
        return "3/8 WALL"
    if " LONG C.S." in upper:
        return ""
    return ""


def _connection_type(description: str) -> str:
    return "Seamless" if "SEAMLESS" in description.upper() else ""


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _item_code(suffix: str) -> str:
    return f"{_ITEM_CODE_PREFIX}-{suffix}"


def _base_notes() -> str:
    return f"Pipe catalog item; unit {PIPE_UNIT} (default material unit; unit not supplied in source data)."


def _duplicate_note(alternate_price: Decimal) -> str:
    return (
        f"Import review: duplicate source record with price ${_price_to_float(alternate_price):.2f} "
        f"(not used as active catalog price)."
    )


def pipe_requires_price_review() -> list[dict[str, Any]]:
    """Source rows with no supplied price — inactive in catalog until priced."""
    return [
        {
            "item_code": item["item_code"],
            "description": item["description"],
            "material_group": item["subcategory"],
            "requires_price_review": True,
        }
        for item in pipe_catalog_items()
        if item.get("_requires_price_review")
    ]


def pipe_duplicate_price_review() -> list[dict[str, Any]]:
    """Catalog items with alternate source prices preserved in notes."""
    review: list[dict[str, Any]] = []
    for item in pipe_catalog_items():
        alt = item.get("_alternate_source_prices") or []
        if alt:
            review.append(
                {
                    "item_code": item["item_code"],
                    "description": item["description"],
                    "active_price": item.get("default_cost"),
                    "alternate_source_prices": list(alt),
                }
            )
    return review


def pipe_active_catalog_items() -> list[dict[str, Any]]:
    """Priced, active pipe rows available to the estimate builder."""
    return [item for item in pipe_catalog_items() if item.get("is_active") is not False]


def pipe_catalog_items() -> list[dict[str, Any]]:
    """
    38 unique catalog rows consolidated from 39 source records.

    Four source rows without prices are imported inactive (not selectable in estimates).
    Duplicate descriptions keep the first-listed price as active.
    """
    by_code: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for (
        description,
        material_group,
        price_raw,
        suffix,
        is_duplicate,
        requires_price_review,
    ) in _PIPE_SOURCE:
        code = _item_code(suffix)
        subcategory = _SUBCATEGORY_BY_GROUP[material_group]
        grade = _material_grade(description, material_group)
        pipe_size = _pipe_size(description)
        pressure_class = _pressure_class(description)
        connection_type = _connection_type(description)

        if code not in by_code:
            notes = _base_notes()
            if requires_price_review:
                notes = f"{notes} {_PRICE_REVIEW_NOTE}"
            elif is_duplicate and price_raw is not None:
                notes = f"{notes} {_duplicate_note(_decimal_price(price_raw))}"

            row: dict[str, Any] = {
                "item_code": code,
                "item_type": "Material",
                "item_class": "Non-Inventory",
                "description": description,
                "category": PIPE_CATEGORY,
                "subcategory": subcategory,
                "unit": PIPE_UNIT,
                "taxable": True,
                "is_active": not requires_price_review,
                "product_type": "Pipe",
                "pipe_size": pipe_size,
                "pressure_class": pressure_class,
                "connection_type": connection_type,
                "material_grade": grade,
                "notes": notes.strip(),
                "_requires_price_review": requires_price_review,
                "_alternate_source_prices": [],
                "_source_row_count": 1,
            }
            if price_raw is not None and not requires_price_review:
                price = _decimal_price(price_raw)
                row["default_cost"] = _price_to_float(price)
                row["default_markup_percent"] = 0.0
                row["default_sell_price"] = _price_to_float(price)
            if is_duplicate and price_raw is not None:
                row["_alternate_source_prices"] = [str(_decimal_price(price_raw))]
            by_code[code] = row
            order.append(code)
            continue

        row = by_code[code]
        row["_source_row_count"] = int(row.get("_source_row_count") or 1) + 1
        if price_raw is not None:
            alt_prices: list[str] = list(row.get("_alternate_source_prices") or [])
            alt_prices.append(str(_decimal_price(price_raw)))
            row["_alternate_source_prices"] = alt_prices
            if is_duplicate:
                row["notes"] = f"{row['notes']} {_duplicate_note(_decimal_price(price_raw))}".strip()
            elif not re.search(r"duplicate source record", row["notes"], re.I):
                row["notes"] = f"{row['notes']} {_duplicate_note(_decimal_price(price_raw))}".strip()

    out = [by_code[code] for code in order]
    for row in out:
        row.pop("_source_row_count", None)
    return out


def pipe_source_row_count() -> int:
    return PIPE_SOURCE_ROW_COUNT
