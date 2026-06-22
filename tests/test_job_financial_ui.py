"""Tests for job financial UI helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.job_financial_ui import (
    apply_projected_financials_to_job_payload,
    job_list_financials_from_row,
    job_manual_financials_editable,
    projected_gross_profit,
    projected_margin_pct,
)


class TestJobFinancialUi(unittest.TestCase):
    def test_projected_margin(self) -> None:
        self.assertEqual(projected_gross_profit(10000, 7000), 3000)
        self.assertEqual(projected_margin_pct(10000, 7000), 30.0)

    def test_manual_financials_editable_without_estimate(self) -> None:
        self.assertTrue(job_manual_financials_editable({"id": "j1"}))

    @patch("app.services.job_cost_transaction_service._estimate_is_approved", return_value=True)
    @patch("app.services.job_cost_transaction_service._approved_estimate_for_job")
    def test_manual_financials_not_editable_with_approved_estimate(
        self,
        estimate_mock,
        _approved_mock,
    ) -> None:
        estimate_mock.return_value = {"id": "e1", "status": "Approved"}
        self.assertFalse(
            job_manual_financials_editable(
                {"id": "j1", "estimate_id": "e1", "status": "Active", "awarded_amount": 1000}
            )
        )

    def test_apply_projected_financials_to_payload(self) -> None:
        payload = apply_projected_financials_to_job_payload(
            {"awarded_amount": 10000, "estimated_cost": 7000}
        )
        self.assertEqual(payload["projected_gross_profit"], 3000)
        self.assertEqual(payload["projected_margin_pct"], 30.0)

    def test_job_list_financials_from_row(self) -> None:
        fin = job_list_financials_from_row(
            {
                "awarded_amount": 5000,
                "estimated_cost": 4000,
                "projected_gross_profit": 1000,
                "projected_margin_pct": 20.0,
            }
        )
        self.assertEqual(fin["contract_value"], 5000)
        self.assertEqual(fin["profit"], 1000)
        self.assertEqual(fin["margin_pct"], 20.0)


if __name__ == "__main__":
    unittest.main()
