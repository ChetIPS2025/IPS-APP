"""Coastal Builders–style dashboard layout."""

from __future__ import annotations

import html
from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from .coastal_charts import render_category_donut, render_job_status_donut, render_sales_line_chart
from .coastal_metrics import CoastalMetrics, TrendDelta, build_coastal_metrics, customers_map, safe_date
from .coastal_theme import COASTAL_MARKER_CLASS, inject_coastal_theme
from .services import DashboardContext, DashboardTables
from .utils import (
    STATE_DATE_END,
    STATE_DATE_START,
    is_open_job,
    norm_status,
    recent_rows,
    row_ts,
)

try:
    from app.auth import current_profile
    from app.services.job_service import job_number_display, job_row_select_label
    from app.ui import IPS_NAV_PENDING_KEY, role_can_open_page
except ImportError:
    from auth import current_profile  # type: ignore
    from services.job_service import job_number_display, job_row_select_label  # type: ignore
    from ui import IPS_NAV_PENDING_KEY, role_can_open_page  # type: ignore

try:
    from app.ui.components.empty_states import render_empty_state
except ImportError:
    from ui.components.empty_states import render_empty_state  # type: ignore


def _welcome_name() -> str:
    prof = current_profile() or {}
    nm = str(prof.get("full_name") or prof.get("name") or "").strip()
    if nm:
        return nm
    return str(prof.get("email") or "there").split("@")[0]


def _trend_html(t: TrendDelta, *, money: bool = False) -> str:
    if t.direction == "up":
        cls, arrow = "up", "↑"
    elif t.direction == "down":
        cls, arrow = "down", "↓"
    else:
        cls, arrow = "flat", "—"
    if money:
        txt = f"{arrow} ${abs(t.value):,.0f}"
    else:
        txt = f"{arrow} {abs(int(t.value)):,}"
    if t.pct is not None and t.direction != "flat":
        txt += f" ({abs(t.pct):.1f}%)"
    return f'<p class="ips-coastal-kpi-trend {cls}">{html.escape(txt)} vs prior period</p>'


def _kpi_card_html(
    *,
    label: str,
    value: str,
    icon: str,
    icon_bg: str,
    trend: TrendDelta,
    money: bool = False,
) -> str:
    return (
        f'<div class="ips-coastal-kpi">'
        f'<div class="ips-coastal-kpi-top">'
        f'<p class="ips-coastal-kpi-label">{html.escape(label)}</p>'
        f'<div class="ips-coastal-kpi-icon" style="background:{icon_bg}">{icon}</div>'
        f"</div>"
        f'<p class="ips-coastal-kpi-value">{html.escape(value)}</p>'
        f"{_trend_html(trend, money=money)}"
        f"</div>"
    )


def _nav(page: str) -> None:
    st.session_state[IPS_NAV_PENDING_KEY] = page
    st.rerun()


def _date_range_from_state() -> tuple[date, date]:
    end = st.session_state.get(STATE_DATE_END)
    start = st.session_state.get(STATE_DATE_START)
    today = date.today()
    if end is None:
        end = today
    elif hasattr(end, "date"):
        end = end.date()  # type: ignore[union-attr]
    if start is None:
        start = end - timedelta(days=30)
    elif hasattr(start, "date"):
        start = start.date()  # type: ignore[union-attr]
    if start > end:
        start, end = end, start
    return start, end


def render_coastal_header() -> tuple[date, date]:
    st.markdown(
        f'<div class="{COASTAL_MARKER_CLASS} ips-dashboard-page" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    inject_coastal_theme()

    start, end = _date_range_from_state()
    h_left, h_right = st.columns([1.6, 1], gap="medium")
    with h_left:
        st.markdown("## Dashboard")
        st.markdown(
            f'<p style="margin:0;color:#64748b;font-size:0.9rem;">Welcome back, '
            f"<strong>{html.escape(_welcome_name())}</strong></p>",
            unsafe_allow_html=True,
        )
    with h_right:
        c1, c2 = st.columns([1.2, 0.55], gap="small")
        with c1:
            dr = st.date_input(
                "Date range",
                value=(start, end),
                key="coastal_dash_date_range",
                label_visibility="collapsed",
            )
            if isinstance(dr, tuple) and len(dr) == 2:
                st.session_state[STATE_DATE_START] = dr[0]
                st.session_state[STATE_DATE_END] = dr[1]
                start, end = dr[0], dr[1]
        with c2:
            if st.button("⚙ Customize", key="coastal_dash_customize", use_container_width=True):
                st.session_state["coastal_dash_show_customize"] = not st.session_state.get(
                    "coastal_dash_show_customize", False
                )
    return start, end


def render_coastal_kpis(m: CoastalMetrics) -> None:
    cards = [
        ("Total Sales", f"${m.total_sales:,.0f}", "💰", "#dbeafe", m.sales_trend, True),
        ("Open Invoices", f"{m.open_invoices:,}", "🧾", "#ffedd5", m.invoices_trend, False),
        ("Active Jobs", f"{m.active_jobs:,}", "🔧", "#dcfce7", m.jobs_trend, False),
        ("Open Estimates", f"{m.open_estimates:,}", "📄", "#ede9fe", m.estimates_trend, False),
        ("Total Inventory Value", f"${m.inventory_value:,.0f}", "📦", "#e0f2fe", m.inventory_trend, True),
    ]
    cols = st.columns(5, gap="small")
    for col, spec in zip(cols, cards):
        with col:
            st.markdown(
                _kpi_card_html(
                    label=spec[0],
                    value=spec[1],
                    icon=spec[2],
                    icon_bg=spec[3],
                    trend=spec[4],
                    money=spec[5],
                ),
                unsafe_allow_html=True,
            )


def _status_pill(status: str) -> str:
    s = norm_status(status)
    colors = {
        "completed": ("#dcfce7", "#166534"),
        "in progress": ("#dbeafe", "#1e40af"),
        "on hold": ("#ffedd5", "#9a3412"),
        "draft": ("#f1f5f9", "#475569"),
    }
    bg, fg = colors.get(s, ("#f1f5f9", "#334155"))
    label = str(status or "—").strip() or "—"
    return (
        f'<span class="ips-coastal-status-pill" style="background:{bg};color:{fg}">'
        f"{html.escape(label.title())}</span>"
    )


def _job_progress_pct(job: dict) -> float:
    for k in ("progress", "percent_complete", "completion_pct"):
        v = job.get(k)
        if v is not None and str(v).strip():
            try:
                p = float(v)
                return max(0.0, min(100.0, p))
            except (TypeError, ValueError):
                pass
    grp = norm_status(job.get("status"))
    if grp in ("complete", "completed", "closed"):
        return 100.0
    if grp in ("in progress", "in_progress", "active", "scheduled"):
        return 55.0
    if grp in ("on hold",):
        return 25.0
    return 10.0


def render_coastal_dashboard(ctx: DashboardContext, tables: DashboardTables) -> None:
    date_start, date_end = render_coastal_header()

    customers = customers_map(getattr(tables, "customers", None) or [])
    expenses = list(tables.expenses or tables.po_rows or [])
    metrics = build_coastal_metrics(
        jobs=tables.jobs,
        estimates=tables.estimates,
        inv_rows=tables.inv_rows,
        expenses=expenses,
        time_entries=tables.time_entries,
        customers_by_id=customers,
        date_start=date_start,
        date_end=date_end,
    )

    if st.session_state.get("coastal_dash_show_customize"):
        with st.container(border=True):
            st.caption("Customize visible sections")
            st.checkbox("Sales charts", value=True, key="coastal_show_sales")
            st.checkbox("Activity panel", value=True, key="coastal_show_activity")
            st.checkbox("Deadlines", value=True, key="coastal_show_deadlines")

    render_coastal_kpis(metrics)

    main_col, side_col = st.columns([2.15, 1], gap="medium")

    with main_col:
        with st.container(border=True):
            st.markdown('<p class="ips-coastal-card-title">Sales Overview</p>', unsafe_allow_html=True)
            render_sales_line_chart(
                metrics.sales_by_month,
                metrics.sales_by_month_prev,
                key="coastal_sales_line",
            )

        c_a, c_b = st.columns(2, gap="small")
        with c_a:
            with st.container(border=True):
                st.markdown('<p class="ips-coastal-card-title">Sales by Category</p>', unsafe_allow_html=True)
                render_category_donut(metrics.category_breakdown, key="coastal_cat_donut")
        with c_b:
            with st.container(border=True):
                st.markdown('<p class="ips-coastal-card-title">Job Status Overview</p>', unsafe_allow_html=True)
                render_job_status_donut(metrics.job_status_breakdown, key="coastal_job_donut")

        with st.container(border=True):
            head_l, head_r = st.columns([2, 1])
            with head_l:
                st.markdown('<p class="ips-coastal-card-title">Recent Jobs</p>', unsafe_allow_html=True)
            with head_r:
                if st.button("View All Jobs →", key="coastal_view_all_jobs", type="secondary"):
                    if role_can_open_page(ctx.role, "Job Database"):
                        _nav("Job Database")
            _render_recent_jobs_table(tables.jobs, customers)

        with st.container(border=True):
            st.markdown('<p class="ips-coastal-card-title">Aging Invoices</p>', unsafe_allow_html=True)
            _render_aging(metrics.aging_buckets)

    with side_col:
        with st.container(border=True):
            h1, h2 = st.columns([2, 1])
            with h1:
                st.markdown('<p class="ips-coastal-card-title">Recent Activity</p>', unsafe_allow_html=True)
            with h2:
                if st.button("View All", key="coastal_act_view_all", type="secondary"):
                    if role_can_open_page(ctx.role, "PO / Expenses"):
                        _nav("PO / Expenses")
            _render_activity(metrics.activity)

        with st.container(border=True):
            h1, h2 = st.columns([2, 1])
            with h1:
                st.markdown('<p class="ips-coastal-card-title">Upcoming Deadlines</p>', unsafe_allow_html=True)
            with h2:
                if st.button("View All", key="coastal_dl_view_all", type="secondary"):
                    if role_can_open_page(ctx.role, "Job Database"):
                        _nav("Job Database")
            _render_deadlines(metrics.deadlines)

        with st.container(border=True):
            st.markdown('<p class="ips-coastal-card-title">Quick Actions</p>', unsafe_allow_html=True)
            _render_quick_actions_grid(ctx)


def _render_activity(items: list[dict[str, Any]]) -> None:
    if not items:
        render_empty_state("No recent activity", "Updates will appear here as you work.", icon="📋")
        return
    for it in items[:8]:
        ts = str(it.get("ts") or "")[:16].replace("T", " ")
        st.markdown(
            f'<div class="ips-coastal-activity-item">'
            f'<div class="ips-coastal-act-icon" style="background:{html.escape(str(it.get("color") or "#f1f5f9"))}">'
            f'{html.escape(str(it.get("icon") or "•"))}</div>'
            f"<div style='flex:1'><p class='ips-coastal-act-title'>{html.escape(str(it.get('title') or ''))}</p>"
            f"<p class='ips-coastal-act-meta'>{html.escape(str(it.get('meta') or ''))} · {html.escape(ts)}</p></div>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_deadlines(items: list[dict[str, Any]]) -> None:
    if not items:
        render_empty_state("No upcoming deadlines", "Job target dates will show here.", icon="📅")
        return
    for it in items[:8]:
        days = int(it.get("days_left", 0))
        if days < 0:
            badge_cls, badge_txt = "ips-coastal-badge-urgent", f"{abs(days)}d overdue"
        elif days <= 7:
            badge_cls, badge_txt = "ips-coastal-badge-soon", f"{days}d left"
        else:
            badge_cls, badge_txt = "ips-coastal-badge-ok", f"{days}d left"
        st.markdown(
            f'<div class="ips-coastal-deadline">'
            f"<div><p class='ips-coastal-act-title' style='margin:0'>{html.escape(str(it.get('label') or ''))}</p>"
            f"<p class='ips-coastal-act-meta'>{html.escape(str(it.get('due') or ''))}</p></div>"
            f'<span class="ips-coastal-badge {badge_cls}">{html.escape(badge_txt)}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_aging(buckets: dict[str, float]) -> None:
    total = sum(buckets.values())
    if total <= 0:
        render_empty_state(
            "No open invoice balances",
            "Aging buckets use unpaid expense lines.",
            icon="🧾",
        )
        return
    max_amt = max(buckets.values()) if buckets else 1.0
    for label, amt in buckets.items():
        pct_bar = (amt / max_amt * 100) if max_amt else 0
        st.markdown(
            f'<div class="ips-coastal-aging-row">'
            f"<span>{html.escape(label)}</span>"
            f'<div class="ips-coastal-aging-bar"><div class="ips-coastal-aging-fill" style="width:{pct_bar:.0f}%"></div></div>'
            f"<span style='font-weight:600'>${amt:,.0f}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        f"<p style='text-align:right;font-weight:700;margin-top:0.5rem'>Total: ${total:,.0f}</p>",
        unsafe_allow_html=True,
    )


def _render_recent_jobs_table(jobs: list[dict], customers: dict[str, str]) -> None:
    rows = recent_rows(list(jobs or []), limit=10)
    if not rows:
        render_empty_state("No recent jobs", "Jobs will appear here.", icon="🔧")
        return
    table_rows: list[dict[str, Any]] = []
    for j in rows:
        if not isinstance(j, dict):
            continue
        cid = str(j.get("customer_id") or "").strip()
        cust = customers.get(cid) or str(j.get("customer_name") or "—")
        prog = _job_progress_pct(j)
        table_rows.append(
            {
                "Job #": job_number_display(j.get("job_number")) or "—",
                "Project / Description": str(j.get("job_name") or "—")[:48],
                "Customer": cust[:32],
                "Status": str(j.get("status") or "—"),
                "Start": str(j.get("start_date") or "—")[:10],
                "End": str(j.get("target_completion_date") or j.get("end_date") or "—")[:10],
                "Progress": prog,
            }
        )
    df = pd.DataFrame(table_rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=min(320, 44 + 38 * len(df)),
        column_config={
            "Progress": st.column_config.ProgressColumn("Progress", min_value=0, max_value=100),
        },
    )


def _render_quick_actions_grid(ctx: DashboardContext) -> None:
    actions: list[tuple[str, str, str]] = [
        ("➕", "New Job", "Job Database"),
        ("📄", "New Estimate", "Estimates"),
        ("🧾", "New Invoice", "PO / Expenses"),
        ("⏱", "Log Time", "Time Tracking"),
        ("🛒", "New Purchase Order", "PO / Expenses"),
        ("📦", "Add Inventory", "Inventory"),
        ("🏗", "Add Asset", "Asset Database"),
        ("📎", "Upload Document", "Job Database"),
    ]
    visible = [(i, ic, lb, pg) for i, (ic, lb, pg) in enumerate(actions) if role_can_open_page(ctx.role, pg)]
    if not visible:
        st.caption("No quick actions available for your role.")
        return
    cols = st.columns(2, gap="small")
    for idx, (i, icon, label, page) in enumerate(visible):
        with cols[idx % 2]:
            if st.button(f"{icon} {label}", key=f"coastal_qa_{i}", use_container_width=True):
                _nav(page)
