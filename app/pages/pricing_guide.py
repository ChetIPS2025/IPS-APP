"""Pricing Guide — unified master estimating database (``pricing_guide_items``)."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.auth import current_role, effective_role
    from app.components.catalog_presence_panel import render_catalog_presence_panel
    from app.components.catalog_stock_policy_panel import render_catalog_stock_policy_panel
    from app.components.pricing_guide_actions import render_pricing_guide_action_buttons
    from app.components.pricing_guide_list_table import (
        build_pricing_guide_html_table,
        render_pricing_guide_table_bridge_legacy,
        render_pricing_guide_table_open_buttons,
    )
    from app.components.pricing_guide_page_layout import (
        close_pricing_guide_filter_bar_shell,
        inject_pricing_guide_page_layout_css,
        render_pricing_guide_filter_bar_shell,
    )
    from app.components.headers import render_page_brand_header
    from app.components.item_photo_manager import render_item_photo_manager
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
        render_missing_record,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
        status_pill_html as modal_status_pill_html,
    )
    from app.components.labor_rates_panel import render_labor_rates_panel
    from app.components.tabs import render_tabs
    from app.db import fetch_table, fetch_table_admin
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._data import load_assets, load_inventory
    from app.pages._core._session import select_key
    from app.services.pricing_guide_service import (
        PRICING_ITEM_CLASSES,
        PRICING_ITEM_TYPES,
        calc_sell_price,
        cached_pricing_guide_rows,
        class_pill_html,
        clear_pricing_guide_cache,
        fetch_price_history,
        fetch_pricing_guide_catalog,
        normalize_pricing_row,
        pricing_guide_fetch_status,
        save_pricing_item,
        search_pricing_rows,
        pricing_guide_summary,
        type_pill_html,
    )
    from app.services.catalog_import_service import parse_catalog_csv
    from app.services.catalog_image_review_service import (
        DECISION_APPROVE,
        DECISION_PENDING,
        DECISION_REPLACE,
        DECISION_SKIP,
        ImportImageReviewRow,
        build_import_image_review,
        import_catalog_with_review,
    )
    from app.services.pricing_guide_images import (
        clear_pricing_guide_image,
        pricing_guide_display_record,
        pricing_guide_image_is_inherited,
        upload_pricing_guide_image,
    )
    from app.services.item_images import ITEM_IMAGE_UPLOAD_TYPES
    from app.styles import inject_pricing_guide_module_css
    from app.utils.formatting import fmt_currency
except ImportError:
    from auth import current_role, effective_role  # type: ignore
    from components.catalog_presence_panel import render_catalog_presence_panel  # type: ignore
    from components.catalog_stock_policy_panel import render_catalog_stock_policy_panel  # type: ignore
    from components.pricing_guide_actions import render_pricing_guide_action_buttons  # type: ignore
    from components.pricing_guide_list_table import (  # type: ignore
        build_pricing_guide_html_table,
        render_pricing_guide_table_bridge_legacy,
        render_pricing_guide_table_open_buttons,
    )
    from components.pricing_guide_page_layout import (  # type: ignore
        close_pricing_guide_filter_bar_shell,
        inject_pricing_guide_page_layout_css,
        render_pricing_guide_filter_bar_shell,
    )
    from components.headers import render_page_brand_header  # type: ignore
    from components.item_photo_manager import render_item_photo_manager  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.table_filters import (  # type: ignore
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from components.table_pagination import (  # type: ignore
        paginate_rows,
        render_table_pagination_footer,
        render_table_pagination_header,
        reset_table_page,
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
        render_missing_record,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
        status_pill_html as modal_status_pill_html,
    )
    from components.labor_rates_panel import render_labor_rates_panel  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from db import fetch_table, fetch_table_admin  # type: ignore
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._data import load_assets, load_inventory  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from services.pricing_guide_service import (  # type: ignore
        PRICING_ITEM_CLASSES,
        PRICING_ITEM_TYPES,
        calc_sell_price,
        cached_pricing_guide_rows,
        class_pill_html,
        clear_pricing_guide_cache,
        fetch_price_history,
        fetch_pricing_guide_catalog,
        normalize_pricing_row,
        pricing_guide_fetch_status,
        save_pricing_item,
        search_pricing_rows,
        pricing_guide_summary,
        type_pill_html,
    )
    from services.catalog_import_service import parse_catalog_csv  # type: ignore
    from services.catalog_image_review_service import (  # type: ignore
        DECISION_APPROVE,
        DECISION_PENDING,
        DECISION_REPLACE,
        DECISION_SKIP,
        ImportImageReviewRow,
        build_import_image_review,
        import_catalog_with_review,
    )
    from services.pricing_guide_images import (  # type: ignore
        clear_pricing_guide_image,
        pricing_guide_display_record,
        pricing_guide_image_is_inherited,
        upload_pricing_guide_image,
    )
    from services.item_images import ITEM_IMAGE_UPLOAD_TYPES  # type: ignore
    from styles import inject_pricing_guide_module_css  # type: ignore
    from utils.formatting import fmt_currency  # type: ignore

_SEL = select_key("pricing_guide")
_MODULE = "pricing_guide"
_TABLE_KEY = "pg_list"
_MODAL_KEY = "ips_pg_detail_modal_id"
_CACHE_KEY = "_ips_pg_modal_by_id"
SELECTED_PG_KEY = "selected_pricing_guide_id"
SHOW_PG_MODAL_KEY = "show_pricing_guide_detail_modal"
_ALL_PG_IDS_KEY = "_ips_pg_visible_ids"
_PG_FILTER_SPECS: list[tuple[str, str]] = [
    ("CLASS", "item_class"),
    ("CATEGORY", "category"),
    ("VENDOR", "vendor"),
    ("STATUS", "status"),
]
_FILTER_FIELDS = ["item_class", "category", "vendor", "status"]
_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("item_class", lambda r: str(r.get("item_class") or "Non-Inventory")),
    ("category", lambda r: str(r.get("category") or "—")),
    ("vendor", lambda r: str(r.get("vendor") or "—")),
    ("status", lambda r: str(r.get("status") or "Active")),
]
_DETAIL_TABS = (
    "Overview",
    "Pricing",
    "Links",
    "Price History",
    "Notes",
)


def _normalize_row(raw: dict[str, Any]) -> dict[str, Any]:
    return normalize_pricing_row(raw)


def _fitting_detail_fields_html(row: dict[str, Any]) -> str:
    """Extra spec lines for fittings (unions, adapters) when catalog columns are set."""
    if not str(row.get("connection_type") or row.get("dash_size") or "").strip():
        return ""
    parts: list[str] = []
    for label, key in (
        ("Product type", "product_type"),
        ("Connection", "connection_type"),
        ("Pipe size", "pipe_size"),
        ("Dash size", "dash_size"),
        ("Pressure class", "pressure_class"),
        ("Body shape", "body_shape"),
        ("Material", "material_grade"),
        ("Max pressure", "max_pressure_temp"),
        ("Max steam pressure", "max_steam_pressure_temp"),
    ):
        val = str(row.get(key) or "").strip()
        if val:
            parts.append(detail_field_html(label, val))
    return "".join(parts)


def _load_rows() -> list[dict[str, Any]]:
    if not st.session_state.get("_pg_catalog_status_checked"):
        fetch_pricing_guide_catalog(include_inactive=True)
        st.session_state["_pg_catalog_status_checked"] = True
    return cached_pricing_guide_rows(include_inactive=True)


def _render_catalog_status_banner() -> None:
    status = pricing_guide_fetch_status()
    if not status or not status.warning:
        return
    if status.fetch_failed:
        st.error(status.warning)
    else:
        st.warning(status.warning)


def _vendor_options() -> list[tuple[str, str]]:
    opts: list[tuple[str, str]] = [("— None —", "")]
    try:
        rows = list(fetch_table_admin("vendors", limit=5000, order_by="vendor_name") or [])
    except Exception:
        try:
            rows = list(fetch_table("vendors", limit=5000, order_by="vendor_name") or [])
        except Exception:
            rows = []
    for r in rows:
        if not isinstance(r, dict) or r.get("is_active") is False:
            continue
        vid = str(r.get("id") or "").strip()
        name = str(r.get("vendor_name") or r.get("name") or "").strip()
        if vid and name:
            opts.append((name, vid))
    return opts


def _inventory_options() -> list[tuple[str, str]]:
    opts: list[tuple[str, str]] = [("— None —", "")]
    for r in load_inventory():
        iid = str(r.get("id") or "").strip()
        label = str(r.get("item_name") or r.get("name") or r.get("description") or "").strip()
        if iid and label:
            opts.append((label, iid))
    return opts


def _asset_options() -> list[tuple[str, str]]:
    opts: list[tuple[str, str]] = [("— None —", "")]
    for r in load_assets():
        aid = str(r.get("id") or "").strip()
        label = str(r.get("asset_name") or r.get("name") or "").strip()
        if aid and label:
            opts.append((label, aid))
    return opts


def _render_summary_cards(rows: list[dict[str, Any]]) -> None:
    stats = pricing_guide_summary(rows)
    cards = [
        ("Active Items", str(stats["active_count"])),
        ("Inventory Class", str(stats["inventory_class"])),
        ("Asset Class", str(stats["asset_class"])),
        ("Non-Inventory", str(stats["non_inventory_class"])),
        ("Stock Linked", str(stats["inventory_linked"])),
        ("Asset Linked", str(stats["asset_linked"])),
        ("Avg Markup", f"{stats['avg_markup']:.1f}%"),
    ]
    html_cards = "".join(
        f'<div class="ips-pg-summary-card"><div class="lbl">{html.escape(lbl)}</div>'
        f'<div class="val">{html.escape(val)}</div></div>'
        for lbl, val in cards
    )
    st.markdown(f'<div class="ips-pg-summary-grid">{html_cards}</div>', unsafe_allow_html=True)


def _clear_modal() -> None:
    _clear_pg_selection()
    clear_edit_modes(_MODULE)
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _open_modal(row_id: str, row: dict | None = None) -> None:
    rid = str(row_id or "").strip()
    if not rid:
        return
    st.session_state[SELECTED_PG_KEY] = rid
    st.session_state[SHOW_PG_MODAL_KEY] = True
    open_record_modal(
        rid,
        row,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
        id_fields=("id",),
    )


def _open_pg_table_item(row_id: str, row: dict | None = None) -> None:
    """Set selected pricing item state; the page render opens the dialog once."""
    rid = str(row_id or "").strip()
    if not rid:
        return
    cache = st.session_state.get(_CACHE_KEY) or {}
    cached = cache.get(rid) if isinstance(cache, dict) else None
    record = cached if isinstance(cached, dict) else row
    _open_modal(rid, record)


def _clear_pg_selection() -> None:
    st.session_state[SELECTED_PG_KEY] = None
    st.session_state[SHOW_PG_MODAL_KEY] = False


def _render_pricing_guide_table_column_filters(
    *,
    filter_options: dict[str, list[str]],
) -> None:
    if not _PG_FILTER_SPECS:
        return
    st.markdown('<div class="ips-pg-table-filter-toolbar">', unsafe_allow_html=True)
    cols = st.columns(len(_PG_FILTER_SPECS), gap="small")
    for col, (label, field) in zip(cols, _PG_FILTER_SPECS):
        with col:
            render_table_header_cell(
                label,
                table_key=_TABLE_KEY,
                filter_field=field,
                filter_options=filter_options.get(field, []),
                base_class="ips-pg-filter-toolbar-cell",
            )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_custom_pricing_guide_table(
    filtered: list[dict[str, Any]],
    *,
    filter_options: dict[str, list[str]],
) -> list[str]:
    if not filtered:
        st.info("No pricing guide items match your filters.")
        st.session_state[_ALL_PG_IDS_KEY] = []
        return []

    all_row_ids = [str(r.get("id") or "").strip() for r in filtered if str(r.get("id") or "").strip()]
    st.session_state[_ALL_PG_IDS_KEY] = all_row_ids

    rows_by_id = {
        str(r.get("id") or "").strip(): r
        for r in filtered
        if str(r.get("id") or "").strip()
    }

    with st.container(key="pricing_guide_table_wrap"):
        _render_pricing_guide_table_column_filters(filter_options=filter_options)
        st.markdown(
            build_pricing_guide_html_table(filtered),
            unsafe_allow_html=True,
        )
        render_pricing_guide_table_open_buttons(
            filtered,
            open_item_fn=_open_pg_table_item,
        )
        render_pricing_guide_table_bridge_legacy(
            rows_by_id,
            open_item_fn=_open_pg_table_item,
        )

    return all_row_ids


def _can_manage_pricing() -> bool:
    return str(effective_role() or "").strip().lower() in {"admin", "supervisor", "manager"}


def _render_pg_photo_manager(row: dict[str, Any]) -> None:
    rid = str(row.get("id") or "").strip()
    rk = record_session_key(row, "id")
    display = pricing_guide_display_record(row)
    render_item_photo_manager(
        row,
        record_id=rid,
        session_prefix=f"pg_photo_{rk}",
        image_css_class="ips-pg-detail-image",
        upload_image=upload_pricing_guide_image,
        clear_image=clear_pricing_guide_image,
        uploaded_by="",
        cache_key=_CACHE_KEY,
        on_change=clear_pricing_guide_cache,
        readonly=not _can_manage_pricing() or is_demo_id(rid),
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


def _render_pg_detail_image(row: dict[str, Any]) -> None:
    _render_pg_photo_manager(row)


def _filter_rows(rows: list[dict[str, Any]], *, q: str) -> list[dict[str, Any]]:
    out = search_pricing_rows(rows, q)
    return apply_column_filters(out, _TABLE_KEY, _COLUMN_FILTER_SPECS)


def _persist_row(data: dict[str, Any], row_id: str | None = None) -> tuple[bool, str]:
    return save_pricing_item(data, row_id=row_id)


def _render_conditional_fields(prefix: str, item_class: str, item_type: str) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    if item_class == "Inventory":
        inv_opts = _inventory_options()
        pick = st.selectbox(
            "Link inventory item",
            [label for label, _ in inv_opts],
            key=f"{prefix}_inv",
        )
        inv_map = {label: vid for label, vid in inv_opts}
        extra["linked_inventory_id"] = inv_map.get(pick) or None
        extra["inventory_item_id"] = extra["linked_inventory_id"]
    elif item_class == "Asset":
        asset_opts = _asset_options()
        pick = st.selectbox(
            "Link asset",
            [label for label, _ in asset_opts],
            key=f"{prefix}_asset",
        )
        asset_map = {label: aid for label, aid in asset_opts}
        extra["linked_asset_id"] = asset_map.get(pick) or None
        extra["asset_id"] = extra["linked_asset_id"]
        extra["equipment_type"] = st.text_input("Equipment type", key=f"{prefix}_eq_type")
    elif item_type == "Labor":
        extra["labor_role"] = st.text_input("Labor role", key=f"{prefix}_labor_role")
    elif item_type == "Travel":
        extra["travel_type"] = st.selectbox(
            "Travel type",
            ["Mileage", "Per Diem", "Lodging", "Mobilization", "Fuel surcharge", "Other"],
            key=f"{prefix}_travel_type",
        )
    elif item_type == "Subcontractor":
        vendor_opts = _vendor_options()
        pick = st.selectbox("Vendor", [label for label, _ in vendor_opts], key=f"{prefix}_vendor")
        vendor_map = {label: vid for label, vid in vendor_opts}
        extra["vendor_id"] = vendor_map.get(pick) or None
    elif item_type == "Service":
        extra["category"] = st.text_input("Service category", key=f"{prefix}_svc_cat")
    elif item_type == "Assembly":
        st.caption("Assembly packages: component grouping will be added in a future release.")
    return extra


def _render_csv_import() -> None:
    with st.expander("Import Catalog CSV", expanded=False):
        st.caption(
            "Imports Pricing Guide, Inventory, and Asset records from CSV. "
            "Item photos require manual review — nothing is auto-attached from cropped thumbnails."
        )
        uploaded = st.file_uploader(
            "CSV file",
            type=["csv"],
            key="pg_csv_upload",
            label_visibility="collapsed",
        )
        image_uploads = st.file_uploader(
            "Candidate item images (optional — match by model #, item #, SKU, then description)",
            type=list(ITEM_IMAGE_UPLOAD_TYPES),
            accept_multiple_files=True,
            key="pg_csv_images",
        )
        st.caption(
            "Approved images are saved under assets/item_images/inventory/ and assets/item_images/assets/. "
            "Existing approved photos are never overwritten."
        )

        if uploaded is None:
            return

        text = uploaded.getvalue().decode("utf-8-sig", errors="replace")
        image_files: list[tuple[str, bytes]] = []
        for f in image_uploads or []:
            image_files.append((str(getattr(f, "name", "") or "image.jpg"), f.getvalue()))

        c1, c2 = st.columns(2)
        with c1:
            prepare = st.button("Prepare Import Review", key="pg_csv_prepare", type="primary")
        with c2:
            if st.button("Clear Review", key="pg_csv_clear_review"):
                for key in list(st.session_state.keys()):
                    if isinstance(key, str) and key.startswith("pg_import_"):
                        del st.session_state[key]
                st.rerun()

        if prepare:
            rows = parse_catalog_csv(text)
            if not rows:
                st.error("No valid rows found in CSV.")
                return
            review = build_import_image_review(rows, image_files or None)
            st.session_state["pg_import_csv_text"] = text
            st.session_state["pg_import_review_meta"] = [
                {
                    "row_index": r.row_index,
                    "description": r.description,
                    "model_number": r.model_number,
                    "item_number": r.item_number,
                    "sku": r.sku,
                    "item_class": r.item_class,
                    "match_filename": r.match_filename,
                    "match_field": r.match_field,
                    "confidence": r.confidence,
                    "decision": r.decision,
                    "existing_approved": r.existing_approved,
                    "row": r.row,
                }
                for r in review
            ]
            blob_cache: dict[str, bytes] = {}
            for r in review:
                if r.suggested_bytes:
                    blob_cache[str(r.row_index)] = r.suggested_bytes
            st.session_state["pg_import_image_blobs"] = blob_cache
            for r in review:
                st.session_state[f"pg_import_decision_{r.row_index}"] = r.decision
            st.rerun()

        meta = st.session_state.get("pg_import_review_meta")
        if not meta:
            return

        st.markdown("### Image review (required before photos are saved)")
        suggested = sum(1 for m in meta if m.get("match_filename"))
        st.caption(
            f"{len(meta)} catalog row(s) · {suggested} with suggested image(s). "
            "Approve, replace, or skip each photo before import."
        )

        page_size = 10
        total_pages = max(1, (len(meta) + page_size - 1) // page_size)
        page = int(st.number_input("Review page", min_value=1, max_value=total_pages, value=1, key="pg_import_review_page"))
        start = (page - 1) * page_size
        batch = meta[start : start + page_size]
        blobs: dict[str, bytes] = st.session_state.get("pg_import_image_blobs") or {}

        for entry in batch:
            idx = int(entry["row_index"])
            decision_key = f"pg_import_decision_{idx}"
            if decision_key not in st.session_state:
                st.session_state[decision_key] = str(entry.get("decision") or DECISION_SKIP)

            with st.container(border=True):
                left, mid, right = st.columns([2.2, 1.2, 1.3])
                with left:
                    st.markdown(f"**{entry.get('description', '')[:120]}**")
                    st.caption(
                        f"Class: {entry.get('item_class')} · "
                        f"Model: {entry.get('model_number') or '—'} · "
                        f"Item #: {entry.get('item_number') or '—'} · "
                        f"SKU: {entry.get('sku') or '—'}"
                    )
                    if entry.get("existing_approved"):
                        st.info("Existing approved photo — will not be overwritten.")
                with mid:
                    blob = blobs.get(str(idx))
                    if blob:
                        st.image(blob, caption=entry.get("match_filename") or "Suggested", use_container_width=True)
                        conf = str(entry.get("confidence") or "none")
                        field = str(entry.get("match_field") or "")
                        st.caption(f"Match: {field or '—'} ({conf})")
                    else:
                        st.caption("No suggested image")
                with right:
                    options = [DECISION_PENDING, DECISION_APPROVE, DECISION_SKIP, DECISION_REPLACE]
                    if entry.get("existing_approved"):
                        options = [DECISION_SKIP]
                    current = str(st.session_state.get(decision_key) or entry.get("decision") or DECISION_PENDING)
                    if current not in options:
                        current = options[0]
                    choice = st.selectbox(
                        "Decision",
                        options,
                        index=options.index(current),
                        key=f"pg_import_decision_select_{idx}",
                        disabled=bool(entry.get("existing_approved")),
                    )
                    st.session_state[decision_key] = choice
                    if choice == DECISION_REPLACE:
                        repl = st.file_uploader(
                            "Replacement image",
                            type=list(ITEM_IMAGE_UPLOAD_TYPES),
                            key=f"pg_import_replace_{idx}",
                            label_visibility="collapsed",
                        )
                        if repl is not None:
                            st.session_state[f"pg_import_replace_bytes_{idx}"] = repl.getvalue()
                            st.session_state[f"pg_import_replace_name_{idx}"] = str(getattr(repl, "name", "") or "replacement.jpg")

        if st.button("Import Catalog + Approved Images", key="pg_csv_import", type="primary"):
            csv_text = str(st.session_state.get("pg_import_csv_text") or text)
            review_rows: list[ImportImageReviewRow] = []
            for entry in meta:
                idx = int(entry["row_index"])
                decision = str(st.session_state.get(f"pg_import_decision_{idx}") or DECISION_SKIP)
                suggested_bytes = blobs.get(str(idx))
                replace_bytes = st.session_state.get(f"pg_import_replace_bytes_{idx}")
                replace_name = str(st.session_state.get(f"pg_import_replace_name_{idx}") or "")
                review_rows.append(
                    ImportImageReviewRow(
                        row_index=idx,
                        row=dict(entry.get("row") or {}),
                        description=str(entry.get("description") or ""),
                        model_number=str(entry.get("model_number") or ""),
                        item_number=str(entry.get("item_number") or ""),
                        sku=str(entry.get("sku") or ""),
                        item_class=str(entry.get("item_class") or ""),
                        match_filename=str(entry.get("match_filename") or ""),
                        match_field=str(entry.get("match_field") or ""),
                        confidence=str(entry.get("confidence") or "none"),
                        suggested_bytes=suggested_bytes if isinstance(suggested_bytes, (bytes, bytearray)) else None,
                        decision=decision,
                        replace_filename=replace_name,
                        replace_bytes=replace_bytes if isinstance(replace_bytes, (bytes, bytearray)) else None,
                        existing_approved=bool(entry.get("existing_approved")),
                    )
                )
            result, _img = import_catalog_with_review(csv_text, review_rows)
            if result.ok:
                st.success(result.message)
                if result.errors:
                    for err in result.errors[:20]:
                        st.warning(err)
                for key in list(st.session_state.keys()):
                    if isinstance(key, str) and key.startswith("pg_import_"):
                        del st.session_state[key]
                st.rerun()
            else:
                st.error(result.message)


def _render_add_form() -> None:
    with st.expander("New Pricing Item", expanded=True):
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

        extra = _render_conditional_fields("pg_new", item_class, item_type)

        if st.button("Save Pricing Item", key="pg_new_save", type="primary"):
            payload = {
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
            ok, msg = _persist_row(payload)
            if apply_persist_feedback(ok, msg, clear_keys=("pg_add_form",)):
                st.rerun()


def _render_item_tabs(row: dict[str, Any]) -> None:
    tab = render_tabs(list(_DETAIL_TABS), session_key=f"ips_pg_tab_{row.get('id')}", default="Overview")
    if tab == "Overview":
        media, details = st.columns([1.0, 2.2])
        with media:
            st.markdown("**Item Image**")
            _render_pg_detail_image(row)
        with details:
            st.markdown(
                dialog_card_html(
                    "Overview",
                    f"{detail_field_html('Description', row.get('item'))}"
                    f"{detail_field_html('Item code', row.get('item_code') or row.get('item_key'))}"
                    f'{detail_field_html("Class", row.get("item_class"), html_value=class_pill_html(str(row.get("item_class") or "")))}'
                    f'{detail_field_html("Estimate type", row.get("item_type"), html_value=type_pill_html(str(row.get("item_type") or "")))}'
                    f"{detail_field_html('SKU', row.get('sku') or '—')}"
                    f"{detail_field_html('Item #', row.get('item_number') or '—')}"
                    f"{detail_field_html('Model #', row.get('model_number') or '—')}"
                    f"{detail_field_html('Image status', row.get('image_status') or 'missing')}"
                    f"{detail_field_html('Category', row.get('category'))}"
                    f"{detail_field_html('Subcategory', row.get('subcategory') or '—')}"
                    f"{_fitting_detail_fields_html(row)}"
                    f"{detail_field_html('Unit', row.get('unit'))}"
                    f'{detail_field_html("Status", row.get("status"), html_value=modal_status_pill_html(str(row.get("status") or "")))}',
                ),
                unsafe_allow_html=True,
            )
    elif tab == "Pricing":
        mk = float(row.get("markup_pct") or 0)
        st.markdown(
            dialog_card_html(
                "Pricing",
                f"{detail_field_html('Cost', fmt_currency(row.get('default_cost')))}"
                f"{detail_field_html('Markup %', f'{mk:.1f}%')}"
                f"{detail_field_html('Sell price', fmt_currency(row.get('customer_price')))}"
                f"{detail_field_html('Taxable', 'Yes' if row.get('taxable') is not False else 'No')}",
            ),
            unsafe_allow_html=True,
        )
    elif tab == "Links":
        inv_label = str(row.get("inventory_label") or "").strip() or "Not linked"
        asset_label = str(row.get("asset_label") or "").strip() or "Not linked"
        body = (
            f"{detail_field_html('Inventory item', inv_label)}"
            f"{detail_field_html('Asset / equipment', asset_label)}"
            f"{detail_field_html('Stock policy', row.get('stock_policy_label') or 'Not stocked')}"
            f"{detail_field_html('Default reorder point', int(float(row.get('default_reorder_point') or 0)))}"
            f"{detail_field_html('Vendor', row.get('vendor') or '—')}"
            f"{detail_field_html('Labor role', row.get('labor_role') or '—')}"
            f"{detail_field_html('Equipment type', row.get('equipment_type') or '—')}"
            f"{detail_field_html('Travel type', row.get('travel_type') or '—')}"
        )
        st.markdown(dialog_card_html("Linked Records", body), unsafe_allow_html=True)
    elif tab == "Price History":
        history = fetch_price_history(str(row.get("id") or ""))
        if not history:
            st.markdown(
                dialog_card_html("Price History", placeholder_html("No price changes recorded yet.")),
                unsafe_allow_html=True,
            )
        else:
            rows_html = "".join(
                f"<tr><td>{html.escape(str(h.get('changed_at') or '')[:10])}</td>"
                f"<td>{html.escape(fmt_currency(h.get('old_cost')))}</td>"
                f"<td>{html.escape(fmt_currency(h.get('new_cost')))}</td>"
                f"<td>{html.escape(str(h.get('changed_by') or '—'))}</td></tr>"
                for h in history
            )
            table = (
                '<table class="ips-est-line-table"><thead><tr>'
                "<th>Date</th><th>Old Cost</th><th>New Cost</th><th>Changed By</th>"
                f"</tr></thead><tbody>{rows_html}</tbody></table>"
            )
            st.markdown(dialog_card_html("Price History", table), unsafe_allow_html=True)
    else:
        notes = safe_value(row.get("notes"), "No notes.")
        st.markdown(
            dialog_card_html("Notes", f"<p style='margin:0;font-size:0.875rem;'>{html.escape(notes)}</p>"),
            unsafe_allow_html=True,
        )


def _render_edit_form(row: dict[str, Any]) -> None:
    rk = record_session_key(row, "id")
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
        stock_label = st.selectbox(
            "Stock policy",
            stock_labels,
            index=stock_ix,
            key=f"pg_edit_stock_{rk}",
        )
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

    extra = _render_conditional_fields(f"pg_edit_{rk}", item_class, item_type)
    notes = st.text_area("Notes", value=str(row.get("notes") or ""), key=f"pg_edit_notes_{rk}")
    st.markdown("**Item Photo**")
    _render_pg_photo_manager(row)

    cancelled, saved = render_save_cancel_actions(
        module=_MODULE,
        record_key=rk,
        cancel_key=f"pg_edit_cancel_{rk}",
        save_key=f"pg_edit_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved:
        ok, msg = _persist_row(
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
        if apply_persist_feedback(ok, msg):
            try:
                from app.services.catalog_stock_policy_service import save_pricing_stock_settings

                save_pricing_stock_settings(
                    {**row, "id": row.get("id"), "stock_policy": stock_policy, "default_reorder_point": float(default_reorder)},
                    stock_policy=stock_policy,
                    default_reorder_point=int(round(default_reorder)),
                    ensure_inventory=True,
                )
            except Exception:
                pass
            set_view_mode(_MODULE, rk)
            st.rerun()
        st.error(msg or "Could not save pricing item.")


def _render_pricing_actions_panel(row: dict) -> None:
    rk = record_session_key(row, "id")
    if is_edit_mode(_MODULE, rk):
        return

    render_pricing_guide_action_buttons(
        row,
        can_manage=_can_manage_pricing(),
        on_deactivate=_clear_modal,
        on_delete=_clear_modal,
    )


@st.dialog("Pricing Guide Item", width="large", on_dismiss=_clear_modal)
def _show_detail_modal() -> None:
    row = get_modal_record(cache_key=_CACHE_KEY, modal_key=_MODAL_KEY, session_select_key=_SEL)
    if not row:
        render_missing_record(_clear_modal, close_key="pg_modal_missing_close")
        return
    row = _normalize_row(row)
    rk = record_session_key(row, "id")
    edit_mode = is_edit_mode(_MODULE, rk)
    render_modal_header(
        title=str(row.get("item") or "Pricing Item"),
        subtitle=str(row.get("item_code") or row.get("item_key") or ""),
        status=str(row.get("status") or ""),
    )
    if effective_role() in {"admin", "supervisor", "manager"}:
        render_modal_edit_button(module=_MODULE, record_key=rk)
    render_modal_meta_grid(
        [
            ("Class", row.get("item_class")),
            ("Estimate type", row.get("item_type")),
            ("Category", row.get("category")),
            ("Unit", row.get("unit")),
            ("Cost", fmt_currency(row.get("default_cost"))),
            ("Sell price", fmt_currency(row.get("customer_price"))),
        ]
    )
    render_modal_shell()
    if edit_mode:
        _render_edit_form(row)
    else:
        render_catalog_presence_panel(
            row,
            can_manage=_can_manage_pricing(),
            on_change=clear_pricing_guide_cache,
        )
        render_catalog_stock_policy_panel(
            row,
            can_manage=_can_manage_pricing(),
            on_change=clear_pricing_guide_cache,
        )
        _render_pricing_actions_panel(row)
        _render_item_tabs(row)


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("pricing_guide"):
        return

    inject_pricing_guide_module_css()
    inject_pricing_guide_page_layout_css()
    st.markdown(
        '<span class="ips-pricing-guide-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    def _pg_new() -> None:
        if st.button("+ New Pricing Item", key="pg_add", type="primary", use_container_width=True):
            st.session_state["pg_add_form"] = True

    render_page_brand_header(
        "Pricing Guide",
        "Master estimating catalog: materials, asset rentals, default labor rates, travel, and estimate-only items.",
        actions=[_pg_new],
    )

    main_tab = render_tabs(
        ["Catalog", "Labor Rates"],
        session_key="pg_main_tab",
        default="Catalog",
    )

    if main_tab == "Labor Rates":
        render_labor_rates_panel(key_prefix="pg_labor", show_header=False)
        return

    _render_catalog_status_banner()
    rows = _load_rows()
    filter_options = build_filter_options(rows, _COLUMN_FILTER_SPECS)

    _render_summary_cards(rows)

    _render_csv_import()

    if st.session_state.get("pg_add_form"):
        _render_add_form()

    def _filters() -> None:
        c1, c2 = st.columns([5, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search description, class, category, vendor, SKU, model #…",
                key="pg_search",
                label_visibility="collapsed",
            )
        with c2:
            if st.button("Clear", key="pg_clear", use_container_width=True):
                clear_table_filters(
                    _TABLE_KEY,
                    _FILTER_FIELDS,
                    extra_keys=["pg_search"],
                )
                _clear_pg_selection()
                reset_table_page(_TABLE_KEY)
                st.rerun()

    render_pricing_guide_filter_bar_shell()
    layout_filter_bar(_filters)
    close_pricing_guide_filter_bar_shell()

    filtered = _filter_rows(
        rows,
        q=str(st.session_state.get("pg_search") or "").strip(),
    )

    build_modal_cache(filtered, cache_key=_CACHE_KEY)
    render_table_pagination_header(len(filtered), _TABLE_KEY, item_label="item")
    page_rows, _, _, _ = paginate_rows(filtered, _TABLE_KEY)
    _render_custom_pricing_guide_table(page_rows, filter_options=filter_options)
    render_table_pagination_footer(len(filtered), _TABLE_KEY)

    selected_id = st.session_state.get(SELECTED_PG_KEY)
    if selected_id and st.session_state.get(SHOW_PG_MODAL_KEY):
        _show_detail_modal()
