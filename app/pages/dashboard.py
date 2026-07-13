"""Dashboard module (Phase 2) — operations executive layout."""

from __future__ import annotations

import html
from datetime import date, timedelta

import streamlit as st

from app.auth import current_profile, current_user_display_name, effective_role
from app.components.dashboard_ops_panels import render_dashboard_ops_panels
from app.components.quote_job_number_autofill import clear_new_job_number_state
from app.navigation import set_nav_slug
from app.pages._core._data import (
    load_dashboard_kpis,
    load_tasks,
    load_timekeeping_summaries,
)
from app.styles import inject_ops_dashboard_css
from app.ui.kit import render_metric_row, render_page_header
from app.utils.formatting import fmt_currency
def _welcome_name() -> str:
    return current_user_display_name()


def _date_range_state() -> tuple[date, date]:
    end = st.session_state.get("ips_dash_date_end")
    start = st.session_state.get("ips_dash_date_start")
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    if not isinstance(end, date):
        end = week_end
        st.session_state["ips_dash_date_end"] = end
    if not isinstance(start, date):
        start = week_start
        st.session_state["ips_dash_date_start"] = start
    return start, end


def _my_todo_count() -> int:
    from app.services.management_reminders_service import filter_dashboard_reminders
    return len(
        filter_dashboard_reminders(
            load_tasks(),
            profile=current_profile() or {},
            role=effective_role(),
            limit=999,
        )
    )


def _employees_working_today() -> int:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    summaries = load_timekeeping_summaries(week_start)
    return sum(
        1
        for row in summaries
        if float(row.get("st_total") or 0) + float(row.get("ot_total") or 0) > 0
    )


def _time_greeting() -> str:
    try:
        from datetime import datetime

        hour = datetime.now().hour
    except Exception:
        hour = 12
    if hour < 12:
        return "Good Morning"
    if hour < 17:
        return "Good Afternoon"
    return "Good Evening"


def _today_display_label() -> str:
    d = date.today()
    return d.strftime("%A, %B %d").replace(" 0", " ")


def _ops_welcome_html(*, employees: int, active_jobs: int) -> str:
    ot = "d" + "iv"
    name = html.escape(_welcome_name())
    greet = html.escape(_time_greeting())
    today = html.escape(_today_display_label())
    return (
        f'<{ot} class="ips-ops-welcome">'
        f'<p class="ips-ops-welcome-greet">{greet}, {name} 👋</p>'
        f'<p class="ips-ops-welcome-meta">'
        f"Today is {today} · {employees:,} employees working · {active_jobs:,} active jobs"
        f"</p>"
        f"</{ot}>"
    )


def render() -> None:
    from app.pages._core._access import begin_module
    if not begin_module("dashboard", inject_css=False):
        return

    start, end = _date_range_state()

    def _on_date_range_change(dr: tuple[date, date]) -> None:
        st.session_state["ips_dash_date_start"] = dr[0]
        st.session_state["ips_dash_date_end"] = dr[1]

    def _dash_new_job() -> None:
        if st.button("+ New Job", key="ips_dash_new_job", type="primary"):
            clear_new_job_number_state()
            st.session_state["ips_job_form"] = True
            set_nav_slug("jobs")
            st.rerun()

    render_page_header(
        "Operations Dashboard",
        "Overview of key operational metrics and performance.",
        show_back=False,
        show_date_range=True,
        date_range_value=(start, end),
        date_range_key="ips_dash_period",
        on_date_range_change=_on_date_range_change,
        show_refresh=True,
        refresh_key="ips_dash_refresh",
        primary_action=_dash_new_job,
        layout_marker="ips-ops-dashboard-marker",
    )
    inject_ops_dashboard_css()

    with st.container(key="dashboard_ops_shell"):
        kpis = load_dashboard_kpis(period_start=start, period_end=end)
        employees_today = _employees_working_today()
        active_jobs_count = int(kpis.get("active_jobs", 0))
        st.markdown(
            _ops_welcome_html(employees=employees_today, active_jobs=active_jobs_count),
            unsafe_allow_html=True,
        )

        kpis_live = bool(kpis.get("is_live"))
        if not kpis_live:
            st.markdown(
                '<p class="ips-alert-banner">Sample KPI data — connect Supabase for live metrics.</p>',
                unsafe_allow_html=True,
            )

        with st.container(key="dashboard_ops_kpis"):
            kpi_items = [
                ("Active Jobs", str(kpis.get("active_jobs", 0)), "💼", "#ffedd5"),
                ("Estimates Pending", str(kpis.get("open_estimates", 0)), "📋", "#f3e8ff"),
                ("Employees Working Today", str(employees_today), "👷", "#dcfce7"),
                ("My To-Do", str(_my_todo_count()), "✅", "#e0f2fe"),
                ("Open Invoices", fmt_currency(kpis.get("open_invoices", 0)), "🧾", "#dbeafe"),
                ("Revenue This Month", fmt_currency(kpis.get("total_sales", 0)), "💵", "#fef3c7"),
                ("Inventory Value", fmt_currency(kpis.get("total_inventory_value", 0)), "📦", "#ede9fe"),
                ("Asset Value", fmt_currency(kpis.get("total_asset_value", 0)), "🚛", "#fce7f3"),
            ]
            render_metric_row(kpi_items)

        render_dashboard_ops_panels()
