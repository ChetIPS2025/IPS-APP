"""Add, import, and link kit item forms."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.asset_kit.reference_options import get_kit_reference_options
from app.components.asset_kit.state import MAX_KIT_UNIT_SERIAL_INPUTS, sk
from app.services.asset_kits_service import (
    CONDITIONS,
    ITEM_STATUSES,
    ITEM_TYPES,
    create_asset_kit_item,
    create_asset_kit_items_multi,
)
from app.ui.streamlit_perf import ips_app_rerun


def parse_bulk_serials(text: str, *, expected: int) -> tuple[list[str] | None, str | None]:
    lines = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
    if len(lines) != expected:
        return None, f"Enter exactly {expected} serial numbers (one per line); got {len(lines)}."
    lowered = [s.lower() for s in lines]
    if len(set(lowered)) != len(lowered):
        return None, "Duplicate serial numbers are not allowed."
    return lines, None


def render_unit_serial_inputs(
    aid: str,
    *,
    unit_count: int,
    key_prefix: str,
    required: bool = False,
) -> list[str]:
    if unit_count <= MAX_KIT_UNIT_SERIAL_INPUTS:
        serials: list[str] = []
        if unit_count > 1:
            st.markdown("**Serial number per unit**")
            for idx in range(unit_count):
                serials.append(
                    st.text_input(
                        f"Unit {idx + 1} serial" + (" *" if required else ""),
                        key=f"{key_prefix}_serial_{aid}_{idx}",
                    )
                )
        else:
            serials.append(
                st.text_input(
                    "Serial number" + (" *" if required else " (optional)"),
                    key=f"{key_prefix}_serial_{aid}_0",
                )
            )
        return serials

    st.info(
        f"Quantity exceeds {MAX_KIT_UNIT_SERIAL_INPUTS}. Enter one serial per line below "
        f"({unit_count} lines expected)."
    )
    bulk = st.text_area(
        "Serial numbers (one per line)",
        height=min(200, 40 + unit_count * 4),
        key=f"{key_prefix}_bulk_serial_{aid}",
    )
    parsed, err = parse_bulk_serials(bulk, expected=unit_count)
    if err and bulk.strip():
        st.error(err)
    return parsed or []


def render_add_kit_item_form(asset: dict, aid: str) -> None:
    if st.button("← Back to kit list", key=f"kit_back_add_{aid}"):
        st.session_state[sk(aid, "view")] = "list"
        st.rerun()
    st.markdown("##### Add Kit Item")
    st.caption(
        "For multiple physical units of the same item, enter the quantity and a serial number for each unit. "
        "Each unit is tracked as its own row in the kit."
    )
    with st.form(f"kit_add_item_{aid}"):
        name = st.text_input("Item name *")
        item_type = st.selectbox("Item type", ITEM_TYPES)
        category = st.text_input("Category")
        c1, c2, c3 = st.columns(3)
        with c1:
            qty = st.number_input("Quantity expected", min_value=1.0, value=1.0, step=1.0)
        with c2:
            unit = st.text_input("Unit", value="EA")
        with c3:
            unit_val = st.number_input("Unit value", min_value=0.0, value=0.0, step=1.0)
        condition = st.selectbox("Condition", CONDITIONS, index=1)
        status = st.selectbox("Status", ITEM_STATUSES, index=0)
        unit_count = max(1, int(round(float(qty or 1))))
        unit_serials = render_unit_serial_inputs(aid, unit_count=unit_count, key_prefix="kit_add", required=unit_count > 1)
        notes = st.text_area("Notes", height=50)
        if st.form_submit_button("Save Kit Item", type="primary"):
            if not str(name or "").strip():
                st.error("Item name is required.")
            elif unit_count > 1 and len(unit_serials) != unit_count:
                st.error(f"Enter a serial number for each of the {unit_count} units.")
            else:
                result = create_asset_kit_items_multi(
                    aid,
                    {
                        "item_name": name,
                        "item_type": item_type,
                        "category": category,
                        "quantity_expected": unit_count,
                        "quantity_actual": unit_count,
                        "unit": unit,
                        "unit_value": unit_val,
                        "condition": condition,
                        "status": status,
                        "notes": notes,
                        "unit_serials": unit_serials,
                    },
                )
                if result.ok:
                    st.session_state[sk(aid, "view")] = "list"
                    n = int((result.data or {}).get("count") or 1) if isinstance(result.data, dict) else 1
                    st.success(f"Added {n} kit item(s).")
                    ips_app_rerun()
                else:
                    st.error(result.error or "Could not add item.")


def render_import_inventory_form(asset: dict, aid: str) -> None:
    if st.button("← Back to kit list", key=f"kit_back_imp_{aid}"):
        st.session_state[sk(aid, "view")] = "list"
        st.rerun()
    st.markdown("##### Import From Inventory")
    refs = get_kit_reference_options(include_inventory=True)
    inv_opts = list(refs.inventory)
    labels = [x[0] for x in inv_opts]
    with st.form(f"kit_import_inv_{aid}"):
        pick = st.selectbox("Inventory item", labels, index=0)
        qty = st.number_input("Quantity", min_value=1.0, value=1.0, step=1.0)
        unit_count = max(1, int(round(float(qty or 1))))
        import_serials = render_unit_serial_inputs(
            aid,
            unit_count=unit_count,
            key_prefix="kit_imp",
            required=unit_count > 1,
        )
        if st.form_submit_button("Import", type="primary"):
            row = next((r for lbl, r in inv_opts if lbl == pick), {})
            if not row:
                st.error("Select an inventory item.")
            elif unit_count > 1 and len(import_serials) != unit_count:
                st.error(f"Enter a serial number for each of the {unit_count} units.")
            else:
                unit_cost = float(row.get("unit_cost") or row.get("purchase_cost") or 0)
                result = create_asset_kit_items_multi(
                    aid,
                    {
                        "item_name": row.get("item_name") or row.get("name"),
                        "item_type": "Consumable"
                        if str(row.get("category") or "").lower() == "materials"
                        else "Material",
                        "category": row.get("category"),
                        "description": row.get("description"),
                        "quantity_expected": unit_count,
                        "quantity_actual": unit_count,
                        "unit": row.get("unit") or "EA",
                        "unit_value": unit_cost,
                        "inventory_item_id": row.get("id"),
                        "unit_serials": import_serials if unit_count > 1 else [],
                    },
                )
                if result.ok:
                    st.session_state[sk(aid, "view")] = "list"
                    n = int((result.data or {}).get("count") or 1) if isinstance(result.data, dict) else 1
                    st.success(f"Imported {n} kit item(s) from inventory.")
                    ips_app_rerun()
                else:
                    st.error(result.error or "Import failed.")


def render_link_asset_form(asset: dict, aid: str) -> None:
    if st.button("← Back to kit list", key=f"kit_back_link_{aid}"):
        st.session_state[sk(aid, "view")] = "list"
        st.rerun()
    st.markdown("##### Link Existing Asset")
    refs = get_kit_reference_options(include_assets=True, exclude_asset_id=aid)
    opts = list(refs.assets)
    labels = [x[0] for x in opts]
    with st.form(f"kit_link_asset_{aid}"):
        pick = st.selectbox("Asset", labels, index=0)
        if st.form_submit_button("Link Asset", type="primary"):
            row = next((a for lbl, a in opts if lbl == pick), {})
            if not row:
                st.error("Select an asset.")
            else:
                val = float(row.get("value") or row.get("current_value") or row.get("purchase_price") or 0)
                result = create_asset_kit_item(
                    aid,
                    {
                        "item_name": row.get("asset_name") or row.get("name"),
                        "item_type": "Equipment",
                        "category": row.get("category"),
                        "quantity_expected": 1,
                        "quantity_actual": 1,
                        "unit_value": val,
                        "serial_number": row.get("serial_number"),
                        "child_asset_id": row.get("id"),
                    },
                )
                if result.ok:
                    st.session_state[sk(aid, "view")] = "list"
                    st.success("Asset linked as kit item.")
                    ips_app_rerun()
                else:
                    st.error(result.error or "Link failed.")
