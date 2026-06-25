"""Pricing Guide — I-beam materials seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_i_beam import (
    I_BEAM_CATEGORY,
    I_BEAM_SOURCE_ROW_COUNT,
    I_BEAM_UNIT,
    i_beam_alias_pairs,
    i_beam_catalog_items,
    i_beam_price_review_items,
)


def test_i_beam_source_and_catalog_counts():
    items = i_beam_catalog_items()
    assert I_BEAM_SOURCE_ROW_COUNT == 17
    assert len(items) == 17


def test_i_beam_category_and_material_group():
    items = i_beam_catalog_items()
    assert {r["category"] for r in items} == {I_BEAM_CATEGORY}
    assert all(r["subcategory"] == "Carbon Steel" for r in items)
    assert all(r["material_grade"] == "Carbon Steel" for r in items)
    assert all(r["unit"] == I_BEAM_UNIT for r in items)
    assert all(r["is_active"] is True for r in items)


def test_i_beam_w_shape_designations_and_prices():
    items = i_beam_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["IBEAM-CS-W8X28-IBEAM"]["description"] == "W8x28 (C.S.) I-BEAM"
    assert by_code["IBEAM-CS-W8X28-IBEAM"]["default_cost"] == 609.40
    assert by_code["IBEAM-CS-W12X45-GALV-BEAM"]["description"] == "W12X45 GALVANIZED BEAM"
    assert by_code["IBEAM-CS-W12X45-GALV-BEAM"]["default_cost"] == 1668.45


def test_i_beam_beam_ibeam_alias_pairs_separate_records():
    items = i_beam_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    w6_beam = by_code["IBEAM-CS-W6X20-BEAM"]
    w6_ibeam = by_code["IBEAM-CS-W6X20-IBEAM"]
    assert w6_beam["default_cost"] == w6_ibeam["default_cost"] == 704.60
    assert w6_beam["description"] != w6_ibeam["description"]
    assert "I-BEAM" in w6_beam["notes"]
    w8_beam = by_code["IBEAM-CS-W8X21-BEAM"]
    w8_ibeam = by_code["IBEAM-CS-W8X21-IBEAM"]
    assert w8_beam["default_cost"] == 850.80
    pairs = i_beam_alias_pairs()
    assert len(pairs) == 2


def test_i_beam_galvanized_finish_retained():
    items = i_beam_catalog_items()
    galv = [r for r in items if "Galvanized" in r.get("body_shape", "") or "Galvanized" in r["description"]]
    assert len(galv) == 7
    for row in galv:
        assert row["subcategory"] == "Carbon Steel"
        assert "Finish: Galvanized" in row["notes"]


def test_i_beam_galvanized_t_bar_distinguishable():
    items = i_beam_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    tbar = by_code["IBEAM-CS-W14X9-GALV-TBAR"]
    assert tbar["body_shape"] == "Galvanized T-Bar (Stitch Cut)"
    assert tbar["product_type"] == "T-Bar"
    assert "Stitch Cut" in tbar["notes"]
    assert tbar["default_cost"] == 1200.00


def test_i_beam_unusual_prices_flagged_but_active():
    items = i_beam_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    low1 = by_code["IBEAM-CS-W10X39-BEAM"]
    low2 = by_code["IBEAM-CS-W8X35-IBEAM"]
    assert low1["default_cost"] == 39.00
    assert low2["default_cost"] == 39.38
    assert low1["is_active"] is True
    assert low2["is_active"] is True
    assert "verify catalog price" in low1["notes"].lower()
    review = i_beam_price_review_items()
    assert len(review) == 2


def test_i_beam_item_codes_are_unique():
    items = i_beam_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_i_beam_prices_use_decimal_precision():
    items = i_beam_catalog_items()
    row = next(r for r in items if r["item_code"] == "IBEAM-CS-W8X35-GALV-BEAM")
    assert Decimal(str(row["default_cost"])) == Decimal("2490.56")
