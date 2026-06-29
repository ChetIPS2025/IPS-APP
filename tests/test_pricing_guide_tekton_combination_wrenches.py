"""Pricing Guide — TEKTON combination wrench seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_tekton_combination_wrenches import (
    COMBINATION_WRENCHES_SUBCATEGORY,
    HAND_TOOLS_CATEGORY,
    HAND_TOOL_UNIT,
    TEKTON_COMBINATION_WRENCH_SOURCE_ROW_COUNT,
    TEKTON_MANUFACTURER,
    tekton_combination_wrench_catalog_items,
)


def test_tekton_combination_wrench_source_and_catalog_counts():
    items = tekton_combination_wrench_catalog_items()
    assert TEKTON_COMBINATION_WRENCH_SOURCE_ROW_COUNT == 6
    assert len(items) == 6


def test_tekton_combination_wrench_category_and_vendor():
    items = tekton_combination_wrench_catalog_items()
    assert all(r["category"] == HAND_TOOLS_CATEGORY for r in items)
    assert all(r["subcategory"] == COMBINATION_WRENCHES_SUBCATEGORY for r in items)
    assert all(r["vendor"] == TEKTON_MANUFACTURER for r in items)
    assert all(r["unit"] == HAND_TOOL_UNIT for r in items)
    assert all(r["is_active"] is True for r in items)


def test_tekton_combination_wrench_part_numbers_and_descriptions():
    items = tekton_combination_wrench_catalog_items()
    by_part = {r["item_code"]: r for r in items}
    assert set(by_part) == {
        "WCB23043",
        "WCB23046",
        "WCB23050",
        "18268",
        "WCB23041",
        "WCB23049",
    }

    row_43 = by_part["WCB23043"]
    assert row_43["description"] == 'TEKTON 1-11/16" Combination Wrench'
    assert row_43["model_number"] == "WCB23043"
    assert row_43["sku"] == "WCB23043"
    assert row_43["default_cost"] == 62.00
    assert row_43["default_sell_price"] == 62.00

    row_46 = by_part["WCB23046"]
    assert row_46["description"] == 'TEKTON 1-13/16" Combination Wrench'
    assert row_46["default_cost"] == 75.00

    row_50 = by_part["WCB23050"]
    assert row_50["description"] == 'TEKTON 2" Combination Wrench'
    assert row_50["default_cost"] == 90.00

    row_18268 = by_part["18268"]
    assert row_18268["description"] == '1-1/8" Combination Wrench'
    assert row_18268["model_number"] == "18268"
    assert row_18268["default_cost"] == 21.00

    row_41 = by_part["WCB23041"]
    assert row_41["description"] == '1-5/8" Combination Wrench'
    assert row_41["default_cost"] == 59.95

    row_49 = by_part["WCB23049"]
    assert row_49["description"] == '1-15/16" Combination Wrench'
    assert row_49["default_cost"] == 90.00


def test_tekton_combination_wrench_prices_use_decimal_precision():
    items = tekton_combination_wrench_catalog_items()
    prices = {r["item_code"]: Decimal(str(r["default_cost"])) for r in items}
    assert prices["WCB23043"] == Decimal("62.00")
    assert prices["WCB23046"] == Decimal("75.00")
    assert prices["WCB23050"] == Decimal("90.00")
    assert prices["18268"] == Decimal("21.00")
    assert prices["WCB23041"] == Decimal("59.95")
    assert prices["WCB23049"] == Decimal("90.00")


def test_tekton_combination_wrench_item_codes_are_unique():
    items = tekton_combination_wrench_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))
