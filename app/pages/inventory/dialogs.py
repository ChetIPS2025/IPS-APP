"""
Inventory dialogs: Add and Edit workflows.

Each dialog is decorated with ``@st.dialog`` so it renders as a modal overlay.
"""

from __future__ import annotations

import streamlit as st

try:
    from app.ui.compact_forms import field_marker
    from app.ui.modal import ensure_modal_styles, modal_wide_marker
    from app.ui.streamlit_perf import ips_app_rerun
    from app.table_actions import TABLE_KEY_INVENTORY, clear_selected_ids
except ImportError:
    from ui.compact_forms import field_marker  # type: ignore
    from ui.modal import ensure_modal_styles, modal_wide_marker  # type: ignore
    from ui.streamlit_perf import ips_app_rerun  # type: ignore
    from table_actions import TABLE_KEY_INVENTORY, clear_selected_ids  # type: ignore

from app.pages.inventory.components import (
    SK_EDIT_MODE,
    SK_SELECTED_ITEM_ID,
    SK_VIEW_MODE,
    _clear_inv_checkbox_keys,
)
from app.pages.inventory.services import save_edited_item, save_new_item
from app.pages.inventory.utils import qr_img_html, qr_png_bytes, inventory_label_html
from app.pages.inventory.services import (
    allocate_unique_qr,
    get_signed_image_url,
    sync_qr_to_storage,
)
from app.pages.inventory.queries import update_inventory_item


# ---------------------------------------------------------------------------
# Dismiss callbacks (called when user closes dialog via X button)
# ---------------------------------------------------------------------------

def _on_add_dismiss() -> None:
    st.session_state[SK_VIEW_MODE] = None
    st.session_state.pop("inventory_panel_mode", None)


def _on_edit_dismiss() -> None:
    st.session_state[SK_EDIT_MODE] = False
    st.session_state.pop(SK_SELECTED_ITEM_ID, None)
    st.session_state["inventory_edit_popup_open"] = False
    st.session_state["editing_inventory_id"] = None


# ---------------------------------------------------------------------------
# Add dialog
# ---------------------------------------------------------------------------

@st.dialog("Add inventory item", width="large", on_dismiss=_on_add_dismiss)
def inventory_add_dialog() -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Add inventory item")

    # Pre-fill category if the category filter is set to something useful
    if str(st.session_state.get(SK_EDIT_MODE) or "").strip().lower() == "materials":
        st.session_state.setdefault("inv_add_cat", "Materials")
    # Legacy pre-fill key
    if str(st.session_state.get("inv_f_cat") or "").strip().lower() == "materials":
        st.session_state.setdefault("inv_add_cat", "Materials")

    with st.form("inv_add_item_form_v2", clear_on_submit=True):
        name = st.text_input("Item Name *", key="inv_add_name")
        sku_add = st.text_input(
            "SKU (optional)",
            key="inv_add_sku",
            help="Alternate lookup on **Scan Inventory** if QR is not used.",
        )
        c1, c2 = st.columns(2, gap="small")
        category = c1.text_input("Category", key="inv_add_cat")
        unit = c2.text_input("Unit", value="EA", key="inv_add_unit")

        r1, r2, r3 = st.columns(3, gap="small")
        qty = r1.number_input(
            "On Hand", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="inv_add_qty"
        )
        reorder = r2.number_input(
            "Reorder Point", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="inv_add_reorder"
        )
        unit_cost = r3.number_input(
            "Unit Cost", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="inv_add_cost"
        )

        v1, v2 = st.columns(2, gap="small")
        vendor = v1.text_input("Vendor", key="inv_add_vendor")
        storage_location = v2.text_input("Storage Location", key="inv_add_loc")

        notes = st.text_area("Notes", key="inv_add_notes", height=68)
        img_add = st.file_uploader(
            "Item Image",
            type=["png", "jpg", "jpeg"],
            key="inv_img_add",
            help="Optional thumbnail (resized on upload). PNG or JPEG.",
        )
        qr_scan = st.text_input(
            "QR scan code (optional)",
            key="inv_add_qr",
            help="Unique value for **Scan Inventory**; leave blank to auto-assign.",
        )
        is_active = st.checkbox("Active", value=True, key="inv_add_active")
        submitted = st.form_submit_button("Create item", type="primary", use_container_width=True)

    if st.button("Cancel", type="secondary", use_container_width=True, key="inv_add_cancel_dlg"):
        st.session_state[SK_VIEW_MODE] = None
        st.session_state.pop("inventory_panel_mode", None)
        ips_app_rerun()

    if submitted:
        t = str(name or "").strip()
        if not t:
            st.error("Item Name is required.")
            return

        ok, msg = save_new_item(
            name=t,
            category=str(category or "").strip(),
            unit=str(unit or "").strip() or "EA",
            qty=float(qty or 0),
            reorder=float(reorder or 0),
            unit_cost=float(unit_cost) if float(unit_cost or 0) > 0 else None,
            vendor=str(vendor or "").strip(),
            storage_location=str(storage_location or "").strip(),
            notes=str(notes or "").strip(),
            is_active=bool(is_active),
            qr_value=str(qr_scan or "").strip() or None,
            sku=str(sku_add or "").strip() or None,
            image_file=img_add,
        )
        if not ok:
            st.error(msg)
            return

        st.session_state[SK_VIEW_MODE] = None
        st.session_state.pop("inventory_panel_mode", None)
        st.session_state["inventory_success"] = msg
        ips_app_rerun()


# ---------------------------------------------------------------------------
# Edit dialog
# ---------------------------------------------------------------------------

@st.dialog("Edit inventory item", width="large", on_dismiss=_on_edit_dismiss)
def inventory_edit_dialog(row: dict) -> None:
    ensure_modal_styles()
    modal_wide_marker()
    rid = str(row.get("id") or "")
    pk = f"inv_ed_{rid}"
    st.markdown("### Edit inventory item")
    st.caption(f"ID `{rid[:8]}…`")

    with st.form(f"inv_edit_item_form_{rid}", clear_on_submit=False):
        name = st.text_input("Item Name *", value=str(row.get("item_name") or ""), key=f"{pk}_name")
        sku_ed = st.text_input(
            "SKU (optional)",
            value=str(row.get("sku") or ""),
            key=f"{pk}_sku",
            help="Alternate lookup on **Scan Inventory**.",
        )
        c1, c2 = st.columns(2, gap="small")
        category = c1.text_input("Category", value=str(row.get("category") or ""), key=f"{pk}_cat")
        unit = c2.text_input("Unit", value=str(row.get("unit") or "EA"), key=f"{pk}_unit")

        r1, r2, r3 = st.columns(3, gap="small")
        qty = r1.number_input(
            "On Hand",
            min_value=0.0,
            value=float(row.get("quantity_on_hand") or 0),
            step=1.0,
            format="%.2f",
            key=f"{pk}_qty",
        )
        reorder = r2.number_input(
            "Reorder Point",
            min_value=0.0,
            value=float(row.get("reorder_point") or 0),
            step=1.0,
            format="%.2f",
            key=f"{pk}_reorder",
        )
        uc_val = row.get("unit_cost")
        try:
            uc_default = float(uc_val) if uc_val is not None and str(uc_val).strip() != "" else 0.0
        except (TypeError, ValueError):
            uc_default = 0.0
        unit_cost = r3.number_input(
            "Unit Cost",
            min_value=0.0,
            value=uc_default,
            step=0.01,
            format="%.2f",
            key=f"{pk}_cost",
        )

        v1, v2 = st.columns(2, gap="small")
        vendor = v1.text_input("Vendor", value=str(row.get("vendor") or ""), key=f"{pk}_vendor")
        storage_location = v2.text_input(
            "Storage Location", value=str(row.get("storage_location") or ""), key=f"{pk}_loc"
        )

        notes = st.text_area("Notes", value=str(row.get("notes") or ""), height=68, key=f"{pk}_notes")

        # Image preview and upload
        st.caption("Item photo")
        img_existing = get_signed_image_url(str(row.get("image_url") or "").strip())
        if img_existing:
            st.image(img_existing, width=80)
        else:
            st.markdown('<p style="font-size:2rem;margin:0;line-height:1;">📦</p>', unsafe_allow_html=True)
        img_ed = st.file_uploader(
            "Replace image",
            type=["png", "jpg", "jpeg"],
            key=f"inv_img_{rid}",
            help="Upload a new image to replace the thumbnail.",
        )

        qr_in = st.text_input(
            "QR scan code",
            value=str(row.get("qr_code_value") or "").strip(),
            key=f"{pk}_qr",
            help="Printed / scanned value for **Scan Inventory**.",
        )
        is_active = st.checkbox("Active", value=bool(row.get("is_active", True)), key=f"{pk}_active")

        submitted = st.form_submit_button("Save", type="primary", use_container_width=True)

    # QR label expander (outside form)
    with st.expander("QR Label / Code", expanded=False):
        qr_cur = str(row.get("qr_code_value") or "").strip()
        if qr_cur:
            st.caption("Label preview")
            st.markdown(qr_img_html(qr_cur), unsafe_allow_html=True)
            html_doc = inventory_label_html(
                item_name=str(row.get("item_name") or ""),
                sku=str(row.get("sku") or ""),
                qr_value=qr_cur,
                item_id=rid,
            )
            st.download_button(
                "Print QR label (HTML)",
                data=html_doc.encode("utf-8"),
                file_name=f"inventory_label_{rid[:8]}.html",
                mime="text/html",
                key=f"{pk}_dl_lbl",
            )
            png = qr_png_bytes(qr_cur)
            if png:
                st.download_button(
                    "Download QR (PNG)",
                    data=png,
                    file_name=f"inventory_qr_{rid[:8]}.png",
                    mime="image/png",
                    key=f"{pk}_dl_png",
                )
        if st.button("Generate new QR code", key=f"{pk}_qrgen", help="Assigns a new unique scan code"):
            try:
                nv = allocate_unique_qr(
                    item_id=str(row.get("id") or ""),
                    preferred=None,
                    exclude_item_id=str(row.get("id") or ""),
                )
                update_inventory_item(str(row.get("id") or ""), {"qr_code_value": nv})
                sync_qr_to_storage(str(row.get("id") or ""), nv)
            except Exception as exc:
                st.error(f"Could not update QR: {exc}")
                return
            ips_app_rerun()

    if st.button("Cancel", type="secondary", use_container_width=True, key=f"{pk}_cancel_dlg"):
        st.session_state[SK_EDIT_MODE] = False
        st.session_state.pop(SK_SELECTED_ITEM_ID, None)
        st.session_state["inventory_edit_popup_open"] = False
        st.session_state["editing_inventory_id"] = None
        st.session_state["selected_inventory_ids"] = []
        _clear_inv_checkbox_keys()
        clear_selected_ids(TABLE_KEY_INVENTORY)
        st.session_state.pop("inventory_panel_mode", None)
        ips_app_rerun()

    if submitted:
        t = str(name or "").strip()
        if not t:
            st.error("Item Name is required.")
            return

        ok, msg = save_edited_item(
            item_id=rid,
            name=t,
            category=str(category or "").strip(),
            unit=str(unit or "").strip() or "EA",
            qty=float(qty or 0),
            reorder=float(reorder or 0),
            unit_cost=float(unit_cost) if float(unit_cost or 0) > 0 else None,
            vendor=str(vendor or "").strip(),
            storage_location=str(storage_location or "").strip(),
            notes=str(notes or "").strip(),
            is_active=bool(is_active),
            qr_value=str(qr_in or "").strip() or None,
            old_qr_value=str(row.get("qr_code_value") or "").strip() or None,
            sku=str(sku_ed or "").strip() or None,
            image_file=img_ed,
        )
        if not ok:
            st.error(msg)
            return

        # Clean up state and return to list
        st.session_state[SK_EDIT_MODE] = False
        st.session_state.pop(SK_SELECTED_ITEM_ID, None)
        st.session_state["inventory_edit_popup_open"] = False
        st.session_state["editing_inventory_id"] = None
        st.session_state["selected_inventory_ids"] = []
        _clear_inv_checkbox_keys()
        clear_selected_ids(TABLE_KEY_INVENTORY)
        st.session_state.pop("inventory_panel_mode", None)
        st.session_state["inventory_success"] = msg
        ips_app_rerun()
