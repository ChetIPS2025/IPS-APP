"""Tests for field → office → billing loop helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.inventory_service import (
    INVENTORY_TXN_TYPES,
    record_shop_inventory_consumption,
)
from app.services.job_cost_transaction_service import sync_timekeeping_day


class TestShopInventoryConsumption(unittest.TestCase):
    def test_consume_in_shop_is_valid_txn_type(self) -> None:
        self.assertIn("consume_in_shop", INVENTORY_TXN_TYPES)

    @patch("app.services.inventory_service.record_inventory_transaction")
    def test_record_shop_inventory_consumption_routes_to_service(self, txn_mock) -> None:
        txn_mock.return_value = MagicMock(ok=True, data={"transaction": {"id": "t1"}})
        record_shop_inventory_consumption(
            {
                "inventory_item_id": "inv-1",
                "quantity": 2.0,
                "notes": "shop use",
            }
        )
        txn_mock.assert_called_once()
        payload = txn_mock.call_args[0][0]
        self.assertEqual(payload["transaction_type"], "consume_in_shop")
        self.assertEqual(payload["destination_type"], "shop")
        self.assertIsNone(payload["job_id"])


class TestTimekeepingLaborSync(unittest.TestCase):
    @patch("app.services.job_cost_transaction_service.delete_job_cost_transaction")
    @patch("app.services.job_cost_transaction_service.upsert_job_cost_transaction")
    @patch("app.services.job_cost_transaction_service._employee_by_id", return_value={"id": "e1", "name": "Pat"})
    @patch("app.services.employee_labor.compute_burdened_labor_cost", return_value=400.0)
    def test_sync_timekeeping_day_approved_creates_labor_cost(
        self,
        _cost_mock,
        _emp_mock,
        upsert_mock,
        delete_mock,
    ) -> None:
        sync_timekeeping_day(
            {
                "id": "day-1",
                "job_id": "job-1",
                "employee_id": "e1",
                "work_date": "2026-05-26",
                "status": "Approved",
                "st_hours": 8,
                "ot_hours": 0,
                "dt_hours": 0,
            }
        )
        upsert_mock.assert_called_once()
        delete_mock.assert_not_called()
        payload = upsert_mock.call_args[0][0]
        self.assertEqual(payload["job_id"], "job-1")
        self.assertEqual(payload["quantity"], 8.0)
        self.assertEqual(payload["total_cost"], 400.0)

    @patch("app.services.job_cost_transaction_service.delete_job_cost_transaction")
    @patch("app.services.job_cost_transaction_service.upsert_job_cost_transaction")
    def test_sync_timekeeping_day_pending_removes_labor_cost(self, upsert_mock, delete_mock) -> None:
        sync_timekeeping_day(
            {
                "id": "day-2",
                "job_id": "job-1",
                "employee_id": "e1",
                "work_date": "2026-05-26",
                "status": "Pending",
                "st_hours": 8,
            }
        )
        delete_mock.assert_called_once()
        upsert_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
