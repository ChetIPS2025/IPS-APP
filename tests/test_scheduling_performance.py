"""Tests for Scheduling module performance and lazy-loading regressions."""

from __future__ import annotations

import inspect
import unittest
from datetime import date
from unittest.mock import patch

import streamlit as st

from app.components.scheduling_dialogs import SCHED_OPEN_DETAIL_KEY
from app.pages import scheduling as scheduling_page
from app.services.scheduling_conflict_batch_service import view_mode_needs_conflict_flags
from app.services.scheduling_page_service import SchedulingPageSnapshot, load_scheduling_page_snapshot
from app.services.scheduling_reference_service import get_jobs_by_ids, rows_to_by_id
from app.services.scheduling_service import scheduling_data_version


class TestSchedulingHeaderBeforeSnapshot(unittest.TestCase):
    def test_render_page_header_before_snapshot_query(self) -> None:
        src = inspect.getsource(scheduling_page.render)
        header_idx = src.index("render_page_header(")
        snapshot_idx = src.index("load_scheduling_page_snapshot(")
        assert header_idx < snapshot_idx


class TestSchedulingReferenceLoading(unittest.TestCase):
    def test_get_jobs_by_ids_does_not_load_full_catalog(self) -> None:
        with patch(
            "app.services.scheduling_reference_service._fetch_rows_by_ids",
            return_value=[{"id": "job-1", "job_number": "J001", "job_name": "Alpha"}],
        ) as fetch_mock:
            with patch("app.pages._core._data.load_jobs") as load_mock:
                rows = get_jobs_by_ids(["job-1"])
        fetch_mock.assert_called_once()
        load_mock.assert_not_called()
        assert rows[0]["id"] == "job-1"

    def test_week_view_snapshot_does_not_call_load_employees(self) -> None:
        fake_snapshot = SchedulingPageSnapshot(
            week_start=date(2026, 7, 13),
            week_end=date(2026, 7, 20),
            events=[],
            employee_assignments_by_event={},
            asset_assignments_by_event={},
            conflict_event_ids=set(),
            jobs_by_id={},
            employees_by_id={},
            assets_by_id={},
            customers_by_id={},
        )
        with patch(
            "app.services.scheduling_page_service.page_data_cache_get",
            return_value=fake_snapshot,
        ):
            with patch("app.pages._core._data.load_employees") as load_employees:
                with patch("app.pages._core._data.load_jobs") as load_jobs:
                    with patch("app.pages._core._data.load_assets") as load_assets:
                        with patch("app.pages._core._data.load_customers") as load_customers:
                            snap = load_scheduling_page_snapshot(
                                week_start=date(2026, 7, 13),
                                week_end=date(2026, 7, 20),
                                selected_day=date(2026, 7, 13),
                                view_mode="Week",
                                filters={},
                            )
        load_employees.assert_not_called()
        load_jobs.assert_not_called()
        load_assets.assert_not_called()
        load_customers.assert_not_called()
        assert snap.events == []


class TestSchedulingAssignmentDedup(unittest.TestCase):
    def test_snapshot_queries_assignments_once(self) -> None:
        calls: list[tuple[str, tuple]] = []

        def _emp(start, end, **kwargs):
            calls.append(("emp", (start, end)))
            return []

        def _asset(start, end, **kwargs):
            calls.append(("asset", (start, end)))
            return []

        with patch("app.services.scheduling_page_service.list_schedule_events", return_value=[]):
            with patch("app.services.scheduling_page_service.list_employee_assignments_in_range", side_effect=_emp):
                with patch("app.services.scheduling_page_service.list_asset_assignments_in_range", side_effect=_asset):
                    with patch(
                        "app.services.scheduling_page_service.page_data_cache_get",
                        side_effect=lambda _k, loader: loader(),
                    ):
                        load_scheduling_page_snapshot(
                            week_start=date(2026, 7, 13),
                            week_end=date(2026, 7, 20),
                            selected_day=date(2026, 7, 13),
                            view_mode="Jobs",
                            filters={},
                            include_conflicts=False,
                        )
        assert calls.count(("emp", (date(2026, 6, 29), date(2026, 8, 3)))) == 1
        assert calls.count(("asset", (date(2026, 6, 29), date(2026, 8, 3)))) == 1


class TestSchedulingConflictLazy(unittest.TestCase):
    def test_jobs_view_skips_conflict_calculation(self) -> None:
        assert view_mode_needs_conflict_flags("Jobs") is False
        assert view_mode_needs_conflict_flags("Week") is True

    def test_snapshot_without_conflicts_does_not_call_batch(self) -> None:
        with patch("app.services.scheduling_page_service.list_schedule_events", return_value=[]):
            with patch("app.services.scheduling_page_service.list_employee_assignments_in_range", return_value=[]):
                with patch("app.services.scheduling_page_service.list_asset_assignments_in_range", return_value=[]):
                    with patch(
                        "app.services.scheduling_page_service.find_conflicting_schedule_event_ids",
                    ) as batch_mock:
                        with patch(
                            "app.services.scheduling_page_service.page_data_cache_get",
                            side_effect=lambda _k, loader: loader(),
                        ):
                            snap = load_scheduling_page_snapshot(
                                week_start=date(2026, 7, 13),
                                week_end=date(2026, 7, 20),
                                selected_day=date(2026, 7, 13),
                                view_mode="Jobs",
                                filters={},
                                include_conflicts=False,
                            )
        batch_mock.assert_not_called()
        assert snap.conflict_event_ids == set()


class TestSchedulingDetailFastPath(unittest.TestCase):
    def test_detail_fast_path_returns_before_snapshot_in_source(self) -> None:
        src = inspect.getsource(scheduling_page.render)
        detail_idx = src.index("if detail_pending:")
        snapshot_idx = src.index("load_scheduling_page_snapshot(")
        assert detail_idx < snapshot_idx

    def test_capture_schedule_detail_query_opens_detail_state(self) -> None:
        st.session_state.clear()
        bundle = {
            "event": {"id": "ev-9", "title": "Shift"},
            "employee_rows": [],
            "asset_rows": [],
            "jobs_by_id": {},
            "employees_by_id": {},
            "assets_by_id": {},
        }
        with patch.object(scheduling_page.st, "query_params", {"schedule_detail": "ev-9"}):
            with patch("app.pages.scheduling.get_schedule_event_detail", return_value=bundle):
                assert scheduling_page._capture_schedule_detail_query() is True
        assert st.session_state[SCHED_OPEN_DETAIL_KEY] == "ev-9"
        assert st.session_state["_sched_detail_cache"] == bundle


class TestSchedulingCacheVersion(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_invalidate_bumps_scheduling_data_version(self) -> None:
        from app.services.scheduling_service import invalidate_scheduling_page_cache

        before = scheduling_data_version()
        invalidate_scheduling_page_cache(force=True)
        assert scheduling_data_version() == before + 1


class TestSchedulingNativeLink(unittest.TestCase):
    def test_schedule_detail_href(self) -> None:
        href = scheduling_page.schedule_detail_href("ev-123")
        assert "ips_nav=scheduling" in href
        assert "schedule_detail=ev-123" in href


if __name__ == "__main__":
    unittest.main()
