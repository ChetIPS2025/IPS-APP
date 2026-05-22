"""Estimates module (Phase 2B)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.charts import render_donut_chart
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.clickable_table import render_clickable_table
    from app.components.record_modal import (
        build_modal_cache,
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
    from app.components.tables import render_data_table
    from app.pages._core._data import (
        ACTIVE_ESTIMATE_KEY,
        customer_contact_select_options,
        customer_filter_options,
        customer_id_for_name,
        get_estimate,
        load_estimates,
        lookup_options,
        persist_estimate,
    )
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
    from app.styles import inject_estimates_module_css
    from app.utils.constants import SESSION_NAV_KEY
    from app.estimates.utils import resolve_estimate_subtotal
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from components.charts import render_donut_chart  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.clickable_table import render_clickable_table  # type: ignore
    from components.record_modal import (  # type: ignore
        build_modal_cache,
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
    from components.tables import render_data_table  # type: ignore
    from pages._core._data import (  # type: ignore
        ACTIVE_ESTIMATE_KEY,
        customer_contact_select_options,
        customer_filter_options,
        customer_id_for_name,
        get_estimate,
        load_estimates,
        lookup_options,
        persist_estimate,
    )
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from styles import inject_estimates_module_css  # type: ignore
    from utils.constants import SESSION_NAV_KEY  # type: ignore
    from estimates.utils import resolve_estimate_subtotal  # type: ignore
    from utils.formatting import fmt_currency, fmt_date  # type: ignore

_SEL = select_key("estimates")
_MOD = "estimates"
_ESTIMATES_MODAL_KEY = "ips_estimates_detail_modal_id"
_ESTIMATES_CACHE_KEY = "_ips_estimates_modal_by_id"
_NEW_CUST_PREV = "est_new_cust_prev"
_ESTIMATE_TABS = [
    "Overview",
    "Line Items",
    "Labor",
    "Materials",
    "Equipment",
    "Subcontractors",
    "Markups",
    "Attachments",
    "Notes",
    "Activity",
    "Proposal Preview",
]


def _contact_label_for_estimate(est: dict) -> str:
    ccid = str(est.get("customer_contact_id") or "").strip()
    if not ccid:
        return "—"
    cid = customer_id_for_name(str(est.get("customer") or ""))
    for label, contact_id in customer_contact_select_options(cid):
        if contact_id == ccid:
            return label
    return "—"


def _customer_contact_select(
    *,
    customer_name: str,
    session_key: str,
    prev_customer_key: str,
    initial_contact_id: str = "",
) -> str:
    cust = str(customer_name or "").strip()
    if st.session_state.get(prev_customer_key) != cust:
        st.session_state.pop(session_key, None)
        st.session_state[prev_customer_key] = cust

    cid = customer_id_for_name(cust)
    if not cust or not cid:
        st.selectbox(
            "Contact",
            ["— Select customer first —"],
            disabled=True,
            key=session_key,
        )
        return ""

    pairs = customer_contact_select_options(cid)
    if not pairs:
        st.selectbox(
            "Contact",
            ["— No contacts for this customer —"],
            disabled=True,
            key=session_key,
        )
        return ""

    labels = ["— Select contact —", *[label for label, _ in pairs]]
    ids = ["", *[contact_id for _, contact_id in pairs]]

    if session_key not in st.session_state and initial_contact_id:
        try:
            st.session_state[session_key] = ids.index(initial_contact_id)
        except ValueError:
            st.session_state[session_key] = 0

    idx = st.selectbox(
        "Contact",
        range(len(labels)),
        format_func=lambda i: labels[i],
        key=session_key,
    )
    return str(ids[int(idx)])


def _filter_rows(rows: list[dict], *, q: str, status: str, customer: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            r
            for r in out
            if ql in str(r.get("estimate_number", "")).lower()
            or ql in str(r.get("project_name", "")).lower()
            or ql in str(r.get("customer", "")).lower()
        ]
    if status and status != "All Statuses":
        out = [r for r in out if str(r.get("status", "")) == status]
    if customer and customer != "All Customers":
        out = [r for r in out if str(r.get("customer", "")) == customer]
    return out


def _clear_estimates_detail_modal() -> None:
    clear_record_modal(
        table_key="estimates_list",
        session_select_key=_SEL,
        modal_key=_ESTIMATES_MODAL_KEY,
        module=_MOD,
    )


def _open_estimates_detail_modal(estimate_id: str, estimate: dict | None = None) -> None:
    open_record_modal(
        estimate_id,
        estimate,
        session_select_key=_SEL,
        modal_key=_ESTIMATES_MODAL_KEY,
        module=_MOD,
        id_fields=("id", "estimate_number"),
    )
    if estimate:
        st.session_state[ACTIVE_ESTIMATE_KEY] = str(estimate.get("id") or "")


def _estimate_line_items() -> list[dict]:
    return [
        {"id": "li1", "item": "Labor — Rough-in", "description": "Plumbing rough-in", "qty": 40, "unit": "HR", "unit_price": 85, "total": 3400},
        {"id": "li2", "item": "MAT-1001", "description": "2x4x8 PT Lumber", "qty": 120, "unit": "EA", "unit_price": 8.45, "total": 1014},
    ]


def _render_line_items_table(*, session_key: str) -> None:
    line_items = _estimate_line_items()

    def _li_cell(field: str, row: dict) -> str:
        if field == "total":
            return html.escape(fmt_currency(row.get("total")))
        if field in ("unit_price",):
            return html.escape(fmt_currency(row.get(field)))
        return html.escape(str(row.get(field) or "—"))

    render_data_table(
        line_items,
        [
            ("item", "ITEM"),
            ("description", "DESCRIPTION"),
            ("qty", "QTY"),
            ("unit", "UNIT"),
            ("unit_price", "UNIT PRICE"),
            ("total", "TOTAL"),
        ],
        row_id_key="id",
        selected_id=None,
        session_select_key=session_key,
        col_fr=["0.8fr", "1.5fr", "0.5fr", "0.5fr", "0.7fr", "0.7fr"],
        cell_renderer=_li_cell,
    )


def _seed_estimate_edit_form(est: dict) -> None:
    eid = str(est.get("id") or "")
    st.session_state[f"est_edit_num_{eid}"] = str(est.get("estimate_number") or "")
    st.session_state[f"est_edit_proj_{eid}"] = str(est.get("project_name") or "")
    st.session_state[f"est_edit_cust_{eid}"] = str(est.get("customer") or "")
    st.session_state[f"est_edit_status_{eid}"] = str(est.get("status") or "Draft")
    st.session_state[f"est_edit_sub_{eid}"] = float(est.get("subtotal") or 0)
    st.session_state[f"est_edit_tax_{eid}"] = float(est.get("tax") or 0)
    st.session_state[f"est_edit_total_{eid}"] = float(est.get("total") or 0)
    st.session_state[f"est_edit_notes_{eid}"] = str(est.get("description") or "")
    st.session_state.pop(f"est_edit_contact_{eid}", None)
    st.session_state.pop(f"est_edit_cust_prev_{eid}", None)


def _set_estimate_view_mode(est: dict) -> None:
    rk = record_session_key(est, "id", "estimate_number")
    set_view_mode(_MOD, rk)


def _set_estimate_edit_mode(est: dict) -> None:
    rk = record_session_key(est, "id", "estimate_number")
    set_edit_mode(_MOD, rk)
    _seed_estimate_edit_form(est)


def _render_estimate_edit_form(est: dict) -> None:
    eid = str(est.get("id") or "")
    rk = record_session_key(est, "id", "estimate_number")
    if f"est_edit_num_{eid}" not in st.session_state:
        _seed_estimate_edit_form(est)

    render_edit_form_header("Edit Estimate")

    if is_demo_id(eid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    ec1, ec2 = st.columns(2)
    with ec1:
        st.text_input("Estimate #", key=f"est_edit_num_{eid}")
        st.text_input("Project", key=f"est_edit_proj_{eid}")
        st.selectbox(
            "Customer",
            customer_filter_options(include_names={str(est.get("customer") or "")}),
            key=f"est_edit_cust_{eid}",
        )
        contact_id = _customer_contact_select(
            customer_name=str(st.session_state.get(f"est_edit_cust_{eid}") or est.get("customer") or ""),
            session_key=f"est_edit_contact_{eid}",
            prev_customer_key=f"est_edit_cust_prev_{eid}",
            initial_contact_id=str(est.get("customer_contact_id") or ""),
        )
        st.selectbox("Status", lookup_options("estimate_statuses"), key=f"est_edit_status_{eid}")
    with ec2:
        st.number_input("Subtotal", key=f"est_edit_sub_{eid}")
        st.number_input("Tax", key=f"est_edit_tax_{eid}")
        st.number_input("Total", key=f"est_edit_total_{eid}")
    st.text_area("Notes", key=f"est_edit_notes_{eid}", height=100)

    cancelled, saved = render_save_cancel_actions(
        module=_MOD,
        record_key=rk,
        cancel_key=f"est_edit_cancel_{eid}",
        save_key=f"est_edit_save_{eid}",
    )
    if cancelled:
        st.rerun()
    if saved:
        cust_name = str(st.session_state.get(f"est_edit_cust_{eid}") or "")
        ok, msg = persist_estimate(
            {
                "estimate_number": st.session_state.get(f"est_edit_num_{eid}"),
                "project_name": st.session_state.get(f"est_edit_proj_{eid}"),
                "customer": cust_name,
                "customer_id": customer_id_for_name(cust_name) or None,
                "customer_contact_id": contact_id or None,
                "status": st.session_state.get(f"est_edit_status_{eid}"),
                "subtotal": st.session_state.get(f"est_edit_sub_{eid}"),
                "tax": st.session_state.get(f"est_edit_tax_{eid}"),
                "total": st.session_state.get(f"est_edit_total_{eid}"),
                "description": st.session_state.get(f"est_edit_notes_{eid}"),
            },
            row_id=eid,
        )
        if ok:
            set_view_mode(_MOD, rk)
            st.success(msg or "Estimate saved.")
            st.rerun()
        else:
            st.error(msg or "Could not save estimate.")


def _render_estimate_detail_tabs(est: dict) -> None:
    eid = str(est.get("id") or "")
    en = safe_value(est.get("estimate_number"))
    status = safe_value(est.get("status"))
    customer = safe_value(est.get("customer"))
    subtotal_display = float(resolve_estimate_subtotal(est))

    (
        tab_overview,
        tab_line_items,
        tab_labor,
        tab_materials,
        tab_equipment,
        tab_subcontractors,
        tab_markups,
        tab_attachments,
        tab_notes,
        tab_activity,
        tab_proposal,
    ) = st.tabs(_ESTIMATE_TABS)

    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Estimate #', en)}"
            f"{detail_field_html('Project', est.get('project_name'))}"
            f"{detail_field_html('Customer', customer)}"
            f"{detail_field_html('Contact', _contact_label_for_estimate(est))}"
            f'{detail_field_html("Status", status, html_value=modal_status_pill_html(status))}'
            f"{detail_field_html('Linked Job', est.get('job_number'))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Estimate Summary", overview_html), unsafe_allow_html=True)

        fin_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Subtotal', fmt_currency(subtotal_display))}"
            f"{detail_field_html('Tax', fmt_currency(est.get('tax')))}"
            f"{detail_field_html('Markup', fmt_currency(est.get('markup')))}"
            f"{detail_field_html('Grand Total', fmt_currency(est.get('total')))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Financial Summary", fin_html), unsafe_allow_html=True)

        c1, c2 = st.columns([1, 1])
        with c2:
            breakdown_base = subtotal_display
            breakdown = {
                "Labor": breakdown_base * 0.4,
                "Materials": breakdown_base * 0.3,
                "Equipment": breakdown_base * 0.2,
                "Other": breakdown_base * 0.1,
            }
            render_donut_chart(
                breakdown,
                center_label="Total",
                center_value=fmt_currency(est.get("total")),
                money_legend=True,
            )

    with tab_line_items:
        st.markdown("**Top Line Items**")
        _render_line_items_table(session_key=f"ips_sel_est_line_items_{eid}")

    with tab_labor:
        placeholder_html("Labor line items will appear here when connected to Supabase.")

    with tab_materials:
        st.session_state[ACTIVE_ESTIMATE_KEY] = eid
        if st.button("Open Estimate Materials", key=f"est_open_materials_{eid}", type="primary"):
            st.session_state[SESSION_NAV_KEY] = "estimate_materials"
            st.rerun()

    with tab_equipment:
        placeholder_html("Equipment line items will appear here when connected to Supabase.")

    with tab_subcontractors:
        placeholder_html("Subcontractor line items will appear here when connected to Supabase.")

    with tab_markups:
        placeholder_html("Markup rules will appear here when connected to Supabase.")

    with tab_attachments:
        placeholder_html("Estimate attachments will appear here when connected to Supabase.")

    with tab_notes:
        notes_text = safe_value(est.get("description"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Estimate activity history will appear here when connected to Supabase.")

    with tab_proposal:
        placeholder_html("Proposal preview will appear here when connected to Supabase.")


def render_estimate_detail_dialog(est: dict) -> None:
    rk = record_session_key(est, "id", "estimate_number")
    en = safe_value(est.get("estimate_number"))
    project = safe_value(est.get("project_name"))
    status = safe_value(est.get("status"))
    customer = safe_value(est.get("customer"))
    total = fmt_currency(est.get("total"))

    render_modal_shell()
    render_modal_header(title=en, subtitle=project, status=status)

    def _on_edit() -> None:
        _set_estimate_edit_mode(est)

    st.markdown('<span class="ips-dialog-actions" aria-hidden="true"></span>', unsafe_allow_html=True)
    act1, act2, act3, act4 = st.columns([1, 1, 1, 1], gap="small")
    with act1:
        st.button("View", key=f"estimates_modal_view_{rk}", on_click=_set_estimate_view_mode, args=(est,))
    with act2:
        st.button("Edit", key=f"estimates_modal_edit_{rk}", on_click=_on_edit)
    with act3:
        st.button("More", key=f"estimates_modal_more_{rk}")
    with act4:
        if st.button("Close", key=f"estimates_modal_close_{rk}"):
            _clear_estimates_detail_modal()
            st.rerun()

    render_modal_meta_grid(
        [
            ("Customer", customer),
            ("Total", total),
            ("Status", status),
            ("Linked Job", safe_value(est.get("job_number"))),
        ]
    )

    if is_edit_mode(_MOD, rk):
        _render_estimate_edit_form(est)
    else:
        _render_estimate_detail_tabs(est)


@st.dialog("Estimate Details", width="large", on_dismiss=_clear_estimates_detail_modal)
def _show_estimates_detail_modal() -> None:
    est = get_modal_record(
        cache_key=_ESTIMATES_CACHE_KEY,
        modal_key=_ESTIMATES_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not est:
        sel = str(st.session_state.get(_ESTIMATES_MODAL_KEY) or st.session_state.get(_SEL) or "").strip()
        est = get_estimate(sel) if sel else None
    if not est:
        render_missing_record(_clear_estimates_detail_modal, close_key="estimates_modal_missing_close")
        return
    st.session_state[ACTIVE_ESTIMATE_KEY] = str(est.get("id") or "")
    render_estimate_detail_dialog(est)


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("estimates"):
        return
    inject_estimates_module_css()
    st.markdown('<div class="ips-estimates-page"></div>', unsafe_allow_html=True)
    rows = load_estimates()
    customers = customer_filter_options()

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Estimates", "Create, review, and manage all project estimates.")
    with act_r:
        st.button("Export", key="est_export", use_container_width=True)
        if st.button("+ New Estimate", key="est_new", type="primary", use_container_width=True):
            st.session_state["ips_est_form"] = True

    if st.session_state.get("ips_est_form"):
        with st.expander("New estimate", expanded=True):
            nc1, nc2 = st.columns(2)
            with nc1:
                st.text_input("Estimate #", key="est_new_num")
                st.text_input("Project name", key="est_new_proj")
                st.selectbox("Customer", customer_filter_options(), key="est_new_cust")
                new_cust = str(st.session_state.get("est_new_cust") or "")
                new_contact_id = _customer_contact_select(
                    customer_name=new_cust,
                    session_key="est_new_contact",
                    prev_customer_key=_NEW_CUST_PREV,
                )
                st.selectbox("Status", lookup_options("estimate_statuses"), key="est_new_status")
            with nc2:
                st.number_input("Total", value=0.0, key="est_new_total")
            st.text_area("Notes", key="est_new_notes")
            if st.button("Save estimate", key="est_save_new", type="primary"):
                ok, msg = persist_estimate(
                    {
                        "estimate_number": st.session_state.get("est_new_num"),
                        "project_name": st.session_state.get("est_new_proj"),
                        "customer": new_cust,
                        "customer_id": customer_id_for_name(new_cust) or None,
                        "customer_contact_id": new_contact_id or None,
                        "status": st.session_state.get("est_new_status"),
                        "total": st.session_state.get("est_new_total"),
                        "description": st.session_state.get("est_new_notes"),
                    }
                )
                if apply_persist_feedback(ok, msg, clear_keys=("ips_est_form",)):
                    st.rerun()

    def _filters() -> None:
        c1, c2, c3, c4 = st.columns([2, 1, 1, 0.7])
        with c1:
            st.text_input("Search", placeholder="Search estimates…", key="est_search", label_visibility="collapsed")
        with c2:
            st.selectbox(
                "Status",
                ["All Statuses", *lookup_options("estimate_statuses")],
                key="est_filter_status",
                label_visibility="collapsed",
            )
        with c3:
            st.selectbox("Customer", ["All Customers", *customers], key="est_filter_customer", label_visibility="collapsed")
        with c4:
            if st.button("Clear", key="est_clear", use_container_width=True):
                st.session_state["est_search"] = ""
                st.session_state["est_filter_status"] = "All Statuses"
                st.session_state["est_filter_customer"] = "All Customers"
                st.rerun()

    layout_filter_bar(_filters)

    filtered = _filter_rows(
        rows,
        q=str(st.session_state.get("est_search") or "").strip(),
        status=str(st.session_state.get("est_filter_status") or "All Statuses"),
        customer=str(st.session_state.get("est_filter_customer") or "All Customers"),
    )

    def _display_cell(field: str, row: dict) -> str:
        if field == "total":
            return fmt_currency(row.get("total"))
        if field in ("estimate_date", "expiration_date"):
            return fmt_date(row.get(field))
        val = row.get(field)
        return str(val).strip() if val is not None and str(val).strip() else "—"

    build_modal_cache(filtered, cache_key=_ESTIMATES_CACHE_KEY)

    render_clickable_table(
        filtered,
        [
            ("estimate_number", "ESTIMATE #"),
            ("project_name", "PROJECT / DESCRIPTION"),
            ("customer", "CUSTOMER"),
            ("estimate_date", "ESTIMATE DATE"),
            ("expiration_date", "EXPIRATION"),
            ("total", "TOTAL"),
            ("status", "STATUS"),
            ("created_by", "CREATED BY"),
        ],
        "estimates_list",
        row_id_key="id",
        session_select_key=_SEL,
        format_cell=_display_cell,
        click_caption=f"{len(filtered)} estimate(s) · Click a row to open details.",
        on_row_selected=_open_estimates_detail_modal,
    )

    show_modal_if_pending(_ESTIMATES_MODAL_KEY, _show_estimates_detail_modal)
