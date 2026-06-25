"""Pricing Guide seed data for C-channel materials."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

C_CHANNEL_CATEGORY = "C-Channel"
# Default material unit when source data does not specify a unit.
C_CHANNEL_UNIT = "EA"

_SUBCATEGORY_BY_GROUP: dict[str, str] = {
    "Aluminium": "Aluminum",
    "Carbon Steel": "Carbon Steel",
}

_ITEM_CODE_PREFIX = "CCH"

# (description, material_group, price, item_code_suffix, duplicate_source_record)
_C_CHANNEL_SOURCE: tuple[tuple[str, str, str, str, bool], ...] = (
    ("C12x25 (C.S.) CHANNEL", "Carbon Steel", "962.50", "CS-C12X25", False),
    ("C12x25 (C.S.) CHANNEL", "Carbon Steel", "495.38", "CS-C12X25", True),
    ("C8x11.5 (C.S.) CHANNEL", "Carbon Steel", "183.05", "CS-C8X11-5", False),
    ("C8x13.75 (C.S.) CHANNEL", "Carbon Steel", "211.99", "CS-C8X13-75", False),
    ("C10x15.3 (C.S.) CHANNEL", "Carbon Steel", "286.99", "CS-C10X15-3", False),
    ("C10x20 (C.S.) CHANNEL", "Carbon Steel", "390.60", "CS-C10X20", False),
    ("MC8X21.4 (C.S.) CHANNEL", "Carbon Steel", "608.55", "CS-MC8X21-4", False),
    ("MC6x#18 (C.S.) CHANNEL", "Carbon Steel", "495.10", "CS-MC6X-18", False),
    ("C6x8.2 C.S. Channel", "Carbon Steel", "140.77", "CS-C6X8-2", False),
    ('3" CHANNEL (ALUMINIUM)', "Aluminium", "130.68", "AL-3IN", False),
)

C_CHANNEL_SOURCE_ROW_COUNT = len(_C_CHANNEL_SOURCE)


def _material_grade(description: str, material_group: str) -> str:
    if "ALUMINIUM" in description.upper():
        return "Aluminum"
    if "(C.S.)" in description or "C.S." in description:
        return "Carbon Steel"
    return _SUBCATEGORY_BY_GROUP.get(material_group, material_group)


def _body_shape(description: str) -> str:
    """Distinguish C-channel from MC (miscellaneous channel) shapes."""
    stripped = description.strip()
    if stripped.upper().startswith("MC"):
        return "MC"
    return "C"


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _item_code(suffix: str) -> str:
    return f"{_ITEM_CODE_PREFIX}-{suffix}"


def _base_notes() -> str:
    return (
        f"C-channel catalog item; unit {C_CHANNEL_UNIT} "
        f"(default material unit; length not supplied in source data)."
    )


def _duplicate_note(alternate_price: Decimal) -> str:
    return (
        f"Import review: duplicate source record with price ${_price_to_float(alternate_price):.2f} "
        f"(not used as active catalog price)."
    )


def c_channel_duplicate_price_review() -> list[dict[str, Any]]:
    """Catalog items with alternate source prices preserved in notes."""
    review: list[dict[str, Any]] = []
    for item in c_channel_catalog_items():
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


def c_channel_catalog_items() -> list[dict[str, Any]]:
    """
    9 unique pricing rows consolidated from 10 source records.

    Duplicate descriptions keep the first-listed price as active; later duplicate
    source prices are stored in ``notes`` and ``_alternate_source_prices``.
    """
    by_code: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for description, material_group, price_raw, suffix, is_duplicate in _C_CHANNEL_SOURCE:
        code = _item_code(suffix)
        price = _decimal_price(price_raw)
        subcategory = _SUBCATEGORY_BY_GROUP[material_group]
        grade = _material_grade(description, material_group)
        body_shape = _body_shape(description)

        if code not in by_code:
            notes = _base_notes()
            if is_duplicate:
                notes = f"{notes} {_duplicate_note(price)}"
            by_code[code] = {
                "item_code": code,
                "item_type": "Material",
                "item_class": "Non-Inventory",
                "description": description,
                "category": C_CHANNEL_CATEGORY,
                "subcategory": subcategory,
                "unit": C_CHANNEL_UNIT,
                "default_cost": _price_to_float(price),
                "default_markup_percent": 0.0,
                "default_sell_price": _price_to_float(price),
                "taxable": True,
                "is_active": True,
                "product_type": "C-Channel",
                "body_shape": body_shape,
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


def c_channel_source_row_count() -> int:
    return C_CHANNEL_SOURCE_ROW_COUNT
