"""Inventory module (Phase 2B)."""

from __future__ import annotations

import html
from dataclasses import dataclass

import streamlit as st

from app.components.inventory_actions import render_inventory_action_buttons
from app.components.inventory_directory_table import inventory_detail_query_key
from app.components.inventory_detail_tabs import (
    inventory_detail_active_tab_key,
    reset_inventory_detail_tab,
    set_inventory_detail_tab_from_query,
)
from app.components.inventory_list_table import (
    INVENTORY_TABLE_LAST_ACTION_KEY,
    build_inventory_html_table,
    inventory_category,
    inventory_description,
    inventory_location,
    inventory_vendor,
    normalize_inventory_status,
    render_inventory_table_bridge_legacy,
    render_inventory_table_open_buttons,
)
from app.components.inventory_page_layout import (
    close_inventory_filter_bar_shell,
    inject_inventory_page_layout_css,
    render_inventory_filter_bar_shell,
)
from app.components.inventory_pricing_guide_actions import render_inventory_pricing_guide_actions
from app.components.item_photo_manager import render_item_photo_manager
from app.components.layout import render_filter_bar as layout_filter_bar
from app.components.table_filters import (
    apply_column_filters,
    build_filter_options,
    clear_table_filters,
    render_table_header_cell,
)
from app.components.table_pagination import (
    pagination_meta,
    render_table_pagination_footer,
    render_table_pagination_header,
    reset_table_page,
)
from app.services.inventory_detail_service import (
    get_inventory_item_detail,
    get_item_from_modal_cache,
    put_item_in_modal_cache,
)
from app.services.inventory_directory_service import (
    build_export_request,
    clear_prepared_export_bytes,
    count_inventory_needing_reorder,
    list_inventory_export_rows,
    list_inventory_page,
)
from app.components.qr_scan_history_ui import inject_qr_scan_history_css, render_qr_scan_history_table
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
    show_modal_if_pending,
    status_pill_html,
)
from app.pages._core._data import load_recent_qr_scans, lookup_options
from app.pages._core._crud import is_demo_id
from app.pages._core._session import select_key
from app.services.inventory_display_helpers import (
    inventory_qr_png_bytes,
    resolve_inventory_sku,
)
from app.services.inventory_images import (
    clear_inventory_image,
    inventory_display_record,
    inventory_image_is_inherited,
    upload_inventory_image as upload_inventory_image_file,
)
from app.services.item_images import ITEM_IMAGE_UPLOAD_TYPES
from app.services.inventory_service import (
    clear_inventory_cache,
    generate_inventory_qr_value,
    get_inventory_transactions,
    update_inventory_item,
    upload_inventory_image,
)
from app.services.catalog_stock_policy_service import (
    INVENTORY_VIEW_FILTERS,
    load_enriched_inventory_rows,
    inventory_needs_reorder,
    passes_inventory_view_filter,
)
from app.styles import inject_inventory_module_css
from app.ui.streamlit_perf import fragment, fragment_rerun
from app.utils.formatting import fmt_currency, fmt_date
from app.utils.inventory_quantity import format_inventory_quantity, inventory_qty_input_kwargs
from app.utils.phone_helpers import format_phone_display
from app.utils.field_context import (
    FIELD_EXPANDED_INVENTORY_KEY,
    clear_field_expanded,
    field_expanded_id,
    inject_field_row_expand_css,
    is_field_context,
    render_field_scan_bar,
    toggle_field_expanded,
)
_SEL = select_key("inventory")
_MODAL_KEY = "ips_inventory_detail_modal_id"
_CACHE_KEY = "_ips_inventory_modal_by_id"
_MODULE = "inventory"
SELECTED_INVENTORY_KEY = "selected_inventory_id"
SHOW_INVENTORY_MODAL_KEY = "show_inventory_detail_modal"
_INVENTORY_DETAIL_QUERY_KEY = inventory_detail_query_key()
_INVENTORY_DETAIL_QUERY_ERROR_KEY = "_ips_inventory_detail_query_error"
_INVENTORY_TAB_QUERY_KEY = "inventory_tab"
_INVENTORY_MAIN_TAB_KEY = "ips_inventory_main_tab"
_INVENTORY_PHOTO_MANAGE_PREFIX = "ips_inventory_photo_manage_"
_ALL_INVENTORY_IDS_KEY = "_ips_inventory_visible_ids"
_TABLE_KEY = "inventory_list"
_EXPORT_CACHE_KEY = "inv_label_export_cache_key"
_EXPORT_ZIP_BYTES_KEY = "inv_label_export_zip_bytes"
_EXPORT_CSV_BYTES_KEY = "inv_label_export_csv_bytes"
_EXPORT_COUNT_KEY = "inv_label_export_item_count"
_INVENTORY_FILTER_SPECS: list[tuple[str, str]] = [
    ("CATEGORY", "category"),
    ("LOCATION", "location"),
    ("STATUS", "status"),
    ("VENDOR", "vendor"),
]
_FILTER_FIELDS = ["category", "location", "status", "vendor"]
_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("category", lambda r: inventory_category(r)),
    ("location", lambda r: inventory_location(r)),
    ("status", lambda r: normalize_inventory_status(r.get("status"))),
    ("vendor", lambda r: inventory_vendor(r)),
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


def _inventory_sku(row: dict) -> str:
    return resolve_inventory_sku(row)


def _inventory_item_number(row: dict) -> str:
    return _inventory_sku(row)


def _inventory_description(row: dict) -> str:
    return inventory_description(row)


def _inventory_category(row: dict) -> str:
    return inventory_category(row)


def _inventory_location(row: dict) -> str:
    return inventory_location(row)


def _inventory_vendor(row: dict) -> str:
    return inventory_vendor(row)


def _inventory_unit(row: dict) -> str:
    return str(row.get("unit") or "").strip() or "—"


def _inventory_qty(row: dict) -> str:
    unit = _inventory_unit(row)
    if unit and unit != "—":
        return format_inventory_quantity(
            row.get("quantity_on_hand") or row.get("qty_on_hand") or row.get("quantity"),
            unit,
        )
    return format_inventory_quantity(row.get("quantity_on_hand") or row.get("qty_on_hand") or row.get("quantity"))


@dataclass(frozen=True)
class InventoryPermissions:
    role: str
    user_id: str
    user_name: str
    can_edit: bool
    can_delete: bool
    can_manage_pricing: bool
    can_issue_to_job: bool


def _inventory_permissions() -> InventoryPermissions:
    from app.auth import current_profile, effective_role
    from app.components.modal_delete import can_admin_mutate
    from app.services.inventory_service import can_manage_inventory_actions

    profile = current_profile() or {}
    role = str(effective_role() or "").strip()
    uid = str(profile.get("id") or "").strip()
    name = str(profile.get("name") or profile.get("full_name") or "").strip()
    can_edit = can_manage_inventory_actions()
    return InventoryPermissions(
        role=role,
        user_id=uid,
        user_name=name,
        can_edit=can_edit,
        can_delete=can_admin_mutate(),
        can_manage_pricing=can_edit,
        can_issue_to_job=can_edit,
    )


def _inventory_photo_manage_key(item_id: str) -> str:
    return f"{_INVENTORY_PHOTO_MANAGE_PREFIX}{str(item_id or '').strip() or 'item'}"


def _current_user_id() -> str | None:
    perms = _inventory_permissions()
    return perms.user_id or None


def _render_inventory_photo_manager(item: dict) -> None:
    iid = str(item.get("id") or "").strip()
    record_key = record_session_key(item, "id")
    display = inventory_display_record(item)
    render_item_photo_manager(
        item,
        record_id=iid,
        session_prefix=f"inv_photo_{record_key}",
        image_css_class="ips-inventory-detail-image",
        upload_image=upload_inventory_image_file,
        clear_image=clear_inventory_image,
        uploaded_by=_current_user_id(),
        cache_key=_CACHE_KEY,
        on_change=clear_inventory_cache,
        readonly=is_demo_id(iid),
        preview_record=display,
    )
    if inventory_image_is_inherited(item):
        st.caption("Photo from linked Pricing Guide or asset record.")


def _render_inventory_detail_image(item: dict, *, manage_photo: bool = False) -> None:
    iid = str(item.get("id") or "").strip()
    manage_key = _inventory_photo_manage_key(iid)
    if manage_photo or st.session_state.get(manage_key):
        _render_inventory_photo_manager(item)
        if not manage_photo and st.button("Hide photo tools", key=f"inv_photo_hide_{iid}"):
            st.session_state.pop(manage_key, None)
            st.rerun()
        return
    from app.services.inventory_images import inventory_thumbnail_html

    st.markdown(inventory_thumbnail_html(item), unsafe_allow_html=True)
    if st.button("Manage Photo", key=f"inv_photo_manage_{iid}", use_container_width=True):
        st.session_state[manage_key] = True
        st.rerun()


def _clear_inventory_selection(item_ids: list[str] | None = None) -> None:
    _ = item_ids
    st.session_state[SELECTED_INVENTORY_KEY] = None
    st.session_state[SHOW_INVENTORY_MODAL_KEY] = False


def _render_inventory_expand_panel(item: dict) -> None:
    iid = str(item.get("id") or "").strip()
    status = str(item.get("status") or "")
    stock_html = (
        f'<div class="ips-detail-grid">'
        f"{detail_field_html('SKU', item.get('sku'))}"
        f"{detail_field_html('Description', _inventory_description(item))}"
        f"{detail_field_html('Location', item.get('location'))}"
        f'{detail_field_html("Status", status, html_value=status_pill_html(status))}'
        f"{detail_field_html('Qty On Hand', _inventory_qty(item))}"
        f"{detail_field_html('Unit', _inventory_unit(item))}"
        f"{detail_field_html('Reorder Point', format_inventory_quantity(item.get('reorder_point'), _inventory_unit(item)))}"
        f"</div>"
    )
    st.markdown(dialog_card_html("Stock at a glance", stock_html), unsafe_allow_html=True)
    if st.button("Full item details", key=f"inv_full_modal_{iid}", use_container_width=True):
        _open_inventory_modal(iid, item)
        st.rerun()


def _render_inventory_table_column_filters(
    *,
    filter_options: dict[str, list[str]],
) -> None:
    if not _INVENTORY_FILTER_SPECS:
        return
    st.markdown('<div class="ips-inventory-table-filter-toolbar">', unsafe_allow_html=True)
    cols = st.columns(len(_INVENTORY_FILTER_SPECS), gap="small")
    for col, (label, field) in zip(cols, _INVENTORY_FILTER_SPECS):
        with col:
            render_table_header_cell(
                label,
                table_key=_TABLE_KEY,
                filter_field=field,
                filter_options=filter_options.get(field, []),
                base_class="ips-inventory-filter-toolbar-cell",
            )
    st.markdown("</div>", unsafe_allow_html=True)


def _on_inventory_table_expand(item_id: str, item: dict) -> None:
    toggle_field_expanded(FIELD_EXPANDED_INVENTORY_KEY, item_id)


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

    items_by_id = {
        str(i.get("id") or "").strip(): i
        for i in filtered
        if str(i.get("id") or "").strip()
    }
    field_mode = is_field_context()
    expanded_item_id = str(field_expanded_id(FIELD_EXPANDED_INVENTORY_KEY) or "").strip() if field_mode else ""

    with st.container(key="inventory_table_wrap"):
        _render_inventory_table_column_filters(filter_options=filter_options)
        st.markdown(
            build_inventory_html_table(
                filtered,
                field_mode=field_mode,
                expanded_item_id=expanded_item_id,
            ),
            unsafe_allow_html=True,
        )
        if field_mode:
            render_inventory_table_open_buttons(
                filtered,
                open_item_fn=_prepare_inventory_table_open,
            )
            render_inventory_table_bridge_legacy(
                items_by_id,
                component_key="ips_inventory_list_bridge",
                hook_key="ipsInvList::action",
                open_item_fn=_open_inventory_table_item,
                on_expand_fn=_on_inventory_table_expand,
                field_mode=True,
            )

        if field_mode and expanded_item_id and expanded_item_id in items_by_id:
            expanded_item = items_by_id[expanded_item_id]
            st.markdown('<div class="ips-field-row-expand">', unsafe_allow_html=True)
            _render_inventory_expand_panel(expanded_item)
            st.markdown("</div>", unsafe_allow_html=True)

    return all_item_ids


def _filter_rows(
    rows: list[dict],
    *,
    q: str,
    stock_view: str,
) -> list[dict]:
    out = rows
    out = [r for r in out if passes_inventory_view_filter(r, view=stock_view)]
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
            or ql in normalize_inventory_status(r.get("status")).lower()
            or ql in str(r.get("stock_policy_label") or "").lower()
        ]
    return apply_column_filters(out, _TABLE_KEY, _COLUMN_FILTER_SPECS)


def _clear_inventory_modal() -> None:
    item_ids = st.session_state.get(_ALL_INVENTORY_IDS_KEY) or []
    _clear_inventory_selection([str(iid) for iid in item_ids])
    st.session_state.pop(INVENTORY_TABLE_LAST_ACTION_KEY, None)
    clear_edit_modes(_MODULE)
    clear_record_modal(
        table_key="inventory_list",
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )
    if _INVENTORY_DETAIL_QUERY_KEY in st.query_params:
        del st.query_params[_INVENTORY_DETAIL_QUERY_KEY]
    if _INVENTORY_TAB_QUERY_KEY in st.query_params:
        del st.query_params[_INVENTORY_TAB_QUERY_KEY]


def _inventory_detail_pending() -> bool:
    return bool(
        st.session_state.get(SHOW_INVENTORY_MODAL_KEY)
        or str(st.session_state.get(_MODAL_KEY) or "").strip()
    )


def _capture_inventory_detail_query() -> None:
    from app.perf_debug import perf_span

    with perf_span("inventory.detail_lookup"):
        requested_id = str(st.query_params.get(_INVENTORY_DETAIL_QUERY_KEY) or "").strip()
        if not requested_id:
            return
        current_modal_id = str(st.session_state.get(_MODAL_KEY) or "").strip()
        if requested_id == current_modal_id and st.session_state.get(SHOW_INVENTORY_MODAL_KEY):
            tab_focus = str(st.query_params.get(_INVENTORY_TAB_QUERY_KEY) or "").strip()
            if tab_focus:
                set_inventory_detail_tab_from_query(tab_focus)
            return
        item = get_inventory_item_detail(requested_id)
        if not item:
            st.session_state[_INVENTORY_DETAIL_QUERY_ERROR_KEY] = requested_id
            if _INVENTORY_DETAIL_QUERY_KEY in st.query_params:
                del st.query_params[_INVENTORY_DETAIL_QUERY_KEY]
            if _INVENTORY_TAB_QUERY_KEY in st.query_params:
                del st.query_params[_INVENTORY_TAB_QUERY_KEY]
            return
        tab_focus = str(st.query_params.get(_INVENTORY_TAB_QUERY_KEY) or "").strip()
        _open_inventory_modal(requested_id, item)
        reset_inventory_detail_tab(default="Overview")
        if tab_focus:
            set_inventory_detail_tab_from_query(tab_focus)


def _show_inventory_detail_query_error_if_any() -> None:
    if st.session_state.pop(_INVENTORY_DETAIL_QUERY_ERROR_KEY, None):
        st.warning("The selected inventory item could not be found.")


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


def _prepare_inventory_table_open(item_id: str, item: dict | None = None) -> None:
    """Set inventory detail modal state without triggering a rerun."""
    _open_inventory_modal(item_id, item)


def _open_inventory_table_item(item_id: str, item: dict | None = None) -> None:
    """Bridge handler during render — modal state plus full app rerun."""
    _prepare_inventory_table_open(item_id, item)


def _inventory_select_options(slug: str, current: str) -> list[str]:
    """Lookup dropdown values with constants fallback and the record's current value."""
    opts = list(lookup_options(slug))
    if not opts:
        from app.utils.constants import INVENTORY_CATEGORIES, INVENTORY_STATUSES
        opts = list(INVENTORY_CATEGORIES if slug == "inventory_categories" else INVENTORY_STATUSES)
    cur = str(current or "").strip()
    if cur and cur not in opts and cur != "—":
        opts = [cur, *opts]
    return opts


def _seed_inventory_edit_form(item: dict) -> None:
    from app.utils.inventory_quantity import read_inventory_quantity

    iid = str(item.get("id") or "")
    st.session_state[f"inv_edit_sku_{iid}"] = str(item.get("sku") or "")
    st.session_state[f"inv_edit_name_{iid}"] = str(item.get("name") or "")
    st.session_state[f"inv_edit_cat_{iid}"] = str(item.get("category") or "")
    st.session_state[f"inv_edit_status_{iid}"] = str(item.get("status") or "")
    st.session_state[f"inv_edit_loc_{iid}"] = str(item.get("location") or "")
    st.session_state[f"inv_edit_qty_{iid}"] = read_inventory_quantity(
        item, "qty_on_hand", "quantity_on_hand", "quantity"
    )
    st.session_state[f"inv_edit_cost_{iid}"] = float(item.get("unit_cost") or 0)


def _render_inventory_detail_overview(item: dict) -> None:
    from app.components.inventory_qr_panel import render_inventory_qr_panel
    from app.utils.inventory_quantity import read_inventory_quantity

    status = str(item.get("status") or "")
    unit = _inventory_unit(item)
    on_hand = read_inventory_quantity(item, "qty_on_hand", "quantity_on_hand", "quantity")
    allocated = read_inventory_quantity(item, "quantity_allocated")
    media1, media2, details = st.columns([1.1, 0.9, 2.0])
    with media1:
        st.markdown("**Item Image**")
        _render_inventory_detail_image(item)
    with media2:
        render_inventory_qr_panel(item)
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
        f"{detail_field_html('Qty On Hand', format_inventory_quantity(on_hand, unit))}"
        f"{detail_field_html('Allocated to Jobs', format_inventory_quantity(allocated, unit))}"
        f"{detail_field_html('Reorder Point', format_inventory_quantity(item.get('reorder_point'), unit))}"
        f"{detail_field_html('Stock policy', item.get('stock_policy_label') or 'Not stocked')}"
        f"{detail_field_html('Needs reorder', 'Yes' if inventory_needs_reorder(item) else 'No')}"
        f"{detail_field_html('Unit', unit)}"
        f"{detail_field_html('Unit Cost', fmt_currency(item.get('unit_cost')))}"
        f"</div>"
    )
    st.markdown(dialog_card_html("Stock", stock_html), unsafe_allow_html=True)


def _render_inventory_transactions_tab(item: dict) -> None:
    from app.components.inventory_transactions_panel import render_inventory_transactions_panel

    perms = _inventory_permissions()
    render_inventory_transactions_panel(item, permissions_user_id=perms.user_id or None)


def _render_inventory_detail_tabs(item: dict) -> None:
    from app.components.inventory_detail_tabs import render_inventory_detail_tabs

    render_inventory_detail_tabs(item)


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
        st.selectbox(
            "Category",
            _inventory_select_options("inventory_categories", str(item.get("category") or "")),
            key=f"inv_edit_cat_{iid}",
        )
        st.selectbox(
            "Status",
            _inventory_select_options("inventory_statuses", str(item.get("status") or "")),
            key=f"inv_edit_status_{iid}",
        )
    with ic2:
        st.text_input("Location", key=f"inv_edit_loc_{iid}")
        st.number_input(
            "Qty on hand",
            key=f"inv_edit_qty_{iid}",
            **inventory_qty_input_kwargs(
                min_value=0,
                value=int(st.session_state.get(f"inv_edit_qty_{iid}") or 0),
            ),
        )
        st.number_input("Unit cost", key=f"inv_edit_cost_{iid}")

    st.markdown("**Item Photo**")
    _render_inventory_photo_manager(item)

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

    render_inventory_action_buttons(
        item,
        on_deactivate=_after_action,
        on_delete=_after_action,
        on_remove_keep_pricing=_after_action,
    )
    render_inventory_pricing_guide_actions(item)


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
            ("On Hand", format_inventory_quantity(item.get("qty_on_hand"), _inventory_unit(item))),
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
    sel = str(
        st.session_state.get(_MODAL_KEY)
        or st.session_state.get(_SEL)
        or st.session_state.get(SELECTED_INVENTORY_KEY)
        or ""
    ).strip()
    item = get_item_from_modal_cache(sel) if sel else None
    if not item:
        render_missing_record(_clear_inventory_modal, close_key="inv_modal_missing_close")
        return
    render_inventory_detail_dialog(item)



@fragment
def _render_inventory_items_fragment() -> None:
    """Inventory items tab — filters and table with local reruns."""
    from app.perf_debug import perf_span

    def _filters() -> None:
        c1, c2, c3 = st.columns([3.2, 2.2, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search SKU, name, category, vendor…",
                key="inv_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "Stock view",
                list(INVENTORY_VIEW_FILTERS),
                key="inv_stock_view",
                label_visibility="collapsed",
            )
        with c3:
            if st.button("Clear", key="inv_clear", use_container_width=True):
                clear_table_filters(
                    _TABLE_KEY,
                    _FILTER_FIELDS,
                    extra_keys=["inv_search", "inv_stock_view"],
                )
                st.session_state["inv_stock_view"] = "In stock"
                reset_table_page(_TABLE_KEY)
                _clear_inventory_selection(st.session_state.get(_ALL_INVENTORY_IDS_KEY))
                clear_field_expanded(FIELD_EXPANDED_INVENTORY_KEY)
                fragment_rerun()

    search = str(st.session_state.get("inv_search") or "").strip()
    stock_view = str(st.session_state.get("inv_stock_view") or "In stock")
    page_num, page_size, _ = pagination_meta(0, _TABLE_KEY)

    with perf_span("inventory.list_query"):
        inv_page = list_inventory_page(
            search=search,
            stock_view=stock_view,
            page=page_num,
            page_size=page_size,
        )
    page_num, page_size, _ = pagination_meta(inv_page.total_count, _TABLE_KEY)
    if page_num != inv_page.page or page_size != inv_page.page_size:
        with perf_span("inventory.list_query"):
            inv_page = list_inventory_page(
                search=search,
                stock_view=stock_view,
                page=page_num,
                page_size=page_size,
            )

    filter_options = inv_page.filter_options
    page_rows = inv_page.rows
    _render_reorder_alert(inv_page.reorder_count)

    render_inventory_filter_bar_shell()
    layout_filter_bar(_filters)
    close_inventory_filter_bar_shell()

    render_table_pagination_header(inv_page.total_count, _TABLE_KEY, item_label="item")

    for row in page_rows:
        put_item_in_modal_cache(str(row.get("id") or "").strip(), row)
    selected_id = str(st.session_state.get(SELECTED_INVENTORY_KEY) or "").strip()
    if selected_id and st.session_state.get(SHOW_INVENTORY_MODAL_KEY):
        detail = get_inventory_item_detail(selected_id)
        if detail:
            put_item_in_modal_cache(selected_id, detail)

    with perf_span("inventory.table_html"):
        _render_custom_inventory_table(page_rows, filter_options=filter_options)

    render_table_pagination_footer(inv_page.total_count, _TABLE_KEY)


def _render_reorder_alert(reorder_count: int) -> None:
    if not reorder_count:
        return
    st.markdown(
        '<span class="ips-inventory-reorder-alert-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    msg_col, action_col = st.columns([5.6, 1.1], gap="small", vertical_alignment="center")
    with msg_col:
        st.info(
            f"{reorder_count} mandatory item(s) need reorder — use the Needs reorder view."
        )
    with action_col:
        if st.button("Needs reorder", key="inv_alert_needs_reorder", type="tertiary"):
            st.session_state["inv_stock_view"] = "Needs reorder"
            reset_table_page(_TABLE_KEY)
            st.rerun()


def _inv_export_header() -> None:
    from app.perf_debug import perf_span
    from app.services.inventory_qr_labels import (
        build_inventory_labels_csv,
        build_inventory_labels_zip,
        inventory_labels_csv_filename,
        inventory_labels_zip_filename,
    )

    search = str(st.session_state.get("inv_search") or "").strip()
    stock_view = str(st.session_state.get("inv_stock_view") or "In stock")
    export_req = build_export_request(search=search, stock_view=stock_view)
    export_cache_key = export_req.cache_key()

    if st.session_state.get(_EXPORT_CACHE_KEY) != export_cache_key:
        clear_prepared_export_bytes()

    zip_bytes = st.session_state.get(_EXPORT_ZIP_BYTES_KEY)
    csv_bytes = st.session_state.get(_EXPORT_CSV_BYTES_KEY)
    prepared = bool(zip_bytes and csv_bytes and st.session_state.get(_EXPORT_CACHE_KEY) == export_cache_key)

    if not prepared:
        if st.button("Prepare Label Export", key="inv_prepare_label_export"):
            with perf_span("inventory.export_query"):
                export_rows = list_inventory_export_rows(search=search, stock_view=stock_view)
            count = len(export_rows)
            if not count:
                st.warning("No items match the current filters.")
                return
            with st.spinner(f"Building labels for {count} item(s)…"):
                with perf_span("inventory.export_build"):
                    st.session_state[_EXPORT_ZIP_BYTES_KEY] = build_inventory_labels_zip(export_rows)
                    st.session_state[_EXPORT_CSV_BYTES_KEY] = build_inventory_labels_csv(export_rows).encode("utf-8")
                    st.session_state[_EXPORT_COUNT_KEY] = count
                    st.session_state[_EXPORT_CACHE_KEY] = export_cache_key
            st.rerun()
        return

    export_count = int(st.session_state.get(_EXPORT_COUNT_KEY) or 0)
    with st.popover("Label Export", help=f"{export_count} item(s) ready to download."):
        st.download_button(
            "Labels ZIP",
            data=zip_bytes,
            file_name=inventory_labels_zip_filename(item_count=export_count),
            mime="application/zip",
            key="inv_export_zip_hdr",
            use_container_width=True,
        )
        st.download_button(
            "Labels CSV",
            data=csv_bytes,
            file_name=inventory_labels_csv_filename(item_count=export_count),
            mime="text/csv",
            key="inv_export_csv_hdr",
            use_container_width=True,
        )
        if st.button("Rebuild export", key="inv_rebuild_label_export", use_container_width=True):
            clear_prepared_export_bytes()
            st.rerun()


def render() -> None:
    from app.pages._core._access import begin_module
    from app.components.tabs import render_tabs
    from app.perf_debug import perf_span

    if not begin_module("inventory"):
        return
    from app.navigation import INVENTORY_SCAN_EMBED_KEY

    if st.session_state.pop(INVENTORY_SCAN_EMBED_KEY, False):
        from app.pages.inventory_scan import render_inventory_scan_page

        render_inventory_scan_page()
        return

    with perf_span("inventory.page_shell"):
        inject_inventory_module_css()
        inject_inventory_page_layout_css()
        if is_field_context():
            inject_field_row_expand_css()
        st.markdown(
            '<span class="ips-inventory-page ips-page-shell-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        def _inventory_header_actions() -> None:
            st.markdown(
                '<span class="ips-inventory-page-header-actions ips-page-header-inline-actions" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            _inv_export_header()
            if st.button("+ New Item", key="inv_new", type="primary"):
                st.session_state["ips_inv_form"] = True

        from app.ui.page_header import render_page_header

        render_page_header(
            "Inventory",
            "Track and manage all inventory items and stock levels.",
            primary_action=_inventory_header_actions,
            primary_action_width=4.8,
        )

    _capture_inventory_detail_query()
    _show_inventory_detail_query_error_if_any()

    if _inventory_detail_pending():
        show_modal_if_pending(_MODAL_KEY, _show_inventory_detail_modal)
        return

    if is_field_context():
        render_field_scan_bar(("📦 Scan Stock", "scan_inventory"))

    if st.session_state.get("ips_inv_form"):
        with st.expander("New Item", expanded=True):
            st.text_input("SKU", key="inv_new_sku")
            st.text_input("Item name", key="inv_new_name")
            st.selectbox("Category", _inventory_select_options("inventory_categories", ""), key="inv_new_cat")
            st.selectbox("Status", _inventory_select_options("inventory_statuses", "In Stock"), key="inv_new_status")
            st.file_uploader(
                "Upload item image",
                type=list(ITEM_IMAGE_UPLOAD_TYPES),
                key="inv_new_image",
            )
            if st.button("Save item", key="inv_save_new", type="primary"):
                from app.services.inventory_service import save_inventory_item

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

    active_main_tab = render_tabs(
        ["Items", "QR Scan History"],
        session_key=_INVENTORY_MAIN_TAB_KEY,
        default="Items",
    )

    if active_main_tab == "Items":
        _render_inventory_items_fragment()
    else:
        with perf_span("inventory.qr_history"):
            inject_qr_scan_history_css()
            st.caption(
                "Recent inventory and tool QR scans — who scanned, what opened, and what action was recorded."
            )
            render_qr_scan_history_table(
                load_recent_qr_scans(limit=25)[0],
                empty_message="No QR scans recorded yet. Scans appear when materials or tools are used via QR.",
            )

    if _inventory_detail_pending():
        show_modal_if_pending(_MODAL_KEY, _show_inventory_detail_modal)
