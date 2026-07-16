"""Quantity-based Small Hand Tools tab on the Assets page."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

from app.components.record_modal import (
    build_modal_cache,
    clear_record_modal,
    detail_field_html,
    dialog_card_html,
    get_modal_record,
    open_record_modal,
    render_missing_record,
    render_modal_header,
    render_modal_meta_grid,
    render_modal_shell,
    safe_value,
    show_modal_if_pending,
)
from app.components.table_filters import (
    apply_column_filters,
    build_filter_options,
    render_table_header_cell,
)
from app.components.table_pagination import paginate_rows, render_table_pagination_footer, render_table_pagination_header, reset_table_page
from app.components.table_filters import clear_table_filters
from app.components.layout import render_filter_bar as layout_filter_bar
from app.pages._core._data import load_assets, load_inventory
from app.services.asset_kits_service import get_tool_trailers
from app.services.catalog_images import CatalogImageContext, build_catalog_image_context, catalog_thumbnail_html
from app.services.small_hand_tool_service import (
    HAND_TOOL_CATEGORIES,
    HAND_TOOL_CONDITIONS,
    HAND_TOOL_STATUSES,
    STORAGE_TYPES,
    adjust_hand_tool_quantity,
    delete_hand_tool,
    list_hand_tools,
    save_hand_tool,
)
from app.utils.formatting import fmt_currency

_TABLE_KEY = "assets_hand_tools_list"
_HAND_TOOL_MOD = "hand_tool"
_HAND_TOOL_SEL = "ht_detail_sel"
_HAND_TOOL_MODAL_KEY = "ht_detail_modal"
_HAND_TOOL_CACHE_KEY = "ht_detail_cache"
_HAND_TOOL_DETAIL_TABLE_KEY = "assets_hand_tools_detail"
_COLS = [0.22, 0.42, 2.35, 1.0, 0.48, 0.48, 1.0, 0.92, 0.85, 0.78]
_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("IMAGE", None),
    ("TOOL", None),
    ("CATEGORY", "category"),
    ("EXPECTED", None),
    ("ACTUAL", None),
    ("LOCATION", "location"),
    ("STORAGE", "storage_type"),
    ("STATUS", "status"),
    ("ACTIONS", None),
]
_FILTER_SPECS: list[tuple[str, object]] = [
    ("category", lambda r: str(r.get("category") or "")),
    ("location", lambda r: str(r.get("location_display") or "")),
    ("storage_type", lambda r: str(r.get("storage_type") or "")),
    ("job", lambda r: str(r.get("job_label") or "—")),
    ("status", lambda r: str(r.get("status") or "")),
    ("condition", lambda r: str(r.get("condition") or "")),
]


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


def render_hand_tool_detail_dialog(tool: dict) -> None:
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

    render_modal_shell(compact=True)
    render_modal_header(title=name, subtitle=category, status=status)

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

    if not editable:
        st.info("Trailer kit item — edit quantity in the Tool Trailer kit tab.")

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


def _hand_tool_status_pill_html(status: str) -> str:
    cls_map = {
        "Available": "ips-asset-status-available",
        "In Use": "ips-asset-status-assigned",
        "Low Stock": "ips-asset-status-maintenance-due",
        "Missing": "ips-asset-status-lost",
        "Damaged": "ips-asset-status-out-for-repair",
        "Out of Service": "ips-asset-status-retired",
        "Retired": "ips-asset-status-retired",
    }
    cls = cls_map.get(status, "ips-asset-status-available")
    return f'<span class="ips-asset-status-pill {cls}">{html.escape(status)}</span>'


def _render_hand_tool_adjust_action(row: dict) -> None:
    rid = str(row.get("id") or "").strip()
    editable = bool(row.get("editable", True))
    if not rid or not editable:
        st.markdown(
            '<div class="ips-hand-tools-cell ips-assets-muted">—</div>',
            unsafe_allow_html=True,
        )
        return

    name = str(row.get("tool_name") or "tool")
    with st.popover("Adjust count", type="primary"):
        st.caption(name)
        delta = st.number_input("Count change (+/−)", value=0.0, step=1.0, key=f"ht_delta_{rid}")
        adj_notes = st.text_input("Audit notes", key=f"ht_adj_notes_{rid}")
        ac1, ac2 = st.columns(2)
        with ac1:
            if st.button("Apply adjustment", key=f"ht_adj_go_{rid}", use_container_width=True):
                if delta == 0:
                    st.warning("Enter a non-zero count change.")
                else:
                    result = adjust_hand_tool_quantity(rid, delta, notes=adj_notes)
                    if result.ok:
                        st.success("Count adjusted.")
                        st.rerun()
                    st.error(result.error or "Adjustment failed.")
        with ac2:
            if st.button("Remove", key=f"ht_del_{rid}", use_container_width=True):
                result = delete_hand_tool(rid)
                if result.ok:
                    st.success("Hand tool removed.")
                    st.rerun()
                st.error(result.error or "Remove failed.")


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


def _render_hand_tool_name_cell(
    row: dict,
    name: str,
    *,
    on_open_tool: Callable[[dict], None] | None,
    title_attr: str = "",
) -> None:
    rid = str(row.get("id") or "").strip()
    if on_open_tool and rid:
        st.markdown(
            f'<span class="ips-hand-tools-name-anchor"{title_attr} aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        if st.button(name, key=f"ht_open_name_{rid}", type="tertiary"):
            on_open_tool(row)
        return
    st.markdown(
        f'<div class="ips-assets-title ips-hand-tools-cell"{title_attr}>{html.escape(name)}</div>',
        unsafe_allow_html=True,
    )


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

    with st.container(key="assets_hand_tools_table_wrap"):
        st.markdown(
            '<div class="ips-assets-table-wrap ips-hand-tools-table-wrap">',
            unsafe_allow_html=True,
        )
        header_cols = st.columns(_COLS, gap="small", vertical_alignment="center")
        for idx, (col, (label, field)) in enumerate(zip(header_cols, _HEADER_SPECS)):
            with col:
                if idx == 0:
                    st.markdown(
                        '<span class="small-tools-table-header" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-assets-header-row ips-hand-tools-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-assets-header-row ips-hand-tools-cell",
                    )

        for row in rows:
            rid = str(row.get("id") or "")
            cols = st.columns(_COLS, gap="small", vertical_alignment="center")
            name = str(row.get("tool_name") or "—")
            category = str(row.get("category") or "—")
            qty_exp = row.get("quantity_expected") or 0
            qty_act = row.get("quantity_on_hand") or 0
            qty_short = qty_act < qty_exp
            location = str(row.get("location_display") or "—")
            storage = str(row.get("storage_type") or "—")
            status = str(row.get("status") or "—")
            editable = bool(row.get("editable", True))
            title_attr = (
                ' title="Trailer kit item — edit in Tool Trailer kit tab"'
                if not editable
                else ""
            )

            with cols[0]:
                st.markdown(
                    '<span class="ips-hand-tools-row-marker small-tools-table-row" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                st.markdown(
                    catalog_thumbnail_html(row, kind="small_tool", context=image_context, alt="Small tool image"),
                    unsafe_allow_html=True,
                )
            with cols[2]:
                _render_hand_tool_name_cell(
                    row,
                    name,
                    on_open_tool=on_open_tool,
                    title_attr=title_attr,
                )
            with cols[3]:
                st.markdown(
                    f'<div class="ips-hand-tools-cell">{html.escape(category)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[4]:
                st.markdown(
                    f'<div class="ips-hand-tools-cell ips-hand-tools-qty">{qty_exp:g}</div>',
                    unsafe_allow_html=True,
                )
            with cols[5]:
                short_cls = " ips-assets-qty-short" if qty_short else ""
                st.markdown(
                    f'<div class="ips-hand-tools-cell ips-hand-tools-qty{short_cls}"><strong>{qty_act:g}</strong></div>',
                    unsafe_allow_html=True,
                )
            with cols[6]:
                st.markdown(
                    f'<div class="ips-assets-muted ips-hand-tools-cell">{html.escape(location)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[7]:
                st.markdown(
                    f'<div class="ips-hand-tools-cell">{html.escape(storage)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[8]:
                st.markdown(_hand_tool_status_pill_html(status), unsafe_allow_html=True)
            with cols[9]:
                _render_hand_tool_adjust_action(row)

        st.markdown("</div>", unsafe_allow_html=True)


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

    render_table_pagination_header(len(filtered), _TABLE_KEY, item_label="tool")
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
