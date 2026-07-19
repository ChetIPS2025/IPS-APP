"""Estimate Materials line detail and edit (conditional tabs)."""

from __future__ import annotations

import html
from typing import Any, Callable

import streamlit as st

from app.components.estimate_materials.state import material_detail_tab_key
from app.components.record_modal import (
    detail_field_html,
    dialog_card_html,
    placeholder_html,
    render_edit_form_header,
)
from app.pages._core._crud import is_demo_id
from app.pages._core._data import lookup_options
from app.services.estimate_costing_service import delete_estimate_material
from app.services.estimate_materials_page_service import (
    get_estimate_material_line_detail,
    invalidate_estimate_materials_page_cache,
    update_estimate_material_line,
)
from app.utils.formatting import fmt_currency


def _render_detail_tab_buttons(line_id: str, active: str) -> str:
    tabs = ("Overview", "Pricing", "Notes")
    parts = []
    for tab in tabs:
        cls = "ips-est-mat-tab-active" if tab == active else "ips-est-mat-tab"
        parts.append(f'<span class="{cls}">{html.escape(tab)}</span>')
    return "".join(parts)


def render_material_detail_panel(
    estimate_id: str,
    line_id: str,
    *,
    can_edit: bool,
    can_delete: bool,
    on_close: Callable[[], None] | None = None,
    on_saved: Callable[[], None] | None = None,
) -> None:
    from app.perf_debug import perf_span

    eid = str(estimate_id or "").strip()
    lid = str(line_id or "").strip()
    if not eid or not lid:
        return
    with perf_span("estimate_materials.detail_lookup"):
        mat = get_estimate_material_line_detail(eid, lid)
    if not mat:
        st.warning("Material line not found for this estimate.")
        if on_close:
            if st.button("Close", key=f"mat_detail_missing_close_{lid}"):
                on_close()
        return

    tab_key = material_detail_tab_key(lid)
    active_tab = str(st.session_state.get(tab_key) or "Overview")
    t1, t2, t3 = st.columns(3, gap="small")
    for col, tab in zip((t1, t2, t3), ("Overview", "Pricing", "Notes")):
        with col:
            if st.button(tab, key=f"mat_detail_tab_{lid}_{tab}", use_container_width=True):
                st.session_state[tab_key] = tab
                st.rerun()

    edit_key = f"mat_detail_edit_{lid}"
    editing = bool(st.session_state.get(edit_key))

    if editing and can_edit:
        _render_edit_form(mat, eid, edit_key=edit_key, on_saved=on_saved)
    elif active_tab == "Overview":
        with perf_span("estimate_materials.detail.overview"):
            overview_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Item #', mat.get('item_number'))}"
                f"{detail_field_html('Description', mat.get('description'))}"
                f"{detail_field_html('Category', mat.get('category'))}"
                f"{detail_field_html('Quantity', mat.get('quantity') or mat.get('qty'))}"
                f"{detail_field_html('Unit', mat.get('unit'))}"
                f"{detail_field_html('Vendor', mat.get('vendor'))}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Material Line", overview_html), unsafe_allow_html=True)
    elif active_tab == "Pricing":
        with perf_span("estimate_materials.detail.pricing"):
            pricing_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Unit Cost', fmt_currency(mat.get('unit_cost')))}"
                f"{detail_field_html('Cost Total', fmt_currency(mat.get('cost_total')))}"
                f"{detail_field_html('Markup %', mat.get('markup_percent'))}"
                f"{detail_field_html('Customer Price', fmt_currency(mat.get('price_total')))}"
                f"{detail_field_html('Taxable', 'Yes' if mat.get('taxable', True) else 'No')}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Pricing", pricing_html), unsafe_allow_html=True)
    elif active_tab == "Notes":
        placeholder_html("Material notes and vendor links will appear here when connected to Supabase.")

    actions = st.columns([1, 1, 2], gap="small")
    with actions[0]:
        if can_edit and not editing:
            if st.button("Edit", key=f"mat_detail_edit_btn_{lid}"):
                st.session_state[edit_key] = True
                st.rerun()
    with actions[1]:
        if can_delete and not editing:
            if st.button("Delete", key=f"mat_detail_del_{lid}"):
                mid = None if is_demo_id(lid) else lid
                if mid:
                    result = delete_estimate_material(mid, estimate_id=eid)
                    if result.ok:
                        invalidate_estimate_materials_page_cache(eid)
                        if on_close:
                            on_close()
                        if on_saved:
                            on_saved()
                        st.rerun()
                    else:
                        st.error(str(result.error or "Could not delete line."))
    with actions[2]:
        if st.button("Close Details", key=f"mat_detail_close_{lid}"):
            st.session_state.pop(edit_key, None)
            if on_close:
                on_close()
            st.rerun()


def _render_edit_form(
    mat: dict[str, Any],
    estimate_id: str,
    *,
    edit_key: str,
    on_saved: Callable[[], None] | None,
) -> None:
    from app.perf_debug import perf_span

    lid = str(mat.get("id") or "")
    rk = lid[:8]
    prefix = f"mat_edit_{rk}_"
    st.session_state.setdefault(f"{prefix}item", str(mat.get("item_number") or ""))
    st.session_state.setdefault(f"{prefix}desc", str(mat.get("description") or ""))
    st.session_state.setdefault(f"{prefix}cat", str(mat.get("category") or lookup_options("inventory_categories")[0]))
    st.session_state.setdefault(f"{prefix}qty", float(mat.get("quantity") or mat.get("qty") or 1))
    st.session_state.setdefault(f"{prefix}unit", str(mat.get("unit") or lookup_options("units")[0]))
    st.session_state.setdefault(f"{prefix}cost", float(mat.get("unit_cost") or 0))
    st.session_state.setdefault(f"{prefix}mk", float(mat.get("markup_percent") or 0))
    st.session_state.setdefault(f"{prefix}tax", bool(mat.get("taxable", True)))

    render_edit_form_header("Edit Material Line")
    ec1, ec2 = st.columns(2)
    with ec1:
        st.text_input("Item #", key=f"{prefix}item")
        st.text_input("Description", key=f"{prefix}desc")
        st.selectbox("Category", lookup_options("inventory_categories"), key=f"{prefix}cat")
    with ec2:
        st.number_input("Qty", min_value=0.0, key=f"{prefix}qty")
        st.selectbox("Unit", lookup_options("units"), key=f"{prefix}unit")
        st.number_input("Unit cost", min_value=0.0, key=f"{prefix}cost")
        st.number_input("Markup %", min_value=0.0, key=f"{prefix}mk")
        st.checkbox("Taxable", key=f"{prefix}tax")

    cancelled = st.button("Cancel", key=f"{prefix}cancel")
    saved = st.button("Save", key=f"{prefix}save", type="primary")
    if cancelled:
        st.session_state.pop(edit_key, None)
        st.rerun()
    if saved:
        with perf_span("estimate_materials.edit"):
            payload = {
                "estimate_id": estimate_id,
                "item_number": st.session_state.get(f"{prefix}item"),
                "description": st.session_state.get(f"{prefix}desc"),
                "category": st.session_state.get(f"{prefix}cat"),
                "quantity": st.session_state.get(f"{prefix}qty"),
                "unit": st.session_state.get(f"{prefix}unit"),
                "unit_cost": st.session_state.get(f"{prefix}cost"),
                "markup_percent": st.session_state.get(f"{prefix}mk"),
                "taxable": st.session_state.get(f"{prefix}tax"),
                "pricing_item_id": mat.get("pricing_item_id"),
                "inventory_item_id": mat.get("inventory_item_id"),
                "vendor_id": mat.get("vendor_id"),
                "vendor": mat.get("vendor"),
            }
            result = update_estimate_material_line(lid, payload)
            if result.ok:
                invalidate_estimate_materials_page_cache(estimate_id)
                st.session_state.pop(edit_key, None)
                st.success("Material line saved.")
                if on_saved:
                    on_saved()
                st.rerun()
            else:
                st.error(str(result.error or "Could not save material line."))


__all__ = ["render_material_detail_panel"]
