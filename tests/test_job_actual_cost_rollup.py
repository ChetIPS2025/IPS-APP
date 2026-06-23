"""Tests for jobs.actual_cost rollup helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.job_cost_transaction_service import (
    refresh_job_actual_cost,
    sum_actual_cost_for_job,
)


class TestJobActualCostRollup(unittest.TestCase):
    @patch("app.services.job_cost_transaction_service.fetch_job_cost_transactions")
    def test_sum_actual_cost_for_job(self, fetch_mock) -> None:
        fetch_mock.return_value = [
            {"total_cost": 100.0},
            {"total_cost": 42.5},
            {"total_cost": "7.50"},
        ]
        self.assertEqual(sum_actual_cost_for_job("job-1"), 150.0)

    @patch("app.services.job_cost_transaction_service._invalidate_jobs_list_cache")
    @patch("app.services.job_cost_transaction_service.sum_actual_cost_for_job", return_value=250.0)
    @patch("app.services.phase2_modules_service.table_column_names")
    @patch("app.services.job_cost_transaction_service._db")
    def test_refresh_job_actual_cost_updates_jobs_row(
        self,
        db_mock,
        cols_mock,
        sum_mock,
        _cache_mock,
    ) -> None:
        cols_mock.return_value = ["id", "actual_cost", "updated_at"]
        db = MagicMock()
        db_mock.return_value = db
        refresh_job_actual_cost("job-1")
        db.update_rows.assert_called_once()
        args = db.update_rows.call_args[0]
        self.assertEqual(args[0], "jobs")
        self.assertEqual(args[1]["actual_cost"], 250.0)
        self.assertEqual(args[2], {"id": "job-1"})


if __name__ == "__main__":
    unittest.main()
