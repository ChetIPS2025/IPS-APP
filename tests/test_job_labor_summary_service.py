"""Tests for job labor summary from approved timekeeping."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.job_labor_summary_service import get_job_labor_summary


class TestJobLaborSummaryService(unittest.TestCase):
    @patch("app.services.job_labor_summary_service.fetch_table_admin")
    @patch("app.services.job_labor_summary_service._employees_map")
    @patch("app.services.job_labor_summary_service._fetch_job")
    def test_aggregates_approved_hours_only(
        self,
        job_mock,
        emp_map_mock,
        fetch_mock,
    ) -> None:
        job_mock.return_value = {"id": "job-1", "job_number": "100", "job_name": "Test"}
        emp_map_mock.return_value = {
            "emp-1": {"id": "emp-1", "name": "Alice", "hourly_rate": 40.0},
        }
        fetch_mock.return_value = [
            {
                "employee_id": "emp-1",
                "job_id": "job-1",
                "work_date": "2026-05-27",
                "st_hours": 8,
                "ot_hours": 2,
                "dt_hours": 0,
                "status": "Approved",
                "updated_at": "2026-05-28T12:00:00+00:00",
            },
            {
                "employee_id": "emp-1",
                "job_id": "job-1",
                "work_date": "2026-05-28",
                "st_hours": 4,
                "ot_hours": 0,
                "dt_hours": 0,
                "status": "Pending",
                "updated_at": "2026-05-28T13:00:00+00:00",
            },
        ]

        summary = get_job_labor_summary("job-1")
        self.assertEqual(summary["total_approved_hours"], 10.0)
        self.assertEqual(summary["st_hours"], 8.0)
        self.assertEqual(summary["ot_hours"], 2.0)
        self.assertEqual(len(summary["by_employee"]), 1)
        self.assertEqual(summary["by_employee"][0]["employee_name"], "Alice")
        self.assertTrue(summary["by_week"])
        self.assertEqual(summary["last_updated_display"], "2026-05-28")

    def test_empty_job_id(self) -> None:
        summary = get_job_labor_summary("")
        self.assertEqual(summary["total_approved_hours"], 0.0)
        self.assertEqual(summary["by_employee"], [])


if __name__ == "__main__":
    unittest.main()
