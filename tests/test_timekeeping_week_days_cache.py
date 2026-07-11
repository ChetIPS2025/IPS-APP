"""Tests for timekeeping week day-row batch cache."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

import streamlit as st

from app.pages import timekeeping as tk


class TestTimekeepingWeekDaysCache(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()
        tk.clear_timekeeping_list_caches()

    @patch("app.services.timekeeping_service.list_timekeeping_days_for_week")
    def test_week_days_loaded_once_per_week(self, fetch_mock) -> None:
        fetch_mock.return_value = [
            {"employee_id": "emp-1", "work_date": "2026-07-07", "week_start": "2026-07-06"},
            {"employee_id": "emp-2", "work_date": "2026-07-07", "week_start": "2026-07-06"},
        ]
        week = date(2026, 7, 6)

        first = tk._ensure_week_days_by_employee(week)
        second = tk._ensure_week_days_by_employee(week)

        self.assertEqual(first, second)
        fetch_mock.assert_called_once_with(week)
        self.assertEqual(tk._day_rows_for_employee("emp-1", week)[0]["employee_id"], "emp-1")

    @patch("app.services.timekeeping_service.list_timekeeping_days_for_week")
    def test_clear_list_caches_forces_reload(self, fetch_mock) -> None:
        fetch_mock.return_value = []
        week = date(2026, 7, 6)
        tk._ensure_week_days_by_employee(week)
        tk.clear_timekeeping_list_caches()
        tk._ensure_week_days_by_employee(week)
        self.assertEqual(fetch_mock.call_count, 2)

    def test_build_timecard_row_uses_summary_status_without_grid_load(self) -> None:
        with patch.object(tk, "_resolved_week_status") as status_mock:
            built = tk._build_timecard_row(
                {
                    "id": "emp-9",
                    "name": "Pat Example",
                    "status": "Pending",
                    "st_total": 40,
                    "ot_total": 2,
                    "dt_total": 0,
                },
                date(2026, 7, 6),
            )
        status_mock.assert_not_called()
        self.assertEqual(built["status"], "Pending")


if __name__ == "__main__":
    unittest.main()
