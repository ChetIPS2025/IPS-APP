"""Job Costing tab for Job Details — ledger-backed metrics and transaction history."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

try:
    from app.components.job_cost_summary_cards import (
        render_job_cost_detail_metrics,
        render_job_cost_summary_cards,
    )
except ImportError:
    from components.job_cost_summary_cards import (  # type: ignore
        render_job_cost_detail_metrics,
        render_job_cost_summary_cards,
    )

try:
    from app.services.job_cost_transaction_service import (
        build_job_cost_summary,
        fetch_job_cost_transactions,
        sync_all_sources_for_job,
        transaction_display_source,
        transaction_employee_name,
    )
except ImportError:
    from services.job_cost_transaction_service import (  # type: ignore
        build_job_cost_summary,
        fetch_job_cost_transactions,
        sync_all_sources_for_job,
        transaction_display_source,
        transaction_employee_name,
    )


def _load_employees() -> dict[str, dict[str, Any]]:
    try:
        from app.db import fetch_table
    except ImportError:
        from db import fetch_table  # type: ignore
    try:
        rows = fetch_table("employees", limit=5000, order_by="name") or []
    except Exception:
        rows = []
    return {str(e.get("id")): e for e in rows if e.get("id")}


def render_job_costing_tab(job: dict[str, Any], *, key_prefix: str = "job_cost") -> None:
    """Full Job Costing panel inside Job Details."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        st.warning("Save this job before viewing costing.")
        return

    st.markdown(
        '<span class="ips-job-costing-tab-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    sync_all_sources_for_job(jid)
    summary = build_job_cost_summary(job)
    render_job_cost_summary_cards(summary)
    st.divider()
    render_job_cost_detail_metrics(summary)

    st.subheader("Transaction history")
    txns = fetch_job_cost_transactions(jid)
    employees_by_id = _load_employees()
    if not txns:
        st.info(
            "No cost transactions yet. Labor, inventory scans, equipment assignments, "
            "and approved PO/expenses post here automatically."
        )
        return

    rows: list[dict[str, Any]] = []
    for t in txns:
        rows.append(
            {
                "Date": str(t.get("transaction_date") or "")[:10],
                "Source": transaction_display_source(t),
                "Employee": transaction_employee_name(t, employees_by_id),
                "Item": str(t.get("item_name") or "—"),
                "Quantity": float(t.get("quantity") or 0),
                "Cost": float(t.get("total_cost") or 0),
                "Job Number": str(t.get("job_number") or job.get("job_number") or "—"),
            }
        )
    df = pd.DataFrame(rows)
    if "Cost" in df.columns:
        display = df.copy()
        display["Cost"] = display["Cost"].map(lambda x: f"${float(x or 0):,.2f}")
        st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(
        f"{len(txns)} transaction(s) · Values refresh automatically when labor, inventory, "
        "equipment, or purchasing records change."
    )
