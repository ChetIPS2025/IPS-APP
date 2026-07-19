"""Inventory transactions tab — paginated history and lazy Use on Job form."""

from __future__ import annotations

import html

import streamlit as st

from app.perf_debug import perf_span
from app.services.inventory_service import generate_inventory_qr_value, get_inventory_transactions_page
from app.utils.formatting import fmt_date
from app.utils.inventory_quantity import format_inventory_quantity, inventory_qty_input_kwargs, read_inventory_quantity
from app.utils.phone_helpers import format_phone_display

_DEFAULT_INVENTORY_TRANSACTION_PAGE_SIZE = 25
_ISSUE_FORM_KEY_PREFIX = "ips_inventory_issue_job_"
_TXN_PAGE_KEY_PREFIX = "ips_inventory_txn_page_"


def _issue_form_session_key(item_id: str) -> str:
    return f"{_ISSUE_FORM_KEY_PREFIX}{str(item_id or '').strip() or 'item'}"


def _txn_page_session_key(item_id: str) -> str:
    return f"{_TXN_PAGE_KEY_PREFIX}{str(item_id or '').strip() or 'item'}"


def _txn_action_label(txn_type: str) -> str:
    from app.services.inventory_service import inventory_action_label

    return inventory_action_label(txn_type)


def render_inventory_issue_to_job_form(item: dict, *, permissions_user_id: str | None) -> None:
    """Lazy Use on Job — opens only after explicit user action."""
    iid = str(item.get("id") or "").strip()
    if not iid:
        return
    form_key = _issue_form_session_key(iid)
    if not st.session_state.get(form_key):
        if st.button("Open Form", key=f"inv_issue_open_{iid}", use_container_width=False):
            st.session_state[form_key] = True
            st.rerun()
        return

    from app.services.job_materials_service import issue_inventory_to_job
    from app.services.job_service import list_assignable_job_options

    st.markdown("**Use on Job**")
    job_options = list_assignable_job_options(limit=100)
    job_labels = ["— Select job —", *[opt["label"] for opt in job_options]]
    job_map = {opt["label"]: opt["id"] for opt in job_options}

    with st.form(f"inv_issue_job_{iid}", clear_on_submit=True):
        job_pick = st.selectbox("Job", job_labels, key=f"inv_issue_job_pick_{iid}")
        qty_kwargs = inventory_qty_input_kwargs(min_value=1, value=1)
        qty = st.number_input("Quantity", key=f"inv_issue_qty_{iid}", **qty_kwargs)
        submitted = st.form_submit_button("Issue to job", type="primary")
        cancelled = st.form_submit_button("Cancel")
    if cancelled:
        st.session_state.pop(form_key, None)
        st.rerun()
    if submitted:
        jid = job_map.get(job_pick, "")
        if not jid:
            st.error("Select a job.")
            return
        result = issue_inventory_to_job(
            inventory_item_id=iid,
            job_id=jid,
            quantity=qty,
            scanned_by_user_id=permissions_user_id,
        )
        if not result.ok:
            st.error(result.error or "Could not issue inventory to job.")
            return
        from app.services.inventory_directory_service import invalidate_inventory_directory_cache

        invalidate_inventory_directory_cache()
        st.session_state.pop(form_key, None)
        st.success("Inventory issued to job.")
        st.rerun()


def render_inventory_transactions_panel(item: dict, *, permissions_user_id: str | None) -> None:
    iid = str(item.get("id") or "").strip()
    st.markdown("**Use on Job**")
    render_inventory_issue_to_job_form(item, permissions_user_id=permissions_user_id)
    st.divider()

    page_key = _txn_page_session_key(iid)
    page = max(1, int(st.session_state.get(page_key, 1) or 1))
    page_size = _DEFAULT_INVENTORY_TRANSACTION_PAGE_SIZE

    with perf_span("inventory.detail.transactions"):
        txns, total = get_inventory_transactions_page(
            inventory_id=iid,
            page=page,
            page_size=page_size,
        )

    on_hand = read_inventory_quantity(item, "qty_on_hand", "quantity_on_hand", "quantity")
    allocated = read_inventory_quantity(item, "quantity_allocated")
    last_scan = fmt_date(txns[0].get("created_at")) if txns else "—"

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        st.metric("On Hand", format_inventory_quantity(on_hand, str(item.get("unit") or "")))
    with c2:
        st.metric("Allocated", format_inventory_quantity(allocated, str(item.get("unit") or "")))
    with c3:
        st.metric("Last use", last_scan)

    scan_url = generate_inventory_qr_value(item)
    if scan_url:
        st.link_button("Open Use Form", scan_url, use_container_width=True)

    if not txns:
        st.caption("No scan transactions yet.")
        return

    total_pages = max(1, (total + page_size - 1) // page_size)
    st.caption(f"Showing page {page} of {total_pages} ({total} transaction(s))")
    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if page > 1 and st.button("Previous", key=f"inv_txn_prev_{iid}"):
            st.session_state[page_key] = page - 1
            st.rerun()
    with nav3:
        if page < total_pages and st.button("Next", key=f"inv_txn_next_{iid}"):
            st.session_state[page_key] = page + 1
            st.rerun()

    head = (
        '<div class="ips-inventory-txn-head">'
        '<span>Date</span><span>Action</span><span>Qty</span><span>Job</span>'
        '<span>Scanned By</span><span>Phone</span><span>Notes</span>'
        "</div>"
    )
    rows_html = ""
    for row in txns:
        rows_html += (
            '<div class="ips-inventory-txn-row">'
            f'<span>{html.escape(fmt_date(row.get("created_at")))}</span>'
            f'<span>{html.escape(_txn_action_label(row.get("transaction_type")))}</span>'
            f'<span>{html.escape(format_inventory_quantity(row.get("quantity_display")))}</span>'
            f'<span>{html.escape(str(row.get("job_label") or "—"))}</span>'
            f'<span>{html.escape(str(row.get("scanned_by_name") or "—"))}</span>'
            f'<span>{html.escape(format_phone_display(str(row.get("scanned_by_phone") or "")))}</span>'
            f'<span>{html.escape(str(row.get("notes") or ""))}</span>'
            "</div>"
        )
    st.markdown(f'<div class="ips-inventory-txn-table">{head}{rows_html}</div>', unsafe_allow_html=True)
