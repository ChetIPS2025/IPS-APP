"""Tests for timekeeping assignment-option caching."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

import streamlit as st

from app.pages import timekeeping as tk


class TestTimekeepingAssignmentOptionsCache(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()
        tk.clear_timekeeping_assignment_options_cache()

    @patch("app.services.tasks_service.get_tasks_for_jobs", return_value={})
    @patch.object(tk, "load_jobs")
    def test_build_assignment_options_includes_jobs_and_specials(
        self,
        load_jobs_mock,
        _tasks_mock,
    ) -> None:
        load_jobs_mock.return_value = [
            {
                "id": "j1",
                "job_number": "100",
                "job_name": "Alpha",
                "status": "Active",
            },
        ]
        with patch.object(tk, "_job_row_assignable_for_timekeeping", return_value=True):
            opts = tk._build_assignment_options_for_timekeeping()
        self.assertEqual(opts[0], "— No assignment —")
        self.assertIn("100 — Alpha", opts)
        self.assertIn("Shop", opts)
        self.assertIn("Administrative", opts)
        self.assertIn("Vacation", opts)

    @patch.object(tk, "_build_assignment_options_for_timekeeping")
    @patch.object(tk, "load_jobs", return_value=[{"id": "j1"}])
    def test_assignment_options_cached_until_cleared(
        self,
        _jobs_mock,
        build_mock,
    ) -> None:
        build_mock.return_value = ["— No assignment —", "Cached Job"]
        week = date(2026, 7, 6)

        first = tk._assignment_options_for_timekeeping(week_start_d=week)
        second = tk._assignment_options_for_timekeeping(week_start_d=week)

        self.assertEqual(first, second)
        build_mock.assert_called_once()

        tk.clear_timekeeping_assignment_options_cache()
        third = tk._assignment_options_for_timekeeping(week_start_d=week)
        self.assertEqual(third, first)
        self.assertEqual(build_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
