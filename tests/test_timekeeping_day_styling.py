"""Tests for timekeeping fully-approved day styling helpers."""

from __future__ import annotations

import unittest

from app.services.timekeeping_day_ui import (
    day_fully_approved_and_allocated,
    list_day_box_marker_classes,
    list_day_status_badge_html,
)


class TestTimekeepingDayStyling(unittest.TestCase):
    def test_fully_approved_requires_both_conditions(self) -> None:
        self.assertTrue(day_fully_approved_and_allocated("complete", "Approved"))
        self.assertFalse(day_fully_approved_and_allocated("complete", "Pending"))
        self.assertFalse(day_fully_approved_and_allocated("incomplete", "Approved"))
        self.assertFalse(day_fully_approved_and_allocated("overallocated", "Approved"))

    def test_marker_class_for_fully_approved_day(self) -> None:
        cls = list_day_box_marker_classes(
            day_status="Approved",
            alloc_state="complete",
            has_hours=True,
        )
        self.assertIn("ips-tk-day-approved-complete", cls)
        self.assertNotIn("ips-tk-day-approved ", cls.strip())

    def test_status_badge_is_green_pill_when_fully_approved(self) -> None:
        html = list_day_status_badge_html("Approved", "complete")
        self.assertIn("ips-timekeeping-status-pill-day-box", html)
        self.assertIn("APPROVED", html)


if __name__ == "__main__":
    unittest.main()
