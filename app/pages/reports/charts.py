"""
Chart rendering functions for the Reports module.
Uses Streamlit's built-in chart APIs (bar_chart, line_chart) for broad compatibility.
Falls back to simple dataframe tables when chart data is empty.
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from .utils import money_str, safe_float


def _empty_chart(message: str = "No data available for this chart.") -> None:
    st.caption(f"_{message}_")


# ── Labor ──────────────────────────────────────────────────────────────────────


def render_labor_chart(
    time_entries: list[dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
    *,
    top_n: int = 10,
) -> None:
    """Horizontal bar chart of hours by employee."""
    if not time_entries:
        _empty_chart("No labor data for the selected range.")
        return

    from collections import defaultdict
    hours_by_emp: dict[str, float] = defaultdict(float)
    for te in time_entries:
        eid = str(te.get("employee_id") or "").strip()
        hours_by_emp[eid] += safe_float(te.get("hours"))

    rows = []
    for eid, hrs in sorted(hours_by_emp.items(), key=lambda x: -x[1])[:top_n]:
        emp = employees_by_id.get(eid, {})
        name = str(emp.get("name") or eid[:8] or "Unknown").strip()
        rows.append({"Employee": name, "Hours": round(hrs, 2)})

    if not rows:
        _empty_chart("No labor hours found.")
        return

    df = pd.DataFrame(rows).set_index("Employee")
    st.bar_chart(df, horizontal=True)


# ── Job Cost ───────────────────────────────────────────────────────────────────


def render_job_cost_chart(
    jobs: list[dict[str, Any]],
    labor_by_job: dict[str, float],
    material_by_job: dict[str, float],
    equipment_by_job: dict[str, float],
    job_labels: dict[str, str],
    *,
    top_n: int = 10,
) -> None:
    """Stacked-style bar chart of labor / material / equipment by job."""
    rows = []
    for job in jobs:
        jid = str(job.get("id") or "").strip()
        labor = safe_float(labor_by_job.get(jid))
        mat = safe_float(material_by_job.get(jid))
        eq = safe_float(equipment_by_job.get(jid))
        total = labor + mat + eq
        if total <= 0:
            continue
        lbl = job_labels.get(jid, jid[:12])
        rows.append({"Job": lbl, "Labor": round(labor, 2), "Materials": round(mat, 2), "Equipment": round(eq, 2)})

    if not rows:
        _empty_chart("No cost data found for the selected jobs.")
        return

    rows.sort(key=lambda r: -(r["Labor"] + r["Materials"] + r["Equipment"]))
    df = pd.DataFrame(rows[:top_n]).set_index("Job")
    st.bar_chart(df)


# ── Inventory Usage ────────────────────────────────────────────────────────────


def render_inventory_usage_chart(
    usage_by_item: dict[str, float],
    item_by_id: dict[str, dict[str, Any]],
    *,
    top_n: int = 10,
) -> None:
    """Bar chart of top items by quantity issued."""
    if not usage_by_item:
        _empty_chart("No inventory issue transactions in the selected range.")
        return

    top = sorted(usage_by_item.items(), key=lambda x: -x[1])[:top_n]
    rows = []
    for iid, qty in top:
        name = str(item_by_id.get(iid, {}).get("item_name") or iid[:10]).strip()
        rows.append({"Item": name, "Qty Issued": round(qty, 2)})

    if not rows:
        _empty_chart("No inventory issues found.")
        return

    df = pd.DataFrame(rows).set_index("Item")
    st.bar_chart(df)


# ── Asset Usage ────────────────────────────────────────────────────────────────


def render_asset_usage_chart(
    assets: list[dict[str, Any]],
    by_status: dict[str, int],
) -> None:
    """Bar chart of asset counts by status."""
    if not by_status:
        _empty_chart("No asset status data available.")
        return

    rows = [{"Status": k.title(), "Count": v} for k, v in sorted(by_status.items(), key=lambda x: -x[1]) if v > 0]
    if not rows:
        _empty_chart("No assets found.")
        return

    df = pd.DataFrame(rows).set_index("Status")
    st.bar_chart(df)


# ── Profitability ──────────────────────────────────────────────────────────────


def render_profitability_chart(
    jobs: list[dict[str, Any]],
    estimates_by_id: dict[str, dict[str, Any]],
    total_cost_by_job: dict[str, float],
    job_labels: dict[str, str],
    *,
    top_n: int = 10,
) -> None:
    """Bar chart of estimate vs actual cost with variance for top jobs."""
    from .calculations import estimate_amount_for_job

    rows = []
    for job in jobs:
        jid = str(job.get("id") or "").strip()
        est = estimate_amount_for_job(job, estimates_by_id)
        cost = safe_float(total_cost_by_job.get(jid))
        if est is None and cost <= 0:
            continue
        lbl = job_labels.get(jid, jid[:12])
        rows.append({
            "Job": lbl,
            "Estimate": round(est or 0, 2),
            "Actual Cost": round(cost, 2),
        })

    if not rows:
        _empty_chart("No financial data available for the selected range.")
        return

    rows.sort(key=lambda r: -max(r["Estimate"], r["Actual Cost"]))
    df = pd.DataFrame(rows[:top_n]).set_index("Job")
    st.bar_chart(df)
