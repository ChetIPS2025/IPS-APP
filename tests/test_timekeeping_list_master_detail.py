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

    def test_rows_use_clickable_day_cells_not_expand(self) -> None:
        collapsed_source = inspect.getsource(tk._render_timekeeping_employee_row_collapsed)
        self.assertIn("_render_clickable_list_day_cell", collapsed_source)
        self.assertNotIn("tk_expand_", collapsed_source)
        self.assertIn("_WEEKLY_TS_LIST_ROW_COLS", collapsed_source)
        self.assertIn('gap="small"', collapsed_source)

    def test_row_body_is_always_compact(self) -> None:
        source = inspect.getsource(tk._render_timekeeping_employee_row_body)
        self.assertIn("_render_timekeeping_employee_row_collapsed", source)
        self.assertNotIn("_render_timekeeping_expand_fragment", source)
        fragment_source = inspect.getsource(tk._render_timekeeping_employee_row_fragment)
        self.assertIn("_render_timekeeping_employee_row_body", fragment_source)
        self.assertNotIn("not expanded and not pending", fragment_source)

    def test_day_editor_session_keys_and_dialog(self) -> None:
        self.assertEqual(tk.SELECTED_TIME_EMPLOYEE_ID_KEY, "selected_time_employee_id")
        self.assertEqual(tk.SELECTED_TIME_DATE_KEY, "selected_time_date")
        self.assertEqual(tk.TIMEKEEPING_MODAL_EMPLOYEE_ID_KEY, "timekeeping_modal_employee_id")
        self.assertEqual(tk.TIMEKEEPING_MODAL_DATE_KEY, "timekeeping_modal_date")
        self.assertIn("@st.dialog", inspect.getsource(tk._show_day_time_dialog))
        self.assertIn("render_day_time_dialog_body", inspect.getsource(tk._show_day_time_dialog))

    def test_clickable_day_cell_opens_editor(self) -> None:
        source = inspect.getsource(tk._render_clickable_list_day_cell)
        self.assertIn('key=f"open_time_day_{eid}_{iso}"', source)
        self.assertIn("_open_day_time_editor", source)
        self.assertIn("_is_day_cell_selected", source)
        self.assertIn("_timekeeping_app_rerun", source)

    def test_split_layout_and_panel_rendering(self) -> None:
        render_source = inspect.getsource(tk.render)
        self.assertIn("weekly_timekeeping_layout", render_source)
        self.assertIn("_render_day_time_entry_panel", render_source)
        self.assertIn("_render_timekeeping_table_area", render_source)
        self.assertIn("ensure_narrow_viewport_detected", render_source)
        self.assertIn("not _is_narrow_viewport()", render_source)

    def test_weekly_toolbar_and_mockup_labels(self) -> None:
        self.assertIn("_render_weekly_timekeeping_toolbar", inspect.getsource(tk.render))
        self.assertIn("Weekly Timekeeping", inspect.getsource(tk.render))
        self.assertIn("View and manage weekly employee time entries.", inspect.getsource(tk.render))
        toolbar_source = inspect.getsource(tk._render_weekly_timekeeping_toolbar)
        self.assertIn("ips-timekeeping-week-helper", toolbar_source)
        self.assertEqual(tk._LIST_VIEW_SUMMARY_LABELS[0], "ST (≤40)")
        self.assertEqual(tk._LIST_VIEW_SUMMARY_LABELS[1], "OT (>40)")

    def test_weekly_row_has_twelve_columns(self) -> None:
        self.assertEqual(len(tk._WEEKLY_TS_LIST_ROW_COLS), 12)

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
