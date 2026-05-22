"""Estimate Materials module (Phase 2B)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.clickable_table import render_clickable_table
    from app.components.headers import render_page_header
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
        load_estimates,
        lookup_options,
        materials_summary,
        persist_estimate_material,
    )
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
    from app.styles import inject_global_css
    from app.utils.constants import SESSION_NAV_KEY
    from app.utils.formatting import fmt_currency
except ImportError:
    from components.clickable_table import render_clickable_table  # type: ignore
    from components.headers import render_page_header  # type: ignore
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
        load_estimates,
        lookup_options,
        materials_summary,
        persist_estimate_material,
    )
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.constants import SESSION_NAV_KEY  # type: ignore
    from utils.formatting import fmt_currency  # type: ignore

_SEL = select_key("estimate_materials")
_MODULE = "estimate_materials"
_TABLE_KEY = "mat_list"
_MODAL_KEY = "ips_mat_detail_modal_id"
_CACHE_KEY = "_ips_mat_modal_by_id"


def _render_summary_card(est: dict) -> None:
    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-summary-card">', unsafe_allow_html=True)
    cols = st.columns(6)
    fields = [
        ("Client", str(est.get("customer") or "—")),
        ("Job", f"{est.get('job_number') or '—'} — {est.get('project_name') or ''}"),
        ("Estimate Date", str(est.get("estimate_date") or "—")[:10]),
        ("Valid Through", str(est.get("expiration_date") or "—")[:10]),
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


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("estimate_materials"):
        return
    estimates = load_estimates()
    est_opts = {str(e.get("id")): f"{e.get('estimate_number')} — {e.get('project_name')}" for e in estimates}
    if not est_opts:
        st.warning("No estimates available.")
        return

    default_id = str(st.session_state.get(ACTIVE_ESTIMATE_KEY) or list(est_opts.keys())[0])
    if default_id not in est_opts:
        default_id = list(est_opts.keys())[0]

    est_hdr = get_estimate(default_id) or estimates[0]
    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        render_page_header(
            f"Estimate {est_hdr.get('estimate_number')} — Materials",
            str(est_hdr.get("project_name") or ""),
        )
        if st.button("← Back to Estimates", key="mat_back_est"):
            st.session_state[SESSION_NAV_KEY] = "estimates"
            st.rerun()
    with hdr_r:
        st.button("Export", key="mat_export", use_container_width=True)
        st.button("Edit Estimate", key="mat_edit", type="primary", use_container_width=True)

    pick = st.selectbox(
        "Estimate",
        options=list(est_opts.keys()),
        format_func=lambda k: est_opts[k],
        index=list(est_opts.keys()).index(default_id),
        key="mat_estimate_pick",
        label_visibility="collapsed",
    )
    st.session_state[ACTIVE_ESTIMATE_KEY] = pick
    est = get_estimate(pick) or estimates[0]
    _render_summary_card(est)

    materials = load_estimate_materials(pick)
    summ = materials_summary(materials)

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
            st.button("Add from Inventory", key="mat_add_inv", use_container_width=True)
        with c3:
            st.button("Add Custom Item", key="mat_add_custom", use_container_width=True)
        with c4:
            if st.button("+ Add Material", key="mat_add", type="primary", use_container_width=True):
                st.session_state["ips_mat_form"] = True

    layout_filter_bar(_mat_filters)

    if mat_tab == "Add Items":
        st.caption("Add lines using **Add from Inventory**, **Add Custom Item**, or **+ Add Material** above.")

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
