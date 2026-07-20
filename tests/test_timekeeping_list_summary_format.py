"""Tests for compact weekly timekeeping list summary formatting."""

from __future__ import annotations

import unittest
from datetime import date

from app.pages import timekeeping as tk


class TestFmtListSummaryHours(unittest.TestCase):
    def test_whole_hours_without_decimals(self) -> None:
        self.assertEqual(tk._fmt_list_summary_hours(40), "40")
        self.assertEqual(tk._fmt_list_summary_hours(40.0), "40")
        self.assertEqual(tk._fmt_list_summary_hours(0), "0")

    def test_fractional_hours_trimmed(self) -> None:
        self.assertEqual(tk._fmt_list_summary_hours(40.5), "40.5")
        self.assertEqual(tk._fmt_list_summary_hours(8.25), "8.2")

    def test_invalid_values_default_to_zero(self) -> None:
        self.assertEqual(tk._fmt_list_summary_hours(None), "0")
        self.assertEqual(tk._fmt_list_summary_hours("bad"), "0")

    def test_day_value_html_formats_match_summary(self) -> None:
        self.assertIn(">0<", tk._weekly_day_value_html(
            work_date=date(2026, 7, 20), hours=0, status="Draft", href="#"
        ))
        self.assertIn(">8<", tk._weekly_day_value_html(
            work_date=date(2026, 7, 20), hours=8, status="Draft", href="#"
        ))
        self.assertIn(">7.5<", tk._weekly_day_value_html(
            work_date=date(2026, 7, 20), hours=7.5, status="Draft", href="#"
        ))


if __name__ == "__main__":
    unittest.main()
