"""Unit tests for inventory transaction whole-number validation."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.inventory_service import record_inventory_transaction


class TestInventoryTransactionQuantity(unittest.TestCase):
    @patch("app.services.inventory_service._db_fetch_by_match")
    def test_rejects_decimal_quantity(self, fetch_mock) -> None:
        fetch_mock.return_value = [{"id": "inv1", "quantity_on_hand": 10, "quantity_checked_out": 0, "quantity_allocated": 0}]
        result = record_inventory_transaction(
            {
                "inventory_id": "inv1",
                "transaction_type": "consume_in_shop",
                "quantity": 1.5,
            }
        )
        self.assertFalse(result.ok)
        self.assertIn("whole number", str(result.error or "").lower())

    @patch("app.services.inventory_service.insert_row")
    @patch("app.services.inventory_service.update_row")
    @patch("app.services.inventory_service._db_fetch_by_match")
    def test_accepts_whole_quantity(self, fetch_mock, update_mock, insert_mock) -> None:
        fetch_mock.return_value = [
            {
                "id": "inv1",
                "quantity_on_hand": 10,
                "quantity_checked_out": 0,
                "quantity_allocated": 0,
                "unit": "EA",
            }
        ]
        update_mock.return_value = type("R", (), {"ok": True, "error": None})()
        insert_mock.return_value = type("R", (), {"ok": True, "error": None, "data": {"id": "txn1"}})()
        result = record_inventory_transaction(
            {
                "inventory_id": "inv1",
                "transaction_type": "consume_in_shop",
                "quantity": 2,
            }
        )
        self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
