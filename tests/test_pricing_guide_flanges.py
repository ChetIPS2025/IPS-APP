"""Pricing Guide — flanges seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_flanges import (
    FLANGES_CATEGORY,
    FLANGES_SOURCE_ROW_COUNT,
    FLANGES_UNIT,
    flanges_active_catalog_items,
    flanges_catalog_items,
    flanges_duplicate_source_review,
    flanges_requires_price_review,
)


def test_flanges_source_and_catalog_counts():
    items = flanges_catalog_items()
    assert FLANGES_SOURCE_ROW_COUNT == 40
    assert len(items) == 33
    assert len(flanges_active_catalog_items()) == 32


def test_flanges_material_groups():
    items = flanges_catalog_items()
    ss = [r for r in items if r["subcategory"] == "Stainless Steel"]
    cs = [r for r in items if r["subcategory"] == "Carbon Steel"]
    assert len(ss) == 18
    assert len(cs) == 15
    assert sum(r.get("_source_row_count", 1) for r in items) == 40
    assert {r["category"] for r in items} == {FLANGES_CATEGORY}
    assert all(r["unit"] == FLANGES_UNIT for r in items)


def test_flanges_stainless_grades_and_lightweight():
    items = flanges_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["FLG-SS316-SO-1-150"]["material_grade"] == "316 Stainless Steel"
    assert by_code["FLG-SS304-SO-1-150"]["material_grade"] == "304 Stainless Steel"
    lw = by_code["FLG-SS-LW-SO-42-150"]
    assert lw["product_type"] == "Lightweight Slip On"
    assert lw["material_grade"] == ""
    assert lw["default_cost"] == 1156.25
    assert "Grade not specified" in lw["notes"]


def test_flanges_flange_types():
    items = flanges_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["FLG-SS304-SO-1-150"]["product_type"] == "Slip On"
    assert by_code["FLG-SS304-BLIND-1-300"]["product_type"] == "Blind"
    assert by_code["FLG-SS304-THR-2-150"]["product_type"] == "Threaded"
    assert by_code["FLG-CS-SW-1-150-SCH80"]["product_type"] == "Socket Weld"
    assert by_code["FLG-CS-WN-4-150-SCH40"]["product_type"] == "Weld Neck"


def test_flanges_pressure_class_face_and_schedule():
    items = flanges_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    sw = by_code["FLG-CS-SW-2-150-SCH80"]
    assert sw["pressure_class"] == "150"
    assert sw["body_shape"] == "Raised Face"
    assert sw["connection_type"] == "SCH80"
    assert sw["default_cost"] == 16.50

    wn_no_sched = by_code["FLG-CS-WN-8-150"]
    wn_sch20 = by_code["FLG-CS-WN-8-150-SCH20"]
    assert wn_no_sched["connection_type"] == ""
    assert wn_sch20["connection_type"] == "SCH20"
    assert wn_no_sched["default_cost"] == 94.49
    assert wn_sch20["default_cost"] == 114.75


def test_flanges_duplicate_descriptions_deduplicated():
    items = flanges_catalog_items()
    descriptions = [r["description"] for r in items]
    assert len(descriptions) == len(set(descriptions))
    review = flanges_duplicate_source_review()
    assert len(review) == 7
    so_2 = next(r for r in items if r["item_code"] == "FLG-SS304-SO-2-150")
    assert so_2["default_cost"] == 39.12
    assert so_2["_source_row_count"] == 2
    assert "source row 16" in so_2["notes"].lower()


def test_flanges_missing_price_threaded_inactive():
    items = flanges_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    threaded = by_code["FLG-SS304-THR-2-150"]
    assert threaded["description"] == '2" #150 FLANGE, THREADED, (304S.S.)'
    assert threaded["is_active"] is False
    assert "default_cost" not in threaded
    assert len(flanges_requires_price_review()) == 1


def test_flanges_exact_prices():
    items = flanges_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["FLG-SS304-BLIND-12-150"]["default_cost"] == 23.50
    assert by_code["FLG-CS-BLIND-6-150"]["default_cost"] == 53.46
    assert by_code["FLG-CS-WN-12-150-SCH20"]["default_cost"] == 263.25


def test_flanges_item_codes_are_unique():
    items = flanges_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_flanges_prices_use_decimal_precision():
    items = flanges_catalog_items()
    row = next(r for r in items if r["item_code"] == "FLG-SS304-SO-12-300")
    assert Decimal(str(row["default_cost"])) == Decimal("30.00")
