"""Pricing Guide — flat bar materials seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_flat_bar import (
    FLAT_BAR_CATEGORY,
    FLAT_BAR_SOURCE_ROW_COUNT,
    FLAT_BAR_UNIT,
    flat_bar_catalog_items,
    flat_bar_duplicate_price_review,
)


def test_flat_bar_source_and_catalog_counts():
    items = flat_bar_catalog_items()
    assert FLAT_BAR_SOURCE_ROW_COUNT == 28
    assert len(items) == 26


def test_flat_bar_category_and_material_groups():
    items = flat_bar_catalog_items()
    assert {r["category"] for r in items} == {FLAT_BAR_CATEGORY}
    subcategories = {r["subcategory"] for r in items}
    assert subcategories == {"Stainless Steel", "Aluminum", "Carbon Steel"}
    assert all(r["unit"] == FLAT_BAR_UNIT for r in items)
    assert all(r["item_type"] == "Material" for r in items)
    assert all(r["is_active"] is True for r in items)


def test_flat_bar_stainless_prices_and_descriptions():
    items = flat_bar_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    ss_316x4 = by_code["FLATBAR-SS-316X4-304"]
    assert ss_316x4["description"] == '3/16" X 4" (304) S.S. FLAT BAR'
    assert ss_316x4["default_cost"] == 143.51
    assert ss_316x4["material_grade"] == "304 Stainless Steel"
    assert by_code["FLATBAR-SS-14X6-316"]["default_cost"] == 441.98


def test_flat_bar_aluminum_uses_us_spelling_in_subcategory():
    items = flat_bar_catalog_items()
    al = next(r for r in items if r["item_code"] == "FLATBAR-AL-14X1")
    assert al["subcategory"] == "Aluminum"
    assert al["description"] == '1/4" X 1" (ALUMINIUM) FLAT BAR'
    assert al["material_grade"] == "Aluminum"


def test_flat_bar_duplicate_prices_preserved_in_notes():
    items = flat_bar_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    ss_dup = by_code["FLATBAR-SS-316X4-304"]
    assert ss_dup["default_cost"] == 143.51
    assert "128.80" in ss_dup["notes"]
    assert "duplicate source record" in ss_dup["notes"].lower()

    al_dup = by_code["FLATBAR-AL-14X2"]
    assert al_dup["default_cost"] == 46.38
    assert "42.76" in al_dup["notes"]

    review = flat_bar_duplicate_price_review()
    assert len(review) == 2
    review_codes = {r["item_code"] for r in review}
    assert review_codes == {"FLATBAR-SS-316X4-304", "FLATBAR-AL-14X2"}


def test_flat_bar_item_codes_are_unique():
    items = flat_bar_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_flat_bar_prices_use_decimal_precision():
    items = flat_bar_catalog_items()
    cs_38x2_half = next(r for r in items if r["item_code"] == "FLATBAR-CS-38X2-12")
    assert Decimal(str(cs_38x2_half["default_cost"])) == Decimal("60.00")
