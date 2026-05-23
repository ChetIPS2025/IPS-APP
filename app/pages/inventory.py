"""Inventory module (Phase 2B)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
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
    from app.pages._core._data import load_inventory, lookup_options, persist_inventory
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
    from app.styles import inject_inventory_module_css
    from app.utils.formatting import fmt_currency
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
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
    from pages._core._data import load_inventory, lookup_options, persist_inventory  # type: ignore
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from styles import inject_inventory_module_css  # type: ignore
    from utils.formatting import fmt_currency  # type: ignore

_SEL = select_key("inventory")
_MODAL_KEY = "ips_inventory_detail_modal_id"
_CACHE_KEY = "_ips_inventory_modal_by_id"
_MODULE = "inventory"
SELECTED_INVENTORY_KEY = "selected_inventory_id"
SHOW_INVENTORY_MODAL_KEY = "show_inventory_detail_modal"
_ALL_INVENTORY_IDS_KEY = "_ips_inventory_visible_ids"
_INV_COLS = [0.35, 1.2, 3.0, 1.5, 1.7, 1.1, 0.8, 1.0, 1.3, 1.6]
_INV_HEADERS = [
    "",
    "ITEM #",
    "DESCRIPTION",
    "CATEGORY",
    "LOCATION",
    "QTY ON HAND",
    "UNIT",
    "UNIT COST",
    "STATUS",
    "VENDOR",
]
_STATUS_FILTER_OPTS = ["All Statuses", "In Stock", "Low Stock", "Out of Stock", "On Order", "Discontinued"]

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


def _inventory_item_number(row: dict) -> str:
    for key in ("item_number", "item_no", "sku"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


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


def _render_custom_inventory_table(filtered: list[dict]) -> list[str]:
    if not filtered:
        st.info("No inventory items match your filters.")
        st.session_state[_ALL_INVENTORY_IDS_KEY] = []
        return []

    all_item_ids = [str(i.get("id") or "").strip() for i in filtered if str(i.get("id") or "").strip()]
    st.session_state[_ALL_INVENTORY_IDS_KEY] = all_item_ids

    with st.container(key="inventory_table_wrap"):
        st.markdown('<div class="ips-inventory-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_INV_COLS, gap="small", vertical_alignment="center")
        for col, label in zip(header_cols, _INV_HEADERS):
            with col:
                st.markdown(
                    f'<div class="ips-inventory-header-row ips-inventory-cell">{html.escape(label)}</div>',
                    unsafe_allow_html=True,
                )

        for item in filtered:
            iid = str(item.get("id") or "").strip()
            if not iid:
                continue

            item_no = _inventory_item_number(item)
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
                st.markdown(
                    f'<div class="ips-inventory-number">{html.escape(item_no)}</div>',
                    unsafe_allow_html=True,
                )

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
    category: str,
    location: str,
    status: str,
    vendor: str,
) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            r
            for r in out
            if ql in _inventory_item_number(r).lower()
            or ql in _inventory_description(r).lower()
            or ql in _inventory_category(r).lower()
            or ql in _inventory_location(r).lower()
            or ql in _inventory_vendor(r).lower()
            or ql in _normalize_inventory_status(r.get("status")).lower()
        ]
    if category and category != "All Categories":
        out = [r for r in out if _inventory_category(r) == category]
    if location and location != "All Locations":
        out = [r for r in out if _inventory_location(r) == location]
    if status and status != "All Statuses":
        out = [r for r in out if _normalize_inventory_status(r.get("status")) == status]
    if vendor and vendor != "All Vendors":
        out = [r for r in out if _inventory_vendor(r) == vendor]
    return out


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
        c1, c2 = st.columns(2)
        with c1:
            details_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('SKU', item.get('sku'))}"
                f"{detail_field_html('Name', item.get('name'))}"
                f"{detail_field_html('Category', item.get('category'))}"
                f'{detail_field_html("Status", status, html_value=status_pill_html(status))}'
                f"{detail_field_html('Location', item.get('location'))}"
                f"{detail_field_html('Department', item.get('department'))}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Item Details", details_html), unsafe_allow_html=True)
        with c2:
            stock_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Qty On Hand', int(item.get('qty_on_hand') or 0))}"
                f"{detail_field_html('Reorder Point', int(item.get('reorder_point') or 0))}"
                f"{detail_field_html('Unit Cost', fmt_currency(item.get('unit_cost')))}"
                f"{detail_field_html('Vendor', item.get('vendor'))}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Stock", stock_html), unsafe_allow_html=True)

    with tab_stock:
        placeholder_html("Stock History will connect to Supabase in a later phase.")

    with tab_transactions:
        placeholder_html("Transactions will connect to Supabase in a later phase.")

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

    cancelled, saved = render_save_cancel_actions(
        module=_MODULE,
        record_key=record_key,
        cancel_key=f"inv_modal_cancel_{record_key}",
        save_key=f"inv_modal_save_{record_key}",
    )
    if cancelled:
        st.rerun()
    if saved and not is_demo_id(iid):
        ok, msg = persist_inventory(
            {
                "sku": st.session_state.get(f"inv_edit_sku_{iid}"),
                "name": st.session_state.get(f"inv_edit_name_{iid}"),
                "category": st.session_state.get(f"inv_edit_cat_{iid}"),
                "status": st.session_state.get(f"inv_edit_status_{iid}"),
                "location": st.session_state.get(f"inv_edit_loc_{iid}"),
                "qty_on_hand": st.session_state.get(f"inv_edit_qty_{iid}"),
                "unit_cost": st.session_state.get(f"inv_edit_cost_{iid}"),
            },
            row_id=iid,
        )
        if apply_persist_feedback(ok, msg):
            set_view_mode(_MODULE, record_key)
            st.rerun()


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
    categories = sorted({_inventory_category(r) for r in rows if _inventory_category(r) != "—"})
    locations = sorted({_inventory_location(r) for r in rows if _inventory_location(r) != "—"})
    vendors = sorted({_inventory_vendor(r) for r in rows if _inventory_vendor(r) != "—"})

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Inventory", "Track and manage all inventory items and stock levels.")
    with act_r:
        exp_col, add_col = st.columns(2, gap="small")
        with exp_col:
            st.button("Export", key="inv_export", use_container_width=True)
        with add_col:
            if st.button("+ New Item", key="inv_new", type="primary", use_container_width=True):
                st.session_state["ips_inv_form"] = True

    if st.session_state.get("ips_inv_form"):
        with st.expander("New Item", expanded=True):
            st.text_input("SKU", key="inv_new_sku")
            st.text_input("Item name", key="inv_new_name")
            st.selectbox("Category", lookup_options("inventory_categories"), key="inv_new_cat")
            st.selectbox("Status", lookup_options("inventory_statuses"), key="inv_new_status")
            if st.button("Save item", key="inv_save_new", type="primary"):
                ok, msg = persist_inventory(
                    {
                        "sku": st.session_state.get("inv_new_sku"),
                        "name": st.session_state.get("inv_new_name"),
                        "category": st.session_state.get("inv_new_cat"),
                        "status": st.session_state.get("inv_new_status"),
                    }
                )
                if apply_persist_feedback(ok, msg, clear_keys=("ips_inv_form",)):
                    st.rerun()

    def _filters() -> None:
        c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1, 1, 1, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search inventory...",
                key="inv_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "Category",
                ["All Categories", *categories],
                key="inv_cat",
                label_visibility="collapsed",
            )
        with c3:
            st.selectbox(
                "Location",
                ["All Locations", *locations],
                key="inv_loc",
                label_visibility="collapsed",
            )
        with c4:
            st.selectbox(
                "Status",
                _STATUS_FILTER_OPTS,
                key="inv_status",
                label_visibility="collapsed",
            )
        with c5:
            st.selectbox(
                "Vendor",
                ["All Vendors", *vendors],
                key="inv_vendor",
                label_visibility="collapsed",
            )
        with c6:
            if st.button("Clear", key="inv_clear", use_container_width=True):
                st.session_state["inv_search"] = ""
                st.session_state["inv_cat"] = "All Categories"
                st.session_state["inv_loc"] = "All Locations"
                st.session_state["inv_status"] = "All Statuses"
                st.session_state["inv_vendor"] = "All Vendors"
                st.rerun()

    layout_filter_bar(_filters)

    filtered = _filter_rows(
        rows,
        q=str(st.session_state.get("inv_search") or "").strip(),
        category=str(st.session_state.get("inv_cat") or "All Categories"),
        location=str(st.session_state.get("inv_loc") or "All Locations"),
        status=str(st.session_state.get("inv_status") or "All Statuses"),
        vendor=str(st.session_state.get("inv_vendor") or "All Vendors"),
    )

    st.caption(f"{len(filtered)} item(s)")

    build_modal_cache(filtered, cache_key=_CACHE_KEY)
    _render_custom_inventory_table(filtered)

    selected_inventory_id = st.session_state.get(SELECTED_INVENTORY_KEY)
    if selected_inventory_id and st.session_state.get(SHOW_INVENTORY_MODAL_KEY):
        _show_inventory_detail_modal()
