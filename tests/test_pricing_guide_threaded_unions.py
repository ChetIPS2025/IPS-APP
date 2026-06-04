"""Pricing Guide — threaded NPT female 3000 unions seed data."""

from __future__ import annotations

from pathlib import Path

from app.data.pricing_guide_fittings import threaded_npt_female_3000_union_items
from app.services.catalog_import_service import parse_catalog_csv


def test_threaded_union_seed_count_and_materials():
    rows = threaded_npt_female_3000_union_items()
    assert len(rows) == 18
    dash_sizes = sorted({r["dash_size"] for r in rows})
    assert dash_sizes == ["02", "04", "06", "08", "12", "16", "20", "24", "32"]
    for dash in dash_sizes:
        group = [r for r in rows if r["dash_size"] == dash]
        assert len(group) == 2
        grades = {r["material_grade"] for r in group}
        assert grades == {"304 Stainless Steel", "316 Stainless Steel"}


def test_threaded_union_preserves_fraction_pipe_sizes_and_exact_costs():
    rows = threaded_npt_female_3000_union_items()
    by_dash = {r["dash_size"]: r for r in rows if r["material_grade"].startswith("304")}
    assert by_dash["20"]["pipe_size"] == "1 1/4"
    assert by_dash["24"]["pipe_size"] == "1 1/2"
    assert by_dash["02"]["default_cost"] == 73.82
    assert by_dash["32"]["default_cost"] == 436.54
    row316 = next(r for r in rows if r["dash_size"] == "08" and "316" in r["material_grade"])
    assert row316["default_cost"] == 131.35
    assert row316["model_number"] == "4443K694"


def test_threaded_union_csv_parses_dash_as_string():
    csv_path = Path(__file__).resolve().parents[1] / "data" / "pricing_guide" / "unions_threaded_npt_female_3000.csv"
    text = csv_path.read_text(encoding="utf-8")
    parsed = parse_catalog_csv(text)
    assert len(parsed) == 18
    row02 = next(r for r in parsed if r.get("dash_size") == "02" and "304" in r.get("material_grade", ""))
    assert row02["connection_type"] == "NPT Female"
    assert row02["category"] == "Unions"
    assert row02["subcategory"] == "Threaded Unions"
    assert row02["unit_cost"] == 73.82
    assert row02["item_code"] == "UNION-TU-NPTF-02-304SS"
