"""Assets module (Phase 2B)."""

from __future__ import annotations

import base64
import html

import streamlit as st

try:
    from app.components.asset_actions import render_asset_action_buttons
    from app.components.asset_pricing_guide_actions import render_asset_pricing_guide_actions
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
        render_modal_header,
        render_modal_edit_button,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
    )
    from app.pages._core._data import load_assets, lookup_options, persist_asset
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
    from app.styles import inject_assets_module_css
    from app.services.asset_images import (
        asset_display_record,
        asset_image_is_inherited,
        clear_asset_image,
        upload_asset_image as upload_asset_image_file,
    )
    from app.services.item_images import ITEM_IMAGE_UPLOAD_TYPES
    from app.services.assets_service import (
        clear_assets_cache,
        generate_asset_qr_value,
        get_asset_document_view_url,
        get_asset_documents,
        rebuild_asset_qr,
        get_asset_image_url,
        get_asset_inspections,
        get_asset_issues,
        upload_asset_image,
    )
    from app.ui.assets_components import (
        inject_assets_page_styles,
        maintenance_table_html,
        status_badge_html,
        summary_card_html,
    )
    from app.utils.formatting import fmt_currency, fmt_date
    from app.services.asset_kits_service import asset_is_kit, list_all_kit_items_enriched
    from app.pages.asset_kits_ui import kit_badge_html, render_kit_accountability_summary, render_kit_contents_tab
    from app.utils.field_context import (
        FIELD_EXPANDED_ASSET_KEY,
        clear_field_expanded,
        field_expanded_id,
        inject_field_row_expand_css,
        is_field_context,
        is_field_mode,
        render_field_scan_bar,
        toggle_field_expanded,
    )
except ImportError:
    from components.asset_actions import render_asset_action_buttons  # type: ignore
    from components.asset_pricing_guide_actions import render_asset_pricing_guide_actions  # type: ignore
    from components.item_photo_manager import render_item_photo_manager  # type: ignore
    from components.headers import render_page_brand_header  # type: ignore
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
        render_modal_header,
        render_modal_edit_button,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
    )
    from pages._core._data import load_assets, lookup_options, persist_asset  # type: ignore
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from styles import inject_assets_module_css  # type: ignore
    from services.asset_images import (  # type: ignore
        asset_display_record,
        asset_image_is_inherited,
        clear_asset_image,
        upload_asset_image as upload_asset_image_file,
    )
    from services.item_images import ITEM_IMAGE_UPLOAD_TYPES  # type: ignore
    from services.assets_service import (  # type: ignore
        clear_assets_cache,
        generate_asset_qr_value,
        get_asset_document_view_url,
        get_asset_documents,
        get_asset_image_url,
        get_asset_inspections,
        get_asset_issues,
        upload_asset_image,
    )
    from ui.assets_components import (  # type: ignore
        inject_assets_page_styles,
        maintenance_table_html,
        status_badge_html,
        summary_card_html,
    )
    from utils.formatting import fmt_currency, fmt_date  # type: ignore
    from services.asset_kits_service import asset_is_kit, list_all_kit_items_enriched  # type: ignore
    from pages.asset_kits_ui import kit_badge_html, render_kit_accountability_summary, render_kit_contents_tab  # type: ignore
    from utils.field_context import (  # type: ignore
        FIELD_EXPANDED_ASSET_KEY,
        clear_field_expanded,
        field_expanded_id,
        inject_field_row_expand_css,
        is_field_context,
        is_field_mode,
        render_field_scan_bar,
        toggle_field_expanded,
    )

_SEL = select_key("assets")
_MOD = "assets"
_ASSETS_MODAL_KEY = "ips_assets_detail_modal_id"
_ASSETS_CACHE_KEY = "_ips_assets_modal_by_id"
SELECTED_ASSET_KEY = "selected_asset_id"
SHOW_ASSET_MODAL_KEY = "show_asset_detail_modal"
_ALL_ASSET_IDS_KEY = "_ips_assets_visible_ids"
_TABLE_KEY = "assets_list"
_SMALL_TOOLS_TABLE_KEY = "assets_small_tools_list"
_ASSET_COLS = [0.42, 0.9, 3.13, 1.6, 1.7, 1.7, 1.5, 1.8, 1.4]
_SMALL_TOOL_COLS = [0.55, 2.6, 1.1, 1.9, 1.5, 1.1, 1.0]
_SMALL_TOOL_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("TOOL", None),
    ("TYPE", "item_type"),
    ("PARENT KIT", "parent_kit"),
    ("LOCATION", "location"),
    ("STATUS", "status"),
    ("VALUE", None),
]
_SMALL_TOOL_FILTER_SPECS: list[tuple[str, object]] = [
    ("item_type", lambda r: _small_tool_type(r)),
    ("parent_kit", lambda r: _small_tool_parent_kit(r)),
    ("location", lambda r: _small_tool_location(r)),
    ("status", lambda r: _small_tool_status(r)),
]
_ASSET_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("IMAGE", None),
    ("ASSET NAME", None),
    ("CATEGORY", "category"),
    ("LOCATION", "location"),
    ("DEPARTMENT", "department"),
    ("STATUS", "status"),
    ("ASSIGNED TO", None),
    ("NEXT SERVICE DUE", None),
]
_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("category", lambda r: _asset_category(r)),
    ("location", lambda r: _asset_location(r)),
    ("department", lambda r: _asset_department(r)),
    ("status", lambda r: _normalize_asset_status(r.get("status"))),
]
_ASSET_BAR_FILTER_FIELDS = ["category", "location", "department", "status"]
_ASSET_TABS = [
    "Overview",
    "Kit / Contents",
    "Maintenance",
    "Documents",
    "Assignments",
    "Depreciation",
    "Notes",
    "Activity",
]


def _normalize_asset_status(raw: object) -> str:
    s = str(raw or "").strip().lower().replace("_", " ")
    mapping = {
        "": "Available",
        "available": "Available",
        "in service": "In Service",
        "in_service": "In Service",
        "assigned": "Assigned",
        "out for repair": "Out for Repair",
        "repair": "Out for Repair",
        "maintenance due": "Maintenance Due",
        "maintenance_due": "Maintenance Due",
        "maintenance": "Maintenance Due",
        "retired": "Retired",
        "sold": "Sold",
        "lost": "Lost",
    }
    if s in mapping:
        return mapping[s]
    label = str(raw or "").strip()
    return label if label else "Available"


def _asset_number(row: dict) -> str:
    for key in ("asset_number", "asset_id", "asset_no"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _asset_name(row: dict) -> str:
    for key in ("asset_name", "name", "description"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _asset_category(row: dict) -> str:
    return str(row.get("category") or "").strip() or "—"


def _is_small_tool_asset(row: dict) -> bool:
    """Standalone assets tracked as small tools (not kit/trailer containers)."""
    if asset_is_kit(row):
        return False
    cat = str(row.get("category") or row.get("asset_type") or "").strip().lower()
    return cat == "tool"


def _small_tool_row_id(row: dict) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        return f"kititem_{row.get('id') or ''}"
    return str(row.get("id") or "")


def _small_tool_name(row: dict) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        return str(row.get("item_name") or "—").strip() or "—"
    return _asset_name(row)


def _small_tool_type(row: dict) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        return str(row.get("item_type") or "Tool").strip() or "Tool"
    return _asset_category(row)


def _small_tool_parent_kit(row: dict) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        parent = str(row.get("parent_asset_name") or "—").strip() or "—"
        number = str(row.get("parent_asset_number") or "").strip()
        if number and number != "—":
            return f"{number} · {parent}"
        return parent
    return "—"


def _small_tool_location(row: dict) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        return str(row.get("parent_location") or "—").strip() or "—"
    return _asset_location(row)


def _small_tool_status(row: dict) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        return str(row.get("status") or "Present").strip() or "Present"
    return _normalize_asset_status(row.get("status"))


def _small_tool_value(row: dict) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        return fmt_currency(row.get("total_value") or 0)
    return fmt_currency(row.get("value") or row.get("purchase_price") or 0)


def _build_small_tool_list(all_assets: list[dict]) -> list[dict]:
    assets_by_id = {
        str(a.get("id") or "").strip(): a for a in all_assets if str(a.get("id") or "").strip()
    }
    tool_asset_ids = {str(a.get("id") or "").strip() for a in all_assets if _is_small_tool_asset(a)}

    unified: list[dict] = []
    for asset in all_assets:
        if _is_small_tool_asset(asset):
            unified.append({**asset, "row_type": "asset"})

    for item in list_all_kit_items_enriched(assets_by_id):
        child_id = str(item.get("child_asset_id") or "").strip()
        if child_id and child_id in tool_asset_ids:
            continue
        unified.append(item)

    return unified


def _filter_small_tool_rows(
    rows: list[dict],
    *,
    q: str = "",
    status: str = "All Statuses",
    parent_kit: str = "All Kits",
) -> list[dict]:
    out = list(rows)
    if q:
        ql = q.lower()
        out = [
            r
            for r in out
            if ql in _small_tool_name(r).lower()
            or ql in _small_tool_type(r).lower()
            or ql in _small_tool_parent_kit(r).lower()
            or ql in _small_tool_location(r).lower()
        ]
    status_val = str(status or "All Statuses").strip()
    if status_val and status_val != "All Statuses":
        out = [r for r in out if _small_tool_status(r) == status_val]
    parent_val = str(parent_kit or "All Kits").strip()
    if parent_val and parent_val != "All Kits":
        out = [r for r in out if _small_tool_parent_kit(r) == parent_val]
    return apply_column_filters(out, _SMALL_TOOLS_TABLE_KEY, _SMALL_TOOL_FILTER_SPECS)


def _open_small_tool_row(row: dict, assets_by_id: dict[str, dict]) -> None:
    if str(row.get("row_type") or "") == "kit_item":
        parent_id = str(row.get("parent_asset_id") or "").strip()
        if parent_id:
            _open_assets_detail_modal(parent_id, assets_by_id.get(parent_id))
        return
    aid = str(row.get("id") or "").strip()
    if aid:
        _open_assets_detail_modal(aid, row)


def _asset_location(row: dict) -> str:
    for key in ("location_name", "location"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _asset_department(row: dict) -> str:
    for key in ("department_name", "department"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _asset_assigned_to(row: dict) -> str:
    for key in ("current_operator", "assigned_to_name", "assigned_to", "operator"):
        val = str(row.get(key) or "").strip()
        if val and val != "—":
            return val
    return "—"


def _asset_next_service(row: dict) -> str:
    for key in ("next_service_due", "next_service", "service_due"):
        val = row.get(key)
        if val not in (None, ""):
            formatted = fmt_date(val)
            if formatted != "—":
                return formatted
    return "—"


def _asset_serial(row: dict) -> str:
    val = str(row.get("serial_number") or "").strip()
    return val if val and val != "—" else "—"


def _asset_status_pill_html(status: str) -> str:
    cls_map = {
        "Available": "ips-asset-status-available",
        "In Service": "ips-asset-status-in-service",
        "Assigned": "ips-asset-status-assigned",
        "Out for Repair": "ips-asset-status-out-for-repair",
        "Maintenance Due": "ips-asset-status-maintenance-due",
        "Retired": "ips-asset-status-retired",
        "Sold": "ips-asset-status-sold",
        "Lost": "ips-asset-status-lost",
    }
    cls = cls_map.get(status, "ips-asset-status-available")
    return f'<span class="ips-asset-status-pill {cls}">{html.escape(status)}</span>'


def _render_asset_thumbnail(asset: dict) -> None:
    image_url = get_asset_image_url(asset)
    if image_url:
        st.markdown(
            (
                f'<span class="ips-asset-thumb-cell">'
                f'<img class="ips-asset-thumb-img" src="{html.escape(image_url, quote=True)}" '
                f'alt="Asset image" />'
                f"</span>"
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="ips-asset-thumb-cell">'
            '<span class="ips-asset-thumb-placeholder">—</span>'
            "</span>",
            unsafe_allow_html=True,
        )


def _current_user_id() -> str | None:
    try:
        from app.auth import current_profile
    except ImportError:
        from auth import current_profile  # type: ignore
    uid = str((current_profile() or {}).get("id") or "").strip()
    return uid or None


def _render_asset_photo_manager(asset: dict) -> None:
    aid = str(asset.get("id") or "").strip()
    rk = record_session_key(asset, "id", "asset_number")
    display = asset_display_record(asset)
    render_item_photo_manager(
        asset,
        record_id=aid,
        session_prefix=f"ast_photo_{rk}",
        image_css_class="ips-asset-detail-image",
        upload_image=upload_asset_image_file,
        clear_image=clear_asset_image,
        uploaded_by=_current_user_id(),
        cache_key=_ASSETS_CACHE_KEY,
        on_change=clear_assets_cache,
        readonly=is_demo_id(aid),
        preview_record=display,
    )
    if asset_image_is_inherited(asset):
        st.caption("Photo from linked Pricing Guide or inventory record.")


def _render_asset_detail_image(asset: dict) -> None:
    _render_asset_photo_manager(asset)


def _asset_select_key(asset_id: str) -> str:
    return f"asset_select_{asset_id}"


def _clear_asset_selection(asset_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_ASSET_KEY] = None
    st.session_state[SHOW_ASSET_MODAL_KEY] = False
    ids = list(asset_ids or [])
    for aid in ids:
        st.session_state[_asset_select_key(aid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("asset_select_"):
            st.session_state[key] = False


def _on_asset_checkbox_change(asset_id: str, all_asset_ids: list[str]) -> None:
    key = _asset_select_key(asset_id)
    if st.session_state.get(key):
        for aid in all_asset_ids:
            if aid != asset_id:
                st.session_state[_asset_select_key(aid)] = False
        st.session_state[SELECTED_ASSET_KEY] = asset_id
        st.session_state[SHOW_ASSET_MODAL_KEY] = True
        cache = st.session_state.get(_ASSETS_CACHE_KEY) or {}
        asset = cache.get(asset_id) if isinstance(cache, dict) else None
        _open_assets_detail_modal(asset_id, asset)
    elif st.session_state.get(SELECTED_ASSET_KEY) == asset_id:
        st.session_state[SELECTED_ASSET_KEY] = None
        st.session_state[SHOW_ASSET_MODAL_KEY] = False


def _render_asset_expand_panel(asset: dict) -> None:
    aid = str(asset.get("id") or "").strip()
    status = str(asset.get("status") or "")
    details_html = (
        f'<div class="ips-detail-grid">'
        f"{detail_field_html('Asset #', asset.get('asset_number'))}"
        f"{detail_field_html('Name', _asset_name(asset))}"
        f"{detail_field_html('Category', _asset_category(asset))}"
        f"{detail_field_html('Location', _asset_location(asset))}"
        f'{detail_field_html("Status", status, html_value=status_badge_html(status))}'
        f"{detail_field_html('Assigned To', _asset_assigned_to(asset))}"
        f"{detail_field_html('Next Service', _asset_next_service(asset))}"
        f"</div>"
    )
    st.markdown(dialog_card_html("Asset at a glance", details_html), unsafe_allow_html=True)
    if st.button("Full asset details", key=f"ast_full_modal_{aid}", use_container_width=True):
        _open_assets_detail_modal(aid, asset)
        st.rerun()


def _render_custom_assets_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
) -> list[str]:
    if not filtered:
        st.info("No assets match your filters.")
        st.session_state[_ALL_ASSET_IDS_KEY] = []
        return []

    all_asset_ids = [str(a.get("id") or "").strip() for a in filtered if str(a.get("id") or "").strip()]
    st.session_state[_ALL_ASSET_IDS_KEY] = all_asset_ids

    with st.container(key="assets_table_wrap"):
        st.markdown('<div class="ips-assets-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_ASSET_COLS, gap="small", vertical_alignment="center")
        for col, (label, field) in zip(header_cols, _ASSET_HEADER_SPECS):
            with col:
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-assets-header-row ips-assets-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-assets-header-row ips-assets-cell",
                    )

        for asset in filtered:
            aid = str(asset.get("id") or "").strip()
            if not aid:
                continue

            name = _asset_name(asset)
            category = _asset_category(asset)
            location = _asset_location(asset)
            department = _asset_department(asset)
            status = _normalize_asset_status(asset.get("status"))
            assigned = _asset_assigned_to(asset)
            next_service = _asset_next_service(asset)
            field_mode = is_field_context()
            expanded = field_mode and field_expanded_id(FIELD_EXPANDED_ASSET_KEY) == aid

            cols = st.columns(_ASSET_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                if field_mode:
                    if st.button(
                        "▾" if expanded else "▸",
                        key=f"ast_expand_{aid}",
                        help="Expand asset details",
                    ):
                        toggle_field_expanded(FIELD_EXPANDED_ASSET_KEY, aid)
                        st.rerun()
                else:
                    st.checkbox(
                        "",
                        key=_asset_select_key(aid),
                        label_visibility="collapsed",
                        on_change=_on_asset_checkbox_change,
                        args=(aid, all_asset_ids),
                    )

            with cols[1]:
                _render_asset_thumbnail(asset)

            with cols[2]:
                st.markdown(
                    f'<div class="ips-assets-title">{html.escape(name)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(
                    f'<div class="ips-assets-cell">{html.escape(category)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(
                    f'<div class="ips-assets-cell">{html.escape(location)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[5]:
                st.markdown(
                    f'<div class="ips-assets-cell">{html.escape(department)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[6]:
                st.markdown(_asset_status_pill_html(status), unsafe_allow_html=True)

            with cols[7]:
                st.markdown(
                    f'<div class="ips-assets-muted ips-assets-cell">{html.escape(assigned)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[8]:
                st.markdown(
                    f'<div class="ips-assets-muted ips-assets-cell">{html.escape(next_service)}</div>',
                    unsafe_allow_html=True,
                )

            if expanded:
                st.markdown('<div class="ips-field-row-expand">', unsafe_allow_html=True)
                _render_asset_expand_panel(asset)
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    return all_asset_ids


def _render_small_tools_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
    assets_by_id: dict[str, dict],
) -> None:
    if not filtered:
        st.info("No small tools match your filters.")
        return

    with st.container(key="assets_small_tools_table_wrap"):
        st.markdown('<div class="ips-assets-table-wrap ips-small-tools-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_SMALL_TOOL_COLS, gap="small", vertical_alignment="center")
        for col, (label, field) in zip(header_cols, _SMALL_TOOL_HEADER_SPECS):
            with col:
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_SMALL_TOOLS_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-assets-header-row ips-assets-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-assets-header-row ips-assets-cell",
                    )

        for row in filtered:
            rid = _small_tool_row_id(row)
            if not rid:
                continue
            name = _small_tool_name(row)
            tool_type = _small_tool_type(row)
            parent_kit = _small_tool_parent_kit(row)
            location = _small_tool_location(row)
            status = _small_tool_status(row)
            value = _small_tool_value(row)

            cols = st.columns(_SMALL_TOOL_COLS, gap="small", vertical_alignment="center")
            with cols[0]:
                if st.button("View", key=f"st_open_{rid}", use_container_width=True):
                    _open_small_tool_row(row, assets_by_id)
                    st.rerun()
            with cols[1]:
                st.markdown(
                    f'<div class="ips-assets-title">{html.escape(name)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[2]:
                st.markdown(
                    f'<div class="ips-assets-cell">{html.escape(tool_type)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[3]:
                st.markdown(
                    f'<div class="ips-assets-muted ips-assets-cell">{html.escape(parent_kit)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[4]:
                st.markdown(
                    f'<div class="ips-assets-cell">{html.escape(location)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[5]:
                st.markdown(_asset_status_pill_html(status), unsafe_allow_html=True)
            with cols[6]:
                st.markdown(
                    f'<div class="ips-assets-cell ips-assets-hours">{html.escape(value)}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)


def _render_equipment_list(
    rows: list[dict],
) -> None:
    equipment_rows = [r for r in rows if not _is_small_tool_asset(r)]
    filter_options = build_filter_options(equipment_rows, _COLUMN_FILTER_SPECS)
    categories = sorted(
        {_asset_category(r) for r in equipment_rows if _asset_category(r) and _asset_category(r) != "—"}
    )
    locations = sorted(
        {_asset_location(r) for r in equipment_rows if _asset_location(r) and _asset_location(r) != "—"}
    )
    departments = sorted(
        {_asset_department(r) for r in equipment_rows if _asset_department(r) and _asset_department(r) != "—"}
    )
    status_options = sorted(
        {_normalize_asset_status(r.get("status")) for r in equipment_rows if _normalize_asset_status(r.get("status"))}
    )

    def _filters() -> None:
        c1, c2, c3, c4, c5, c6 = st.columns([2.2, 1.1, 1.1, 1.1, 1.1, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search asset #, name, category, location…",
                key="ast_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "Category",
                ["All Categories", *categories],
                key="ast_bar_category",
                label_visibility="collapsed",
            )
        with c3:
            st.selectbox(
                "Location",
                ["All Locations", *locations],
                key="ast_bar_location",
                label_visibility="collapsed",
            )
        with c4:
            st.selectbox(
                "Status",
                ["All Statuses", *status_options],
                key="ast_bar_status",
                label_visibility="collapsed",
            )
        with c5:
            st.selectbox(
                "Department",
                ["All Departments", *departments],
                key="ast_bar_department",
                label_visibility="collapsed",
            )
        with c6:
            if st.button("Clear", key="ast_clear", use_container_width=True):
                clear_table_filters(
                    _TABLE_KEY,
                    _ASSET_BAR_FILTER_FIELDS,
                    extra_keys=[
                        "ast_search",
                        "ast_bar_category",
                        "ast_bar_location",
                        "ast_bar_status",
                        "ast_bar_department",
                    ],
                )
                st.session_state["ast_bar_category"] = "All Categories"
                st.session_state["ast_bar_location"] = "All Locations"
                st.session_state["ast_bar_status"] = "All Statuses"
                st.session_state["ast_bar_department"] = "All Departments"
                reset_table_page(_TABLE_KEY)
                _clear_asset_selection(st.session_state.get(_ALL_ASSET_IDS_KEY))
                clear_field_expanded(FIELD_EXPANDED_ASSET_KEY)
                st.rerun()

    layout_filter_bar(_filters)

    filtered = _filter_rows(
        equipment_rows,
        q=str(st.session_state.get("ast_search") or "").strip(),
        category=str(st.session_state.get("ast_bar_category") or "All Categories"),
        location=str(st.session_state.get("ast_bar_location") or "All Locations"),
        status=str(st.session_state.get("ast_bar_status") or "All Statuses"),
        department=str(st.session_state.get("ast_bar_department") or "All Departments"),
    )

    render_table_pagination_header(len(filtered), _TABLE_KEY, item_label="asset")
    page_rows, _, _, _ = paginate_rows(filtered, _TABLE_KEY)
    build_modal_cache(filtered, cache_key=_ASSETS_CACHE_KEY)
    _render_custom_assets_table(page_rows, filter_options=filter_options)
    render_table_pagination_footer(len(filtered), _TABLE_KEY)


def _render_small_tools_list(rows: list[dict]) -> None:
    assets_by_id = {
        str(a.get("id") or "").strip(): a for a in rows if str(a.get("id") or "").strip()
    }
    small_tool_rows = _build_small_tool_list(rows)
    filter_options = build_filter_options(small_tool_rows, _SMALL_TOOL_FILTER_SPECS)
    parent_kits = sorted(
        {
            _small_tool_parent_kit(r)
            for r in small_tool_rows
            if _small_tool_parent_kit(r) and _small_tool_parent_kit(r) != "—"
        }
    )
    status_options = sorted({_small_tool_status(r) for r in small_tool_rows if _small_tool_status(r)})

    def _filters() -> None:
        c1, c2, c3, c4 = st.columns([2.4, 1.2, 1.2, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search tool name, kit, location…",
                key="ast_st_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "Parent kit",
                ["All Kits", *parent_kits],
                key="ast_st_parent_kit",
                label_visibility="collapsed",
            )
        with c3:
            st.selectbox(
                "Status",
                ["All Statuses", *status_options],
                key="ast_st_status",
                label_visibility="collapsed",
            )
        with c4:
            if st.button("Clear", key="ast_st_clear", use_container_width=True):
                clear_table_filters(
                    _SMALL_TOOLS_TABLE_KEY,
                    ["item_type", "parent_kit", "location", "status"],
                    extra_keys=["ast_st_search", "ast_st_parent_kit", "ast_st_status"],
                )
                st.session_state["ast_st_parent_kit"] = "All Kits"
                st.session_state["ast_st_status"] = "All Statuses"
                reset_table_page(_SMALL_TOOLS_TABLE_KEY)
                st.rerun()

    st.caption(
        "Hand tools and kit inventory — standalone Tool assets plus items stored in tool trailers and kits."
    )
    layout_filter_bar(_filters)

    filtered = _filter_small_tool_rows(
        small_tool_rows,
        q=str(st.session_state.get("ast_st_search") or "").strip(),
        status=str(st.session_state.get("ast_st_status") or "All Statuses"),
        parent_kit=str(st.session_state.get("ast_st_parent_kit") or "All Kits"),
    )

    render_table_pagination_header(len(filtered), _SMALL_TOOLS_TABLE_KEY, item_label="tool")
    page_rows, _, _, _ = paginate_rows(filtered, _SMALL_TOOLS_TABLE_KEY)
    _render_small_tools_table(page_rows, filter_options=filter_options, assets_by_id=assets_by_id)
    render_table_pagination_footer(len(filtered), _SMALL_TOOLS_TABLE_KEY)


def _apply_assets_search_filter(rows: list[dict], q: str) -> list[dict]:
    query = str(q or "").strip()
    if not query:
        return rows
    ql = query.lower()
    return [
        r
        for r in rows
        if ql in str(r.get("asset_number") or "").lower()
        or ql in str(r.get("asset_name") or "").lower()
        or ql in _asset_category(r).lower()
        or ql in _asset_location(r).lower()
    ]


def _apply_assets_bar_filters(
    rows: list[dict],
    *,
    category: str,
    location: str,
    status: str,
    department: str,
) -> list[dict]:
    out = rows
    category_val = str(category or "All Categories").strip()
    if category_val and category_val != "All Categories":
        out = [r for r in out if _asset_category(r) == category_val]
    location_val = str(location or "All Locations").strip()
    if location_val and location_val != "All Locations":
        out = [r for r in out if _asset_location(r) == location_val]
    status_val = str(status or "All Statuses").strip()
    if status_val and status_val != "All Statuses":
        out = [r for r in out if _normalize_asset_status(r.get("status")) == status_val]
    department_val = str(department or "All Departments").strip()
    if department_val and department_val != "All Departments":
        out = [r for r in out if _asset_department(r) == department_val]
    return out


def _filter_rows(
    rows: list[dict],
    *,
    q: str = "",
    category: str = "All Categories",
    location: str = "All Locations",
    status: str = "All Statuses",
    department: str = "All Departments",
) -> list[dict]:
    out = _apply_assets_search_filter(rows, q)
    out = _apply_assets_bar_filters(
        out,
        category=category,
        location=location,
        status=status,
        department=department,
    )
    return apply_column_filters(out, _TABLE_KEY, _COLUMN_FILTER_SPECS)


def _clear_assets_detail_modal() -> None:
    asset_ids = st.session_state.get(_ALL_ASSET_IDS_KEY) or []
    _clear_asset_selection([str(aid) for aid in asset_ids])
    clear_edit_modes(_MOD)
    clear_record_modal(
        table_key="assets_list",
        session_select_key=_SEL,
        modal_key=_ASSETS_MODAL_KEY,
        module=_MOD,
    )


def _open_assets_detail_modal(asset_id: str, asset: dict | None = None) -> None:
    aid = str(asset_id or "").strip()
    if not aid:
        return
    st.session_state[SELECTED_ASSET_KEY] = aid
    st.session_state[SHOW_ASSET_MODAL_KEY] = True
    open_record_modal(
        aid,
        asset,
        session_select_key=_SEL,
        modal_key=_ASSETS_MODAL_KEY,
        module=_MOD,
        id_fields=("id", "asset_number"),
    )


def _maintenance_rows(asset: dict) -> list[dict[str, str]]:
    operator = str(asset.get("operator") or "Mark Johnson")
    return [
        {
            "date": "Apr 20, 2025",
            "type": "Inspection",
            "description": "Quarterly inspection and safety check",
            "performed_by": operator,
            "cost": "$150.00",
            "next_due": "Jul 20, 2025",
            "status_html": status_badge_html("In Service").replace("In Service", "Completed"),
        },
        {
            "date": "Jan 20, 2025",
            "type": "Service",
            "description": "Grease bearings, check lights and brakes",
            "performed_by": operator,
            "cost": "$175.00",
            "next_due": "Apr 20, 2025",
            "status_html": status_badge_html("In Service").replace("In Service", "Completed"),
        },
        {
            "date": "Oct 20, 2024",
            "type": "Repair",
            "description": "Replaced left tail light and wiring",
            "performed_by": "Coastal Trailer Repair",
            "cost": "$85.00",
            "next_due": "Jan 20, 2025",
            "status_html": status_badge_html("In Service").replace("In Service", "Completed"),
        },
    ]


def _asset_image_html(asset: dict) -> str:
    url = get_asset_image_url(asset)
    if url:
        safe = html.escape(url, quote=True)
        alt = html.escape(str(asset.get("asset_name") or "Asset image"), quote=True)
        return f'<img class="ips-asset-detail-image" src="{safe}" alt="{alt}" />'
    return (
        '<p style="margin:0;color:#64748b;font-size:0.875rem;">No asset image uploaded.</p>'
    )


def _asset_for_qr(asset: dict) -> dict:
    num = str(asset.get("asset_number") or asset.get("asset_id") or "").strip()
    return {**asset, "asset_id": num}


def _render_asset_qr_block(asset: dict, aid: str) -> None:
    try:
        from app.services.asset_qr import (
            qr_embed_subject,
            qr_label_2x1_sticker_download_filename,
            qr_label_2x1_sticker_pdf_bytes,
            qr_label_for_download,
            qr_payload,
            qr_png_bytes,
        )
    except ImportError:
        from services.asset_qr import (  # type: ignore
            qr_embed_subject,
            qr_label_2x1_sticker_download_filename,
            qr_label_2x1_sticker_pdf_bytes,
            qr_label_for_download,
            qr_payload,
            qr_png_bytes,
        )

    qr_asset = _asset_for_qr(asset)
    token = qr_payload(qr_asset)
    if not token:
        return
    subject = qr_embed_subject(qr_asset)
    scan_url = generate_asset_qr_value(asset)
    is_secure_url = scan_url.startswith("http") and "scan=asset" in scan_url and "token=" in scan_url

    with st.container(border=True):
        st.markdown(
            '<span class="ips-assets-qr-tool"></span>'
            '<p style="margin:0 0 0.35rem;font-weight:700;font-size:0.9rem;">Equipment QR</p>',
            unsafe_allow_html=True,
        )
        if not is_secure_url:
            st.warning(
                "This label uses an older QR format. Reprint it to use secure scan links."
            )
        try:
            qr_png = qr_png_bytes(subject)
            if qr_png and scan_url:
                b64 = base64.b64encode(qr_png).decode("ascii")
                safe_url = html.escape(scan_url, quote=True)
                st.markdown(
                    f'<a href="{safe_url}" target="_self" title="Open asset QR page">'
                    f'<img src="data:image/png;base64,{b64}" width="132" alt="Asset QR code" '
                    f'style="display:block;border:1px solid #e2e8f0;border-radius:8px;" />'
                    f"</a>",
                    unsafe_allow_html=True,
                )
            elif qr_png:
                st.image(qr_png, width=132)
        except Exception:
            st.caption(f"Scan code: {token}")
        st.caption(f"Asset tag: **{html.escape(str(asset.get('asset_number') or token))}**", unsafe_allow_html=True)
        if scan_url.startswith("http"):
            st.caption("Scan with a phone camera to open the mobile asset card.")
            st.link_button("Open Asset QR Page", scan_url, use_container_width=True)
        else:
            st.caption("Set APP_BASE_URL so printed labels open the asset card when scanned.")
        if scan_url:
            st.caption("Scan URL")
            st.code(scan_url, language=None)
        act1, act2, act3 = st.columns(3)
        with act1:
            if st.button("Rebuild QR", key=f"ast_qr_rebuild_{aid}", use_container_width=True):
                result = rebuild_asset_qr(asset)
                if result.ok and isinstance(result.data, dict):
                    clear_assets_cache()
                    st.session_state["ips_sel_assets"] = aid
                    st.success("QR label rebuilt. Reprint the sticker when ready.")
                    st.rerun()
                else:
                    st.error(str(getattr(result, "error", None) or "Could not rebuild QR."))
        with act2:
            try:
                dl_bytes, dl_mime, dl_name = qr_label_for_download(qr_asset, subject)
                st.download_button(
                    "Print Label",
                    data=dl_bytes,
                    file_name=dl_name,
                    mime=dl_mime,
                    key=f"ast_qr_label_{aid}",
                    use_container_width=True,
                )
            except Exception:
                st.download_button(
                    "Download QR (PNG)",
                    data=qr_png_bytes(subject),
                    file_name=f"{token}_qr.png",
                    mime="image/png",
                    key=f"ast_qr_png_{aid}",
                    use_container_width=True,
                )
        with act3:
            try:
                st.download_button(
                    "2×1 sticker",
                    data=qr_label_2x1_sticker_pdf_bytes(qr_asset, subject),
                    file_name=qr_label_2x1_sticker_download_filename(qr_asset),
                    mime="application/pdf",
                    key=f"ast_qr_sticker_{aid}",
                    use_container_width=True,
                )
            except Exception:
                pass


def _render_asset_documents_tab(asset: dict) -> None:
    aid = str(asset.get("id") or "")
    try:
        from app.auth import current_role, is_authenticated
    except ImportError:
        from auth import current_role, is_authenticated  # type: ignore
    include_restricted = is_authenticated() and str(current_role() or "").lower() in {
        "admin",
        "supervisor",
        "manager",
    }
    docs = get_asset_documents(aid, include_restricted=include_restricted)
    if not docs:
        placeholder_html("No documents attached to this asset.")
        return
    for doc in docs:
        fname = str(doc.get("file_name") or "Document")
        dtype = str(doc.get("doc_type") or "Document")
        view_url = doc.get("view_url") or get_asset_document_view_url(doc)
        label = f"{dtype} — {fname}" if dtype else fname
        key = f"ast_doc_tab_{doc.get('id') or fname}"
        if doc.get("is_restricted") and not include_restricted:
            st.caption(f"Restricted: {html.escape(fname)}")
            continue
        if view_url:
            st.link_button(f"View {label}", view_url, use_container_width=True, key=key)
        else:
            st.caption(f"{label} (no preview URL)")


def _render_asset_maintenance_tab(asset: dict) -> None:
    aid = str(asset.get("id") or "")
    inspections = get_asset_inspections(aid)
    issues = get_asset_issues(aid)
    if inspections or issues:
        if inspections:
            st.markdown("**Inspections**")
            for row in inspections[:25]:
                st.markdown(
                    f"- **{html.escape(fmt_date(row.get('inspection_date')))}** — "
                    f"{html.escape(str(row.get('condition') or '—'))} · "
                    f"{html.escape(str(row.get('inspector_name') or '—'))}"
                )
        if issues:
            st.markdown("**Reported Issues**")
            for row in issues[:25]:
                st.markdown(
                    f"- **{html.escape(str(row.get('severity') or '—'))}** "
                    f"({html.escape(str(row.get('status') or 'Open'))}) — "
                    f"{html.escape(str(row.get('description') or '')[:160])}"
                )
        return
    st.markdown(
        '<div class="ips-assets-maint-section">'
        '<div class="ips-assets-maint-head"><h4>Maintenance History</h4></div>'
        f"{maintenance_table_html(_maintenance_rows(asset))}"
        "</div>",
        unsafe_allow_html=True,
    )


def _seed_asset_edit_form(asset: dict) -> None:
    aid = str(asset.get("id") or "")
    st.session_state[f"ast_edit_num_{aid}"] = str(asset.get("asset_number") or "")
    st.session_state[f"ast_edit_name_{aid}"] = str(asset.get("asset_name") or "")
    st.session_state[f"ast_edit_cat_{aid}"] = str(asset.get("category") or lookup_options("asset_categories")[0])
    st.session_state[f"ast_edit_status_{aid}"] = str(asset.get("status") or lookup_options("asset_statuses")[0])
    st.session_state[f"ast_edit_loc_{aid}"] = str(asset.get("location") or "")
    st.session_state[f"ast_edit_serial_{aid}"] = str(asset.get("serial_number") or "")
    st.session_state[f"ast_edit_pg_{aid}"] = bool(asset.get("include_in_pricing_guide"))


def _set_asset_view_mode(asset: dict) -> None:
    rk = record_session_key(asset, "id", "asset_number")
    set_view_mode(_MOD, rk)


def _set_asset_edit_mode(asset: dict) -> None:
    rk = record_session_key(asset, "id", "asset_number")
    set_edit_mode(_MOD, rk)
    _seed_asset_edit_form(asset)


def _render_asset_edit_form(asset: dict) -> None:
    aid = str(asset.get("id") or "")
    rk = record_session_key(asset, "id", "asset_number")
    if f"ast_edit_num_{aid}" not in st.session_state:
        _seed_asset_edit_form(asset)

    render_edit_form_header("Edit Asset")

    if is_demo_id(aid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    ac1, ac2 = st.columns(2)
    with ac1:
        st.text_input("Asset #", key=f"ast_edit_num_{aid}")
        st.text_input("Name", key=f"ast_edit_name_{aid}")
        st.selectbox("Category", lookup_options("asset_categories"), key=f"ast_edit_cat_{aid}")
        st.selectbox("Status", lookup_options("asset_statuses"), key=f"ast_edit_status_{aid}")
    with ac2:
        st.text_input("Location", key=f"ast_edit_loc_{aid}")
        st.text_input("Serial", key=f"ast_edit_serial_{aid}")

    st.checkbox(
        "Include on Pricing Guide (billable on estimates)",
        key=f"ast_edit_pg_{aid}",
        help="Turn off for fleet/shop assets that should stay in Assets only.",
    )

    st.markdown("**Item Photo**")
    _render_asset_photo_manager(asset)

    cancelled, saved = render_save_cancel_actions(
        module=_MOD,
        record_key=rk,
        cancel_key=f"ast_edit_cancel_{aid}",
        save_key=f"ast_edit_save_{aid}",
    )
    if cancelled:
        st.rerun()
    if saved:
        ok, msg = persist_asset(
            {
                "asset_number": st.session_state.get(f"ast_edit_num_{aid}"),
                "asset_name": st.session_state.get(f"ast_edit_name_{aid}"),
                "category": st.session_state.get(f"ast_edit_cat_{aid}"),
                "status": st.session_state.get(f"ast_edit_status_{aid}"),
                "location": st.session_state.get(f"ast_edit_loc_{aid}"),
                "serial_number": st.session_state.get(f"ast_edit_serial_{aid}"),
                "include_in_pricing_guide": bool(st.session_state.get(f"ast_edit_pg_{aid}")),
            },
            row_id=aid,
        )
        if ok:
            clear_assets_cache()
            set_view_mode(_MOD, rk)
            st.success(msg or "Asset saved.")
            st.rerun()
        else:
            st.error(msg or "Could not save asset.")


def _render_asset_detail_tabs(asset: dict) -> None:
    aid = str(asset.get("id") or "")
    asset_number = safe_value(asset.get("asset_number"))
    asset_name = safe_value(asset.get("asset_name"))
    status = safe_value(asset.get("status"))

    (
        tab_overview,
        tab_kit,
        tab_maintenance,
        tab_documents,
        tab_assignments,
        tab_depreciation,
        tab_notes,
        tab_activity,
    ) = st.tabs(_ASSET_TABS)

    with tab_overview:
        c1, c2 = st.columns([1.2, 1])
        with c1:
            st.markdown(
                summary_card_html(
                    "Asset Details",
                    [
                        ("Asset Number", asset_number),
                        ("Asset Name", asset_name),
                        ("Category", str(asset.get("category") or "—")),
                        ("Status", status_badge_html(str(asset.get("status") or ""))),
                        ("Location", str(asset.get("location") or "—")),
                        ("Department", str(asset.get("department") or "—")),
                        ("Manufacturer", str(asset.get("manufacturer") or "—")),
                        ("Model", str(asset.get("model") or "—")),
                        ("Serial Number", str(asset.get("serial_number") or "—")),
                        ("Description", str(asset.get("description") or "—")),
                    ],
                    html_value_keys=frozenset({"Status"}),
                ),
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                summary_card_html(
                    "Usage Information",
                    [
                        ("Current Operator", str(asset.get("operator") or "—")),
                        ("Primary Use", str(asset.get("primary_use") or asset.get("description") or "Equipment Transport")),
                        ("Hours/Miles", str(asset.get("hours_miles") or "—")),
                        ("Last Used", str(asset.get("last_used") or "—")),
                        ("Condition", str(asset.get("condition") or "Good")),
                        ("Next Service Due", str(asset.get("next_service_due") or "—")),
                    ],
                ),
                unsafe_allow_html=True,
            )

        c3, c4 = st.columns([1, 1])
        with c3:
            st.markdown(
                summary_card_html(
                    "Financial Information",
                    [
                        ("Acquired Date", fmt_date(asset.get("acquired_date"))),
                        ("Purchase Price", fmt_currency(asset.get("purchase_price") or asset.get("value"))),
                        ("Current Value", fmt_currency(asset.get("value"))),
                        ("Salvage Value", fmt_currency(asset.get("salvage_value"))),
                        ("Depreciation Method", str(asset.get("depreciation_method") or "Straight Line")),
                        ("Useful Life", str(asset.get("useful_life") or "7 years")),
                        ("Annual Depreciation", fmt_currency(asset.get("annual_depreciation"))),
                    ],
                ),
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown("#### Image")
            _render_asset_photo_manager(asset)
            _render_asset_qr_block(asset, aid)

    with tab_kit:
        render_kit_contents_tab(asset)

    with tab_maintenance:
        _render_asset_maintenance_tab(asset)

    with tab_documents:
        _render_asset_documents_tab(asset)

    with tab_assignments:
        assign_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Current Operator', asset.get('operator'))}"
            f"{detail_field_html('Department', asset.get('department'))}"
            f"{detail_field_html('Location', asset.get('location'))}"
            f"{detail_field_html('Primary Use', asset.get('primary_use') or asset.get('description'))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Assignments", assign_html), unsafe_allow_html=True)

    with tab_depreciation:
        dep_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Acquired Date', fmt_date(asset.get('acquired_date')))}"
            f"{detail_field_html('Purchase Price', fmt_currency(asset.get('purchase_price') or asset.get('value')))}"
            f"{detail_field_html('Current Value', fmt_currency(asset.get('value')))}"
            f"{detail_field_html('Salvage Value', fmt_currency(asset.get('salvage_value')))}"
            f"{detail_field_html('Depreciation Method', asset.get('depreciation_method') or 'Straight Line')}"
            f"{detail_field_html('Useful Life', asset.get('useful_life') or '7 years')}"
            f"{detail_field_html('Annual Depreciation', fmt_currency(asset.get('annual_depreciation')))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Depreciation", dep_html), unsafe_allow_html=True)

    with tab_notes:
        notes_text = safe_value(asset.get("description"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Asset activity history will appear here when connected to Supabase.")


def _render_asset_actions_panel(asset: dict) -> None:
    rk = record_session_key(asset, "id", "asset_number")
    if is_edit_mode(_MOD, rk):
        return
    aid = str(asset.get("id") or "").strip()
    if not aid or is_demo_id(aid):
        return

    def _after_action() -> None:
        _clear_assets_detail_modal()

    render_asset_action_buttons(asset, on_retire=_after_action, on_delete=_after_action)
    render_asset_pricing_guide_actions(asset)


def render_asset_detail_dialog(asset: dict) -> None:
    rk = record_session_key(asset, "id", "asset_number")
    asset_number = safe_value(asset.get("asset_number"))
    asset_name = safe_value(asset.get("asset_name"))
    status = safe_value(asset.get("status"))

    render_modal_shell()
    render_modal_header(title=asset_number, subtitle=asset_name, status=status)

    render_modal_edit_button(
        module=_MOD,
        record_key=rk,
        on_edit=lambda: _set_asset_edit_mode(asset),
        key_prefix=f"assets_modal_{rk}",
    )

    render_modal_meta_grid(
        [
            ("Category", safe_value(asset.get("category"))),
            ("Location", safe_value(asset.get("location"))),
            ("Department", safe_value(asset.get("department"))),
            ("Current Value", fmt_currency(asset.get("value"))),
        ]
    )

    if is_edit_mode(_MOD, rk):
        _render_asset_edit_form(asset)
    else:
        _render_asset_actions_panel(asset)
        _render_asset_detail_tabs(asset)


@st.dialog("Asset Details", width="large", on_dismiss=_clear_assets_detail_modal)
def _show_assets_detail_modal() -> None:
    asset = get_modal_record(
        cache_key=_ASSETS_CACHE_KEY,
        modal_key=_ASSETS_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not asset:
        sel = str(st.session_state.get(_ASSETS_MODAL_KEY) or st.session_state.get(_SEL) or "").strip()
        rows = st.session_state.get(_ASSETS_CACHE_KEY)
        if isinstance(rows, dict) and sel:
            asset = rows.get(sel)
    if not asset:
        render_missing_record(_clear_assets_detail_modal, close_key="assets_modal_missing_close")
        return
    render_asset_detail_dialog(asset)


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("assets"):
        return
    try:
        from app.services.asset_qr import apply_pending_asset_deeplink
    except ImportError:
        from services.asset_qr import apply_pending_asset_deeplink  # type: ignore
    apply_pending_asset_deeplink()
    inject_assets_page_styles()
    inject_assets_module_css()
    if is_field_context():
        inject_field_row_expand_css()
    st.markdown(
        '<span class="ips-assets-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    rows = load_assets()

    def _assets_export() -> None:
        st.button("Export", key="ast_export", use_container_width=True)

    def _assets_new() -> None:
        if st.button("+ New Asset", key="ast_new", type="primary", use_container_width=True):
            st.session_state["ips_ast_form"] = True

    render_page_brand_header(
        "Assets",
        "Track and manage all company assets and equipment.",
        actions=[_assets_export, _assets_new],
    )

    if is_field_context():
        render_field_scan_bar(("🔧 Scan Asset", "scan_asset"))

    if st.session_state.get("ips_ast_form"):
        with st.expander("New Asset", expanded=True):
            st.text_input("Asset #", key="ast_new_num")
            st.text_input("Asset name", key="ast_new_name")
            st.selectbox("Category", lookup_options("asset_categories"), key="ast_new_cat")
            st.selectbox("Status", lookup_options("asset_statuses"), key="ast_new_status")
            st.file_uploader(
                "Upload asset image",
                type=list(ITEM_IMAGE_UPLOAD_TYPES),
                key="ast_new_image",
            )
            if st.button("Save asset", key="ast_save_new", type="primary"):
                try:
                    from app.services.assets_service import save_asset
                except ImportError:
                    from services.assets_service import save_asset  # type: ignore
                result = save_asset(
                    {
                        "asset_number": st.session_state.get("ast_new_num"),
                        "asset_name": st.session_state.get("ast_new_name"),
                        "category": st.session_state.get("ast_new_cat"),
                        "status": st.session_state.get("ast_new_status"),
                    }
                )
                if not result.ok:
                    st.error(result.error or "Could not save asset.")
                else:
                    new_id = ""
                    if isinstance(result.data, dict):
                        new_id = str(result.data.get("id") or "").strip()
                    uploaded_file = st.session_state.get("ast_new_image")
                    if uploaded_file is not None and new_id and not is_demo_id(new_id):
                        upload_result = upload_asset_image(
                            new_id,
                            uploaded_file,
                            uploaded_by=_current_user_id(),
                        )
                        if not upload_result.ok:
                            st.warning(upload_result.error or "Asset saved, but image upload failed.")
                    clear_assets_cache()
                    st.session_state.pop("ips_ast_form", None)
                    st.success("Asset saved.")
                    st.rerun()

    build_modal_cache(rows, cache_key=_ASSETS_CACHE_KEY)

    deeplink_sel = str(st.session_state.get(_SEL) or "").strip()
    if deeplink_sel and not str(st.session_state.get(_ASSETS_MODAL_KEY) or "").strip():
        cached = st.session_state.get(_ASSETS_CACHE_KEY)
        if isinstance(cached, dict) and deeplink_sel in cached:
            _open_assets_detail_modal(deeplink_sel, cached[deeplink_sel])

    tab_equipment, tab_small_tools = st.tabs(["Equipment", "Small Tools"])

    with tab_equipment:
        with st.expander("Tool Trailers & Kits", expanded=False):
            if st.button("Load kit summary", key="ast_kit_summary_load", use_container_width=True):
                st.session_state["ast_kit_summary_on"] = True
            if st.session_state.get("ast_kit_summary_on"):
                render_kit_accountability_summary()
            else:
                st.caption("Load kit accountability metrics on demand to speed up the assets page.")
        _render_equipment_list(rows)

    with tab_small_tools:
        _render_small_tools_list(rows)

    selected_asset_id = st.session_state.get(SELECTED_ASSET_KEY)
    if selected_asset_id and st.session_state.get(SHOW_ASSET_MODAL_KEY):
        _show_assets_detail_modal()
    elif str(st.session_state.get(_ASSETS_MODAL_KEY) or "").strip():
        _show_assets_detail_modal()
