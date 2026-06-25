"""Pricing Guide — pipe materials seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_pipe import (
    PIPE_CATEGORY,
    PIPE_SOURCE_ROW_COUNT,
    PIPE_UNIT,
    pipe_active_catalog_items,
    pipe_catalog_items,
    pipe_duplicate_price_review,
    pipe_requires_price_review,
)


def test_pipe_source_and_catalog_counts():
    items = pipe_catalog_items()
    assert PIPE_SOURCE_ROW_COUNT == 39
    assert len(items) == 38
    assert len(pipe_active_catalog_items()) == 34


def test_pipe_category_and_material_groups():
    items = pipe_catalog_items()
    assert {r["category"] for r in items} == {PIPE_CATEGORY}
    subcategories = {r["subcategory"] for r in items}
    assert subcategories == {"Stainless Steel", "Aluminum", "Carbon Steel"}
    assert all(r["unit"] == PIPE_UNIT for r in items)
    assert all(r["item_type"] == "Material" for r in items)


def test_pipe_stainless_schedule_and_prices():
    items = pipe_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    row = by_code["PIPE-SS-24-STD-304"]
    assert row["description"] == '24" PIPE STD WALL (304 S.S.)'
    assert row["pressure_class"] == "STD WALL"
    assert row["default_cost"] == 443.75
    seam = by_code["PIPE-SS-2-SCH40-SEAM-304"]
    assert seam["connection_type"] == "Seamless"
    assert seam["pressure_class"] == "SCH40"


def test_pipe_carbon_steel_exact_2_inch_sch40_price():
    items = pipe_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["PIPE-CS-2-SCH40"]["default_cost"] == 103.95


def test_pipe_large_diameter_cs_stays_in_pipe_category():
    items = pipe_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    large = by_code["PIPE-CS-48-78-10FT"]
    assert large["category"] == PIPE_CATEGORY
    assert large["description"] == '48" X 7/8" X 10\' LONG C.S.'
    assert large["default_cost"] == 6825.75
    wall = by_code["PIPE-CS-42-38WALL"]
    assert wall["category"] == PIPE_CATEGORY
    assert wall["pressure_class"] == "3/8 WALL"


def test_pipe_missing_price_records_inactive_without_catalog_price():
    items = pipe_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    missing_codes = {
        "PIPE-CS-12-SCH40",
        "PIPE-CS-12-SCH80",
        "PIPE-CS-34-SCH40",
        "PIPE-CS-1-SCH40",
    }
    for code in missing_codes:
        row = by_code[code]
        assert row["is_active"] is False
        assert "default_cost" not in row
        assert "price not supplied" in row["notes"].lower()

    review = pipe_requires_price_review()
    assert len(review) == 4
    assert {r["item_code"] for r in review} == missing_codes


def test_pipe_aluminum_duplicate_price_preserved_in_notes():
    items = pipe_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    al_dup = by_code["PIPE-AL-1-SCH40-SEAM"]
    assert al_dup["description"] == '1" PIPE SCH40 SEAMLESS (ALUMINIUM)'
    assert al_dup["default_cost"] == 91.48
    assert "42.18" in al_dup["notes"]
    assert al_dup["subcategory"] == "Aluminum"

    review = pipe_duplicate_price_review()
    assert len(review) == 1
    assert review[0]["item_code"] == "PIPE-AL-1-SCH40-SEAM"


def test_pipe_item_codes_are_unique():
    items = pipe_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_pipe_prices_use_decimal_precision():
    items = pipe_catalog_items()
    cs = next(r for r in items if r["item_code"] == "PIPE-CS-1-12-SCH40")
    assert Decimal(str(cs["default_cost"])) == Decimal("2.65")
