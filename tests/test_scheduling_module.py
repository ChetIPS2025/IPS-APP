"""Scheduling service, permissions, and navigation tests."""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.scheduling_service import (
    clear_scheduling_cache,
    enrich_events,
    list_schedule_events,
    monday_of,
    week_range,
    build_weekly_schedule_export_rows,
)
from app.utils.permissions import role_can_access_page


def test_monday_of_and_week_range():
    d = date(2026, 7, 15)  # Wednesday
    start, end = week_range(d)
    assert start == date(2026, 7, 13)
    assert end == date(2026, 7, 20)
    assert monday_of(d) == start


def test_scheduling_permissions_by_role():
    assert role_can_access_page("admin", "scheduling") is True
    assert role_can_access_page("supervisor", "scheduling") is True
    assert role_can_access_page("project manager", "scheduling") is True
    assert role_can_access_page("employee", "scheduling") is False
    assert role_can_access_page("viewer", "scheduling") is False


def test_navigation_registers_scheduling_module():
    from app import phase2
    from app.navigation import ACTIVE_MODULE_SLUGS

    assert "scheduling" in ACTIVE_MODULE_SLUGS
    assert "scheduling" in phase2._MODULE_SPECS
    fn = phase2.BUILT_MODULES.get("scheduling")
    assert callable(fn)


def test_list_schedule_events_applies_server_side_range(monkeypatch):
    captured: dict[str, object] = {}

    class _Query:
        def select(self, *_a, **_k):
            return self

        def lt(self, col, val):
            captured["lt"] = (col, val)
            return self

        def gt(self, col, val):
            captured["gt"] = (col, val)
            return self

        def order(self, *_a, **_k):
            return self

        def limit(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def execute(self):
            return SimpleNamespace(data=[{"id": "ev-1", "start_at": "2026-07-14T08:00:00+00:00"}])

    monkeypatch.setattr(
        "app.services.scheduling_service.get_client",
        lambda: SimpleNamespace(table=lambda _t: _Query()),
    )
    monkeypatch.setattr(
        "app.services.scheduling_service.run_user_supabase_operation",
        lambda _op, fn, **_: fn(),
    )

    rows = list_schedule_events(date(2026, 7, 13), date(2026, 7, 20))
    assert len(rows) == 1
    assert captured["lt"] == ("start_at", captured["lt"][1])
    assert captured["gt"] == ("end_at", captured["gt"][1])


def test_enrich_events_adds_job_and_supervisor_fields():
    events = [{"id": "ev-1", "job_id": "job-1", "supervisor_id": "emp-1"}]
    jobs_by_id = {"job-1": {"job_number": "J100", "job_name": "Plant outage"}}
    employees_by_id = {"emp-1": {"full_name": "Sam Supervisor"}}
    emp_map = {"ev-1": [{"employee_id": "emp-2"}, {"employee_id": "emp-3"}]}
    out = enrich_events(
        events,
        jobs_by_id=jobs_by_id,
        employees_by_id=employees_by_id,
        employee_rows_by_event=emp_map,
    )
    assert out[0]["job_number"] == "J100"
    assert out[0]["supervisor_name"] == "Sam Supervisor"
    assert out[0]["assigned_employee_count"] == 2


def test_clear_scheduling_cache_clears_session_keys(monkeypatch):
    import streamlit as st

    st.session_state["_ips_schedule_events_cache"] = ["x"]
    st.session_state["_ips_schedule_range_cache"] = ["y"]
    cleared: list[str] = []

    monkeypatch.setattr(
        "app.services.scheduling_service.clear_data_cache_for_table",
        lambda table: cleared.append(table),
    )
    clear_scheduling_cache()
    assert "_ips_schedule_events_cache" not in st.session_state
    assert "schedule_events" in cleared


def test_weekly_export_rows_skip_cancelled_and_internal_notes():
    events = [
        {
            "id": "ev-1",
            "title": "Field work",
            "start_at": "2026-07-14T08:00:00+00:00",
            "end_at": "2026-07-14T17:00:00+00:00",
            "status": "confirmed",
            "location": "Site A",
            "supervisor_name": "Sam",
            "per_diem_amount": 75,
            "lodging_name": "Hotel",
            "internal_notes": "secret",
        },
        {"id": "ev-2", "title": "Cancelled", "status": "cancelled"},
    ]
    rows = build_weekly_schedule_export_rows(
        events,
        jobs_by_id={},
        employees_by_id={"emp-1": {"full_name": "Jane Doe"}},
        employee_rows_by_event={"ev-1": [{"employee_id": "emp-1"}]},
    )
    assert len(rows) == 1
    assert rows[0]["employee"] == "Jane Doe"
    assert "secret" not in rows[0].values()


def test_scheduling_page_has_mobile_friendly_css():
    from app.components.scheduling_css import SCHEDULING_CSS

    assert "ips-scheduling-week-grid" in SCHEDULING_CSS
    assert "@media" in SCHEDULING_CSS


def test_scheduling_page_unique_widget_key_prefixes():
    import inspect

    from app.pages import scheduling as sched_page

    source = inspect.getsource(sched_page)
    assert 'key="sched_' in source or "key=f\"sched_" in source
    assert "scheduling_view_mode" in source


def test_upcoming_employee_schedule_skips_cancelled(monkeypatch):
    from app.services.scheduling_service import list_upcoming_employee_schedule

    monkeypatch.setattr(
        "app.services.scheduling_service.list_employee_schedule",
        lambda _eid, _s, _e: [
            {"id": "1", "status": "confirmed", "start_at": "2026-07-20T08:00:00+00:00"},
            {"id": "2", "status": "cancelled", "start_at": "2026-07-21T08:00:00+00:00"},
            {"id": "3", "status": "tentative", "start_at": "2026-07-22T08:00:00+00:00"},
        ],
    )
    rows = list_upcoming_employee_schedule("emp-1", limit=4)
    assert len(rows) == 2
    assert all(str(r.get("status")).lower() != "cancelled" for r in rows)


def test_timekeeping_schedule_suggestion(monkeypatch):
    from datetime import date

    from app.services.scheduling_service import schedule_suggestion_for_employee_day

    monkeypatch.setattr(
        "app.services.scheduling_service.list_employee_schedule",
        lambda _eid, _s, _e: [
            {
                "id": "ev-1",
                "title": "Plant outage",
                "job_id": "job-1",
                "start_at": "2026-07-14T08:00:00+00:00",
                "end_at": "2026-07-14T17:00:00+00:00",
                "shift_name": "Day",
                "status": "confirmed",
            }
        ],
    )
    hint = schedule_suggestion_for_employee_day("emp-1", date(2026, 7, 14))
    assert hint is not None
    assert hint["expected_hours"] == 9.0
    assert hint["shift"] == "Day"

