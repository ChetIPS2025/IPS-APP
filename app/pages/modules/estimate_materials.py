"""Estimate Materials module (Phase 2B)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.status import status_pill_html
    from app.components.tables import render_data_table
    from app.components.tabs import render_tabs
    from app.pages.modules._data import (
        ACTIVE_ESTIMATE_KEY,
        get_estimate,
        load_estimate_materials,
        load_estimates,
        lookup_options,
        materials_summary,
        persist_estimate_material,
    )
    from app.pages.modules._crud import apply_persist_feedback
    from app.styles import inject_global_css
    from app.utils.constants import SESSION_NAV_KEY
    from app.utils.formatting import fmt_currency
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._data import (  # type: ignore
        ACTIVE_ESTIMATE_KEY,
        get_estimate,
        load_estimate_materials,
        load_estimates,
        lookup_options,
        materials_summary,
        persist_estimate_material,
    )
    from pages.modules._crud import apply_persist_feedback  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.constants import SESSION_NAV_KEY  # type: ignore
    from utils.formatting import fmt_currency  # type: ignore


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


def render() -> None:
    try:
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
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

    def _cell(field: str, row: dict) -> str:
        if field == "item_number":
            return f'<span style="color:#2563eb;font-weight:600">{html.escape(str(row.get("item_number") or ""))}</span>'
        if field in ("unit_cost", "total_cost"):
            return html.escape(fmt_currency(row.get(field)))
        return html.escape(str(row.get(field) or "—"))

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
            render_data_table(
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
                row_id_key="id",
                selected_id=None,
                session_select_key="ips_sel_mat_rows",
                col_fr=["0.75fr", "1.4fr", "0.8fr", "0.5fr", "0.45fr", "0.7fr", "0.75fr"],
                cell_renderer=_cell,
            )

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
