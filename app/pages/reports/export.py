"""
Export and download helpers for the Reports module.
Supports CSV export. PDF is not currently available in this app;
a printable view is provided via CSV download.
"""
from __future__ import annotations

from datetime import date
from io import StringIO
from typing import Any

import pandas as pd
import streamlit as st


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Encode a DataFrame as UTF-8 CSV bytes (with BOM for Excel compatibility)."""
    buf = StringIO()
    df.to_csv(buf, index=False)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def render_csv_download(
    df: pd.DataFrame,
    *,
    filename: str,
    label: str = "Download CSV",
    disabled: bool = False,
    key: str | None = None,
) -> None:
    """Render a Streamlit download button for a DataFrame as CSV."""
    if df.empty:
        st.caption("_No data to export._")
        return
    data = df_to_csv_bytes(df)
    st.download_button(
        label=label,
        data=data,
        file_name=filename,
        mime="text/csv",
        disabled=disabled,
        key=key,
        use_container_width=True,
    )


def build_labor_export_df(
    time_entries: list[dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
    job_labels: dict[str, str],
) -> pd.DataFrame:
    from .utils import safe_float
    rows = []
    for te in time_entries:
        jid = str(te.get("job_id") or "").strip()
        eid = str(te.get("employee_id") or "").strip()
        emp = employees_by_id.get(eid, {})
        rate = safe_float(emp.get("hourly_rate"))
        hours = safe_float(te.get("hours"))
        rows.append({
            "Date": str(te.get("work_date") or "")[:10],
            "Employee": str(emp.get("name") or eid[:8] or "—").strip(),
            "Job": job_labels.get(jid, jid[:12] or "—"),
            "Hours": round(hours, 2),
            "Rate": round(rate, 2),
            "Cost": round(hours * rate, 2),
        })
    return pd.DataFrame(rows)


def build_job_cost_export_df(
    jobs: list[dict[str, Any]],
    estimates_by_id: dict[str, dict[str, Any]],
    labor_by_job: dict[str, float],
    material_by_job: dict[str, float],
    equipment_by_job: dict[str, float],
    job_labels: dict[str, str],
) -> pd.DataFrame:
    from .calculations import estimate_amount_for_job, gross_profit, margin_percentage
    from .utils import safe_float
    rows = []
    for job in jobs:
        jid = str(job.get("id") or "").strip()
        labor = safe_float(labor_by_job.get(jid))
        mat = safe_float(material_by_job.get(jid))
        eq = safe_float(equipment_by_job.get(jid))
        total = labor + mat + eq
        est = estimate_amount_for_job(job, estimates_by_id)
        gp = gross_profit(revenue=est or 0, total_cost=total) if est is not None else None
        margin = margin_percentage(revenue=est or 0, total_cost=total) if est is not None else None
        rows.append({
            "Job": job_labels.get(jid, jid[:12]),
            "Status": str(job.get("status") or ""),
            "Labor Cost": round(labor, 2),
            "Material Cost": round(mat, 2),
            "Equipment Cost": round(eq, 2),
            "Total Cost": round(total, 2),
            "Estimate": round(est, 2) if est is not None else "",
            "Gross Profit": round(gp, 2) if gp is not None else "",
            "Margin %": round(margin, 1) if margin is not None else "",
        })
    return pd.DataFrame(rows)


def build_inventory_export_df(
    items: list[dict[str, Any]],
    usage_by_item: dict[str, float],
) -> pd.DataFrame:
    from .utils import safe_float
    rows = []
    for item in items:
        iid = str(item.get("id") or "").strip()
        rows.append({
            "Item": str(item.get("item_name") or ""),
            "SKU": str(item.get("sku") or ""),
            "Qty On Hand": safe_float(item.get("quantity_on_hand")),
            "Reorder Point": safe_float(item.get("reorder_point")),
            "Unit Cost": safe_float(item.get("unit_cost")),
            "Est. Value": round(safe_float(item.get("quantity_on_hand")) * safe_float(item.get("unit_cost")), 2),
            "Qty Issued (range)": round(usage_by_item.get(iid, 0.0), 2),
            "Active": bool(item.get("is_active", True)),
        })
    return pd.DataFrame(rows)


def build_asset_export_df(
    assets: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    job_labels: dict[str, str],
) -> pd.DataFrame:
    assignment_by_asset: dict[str, dict[str, Any]] = {}
    for a in assignments:
        aid = str(a.get("asset_id") or "").strip()
        if aid and not a.get("returned_date"):
            assignment_by_asset[aid] = a
    rows = []
    for asset in assets:
        aid = str(asset.get("id") or "").strip()
        assign = assignment_by_asset.get(aid)
        jid = str((assign or {}).get("job_id") or "").strip() if assign else ""
        rows.append({
            "Asset": str(asset.get("asset_name") or asset.get("label") or ""),
            "Status": str(asset.get("status") or ""),
            "Type": str(asset.get("asset_type") or asset.get("category") or ""),
            "Serial #": str(asset.get("serial_number") or ""),
            "Assigned To": job_labels.get(jid, "—") if jid else "—",
            "Assigned Date": str((assign or {}).get("assigned_date") or "")[:10] if assign else "",
        })
    return pd.DataFrame(rows)
