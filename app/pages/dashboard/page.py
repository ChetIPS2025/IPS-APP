"""Dashboard page entry: orchestrates data load and UI modules."""

from __future__ import annotations

import streamlit as st

try:
    from app.auth import current_profile, current_role
except ImportError:
    from auth import current_profile, current_role  # type: ignore

from . import components as ui
from .services import DashboardContext, build_kpi_specs, load_dashboard_tables


def render() -> None:
    ui.render_dashboard_header()

    prof = current_profile()
    sk = str(prof.get("id") or "anonymous")
    ctx = DashboardContext(
        session_key=sk,
        use_admin=current_role() in {"admin", "manager"},
        role=current_role(),
        user_id=str(prof.get("id") or "").strip(),
    )

    tables = load_dashboard_tables(ctx)

    kpi_specs = build_kpi_specs(tables, ctx)
    ui.render_kpi_cards(kpi_specs)
    ui.render_quick_actions(ctx)
    ui.render_charts_section(tables, ctx)

    ui.render_task_progress(ctx, tables)
    ui.render_who_has_what(tables, ctx)
    ui.render_alerts_panel(tables, ctx)
    ui.render_todo_section(ctx, tables)

    ui.render_jobs_estimates_grid(tables)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        ui.render_open_jobs(tables.jobs)
    with c2:
        ui.render_pending_estimates(tables.estimates)
