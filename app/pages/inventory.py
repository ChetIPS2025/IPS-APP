"""Inventory module (Phase 2B)."""

from __future__ import annotations

import base64
import html

import streamlit as st

from app.components.inventory_actions import render_inventory_action_buttons
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
from app.components.headers import render_page_brand_header
from app.components.layout import render_filter_bar as layout_filter_bar
from app.components.table_filters import (
    apply_column_filters,
    build_filter_options,
    clear_table_filters,
    render_table_header_cell,
)
from app.components.table_pagination import (
    paginate_rows,
    render_table_pagination_footer,
    render_table_pagination_header,
    reset_table_page,
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
from app.pages._core._data import load_inventory, load_recent_qr_scans, lookup_options
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
    get_inventory_image_url,
    get_inventory_transactions,
    update_inventory_item,
    upload_inventory_image,
)
from app.services.catalog_stock_policy_service import (
    INVENTORY_VIEW_FILTERS,
    enrich_inventory_rows,
    load_enriched_inventory_rows,
    inventory_needs_reorder,
    passes_inventory_view_filter,
)
from app.styles import inject_inventory_module_css
from app.ui.streamlit_perf import fragment, fragment_rerun, ips_app_rerun
from app.utils.formatting import fmt_currency, fmt_date
from app.utils.inventory_quantity import format_inventory_quantity, inventory_qty_input_kwargs
from app.utils.phone_helpers import format_phone_display
from app.utils.field_context import (
    FIELD_EXPANDED_INVENTORY_KEY,
    clear_field_expanded,
    field_expanded_id,
    inject_field_row_expand_css,
    is_field_context,
    is_field_mode,
    render_field_scan_bar,
    toggle_field_expanded,
)
_SEL = select_key("inventory")
_MODAL_KEY = "ips_inventory_detail_modal_id"
_CACHE_KEY = "_ips_inventory_modal_by_id"
_MODULE = "inventory"
SELECTED_INVENTORY_KEY = "selected_inventory_id"
SHOW_INVENTORY_MODAL_KEY = "show_inventory_detail_modal"
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


def _current_user_id() -> str | None:
    from app.auth import current_profile
    uid = str((current_profile() or {}).get("id") or "").strip()
    return uid or None


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


def _render_inventory_detail_image(item: dict) -> None:
    _render_inventory_photo_manager(item)


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
        f"{detail_field_html('Qty On Hand', int(item.get('qty_on_hand') or 0))}"
        f"{detail_field_html('Unit', _inventory_unit(item))}"
        f"{detail_field_html('Reorder Point', int(item.get('reorder_point') or 0))}"
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
        render_inventory_table_open_buttons(
            filtered,
            open_item_fn=_open_inventory_table_item,
        )
        render_inventory_table_bridge_legacy(
            items_by_id,
            component_key="ips_inventory_list_bridge",
            hook_key="ipsInvList::action",
            open_item_fn=_open_inventory_table_item,
            on_expand_fn=_on_inventory_table_expand if field_mode else None,
            field_mode=field_mode,
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


def _open_inventory_table_item(item_id: str, item: dict | None = None) -> None:
    """Set selected inventory state; the page render opens the dialog once."""
    _open_inventory_modal(item_id, item)
    ips_app_rerun()


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
    iid = str(item.get("id") or "")
    st.session_state[f"inv_edit_sku_{iid}"] = str(item.get("sku") or "")
    st.session_state[f"inv_edit_name_{iid}"] = str(item.get("name") or "")
    st.session_state[f"inv_edit_cat_{iid}"] = str(item.get("category") or "")
    st.session_state[f"inv_edit_status_{iid}"] = str(item.get("status") or "")
    st.session_state[f"inv_edit_loc_{iid}"] = str(item.get("location") or "")
    st.session_state[f"inv_edit_qty_{iid}"] = int(item.get("qty_on_hand") or 0)
    st.session_state[f"inv_edit_cost_{iid}"] = float(item.get("unit_cost") or 0)


def _render_inventory_qr_block(item: dict) -> None:
    """Clickable QR, scan link, and printable label downloads."""
    from app.components.qr_label_toolbar import render_qr_label_png_buttons
    from app.services.inventory_qr_labels import (
        inventory_label_download_basename,
        inventory_label_png_bytes,
        inventory_qr_subject,
    )
    scan_url = generate_inventory_qr_value(item)
    subject = inventory_qr_subject(item)
    qr_png = inventory_qr_png_bytes(item)
    iid = str(item.get("id") or "").strip() or "item"

    with st.container(border=True):
        st.markdown(
            '<p style="margin:0 0 0.35rem;font-weight:700;font-size:0.9rem;">Inventory QR</p>',
            unsafe_allow_html=True,
        )
        if qr_png and scan_url:
            b64 = base64.b64encode(qr_png).decode("ascii")
            safe_url = html.escape(scan_url, quote=True)
            st.markdown(
                f'<a href="{safe_url}" target="_self" title="Open use form">'
                f'<img src="data:image/png;base64,{b64}" width="132" alt="Inventory QR code" '
                f'style="display:block;border:1px solid #e2e8f0;border-radius:8px;" />'
                f"</a>",
                unsafe_allow_html=True,
            )
        elif qr_png:
            st.image(qr_png, width=132)
        else:
            st.caption(str(item.get("qr_code_value") or "—"))
        sku = resolve_inventory_sku(item)
        st.caption(f"SKU: **{html.escape(sku)}**", unsafe_allow_html=True)
        if scan_url:
            st.caption("Scan with a phone or tap to record material use.")
            st.link_button("Open Use Form", scan_url, use_container_width=True)
            if scan_url.startswith("http"):
                st.caption("Scan URL")
                st.code(scan_url, language=None)
        render_qr_label_png_buttons(
            key_prefix=f"inv_qr_{iid}",
            basename=inventory_label_download_basename(item),
            build_png=lambda size_key: inventory_label_png_bytes(item, subject, size=size_key),
        )


def _txn_action_label(txn_type: str) -> str:
    from app.services.inventory_service import inventory_action_label
    return inventory_action_label(txn_type)


def _render_inventory_issue_to_job_form(item: dict) -> None:
    """Record use of this consumable on a job — updates stock and job costing."""
    iid = str(item.get("id") or "").strip()
    if not iid:
        return
    from app.pages._core._data import load_jobs
    from app.services.job_materials_service import issue_inventory_to_job
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
    jobs = sort_jobs_by_number_then_name([j for j in load_jobs() if j.get("id")])
    job_labels = [job_row_select_label(j) for j in jobs]
    job_map = {job_row_select_label(j): str(j.get("id") or "") for j in jobs}

    st.markdown("**Use on Job**")
    with st.form(f"inv_issue_job_{iid}", clear_on_submit=True):
        job_pick = st.selectbox("Job", ["— Select job —", *job_labels], key=f"inv_issue_job_pick_{iid}")
        qty = st.number_input(
            "Quantity",
            key=f"inv_issue_job_qty_{iid}",
            **inventory_qty_input_kwargs(min_value=1, value=1),
        )
        notes = st.text_area("Notes", key=f"inv_issue_job_notes_{iid}", height=60)
        submit = st.form_submit_button("Use on Job", type="primary", use_container_width=True)

    if not submit:
        return
    jid = job_map.get(str(job_pick or "").strip())
    if not jid:
        st.error("Select a job.")
        return
    qv = int(qty or 0)
    if qv <= 0:
        st.error("Quantity must be greater than zero.")
        return
    result = issue_inventory_to_job(
        job_id=jid,
        inventory_item_id=iid,
        quantity=qv,
        transaction_type="consume_on_job",
        notes=notes,
        usage_source="manual_inventory",
        source="inventory_detail",
    )
    if result.ok:
        st.success("Material consumed on job. Stock and job costing updated.")
        st.rerun()
    else:
        st.error(result.error or "Could not record material use.")


def _render_inventory_transactions_tab(item: dict) -> None:
    iid = str(item.get("id") or "")
    _render_inventory_issue_to_job_form(item)
    st.divider()
    txns = get_inventory_transactions(inventory_id=iid, limit=100)
    last_scan = "—"
    if txns:
        last_scan = fmt_date(txns[0].get("created_at"))

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        st.metric("On Hand", int(item.get("qty_on_hand") or 0))
    with c2:
        st.metric("Allocated", int(float(item.get("quantity_allocated") or 0)))
    with c3:
        st.metric("Last use", last_scan)

    scan_url = generate_inventory_qr_value(item)
    if scan_url:
        st.link_button("Open Use Form", scan_url, use_container_width=True)
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
            f'<span>{html.escape(format_inventory_quantity(row.get("quantity_display")))}</span>'
            f'<span>{html.escape(str(row.get("job_label") or "—"))}</span>'
            f'<span>{html.escape(str(row.get("scanned_by_name") or "—"))}</span>'
            f'<span>{html.escape(format_phone_display(str(row.get("scanned_by_phone") or "")))}</span>'
            f'<span>{html.escape(str(row.get("notes") or ""))}</span>'
            "</div>"
        )
    st.markdown(f'<div class="ips-inventory-txn-table">{head}{rows_html}</div>', unsafe_allow_html=True)


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
            f"{detail_field_html('Allocated to Jobs', int(float(item.get('quantity_allocated') or 0)))}"
            f"{detail_field_html('Reorder Point', int(item.get('reorder_point') or 0))}"
            f"{detail_field_html('Stock policy', item.get('stock_policy_label') or 'Not stocked')}"
            f"{detail_field_html('Needs reorder', 'Yes' if inventory_needs_reorder(item) else 'No')}"
            f"{detail_field_html('Unit', _inventory_unit(item))}"
            f"{detail_field_html('Unit Cost', fmt_currency(item.get('unit_cost')))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Stock", stock_html), unsafe_allow_html=True)

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
        st.number_input("Qty on hand", key=f"inv_edit_qty_{iid}", min_value=0, step=1, format="%d")
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


def _inventory_export_cache_key(filtered: list[dict]) -> str:
    """Fingerprint current filter + visible export rows; invalidates prepared downloads when stale."""
    ids = ",".join(sorted(str(r.get("id") or "") for r in filtered))
    q = str(st.session_state.get("inv_search") or "").strip()
    stock_view = str(st.session_state.get("inv_stock_view") or "In stock")
    return f"{q}|{stock_view}|{ids}"


def _clear_prepared_inventory_exports() -> None:
    for key in (_EXPORT_CACHE_KEY, _EXPORT_ZIP_BYTES_KEY, _EXPORT_CSV_BYTES_KEY, _EXPORT_COUNT_KEY):
        st.session_state.pop(key, None)


def _sync_inventory_export_cache(filtered: list[dict]) -> str:
    cache_key = _inventory_export_cache_key(filtered)
    if st.session_state.get(_EXPORT_CACHE_KEY) != cache_key:
        _clear_prepared_inventory_exports()
        st.session_state[_EXPORT_CACHE_KEY] = cache_key
    return cache_key


@fragment
def _render_inventory_items_fragment(
    rows: list[dict],
    *,
    filter_options: dict[str, list[str]],
) -> None:
    """Inventory items tab — filters and table with local reruns."""

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

    render_inventory_filter_bar_shell()
    layout_filter_bar(_filters)
    close_inventory_filter_bar_shell()

    filtered = _filter_rows(
        rows,
        q=str(st.session_state.get("inv_search") or "").strip(),
        stock_view=str(st.session_state.get("inv_stock_view") or "In stock"),
    )

    render_table_pagination_header(len(filtered), _TABLE_KEY, item_label="item")
    page_rows, _, _, _ = paginate_rows(filtered, _TABLE_KEY)

    build_modal_cache(filtered, cache_key=_CACHE_KEY)
    _render_custom_inventory_table(page_rows, filter_options=filter_options)

    render_table_pagination_footer(len(filtered), _TABLE_KEY)


def render() -> None:
    from app.pages._core._access import begin_module
    if not begin_module("inventory"):
        return
    from app.navigation import INVENTORY_SCAN_EMBED_KEY
    if st.session_state.pop(INVENTORY_SCAN_EMBED_KEY, False):
        from app.pages.inventory_scan import render_inventory_scan_page
        render_inventory_scan_page()
        return
    inject_inventory_module_css()
    inject_inventory_page_layout_css()
    if is_field_context():
        inject_field_row_expand_css()
    st.markdown(
        '<span class="ips-inventory-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    rows = load_enriched_inventory_rows()
    filter_options = build_filter_options(rows, _COLUMN_FILTER_SPECS)
    reorder_count = sum(1 for r in rows if inventory_needs_reorder(r))
    if reorder_count:
        st.info(f"{reorder_count} mandatory item(s) need reorder — use the **Needs reorder** view.")

    filtered_export = _filter_rows(
        rows,
        q=str(st.session_state.get("inv_search") or "").strip(),
        stock_view=str(st.session_state.get("inv_stock_view") or "In stock"),
    )
    export_cache_key = _sync_inventory_export_cache(filtered_export)

    def _inv_export_header() -> None:
        from app.services.inventory_qr_labels import (
            build_inventory_labels_csv,
            build_inventory_labels_zip,
            inventory_labels_csv_filename,
            inventory_labels_zip_filename,
        )
        count = len(filtered_export)
        if not count:
            st.button(
                "Prepare Label Export",
                key="inv_prepare_label_export",
                disabled=True,
                help="No items match the current filters.",
            )
            return

        zip_bytes = st.session_state.get(_EXPORT_ZIP_BYTES_KEY)
        csv_bytes = st.session_state.get(_EXPORT_CSV_BYTES_KEY)
        prepared = (
            zip_bytes
            and csv_bytes
            and st.session_state.get(_EXPORT_CACHE_KEY) == export_cache_key
        )

        if not prepared:
            if st.button(
                "Prepare Label Export",
                key="inv_prepare_label_export",
                help=f"Build ZIP and CSV for {count} filtered item(s).",
            ):
                with st.spinner(f"Building labels for {count} item(s)…"):
                    st.session_state[_EXPORT_ZIP_BYTES_KEY] = build_inventory_labels_zip(filtered_export)
                    st.session_state[_EXPORT_CSV_BYTES_KEY] = build_inventory_labels_csv(filtered_export).encode(
                        "utf-8"
                    )
                    st.session_state[_EXPORT_COUNT_KEY] = count
                    st.session_state[_EXPORT_CACHE_KEY] = export_cache_key
                st.rerun()
            return

        export_count = int(st.session_state.get(_EXPORT_COUNT_KEY) or count)
        with st.popover("Label Export", help=f"{export_count} item(s) ready to download."):
            st.download_button(
                "Labels ZIP",
                data=zip_bytes,
                file_name=inventory_labels_zip_filename(item_count=export_count),
                mime="application/zip",
                key="inv_export_zip_hdr",
                use_container_width=True,
                help="DuraLabel bulk import: CSV plus PDF labels, QR PNGs, and thumbnails.",
            )
            st.download_button(
                "Labels CSV",
                data=csv_bytes,
                file_name=inventory_labels_csv_filename(item_count=export_count),
                mime="text/csv",
                key="inv_export_csv_hdr",
                use_container_width=True,
                help="Variable data only — pair with ZIP for image and PDF paths.",
            )
            if st.button("Rebuild export", key="inv_rebuild_label_export", use_container_width=True):
                _clear_prepared_inventory_exports()
                st.session_state[_EXPORT_CACHE_KEY] = export_cache_key
                st.rerun()

    def _inv_new() -> None:
        if st.button("+ New Item", key="inv_new", type="primary"):
            st.session_state["ips_inv_form"] = True

    render_page_brand_header(
        "Inventory",
        "Track and manage all inventory items and stock levels.",
        secondary_action=_inv_export_header,
        primary_action=_inv_new,
    )

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

    tab_items, tab_qr_history = st.tabs(["Items", "QR Scan History"])

    with tab_items:
        _render_inventory_items_fragment(rows, filter_options=filter_options)

    with tab_qr_history:
        inject_qr_scan_history_css()
        st.caption(
            "Recent inventory and tool QR scans — who scanned, what opened, and what action was recorded."
        )
        render_qr_scan_history_table(
            load_recent_qr_scans(limit=25)[0],
            empty_message="No QR scans recorded yet. Scans appear when materials or tools are used via QR.",
        )

    if st.session_state.get(SHOW_INVENTORY_MODAL_KEY) or str(st.session_state.get(_MODAL_KEY) or "").strip():
        show_modal_if_pending(_MODAL_KEY, _show_inventory_detail_modal)
