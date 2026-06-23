"""Job Costing tab for Job Details — ledger-backed metrics and transaction history."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

try:
    from app.components.job_cost_summary_cards import (
        render_job_cost_breakdown,
        render_job_cost_detail_metrics,
        render_job_cost_summary_cards,
    )
except ImportError:
    from components.job_cost_summary_cards import (  # type: ignore
        render_job_cost_breakdown,
        render_job_cost_detail_metrics,
        render_job_cost_summary_cards,
    )

try:
    from app.components.job_expenses_section import render_job_expenses_section
except ImportError:
    from components.job_expenses_section import render_job_expenses_section  # type: ignore

try:
    from app.services.job_cost_transaction_service import (
        COST_EQUIPMENT,
        COST_LABOR,
        COST_MATERIAL,
        COST_OTHER,
        COST_RENTAL,
        COST_SUBCONTRACT,
        SOURCE_MANUAL_ADJUSTMENT,
        build_job_cost_summary,
        cached_job_cost_summary,
        can_manage_manual_cost_adjustments,
        create_manual_cost_adjustment,
        delete_manual_cost_adjustment,
        fetch_job_cost_transactions,
        invalidate_job_cost_session,
        transaction_display_source,
        transaction_employee_name,
        update_manual_cost_adjustment,
    )
except ImportError:
    from services.job_cost_transaction_service import (  # type: ignore
        COST_EQUIPMENT,
        COST_LABOR,
        COST_MATERIAL,
        COST_OTHER,
        COST_RENTAL,
        COST_SUBCONTRACT,
        SOURCE_MANUAL_ADJUSTMENT,
        build_job_cost_summary,
        cached_job_cost_summary,
        can_manage_manual_cost_adjustments,
        create_manual_cost_adjustment,
        delete_manual_cost_adjustment,
        fetch_job_cost_transactions,
        invalidate_job_cost_session,
        transaction_display_source,
        transaction_employee_name,
        update_manual_cost_adjustment,
    )

_CATEGORY_OPTIONS = [
    COST_LABOR,
    COST_MATERIAL,
    COST_EQUIPMENT,
    COST_RENTAL,
    COST_SUBCONTRACT,
    COST_OTHER,
]
_SOURCE_FILTER_OPTIONS = [
    "All",
    "Labor time",
    "Timekeeping",
    "Material",
    "Equipment",
    "Purchase / expense",
    "Equipment assignment",
    "Manual adjustment",
]


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


def _current_user_id() -> str | None:
    try:
        from app.auth import current_profile
    except ImportError:
        from auth import current_profile  # type: ignore
    pid = str(current_profile().get("id") or "").strip()
    return pid or None


def _filter_transactions(
    txns: list[dict[str, Any]],
    *,
    category: str,
    source_label: str,
    date_from: date | None,
    date_to: date | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in txns:
        cat = str(t.get("cost_category") or "").strip().lower()
        if category != "All" and cat != category.lower():
            continue
        src = transaction_display_source(t)
        if source_label != "All" and src != source_label:
            continue
        txn_date = str(t.get("transaction_date") or "")[:10]
        if date_from and txn_date and txn_date < date_from.isoformat():
            continue
        if date_to and txn_date and txn_date > date_to.isoformat():
            continue
        out.append(t)
    return out


def _render_manual_adjustment_form(job: dict[str, Any], *, key_prefix: str) -> None:
    if not can_manage_manual_cost_adjustments():
        return
    jid = str(job.get("id") or "").strip()
    with st.expander("Add manual cost adjustment (admin)", expanded=False):
        with st.form(f"{key_prefix}_manual_adj_form"):
            c1, c2 = st.columns(2)
            with c1:
                adj_date = st.date_input("Date", value=date.today(), key=f"{key_prefix}_adj_date")
                category = st.selectbox(
                    "Category",
                    _CATEGORY_OPTIONS,
                    key=f"{key_prefix}_adj_cat",
                )
                description = st.text_input("Description", key=f"{key_prefix}_adj_desc")
            with c2:
                quantity = st.number_input("Quantity", min_value=0.0, value=1.0, step=0.25, key=f"{key_prefix}_adj_qty")
                unit_cost = st.number_input(
                    "Unit cost ($)",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"{key_prefix}_adj_unit",
                )
                notes = st.text_area("Notes", height=68, key=f"{key_prefix}_adj_notes")
            total_preview = round(float(quantity or 0) * float(unit_cost or 0), 2)
            st.caption(f"Total cost: ${total_preview:,.2f}")
            if st.form_submit_button("Save adjustment", type="primary"):
                ok = create_manual_cost_adjustment(
                    job_id=jid,
                    transaction_date=adj_date.isoformat(),
                    cost_category=category,
                    description=description.strip() or "Manual adjustment",
                    quantity=float(quantity or 0),
                    unit_cost=float(unit_cost or 0),
                    notes=notes.strip(),
                    created_by=_current_user_id(),
                )
                if ok:
                    invalidate_job_cost_session(jid)
                    st.success("Manual adjustment saved.")
                    st.rerun()
                else:
                    st.error("Could not save adjustment. Check quantity and unit cost.")


def _render_manual_adjustment_editor(
    txns: list[dict[str, Any]],
    *,
    key_prefix: str,
) -> None:
    if not can_manage_manual_cost_adjustments():
        return
    manual = [t for t in txns if str(t.get("source_type") or "") == SOURCE_MANUAL_ADJUSTMENT]
    if not manual:
        return
    with st.expander("Edit / delete manual adjustments (admin)", expanded=False):
        for t in manual:
            tid = str(t.get("id") or "")
            label = str(t.get("description") or t.get("item_name") or tid)[:60]
            with st.form(f"{key_prefix}_edit_manual_{tid}"):
                st.markdown(f"**{label}**")
                ec1, ec2 = st.columns(2)
                with ec1:
                    txn_date = st.date_input(
                        "Date",
                        value=date.fromisoformat(str(t.get("transaction_date") or date.today())[:10]),
                        key=f"{key_prefix}_ed_date_{tid}",
                    )
                    category = st.selectbox(
                        "Category",
                        _CATEGORY_OPTIONS,
                        index=_CATEGORY_OPTIONS.index(str(t.get("cost_category") or COST_OTHER))
                        if str(t.get("cost_category") or "") in _CATEGORY_OPTIONS
                        else len(_CATEGORY_OPTIONS) - 1,
                        key=f"{key_prefix}_ed_cat_{tid}",
                    )
                    description = st.text_input(
                        "Description",
                        value=str(t.get("description") or t.get("item_name") or ""),
                        key=f"{key_prefix}_ed_desc_{tid}",
                    )
                with ec2:
                    quantity = st.number_input(
                        "Quantity",
                        min_value=0.0,
                        value=float(t.get("quantity") or 0),
                        step=0.25,
                        key=f"{key_prefix}_ed_qty_{tid}",
                    )
                    unit_cost = st.number_input(
                        "Unit cost ($)",
                        min_value=0.0,
                        value=float(t.get("unit_cost") or 0),
                        step=0.01,
                        format="%.2f",
                        key=f"{key_prefix}_ed_unit_{tid}",
                    )
                    notes = st.text_area(
                        "Notes",
                        value=str(t.get("notes") or ""),
                        height=68,
                        key=f"{key_prefix}_ed_notes_{tid}",
                    )
                bc1, bc2 = st.columns(2)
                with bc1:
                    save = st.form_submit_button("Update", type="primary")
                with bc2:
                    delete = st.form_submit_button("Delete", type="secondary")
                if save:
                    ok = update_manual_cost_adjustment(
                        tid,
                        {
                            "transaction_date": txn_date.isoformat(),
                            "cost_category": category,
                            "description": description.strip(),
                            "quantity": float(quantity or 0),
                            "unit_cost": float(unit_cost or 0),
                            "notes": notes.strip(),
                        },
                    )
                    if ok:
                        invalidate_job_cost_session(str(t.get("job_id") or ""))
                        st.success("Adjustment updated.")
                        st.rerun()
                    else:
                        st.error("Update failed.")
                if delete:
                    if delete_manual_cost_adjustment(tid):
                        invalidate_job_cost_session(str(t.get("job_id") or ""))
                        st.success("Adjustment deleted.")
                        st.rerun()
                    else:
                        st.error("Delete failed.")


def render_job_costing_tab(
    job: dict[str, Any],
    *,
    key_prefix: str = "job_cost",
    cost_summary: dict[str, Any] | None = None,
) -> None:
    """Full Job Costing panel inside Job Details."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        st.warning("Save this job before viewing costing.")
        return

    st.markdown(
        '<span class="ips-job-costing-tab-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    refresh = st.button("Refresh costs", key=f"{key_prefix}_refresh", type="secondary")
    summary = cached_job_cost_summary(job, force_refresh=refresh)
    if isinstance(cost_summary, dict) and cost_summary and not refresh:
        summary = cost_summary
    render_job_cost_summary_cards(summary)
    st.divider()
    render_job_cost_detail_metrics(summary)
    render_job_cost_breakdown(summary)

    render_job_expenses_section(job, key_prefix=key_prefix)
    st.divider()

    _render_manual_adjustment_form(job, key_prefix=key_prefix)

    st.subheader("Transaction history")
    txns = fetch_job_cost_transactions(jid)
    _render_manual_adjustment_editor(txns, key_prefix=key_prefix)

    if not txns:
        st.info(
            "No cost transactions yet. Labor, inventory scans, equipment assignments, "
            "and approved PO/expenses post here automatically."
        )
        return

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        cat_filter = st.selectbox(
            "Category",
            ["All", *_CATEGORY_OPTIONS],
            key=f"{key_prefix}_filter_cat",
        )
    with fc2:
        src_filter = st.selectbox(
            "Source",
            _SOURCE_FILTER_OPTIONS,
            key=f"{key_prefix}_filter_src",
        )
    with fc3:
        date_from = st.date_input(
            "From",
            value=date(2000, 1, 1),
            key=f"{key_prefix}_filter_from",
        )
    with fc4:
        date_to = st.date_input(
            "To",
            value=date.today(),
            key=f"{key_prefix}_filter_to",
        )

    filtered = _filter_transactions(
        txns,
        category=cat_filter,
        source_label=src_filter,
        date_from=date_from,
        date_to=date_to,
    )

    employees_by_id = _load_employees()
    rows: list[dict[str, Any]] = []
    for t in filtered:
        rows.append(
            {
                "Date": str(t.get("transaction_date") or "")[:10],
                "Category": str(t.get("cost_category") or "—").title(),
                "Source": transaction_display_source(t),
                "Description": str(t.get("description") or t.get("item_name") or "—"),
                "Quantity": float(t.get("quantity") or 0),
                "Unit Cost": float(t.get("unit_cost") or 0),
                "Total Cost": float(t.get("total_cost") or 0),
                "Notes": str(t.get("notes") or "—"),
                "Employee": transaction_employee_name(t, employees_by_id),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty and "Unit Cost" in df.columns:
        display = df.copy()
        display["Unit Cost"] = display["Unit Cost"].map(lambda x: f"${float(x or 0):,.2f}")
        display["Total Cost"] = display["Total Cost"].map(lambda x: f"${float(x or 0):,.2f}")
        st.dataframe(display, use_container_width=True, hide_index=True)
    elif not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions match the selected filters.")

    st.caption(
        f"{len(filtered)} of {len(txns)} transaction(s) shown · Values refresh automatically when "
        "labor, inventory, equipment, or purchasing records change."
    )
