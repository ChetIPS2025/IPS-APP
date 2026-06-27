"""Estimate material line payload and repository filtering."""

from __future__ import annotations

from unittest.mock import patch

from app.services.estimate_costing_service import _material_insert_payload, _uuid_or_none
from app.services.repository import (
    TABLE_COLUMN_CORE,
    filter_payload_to_table,
    insert_row_admin,
)


def test_uuid_or_none_rejects_invalid_values():
    assert _uuid_or_none(None) is None
    assert _uuid_or_none("") is None
    assert _uuid_or_none("not-a-uuid") is None
    assert _uuid_or_none("demo-123") is None
    valid = "550e8400-e29b-41d4-a716-446655440000"
    assert _uuid_or_none(valid) == valid


def test_material_insert_payload_uses_total_cost_not_cost_total():
    payload = _material_insert_payload(
        "550e8400-e29b-41d4-a716-446655440000",
        {
            "description": '1" BALL VALVE',
            "quantity": 2,
            "unit_cost": 10.0,
            "markup_percent": 25,
            "pricing_item_id": "550e8400-e29b-41d4-a716-446655440001",
            "inventory_item_id": "bad-id",
        },
        0,
    )
    assert payload["total_cost"] == 20.0
    assert "cost_total" not in payload
    assert payload["pricing_item_id"] == "550e8400-e29b-41d4-a716-446655440001"
    assert payload["inventory_item_id"] is None
    assert payload["markup"] == 25


def test_filter_payload_to_table_uses_allowlist_when_table_empty():
    raw = {
        "estimate_id": "550e8400-e29b-41d4-a716-446655440000",
        "description": "Test item",
        "qty": 1,
        "unit_cost": 10,
        "total_cost": 10,
        "cost_total": 10,
        "markup_percent": 25,
        "price_total": 12.5,
        "pricing_item_id": "550e8400-e29b-41d4-a716-446655440001",
    }
    with patch("app.services.repository.table_column_names", return_value=frozenset()):
        filtered = filter_payload_to_table("estimate_line_items", raw)
    assert "cost_total" not in filtered
    assert "pricing_item_id" not in filtered
    assert "markup_percent" not in filtered
    assert "markup" not in filtered
    assert filtered["total_cost"] == 10
    assert set(filtered.keys()).issubset(TABLE_COLUMN_CORE["estimate_line_items"])


def test_filter_payload_to_table_maps_markup_percent_to_legacy_markup():
    raw = {"markup_percent": 25.0, "description": "x", "qty": 1}
    with patch(
        "app.services.repository.table_column_names",
        return_value=frozenset({"markup", "description", "qty"}),
    ):
        filtered = filter_payload_to_table("estimate_line_items", raw)
    assert filtered["markup"] == 25.0
    assert "markup_percent" not in filtered


def test_insert_row_admin_retries_after_pgrst204_unknown_column():
    payload = {
        "estimate_id": "550e8400-e29b-41d4-a716-446655440000",
        "description": "Test item",
        "qty": 1,
        "unit_cost": 10,
        "total_cost": 10,
        "inventory_item_id": "550e8400-e29b-41d4-a716-446655440001",
    }
    calls: list[dict] = []

    def fake_insert(table, filtered):
        calls.append(dict(filtered))
        if "inventory_item_id" in filtered:
            raise RuntimeError(
                "insert_row_admin into 'estimate_line_items' failed: Error PGRST204: "
                "Could not find the 'inventory_item_id' column of 'estimate_line_items' in the schema cache"
            )
        return {"id": "new-row-id", **filtered}

    with patch(
        "app.services.repository.table_column_names",
        return_value=frozenset(
            {
                "estimate_id",
                "description",
                "qty",
                "unit_cost",
                "total_cost",
                "inventory_item_id",
            }
        ),
    ):
        with patch("app.services.repository._db") as mock_db:
            mock_db.return_value.insert_row_admin.side_effect = fake_insert
            with patch("app.services.repository.clear_all_data_caches"):
                result = insert_row_admin("estimate_line_items", payload)

    assert result.ok is True
    assert len(calls) == 2
    assert "inventory_item_id" not in calls[1]
    assert calls[1]["description"] == "Test item"
