"""Pricing Guide add/edit forms with lightweight reference lookups."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.item_photo_manager import render_item_photo_manager
from app.components.record_modal import render_edit_form_header, render_save_cancel_actions, set_view_mode
from app.pages._core._crud import apply_persist_feedback, is_demo_id
from app.services.pricing_guide_images import (
    clear_pricing_guide_image,
    pricing_guide_display_record,
    pricing_guide_image_is_inherited,
    upload_pricing_guide_image,
)
from app.services.pricing_guide_reference_service import (
    ensure_option_for_id,
    search_asset_link_options,
    search_inventory_link_options,
    search_vendor_options,
)
from app.services.pricing_guide_service import PRICING_ITEM_CLASSES, PRICING_ITEM_TYPES, calc_sell_price, clear_pricing_guide_cache
from app.utils.formatting import fmt_currency


def render_conditional_fields(
    prefix: str,
    item_class: str,
    item_type: str,
    *,
    row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    if item_class == "Inventory":
        search = st.text_input("Search inventory", key=f"{prefix}_inv_search", placeholder="SKU or name…")
        inv_opts = search_inventory_link_options(search=search, limit=100)
        current_id = str((row or {}).get("linked_inventory_id") or (row or {}).get("inventory_item_id") or "")
        inv_opts = ensure_option_for_id(
            inv_opts,
            record_id=current_id,
            display_label=str((row or {}).get("inventory_label") or current_id),
        )
        labels = ["— None —"] + [o["display_label"] for o in inv_opts]
        default_ix = 0
        if current_id:
            for i, opt in enumerate(inv_opts):
                if opt["id"] == current_id:
                    default_ix = i + 1
                    break
        pick = st.selectbox("Link inventory item", labels, index=default_ix, key=f"{prefix}_inv")
        if pick == "— None —":
            extra["linked_inventory_id"] = None
            extra["inventory_item_id"] = None
        else:
            chosen = inv_opts[labels.index(pick) - 1]
            extra["linked_inventory_id"] = chosen["id"]
            extra["inventory_item_id"] = chosen["id"]
    elif item_class == "Asset":
        search = st.text_input("Search assets", key=f"{prefix}_asset_search", placeholder="Asset # or name…")
        asset_opts = search_asset_link_options(search=search, limit=100)
        current_id = str((row or {}).get("linked_asset_id") or (row or {}).get("asset_id") or "")
        asset_opts = ensure_option_for_id(
            asset_opts,
            record_id=current_id,
            display_label=str((row or {}).get("asset_label") or current_id),
        )
        labels = ["— None —"] + [o["display_label"] for o in asset_opts]
        default_ix = 0
        if current_id:
            for i, opt in enumerate(asset_opts):
                if opt["id"] == current_id:
                    default_ix = i + 1
                    break
        pick = st.selectbox("Link asset", labels, index=default_ix, key=f"{prefix}_asset")
        if pick == "— None —":
            extra["linked_asset_id"] = None
            extra["asset_id"] = None
        else:
            chosen = asset_opts[labels.index(pick) - 1]
            extra["linked_asset_id"] = chosen["id"]
            extra["asset_id"] = chosen["id"]
        extra["equipment_type"] = st.text_input(
            "Equipment type",
            value=str((row or {}).get("equipment_type") or ""),
            key=f"{prefix}_eq_type",
        )
    elif item_type == "Labor":
        extra["labor_role"] = st.text_input(
            "Labor role",
            value=str((row or {}).get("labor_role") or ""),
            key=f"{prefix}_labor_role",
        )
    elif item_type == "Travel":
        travel_types = ["Mileage", "Per Diem", "Lodging", "Mobilization", "Fuel surcharge", "Other"]
        current = str((row or {}).get("travel_type") or "Mileage")
        extra["travel_type"] = st.selectbox(
            "Travel type",
            travel_types,
            index=travel_types.index(current) if current in travel_types else 0,
            key=f"{prefix}_travel_type",
        )
    elif item_type == "Subcontractor":
        search = st.text_input("Search vendors", key=f"{prefix}_vendor_search", placeholder="Vendor name…")
        vendor_opts = search_vendor_options(search=search, limit=100)
        current_id = str((row or {}).get("vendor_id") or "")
        vendor_opts = ensure_option_for_id(
            vendor_opts,
            record_id=current_id,
            display_label=str((row or {}).get("vendor") or current_id),
        )
        labels = ["— None —"] + [o["display_label"] for o in vendor_opts]
        default_ix = 0
        if current_id:
            for i, opt in enumerate(vendor_opts):
                if opt["id"] == current_id:
                    default_ix = i + 1
                    break
        pick = st.selectbox("Vendor", labels, index=default_ix, key=f"{prefix}_vendor")
        extra["vendor_id"] = None if pick == "— None —" else vendor_opts[labels.index(pick) - 1]["id"]
    elif item_type == "Service":
        extra["category"] = st.text_input(
            "Service category",
            value=str((row or {}).get("category") or ""),
            key=f"{prefix}_svc_cat",
        )
    elif item_type == "Assembly":
        st.caption("Assembly packages: component grouping will be added in a future release.")
    return extra


def render_pg_photo_manager(
    row: dict[str, Any],
    *,
    cache_key: str,
    module: str,
    permissions: Any,
    record_session_key_fn: Any,
) -> None:
    rid = str(row.get("id") or "").strip()
    rk = record_session_key_fn(row, "id")
    display = pricing_guide_display_record(row)
    render_item_photo_manager(
        row,
        record_id=rid,
        session_prefix=f"pg_photo_{rk}",
        image_css_class="ips-pg-detail-image",
        upload_image=upload_pricing_guide_image,
        clear_image=clear_pricing_guide_image,
        uploaded_by=str(getattr(permissions, "user_name", "") or ""),
        cache_key=cache_key,
        on_change=clear_pricing_guide_cache,
        readonly=not permissions.can_manage or is_demo_id(rid),
        preview_record=display,
    )
    if pricing_guide_image_is_inherited(row):
        item_class = str(row.get("item_class") or "").strip().lower()
        if item_class == "asset":
            st.caption("Photo from linked asset.")
        elif item_class == "inventory":
            st.caption("Photo from linked inventory item.")
        else:
            st.caption("Photo from linked catalog record.")


def render_pricing_guide_edit_form(
    row: dict[str, Any],
    *,
    module: str,
    cache_key: str,
    permissions: Any,
    record_session_key_fn: Any,
    persist_fn: Any,
) -> None:
    from app.perf_debug import perf_span

    rk = record_session_key_fn(row, "id")
    with perf_span("pricing_guide.detail.edit"):
        render_edit_form_header("Edit Pricing Item")
        c1, c2 = st.columns(2)
        with c1:
            description = st.text_input(
                "Description",
                value=str(row.get("description") or row.get("item") or ""),
                key=f"pg_edit_desc_{rk}",
            )
            item_class = st.selectbox(
                "Item Class",
                list(PRICING_ITEM_CLASSES),
                index=list(PRICING_ITEM_CLASSES).index(str(row.get("item_class") or "Non-Inventory"))
                if str(row.get("item_class") or "Non-Inventory") in PRICING_ITEM_CLASSES
                else 2,
                key=f"pg_edit_class_{rk}",
            )
            item_type = st.selectbox(
                "Estimate Line Type",
                list(PRICING_ITEM_TYPES),
                index=list(PRICING_ITEM_TYPES).index(str(row.get("item_type") or "Material"))
                if str(row.get("item_type") or "Material") in PRICING_ITEM_TYPES
                else 0,
                key=f"pg_edit_type_{rk}",
            )
            unit = st.text_input("Unit", value=str(row.get("unit") or "EA"), key=f"pg_edit_unit_{rk}")
            category = st.text_input("Category", value=str(row.get("category") or ""), key=f"pg_edit_cat_{rk}")
            stock_labels = [
                "Not stocked",
                "Optional (extras only)",
                "Mandatory (reorder when low)",
            ]
            stock_keys = ["none", "optional", "mandatory"]
            cur_policy = str(row.get("stock_policy") or "none")
            stock_ix = stock_keys.index(cur_policy) if cur_policy in stock_keys else 0
            stock_label = st.selectbox("Stock policy", stock_labels, index=stock_ix, key=f"pg_edit_stock_{rk}")
            stock_policy = stock_keys[stock_labels.index(stock_label)]
            default_reorder = st.number_input(
                "Default reorder point",
                min_value=0,
                value=int(round(float(row.get("default_reorder_point") or 0))),
                step=1,
                format="%d",
                key=f"pg_edit_reorder_{rk}",
                disabled=stock_policy == "none",
            )
        with c2:
            purchase = st.number_input(
                "Cost",
                min_value=0.0,
                value=float(row.get("default_cost") or 0),
                key=f"pg_edit_cost_{rk}",
            )
            markup = st.number_input(
                "Markup %",
                min_value=0.0,
                value=float(row.get("markup_pct") or 0),
                key=f"pg_edit_mk_{rk}",
            )
            sell = calc_sell_price(
                float(st.session_state.get(f"pg_edit_cost_{rk}", purchase)),
                float(st.session_state.get(f"pg_edit_mk_{rk}", markup)),
            )
            st.metric("Sell Price", fmt_currency(sell))
            active = st.checkbox("Active", value=bool(row.get("is_active", True)), key=f"pg_edit_active_{rk}")

        extra = render_conditional_fields(f"pg_edit_{rk}", item_class, item_type, row=row)
        notes = st.text_area("Notes", value=str(row.get("notes") or ""), key=f"pg_edit_notes_{rk}")
        st.markdown("**Item Photo**")
        render_pg_photo_manager(
            row,
            cache_key=cache_key,
            module=module,
            permissions=permissions,
            record_session_key_fn=record_session_key_fn,
        )

        cancelled, saved = render_save_cancel_actions(
            module=module,
            record_key=rk,
            cancel_key=f"pg_edit_cancel_{rk}",
            save_key=f"pg_edit_save_{rk}",
        )
        if cancelled:
            st.rerun()
        if saved:
            ok, msg = persist_fn(
                {
                    "description": description,
                    "item_class": item_class,
                    "item_type": item_type,
                    "category": extra.get("category") or category,
                    "unit": unit,
                    "default_cost": purchase,
                    "default_markup_percent": markup,
                    "default_sell_price": sell,
                    "is_active": active,
                    "notes": notes,
                    "stock_policy": stock_policy,
                    "default_reorder_point": int(round(default_reorder)),
                    "item_code": row.get("item_code") or row.get("item_key"),
                    **extra,
                },
                row_id=str(row.get("id") or ""),
            )
            stock_saved = True
            stock_error = ""
            if ok:
                try:
                    from app.services.catalog_stock_policy_service import save_pricing_stock_settings

                    save_pricing_stock_settings(
                        {
                            **row,
                            "id": row.get("id"),
                            "stock_policy": stock_policy,
                            "default_reorder_point": float(default_reorder),
                        },
                        stock_policy=stock_policy,
                        default_reorder_point=int(round(default_reorder)),
                        ensure_inventory=True,
                    )
                except Exception as exc:
                    stock_saved = False
                    stock_error = str(exc)
            if apply_persist_feedback(ok, msg):
                if not stock_saved:
                    st.warning("Pricing item saved, but stock/reorder settings could not be updated.")
                    if stock_error:
                        st.caption(stock_error[:240])
                set_view_mode(module, rk)
                st.rerun()
            st.error(msg or "Could not save pricing item.")


@st.dialog("New Pricing Item")
def render_new_pricing_item_dialog(
    *,
    module: str,
    permissions: Any,
    persist_fn: Any,
) -> None:
    if not permissions.can_manage:
        st.info("You do not have permission to add pricing items.")
        return
    c1, c2 = st.columns(2, gap="small")
    with c1:
        description = st.text_input("Description *", key="pg_new_desc")
        item_class = st.selectbox("Item Class *", list(PRICING_ITEM_CLASSES), key="pg_new_class")
        item_type = st.selectbox("Estimate Line Type *", list(PRICING_ITEM_TYPES), key="pg_new_type")
        unit = st.text_input("Unit *", value="EA", key="pg_new_unit")
        category = st.text_input("Category", key="pg_new_cat")
    with c2:
        cost = st.number_input("Cost *", min_value=0.0, value=0.0, key="pg_new_cost")
        markup = st.number_input("Markup % *", min_value=0.0, value=25.0, key="pg_new_mk")
        sell = calc_sell_price(float(st.session_state.get("pg_new_cost") or 0), float(st.session_state.get("pg_new_mk") or 0))
        st.metric("Sell Price", fmt_currency(sell))
        active = st.checkbox("Active", value=True, key="pg_new_active")
    extra = render_conditional_fields("pg_new", item_class, item_type)
    if st.button("Save Pricing Item", key="pg_new_save", type="primary"):
        ok, msg = persist_fn(
            {
                "description": description,
                "item_class": item_class,
                "item_type": item_type,
                "unit": unit,
                "category": extra.get("category") or category,
                "default_cost": cost,
                "default_markup_percent": markup,
                "default_sell_price": sell,
                "is_active": active,
                **extra,
            }
        )
        if apply_persist_feedback(ok, msg):
            st.session_state.pop("pg_new_dialog_open", None)
            st.rerun()
