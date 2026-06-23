"""Tests for simplified job status normalization."""

from __future__ import annotations

import unittest

from app.services.jobs_service import MANUAL_JOB_STATUSES, normalize_job_status


class TestJobStatusNormalization(unittest.TestCase):
    def test_manual_statuses(self) -> None:
        self.assertEqual(MANUAL_JOB_STATUSES, ("Active", "On Hold", "Completed", "Cancelled"))

    def test_legacy_statuses_map_to_active(self) -> None:
        for raw in ("Draft", "Pending", "Awarded", "Estimate Pending", "Planning", ""):
            self.assertEqual(normalize_job_status(raw), "Active", msg=raw)

    def test_canonical_statuses_preserved(self) -> None:
        self.assertEqual(normalize_job_status("On Hold"), "On Hold")
        self.assertEqual(normalize_job_status("Completed"), "Completed")
        self.assertEqual(normalize_job_status("Cancelled"), "Cancelled")
        self.assertEqual(normalize_job_status("Closed"), "Completed")

    def test_lifecycle_statuses(self) -> None:
        self.assertEqual(normalize_job_status("Archived"), "Archived")
        self.assertEqual(normalize_job_status("Deleted"), "Deleted")


if __name__ == "__main__":
    unittest.main()
