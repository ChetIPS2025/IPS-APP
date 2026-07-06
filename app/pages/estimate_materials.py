"""Estimate Materials module (Phase 2B)."""

from __future__ import annotations

import csv
import html
import io
from uuid import uuid4

import streamlit as st

try:
    from app.components.clickable_table import render_clickable_table
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.searchable_select import render_searchable_selectbox
    from app.components.record_modal import (
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        edit_mode_key,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_view_mode,
        show_modal_if_pending,
    )
    from app.components.status import status_pill_html
    from app.components.tabs import render_tabs
    from app.pages._core._data import (
        ACTIVE_ESTIMATE_KEY,
        get_estimate,
        load_estimate_materials,
        load_inventory,
        lookup_options,
        materials_summary,
        persist_estimate_material,
    )
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
    from app.services.estimate_costing_service import delete_estimate_material
    from app.utils.formatting import fmt_currency
except ImportError:
    from components.searchable_select import render_searchable_selectbox  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        edit_mode_key,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_view_mode,
        show_modal_if_pending,
    )
    from components.status import status_pill_html  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages._core._data import (  # type: ignore
        ACTIVE_ESTIMATE_KEY,
        get_estimate,
        load_estimate_materials,
        load_inventory,
        lookup_options,
        materials_summary,
        persist_estimate_material,
    )
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from services.estimate_costing_service import delete_estimate_material  # type: ignore
    from utils.formatting import fmt_currency  # type: ignore

_SEL = select_key("estimate_materials")
_MODULE = "estimate_materials"
_TABLE_KEY = "mat_list"
_MODAL_KEY = "ips_mat_detail_modal_id"
_CACHE_KEY = "_ips_mat_modal_by_id"
_TAKEOFF_DRAFT_COUNT = 5
_CUSTOM_TAKEOFF_ITEM = "— Custom item —"


def _estimate_materials_date(est: dict) -> str:
    try:
        from app.services.estimate_expiration_service import format_estimate_date
    except ImportError:
        from services.estimate_expiration_service import format_estimate_date  # type: ignore
    return format_estimate_date(est)


def _estimate_materials_expiration(est: dict) -> str:
    try:
        from app.services.estimate_expiration_service import format_effective_expiration
    except ImportError:
        from services.estimate_expiration_service import format_effective_expiration  # type: ignore
    return format_effective_expiration(est)


def _render_summary_card(est: dict) -> None:
    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-summary-card">', unsafe_allow_html=True)
    cols = st.columns(6)
    fields = [
        ("Client", str(est.get("customer") or "—")),
        ("Job", f"{est.get('job_number') or '—'} — {est.get('project_name') or ''}"),
        ("Estimate Date", _estimate_materials_date(est)),
        ("Valid Through", _estimate_materials_expiration(est)),
        ("Prepared By", str(est.get("created_by") or "—")),
        ("Estimated Total", fmt_currency(est.get("total"))),
    ]
    for col, (lbl, val) in zip(cols, fields):
        with col:
            lg = " val-lg" if lbl == "Estimated Total" else ""
            st.markdown(
                f'<p class="lbl">{html.escape(lbl)}</p><p class="val{lg}">{html.escape(val)}</p>',
                unsafe_allow_html=True,
            )
    st.markdown(
        f'<p style="margin:0.5rem 0 0;">{status_pill_html(str(est.get("status") or ""))} '
        f'<strong>{html.escape(str(est.get("estimate_number") or ""))}</strong> — '
        f'{html.escape(str(est.get("project_name") or ""))}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(f"</{ot}>", unsafe_allow_html=True)


def _clear_mat_modal() -> None:
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _open_mat_modal(mat_id: str, mat: dict | None = None) -> None:
    open_record_modal(
        mat_id,
        mat,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
        id_fields=("id",),
    )


def _seed_mat_edit_form(mat: dict) -> None:
    rk = record_session_key(mat, "id")
    st.session_state[f"mat_edit_item_{rk}"] = str(mat.get("item_number") or "")
    st.session_state[f"mat_edit_desc_{rk}"] = str(mat.get("description") or "")
    st.session_state[f"mat_edit_cat_{rk}"] = str(mat.get("category") or lookup_options("inventory_categories")[0])
    st.session_state[f"mat_edit_qty_{rk}"] = float(mat.get("qty") or 1)
    st.session_state[f"mat_edit_unit_{rk}"] = str(mat.get("unit") or lookup_options("units")[0])
    st.session_state[f"mat_edit_cost_{rk}"] = float(mat.get("unit_cost") or 0)


def _render_mat_view_tabs(mat: dict) -> None:
    tab_overview, tab_pricing, tab_notes = st.tabs(["Overview", "Pricing", "Notes"])
    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Item #', mat.get('item_number'))}"
            f"{detail_field_html('Description', mat.get('description'))}"
            f"{detail_field_html('Category', mat.get('category'))}"
            f"{detail_field_html('Quantity', mat.get('qty'))}"
            f"{detail_field_html('Unit', mat.get('unit'))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Material Line", overview_html), unsafe_allow_html=True)
    with tab_pricing:
        pricing_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Unit Cost', fmt_currency(mat.get('unit_cost')))}"
            f"{detail_field_html('Total Cost', fmt_currency(mat.get('total_cost')))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Pricing", pricing_html), unsafe_allow_html=True)
    with tab_notes:
        placeholder_html("Material notes and vendor links will appear here when connected to Supabase.")


def _render_mat_edit_form(mat: dict, estimate_id: str) -> None:
    rk = record_session_key(mat, "id")
    mid = str(mat.get("id") or "")
    if f"mat_edit_item_{rk}" not in st.session_state:
        _seed_mat_edit_form(mat)

    render_edit_form_header("Edit Material Line")
    ec1, ec2 = st.columns(2)
    with ec1:
        st.text_input("Item #", key=f"mat_edit_item_{rk}")
        st.text_input("Description", key=f"mat_edit_desc_{rk}")
        st.selectbox("Category", lookup_options("inventory_categories"), key=f"mat_edit_cat_{rk}")
    with ec2:
        st.number_input("Qty", min_value=0.0, key=f"mat_edit_qty_{rk}")
        st.selectbox("Unit", lookup_options("units"), key=f"mat_edit_unit_{rk}")
        st.number_input("Unit cost", min_value=0.0, key=f"mat_edit_cost_{rk}")

    cancelled, saved = render_save_cancel_actions(
        module=_MODULE,
        record_key=rk,
        cancel_key=f"mat_edit_cancel_{rk}",
        save_key=f"mat_edit_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved:
        ui = {
            "estimate_id": estimate_id,
            "item_number": st.session_state.get(f"mat_edit_item_{rk}"),
            "description": st.session_state.get(f"mat_edit_desc_{rk}"),
            "category": st.session_state.get(f"mat_edit_cat_{rk}"),
            "qty": st.session_state.get(f"mat_edit_qty_{rk}"),
            "unit": st.session_state.get(f"mat_edit_unit_{rk}"),
            "unit_cost": st.session_state.get(f"mat_edit_cost_{rk}"),
        }
        row_id = None if is_demo_id(mid) else mid
        ok, msg = persist_estimate_material(ui, row_id=row_id)
        if ok:
            set_view_mode(_MODULE, rk)
            st.success(msg or "Material line saved.")
            st.rerun()
        else:
            st.error(msg or "Could not save material line.")


def render_material_detail_dialog(mat: dict, *, estimate_id: str) -> None:
    rk = record_session_key(mat, "id")
    st.session_state.setdefault(edit_mode_key(_MODULE, rk), False)
    edit_mode = is_edit_mode(_MODULE, rk)

    render_modal_shell()
    render_modal_header(
        title=str(mat.get("item_number") or "Material"),
        subtitle=str(mat.get("description") or ""),
    )
    render_modal_edit_button(
        module=_MODULE,
        record_key=rk,
        key_prefix=f"mat_modal_{rk}",
    )
    render_modal_meta_grid(
        [
            ("Category", mat.get("category")),
            ("Qty", mat.get("qty")),
            ("Unit", mat.get("unit")),
            ("Total", fmt_currency(mat.get("total_cost"))),
        ]
    )

    if edit_mode:
        _render_mat_edit_form(mat, estimate_id)
    else:
        _render_mat_view_tabs(mat)


@st.dialog("Material Details", width="large", on_dismiss=_clear_mat_modal)
def _show_mat_detail_modal() -> None:
    mat = get_modal_record(
        cache_key=_CACHE_KEY,
        modal_key=_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not mat:
        render_missing_record(_clear_mat_modal, close_key="mat_modal_missing_close")
        return
    estimate_id = str(st.session_state.get(ACTIVE_ESTIMATE_KEY) or "")
    render_material_detail_dialog(mat, estimate_id=estimate_id)


def _mat_display_cell(field: str, row: dict) -> str:
    if field in ("unit_cost", "total_cost"):
        return fmt_currency(row.get(field))
    val = row.get(field)
    return str(val).strip() if val is not None and str(val).strip() else "—"


def _materials_csv_bytes(materials: list[dict], *, estimate_number: str) -> bytes:
    buf = io.StringIO()
    fieldnames = [
        "item_number",
        "description",
        "category",
        "qty",
        "unit",
        "unit_cost",
        "total_cost",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in materials:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    return buf.getvalue().encode("utf-8")


def _inventory_picker_options(items: list[dict]) -> tuple[list[str], dict[str, dict]]:
    labels: list[str] = []
    by_id: dict[str, dict] = {}
    for item in items:
        iid = str(item.get("id") or "").strip()
        if not iid or is_demo_id(iid):
            continue
        label = f"{item.get('sku') or '—'} — {item.get('name') or 'Item'}"
        labels.append(label)
        by_id[label] = item
    return labels, by_id


def _mat_takeoff_draft_key(estimate_id: str) -> str:
    return f"mat_takeoff_batch_{estimate_id}"


def _mat_takeoff_key(estimate_id: str, field: str, rid: str) -> str:
    return f"mat_to_{estimate_id}_{field}_{rid}"


def _inventory_search_options(items: list[dict]) -> tuple[list[str], list[tuple[str, dict]], dict[str, dict]]:
    labels: list[str] = []
    searchable: list[tuple[str, dict]] = []
    by_label: dict[str, dict] = {}
    for item in items:
        iid = str(item.get("id") or "").strip()
        if not iid or is_demo_id(iid):
            continue
        sku = str(item.get("sku") or "—").strip()
        name = str(item.get("name") or "Item").strip()
        label = f"{sku} — {name}"
        labels.append(label)
        searchable.append((label, item))
        by_label[label] = item
    pick_labels = [*labels, _CUSTOM_TAKEOFF_ITEM] if labels else [_CUSTOM_TAKEOFF_ITEM]
    return pick_labels, searchable, by_label


def _new_takeoff_row() -> dict[str, str]:
    return {"rid": uuid4().hex[:8], "pick": _CUSTOM_TAKEOFF_ITEM}


def _initial_takeoff_rows() -> list[dict[str, str]]:
    return [_new_takeoff_row() for _ in range(_TAKEOFF_DRAFT_COUNT)]


def _ensure_takeoff_draft(estimate_id: str) -> list[dict[str, str]]:
    draft_key = _mat_takeoff_draft_key(estimate_id)
    rows = list(st.session_state.get(draft_key) or [])
    if len(rows) < _TAKEOFF_DRAFT_COUNT:
        st.session_state[draft_key] = _initial_takeoff_rows()
        rows = list(st.session_state.get(draft_key) or [])
    return rows


def _sync_takeoff_inventory_pick(
    estimate_id: str,
    rid: str,
    pick: str,
    inv_by_label: dict[str, dict],
    *,
    categories: list[str],
    units: list[str],
) -> None:
    last_key = _mat_takeoff_key(estimate_id, f"last_pick_{rid}", rid)
    if st.session_state.get(last_key) == pick:
        return
    if pick and pick != _CUSTOM_TAKEOFF_ITEM and pick in inv_by_label:
        inv = inv_by_label[pick]
        st.session_state[_mat_takeoff_key(estimate_id, "item", rid)] = str(inv.get("sku") or "")
        st.session_state[_mat_takeoff_key(estimate_id, "desc", rid)] = str(inv.get("name") or "")
        cat = str(inv.get("category") or "").strip()
        if cat and cat in categories:
            st.session_state[_mat_takeoff_key(estimate_id, "cat", rid)] = cat
        unit = str(inv.get("unit") or "EA").strip()
        if unit and unit in units:
            st.session_state[_mat_takeoff_key(estimate_id, "unit", rid)] = unit
        st.session_state[_mat_takeoff_key(estimate_id, "cost", rid)] = float(
            inv.get("unit_cost") or inv.get("average_cost") or 0
        )
    elif pick == _CUSTOM_TAKEOFF_ITEM:
        st.session_state.setdefault(_mat_takeoff_key(estimate_id, "item", rid), "")
        st.session_state.setdefault(_mat_takeoff_key(estimate_id, "desc", rid), "")
    st.session_state[last_key] = pick


def _takeoff_row_has_data(estimate_id: str, rid: str) -> bool:
    item_no = str(st.session_state.get(_mat_takeoff_key(estimate_id, "item", rid)) or "").strip()
    desc = str(st.session_state.get(_mat_takeoff_key(estimate_id, "desc", rid)) or "").strip()
    qty = float(st.session_state.get(_mat_takeoff_key(estimate_id, "qty", rid)) or 0)
    return qty > 0 and bool(item_no or desc)


def _first_empty_takeoff_rid(estimate_id: str) -> str | None:
    for row in _ensure_takeoff_draft(estimate_id):
        rid = str(row.get("rid") or "")
        if rid and not _takeoff_row_has_data(estimate_id, rid):
            return rid
    return None


def _populate_takeoff_row_from_inventory(estimate_id: str, rid: str, inv: dict, *, categories: list[str], units: list[str]) -> None:
    st.session_state[_mat_takeoff_key(estimate_id, "item", rid)] = str(inv.get("sku") or "")
    st.session_state[_mat_takeoff_key(estimate_id, "desc", rid)] = str(inv.get("name") or "")
    cat = str(inv.get("category") or categories[0] if categories else "General")
    st.session_state[_mat_takeoff_key(estimate_id, "cat", rid)] = cat if cat in categories else categories[0]
    unit = str(inv.get("unit") or "EA")
    st.session_state[_mat_takeoff_key(estimate_id, "unit", rid)] = unit if unit in units else units[0]
    st.session_state[_mat_takeoff_key(estimate_id, "qty", rid)] = float(st.session_state.get("mat_inv_qty") or 1)
    st.session_state[_mat_takeoff_key(estimate_id, "cost", rid)] = float(
        inv.get("unit_cost") or inv.get("average_cost") or 0
    )
    st.session_state[_mat_takeoff_key(estimate_id, f"last_pick_{rid}", rid)] = _CUSTOM_TAKEOFF_ITEM


def _render_saved_materials_list(estimate_id: str, materials: list[dict]) -> None:
    if not materials:
        return
    st.caption("Saved material lines — remove with ✕, or add more lines below.")
    for row in materials:
        mid = str(row.get("id") or "").strip()
        if not mid:
            continue
        c0, c1 = st.columns([10, 1], gap="small")
        with c0:
            st.markdown(
                f"**{html.escape(str(row.get('item_number') or '—'))}** · "
                f"{html.escape(str(row.get('description') or '—'))} · "
                f"Qty {html.escape(str(row.get('qty') or ''))} · "
                f"{html.escape(fmt_currency(row.get('total_cost')))}"
            )
        with c1:
            if st.button("✕", key=f"mat_saved_del_{mid}", help="Delete material line"):
                result = delete_estimate_material(mid, estimate_id=estimate_id)
                if result.ok:
                    st.rerun()
                else:
                    st.error(str(result.error or "Could not delete line."))


def _render_materials_takeoff_grid(estimate_id: str) -> None:
    pick = str(estimate_id or "").strip()
    categories = lookup_options("inventory_categories")
    units = lookup_options("units")
    inv_items = load_inventory()
    pick_labels, searchable, inv_by_label = _inventory_search_options(inv_items)
    draft_key = _mat_takeoff_draft_key(pick)
    draft_rows = _ensure_takeoff_draft(pick)

    st.caption(
        f"{_TAKEOFF_DRAFT_COUNT} blank rows ready — type in Item # to search inventory, "
        "then save. A new blank row appears when you fill the last one."
    )
    hdr = st.columns([1.2, 2.0, 1.0, 0.65, 0.65, 0.85, 0.85, 0.45], gap="small")
    for col, label in zip(
        hdr,
        ("Item #", "Description", "Category", "Qty", "Unit", "Unit Cost", "Extended", ""),
    ):
        with col:
            st.markdown(
                f'<div style="font-size:0.72rem;font-weight:700;color:#64748b;">{html.escape(label)}</div>',
                unsafe_allow_html=True,
            )

    remove_rid = ""
    for row in draft_rows:
        rid = str(row.get("rid") or "")
        if not rid:
            continue
        st.session_state.setdefault(_mat_takeoff_key(pick, "qty", rid), 1.0)
        st.session_state.setdefault(_mat_takeoff_key(pick, "cost", rid), 0.0)
        st.session_state.setdefault(_mat_takeoff_key(pick, "cat", rid), categories[0] if categories else "General")
        st.session_state.setdefault(_mat_takeoff_key(pick, "unit", rid), units[0] if units else "EA")
        if _mat_takeoff_key(pick, f"pick_{rid}", rid) not in st.session_state:
            st.session_state[_mat_takeoff_key(pick, f"pick_{rid}", rid)] = _CUSTOM_TAKEOFF_ITEM

        cols = st.columns([1.2, 2.0, 1.0, 0.65, 0.65, 0.85, 0.85, 0.45], gap="small")
        with cols[0]:
            item_pick = render_searchable_selectbox(
                "Item #",
                pick_labels,
                key=_mat_takeoff_key(pick, f"pick_{rid}", rid),
                placeholder="Search item #…",
                searchable_options=searchable,
            )
            _sync_takeoff_inventory_pick(pick, rid, item_pick, inv_by_label, categories=categories, units=units)
            if item_pick == _CUSTOM_TAKEOFF_ITEM:
                st.text_input(
                    "Item #",
                    key=_mat_takeoff_key(pick, "item", rid),
                    label_visibility="collapsed",
                    placeholder="Item #",
                )
        with cols[1]:
            st.text_input(
                "Description",
                key=_mat_takeoff_key(pick, "desc", rid),
                label_visibility="collapsed",
                placeholder="Description",
            )
        with cols[2]:
            st.selectbox(
                "Category",
                categories,
                key=_mat_takeoff_key(pick, "cat", rid),
                label_visibility="collapsed",
            )
        with cols[3]:
            qty = st.number_input(
                "Qty",
                min_value=0.0,
                step=1.0,
                key=_mat_takeoff_key(pick, "qty", rid),
                label_visibility="collapsed",
            )
        with cols[4]:
            st.selectbox(
                "Unit",
                units,
                key=_mat_takeoff_key(pick, "unit", rid),
                label_visibility="collapsed",
            )
        with cols[5]:
            unit_cost = st.number_input(
                "Unit cost",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                key=_mat_takeoff_key(pick, "cost", rid),
                label_visibility="collapsed",
            )
        with cols[6]:
            extended = float(qty or 0) * float(unit_cost or 0)
            st.markdown(
                f'<div style="padding-top:0.45rem;font-weight:700;font-size:0.82rem;">'
                f"{html.escape(fmt_currency(extended))}</div>",
                unsafe_allow_html=True,
            )
        with cols[7]:
            if st.button("✕", key=_mat_takeoff_key(pick, "rm", rid), help="Remove row"):
                remove_rid = rid

    if draft_rows and _takeoff_row_has_data(pick, str(draft_rows[-1].get("rid") or "")):
        extended_rows = list(draft_rows)
        extended_rows.append(_new_takeoff_row())
        st.session_state[draft_key] = extended_rows
        st.rerun()

    if remove_rid:
        remaining = [r for r in draft_rows if str(r.get("rid")) != remove_rid]
        st.session_state[draft_key] = remaining or _initial_takeoff_rows()
        st.rerun()

    if st.button("Save Material Lines", key=f"mat_takeoff_save_{pick}", type="primary", use_container_width=True):
        saved = 0
        errors: list[str] = []
        for row in list(st.session_state.get(draft_key) or []):
            rid = str(row.get("rid") or "")
            if not rid or not _takeoff_row_has_data(pick, rid):
                continue
            ok, msg = persist_estimate_material(
                {
                    "estimate_id": pick,
                    "item_number": st.session_state.get(_mat_takeoff_key(pick, "item", rid)),
                    "description": st.session_state.get(_mat_takeoff_key(pick, "desc", rid)),
                    "category": st.session_state.get(_mat_takeoff_key(pick, "cat", rid)),
                    "qty": st.session_state.get(_mat_takeoff_key(pick, "qty", rid)),
                    "unit": st.session_state.get(_mat_takeoff_key(pick, "unit", rid)),
                    "unit_cost": st.session_state.get(_mat_takeoff_key(pick, "cost", rid)),
                }
            )
            if ok:
                saved += 1
            elif msg:
                errors.append(str(msg))
        if saved:
            st.session_state[draft_key] = _initial_takeoff_rows()
            st.success(f"Saved {saved} material line{'s' if saved != 1 else ''}.")
            st.rerun()
        if errors:
            st.error(errors[0])
        else:
            st.error("Enter at least one material line with item/description and quantity.")


def _persist_inventory_material_line(*, estimate_id: str, inv: dict, qty: float) -> tuple[bool, str]:
    unit_cost = float(inv.get("unit_cost") or inv.get("average_cost") or 0)
    return persist_estimate_material(
        {
            "estimate_id": estimate_id,
            "item_number": str(inv.get("sku") or inv.get("id") or ""),
            "description": str(inv.get("name") or "Inventory item"),
            "category": str(inv.get("category") or lookup_options("inventory_categories")[0]),
            "qty": max(float(qty or 1), 0.0),
            "unit": "EA",
            "unit_cost": unit_cost,
        }
    )


def render_estimate_materials_panel(
    *,
    estimate_id: str,
    est: dict,
    materials: list[dict] | None = None,
    summary: dict | None = None,
) -> None:
    """Materials takeoff UI — embedded in estimate detail or standalone page."""
    pick = str(estimate_id or "").strip()
    if not pick:
        st.warning("No estimate selected.")
        return
    if materials is None:
        materials = load_estimate_materials(pick)
    summ = summary if summary is not None else materials_summary(materials)

    export_col, _ = st.columns([1, 3], gap="small")
    with export_col:
        export_name = f"estimate_{est.get('estimate_number') or pick}_materials.csv"
        st.download_button(
            "Export Materials",
            data=_materials_csv_bytes(materials, estimate_number=str(est.get("estimate_number") or "")),
            file_name=export_name,
            mime="text/csv",
            key=f"mat_export_{pick}",
            use_container_width=True,
        )

    _render_summary_card(est)

    mat_tab = render_tabs(
        ["Materials", "Add Items", "Summary"],
        session_key="ips_mat_section_tab",
        default="Materials",
    )

    def _mat_filters() -> None:
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.text_input("Search", placeholder="Search materials…", key="mat_search", label_visibility="collapsed")
        with c2:
            if st.button("Add from Inventory", key="mat_add_inv", use_container_width=True):
                st.session_state["ips_mat_inv_panel"] = True
        with c3:
            if st.button("Add Custom Item", key="mat_add_custom", use_container_width=True):
                st.session_state.pop("ips_mat_inv_panel", None)
                _ensure_takeoff_draft(pick)

    layout_filter_bar(_mat_filters)

    if mat_tab == "Add Items":
        st.caption("Use **Add from Inventory** or type directly in the blank rows on the **Materials** tab.")

    if st.session_state.get("ips_mat_inv_panel"):
        with st.expander("Add from inventory", expanded=True):
            inv_labels, inv_by_label = _inventory_picker_options(load_inventory())
            categories = lookup_options("inventory_categories")
            units = lookup_options("units")
            if not inv_labels:
                st.warning("No live inventory items available.")
            else:
                picked_label = st.selectbox("Inventory item", inv_labels, key="mat_inv_pick")
                st.number_input("Qty", min_value=0.0, value=1.0, key="mat_inv_qty")
                add_col, cancel_col = st.columns(2)
                with add_col:
                    if st.button("Add line", key="mat_inv_save", type="primary", use_container_width=True):
                        inv = inv_by_label.get(str(st.session_state.get("mat_inv_pick") or picked_label))
                        if not inv:
                            st.error("Select an inventory item.")
                        else:
                            draft_key = _mat_takeoff_draft_key(pick)
                            draft_rows = _ensure_takeoff_draft(pick)
                            target_rid = _first_empty_takeoff_rid(pick)
                            if not target_rid:
                                new_row = _new_takeoff_row()
                                draft_rows = list(draft_rows) + [new_row]
                                st.session_state[draft_key] = draft_rows
                                target_rid = str(new_row.get("rid") or "")
                            _populate_takeoff_row_from_inventory(
                                pick,
                                target_rid,
                                inv,
                                categories=categories,
                                units=units,
                            )
                            st.session_state.pop("ips_mat_inv_panel", None)
                            st.rerun()
                with cancel_col:
                    if st.button("Cancel", key="mat_inv_cancel", use_container_width=True):
                        st.session_state.pop("ips_mat_inv_panel", None)
                        st.rerun()

    q = str(st.session_state.get("mat_search") or "").strip().lower()
    filtered = materials
    if q:
        filtered = [
            m
            for m in materials
            if q in str(m.get("description", "")).lower()
            or q in str(m.get("item_number", "")).lower()
        ]

    main_l, main_r = st.columns([2.4, 1], gap="medium")

    with main_l:
        if mat_tab == "Summary":
            ot = "d" + "iv"
            st.markdown(f'<{ot} class="ips-panel-card">', unsafe_allow_html=True)
            st.markdown("**Full materials breakdown**")
            for lbl, key in [
                ("Material Total", "material_total"),
                ("Freight", "freight"),
                ("Tax (8.25%)", "tax"),
                ("Total", "total"),
            ]:
                st.markdown(f"**{lbl}:** {fmt_currency(summ[key])}")
            st.markdown(f"</{ot}>", unsafe_allow_html=True)
        elif mat_tab in ("Materials", "Add Items"):
            _render_saved_materials_list(pick, filtered)
            _render_materials_takeoff_grid(pick)

    with main_r:
        ot = "d" + "iv"
        st.markdown(f'<{ot} class="ips-side-panel">', unsafe_allow_html=True)
        st.markdown("<h4>Materials Summary</h4>", unsafe_allow_html=True)
        for lbl, key in [
            ("Material Total", "material_total"),
            ("Freight", "freight"),
            ("Tax (8.25%)", "tax"),
            ("Total", "total"),
        ]:
            st.markdown(
                f'<{ot} class="ips-side-line"><span>{html.escape(lbl)}</span>'
                f"<span>{html.escape(fmt_currency(summ[key]))}</span></{ot}>",
                unsafe_allow_html=True,
            )
        st.markdown("<h4 style='margin-top:0.75rem'>Materials Markup</h4>", unsafe_allow_html=True)
        st.number_input("Markup %", value=summ["markup_pct"] * 100, key="mat_markup_pct", format="%.2f")
        st.markdown(
            f'<{ot} class="ips-side-line"><span>Markup Amount</span>'
            f"<span>{html.escape(fmt_currency(summ['markup_amt']))}</span></{ot}>"
            f'<{ot} class="ips-side-line"><span>Materials w/ Markup</span>'
            f"<span>{html.escape(fmt_currency(summ['with_markup']))}</span></{ot}>",
            unsafe_allow_html=True,
        )
        st.markdown(f"</{ot}>", unsafe_allow_html=True)


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("estimate_materials"):
        return

    eid = str(st.session_state.get(ACTIVE_ESTIMATE_KEY) or "").strip()
    try:
        from app.navigation import ESTIMATE_DETAIL_TAB_KEY, navigate_to_estimate_detail, set_nav_slug
    except ImportError:
        from navigation import ESTIMATE_DETAIL_TAB_KEY, navigate_to_estimate_detail, set_nav_slug  # type: ignore

    if eid:
        navigate_to_estimate_detail(eid, tab="Materials")
        st.rerun()
        return

    st.info("Materials are managed inside each estimate. Open an estimate from the Estimates list.")
    if st.button("Go to Estimates", key="mat_redirect_estimates"):
        st.session_state.pop(ESTIMATE_DETAIL_TAB_KEY, None)
        set_nav_slug("estimates")
        st.rerun()

