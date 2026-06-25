"""Pricing Guide seed data for rebar materials."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

REBAR_CATEGORY = "Rebar"
# Default material unit when source data does not specify a unit.
REBAR_UNIT = "EA"

_ITEM_CODE_PREFIX = "REBAR"

# (description, bar_number, diameter, price or None, suffix, requires_price_review)
_REBAR_SOURCE: tuple[tuple[str, str, str, str | None, str, bool], ...] = (
    ('#6 (3/4") REBAR', "#6", '3/4"', "16.69", "CS-6", False),
    ('#5 (5/8") REBAR', "#5", '5/8"', None, "CS-5", True),
    ('#4 (1/2") REBAR', "#4", '1/2"', None, "CS-4", True),
)

REBAR_SOURCE_ROW_COUNT = len(_REBAR_SOURCE)

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


def _base_notes() -> str:
    return (
        f"Rebar catalog item; unit {REBAR_UNIT} "
        f"(default material unit; length/weight basis not supplied in source data)."
    )


def rebar_requires_price_review() -> list[dict[str, Any]]:
    """Source rows with no supplied price — inactive in catalog until priced."""
    return [
        {
            "item_code": item["item_code"],
            "description": item["description"],
            "bar_number": item.get("dash_size"),
            "diameter": item.get("pipe_size"),
            "requires_price_review": True,
        }
        for item in rebar_catalog_items()
        if item.get("_requires_price_review")
    ]


def rebar_active_catalog_items() -> list[dict[str, Any]]:
    """Priced, active rebar rows available to the estimate builder."""
    return [item for item in rebar_catalog_items() if item.get("is_active") is not False]


def rebar_catalog_items() -> list[dict[str, Any]]:
    """3 catalog rows; two inactive rows have no supplied source price."""
    out: list[dict[str, Any]] = []
    for description, bar_number, diameter, price_raw, suffix, requires_price_review in _REBAR_SOURCE:
        notes = _base_notes()
        if requires_price_review:
            notes = f"{notes} {_PRICE_REVIEW_NOTE}"

        row: dict[str, Any] = {
            "item_code": _item_code(suffix),
            "item_type": "Material",
            "item_class": "Non-Inventory",
            "description": description,
            "category": REBAR_CATEGORY,
            "subcategory": "Carbon Steel",
            "unit": REBAR_UNIT,
            "taxable": True,
            "is_active": not requires_price_review,
            "product_type": "Rebar",
            "dash_size": bar_number,
            "pipe_size": diameter,
            "material_grade": "Carbon Steel",
            "notes": notes.strip(),
            "_requires_price_review": requires_price_review,
        }
        if price_raw is not None and not requires_price_review:
            price = _decimal_price(price_raw)
            row["default_cost"] = _price_to_float(price)
            row["default_markup_percent"] = 0.0
            row["default_sell_price"] = _price_to_float(price)
        out.append(row)
    return out


def rebar_source_row_count() -> int:
    return REBAR_SOURCE_ROW_COUNT
