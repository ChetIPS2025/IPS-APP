"""Tests for weekly timekeeping list row layout and day cell rendering."""

from __future__ import annotations

import inspect
import re
import unittest
from datetime import date
from unittest.mock import patch

import streamlit as st

from app.pages import timekeeping as tk
from app.services.weekly_timekeeping_service import _timekeeping_employee_id


class TestWeeklyDayValueHtml(unittest.TestCase):
    def test_zero_renders_visible_zero(self) -> None:
        html = tk._weekly_day_value_html(
            work_date=date(2026, 7, 20),
            hours=0.0,
            status="Draft",
            href="?tk_employee=e1&tk_date=2026-07-20",
        )
        self.assertIn(">0<", html)
        self.assertIn("timekeeping-weekly-day-hours", html)

    def test_eight_hour_monday(self) -> None:
        html = tk._weekly_day_value_html(
            work_date=date(2026, 7, 20),
            hours=8.0,
            status="Draft",
            href="?tk_employee=e1&tk_date=2026-07-20",
        )
        self.assertIn(">8<", html)

    def test_fractional_hours(self) -> None:
        html = tk._weekly_day_value_html(
            work_date=date(2026, 7, 21),
            hours=7.5,
            status="Draft",
            href="?tk_employee=e1&tk_date=2026-07-21",
        )
        self.assertIn(">7.5<", html)

    def test_query_failure_renders_dash_not_zero(self) -> None:
        html = tk._weekly_day_value_html(
            work_date=date(2026, 7, 20),
            hours=0.0,
            status="Draft",
            href="#",
            hours_unknown=True,
        )
        self.assertIn(">—<", html)
        self.assertNotIn(">0<", html)


class TestTimekeepingEmployeeId(unittest.TestCase):
    def test_prefers_employee_id_over_summary_id(self) -> None:
        row = {"employee_id": "emp-real", "id": "timecard-uuid"}
        self.assertEqual(_timekeeping_employee_id(row), "emp-real")

    def test_falls_back_to_id_when_no_employee_id(self) -> None:
        row = {"id": "emp-1"}
        self.assertEqual(_timekeeping_employee_id(row), "emp-1")

    def test_matching_daily_rows_by_employee_id(self) -> None:
        from app.services.weekly_timekeeping_service import aggregate_daily_display_rows

        week = date(2026, 7, 20)
        summary_eid = _timekeeping_employee_id({"employee_id": "emp-1", "id": "tc-9"})
        rows = aggregate_daily_display_rows(
            [
                {
                    "employee_id": "emp-1",
                    "work_date": "2026-07-20",
                    "st_hours": 8,
                    "ot_hours": 0,
                    "dt_hours": 0,
                }
            ],
            week,
        )
        batch = {"emp-1": [{"employee_id": "emp-1", "work_date": "2026-07-20", "st_hours": 8}]}
        matched = aggregate_daily_display_rows(batch.get(summary_eid, []), week)
        self.assertEqual(matched[0]["st"], rows[0]["st"])

    def test_timecard_id_in_summary_id_does_not_match_daily_rows(self) -> None:
        from app.services.weekly_timekeeping_service import aggregate_daily_display_rows

        week = date(2026, 7, 20)
        wrong_key = _timekeeping_employee_id({"id": "timecard-99"})
        daily = aggregate_daily_display_rows(
            [{"employee_id": "emp-1", "work_date": "2026-07-20", "st_hours": 8}],
            week,
        )
        wrong = aggregate_daily_display_rows([], week)
        self.assertEqual(daily[0]["st"], 8.0)
        self.assertEqual(wrong[0]["st"], 0.0)
        self.assertNotEqual(wrong_key, "emp-1")


class TestCollapsedRowRenderer(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()
        tk.clear_timekeeping_list_caches()

    def test_collapsed_row_uses_twelve_column_layout(self) -> None:
        source = inspect.getsource(tk._render_timekeeping_employee_row_collapsed)
        self.assertIn("st.columns(_WEEKLY_TS_LIST_ROW_COLS", source)
        self.assertIn("row_cols[1:8]", source)
        self.assertIn("row_cols[8]", source)
        self.assertIn("row_cols[11]", source)

    def test_collapsed_row_does_not_load_session_grid_or_assignment_options(self) -> None:
        source = inspect.getsource(tk._render_timekeeping_employee_row_collapsed)
        self.assertNotIn("_ensure_weekly_grid", source)
        self.assertNotIn("_ensure_allocation_state", source)
        self.assertNotIn("_assignment_options_for_timekeeping", source)
        self.assertNotIn("_list_row_day_rows_for_display", source)

    @patch("app.pages.timekeeping._render_clickable_list_day_cell")
    def test_row_renderer_invokes_daily_cell_renderer_seven_times(self, cell_mock) -> None:
        week = date(2026, 7, 20)
        days = [date(2026, 7, 20 + i) for i in range(7)]
        row = {
            "timecard_id": "emp-1_2026-07-20",
            "employee_id": "emp-1",
            "employee_name": "Pat Example",
            "st_total": 0,
            "ot_total": 0,
            "total_hours": 0,
            "status": "Draft",
            "_daily_display_rows": [
                {"date": d.isoformat(), "st": 0.0, "ot": 0.0, "dt": 0.0, "status": "Draft"}
                for d in days
            ],
        }
        tk._render_timekeeping_employee_row_collapsed(
            row,
            week_start_d=week,
            days=days,
            timecard_id="emp-1_2026-07-20",
            emp={"id": "emp-1", "name": "Pat Example"},
            employee_name="Pat Example",
            eid="emp-1",
        )
        self.assertEqual(cell_mock.call_count, 7)

    def test_fifteen_employees_produce_one_hundred_five_day_cells(self) -> None:
        week = date(2026, 7, 20)
        days = [date(2026, 7, 20 + i) for i in range(7)]
        html_parts = []
        for n in range(15):
            for day in days:
                html_parts.append(
                    tk._weekly_day_value_html(
                        work_date=day,
                        hours=0.0,
                        status="Draft",
                        href=f"?tk_employee=emp-{n}&tk_date={day.isoformat()}",
                    )
                )
        self.assertEqual(len(html_parts), 105)
        self.assertTrue(all("timekeeping-weekly-day-hours" in part for part in html_parts))

    def test_page_ready_marker_after_weekly_list(self) -> None:
        source = inspect.getsource(tk._render_custom_timekeeping_table)
        self.assertIn("ips-page-ready ips-timekeeping-page-ready", source)
        match = re.search(
            r"for row in filtered:.*?ips-page-ready ips-timekeeping-page-ready",
            source,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)


class TestWeeklyDayCellHtml(unittest.TestCase):
    def test_clickable_cell_delegates_to_weekly_day_value_html(self) -> None:
        html = tk._clickable_list_day_cell_html(
            day_d=date(2026, 7, 20),
            day_ix=0,
            day_row={"st": 8.0, "ot": 0.0, "dt": 0.0, "status": "Draft"},
            eid="emp-1",
            timecard_id="emp-1_2026-07-20",
        )
        self.assertIn("timekeeping-weekly-day-link", html)
        self.assertIn(">8<", html)
        self.assertIn("timekeeping-day-cell-clickable-marker", html)

    def test_monday_and_sunday_in_week_batch(self) -> None:
        from app.services.weekly_timekeeping_service import aggregate_daily_display_rows

        week = date(2026, 7, 20)
        rows = aggregate_daily_display_rows([], week)
        self.assertEqual(rows[0]["date"], "2026-07-20")
        self.assertEqual(rows[-1]["date"], "2026-07-26")


if __name__ == "__main__":
    unittest.main()
