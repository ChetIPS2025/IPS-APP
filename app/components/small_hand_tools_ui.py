"""Quantity-based Small Hand Tools tab on the Assets page."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from app.components.record_modal import (
    build_modal_cache,
    clear_record_modal,
    detail_field_html,
    dialog_card_html,
    get_modal_record,
    is_edit_mode,
    open_record_modal,
    record_session_key,
    render_compact_modal_header,
    render_edit_form_header,
    render_missing_record,
    render_modal_header,
    render_modal_meta_grid,
    render_modal_shell,
    render_save_cancel_actions,
    safe_value,
    set_edit_mode,
    set_view_mode,
    show_modal_if_pending,
)
from app.components.small_hand_tools_list_table import (
    HAND_TOOLS_TABLE_COL_WIDTHS_PX,
    build_hand_tools_html_table,
    render_hand_tools_table_bridge_legacy,
    render_hand_tools_table_open_buttons,
)
from app.components.table_filters import (
    apply_column_filters,
    build_filter_options,
    render_table_header_cell,
)
from app.components.table_pagination import (
    DEFAULT_CATALOG_PAGE_SIZE,
    paginate_rows,
    pagination_meta,
    render_table_pagination_footer,
    reset_table_page,
)
from app.components.table_filters import clear_table_filters
from app.components.layout import render_filter_bar as layout_filter_bar
from app.components.item_photo_manager import render_item_photo_manager
from app.pages._core._data import load_assets, load_inventory
from app.services.asset_kits_service import get_tool_trailers
from app.services.catalog_images import CatalogImageContext, build_catalog_image_context
from app.services.small_hand_tool_service import (
    HAND_TOOL_CATEGORIES,
    HAND_TOOL_CONDITIONS,
    HAND_TOOL_STATUSES,
    STORAGE_TYPES,
    adjust_hand_tool_quantity,
    clear_hand_tools_list_cache,
    delete_hand_tool,
    link_hand_tool_to_kit,
    list_hand_tools,
    save_hand_tool,
)
from app.services.small_hand_tool_images import (
    clear_small_hand_tool_image,
    small_hand_tool_photo_preview_record,
    upload_small_hand_tool_image,
)
from app.utils.formatting import fmt_currency

_TABLE_KEY = "assets_hand_tools_list"
_HAND_TOOL_MOD = "hand_tool"
_HAND_TOOL_SEL = "ht_detail_sel"
_HAND_TOOL_MODAL_KEY = "ht_detail_modal"
_HAND_TOOL_CACHE_KEY = "ht_detail_cache"
_HAND_TOOL_DETAIL_TABLE_KEY = "assets_hand_tools_detail"
_HAND_TOOL_ADJUST_ID_KEY = "ht_adjust_tool_id"
_HAND_TOOL_FILTER_COLUMN_LAYOUT: list[tuple[str | None, str | None]] = [
    (None, None),
    (None, None),
    ("CATEGORY", "category"),
    (None, None),
    (None, None),
    ("LOCATION", "location"),
    ("STORAGE", "storage_type"),
    ("STATUS", "status"),
    (None, None),
]
_HAND_TOOL_FILTER_COL_WEIGHTS: list[int] = [
    HAND_TOOLS_TABLE_COL_WIDTHS_PX[key]
    for key in ("image", "name", "category", "expected", "actual", "location", "storage", "status", "actions")
]
_FILTER_SPECS: list[tuple[str, object]] = [
    ("category", lambda r: str(r.get("category") or "")),
    ("location", lambda r: str(r.get("location_display") or "")),
    ("storage_type", lambda r: str(r.get("storage_type") or "")),
    ("job", lambda r: str(r.get("job_label") or "—")),
    ("status", lambda r: str(r.get("status") or "")),
    ("condition", lambda r: str(r.get("condition") or "")),
]


def _current_user_id() -> str | None:
    from app.auth import current_profile

    uid = str((current_profile() or {}).get("id") or "").strip()
    return uid or None


def _render_hand_tool_photo_manager(tool: dict) -> None:
    rid = str(tool.get("id") or "").strip()
    if not rid:
        return
    record_key = record_session_key(tool, "id")
    preview = small_hand_tool_photo_preview_record(tool)
    render_item_photo_manager(
        tool,
        record_id=rid,
        session_prefix=f"ht_photo_{record_key}",
        image_css_class="ips-asset-thumb-img",
        upload_image=upload_small_hand_tool_image,
        clear_image=clear_small_hand_tool_image,
        uploaded_by=_current_user_id(),
        cache_key=_HAND_TOOL_CACHE_KEY,
        on_change=clear_hand_tools_list_cache,
        preview_record=preview,
    )


def _trailer_options() -> tuple[list[str], dict[str, str]]:
    labels = ["— None —"]
    label_to_id: dict[str, str] = {}
    for trailer in get_tool_trailers():
        number = str(trailer.get("asset_number") or "").strip()
        name = str(trailer.get("asset_name") or trailer.get("name") or "Trailer").strip()
        label = f"{number} · {name}" if number else name
        labels.append(label)
        label_to_id[label] = str(trailer.get("id") or "")
    return labels, label_to_id


def _job_options() -> tuple[list[str], dict[str, str]]:
    from app.pages._core._data import load_jobs
    labels = ["— None —"]
    label_to_id: dict[str, str] = {}
    for job in load_jobs():
        jid = str(job.get("id") or "").strip()
        if not jid:
            continue
        number = str(job.get("job_number") or "").strip()
        name = str(job.get("job_name") or job.get("name") or "").strip()
        label = f"{number} · {name}" if number and name else (number or name or jid[:8])
        labels.append(label)
        label_to_id[label] = jid
    return labels, label_to_id


def _render_assign_hand_tool_to_kit(tool: dict) -> None:
    rid = str(tool.get("id") or "").strip()
    if not rid or tool.get("row_type") != "hand_tool":
        return
    if str(tool.get("serial_number") or "").strip():
        return

    trailers, trailer_map = _trailer_options()
    pick_labels = [label for label in trailers if label != "— None —"]
    if not pick_labels:
        return

    current_cid = str(tool.get("container_asset_id") or "").strip()
    with st.expander("Assign to Tool Trailer kit", expanded=False):
        st.caption(
            "Adds this tool to the selected trailer kit and sets storage to Tool Trailer. "
            "If the tool is on another trailer, its old kit line is removed."
        )
        default_idx = 0
        for idx, label in enumerate(pick_labels):
            if trailer_map.get(label) == current_cid:
                default_idx = idx
                break
        pick = st.selectbox(
            "Tool Trailer",
            pick_labels,
            index=default_idx,
            key=f"ht_kit_assign_trailer_{rid}",
        )
        kit_qty = st.number_input(
            "Kit quantity",
            min_value=1.0,
            value=float(tool.get("quantity_on_hand") or 1),
            step=1.0,
            key=f"ht_kit_assign_qty_{rid}",
        )
        if st.button("Add to kit", key=f"ht_kit_assign_btn_{rid}", type="primary"):
            trailer_id = trailer_map.get(pick) or ""
            result = link_hand_tool_to_kit(rid, trailer_id, kit_qty=kit_qty)
            if result.ok:
                clear_hand_tools_list_cache()
                st.success("Tool linked to trailer kit.")
                st.rerun()
            st.error(result.error or "Could not assign tool to kit.")


def _render_add_hand_tool_form() -> None:
    with st.expander("Add Small Hand Tool", expanded=False):
        trailer_labels, trailer_map = _trailer_options()
        job_labels, job_map = _job_options()
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Tool name", key="ht_new_name", placeholder="Channel-lock Pliers 10in")
            st.selectbox("Category", HAND_TOOL_CATEGORIES, key="ht_new_category")
            st.number_input("Quantity on hand", min_value=0.0, value=1.0, step=1.0, key="ht_new_qty")
            st.number_input("Expected quantity", min_value=0.0, value=1.0, step=1.0, key="ht_new_qty_exp")
        with c2:
            st.selectbox("Storage", STORAGE_TYPES, key="ht_new_storage")
            st.selectbox("Tool Trailer", trailer_labels, key="ht_new_trailer")
            st.text_input("Shop / warehouse location", key="ht_new_location", placeholder="Shop tool crib")
            st.selectbox("Assigned job", job_labels, key="ht_new_job")
        c3, c4 = st.columns(2)
        with c3:
            st.number_input("Unit value", min_value=0.0, value=0.0, step=1.0, key="ht_new_value")
            st.selectbox("Status", HAND_TOOL_STATUSES, key="ht_new_status")
        with c4:
            st.selectbox("Condition", HAND_TOOL_CONDITIONS, key="ht_new_condition")
            st.text_area("Notes", key="ht_new_notes", height=60)
        if st.button("Save Hand Tool", type="primary", key="ht_save_new"):
            storage = str(st.session_state.get("ht_new_storage") or "Warehouse")
            trailer_pick = str(st.session_state.get("ht_new_trailer") or "")
            job_pick = str(st.session_state.get("ht_new_job") or "")
            result = save_hand_tool(
                {
                    "tool_name": st.session_state.get("ht_new_name"),
                    "category": st.session_state.get("ht_new_category"),
                    "quantity_on_hand": st.session_state.get("ht_new_qty"),
                    "quantity_expected": st.session_state.get("ht_new_qty_exp"),
                    "unit_value": st.session_state.get("ht_new_value"),
                    "storage_type": storage,
                    "container_asset_id": trailer_map.get(trailer_pick)
                    if storage == "Tool Trailer" and trailer_pick != "— None —"
                    else None,
                    "storage_location": st.session_state.get("ht_new_location"),
                    "assigned_job_id": job_map.get(job_pick) if job_pick != "— None —" else None,
                    "status": st.session_state.get("ht_new_status"),
                    "condition": st.session_state.get("ht_new_condition"),
                    "notes": st.session_state.get("ht_new_notes"),
                }
            )
            if result.ok:
                st.success("Hand tool saved.")
                st.rerun()
            st.error(result.error or "Could not save hand tool.")


def open_hand_tool_detail(tool: dict) -> None:
    """Open the small hand tool detail dialog for a table row."""
    rid = str(tool.get("id") or "").strip()
    if not rid:
        return
    open_record_modal(
        rid,
        tool,
        session_select_key=_HAND_TOOL_SEL,
        modal_key=_HAND_TOOL_MODAL_KEY,
        module=_HAND_TOOL_MOD,
        id_fields=("id",),
    )


def _clear_hand_tool_detail_modal() -> None:
    clear_record_modal(
        table_key=_HAND_TOOL_DETAIL_TABLE_KEY,
        session_select_key=_HAND_TOOL_SEL,
        modal_key=_HAND_TOOL_MODAL_KEY,
        module=_HAND_TOOL_MOD,
    )


def _trailer_label_for_id(container_id: object, trailer_map: dict[str, str]) -> str:
    cid = str(container_id or "").strip()
    if not cid:
        return "— None —"
    for label, tid in trailer_map.items():
        if tid == cid:
            return label
    return "— None —"


def _job_label_for_id(job_id: object, job_map: dict[str, str]) -> str:
    jid = str(job_id or "").strip()
    if not jid:
        return "— None —"
    for label, j in job_map.items():
        if j == jid:
            return label
    return "— None —"


def _seed_hand_tool_edit_form(tool: dict) -> None:
    rid = str(tool.get("id") or "").strip()
    if not rid:
        return
    trailer_labels, trailer_map = _trailer_options()
    job_labels, job_map = _job_options()
    storage = str(tool.get("storage_type") or "Warehouse")
    trailer_label = _trailer_label_for_id(tool.get("container_asset_id"), trailer_map)
    if trailer_label not in trailer_labels:
        trailer_label = "— None —"
    job_label = _job_label_for_id(tool.get("assigned_job_id"), job_map)
    if job_label not in job_labels:
        job_label = "— None —"

    st.session_state[f"ht_edit_name_{rid}"] = str(tool.get("tool_name") or "")
    st.session_state[f"ht_edit_category_{rid}"] = str(tool.get("category") or "Other")
    st.session_state[f"ht_edit_model_{rid}"] = str(tool.get("model_number") or "")
    st.session_state[f"ht_edit_serial_{rid}"] = str(tool.get("serial_number") or "")
    st.session_state[f"ht_edit_qty_{rid}"] = float(tool.get("quantity_on_hand") or 0)
    st.session_state[f"ht_edit_qty_exp_{rid}"] = float(tool.get("quantity_expected") or tool.get("quantity_on_hand") or 0)
    st.session_state[f"ht_edit_value_{rid}"] = float(tool.get("unit_value") or 0)
    st.session_state[f"ht_edit_storage_{rid}"] = storage if storage in STORAGE_TYPES else "Warehouse"
    st.session_state[f"ht_edit_trailer_{rid}"] = trailer_label
    st.session_state[f"ht_edit_location_{rid}"] = str(tool.get("storage_location") or "")
    st.session_state[f"ht_edit_job_{rid}"] = job_label
    st.session_state[f"ht_edit_status_{rid}"] = str(tool.get("status") or "Available")
    st.session_state[f"ht_edit_condition_{rid}"] = str(tool.get("condition") or "Good")
    st.session_state[f"ht_edit_notes_{rid}"] = str(tool.get("notes") or "")


def _set_hand_tool_edit_mode(tool: dict) -> None:
    _seed_hand_tool_edit_form(tool)
    set_edit_mode(_HAND_TOOL_MOD, record_session_key(tool, "id"))


def _render_hand_tool_edit_form(tool: dict) -> None:
    rid = str(tool.get("id") or "").strip()
    record_key = record_session_key(tool, "id")
    if not rid:
        return
    if f"ht_edit_name_{rid}" not in st.session_state:
        _seed_hand_tool_edit_form(tool)

    trailer_labels, trailer_map = _trailer_options()
    job_labels, job_map = _job_options()

    render_edit_form_header("Edit Small Hand Tool")

    _render_hand_tool_photo_manager(tool)

    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Tool name", key=f"ht_edit_name_{rid}")
        st.selectbox("Category", HAND_TOOL_CATEGORIES, key=f"ht_edit_category_{rid}")
        st.text_input("Model #", key=f"ht_edit_model_{rid}")
        st.text_input("Serial #", key=f"ht_edit_serial_{rid}")
    with c2:
        st.selectbox("Status", HAND_TOOL_STATUSES, key=f"ht_edit_status_{rid}")
        st.selectbox("Condition", HAND_TOOL_CONDITIONS, key=f"ht_edit_condition_{rid}")
        st.number_input("Quantity on hand", min_value=0.0, step=1.0, key=f"ht_edit_qty_{rid}")
        st.number_input("Expected quantity", min_value=0.0, step=1.0, key=f"ht_edit_qty_exp_{rid}")

    st.markdown("##### Financial")
    f1, f2 = st.columns(2)
    with f1:
        st.number_input(
            "Unit value",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            key=f"ht_edit_value_{rid}",
            help="Used to calculate total value and Tool Trailer kit totals.",
        )
    with f2:
        qty = float(st.session_state.get(f"ht_edit_qty_{rid}") or 0)
        unit_val = float(st.session_state.get(f"ht_edit_value_{rid}") or 0)
        st.metric("Total value", fmt_currency(qty * unit_val))

    st.markdown("##### Storage & assignment")
    s1, s2 = st.columns(2)
    with s1:
        st.selectbox("Storage", STORAGE_TYPES, key=f"ht_edit_storage_{rid}")
        storage = str(st.session_state.get(f"ht_edit_storage_{rid}") or "Warehouse")
        if storage == "Tool Trailer":
            st.selectbox("Tool Trailer", trailer_labels, key=f"ht_edit_trailer_{rid}")
        st.text_input("Shop / warehouse location", key=f"ht_edit_location_{rid}")
    with s2:
        st.selectbox("Assigned job", job_labels, key=f"ht_edit_job_{rid}")
        st.text_area("Notes", key=f"ht_edit_notes_{rid}", height=80)

    cancelled, saved = render_save_cancel_actions(
        module=_HAND_TOOL_MOD,
        record_key=record_key,
        cancel_key=f"ht_modal_cancel_{record_key}",
        save_key=f"ht_modal_save_{record_key}",
    )
    if cancelled:
        st.rerun()
    if not saved:
        return

    storage = str(st.session_state.get(f"ht_edit_storage_{rid}") or "Warehouse")
    trailer_pick = str(st.session_state.get(f"ht_edit_trailer_{rid}") or "")
    job_pick = str(st.session_state.get(f"ht_edit_job_{rid}") or "")
    result = save_hand_tool(
        {
            "tool_name": st.session_state.get(f"ht_edit_name_{rid}"),
            "category": st.session_state.get(f"ht_edit_category_{rid}"),
            "model_number": st.session_state.get(f"ht_edit_model_{rid}"),
            "serial_number": st.session_state.get(f"ht_edit_serial_{rid}"),
            "quantity_on_hand": st.session_state.get(f"ht_edit_qty_{rid}"),
            "quantity_expected": st.session_state.get(f"ht_edit_qty_exp_{rid}"),
            "unit_value": st.session_state.get(f"ht_edit_value_{rid}"),
            "storage_type": storage,
            "container_asset_id": trailer_map.get(trailer_pick)
            if storage == "Tool Trailer" and trailer_pick != "— None —"
            else None,
            "storage_location": st.session_state.get(f"ht_edit_location_{rid}"),
            "assigned_job_id": job_map.get(job_pick) if job_pick != "— None —" else None,
            "status": st.session_state.get(f"ht_edit_status_{rid}"),
            "condition": st.session_state.get(f"ht_edit_condition_{rid}"),
            "notes": st.session_state.get(f"ht_edit_notes_{rid}"),
            "source_asset_id": tool.get("source_asset_id"),
        },
        row_id=rid,
    )
    if not result.ok:
        st.error(result.error or "Could not save hand tool.")
        return
    set_view_mode(_HAND_TOOL_MOD, record_key)
    st.success("Hand tool saved.")
    st.rerun()


def render_hand_tool_detail_dialog(tool: dict) -> None:
    record_key = record_session_key(tool, "id")
    name = safe_value(tool.get("tool_name"))
    category = safe_value(tool.get("category"))
    status = safe_value(tool.get("status"))
    qty_exp = tool.get("quantity_expected") or 0
    qty_act = tool.get("quantity_on_hand") or 0
    location = safe_value(tool.get("location_display"))
    storage = safe_value(tool.get("storage_type"))
    condition = safe_value(tool.get("condition"))
    job = safe_value(tool.get("job_label"))
    model = str(tool.get("model_number") or "").strip()
    serial = str(tool.get("serial_number") or "").strip()
    notes = str(tool.get("notes") or "").strip()
    editable = bool(tool.get("editable", True))
    row_type = str(tool.get("row_type") or "hand_tool")
    can_edit = editable and row_type == "hand_tool"

    render_modal_shell(compact=True)

    if is_edit_mode(_HAND_TOOL_MOD, record_key) and can_edit:
        _render_hand_tool_edit_form(tool)
        return

    if can_edit:
        render_compact_modal_header(
            title=name,
            subtitle=category,
            status=status,
            module=_HAND_TOOL_MOD,
            record_key=record_key,
            on_edit=lambda: _set_hand_tool_edit_mode(tool),
            key_prefix=f"ht_modal_{record_key}",
        )
    else:
        render_modal_header(title=name, subtitle=category, status=status)

    if can_edit:
        _render_hand_tool_photo_manager(tool)
        _render_assign_hand_tool_to_kit(tool)

    meta: list[tuple[str, object]] = []
    if model:
        meta.append(("Model", model))
    if serial:
        meta.append(("Serial", serial))
    meta.extend(
        [
            ("Expected", f"{qty_exp:g}"),
            ("Actual", f"{qty_act:g}"),
            ("Location", location),
            ("Storage", storage),
            ("Condition", condition),
            ("Unit Value", fmt_currency(tool.get("unit_value"))),
            ("Total Value", fmt_currency(tool.get("total_value"))),
            ("Job", job),
        ]
    )
    render_modal_meta_grid(meta)

    if not can_edit:
        trailer = safe_value(tool.get("container_label"))
        if trailer and trailer != "—":
            st.info(
                f"Trailer kit item — edit quantity and unit value on the **Tool Trailer** "
                f"({trailer}) kit tab so kit totals stay accurate."
            )
        else:
            st.info("Trailer kit item — edit quantity and unit value in the Tool Trailer kit tab.")

    if notes and notes not in {"—", "-"}:
        st.markdown(
            dialog_card_html("Notes", detail_field_html("Notes", notes)),
            unsafe_allow_html=True,
        )


@st.dialog("Small Tool Details", width="large", on_dismiss=_clear_hand_tool_detail_modal)
def _show_hand_tool_detail_modal() -> None:
    tool = get_modal_record(
        cache_key=_HAND_TOOL_CACHE_KEY,
        modal_key=_HAND_TOOL_MODAL_KEY,
        session_select_key=_HAND_TOOL_SEL,
    )
    if not tool:
        render_missing_record(_clear_hand_tool_detail_modal, close_key="ht_modal_missing_close")
        return
    render_hand_tool_detail_dialog(tool)


@st.dialog("Adjust count", width="small", on_dismiss=lambda: st.session_state.pop(_HAND_TOOL_ADJUST_ID_KEY, None))
def _show_hand_tool_adjust_dialog(tool: dict) -> None:
    rid = str(tool.get("id") or "").strip()
    if not rid:
        return
    name = str(tool.get("tool_name") or "tool")
    st.caption(name)
    delta = st.number_input("Count change (+/−)", value=0.0, step=1.0, key=f"ht_dialog_delta_{rid}")
    adj_notes = st.text_input("Audit notes", key=f"ht_dialog_notes_{rid}")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Apply adjustment", key=f"ht_dialog_apply_{rid}", type="primary", use_container_width=True):
            if delta == 0:
                st.warning("Enter a non-zero count change.")
            else:
                result = adjust_hand_tool_quantity(rid, delta, notes=adj_notes)
                if result.ok:
                    st.session_state.pop(_HAND_TOOL_ADJUST_ID_KEY, None)
                    st.success("Count adjusted.")
                    st.rerun()
                st.error(result.error or "Adjustment failed.")
    with c2:
        if st.button("Remove tool", key=f"ht_dialog_remove_{rid}", use_container_width=True):
            result = delete_hand_tool(rid)
            if result.ok:
                st.session_state.pop(_HAND_TOOL_ADJUST_ID_KEY, None)
                st.success("Hand tool removed.")
                st.rerun()
            st.error(result.error or "Remove failed.")


def _queue_hand_tool_adjust(row: dict) -> None:
    rid = str(row.get("id") or "").strip()
    if rid:
        st.session_state[_HAND_TOOL_ADJUST_ID_KEY] = rid


def _filter_rows(rows: list[dict], *, q: str = "") -> list[dict]:
    out = list(rows)
    if q:
        ql = q.casefold()
        out = [
            r
            for r in out
            if ql in str(r.get("tool_name") or "").casefold()
            or ql in str(r.get("category") or "").casefold()
            or ql in str(r.get("location_display") or "").casefold()
        ]
    return apply_column_filters(out, _TABLE_KEY, _FILTER_SPECS)


_PAGE_SIZE_OPTIONS = (50, 75, 100, 150)


def _render_hand_tools_pagination_header(total: int) -> None:
    """Pagination summary aligned with the hand-tools table width."""
    page, page_size, total_pages = pagination_meta(total, _TABLE_KEY)
    with st.container(key="assets_hand_tools_pg_header"):
        c1, c2 = st.columns([2.2, 1], gap="small")
        with c1:
            st.caption(
                f"{total:,} tool{'' if total == 1 else 's'}"
                + (f" · page {page} of {total_pages}" if total_pages > 1 else "")
            )
        with c2:
            picked = st.selectbox(
                "Rows per page",
                list(_PAGE_SIZE_OPTIONS),
                index=_PAGE_SIZE_OPTIONS.index(page_size)
                if page_size in _PAGE_SIZE_OPTIONS
                else _PAGE_SIZE_OPTIONS.index(DEFAULT_CATALOG_PAGE_SIZE),
                key=f"{_TABLE_KEY}_pg_size_select",
                label_visibility="collapsed",
            )
            if int(picked) != page_size:
                from app.components.table_pagination import page_size_key

                st.session_state[page_size_key(_TABLE_KEY)] = int(picked)
                reset_table_page(_TABLE_KEY)
                st.rerun()


def _render_hand_tools_table_column_filters(*, filter_options: dict[str, list[str]]) -> None:
    st.markdown(
        '<div class="ips-assets-table-filter-toolbar ips-hand-tools-filter-toolbar">',
        unsafe_allow_html=True,
    )
    cols = st.columns(_HAND_TOOL_FILTER_COL_WEIGHTS, gap="small")
    for col, (label, field) in zip(cols, _HAND_TOOL_FILTER_COLUMN_LAYOUT):
        with col:
            if label and field:
                render_table_header_cell(
                    label,
                    table_key=_TABLE_KEY,
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


def _render_table(
    rows: list[dict],
    *,
    filter_options: dict[str, list[str]],
    image_context: CatalogImageContext,
    on_open_tool: Callable[[dict], None] | None = None,
) -> None:
    if not rows:
        st.info("No small hand tools match your filters.")
        return

    row_by_id = {str(row.get("id") or "").strip(): row for row in rows if str(row.get("id") or "").strip()}

    def _open_row(row_id: str, row: dict) -> None:
        if on_open_tool:
            on_open_tool(row)
        else:
            open_hand_tool_detail(row)

    def _adjust_row(_row_id: str, row: dict) -> None:
        _queue_hand_tool_adjust(row)

    with st.container(key="assets_table_wrap"):
        st.markdown(
            '<div class="ips-assets-table-wrap ips-hand-tools-table-wrap">',
            unsafe_allow_html=True,
        )
        _render_hand_tools_table_column_filters(filter_options=filter_options)
        st.markdown(
            build_hand_tools_html_table(rows, image_context=image_context),
            unsafe_allow_html=True,
        )
        render_hand_tools_table_open_buttons(rows, open_row_fn=_open_row)
        render_hand_tools_table_bridge_legacy(
            row_by_id,
            open_row_fn=_open_row,
            adjust_row_fn=_adjust_row,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    adjust_id = str(st.session_state.get(_HAND_TOOL_ADJUST_ID_KEY) or "").strip()
    if adjust_id and adjust_id in row_by_id:
        _show_hand_tool_adjust_dialog(row_by_id[adjust_id])


def render_hand_tools_tab(
    all_assets: list[dict] | None = None,
    *,
    on_open_tool: Callable[[dict], None] | None = None,
) -> None:
    """Quantity-based small hand tools — pliers, wrenches, etc."""
    import_msg = st.session_state.pop("ht_import_success_message", None)
    if import_msg:
        st.success(str(import_msg))
    st.caption(
        "Small tools are **counted** and **audited** (not checked out). Track expected vs actual quantity "
        "per Tool Trailer, shop, warehouse, or job — **move**, mark **missing**, or **adjust** counts."
    )
    _ = all_assets
    assets_by_id = {
        str(a.get("id") or "").strip(): a
        for a in (all_assets or load_assets())
        if str(a.get("id") or "").strip()
    }
    from app.pages._core._data import load_jobs
    jobs_by_id = {str(j.get("id") or "").strip(): j for j in load_jobs() if str(j.get("id") or "").strip()}

    rows = list_hand_tools(assets_by_id=assets_by_id, jobs_by_id=jobs_by_id)
    image_context = build_catalog_image_context(
        assets_by_id=assets_by_id,
        inventory_rows=load_inventory(),
    )
    filter_options = build_filter_options(rows, _FILTER_SPECS)
    categories = sorted({str(r.get("category") or "") for r in rows if r.get("category")})
    locations = sorted({str(r.get("location_display") or "") for r in rows if r.get("location_display")})

    def _filters() -> None:
        c1, c2, c3, c4 = st.columns([2.4, 1.2, 1.2, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search tool name, category, location…",
                key="ht_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "Category",
                ["All Categories", *categories],
                key="ht_category",
                label_visibility="collapsed",
            )
        with c3:
            st.selectbox(
                "Location",
                ["All Locations", *locations],
                key="ht_location",
                label_visibility="collapsed",
            )
        with c4:
            if st.button("Clear", key="ht_clear", use_container_width=True):
                clear_table_filters(
                    _TABLE_KEY,
                    ["category", "location", "storage_type", "job", "status", "condition"],
                    extra_keys=["ht_search", "ht_category", "ht_location"],
                )
                st.session_state["ht_category"] = "All Categories"
                st.session_state["ht_location"] = "All Locations"
                reset_table_page(_TABLE_KEY)
                st.rerun()

    layout_filter_bar(_filters)
    _render_add_hand_tool_form()

    filtered = _filter_rows(rows, q=str(st.session_state.get("ht_search") or "").strip())
    cat = str(st.session_state.get("ht_category") or "All Categories")
    if cat != "All Categories":
        filtered = [r for r in filtered if str(r.get("category") or "") == cat]
    loc = str(st.session_state.get("ht_location") or "All Locations")
    if loc != "All Locations":
        filtered = [r for r in filtered if str(r.get("location_display") or "") == loc]

    _render_hand_tools_pagination_header(len(filtered))
    page_rows, _, _, _ = paginate_rows(filtered, _TABLE_KEY)
    _render_table(
        page_rows,
        filter_options=filter_options,
        image_context=image_context,
        on_open_tool=on_open_tool,
    )
    render_table_pagination_footer(len(filtered), _TABLE_KEY)
    build_modal_cache(rows, cache_key=_HAND_TOOL_CACHE_KEY)
    show_modal_if_pending(_HAND_TOOL_MODAL_KEY, _show_hand_tool_detail_modal)
