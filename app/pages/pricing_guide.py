"""Pricing Guide — master estimating price list (``estimate_materials`` catalog rows)."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

import streamlit as st

try:
    from app.auth import current_role
    from app.components.clickable_table import render_clickable_table
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
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
        show_modal_if_pending,
        status_pill_html as modal_status_pill_html,
    )
    from app.components.status import status_pill_html
    from app.components.tabs import render_tabs
    from app.db import fetch_table, fetch_table_admin, insert_row_admin, update_rows_admin
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
    from app.services.estimate_materials_catalog import clear_estimate_materials_catalog_cache
    from app.utils.formatting import fmt_currency
except ImportError:
    from auth import current_role  # type: ignore
    from components.clickable_table import render_clickable_table  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
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
        show_modal_if_pending,
        status_pill_html as modal_status_pill_html,
    )
    from components.status import status_pill_html  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from db import fetch_table, fetch_table_admin, insert_row_admin, update_rows_admin  # type: ignore
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from services.estimate_materials_catalog import clear_estimate_materials_catalog_cache  # type: ignore
    from utils.formatting import fmt_currency  # type: ignore

_SEL = select_key("pricing_guide")
_MODULE = "pricing_guide"
_TABLE_KEY = "pg_list"
_MODAL_KEY = "ips_pg_detail_modal_id"
_CACHE_KEY = "_ips_pg_modal_by_id"
_DETAIL_TABS = (
    "Overview",
    "Pricing",
    "Vendors",
    "Inventory Link",
    "Estimate Usage",
    "Price History",
    "Notes",
    "Activity",
)


def _markup_pct(purchase: float, sell: float) -> float:
    if purchase <= 0:
        return 0.0
    return round(((sell - purchase) / purchase) * 100.0, 2)


def _sell_from_markup(purchase: float, markup: float) -> float:
    return round(purchase * (1.0 + (markup / 100.0)), 2)


def _normalize_row(raw: dict[str, Any]) -> dict[str, Any]:
    purchase = float(raw.get("purchase_price") or 0)
    sell_raw = raw.get("sell_price")
    sell = float(sell_raw) if sell_raw not in (None, "") else _sell_from_markup(purchase, 25.0)
    active = raw.get("is_active") is not False
    return {
        **raw,
        "id": str(raw.get("id") or ""),
        "item": str(raw.get("description") or raw.get("item_key") or "—"),
        "item_key": str(raw.get("item_key") or ""),
        "description": str(raw.get("description") or ""),
        "category": str(raw.get("category") or "—"),
        "unit": str(raw.get("unit") or "EA"),
        "default_cost": purchase,
        "markup_pct": _markup_pct(purchase, sell),
        "customer_price": sell,
        "vendor": str(raw.get("vendor_item_number") or raw.get("vendor") or "—"),
        "status": "Active" if active else "Inactive",
        "is_active": active,
        "inventory_ref_id": str(raw.get("inventory_ref_id") or ""),
        "notes": str(raw.get("notes") or ""),
    }


def _load_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        rows = list(fetch_table_admin("estimate_materials", limit=10000, order_by="item_key") or [])
    except Exception:
        try:
            rows = list(fetch_table("estimate_materials", limit=10000, order_by="item_key") or [])
        except Exception:
            rows = []
    return [_normalize_row(r) for r in rows if isinstance(r, dict) and str(r.get("item_key") or "").strip()]


def _clear_modal() -> None:
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _open_modal(row_id: str, row: dict | None = None) -> None:
    open_record_modal(
        row_id,
        row,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
        id_fields=("id",),
    )


def _persist_row(data: dict[str, Any], row_id: str | None = None) -> tuple[bool, str]:
    purchase = float(data.get("purchase_price") or data.get("default_cost") or 0)
    markup = float(data.get("markup_pct") or 0)
    sell = data.get("sell_price")
    if sell in (None, ""):
        sell = _sell_from_markup(purchase, markup)
    payload = {
        "item_key": str(data.get("item_key") or "").strip()[:500],
        "description": str(data.get("description") or data.get("item") or "").strip()[:2000],
        "category": str(data.get("category") or "Pricing Guide").strip()[:200],
        "unit": str(data.get("unit") or "EA").strip()[:32],
        "purchase_price": purchase,
        "sell_price": float(sell or 0),
        "vendor_item_number": str(data.get("vendor_item_number") or data.get("vendor") or "").strip()[:200],
        "is_active": bool(data.get("is_active", True)),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if not payload["item_key"]:
        return False, "Item key is required."
    if not payload["description"]:
        payload["description"] = payload["item_key"]
    try:
        if row_id and not is_demo_id(row_id):
            update_rows_admin("estimate_materials", payload, {"id": row_id})
        else:
            payload["created_at"] = payload["updated_at"]
            insert_row_admin("estimate_materials", payload)
        clear_estimate_materials_catalog_cache()
        return True, "Saved."
    except Exception as exc:
        return False, str(exc)


def _cell(field: str, row: dict[str, Any]) -> str:
    if field in ("default_cost", "customer_price"):
        return html.escape(fmt_currency(row.get(field)))
    if field == "markup_pct":
        return html.escape(f"{float(row.get(field) or 0):.1f}%")
    if field == "status":
        return status_pill_html(str(row.get("status") or ""))
    val = row.get(field)
    return html.escape(str(val).strip() if val is not None and str(val).strip() else "—")


def _render_item_tabs(row: dict[str, Any]) -> None:
    tab = render_tabs(list(_DETAIL_TABS), session_key=f"ips_pg_tab_{row.get('id')}", default="Overview")
    if tab == "Overview":
        st.markdown(
            dialog_card_html(
                "Overview",
                f"{detail_field_html('Item', row.get('item'))}"
                f"{detail_field_html('Item key', row.get('item_key'))}"
                f"{detail_field_html('Category', row.get('category'))}"
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
                f"{detail_field_html('Default cost', fmt_currency(row.get('default_cost')))}"
                f"{detail_field_html('Markup %', f'{mk:.1f}%')}"
                f"{detail_field_html('Customer price', fmt_currency(row.get('customer_price')))}",
            ),
            unsafe_allow_html=True,
        )
    elif tab == "Vendors":
        st.markdown(
            dialog_card_html(
                "Vendors",
                f"{detail_field_html('Vendor / part #', row.get('vendor'))}"
                f"{detail_field_html('Vendor item number', row.get('vendor_item_number') or row.get('vendor'))}",
            ),
            unsafe_allow_html=True,
        )
    elif tab == "Inventory Link":
        ref = str(row.get("inventory_ref_id") or "").strip()
        body = detail_field_html("Linked inventory ID", ref or "Not linked")
        if ref:
            body += "<p style='margin:0.35rem 0 0;font-size:0.82rem;color:#64748b;'>Open Inventory to view stock for this linked item.</p>"
        st.markdown(dialog_card_html("Inventory Link", body), unsafe_allow_html=True)
    elif tab == "Estimate Usage":
        st.markdown(
            dialog_card_html(
                "Estimate Usage",
                placeholder_html("Estimate line usage tracking will appear here when linked on quotes."),
            ),
            unsafe_allow_html=True,
        )
    elif tab == "Price History":
        st.markdown(
            dialog_card_html(
                "Price History",
                placeholder_html("Price change history is not recorded yet for this item."),
            ),
            unsafe_allow_html=True,
        )
    elif tab == "Notes":
        notes = safe_value(row.get("notes"), "No notes.")
        st.markdown(dialog_card_html("Notes", f"<p style='margin:0;font-size:0.875rem;'>{html.escape(notes)}</p>"), unsafe_allow_html=True)
    else:
        st.markdown(
            dialog_card_html(
                "Activity",
                placeholder_html("Activity log is not available for pricing guide items yet."),
            ),
            unsafe_allow_html=True,
        )


def _render_edit_form(row: dict[str, Any]) -> None:
    rk = record_session_key(row, "id")
    render_edit_form_header("Edit Pricing Guide Item")
    item_key = st.text_input("Item key", value=str(row.get("item_key") or ""), key=f"pg_edit_key_{rk}")
    description = st.text_input("Description", value=str(row.get("description") or row.get("item") or ""), key=f"pg_edit_desc_{rk}")
    category = st.text_input("Category", value=str(row.get("category") or ""), key=f"pg_edit_cat_{rk}")
    unit = st.text_input("Unit", value=str(row.get("unit") or "EA"), key=f"pg_edit_unit_{rk}")
    c1, c2, c3 = st.columns(3)
    with c1:
        purchase = st.number_input("Default cost", min_value=0.0, value=float(row.get("default_cost") or 0), key=f"pg_edit_cost_{rk}")
    with c2:
        markup = st.number_input("Markup %", min_value=0.0, value=float(row.get("markup_pct") or 0), key=f"pg_edit_mk_{rk}")
    with c3:
        sell = st.number_input("Customer price", min_value=0.0, value=float(row.get("customer_price") or 0), key=f"pg_edit_sell_{rk}")
    vendor = st.text_input("Vendor / part #", value=str(row.get("vendor") or ""), key=f"pg_edit_vendor_{rk}")
    active = st.checkbox("Active", value=bool(row.get("is_active", True)), key=f"pg_edit_active_{rk}")

    def _save() -> None:
        ok, msg = _persist_row(
            {
                "item_key": item_key,
                "description": description,
                "category": category,
                "unit": unit,
                "purchase_price": purchase,
                "markup_pct": markup,
                "sell_price": sell,
                "vendor_item_number": vendor,
                "is_active": active,
            },
            row_id=str(row.get("id") or ""),
        )
        if apply_persist_feedback(ok, msg):
            set_view_mode(_MODULE, rk)
            st.rerun()

    render_save_cancel_actions(_save, lambda: set_view_mode(_MODULE, rk), save_label="Save Pricing Guide Item")


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
        title=str(row.get("item") or "Pricing Guide Item"),
        subtitle=str(row.get("item_key") or ""),
        status=str(row.get("status") or ""),
    )
    if current_role() in {"admin", "supervisor", "manager"}:
        render_modal_edit_button(module=_MODULE, record_key=rk)
    render_modal_meta_grid(
        [
            ("Category", row.get("category")),
            ("Unit", row.get("unit")),
            ("Default cost", fmt_currency(row.get("default_cost"))),
            ("Customer price", fmt_currency(row.get("customer_price"))),
        ]
    )
    render_modal_shell()
    if edit_mode:
        _render_edit_form(row)
    else:
        _render_item_tabs(row)


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("pricing_guide"):
        return

    render_page_header(
        "Pricing Guide",
        "Manage default material costs, vendors, units, and markup rates for estimating.",
    )

    rows = _load_rows()
    build_modal_cache(rows, cache_key=_CACHE_KEY)

    def _filters() -> None:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.text_input("Search", placeholder="Search pricing items…", key="pg_search", label_visibility="collapsed")
        with c2:
            if st.button("+ New Pricing Item", key="pg_add", type="primary", use_container_width=True):
                st.session_state["pg_add_form"] = True

    layout_filter_bar(_filters)

    if st.session_state.get("pg_add_form"):
        with st.expander("Add Pricing Guide Item", expanded=True):
            nk = st.text_input("Item key", key="pg_new_key")
            nd = st.text_input("Description", key="pg_new_desc")
            nc = st.text_input("Category", value="Pricing Guide", key="pg_new_cat")
            nu = st.text_input("Unit", value="EA", key="pg_new_unit")
            ncost = st.number_input("Default cost", min_value=0.0, value=0.0, key="pg_new_cost")
            nmk = st.number_input("Markup %", min_value=0.0, value=25.0, key="pg_new_mk")
            nv = st.text_input("Vendor / part #", key="pg_new_vendor")
            if st.button("Save Pricing Guide Item", key="pg_new_save", type="primary"):
                ok, msg = _persist_row(
                    {
                        "item_key": nk,
                        "description": nd,
                        "category": nc,
                        "unit": nu,
                        "purchase_price": ncost,
                        "markup_pct": nmk,
                        "vendor_item_number": nv,
                        "is_active": True,
                    }
                )
                if apply_persist_feedback(ok, msg, clear_keys=("pg_add_form",)):
                    st.rerun()

    q = str(st.session_state.get("pg_search") or "").strip().lower()
    filtered = rows
    if q:
        filtered = [
            r
            for r in rows
            if q in str(r.get("item") or "").lower()
            or q in str(r.get("item_key") or "").lower()
            or q in str(r.get("category") or "").lower()
            or q in str(r.get("vendor") or "").lower()
        ]

    columns = [
        ("item", "Item"),
        ("category", "Category"),
        ("unit", "Unit"),
        ("default_cost", "Default Cost"),
        ("markup_pct", "Markup %"),
        ("customer_price", "Customer Price"),
        ("vendor", "Vendor"),
        ("status", "Status"),
    ]

    render_clickable_table(
        filtered,
        columns,
        _TABLE_KEY,
        row_id_key="id",
        session_select_key=_SEL,
        format_cell=_cell,
        click_caption="Click a row to open pricing guide item details.",
        on_row_selected=_open_modal,
    )

    show_modal_if_pending(_MODAL_KEY, _show_detail_modal)
