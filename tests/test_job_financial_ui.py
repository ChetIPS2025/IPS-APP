"""Tests for job financial UI helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.job_financial_ui import (
    BILLING_TYPE_TM,
    apply_projected_financials_to_job_payload,
    billing_type_label,
    job_financials_locked_by_approved_estimate,
    job_is_time_and_material,
    job_list_financials_from_row,
    job_manual_financials_editable,
    job_table_list_financials_from_row,
    normalize_billing_type,
    projected_gross_profit,
    projected_margin_pct,
)


class TestJobFinancialUi(unittest.TestCase):
    def test_projected_margin(self) -> None:
        self.assertEqual(projected_gross_profit(10000, 7000), 3000)
        self.assertEqual(projected_margin_pct(10000, 7000), 30.0)

    def test_manual_financials_editable_without_estimate(self) -> None:
        self.assertTrue(job_manual_financials_editable({"id": "j1"}))

    def test_manual_financials_editable_with_draft_estimate_link(self) -> None:
        with patch(
            "app.services.job_financial_ui._fetch_estimate_for_financial_lock",
            return_value={"id": "e1", "status": "Draft", "job_id": "j1"},
        ):
            self.assertTrue(
                job_manual_financials_editable({"id": "j1", "estimate_id": "e1", "status": "Active"})
            )

    def test_manual_financials_editable_when_only_reverse_estimate_link(self) -> None:
        """Approved estimate pointing at job without jobs.estimate_id stays manual/editable."""
        self.assertTrue(job_manual_financials_editable({"id": "j1", "status": "Active", "awarded_amount": 5000}))

    @patch("app.services.job_cost_transaction_service._estimate_is_approved", return_value=True)
    @patch("app.services.job_financial_ui._fetch_estimate_for_financial_lock")
    def test_manual_financials_not_editable_with_bidirectional_approved_link(
        self,
        fetch_mock,
        _approved_mock,
    ) -> None:
        fetch_mock.return_value = {
            "id": "e1",
            "status": "Approved",
            "job_id": "j1",
            "quote_number": "Q26070",
        }
        job = {"id": "j1", "estimate_id": "e1", "status": "Active", "job_number": "J26070"}
        self.assertFalse(job_manual_financials_editable(job))
        self.assertTrue(job_financials_locked_by_approved_estimate(job))

    @patch("app.services.job_cost_transaction_service._estimate_is_approved", return_value=True)
    @patch("app.services.job_financial_ui._fetch_estimate_for_financial_lock")
    def test_manual_financials_not_editable_with_matching_quote(
        self,
        fetch_mock,
        _approved_mock,
    ) -> None:
        fetch_mock.return_value = {
            "id": "e1",
            "status": "Approved",
            "job_id": "",
            "quote_number": "Q26070",
        }
        job = {
            "id": "j1",
            "estimate_id": "e1",
            "status": "Active",
            "job_number": "J26070",
            "source_estimate_number": "Q26070",
        }
        self.assertFalse(job_manual_financials_editable(job))

    @patch("app.services.job_cost_transaction_service._estimate_is_approved", return_value=True)
    @patch("app.services.job_financial_ui._fetch_estimate_for_financial_lock")
    def test_manual_financials_editable_when_estimate_id_points_elsewhere(
        self,
        fetch_mock,
        _approved_mock,
    ) -> None:
        fetch_mock.return_value = {
            "id": "e1",
            "status": "Approved",
            "job_id": "other-job",
            "quote_number": "Q99999",
        }
        job = {"id": "j1", "estimate_id": "e1", "status": "Active", "job_number": "J26070"}
        self.assertTrue(job_manual_financials_editable(job))

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
        self.assertEqual(fin["actual_cost"], 0.0)
        self.assertFalse(fin["has_actual"])

    def test_job_list_financials_uses_running_actual_cost(self) -> None:
        fin = job_list_financials_from_row(
            {
                "awarded_amount": 10000,
                "estimated_cost": 7000,
                "actual_cost": 3200,
            }
        )
        self.assertEqual(fin["actual_cost"], 3200)
        self.assertTrue(fin["has_actual"])
        self.assertEqual(fin["profit"], 6800)
        self.assertEqual(fin["margin_pct"], 68.0)

    @patch("app.services.job_financial_ui._linked_estimate_for_jobs_table")
    def test_job_table_list_uses_linked_estimate_total_not_job_estimated_cost(
        self,
        link_mock,
    ) -> None:
        link_mock.return_value = {"id": "e1", "customer_price": 12500.0}
        fin = job_table_list_financials_from_row(
            {
                "id": "j1",
                "estimate_id": "e1",
                "estimated_cost": 4000,
                "actual_cost": 5000,
            }
        )
        self.assertEqual(fin["estimated_cost"], 12500.0)
        self.assertTrue(fin["has_estimated"])
        self.assertEqual(fin["actual_cost"], 5000.0)

    @patch("app.services.job_financial_ui._linked_estimate_for_jobs_table", return_value=None)
    def test_job_table_list_shows_dash_when_no_linked_estimate(self, _link_mock) -> None:
        fin = job_table_list_financials_from_row(
            {"id": "j1", "estimated_cost": 9000, "actual_cost": 100}
        )
        self.assertEqual(fin["estimated_cost"], 0.0)
        self.assertFalse(fin["has_estimated"])

    def test_billing_type_normalization(self) -> None:
        self.assertEqual(normalize_billing_type("Time & Materials"), BILLING_TYPE_TM)
        self.assertEqual(normalize_billing_type("Fixed Price"), "fixed_price")
        self.assertTrue(job_is_time_and_material({"billing_type": "time_and_material"}))
        self.assertEqual(billing_type_label(BILLING_TYPE_TM), "Time & Materials")


if __name__ == "__main__":
    unittest.main()
