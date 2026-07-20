"""Dashboard Asset Value breakdown across Equipment, Serialized Tools, and Small Tools."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.asset_value_service import (
    AssetValueBreakdown,
    calculate_asset_value_breakdown,
    compute_asset_value_breakdown,
)
from app.services.dashboard_metrics_service import compute_dashboard_kpis
from app.services.small_hand_tool_service import (
    SmallHandToolsValueSummary,
    get_small_hand_tools_value_summary,
)


def _empty_small_tools() -> SmallHandToolsValueSummary:
    return SmallHandToolsValueSummary(
        total_value=0.0,
        tool_type_count=0,
        total_quantity=0.0,
        missing_value_count=0,
    )


def test_equipment_value_includes_active_and_prefers_purchase_cost():
    assets = [
        {"id": "eq1", "status": "In Service", "purchase_cost": 1000, "current_value": 500},
        {"id": "eq2", "status": "Retired", "purchase_cost": 9000},
        {"id": "eq3", "status": "Active", "replacement_value": 750},
    ]
    breakdown = calculate_asset_value_breakdown(assets, small_tools_summary=_empty_small_tools())
    assert breakdown.equipment_value == 1750.0
    assert breakdown.equipment_count == 2
    assert breakdown.serialized_tools_value == 0.0


def test_serialized_tool_not_counted_as_equipment():
    assets = [
        {
            "id": "ser1",
            "status": "In Service",
            "purchase_cost": 400,
            "is_serialized_tool": True,
            "serial_number": "SN-001",
            "category": "Tool",
        },
        {"id": "eq1", "status": "In Service", "purchase_cost": 100},
    ]
    breakdown = calculate_asset_value_breakdown(assets, small_tools_summary=_empty_small_tools())
    assert breakdown.serialized_tools_value == 400.0
    assert breakdown.equipment_value == 100.0
    assert breakdown.serialized_tools_count == 1
    assert breakdown.equipment_count == 1


def test_small_tools_quantity_times_unit_value(monkeypatch):
    hand_rows = (
        {
            "id": "ht1",
            "tool_name": "Pliers",
            "quantity_on_hand": 3,
            "quantity_expected": 5,
            "unit_value": 12.5,
            "is_active": True,
            "status": "Available",
        },
    )

    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: (hand_rows, ()),
    )
    summary = get_small_hand_tools_value_summary()
    assert summary.total_value == 37.5
    assert summary.tool_type_count == 1
    assert summary.total_quantity == 3.0


def test_small_tools_uses_actual_not_expected_quantity(monkeypatch):
    hand_rows = (
        {
            "id": "ht1",
            "quantity_on_hand": 2,
            "quantity_expected": 10,
            "unit_value": 5,
            "is_active": True,
            "status": "Available",
        },
    )
    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: (hand_rows, ()),
    )
    summary = get_small_hand_tools_value_summary()
    assert summary.total_value == 10.0


def test_small_tools_fractional_quantity_supported(monkeypatch):
    hand_rows = (
        {
            "id": "ht1",
            "quantity_on_hand": 1.5,
            "unit_value": 10,
            "is_active": True,
            "status": "Available",
        },
    )
    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: (hand_rows, ()),
    )
    summary = get_small_hand_tools_value_summary()
    assert summary.total_value == 15.0


def test_small_tools_total_value_fallback_when_unit_value_missing(monkeypatch):
    hand_rows = (
        {
            "id": "ht1",
            "quantity_on_hand": 99,
            "unit_value": 0,
            "total_value": 45,
            "is_active": True,
            "status": "Available",
        },
    )
    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: (hand_rows, ()),
    )
    summary = get_small_hand_tools_value_summary()
    assert summary.total_value == 45.0
    assert summary.missing_value_count == 0


def test_small_tools_missing_unit_value_counts_zero_and_increments_missing(monkeypatch):
    hand_rows = (
        {
            "id": "ht1",
            "quantity_on_hand": 4,
            "unit_value": 0,
            "is_active": True,
            "status": "Available",
        },
    )
    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: (hand_rows, ()),
    )
    summary = get_small_hand_tools_value_summary()
    assert summary.total_value == 0.0
    assert summary.missing_value_count == 1


def test_small_tools_excludes_inactive_and_retired(monkeypatch):
    hand_rows = (
        {"id": "ht1", "quantity_on_hand": 1, "unit_value": 100, "is_active": False},
        {"id": "ht2", "quantity_on_hand": 1, "unit_value": 100, "status": "Retired", "is_active": True},
    )
    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: (hand_rows, ()),
    )
    summary = get_small_hand_tools_value_summary()
    assert summary.total_value == 0.0
    assert summary.tool_type_count == 0


def test_kit_item_included_with_actual_quantity(monkeypatch):
    kit_rows = (
        {
            "id": "ki1",
            "parent_asset_id": "trailer1",
            "item_name": "Wrench set",
            "quantity_actual": 2,
            "quantity_expected": 4,
            "unit_value": 25,
            "is_active": True,
            "status": "Present",
        },
    )
    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: ((), kit_rows),
    )
    summary = get_small_hand_tools_value_summary()
    assert summary.total_value == 50.0
    assert summary.tool_type_count == 1


def test_kit_item_with_serial_excluded(monkeypatch):
    kit_rows = (
        {
            "id": "ki1",
            "quantity_actual": 1,
            "unit_value": 500,
            "serial_number": "SN-999",
            "is_active": True,
        },
    )
    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: ((), kit_rows),
    )
    summary = get_small_hand_tools_value_summary()
    assert summary.total_value == 0.0


def test_kit_item_with_child_asset_excluded_from_small_tools(monkeypatch):
    kit_rows = (
        {
            "id": "ki1",
            "child_asset_id": "child1",
            "quantity_actual": 1,
            "unit_value": 500,
            "is_active": True,
        },
    )
    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: ((), kit_rows),
    )
    summary = get_small_hand_tools_value_summary()
    assert summary.total_value == 0.0


def test_duplicate_hand_tool_counted_once(monkeypatch):
    row = {
        "id": "ht1",
        "quantity_on_hand": 1,
        "unit_value": 10,
        "is_active": True,
        "status": "Available",
    }
    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: ((row, row), ()),
    )
    summary = get_small_hand_tools_value_summary()
    assert summary.total_value == 10.0
    assert summary.tool_type_count == 1


def test_source_asset_id_linked_to_included_asset_excluded(monkeypatch):
    hand_rows = (
        {
            "id": "ht1",
            "source_asset_id": "eq1",
            "quantity_on_hand": 2,
            "unit_value": 50,
            "is_active": True,
            "status": "Available",
        },
    )
    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: (hand_rows, ()),
    )
    summary = get_small_hand_tools_value_summary(excluded_asset_ids={"eq1"})
    assert summary.total_value == 0.0


def test_duplicate_asset_ids_counted_once_in_equipment():
    assets = [
        {"id": "eq1", "status": "Active", "purchase_cost": 100},
        {"id": "eq1", "status": "Active", "purchase_cost": 100},
    ]
    breakdown = calculate_asset_value_breakdown(assets, small_tools_summary=_empty_small_tools())
    assert breakdown.equipment_value == 100.0
    assert breakdown.equipment_count == 1


def test_combined_total_equals_sum_of_subtotals(monkeypatch):
    assets = [
        {"id": "eq1", "status": "Active", "purchase_cost": 1000.12},
        {
            "id": "ser1",
            "status": "Active",
            "purchase_cost": 200.33,
            "is_serialized_tool": True,
            "serial_number": "S1",
            "category": "Tool",
        },
    ]
    hand_rows = (
        {"id": "ht1", "quantity_on_hand": 2, "unit_value": 10.5, "is_active": True, "status": "Available"},
    )
    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: (hand_rows, ()),
    )
    breakdown = compute_asset_value_breakdown(assets)
    assert breakdown.total_asset_value == round(
        breakdown.equipment_value + breakdown.serialized_tools_value + breakdown.small_tools_value,
        2,
    )
    assert breakdown.total_asset_value == 1221.45


def test_compute_dashboard_kpis_combined_asset_value(monkeypatch):
    from datetime import date

    hand_rows = (
        {"id": "ht1", "quantity_on_hand": 1, "unit_value": 50, "is_active": True, "status": "Available"},
    )
    monkeypatch.setattr(
        "app.services.small_hand_tool_service._cached_hand_tools_sources",
        lambda *, include_kit_items: (hand_rows, ()),
    )
    today = date.today()
    kpis = compute_dashboard_kpis(
        [],
        [],
        [],
        [
            {"id": "eq1", "status": "Active", "purchase_cost": 1000},
            {
                "id": "ser1",
                "status": "Active",
                "purchase_cost": 200,
                "is_serialized_tool": True,
                "serial_number": "SN",
                "category": "Tool",
            },
        ],
        period_start=today.replace(day=1),
        period_end=today,
    )
    assert kpis["equipment_value"] == 1000.0
    assert kpis["serialized_tools_value"] == 200.0
    assert kpis["small_tools_value"] == 50.0
    assert kpis["total_asset_value"] == 1250.0
    assert kpis["asset_value"] == 1250.0


def test_dashboard_snapshot_uses_combined_asset_value():
    from datetime import date

    from app.services.dashboard_service import DashboardSnapshot

    snap = DashboardSnapshot(
        period_start=date.today(),
        period_end=date.today(),
        active_jobs=0,
        open_estimates=0,
        employees_working_today=0,
        my_todo_count=0,
        open_invoices=0.0,
        period_revenue=0.0,
        inventory_value=0.0,
        asset_value=1250.0,
        is_live=True,
        asset_value_caption="Equipment: $1,000.00 · Serialized Tools: $200.00 · Small Tools: $50.00",
    )
    assert snap.asset_value == 1250.0


def test_small_hand_tools_data_version_bumps_on_catalog_clear():
    session_state = {}
    with patch("app.pages._core._data.st.session_state", session_state):
        from app.pages._core._data import (
            clear_small_hand_tools_catalog_cache,
            small_hand_tools_data_version,
        )

        assert small_hand_tools_data_version() == 0
        with patch("app.services.small_hand_tool_service._cached_hand_tools_sources") as mock_cache:
            mock_cache.clear = lambda: None
            with patch("app.pages._core._data.clear_dashboard_page_data_cache"):
                clear_small_hand_tools_catalog_cache()
        assert small_hand_tools_data_version() == 1


def test_dashboard_version_token_includes_small_hand_tools_version():
    session_state = {"_ips_small_hand_tools_catalog_version": 3, "_ips_assets_catalog_version": 1}
    with patch("app.pages._core._data.st.session_state", session_state):
        from app.services.dashboard_service import dashboard_data_version_token

        token = dashboard_data_version_token()
        assert ":3:" in token or token.endswith(":3") or "3" in token.split(":")


def test_reclassification_equipment_to_serialized_preserves_combined_total():
    assets_before = [{"id": "a1", "status": "Active", "purchase_cost": 500}]
    assets_after = [
        {
            "id": "a1",
            "status": "Active",
            "purchase_cost": 500,
            "is_serialized_tool": True,
            "serial_number": "SN-1",
            "category": "Tool",
        }
    ]
    before = calculate_asset_value_breakdown(assets_before, small_tools_summary=_empty_small_tools())
    after = calculate_asset_value_breakdown(assets_after, small_tools_summary=_empty_small_tools())
    assert before.total_asset_value == after.total_asset_value == 500.0
