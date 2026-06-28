"""Tests for handwritten material quote import."""

from __future__ import annotations

from decimal import Decimal

from app.data.handwritten_material_quote_source import HANDWRITTEN_MATERIAL_QUOTE_LINES
from app.services.estimate_material_quote_import import (
    build_material_quote_import_bundle,
    build_material_quote_line,
    material_quote_lines_to_estimate_payloads,
)


def test_source_has_ten_rows():
    assert len(HANDWRITTEN_MATERIAL_QUOTE_LINES) == 10


def test_bundle_line_count_and_preliminary_subtotal():
    bundle = build_material_quote_import_bundle(catalog_rows=[])
    assert bundle.source_row_count == 10
    assert len(bundle.lines) == 10
    assert bundle.preliminary_subtotal == Decimal("6244.82")


def test_square_stock_uses_two_pricing_sticks():
    row = HANDWRITTEN_MATERIAL_QUOTE_LINES[2]
    line = build_material_quote_line(row, line_number=3, catalog_rows=[])
    assert line.quantity == Decimal("2")
    assert line.unit == "EA"
    assert line.unit_cost == Decimal("14.24")
    assert line.total_cost == Decimal("28.48")
    assert "Pricing qty: 2 stick" in line.notes


def test_flat_bar_unclear_basis_preserves_line_total_without_multiplying():
    row = HANDWRITTEN_MATERIAL_QUOTE_LINES[4]
    line = build_material_quote_line(row, line_number=5, catalog_rows=[])
    assert line.requires_review is True
    assert line.quantity == Decimal("1")
    assert line.unit_cost == Decimal("67.20")
    assert line.total_cost == Decimal("67.20")
    assert "REVIEW REQUIRED" in line.notes


def test_per_ft_pipe_line_total():
    row = HANDWRITTEN_MATERIAL_QUOTE_LINES[0]
    line = build_material_quote_line(row, line_number=1, catalog_rows=[])
    assert line.quantity == Decimal("20")
    assert line.unit == "FT"
    assert line.unit_cost == Decimal("28.93")
    assert line.total_cost == Decimal("578.60")


def test_separate_316_and_a106_pipe_rows_remain_distinct():
    bundle = build_material_quote_import_bundle(catalog_rows=[])
    line316_first = bundle.lines[0]
    line_a106 = bundle.lines[6]
    line316_second = bundle.lines[9]
    assert "316 SS" in line316_first.description
    assert "A-106" in line_a106.description
    assert line_a106.quantity == Decimal("320")
    assert "316 SS" in line316_second.description
    assert line316_first.line_number != line316_second.line_number


def test_review_flags_include_uncertain_prices():
    bundle = build_material_quote_import_bundle(catalog_rows=[])
    flagged = [line.line_number for line in bundle.lines if line.requires_review]
    assert flagged == [4, 5, 7]


def test_estimate_payloads_have_zero_markup_and_notes():
    bundle = build_material_quote_import_bundle(catalog_rows=[])
    payloads = material_quote_lines_to_estimate_payloads(bundle)
    assert len(payloads) == 10
    assert all(p["markup_percent"] == 0.0 for p in payloads)
    assert all(p["notes"] for p in payloads)
    assert payloads[0]["unit"] == "FT"


def test_catalog_match_when_description_aligns():
    catalog_rows = [
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "description": '3/8" X 3" (C.S.) FLAT BAR',
            "material_grade": "Carbon Steel",
            "category": "Flat Bar",
        }
    ]
    row = HANDWRITTEN_MATERIAL_QUOTE_LINES[4]
    line = build_material_quote_line(row, line_number=5, catalog_rows=catalog_rows)
    assert line.pricing_item_id == "550e8400-e29b-41d4-a716-446655440001"
    assert line.unit_cost == Decimal("67.20")


def test_no_catalog_match_for_unknown_fitting():
    row = HANDWRITTEN_MATERIAL_QUOTE_LINES[1]
    line = build_material_quote_line(row, line_number=2, catalog_rows=[])
    assert line.pricing_item_id is None
