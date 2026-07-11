"""Tests for timekeeping master-detail list rendering."""

from __future__ import annotations

import inspect
import unittest
from datetime import date
from unittest.mock import patch

import streamlit as st

from app.pages import timekeeping as tk


class TestTimekeepingListMasterDetail(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()
        tk.clear_timekeeping_list_caches()

    def test_collapsed_rows_skip_fragment_wrapper(self) -> None:
        source = inspect.getsource(tk._render_timekeeping_employee_row_fragment)
        self.assertIn("not expanded and not pending", source)
        self.assertIn("_render_timekeeping_employee_row_body", source)

    def test_row_body_branches_on_expanded_state(self) -> None:
        source = inspect.getsource(tk._render_timekeeping_employee_row_body)
        self.assertIn("_render_timekeeping_employee_row_collapsed", source)
        self.assertIn("_render_list_row_day_cell(", source)
        collapsed_source = inspect.getsource(tk._render_timekeeping_employee_row_collapsed)
        self.assertIn("_build_collapsed_timecard_row_html", collapsed_source)
        build_source = inspect.getsource(tk._build_collapsed_timecard_row_html)
        self.assertIn("weekly-timecard-row-collapsed", build_source)
        html = tk._build_collapsed_timecard_row_html(
            employee_name="Amanda M. Robicheaux",
            days=[date(2026, 7, 6 + i) for i in range(7)],
            grid=None,
            st_total=32.0,
            ot_total=0.0,
            total_hours=32.0,
            status="Draft",
        )
        self.assertIn('class="day-cell"', html)
        self.assertIn('class="day-date"', html)
        self.assertIn('class="day-state"', html)
        self.assertIn('class="day-value"', html)
        self.assertIn('class="total-cell"', html)
        self.assertIn('class="employee-cell"', html)
        self.assertIn("<span class=\"day-date\">", html)
        self.assertIn("<span class=\"day-state\">", html)
        self.assertIn("<span class=\"day-value\">", html)

    @patch("app.pages.timekeeping._ensure_weekly_grid")
    @patch("app.pages.timekeeping._ensure_week_days_by_employee")
    def test_preload_warms_grids_for_visible_rows(self, week_mock, grid_mock) -> None:
        week_mock.return_value = {}
        rows = [
            {"employee_id": "emp-1", "id": "emp-1", "timecard_id": "tc-1"},
            {"employee_id": "emp-2", "id": "emp-2", "timecard_id": "tc-2"},
        ]
        tk._preload_weekly_grids_for_rows(rows, date(2026, 7, 6))
        week_mock.assert_called_once()
        self.assertEqual(grid_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
