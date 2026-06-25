"""Pricing Guide — socket weld fittings seed data."""

from __future__ import annotations

from decimal import Decimal

from app.data.pricing_guide_socket_weld_fittings import (
    SOCKET_WELD_CONNECTION_TYPE,
    SOCKET_WELD_FITTINGS_CATEGORY,
    SOCKET_WELD_FITTINGS_SOURCE_ROW_COUNT,
    SOCKET_WELD_FITTINGS_UNIT,
    socket_weld_fittings_active_catalog_items,
    socket_weld_fittings_catalog_items,
    socket_weld_fittings_requires_price_review,
)


def test_socket_weld_fittings_source_and_catalog_counts():
    items = socket_weld_fittings_catalog_items()
    assert SOCKET_WELD_FITTINGS_SOURCE_ROW_COUNT == 29
    assert len(items) == 29
    assert len(socket_weld_fittings_active_catalog_items()) == 28


def test_socket_weld_fittings_material_groups():
    items = socket_weld_fittings_catalog_items()
    ss = [r for r in items if r["subcategory"] == "Stainless Steel"]
    cs = [r for r in items if r["subcategory"] == "Carbon Steel"]
    assert len(ss) == 10
    assert len(cs) == 19
    assert {r["category"] for r in items} == {SOCKET_WELD_FITTINGS_CATEGORY}
    assert all(r["unit"] == SOCKET_WELD_FITTINGS_UNIT for r in items)
    assert all(r["connection_type"] == SOCKET_WELD_CONNECTION_TYPE for r in items)


def test_socket_weld_fittings_stainless_grades_and_pressure_class():
    items = socket_weld_fittings_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    tee_304 = by_code["SWF-SS304-TEE-1-3000"]
    assert tee_304["material_grade"] == "304 Stainless Steel"
    assert tee_304["pressure_class"] == "3000"
    assert tee_304["default_cost"] == 18.20

    tee_316_no_pc = by_code["SWF-SS316-TEE-1-12"]
    assert tee_316_no_pc["material_grade"] == "316 Stainless Steel"
    assert tee_316_no_pc["pressure_class"] == ""
    assert tee_316_no_pc["default_cost"] == 51.91


def test_socket_weld_fittings_fitting_types():
    items = socket_weld_fittings_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["SWF-SS304-TEE-1-3000"]["product_type"] == "Tee"
    assert by_code["SWF-SS304-EL90-1-3000"]["product_type"] == "90-Degree Elbow"
    assert by_code["SWF-SS304-CAP-1-3000"]["product_type"] == "Cap"
    assert by_code["SWF-SS316-CPL-1"]["product_type"] == "Coupling"
    assert by_code["SWF-CS-SOCK-4X1-3000"]["product_type"] == "Sockolet"


def test_socket_weld_fittings_sockolet_run_and_branch_sizes():
    items = socket_weld_fittings_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    sock = by_code["SWF-CS-SOCK-10X1-12-3000"]
    assert sock["pipe_size"] == '10"'
    assert sock["dash_size"] == '1-1/2"'
    assert sock["pressure_class"] == "3000"
    assert sock["default_cost"] == 23.92
    assert sock["description"] == '10"X1-1/2" SOCKOLET, #3000, S.W. (C.S.)'


def test_socket_weld_fittings_collar_coupling_aliases():
    items = socket_weld_fittings_catalog_items()
    row = next(r for r in items if r["item_code"] == "SWF-SS316-CPL-1")
    assert row["description"] == '1" COLLAR/COUPLING S.W. (316 S.S.)'
    assert row["product_type"] == "Coupling"
    assert "Collar" in row["notes"]
    assert "Coupling" in row["notes"]


def test_socket_weld_fittings_missing_price_inactive():
    items = socket_weld_fittings_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    missing = by_code["SWF-SS316-TEE-2"]
    assert missing["description"] == '2" S.W. TEE (316 S.S.)'
    assert missing["is_active"] is False
    assert "default_cost" not in missing
    assert "price not supplied" in missing["notes"].lower()
    review = socket_weld_fittings_requires_price_review()
    assert len(review) == 1
    assert review[0]["item_code"] == "SWF-SS316-TEE-2"


def test_socket_weld_fittings_carbon_steel_exact_prices():
    items = socket_weld_fittings_catalog_items()
    by_code = {r["item_code"]: r for r in items}
    assert by_code["SWF-CS-TEE-1-3000"]["default_cost"] == 11.47
    assert by_code["SWF-CS-EL90-2-3000"]["default_cost"] == 24.48
    assert by_code["SWF-CS-SOCK-6X2-3000"]["default_cost"] == 27.18


def test_socket_weld_fittings_item_codes_are_unique():
    items = socket_weld_fittings_catalog_items()
    codes = [r["item_code"] for r in items]
    assert len(codes) == len(set(codes))


def test_socket_weld_fittings_prices_use_decimal_precision():
    items = socket_weld_fittings_catalog_items()
    row = next(r for r in items if r["item_code"] == "SWF-SS304-EL90-12-3000")
    assert Decimal(str(row["default_cost"])) == Decimal("28.18")
