"""Dashboard module (Phase 2)."""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

try:
    from app.auth import current_profile
    from app.components.cards import render_kpi_card
    from app.components.charts import render_donut_chart, render_horizontal_bars, render_line_chart
    from app.components.headers import render_page_header
    from app.components.status import status_pill_html
    from app.components.tables import render_data_table
    from app.pages.modules._data import (
        demo_activities,
        demo_deadlines,
        demo_job_status,
        demo_recent_jobs,
        demo_sales_categories,
        demo_sales_series,
        load_dashboard_kpis,
    )
    from app.styles import inject_global_css
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from auth import current_profile  # type: ignore
    from components.cards import render_kpi_card  # type: ignore
    from components.charts import render_donut_chart, render_horizontal_bars, render_line_chart  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from pages.modules._data import (  # type: ignore
        demo_activities,
        demo_deadlines,
        demo_job_status,
        demo_recent_jobs,
        demo_sales_categories,
        demo_sales_series,
        load_dashboard_kpis,
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
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
    if not begin_module("dashboard", inject_css=False):
        return
    start, end = _date_range_state()

    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        render_page_header("Dashboard", f"Welcome back, {_welcome_name()}!")
    with hdr_r:
        dr = st.date_input(
            "Period",
            value=(start, end),
            key="ips_dash_period",
            label_visibility="collapsed",
        )
        if isinstance(dr, tuple) and len(dr) == 2:
            st.session_state["ips_dash_date_start"] = dr[0]
            st.session_state["ips_dash_date_end"] = dr[1]
        st.button("Customize", key="ips_dash_customize", use_container_width=True)

    kpis = load_dashboard_kpis()
    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-kpi-grid">', unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)
    cards = [
        (k1, "Total Sales", fmt_currency(kpis["total_sales"]), "💵", "#dbeafe", "↑ 12.5% vs previous period", "up"),
        (k2, "Open Invoices", fmt_currency(kpis["open_invoices"]), "🧾", "#dcfce7", "↑ 8.3% vs previous period", "up"),
        (k3, "Active Jobs", str(kpis["active_jobs"]), "💼", "#ffedd5", "↑ 5 vs previous period", "up"),
        (k4, "Open Estimates", str(kpis["open_estimates"]), "📋", "#f3e8ff", "↓ 2 vs previous period", "down"),
        (k5, "Inventory Value", fmt_currency(kpis["inventory_value"]), "📦", "#e0f2fe", "↑ 6.7% vs previous period", "up"),
    ]
    for col, *args in cards:
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
        st.markdown(f'<{ot} class="ips-panel-card"><p class="ips-panel-title">Recent Activity</p>', unsafe_allow_html=True)
        for act in demo_activities():
            st.markdown(
                f'<{ot} class="ips-activity-item">'
                f'<{ot} class="ips-activity-icon" style="background:{act["bg"]}">{act["icon"]}</{ot}>'
                f"<{ot}><span>{html.escape(act['text'])}</span>"
                f'<{ot} class="ips-activity-meta">{html.escape(act["time"])}</{ot}></{ot}></{ot}>',
                unsafe_allow_html=True,
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

    st.markdown(f'<{ot} class="ips-panel-card"><p class="ips-panel-title">Recent Jobs</p>', unsafe_allow_html=True)

    def _job_cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "progress":
            pct = int(row.get("progress") or 0)
            return (
                f'{pct}%<div class="ips-progress-bar">'
                f'<div class="ips-progress-fill" style="width:{pct}%"></div></motion.div>'.replace("motion.", "")
            )
        if field == "job_number":
            return f'<span style="color:#2563eb;font-weight:600">{html.escape(str(row.get("job_number") or ""))}</span>'
        return html.escape(str(row.get(field) or "—"))

    jobs = demo_recent_jobs()
    render_data_table(
        jobs,
        [
            ("job_number", "JOB #"),
            ("job_name", "PROJECT / DESCRIPTION"),
            ("customer", "CUSTOMER"),
            ("status", "STATUS"),
            ("start_date", "START"),
            ("end_date", "END"),
            ("progress", "PROGRESS"),
        ],
        row_id_key="id",
        selected_id=None,
        session_select_key="ips_sel_dashboard_jobs",
        col_fr=["0.9fr", "1.6fr", "1.1fr", "0.9fr", "0.8fr", "0.8fr", "0.9fr"],
        cell_renderer=_job_cell,
    )
    st.markdown(f"</{ot}>", unsafe_allow_html=True)

    st.markdown(f'<{ot} class="ips-panel-card"><p class="ips-panel-title">Quick Actions</p>', unsafe_allow_html=True)
    actions = [
        "New Job",
        "New Estimate",
        "New Invoice",
        "Log Time",
        "New PO",
        "Add Inventory",
        "Add Asset",
        "Upload Doc",
    ]
    qa_cols = st.columns(4)
    for i, label in enumerate(actions):
        with qa_cols[i % 4]:
            if st.button(label, key=f"ips_dash_qa_{i}", use_container_width=True):
                st.session_state["ips_nav_page"] = {
                    "New Job": "jobs",
                    "New Estimate": "estimates",
                    "Log Time": "timekeeping",
                    "Add Inventory": "inventory",
                    "Add Asset": "assets",
                }.get(label, st.session_state.get("ips_nav_page", "dashboard"))
                st.rerun()
    st.markdown(f"</{ot}>", unsafe_allow_html=True)
