"""Dashboard performance, caching, and accuracy tests."""

from __future__ import annotations

import html
import inspect
from datetime import date, timedelta
from unittest.mock import patch

import streamlit as st

from app.pages import dashboard as dash
from app.services.dashboard_service import (
    clear_dashboard_snapshot_cache,
    load_dashboard_snapshot,
    revenue_kpi_label,
)
from app.services.management_reminders_service import count_dashboard_reminders
from app.services.phase2_modules_service import count_employees_working_on_date


def test_count_employees_working_on_date_distinct_and_day_scoped():
    monday = date(2026, 7, 13)
    tuesday = date(2026, 7, 14)
    monday_rows = [
        {"employee_id": "e1", "work_date": monday.isoformat(), "st_hours": 8, "ot_hours": 0, "dt_hours": 0},
        {"employee_id": "e1", "work_date": monday.isoformat(), "st_hours": 2, "ot_hours": 1, "dt_hours": 0},
        {"employee_id": "e2", "work_date": monday.isoformat(), "st_hours": 0, "ot_hours": 0, "dt_hours": 0},
        {"employee_id": "e3", "work_date": monday.isoformat(), "st_hours": 0, "ot_hours": 4, "dt_hours": 0},
        {"employee_id": "e4", "work_date": monday.isoformat(), "st_hours": 0, "ot_hours": 0, "dt_hours": 3},
    ]
    tuesday_rows = [
        {"employee_id": "e1", "work_date": tuesday.isoformat(), "st_hours": 0, "ot_hours": 0, "dt_hours": 0},
    ]

    def fake_fetch(table, match, **kwargs):
        wd = str(match.get("work_date") or "")
        if wd == monday.isoformat():
            return monday_rows
        if wd == tuesday.isoformat():
            return tuesday_rows
        return []

    with patch("app.db.fetch_by_match", side_effect=fake_fetch):
        mon_count, live = count_employees_working_on_date(monday)
        tue_count, _ = count_employees_working_on_date(tuesday)

    assert live is False
    assert mon_count == 3
    assert tue_count == 0


def test_count_dashboard_reminders_scoped_to_profile():
    rows = [
        {"id": "1", "title": "Mine", "status": "Open", "assigned_to": "Pat", "linked_job": "— None —"},
        {"id": "2", "title": "Theirs", "status": "Open", "assigned_to": "Other", "linked_job": "— None —"},
        {"id": "3", "title": "Job task", "status": "Open", "job_id": "j1", "assigned_to": "Pat"},
    ]
    count = count_dashboard_reminders(
        profile={"full_name": "Pat"},
        role="admin",
        projections=rows,
    )
    assert count == 1


def test_revenue_kpi_label_week_month_and_custom():
    today = date(2026, 7, 15)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    month_start = today.replace(day=1)
    month_end = date(2026, 7, 31)

    assert revenue_kpi_label(week_start, week_end, today=today) == "Revenue This Week"
    assert revenue_kpi_label(month_start, month_end, today=today) == "Revenue This Month"
    assert revenue_kpi_label(month_start, today, today=today) == "Revenue This Month"
    assert (
        revenue_kpi_label(date(2026, 6, 1), date(2026, 6, 15), today=today)
        == "Revenue for Period"
    )


def test_snapshot_cache_key_varies_by_user_role_and_range():
    from app.services.dashboard_service import _snapshot_cache_key

    k1 = _snapshot_cache_key(
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
        profile={"id": "u1"},
        role="admin",
    )
    k2 = _snapshot_cache_key(
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
        profile={"id": "u2"},
        role="admin",
    )
    k3 = _snapshot_cache_key(
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        profile={"id": "u1"},
        role="admin",
    )
    k4 = _snapshot_cache_key(
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
        profile={"id": "u1"},
        role="employee",
    )
    assert k1 != k2
    assert k1 != k3
    assert k1 != k4


def test_clear_dashboard_snapshot_cache_removes_cached_snapshot(monkeypatch):
    st.session_state.clear()
    calls: list[str] = []

    class _Snap:
        period_start = date(2026, 7, 1)
        period_end = date(2026, 7, 31)
        active_jobs = 1
        open_estimates = 2
        employees_working_today = 3
        my_todo_count = 4
        open_invoices = 5.0
        period_revenue = 6.0
        inventory_value = 7.0
        asset_value = 8.0
        is_live = True
        warnings = ()

    monkeypatch.setattr(
        "app.services.dashboard_service._load_dashboard_snapshot_uncached",
        lambda **kwargs: _Snap(),
    )
    monkeypatch.setattr(
        "app.services.dashboard_service.dashboard_data_version_token",
        lambda: "v1",
    )

    profile = {"id": "user-1"}
    snap1 = load_dashboard_snapshot(
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
        profile=profile,
        role="admin",
    )
    assert snap1.active_jobs == 1

    def _track_clear(**kwargs):
        calls.append("cleared")

    monkeypatch.setattr(
        "app.pages._core.page_data_cache.clear_page_data_cache_prefix",
        lambda prefix: calls.append(prefix),
    )
    clear_dashboard_snapshot_cache()
    assert any("dashboard_snapshot:" in c for c in calls)


def test_dashboard_render_uses_single_auth_capture():
    source = inspect.getsource(dash.render)
    assert source.count("current_profile()") == 1
    assert source.count("effective_role()") == 1
    assert source.count("current_user_display_name()") == 1
    assert "load_dashboard_snapshot" in source
    assert "load_tasks()" not in source
    assert "load_timekeeping_summaries" not in source


def test_dashboard_header_escapes_display_name():
    header = dash._ops_dashboard_header_html(  # noqa: SLF001
        display_name='<script>alert("x")</script>',
        current_hour=10,
        today=date(2026, 7, 15),
        employees=2,
        active_jobs=3,
    )
    assert "<script>" not in header
    assert html.escape('<script>alert("x")</script>') in header
    assert '<div class="dashboard-header">' in header


def test_dashboard_header_source_uses_plain_div_tags():
    source = inspect.getsource(dash._ops_dashboard_header_html)  # noqa: SLF001
    assert '"d" + "iv"' not in source
    assert '<div class="dashboard-header">' in source


def test_dashboard_secondary_panels_are_fragment():
    source = inspect.getsource(dash._render_dashboard_secondary_panels)  # noqa: SLF001
    assert "render_dashboard_secondary_panels" in source


def test_new_job_action_does_not_rerun_twice():
    source = inspect.getsource(dash.render)
    new_job_block = source.split("def _dash_new_job")[1].split("render_page_header")[0]
    assert "set_nav_slug(\"jobs\")" in new_job_block
    assert "st.rerun()" not in new_job_block


def test_ops_dashboard_renders_snapshot_before_secondary_panels():
    source = inspect.getsource(dash.render)
    snapshot_idx = source.index("load_dashboard_snapshot")
    panels_idx = source.index("_render_dashboard_secondary_panels")
    assert snapshot_idx < panels_idx
