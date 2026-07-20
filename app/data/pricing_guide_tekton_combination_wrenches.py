"""Pricing Guide seed data for TEKTON combination wrenches."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

HAND_TOOLS_CATEGORY = "Hand Tools"
COMBINATION_WRENCHES_SUBCATEGORY = "Combination Wrenches"
TEKTON_MANUFACTURER = "TEKTON"
HAND_TOOL_UNIT = "EA"

# (description, part_number, price)
_TEKTON_COMBINATION_WRENCH_SOURCE: tuple[tuple[str, str, str], ...] = (
    ('TEKTON 1-1/8" Combination Wrench', "18268", "21.00"),
    ('TEKTON 1-3/16" Combination Wrench', "18269", "23.00"),
    ('TEKTON 1-3/8" Combination Wrench', "WCB23035", "34.21"),
    ('TEKTON 1-7/16" Combination Wrench', "WCB23036", "43.94"),
    ('TEKTON 1-5/8" Combination Wrench', "WCB23041", "59.95"),
    ('TEKTON 1-9/16" Combination Wrench', "WCB23040", "62.00"),
    ('TEKTON 1-11/16" Combination Wrench', "WCB23043", "62.00"),
    ('TEKTON 1-3/4" Combination Wrench', "WCB23044", "75.00"),
    ('TEKTON 1-13/16" Combination Wrench', "WCB23046", "75.00"),
    ('TEKTON 1-7/8" Combination Wrench', "WCB23048", "86.00"),
    ('TEKTON 1-15/16" Combination Wrench', "WCB23049", "90.00"),
    ('TEKTON 2" Combination Wrench', "WCB23050", "90.00"),
)

TEKTON_COMBINATION_WRENCH_SOURCE_ROW_COUNT = len(_TEKTON_COMBINATION_WRENCH_SOURCE)


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _base_notes() -> str:
    return (
        f"Hand tool catalog item; manufacturer {TEKTON_MANUFACTURER}; "
        f"unit {HAND_TOOL_UNIT}."
    )


def tekton_combination_wrench_catalog_items() -> list[dict[str, Any]]:
    """Active TEKTON combination wrench rows for the Pricing Guide."""
    out: list[dict[str, Any]] = []
    for description, part_number, price_raw in _TEKTON_COMBINATION_WRENCH_SOURCE:
        price = _decimal_price(price_raw)
        catalog_price = _price_to_float(price)
        out.append(
            {
                "item_code": part_number,
                "item_type": "Material",
                "item_class": "Non-Inventory",
                "description": description,
                "category": HAND_TOOLS_CATEGORY,
                "subcategory": COMBINATION_WRENCHES_SUBCATEGORY,
                "unit": HAND_TOOL_UNIT,
                "default_cost": catalog_price,
                "default_markup_percent": 0.0,
                "default_sell_price": catalog_price,
                "markup_percent": 0.0,
                "sell_price": catalog_price,
                "model_number": part_number,
                "item_number": part_number,
                "sku": part_number,
                "vendor": TEKTON_MANUFACTURER,
                "taxable": True,
                "is_active": True,
                "product_type": "Combination Wrench",
                "notes": _base_notes(),
            }
        )
    return out


def tekton_combination_wrench_source_row_count() -> int:
    return TEKTON_COMBINATION_WRENCH_SOURCE_ROW_COUNT
