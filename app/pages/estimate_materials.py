"""Estimate Materials module (Phase 2B)."""

from __future__ import annotations

import csv
import html
import io

import streamlit as st

try:
    from app.components.clickable_table import render_clickable_table
    from app.components.layout import render_filter_bar as layout_filter_bar
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
    from app.utils.formatting import fmt_currency
except ImportError:
    from components.clickable_table import render_clickable_table  # type: ignore
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
    from utils.formatting import fmt_currency  # type: ignore

_SEL = select_key("estimate_materials")
_MODULE = "estimate_materials"
_TABLE_KEY = "mat_list"
_MODAL_KEY = "ips_mat_detail_modal_id"
_CACHE_KEY = "_ips_mat_modal_by_id"


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
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            st.text_input("Search", placeholder="Search materials…", key="mat_search", label_visibility="collapsed")
        with c2:
            if st.button("Add from Inventory", key="mat_add_inv", use_container_width=True):
                st.session_state["ips_mat_inv_panel"] = True
                st.session_state.pop("ips_mat_form", None)
        with c3:
            if st.button("Add Custom Item", key="mat_add_custom", use_container_width=True):
                st.session_state["ips_mat_form"] = True
                st.session_state.pop("ips_mat_inv_panel", None)
        with c4:
            if st.button("+ Add Material", key="mat_add", type="primary", use_container_width=True):
                st.session_state["ips_mat_form"] = True

    layout_filter_bar(_mat_filters)

    if mat_tab == "Add Items":
        st.caption("Add lines using **Add from Inventory**, **Add Custom Item**, or **+ Add Material** above.")

    if st.session_state.get("ips_mat_inv_panel"):
        with st.expander("Add from inventory", expanded=True):
            inv_labels, inv_by_label = _inventory_picker_options(load_inventory())
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
                            ok, msg = _persist_inventory_material_line(
                                estimate_id=pick,
                                inv=inv,
                                qty=float(st.session_state.get("mat_inv_qty") or 1),
                            )
                            if apply_persist_feedback(ok, msg, clear_keys=("ips_mat_inv_panel",)):
                                st.rerun()
                with cancel_col:
                    if st.button("Cancel", key="mat_inv_cancel", use_container_width=True):
                        st.session_state.pop("ips_mat_inv_panel", None)
                        st.rerun()

    if st.session_state.get("ips_mat_form"):
        with st.expander("Add material line", expanded=True):
            st.text_input("Item #", key="mat_new_item")
            st.text_input("Description", key="mat_new_desc")
            st.selectbox("Category", lookup_options("inventory_categories"), key="mat_new_cat")
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                st.number_input("Qty", value=1.0, key="mat_new_qty")
            with mc2:
                st.selectbox("Unit", lookup_options("units"), key="mat_new_unit")
            with mc3:
                st.number_input("Unit cost", value=0.0, key="mat_new_cost")
            if st.button("Save line", key="mat_save_new", type="primary"):
                ok, msg = persist_estimate_material(
                    {
                        "estimate_id": pick,
                        "item_number": st.session_state.get("mat_new_item"),
                        "description": st.session_state.get("mat_new_desc"),
                        "category": st.session_state.get("mat_new_cat"),
                        "qty": st.session_state.get("mat_new_qty"),
                        "unit": st.session_state.get("mat_new_unit"),
                        "unit_cost": st.session_state.get("mat_new_cost"),
                    }
                )
                if apply_persist_feedback(ok, msg, clear_keys=("ips_mat_form",)):
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
        else:
            build_modal_cache(filtered, cache_key=_CACHE_KEY)
            render_clickable_table(
                filtered,
                [
                    ("item_number", "ITEM #"),
                    ("description", "DESCRIPTION"),
                    ("category", "CATEGORY"),
                    ("qty", "QTY"),
                    ("unit", "UNIT"),
                    ("unit_cost", "UNIT COST"),
                    ("total_cost", "TOTAL COST"),
                ],
                _TABLE_KEY,
                row_id_key="id",
                session_select_key=_SEL,
                format_cell=_mat_display_cell,
                click_caption="Click a row to open material details.",
                on_row_selected=_open_mat_modal,
            )
            show_modal_if_pending(_MODAL_KEY, _show_mat_detail_modal)

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

