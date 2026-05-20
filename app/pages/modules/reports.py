"""Reports module (Phase 2D)."""

from __future__ import annotations

import csv
import html
import io
from typing import Any, Callable

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.status import status_pill_html
    from app.components.tables import render_data_table
    from app.components.tabs import render_tabs
    from app.pages.modules._data import (
        demo_report_asset_maintenance,
        demo_report_certs_expiring,
        demo_report_completed_jobs,
        demo_report_inventory_value,
        demo_report_job_profitability,
        demo_report_labor_by_employee,
        demo_report_labor_by_job,
        demo_report_low_stock,
        demo_report_open_estimates,
        demo_report_timekeeping_summary,
    )
    from app.utils.formatting import fmt_currency, fmt_date, fmt_hours
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._data import (  # type: ignore
        demo_report_asset_maintenance,
        demo_report_certs_expiring,
        demo_report_completed_jobs,
        demo_report_inventory_value,
        demo_report_job_profitability,
        demo_report_labor_by_employee,
        demo_report_labor_by_job,
        demo_report_low_stock,
        demo_report_open_estimates,
        demo_report_timekeeping_summary,
    )
    from utils.formatting import fmt_currency, fmt_date, fmt_hours  # type: ignore

_TAB_KEY = "ips_reports_tab"


def _csv_download(rows: list[dict[str, Any]], filename: str, key: str) -> None:
    if not rows:
        st.caption("No rows to export.")
        return
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    st.download_button(
        "Export CSV",
        buf.getvalue(),
        file_name=filename,
        mime="text/csv",
        key=key,
        use_container_width=True,
    )


def _report_block(
    title: str,
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    *,
    csv_name: str,
    key: str,
    cell_fn: Callable[[str, dict], str] | None = None,
) -> None:
    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-report-section">', unsafe_allow_html=True)
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(f'<p class="ips-report-section-title">{html.escape(title)}</p>', unsafe_allow_html=True)
    with h2:
        _csv_download(rows, csv_name, key)
    id_key = "id" if rows and "id" in rows[0] else (list(rows[0].keys())[0] if rows else "id")
    render_data_table(
        rows,
        columns,
        row_id_key=id_key,
        selected_id=None,
        session_select_key=f"_rpt_{key}",
        cell_renderer=cell_fn,
        hide_select=True,
    )
    st.markdown(f"</{ot}>", unsafe_allow_html=True)


def _render_financial() -> None:
    prof_rows = demo_report_job_profitability()
    prof_display = [
        {
            "id": r["job_number"],
            "job_number": r["job_number"],
            "job_name": r["job_name"],
            "revenue": fmt_currency(r.get("revenue")),
            "cost": fmt_currency(r.get("cost")),
            "margin_pct": f"{float(r.get('margin_pct') or 0):.1f}%",
        }
        for r in prof_rows
    ]
    _report_block(
        "Job Profitability",
        prof_display,
        [
            ("job_number", "JOB #"),
            ("job_name", "PROJECT"),
            ("revenue", "REVENUE"),
            ("cost", "COST"),
            ("margin_pct", "MARGIN %"),
        ],
        csv_name="job_profitability.csv",
        key="profit",
    )
    open_est = [
        {"id": str(r.get("estimate_number")), **r, "total": fmt_currency(r.get("total"))}
        for r in demo_report_open_estimates()
    ]
    _report_block(
        "Open Estimates",
        open_est,
        [("estimate_number", "ESTIMATE #"), ("customer", "CUSTOMER"), ("status", "STATUS"), ("total", "TOTAL")],
        csv_name="open_estimates.csv",
        key="open_est",
    )
    _report_block(
        "Completed Jobs",
        [{"id": r["job_number"], **r, "end_date": fmt_date(r.get("end_date"))} for r in demo_report_completed_jobs()],
        [("job_number", "JOB #"), ("job_name", "PROJECT"), ("customer", "CUSTOMER"), ("end_date", "COMPLETED")],
        csv_name="completed_jobs.csv",
        key="completed",
    )


def _render_labor() -> None:
    labor_job = [
        {
            "id": r["job_number"],
            **r,
            "st_hours": fmt_hours(r.get("st_hours")),
            "ot_hours": fmt_hours(r.get("ot_hours")),
            "dt_hours": fmt_hours(r.get("dt_hours")),
            "total_hours": fmt_hours(r.get("total_hours")),
        }
        for r in demo_report_labor_by_job()
    ]
    _report_block(
        "Labor Hours by Job",
        labor_job,
        [
            ("job_number", "JOB #"),
            ("st_hours", "ST"),
            ("ot_hours", "OT"),
            ("dt_hours", "DT"),
            ("total_hours", "TOTAL"),
        ],
        csv_name="labor_by_job.csv",
        key="labor_job",
    )
    labor_emp = [
        {
            "id": r["employee"],
            **r,
            "st_hours": fmt_hours(r.get("st_hours")),
            "ot_hours": fmt_hours(r.get("ot_hours")),
            "dt_hours": fmt_hours(r.get("dt_hours")),
            "total_hours": fmt_hours(r.get("total_hours")),
        }
        for r in demo_report_labor_by_employee()
    ]
    _report_block(
        "Labor Hours by Employee",
        labor_emp,
        [
            ("employee", "EMPLOYEE"),
            ("st_hours", "ST"),
            ("ot_hours", "OT"),
            ("dt_hours", "DT"),
            ("total_hours", "TOTAL"),
        ],
        csv_name="labor_by_employee.csv",
        key="labor_emp",
    )
    tk = demo_report_timekeeping_summary()
    tk_rows = [
        {
            "id": r.get("id"),
            "name": r.get("name"),
            "department": r.get("department"),
            "st_total": fmt_hours(r.get("st_total")),
            "ot_total": fmt_hours(r.get("ot_total")),
            "status": r.get("status"),
        }
        for r in tk
    ]

    def _tk_cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        return html.escape(str(row.get(field) or "—"))

    _report_block(
        "Timekeeping Approval Summary",
        tk_rows,
        [("name", "EMPLOYEE"), ("department", "DEPARTMENT"), ("st_total", "ST HRS"), ("ot_total", "OT HRS"), ("status", "STATUS")],
        csv_name="timekeeping_summary.csv",
        key="timekeeping",
        cell_fn=_tk_cell,
    )


def _render_inventory_assets() -> None:
    inv_val = [
        {"id": r["category"], **r, "on_hand_value": fmt_currency(r.get("on_hand_value"))}
        for r in demo_report_inventory_value()
    ]
    _report_block(
        "Inventory Value",
        inv_val,
        [("category", "CATEGORY"), ("sku_count", "SKUS"), ("on_hand_value", "VALUE")],
        csv_name="inventory_value.csv",
        key="inv_val",
    )
    _report_block(
        "Low Stock",
        [{"id": str(r.get("sku")), **r} for r in demo_report_low_stock()],
        [("sku", "SKU"), ("name", "ITEM"), ("qty_on_hand", "ON HAND"), ("reorder_point", "REORDER PT")],
        csv_name="low_stock.csv",
        key="low_stock",
    )

    def _maint_cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        return html.escape(str(row.get(field) or "—"))

    _report_block(
        "Asset Maintenance Due",
        [{"id": r["asset_number"], **r} for r in demo_report_asset_maintenance()],
        [("asset_number", "ASSET #"), ("name", "NAME"), ("next_service", "NEXT SERVICE"), ("status", "STATUS")],
        csv_name="asset_maintenance.csv",
        key="maint",
        cell_fn=_maint_cell,
    )


def _render_compliance() -> None:
    def _cert_cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        return html.escape(str(row.get(field) or "—"))

    _report_block(
        "Certifications Expiring",
        [{"id": f"{r.get('employee_name')}-{r.get('cert_type')}", **r} for r in demo_report_certs_expiring()],
        [("employee_name", "EMPLOYEE"), ("cert_type", "TYPE"), ("expiration_date", "EXPIRES"), ("status", "STATUS")],
        csv_name="certs_expiring.csv",
        key="certs",
        cell_fn=_cert_cell,
    )


def render() -> None:
    try:
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
    if not begin_module("reports"):
        return
    render_page_header("Reports", "Operational summaries with CSV export.")

    tab = render_tabs(
        ["Financial", "Labor & Time", "Inventory & Assets", "Compliance"],
        session_key=_TAB_KEY,
        default="Financial",
    )
    if tab == "Financial":
        _render_financial()
    elif tab == "Labor & Time":
        _render_labor()
    elif tab == "Inventory & Assets":
        _render_inventory_assets()
    else:
        _render_compliance()
