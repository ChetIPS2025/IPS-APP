"""Pricing Guide — plate materials seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_plate import (
    PLATE_CATEGORY,
    PLATE_SOURCE_ROW_COUNT,
    PLATE_UNIT,
    plate_catalog_items,
    plate_duplicate_price_review,
)


def test_plate_source_and_catalog_counts():
    items = plate_catalog_items()
    assert PLATE_SOURCE_ROW_COUNT == 44
    assert len(items) == 43


def test_plate_category_and_material_groups():
    items = plate_catalog_items()
    assert {r["category"] for r in items} == {PLATE_CATEGORY}
    subcategories = {r["subcategory"] for r in items}
    assert subcategories == {"Stainless Steel", "Aluminum", "Carbon Steel"}
    assert all(r["unit"] == PLATE_UNIT for r in items)
    assert all(r["item_type"] == "Material" for r in items)
    assert all(r["is_active"] is True for r in items)


def test_plate_stainless_grades_and_prices():
    items = plate_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["PLATE-SS-4X8-12-304H"]["material_grade"] == "304H Stainless Steel"
    assert by_code["PLATE-SS-4X8-12-304H"]["default_cost"] == 3639.20
    assert by_code["PLATE-SS-5X10-1-304L"]["material_grade"] == "304L Stainless Steel"
    assert by_code["PLATE-SS-4X8-38-316"]["default_cost"] == 1922.40
    assert by_code["PLATE-SS-4X8-2-316"]["default_cost"] == 11187.50


def test_plate_deck_plate_distinguishable_from_standard_plate():
    items = plate_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    deck = by_code["PLATE-CS-5X10-18-DECK"]
    standard = by_code["PLATE-CS-5X10-18"]
    assert deck["description"] == '5\' X 10\' X 1/8" (C.S.) DECK PLATE'
    assert standard["description"] == '5\' X 10\' X 1/8" (C.S.) PLATE'
    assert deck["product_type"] == "Deck Plate"
    assert standard["product_type"] == "Plate"
    assert deck["default_cost"] == 295.28
    assert standard["default_cost"] == 215.18


def test_plate_aluminum_duplicate_price_preserved_in_notes():
    items = plate_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    al_dup = by_code["PLATE-AL-5X10-18"]
    assert al_dup["description"] == '5\' X 10\' X 1/8" (ALUMINIUM) PLATE'
    assert al_dup["default_cost"] == 318.00
    assert "519.52" in al_dup["notes"]
    assert "duplicate source record" in al_dup["notes"].lower()

    review = plate_duplicate_price_review()
    assert len(review) == 1
    assert review[0]["item_code"] == "PLATE-AL-5X10-18"
    assert review[0]["alternate_source_prices"] == ["519.52"]


def test_plate_aluminum_uses_us_spelling_in_subcategory():
    items = plate_catalog_items()
    al = next(r for r in items if r["item_code"] == "PLATE-AL-4X8-18")
    assert al["subcategory"] == "Aluminum"
    assert al["material_grade"] == "Aluminum"


def test_plate_item_codes_are_unique():
    items = plate_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_plate_prices_use_decimal_precision():
    items = plate_catalog_items()
    cs = next(r for r in items if r["item_code"] == "PLATE-CS-8X10-78")
    assert Decimal(str(cs["default_cost"])) == Decimal("2006.75")
