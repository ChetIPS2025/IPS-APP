"""Tests for live reports aggregation."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.reports_service import (
    ReportData,
    live_job_profitability_report,
    live_labor_by_job_report,
    live_open_estimates_report,
)


class TestLiveLaborByJobReport(unittest.TestCase):
    @patch("app.services.reports_service._aggregate_time_entries_by_job", return_value=([], True))
    @patch("app.services.reports_service._aggregate_timekeeping_hours")
    @patch("app.services.reports_service._load_jobs_live")
    def test_aggregates_timekeeping_by_job_number(self, jobs_mock, tk_mock, _te_mock) -> None:
        jobs_mock.return_value = (
            [{"id": "j1", "job_number": "J100", "job_name": "Tank Farm"}],
            True,
        )
        tk_mock.return_value = (
            [
                {
                    "job_number": "J100",
                    "job_name": "Tank Farm",
                    "st_hours": 40.0,
                    "ot_hours": 4.0,
                    "dt_hours": 0.0,
                    "total_hours": 44.0,
                }
            ],
            True,
        )
        data = live_labor_by_job_report()
        self.assertTrue(data.is_live)
        self.assertEqual(len(data.rows), 1)
        self.assertEqual(data.rows[0]["job_number"], "J100")
        self.assertEqual(data.rows[0]["total_hours"], 44.0)


class TestLiveJobProfitabilityReport(unittest.TestCase):
    @patch("app.services.job_cost_transaction_service.sync_all_sources_for_job")
    @patch("app.services.job_cost_transaction_service.build_job_cost_summary")
    @patch("app.services.reports_service._load_jobs_live")
    def test_builds_margin_rows_from_cost_summary(self, jobs_mock, summary_mock, _sync_mock) -> None:
        jobs_mock.return_value = (
            [{"id": "j1", "job_number": "J100", "job_name": "Retrofit"}],
            True,
        )
        summary_mock.return_value = {
            "contract_value": 100000.0,
            "actual_cost": 78000.0,
            "margin_pct": 22.0,
        }
        data = live_job_profitability_report(sync_sources=False)
        self.assertTrue(data.is_live)
        self.assertEqual(len(data.rows), 1)
        self.assertEqual(data.rows[0]["revenue"], 100000.0)
        self.assertEqual(data.rows[0]["cost"], 78000.0)
        self.assertEqual(data.rows[0]["margin_pct"], 22.0)


class TestLiveOpenEstimatesReport(unittest.TestCase):
    @patch("app.services.reports_service.fetch_rows")
    def test_filters_open_estimate_statuses(self, fetch_mock) -> None:
        fetch_mock.return_value = (
            [
                {"estimate_number": "E1", "customer": "Acme", "status": "Sent", "total": 50000},
                {"estimate_number": "E2", "customer": "Bayou", "status": "Approved", "total": 90000},
            ],
            None,
        )
        data = live_open_estimates_report()
        self.assertTrue(data.is_live)
        self.assertEqual(len(data.rows), 1)
        self.assertEqual(data.rows[0]["estimate_number"], "E1")


class TestReportData(unittest.TestCase):
    def test_frozen_dataclass(self) -> None:
        data = ReportData(rows=[{"a": 1}], is_live=True)
        self.assertTrue(data.is_live)
        self.assertEqual(data.rows[0]["a"], 1)


if __name__ == "__main__":
    unittest.main()
