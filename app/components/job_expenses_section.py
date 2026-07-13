"""PO / expense entry panel for Job Costing."""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from app.services.job_expense_service import (
    EXPENSE_CATEGORIES,
    EXPENSE_STATUSES,
    delete_job_expense,
    list_job_expenses,
    save_job_expense,
)
def _current_user_id() -> str | None:
    from app.auth import current_profile
    pid = str(current_profile().get("id") or "").strip()
    return pid or None


def _money(value: float) -> str:
    return f"${float(value or 0):,.2f}"


def render_job_expenses_section(job: dict[str, Any], *, key_prefix: str) -> None:
    """Add / list PO and expense lines that post to job costing when approved."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        return

    st.subheader("PO / expenses")
    st.caption(
        "Approved expenses post to running cost automatically. "
        "Open expenses are tracked but not counted until approved."
    )

    with st.expander("Add PO / expense", expanded=False):
        with st.form(f"{key_prefix}_expense_form"):
            c1, c2 = st.columns(2)
            with c1:
                expense_date = st.date_input("Date", value=date.today(), key=f"{key_prefix}_exp_date")
                category = st.selectbox("Category", EXPENSE_CATEGORIES, key=f"{key_prefix}_exp_cat")
                vendor = st.text_input("Vendor", key=f"{key_prefix}_exp_vendor")
                po_number = st.text_input("PO #", key=f"{key_prefix}_exp_po")
            with c2:
                amount = st.number_input(
                    "Amount ($)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"{key_prefix}_exp_amt",
                )
                status = st.selectbox("Status", EXPENSE_STATUSES, index=1, key=f"{key_prefix}_exp_status")
                invoice_number = st.text_input("Invoice #", key=f"{key_prefix}_exp_inv")
                description = st.text_input("Description", key=f"{key_prefix}_exp_desc")
            notes = st.text_area("Notes", height=68, key=f"{key_prefix}_exp_notes")
            if st.form_submit_button("Save expense", type="primary"):
                ok, msg = save_job_expense(
                    jid,
                    {
                        "expense_date": expense_date,
                        "category": category,
                        "vendor": vendor,
                        "po_number": po_number,
                        "invoice_number": invoice_number,
                        "description": description,
                        "amount": amount,
                        "status": status,
                        "notes": notes,
                    },
                    entered_by=_current_user_id(),
                )
                if ok:
                    from app.services.job_cost_transaction_service import invalidate_job_cost_session
                    invalidate_job_cost_session(jid)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    rows = list_job_expenses(jid)
    if not rows:
        st.info("No PO or expense lines yet.")
        return

    for row in rows:
        xid = str(row.get("id") or "")
        label = str(row.get("description") or row.get("vendor") or row.get("category") or "Expense")
        status = str(row.get("status") or "Open")
        amt = float(row.get("amount") or 0)
        with st.expander(f"{label[:48]} — {_money(amt)} ({status})", expanded=False):
            with st.form(f"{key_prefix}_edit_exp_{xid}"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    ed = st.date_input(
                        "Date",
                        value=date.fromisoformat(str(row.get("expense_date") or date.today())[:10]),
                        key=f"{key_prefix}_ed_date_{xid}",
                    )
                    cat = st.selectbox(
                        "Category",
                        EXPENSE_CATEGORIES,
                        index=EXPENSE_CATEGORIES.index(str(row.get("category") or "Other"))
                        if str(row.get("category") or "Other") in EXPENSE_CATEGORIES
                        else len(EXPENSE_CATEGORIES) - 1,
                        key=f"{key_prefix}_ed_cat_{xid}",
                    )
                    vend = st.text_input("Vendor", value=str(row.get("vendor") or ""), key=f"{key_prefix}_ed_vend_{xid}")
                    po = st.text_input("PO #", value=str(row.get("po_number") or ""), key=f"{key_prefix}_ed_po_{xid}")
                with ec2:
                    eamt = st.number_input(
                        "Amount ($)",
                        min_value=0.0,
                        value=float(row.get("amount") or 0),
                        step=0.01,
                        format="%.2f",
                        key=f"{key_prefix}_ed_amt_{xid}",
                    )
                    estatus = st.selectbox(
                        "Status",
                        EXPENSE_STATUSES,
                        index=EXPENSE_STATUSES.index(status) if status in EXPENSE_STATUSES else 1,
                        key=f"{key_prefix}_ed_status_{xid}",
                    )
                    inv = st.text_input(
                        "Invoice #",
                        value=str(row.get("invoice_number") or ""),
                        key=f"{key_prefix}_ed_inv_{xid}",
                    )
                    desc = st.text_input(
                        "Description",
                        value=str(row.get("description") or ""),
                        key=f"{key_prefix}_ed_desc_{xid}",
                    )
                enotes = st.text_area(
                    "Notes",
                    value=str(row.get("notes") or ""),
                    height=68,
                    key=f"{key_prefix}_ed_notes_{xid}",
                )
                save_btn, delete_btn = st.columns(2)
                with save_btn:
                    saved = st.form_submit_button("Save changes", type="primary")
                with delete_btn:
                    deleted = st.form_submit_button("Delete")
                if saved:
                    ok, msg = save_job_expense(
                        jid,
                        {
                            "expense_date": ed,
                            "category": cat,
                            "vendor": vend,
                            "po_number": po,
                            "invoice_number": inv,
                            "description": desc,
                            "amount": eamt,
                            "status": estatus,
                            "notes": enotes,
                        },
                        row_id=xid,
                        entered_by=_current_user_id(),
                    )
                    if ok:
                        from app.services.job_cost_transaction_service import invalidate_job_cost_session
                        invalidate_job_cost_session(jid)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                if deleted:
                    ok, msg = delete_job_expense(xid)
                    if ok:
                        from app.services.job_cost_transaction_service import invalidate_job_cost_session
                        invalidate_job_cost_session(jid)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
