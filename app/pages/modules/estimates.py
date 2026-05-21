"""Estimates module (Phase 2B)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.charts import render_donut_chart
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.layout import render_tab_placeholder
    from app.components.modals import render_record_detail_dialog
    from app.components.status import status_pill_html
    from app.components.tables import render_clickable_table, render_data_table
    from app.components.tabs import render_tabs
    from app.pages.modules._data import (
        ACTIVE_ESTIMATE_KEY,
        customer_filter_options,
        get_estimate,
        load_estimates,
        lookup_options,
        persist_estimate,
    )
    from app.pages.modules._crud import apply_persist_feedback, is_demo_id
    from app.pages.modules._session import select_key, tab_key
    from app.styles import inject_estimates_module_css
    from app.utils.constants import ESTIMATE_STATUSES, SESSION_NAV_KEY
    from app.estimates.utils import resolve_estimate_subtotal
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from components.charts import render_donut_chart  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.layout import render_tab_placeholder  # type: ignore
    from components.modals import render_record_detail_dialog  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_clickable_table, render_data_table  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._data import (  # type: ignore
        ACTIVE_ESTIMATE_KEY,
        customer_filter_options,
        get_estimate,
        load_estimates,
        lookup_options,
        persist_estimate,
    )
    from pages.modules._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages.modules._session import select_key, tab_key  # type: ignore
    from styles import inject_estimates_module_css, inject_global_css  # type: ignore
    from utils.constants import ESTIMATE_STATUSES, SESSION_NAV_KEY  # type: ignore
    from estimates.utils import resolve_estimate_subtotal  # type: ignore
    from utils.formatting import fmt_currency, fmt_date  # type: ignore

_SEL = select_key("estimates")
_TAB = tab_key("estimates")


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


def _render_detail(est: dict) -> None:
    en = str(est.get("estimate_number") or "")
    title = str(est.get("project_name") or en)

    def _tabs() -> None:
        render_tabs(
            [
                "Overview",
                "Line Items",
                "Labor",
                "Materials",
                "Equipment",
                "Attachments",
                "Notes",
                "Activity",
            ],
            session_key=_TAB,
            default="Overview",
        )

    def _body() -> None:
        ot = "d" + "iv"
        st.markdown(
            f'<{ot} class="ips-detail-meta-row">'
            f"<span>Status<br>{status_pill_html(str(est.get('status') or ''))}</span>"
            f"<span>Customer<br><strong>{html.escape(str(est.get('customer') or '—'))}</strong></span>"
            f"<span>Total<br><strong>{html.escape(fmt_currency(est.get('total')))}</strong></span>"
            f"</{ot}>",
            unsafe_allow_html=True,
        )
        tab = str(st.session_state.get(_TAB) or "Overview")
        if tab == "Materials":
            st.session_state[ACTIVE_ESTIMATE_KEY] = str(est.get("id") or "")
            if st.button("Open Estimate Materials", key="est_open_materials", type="primary"):
                st.session_state[SESSION_NAV_KEY] = "estimate_materials"
                st.rerun()
            return
        if tab != "Overview":
            render_tab_placeholder(f"{tab} will connect to Supabase in a later phase.")
            return
        c1, c2, c3 = st.columns([1.2, 1, 1])
        with c1:
            st.markdown("**Estimate Summary**")
            st.markdown(
                f'<dl class="ips-info-grid">'
                f"<dt>Estimate #</dt><dd>{html.escape(en)}</dd>"
                f"<dt>Project</dt><dd>{html.escape(str(est.get('project_name') or '—'))}</dd>"
                f"<dt>Customer</dt><dd>{html.escape(str(est.get('customer') or '—'))}</dd>"
                f"<dt>Status</dt><dd>{status_pill_html(str(est.get('status') or ''))}</dd>"
                f"<dt>Linked Job</dt><dd>{html.escape(str(est.get('job_number') or '—'))}</dd>"
                f"</dl>",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown("**Financial Summary**")
            subtotal_display = float(resolve_estimate_subtotal(est))
            st.markdown(
                f'<dl class="ips-info-grid">'
                f"<dt>Subtotal</dt><dd>{html.escape(fmt_currency(subtotal_display))}</dd>"
                f"<dt>Tax</dt><dd>{html.escape(fmt_currency(est.get('tax')))}</dd>"
                f"<dt>Markup</dt><dd>{html.escape(fmt_currency(est.get('markup')))}</dd>"
                f"<dt>Grand Total</dt><dd>{html.escape(fmt_currency(est.get('total')))}</dd>"
                f"</dl>",
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown("**Estimate Totals**")
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
        st.markdown('<p class="ips-panel-title">Top Line Items</p>', unsafe_allow_html=True)
        line_items = [
            {"id": "li1", "item": "Labor — Rough-in", "description": "Plumbing rough-in", "qty": 40, "unit": "HR", "unit_price": 85, "total": 3400},
            {"id": "li2", "item": "MAT-1001", "description": "2x4x8 PT Lumber", "qty": 120, "unit": "EA", "unit_price": 8.45, "total": 1014},
        ]

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
            session_select_key="ips_sel_est_line_items",
            col_fr=["0.8fr", "1.5fr", "0.5fr", "0.5fr", "0.7fr", "0.7fr"],
            cell_renderer=_li_cell,
        )
        eid = str(est.get("id") or "")
        if not is_demo_id(eid):
            with st.expander("Edit estimate", expanded=False):
                ec1, ec2 = st.columns(2)
                with ec1:
                    st.text_input("Estimate #", value=str(est.get("estimate_number") or ""), key=f"est_edit_num_{eid}")
                    st.text_input("Project", value=str(est.get("project_name") or ""), key=f"est_edit_proj_{eid}")
                    st.selectbox("Customer", customer_filter_options(), key=f"est_edit_cust_{eid}")
                    st.selectbox("Status", lookup_options("estimate_statuses"), key=f"est_edit_status_{eid}")
                with ec2:
                    st.number_input("Subtotal", value=float(est.get("subtotal") or 0), key=f"est_edit_sub_{eid}")
                    st.number_input("Tax", value=float(est.get("tax") or 0), key=f"est_edit_tax_{eid}")
                    st.number_input("Total", value=float(est.get("total") or 0), key=f"est_edit_total_{eid}")
                st.text_area("Notes", value=str(est.get("description") or ""), key=f"est_edit_notes_{eid}")
                if st.button("Save estimate", key=f"est_save_{eid}", type="primary"):
                    ok, msg = persist_estimate(
                        {
                            "estimate_number": st.session_state.get(f"est_edit_num_{eid}"),
                            "project_name": st.session_state.get(f"est_edit_proj_{eid}"),
                            "customer": st.session_state.get(f"est_edit_cust_{eid}"),
                            "status": st.session_state.get(f"est_edit_status_{eid}"),
                            "subtotal": st.session_state.get(f"est_edit_sub_{eid}"),
                            "tax": st.session_state.get(f"est_edit_tax_{eid}"),
                            "total": st.session_state.get(f"est_edit_total_{eid}"),
                            "description": st.session_state.get(f"est_edit_notes_{eid}"),
                        },
                        row_id=eid,
                    )
                    if apply_persist_feedback(ok, msg):
                        st.rerun()

    render_record_detail_dialog(
        f"{title} — Estimate Details",
        module_name="estimates",
        session_select_key=_SEL,
        tabs_fn=_tabs,
        body_fn=_body,
    )


def render() -> None:
    try:
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
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
                st.selectbox("Status", lookup_options("estimate_statuses"), key="est_new_status")
            with nc2:
                st.number_input("Total", value=0.0, key="est_new_total")
            st.text_area("Notes", key="est_new_notes")
            if st.button("Save estimate", key="est_save_new", type="primary"):
                ok, msg = persist_estimate(
                    {
                        "estimate_number": st.session_state.get("est_new_num"),
                        "project_name": st.session_state.get("est_new_proj"),
                        "customer": st.session_state.get("est_new_cust"),
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

    selected_id = str(st.session_state.get(_SEL) or "")
    if selected_id and not any(str(r.get("id")) == selected_id for r in filtered):
        st.session_state.pop(_SEL, None)
        selected_id = ""

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "estimate_number":
            return f'<span style="color:#2563eb;font-weight:600">{html.escape(str(row.get("estimate_number") or ""))}</span>'
        if field == "total":
            return html.escape(fmt_currency(row.get("total")))
        if field in ("estimate_date", "expiration_date"):
            return html.escape(fmt_date(row.get(field)))
        return html.escape(str(row.get(field) or "—"))

    def _plain_cell(field: str, row: dict) -> str:
        if field == "total":
            return fmt_currency(row.get("total"))
        if field in ("estimate_date", "expiration_date"):
            return fmt_date(row.get(field))
        return str(row.get(field) or "—")

    sel = render_clickable_table(
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
        selected_id=selected_id or None,
        plain_cell=_plain_cell,
    )

    if sel:
        est = get_estimate(sel) or next((r for r in filtered if str(r.get("id")) == sel), None)
        if est:
            st.session_state[ACTIVE_ESTIMATE_KEY] = str(est.get("id") or "")
            _render_detail(est)
