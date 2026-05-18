"""Dashboard UI components (Streamlit rendering only)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from . import calculations as calc
from .services import DashboardContext, DashboardTables, load_task_progress_tables
from .todo_components import render_todo_list
from .utils import (
    _DASH_OUT_OVERDUE_DAYS,
    _KIT_REPL_HOT_THRESHOLD,
    _KIT_REPL_WINDOW_DAYS,
    asset_is_out,
    days_out_value,
    estimates_display_df,
    inject_dashboard_layout_css,
    is_open_job,
    is_pending_estimate,
    jobs_display_df,
    parse_co_ts,
    recent_rows,
    STATE_DATE_END,
    STATE_DATE_START,
    STATE_FILTER_COMPANY,
    STATE_FILTER_JOB_STATUS,
    STATE_SELECTED_METRIC,
    STATE_VIEW_MODE,
)

try:
    from app.auth import current_role
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
    from app.ui import IPS_NAV_PENDING_KEY, role_can_open_page
    from app.ui.field_light_theme import inject_field_light_theme
    from app.ui.page_shell import render_page_header, render_section_header
except ImportError:
    from auth import current_role  # type: ignore
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore
    from ui import IPS_NAV_PENDING_KEY, role_can_open_page  # type: ignore
    from ui.field_light_theme import inject_field_light_theme  # type: ignore
    from ui.page_shell import render_page_header, render_section_header  # type: ignore

try:
    from app.ui.components.cards import render_kpi_grid
    from app.ui.components.empty_states import render_empty_state
except ImportError:
    from ui.components.cards import render_kpi_grid  # type: ignore
    from ui.components.empty_states import render_empty_state  # type: ignore


def _init_dashboard_state() -> None:
    st.session_state.setdefault(STATE_DATE_START, None)
    st.session_state.setdefault(STATE_DATE_END, None)
    st.session_state.setdefault(STATE_FILTER_COMPANY, "")
    st.session_state.setdefault(STATE_FILTER_JOB_STATUS, "All")
    st.session_state.setdefault(STATE_SELECTED_METRIC, "")
    st.session_state.setdefault(STATE_VIEW_MODE, "overview")


def render_dashboard_header() -> None:
    st.markdown('<div class="ips-dashboard-page" aria-hidden="true"></div>', unsafe_allow_html=True)
    _init_dashboard_state()
    inject_dashboard_layout_css()
    inject_field_light_theme()
    render_page_header(
        "Dashboard",
        "Overview of jobs, tasks, inventory, and company activity.",
    )


def render_kpi_cards(kpi_specs: list[dict]) -> None:
    render_section_header("At a glance")
    st.markdown('<div class="ips-dash-grid">', unsafe_allow_html=True)
    n_cols = 4 if len(kpi_specs) > 6 else 5
    render_kpi_grid(kpi_specs, columns=n_cols)
    st.markdown("</div>", unsafe_allow_html=True)


def render_quick_actions(ctx: DashboardContext) -> None:
    """Shortcut navigation for common field workflows."""
    actions: list[tuple[str, str]] = []
    role = ctx.role
    if role_can_open_page(role, "Job Database"):
        actions.append(("Jobs", "Job Database"))
    if role_can_open_page(role, "Estimates"):
        actions.append(("Estimates", "Estimates"))
    if role_can_open_page(role, "Time Tracking"):
        actions.append(("Time", "Time Tracking"))
    if role_can_open_page(role, "Inventory"):
        actions.append(("Inventory", "Inventory"))
    if role_can_open_page(role, "PO / Expenses"):
        actions.append(("POs", "PO / Expenses"))
    if not actions:
        return
    render_section_header("Quick actions")
    cols = st.columns(min(len(actions), 4), gap="small")
    for i, (label, page) in enumerate(actions):
        with cols[i % len(cols)]:
            if st.button(label, key=f"dash_quick_{i}", use_container_width=True):
                st.session_state[IPS_NAV_PENDING_KEY] = page
                st.rerun()


def render_empty_dashboard_state() -> None:
    render_empty_state(
        "No dashboard data yet",
        "Once jobs, estimates, or inventory are loaded you will see KPIs and activity here.",
        icon="📊",
    )


def render_recent_jobs(jobs: list[dict]) -> None:
    render_section_header("Recent jobs")
    rj = recent_rows(list(jobs or []))
    if not rj:
        render_empty_state("No recent jobs", "Jobs will appear here as they are created or updated.", icon="🔧")
        return
    st.dataframe(jobs_display_df(rj), use_container_width=True, hide_index=True, height=min(320, 44 + 36 * len(rj)))


def render_recent_estimates(estimates: list[dict]) -> None:
    render_section_header("Recent estimates")
    re = recent_rows(list(estimates or []))
    if not re:
        render_empty_state(
            "No recent estimates",
            "New and updated estimates will show here.",
            icon="📄",
        )
        return
    st.dataframe(
        estimates_display_df(re),
        use_container_width=True,
        hide_index=True,
        height=min(320, 44 + 36 * len(re)),
    )


def render_open_jobs(jobs: list[dict]) -> None:
    open_rows = [j for j in (jobs or []) if isinstance(j, dict) and is_open_job(j)]
    render_section_header("Open jobs", f"{len(open_rows):,} active")
    if not open_rows:
        render_empty_state("No open jobs", "All jobs are closed or complete.", icon="✓")
        return
    show = recent_rows(open_rows, limit=15)
    st.dataframe(jobs_display_df(show), use_container_width=True, hide_index=True, height=min(360, 44 + 36 * len(show)))


def render_pending_estimates(estimates: list[dict]) -> None:
    pending = [e for e in (estimates or []) if isinstance(e, dict) and is_pending_estimate(e)]
    render_section_header("Pending estimates", "Not yet linked to a job")
    if not pending:
        render_empty_state("No pending estimates", "Estimates linked to jobs are excluded.", icon="✓")
        return
    show = recent_rows(pending, limit=15)
    st.dataframe(
        estimates_display_df(show),
        use_container_width=True,
        hide_index=True,
        height=min(360, 44 + 36 * len(show)),
    )


def render_task_progress(ctx: DashboardContext, tables: DashboardTables) -> None:
    dwp = load_task_progress_tables(
        ctx.session_key, ctx.use_admin, job_tasks=tables.job_tasks
    )
    ts, repeat = calc.task_progress_snapshot(
        today=ctx.today,
        packages=dwp["packages"],
        package_tasks=dwp["package_tasks"],
        tasks=dwp["tasks"],
        photo_rows=dwp["photo_rows"],
        executions=dwp["executions"],
    )
    with st.container(border=True):
        render_section_header("Daily work packages", "Tasks on today's work packages.")
        r1c1, r1c2, r1c3 = st.columns(3, gap="small")
        r1c1.metric("Work packages today", f"{ts.get('work_packages_today', 0):,}")
        r1c2.metric("Tasks assigned today", f"{ts.get('tasks_assigned_today', 0):,}")
        r1c3.metric("Tasks completed today", f"{ts.get('tasks_completed_today', 0):,}")
        r2c1, r2c2, r2c3 = st.columns(3, gap="small")
        r2c1.metric("Blocked tasks", f"{ts.get('blocked', 0):,}")
        r2c2.metric("High priority open", f"{ts.get('high_priority_open', 0):,}")
        r2c3.metric("Missing after photos", f"{ts.get('missing_after_photo', 0):,}")
        if repeat:
            st.caption(
                "Repeat shift delay reasons (14d): "
                + " · ".join(f"{a} ({b}×)" for a, b in repeat[:6])[:400]
            )
        c_open1, c_open2 = st.columns(2, gap="small")
        with c_open1:
            if role_can_open_page(current_role(), "Work & Plan (Supervisor)") and st.button(
                "Work & Plan (Supervisor)",
                key="dash_tasks_super_open",
                use_container_width=True,
            ):
                st.session_state[IPS_NAV_PENDING_KEY] = "Work & Plan (Supervisor)"
                st.rerun()
        with c_open2:
            if role_can_open_page(current_role(), "Assign Tasks (PM)") and st.button(
                "Assign Tasks (PM)",
                key="dash_tasks_pm_open",
                use_container_width=True,
            ):
                st.session_state[IPS_NAV_PENDING_KEY] = "Assign Tasks (PM)"
                st.rerun()


def render_who_has_what(tables: DashboardTables, ctx: DashboardContext) -> None:
    rows = [a for a in (tables.assets or []) if isinstance(a, dict) and asset_is_out(a)]
    jobs_sorted = sort_jobs_by_number_then_name(list(tables.jobs or []))
    job_by_id = {str(j.get("id")): j for j in jobs_sorted if j.get("id")}
    emp_id_to_name = {
        str(e["id"]): str(e.get("name") or "").strip() or "—"
        for e in (tables.employees or [])
        if isinstance(e, dict) and e.get("id")
    }
    n_out, n_overdue, n_on_job = calc.who_has_what_counts(
        tables.assets, overdue_days=_DASH_OUT_OVERDUE_DAYS
    )

    with st.container(border=True):
        st.markdown("##### Who Has What")
        st.caption("Tools and assets with **Checked Out** status or an assigned holder.")
        m1, m2, m3 = st.columns(3, gap="small")
        m1.metric("Checked out tools", f"{n_out:,}")
        m2.metric("Overdue tools", f"{n_overdue:,}")
        m3.metric("Assigned to jobs", f"{n_on_job:,}")

        if not rows:
            st.caption("Nothing checked out or held right now.")
        else:
            disp: list[dict] = []
            for r in rows:
                eid = str(r.get("current_holder_employee_id") or "").strip()
                holder = emp_id_to_name.get(eid) or str(r.get("assigned_employee") or "").strip() or "—"
                jid = r.get("assigned_job_id")
                jl = "—"
                if jid and str(jid).strip() in job_by_id:
                    jl = job_row_select_label(job_by_id[str(jid).strip()])
                co = parse_co_ts(r.get("last_checkout_at"))
                co_s = co.strftime("%Y-%m-%d %H:%M") if co else "—"
                dv = days_out_value(r.get("last_checkout_at"))
                days_s = (
                    f"{int(dv)} d"
                    if dv is not None and dv >= 1.0
                    else (f"{dv:.1f} d" if dv is not None else "—")
                )
                disp.append(
                    {
                        "Tool / asset": str(r.get("asset_name") or "—").strip() or "—",
                        "Holder": holder,
                        "Job": jl,
                        "Checked out": co_s,
                        "Days out": days_s,
                        "Status": str(r.get("status") or "").strip() or "—",
                    }
                )
            df = pd.DataFrame(disp)
            df["_sort"] = [days_out_value(x.get("last_checkout_at")) for x in rows]
            df = df.sort_values(by="_sort", ascending=False, na_position="last").drop(
                columns=["_sort"], errors="ignore"
            )
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                height=min(420, 44 + 36 * len(df)),
            )

        if role_can_open_page(ctx.role, "Who Has What"):
            if st.button("View all", key="dash_whw_view_all", help="Open the full Who Has What page"):
                st.session_state[IPS_NAV_PENDING_KEY] = "Who Has What"
                st.rerun()


def _render_kit_theft_alerts(tables: DashboardTables, ctx: DashboardContext) -> None:
    if not role_can_open_page(ctx.role, "Asset Database"):
        return
    trailers = {
        str(a.get("id") or "").strip(): a
        for a in (tables.assets or [])
        if isinstance(a, dict) and str(a.get("asset_type") or "").strip().lower() == "tool trailer"
    }
    if not trailers:
        return
    metrics = calc.kit_theft_metrics(tables.assets, tables.kit_items, tables.kit_replacements)
    n_short = int(metrics["short_lines"])
    n_hot = int(metrics["hot_items"])
    if not n_short and not n_hot and not metrics["replacements_90d"]:
        return

    with st.container(border=True):
        st.markdown("##### Kit theft / audit signals")
        st.caption(
            f"Tool trailer kit lines only. **Hot items** = ≥{_KIT_REPL_HOT_THRESHOLD} replacement rows in the last "
            f"{_KIT_REPL_WINDOW_DAYS} days. Missing value uses shortage × replacement cost."
        )
        m1, m2, m3, m4 = st.columns(4, gap="small")
        m1.metric("Kit lines with shortage", f"{int(metrics['short_lines']):,}")
        m2.metric(f"Replacements ({_KIT_REPL_WINDOW_DAYS}d)", f"{int(metrics['replacements_90d']):,}")
        m3.metric("Hot kit items (90d)", f"{n_hot:,}")
        m4.metric("Est. missing value", f"${float(metrics['missing_value']):,.0f}")
        if n_short or n_hot:
            st.warning(
                "Review **Asset Database** → open a **Tool Trailer** → **Tool Kits** → **Count / Audit Kit**."
            )
        if st.button("Open Asset Database", key="dash_kit_open_adb", help="Manage trailers and kit audits"):
            st.session_state[IPS_NAV_PENDING_KEY] = "Asset Database"
            st.rerun()


def render_alerts_panel(tables: DashboardTables, ctx: DashboardContext) -> None:
    """Inventory, asset, and kit alerts."""
    low_n = calc.count_low_stock(tables.inv_rows)
    has_inv_alert = bool(tables.inv_rows and low_n > 0)
    kit_metrics = (
        calc.kit_theft_metrics(tables.assets, tables.kit_items, tables.kit_replacements)
        if role_can_open_page(ctx.role, "Asset Database")
        else None
    )
    has_kit_alert = bool(
        kit_metrics
        and (
            int(kit_metrics.get("short_lines", 0))
            or int(kit_metrics.get("hot_items", 0))
            or int(kit_metrics.get("replacements_90d", 0))
        )
    )

    if not has_inv_alert and not has_kit_alert:
        return

    if has_inv_alert:
        disp = calc.low_stock_display_df(tables.inv_rows)
        if disp is not None and not disp.empty:
            st.markdown('<span class="ips-surface-soft" aria-hidden="true"></span>', unsafe_allow_html=True)
            render_section_header("Low stock alerts", "At or below reorder point.")
            st.dataframe(
                disp,
                use_container_width=True,
                hide_index=True,
                height=min(360, 44 + 30 * len(disp)),
            )

    if has_kit_alert:
        _render_kit_theft_alerts(tables, ctx)


def render_charts_section(tables: DashboardTables, ctx: DashboardContext) -> None:
    """Summary charts (collapsed by default)."""
    has_jobs = bool(tables.jobs)
    has_est = bool(tables.estimates)
    has_labor = bool(tables.time_entries)
    if not has_jobs and not has_est and not has_labor:
        return
    with st.expander("Charts", expanded=False):
        from . import charts

        if not has_jobs and not has_est:
            st.caption("No chart data available.")
        if has_jobs or has_est:
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if has_jobs:
                    charts.render_jobs_chart(tables.jobs)
                else:
                    st.caption("No chart data available for jobs.")
            with c2:
                if has_est:
                    charts.render_estimates_chart(tables.estimates)
                else:
                    st.caption("No chart data available for estimates.")
        if has_labor:
            charts.render_labor_summary_chart(
                tables.time_entries, work_date=ctx.today.isoformat()
            )
        if has_jobs:
            charts.render_profitability_chart(tables.jobs)


def render_jobs_estimates_grid(tables: DashboardTables) -> None:
    """Side-by-side recent activity on wide screens."""
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        render_recent_jobs(tables.jobs)
    with c2:
        render_recent_estimates(tables.estimates)


def render_todo_section(ctx: DashboardContext, tables: DashboardTables) -> None:
    render_todo_list(
        session_key=ctx.session_key,
        use_admin=ctx.use_admin,
        todos=tables.todos,
    )
