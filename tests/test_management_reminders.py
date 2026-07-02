"""Management reminders (dashboard office todos)."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.management_reminders_service import (
    can_create_management_reminder,
    due_date_badge,
    filter_dashboard_reminders,
    is_office_reminder,
    is_open_reminder,
    visible_to_user,
)


def test_is_office_reminder_when_no_job():
    assert is_office_reminder({"title": "Call vendor", "linked_job": "— None —"}) is True
    assert is_office_reminder({"title": "PM fan", "job_id": "job-1"}) is False


def test_filter_shows_all_open_office_for_managers():
    today = date.today()
    rows = [
        {"id": "1", "title": "A", "status": "Open", "assigned_to": "Pat", "due_date": today.isoformat()},
        {"id": "2", "title": "B", "status": "Open", "job_id": "j1", "assigned_to": "Pat"},
        {"id": "3", "title": "C", "status": "Complete", "assigned_to": "Pat"},
    ]
    out = filter_dashboard_reminders(rows, profile={"full_name": "Other"}, role="admin", limit=5)
    assert len(out) == 1
    assert out[0]["title"] == "A"


def test_filter_assignee_scoped_for_employee():
    rows = [
        {"id": "1", "title": "Mine", "status": "Open", "assigned_to": "Alex Manager"},
        {"id": "2", "title": "Theirs", "status": "Open", "assigned_to": "Someone Else"},
    ]
    out = filter_dashboard_reminders(
        rows,
        profile={"full_name": "Alex Manager", "email": "alex@ips.com"},
        role="employee",
        limit=5,
    )
    assert [r["title"] for r in out] == ["Mine"]


def test_overdue_sorted_first():
    today = date.today()
    rows = [
        {"id": "1", "title": "Later", "status": "Open", "due_date": (today + timedelta(days=5)).isoformat()},
        {"id": "2", "title": "Late", "status": "Open", "due_date": (today - timedelta(days=2)).isoformat()},
    ]
    out = filter_dashboard_reminders(rows, profile={}, role="admin", limit=5)
    assert out[0]["title"] == "Late"


def test_due_date_badge_overdue():
    label, level = due_date_badge((date.today() - timedelta(days=1)).isoformat())
    assert "Overdue" in label
    assert level == "danger"


def test_can_create_for_pm_and_employee_not_viewer():
    assert can_create_management_reminder("project manager") is True
    assert can_create_management_reminder("employee") is True
    assert can_create_management_reminder("viewer") is False


def test_clear_tasks_catalog_cache_drops_session_mirror(monkeypatch):
    import streamlit as st

    from app.pages._core._data import (
        _CATALOG_SESSION_KEY,
        clear_tasks_catalog_cache,
    )

    monkeypatch.setattr(
        "app.pages._core._data.clear_tasks_list_cache",
        lambda: None,
    )
    st.session_state[_CATALOG_SESSION_KEY] = {"tasks": [{"id": "stale", "title": "Old"}]}

    clear_tasks_catalog_cache()

    store = st.session_state.get(_CATALOG_SESSION_KEY, {})
    assert "tasks" not in store


def test_is_open_reminder():
    assert is_open_reminder({"status": "Open"}) is True
    assert is_open_reminder({"status": "Complete"}) is False


def test_visible_to_user_requires_office_open():
    row = {"id": "1", "title": "X", "status": "Open", "job_id": "j1"}
    assert visible_to_user(row, profile={"full_name": "A"}, role="admin") is False
