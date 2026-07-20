"""Tests for kit item ↔ master tool two-way sync."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.kit_item_sync_service import (
    append_hand_tool_tag,
    hand_tool_id_from_notes,
    kit_item_should_sync_to_master,
    resolve_kit_item_tracking_mode,
    sync_master_from_kit_item_create,
    sync_master_from_kit_item_update,
    sync_master_on_kit_item_delete,
)


class TestKitItemSyncRules(unittest.TestCase):
    def test_consumable_not_synced(self) -> None:
        row = {"item_type": "Consumable", "item_name": "Tape", "quantity_expected": 1}
        self.assertFalse(kit_item_should_sync_to_master(row))
        self.assertIsNone(resolve_kit_item_tracking_mode(row))

    def test_inventory_link_not_synced(self) -> None:
        row = {"item_type": "Tool", "inventory_item_id": "inv-1", "item_name": "Drill"}
        self.assertFalse(kit_item_should_sync_to_master(row))

    def test_linked_asset_not_synced(self) -> None:
        row = {"item_type": "Tool", "child_asset_id": "asset-1", "item_name": "Drill"}
        self.assertFalse(kit_item_should_sync_to_master(row))

    def test_serial_qty_one_is_serialized(self) -> None:
        row = {
            "item_type": "Tool",
            "item_name": "Impact",
            "quantity_expected": 1,
            "serial_number": "SN-100",
        }
        self.assertTrue(kit_item_should_sync_to_master(row))
        self.assertEqual(resolve_kit_item_tracking_mode(row), "serialized")

    def test_no_serial_is_hand_tool(self) -> None:
        row = {"item_type": "Tool", "item_name": "Hammer", "quantity_expected": 3}
        self.assertEqual(resolve_kit_item_tracking_mode(row), "hand_tool")

    def test_hand_tool_tag_parser(self) -> None:
        tool_id = "550e8400-e29b-41d4-a716-446655440000"
        notes = f"Shop stock hand_tool:{tool_id}"
        self.assertEqual(hand_tool_id_from_notes(notes), tool_id)
        self.assertEqual(
            append_hand_tool_tag("Keep", tool_id),
            f"Keep hand_tool:{tool_id}",
        )


class TestKitItemSyncCreate(unittest.TestCase):
    @patch("app.services.kit_item_sync_service._link_kit_item_fields")
    @patch("app.services.serialized_tool_service.create_serialized_tool")
    @patch("app.services.kit_item_sync_service.delete_row")
    def test_create_serialized_links_child_asset(
        self,
        mock_delete: unittest.mock.MagicMock,
        mock_create_tool: unittest.mock.MagicMock,
        mock_link: unittest.mock.MagicMock,
    ) -> None:
        mock_create_tool.return_value = type(
            "R",
            (),
            {"ok": True, "data": {"id": "tool-99"}},
        )()

        result = sync_master_from_kit_item_create(
            "trailer-1",
            "kit-1",
            {
                "item_name": "Drill",
                "item_type": "Tool",
                "quantity_expected": 1,
                "serial_number": "SN-1",
                "status": "Present",
            },
        )

        self.assertTrue(result.ok)
        mock_create_tool.assert_called_once()
        self.assertTrue(mock_create_tool.call_args.args[0]["skip_kit_sync"])
        mock_link.assert_called_once_with("kit-1", child_asset_id="tool-99")
        mock_delete.assert_not_called()

    @patch("app.services.kit_item_sync_service._link_kit_item_fields")
    @patch("app.services.small_hand_tool_service.save_hand_tool")
    @patch("app.services.kit_item_sync_service.delete_row")
    def test_create_hand_tool_links_notes_tag(
        self,
        mock_delete: unittest.mock.MagicMock,
        mock_save_hand: unittest.mock.MagicMock,
        mock_link: unittest.mock.MagicMock,
    ) -> None:
        mock_save_hand.return_value = type(
            "R",
            (),
            {"ok": True, "data": {"id": "hand-42"}},
        )()

        result = sync_master_from_kit_item_create(
            "trailer-1",
            "kit-2",
            {
                "item_name": "Pliers",
                "item_type": "Tool",
                "quantity_expected": 2,
                "notes": "Red handle",
            },
        )

        self.assertTrue(result.ok)
        mock_save_hand.assert_called_once()
        self.assertTrue(mock_save_hand.call_args.args[0]["skip_kit_sync"])
        mock_link.assert_called_once()
        self.assertIn("hand-42", mock_link.call_args.kwargs["notes"])
        mock_delete.assert_not_called()


class TestKitItemSyncUpdate(unittest.TestCase):
    @patch("app.services.kit_item_sync_service.update_row")
    def test_update_pushes_to_linked_serialized_asset(self, mock_update: unittest.mock.MagicMock) -> None:
        mock_update.return_value = type("R", (), {"ok": True, "data": {}})()
        row = {
            "id": "kit-1",
            "parent_asset_id": "trailer-1",
            "child_asset_id": "tool-1",
            "item_name": "Updated Drill",
            "serial_number": "SN-1",
            "status": "Checked Out",
            "assigned_to_employee_id": "emp-1",
            "assigned_to_name": "Alex",
            "condition": "Good",
        }
        result = sync_master_from_kit_item_update(row)
        self.assertTrue(result.ok)
        mock_update.assert_called_once()
        self.assertEqual(mock_update.call_args.args[2], {"id": "tool-1"})
        payload = mock_update.call_args.args[1]
        self.assertEqual(payload["asset_name"], "Updated Drill")
        self.assertEqual(payload["status"], "Checked Out")

    @patch("app.services.kit_item_sync_service.update_row")
    def test_update_pushes_to_linked_hand_tool(self, mock_update: unittest.mock.MagicMock) -> None:
        mock_update.return_value = type("R", (), {"ok": True, "data": {}})()
        row = {
            "id": "kit-2",
            "parent_asset_id": "trailer-1",
            "notes": "hand_tool:hand-9",
            "item_name": "Wrench set",
            "quantity_actual": 4,
            "quantity_expected": 4,
            "status": "Present",
        }
        result = sync_master_from_kit_item_update(row)
        self.assertTrue(result.ok)
        mock_update.assert_called_once()
        self.assertEqual(mock_update.call_args.args[0], "small_hand_tools")
        self.assertEqual(mock_update.call_args.args[2], {"id": "hand-9"})


class TestKitItemSyncDelete(unittest.TestCase):
    @patch("app.services.kit_item_sync_service.fetch_by_id")
    @patch("app.services.kit_item_sync_service.update_row")
    def test_delete_detaches_serialized_tool(self, mock_update: unittest.mock.MagicMock, mock_fetch: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = {"current_container_asset_id": "trailer-1"}
        sync_master_on_kit_item_delete(
            {"parent_asset_id": "trailer-1", "child_asset_id": "tool-1", "notes": ""}
        )
        mock_update.assert_called_once()
        self.assertEqual(mock_update.call_args.args[0], "assets")
        self.assertIsNone(mock_update.call_args.args[1]["current_container_asset_id"])

    @patch("app.services.kit_item_sync_service.update_row")
    def test_delete_deactivates_hand_tool(self, mock_update: unittest.mock.MagicMock) -> None:
        sync_master_on_kit_item_delete(
            {"notes": "hand_tool:hand-5", "parent_asset_id": "trailer-1"}
        )
        mock_update.assert_called_once()
        self.assertEqual(mock_update.call_args.args[0], "small_hand_tools")
        self.assertFalse(mock_update.call_args.args[1]["is_active"])


if __name__ == "__main__":
    unittest.main()
