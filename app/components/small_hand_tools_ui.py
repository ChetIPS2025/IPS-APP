"""Quantity-based Small Hand Tools tab on the Assets page."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.components.table_filters import (
        apply_column_filters,
        build_filter_options,
        render_table_header_cell,
    )
    from app.components.table_pagination import paginate_rows, render_table_pagination_footer, render_table_pagination_header, reset_table_page
    from app.components.table_filters import clear_table_filters
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.pages._core._data import load_assets
    from app.services.asset_kits_service import get_tool_trailers
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
except ImportError:
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
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from pages._core._data import load_assets  # type: ignore
    from services.asset_kits_service import get_tool_trailers  # type: ignore
    from services.small_hand_tool_service import (  # type: ignore
        HAND_TOOL_CATEGORIES,
        HAND_TOOL_CONDITIONS,
        HAND_TOOL_STATUSES,
        STORAGE_TYPES,
        adjust_hand_tool_quantity,
        delete_hand_tool,
        list_hand_tools,
        save_hand_tool,
    )

_TABLE_KEY = "assets_hand_tools_list"
_COLS = [2.9, 1.05, 0.5, 0.5, 1.05, 0.95, 0.9, 0.8]
_HEADER_SPECS: list[tuple[str, str | None]] = [
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
    try:
        from app.pages._core._data import load_jobs
    except ImportError:
        from pages._core._data import load_jobs  # type: ignore
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
    with st.popover("Adjust", type="primary"):
        st.caption(name)
        delta = st.number_input("Qty change (+/−)", value=0.0, step=1.0, key=f"ht_delta_{rid}")
        adj_notes = st.text_input("Notes", key=f"ht_adj_notes_{rid}")
        ac1, ac2 = st.columns(2)
        with ac1:
            if st.button("Apply", key=f"ht_adj_go_{rid}", use_container_width=True):
                if delta == 0:
                    st.warning("Enter a non-zero quantity change.")
                else:
                    result = adjust_hand_tool_quantity(rid, delta, notes=adj_notes)
                    if result.ok:
                        st.success("Quantity updated.")
                        st.rerun()
                    st.error(result.error or "Update failed.")
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


def _render_table(rows: list[dict], *, filter_options: dict[str, list[str]]) -> None:
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
                    f'<span class="ips-hand-tools-row-marker small-tools-table-row" aria-hidden="true"></span>'
                    f'<div class="ips-assets-title ips-hand-tools-cell"{title_attr}>{html.escape(name)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                st.markdown(
                    f'<div class="ips-hand-tools-cell">{html.escape(category)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[2]:
                st.markdown(
                    f'<div class="ips-hand-tools-cell ips-hand-tools-qty">{qty_exp:g}</div>',
                    unsafe_allow_html=True,
                )
            with cols[3]:
                short_cls = " ips-assets-qty-short" if qty_short else ""
                st.markdown(
                    f'<div class="ips-hand-tools-cell ips-hand-tools-qty{short_cls}"><strong>{qty_act:g}</strong></div>',
                    unsafe_allow_html=True,
                )
            with cols[4]:
                st.markdown(
                    f'<div class="ips-assets-muted ips-hand-tools-cell">{html.escape(location)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[5]:
                st.markdown(
                    f'<div class="ips-hand-tools-cell">{html.escape(storage)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[6]:
                st.markdown(_hand_tool_status_pill_html(status), unsafe_allow_html=True)
            with cols[7]:
                _render_hand_tool_adjust_action(row)

        st.markdown("</div>", unsafe_allow_html=True)


def render_hand_tools_tab(all_assets: list[dict] | None = None) -> None:
    """Quantity-based small hand tools — pliers, wrenches, etc."""
    st.caption(
        "Quantity-counted hand tools (no serial number). Track **expected** vs **actual** quantity "
        "per Tool Trailer, shop, warehouse, or job."
    )
    _ = all_assets
    assets_by_id = {
        str(a.get("id") or "").strip(): a
        for a in (all_assets or load_assets())
        if str(a.get("id") or "").strip()
    }
    try:
        from app.pages._core._data import load_jobs
    except ImportError:
        from pages._core._data import load_jobs  # type: ignore
    jobs_by_id = {str(j.get("id") or "").strip(): j for j in load_jobs() if str(j.get("id") or "").strip()}

    rows = list_hand_tools(assets_by_id=assets_by_id, jobs_by_id=jobs_by_id)
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
    _render_table(page_rows, filter_options=filter_options)
    render_table_pagination_footer(len(filtered), _TABLE_KEY)
