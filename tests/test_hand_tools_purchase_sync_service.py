"""Tests for purchase-list sync into small hand tools and serialized assets."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.data.hand_tools_purchase_list import (
    hand_tools_purchase_item_count,
    hand_tools_purchase_total_qty,
    hand_tools_purchase_total_value,
)
from app.services.hand_tools_purchase_sync_service import (
    find_hand_tool_match,
    find_serialized_matches,
    sync_hand_tools_purchase_list,
    upsert_hand_tool_from_purchase,
)


class TestPurchaseListData(unittest.TestCase):
    def test_batch1_totals(self) -> None:
        self.assertEqual(hand_tools_purchase_item_count(batch=1), 26)
        self.assertEqual(hand_tools_purchase_total_qty(batch=1), 52)
        self.assertEqual(hand_tools_purchase_total_value(batch=1), 3590.19)

    def test_batch2_totals(self) -> None:
        from app.data.hand_tools_purchase_list_batch2 import (
            BATCH2_ITEM_COUNT,
            BATCH2_TOTAL_QTY,
            BATCH2_TOTAL_VALUE,
        )

        self.assertEqual(hand_tools_purchase_item_count(batch=2), BATCH2_ITEM_COUNT)
        self.assertEqual(hand_tools_purchase_total_qty(batch=2), BATCH2_TOTAL_QTY)
        self.assertEqual(hand_tools_purchase_total_value(batch=2), BATCH2_TOTAL_VALUE)
        self.assertEqual(BATCH2_TOTAL_QTY, 133)
        self.assertAlmostEqual(BATCH2_TOTAL_VALUE, 7750.16, delta=0.02)

    def test_batch3_totals(self) -> None:
        from app.data.hand_tools_purchase_list_batch3 import (
            BATCH3_ITEM_COUNT,
            BATCH3_TOTAL_QTY,
            BATCH3_TOTAL_VALUE,
        )

        self.assertEqual(hand_tools_purchase_item_count(batch=3), BATCH3_ITEM_COUNT)
        self.assertEqual(hand_tools_purchase_total_qty(batch=3), BATCH3_TOTAL_QTY)
        self.assertEqual(hand_tools_purchase_total_value(batch=3), BATCH3_TOTAL_VALUE)
        self.assertEqual(BATCH3_TOTAL_QTY, 161)
        self.assertAlmostEqual(BATCH3_TOTAL_VALUE, 9286.85, delta=0.02)

    def test_batch4_totals(self) -> None:
        from app.data.hand_tools_purchase_list_batch4 import (
            BATCH4_ITEM_COUNT,
            BATCH4_TOTAL_QTY,
            BATCH4_TOTAL_VALUE,
        )

        self.assertEqual(hand_tools_purchase_item_count(batch=4), BATCH4_ITEM_COUNT)
        self.assertEqual(hand_tools_purchase_total_qty(batch=4), BATCH4_TOTAL_QTY)
        self.assertEqual(hand_tools_purchase_total_value(batch=4), BATCH4_TOTAL_VALUE)
        self.assertEqual(BATCH4_TOTAL_QTY, 304)
        self.assertAlmostEqual(BATCH4_TOTAL_VALUE, 17456.08, delta=0.02)


class TestPurchaseMatching(unittest.TestCase):
    def test_find_hand_tool_by_model(self) -> None:
        by_model = {"18268": {"id": "ht-1", "tool_name": "Wrench", "model_number": "18268"}}
        match = find_hand_tool_match(
            {"model_number": "18268", "tool_name": "Other name"},
            by_model=by_model,
            by_name={},
            by_tool_key={},
        )
        self.assertEqual(match, by_model["18268"])

    def test_find_serialized_by_model(self) -> None:
        assets = [
            {"id": "a-1", "asset_name": "Grinder", "model": "DWE402W", "is_serialized_tool": True},
            {"id": "a-2", "asset_name": "Hammer", "model": "H1", "is_serialized_tool": True},
        ]
        with patch(
            "app.services.hand_tools_purchase_sync_service.is_serialized_tool_asset",
            side_effect=lambda row: bool(row.get("is_serialized_tool")),
        ):
            matches = find_serialized_matches({"model_number": "DWE402W", "tool_name": "DEWALT"}, assets)
        self.assertEqual([row["id"] for row in matches], ["a-1"])


class TestPurchaseSync(unittest.TestCase):
    @patch("app.services.hand_tools_purchase_sync_service.update_row_admin")
    @patch("app.services.hand_tools_purchase_sync_service.find_hand_tool_match")
    def test_upsert_updates_existing_hand_tool(
        self,
        mock_find: unittest.mock.MagicMock,
        mock_update: unittest.mock.MagicMock,
    ) -> None:
        mock_find.return_value = {"id": "ht-99", "tool_name": "Wrench", "model_number": "18268"}
        mock_update.return_value = type("R", (), {"ok": True, "data": {}})()

        item = {
            "tool_name": 'TEKTON 1-1/8" Combination Wrench',
            "model_number": "18268",
            "category": "Wrenches",
            "qty": 1,
            "unit_value": 21.0,
        }
        result = upsert_hand_tool_from_purchase(item, increment_qty=False)
        self.assertTrue(result.ok)
        self.assertEqual((result.data or {}).get("action"), "updated")
        mock_update.assert_called_once()
        payload = mock_update.call_args.args[1]
        self.assertEqual(payload["quantity_on_hand"], 1.0)
        self.assertEqual(payload["unit_value"], 21.0)

    @patch("app.services.hand_tools_purchase_sync_service.update_serialized_from_purchase")
    @patch("app.services.hand_tools_purchase_sync_service.upsert_hand_tool_from_purchase")
    def test_sync_routes_by_tracking_mode(
        self,
        mock_hand: unittest.mock.MagicMock,
        mock_serial: unittest.mock.MagicMock,
    ) -> None:
        mock_hand.return_value = type("R", (), {"ok": True, "data": {"action": "updated"}})()
        mock_serial.return_value = type("R", (), {"ok": True, "data": {"action": "updated", "updated": 1}})()

        items = [
            {"tool_name": "Hammer", "tracking": "quantity", "qty": 2, "unit_value": 10},
            {"tool_name": "Hoist", "tracking": "serialized", "qty": 1, "unit_value": 100},
        ]
        result = sync_hand_tools_purchase_list(items=items)
        self.assertTrue(result.ok)
        mock_hand.assert_called_once()
        mock_serial.assert_called_once()
        summary = result.data or {}
        self.assertEqual(summary.get("hand_tools_updated"), 1)
        self.assertEqual(summary.get("serialized_updated"), 1)

    @patch("app.services.hand_tools_purchase_sync_service.update_row_admin")
    @patch("app.services.hand_tools_purchase_sync_service.find_hand_tool_match")
    def test_upsert_increments_existing_qty(
        self,
        mock_find: unittest.mock.MagicMock,
        mock_update: unittest.mock.MagicMock,
    ) -> None:
        mock_find.return_value = {
            "id": "ht-99",
            "tool_name": "Socket",
            "model_number": "560D",
            "quantity_on_hand": 2,
        }
        mock_update.return_value = type("R", (), {"ok": True, "data": {}})()

        result = upsert_hand_tool_from_purchase(
            {"tool_name": "Socket", "model_number": "560D", "qty": 1, "unit_value": 30.0},
            increment_qty=True,
        )
        self.assertTrue(result.ok)
        payload = mock_update.call_args.args[1]
        self.assertEqual(payload["quantity_on_hand"], 3.0)
