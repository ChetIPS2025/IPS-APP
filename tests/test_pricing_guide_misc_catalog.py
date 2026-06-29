"""Pricing Guide — mixed building, tools, and electrical catalog seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_misc_catalog import (
    CATALOG_UNIT,
    MISC_CATALOG_SOURCE_ROW_COUNT,
    misc_catalog_items,
)


def test_misc_catalog_source_and_catalog_counts():
    items = misc_catalog_items()
    assert MISC_CATALOG_SOURCE_ROW_COUNT == 4
    assert len(items) == 4


def test_misc_catalog_categories_and_manufacturers():
    items = misc_catalog_items()
    by_code = {r["item_code"]: r for r in items}

    art3d = by_code["ART3D-ACOUSTIC-CEILING-TILE-12PK"]
    assert art3d["category"] == "Building Materials"
    assert art3d["subcategory"] == "Ceiling Tiles"
    assert art3d["vendor"] == "Art3d"

    xiiw = by_code["XIIW-1IN-AIR-IMPACT-WRENCH"]
    assert xiiw["category"] == "Tools"
    assert xiiw["subcategory"] == "Pneumatic Impact Wrenches"
    assert xiiw["vendor"] == "XIIW"

    lithonia = by_code["LITHONIA-CPX-2X2"]
    assert lithonia["category"] == "Electrical"
    assert lithonia["subcategory"] == "LED Flat Panel Lights"
    assert lithonia["vendor"] == "Lithonia Lighting"
    assert lithonia["model_number"] == "CPX 2x2"

    stickgoo = by_code["STICKGOO-CEILING-TILE-12PK-BLK"]
    assert stickgoo["category"] == "Building Materials"
    assert stickgoo["subcategory"] == "Ceiling Tiles"
    assert stickgoo["vendor"] == "STICKGOO"

    assert all(r["unit"] == CATALOG_UNIT for r in items)
    assert all(r["is_active"] is True for r in items)


def test_misc_catalog_descriptions_and_prices():
    items = misc_catalog_items()
    by_code = {r["item_code"]: r for r in items}

    assert by_code["ART3D-ACOUSTIC-CEILING-TILE-12PK"]["description"] == (
        "Acoustic Polyester Drop Ceiling Tiles, Waterproof 12-Pack, 2 ft x 2 ft, "
        "Covers 48 Sq. Ft., Black"
    )
    assert by_code["ART3D-ACOUSTIC-CEILING-TILE-12PK"]["default_cost"] == 84.60

    assert by_code["XIIW-1IN-AIR-IMPACT-WRENCH"]["description"] == (
        '1" Air Impact Wrench, Up to 4000 ft-lbs High Reverse Torque, 27.6 lb, '
        "Pneumatic, Dual Handles, 3800 RPM"
    )
    assert by_code["XIIW-1IN-AIR-IMPACT-WRENCH"]["default_cost"] == 274.39

    assert by_code["LITHONIA-CPX-2X2"]["description"] == (
        "2 ft x 2 ft LED Flat Panel Light, 2500/3200/4000 Adjustable Lumens, "
        "3500K/4000K/5000K Switchable CCT, White"
    )
    assert by_code["LITHONIA-CPX-2X2"]["default_cost"] == 56.37

    assert by_code["STICKGOO-CEILING-TILE-12PK-BLK"]["description"] == (
        "Black Drop Ceiling Tiles, 2 ft x 2 ft, Waterproof PVC Ceiling Panels, Fire Resistant, "
        "Smooth Ceiling Decor Coverings, 24 in x 24 in, 12-Pack, Covers 48 Sq. Ft."
    )
    assert by_code["STICKGOO-CEILING-TILE-12PK-BLK"]["default_cost"] == 79.90


def test_misc_catalog_prices_use_decimal_precision():
    items = misc_catalog_items()
    prices = {r["item_code"]: Decimal(str(r["default_cost"])) for r in items}
    assert prices["ART3D-ACOUSTIC-CEILING-TILE-12PK"] == Decimal("84.60")
    assert prices["XIIW-1IN-AIR-IMPACT-WRENCH"] == Decimal("274.39")
    assert prices["LITHONIA-CPX-2X2"] == Decimal("56.37")
    assert prices["STICKGOO-CEILING-TILE-12PK-BLK"] == Decimal("79.90")


def test_misc_catalog_item_codes_are_unique():
    items = misc_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))
