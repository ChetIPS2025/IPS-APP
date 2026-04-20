from __future__ import annotations

"""
Job Costing rolls up **actuals by job** (``job_id`` on time entries, grid time, expenses, etc.).

When ``jobs.estimate_id`` is set, estimate totals are shown **for comparison only** — quotes
remain on the Estimates page; the job is the costing / work record.
"""

import pandas as pd
import streamlit as st

from auth import current_role
from branding import render_header

try:
    from app.ips_crud_list_styles import render_crud_list_subtitle
except ImportError:
    from ips_crud_list_styles import render_crud_list_subtitle  # type: ignore
from db import fetch_table, fetch_table_admin

try:
    from services.job_service import job_display_primary
except ImportError:
    from app.services.job_service import job_display_primary  # type: ignore

try:
    from services.employee_labor import entry_labor_dollars
except ImportError:
    from app.services.employee_labor import entry_labor_dollars  # type: ignore

try:
    from services.time_grid_service import grid_labor_cost_dollars
except ImportError:
    from app.services.time_grid_service import grid_labor_cost_dollars  # type: ignore


def _job_costing_admin_read() -> bool:
    """Match Job Database / Estimates: service-role reads so ``jobs`` rows are visible under RLS."""
    return current_role() in {"admin", "estimator"}


def render() -> None:
    render_header("Job Costing")
    render_crud_list_subtitle(
        "Actual labor, materials, travel, assets, and expenses **by job** (``job_id``). "
        "Linked quote totals appear for comparison when the job has an ``estimate_id``."
    )

    customers = fetch_table("customers", limit=5000, order_by="customer_name")
    jobs: list[dict] = []
    estimates: list[dict] = []
    if _job_costing_admin_read():
        try:
            jobs = fetch_table_admin("jobs", limit=5000, order_by="job_number")
            estimates = fetch_table_admin("estimates", limit=5000, order_by="quote_number")
        except Exception:
            jobs = fetch_table("jobs", limit=5000, order_by="job_number")
            estimates = fetch_table("estimates", limit=5000, order_by="quote_number")
    else:
        jobs = fetch_table("jobs", limit=5000, order_by="job_number")
        estimates = fetch_table("estimates", limit=5000, order_by="quote_number")
    # Costing is keyed by job id; keep any row with a primary key (all statuses — e.g. Awarded from conversion).
    jobs = [j for j in (jobs or []) if j.get("id")]
    labor_rates = fetch_table("labor_rates", limit=5000, order_by="classification")
    time_entries = fetch_table("employee_time_entries", limit=10000, order_by="entry_date")
    try:
        employees = fetch_table("employees", limit=5000, order_by="name")
    except Exception:
        employees = []
    employees_by_id = {str(e.get("id")): e for e in employees if e.get("id")}
    try:
        all_grid_te = fetch_table("time_entries", limit=50000, order_by="work_date")
    except Exception:
        all_grid_te = []
    asset_usage_logs = fetch_table("asset_usage_logs", limit=10000, order_by="usage_date")
    job_expenses = fetch_table("job_expenses", limit=10000, order_by="expense_date")

    customer_name_by_id = {c.get("id"): c.get("customer_name", "") for c in customers}
    estimate_by_id = {e.get("id"): e for e in estimates}
    labor_rate_map = {
        str(r.get("classification", "")).strip(): {
            "st_rate": float(r.get("st_rate", 0) or 0),
            "ot_rate": float(r.get("ot_rate", 0) or 0),
        }
        for r in labor_rates
    }

    if not jobs:
        st.info("No jobs found.")
        return

    rows = []
    labor_detail_rows: list[dict] = []

    def _entry_employee_display(t: dict) -> str:
        eid = t.get("employee_id")
        if eid and str(eid) in employees_by_id:
            nm = str(employees_by_id[str(eid)].get("name") or "").strip()
            if nm:
                return nm
        return str(t.get("employee_name", "") or "").strip() or "—"

    for job in jobs:
        job_id = job.get("id")
        customer_id = job.get("customer_id")
        estimate_id = job.get("estimate_id")

        # Proposal / pricing snapshot from the linked quote (optional for standalone jobs).
        estimate = estimate_by_id.get(estimate_id, {}) if estimate_id else {}

        estimated_labor = float(estimate.get("labor_total", 0) or 0)
        estimated_equipment = float(estimate.get("equipment_total", 0) or 0)
        estimated_materials = float(estimate.get("material_sell_basis", 0) or 0)
        estimated_travel = float(estimate.get("travel_total", 0) or 0)
        estimated_total = float(estimate.get("final_bid", 0) or 0)

        awarded_amount = float(job.get("awarded_amount", 0) or 0)
        if awarded_amount == 0:
            awarded_amount = float(estimate.get("proposal_total", 0) or 0)

        job_time_entries = [
            t for t in time_entries
            if t.get("job_id") == job_id and str(t.get("status", "")).strip() == "Approved"
        ]

        actual_labor = 0.0
        for t in job_time_entries:
            st_hours = float(t.get("straight_time_hours", 0) or 0)
            ot_hours = float(t.get("overtime_hours", 0) or 0)
            line_cost = entry_labor_dollars(t, labor_rate_map, employees_by_id)
            actual_labor += line_cost
            labor_detail_rows.append(
                {
                    "job_number": job_display_primary(job),
                    "job_name": job.get("job_name", ""),
                    "customer_name": customer_name_by_id.get(customer_id, ""),
                    "job_status": job.get("status", ""),
                    "employee": _entry_employee_display(t),
                    "straight_time_hours": st_hours,
                    "overtime_hours": ot_hours,
                    "labor_cost": line_cost,
                    "source": "Time entry (legacy)",
                }
            )

        for te in all_grid_te:
            if str(te.get("job_id")) != str(job_id):
                continue
            hours = float(te.get("hours", 0) or 0)
            emp = employees_by_id.get(str(te.get("employee_id")))
            line_cost = grid_labor_cost_dollars(hours, emp)
            actual_labor += line_cost
            ename = str(emp.get("name", "")).strip() if emp else "—"
            labor_detail_rows.append(
                {
                    "job_number": job_display_primary(job),
                    "job_name": job.get("job_name", ""),
                    "customer_name": customer_name_by_id.get(customer_id, ""),
                    "job_status": job.get("status", ""),
                    "employee": ename,
                    "straight_time_hours": hours,
                    "overtime_hours": 0.0,
                    "labor_cost": line_cost,
                    "source": "Weekly grid",
                }
            )

        job_asset_usage = [u for u in asset_usage_logs if u.get("job_id") == job_id]
        actual_equipment = 0.0
        for u in job_asset_usage:
            usage_days = float(u.get("usage_days", 0) or 0)
            rate_per_day = float(u.get("rate_per_day", 0) or 0)
            usage_hours = float(u.get("usage_hours", 0) or 0)
            rate_per_hour = float(u.get("rate_per_hour", 0) or 0)
            actual_equipment += (usage_days * rate_per_day) + (usage_hours * rate_per_hour)

        approved_expenses = [
            e for e in job_expenses
            if e.get("job_id") == job_id and str(e.get("status", "")).strip() in {"Approved", "Paid"}
        ]

        actual_materials = sum(
            float(e.get("amount", 0) or 0)
            for e in approved_expenses
            if str(e.get("category", "")).strip() == "Materials"
        )

        actual_travel = sum(
            float(e.get("amount", 0) or 0)
            for e in approved_expenses
            if str(e.get("category", "")).strip() in {"Travel", "Fuel", "Lodging", "Meals", "Freight"}
        )

        actual_other = sum(
            float(e.get("amount", 0) or 0)
            for e in approved_expenses
            if str(e.get("category", "")).strip() not in {"Materials", "Travel", "Fuel", "Lodging", "Meals", "Freight"}
        )

        actual_total_cost = actual_labor + actual_equipment + actual_materials + actual_travel + actual_other
        gross_profit = awarded_amount - actual_total_cost
        gross_margin_pct = (gross_profit / awarded_amount * 100) if awarded_amount else 0.0

        rows.append(
            {
                "job_number": job_display_primary(job),
                "job_name": job.get("job_name", ""),
                "customer_name": customer_name_by_id.get(customer_id, ""),
                "status": job.get("status", ""),
                "project_manager": job.get("project_manager", ""),
                "supervisor": job.get("supervisor", ""),
                "awarded_amount": awarded_amount,
                "estimated_total": estimated_total,
                "estimated_labor": estimated_labor,
                "estimated_equipment": estimated_equipment,
                "estimated_materials": estimated_materials,
                "estimated_travel": estimated_travel,
                "actual_labor": actual_labor,
                "actual_equipment": actual_equipment,
                "actual_materials": actual_materials,
                "actual_travel": actual_travel,
                "actual_other": actual_other,
                "actual_total_cost": actual_total_cost,
                "gross_profit": gross_profit,
                "gross_margin_pct": gross_margin_pct,
            }
        )

    df = pd.DataFrame(rows)

    f1, f2, f3 = st.columns([1, 1, 2], gap="small")

    customer_names = sorted([r["customer_name"] for r in rows if str(r["customer_name"]).strip()])
    selected_customer = f1.selectbox("Filter Customer", ["All"] + sorted(set(customer_names)))

    status_names = sorted([r["status"] for r in rows if str(r["status"]).strip()])
    selected_status = f2.selectbox("Filter Status", ["All"] + sorted(set(status_names)))

    search = f3.text_input(
        "Search Job Costing",
        placeholder="Search job number, job name, customer, PM, supervisor",
    )

    filtered = df.copy()

    if selected_customer != "All":
        filtered = filtered[filtered["customer_name"].astype(str) == selected_customer]

    if selected_status != "All":
        filtered = filtered[filtered["status"].astype(str) == selected_status]

    if search.strip():
        s = search.strip().lower()
        mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
        filtered = filtered[mask.any(axis=1)]

    currency_cols = [
        "awarded_amount",
        "estimated_total",
        "estimated_labor",
        "estimated_equipment",
        "estimated_materials",
        "estimated_travel",
        "actual_labor",
        "actual_equipment",
        "actual_materials",
        "actual_travel",
        "actual_other",
        "actual_total_cost",
        "gross_profit",
    ]
    for col in currency_cols:
        if col in filtered.columns:
            filtered[col] = filtered[col].map(lambda x: f"${float(x or 0):,.2f}")

    if "gross_margin_pct" in filtered.columns:
        filtered["gross_margin_pct"] = filtered["gross_margin_pct"].map(lambda x: f"{float(x or 0):.1f}%")

    st.dataframe(filtered, use_container_width=True, hide_index=True)

    detail_df = pd.DataFrame(labor_detail_rows)
    if not detail_df.empty:
        st.subheader("Labor by employee (approved time entries)")
        st.caption(
            "Per-line cost: **Time entry (legacy)** — labor_cost, else employee rates, else labor classification. "
            "**Weekly grid** — hours × employee hourly rate from **time_entries**."
        )
        d2 = detail_df.copy()
        if selected_customer != "All":
            d2 = d2[d2["customer_name"].astype(str) == selected_customer]
        if selected_status != "All":
            d2 = d2[d2["job_status"].astype(str) == selected_status]
        if search.strip():
            s = search.strip().lower()
            mask = d2.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
            d2 = d2[mask.any(axis=1)]
        show_d = d2.copy()
        if "labor_cost" in show_d.columns:
            show_d["labor_cost"] = show_d["labor_cost"].map(lambda x: f"${float(x or 0):,.2f}")
        st.dataframe(show_d, use_container_width=True, hide_index=True)

        if all(c in d2.columns for c in ("straight_time_hours", "overtime_hours", "labor_cost")):
            agg = (
                d2.groupby(["job_number", "job_name", "employee"], as_index=False)[
                    ["straight_time_hours", "overtime_hours", "labor_cost"]
                ]
                .sum()
                .sort_values(["job_number", "employee"])
            )
            st.subheader("Labor totals by employee (same filters)")
            show_a = agg.copy()
            show_a["labor_cost"] = show_a["labor_cost"].map(lambda x: f"${float(x or 0):,.2f}")
            st.dataframe(show_a, use_container_width=True, hide_index=True)