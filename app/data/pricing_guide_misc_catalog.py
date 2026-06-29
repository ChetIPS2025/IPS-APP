"""Pricing Guide seed data for mixed building, tools, and electrical catalog items."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

CATALOG_UNIT = "EA"

# (
#   category,
#   subcategory,
#   manufacturer,
#   description,
#   price,
#   item_code,
#   model_number,
#   product_type,
# )
_MISC_CATALOG_SOURCE: tuple[tuple[str, str, str, str, str, str, str, str], ...] = (
    (
        "Building Materials",
        "Ceiling Tiles",
        "Art3d",
        "Acoustic Polyester Drop Ceiling Tiles, Waterproof 12-Pack, 2 ft x 2 ft, Covers 48 Sq. Ft., Black",
        "84.60",
        "ART3D-ACOUSTIC-CEILING-TILE-12PK",
        "",
        "Ceiling Tile",
    ),
    (
        "Building Materials",
        "Ceiling Tiles",
        "STICKGOO",
        "Black Drop Ceiling Tiles, 2 ft x 2 ft, Waterproof PVC Ceiling Panels, Fire Resistant, Smooth Ceiling Decor Coverings, 24 in x 24 in, 12-Pack, Covers 48 Sq. Ft.",
        "79.90",
        "STICKGOO-CEILING-TILE-12PK-BLK",
        "",
        "Ceiling Tile",
    ),
    (
        "Tools",
        "Pneumatic Impact Wrenches",
        "XIIW",
        '1" Air Impact Wrench, Up to 4000 ft-lbs High Reverse Torque, 27.6 lb, Pneumatic, Dual Handles, 3800 RPM',
        "274.39",
        "XIIW-1IN-AIR-IMPACT-WRENCH",
        "",
        "Pneumatic Impact Wrench",
    ),
    (
        "Electrical",
        "LED Flat Panel Lights",
        "Lithonia Lighting",
        "2 ft x 2 ft LED Flat Panel Light, 2500/3200/4000 Adjustable Lumens, 3500K/4000K/5000K Switchable CCT, White",
        "56.37",
        "LITHONIA-CPX-2X2",
        "CPX 2x2",
        "LED Flat Panel Light",
    ),
)

MISC_CATALOG_SOURCE_ROW_COUNT = len(_MISC_CATALOG_SOURCE)


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _base_notes(*, manufacturer: str, category: str, subcategory: str) -> str:
    return (
        f"Catalog item; manufacturer {manufacturer}; "
        f"category {category} / {subcategory}; unit {CATALOG_UNIT}."
    )


def misc_catalog_items() -> list[dict[str, Any]]:
    """Active mixed catalog rows for the Pricing Guide."""
    out: list[dict[str, Any]] = []
    for (
        category,
        subcategory,
        manufacturer,
        description,
        price_raw,
        item_code,
        model_number,
        product_type,
    ) in _MISC_CATALOG_SOURCE:
        price = _decimal_price(price_raw)
        catalog_price = _price_to_float(price)
        sku = model_number or item_code
        row: dict[str, Any] = {
            "item_code": item_code,
            "item_type": "Material",
            "item_class": "Non-Inventory",
            "description": description,
            "category": category,
            "subcategory": subcategory,
            "unit": CATALOG_UNIT,
            "default_cost": catalog_price,
            "default_markup_percent": 0.0,
            "default_sell_price": catalog_price,
            "markup_percent": 0.0,
            "sell_price": catalog_price,
            "item_number": item_code,
            "sku": sku,
            "vendor": manufacturer,
            "taxable": True,
            "is_active": True,
            "product_type": product_type,
            "notes": _base_notes(
                manufacturer=manufacturer,
                category=category,
                subcategory=subcategory,
            ),
        }
        if model_number:
            row["model_number"] = model_number
        out.append(row)
    return out


def misc_catalog_source_row_count() -> int:
    return MISC_CATALOG_SOURCE_ROW_COUNT
