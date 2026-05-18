"""
UI rendering components for the Reports module.
Each function renders one self-contained section of the Reports page.
All data is passed in as arguments — no direct DB calls from this layer.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from .charts import (
    render_asset_usage_chart,
    render_inventory_usage_chart,
    render_job_cost_chart,
    render_labor_chart,
    render_profitability_chart,
)
from .export import (
    build_asset_export_df,
    build_inventory_export_df,
    build_job_cost_export_df,
    build_labor_export_df,
    render_csv_download,
)
from .utils import DATE_RANGE_PRESETS, money_str, pct_str, safe_float, truncate


# ── Page-level header ──────────────────────────────────────────────────────────


def render_reports_header() -> None:
    try:
        from app.ui.page_shell import render_page_header
    except ImportError:
        from ui.page_shell import render_page_header  # type: ignore
    render_page_header(
        "Reports",
        "Job costing, labor, inventory, assets, and financial summaries.",
    )


# ── Filters bar ───────────────────────────────────────────────────────────────


def render_reports_filters() -> None:
    """Render the unified filter strip; writes to standardized session state keys."""
    with st.container():
        st.markdown('<span class="ips-flat-section" aria-hidden="true"></span>', unsafe_allow_html=True)
        col_date, col_type, col_view = st.columns([1.4, 1, 1], gap="small")

        with col_date:
            st.selectbox(
                "Date range",
                DATE_RANGE_PRESETS,
                key="reports_date_preset",
            )

        preset = st.session_state.get("reports_date_preset", "Last 30 Days")
        if preset == "Custom":
            c1, c2 = st.columns(2, gap="small")
            with c1:
                st.date_input("From", key="reports_date_start", value=date.today().replace(day=1))
            with c2:
                st.date_input("To", key="reports_date_end", value=date.today())
        else:
            from .utils import date_range_for_preset
            start, end = date_range_for_preset(preset)
            st.session_state["reports_date_start"] = start
            st.session_state["reports_date_end"] = end

        with col_type:
            report_types = ["All Types", "Job Reports", "Labor / Time", "Materials / Inventory", "Assets", "Financial"]
            st.selectbox("Report type", report_types, key="reports_filter_type")

        with col_view:
            st.selectbox("View mode", ["Summary", "Detail"], key="reports_view_mode")


# ── KPI summary cards ─────────────────────────────────────────────────────────


def render_report_metric_card(label: str, value: str, *, delta: str | None = None) -> None:
    st.metric(label, value, delta=delta)


def render_report_summary_cards(
    *,
    open_jobs: int,
    closed_jobs: int,
    total_labor_hours: float,
    total_labor_cost: float,
    on_hand_value: float,
    low_stock: int,
    total_assets: int,
) -> None:
    """Top-of-page KPI strip."""
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7, gap="small")
    c1.metric("Open Jobs", f"{open_jobs:,}")
    c2.metric("Closed Jobs", f"{closed_jobs:,}")
    c3.metric("Labor Hours", f"{total_labor_hours:,.1f}")
    c4.metric("Labor Cost", money_str(total_labor_cost))
    c5.metric("Inventory Value", money_str(on_hand_value))
    c6.metric("Low Stock", f"{low_stock:,}")
    c7.metric("Total Assets", f"{total_assets:,}")


# ── Job Reports tab ───────────────────────────────────────────────────────────


def render_job_reports_tab(data: dict[str, Any]) -> None:
    jobs = data.get("jobs", [])
    counts = data.get("counts", {})
    job_labels = data.get("job_labels", {})

    c1, c2, c3 = st.columns(3, gap="small")
    c1.metric("Total Jobs", counts.get("total", 0))
    c2.metric("Open / Active", counts.get("open", 0))
    c3.metric("Closed / Complete", counts.get("closed", 0))

    if not jobs:
        render_reports_empty_state("no_jobs")
        return

    rows = []
    for j in jobs:
        jid = str(j.get("id") or "").strip()
        rows.append({
            "Job": job_labels.get(jid, jid[:12]),
            "Status": str(j.get("status") or "—").strip(),
            "Customer": str(j.get("customer_name") or j.get("customer") or "—").strip(),
            "Start Date": str(j.get("start_date") or "")[:10] or "—",
            "End Date": str(j.get("end_date") or j.get("target_end_date") or "")[:10] or "—",
            "Job #": str(j.get("job_number") or "").strip(),
        })

    df = pd.DataFrame(rows)
    render_reports_table(df, key="rpt_jobs_table")

    render_csv_download(
        df,
        filename="jobs_report.csv",
        label="Download Jobs CSV",
        key="rpt_jobs_dl",
    )


# ── Labor / Time tab ──────────────────────────────────────────────────────────


def render_labor_tab(data: dict[str, Any]) -> None:
    employees_by_id = data.get("employees_by_id", {})
    time_entries = data.get("time_entries", [])
    job_labels = data.get("job_labels", {})
    total_hours = data.get("total_hours", 0.0)
    total_cost = data.get("total_cost", 0.0)
    hours_by_job = data.get("hours_by_job", {})

    c1, c2, c3 = st.columns(3, gap="small")
    c1.metric("Total Hours", f"{total_hours:,.1f}")
    c2.metric("Total Labor Cost", money_str(total_cost))
    c3.metric("Time Entries", f"{len(time_entries):,}")

    if not time_entries:
        render_reports_empty_state("no_labor")
        return

    st.markdown("#### Labor Hours by Employee")
    render_labor_chart(time_entries, employees_by_id)

    rows = []
    for te in time_entries:
        jid = str(te.get("job_id") or "").strip()
        eid = str(te.get("employee_id") or "").strip()
        emp = employees_by_id.get(eid, {})
        rate = safe_float(emp.get("hourly_rate"))
        hours = safe_float(te.get("hours"))
        rows.append({
            "Date": str(te.get("work_date") or "")[:10],
            "Employee": str(emp.get("name") or "—").strip(),
            "Job": job_labels.get(jid, jid[:12] or "—"),
            "Hours": round(hours, 2),
            "Rate": money_str(rate),
            "Cost": money_str(hours * rate),
        })

    df = pd.DataFrame(rows)
    st.markdown("#### Time Entries")
    render_reports_table(df, key="rpt_labor_table")

    export_df = build_labor_export_df(time_entries, employees_by_id, job_labels)
    render_csv_download(
        export_df,
        filename="labor_report.csv",
        label="Download Labor CSV",
        key="rpt_labor_dl",
    )


# ── Materials / Inventory tab ─────────────────────────────────────────────────


def render_inventory_tab(data: dict[str, Any]) -> None:
    items = data.get("items", [])
    item_by_id = data.get("item_by_id", {})
    usage_by_item = data.get("usage_by_item", {})
    on_hand_value = data.get("on_hand_value", 0.0)
    low_stock = data.get("low_stock_count", 0)
    issued_units = data.get("issued_units", 0.0)
    active_items = data.get("active_items", 0)

    c1, c2, c3, c4 = st.columns(4, gap="small")
    c1.metric("Active Items", f"{active_items:,}")
    c2.metric("On-Hand Value", money_str(on_hand_value))
    c3.metric("Units Issued (range)", f"{issued_units:,.1f}")
    c4.metric("Low Stock Count", f"{low_stock:,}")

    if not items:
        render_reports_empty_state("no_inventory")
        return

    if usage_by_item:
        st.markdown("#### Top Items by Quantity Issued")
        render_inventory_usage_chart(usage_by_item, item_by_id)
    else:
        st.caption("_No inventory issues in the selected date range._")

    if low_stock > 0:
        st.markdown("#### Low Stock Items")
        low_rows = [
            {
                "Item": str(r.get("item_name") or ""),
                "Qty On Hand": safe_float(r.get("quantity_on_hand")),
                "Reorder Point": safe_float(r.get("reorder_point")),
                "SKU": str(r.get("sku") or ""),
                "Vendor": str(r.get("vendor") or ""),
            }
            for r in items
            if bool(r.get("is_active", True)) and safe_float(r.get("quantity_on_hand")) <= safe_float(r.get("reorder_point"))
        ]
        render_reports_table(pd.DataFrame(low_rows), key="rpt_inv_low_table")

    export_df = build_inventory_export_df(items, usage_by_item)
    render_csv_download(
        export_df,
        filename="inventory_report.csv",
        label="Download Inventory CSV",
        key="rpt_inv_dl",
    )


# ── Assets tab ────────────────────────────────────────────────────────────────


def render_asset_tab(data: dict[str, Any]) -> None:
    assets = data.get("assets", [])
    assignments = data.get("assignments", [])
    utilization = data.get("utilization", {})
    job_labels = data.get("job_labels", {})

    c1, c2, c3, c4 = st.columns(4, gap="small")
    c1.metric("Total Assets", utilization.get("total", 0))
    c2.metric("Assigned", utilization.get("assigned", 0))
    c3.metric("Available", utilization.get("available", 0))
    by_status = utilization.get("by_status", {})
    in_shop = by_status.get("in shop", 0) + by_status.get("in_shop", 0)
    c4.metric("In Shop", in_shop)

    if not assets:
        render_reports_empty_state("no_assets")
        return

    st.markdown("#### Asset Status Distribution")
    render_asset_usage_chart(assets, by_status)

    rows = []
    assignment_by_asset: dict[str, dict[str, Any]] = {}
    for a in assignments:
        aid = str(a.get("asset_id") or "").strip()
        if aid and not a.get("returned_date"):
            assignment_by_asset[aid] = a

    for asset in assets:
        aid = str(asset.get("id") or "").strip()
        assign = assignment_by_asset.get(aid)
        jid = str((assign or {}).get("job_id") or "").strip() if assign else ""
        rows.append({
            "Asset": str(asset.get("asset_name") or asset.get("label") or ""),
            "Type": str(asset.get("asset_type") or asset.get("category") or "—"),
            "Status": str(asset.get("status") or "—"),
            "Serial #": str(asset.get("serial_number") or "—"),
            "Assigned To": job_labels.get(jid, "—") if jid else "—",
            "Assigned Date": str((assign or {}).get("assigned_date") or "")[:10] if assign else "—",
        })

    df = pd.DataFrame(rows)
    st.markdown("#### Asset List")
    render_reports_table(df, key="rpt_asset_table")

    export_df = build_asset_export_df(assets, assignments, job_labels)
    render_csv_download(
        export_df,
        filename="assets_report.csv",
        label="Download Assets CSV",
        key="rpt_asset_dl",
    )


# ── Financial / Profitability tab ─────────────────────────────────────────────


def render_financial_tab(data: dict[str, Any]) -> None:
    jobs = data.get("jobs", [])
    estimates_by_id = data.get("estimates_by_id", {})
    job_labels = data.get("job_labels", {})
    labor_by_job = data.get("labor_by_job", {})
    material_by_job = data.get("material_by_job", {})
    equipment_by_job = data.get("equipment_by_job", {})
    total_cost_by_job = data.get("total_cost_by_job", {})

    from .calculations import estimate_amount_for_job, gross_profit, margin_percentage

    total_revenue = sum(
        safe_float(estimate_amount_for_job(j, estimates_by_id))
        for j in jobs
        if estimate_amount_for_job(j, estimates_by_id) is not None
    )
    total_cost_all = sum(total_cost_by_job.values())
    gp = gross_profit(revenue=total_revenue, total_cost=total_cost_all)
    margin = margin_percentage(revenue=total_revenue, total_cost=total_cost_all)

    c1, c2, c3, c4 = st.columns(4, gap="small")
    c1.metric("Total Estimate Value", money_str(total_revenue))
    c2.metric("Total Job Cost", money_str(total_cost_all))
    c3.metric("Gross Profit", money_str(gp))
    c4.metric("Avg Margin", pct_str(margin) if margin is not None else "—")

    if not jobs:
        render_reports_empty_state("no_financial")
        return

    st.markdown("#### Estimate vs Actual Cost")
    render_profitability_chart(jobs, estimates_by_id, total_cost_by_job, job_labels)

    # Detailed table
    rows = []
    for job in jobs:
        jid = str(job.get("id") or "").strip()
        labor = safe_float(labor_by_job.get(jid))
        mat = safe_float(material_by_job.get(jid))
        eq = safe_float(equipment_by_job.get(jid))
        total = labor + mat + eq
        est = estimate_amount_for_job(job, estimates_by_id)
        gp_j = gross_profit(revenue=est or 0, total_cost=total) if est is not None else None
        margin_j = margin_percentage(revenue=est or 0, total_cost=total) if est is not None else None
        if total <= 0 and est is None:
            continue
        rows.append({
            "Job": job_labels.get(jid, jid[:12]),
            "Status": str(job.get("status") or ""),
            "Labor": money_str(labor),
            "Materials": money_str(mat),
            "Equipment": money_str(eq),
            "Total Cost": money_str(total),
            "Estimate": money_str(est) if est is not None else "—",
            "Gross Profit": money_str(gp_j) if gp_j is not None else "—",
            "Margin %": pct_str(margin_j) if margin_j is not None else "—",
        })

    if rows:
        df = pd.DataFrame(rows)
        st.markdown("#### Job Cost Detail")
        render_reports_table(df, key="rpt_fin_table")
    else:
        st.caption("_No jobs with cost or estimate data found._")

    export_df = build_job_cost_export_df(
        jobs, estimates_by_id, labor_by_job, material_by_job, equipment_by_job, job_labels
    )
    render_csv_download(
        export_df,
        filename="financial_report.csv",
        label="Download Financial CSV",
        key="rpt_fin_dl",
    )


# ── Shared table renderer ─────────────────────────────────────────────────────


def render_reports_table(df: pd.DataFrame, *, key: str | None = None) -> None:
    """Standard table display for reports — mobile friendly, no overflow."""
    if df.empty:
        st.caption("_No rows to display._")
        return
    height = min(520, 44 + 32 * len(df))
    kwargs: dict[str, Any] = {
        "use_container_width": True,
        "hide_index": True,
        "height": height,
    }
    st.dataframe(df, **kwargs)


# ── Empty states ──────────────────────────────────────────────────────────────


_EMPTY_MESSAGES: dict[str, str] = {
    "no_jobs": "No jobs found. Add jobs in the Job Database.",
    "no_labor": "No time entries found for the selected date range.",
    "no_inventory": "No inventory items found.",
    "no_assets": "No assets found in the Asset Database.",
    "no_financial": "No jobs with cost or estimate data found.",
    "no_date_range": "No data available for the selected date range.",
    "no_chart": "No chart data available.",
    "no_export": "No exportable data for the current selection.",
}


def render_reports_empty_state(kind: str = "no_date_range") -> None:
    msg = _EMPTY_MESSAGES.get(kind, "No data found.")
    st.info(msg)


# ── Detail panel ─────────────────────────────────────────────────────────────


def render_report_detail_panel(report_id: str | None, *, data: dict[str, Any]) -> None:
    """Placeholder detail panel — extended in future iterations."""
    if not report_id:
        st.caption("_Select a row to view details._")
        return
    st.caption(f"Detail for ID: `{report_id}`")
