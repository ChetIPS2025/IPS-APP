"""Pricing Guide — unified master estimating database (``pricing_guide_items``)."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.auth import current_role
    from app.components.action_styles import danger_outline_button
    from app.components.modal_delete import modal_danger_zone, render_modal_delete_panel
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.table_filters import (
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
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
    from app.components.tabs import render_tabs
    from app.db import fetch_table, fetch_table_admin
    from app.pages._core._crud import apply_persist_feedback
    from app.pages._core._data import load_assets, load_inventory
    from app.pages._core._session import select_key
    from app.services.pricing_guide_service import (
        PRICING_ITEM_TYPES,
        calc_sell_price,
        cached_pricing_guide_rows,
        delete_pricing_item,
        fetch_price_history,
        normalize_pricing_row,
        save_pricing_item,
        search_pricing_rows,
        pricing_guide_summary,
        type_pill_html,
    )
    from app.styles import inject_pricing_guide_module_css
    from app.utils.formatting import fmt_currency
except ImportError:
    from auth import current_role  # type: ignore
    from components.action_styles import danger_outline_button  # type: ignore
    from components.modal_delete import modal_danger_zone, render_modal_delete_panel  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.table_filters import (  # type: ignore
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
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
    from components.tabs import render_tabs  # type: ignore
    from db import fetch_table, fetch_table_admin  # type: ignore
    from pages._core._crud import apply_persist_feedback  # type: ignore
    from pages._core._data import load_assets, load_inventory  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from services.pricing_guide_service import (  # type: ignore
        PRICING_ITEM_TYPES,
        calc_sell_price,
        cached_pricing_guide_rows,
        delete_pricing_item,
        fetch_price_history,
        normalize_pricing_row,
        save_pricing_item,
        search_pricing_rows,
        pricing_guide_summary,
        type_pill_html,
    )
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
_PG_COLS = [0.35, 3.2, 1.15, 1.35, 0.75, 1.05, 0.85, 1.15, 1.35, 0.95]
_PG_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("DESCRIPTION", None),
    ("TYPE", "item_type"),
    ("CATEGORY", "category"),
    ("UNIT", None),
    ("COST", None),
    ("MARKUP %", None),
    ("SELL PRICE", None),
    ("VENDOR", "vendor"),
    ("STATUS", "status"),
]
_FILTER_FIELDS = ["item_type", "category", "vendor", "status"]
_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("item_type", lambda r: str(r.get("item_type") or "—")),
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


def _load_rows() -> list[dict[str, Any]]:
    return cached_pricing_guide_rows(include_inactive=True)


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
        ("Inventory Linked", str(stats["inventory_linked"])),
        ("Labor Items", str(stats["labor_count"])),
        ("Equipment Items", str(stats["equipment_count"])),
        ("Travel Items", str(stats["travel_count"])),
        ("Avg Markup", f"{stats['avg_markup']:.1f}%"),
        ("Last Updated", stats["last_updated"]),
    ]
    html_cards = "".join(
        f'<div class="ips-pg-summary-card"><div class="lbl">{html.escape(lbl)}</div>'
        f'<div class="val">{html.escape(val)}</div></div>'
        for lbl, val in cards
    )
    st.markdown(f'<div class="ips-pg-summary-grid">{html_cards}</div>', unsafe_allow_html=True)


def _clear_modal() -> None:
    row_ids = st.session_state.get(_ALL_PG_IDS_KEY) or []
    _clear_pg_selection([str(rid) for rid in row_ids])
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


def _pg_select_key(row_id: str) -> str:
    return f"pg_select_{row_id}"


def _clear_pg_selection(row_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_PG_KEY] = None
    st.session_state[SHOW_PG_MODAL_KEY] = False
    ids = list(row_ids or [])
    for rid in ids:
        st.session_state[_pg_select_key(rid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("pg_select_"):
            st.session_state[key] = False


def _on_pg_checkbox_change(row_id: str, all_row_ids: list[str]) -> None:
    key = _pg_select_key(row_id)
    if st.session_state.get(key):
        for rid in all_row_ids:
            if rid != row_id:
                st.session_state[_pg_select_key(rid)] = False
        st.session_state[SELECTED_PG_KEY] = row_id
        st.session_state[SHOW_PG_MODAL_KEY] = True
        cache = st.session_state.get(_CACHE_KEY) or {}
        row = cache.get(row_id) if isinstance(cache, dict) else None
        _open_modal(row_id, row)
    elif st.session_state.get(SELECTED_PG_KEY) == row_id:
        st.session_state[SELECTED_PG_KEY] = None
        st.session_state[SHOW_PG_MODAL_KEY] = False


def _pg_status_pill_html(status: str) -> str:
    cls_map = {
        "Active": "ips-pg-status-active",
        "Inactive": "ips-pg-status-inactive",
    }
    cls = cls_map.get(status, "ips-pg-status-active")
    return f'<span class="ips-pg-status-pill {cls}">{html.escape(status)}</span>'


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

    with st.container(key="pricing_guide_table_wrap"):
        st.markdown('<div class="ips-pg-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_PG_COLS, gap="small", vertical_alignment="center")
        for col, (label, field) in zip(header_cols, _PG_HEADER_SPECS):
            with col:
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-pg-header-row ips-pg-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-pg-header-row ips-pg-cell",
                    )

        for row in filtered:
            rid = str(row.get("id") or "").strip()
            if not rid:
                continue

            item = str(row.get("item") or "—")
            item_type = str(row.get("item_type") or "Material")
            category = str(row.get("category") or "—")
            unit = str(row.get("unit") or "—")
            default_cost = fmt_currency(row.get("default_cost"))
            markup = f"{float(row.get('markup_pct') or 0):.1f}%"
            sell_price = fmt_currency(row.get("customer_price"))
            vendor = str(row.get("vendor") or "—")
            status = str(row.get("status") or "Active")

            cols = st.columns(_PG_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                st.checkbox(
                    "",
                    key=_pg_select_key(rid),
                    label_visibility="collapsed",
                    on_change=_on_pg_checkbox_change,
                    args=(rid, all_row_ids),
                )

            with cols[1]:
                st.markdown(
                    f'<div class="ips-pg-title">{html.escape(item)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[2]:
                st.markdown(type_pill_html(item_type), unsafe_allow_html=True)

            with cols[3]:
                st.markdown(
                    f'<div class="ips-pg-cell">{html.escape(category)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(
                    f'<div class="ips-pg-muted ips-pg-cell">{html.escape(unit)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[5]:
                st.markdown(
                    f'<div class="ips-pg-cell ips-pg-money">{html.escape(default_cost)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[6]:
                st.markdown(
                    f'<div class="ips-pg-cell ips-pg-money">{html.escape(markup)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[7]:
                st.markdown(
                    f'<div class="ips-pg-cell ips-pg-money">{html.escape(sell_price)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[8]:
                st.markdown(
                    f'<div class="ips-pg-muted ips-pg-cell">{html.escape(vendor)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[9]:
                st.markdown(_pg_status_pill_html(status), unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    return all_row_ids


def _filter_rows(rows: list[dict[str, Any]], *, q: str) -> list[dict[str, Any]]:
    out = search_pricing_rows(rows, q)
    return apply_column_filters(out, _TABLE_KEY, _COLUMN_FILTER_SPECS)


def _persist_row(data: dict[str, Any], row_id: str | None = None) -> tuple[bool, str]:
    return save_pricing_item(data, row_id=row_id)


def _render_conditional_fields(prefix: str, item_type: str) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    if item_type == "Inventory":
        inv_opts = _inventory_options()
        pick = st.selectbox(
            "Link inventory item",
            [label for label, _ in inv_opts],
            key=f"{prefix}_inv",
        )
        inv_map = {label: vid for label, vid in inv_opts}
        extra["inventory_item_id"] = inv_map.get(pick) or None
    elif item_type == "Equipment":
        asset_opts = _asset_options()
        pick = st.selectbox(
            "Link asset",
            [label for label, _ in asset_opts],
            key=f"{prefix}_asset",
        )
        asset_map = {label: aid for label, aid in asset_opts}
        extra["asset_id"] = asset_map.get(pick) or None
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


def _render_add_form() -> None:
    with st.expander("New Pricing Item", expanded=True):
        c1, c2 = st.columns(2, gap="small")
        with c1:
            description = st.text_input("Description *", key="pg_new_desc")
            item_type = st.selectbox("Item Type *", list(PRICING_ITEM_TYPES), key="pg_new_type")
            unit = st.text_input("Unit *", value="EA", key="pg_new_unit")
            category = st.text_input("Category", key="pg_new_cat")
        with c2:
            cost = st.number_input("Cost *", min_value=0.0, value=0.0, key="pg_new_cost")
            markup = st.number_input("Markup % *", min_value=0.0, value=25.0, key="pg_new_mk")
            sell = calc_sell_price(float(st.session_state.get("pg_new_cost") or 0), float(st.session_state.get("pg_new_mk") or 0))
            st.metric("Sell Price", fmt_currency(sell))
            active = st.checkbox("Active", value=True, key="pg_new_active")

        extra = _render_conditional_fields("pg_new", item_type)

        if st.button("Save Pricing Item", key="pg_new_save", type="primary"):
            payload = {
                "description": description,
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
        st.markdown(
            dialog_card_html(
                "Overview",
                f"{detail_field_html('Description', row.get('item'))}"
                f"{detail_field_html('Item code', row.get('item_code') or row.get('item_key'))}"
                f'{detail_field_html("Type", row.get("item_type"), html_value=type_pill_html(str(row.get("item_type") or "")))}'
                f"{detail_field_html('Category', row.get('category'))}"
                f"{detail_field_html('Subcategory', row.get('subcategory') or '—')}"
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
        item_type = st.selectbox(
            "Item Type",
            list(PRICING_ITEM_TYPES),
            index=list(PRICING_ITEM_TYPES).index(str(row.get("item_type") or "Material"))
            if str(row.get("item_type") or "Material") in PRICING_ITEM_TYPES
            else 0,
            key=f"pg_edit_type_{rk}",
        )
        unit = st.text_input("Unit", value=str(row.get("unit") or "EA"), key=f"pg_edit_unit_{rk}")
        category = st.text_input("Category", value=str(row.get("category") or ""), key=f"pg_edit_cat_{rk}")
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

    extra = _render_conditional_fields(f"pg_edit_{rk}", item_type)
    notes = st.text_area("Notes", value=str(row.get("notes") or ""), key=f"pg_edit_notes_{rk}")

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
                "item_type": item_type,
                "category": extra.get("category") or category,
                "unit": unit,
                "default_cost": purchase,
                "default_markup_percent": markup,
                "default_sell_price": sell,
                "is_active": active,
                "notes": notes,
                "item_code": row.get("item_code") or row.get("item_key"),
                **extra,
            },
            row_id=str(row.get("id") or ""),
        )
        if apply_persist_feedback(ok, msg):
            set_view_mode(_MODULE, rk)
            st.rerun()
        st.error(msg or "Could not save pricing item.")


def _can_manage_pricing() -> bool:
    return str(current_role() or "").strip().lower() in {"admin", "supervisor", "manager"}


def _render_pricing_actions_panel(row: dict) -> None:
    rk = record_session_key(row, "id")
    if is_edit_mode(_MODULE, rk):
        return
    rid = str(row.get("id") or "").strip()
    if not rid:
        return
    try:
        from app.pages._core._crud import is_demo_id
    except ImportError:
        from pages._core._crud import is_demo_id  # type: ignore
    if is_demo_id(rid):
        return

    can_mutate = _can_manage_pricing()
    with modal_danger_zone():
        if danger_outline_button(
            "Deactivate Item",
            f"pg_deactivate_{rk}",
            disabled=not can_mutate,
            help="Marks this pricing item inactive.",
        ):
            try:
                from app.services.repository import update_row
            except ImportError:
                from services.repository import update_row  # type: ignore
            result = update_row("pricing_guide_items", {"is_active": False}, {"id": rid})
            if result.ok:
                try:
                    from app.services.pricing_guide_service import clear_pricing_guide_cache
                except ImportError:
                    from services.pricing_guide_service import clear_pricing_guide_cache  # type: ignore
                clear_pricing_guide_cache()
                _clear_modal()
                st.success("Pricing item deactivated.")
                st.rerun()
            st.error(result.error or "Could not deactivate pricing item.")

        def _delete_item() -> None:
            ok, msg = delete_pricing_item(rid)
            if ok:
                _clear_modal()
                st.success(msg or "Pricing item deleted.")
                st.rerun()
            st.error(msg or "Could not delete pricing item.")

        render_modal_delete_panel(
            prefix=f"pg_del_{rk}",
            delete_label="Delete Item",
            confirm_message="Delete this pricing guide item permanently? This cannot be undone.",
            confirm_label="Confirm Delete",
            can_delete=can_mutate,
            disabled_reason="Only admin, manager, or supervisor can delete pricing items.",
            on_confirm=_delete_item,
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
    if current_role() in {"admin", "supervisor", "manager"}:
        render_modal_edit_button(module=_MODULE, record_key=rk)
    render_modal_meta_grid(
        [
            ("Type", row.get("item_type")),
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
    st.markdown(
        '<span class="ips-pricing-guide-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    rows = _load_rows()
    filter_options = build_filter_options(rows, _COLUMN_FILTER_SPECS)

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header(
            "Pricing Guide",
            "Master estimating database: inventory-linked items, labor, equipment, travel, subcontractors, and more.",
        )
    with act_r:
        if st.button("+ New Pricing Item", key="pg_add", type="primary", use_container_width=True):
            st.session_state["pg_add_form"] = True

    _render_summary_cards(rows)

    if st.session_state.get("pg_add_form"):
        _render_add_form()

    def _filters() -> None:
        c1, c2 = st.columns([5, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search description, type, category, vendor, labor role…",
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
                _clear_pg_selection(st.session_state.get(_ALL_PG_IDS_KEY))
                st.rerun()

    layout_filter_bar(_filters)

    filtered = _filter_rows(
        rows,
        q=str(st.session_state.get("pg_search") or "").strip(),
    )

    st.caption(f"{len(filtered)} item(s)")

    build_modal_cache(filtered, cache_key=_CACHE_KEY)
    _render_custom_pricing_guide_table(filtered, filter_options=filter_options)

    selected_id = st.session_state.get(SELECTED_PG_KEY)
    if selected_id and st.session_state.get(SHOW_PG_MODAL_KEY):
        _show_detail_modal()
