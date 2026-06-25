"""Pricing Guide — valves and Y-strainers seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_valves import (
    VALVES_CATEGORY,
    VALVES_SOURCE_ROW_COUNT,
    VALVES_UNIT,
    valves_active_catalog_items,
    valves_catalog_items,
)


def test_valves_source_and_catalog_counts():
    items = valves_catalog_items()
    assert VALVES_SOURCE_ROW_COUNT == 23
    assert len(items) == 23
    assert len(valves_active_catalog_items()) == 23


def test_valves_material_groups():
    items = valves_catalog_items()
    ss = [r for r in items if r["subcategory"] == "Stainless Steel"]
    cs = [r for r in items if r["subcategory"] == "Carbon Steel"]
    unsp = [r for r in items if r["subcategory"] == "Unspecified"]
    assert len(ss) == 9
    assert len(cs) == 4
    assert len(unsp) == 10
    assert all(r["category"] == VALVES_CATEGORY for r in items)
    assert all(r["unit"] == VALVES_UNIT for r in items)


def test_valves_types():
    items = valves_catalog_items()
    by_type: dict[str, int] = {}
    for row in items:
        by_type[row["product_type"]] = by_type.get(row["product_type"], 0) + 1
    assert by_type["Ball Valve"] == 7
    assert by_type["Check Valve"] == 4
    assert by_type["Gate Valve"] == 9
    assert by_type["Globe Valve"] == 2
    assert by_type["Y-Strainer"] == 1


def test_valves_stainless_grades_not_inferred():
    items = valves_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["VAL-SS316-BV-12-THR-2000"]["material_grade"] == "316 Stainless Steel"
    assert by_code["VAL-SS304-BV-1-FLG-150-FB"]["material_grade"] == "304 Stainless Steel"
    assert by_code["VAL-SS-BV-1-FLG-150"]["material_grade"] == ""
    assert by_code["VAL-SS-BV-2-SW"]["material_grade"] == ""


def test_valves_connection_types_not_inferred_from_section():
    items = valves_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["VAL-SS316-BV-12-THR-2000"]["connection_type"] == "Threaded"
    assert by_code["VAL-CS-CV-1-12-SW-800-FP"]["connection_type"] == "Socket Weld"
    assert by_code["VAL-SS-GV-3-150-RF-FE"]["connection_type"] == ""
    assert by_code["VAL-SS-YS-3-150-RF-FE"]["product_type"] == "Y-Strainer"


def test_valves_pressure_designations_exact():
    items = valves_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["VAL-SS316-BV-12-THR-2000"]["pressure_class"] == "#2000"
    assert by_code["VAL-CS-GV-1-12-SW-800-FP"]["pressure_class"] == "800lb"
    assert by_code["VAL-CS-GV-1-12-SW-1500-VELAN"]["pressure_class"] == "1500lb"
    assert by_code["VAL-SS304-BV-2-FLG-300-FB"]["pressure_class"] == "#300"


def test_valves_api_standards_and_features():
    items = valves_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    api600 = by_code["VAL-UNSP-GV-6-FLG-150-API600"]
    assert api600["dash_size"] == "API 600"
    assert "Solid Wedge" in api600["notes"] or api600["body_shape"] == "Raised Face"
    api608 = by_code["VAL-UNSP-BV-1-FLG-150-API608"]
    assert api608["dash_size"] == "API 608"
    assert "Anti-Blowout" in api608["notes"]
    assert "Antistatic" in api608["notes"]


def test_valves_unspecified_material_records():
    items = valves_catalog_items()
    unsp = [r for r in items if r["subcategory"] == "Unspecified"]
    assert len(unsp) == 10
    for row in unsp:
        assert row["material_grade"] == ""
        assert "Material not specified" in row["notes"]


def test_valves_velan_manufacturer():
    items = valves_catalog_items()
    velan = next(r for r in items if r["item_code"] == "VAL-CS-GV-1-12-SW-1500-VELAN")
    assert velan["vendor"] == "Velan"
    assert "Manufacturer: Velan" in velan["notes"]
    assert velan["default_cost"] == 594.00


def test_valves_exact_prices():
    items = valves_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["VAL-SS-CV-2-FLG-150-SWING"]["default_cost"] == 333.38
    assert by_code["VAL-UNSP-GV-12-FLG-150-API600"]["default_cost"] == 2395.80
    assert by_code["VAL-SS-YS-3-150-RF-FE"]["default_cost"] == 924.75


def test_valves_item_codes_are_unique():
    items = valves_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_valves_prices_use_decimal_precision():
    items = valves_catalog_items()
    row = next(r for r in items if r["item_code"] == "VAL-UNSP-GV-8-FLG-150-API600")
    assert Decimal(str(row["default_cost"])) == Decimal("1081.80")
