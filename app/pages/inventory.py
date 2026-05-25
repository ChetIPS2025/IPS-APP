"""Inventory module (Phase 2B)."""

from __future__ import annotations

import base64
import html

import streamlit as st

try:
    from app.components.inventory_actions import render_inventory_action_buttons
    from app.components.headers import render_page_brand_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.table_filters import (
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from app.components.record_modal import (
        build_modal_cache,
        clear_edit_modes,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_view_mode,
        status_pill_html,
    )
    from app.pages._core._data import load_inventory, lookup_options
    from app.pages._core._crud import is_demo_id
    from app.pages._core._session import select_key
    from app.services.inventory_display_helpers import (
        inventory_qr_png_bytes,
        resolve_inventory_sku,
    )
    from app.services.inventory_service import (
        clear_inventory_cache,
        ensure_inventory_qr_tokens,
        generate_inventory_qr_value,
        get_inventory_image_url,
        get_inventory_transactions,
        update_inventory_item,
        upload_inventory_image,
    )
    from app.styles import inject_inventory_module_css
    from app.utils.formatting import fmt_currency, fmt_date
    from app.utils.phone_helpers import format_phone_display
except ImportError:
    from components.inventory_actions import render_inventory_action_buttons  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.table_filters import (  # type: ignore
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_edit_modes,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_view_mode,
        status_pill_html,
    )
    from pages._core._data import load_inventory, lookup_options  # type: ignore
    from pages._core._crud import is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from services.inventory_display_helpers import (  # type: ignore
        inventory_qr_png_bytes,
        resolve_inventory_sku,
    )
    from services.inventory_service import (  # type: ignore
        clear_inventory_cache,
        ensure_inventory_qr_tokens,
        generate_inventory_qr_value,
        get_inventory_image_url,
        get_inventory_transactions,
        update_inventory_item,
        upload_inventory_image,
    )
    from styles import inject_inventory_module_css  # type: ignore
    from utils.formatting import fmt_currency  # type: ignore

_SEL = select_key("inventory")
_MODAL_KEY = "ips_inventory_detail_modal_id"
_CACHE_KEY = "_ips_inventory_modal_by_id"
_MODULE = "inventory"
SELECTED_INVENTORY_KEY = "selected_inventory_id"
SHOW_INVENTORY_MODAL_KEY = "show_inventory_detail_modal"
_ALL_INVENTORY_IDS_KEY = "_ips_inventory_visible_ids"
_TABLE_KEY = "inventory_list"
_INV_COLS = [0.35, 0.9, 4.35, 1.8, 1.6, 1.1, 0.8, 1.0, 1.3, 1.8]
_INV_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("IMAGE", None),
    ("DESCRIPTION", None),
    ("CATEGORY", "category"),
    ("LOCATION", "location"),
    ("QTY ON HAND", None),
    ("UNIT", None),
    ("UNIT COST", None),
    ("STATUS", "status"),
    ("VENDOR", "vendor"),
]
_FILTER_FIELDS = ["category", "location", "status", "vendor"]
_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("category", lambda r: _inventory_category(r)),
    ("location", lambda r: _inventory_location(r)),
    ("status", lambda r: _normalize_inventory_status(r.get("status"))),
    ("vendor", lambda r: _inventory_vendor(r)),
]

_INV_TABS = [
    "Overview",
    "Stock History",
    "Transactions",
    "Purchase Orders",
    "Vendors",
    "Notes",
    "Attachments",
]


def _normalize_inventory_status(raw: object) -> str:
    s = str(raw or "").strip().lower().replace("_", " ")
    mapping = {
        "": "In Stock",
        "in stock": "In Stock",
        "available": "In Stock",
        "low stock": "Low Stock",
        "out of stock": "Out of Stock",
        "depleted": "Out of Stock",
        "on order": "On Order",
        "discontinued": "Discontinued",
    }
    if s in mapping:
        return mapping[s]
    label = str(raw or "").strip()
    return label if label else "In Stock"


def _inventory_sku(row: dict) -> str:
    return resolve_inventory_sku(row)


def _inventory_item_number(row: dict) -> str:
    return _inventory_sku(row)


def _inventory_description(row: dict) -> str:
    for key in ("description", "item_name", "name"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _inventory_category(row: dict) -> str:
    return str(row.get("category") or "").strip() or "—"


def _inventory_location(row: dict) -> str:
    for key in ("location_name", "location"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _inventory_vendor(row: dict) -> str:
    for key in ("vendor_name", "vendor"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _inventory_unit(row: dict) -> str:
    return str(row.get("unit") or "").strip() or "—"


def _inventory_qty(row: dict) -> str:
    for key in ("quantity_on_hand", "qty_on_hand", "quantity"):
        val = row.get(key)
        if val is not None and str(val).strip() != "":
            try:
                num = float(val)
                return str(int(num)) if num == int(num) else f"{num:.1f}"
            except (TypeError, ValueError):
                return str(val).strip()
    return "0"


def _inventory_status_pill_html(status: str) -> str:
    cls_map = {
        "In Stock": "ips-inventory-status-in-stock",
        "Low Stock": "ips-inventory-status-low-stock",
        "Out of Stock": "ips-inventory-status-out-of-stock",
        "On Order": "ips-inventory-status-on-order",
        "Discontinued": "ips-inventory-status-discontinued",
    }
    cls = cls_map.get(status, "ips-inventory-status-in-stock")
    return f'<span class="ips-inventory-status-pill {cls}">{html.escape(status)}</span>'


def _current_user_id() -> str | None:
    try:
        from app.auth import current_profile
    except ImportError:
        from auth import current_profile  # type: ignore
    uid = str((current_profile() or {}).get("id") or "").strip()
    return uid or None


def _render_inventory_thumbnail(item: dict) -> None:
    image_url = get_inventory_image_url(item)
    if image_url:
        st.markdown(
            (
                f'<span class="ips-inventory-thumb-cell">'
                f'<img class="ips-inventory-thumb-img" src="{html.escape(image_url, quote=True)}" '
                f'alt="Inventory item image" />'
                f"</span>"
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="ips-inventory-thumb-cell">'
            '<span class="ips-inventory-thumb-placeholder">—</span>'
            "</span>",
            unsafe_allow_html=True,
        )


def _render_inventory_detail_image(item: dict) -> None:
    image_url = get_inventory_image_url(item)
    if image_url:
        st.markdown(
            f'<img class="ips-inventory-detail-image" src="{html.escape(image_url, quote=True)}" '
            f'alt="Inventory item image" />',
            unsafe_allow_html=True,
        )
    else:
        st.caption("No item image uploaded.")


def _inventory_select_key(item_id: str) -> str:
    return f"inventory_select_{item_id}"


def _clear_inventory_selection(item_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_INVENTORY_KEY] = None
    st.session_state[SHOW_INVENTORY_MODAL_KEY] = False
    ids = list(item_ids or [])
    for iid in ids:
        st.session_state[_inventory_select_key(iid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("inventory_select_"):
            st.session_state[key] = False


def _on_inventory_checkbox_change(item_id: str, all_item_ids: list[str]) -> None:
    key = _inventory_select_key(item_id)
    if st.session_state.get(key):
        for iid in all_item_ids:
            if iid != item_id:
                st.session_state[_inventory_select_key(iid)] = False
        st.session_state[SELECTED_INVENTORY_KEY] = item_id
        st.session_state[SHOW_INVENTORY_MODAL_KEY] = True
        cache = st.session_state.get(_CACHE_KEY) or {}
        item = cache.get(item_id) if isinstance(cache, dict) else None
        _open_inventory_modal(item_id, item)
    elif st.session_state.get(SELECTED_INVENTORY_KEY) == item_id:
        st.session_state[SELECTED_INVENTORY_KEY] = None
        st.session_state[SHOW_INVENTORY_MODAL_KEY] = False


def _render_custom_inventory_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
) -> list[str]:
    if not filtered:
        st.info("No inventory items match your filters.")
        st.session_state[_ALL_INVENTORY_IDS_KEY] = []
        return []

    all_item_ids = [str(i.get("id") or "").strip() for i in filtered if str(i.get("id") or "").strip()]
    st.session_state[_ALL_INVENTORY_IDS_KEY] = all_item_ids

    with st.container(key="inventory_table_wrap"):
        st.markdown('<div class="ips-inventory-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_INV_COLS, gap="small", vertical_alignment="center")
        for col, (label, field) in zip(header_cols, _INV_HEADER_SPECS):
            with col:
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-inventory-header-row ips-inventory-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-inventory-header-row ips-inventory-cell",
                    )

        for item in filtered:
            iid = str(item.get("id") or "").strip()
            if not iid:
                continue

            description = _inventory_description(item)
            category = _inventory_category(item)
            location = _inventory_location(item)
            qty = _inventory_qty(item)
            unit = _inventory_unit(item)
            unit_cost = fmt_currency(item.get("unit_cost"))
            status = _normalize_inventory_status(item.get("status"))
            vendor = _inventory_vendor(item)

            cols = st.columns(_INV_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                st.checkbox(
                    "",
                    key=_inventory_select_key(iid),
                    label_visibility="collapsed",
                    on_change=_on_inventory_checkbox_change,
                    args=(iid, all_item_ids),
                )

            with cols[1]:
                _render_inventory_thumbnail(item)

            with cols[2]:
                st.markdown(
                    f'<div class="ips-inventory-title">{html.escape(description)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(
                    f'<div class="ips-inventory-cell">{html.escape(category)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(
                    f'<div class="ips-inventory-cell">{html.escape(location)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[5]:
                st.markdown(
                    f'<div class="ips-inventory-cell ips-inventory-qty">{html.escape(qty)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[6]:
                st.markdown(
                    f'<div class="ips-inventory-muted ips-inventory-cell">{html.escape(unit)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[7]:
                st.markdown(
                    f'<div class="ips-inventory-cell">{html.escape(unit_cost)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[8]:
                st.markdown(_inventory_status_pill_html(status), unsafe_allow_html=True)

            with cols[9]:
                st.markdown(
                    f'<div class="ips-inventory-muted ips-inventory-cell">{html.escape(vendor)}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    return all_item_ids


def _filter_rows(
    rows: list[dict],
    *,
    q: str,
) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            r
            for r in out
            if ql in _inventory_sku(r).lower()
            or ql in str(r.get("qr_code_value") or "").lower()
            or ql in _inventory_description(r).lower()
            or ql in _inventory_category(r).lower()
            or ql in _inventory_location(r).lower()
            or ql in _inventory_vendor(r).lower()
            or ql in _normalize_inventory_status(r.get("status")).lower()
        ]
    return apply_column_filters(out, _TABLE_KEY, _COLUMN_FILTER_SPECS)


def _clear_inventory_modal() -> None:
    item_ids = st.session_state.get(_ALL_INVENTORY_IDS_KEY) or []
    _clear_inventory_selection([str(iid) for iid in item_ids])
    clear_edit_modes(_MODULE)
    clear_record_modal(
        table_key="inventory_list",
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _open_inventory_modal(record_id: str, record: dict | None) -> None:
    rid = str(record_id or "").strip()
    if not rid:
        return
    st.session_state[SELECTED_INVENTORY_KEY] = rid
    st.session_state[SHOW_INVENTORY_MODAL_KEY] = True
    open_record_modal(
        rid,
        record,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _seed_inventory_edit_form(item: dict) -> None:
    iid = str(item.get("id") or "")
    st.session_state[f"inv_edit_sku_{iid}"] = str(item.get("sku") or "")
    st.session_state[f"inv_edit_name_{iid}"] = str(item.get("name") or "")
    st.session_state[f"inv_edit_cat_{iid}"] = str(item.get("category") or "")
    st.session_state[f"inv_edit_status_{iid}"] = str(item.get("status") or "")
    st.session_state[f"inv_edit_loc_{iid}"] = str(item.get("location") or "")
    st.session_state[f"inv_edit_qty_{iid}"] = int(item.get("qty_on_hand") or 0)
    st.session_state[f"inv_edit_cost_{iid}"] = float(item.get("unit_cost") or 0)


def _render_inventory_qr_block(item: dict) -> None:
    """Clickable QR + checkout link for inventory scan form."""
    scan_url = generate_inventory_qr_value(item)
    qr_png = inventory_qr_png_bytes(item)
    if qr_png and scan_url:
        b64 = base64.b64encode(qr_png).decode("ascii")
        safe_url = html.escape(scan_url, quote=True)
        st.markdown(
            f'<a href="{safe_url}" target="_self" title="Open checkout form">'
            f'<img src="data:image/png;base64,{b64}" width="140" alt="Inventory QR code" '
            f'style="display:block;border:1px solid #e2e8f0;border-radius:8px;" />'
            f"</a>",
            unsafe_allow_html=True,
        )
    elif qr_png:
        st.image(qr_png, width=140)
    else:
        st.caption(str(item.get("qr_code_value") or "—"))
    if scan_url:
        st.link_button("Open Checkout Form", scan_url, use_container_width=True)
        st.caption("Scan with a phone or tap to open the checkout form.")


def _txn_action_label(txn_type: str) -> str:
    labels = {
        "check_out": "Take / Check Out",
        "check_in": "Return / Check In",
        "issue_to_job": "Issue to Job",
        "return_from_job": "Return From Job",
        "consume_on_job": "Consume On Job",
        "adjustment": "Adjustment",
        "TO_JOB": "Issue to Job",
        "OUT": "Check Out",
        "IN": "Check In",
        "SHOP": "Shop Use",
        "ADJUST": "Adjustment",
    }
    return labels.get(str(txn_type or "").strip(), str(txn_type or "—"))


def _render_inventory_transactions_tab(item: dict) -> None:
    iid = str(item.get("id") or "")
    txns = get_inventory_transactions(inventory_id=iid, limit=100)
    last_scan = "—"
    if txns:
        last_scan = fmt_date(txns[0].get("created_at"))

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.metric("On Hand", int(item.get("qty_on_hand") or 0))
    with c2:
        st.metric("Checked Out", int(float(item.get("quantity_checked_out") or 0)))
    with c3:
        st.metric("Allocated", int(float(item.get("quantity_allocated") or 0)))
    with c4:
        st.metric("Last Scan", last_scan)

    scan_url = generate_inventory_qr_value(item)
    if scan_url:
        st.link_button("Open Checkout Form", scan_url, use_container_width=True)
        st.code(scan_url, language=None)

    if not txns:
        st.caption("No scan transactions yet.")
        return

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
            f'<span>{html.escape(str(row.get("quantity_display") or ""))}</span>'
            f'<span>{html.escape(str(row.get("job_label") or "—"))}</span>'
            f'<span>{html.escape(str(row.get("scanned_by_name") or "—"))}</span>'
            f'<span>{html.escape(format_phone_display(str(row.get("scanned_by_phone") or "")))}</span>'
            f'<span>{html.escape(str(row.get("notes") or ""))}</span>'
            "</div>"
        )
    st.markdown(f'<div class="ips-inventory-txn-table">{head}{rows_html}</div>', unsafe_allow_html=True)


def _render_inventory_pricing_guide_section(item: dict) -> None:
    iid = str(item.get("id") or "")
    pricing_item_id = str(item.get("pricing_item_id") or "").strip()
    st.markdown("#### Pricing Guide")
    try:
        from app.services.pricing_guide_service import (
            cached_pricing_guide_rows,
            create_pricing_item_from_inventory,
            link_inventory_to_pricing_item,
        )
    except ImportError:
        from services.pricing_guide_service import (  # type: ignore
            cached_pricing_guide_rows,
            create_pricing_item_from_inventory,
            link_inventory_to_pricing_item,
        )

    linked = None
    if pricing_item_id:
        linked = next(
            (r for r in cached_pricing_guide_rows(include_inactive=True) if str(r.get("id")) == pricing_item_id),
            None,
        )
    if linked:
        st.success(f"Linked: **{linked.get('description')}** ({linked.get('item_type')})")
        st.caption(
            f"Cost {fmt_currency(linked.get('default_cost'))} · "
            f"Sell {fmt_currency(linked.get('default_sell_price'))}"
        )
    else:
        inv_linked = next(
            (r for r in cached_pricing_guide_rows(include_inactive=True) if str(r.get("inventory_item_id") or "") == iid),
            None,
        )
        if inv_linked:
            st.info(f"Linked via pricing item: **{inv_linked.get('description')}**")
        else:
            st.caption("No pricing guide item linked.")

    sync_cost = bool(item.get("sync_cost_to_pricing"))
    st.checkbox(
        "Sync inventory cost to pricing guide",
        value=sync_cost,
        key=f"inv_sync_cost_pg_{iid}",
        disabled=not (linked or pricing_item_id),
    )

    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("Create Pricing Item from Inventory", key=f"inv_create_pg_{iid}", use_container_width=True):
            ok, msg, pid = create_pricing_item_from_inventory(item)
            if ok and pid:
                link_inventory_to_pricing_item(iid, pid, sync_cost=st.session_state.get(f"inv_sync_cost_pg_{iid}", False))
                st.success(msg)
                st.rerun()
            elif ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    with c2:
        options = [
            (f"{r.get('description')} — {r.get('item_type')}", str(r.get("id")))
            for r in cached_pricing_guide_rows(include_inactive=True)
            if r.get("item_type") in {"Inventory", "Material", "Consumable"}
        ]
        if options and st.button("Link to Pricing Guide Item", key=f"inv_link_pg_{iid}", use_container_width=True):
            st.session_state[f"inv_show_pg_link_{iid}"] = True
    if st.session_state.get(f"inv_show_pg_link_{iid}") and options:
        labels = [label for label, _ in options]
        pick = st.selectbox("Pricing item", labels, key=f"inv_pg_pick_{iid}")
        id_map = {label: pid for label, pid in options}
        if st.button("Confirm Link", key=f"inv_pg_link_confirm_{iid}"):
            ok, msg = link_inventory_to_pricing_item(
                iid,
                id_map.get(pick, ""),
                sync_cost=st.session_state.get(f"inv_sync_cost_pg_{iid}", False),
            )
            if ok:
                st.success(msg)
                st.session_state.pop(f"inv_show_pg_link_{iid}", None)
                st.rerun()
            st.error(msg)


def _render_inventory_detail_tabs(item: dict) -> None:
    status = str(item.get("status") or "")
    (
        tab_overview,
        tab_stock,
        tab_transactions,
        tab_pos,
        tab_vendors,
        tab_notes,
        tab_attachments,
    ) = st.tabs(_INV_TABS)

    with tab_overview:
        media1, media2, details = st.columns([1.1, 0.9, 2.0])
        with media1:
            st.markdown("**Item Image**")
            _render_inventory_detail_image(item)
        with media2:
            st.markdown("**QR Code**")
            _render_inventory_qr_block(item)
        with details:
            details_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('SKU', item.get('sku'))}"
                f"{detail_field_html('Description', _inventory_description(item))}"
                f"{detail_field_html('Category', item.get('category'))}"
                f'{detail_field_html("Status", status, html_value=status_pill_html(status))}'
                f"{detail_field_html('Location', item.get('location'))}"
                f"{detail_field_html('Department', item.get('department'))}"
                f"{detail_field_html('Vendor', item.get('vendor'))}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Item Details", details_html), unsafe_allow_html=True)

        stock_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Qty On Hand', int(item.get('qty_on_hand') or 0))}"
            f"{detail_field_html('Checked Out', int(float(item.get('quantity_checked_out') or 0)))}"
            f"{detail_field_html('Allocated to Jobs', int(float(item.get('quantity_allocated') or 0)))}"
            f"{detail_field_html('Reorder Point', int(item.get('reorder_point') or 0))}"
            f"{detail_field_html('Unit', _inventory_unit(item))}"
            f"{detail_field_html('Unit Cost', fmt_currency(item.get('unit_cost')))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Stock", stock_html), unsafe_allow_html=True)
        _render_inventory_pricing_guide_section(item)

    with tab_stock:
        placeholder_html("Stock History will connect to Supabase in a later phase.")

    with tab_transactions:
        _render_inventory_transactions_tab(item)

    with tab_pos:
        placeholder_html("Purchase Orders will connect to Supabase in a later phase.")

    with tab_vendors:
        placeholder_html("Vendors will connect to Supabase in a later phase.")

    with tab_notes:
        placeholder_html("Notes will connect to Supabase in a later phase.")

    with tab_attachments:
        placeholder_html("Attachments will connect to Supabase in a later phase.")


def _render_inventory_edit_form(item: dict) -> None:
    iid = str(item.get("id") or "")
    record_key = record_session_key(item, "id")
    if f"inv_edit_sku_{iid}" not in st.session_state:
        _seed_inventory_edit_form(item)

    render_edit_form_header("Edit Item")

    ic1, ic2 = st.columns(2)
    with ic1:
        st.text_input("SKU", key=f"inv_edit_sku_{iid}")
        st.text_input("Name", key=f"inv_edit_name_{iid}")
        st.selectbox("Category", lookup_options("inventory_categories"), key=f"inv_edit_cat_{iid}")
        st.selectbox("Status", lookup_options("inventory_statuses"), key=f"inv_edit_status_{iid}")
    with ic2:
        st.text_input("Location", key=f"inv_edit_loc_{iid}")
        st.number_input("Qty on hand", key=f"inv_edit_qty_{iid}")
        st.number_input("Unit cost", key=f"inv_edit_cost_{iid}")

    st.file_uploader(
        "Upload item image",
        type=["png", "jpg", "jpeg", "webp"],
        key=f"inv_edit_image_{iid}",
    )
    st.caption("PNG, JPG, JPEG, or WEBP. Image is saved when you click Save Changes.")

    cancelled, saved = render_save_cancel_actions(
        module=_MODULE,
        record_key=record_key,
        cancel_key=f"inv_modal_cancel_{record_key}",
        save_key=f"inv_modal_save_{record_key}",
    )
    if cancelled:
        st.rerun()
    if saved and not is_demo_id(iid):
        result = update_inventory_item(
            iid,
            {
                "sku": st.session_state.get(f"inv_edit_sku_{iid}"),
                "name": st.session_state.get(f"inv_edit_name_{iid}"),
                "category": st.session_state.get(f"inv_edit_cat_{iid}"),
                "status": st.session_state.get(f"inv_edit_status_{iid}"),
                "location": st.session_state.get(f"inv_edit_loc_{iid}"),
                "qty_on_hand": st.session_state.get(f"inv_edit_qty_{iid}"),
                "unit_cost": st.session_state.get(f"inv_edit_cost_{iid}"),
                "reorder_point": item.get("reorder_point", 0),
            },
        )
        if not result.ok:
            st.error(result.error or "Could not save inventory item.")
            return

        uploaded_file = st.session_state.get(f"inv_edit_image_{iid}")
        if uploaded_file is not None:
            upload_result = upload_inventory_image(iid, uploaded_file, uploaded_by=_current_user_id())
            if not upload_result.ok:
                st.warning(upload_result.error or "Item saved, but image upload failed.")

        clear_inventory_cache()
        set_view_mode(_MODULE, record_key)
        st.success("Inventory item saved.")
        st.rerun()


def _render_inventory_actions_panel(item: dict) -> None:
    record_key = record_session_key(item, "id")
    if is_edit_mode(_MODULE, record_key):
        return
    iid = str(item.get("id") or "").strip()
    if not iid or is_demo_id(iid):
        return

    def _after_action() -> None:
        _clear_inventory_modal()

    render_inventory_action_buttons(item, on_deactivate=_after_action, on_delete=_after_action)


def render_inventory_detail_dialog(item: dict) -> None:
    record_key = record_session_key(item, "id")
    title = str(item.get("name") or item.get("sku") or "")
    subtitle = str(item.get("sku") or "")
    status = str(item.get("status") or "")

    render_modal_shell()
    render_modal_header(title=title, subtitle=subtitle, status=status)
    render_modal_edit_button(
        module=_MODULE,
        record_key=record_key,
        key_prefix=f"inv_modal_{record_key}",
    )
    render_modal_meta_grid(
        [
            ("SKU", item.get("sku")),
            ("On Hand", int(item.get("qty_on_hand") or 0)),
            ("Location", item.get("location")),
            ("Unit Cost", fmt_currency(item.get("unit_cost"))),
        ]
    )

    if is_edit_mode(_MODULE, record_key) and not is_demo_id(str(item.get("id") or "")):
        _render_inventory_edit_form(item)
    else:
        _render_inventory_actions_panel(item)
        _render_inventory_detail_tabs(item)


@st.dialog("Inventory Item Details", width="large", on_dismiss=_clear_inventory_modal)
def _show_inventory_detail_modal() -> None:
    item = get_modal_record(
        cache_key=_CACHE_KEY,
        modal_key=_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not item:
        render_missing_record(_clear_inventory_modal, close_key="inv_modal_missing_close")
        return
    render_inventory_detail_dialog(item)


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("inventory"):
        return
    inject_inventory_module_css()
    st.markdown(
        '<span class="ips-inventory-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    rows = load_inventory()
    if not st.session_state.get("_inv_qr_tokens_seeded"):
        ensure_inventory_qr_tokens(rows)
        st.session_state["_inv_qr_tokens_seeded"] = True
        rows = load_inventory()
    filter_options = build_filter_options(rows, _COLUMN_FILTER_SPECS)

    def _inv_export() -> None:
        st.button("Export", key="inv_export", use_container_width=True)

    def _inv_new() -> None:
        if st.button("+ New Item", key="inv_new", type="primary", use_container_width=True):
            st.session_state["ips_inv_form"] = True

    render_page_brand_header(
        "Inventory",
        "Track and manage all inventory items and stock levels.",
        actions=[_inv_export, _inv_new],
    )

    if st.session_state.get("ips_inv_form"):
        with st.expander("New Item", expanded=True):
            st.text_input("SKU", key="inv_new_sku")
            st.text_input("Item name", key="inv_new_name")
            st.selectbox("Category", lookup_options("inventory_categories"), key="inv_new_cat")
            st.selectbox("Status", lookup_options("inventory_statuses"), key="inv_new_status")
            st.file_uploader(
                "Upload item image",
                type=["png", "jpg", "jpeg", "webp"],
                key="inv_new_image",
            )
            if st.button("Save item", key="inv_save_new", type="primary"):
                try:
                    from app.services.inventory_service import save_inventory_item
                except ImportError:
                    from services.inventory_service import save_inventory_item  # type: ignore
                result = save_inventory_item(
                    {
                        "sku": st.session_state.get("inv_new_sku"),
                        "name": st.session_state.get("inv_new_name"),
                        "category": st.session_state.get("inv_new_cat"),
                        "status": st.session_state.get("inv_new_status"),
                        "reorder_point": 0,
                        "qty_on_hand": 0,
                    }
                )
                if not result.ok:
                    st.error(result.error or "Could not save inventory item.")
                else:
                    new_id = ""
                    if isinstance(result.data, dict):
                        new_id = str(result.data.get("id") or "").strip()
                    uploaded_file = st.session_state.get("inv_new_image")
                    if uploaded_file is not None and new_id and not is_demo_id(new_id):
                        upload_result = upload_inventory_image(
                            new_id,
                            uploaded_file,
                            uploaded_by=_current_user_id(),
                        )
                        if not upload_result.ok:
                            st.warning(upload_result.error or "Item saved, but image upload failed.")
                    clear_inventory_cache()
                    st.session_state.pop("ips_inv_form", None)
                    st.success("Inventory item saved.")
                    st.rerun()

    def _filters() -> None:
        c1, c2 = st.columns([5, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search inventory...",
                key="inv_search",
                label_visibility="collapsed",
            )
        with c2:
            if st.button("Clear", key="inv_clear", use_container_width=True):
                clear_table_filters(
                    _TABLE_KEY,
                    _FILTER_FIELDS,
                    extra_keys=["inv_search"],
                )
                _clear_inventory_selection(st.session_state.get(_ALL_INVENTORY_IDS_KEY))
                st.rerun()

    layout_filter_bar(_filters)

    filtered = _filter_rows(
        rows,
        q=str(st.session_state.get("inv_search") or "").strip(),
    )

    st.caption(f"{len(filtered)} item(s)")

    build_modal_cache(filtered, cache_key=_CACHE_KEY)
    _render_custom_inventory_table(filtered, filter_options=filter_options)

    selected_inventory_id = st.session_state.get(SELECTED_INVENTORY_KEY)
    if selected_inventory_id and st.session_state.get(SHOW_INVENTORY_MODAL_KEY):
        _show_inventory_detail_modal()
