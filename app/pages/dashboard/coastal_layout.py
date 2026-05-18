"""Coastal Builders–style dashboard layout."""

from __future__ import annotations

import html
from datetime import date, timedelta
from typing import Any

import streamlit as st

from .coastal_charts import render_category_donut, render_job_status_donut, render_sales_line_chart
from .coastal_metrics import (
    CoastalMetrics,
    TrendDelta,
    _assets_checked_out,
    _low_stock_count,
    build_coastal_metrics,
    customers_map,
    format_period_range,
)
from .coastal_theme import COASTAL_MARKER, inject_coastal_theme
from .services import DashboardContext, DashboardTables
from .utils import STATE_DATE_END, STATE_DATE_START, is_open_job, recent_rows

try:
    from app.services.job_service import job_number_display
    from app.ui import IPS_NAV_PENDING_KEY, role_can_open_page
except ImportError:
    from services.job_service import job_number_display  # type: ignore
    from ui import IPS_NAV_PENDING_KEY, role_can_open_page  # type: ignore

try:
    from app.ui.components.empty_states import render_empty_state
except ImportError:
    from ui.components.empty_states import render_empty_state  # type: ignore

try:
    from .coastal_sidebar import inject_coastal_sidebar_footer
except ImportError:
    inject_coastal_sidebar_footer = None  # type: ignore


def _nav(page: str) -> None:
    st.session_state[IPS_NAV_PENDING_KEY] = page
    st.rerun()


def _welcome_name() -> str:
    try:
        from app.auth import current_profile
    except ImportError:
        from auth import current_profile  # type: ignore
    prof = current_profile() or {}
    nm = str(prof.get("full_name") or prof.get("name") or "").strip()
    return nm or str(prof.get("email") or "there").split("@")[0]


def _money(v: float) -> str:
    return f"${v:,.2f}"


def _trend_html(
    t: TrendDelta,
    *,
    money: bool = False,
    prior_label: str = "",
    invert: bool = False,
    use_percent: bool = False,
) -> str:
    arrow = {"up": "↑", "down": "↓", "flat": "—"}[t.direction]
    if t.direction == "flat":
        txt = "No change"
    elif use_percent and t.pct is not None:
        txt = f"{arrow} {abs(t.pct):.1f}%"
    elif money:
        txt = f"{arrow} {_money(abs(t.value))}"
    else:
        txt = f"{arrow} {abs(int(t.value)):,}"
    vs = " vs previous period" if not prior_label else f" vs {prior_label}"
    cls = t.direction
    if invert and t.direction == "up":
        cls = "bad-up"
    elif invert and t.direction == "down":
        cls = "good-down"
    return f'<p class="ips-coastal-kpi-trend {cls}">{html.escape(txt + vs)}</p>'


def _kpi_html(
    label: str,
    value: str,
    icon: str,
    bg: str,
    trend: TrendDelta,
    *,
    money: bool,
    prior_label: str,
    invert: bool = False,
    use_percent: bool = False,
) -> str:
    return (
        f'<div class="ips-coastal-kpi">'
        f'<div class="ips-coastal-kpi-top">'
        f'<div class="ips-coastal-kpi-icon" style="background:{bg}">{icon}</div>'
        f'<div class="ips-coastal-kpi-body">'
        f'<p class="ips-coastal-kpi-label">{html.escape(label)}</p>'
        f'<p class="ips-coastal-kpi-value">{html.escape(value)}</p>'
        f"</div></div>"
        f"{_trend_html(trend, money=money, prior_label=prior_label, invert=invert, use_percent=use_percent)}"
        f"</div>"
    )


def _ensure_date_range_state() -> None:
    if STATE_DATE_END not in st.session_state:
        st.session_state[STATE_DATE_END] = date.today()
    if STATE_DATE_START not in st.session_state:
        end = st.session_state[STATE_DATE_END]
        if hasattr(end, "date"):
            end = end.date()  # type: ignore[union-attr]
        st.session_state[STATE_DATE_START] = end - timedelta(days=30)


def _date_range() -> tuple[date, date]:
    _ensure_date_range_state()
    end = st.session_state.get(STATE_DATE_END) or date.today()
    start = st.session_state.get(STATE_DATE_START) or (end - timedelta(days=30))
    if hasattr(end, "date"):
        end = end.date()  # type: ignore[union-attr]
    if hasattr(start, "date"):
        start = start.date()  # type: ignore[union-attr]
    if start > end:
        start, end = end, start
    return start, end


def _card_header(title: str, *, view_key: str | None = None, page: str | None = None, ctx: DashboardContext | None = None) -> None:
    left, right = st.columns([2.2, 1], gap="small")
    with left:
        st.markdown(f'<p class="ips-coastal-card-title">{html.escape(title)}</p>', unsafe_allow_html=True)
    with right:
        if view_key and page and ctx and role_can_open_page(ctx.role, page):
            st.markdown('<div class="ips-coastal-view-all-wrap">', unsafe_allow_html=True)
            if st.button("View All", key=view_key, type="secondary", use_container_width=True):
                _nav(page)
            st.markdown('</div>', unsafe_allow_html=True)


def render_coastal_header() -> tuple[date, date]:
    st.markdown(f'<div class="{COASTAL_MARKER} ips-dashboard-page" aria-hidden="true"></div>', unsafe_allow_html=True)
    inject_coastal_theme()
    if inject_coastal_sidebar_footer:
        inject_coastal_sidebar_footer()
    start, end = _date_range()
    left, right = st.columns([1.55, 1], gap="medium")
    with left:
        st.markdown('<p class="ips-coastal-dash-title">Dashboard</p>', unsafe_allow_html=True)
        st.markdown(
            f'<p class="ips-coastal-dash-sub">Welcome back, <strong>{html.escape(_welcome_name())}</strong>!</p>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown('<div class="ips-coastal-controls">', unsafe_allow_html=True)
        st.markdown(
            f'<p class="ips-coastal-date-pill">📅 {html.escape(format_period_range(start, end))}</p>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([1.25, 0.55], gap="small")
        with c1:
            dr = st.date_input("Range", value=(start, end), key="coastal_dash_dr", label_visibility="collapsed")
            if isinstance(dr, tuple) and len(dr) == 2:
                st.session_state[STATE_DATE_START], st.session_state[STATE_DATE_END] = dr[0], dr[1]
                start, end = dr[0], dr[1]
        with c2:
            if st.button("⚙ Customize", key="coastal_customize", use_container_width=True):
                st.session_state["coastal_customize_open"] = not st.session_state.get("coastal_customize_open", False)
        st.markdown("</div>", unsafe_allow_html=True)
    return start, end


def render_coastal_kpis(m: CoastalMetrics) -> None:
    prior = m.prior_period_label
    specs = [
        ("Total Sales", _money(m.total_sales), "💰", "#dbeafe", m.sales_trend, True, False, True),
        ("Open Invoices", _money(m.open_invoices_amount), "🧾", "#dcfce7", m.invoices_trend, True, True, True),
        ("Active Jobs", f"{m.active_jobs:,}", "🔧", "#ede9fe", m.jobs_trend, False, False),
        ("Open Estimates", f"{m.open_estimates:,}", "📄", "#ffedd5", m.estimates_trend, False, True),
        ("Total Inventory Value", _money(m.inventory_value), "📦", "#e0f2fe", m.inventory_trend, True, False, False),
    ]
    cols = st.columns(5, gap="small")
    for col, s in zip(cols, specs):
        with col:
            st.markdown(
                _kpi_html(
                    s[0], s[1], s[2], s[3], s[4],
                    money=s[5], prior_label=prior, invert=s[6],
                    use_percent=s[7] if len(s) > 7 else False,
                ),
                unsafe_allow_html=True,
            )


def _render_alerts_panel(
    *,
    low_stock: int,
    assets_out: int,
    ctx: DashboardContext,
) -> None:
    if low_stock <= 0 and assets_out <= 0:
        return
    parts: list[str] = []
    if low_stock > 0 and role_can_open_page(ctx.role, "Inventory"):
        parts.append(
            f'<span class="ips-coastal-alert-chip warn">📦 {low_stock:,} low-stock item'
            f'{"s" if low_stock != 1 else ""}</span>'
        )
    if assets_out > 0 and role_can_open_page(ctx.role, "Who Has What"):
        parts.append(
            f'<span class="ips-coastal-alert-chip info">🏗 {assets_out:,} asset'
            f'{"s" if assets_out != 1 else ""} checked out</span>'
        )
    if not parts:
        return
    st.markdown(
        f'<div class="ips-coastal-alerts">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def render_coastal_dashboard(ctx: DashboardContext, tables: DashboardTables) -> None:
    start, end = render_coastal_header()
    expenses = list(tables.expenses or tables.po_rows or [])
    metrics = build_coastal_metrics(
        jobs=tables.jobs,
        estimates=tables.estimates,
        inv_rows=tables.inv_rows,
        expenses=expenses,
        time_entries=tables.time_entries,
        date_start=start,
        date_end=end,
    )

    show_sales = True
    show_side = True
    if st.session_state.get("coastal_customize_open"):
        with st.container(border=True):
            st.caption("Toggle sections")
            show_sales = st.checkbox(
                "Sales charts",
                value=st.session_state.get("coastal_sec_sales", True),
                key="coastal_sec_sales",
            )
            show_side = st.checkbox(
                "Activity & deadlines",
                value=st.session_state.get("coastal_sec_side", True),
                key="coastal_sec_side",
            )
    else:
        show_sales = st.session_state.get("coastal_sec_sales", True)
        show_side = st.session_state.get("coastal_sec_side", True)

    render_coastal_kpis(metrics)
    _render_alerts_panel(
        low_stock=_low_stock_count(tables.inv_rows),
        assets_out=_assets_checked_out(tables.assets),
        ctx=ctx,
    )

    if not show_sales and not show_side:
        render_empty_state(
            "Dashboard sections hidden",
            "Use Customize to show sales charts or the activity column.",
            icon="⚙️",
        )
        return

    # Row 2: Sales overview | Sales by category | Recent activity
    if show_sales and show_side:
        r2a, r2b, r2c = st.columns([2.35, 1.05, 1.05], gap="medium")
        sales_cols = (r2a, r2b)
        activity_col = r2c
    elif show_sales:
        r2a, r2b = st.columns([1.35, 1], gap="medium")
        sales_cols = (r2a, r2b)
        activity_col = None
    elif show_side:
        activity_col = st.columns([1])[0]
        sales_cols = None
    else:
        sales_cols = None
        activity_col = None

    if sales_cols:
        with sales_cols[0]:
            with st.container(border=True):
                st.markdown('<p class="ips-coastal-card-title">Sales Overview</p>', unsafe_allow_html=True)
                render_sales_line_chart(metrics.sales_by_month, metrics.sales_by_month_prev)
        with sales_cols[1]:
            with st.container(border=True):
                st.markdown('<p class="ips-coastal-card-title">Sales by Category</p>', unsafe_allow_html=True)
                render_category_donut(metrics.category_breakdown)
    if show_side and activity_col is not None:
        with activity_col:
            with st.container(border=True):
                _card_header("Recent Activity", view_key="coastal_all_act", page="PO / Expenses", ctx=ctx)
                _activity(metrics.activity)

    # Row 3: Job status | Aging | Deadlines
    if show_sales and show_side:
        r3a, r3b, r3c = st.columns(3, gap="medium")
        with r3a:
            with st.container(border=True):
                st.markdown('<p class="ips-coastal-card-title">Job Status Overview</p>', unsafe_allow_html=True)
                render_job_status_donut(metrics.job_status_breakdown)
        with r3b:
            with st.container(border=True):
                st.markdown('<p class="ips-coastal-card-title">Aging Invoices</p>', unsafe_allow_html=True)
                _aging(metrics.aging_buckets)
        with r3c:
            with st.container(border=True):
                _card_header("Upcoming Deadlines", view_key="coastal_all_dl", page="Job Database", ctx=ctx)
                _deadlines(metrics.deadlines)
    elif show_sales:
        r3a, r3b = st.columns(2, gap="medium")
        with r3a:
            with st.container(border=True):
                st.markdown('<p class="ips-coastal-card-title">Job Status Overview</p>', unsafe_allow_html=True)
                render_job_status_donut(metrics.job_status_breakdown)
        with r3b:
            with st.container(border=True):
                st.markdown('<p class="ips-coastal-card-title">Aging Invoices</p>', unsafe_allow_html=True)
                _aging(metrics.aging_buckets)
    elif show_side:
        with st.container(border=True):
            _card_header("Upcoming Deadlines", view_key="coastal_all_dl", page="Job Database", ctx=ctx)
            _deadlines(metrics.deadlines)

    # Row 4: Recent jobs | Quick actions
    if show_side:
        r4a, r4b = st.columns([2.45, 1], gap="medium")
    else:
        r4a, r4b = st.columns([1]), None
    with r4a:
        with st.container(border=True):
            _card_header("Recent Jobs", view_key="coastal_all_jobs", page="Job Database", ctx=ctx)
            _recent_jobs_table(tables.jobs, customers_map(tables.customers))
    if show_side and r4b is not None:
        with r4b:
            with st.container(border=True):
                st.markdown('<p class="ips-coastal-card-title">Quick Actions</p>', unsafe_allow_html=True)
                st.markdown('<div class="ips-qa-grid">', unsafe_allow_html=True)
                _quick_actions(ctx)
                st.markdown("</div>", unsafe_allow_html=True)


def _activity(items: list[dict[str, Any]]) -> None:
    if not items:
        render_empty_state("No recent activity", "Updates will show here.", icon="📋")
        return
    for it in items[:8]:
        age = str(it.get("age") or "")
        desc = str(it.get("desc") or it.get("meta") or "")
        st.markdown(
            f'<div class="ips-coastal-activity-row">'
            f'<div class="ips-coastal-act-icon" style="background:{html.escape(str(it.get("color") or "#f1f5f9"))}">'
            f'{html.escape(str(it.get("icon") or "•"))}</div>'
            f'<div class="ips-coastal-act-body">'
            f'<p class="ips-coastal-act-title">{html.escape(str(it.get("title") or ""))}</p>'
            f'<p class="ips-coastal-act-desc">{html.escape(desc)}</p></div>'
            f'<span class="ips-coastal-act-time">{html.escape(age)}</span></div>',
            unsafe_allow_html=True,
        )


def _deadline_pill(days: int) -> tuple[str, str]:
    if days < 0:
        return "ips-coastal-pill-red", f"{abs(days)} days overdue"
    if days <= 3:
        return "ips-coastal-pill-red", f"{days} days"
    if days <= 7:
        return "ips-coastal-pill-orange", f"{days} days"
    if days <= 14:
        return "ips-coastal-pill-blue", f"{days} days"
    return "ips-coastal-pill-green", f"{days} days"


def _deadlines(items: list[dict[str, Any]]) -> None:
    if not items:
        render_empty_state("No upcoming deadlines", "Job target dates will appear here.", icon="📅")
        return
    for it in items[:8]:
        days = int(it.get("days_left", 0))
        cls, txt = _deadline_pill(days)
        due = it.get("due")
        due_s = due.strftime("%b %d, %Y") if hasattr(due, "strftime") else str(due or "")
        st.markdown(
            f'<div class="ips-coastal-deadline-row"><div>'
            f'<p class="ips-coastal-deadline-title">{html.escape(str(it.get("label") or ""))}</p>'
            f'<p class="ips-coastal-deadline-date">{html.escape(due_s)}</p></div>'
            f'<span class="ips-coastal-pill {cls}">{html.escape(txt)}</span></div>',
            unsafe_allow_html=True,
        )


def _aging(buckets: dict[str, float]) -> None:
    total = sum(buckets.values())
    if total <= 0:
        render_empty_state("No open balances", "Unpaid expense lines drive aging buckets.", icon="🧾")
        return
    mx = max(buckets.values()) or 1.0
    colors = {
        "Current (0-30)": "#22c55e",
        "31-60 Days": "#f59e0b",
        "61-90 Days": "#f97316",
        "90+ Days": "#ef4444",
    }
    for label, amt in buckets.items():
        w = amt / mx * 100
        fill = colors.get(label, "#3b82f6")
        st.markdown(
            f'<div class="ips-coastal-aging-row"><span>{html.escape(label)}</span>'
            f'<div class="ips-coastal-aging-bar"><div class="ips-coastal-aging-fill" '
            f'style="width:{w:.0f}%;background:{fill}"></div></div>'
            f'<span class="ips-coastal-aging-amt">${amt:,.0f}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<p style="text-align:right;font-weight:700;color:#0f172a;margin:0.5rem 0 0">'
        f"Total: {_money(total)}</p>",
        unsafe_allow_html=True,
    )


def _status_pill_class(status: str) -> str:
    s = status.lower()
    if "progress" in s or s == "active":
        return "background:#dbeafe;color:#1d4ed8"
    if "sched" in s:
        return "background:#e0f2fe;color:#0369a1"
    if "hold" in s:
        return "background:#ffedd5;color:#c2410c"
    if "complete" in s or "closed" in s:
        return "background:#dcfce7;color:#166534"
    if "not" in s or "pending" in s:
        return "background:#f1f5f9;color:#475569"
    return "background:#ede9fe;color:#6d28d9"


def _job_progress(job: dict) -> float:
    for k in ("progress", "percent_complete", "completion_pct"):
        v = job.get(k)
        if v is not None and str(v).strip():
            try:
                return max(0.0, min(100.0, float(v)))
            except (TypeError, ValueError):
                pass
    s = str(job.get("status") or "").lower()
    if s in ("complete", "completed", "closed"):
        return 100.0
    if "progress" in s or s in ("active", "scheduled", "in progress"):
        return 55.0
    return 12.0


def _recent_jobs_table(jobs: list[dict], customers: dict[str, str]) -> None:
    rows = recent_rows(list(jobs or []), limit=10)
    if not rows:
        render_empty_state("No recent jobs", "Jobs will appear here.", icon="🔧")
        return

    header = (
        "<table class='ips-coastal-jobs-table'><thead><tr>"
        "<th>JOB #</th><th>PROJECT / DESCRIPTION</th><th>CUSTOMER</th>"
        "<th>STATUS</th><th>START</th><th>END</th><th>PROGRESS</th>"
        "</tr></thead><tbody>"
    )
    body_parts: list[str] = []
    for j in rows:
        if not isinstance(j, dict):
            continue
        cid = str(j.get("customer_id") or "")
        status = str(j.get("status") or "—")
        pct = _job_progress(j)
        pill = _status_pill_class(status)
        body_parts.append(
            "<tr>"
            f"<td>{html.escape(job_number_display(j.get('job_number')) or '—')}</td>"
            f"<td>{html.escape(str(j.get('job_name') or '—')[:48])}</td>"
            f"<td>{html.escape(customers.get(cid, str(j.get('customer_name') or '—'))[:32])}</td>"
            f"<td><span class='ips-status-pill' style='{pill}'>{html.escape(status)}</span></td>"
            f"<td>{html.escape(str(j.get('start_date') or '—')[:10])}</td>"
            f"<td>{html.escape(str(j.get('target_completion_date') or j.get('end_date') or '—')[:10])}</td>"
            f"<td><div class='ips-coastal-progress-wrap'>"
            f"<div class='ips-coastal-progress-bar'><div style='width:{pct:.0f}%'></div></div>"
            f"<span>{pct:.0f}%</span></div></td>"
            "</tr>"
        )
    st.markdown(header + "".join(body_parts) + "</tbody></table>", unsafe_allow_html=True)


def _quick_actions(ctx: DashboardContext) -> None:
    actions = [
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
        st.caption("No actions for your role.")
        return
    cols = st.columns(2, gap="small")
    for n, (i, ic, lb, pg) in enumerate(visible):
        with cols[n % 2]:
            label = f"{ic}\n{lb}"
            if st.button(label, key=f"coastal_qa_{i}", use_container_width=True):
                _nav(pg)
