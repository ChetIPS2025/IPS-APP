"""Tests for job cost tab helpers and invoice visibility."""

from __future__ import annotations

import unittest

import pandas as pd

from app.components.job_cost_tab import (
    _compact_cost_display_df,
    _format_amount_line,
    _format_qty_unit,
    _join_employee_notes,
)
from app.services.job_cost_transaction_service import (
    COST_LABOR,
    COST_MATERIAL,
    SOURCE_JOB_MATERIAL,
    SOURCE_TIMEKEEPING_DAY,
    transaction_cost_tab_source,
    transaction_show_on_invoice,
)


class TestJobCostTabDisplay(unittest.TestCase):
    def test_format_qty_unit(self) -> None:
        self.assertEqual(_format_qty_unit(1, "ea"), "1 ea")
        self.assertEqual(_format_qty_unit(2.5, "ft"), "2.5 ft")

    def test_format_amount_line_single_qty(self) -> None:
        self.assertEqual(_format_amount_line(26.25, 26.25, 1), "$26.25")

    def test_format_amount_line_multi_qty(self) -> None:
        self.assertEqual(_format_amount_line(10, 20, 2), "$10.00/ea · $20.00")

    def test_join_employee_notes(self) -> None:
        self.assertEqual(_join_employee_notes("Pat", "Inventory scan"), "Pat · Inventory scan")
        self.assertEqual(_join_employee_notes("—", "Inventory scan"), "Inventory scan")

    def test_compact_cost_display_df(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "id": "t1",
                    "description": "Safety Tags",
                    "qty": 1,
                    "unit": "ea",
                    "unit_cost": 26.25,
                    "total_cost": 26.25,
                    "employee": "—",
                    "notes": "Inventory scan",
                    "show_on_invoice": True,
                }
            ]
        )
        compact = _compact_cost_display_df(df)
        self.assertEqual(list(compact.columns), ["id", "description", "qty_unit", "amount", "detail", "show_on_invoice"])
        self.assertEqual(compact.iloc[0]["qty_unit"], "1 ea")
        self.assertEqual(compact.iloc[0]["amount"], "$26.25")
        self.assertEqual(compact.iloc[0]["detail"], "Inventory scan")


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
