"""Tests for shared date helpers used by Streamlit date inputs."""

from __future__ import annotations

import inspect
import unittest
from datetime import date, datetime

from app.pages import timekeeping as tk
from app.utils.dates import DATE_INPUT_FORMAT, normalize_date


class NormalizeDateTests(unittest.TestCase):
    def test_normalize_date_accepts_date_and_datetime(self) -> None:
        d = date(2026, 7, 13)
        self.assertEqual(normalize_date(d), d)
        self.assertEqual(normalize_date(datetime(2026, 7, 13, 9, 30)), d)

    def test_normalize_date_parses_iso_strings(self) -> None:
        self.assertEqual(normalize_date("2026-07-13"), date(2026, 7, 13))
        self.assertEqual(normalize_date("2026-07-13T15:00:00"), date(2026, 7, 13))

    def test_normalize_date_returns_none_for_invalid_values(self) -> None:
        self.assertIsNone(normalize_date(None))
        self.assertIsNone(normalize_date(""))
        self.assertIsNone(normalize_date("not-a-date"))
        self.assertIsNone(normalize_date(42))


class StreamlitDateInputFormatTests(unittest.TestCase):
    def test_date_input_format_is_streamlit_compatible(self) -> None:
        self.assertEqual(DATE_INPUT_FORMAT, "MM/DD/YYYY")

    def test_timekeeping_page_uses_supported_date_input_format(self) -> None:
        src = inspect.getsource(tk.render)
        self.assertNotIn("show_date_range=True", src)
        self.assertNotIn("date_range_key=\"tk_hdr_week_range\"", src)
        self.assertNotIn('format="MMM D, YYYY"', src)
        self.assertNotIn("format='MMM D, YYYY'", src)

    def test_timekeeping_week_toolbar_uses_date_range_picker(self) -> None:
        src = inspect.getsource(tk._render_weekly_timekeeping_toolbar)
        self.assertIn("st.popover", src)
        self.assertIn("st.date_input", src)
        self.assertIn("tk_week_range_picker", src)
        self.assertIn("Week of", src)
        self.assertIn("format=DATE_INPUT_FORMAT", src)
        self.assertNotIn("ips-timekeeping-week-pill", src)
        self.assertNotIn("tk_prev_week", src)
        self.assertNotIn("tk_next_week", src)


if __name__ == "__main__":
    unittest.main()
