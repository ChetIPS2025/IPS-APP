"""Kit item inline detail and edit form."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.components.action_styles import danger_outline
from app.components.asset_kit.reference_options import get_kit_reference_options
from app.components.asset_kit.state import clear_kit_item_query_param, kit_item_row_label, sk
from app.components.asset_kit.styles import kit_item_status_pill_html
from app.services.asset_kits_service import (
    CONDITIONS,
    ITEM_STATUSES,
    ITEM_TYPES,
    delete_asset_kit_item,
    update_asset_kit_item,
)
from app.ui.streamlit_perf import fragment_rerun, ips_app_rerun
from app.utils.formatting import fmt_currency


def render_kit_item_detail_inline(
    asset: dict,
    aid: str,
    item: dict,
    *,
    items: list[dict[str, Any]],
) -> None:
    iid = str(item.get("id") or "")
    edit_key = sk(aid, f"edit_{iid}")
    editing = st.session_state.get(edit_key, False)

    st.markdown('<div class="ips-kit-detail-panel">', unsafe_allow_html=True)
    h1, h2, h3 = st.columns([2, 1, 1])
    with h1:
        st.markdown(f"**{html.escape(kit_item_row_label(item, items))}**")
    with h2:
        if not editing and st.button("Edit", key=f"kit_edit_btn_{aid}_{iid}"):
            st.session_state[edit_key] = True
            fragment_rerun()
    with h3:
        if st.button("Close", key=f"kit_close_{aid}_{iid}"):
            st.session_state[sk(aid, "sel")] = ""
            st.session_state[sk(aid, "view")] = "list"
            clear_kit_item_query_param()
            fragment_rerun()

    if editing:
        _render_kit_item_edit_form(asset, aid, item, items)
    else:
        st.markdown(
            f"Type: **{item.get('item_type')}** · Category: **{item.get('category') or '—'}**  \n"
            f"Expected: **{item.get('quantity_expected')}** · Actual: **{item.get('quantity_actual')}** · "
            f"Unit: **{item.get('unit')}**  \n"
            f"Value: **{fmt_currency(item.get('total_value'))}** "
            f"(unit {fmt_currency(item.get('unit_value'))})  \n"
            f"Condition: {kit_item_status_pill_html(str(item.get('condition') or ''))} · "
            f"Status: {kit_item_status_pill_html(str(item.get('status') or ''))}  \n"
            f"Serial: **{item.get('serial_number') or '—'}** · Assigned: **{item.get('assigned_to_name') or '—'}**",
            unsafe_allow_html=True,
        )
        if item.get("description"):
            st.caption(str(item.get("description")))
        if item.get("notes"):
            st.caption(f"Notes: {item.get('notes')}")
        if item.get("child_asset_id"):
            st.caption(f"Linked asset ID: {item.get('child_asset_id')}")
        if item.get("inventory_item_id"):
            st.caption(f"Linked inventory ID: {item.get('inventory_item_id')}")
        with danger_outline(f"kit_del_{aid}_{iid}"):
            if st.button("Delete item", key=f"kit_del_{aid}_{iid}"):
                result = delete_asset_kit_item(iid)
                if result.ok:
                    st.session_state[sk(aid, "sel")] = ""
                    clear_kit_item_query_param()
                    ips_app_rerun()
                else:
                    st.error(result.error or "Could not delete.")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_kit_item_edit_form(
    asset: dict,
    aid: str,
    item: dict,
    items: list[dict[str, Any]],
) -> None:
    iid = str(item.get("id") or "")
    edit_key = sk(aid, f"edit_{iid}")
    link_asset_key = sk(aid, f"link_asset_{iid}")
    link_inv_key = sk(aid, f"link_inv_{iid}")

    refs = get_kit_reference_options(include_employees=True, exclude_asset_id=aid)
    emp_opts = list(refs.employees)

    with st.form(f"kit_item_edit_{aid}_{iid}"):
        name = st.text_input("Item name", value=str(item.get("item_name") or ""))
        item_type = st.selectbox(
            "Type",
            ITEM_TYPES,
            index=ITEM_TYPES.index(str(item.get("item_type") or "Tool"))
            if str(item.get("item_type") or "Tool") in ITEM_TYPES
            else 0,
        )
        category = st.text_input("Category", value=str(item.get("category") or ""))
        c1, c2, c3 = st.columns(3)
        with c1:
            qty_exp = st.number_input(
                "Expected qty",
                min_value=0.0,
                value=float(item.get("quantity_expected") or 1),
                step=1.0,
            )
        with c2:
            qty_act = st.number_input(
                "Actual qty",
                min_value=0.0,
                value=float(item.get("quantity_actual") or 1),
                step=1.0,
            )
        with c3:
            unit_val = st.number_input(
                "Unit value",
                min_value=0.0,
                value=float(item.get("unit_value") or 0),
                step=1.0,
            )
        condition = st.selectbox(
            "Condition",
            CONDITIONS,
            index=CONDITIONS.index(str(item.get("condition") or "Good"))
            if str(item.get("condition") or "Good") in CONDITIONS
            else 1,
        )
        status = st.selectbox(
            "Status",
            ITEM_STATUSES,
            index=ITEM_STATUSES.index(str(item.get("status") or "Present"))
            if str(item.get("status") or "Present") in ITEM_STATUSES
            else 0,
        )
        serial = st.text_input("Serial number", value=str(item.get("serial_number") or ""))
        emp_labels = [x[0] for x in emp_opts]
        cur_assign = str(item.get("assigned_to_name") or "")
        assign_label = st.selectbox(
            "Assigned to",
            emp_labels,
            index=emp_labels.index(cur_assign) if cur_assign in emp_labels else 0,
        )

        change_asset = st.checkbox("Change linked asset", key=link_asset_key)
        change_inv = st.checkbox("Change linked inventory item", key=link_inv_key)
        link_asset = None
        link_inv = None
        if change_asset:
            asset_refs = get_kit_reference_options(include_assets=True, exclude_asset_id=aid)
            asset_labels = [x[0] for x in asset_refs.assets]
            cur_child = str(item.get("child_asset_id") or "")
            default_idx = 0
            for idx, (_, row) in enumerate(asset_refs.assets):
                if str(row.get("id") or "") == cur_child:
                    default_idx = idx
                    break
            link_asset = st.selectbox("Link asset", asset_labels, index=default_idx)
        if change_inv:
            inv_refs = get_kit_reference_options(include_inventory=True)
            inv_labels = [x[0] for x in inv_refs.inventory]
            cur_inv = str(item.get("inventory_item_id") or "")
            default_idx = 0
            for idx, (_, row) in enumerate(inv_refs.inventory):
                if str(row.get("id") or "") == cur_inv:
                    default_idx = idx
                    break
            link_inv = st.selectbox("Link inventory", inv_labels, index=default_idx)

        notes = st.text_area("Notes", value=str(item.get("notes") or ""), height=60)
        csave, ccancel = st.columns(2)
        save = csave.form_submit_button("Save", type="primary")
        cancel = ccancel.form_submit_button("Cancel")

    if cancel:
        st.session_state[edit_key] = False
        fragment_rerun()
    if save:
        emp = next((e for lbl, e in emp_opts if lbl == assign_label), {})
        payload: dict[str, Any] = {
            "item_name": name,
            "item_type": item_type,
            "category": category,
            "quantity_expected": qty_exp,
            "quantity_actual": qty_act,
            "unit_value": unit_val,
            "condition": condition,
            "status": status,
            "serial_number": serial,
            "assigned_to_name": assign_label if assign_label != "— None —" else "",
            "assigned_to_employee_id": emp.get("id"),
            "notes": notes,
        }
        if change_asset and link_asset is not None:
            asset_refs = get_kit_reference_options(include_assets=True, exclude_asset_id=aid)
            child = next((a for lbl, a in asset_refs.assets if lbl == link_asset), {})
            payload["child_asset_id"] = child.get("id") if child else None
        if change_inv and link_inv is not None:
            inv_refs = get_kit_reference_options(include_inventory=True)
            inv_row = next((r for lbl, r in inv_refs.inventory if lbl == link_inv), {})
            payload["inventory_item_id"] = inv_row.get("id") if inv_row else None

        result = update_asset_kit_item(iid, payload)
        if result.ok:
            st.session_state[edit_key] = False
            ips_app_rerun()
        else:
            st.error(result.error or "Could not save item.")
