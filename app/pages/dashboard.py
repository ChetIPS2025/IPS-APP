"""Dashboard module (Phase 2)."""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

try:
    from app.auth import current_profile
    from app.components.cards import render_kpi_card, render_panel_card
    from app.components.charts import render_donut_chart, render_horizontal_bars, render_line_chart
    from app.components.company_updates_feed import render_dashboard_company_updates_section
    from app.components.feeds import render_activity_feed
    from app.components.qr_scan_history_ui import inject_qr_scan_history_css, qr_scan_history_table_html
    from app.components.headers import render_dashboard_quick_actions, render_page_brand_header
    from app.components.tables import data_table_html
    from app.pages._core._data import (
        demo_deadlines,
        demo_job_status,
        load_awarded_jobs,
        demo_sales_categories,
        demo_sales_series,
        load_dashboard_kpis,
        load_recent_company_updates,
        load_recent_item_activity,
        load_recent_qr_scans,
    )
    from app.styles import inject_global_css
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from auth import current_profile  # type: ignore
    from components.cards import render_kpi_card, render_panel_card  # type: ignore
    from components.charts import render_donut_chart, render_horizontal_bars, render_line_chart  # type: ignore
    from components.company_updates_feed import render_dashboard_company_updates_section  # type: ignore
    from components.feeds import render_activity_feed  # type: ignore
    from components.qr_scan_history_ui import inject_qr_scan_history_css, qr_scan_history_table_html  # type: ignore
    from components.headers import render_dashboard_quick_actions, render_page_brand_header  # type: ignore
    from components.tables import data_table_html  # type: ignore
    from pages._core._data import (  # type: ignore
        demo_deadlines,
        demo_job_status,
        load_awarded_jobs,
        demo_sales_categories,
        demo_sales_series,
        load_dashboard_kpis,
        load_recent_company_updates,
        load_recent_item_activity,
        load_recent_qr_scans,
    )
    from styles import inject_global_css  # type: ignore
    from utils.formatting import fmt_currency, fmt_date  # type: ignore


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


def render() -> None:
    inject_global_css()
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("dashboard", inject_css=False):
        return
    start, end = _date_range_state()

    def _dash_period() -> None:
        dr = st.date_input(
            "Period",
            value=(start, end),
            key="ips_dash_period",
            label_visibility="collapsed",
        )
        if isinstance(dr, tuple) and len(dr) == 2:
            st.session_state["ips_dash_date_start"] = dr[0]
            st.session_state["ips_dash_date_end"] = dr[1]

    def _dash_customize() -> None:
        st.button("Customize", key="ips_dash_customize", use_container_width=True)

    render_page_brand_header(
        "Dashboard",
        f"Welcome back, {_welcome_name()}!",
        actions=[_dash_period, _dash_customize],
    )

    render_dashboard_company_updates_section(load_recent_company_updates(limit=8))

    kpis = load_dashboard_kpis()
    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-kpi-grid">', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    for col, *args in [
        (k1, "Total Sales", fmt_currency(kpis["total_sales"]), "💵", "#dbeafe", "↑ 12.5% vs previous period", "up"),
        (k2, "Open Invoices", fmt_currency(kpis["open_invoices"]), "🧾", "#dcfce7", "↑ 8.3% vs previous period", "up"),
        (k3, "Open Estimates", str(kpis["open_estimates"]), "📋", "#f3e8ff", "↓ 2 vs previous period", "down"),
        (k4, "Inventory Value", fmt_currency(kpis["inventory_value"]), "📦", "#e0f2fe", "↑ 6.7% vs previous period", "up"),
    ]:
        with col:
            render_kpi_card(*args)
    st.markdown(f"</{ot}>", unsafe_allow_html=True)

    st.markdown(f'<{ot} class="ips-kpi-grid ips-kpi-grid-jobs">', unsafe_allow_html=True)
    j1, j2, j3, j4 = st.columns(4)
    for col, *args in [
        (j1, "Jobs Awarded", str(kpis.get("jobs_awarded", 0)), "🏆", "#dbeafe", "Won — not yet started", "flat"),
        (j2, "Active Jobs", str(kpis.get("active_jobs", 0)), "💼", "#ffedd5", "In progress now", "flat"),
        (j3, "Pending Jobs", str(kpis.get("pending_jobs", 0)), "⏳", "#f3e8ff", "Draft or awaiting start", "flat"),
        (j4, "Complete Jobs", str(kpis.get("complete_jobs", 0)), "✅", "#dcfce7", "Finished work", "flat"),
    ]:
        with col:
            render_kpi_card(*args)
    st.markdown(f"</{ot}>", unsafe_allow_html=True)

    row1_l, row1_m, row1_r = st.columns([2.2, 1.2, 1], gap="medium")
    labels, series = demo_sales_series()
    cats = demo_sales_categories()

    with row1_l:
        st.markdown(f'<{ot} class="ips-panel-card"><p class="ips-panel-title">Sales Overview</p>', unsafe_allow_html=True)
        render_line_chart(labels, series)
        st.markdown(f"</{ot}>", unsafe_allow_html=True)
    with row1_m:
        st.markdown(f'<{ot} class="ips-panel-card"><p class="ips-panel-title">Sales by Category</p>', unsafe_allow_html=True)
        total = sum(cats.values())
        render_donut_chart(cats, center_label="Total", center_value=fmt_currency(total), money_legend=True)
        st.markdown(f"</{ot}>", unsafe_allow_html=True)
    with row1_r:
        st.markdown(
            f'<{ot} class="ips-panel-card">'
            f'<p class="ips-panel-title">Recent Activity</p>'
            f'<p class="ips-panel-subtitle">System events — inventory, tools, and scans</p>',
            unsafe_allow_html=True,
        )
        render_activity_feed(
            load_recent_item_activity(limit=10),
            empty_message="No recent system activity.",
        )
        st.markdown(f"</{ot}>", unsafe_allow_html=True)

    row2_l, row2_m, row2_r = st.columns([1.2, 1.2, 1], gap="medium")
    status = demo_job_status()
    with row2_l:
        st.markdown(f'<{ot} class="ips-panel-card"><p class="ips-panel-title">Job Status Overview</p>', unsafe_allow_html=True)
        render_donut_chart(status, center_label="Jobs", center_value=str(sum(status.values())), money_legend=False)
        st.markdown(f"</{ot}>", unsafe_allow_html=True)
    with row2_m:
        st.markdown(f'<{ot} class="ips-panel-card"><p class="ips-panel-title">Aging Invoices</p>', unsafe_allow_html=True)
        render_horizontal_bars(
            [
                ("0–30 days", 82000, "#22c55e"),
                ("31–60 days", 28000, "#f59e0b"),
                ("61–90 days", 12000, "#f97316"),
                ("90+ days", 5430, "#ef4444"),
            ]
        )
        st.markdown(f"</{ot}>", unsafe_allow_html=True)
    with row2_r:
        st.markdown(f'<{ot} class="ips-panel-card"><p class="ips-panel-title">Upcoming Deadlines</p>', unsafe_allow_html=True)
        for d in demo_deadlines():
            st.markdown(
                f'<{ot} class="ips-deadline-row">'
                f'<span>{html.escape(d["title"])}<br><span class="ips-activity-meta">{fmt_date(d["date"])}</span></span>'
                f'<span class="ips-deadline-badge {html.escape(d["level"])}">{html.escape(d["badge"])}</span>'
                f"</{ot}>",
                unsafe_allow_html=True,
            )
        st.markdown(f"</{ot}>", unsafe_allow_html=True)

    inject_qr_scan_history_css()
    render_panel_card(
        "Recent QR Scans",
        qr_scan_history_table_html(load_recent_qr_scans(limit=10), compact=True),
        compact=True,
    )

    def _dash_awarded_job_cell(field: str, row: dict) -> str:
        if field == "job_number":
            return f'<span class="ips-dash-job-number">{html.escape(str(row.get("job_number") or ""))}</span>'
        if field == "awarded_date":
            return html.escape(fmt_date(row.get("awarded_date")) if row.get("awarded_date") else "—")
        return html.escape(str(row.get(field) or "—"))

    render_panel_card(
        "Active Jobs",
        data_table_html(
            load_awarded_jobs(),
            [
                ("job_number", "Job #"),
                ("job_name", "Project / Description"),
                ("customer", "Customer"),
                ("awarded_date", "Start Date"),
            ],
            col_fr=["0.55fr", "1.35fr", "0.95fr", "0.75fr"],
            cell_renderer=_dash_awarded_job_cell,
            table_class="ips-data-table-wrap ips-data-table-stable ips-dash-list-table",
            empty_message="No active jobs.",
        ),
        compact=True,
    )

    render_dashboard_quick_actions(
        [
            ("💼", "New Job", "jobs"),
            ("📋", "New Estimate", "estimates"),
            ("🧾", "New Invoice", "reports"),
            ("⏱", "Log Time", "timekeeping"),
            ("📦", "New PO", "reports"),
            ("📥", "Add Inventory", "inventory"),
            ("🚛", "Add Asset", "assets"),
            ("📎", "Upload Doc", "documents"),
        ],
        key_prefix="ips_dash_qa",
    )
