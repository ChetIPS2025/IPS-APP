"""Estimate Materials takeoff draft form (lazy batch entry)."""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from app.components.estimate_materials.state import (
    _MAX_TAKEOFF_DRAFT_ROWS,
    _TAKEOFF_DRAFT_COUNT,
    clear_material_takeoff_draft,
    initial_takeoff_rows,
    maybe_extend_takeoff_draft,
    takeoff_draft_key,
    takeoff_field_key,
    takeoff_open_key,
)
from app.components.searchable_select import render_searchable_selectbox
from app.pages._core._data import lookup_options
from app.services.estimate_costing_service import add_estimate_material_batch
from app.services.estimate_material_reference_service import (
    _CUSTOM_INVENTORY_LABEL,
    inventory_search_provider,
    search_estimate_inventory_options,
)
from app.services.estimate_materials_page_service import invalidate_estimate_materials_page_cache
from app.utils.formatting import fmt_currency


def _lookup_inventory_option(option_id: str) -> dict[str, Any] | None:
    oid = str(option_id or "").strip()
    if not oid or oid == _CUSTOM_INVENTORY_LABEL:
        return None
    for row in search_estimate_inventory_options(search="", limit=200):
        if str(row.get("option_id") or "") == oid:
            return row
    return None


def _sync_takeoff_pick(
    estimate_id: str,
    rid: str,
    pick: str,
    *,
    categories: list[str],
    units: list[str],
    default_markup: float,
) -> None:
    last_key = takeoff_field_key(estimate_id, f"last_pick_{rid}", rid)
    if st.session_state.get(last_key) == pick:
        return
    fk = lambda field: takeoff_field_key(estimate_id, field, rid)  # noqa: E731
    item = _lookup_inventory_option(pick)
    if item:
        st.session_state[fk("item")] = str(item.get("sku") or item.get("item_number") or "")
        st.session_state[fk("desc")] = str(item.get("description") or "")
        cat = str(item.get("category") or "").strip()
        if cat and cat in categories:
            st.session_state[fk("cat")] = cat
        unit = str(item.get("unit") or "EA").strip()
        if unit and unit in units:
            st.session_state[fk("unit")] = unit
        st.session_state[fk("cost")] = float(item.get("unit_cost") or 0)
        st.session_state[fk("mk")] = float(item.get("markup_pct") or default_markup)
        st.session_state[fk("tax")] = bool(item.get("taxable", True))
        st.session_state[fk("pg_id")] = str(item.get("pricing_item_id") or "")
        st.session_state[fk("inv_id")] = str(item.get("inventory_item_id") or "")
    elif pick == _CUSTOM_INVENTORY_LABEL:
        st.session_state.setdefault(fk("item"), "")
        st.session_state.setdefault(fk("desc"), "")
        st.session_state.setdefault(fk("mk"), float(default_markup))
        st.session_state.setdefault(fk("tax"), True)
    st.session_state[last_key] = pick


def _row_has_data(estimate_id: str, rid: str) -> bool:
    fk = lambda field: takeoff_field_key(estimate_id, field, rid)  # noqa: E731
    item_no = str(st.session_state.get(fk("item")) or "").strip()
    desc = str(st.session_state.get(fk("desc")) or "").strip()
    qty = float(st.session_state.get(fk("qty")) or 0)
    return qty > 0 and bool(item_no or desc)


def render_material_takeoff_form(
    estimate_id: str,
    est: dict[str, Any],
    *,
    can_edit: bool,
    on_saved: Callable[[], None] | None = None,
) -> None:
    from app.perf_debug import perf_span

    eid = str(estimate_id or "").strip()
    if not eid or not can_edit:
        return
    with perf_span("estimate_materials.takeoff_render"):
        categories = lookup_options("inventory_categories")
        units = lookup_options("units")
        default_markup = float(est.get("default_material_markup_pct") or 0)
        draft_key = takeoff_draft_key(eid)
        draft_rows = list(st.session_state.get(draft_key) or [])
        if len(draft_rows) < _TAKEOFF_DRAFT_COUNT:
            st.session_state[draft_key] = initial_takeoff_rows(pick=_CUSTOM_INVENTORY_LABEL)
            draft_rows = list(st.session_state.get(draft_key) or [])

        provider = inventory_search_provider(limit=100)
        st.caption(
            f"Up to {_MAX_TAKEOFF_DRAFT_ROWS} rows — search inventory/pricing items or enter custom lines."
        )
        hdr = st.columns([1.2, 2.0, 1.0, 0.65, 0.65, 0.85, 0.85, 0.45], gap="small")
        for col, label in zip(
            hdr,
            ("Item #", "Description", "Category", "Qty", "Unit", "Unit Cost", "Extended", ""),
        ):
            with col:
                st.markdown(
                    f'<div style="font-size:0.72rem;font-weight:700;color:#64748b;">{label}</div>',
                    unsafe_allow_html=True,
                )

        remove_rid = ""
        for row in draft_rows:
            rid = str(row.get("rid") or "")
            if not rid:
                continue
            fk = lambda field, _rid=rid: takeoff_field_key(eid, field, _rid)  # noqa: E731
            st.session_state.setdefault(fk("qty"), 1.0)
            st.session_state.setdefault(fk("cost"), 0.0)
            st.session_state.setdefault(fk("cat"), categories[0] if categories else "General")
            st.session_state.setdefault(fk("unit"), units[0] if units else "EA")
            st.session_state.setdefault(fk("mk"), default_markup)
            st.session_state.setdefault(fk("tax"), True)
            if fk(f"pick_{rid}") not in st.session_state:
                st.session_state[fk(f"pick_{rid}")] = _CUSTOM_INVENTORY_LABEL

            cols = st.columns([1.2, 2.0, 1.0, 0.65, 0.65, 0.85, 0.85, 0.45], gap="small")
            with cols[0]:
                item_pick = render_searchable_selectbox(
                    "Item #",
                    [_CUSTOM_INVENTORY_LABEL],
                    key=fk(f"pick_{rid}"),
                    placeholder="Search item #…",
                    search_provider=provider,
                )
                _sync_takeoff_pick(
                    eid,
                    rid,
                    item_pick,
                    categories=categories,
                    units=units,
                    default_markup=default_markup,
                )
                if item_pick == _CUSTOM_INVENTORY_LABEL:
                    st.text_input(
                        "Item #",
                        key=fk("item"),
                        label_visibility="collapsed",
                        placeholder="Item #",
                    )
            with cols[1]:
                st.text_input(
                    "Description",
                    key=fk("desc"),
                    label_visibility="collapsed",
                    placeholder="Description",
                )
            with cols[2]:
                st.selectbox(
                    "Category",
                    categories,
                    key=fk("cat"),
                    label_visibility="collapsed",
                )
            with cols[3]:
                qty = st.number_input(
                    "Qty",
                    min_value=0.0,
                    step=1.0,
                    key=fk("qty"),
                    label_visibility="collapsed",
                )
            with cols[4]:
                st.selectbox(
                    "Unit",
                    units,
                    key=fk("unit"),
                    label_visibility="collapsed",
                )
            with cols[5]:
                unit_cost = st.number_input(
                    "Unit cost",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    key=fk("cost"),
                    label_visibility="collapsed",
                )
            with cols[6]:
                extended = float(qty or 0) * float(unit_cost or 0)
                st.markdown(
                    f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                    f"{fmt_currency(extended)}</div>",
                    unsafe_allow_html=True,
                )
            with cols[7]:
                if st.button("✕", key=fk("rm"), help="Remove row"):
                    remove_rid = rid

        capped = maybe_extend_takeoff_draft(
            eid,
            draft_rows,
            is_row_filled=lambda row_id: _row_has_data(eid, row_id),
            pick=_CUSTOM_INVENTORY_LABEL,
        )
        if capped:
            st.caption("Save these material lines before adding more.")

        if remove_rid:
            remaining = [r for r in draft_rows if str(r.get("rid")) != remove_rid]
            st.session_state[draft_key] = remaining or initial_takeoff_rows(pick=_CUSTOM_INVENTORY_LABEL)
            st.rerun()

        btn1, btn2, btn3 = st.columns(3, gap="small")
        with btn1:
            save_clicked = st.button(
                "Save Material Lines",
                key=f"mat_takeoff_save_{eid}",
                type="primary",
                use_container_width=True,
            )
        with btn2:
            clear_clicked = st.button("Clear Draft", key=f"mat_takeoff_clear_{eid}", use_container_width=True)
        with btn3:
            close_clicked = st.button("Close Form", key=f"mat_takeoff_close_{eid}", use_container_width=True)

        if clear_clicked:
            clear_material_takeoff_draft(eid)
            st.session_state[takeoff_open_key(eid)] = True
            st.session_state[draft_key] = initial_takeoff_rows(pick=_CUSTOM_INVENTORY_LABEL)
            st.rerun()

        if close_clicked:
            clear_material_takeoff_draft(eid)
            st.session_state.pop(takeoff_open_key(eid), None)
            st.rerun()

        if save_clicked:
            with perf_span("estimate_materials.batch_save"):
                payloads: list[dict[str, Any]] = []
                for row in list(st.session_state.get(draft_key) or []):
                    rid = str(row.get("rid") or "")
                    if not rid or not _row_has_data(eid, rid):
                        continue
                    fk = lambda field, _rid=rid: takeoff_field_key(eid, field, _rid)  # noqa: E731
                    pg_id = str(st.session_state.get(fk("pg_id")) or "").strip() or None
                    inv_id = str(st.session_state.get(fk("inv_id")) or "").strip() or None
                    payloads.append(
                        {
                            "estimate_id": eid,
                            "item_number": st.session_state.get(fk("item")),
                            "description": st.session_state.get(fk("desc")),
                            "category": st.session_state.get(fk("cat")),
                            "quantity": st.session_state.get(fk("qty")),
                            "unit": st.session_state.get(fk("unit")),
                            "unit_cost": st.session_state.get(fk("cost")),
                            "markup_percent": st.session_state.get(fk("mk")),
                            "taxable": st.session_state.get(fk("tax")),
                            "pricing_item_id": pg_id,
                            "inventory_item_id": inv_id,
                        }
                    )
                if not payloads:
                    st.error("Enter at least one material line with item/description and quantity.")
                else:
                    result = add_estimate_material_batch(eid, payloads)
                    if result.ok:
                        invalidate_estimate_materials_page_cache(eid)
                        clear_material_takeoff_draft(eid)
                        st.session_state.pop(takeoff_open_key(eid), None)
                        saved = int((getattr(result, "data", None) or {}).get("saved") or len(payloads))
                        st.success(f"Saved {saved} material line{'s' if saved != 1 else ''}.")
                        if on_saved:
                            on_saved()
                        st.rerun()
                    else:
                        st.error(str(getattr(result, "error", None) or "Could not save material lines."))


__all__ = ["render_material_takeoff_form"]
