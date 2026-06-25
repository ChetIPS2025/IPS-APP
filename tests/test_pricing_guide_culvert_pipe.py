"""Pricing Guide — culvert pipe seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_culvert_pipe import (
    CULVERT_PIPE_CATEGORY,
    CULVERT_PIPE_SOURCE_ROW_COUNT,
    CULVERT_PIPE_UNIT,
    culvert_pipe_catalog_items,
)


def test_culvert_pipe_source_and_catalog_counts():
    items = culvert_pipe_catalog_items()
    assert CULVERT_PIPE_SOURCE_ROW_COUNT == 2
    assert len(items) == 2


def test_culvert_pipe_category_and_no_material_group():
    items = culvert_pipe_catalog_items()
    assert {r["category"] for r in items} == {CULVERT_PIPE_CATEGORY}
    assert all(r["subcategory"] == "" for r in items)
    assert all(r["material_grade"] == "" for r in items)
    assert all(r["unit"] == CULVERT_PIPE_UNIT for r in items)
    assert all(r["is_active"] is True for r in items)


def test_culvert_pipe_exact_prices_and_descriptions():
    items = culvert_pipe_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    c30 = by_code["CULV-30-20"]
    assert c30["description"] == '30" X 20\' BLACK CORRIGATED CULVERT'
    assert c30["default_cost"] == 945.00
    c18 = by_code["CULV-18-20"]
    assert c18["description"] == '18" X 20\' BLACK CORRIGATED CULVERT'
    assert c18["default_cost"] == 405.00


def test_culvert_pipe_diameter_length_color_and_construction():
    items = culvert_pipe_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    c30 = by_code["CULV-30-20"]
    assert c30["pipe_size"] == '30"'
    assert c30["connection_type"] == "20'"
    assert c30["body_shape"] == "Corrugated"
    assert c30["product_type"] == "Culvert"
    assert "Color: Black" in c30["notes"]
    assert "Material not specified" in c30["notes"]


def test_culvert_pipe_item_codes_are_unique():
    items = culvert_pipe_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_culvert_pipe_prices_use_decimal_precision():
    items = culvert_pipe_catalog_items()
    row = next(r for r in items if r["item_code"] == "CULV-18-20")
    assert Decimal(str(row["default_cost"])) == Decimal("405.00")
