"""Inventory module (Phase 2B)."""

from __future__ import annotations

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.clickable_table import render_clickable_table
    from app.components.record_modal import (
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_modal_actions,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_view_mode,
        show_modal_if_pending,
        status_pill_html,
    )
    from app.pages._core._data import load_inventory, lookup_options, persist_inventory
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
    from app.styles import inject_global_css
    from app.utils.constants import INVENTORY_STATUSES
    from app.utils.formatting import fmt_currency
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.clickable_table import render_clickable_table  # type: ignore
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_modal_actions,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_view_mode,
        show_modal_if_pending,
        status_pill_html,
    )
    from pages._core._data import load_inventory, lookup_options, persist_inventory  # type: ignore
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.constants import INVENTORY_STATUSES  # type: ignore
    from utils.formatting import fmt_currency  # type: ignore

_SEL = select_key("inventory")
_MODAL_KEY = "ips_inventory_detail_modal_id"
_CACHE_KEY = "_ips_inventory_modal_by_id"
_MODULE = "inventory"

_INV_TABS = [
    "Overview",
    "Stock History",
    "Transactions",
    "Purchase Orders",
    "Vendors",
    "Notes",
    "Attachments",
]


def _filter_rows(rows: list[dict], *, q: str, category: str, location: str, status: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            r
            for r in out
            if ql in str(r.get("sku", "")).lower() or ql in str(r.get("name", "")).lower()
        ]
    if category and category != "All Categories":
        out = [r for r in out if str(r.get("category", "")) == category]
    if location and location != "All Locations":
        out = [r for r in out if str(r.get("location", "")) == location]
    if status and status != "All Statuses":
        out = [r for r in out if str(r.get("status", "")) == status]
    return out


def _clear_inventory_modal() -> None:
    clear_record_modal(
        table_key="inventory_list",
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _open_inventory_modal(record_id: str, record: dict | None) -> None:
    open_record_modal(
        record_id,
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
    render_modal_actions(
        module=_MODULE,
        record_key=record_key,
        record=item,
        on_close=_clear_inventory_modal,
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
    rows = load_inventory()
    categories = sorted({str(r.get("category") or "") for r in rows if r.get("category")})
    locations = sorted({str(r.get("location") or "") for r in rows if r.get("location")})

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Inventory", "Track stocked materials, supplies, and warehouse levels.")
    with act_r:
        st.button("Export", key="inv_export", use_container_width=True)
        if st.button("+ New Item", key="inv_new", type="primary", use_container_width=True):
            st.session_state["ips_inv_form"] = True

    if st.session_state.get("ips_inv_form"):
        with st.expander("New inventory item", expanded=True):
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
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 0.7])
        with c1:
            st.text_input("Search", placeholder="Search inventory…", key="inv_search", label_visibility="collapsed")
        with c2:
            st.selectbox("Category", ["All Categories", *categories], key="inv_cat", label_visibility="collapsed")
        with c3:
            st.selectbox("Location", ["All Locations", *locations], key="inv_loc", label_visibility="collapsed")
        with c4:
            st.selectbox(
                "Status",
                ["All Statuses", *lookup_options("inventory_statuses")],
                key="inv_status",
                label_visibility="collapsed",
            )
        with c5:
            if st.button("Clear", key="inv_clear", use_container_width=True):
                for k in ("inv_search",):
                    st.session_state[k] = ""
                st.session_state["inv_cat"] = "All Categories"
                st.session_state["inv_loc"] = "All Locations"
                st.session_state["inv_status"] = "All Statuses"
                st.rerun()

    layout_filter_bar(_filters)

    filtered = _filter_rows(
        rows,
        q=str(st.session_state.get("inv_search") or "").strip(),
        category=str(st.session_state.get("inv_cat") or "All Categories"),
        location=str(st.session_state.get("inv_loc") or "All Locations"),
        status=str(st.session_state.get("inv_status") or "All Statuses"),
    )

    selected_id = str(st.session_state.get(_SEL) or "")
    if selected_id and not any(str(r.get("id")) == selected_id for r in filtered):
        st.session_state.pop(_SEL, None)
        st.session_state.pop(_MODAL_KEY, None)
        selected_id = ""

    def _display_cell(field: str, row: dict) -> str:
        if field == "unit_cost":
            return fmt_currency(row.get("unit_cost"))
        val = row.get(field)
        return str(val).strip() if val is not None and str(val).strip() else "—"

    build_modal_cache(filtered, cache_key=_CACHE_KEY)

    render_clickable_table(
        filtered,
        [
            ("sku", "SKU"),
            ("name", "ITEM NAME"),
            ("category", "CATEGORY"),
            ("location", "LOCATION"),
            ("department", "DEPARTMENT"),
            ("status", "STATUS"),
            ("qty_on_hand", "QTY"),
            ("unit_cost", "UNIT COST"),
        ],
        "inventory_list",
        row_id_key="id",
        session_select_key=_SEL,
        format_cell=_display_cell,
        click_caption=f"{len(filtered)} item(s) · Click a row to open details.",
        on_row_selected=_open_inventory_modal,
    )

    show_modal_if_pending(_MODAL_KEY, _show_inventory_detail_modal)
