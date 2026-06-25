"""Pricing Guide seed data for flanges."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

FLANGES_CATEGORY = "Flanges"
# Default fitting unit when source data does not specify a unit.
FLANGES_UNIT = "EA"

_ITEM_CODE_PREFIX = "FLG"

_SUBCATEGORY_BY_GROUP: dict[str, str] = {
    "Stainless Steel": "Stainless Steel",
    "Carbon Steel": "Carbon Steel",
}

# (
#   source_row,
#   description,
#   material_group,
#   grade,
#   flange_type,
#   nominal_size,
#   pressure_class,
#   face,
#   schedule,
#   price or None,
#   item_code_suffix,
#   requires_price_review,
# )
_FLANGE_SOURCE: tuple[tuple[Any, ...], ...] = (
    (1, '1" #150 S.O. FLANGE (304S.S.)', "Stainless Steel", "304", "Slip On", '1"', "150", None, None, "22.50", "SS304-SO-1-150", False),
    (2, '1" #150 S.O. FLANGE (316S.S.)', "Stainless Steel", "316", "Slip On", '1"', "150", None, None, "40.20", "SS316-SO-1-150", False),
    (3, '1" #300 BLIND FLANGE (304S.S.)', "Stainless Steel", "304", "Blind", '1"', "300", None, None, "31.50", "SS304-BLIND-1-300", False),
    (4, '1" #150 BLIND FLANGE (304S.S.)', "Stainless Steel", "304", "Blind", '1"', "150", None, None, "23.50", "SS304-BLIND-1-150", False),
    (5, '1/2" #150 BLIND FLANGE (304S.S.)', "Stainless Steel", "304", "Blind", '1/2"', "150", None, None, "23.50", "SS304-BLIND-12-150", False),
    (6, '1/2" #300 BLIND FLANGE (304S.S.)', "Stainless Steel", "304", "Blind", '1/2"', "300", None, None, "31.50", "SS304-BLIND-12-300", False),
    (7, '1/2" #150 S.O. FLANGE (304S.S.)', "Stainless Steel", "304", "Slip On", '1/2"', "150", None, None, "20.50", "SS304-SO-12-150", False),
    (8, '1/2" #300 S.O. FLANGE (304S.S.)', "Stainless Steel", "304", "Slip On", '1/2"', "300", None, None, "30.00", "SS304-SO-12-300", False),
    (9, '1/2" #150 S.O. FLANGE (304S.S.)', "Stainless Steel", "304", "Slip On", '1/2"', "150", None, None, "20.50", "SS304-SO-12-150", False),
    (10, '1/2" #300 S.O. FLANGE (304S.S.)', "Stainless Steel", "304", "Slip On", '1/2"', "300", None, None, "30.00", "SS304-SO-12-300", False),
    (11, '2" #150 S.O. FLANGE (304S.S.)', "Stainless Steel", "304", "Slip On", '2"', "150", None, None, "39.12", "SS304-SO-2-150", False),
    (12, '42" #150 LIGHT WEIGHT SLIP ON FLANGE', "Stainless Steel", None, "Lightweight Slip On", '42"', "150", None, None, "1156.25", "SS-LW-SO-42-150", False),
    (13, '42" #125 LIGHT WEIGHT SLIP ON FLANGE', "Stainless Steel", None, "Lightweight Slip On", '42"', "125", None, None, "1787.50", "SS-LW-SO-42-125", False),
    (14, '1-1/2" #150 S.O. FLANGE (304S.S.)', "Stainless Steel", "304", "Slip On", '1-1/2"', "150", None, None, "30.50", "SS304-SO-1-12-150", False),
    (15, '1-1/2" #300 S.O. FLANGE (304S.S.)', "Stainless Steel", "304", "Slip On", '1-1/2"', "300", None, None, "46.00", "SS304-SO-1-12-300", False),
    (16, '2" #150 S.O. FLANGE (304S.S.)', "Stainless Steel", "304", "Slip On", '2"', "150", None, None, None, "SS304-SO-2-150", False),
    (17, '2" #150 FLANGE, THREADED, (304S.S.)', "Stainless Steel", "304", "Threaded", '2"', "150", None, None, None, "SS304-THR-2-150", True),
    (18, '1/2" #150 BLIND FLANGE (304S.S.)', "Stainless Steel", "304", "Blind", '1/2"', "150", None, None, "23.50", "SS304-BLIND-12-150", False),
    (19, '1/2" #300 BLIND FLANGE (304S.S.)', "Stainless Steel", "304", "Blind", '1/2"', "300", None, None, "31.50", "SS304-BLIND-12-300", False),
    (20, '3/4" #150 BLIND FLANGE (304S.S.)', "Stainless Steel", "304", "Blind", '3/4"', "150", None, None, "23.50", "SS304-BLIND-34-150", False),
    (21, '3/4" #300 BLIND FLANGE (304S.S.)', "Stainless Steel", "304", "Blind", '3/4"', "300", None, None, "31.50", "SS304-BLIND-34-300", False),
    (22, '1" #150 BLIND FLANGE (304S.S.)', "Stainless Steel", "304", "Blind", '1"', "150", None, None, "23.50", "SS304-BLIND-1-150", False),
    (23, '1" #300 BLIND FLANGE (304S.S.)', "Stainless Steel", "304", "Blind", '1"', "300", None, None, "31.50", "SS304-BLIND-1-300", False),
    (24, '1-1/2" #150 BLIND FLANGE (304S.S.)', "Stainless Steel", "304", "Blind", '1-1/2"', "150", None, None, "30.50", "SS304-BLIND-1-12-150", False),
    (25, '1-1/2" #300 BLIND FLANGE (304S.S.)', "Stainless Steel", "304", "Blind", '1-1/2"', "300", None, None, "43.00", "SS304-BLIND-1-12-300", False),
    (26, '1" #150 BLIND FLANGE (C.S.)', "Carbon Steel", None, "Blind", '1"', "150", None, None, "22.11", "CS-BLIND-1-150", False),
    (27, '2" #150 BLIND FLANGE (C.S.)', "Carbon Steel", None, "Blind", '2"', "150", None, None, "19.80", "CS-BLIND-2-150", False),
    (28, '4" #150 BLIND FLANGE (C.S.)', "Carbon Steel", None, "Blind", '4"', "150", None, None, "35.09", "CS-BLIND-4-150", False),
    (29, '6" #150 BLIND FLANGE (C.S.)', "Carbon Steel", None, "Blind", '6"', "150", None, None, "53.46", "CS-BLIND-6-150", False),
    (30, '3/4" FLANGE, SW, #150, RF, SCH80 (C.S.)', "Carbon Steel", None, "Socket Weld", '3/4"', "150", "Raised Face", "80", "18.37", "CS-SW-34-150-SCH80", False),
    (31, '1" FLANGE, SW, #150, RF, SCH80 (C.S.)', "Carbon Steel", None, "Socket Weld", '1"', "150", "Raised Face", "80", "18.37", "CS-SW-1-150-SCH80", False),
    (32, '1-1/2" FLANGE, SW, #150, RF, SCH80 (C.S.)', "Carbon Steel", None, "Socket Weld", '1-1/2"', "150", "Raised Face", "80", "26.29", "CS-SW-1-12-150-SCH80", False),
    (33, '2" FLANGE, SW, #150, RF, SCH80 (C.S.)', "Carbon Steel", None, "Socket Weld", '2"', "150", "Raised Face", "80", "16.50", "CS-SW-2-150-SCH80", False),
    (34, '3" #150 FLANGE, WN, RF, SCH40 (C.S.)', "Carbon Steel", None, "Weld Neck", '3"', "150", "Raised Face", "40", "29.26", "CS-WN-3-150-SCH40", False),
    (35, '4" #150 FLANGE, WN, RF, SCH40 (C.S.)', "Carbon Steel", None, "Weld Neck", '4"', "150", "Raised Face", "40", "35.20", "CS-WN-4-150-SCH40", False),
    (36, '6" #150 FLANGE, WN, RF, SCH40 (C.S.)', "Carbon Steel", None, "Weld Neck", '6"', "150", "Raised Face", "40", "53.46", "CS-WN-6-150-SCH40", False),
    (37, '8" #150 FLANGE, WN, RF, (C.S.)', "Carbon Steel", None, "Weld Neck", '8"', "150", "Raised Face", None, "94.49", "CS-WN-8-150", False),
    (38, '8" #150 FLANGE, WN, RF, SCH20 (C.S.)', "Carbon Steel", None, "Weld Neck", '8"', "150", "Raised Face", "20", "114.75", "CS-WN-8-150-SCH20", False),
    (39, '10" #150 FLANGE, WN, RF, SCH20 (C.S.)', "Carbon Steel", None, "Weld Neck", '10"', "150", "Raised Face", "20", "182.25", "CS-WN-10-150-SCH20", False),
    (40, '12" #150 FLANGE, WN, RF, SCH20 (C.S.)', "Carbon Steel", None, "Weld Neck", '12"', "150", "Raised Face", "20", "263.25", "CS-WN-12-150-SCH20", False),
)

FLANGES_SOURCE_ROW_COUNT = len(_FLANGE_SOURCE)

_PRICE_REVIEW_NOTE = (
    "Import review: price not supplied in source data — item inactive until catalog price is entered. "
    "Database default_cost is not an estimate price."
)


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _item_code(suffix: str) -> str:
    return f"{_ITEM_CODE_PREFIX}-{suffix}"


def _material_grade(*, material_group: str, grade: str | None) -> str:
    if grade == "304":
        return "304 Stainless Steel"
    if grade == "316":
        return "316 Stainless Steel"
    if material_group == "Carbon Steel":
        return "Carbon Steel"
    return ""


def _schedule_label(schedule: str | None) -> str:
    if not schedule:
        return ""
    sched = str(schedule).strip()
    if sched.upper().startswith("SCH"):
        return sched.upper()
    return f"SCH{sched}"


def _base_notes(*, flange_type: str, grade: str | None) -> str:
    notes = (
        f"Flange catalog item; unit {FLANGES_UNIT} "
        f"(default fitting unit; unit not supplied in source data). "
        f"Type: {flange_type}."
    )
    if grade is None and flange_type == "Lightweight Slip On":
        notes = f"{notes} Grade not specified in source data."
    return notes


def _duplicate_occurrence_note(*, source_rows: list[int], price_raw: str | None) -> str:
    rows = ", ".join(str(r) for r in sorted(source_rows))
    if price_raw is None:
        return (
            f"Import review: duplicate source occurrence with no supplied price "
            f"(source rows {rows})."
        )
    price = _price_to_float(_decimal_price(price_raw))
    return (
        f"Import review: duplicate source occurrence (source rows {rows}); "
        f"same price ${price:.2f}."
    )


def _blank_price_duplicate_note(*, priced_row: int, blank_row: int, price_raw: str) -> str:
    price = _price_to_float(_decimal_price(price_raw))
    return (
        f"Import review: duplicate source occurrence with no supplied price "
        f"(source row {blank_row}); active catalog price ${price:.2f} from source row {priced_row}."
    )


def flanges_requires_price_review() -> list[dict[str, Any]]:
    """Source rows with no supplied price and no priced duplicate — inactive until priced."""
    return [
        {
            "item_code": item["item_code"],
            "description": item["description"],
            "material_group": item["subcategory"],
            "requires_price_review": True,
        }
        for item in flanges_catalog_items()
        if item.get("_requires_price_review")
    ]


def flanges_duplicate_source_review() -> list[dict[str, Any]]:
    """Canonical items consolidated from repeated source descriptions."""
    review: list[dict[str, Any]] = []
    for item in flanges_catalog_items():
        source_row_count = int(item.get("_source_row_count") or 1)
        if source_row_count <= 1:
            continue
        review.append(
            {
                "item_code": item["item_code"],
                "description": item["description"],
                "source_row_count": source_row_count,
                "active_price": item.get("default_cost"),
            }
        )
    return review


def flanges_active_catalog_items() -> list[dict[str, Any]]:
    """Priced, active flange rows available to the estimate builder."""
    return [item for item in flanges_catalog_items() if item.get("is_active") is not False]


def flanges_catalog_items() -> list[dict[str, Any]]:
    """
    33 unique catalog rows consolidated from 40 source records.

    Seven repeated descriptions map to canonical items; blank-price duplicate
    occurrences are preserved in notes. One threaded flange is inactive (no price).
    """
    by_code: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for (
        source_row,
        description,
        material_group,
        grade,
        flange_type,
        nominal_size,
        pressure_class,
        face,
        schedule,
        price_raw,
        suffix,
        requires_price_review,
    ) in _FLANGE_SOURCE:
        code = _item_code(suffix)
        schedule_label = _schedule_label(schedule)

        if code not in by_code:
            notes = _base_notes(flange_type=flange_type, grade=grade)
            if requires_price_review:
                notes = f"{notes} {_PRICE_REVIEW_NOTE}"

            row: dict[str, Any] = {
                "item_code": code,
                "item_type": "Material",
                "item_class": "Non-Inventory",
                "description": description,
                "category": FLANGES_CATEGORY,
                "subcategory": _SUBCATEGORY_BY_GROUP[material_group],
                "unit": FLANGES_UNIT,
                "taxable": True,
                "is_active": not requires_price_review,
                "product_type": flange_type,
                "pipe_size": nominal_size,
                "pressure_class": str(pressure_class or ""),
                "body_shape": str(face or ""),
                "connection_type": schedule_label,
                "material_grade": _material_grade(material_group=material_group, grade=grade),
                "notes": notes.strip(),
                "_requires_price_review": requires_price_review,
                "_source_rows": [source_row],
                "_blank_price_rows": [] if price_raw is not None else [source_row],
                "_priced_source_row": source_row if price_raw is not None else None,
            }
            if price_raw is not None and not requires_price_review:
                price = _decimal_price(price_raw)
                row["default_cost"] = _price_to_float(price)
                row["default_markup_percent"] = 0.0
                row["default_sell_price"] = _price_to_float(price)
            by_code[code] = row
            order.append(code)
            continue

        row = by_code[code]
        row["_source_rows"].append(source_row)
        if price_raw is None:
            row["_blank_price_rows"].append(source_row)
            priced_row = row.get("_priced_source_row")
            if priced_row is not None and row.get("default_cost") is not None:
                active_price = f"{Decimal(str(row['default_cost'])):.2f}"
                note = _blank_price_duplicate_note(
                    priced_row=priced_row,
                    blank_row=source_row,
                    price_raw=active_price,
                )
                if note not in row["notes"]:
                    row["notes"] = f"{row['notes']} {note}".strip()
            continue

        if row.get("_requires_price_review"):
            continue

        priced_row = row.get("_priced_source_row")
        if priced_row is None:
            row["_priced_source_row"] = source_row
            price = _decimal_price(price_raw)
            row["default_cost"] = _price_to_float(price)
            row["default_markup_percent"] = 0.0
            row["default_sell_price"] = _price_to_float(price)
            continue

        dup_note = _duplicate_occurrence_note(
            source_rows=row["_source_rows"],
            price_raw=price_raw,
        )
        if not re.search(r"duplicate source occurrence", row["notes"], re.I):
            row["notes"] = f"{row['notes']} {dup_note}".strip()
        elif dup_note not in row["notes"]:
            row["notes"] = f"{row['notes']} {dup_note}".strip()

    out = [by_code[code] for code in order]
    for row in out:
        source_rows = row.pop("_source_rows", [])
        row.pop("_priced_source_row", None)
        blank_rows = row.pop("_blank_price_rows", [])
        if len(source_rows) > 1 and not blank_rows and not row.get("_requires_price_review"):
            dup_note = _duplicate_occurrence_note(
                source_rows=source_rows,
                price_raw=f"{Decimal(str(row.get('default_cost'))):.2f}" if row.get("default_cost") is not None else None,
            )
            if dup_note not in row["notes"]:
                row["notes"] = f"{row['notes']} {dup_note}".strip()
        row["_source_row_count"] = len(source_rows)
    return out


def flanges_source_row_count() -> int:
    return FLANGES_SOURCE_ROW_COUNT
