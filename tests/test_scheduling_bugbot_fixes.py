"""Regression tests for scheduling Bugbot findings."""

from __future__ import annotations

from datetime import date, datetime, time, timezone

import streamlit as st

from app.components.scheduling_dialogs import (
    SCHED_FORM_LOADED_KEY,
    _dt_from_inputs,
    _seed_schedule_form_from_event,
)
from app.components.scheduling_view_nav import clamp_day_to_week, week_anchor
from app.pages.scheduling import _DAY_KEY, _WEEK_KEY
from app.services.scheduling_service import monday_of, week_range


def test_all_day_uses_full_calendar_day():
    d = date(2026, 7, 14)
    start = _dt_from_inputs(d, None, all_day=True)
    end = _dt_from_inputs(d, None, end=True, all_day=True)
    assert start == datetime(2026, 7, 14, 0, 0, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 7, 14, 23, 59, 59, tzinfo=timezone.utc)


def test_timed_event_defaults_unchanged():
    d = date(2026, 7, 14)
    start = _dt_from_inputs(d, None)
    end = _dt_from_inputs(d, None, end=True)
    assert start == datetime(2026, 7, 14, 8, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 7, 14, 23, 59, 59, tzinfo=timezone.utc)


def test_seed_schedule_form_loads_existing_dates():
    st.session_state.clear()
    existing = {
        "start_at": "2026-07-10T09:30:00+00:00",
        "end_at": "2026-07-11T16:45:00+00:00",
        "all_day": False,
    }
    _seed_schedule_form_from_event(existing, edit_id="ev-1")
    assert st.session_state["sched_form_start_date"] == date(2026, 7, 10)
    assert st.session_state["sched_form_start_time"] == time(9, 30)
    assert st.session_state["sched_form_end_date"] == date(2026, 7, 11)
    assert st.session_state["sched_form_end_time"] == time(16, 45)
    assert st.session_state[SCHED_FORM_LOADED_KEY] == "ev-1"

    _seed_schedule_form_from_event(existing, edit_id="ev-1")
    assert st.session_state["sched_form_start_date"] == date(2026, 7, 10)


def test_seed_schedule_form_resets_when_switching_events():
    st.session_state.clear()
    _seed_schedule_form_from_event(
        {"start_at": "2026-07-10T09:30:00+00:00", "end_at": "2026-07-10T17:00:00+00:00"},
        edit_id="ev-1",
    )
    _seed_schedule_form_from_event(
        {"start_at": "2026-08-01T08:00:00+00:00", "end_at": "2026-08-01T17:00:00+00:00"},
        edit_id="ev-2",
    )
    assert st.session_state["sched_form_start_date"] == date(2026, 8, 1)
    assert st.session_state[SCHED_FORM_LOADED_KEY] == "ev-2"


def test_clamp_day_to_selected_week():
    st.session_state.clear()
    week = date(2026, 7, 13)
    st.session_state[_WEEK_KEY] = week
    st.session_state[_DAY_KEY] = date(2026, 7, 1)
    clamp_day_to_week(week_key=_WEEK_KEY, day_key=_DAY_KEY)
    assert st.session_state[_DAY_KEY] == week

    st.session_state[_DAY_KEY] = date(2026, 7, 15)
    clamp_day_to_week(week_key=_WEEK_KEY, day_key=_DAY_KEY)
    assert st.session_state[_DAY_KEY] == date(2026, 7, 15)


def test_day_in_week_defaults_to_monday():
    st.session_state.clear()
    anchor = date(2026, 7, 15)
    st.session_state[_WEEK_KEY] = monday_of(anchor)
    st.session_state.pop(_DAY_KEY, None)
    clamp_day_to_week(week_key=_WEEK_KEY, day_key=_DAY_KEY)
    day = st.session_state[_DAY_KEY]
    week_start, _ = week_range(anchor)
    assert day == week_start


def test_crew_table_includes_unassigned_employees():
    from app.components.scheduling_calendar import render_crew_schedule_table

    events = [
        {
            "id": "ev-1",
            "start_at": "2026-07-14T08:00:00+00:00",
            "end_at": "2026-07-14T17:00:00+00:00",
            "title": "Job A",
        }
    ]
    employees_by_id = {
        "emp-1": {"full_name": "Assigned Alice"},
        "emp-2": {"full_name": "Unassigned Bob"},
    }
    employee_rows_by_event = {"ev-1": [{"employee_id": "emp-1"}]}

    class _Markdown:
        def __call__(self, html: str, **_: object) -> None:
            self.last_html = html

    markdown = _Markdown()
    import app.components.scheduling_calendar as cal

    original_markdown = cal.st.markdown
    cal.st.markdown = markdown  # type: ignore[assignment]
    try:
        render_crew_schedule_table(
            events,
            week_anchor=date(2026, 7, 13),
            employees_by_id=employees_by_id,
            employee_rows_by_event=employee_rows_by_event,
            show_unassigned=True,
        )
    finally:
        cal.st.markdown = original_markdown

    assert "Assigned Alice" in markdown.last_html
    assert "Unassigned Bob" in markdown.last_html
