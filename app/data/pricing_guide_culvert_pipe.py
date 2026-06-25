"""Pricing Guide seed data for culvert pipe."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

CULVERT_PIPE_CATEGORY = "Culvert Pipe"
# Unit for a complete pipe section; source does not specify price-per-foot basis.
CULVERT_PIPE_UNIT = "EA"

_ITEM_CODE_PREFIX = "CULV"

# (description, diameter, length, color, construction, price, suffix)
_CULVERT_PIPE_SOURCE: tuple[tuple[str, str, str, str, str, str, str], ...] = (
    ('30" X 20\' BLACK CORRIGATED CULVERT', '30"', "20'", "Black", "Corrugated", "945.00", "30-20"),
    ('18" X 20\' BLACK CORRIGATED CULVERT', '18"', "20'", "Black", "Corrugated", "405.00", "18-20"),
)

CULVERT_PIPE_SOURCE_ROW_COUNT = len(_CULVERT_PIPE_SOURCE)


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _item_code(suffix: str) -> str:
    return f"{_ITEM_CODE_PREFIX}-{suffix}"


def _base_notes(*, color: str, length: str, construction: str) -> str:
    return (
        f"Culvert pipe catalog item; unit {CULVERT_PIPE_UNIT} (complete pipe section; "
        f"price-per-foot basis not supplied). "
        f"Color: {color}. Length: {length}. Construction: {construction}. "
        f"Material not specified in source data."
    )


def culvert_pipe_catalog_items() -> list[dict[str, Any]]:
    """2 pricing rows for corrugated black culvert pipe sections."""
    out: list[dict[str, Any]] = []
    for description, diameter, length, color, construction, price_raw, suffix in _CULVERT_PIPE_SOURCE:
        price = _decimal_price(price_raw)
        out.append(
            {
                "item_code": _item_code(suffix),
                "item_type": "Material",
                "item_class": "Non-Inventory",
                "description": description,
                "category": CULVERT_PIPE_CATEGORY,
                "subcategory": "",
                "unit": CULVERT_PIPE_UNIT,
                "default_cost": _price_to_float(price),
                "default_markup_percent": 0.0,
                "default_sell_price": _price_to_float(price),
                "taxable": True,
                "is_active": True,
                "product_type": "Culvert",
                "pipe_size": diameter,
                "body_shape": construction,
                "connection_type": length,
                "material_grade": "",
                "notes": _base_notes(color=color, length=length, construction=construction),
            }
        )
    return out


def culvert_pipe_source_row_count() -> int:
    return CULVERT_PIPE_SOURCE_ROW_COUNT
