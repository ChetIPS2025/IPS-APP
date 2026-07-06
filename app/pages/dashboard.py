"""Dashboard module (Phase 2) — operations executive layout."""

from __future__ import annotations

import html
from datetime import date, timedelta

import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.components.cards import render_ops_kpi_row
    from app.components.dashboard_active_jobs_table import render_dashboard_active_jobs_table
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
        load_documents_hub,
    )
    from app.styles import inject_global_css, inject_ops_dashboard_css
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from components.cards import render_ops_kpi_row  # type: ignore
    from components.dashboard_active_jobs_table import render_dashboard_active_jobs_table  # type: ignore
    from components.company_updates_feed import render_dashboard_company_updates_section  # type: ignore
    from components.dashboard_preview_cards import render_dashboard_preview_sections  # type: ignore
    from components.headers import (  # type: ignore
        render_ops_quick_action_tiles,
        render_page_brand_header,
    )
    from pages._core._data import (  # type: ignore
        load_awarded_jobs,
        load_dashboard_kpis,
        load_documents_hub,
        load_estimates,
        load_recent_company_updates,
        load_tasks,
        load_timekeeping_summaries,
    )
    from styles import inject_global_css, inject_ops_dashboard_css  # type: ignore
    from utils.formatting import fmt_currency, fmt_date  # type: ignore


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


def _activity_widget_html(
    icon: str,
    title: str,
    lines: list[str],
    *,
    empty: str = "Nothing scheduled",
) -> str:
    ot = "d" + "iv"
    if lines:
        items = "".join(f'<li class="ips-ops-widget-item">{line}</li>' for line in lines)
    else:
        items = f'<li class="ips-ops-widget-empty">{html.escape(empty)}</li>'
    return (
        f'<{ot} class="ips-ops-widget">'
        f'<{ot} class="ips-ops-widget-head">'
        f'<span class="ips-ops-widget-icon">{html.escape(icon)}</span>'
        f'<p class="ips-ops-widget-title">{html.escape(title)}</p>'
        f"</{ot}>"
        f'<ul class="ips-ops-widget-list">{items}</ul>'
        f"</{ot}>"
    )


def _activity_card_html(title: str, lines: list[str], *, empty: str = "Nothing scheduled") -> str:
    icon_map = {
        "Today's Scheduled Jobs": "📅",
        "Employees Clocked In": "👷",
        "Recent Job Updates": "💼",
        "Recent Time Entries": "⏱",
        "Recent Documents": "📎",
        "Recent Estimates": "📋",
    }
    return _activity_widget_html(icon_map.get(title, "•"), title, lines, empty=empty)


def _today_iso() -> str:
    return date.today().isoformat()


def _jobs_scheduled_today(limit: int = 4) -> list[str]:
    today = _today_iso()
    lines: list[str] = []
    for job in load_awarded_jobs():
        when = str(job.get("awarded_date") or job.get("start_date") or "")[:10]
        if when != today:
            continue
        num = str(job.get("job_number") or "").strip()
        name = str(job.get("job_name") or job.get("name") or "").strip()
        label = f"{num} — {name}" if num and name else (num or name or "Scheduled job")
        lines.append(html.escape(label))
        if len(lines) >= limit:
            break
    return lines


def _employees_clocked_in_lines(limit: int = 4) -> list[str]:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    lines: list[str] = []
    for row in load_timekeeping_summaries(week_start):
        hours = float(row.get("st_total") or 0) + float(row.get("ot_total") or 0)
        if hours <= 0:
            continue
        name = str(row.get("name") or "Employee").strip()
        dept = str(row.get("department") or "").strip()
        suffix = f" · {html.escape(dept)}" if dept else ""
        lines.append(f"{html.escape(name)}{suffix} — {hours:.1f}h")
        if len(lines) >= limit:
            break
    return lines


def _recent_job_update_lines(limit: int = 4) -> list[str]:
    jobs = sorted(
        load_awarded_jobs(),
        key=lambda row: str(row.get("updated_at") or row.get("awarded_date") or ""),
        reverse=True,
    )
    lines: list[str] = []
    for job in jobs:
        num = str(job.get("job_number") or "").strip()
        name = str(job.get("job_name") or job.get("name") or "").strip()
        status = str(job.get("status") or "").strip()
        label = f"{num} — {name}" if num and name else (num or name or "Job update")
        if status:
            label = f"{label} ({status})"
        lines.append(html.escape(label))
        if len(lines) >= limit:
            break
    return lines


def _recent_time_entry_lines(limit: int = 4) -> list[str]:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    rows = sorted(
        load_timekeeping_summaries(week_start),
        key=lambda row: float(row.get("st_total") or 0) + float(row.get("ot_total") or 0),
        reverse=True,
    )
    lines: list[str] = []
    for row in rows:
        hours = float(row.get("st_total") or 0) + float(row.get("ot_total") or 0)
        if hours <= 0:
            continue
        name = str(row.get("name") or "Employee").strip()
        status = str(row.get("status") or "Draft").strip()
        lines.append(html.escape(f"{name} — {hours:.1f}h ({status})"))
        if len(lines) >= limit:
            break
    return lines


def _recent_document_lines(limit: int = 4) -> list[str]:
    role = current_role() or "admin"
    docs = sorted(
        load_documents_hub(role=role),
        key=lambda row: str(row.get("uploaded_at") or row.get("date") or row.get("created_at") or ""),
        reverse=True,
    )
    lines: list[str] = []
    for doc in docs:
        title = str(doc.get("title") or doc.get("name") or doc.get("filename") or "Document").strip()
        when = str(doc.get("uploaded_at") or doc.get("date") or "")[:10]
        label = f"{title} · {fmt_date(when)}" if when else title
        lines.append(html.escape(label))
        if len(lines) >= limit:
            break
    return lines


def _recent_estimate_lines(limit: int = 4) -> list[str]:
    estimates = sorted(
        load_estimates(),
        key=lambda row: str(row.get("estimate_date") or row.get("updated_at") or row.get("created_at") or ""),
        reverse=True,
    )
    lines: list[str] = []
    for est in estimates:
        num = str(est.get("estimate_number") or est.get("number") or "Estimate").strip()
        customer = str(est.get("customer") or est.get("customer_name") or "").strip()
        status = str(est.get("status") or "").strip()
        label = num
        if customer:
            label = f"{num} — {customer}"
        if status:
            label = f"{label} ({status})"
        lines.append(html.escape(label))
        if len(lines) >= limit:
            break
    return lines


def _render_todays_activity() -> None:
    ot = "d" + "iv"
    with st.container(key="dashboard_ops_activity"):
        st.markdown('<p class="ips-ops-section-title">Today\'s Activity</p>', unsafe_allow_html=True)
        panels = [
            ("📅", "Today's Jobs", _jobs_scheduled_today(), "No jobs scheduled today"),
            ("👷", "Employees Clocked In", _employees_clocked_in_lines(), "No time logged this week"),
            ("💼", "Recent Job Updates", _recent_job_update_lines(), "No recent job activity"),
            ("⏱", "Recent Time Entries", _recent_time_entry_lines(), "No time entries"),
            ("📎", "Recent Documents", _recent_document_lines(), "No recent documents"),
            ("📋", "Recent Estimates", _recent_estimate_lines(), "No recent estimates"),
        ]
        cards = "".join(
            _activity_widget_html(icon, title, lines, empty=empty)
            for icon, title, lines, empty in panels
        )
        st.markdown(f'<{ot} class="ips-ops-activity-grid">{cards}</{ot}>', unsafe_allow_html=True)


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

        with st.container(key="dashboard_ops_row2"):
            st.markdown(
                '<span class="ips-ops-row2-grid-marker" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            news_col, qa_col = st.columns([2, 1], gap="medium")
            with news_col:
                render_dashboard_company_updates_section(
                    load_recent_company_updates(limit=5),
                    limit=5,
                )
            with qa_col:
                render_ops_quick_action_tiles(
                    [
                        ("📁", "New Job", "jobs"),
                        ("📄", "New Estimate", "estimates"),
                        ("👤", "New Customer", "customers"),
                        ("📝", "Daily Report", "field_daily_reports"),
                        ("🕒", "Time Entry", "timekeeping"),
                        ("📦", "Inventory", "inventory"),
                    ],
                    key_prefix="ips_ops_qa",
                )

        _render_todays_activity()

        render_dashboard_active_jobs_table(load_awarded_jobs(), limit=12)

        render_dashboard_preview_sections()
