"""Assets module (Phase 2B)."""

from __future__ import annotations

import base64
import html
from datetime import date
from typing import Any

import streamlit as st

from app.components.asset_actions import (
    asset_retire_delete_action_specs,
    is_asset_action_confirm_open,
    open_asset_action_confirm,
    render_asset_action_confirm_panel,
)
from app.components.asset_pricing_guide_actions import (
    handle_pricing_guide_header_click,
    is_asset_pricing_guide_confirm_open,
    pricing_guide_header_action_spec,
    render_asset_pricing_guide_actions,
    render_asset_pricing_guide_confirm_panel,
)
from app.components.asset_documents_tab import asset_documents_count, render_asset_documents_tab
from app.components.item_photo_manager import render_item_photo_manager
from app.components.layout import render_filter_bar as layout_filter_bar
from app.components.table_filters import (
    apply_column_filters,
    clear_table_filters,
    render_table_header_cell,
)
from app.components.table_pagination import (
    render_table_pagination_footer,
    render_table_pagination_header,
    reset_table_page,
)
from app.components.record_modal import (
    clear_edit_modes,
    clear_record_modal,
    detail_field_html,
    dialog_card_html,
    get_modal_record,
    is_edit_mode,
    open_record_modal,
    record_session_key,
    render_edit_form_header,
    render_missing_record,
    render_compact_modal_header,
    render_modal_meta_grid,
    render_modal_shell,
    render_save_cancel_actions,
    safe_value,
    set_edit_mode,
    set_view_mode,
    show_modal_if_pending,
)
from app.pages._core._data import lookup_options, persist_asset
from app.pages._core._crud import is_demo_id
from app.pages._core._session import select_key
from app.components.assets_css import inject_assets_page_css
from app.services.asset_images import (
    asset_display_record,
    asset_image_is_inherited,
    clear_asset_image,
    upload_asset_image as upload_asset_image_file,
)
from app.services.item_images import ITEM_IMAGE_UPLOAD_TYPES
from app.services.assets_service import (
    ASSETS_MODAL_CACHE_KEY,
    generate_asset_qr_value,
    rebuild_asset_qr,
    get_asset_inspections,
    get_asset_issues,
    upload_asset_image,
)
from app.ui.assets_components import (
    maintenance_table_html,
    status_badge_html,
    summary_card_html,
)
from app.ui.streamlit_perf import fragment, fragment_rerun, ips_app_rerun
from app.utils.formatting import fmt_currency, fmt_date
from app.services.asset_rental_service import (
    RENTAL_RATE_UNITS,
    normalize_rental_rate_unit,
    primary_rental_rate_from_asset,
)
from app.services.phase2_modules_service import asset_is_rentable
from app.components.serialized_tools_ui import (
    render_serialized_tool_tracking_panel,
    render_serialized_tools_toolbar,
)
from app.components.small_hand_tools_ui import open_hand_tool_detail, render_hand_tools_tab
from app.components.asset_reclassification_ui import (
    apply_tracking_bucket_change,
    render_asset_reclassification_panel,
    render_asset_tracking_bucket_select,
    render_equipment_bulk_move_toolbar,
    seed_tracking_form_state,
)
from app.components.asset_row_actions_ui import ASSET_OPEN_ACTIVITY_KEY, render_asset_activity_snippet
from app.components.assets_list_table import (
    build_assets_html_table,
    render_assets_table_bridge_legacy,
)
from app.components.serialized_tools_list_table import (
    SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX,
    build_serialized_tools_html_table,
    render_serialized_tools_table_bridge_legacy,
)
from app.services.assets_directory_service import list_equipment_page
from app.services.serialized_tools_directory_service import list_serialized_tools_page
from app.components.assets_page_layout import (
    close_assets_filter_bar_shell,
    render_assets_filter_bar_shell,
)
from app.components.quick_add_tool_ui import (
    QUICK_ADD_OPEN_KEY,
    open_quick_add_tool_dialog,
    show_quick_add_tool_dialog,
)
from app.components.small_hand_tools_import_ui import (
    HAND_TOOL_IMPORT_OPEN_KEY,
    hand_tool_csv_template_bytes,
    open_hand_tool_import_dialog,
    show_hand_tool_import_dialog,
)
from app.pages.asset_kits_ui import render_kit_accountability_summary, render_kit_contents_tab
from app.services.asset_classification_service import tracking_type_label
from app.services.serialized_tool_service import is_serialized_tool_asset
from app.utils.field_context import (
    FIELD_EXPANDED_ASSET_KEY,
    clear_field_expanded,
    field_expanded_id,
    inject_field_row_expand_css,
    is_field_context,
    render_field_scan_bar,
    toggle_field_expanded,
)
_SEL = select_key("assets")
_MOD = "assets"
_ASSETS_MODAL_KEY = "ips_assets_detail_modal_id"
_ASSETS_CACHE_KEY = ASSETS_MODAL_CACHE_KEY
SELECTED_ASSET_KEY = "selected_asset_id"
SELECTED_ASSET_IDS_KEY = "selected_asset_ids"
SHOW_ASSET_MODAL_KEY = "show_asset_detail_modal"
_ASSET_DETAIL_QUERY_KEY = "asset_detail"
_ASSET_DETAIL_QUERY_ERROR_KEY = "_ips_asset_detail_query_error"
_ASSET_DETAIL_ACTIVE_TAB_KEY = "ips_asset_detail_active_tab"
_BULK_MOVE_OPEN_KEY = "ips_assets_bulk_move_open"
_ASSETS_MAIN_TAB_KEY = "ips_assets_main_tab"
_ASSETS_MAIN_TABS = ("Equipment", "Serialized Tools", "Small Tools")
ASSET_DETAIL_TAB_FOCUS_KEY = "ast_detail_tab_focus"
_SHOW_NEW_ASSET_FORM_KEY = "assets_show_new_asset_form"
_ALL_ASSET_IDS_KEY = "_ips_assets_visible_ids"
_ALL_SMALL_TOOL_IDS_KEY = "_ips_small_tools_visible_ids"
_TABLE_KEY = "assets_list"
_SMALL_TOOLS_TABLE_KEY = "assets_small_tools_list"
_SMALL_TOOL_FILTER_COLUMN_LAYOUT: list[tuple[str | None, str | None]] = [
    (None, None),
    (None, None),
    (None, None),
    ("MODEL #", "model_number"),
    (None, None),
    ("TRAILER", "trailer"),
    ("JOB", "job"),
    ("STATUS", "status"),
    ("CONDITION", "condition"),
]
_SMALL_TOOL_FILTER_COL_WEIGHTS: list[int] = [
    SERIALIZED_TOOLS_TABLE_COL_WIDTHS_PX[key]
    for key in ("select", "image", "name", "model", "serial", "trailer", "job", "status", "condition")
]
_ASSETS_FILTER_SPECS: list[tuple[str, str]] = [
    ("CATEGORY", "category"),
    ("LOCATION", "location"),
    ("STATUS", "status"),
    ("DEPARTMENT", "department"),
]
_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("category", lambda r: _asset_category(r)),
    ("location", lambda r: _asset_location(r)),
    ("status", lambda r: _normalize_asset_status(r.get("status"))),
    ("department", lambda r: _asset_department(r)),
]
_ASSET_BAR_FILTER_FIELDS = ["status"]
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
    from app.services.status_maps import normalize_asset_status
    return normalize_asset_status(raw)


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


def _asset_rentable_badge_html(row: dict) -> str:
    if not asset_is_rentable(row):
        return ""
    return '<span class="ips-asset-rental-badge" title="Rental equipment">RENTAL</span>'


def _small_tool_select_key(row_id: str) -> str:
    return f"small_tool_select_{row_id}"


def _small_tool_modal_asset_id(row: dict) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        return str(row.get("parent_asset_id") or "").strip()
    return str(row.get("id") or "").strip()


def _clear_small_tool_selection(row_ids: list[str] | None = None) -> None:
    for rid in list(row_ids or []):
        st.session_state[_small_tool_select_key(rid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("small_tool_select_"):
            st.session_state[key] = False


def _rerun_if_assets_modal_pending() -> None:
    """Escalate fragment widget interactions to a full app rerun for @st.dialog."""
    if st.session_state.get(SHOW_ASSET_MODAL_KEY) or str(
        st.session_state.get(_ASSETS_MODAL_KEY) or ""
    ).strip():
        ips_app_rerun()


def _show_assets_modal_if_selected() -> None:
    if not st.session_state.get(SHOW_ASSET_MODAL_KEY):
        return
    if not str(st.session_state.get(_ASSETS_MODAL_KEY) or "").strip():
        return
    show_modal_if_pending(_ASSETS_MODAL_KEY, _show_assets_detail_modal)


def _prepare_open_hand_tool_row(row: dict) -> None:
    """Set hand tool or parent trailer detail state without rerunning."""
    if not row.get("editable", True):
        parent_id = str(row.get("container_asset_id") or row.get("parent_asset_id") or "").strip()
        if parent_id:
            asset = _cached_asset_for_modal(parent_id)
            _open_assets_detail_modal(parent_id, asset, tab_focus="Kit")
        return
    open_hand_tool_detail(row)


def _open_hand_tool_row(row: dict) -> None:
    _prepare_open_hand_tool_row(row)


def _prepare_open_small_tool_row(row: dict, assets_by_id: dict[str, dict] | None = None) -> None:
    """Set serialized tool detail modal state (caller must app-rerun to show dialog)."""
    lookup = assets_by_id or {}
    if str(row.get("row_type") or "") == "kit_item":
        parent_id = str(row.get("parent_asset_id") or "").strip()
        if parent_id:
            parent = lookup.get(parent_id) or _cached_asset_for_modal(parent_id)
            _open_assets_detail_modal(parent_id, parent, tab_focus="Kit")
        return
    aid = str(row.get("id") or row.get("_detail_asset_id") or "").strip()
    if aid:
        asset = lookup.get(aid) or row if str(row.get("row_type") or "") == "asset" else None
        if asset is None:
            asset = _cached_asset_for_modal(aid)
        _open_assets_detail_modal(aid, asset)


def _open_serialized_tool_table_row(_row_id: str, row: dict, assets_by_id: dict[str, dict]) -> None:
    _prepare_open_small_tool_row(row, assets_by_id)


def _select_serialized_tool_table_row(
    row_id: str,
    checked: bool,
    *,
    all_row_ids: list[str],
    row_by_id: dict[str, dict],
    assets_by_id: dict[str, dict],
) -> None:
    st.session_state[_small_tool_select_key(row_id)] = checked
    if checked:
        for other_id in all_row_ids:
            if other_id != row_id:
                st.session_state[_small_tool_select_key(other_id)] = False
        row = row_by_id.get(row_id)
        if row:
            _prepare_open_small_tool_row(row, assets_by_id)
        return
    row = row_by_id.get(row_id)
    if not row:
        return
    modal_aid = _small_tool_modal_asset_id(row)
    if modal_aid and st.session_state.get(SELECTED_ASSET_KEY) == modal_aid:
        st.session_state[SELECTED_ASSET_KEY] = None
        st.session_state[SHOW_ASSET_MODAL_KEY] = False
        clear_record_modal(
            table_key=_SMALL_TOOLS_TABLE_KEY,
            session_select_key=_SEL,
            modal_key=_ASSETS_MODAL_KEY,
            module=_MOD,
        )


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


def _asset_image_src(asset: dict) -> str | None:
    """Resolve a browser-safe thumbnail URL via the unified catalog image resolver."""
    from app.services.catalog_images import get_catalog_image_url
    return get_catalog_image_url(asset, kind="asset")


def _current_user_id() -> str | None:
    from app.auth import current_profile

    prof = current_profile() or {}
    uid = str(prof.get("id") or prof.get("user_id") or "").strip()
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
        on_change=_clear_assets_catalog_cache,
        readonly=is_demo_id(aid),
        preview_record=display,
    )
    if asset_image_is_inherited(asset):
        st.caption("Photo from linked Pricing Guide or inventory record.")


def _asset_select_key(asset_id: str) -> str:
    return f"asset_select_{asset_id}"


def _get_selected_asset_ids() -> list[str]:
    raw = st.session_state.get(SELECTED_ASSET_IDS_KEY)
    if isinstance(raw, (set, list, tuple)):
        return sorted({str(x).strip() for x in raw if str(x).strip()})
    legacy = st.session_state.get(SELECTED_ASSET_KEY)
    return [str(legacy).strip()] if legacy else []


def _clear_asset_selection(asset_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_ASSET_KEY] = None
    st.session_state[SELECTED_ASSET_IDS_KEY] = set()
    st.session_state[SHOW_ASSET_MODAL_KEY] = False
    ids = list(asset_ids or [])
    for aid in ids:
        st.session_state[_asset_select_key(aid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("asset_select_"):
            st.session_state[key] = False


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
        f"{detail_field_html('Rentable', 'Yes' if asset_is_rentable(asset) else 'No')}"
    )
    if asset_is_rentable(asset):
        rate_unit = normalize_rental_rate_unit(asset.get("rental_rate_unit"))
        rate_amt = primary_rental_rate_from_asset(asset)
        details_html += (
            f"{detail_field_html('Rental rate', fmt_currency(rate_amt) if rate_amt else '—')}"
            f"{detail_field_html('Rate unit', rate_unit)}"
            f"{detail_field_html('Default markup %', asset.get('rental_default_markup_percent') or '0')}"
        )
        notes_rn = str(asset.get("rental_notes") or "").strip()
        if notes_rn:
            details_html += detail_field_html("Rental notes", notes_rn)
    details_html += (
        f"{detail_field_html('Assigned To', _asset_assigned_to(asset))}"
        f"{detail_field_html('Next Service', _asset_next_service(asset))}"
        f"</div>"
    )
    st.markdown(dialog_card_html("Asset at a glance", details_html), unsafe_allow_html=True)
    st.markdown('<div class="ips-nav-name-button">', unsafe_allow_html=True)
    if st.button("Full asset details", key=f"ast_full_modal_{aid}", use_container_width=True):
        _open_assets_detail_modal(aid, asset)
        ips_app_rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_assets_table_column_filters(
    *,
    filter_options: dict[str, list[str]],
) -> None:
    if not _ASSETS_FILTER_SPECS:
        return
    st.markdown('<div class="ips-assets-table-filter-toolbar">', unsafe_allow_html=True)
    cols = st.columns(len(_ASSETS_FILTER_SPECS), gap="small")
    for col, (label, field) in zip(cols, _ASSETS_FILTER_SPECS):
        with col:
            render_table_header_cell(
                label,
                table_key=_TABLE_KEY,
                filter_field=field,
                filter_options=filter_options.get(field, []),
                base_class="ips-assets-filter-toolbar-cell",
            )
    st.markdown("</div>", unsafe_allow_html=True)


def _on_assets_table_expand(asset_id: str, asset: dict) -> None:
    toggle_field_expanded(FIELD_EXPANDED_ASSET_KEY, asset_id)


def _prepare_open_assets_table_item(asset_id: str, asset: dict) -> None:
    """Set selected asset state for the detail dialog."""
    _handle_open_asset(asset)


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

    assets_by_id = {
        str(a.get("id") or "").strip(): a
        for a in filtered
        if str(a.get("id") or "").strip()
    }
    field_mode = is_field_context()
    expanded_asset_id = str(field_expanded_id(FIELD_EXPANDED_ASSET_KEY) or "").strip() if field_mode else ""

    with st.container(key="assets_table_wrap"):
        _render_assets_table_column_filters(filter_options=filter_options)
        from app.perf_debug import perf_span

        with perf_span("assets.table_html"):
            st.markdown(
                build_assets_html_table(
                    filtered,
                    field_mode=field_mode,
                    expanded_asset_id=expanded_asset_id,
                ),
                unsafe_allow_html=True,
            )
        if field_mode:
            render_assets_table_bridge_legacy(
                assets_by_id,
                component_key="ips_assets_list_bridge",
                hook_key="ipsAssetsList::action",
                open_asset_fn=_prepare_open_assets_table_item,
                on_expand_fn=_on_assets_table_expand,
                field_mode=True,
            )

        if field_mode and expanded_asset_id and expanded_asset_id in assets_by_id:
            expanded_asset = assets_by_id[expanded_asset_id]
            st.markdown('<div class="ips-field-row-expand">', unsafe_allow_html=True)
            _render_asset_expand_panel(expanded_asset)
            st.markdown("</div>", unsafe_allow_html=True)

    return all_asset_ids


def _render_small_tools_table_column_filters(
    *,
    filter_options: dict[str, list[str]],
) -> None:
    if not _SMALL_TOOL_FILTER_COLUMN_LAYOUT:
        return
    st.markdown(
        '<div class="ips-assets-table-filter-toolbar ips-serialized-tools-filter-toolbar">',
        unsafe_allow_html=True,
    )
    cols = st.columns(_SMALL_TOOL_FILTER_COL_WEIGHTS, gap="small")
    for col, (label, field) in zip(cols, _SMALL_TOOL_FILTER_COLUMN_LAYOUT):
        with col:
            if label and field:
                render_table_header_cell(
                    label,
                    table_key=_SMALL_TOOLS_TABLE_KEY,
                    filter_field=field,
                    filter_options=filter_options.get(field, []),
                    base_class="ips-assets-filter-toolbar-cell",
                )
            else:
                st.markdown(
                    '<span class="ips-assets-filter-spacer" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_small_tools_table(
    display_rows: list[dict],
    *,
    filter_options: dict[str, list[str]],
    field_mode: bool = False,
) -> None:
    if not display_rows:
        st.info("No serialized tools match your filters.")
        return

    row_by_id = {
        str(row.get("_row_id") or ""): row for row in display_rows if str(row.get("_row_id") or "")
    }

    def _is_row_selected(row_id: str) -> bool:
        return bool(st.session_state.get(_small_tool_select_key(row_id)))

    def _open_row(row_id: str, row: dict) -> None:
        _open_serialized_tool_table_row(row_id, row, {})

    def _select_row(row_id: str, checked: bool) -> None:
        _select_serialized_tool_table_row(
            row_id,
            checked,
            all_row_ids=list(row_by_id.keys()),
            row_by_id=row_by_id,
            assets_by_id={},
        )

    with st.container(key="assets_table_wrap"):
        _render_small_tools_table_column_filters(filter_options=filter_options)
        st.markdown(
            build_serialized_tools_html_table(
                display_rows,
                field_mode=field_mode,
                is_row_selected=_is_row_selected if field_mode else None,
            ),
            unsafe_allow_html=True,
        )
        if field_mode:
            render_serialized_tools_table_bridge_legacy(
                row_by_id,
                open_row_fn=_open_row,
                select_row_fn=_select_row,
                field_mode=True,
            )


@fragment
def _render_equipment_list() -> None:
    """Equipment tab filters and table — local reruns avoid full page reload."""
    from app.components.table_pagination import pagination_meta
    from app.perf_debug import perf_span

    search = str(st.session_state.get("ast_search") or "").strip()
    status = str(st.session_state.get("ast_bar_status") or "All Statuses")
    statuses = [status] if status and status != "All Statuses" else None

    with perf_span("assets.equipment.list_query"):
        equip_page = list_equipment_page(
            search=search,
            statuses=statuses,
            page=1,
            page_size=50,
        )
    page_num, page_size, _ = pagination_meta(equip_page.total_count, _TABLE_KEY)
    if page_num != equip_page.page or page_size != equip_page.page_size:
        with perf_span("assets.equipment.list_query"):
            equip_page = list_equipment_page(
                search=search,
                statuses=statuses,
                page=page_num,
                page_size=page_size,
            )

    filter_options = equip_page.filter_options
    status_options = filter_options.get("status") or []

    def _filters() -> None:
        c1, c2, c3 = st.columns([3.2, 2.2, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search assets...",
                key="ast_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "Status",
                ["All Statuses", *status_options],
                key="ast_bar_status",
                label_visibility="collapsed",
            )
        with c3:
            if st.button("Clear", key="ast_clear", use_container_width=True):
                clear_table_filters(
                    _TABLE_KEY,
                    _ASSET_BAR_FILTER_FIELDS,
                    extra_keys=["ast_search", "ast_bar_status"],
                )
                st.session_state["ast_bar_status"] = "All Statuses"
                reset_table_page(_TABLE_KEY)
                _clear_asset_selection(st.session_state.get(_ALL_ASSET_IDS_KEY))
                clear_field_expanded(FIELD_EXPANDED_ASSET_KEY)
                fragment_rerun()

    render_assets_filter_bar_shell()
    layout_filter_bar(_filters)
    close_assets_filter_bar_shell()

    bulk_col1, bulk_col2 = st.columns([1.2, 4])
    with bulk_col1:
        if st.button("Bulk move tools", key="ast_bulk_move_open", use_container_width=True):
            st.session_state[_BULK_MOVE_OPEN_KEY] = True
            fragment_rerun()
    if st.session_state.get(_BULK_MOVE_OPEN_KEY):
        selected_ids = _get_selected_asset_ids()
        assets_lookup: dict[str, dict] = {}
        if selected_ids:
            from app.services.repository import fetch_by_id

            for aid in selected_ids:
                row = fetch_by_id("assets", aid)
                if isinstance(row, dict):
                    assets_lookup[aid] = row
        render_equipment_bulk_move_toolbar(
            selected_ids,
            assets_lookup,
            on_clear_selection=lambda: _clear_asset_selection(st.session_state.get(_ALL_ASSET_IDS_KEY)),
            on_success_cache_clear=_clear_assets_catalog_cache,
        )

    with perf_span("assets.equipment.pagination"):
        render_table_pagination_header(equip_page.total_count, _TABLE_KEY, item_label="asset")
        render_table_pagination_footer(equip_page.total_count, _TABLE_KEY)

    with perf_span("assets.equipment.table_html"):
        _render_custom_assets_table(equip_page.rows, filter_options=filter_options)
    _rerun_if_assets_modal_pending()


@fragment
def _render_small_tools_list() -> None:
    """Serialized tools tab filters and table — local reruns avoid full page reload."""
    from app.components.table_pagination import pagination_meta
    from app.perf_debug import perf_span

    search = str(st.session_state.get("ast_st_search") or "").strip()
    status = str(st.session_state.get("ast_st_status") or "All Statuses")
    parent_kit = str(st.session_state.get("ast_st_parent_kit") or "All Trailers")
    statuses = [status] if status and status != "All Statuses" else None
    trailers = [parent_kit] if parent_kit and parent_kit not in {"All Trailers", "All Kits"} else None
    field_mode = is_field_context()

    with perf_span("assets.serialized.list_query"):
        tools_page = list_serialized_tools_page(
            search=search,
            statuses=statuses,
            trailers=trailers,
            page=1,
            page_size=50,
        )
    page_num, page_size, _ = pagination_meta(tools_page.total_count, _SMALL_TOOLS_TABLE_KEY)
    if page_num != tools_page.page or page_size != tools_page.page_size:
        with perf_span("assets.serialized.list_query"):
            tools_page = list_serialized_tools_page(
                search=search,
                statuses=statuses,
                trailers=trailers,
                page=page_num,
                page_size=page_size,
            )

    filter_options = tools_page.filter_options
    parent_kits = filter_options.get("trailer") or []
    status_options = filter_options.get("status") or []

    def _filters() -> None:
        c1, c2, c3, c4 = st.columns([2.4, 1.2, 1.2, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search tool name, asset #, kit…",
                key="ast_st_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "Tool Trailer",
                ["All Trailers", *parent_kits],
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
                    ["model_number", "trailer", "job", "status", "condition"],
                    extra_keys=["ast_st_search", "ast_st_parent_kit", "ast_st_status"],
                )
                st.session_state["ast_st_parent_kit"] = "All Trailers"
                st.session_state["ast_st_status"] = "All Statuses"
                reset_table_page(_SMALL_TOOLS_TABLE_KEY)
                _clear_small_tool_selection(st.session_state.get(_ALL_SMALL_TOOL_IDS_KEY))
                fragment_rerun()

    render_assets_filter_bar_shell()
    layout_filter_bar(_filters)
    close_assets_filter_bar_shell()

    render_serialized_tools_toolbar()

    with perf_span("assets.serialized.pagination"):
        render_table_pagination_header(tools_page.total_count, _SMALL_TOOLS_TABLE_KEY, item_label="tool")
        render_table_pagination_footer(tools_page.total_count, _SMALL_TOOLS_TABLE_KEY)

    with perf_span("assets.serialized.table_html"):
        _render_small_tools_table(
            tools_page.rows,
            filter_options=filter_options,
            field_mode=field_mode,
        )
    _rerun_if_assets_modal_pending()


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
        or ql in _asset_department(r).lower()
        or ql in _normalize_asset_status(r.get("status")).lower()
    ]


def _filter_rows(
    rows: list[dict],
    *,
    q: str = "",
    status: str = "All Statuses",
) -> list[dict]:
    out = _apply_assets_search_filter(rows, q)
    status_val = str(status or "All Statuses").strip()
    if status_val and status_val != "All Statuses":
        out = [r for r in out if _normalize_asset_status(r.get("status")) == status_val]
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
    if _ASSET_DETAIL_QUERY_KEY in st.query_params:
        del st.query_params[_ASSET_DETAIL_QUERY_KEY]


def _capture_asset_detail_query() -> None:
    from app.perf_debug import perf_span

    with perf_span("assets.query_capture"):
        requested_id = str(
            st.query_params.get(_ASSET_DETAIL_QUERY_KEY)
            or ""
        ).strip()

        if not requested_id:
            return

        current_modal_id = str(
            st.session_state.get(_ASSETS_MODAL_KEY)
            or ""
        ).strip()

        if requested_id == current_modal_id:
            return

        asset = _cached_asset_for_modal(requested_id)

        if not asset:
            st.session_state[_ASSET_DETAIL_QUERY_ERROR_KEY] = requested_id
            if _ASSET_DETAIL_QUERY_KEY in st.query_params:
                del st.query_params[_ASSET_DETAIL_QUERY_KEY]
            return

        tab_focus = str(st.query_params.get("asset_tab") or "").strip() or None
        _open_assets_detail_modal(
            requested_id,
            asset,
            tab_focus=tab_focus,
        )


def _show_asset_detail_query_error_if_any() -> None:
    if st.session_state.pop(_ASSET_DETAIL_QUERY_ERROR_KEY, None):
        st.warning("The selected asset could not be found.")


def _put_asset_in_modal_cache(asset_id: str, asset: dict | None) -> None:
    """Keep modal lookup working for Small Tools and other non-equipment rows."""
    aid = str(asset_id or "").strip()
    if not aid or not isinstance(asset, dict):
        return
    cache = st.session_state.get(_ASSETS_CACHE_KEY)
    if not isinstance(cache, dict):
        cache = {}
    else:
        cache = dict(cache)
    cache[aid] = asset
    st.session_state[_ASSETS_CACHE_KEY] = cache


def _clear_assets_catalog_cache() -> None:
    from app.pages._core._data import clear_assets_catalog_cache

    clear_assets_catalog_cache()


def _assets_catalog_version() -> int:
    from app.pages._core._data import assets_catalog_data_version

    return assets_catalog_data_version()


def _cached_asset_for_modal(asset_id: str) -> dict | None:
    """Resolve one asset for the detail modal without building a full-page cache."""
    from app.perf_debug import perf_span

    with perf_span("assets.detail_lookup"):
        aid = str(asset_id or "").strip()
        if not aid:
            return None
        cache = st.session_state.get(_ASSETS_CACHE_KEY)
        if isinstance(cache, dict):
            hit = cache.get(aid)
            if isinstance(hit, dict):
                return hit
        from app.services.phase2_modules_service import normalize_asset
        from app.services.repository import fetch_by_id

        raw = fetch_by_id("assets", aid)
        if isinstance(raw, dict):
            asset = normalize_asset(raw)
            _put_asset_in_modal_cache(aid, asset)
            return asset
        from app.pages._core._data import _DEMO_ASSETS

        for row in _DEMO_ASSETS:
            if str(row.get("id") or "").strip() == aid:
                asset = normalize_asset(row)
                _put_asset_in_modal_cache(aid, asset)
                return asset
        return None


def _open_assets_detail_modal(
    asset_id: str,
    asset: dict | None = None,
    *,
    tab_focus: str | None = None,
) -> None:
    aid = str(asset_id or "").strip()
    if not aid:
        return
    prev_id = str(st.session_state.get(_ASSETS_MODAL_KEY) or "").strip()
    _put_asset_in_modal_cache(aid, asset)
    st.session_state[SELECTED_ASSET_KEY] = aid
    st.session_state[SHOW_ASSET_MODAL_KEY] = True
    focus = str(tab_focus or "").strip()
    if not focus:
        focus = str(st.session_state.pop(ASSET_DETAIL_TAB_FOCUS_KEY, "") or "").strip()
    resolved_focus = _resolve_asset_detail_tab_name(focus) if focus else None
    if resolved_focus:
        st.session_state[_ASSET_DETAIL_ACTIVE_TAB_KEY] = resolved_focus
    elif aid != prev_id:
        st.session_state[_ASSET_DETAIL_ACTIVE_TAB_KEY] = "Overview"
        st.session_state.pop(_asset_qr_loaded_key(aid), None)
        st.session_state.pop(_asset_doc_count_loaded_key(aid), None)
    open_record_modal(
        aid,
        asset,
        session_select_key=_SEL,
        modal_key=_ASSETS_MODAL_KEY,
        module=_MOD,
        id_fields=("id", "asset_number"),
    )


def _handle_open_asset(asset: dict) -> None:
    """Shared entry point for opening an asset detail view from the table."""
    aid = str(asset.get("id") or "").strip()
    if aid:
        _open_assets_detail_modal(aid, asset)


def _asset_qr_loaded_key(asset_id: str) -> str:
    return f"_ips_asset_qr_loaded_{asset_id}"


def _asset_doc_count_loaded_key(asset_id: str) -> str:
    return f"_ips_asset_doc_count_loaded_{asset_id}"


def _resolve_asset_detail_tab_name(focus: str) -> str | None:
    raw = str(focus or "").strip().lower()
    if not raw:
        return None
    aliases = {
        "overview": "Overview",
        "kit": "Kit / Contents",
        "kit / contents": "Kit / Contents",
        "contents": "Kit / Contents",
        "maintenance": "Maintenance",
        "documents": "Documents",
        "assignments": "Assignments",
        "depreciation": "Depreciation",
        "notes": "Notes",
        "activity": "Activity",
    }
    if raw in aliases:
        return aliases[raw]
    for tab in _ASSET_TABS:
        if tab.lower() == raw or tab.lower().startswith(raw):
            return tab
    return None


def _asset_detail_tab_labels(asset: dict, *, include_doc_count: bool) -> list[str]:
    labels = list(_ASSET_TABS)
    if not include_doc_count:
        return labels
    aid = str(asset.get("id") or "").strip()
    if not aid:
        return labels
    doc_count = asset_documents_count(aid)
    if doc_count:
        labels = [
            f"Documents ({doc_count})" if name == "Documents" else name
            for name in labels
        ]
    return labels


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


def _asset_for_qr(asset: dict) -> dict:
    num = str(asset.get("asset_number") or asset.get("asset_id") or "").strip()
    return {**asset, "asset_id": num}


def _render_asset_qr_block(asset: dict, aid: str) -> None:
    from app.components.qr_label_toolbar import render_qr_label_png_buttons
    from app.services.asset_qr import (
        qr_embed_subject,
        qr_label_download_basename,
        qr_label_png_bytes,
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
        if st.button("Rebuild QR", key=f"ast_qr_rebuild_{aid}", use_container_width=True):
            result = rebuild_asset_qr(asset)
            if result.ok and isinstance(result.data, dict):
                _clear_assets_catalog_cache()
                st.session_state["ips_sel_assets"] = aid
                st.success("QR label rebuilt. Download a label PNG when ready.")
                st.rerun()
            else:
                st.error(str(getattr(result, "error", None) or "Could not rebuild QR."))
        render_qr_label_png_buttons(
            key_prefix=f"ast_qr_{aid}",
            basename=qr_label_download_basename(qr_asset),
            build_png=lambda size_key: qr_label_png_bytes(qr_asset, subject, size=size_key),
        )


def _render_asset_qr_section(asset: dict, aid: str) -> None:
    loaded_key = _asset_qr_loaded_key(aid)
    if not st.session_state.get(loaded_key):
        if st.button("Load QR Tools", key=f"ast_qr_load_{aid}", use_container_width=True):
            st.session_state[loaded_key] = True
            st.rerun()
        return
    _render_asset_qr_block(asset, aid)


def _render_asset_documents_tab(asset: dict) -> None:
    from app.auth import effective_role, is_authenticated
    include_restricted = is_authenticated() and str(effective_role() or "").lower() in {
        "admin",
        "supervisor",
        "manager",
    }
    rk = record_session_key(asset, "id", "asset_number")
    render_asset_documents_tab(
        asset,
        key_prefix=f"ast_doc_{rk}",
        include_restricted=include_restricted,
    )


def _render_asset_maintenance_tab(asset: dict) -> None:
    aid = str(asset.get("id") or "")
    from app.components.coupling_inspection_launcher import render_coupling_inspection_launcher
    job_id = str(asset.get("assigned_job_id") or asset.get("job_id") or "").strip() or None
    render_coupling_inspection_launcher(
        job_id=job_id,
        equipment_id=aid,
        key_prefix=f"asset_ci_{aid}",
    )
    st.divider()

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


def _asset_rental_session_keys(aid: str = "", *, new_asset: bool = False) -> dict[str, str]:
    if new_asset:
        return {
            "rentable": "ast_new_rentable",
            "rate": "ast_new_rental_rate",
            "unit": "ast_new_rental_unit",
            "mk": "ast_new_rental_mk",
            "notes": "ast_new_rental_notes",
        }
    return {
        "rentable": f"ast_edit_rentable_{aid}",
        "rate": f"ast_edit_rental_rate_{aid}",
        "unit": f"ast_edit_rental_unit_{aid}",
        "mk": f"ast_edit_rental_mk_{aid}",
        "notes": f"ast_edit_rental_notes_{aid}",
    }


def _rental_fields_from_session(keys: dict[str, str]) -> dict[str, Any]:
    return {
        "is_rentable": bool(st.session_state.get(keys["rentable"])),
        "rental_rate": float(st.session_state.get(keys["rate"]) or 0),
        "rental_rate_unit": st.session_state.get(keys["unit"]),
        "rental_default_markup_percent": float(st.session_state.get(keys["mk"]) or 0),
        "rental_notes": str(st.session_state.get(keys["notes"]) or "").strip(),
    }


def _render_asset_rental_pricing_fields(
    asset: dict | None = None,
    *,
    aid: str = "",
    new_asset: bool = False,
) -> None:
    keys = _asset_rental_session_keys(aid, new_asset=new_asset)
    if asset is not None and not new_asset:
        st.session_state.setdefault(keys["rentable"], asset_is_rentable(asset))
        st.session_state.setdefault(keys["rate"], primary_rental_rate_from_asset(asset))
        st.session_state.setdefault(
            keys["unit"],
            normalize_rental_rate_unit(asset.get("rental_rate_unit")),
        )
        st.session_state.setdefault(
            keys["mk"],
            float(asset.get("rental_default_markup_percent") or 0),
        )
        st.session_state.setdefault(keys["notes"], str(asset.get("rental_notes") or ""))
    if new_asset:
        st.session_state.setdefault(keys["rate"], 0.0)
        st.session_state.setdefault(keys["unit"], "Days")
        st.session_state.setdefault(keys["mk"], 0.0)
        st.session_state.setdefault(keys["notes"], "")

    st.checkbox(
        "Rentable (estimate equipment)",
        key=keys["rentable"],
        help="When enabled, this asset appears when adding equipment on estimates.",
    )
    if st.session_state.get(keys["rentable"]):
        st.markdown("**Rental pricing**")
        rc1, rc2 = st.columns(2)
        with rc1:
            st.number_input(
                "Rental rate",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                key=keys["rate"],
                help="Cost rate for the unit selected below (used on estimates).",
            )
        with rc2:
            st.selectbox("Rental rate unit", RENTAL_RATE_UNITS, key=keys["unit"])
        st.number_input(
            "Default markup %",
            min_value=0.0,
            step=0.5,
            format="%.1f",
            key=keys["mk"],
            help="Pre-fills markup when this asset is added to an estimate.",
        )
        st.text_area("Rental notes", key=keys["notes"], height=72)


_ASSET_CONDITION_OPTS = ("Good", "Fair", "Poor", "Needs Repair", "Out of Service")


def _parse_asset_date_for_input(raw: object) -> date | None:
    s = str(raw or "").strip()[:10]
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _asset_edit_payload_from_session(aid: str) -> dict[str, Any]:
    desc = str(st.session_state.get(f"ast_edit_desc_{aid}") or "").strip()
    hours_raw = st.session_state.get(f"ast_edit_hours_{aid}")
    try:
        hours_miles = float(hours_raw) if hours_raw not in (None, "") else None
    except (TypeError, ValueError):
        hours_miles = None
    last_used = st.session_state.get(f"ast_edit_last_used_{aid}")
    acquired = st.session_state.get(f"ast_edit_acquired_{aid}")
    next_svc = st.session_state.get(f"ast_edit_next_svc_{aid}")

    def _money(key: str) -> float | None:
        raw = st.session_state.get(key)
        if raw in (None, ""):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    return {
        "asset_number": st.session_state.get(f"ast_edit_num_{aid}"),
        "asset_name": st.session_state.get(f"ast_edit_name_{aid}"),
        "category": st.session_state.get(f"ast_edit_cat_{aid}"),
        "status": st.session_state.get(f"ast_edit_status_{aid}"),
        "location": st.session_state.get(f"ast_edit_loc_{aid}"),
        "department": st.session_state.get(f"ast_edit_dept_{aid}"),
        "manufacturer": st.session_state.get(f"ast_edit_mfr_{aid}"),
        "model_number": st.session_state.get(f"ast_edit_model_number_{aid}"),
        "serial_number": st.session_state.get(f"ast_edit_serial_{aid}"),
        "description": desc,
        "operator": st.session_state.get(f"ast_edit_operator_{aid}"),
        "primary_use": st.session_state.get(f"ast_edit_primary_use_{aid}"),
        "hours_miles": hours_miles,
        "last_used": last_used.isoformat() if hasattr(last_used, "isoformat") else last_used,
        "condition": st.session_state.get(f"ast_edit_condition_{aid}"),
        "next_service_due": next_svc.isoformat() if hasattr(next_svc, "isoformat") else next_svc,
        "acquired_date": acquired.isoformat() if hasattr(acquired, "isoformat") else acquired,
        "purchase_price": _money(f"ast_edit_purchase_{aid}"),
        "value": _money(f"ast_edit_value_{aid}"),
        "salvage_value": _money(f"ast_edit_salvage_{aid}"),
        "depreciation_method": st.session_state.get(f"ast_edit_depr_method_{aid}"),
        "useful_life": st.session_state.get(f"ast_edit_useful_life_{aid}"),
        "annual_depreciation": _money(f"ast_edit_annual_depr_{aid}"),
        "include_in_pricing_guide": bool(st.session_state.get(f"ast_edit_pg_{aid}")),
        **_rental_fields_from_session(_asset_rental_session_keys(aid)),
    }


def _seed_asset_edit_form(asset: dict) -> None:
    aid = str(asset.get("id") or "")
    st.session_state[f"ast_edit_num_{aid}"] = str(asset.get("asset_number") or "")
    st.session_state[f"ast_edit_name_{aid}"] = str(asset.get("asset_name") or "")
    st.session_state[f"ast_edit_cat_{aid}"] = str(asset.get("category") or lookup_options("asset_categories")[0])
    st.session_state[f"ast_edit_status_{aid}"] = str(asset.get("status") or lookup_options("asset_statuses")[0])
    st.session_state[f"ast_edit_loc_{aid}"] = str(asset.get("location") or "")
    st.session_state[f"ast_edit_dept_{aid}"] = str(asset.get("department") or "")
    st.session_state[f"ast_edit_mfr_{aid}"] = str(asset.get("manufacturer") or "")
    st.session_state[f"ast_edit_model_number_{aid}"] = str(
        asset.get("model_number") or asset.get("model") or ""
    )
    st.session_state[f"ast_edit_serial_{aid}"] = str(asset.get("serial_number") or "")
    st.session_state[f"ast_edit_desc_{aid}"] = str(asset.get("description") or asset.get("notes") or "")
    st.session_state[f"ast_edit_operator_{aid}"] = str(asset.get("operator") or "")
    st.session_state[f"ast_edit_primary_use_{aid}"] = str(
        asset.get("primary_use") or asset.get("description") or ""
    )
    hm = asset.get("hours_miles")
    st.session_state[f"ast_edit_hours_{aid}"] = float(hm) if hm not in (None, "") else 0.0
    st.session_state[f"ast_edit_last_used_{aid}"] = _parse_asset_date_for_input(asset.get("last_used"))
    cond = str(asset.get("condition") or "Good").strip()
    st.session_state[f"ast_edit_condition_{aid}"] = (
        cond if cond in _ASSET_CONDITION_OPTS else _ASSET_CONDITION_OPTS[0]
    )
    st.session_state[f"ast_edit_next_svc_{aid}"] = _parse_asset_date_for_input(
        asset.get("next_service_due") or asset.get("service_due")
    )
    st.session_state[f"ast_edit_acquired_{aid}"] = _parse_asset_date_for_input(asset.get("acquired_date"))
    st.session_state[f"ast_edit_purchase_{aid}"] = float(
        asset.get("purchase_price") or asset.get("purchase_cost") or 0
    )
    st.session_state[f"ast_edit_value_{aid}"] = float(asset.get("value") or asset.get("current_value") or 0)
    st.session_state[f"ast_edit_salvage_{aid}"] = float(asset.get("salvage_value") or 0)
    st.session_state[f"ast_edit_depr_method_{aid}"] = str(
        asset.get("depreciation_method") or "Straight Line"
    )
    st.session_state[f"ast_edit_useful_life_{aid}"] = str(asset.get("useful_life") or "7 years")
    st.session_state[f"ast_edit_annual_depr_{aid}"] = float(asset.get("annual_depreciation") or 0)
    st.session_state[f"ast_edit_pg_{aid}"] = bool(asset.get("include_in_pricing_guide"))
    seed_tracking_form_state(asset, prefix="ast_edit")
    rk = _asset_rental_session_keys(aid)
    st.session_state[rk["rentable"]] = asset_is_rentable(asset)
    st.session_state[rk["rate"]] = primary_rental_rate_from_asset(asset)
    st.session_state[rk["unit"]] = normalize_rental_rate_unit(asset.get("rental_rate_unit"))
    st.session_state[rk["mk"]] = float(asset.get("rental_default_markup_percent") or 0)
    st.session_state[rk["notes"]] = str(asset.get("rental_notes") or "")


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

    st.markdown("##### Asset details")
    ac1, ac2 = st.columns(2)
    with ac1:
        st.text_input("Asset Number", key=f"ast_edit_num_{aid}")
        st.text_input("Asset Name", key=f"ast_edit_name_{aid}")
        st.selectbox("Category", lookup_options("asset_categories"), key=f"ast_edit_cat_{aid}")
        st.selectbox("Status", lookup_options("asset_statuses"), key=f"ast_edit_status_{aid}")
        st.text_input("Location", key=f"ast_edit_loc_{aid}")
        st.text_input("Department", key=f"ast_edit_dept_{aid}")
    with ac2:
        st.text_input("Manufacturer", key=f"ast_edit_mfr_{aid}")
        st.text_input("Model #", key=f"ast_edit_model_number_{aid}")
        st.text_input("Serial Number", key=f"ast_edit_serial_{aid}")
        st.text_area("Description", key=f"ast_edit_desc_{aid}", height=100)

    st.checkbox(
        "Include on Pricing Guide (billable on estimates)",
        key=f"ast_edit_pg_{aid}",
        help="Turn off for fleet/shop assets that should stay in Assets only.",
    )
    _render_asset_rental_pricing_fields(asset, aid=aid)

    st.markdown("##### Tracking tab")
    bucket = render_asset_tracking_bucket_select(asset, prefix="ast_edit")
    from app.components.asset_reclassification_ui import render_tracking_bucket_extra_fields
    render_tracking_bucket_extra_fields(asset, bucket, prefix="ast_edit")

    st.markdown("##### Usage")
    u1, u2 = st.columns(2)
    with u1:
        st.text_input("Current Operator", key=f"ast_edit_operator_{aid}")
        st.text_input("Primary Use", key=f"ast_edit_primary_use_{aid}")
        st.number_input("Hours/Miles", min_value=0.0, step=0.1, key=f"ast_edit_hours_{aid}")
    with u2:
        st.date_input("Last Used", key=f"ast_edit_last_used_{aid}")
        st.selectbox("Condition", _ASSET_CONDITION_OPTS, key=f"ast_edit_condition_{aid}")
        st.date_input("Next Service Due", key=f"ast_edit_next_svc_{aid}")

    st.markdown("##### Financial")
    f1, f2 = st.columns(2)
    with f1:
        st.date_input("Acquired Date", key=f"ast_edit_acquired_{aid}")
        st.number_input("Purchase Price", min_value=0.0, step=1.0, format="%.2f", key=f"ast_edit_purchase_{aid}")
        st.number_input("Current Value", min_value=0.0, step=1.0, format="%.2f", key=f"ast_edit_value_{aid}")
    with f2:
        st.number_input("Salvage Value", min_value=0.0, step=1.0, format="%.2f", key=f"ast_edit_salvage_{aid}")
        st.text_input("Depreciation Method", key=f"ast_edit_depr_method_{aid}")
        st.text_input("Useful Life", key=f"ast_edit_useful_life_{aid}")
        st.number_input(
            "Annual Depreciation",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            key=f"ast_edit_annual_depr_{aid}",
        )

    st.markdown("##### Image")
    _render_asset_photo_manager(asset)

    cancelled, saved = render_save_cancel_actions(
        module=_MOD,
        record_key=rk,
        cancel_key=f"ast_edit_cancel_{aid}",
        save_key=f"ast_edit_save_{aid}",
        save_label="Save Asset",
    )
    if cancelled:
        st.rerun()
    if saved:
        payload = _asset_edit_payload_from_session(aid)
        rc_ok, rc_msg = apply_tracking_bucket_change(
            asset,
            prefix="ast_edit",
            serial_number=str(payload.get("serial_number") or ""),
            on_success_cache_clear=_clear_assets_catalog_cache,
        )
        if not rc_ok:
            st.error(rc_msg or "Could not update tracking tab.")
        else:
            ok, msg = persist_asset(payload, row_id=aid)
            if ok:
                _clear_assets_catalog_cache()
                set_view_mode(_MOD, rk)
                parts = [p for p in (rc_msg, msg or "Asset saved.") if p]
                st.success(" ".join(parts))
                st.rerun()
            else:
                st.error(msg or "Could not save asset.")


def _render_asset_detail_tabs(asset: dict) -> None:
    from app.components.tabs import render_tabs
    from app.perf_debug import perf_span

    aid = str(asset.get("id") or "")
    asset_number = safe_value(asset.get("asset_number"))
    asset_name = safe_value(asset.get("asset_name"))

    focus = str(st.session_state.pop(ASSET_DETAIL_TAB_FOCUS_KEY, "") or "").strip()
    resolved_focus = _resolve_asset_detail_tab_name(focus) if focus else None
    if resolved_focus:
        st.session_state[_ASSET_DETAIL_ACTIVE_TAB_KEY] = resolved_focus

    include_doc_count = bool(
        st.session_state.get(_asset_doc_count_loaded_key(aid))
        or str(st.session_state.get(_ASSET_DETAIL_ACTIVE_TAB_KEY) or "Overview").startswith("Documents")
    )
    tab_labels = _asset_detail_tab_labels(asset, include_doc_count=include_doc_count)
    active_tab = render_tabs(
        tab_labels,
        session_key=_ASSET_DETAIL_ACTIVE_TAB_KEY,
        default="Overview",
    )
    active_base = str(active_tab).split(" (")[0].strip()

    if active_base == "Documents":
        st.session_state[_asset_doc_count_loaded_key(aid)] = True

    if active_base == "Overview":
        with perf_span("assets.modal.overview"):
            c1, c2 = st.columns([1.2, 1])
            with c1:
                st.markdown(
                    summary_card_html(
                        "Asset Details",
                        [
                            ("Asset Number", asset_number),
                            ("Asset Name", asset_name),
                            ("Category", str(asset.get("category") or "—")),
                            ("Assets tab", tracking_type_label(asset)),
                            ("Status", status_badge_html(str(asset.get("status") or ""))),
                            ("Location", str(asset.get("location") or "—")),
                            ("Department", str(asset.get("department") or "—")),
                            ("Manufacturer", str(asset.get("manufacturer") or "—")),
                            ("Model #", str(asset.get("model_number") or asset.get("model") or "—")),
                            ("Serial Number", str(asset.get("serial_number") or "—")),
                            (
                                "Rentable",
                                "Yes" if asset_is_rentable(asset) else "No",
                            ),
                            *(
                                [
                                    (
                                        "Rental rate",
                                        fmt_currency(primary_rental_rate_from_asset(asset))
                                        if primary_rental_rate_from_asset(asset)
                                        else "—",
                                    ),
                                    (
                                        "Rental rate unit",
                                        normalize_rental_rate_unit(asset.get("rental_rate_unit")),
                                    ),
                                    (
                                        "Default markup %",
                                        str(asset.get("rental_default_markup_percent") or "0"),
                                    ),
                                    ("Rental notes", str(asset.get("rental_notes") or "—")),
                                ]
                                if asset_is_rentable(asset)
                                else []
                            ),
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

            render_asset_reclassification_panel(asset)

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
                _render_asset_qr_section(asset, aid)

    elif active_base == "Kit / Contents":
        with perf_span("assets.modal.kit"):
            render_kit_contents_tab(asset)

    elif active_base == "Maintenance":
        with perf_span("assets.modal.maintenance"):
            _render_asset_maintenance_tab(asset)

    elif active_base == "Documents":
        with perf_span("assets.modal.documents"):
            _render_asset_documents_tab(asset)

    elif active_base == "Assignments":
        assign_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Current Operator', asset.get('operator'))}"
            f"{detail_field_html('Department', asset.get('department'))}"
            f"{detail_field_html('Location', asset.get('location'))}"
            f"{detail_field_html('Primary Use', asset.get('primary_use') or asset.get('description'))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Assignments", assign_html), unsafe_allow_html=True)

    elif active_base == "Depreciation":
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

    elif active_base == "Notes":
        notes_text = safe_value(asset.get("description"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    elif active_base == "Activity":
        with perf_span("assets.modal.activity"):
            if str(st.session_state.get(ASSET_OPEN_ACTIVITY_KEY) or "") == aid:
                st.session_state.pop(ASSET_OPEN_ACTIVITY_KEY, None)
            try:
                render_asset_activity_snippet(asset)
            except Exception:
                st.info("No recent activity for this asset.")
            st.caption("Checkout, audit, and document events will expand here as integrations are connected.")
            if is_serialized_tool_asset(asset):
                render_serialized_tool_tracking_panel(asset)


def _asset_action_callbacks() -> tuple[object, object]:
    def _after_action() -> None:
        _clear_assets_detail_modal()

    return _after_action, _after_action


def _asset_header_action_slot_count(asset: dict) -> int:
    count = len(asset_retire_delete_action_specs(asset))
    if pricing_guide_header_action_spec(asset):
        count += 1
    return max(count, 1)


def _render_asset_header_actions(asset: dict, header_cols: list | None = None) -> None:
    if is_asset_action_confirm_open(asset) or is_asset_pricing_guide_confirm_open(asset):
        return

    aid = str(asset.get("id") or "").strip()
    if not aid or is_demo_id(aid):
        return

    on_retire, on_delete = _asset_action_callbacks()
    action_specs = list(asset_retire_delete_action_specs(asset))
    pg_spec = pricing_guide_header_action_spec(asset)
    if pg_spec:
        action_specs.append(pg_spec)
    if not action_specs:
        return

    asset_key = "".join(ch if ch.isalnum() else "_" for ch in aid) or "asset"

    def _render_in_cols(cols: list) -> None:
        for col, (action, btn_fn, label, suffix) in zip(cols, action_specs):
            with col:
                if not btn_fn(label, suffix, use_container_width=False):
                    continue
                if action in {"retire", "delete"}:
                    open_asset_action_confirm(aid, action)
                elif action in {"include", "exclude"}:
                    handle_pricing_guide_header_click(
                        asset,
                        action,
                        on_change=on_retire,
                    )

    if header_cols is not None:
        st.markdown('<span class="ips-asset-actions-header-marker"></span>', unsafe_allow_html=True)
        _render_in_cols(header_cols[: len(action_specs)])
        return

    with st.container(key=f"asset_header_actions_{asset_key}"):
        st.markdown('<span class="ips-asset-actions-header-marker"></span>', unsafe_allow_html=True)
        cols = st.columns(len(action_specs), gap="small")
        _render_in_cols(cols)


def _render_asset_actions_panel(asset: dict) -> None:
    rk = record_session_key(asset, "id", "asset_number")
    if is_edit_mode(_MOD, rk):
        return
    aid = str(asset.get("id") or "").strip()
    if not aid or is_demo_id(aid):
        return

    on_retire, on_delete = _asset_action_callbacks()
    render_asset_action_confirm_panel(asset, on_retire=on_retire, on_delete=on_delete)
    render_asset_pricing_guide_confirm_panel(asset, on_change=on_retire)
    render_asset_pricing_guide_actions(asset, on_change=on_retire, buttons_in_header=True)


def render_asset_detail_dialog(asset: dict) -> None:
    rk = record_session_key(asset, "id", "asset_number")
    asset_number = safe_value(asset.get("asset_number"))
    asset_name = safe_value(asset.get("asset_name"))
    status = safe_value(asset.get("status"))

    render_modal_shell(compact=True)
    if not is_edit_mode(_MOD, rk):
        aid = str(asset.get("id") or "").strip()
        show_header_actions = bool(aid) and not is_demo_id(aid)
        render_compact_modal_header(
            title=asset_number,
            subtitle=asset_name,
            status=status,
            module=_MOD,
            record_key=rk,
            on_edit=lambda: _set_asset_edit_mode(asset),
            key_prefix=f"assets_modal_{rk}",
            extra_action_slots=_asset_header_action_slot_count(asset) if show_header_actions else 3,
            extra_actions=(lambda cols: _render_asset_header_actions(asset, header_cols=cols))
            if show_header_actions
            else None,
        )

        render_modal_meta_grid(
            [
                ("Category", safe_value(asset.get("category"))),
                ("Assets tab", tracking_type_label(asset)),
                ("Location", safe_value(asset.get("location"))),
                ("Department", safe_value(asset.get("department"))),
                ("Current Value", fmt_currency(asset.get("value"))),
            ]
        )
        _render_asset_actions_panel(asset)

    if is_edit_mode(_MOD, rk):
        _render_asset_edit_form(asset)
    else:
        _render_asset_detail_tabs(asset)


def _detail_modal_pending() -> bool:
    return bool(
        st.session_state.get(SHOW_ASSET_MODAL_KEY)
        or str(st.session_state.get(_ASSETS_MODAL_KEY) or "").strip()
    )


@st.dialog("Asset Details", width="large", on_dismiss=_clear_assets_detail_modal)
def _show_assets_detail_modal() -> None:
    asset = get_modal_record(
        cache_key=_ASSETS_CACHE_KEY,
        modal_key=_ASSETS_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not asset:
        sel = str(st.session_state.get(_ASSETS_MODAL_KEY) or st.session_state.get(_SEL) or "").strip()
        asset = _cached_asset_for_modal(sel)
    if not asset:
        render_missing_record(_clear_assets_detail_modal, close_key="assets_modal_missing_close")
        return
    render_asset_detail_dialog(asset)


@st.dialog("New Asset", width="large")
def _show_new_asset_dialog() -> None:
    from app.perf_debug import perf_span

    with perf_span("assets.new_form"):
        st.text_input("Asset #", key="ast_new_num")
        st.text_input("Asset name", key="ast_new_name")
        st.text_input("Model #", key="ast_new_model_number")
        st.selectbox("Category", lookup_options("asset_categories"), key="ast_new_cat")
        st.selectbox("Status", lookup_options("asset_statuses"), key="ast_new_status")
        _render_asset_rental_pricing_fields(new_asset=True)
        st.file_uploader(
            "Upload asset image",
            type=list(ITEM_IMAGE_UPLOAD_TYPES),
            key="ast_new_image",
        )
        save_col, cancel_col = st.columns(2)
        with save_col:
            save_clicked = st.button("Save Asset", key="ast_save_new", type="primary")
        with cancel_col:
            cancel_clicked = st.button("Cancel", key="ast_cancel_new")
        if cancel_clicked:
            return
        if save_clicked:
            from app.services.assets_service import save_asset

            result = save_asset(
                {
                    "asset_number": st.session_state.get("ast_new_num"),
                    "asset_name": st.session_state.get("ast_new_name"),
                    "model_number": st.session_state.get("ast_new_model_number"),
                    "category": st.session_state.get("ast_new_cat"),
                    "status": st.session_state.get("ast_new_status"),
                    **_rental_fields_from_session(_asset_rental_session_keys(new_asset=True)),
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
                _clear_assets_catalog_cache()
                st.success("Asset saved.")
                st.rerun()


def render() -> None:
    from app.pages._core._access import begin_module
    if not begin_module("assets"):
        return
    from app.navigation import ASSET_SCAN_EMBED_KEY
    if st.session_state.pop(ASSET_SCAN_EMBED_KEY, False):
        from app.pages.asset_scan import render_asset_scan_page
        render_asset_scan_page()
        return
    from app.services.asset_qr import apply_pending_asset_deeplink
    apply_pending_asset_deeplink()
    _capture_asset_detail_query()
    _show_asset_detail_query_error_if_any()

    deeplink_sel = str(st.session_state.get(_SEL) or "").strip()
    if deeplink_sel and not str(st.session_state.get(_ASSETS_MODAL_KEY) or "").strip():
        deeplink_asset = _cached_asset_for_modal(deeplink_sel)
        if deeplink_asset:
            _open_assets_detail_modal(deeplink_sel, deeplink_asset)

    detail_pending = _detail_modal_pending()

    def _assets_header_actions() -> None:
        st.markdown(
            '<span class="ips-assets-page-header-actions ips-page-header-inline-actions" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        export_col, template_col, import_col, quick_col, new_col = st.columns(
            [0.85, 1.15, 1.0, 1.35, 1.05],
            gap="small",
        )
        with export_col:
            st.button("Export", key="ast_export")
        with template_col:
            st.download_button(
                "CSV Template",
                data=hand_tool_csv_template_bytes(),
                file_name="small_hand_tools_import_template.csv",
                mime="text/csv",
                key="ast_hand_tool_csv_template",
            )
        with import_col:
            if st.button("Import CSV", key="ast_hand_tool_import"):
                open_hand_tool_import_dialog()
        with quick_col:
            if st.button("+ Quick Add Tool", key="ast_quick_add", type="primary"):
                open_quick_add_tool_dialog()
        with new_col:
            if st.button("+ New Asset", key="ast_new", type="secondary"):
                _show_new_asset_dialog()

    from app.ui.page_header import render_page_header

    render_page_header(
        "Assets",
        "Track and manage all company assets and equipment.",
        primary_action=_assets_header_actions,
        primary_action_width=6.4,
    )

    active_tab = str(st.session_state.get(_ASSETS_MAIN_TAB_KEY) or _ASSETS_MAIN_TABS[0]).strip()
    if active_tab not in _ASSETS_MAIN_TABS:
        active_tab = _ASSETS_MAIN_TABS[0]

    inject_assets_page_css(
        active_tab,
        detail_open=bool(st.session_state.get(SHOW_ASSET_MODAL_KEY)),
    )
    if is_field_context():
        inject_field_row_expand_css()
    st.markdown(
        '<span class="ips-assets-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    if detail_pending:
        _show_assets_modal_if_selected()
        return

    if st.session_state.get(QUICK_ADD_OPEN_KEY):
        show_quick_add_tool_dialog(uploaded_by=_current_user_id())

    if st.session_state.get(HAND_TOOL_IMPORT_OPEN_KEY):
        show_hand_tool_import_dialog()

    if is_field_context():
        render_field_scan_bar(("🔧 Scan Asset", "scan_asset"))

    st.markdown(
        '<span class="ips-assets-main-tabs-anchor" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    from app.components.tabs import render_tabs

    active_tab = render_tabs(
        list(_ASSETS_MAIN_TABS),
        session_key=_ASSETS_MAIN_TAB_KEY,
        default=_ASSETS_MAIN_TABS[0],
    )

    if active_tab == "Equipment":
        with st.expander("Tool Trailers & Kits", expanded=False):
            if st.button("Load kit summary", key="ast_kit_summary_load", use_container_width=True):
                st.session_state["ast_kit_summary_on"] = True
            if st.session_state.get("ast_kit_summary_on"):
                render_kit_accountability_summary()
            else:
                st.caption("Load kit accountability metrics on demand to speed up the assets page.")
        _render_equipment_list()
    elif active_tab == "Serialized Tools":
        st.caption(
            "Individual tools tracked by serial number — Milwaukee drills, impacts, grinders, saws, rotary hammers, and similar cordless tools."
        )
        _render_small_tools_list()
    else:
        render_hand_tools_tab(on_open_tool=_open_hand_tool_row)
