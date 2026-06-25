"""Pricing Guide — C-channel materials seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_c_channel import (
    C_CHANNEL_CATEGORY,
    C_CHANNEL_SOURCE_ROW_COUNT,
    C_CHANNEL_UNIT,
    c_channel_catalog_items,
    c_channel_duplicate_price_review,
)


def test_c_channel_source_and_catalog_counts():
    items = c_channel_catalog_items()
    assert C_CHANNEL_SOURCE_ROW_COUNT == 10
    assert len(items) == 9


def test_c_channel_category_and_material_groups():
    items = c_channel_catalog_items()
    assert {r["category"] for r in items} == {C_CHANNEL_CATEGORY}
    subcategories = {r["subcategory"] for r in items}
    assert subcategories == {"Carbon Steel", "Aluminum"}
    assert all(r["unit"] == C_CHANNEL_UNIT for r in items)
    assert all(r["is_active"] is True for r in items)


def test_c_channel_c_and_mc_shapes_distinguishable():
    items = c_channel_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["CCH-CS-C12X25"]["body_shape"] == "C"
    assert by_code["CCH-CS-MC8X21-4"]["body_shape"] == "MC"
    assert by_code["CCH-CS-MC8X21-4"]["description"] == "MC8X21.4 (C.S.) CHANNEL"
    assert by_code["CCH-CS-MC6X-18"]["description"] == "MC6x#18 (C.S.) CHANNEL"
    assert "#" in by_code["CCH-CS-MC6X-18"]["description"]


def test_c_channel_exact_prices_and_descriptions():
    items = c_channel_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["CCH-CS-C12X25"]["default_cost"] == 962.50
    assert by_code["CCH-CS-C8X11-5"]["default_cost"] == 183.05
    assert by_code["CCH-CS-C6X8-2"]["description"] == "C6x8.2 C.S. Channel"
    assert by_code["CCH-AL-3IN"]["default_cost"] == 130.68
    assert by_code["CCH-AL-3IN"]["subcategory"] == "Aluminum"


def test_c_channel_duplicate_price_preserved_in_notes():
    items = c_channel_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    dup = by_code["CCH-CS-C12X25"]
    assert dup["default_cost"] == 962.50
    assert "495.38" in dup["notes"]
    review = c_channel_duplicate_price_review()
    assert len(review) == 1
    assert review[0]["item_code"] == "CCH-CS-C12X25"


def test_c_channel_item_codes_are_unique():
    items = c_channel_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_c_channel_prices_use_decimal_precision():
    items = c_channel_catalog_items()
    row = next(r for r in items if r["item_code"] == "CCH-CS-C8X13-75")
    assert Decimal(str(row["default_cost"])) == Decimal("211.99")
