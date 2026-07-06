"""Dashboard module (Phase 2) — operations executive layout."""

from __future__ import annotations

import html
from datetime import date, timedelta

import streamlit as st

try:
    from app.auth import current_profile
    from app.components.cards import render_ops_kpi_row
    from app.components.dashboard_active_jobs_table import render_dashboard_active_jobs_table
    from app.components.dashboard_estimates_waiting_table import render_dashboard_estimates_waiting_table
    from app.components.company_updates_feed import render_dashboard_company_updates_section
    from app.components.dashboard_preview_cards import render_dashboard_preview_sections
    from app.components.headers import (
        render_ops_quick_action_tiles,
        render_page_brand_header,
    )
    from app.pages._core._data import (
        load_awarded_jobs,
        load_dashboard_kpis,
        load_estimates,
        load_recent_company_updates,
        load_tasks,
        load_timekeeping_summaries,
    )
    from app.styles import inject_global_css, inject_ops_dashboard_css
    from app.utils.formatting import fmt_currency
except ImportError:
    from auth import current_profile  # type: ignore
    from components.cards import render_ops_kpi_row  # type: ignore
    from components.dashboard_active_jobs_table import render_dashboard_active_jobs_table  # type: ignore
    from components.dashboard_estimates_waiting_table import render_dashboard_estimates_waiting_table  # type: ignore
    from components.company_updates_feed import render_dashboard_company_updates_section  # type: ignore
    from components.dashboard_preview_cards import render_dashboard_preview_sections  # type: ignore
    from components.headers import (  # type: ignore
        render_ops_quick_action_tiles,
        render_page_brand_header,
    )
    from pages._core._data import (  # type: ignore
        load_awarded_jobs,
        load_dashboard_kpis,
        load_estimates,
        load_recent_company_updates,
        load_tasks,
        load_timekeeping_summaries,
    )
    from styles import inject_global_css, inject_ops_dashboard_css  # type: ignore
    from utils.formatting import fmt_currency  # type: ignore


_CLOSED_TASK_STATUSES = frozenset({"done", "cancelled", "closed", "completed"})


def _welcome_name() -> str:
    prof = current_profile() or {}
    nm = str(prof.get("full_name") or "").strip()
    return nm or str(prof.get("email") or "there").split("@")[0]


def _date_range_state() -> tuple[date, date]:
    end = st.session_state.get("ips_dash_date_end")
    start = st.session_state.get("ips_dash_date_start")
    if not isinstance(end, date):
        end = date.today().replace(day=1)
        st.session_state["ips_dash_date_end"] = end
    if not isinstance(start, date):
        start = end.replace(day=1)
        st.session_state["ips_dash_date_start"] = start
    return start, end


def _count_open_tasks() -> int:
    return sum(
        1
        for task in load_tasks()
        if str(task.get("status") or "").strip().lower() not in _CLOSED_TASK_STATUSES
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
    inject_global_css()
    inject_ops_dashboard_css()
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("dashboard", inject_css=False):
        return

    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-ops-dashboard-marker"></{ot}>', unsafe_allow_html=True)

    start, end = _date_range_state()

    def _dash_period() -> None:
        st.markdown('<span class="ips-ops-action-label">📅 Date Range</span>', unsafe_allow_html=True)
        dr = st.date_input(
            "Period",
            value=(start, end),
            key="ips_dash_period",
            label_visibility="collapsed",
        )
        if isinstance(dr, tuple) and len(dr) == 2:
            st.session_state["ips_dash_date_start"] = dr[0]
            st.session_state["ips_dash_date_end"] = dr[1]

    def _dash_refresh() -> None:
        if st.button("🔄 Refresh", key="ips_dash_refresh", use_container_width=True):
            st.rerun()

    def _dash_customize() -> None:
        if st.button("⚙ Customize", key="ips_dash_customize", use_container_width=True):
            pass

    render_page_brand_header(
        "Operations Dashboard",
        actions=[_dash_period, _dash_refresh, _dash_customize],
        actions_column_ratio=(1.5, 2.5),
    )

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
                ("Open Tasks", str(_count_open_tasks()), "✅", "#e0f2fe"),
                ("Open Invoices", fmt_currency(kpis.get("open_invoices", 0)), "🧾", "#dbeafe"),
                ("Revenue This Month", fmt_currency(kpis.get("total_sales", 0)), "💵", "#fef3c7"),
            ]
            render_ops_kpi_row(kpi_items)

        with st.container(key="dashboard_ops_company_updates"):
            render_dashboard_company_updates_section(
                load_recent_company_updates(limit=5),
                limit=5,
            )

        with st.container(key="dashboard_ops_row2"):
            st.markdown(
                '<span class="ips-ops-row2-grid-marker" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            render_ops_quick_action_tiles(
                [
                    ("📁", "New Job", "jobs"),
                    ("📄", "New Estimate", "estimates"),
                    ("👤", "New Customer", "customers"),
                    ("📝", "Daily Report", "field_daily_reports"),
                    ("🕒", "Time Entry", "timekeeping"),
                    ("📦", "Inventory", "inventory"),
                    ("✅", "Create Task", "tasks"),
                    ("📎", "Upload Document", "documents"),
                    ("📦", "Add Inventory", "inventory"),
                    ("🚛", "Add Asset", "assets"),
                    ("📝", "Start Daily Report", "field_daily_reports"),
                    ("📊", "Run Job Cost Report", "job_costing"),
                ],
                key_prefix="ips_ops_qa",
            )

        render_dashboard_estimates_waiting_table(load_estimates(), limit=5)

        render_dashboard_active_jobs_table(load_awarded_jobs(), limit=12)

        render_dashboard_preview_sections()
