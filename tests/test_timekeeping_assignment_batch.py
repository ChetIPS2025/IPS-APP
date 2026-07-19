"""Tests for batched timekeeping assignment-option loading."""

from __future__ import annotations

import inspect
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import streamlit as st

from app.pages import timekeeping as tk
from app.services import tasks_service


class TestGetTasksForJobs(unittest.TestCase):
    def test_empty_job_ids_performs_no_query(self) -> None:
        with patch.object(tasks_service, "_fetch_tasks_rows_for_job_id_chunk") as fetch_mock:
            result = tasks_service.get_tasks_for_jobs([])
        fetch_mock.assert_not_called()
        self.assertEqual(result, {})

    @patch.object(tasks_service, "normalize_task", side_effect=lambda row: dict(row))
    def test_get_tasks_for_jobs_batches_query(self, _norm_mock) -> None:
        job_ids = [f"j{i}" for i in range(150)]
        fetch_mock = MagicMock(return_value=[])
        with patch.object(tasks_service, "_fetch_tasks_rows_for_job_id_chunk", fetch_mock):
            with patch.object(tasks_service, "_tasks_for_jobs_from_index", return_value={jid: [] for jid in job_ids}):
                tasks_service.get_tasks_for_jobs(job_ids, include_closed=True)
        self.assertEqual(fetch_mock.call_count, 2)
        first_chunk = fetch_mock.call_args_list[0].args[0]
        second_chunk = fetch_mock.call_args_list[1].args[0]
        self.assertEqual(len(first_chunk), 100)
        self.assertEqual(len(second_chunk), 50)

    @patch.object(tasks_service, "normalize_task", side_effect=lambda row: dict(row))
    def test_get_tasks_for_jobs_groups_and_preserves_job_order(self, _norm_mock) -> None:
        rows = [
            {"id": "t1", "job_id": "j2", "title": "B task", "due_date": "2026-07-02"},
            {"id": "t2", "job_id": "j1", "title": "A task", "due_date": "2026-07-01"},
            {"id": "t3", "job_id": "j1", "title": "Second", "due_date": "2026-07-03"},
        ]
        with patch.object(tasks_service, "_fetch_tasks_rows_for_job_id_chunk", return_value=rows):
            grouped = tasks_service.get_tasks_for_jobs(["j1", "j2"], include_closed=True)
        self.assertEqual(list(grouped.keys()), ["j1", "j2"])
        self.assertEqual([t["id"] for t in grouped["j1"]], ["t2", "t3"])
        self.assertEqual([t["id"] for t in grouped["j2"]], ["t1"])


class TestTimekeepingAssignmentOptionsBatch(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()
        tk.clear_timekeeping_assignment_options_cache()

    def test_build_does_not_call_get_tasks_by_job_in_loop(self) -> None:
        source = inspect.getsource(tk._build_assignment_options_for_timekeeping)
        self.assertIn("get_tasks_for_jobs", source)
        self.assertNotIn("get_tasks_by_job", source)

    @patch("app.services.tasks_service.get_tasks_for_jobs")
    @patch.object(tk, "load_jobs")
    def test_subjob_label_format_unchanged(self, load_jobs_mock, tasks_mock) -> None:
        load_jobs_mock.return_value = [
            {
                "id": "j1",
                "job_number": "100",
                "job_name": "Alpha",
                "status": "Active",
            },
        ]
        tasks_mock.return_value = {
            "j1": [
                {
                    "title": "Install",
                    "task_number": "01",
                }
            ]
        }
        with patch.object(tk, "_job_row_assignable_for_timekeeping", return_value=True):
            opts = tk._build_assignment_options_for_timekeeping()
        self.assertIn("100 — Alpha · 01: Install", opts)

    @patch("app.services.tasks_service.get_tasks_for_jobs", return_value={})
    @patch.object(tk, "load_jobs")
    def test_duplicate_labels_removed(self, load_jobs_mock, _tasks_mock) -> None:
        load_jobs_mock.return_value = [
            {"id": "j1", "job_number": "100", "job_name": "Alpha", "status": "Active"},
            {"id": "j2", "job_number": "100", "job_name": "Alpha", "status": "Active"},
        ]
        with patch.object(tk, "_job_row_assignable_for_timekeeping", return_value=True):
            opts = tk._build_assignment_options_for_timekeeping()
        self.assertEqual(opts.count("100 — Alpha"), 1)

    @patch("app.services.tasks_service.get_tasks_for_jobs", return_value={})
    @patch.object(tk, "load_jobs")
    def test_closed_jobs_excluded(self, load_jobs_mock, _tasks_mock) -> None:
        load_jobs_mock.return_value = [
            {"id": "j1", "job_number": "100", "job_name": "Open Job", "status": "Active"},
            {"id": "j2", "job_number": "200", "job_name": "Closed Job", "status": "Closed"},
        ]

        def _assignable(job: dict) -> bool:
            return str(job.get("status") or "") != "Closed"

        with patch.object(tk, "_job_row_assignable_for_timekeeping", side_effect=_assignable):
            opts = tk._build_assignment_options_for_timekeeping()
        self.assertIn("100 — Open Job", opts)
        self.assertNotIn("200 — Closed Job", opts)

    @patch("app.services.tasks_service.get_tasks_for_jobs", return_value={})
    @patch.object(tk, "load_jobs", return_value=[])
    def test_special_options_present(self, _jobs_mock, _tasks_mock) -> None:
        opts = tk._build_assignment_options_for_timekeeping()
        self.assertEqual(opts[0], "— No assignment —")
        self.assertIn("Shop", opts)
        self.assertIn("Administrative", opts)
        self.assertIn("Vacation", opts)

    @patch.object(tk, "_build_assignment_options_for_timekeeping")
    def test_cache_invalidates_when_catalog_versions_change(self, build_mock) -> None:
        from app.pages._core._data import (
            _bump_jobs_catalog_data_version,
            _bump_tasks_catalog_data_version,
        )

        build_mock.return_value = ["— No assignment —", "Cached Job"]
        week = date(2026, 7, 6)

        tk._assignment_options_for_timekeeping(week_start_d=week)
        tk._assignment_options_for_timekeeping(week_start_d=week)
        self.assertEqual(build_mock.call_count, 1)

        _bump_jobs_catalog_data_version()
        tk._assignment_options_for_timekeeping(week_start_d=week)
        self.assertEqual(build_mock.call_count, 2)

        _bump_tasks_catalog_data_version()
        tk._assignment_options_for_timekeeping(week_start_d=week)
        self.assertEqual(build_mock.call_count, 3)

    @patch.object(tk, "load_jobs", return_value=[{"id": "j1"}])
    def test_assignment_options_cache_sig_uses_catalog_versions(self, _jobs_mock) -> None:
        from app.pages._core._data import (
            jobs_catalog_data_version,
            tasks_catalog_data_version,
        )

        week = date(2026, 7, 6)
        self.assertEqual(
            tk._assignment_options_cache_sig(week_start_d=week),
            f"{week.isoformat()}:{jobs_catalog_data_version()}:{tasks_catalog_data_version()}",
        )

    def test_collapsed_list_does_not_build_assignment_options(self) -> None:
        collapsed = inspect.getsource(tk._render_timekeeping_employee_row_collapsed)
        row_body = inspect.getsource(tk._render_timekeeping_employee_row_body)
        render_src = inspect.getsource(tk.render)
        self.assertNotIn("_assignment_options_for_timekeeping", collapsed)
        self.assertNotIn("_build_assignment_options_for_timekeeping", collapsed)
        self.assertNotIn("_assignment_options_for_timekeeping", row_body)
        fast_return = render_src.split("summaries = _filter_summaries_for_field_user")[0]
        self.assertNotIn("_build_assignment_options_for_timekeeping", fast_return)


if __name__ == "__main__":
    unittest.main()
