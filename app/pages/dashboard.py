"""Dashboard module (Phase 2) — operations executive layout."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import streamlit as st

from app.auth import current_profile, current_user_display_name, effective_role
from app.components.cards import render_ops_kpi_grid, render_ops_value_grid
from app.components.dashboard_ops_panels import render_dashboard_secondary_panels
from app.components.quote_job_number_autofill import clear_new_job_number_state
from app.navigation import set_nav_slug
from app.services.dashboard_service import (
    load_dashboard_snapshot,
    revenue_kpi_label,
)
from app.ui.kit import render_page_header
from app.ui.ops_dashboard_styles import inject_ops_dashboard_styles
from app.ui.streamlit_perf import fragment


@dataclass(frozen=True)
class DashboardRenderContext:
    today: date
    current_hour: int
    period_start: date
    period_end: date


def _build_render_context() -> DashboardRenderContext:
    from app.perf_debug import perf_span

    with perf_span("dashboard.context"):
        now = datetime.now()
        today = now.date()
        end = st.session_state.get("ips_dash_date_end")
        start = st.session_state.get("ips_dash_date_start")
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        if not isinstance(end, date):
            end = week_end
            st.session_state["ips_dash_date_end"] = end
        if not isinstance(start, date):
            start = week_start
            st.session_state["ips_dash_date_start"] = start
        return DashboardRenderContext(
            today=today,
            current_hour=now.hour,
            period_start=start,
            period_end=end,
        )


def _time_greeting(current_hour: int) -> str:
    if current_hour < 12:
        return "Good Morning"
    if current_hour < 17:
        return "Good Afternoon"
    return "Good Evening"


def _today_display_label(today: date) -> str:
    return today.strftime("%A, %B %d").replace(" 0", " ")


def _ops_dashboard_header_html(
    *,
    display_name: str,
    current_hour: int,
    today: date,
    employees: int,
    active_jobs: int,
) -> str:
    name = html.escape(display_name)
    greet = html.escape(_time_greeting(current_hour))
    today_label = html.escape(_today_display_label(today))
    return (
        '<div class="dashboard-header">'
        '<div class="dashboard-header-left">'
        f'<h2 class="dashboard-header-greet">{greet}, {name} 👋</h2>'
        f'<p class="dashboard-header-meta">'
        f"Today is {today_label} · {employees:,} employees working · {active_jobs:,} active jobs"
        f"</p>"
        "</div>"
        "</div>"
    )


@fragment
def _render_dashboard_secondary_panels(*, profile: dict[str, object], role: str) -> None:
    from app.perf_debug import perf_span

    with perf_span("dashboard.secondary_panels"):
        render_dashboard_secondary_panels(profile=profile, role=role)


def render() -> None:
    from app.pages._core._access import begin_module
    from app.perf_debug import perf_span

    if not begin_module("dashboard"):
        return

    ctx = _build_render_context()
    profile = current_profile() or {}
    role = effective_role()
    display_name = current_user_display_name()

    def _on_date_range_change(dr: tuple[date, date]) -> None:
        st.session_state["ips_dash_date_start"] = dr[0]
        st.session_state["ips_dash_date_end"] = dr[1]

    def _on_dashboard_refresh() -> None:
        from app.services.dashboard_service import clear_dashboard_snapshot_cache

        clear_dashboard_snapshot_cache()

    def _dash_new_job() -> None:
        if st.button("+ New Job", key="ips_dash_new_job", type="primary"):
            clear_new_job_number_state()
            st.session_state["ips_job_form"] = True
            set_nav_slug("jobs")

    render_page_header(
        "Operations Dashboard",
        "Overview of key operational metrics and performance.",
        show_back=False,
        show_date_range=True,
        date_range_value=(ctx.period_start, ctx.period_end),
        date_range_key="ips_dash_period",
        on_date_range_change=_on_date_range_change,
        show_refresh=True,
        refresh_key="ips_dash_refresh",
        on_refresh=_on_dashboard_refresh,
        primary_action=_dash_new_job,
        layout_marker="ips-ops-dashboard-marker",
    )
    inject_ops_dashboard_styles()

    with st.container(key="dashboard_root"):
        with perf_span("dashboard.snapshot"):
            snapshot = load_dashboard_snapshot(
                period_start=ctx.period_start,
                period_end=ctx.period_end,
                profile=profile,
                role=role,
                today=ctx.today,
            )

        if snapshot.warnings:
            warning_text = html.escape("; ".join(snapshot.warnings))
            st.markdown(
                f'<p class="ips-alert-banner ips-alert-banner--warn">{warning_text}</p>',
                unsafe_allow_html=True,
            )

        with perf_span("dashboard.header"):
            with st.container(key="dashboard_header"):
                st.markdown(
                    _ops_dashboard_header_html(
                        display_name=display_name,
                        current_hour=ctx.current_hour,
                        today=ctx.today,
                        employees=snapshot.employees_working_today,
                        active_jobs=snapshot.active_jobs,
                    ),
                    unsafe_allow_html=True,
                )

        if not snapshot.is_live:
            st.markdown(
                '<p class="ips-alert-banner">Sample KPI data — connect Supabase for live metrics.</p>',
                unsafe_allow_html=True,
            )

        revenue_label = revenue_kpi_label(
            ctx.period_start,
            ctx.period_end,
            today=ctx.today,
        )
        with perf_span("dashboard.kpi_cards"):
            primary_kpis = [
                ("Active Jobs", str(snapshot.active_jobs), "💼", "#ffedd5"),
                ("Estimates Pending", str(snapshot.open_estimates), "📋", "#f3e8ff"),
                (
                    "Employees Working Today",
                    str(snapshot.employees_working_today),
                    "👷",
                    "#dcfce7",
                ),
                ("My To-Do", str(snapshot.my_todo_count), "✅", "#e0f2fe"),
                (
                    "Open Invoices",
                    _format_currency(snapshot.open_invoices),
                    "🧾",
                    "#dbeafe",
                ),
                (
                    revenue_label,
                    _format_currency(snapshot.period_revenue),
                    "💵",
                    "#fef3c7",
                ),
            ]
            value_kpis = [
                (
                    "Inventory Value",
                    _format_currency(snapshot.inventory_value),
                    "📦",
                    "#ede9fe",
                ),
                (
                    "Asset Value",
                    _format_currency(snapshot.asset_value),
                    "🚛",
                    "#fce7f3",
                ),
            ]

            with st.container(key="dashboard_kpis"):
                render_ops_kpi_grid(primary_kpis)

            with st.container(key="dashboard_value_cards"):
                render_ops_value_grid(value_kpis)

        st.markdown(
            '<p class="ips-dash-panels-loading" aria-hidden="true">Loading operations panels…</p>',
            unsafe_allow_html=True,
        )
        _render_dashboard_secondary_panels(profile=profile, role=role)


def _format_currency(value: float) -> str:
    from app.utils.formatting import fmt_currency

    return fmt_currency(value)


__all__ = [
    "DashboardRenderContext",
    "_ops_dashboard_header_html",
    "_render_dashboard_secondary_panels",
    "render",
]
