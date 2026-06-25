"""Pricing Guide — solid round bar materials seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_solid_round_bar import (
    SOLID_ROUND_BAR_CATEGORY,
    SOLID_ROUND_BAR_SOURCE_ROW_COUNT,
    SOLID_ROUND_BAR_UNIT,
    solid_round_bar_catalog_items,
)


def test_solid_round_bar_source_and_catalog_counts():
    items = solid_round_bar_catalog_items()
    assert SOLID_ROUND_BAR_SOURCE_ROW_COUNT == 9
    assert len(items) == 9


def test_solid_round_bar_category_and_material_groups():
    items = solid_round_bar_catalog_items()
    assert {r["category"] for r in items} == {SOLID_ROUND_BAR_CATEGORY}
    al = [r for r in items if r["subcategory"] == "Aluminum"]
    cs = [r for r in items if r["subcategory"] == "Carbon Steel"]
    ss = [r for r in items if r["subcategory"] == "Stainless Steel"]
    assert len(al) == 5
    assert len(cs) == 1
    assert len(ss) == 3
    assert all(r["unit"] == SOLID_ROUND_BAR_UNIT for r in items)
    assert all(r["is_active"] is True for r in items)


def test_solid_round_bar_diameters_and_prices():
    items = solid_round_bar_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["SRBAR-AL-14"]["pipe_size"] == '1/4"'
    assert by_code["SRBAR-AL-14"]["default_cost"] == 3.25
    assert by_code["SRBAR-CS-1-716"]["pipe_size"] == '1-7/16"'
    assert by_code["SRBAR-CS-1-716"]["default_cost"] == 130.24


def test_solid_round_bar_stainless_304_grade():
    items = solid_round_bar_catalog_items()
    ss = [r for r in items if r["subcategory"] == "Stainless Steel"]
    assert len(ss) == 3
    for row in ss:
        assert row["material_grade"] == "304 Stainless Steel"
    by_code = {r["item_code"]: r for r in items}
    assert by_code["SRBAR-SS-58-304"]["default_cost"] == 53.20


def test_solid_round_bar_source_descriptions_preserved_in_notes():
    items = solid_round_bar_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    al12 = by_code["SRBAR-AL-12"]
    assert al12["description"] == '1/2" SOLID ROUND BAR (ALUMINUM)'
    assert '1/2" SOLID ROUND BAR(ALUMINUM)' in al12["notes"]


def test_solid_round_bar_item_codes_are_unique():
    items = solid_round_bar_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_solid_round_bar_prices_use_decimal_precision():
    items = solid_round_bar_catalog_items()
    row = next(r for r in items if r["item_code"] == "SRBAR-AL-1")
    assert Decimal(str(row["default_cost"])) == Decimal("85.63")
