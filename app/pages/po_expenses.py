from __future__ import annotations

import pandas as pd
import streamlit as st

from auth import current_profile, current_role
try:
    from app.ui.page_shell import render_page_header
except ImportError:
    from ui.page_shell import render_page_header  # type: ignore
from db import delete_rows_admin, fetch_one, fetch_table, insert_row, update_rows

try:
    from table_actions import (
        IPS_PENDING_DELETE,
        TABLE_KEY_PO_EXPENSES,
        clear_selected_ids,
        render_selectable_dataframe,
        render_selection_action_bar,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_PO_EXPENSES,
        clear_selected_ids,
        render_selectable_dataframe,
        render_selection_action_bar,
    )

try:
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore

EXPENSE_CATEGORIES = [
    "Materials",
    "Travel",
    "Equipment Rental",
    "Subcontractor",
    "Fuel",
    "Lodging",
    "Meals",
    "Freight",
    "Permits",
    "Miscellaneous",
]

EXPENSE_STATUSES = [
    "Open",
    "Approved",
    "Paid",
    "Rejected",
]


def _safe_date_value(value):
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def render() -> None:
    render_page_header("PO / Expenses", "Expenses and PO lines tied to jobs.")

    can_add = current_role() in {"admin", "pm"}
    can_approve = current_role() == "admin"

    customers = fetch_table("customers", limit=5000, order_by="customer_name")
    jobs = sort_jobs_by_number_then_name(fetch_table("jobs", limit=5000, order_by="job_number"))
    expenses = fetch_table("job_expenses", limit=10000, order_by="expense_date")

    customer_name_by_id = {c.get("id"): c.get("customer_name", "") for c in customers}
    job_label_by_id = {j.get("id"): job_row_select_label(j) for j in jobs}

    vid = st.session_state.get("po_expense_view_id")
    if vid:
        vr = fetch_one("job_expenses", {"id": vid})
        if not vr:
            st.session_state.pop("po_expense_view_id", None)
        else:
            st.subheader("Expense detail")
            st.caption("Read-only. Use **Edit Expense** in the table to change this row in the form below.")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Date:** {vr.get('expense_date') or '—'}")
                st.markdown(f"**Customer:** {customer_name_by_id.get(vr.get('customer_id')) or '—'}")
                st.markdown(f"**Job:** {job_label_by_id.get(vr.get('job_id')) or '—'}")
                st.markdown(f"**Category:** {vr.get('category') or '—'}")
                st.markdown(f"**Vendor:** {vr.get('vendor') or '—'}")
            with c2:
                st.markdown(f"**Amount:** ${float(vr.get('amount') or 0):,.2f}")
                st.markdown(f"**Status:** {vr.get('status') or '—'}")
                st.markdown(f"**PO #:** {vr.get('po_number') or '—'}")
                st.markdown(f"**Invoice #:** {vr.get('invoice_number') or '—'}")
            st.markdown(f"**Description:** {vr.get('description') or '—'}")
            st.markdown(f"**Notes:** {vr.get('notes') or '—'}")
            if st.button("← Back to overview", use_container_width=True, key="po_exp_view_back"):
                st.session_state.pop("po_expense_view_id", None)
                st.rerun()
            st.divider()

    st.subheader("Expense Overview")

    expense_df = pd.DataFrame(expenses)

    if expense_df.empty:
        st.info("No expenses found.")
    else:
        expense_df["customer_name"] = expense_df["customer_id"].map(customer_name_by_id)
        expense_df["job"] = expense_df["job_id"].map(job_label_by_id)

        f1, f2, f3, f4 = st.columns([1, 1, 1, 2])

        customer_names = sorted(
            [c.get("customer_name", "") for c in customers if str(c.get("customer_name", "")).strip()]
        )
        selected_customer = f1.selectbox("Filter Customer", ["All"] + customer_names)

        selected_category = f2.selectbox("Filter Category", ["All"] + EXPENSE_CATEGORIES)

        selected_status = f3.selectbox("Filter Status", ["All"] + EXPENSE_STATUSES)

        search = f4.text_input(
            "Search Expenses",
            placeholder="Search vendor, PO, invoice, description, customer, job",
        )

        filtered = expense_df.copy()

        if selected_customer != "All":
            filtered = filtered[filtered["customer_name"].astype(str) == selected_customer]

        if selected_category != "All":
            filtered = filtered[filtered["category"].astype(str) == selected_category]

        if selected_status != "All":
            filtered = filtered[filtered["status"].astype(str) == selected_status]

        if search.strip():
            s = search.strip().lower()
            mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
            filtered = filtered[mask.any(axis=1)]

        table_df = filtered.copy()
        display_df = filtered.copy()
        if "amount" in display_df.columns:
            display_df["amount"] = display_df["amount"].map(lambda x: f"${float(x or 0):,.2f}")

        show_cols = [
            c
            for c in [
                "expense_date",
                "customer_name",
                "job",
                "category",
                "vendor",
                "po_number",
                "invoice_number",
                "description",
                "amount",
                "status",
                "notes",
            ]
            if c in display_df.columns
        ]

        if filtered.empty:
            st.warning("No expenses match your filters.")
        else:
            st.caption(
                "Action bar above the grid. Checkbox on the **left**; selection: **selected_po_expenses_ids**."
            )
            if "id" not in table_df.columns:
                st.dataframe(display_df[show_cols], use_container_width=True, hide_index=True)
            else:
                bar_placeholder = st.empty()
                _, sel = render_selectable_dataframe(
                    display_df,
                    table_key=TABLE_KEY_PO_EXPENSES,
                    id_column="id",
                    columns=show_cols,
                    editor_key="po_exp_sel_editor",
                )
                with bar_placeholder.container():
                    actions = render_selection_action_bar(
                        TABLE_KEY_PO_EXPENSES,
                        sel,
                        can_view=True,
                        can_edit=can_add,
                        can_delete=can_add,
                        export_df=table_df,
                        visible_df=table_df,
                        id_column="id",
                        export_filename="job_expenses_export.csv",
                        view_label="View Expense",
                        edit_label="Edit Expense",
                        delete_label="Delete Expense",
                        delete_selected_label="Delete Selected",
                    )
                if actions.get("view") and sel and len(sel) == 1:
                    st.session_state["po_expense_view_id"] = str(sel[0])
                    st.rerun()
                if actions.get("edit") and sel and len(sel) == 1 and can_add:
                    st.session_state["po_expense_edit_focus_id"] = str(sel[0])
                    st.session_state["po_mode"] = "Edit Existing Expense"
                    st.session_state.pop("po_expense_view_id", None)
                    st.rerun()
                pend = st.session_state.get(IPS_PENDING_DELETE) or {}
                if actions.get("confirm_delete") and pend.get(TABLE_KEY_PO_EXPENSES) and can_add:
                    for xid in pend[TABLE_KEY_PO_EXPENSES]:
                        try:
                            delete_rows_admin("job_expenses", {"id": xid})
                        except Exception as exc:
                            st.error(f"Could not delete {xid}: {exc}")
                    pend.pop(TABLE_KEY_PO_EXPENSES, None)
                    clear_selected_ids(TABLE_KEY_PO_EXPENSES)
                    st.success("Delete completed where permitted.")
                    st.rerun()

    st.markdown("---")
    st.subheader("Create / Update Expense")

    existing_labels = [
        f"{e.get('expense_date', '')} | {e.get('vendor', '')} | {job_label_by_id.get(e.get('job_id'), '')} | ${float(e.get('amount', 0) or 0):,.2f}"
        for e in expenses
    ]

    exp_pick_idx = 0
    focus_exp = st.session_state.pop("po_expense_edit_focus_id", None)
    if focus_exp and expenses:
        for i, e in enumerate(expenses):
            if str(e.get("id")) == str(focus_exp):
                exp_pick_idx = i
                break

    selected_mode = st.radio(
        "Mode",
        ["Add New Expense", "Edit Existing Expense"],
        horizontal=True,
        key="po_mode",
    )

    selected_expense = None
    if selected_mode == "Edit Existing Expense" and expenses:
        pick_idx = min(exp_pick_idx, len(existing_labels) - 1) if existing_labels else 0
        selected_label = st.selectbox(
            "Select Expense",
            existing_labels,
            index=pick_idx,
            key="po_exp_pick",
        )
        selected_expense = next(
            e for e in expenses
            if f"{e.get('expense_date', '')} | {e.get('vendor', '')} | {job_label_by_id.get(e.get('job_id'), '')} | ${float(e.get('amount', 0) or 0):,.2f}" == selected_label
        )

    def current_value(field_name, default=""):
        if selected_expense:
            value = selected_expense.get(field_name, default)
            return "" if value is None else value
        return default

    customer_options = {c.get("customer_name", ""): c.get("id") for c in customers if str(c.get("customer_name", "")).strip()}

    selected_customer_name_default = ""
    if selected_expense and selected_expense.get("customer_id") in customer_name_by_id:
        selected_customer_name_default = customer_name_by_id[selected_expense.get("customer_id")]

    c1, c2, c3 = st.columns(3)
    expense_date = c1.text_input("Expense Date (YYYY-MM-DD)", value=str(current_value("expense_date")), disabled=not can_add)
    selected_customer_name = c2.selectbox(
        "Customer",
        [""] + sorted(customer_options.keys()),
        index=([""] + sorted(customer_options.keys())).index(selected_customer_name_default)
        if selected_customer_name_default in ([""] + sorted(customer_options.keys()))
        else 0,
        disabled=not can_add,
    )

    matching_jobs = [
        j for j in jobs
        if not selected_customer_name or j.get("customer_id") == customer_options.get(selected_customer_name)
    ]
    job_options = {
        job_row_select_label(j): j.get("id")
        for j in matching_jobs
        if job_row_select_label(j) and job_row_select_label(j) != "—"
    }

    selected_job_label_default = ""
    if selected_expense and selected_expense.get("job_id") in job_label_by_id:
        selected_job_label_default = job_label_by_id[selected_expense.get("job_id")]

    selected_job_label = c3.selectbox(
        "Job",
        [""] + sorted(job_options.keys()),
        index=([""] + sorted(job_options.keys())).index(selected_job_label_default)
        if selected_job_label_default in ([""] + sorted(job_options.keys()))
        else 0,
        disabled=not can_add,
    )

    c4, c5, c6 = st.columns(3)
    category_default = current_value("category", EXPENSE_CATEGORIES[0]) or EXPENSE_CATEGORIES[0]
    if category_default not in EXPENSE_CATEGORIES:
        category_default = EXPENSE_CATEGORIES[0]

    category = c4.selectbox(
        "Category",
        EXPENSE_CATEGORIES,
        index=EXPENSE_CATEGORIES.index(category_default),
        disabled=not can_add,
    )
    vendor = c5.text_input("Vendor", value=current_value("vendor"), disabled=not can_add)
    amount = c6.number_input(
        "Amount",
        min_value=0.0,
        value=float(current_value("amount", 0) or 0),
        step=1.0,
        format="%.2f",
        disabled=not can_add,
    )

    c7, c8, c9 = st.columns(3, gap="small")
    po_number = c7.text_input("PO Number", value=current_value("po_number"), disabled=not can_add)
    invoice_number = c8.text_input("Invoice Number", value=current_value("invoice_number"), disabled=not can_add)

    status_default = current_value("status", "Open") or "Open"
    if status_default not in EXPENSE_STATUSES:
        status_default = "Open"

    if can_approve:
        expense_status = c9.selectbox(
            "Status",
            EXPENSE_STATUSES,
            index=EXPENSE_STATUSES.index(status_default),
            disabled=not can_add,
        )
    else:
        expense_status = status_default
        c9.text_input("Status", value=expense_status, disabled=True)

    d1, d2 = st.columns(2, gap="small")
    with d1:
        description = st.text_area(
            "Description",
            value=current_value("description"),
            disabled=not can_add,
            height=88,
        )
    with d2:
        notes = st.text_area(
            "Notes",
            value=current_value("notes"),
            disabled=not can_add,
            height=88,
        )

    if not can_add:
        st.info("Only admin or estimator users can add or update expenses.")
        return

    if selected_mode == "Add New Expense":
        if st.button("Add Expense", use_container_width=True):
            if not expense_date.strip():
                st.error("Expense Date required")
                st.stop()

            if not category.strip():
                st.error("Category required")
                st.stop()

            payload = {
                "expense_date": _safe_date_value(expense_date.strip()),
                "customer_id": customer_options.get(selected_customer_name),
                "job_id": job_options.get(selected_job_label),
                "category": category.strip(),
                "vendor": vendor.strip(),
                "po_number": po_number.strip(),
                "invoice_number": invoice_number.strip(),
                "description": description.strip(),
                "amount": float(amount or 0),
                "status": expense_status if can_approve else "Open",
                "notes": notes.strip(),
                "entered_by": current_profile().get("id"),
            }

            row = insert_row("job_expenses", payload)
            try:
                from app.services.job_cost_transaction_service import _safe_sync, sync_job_expense
            except ImportError:
                from services.job_cost_transaction_service import _safe_sync, sync_job_expense  # type: ignore
            if isinstance(row, dict):
                _safe_sync(sync_job_expense, row)
            st.success("Expense added.")
            st.rerun()

    else:
        if st.button("Update Expense", use_container_width=True):
            if not selected_expense:
                st.error("Select an expense first.")
                st.stop()

            if not expense_date.strip():
                st.error("Expense Date required")
                st.stop()

            payload = {
                "expense_date": _safe_date_value(expense_date.strip()),
                "customer_id": customer_options.get(selected_customer_name),
                "job_id": job_options.get(selected_job_label),
                "category": category.strip(),
                "vendor": vendor.strip(),
                "po_number": po_number.strip(),
                "invoice_number": invoice_number.strip(),
                "description": description.strip(),
                "amount": float(amount or 0),
                "status": expense_status if can_approve else selected_expense.get("status", "Open"),
                "notes": notes.strip(),
            }

            update_rows("job_expenses", payload, {"id": selected_expense["id"]})
            try:
                from app.services.job_cost_transaction_service import _safe_sync, sync_job_expense
            except ImportError:
                from services.job_cost_transaction_service import _safe_sync, sync_job_expense  # type: ignore
            merged = {**selected_expense, **payload, "id": selected_expense["id"]}
            _safe_sync(sync_job_expense, merged)
            st.success("Expense updated.")
            st.rerun()