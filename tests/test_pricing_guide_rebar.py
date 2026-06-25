"""Pricing Guide — rebar materials seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_rebar import (
    REBAR_CATEGORY,
    REBAR_SOURCE_ROW_COUNT,
    REBAR_UNIT,
    rebar_active_catalog_items,
    rebar_catalog_items,
    rebar_requires_price_review,
)


def test_rebar_source_and_catalog_counts():
    items = rebar_catalog_items()
    assert REBAR_SOURCE_ROW_COUNT == 3
    assert len(items) == 3
    assert len(rebar_active_catalog_items()) == 1


def test_rebar_category_and_material_group():
    items = rebar_catalog_items()
    assert {r["category"] for r in items} == {REBAR_CATEGORY}
    assert all(r["subcategory"] == "Carbon Steel" for r in items)
    assert all(r["unit"] == REBAR_UNIT for r in items)


def test_rebar_bar_numbers_and_diameters():
    items = rebar_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    r6 = by_code["REBAR-CS-6"]
    assert r6["dash_size"] == "#6"
    assert r6["pipe_size"] == '3/4"'
    assert r6["description"] == '#6 (3/4") REBAR'
    assert r6["default_cost"] == 16.69
    r5 = by_code["REBAR-CS-5"]
    assert r5["dash_size"] == "#5"
    assert r5["pipe_size"] == '5/8"'


def test_rebar_missing_price_records_inactive():
    items = rebar_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    for code in ("REBAR-CS-5", "REBAR-CS-4"):
        row = by_code[code]
        assert row["is_active"] is False
        assert "default_cost" not in row
        assert "price not supplied" in row["notes"].lower()
    review = rebar_requires_price_review()
    assert len(review) == 2
    assert {r["item_code"] for r in review} == {"REBAR-CS-5", "REBAR-CS-4"}


def test_rebar_item_codes_are_unique():
    items = rebar_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_rebar_prices_use_decimal_precision():
    items = rebar_catalog_items()
    row = next(r for r in items if r["item_code"] == "REBAR-CS-6")
    assert Decimal(str(row["default_cost"])) == Decimal("16.69")
