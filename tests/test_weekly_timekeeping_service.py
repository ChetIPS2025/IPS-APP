"""Tests for weekly timekeeping list snapshot service."""

from __future__ import annotations

import inspect
import unittest
from datetime import date
from unittest.mock import patch

import streamlit as st

from app.pages import timekeeping as tk
from app.services.weekly_timekeeping_service import (
    aggregate_daily_display_rows,
    invalidate_weekly_timekeeping_page_cache,
    load_weekly_timekeeping_page,
    normalize_work_date,
)


class TestWeeklyTimekeepingService(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()
        tk.clear_timekeeping_list_caches()

    def test_normalize_work_date_strips_timestamp(self) -> None:
        self.assertEqual(normalize_work_date("2026-07-20T05:00:00+00:00"), "2026-07-20")

    def test_aggregate_sums_multiple_allocation_rows_same_date(self) -> None:
        week = date(2026, 7, 20)
        rows = aggregate_daily_display_rows(
            [
                {
                    "work_date": "2026-07-20",
                    "st_hours": 4,
                    "ot_hours": 0,
                    "dt_hours": 0,
                },
                {
                    "work_date": "2026-07-20",
                    "st_hours": 2,
                    "ot_hours": 2,
                    "dt_hours": 0,
                },
            ],
            week,
        )
        monday = rows[0]
        self.assertEqual(monday["st"], 6.0)
        self.assertEqual(monday["ot"], 2.0)
        self.assertEqual(monday["st"] + monday["ot"], 8.0)

    def test_aggregate_includes_monday_and_sunday(self) -> None:
        week = date(2026, 7, 20)
        rows = aggregate_daily_display_rows(
            [
                {"work_date": "2026-07-20", "st_hours": 8, "ot_hours": 0, "dt_hours": 0},
                {"work_date": "2026-07-26", "st_hours": 0, "ot_hours": 0, "dt_hours": 4},
            ],
            week,
        )
        self.assertEqual(rows[0]["date"], "2026-07-20")
        self.assertEqual(rows[0]["st"], 8.0)
        self.assertEqual(rows[-1]["date"], "2026-07-26")
        self.assertEqual(rows[-1]["dt"], 4.0)

    def test_aggregate_zero_day_renders_zero_not_unknown(self) -> None:
        week = date(2026, 7, 20)
        rows = aggregate_daily_display_rows([], week)
        self.assertEqual(len(rows), 7)
        self.assertFalse(rows[0]["hours_unknown"])
        self.assertEqual(rows[0]["st"], 0.0)

    def test_query_failure_marks_hours_unknown(self) -> None:
        week = date(2026, 7, 20)
        rows = aggregate_daily_display_rows([], week, hours_unknown=True)
        self.assertTrue(all(row["hours_unknown"] for row in rows))

    @patch("app.services.weekly_timekeeping_service.load_timekeeping_summaries")
    @patch("app.services.weekly_timekeeping_service._load_week_days_batch")
    def test_load_page_uses_single_batch_and_builds_rows(self, batch_mock, summaries_mock) -> None:
        week = date(2026, 7, 20)
        summaries_mock.return_value = [
            {
                "id": "emp-1",
                "name": "Pat Example",
                "st_total": 8,
                "ot_total": 0,
                "dt_total": 0,
                "status": "Draft",
            }
        ]
        batch_mock.return_value = (
            {
                "emp-1": [
                    {
                        "employee_id": "emp-1",
                        "work_date": "2026-07-20",
                        "st_hours": 8,
                        "ot_hours": 0,
                        "dt_hours": 0,
                    }
                ]
            },
            True,
            None,
        )
        page = load_weekly_timekeeping_page(week_start=week, role="admin")
        self.assertEqual(page.total_count, 1)
        self.assertEqual(page.employees[0]["monday_hours"], 8.0)
        self.assertEqual(page.employees[0]["st_total"], 8.0)
        batch_mock.assert_called_once()

    @patch("app.services.weekly_timekeeping_service.load_timekeeping_summaries")
    @patch("app.services.weekly_timekeeping_service._load_week_days_batch")
    def test_failed_batch_is_not_cached(self, batch_mock, summaries_mock) -> None:
        week = date(2026, 7, 20)
        summaries_mock.return_value = [{"id": "emp-1", "name": "Pat", "status": "Draft"}]
        batch_mock.return_value = ({}, False, "db error")
        first = load_weekly_timekeeping_page(week_start=week, role="admin")
        second = load_weekly_timekeeping_page(week_start=week, role="admin")
        self.assertFalse(first.days_loaded)
        self.assertEqual(first.warning, "Daily time entries could not be loaded.")
        self.assertEqual(batch_mock.call_count, 2)
        self.assertTrue(all(row["_daily_display_rows"][0]["hours_unknown"] for row in first.employees))

    def test_invalidate_clears_week_snapshot_cache(self) -> None:
        week = date(2026, 7, 20)
        st.session_state["_ips_page_data_cache"] = {
            "weekly_timekeeping_page:2026-07-20:admin:1:50:0:emp=:status=": object(),
            "timekeeping_summaries:2026-07-20": object(),
        }
        st.session_state["ips_tk_week_days_sig"] = "2026-07-20"
        st.session_state["ips_tk_week_days_by_employee"] = {"emp-1": []}
        invalidate_weekly_timekeeping_page_cache(week)
        store = st.session_state["_ips_page_data_cache"]
        self.assertFalse(any(str(k).startswith("weekly_timekeeping_page:2026-07-20:") for k in store))
        self.assertNotIn("timekeeping_summaries:2026-07-20", store)
        self.assertNotIn("ips_tk_week_days_sig", st.session_state)


class TestTimekeepingEmployeeIdService(unittest.TestCase):
    def test_prefers_employee_id_for_batch_grouping(self) -> None:
        from app.services.weekly_timekeeping_service import _timekeeping_employee_id

        self.assertEqual(
            _timekeeping_employee_id({"employee_id": "emp-1", "id": "timecard-1"}),
            "emp-1",
        )

    def test_build_row_sets_daily_hours_unknown_on_failure(self) -> None:
        from app.services.weekly_timekeeping_service import _build_employee_row

        week = date(2026, 7, 20)
        row = _build_employee_row(
            {"employee_id": "emp-1", "name": "Pat", "status": "Draft"},
            week_start_d=week,
            week_days_by_employee={},
            days_loaded=False,
            hours_unknown=True,
        )
        self.assertTrue(row["_daily_hours_unknown"])
        self.assertTrue(row["_daily_display_rows"][0]["hours_unknown"])


class TestWeeklyTimekeepingRenderGuards(unittest.TestCase):
    def test_render_uses_weekly_snapshot_without_spinner(self) -> None:
        source = inspect.getsource(tk.render)
        self.assertIn("load_weekly_timekeeping_page", source)
        self.assertIn("timekeeping.page_shell", source)
        self.assertNotIn('st.spinner("Loading weekly timecards', source)

    def test_collapsed_row_does_not_build_session_grid(self) -> None:
        source = inspect.getsource(tk._render_timekeeping_employee_row_collapsed)
        self.assertNotIn("_ensure_weekly_grid", source)
        self.assertNotIn("_list_row_day_rows_for_display", source)
        self.assertNotIn("st.number_input", source)

    def test_stable_render_does_not_call_st_rerun_in_list_fragment(self) -> None:
        source = inspect.getsource(tk._render_timekeeping_table_area)
        self.assertNotIn("st.rerun()", source)
        self.assertNotIn("ips_app_rerun()", source)


if __name__ == "__main__":
    unittest.main()
