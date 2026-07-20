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
        row_source = inspect.getsource(tk._render_timekeeping_employee_row)
        self.assertIn("_render_timekeeping_employee_row_body", row_source)
        self.assertNotIn("@fragment", row_source)

    def test_day_editor_session_keys_and_dialog(self) -> None:
        self.assertEqual(tk.SELECTED_TIME_EMPLOYEE_ID_KEY, "selected_time_employee_id")
        self.assertEqual(tk.SELECTED_TIME_DATE_KEY, "selected_time_date")
        self.assertEqual(tk.TIMEKEEPING_MODAL_EMPLOYEE_ID_KEY, "timekeeping_modal_employee_id")
        self.assertEqual(tk.TIMEKEEPING_MODAL_DATE_KEY, "timekeeping_modal_date")
        self.assertIn("@st.dialog", inspect.getsource(tk._show_day_time_dialog))
        self.assertIn("render_day_time_dialog_body", inspect.getsource(tk._show_day_time_dialog))

    def test_clickable_day_cell_uses_native_link(self) -> None:
        source = inspect.getsource(tk._render_clickable_list_day_cell)
        html_source = inspect.getsource(tk._clickable_list_day_cell_html)
        value_source = inspect.getsource(tk._weekly_day_value_html)
        self.assertIn("_clickable_list_day_cell_html", source)
        self.assertIn("_weekly_day_value_html", html_source)
        self.assertIn("timekeeping-weekly-day-link", value_source)
        self.assertIn('target="_self"', value_source)
        self.assertIn("_is_day_cell_selected", html_source)
        self.assertNotIn("st.button", source)
        self.assertNotIn("_open_day_time_editor", source)

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
    def test_collapsed_row_uses_embedded_batch_rows_not_session_grid(self, grid_mock) -> None:
        source = inspect.getsource(tk._render_timekeeping_employee_row_collapsed)
        self.assertIn("_daily_display_rows", source)
        self.assertNotIn("_ensure_weekly_grid", source)
        self.assertNotIn("_list_row_day_rows_for_display", source)

    @patch("app.services.timekeeping_service.list_timekeeping_days_for_week")
    def test_list_display_day_rows_uses_batch_cache(self, fetch_mock) -> None:
        fetch_mock.return_value = [
            {
                "employee_id": "emp-1",
                "work_date": "2026-07-07",
                "st_hours": 8,
                "ot_hours": 0,
                "dt_hours": 0,
                "status": "Draft",
            }
        ]
        week = date(2026, 7, 6)
        rows = tk._list_display_day_rows("emp-1", week)
        self.assertEqual(len(rows), 7)
        tuesday = next(r for r in rows if r.get("date") == "2026-07-07")
        self.assertEqual(tuesday.get("st"), 8.0)
        fetch_mock.assert_called_once_with(week)

    @patch("app.pages.timekeeping._ensure_weekly_grid")
    def test_open_day_editor_loads_session_grid(self, grid_mock) -> None:
        week = date(2026, 7, 6)
        tk._open_day_time_editor(
            eid="emp-1",
            work_date=date(2026, 7, 8),
            timecard_id="tc-1",
            week_start_d=week,
        )
        grid_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
