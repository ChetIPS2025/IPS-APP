"""Pricing Guide — square and rectangular tubing seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_square_tubing import (
    SQUARE_TUBING_CATEGORY,
    SQUARE_TUBING_SOURCE_ROW_COUNT,
    SQUARE_TUBING_UNIT,
    square_tubing_catalog_items,
)


def test_square_tubing_source_and_catalog_counts():
    items = square_tubing_catalog_items()
    assert SQUARE_TUBING_SOURCE_ROW_COUNT == 14
    assert len(items) == 14


def test_square_tubing_category_material_groups_and_shapes():
    items = square_tubing_catalog_items()
    assert {r["category"] for r in items} == {SQUARE_TUBING_CATEGORY}
    assert {r["subcategory"] for r in items} == {"Carbon Steel", "Aluminum", "Stainless Steel"}
    cs = [r for r in items if r["subcategory"] == "Carbon Steel"]
    al = [r for r in items if r["subcategory"] == "Aluminum"]
    ss = [r for r in items if r["subcategory"] == "Stainless Steel"]
    assert len(cs) == 8
    assert len(al) == 5
    assert len(ss) == 1
    shapes = {r["body_shape"] for r in items}
    assert shapes == {"Square", "Rectangular"}
    assert all(r["unit"] == SQUARE_TUBING_UNIT for r in items)
    assert all(r["is_active"] is True for r in items)


def test_square_tubing_ts_prefix_and_exact_descriptions():
    items = square_tubing_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    ts4 = by_code["SQTB-CS-TS-4X4-38"]
    assert ts4["description"] == 'TS4"X4"X3/8" SQUARE TUBING (CS)'
    assert ts4["default_cost"] == 331.24
    assert ts4["body_shape"] == "Square"
    ts3 = by_code["SQTB-CS-TS-3X3-14"]
    assert ts3["description"].startswith("TS3")


def test_square_tubing_rectangular_distinguishable_from_square():
    items = square_tubing_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    rect = by_code["SQTB-CS-2X6-316-RECT"]
    assert rect["body_shape"] == "Rectangular"
    assert "RECTANGULAR" in rect["description"]
    sq = by_code["SQTB-CS-2X2-18"]
    assert sq["body_shape"] == "Square"
    assert "SQUARE" in sq["description"]


def test_square_tubing_exact_prices():
    items = square_tubing_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["SQTB-AL-2X2-14"]["default_cost"] == 157.91
    assert by_code["SQTB-SS-1X1-18"]["default_cost"] == 216.00
    assert by_code["SQTB-CS-2X3-316-RECT"]["default_cost"] == 172.80


def test_square_tubing_aluminum_uses_us_spelling_in_subcategory():
    items = square_tubing_catalog_items()
    al = next(r for r in items if r["item_code"] == "SQTB-AL-2X2-18")
    assert al["subcategory"] == "Aluminum"
    assert "ALUMINIUM" in al["description"]


def test_square_tubing_item_codes_are_unique():
    items = square_tubing_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_square_tubing_prices_use_decimal_precision():
    items = square_tubing_catalog_items()
    row = next(r for r in items if r["item_code"] == "SQTB-CS-2X4-18-RECT")
    assert Decimal(str(row["default_cost"])) == Decimal("156.73")
