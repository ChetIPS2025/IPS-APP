"""
Reports page — main entry point.
Wires together filters, data loading, and tab-based report rendering.
Session state keys follow the standardized reports_* prefix convention.
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from .components import (
    render_asset_tab,
    render_financial_tab,
    render_inventory_tab,
    render_job_reports_tab,
    render_labor_tab,
    render_report_summary_cards,
    render_reports_empty_state,
    render_reports_filters,
    render_reports_header,
)
from .services import (
    load_asset_report_data,
    load_financial_report_data,
    load_inventory_report_data,
    load_jobs_report_data,
    load_labor_report_data,
)
from .utils import safe_float


def _is_admin() -> bool:
    try:
        from app.auth import current_role
    except ImportError:
        from auth import current_role  # type: ignore
    return current_role() in {"admin", "pm", "manager"}


def _init_session_state() -> None:
    """Set sensible defaults for all reports session state keys."""
    st.session_state.setdefault("reports_date_preset", "Last 30 Days")
    st.session_state.setdefault("reports_filter_type", "All Types")
    st.session_state.setdefault("reports_filter_job_id", "")
    st.session_state.setdefault("reports_filter_employee_id", "")
    st.session_state.setdefault("reports_selected_report_id", "")
    st.session_state.setdefault("reports_view_mode", "Summary")

    # Ensure date range is populated even if preset hasn't triggered yet.
    if "reports_date_start" not in st.session_state or "reports_date_end" not in st.session_state:
        from .utils import date_range_for_preset
        preset = str(st.session_state.get("reports_date_preset") or "Last 30 Days")
        start, end = date_range_for_preset(preset)
        st.session_state.setdefault("reports_date_start", start)
        st.session_state.setdefault("reports_date_end", end)


def render() -> None:
    _init_session_state()
    render_reports_header()

    admin = _is_admin()

    render_reports_filters()


    date_start: date = st.session_state.get("reports_date_start") or date(2000, 1, 1)
    date_end: date = st.session_state.get("reports_date_end") or date.today()
    report_type: str = str(st.session_state.get("reports_filter_type") or "All Types")

    # ── Load data for top KPI strip ──────────────────────────────────────────
    # Load these once; individual tabs refetch with their own service calls
    # (which are cached, so repeated calls are free after the first).
    with st.spinner("Loading report data…"):
        jobs_data = load_jobs_report_data(admin=admin)
        labor_data = load_labor_report_data(admin=admin, date_start=date_start, date_end=date_end)
        inv_data = load_inventory_report_data(admin=admin, date_start=date_start, date_end=date_end)
        asset_data = load_asset_report_data(admin=admin)

    counts = jobs_data.get("counts", {})

    render_report_summary_cards(
        open_jobs=counts.get("open", 0),
        closed_jobs=counts.get("closed", 0),
        total_labor_hours=safe_float(labor_data.get("total_hours")),
        total_labor_cost=safe_float(labor_data.get("total_cost")),
        on_hand_value=safe_float(inv_data.get("on_hand_value")),
        low_stock=int(inv_data.get("low_stock_count", 0)),
        total_assets=int(asset_data.get("utilization", {}).get("total", 0)),
    )

    st.divider()

    # ── Tab navigation ──────────────────────────────────────────────────────
    # Map report type filter to the initially active tab
    _TYPE_TO_TAB: dict[str, int] = {
        "Job Reports": 0,
        "Labor / Time": 1,
        "Materials / Inventory": 2,
        "Assets": 3,
        "Financial": 4,
    }
    default_tab = _TYPE_TO_TAB.get(report_type, 0)

    tabs = st.tabs(["Jobs", "Labor / Time", "Materials / Inventory", "Assets", "Financial"])

    # ── Jobs tab ──────────────────────────────────────────────────────────────
    with tabs[0]:
        if report_type in ("All Types", "Job Reports"):
            render_job_reports_tab(jobs_data)
        else:
            st.caption("_Switch 'Report type' to 'Job Reports' or 'All Types' to see this section._")

    # ── Labor / Time tab ─────────────────────────────────────────────────────
    with tabs[1]:
        if report_type in ("All Types", "Labor / Time"):
            render_labor_tab(labor_data)
        else:
            st.caption("_Switch 'Report type' to 'Labor / Time' or 'All Types' to see this section._")

    # ── Materials / Inventory tab ─────────────────────────────────────────────
    with tabs[2]:
        if report_type in ("All Types", "Materials / Inventory"):
            render_inventory_tab(inv_data)
        else:
            st.caption("_Switch 'Report type' to 'Materials / Inventory' or 'All Types' to see this section._")

    # ── Assets tab ────────────────────────────────────────────────────────────
    with tabs[3]:
        if report_type in ("All Types", "Assets"):
            render_asset_tab(asset_data)
        else:
            st.caption("_Switch 'Report type' to 'Assets' or 'All Types' to see this section._")

    # ── Financial tab ─────────────────────────────────────────────────────────
    with tabs[4]:
        if report_type in ("All Types", "Financial"):
            fin_data = load_financial_report_data(admin=admin, date_start=date_start, date_end=date_end)
            render_financial_tab(fin_data)
        else:
            st.caption("_Switch 'Report type' to 'Financial' or 'All Types' to see this section._")
