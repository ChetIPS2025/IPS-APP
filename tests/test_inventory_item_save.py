"""Inventory item save payload — NOT NULL text coercion and update resilience."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.phase2_modules_service import save_inventory_item
from app.services.repository import ServiceResult, update_row


def test_save_inventory_item_update_coerces_null_vendor() -> None:
    captured: dict = {}

    def fake_update(table, payload, match):
        captured["table"] = table
        captured["payload"] = payload
        captured["match"] = match
        return ServiceResult(ok=True, data={"id": match["id"]})

    with patch("app.services.phase2_modules_service.update_row", side_effect=fake_update):
        with patch(
            "app.services.inventory_display_helpers.resolve_inventory_sku",
            return_value="INV-TEST",
        ):
            with patch(
                "app.services.inventory_display_helpers.resolve_inventory_qr_value",
                return_value="http://example/scan",
            ):
                result = save_inventory_item(
                    {
                        "name": "Ball Valve",
                        "category": "Plumbing",
                        "location": "Shelf A",
                        "qty_on_hand": 3,
                        "unit_cost": 12.5,
                        "status": "In Stock",
                    },
                    row_id="550e8400-e29b-41d4-a716-446655440000",
                )

    assert result.ok is True
    assert captured["table"] == "inventory_items"
    assert captured["payload"]["vendor"] == ""
    assert captured["payload"]["category"] == "Plumbing"
    assert captured["payload"]["item_name"] == "Ball Valve"
    assert captured["match"] == {"id": "550e8400-e29b-41d4-a716-446655440000"}


def test_save_inventory_item_requires_name() -> None:
    result = save_inventory_item({"name": "", "category": "General"}, row_id="550e8400-e29b-41d4-a716-446655440000")
    assert result.ok is False
    assert "name" in (result.error or "").casefold()


def test_update_row_strips_unknown_columns_on_pgrst204() -> None:
    mock_db = MagicMock()
    mock_db.update_rows.side_effect = [
        RuntimeError("Could not find the 'status' column of 'inventory_items' in the schema cache"),
        [{"id": "i1", "item_name": "Widget"}],
    ]

    with patch("app.services.repository._db", return_value=mock_db):
        with patch(
            "app.services.repository.filter_payload_to_table",
            side_effect=lambda _t, p: dict(p),
        ):
            result = update_row(
                "inventory_items",
                {"item_name": "Widget", "status": "In Stock", "vendor": ""},
                {"id": "i1"},
            )

    assert result.ok is True
    assert mock_db.update_rows.call_count == 2
    second_payload = mock_db.update_rows.call_args_list[1][0][1]
    assert "status" not in second_payload
    assert second_payload["vendor"] == ""
