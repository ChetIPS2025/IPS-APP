"""Tests for Jobs table status pill display labels."""

from __future__ import annotations

import unittest

from app.components.job_status_ui import job_status_pill_class, job_status_table_label


class TestJobStatusTableLabel(unittest.TestCase):
    def test_preserves_granular_status_labels(self) -> None:
        self.assertEqual(job_status_table_label("Pending"), "Pending")
        self.assertEqual(job_status_table_label("Scheduled"), "Scheduled")
        self.assertEqual(job_status_table_label("On Hold"), "On Hold")

    def test_maps_closed_family_to_closed(self) -> None:
        self.assertEqual(job_status_table_label("Closed"), "Closed")
        self.assertEqual(job_status_table_label("Cancelled"), "Closed")
        self.assertEqual(job_status_table_label("Archived"), "Closed")

    def test_completed_shows_complete(self) -> None:
        self.assertEqual(job_status_table_label("Completed"), "Complete")

    def test_pill_classes_match_color_scheme(self) -> None:
        self.assertEqual(job_status_pill_class("Active"), "ips-job-status-active")
        self.assertEqual(job_status_pill_class("Pending"), "ips-job-status-pending")
        self.assertEqual(job_status_pill_class("Complete"), "ips-job-status-completed")
        self.assertEqual(job_status_pill_class("Scheduled"), "ips-job-status-scheduled")
        self.assertEqual(job_status_pill_class("On Hold"), "ips-job-status-on-hold")
        self.assertEqual(job_status_pill_class("Closed"), "ips-job-status-closed")


if __name__ == "__main__":
    unittest.main()
