"""Pricing Guide — angle iron materials seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_angle_iron import (
    ANGLE_IRON_CATEGORY,
    ANGLE_IRON_SOURCE_ROW_COUNT,
    ANGLE_IRON_UNIT,
    angle_iron_active_catalog_items,
    angle_iron_catalog_items,
    angle_iron_requires_price_review,
)


def test_angle_iron_source_and_catalog_counts():
    items = angle_iron_catalog_items()
    assert ANGLE_IRON_SOURCE_ROW_COUNT == 17
    assert len(items) == 17
    assert len(angle_iron_active_catalog_items()) == 16


def test_angle_iron_category_and_material_groups():
    items = angle_iron_catalog_items()
    assert {r["category"] for r in items} == {ANGLE_IRON_CATEGORY}
    cs = [r for r in items if r["subcategory"] == "Carbon Steel"]
    al = [r for r in items if r["subcategory"] == "Aluminum"]
    ss = [r for r in items if r["subcategory"] == "Stainless Steel"]
    assert len(cs) == 10
    assert len(al) == 5
    assert len(ss) == 2
    assert all(r["unit"] == ANGLE_IRON_UNIT for r in items)


def test_angle_iron_missing_price_inactive_without_catalog_price():
    items = angle_iron_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    missing = by_code["ANGL-CS-L4X2-14"]
    assert missing["description"] == 'L4"x2"x1/4" ANGLE (C.S.)'
    assert missing["is_active"] is False
    assert "default_cost" not in missing
    assert "price not supplied" in missing["notes"].lower()
    review = angle_iron_requires_price_review()
    assert len(review) == 1
    assert review[0]["item_code"] == "ANGL-CS-L4X2-14"


def test_angle_iron_galvanized_retains_cs_group_and_finish_note():
    items = angle_iron_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    galv = by_code["ANGL-CS-L2X2-38-GALV"]
    assert galv["subcategory"] == "Carbon Steel"
    assert galv["material_grade"] == "Carbon Steel"
    assert galv["body_shape"] == "Angle"
    assert "Finish: Galvanized" in galv["notes"]
    assert galv["default_cost"] == 84.98


def test_angle_iron_aluminum_t_beam_distinguishable_from_angle():
    items = angle_iron_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    tbeam = by_code["ANGL-AL-TBEAM-2X2-14"]
    assert tbeam["body_shape"] == "T-Beam"
    assert tbeam["product_type"] == "T-Beam"
    assert tbeam["description"] == '2"X2"X1/4" STRUCTURAL T-BEAM (ALUMINUM)'
    assert "STRUCTUAL T-BEAM(ALUMINUM)" in tbeam["notes"]
    assert "ANGLE" not in tbeam["description"].upper() or "T-BEAM" in tbeam["description"].upper()
    angle = by_code["ANGL-AL-L2X2-14"]
    assert angle["body_shape"] == "Angle"
    assert angle["product_type"] == "Angle Iron"


def test_angle_iron_stainless_316_grade_and_prices():
    items = angle_iron_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    ss1 = by_code["ANGL-SS-L1X1-18-316"]
    assert ss1["material_grade"] == "316 Stainless Steel"
    assert ss1["default_cost"] == 86.34
    ss2 = by_code["ANGL-SS-L3X3-38-316"]
    assert ss2["default_cost"] == 747.90


def test_angle_iron_exact_cs_prices():
    items = angle_iron_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["ANGL-CS-L3X3-12"]["default_cost"] == 159.53
    assert by_code["ANGL-CS-L4X3-12-516"]["default_cost"] == 316.66


def test_angle_iron_item_codes_are_unique():
    items = angle_iron_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_angle_iron_prices_use_decimal_precision():
    items = angle_iron_catalog_items()
    row = next(r for r in items if r["item_code"] == "ANGL-AL-L1X1-18")
    assert Decimal(str(row["default_cost"])) == Decimal("28.35")
