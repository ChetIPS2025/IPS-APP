"""Tests for linking master small hand tools to trailer kits."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.small_hand_tool_service import (
    hand_tool_kit_option_label,
    link_hand_tool_to_kit,
    link_hand_tools_to_kit,
)


class TestHandToolKitLink(unittest.TestCase):
    @patch("app.services.small_hand_tool_service._sync_kit_item_for_hand_tool")
    @patch("app.services.small_hand_tool_service.clear_hand_tools_list_cache")
    @patch("app.services.small_hand_tool_service.update_row")
    @patch("app.services.repository.fetch_by_id")
    @patch("app.services.small_hand_tool_service.asset_is_kit", return_value=True)
    def test_link_hand_tool_to_kit_updates_storage_and_syncs(
        self,
        _mock_is_kit: unittest.mock.MagicMock,
        mock_fetch: unittest.mock.MagicMock,
        mock_update: unittest.mock.MagicMock,
        _mock_clear: unittest.mock.MagicMock,
        mock_sync: unittest.mock.MagicMock,
    ) -> None:
        mock_fetch.side_effect = lambda table, rid: {
            "assets": {"id": "trailer-1", "is_kit": True},
            "small_hand_tools": {
                "id": "ht-1",
                "tool_name": "Pliers",
                "category": "Pliers",
                "quantity_on_hand": 2,
                "quantity_expected": 2,
                "unit_value": 10,
                "storage_type": "Warehouse",
                "is_active": True,
            },
        }.get(table)
        mock_update.return_value = type("R", (), {"ok": True, "data": {}})()

        result = link_hand_tool_to_kit("ht-1", "trailer-1")
        self.assertTrue(result.ok)
        mock_sync.assert_called_once()
        payload = mock_update.call_args.args[1]
        self.assertEqual(payload["storage_type"], "Tool Trailer")
        self.assertEqual(payload["container_asset_id"], "trailer-1")

    @patch("app.services.small_hand_tool_service.link_hand_tool_to_kit")
    def test_link_hand_tools_to_kit_bulk(self, mock_link: unittest.mock.MagicMock) -> None:
        mock_link.return_value = type("R", (), {"ok": True, "data": {}})()
        result = link_hand_tools_to_kit("trailer-1", ["ht-1", "ht-2"])
        self.assertTrue(result.ok)
        self.assertEqual(mock_link.call_count, 2)

    def test_hand_tool_kit_option_label(self) -> None:
        label = hand_tool_kit_option_label(
            {
                "tool_name": "Channel Lock",
                "category": "Pliers",
                "quantity_on_hand": 3,
                "location_display": "Warehouse",
            }
        )
        self.assertIn("Channel Lock", label)
        self.assertIn("qty 3", label)


if __name__ == "__main__":
    unittest.main()
