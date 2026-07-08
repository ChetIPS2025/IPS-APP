"""Tests for job cost tab helpers and invoice visibility."""

from __future__ import annotations

import unittest

from app.services.job_cost_transaction_service import (
    COST_LABOR,
    COST_MATERIAL,
    SOURCE_JOB_MATERIAL,
    SOURCE_TIMEKEEPING_DAY,
    transaction_cost_tab_source,
    transaction_show_on_invoice,
)


class TestJobCostTransactionInvoice(unittest.TestCase):
    def test_transaction_show_on_invoice_defaults_true(self) -> None:
        self.assertTrue(transaction_show_on_invoice({}))
        self.assertTrue(transaction_show_on_invoice({"show_on_invoice": True}))
        self.assertFalse(transaction_show_on_invoice({"show_on_invoice": False}))

    def test_transaction_cost_tab_source_mapping(self) -> None:
        self.assertEqual(
            transaction_cost_tab_source(
                {"source_type": SOURCE_TIMEKEEPING_DAY, "cost_category": COST_LABOR}
            ),
            "Labor",
        )
        self.assertEqual(
            transaction_cost_tab_source(
                {
                    "source_type": SOURCE_JOB_MATERIAL,
                    "cost_category": COST_MATERIAL,
                    "notes": "Inventory scan",
                    "inventory_item_id": "inv-1",
                }
            ),
            "QR Scan",
        )
        self.assertEqual(
            transaction_cost_tab_source(
                {
                    "source_type": SOURCE_JOB_MATERIAL,
                    "cost_category": COST_MATERIAL,
                    "inventory_item_id": "inv-2",
                }
            ),
            "Inventory",
        )


if __name__ == "__main__":
    unittest.main()
