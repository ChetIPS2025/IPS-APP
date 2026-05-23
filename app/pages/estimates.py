"""Estimates module (Phase 2B)."""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

try:
    from app.components.charts import render_donut_chart
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
        render_modal_header,
        render_modal_edit_button,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
        status_pill_html as modal_status_pill_html,
    )
    from app.components.tables import render_data_table
    from app.pages._core._data import (
        ACTIVE_ESTIMATE_KEY,
        customer_contact_select_options,
        customer_filter_options,
        customer_id_for_name,
        customer_location_select_options,
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
        render_modal_header,
        render_modal_edit_button,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_edit_mode,
        set_view_mode,
        status_pill_html as modal_status_pill_html,
    )
    from components.tables import render_data_table  # type: ignore
    from pages._core._data import (  # type: ignore
        ACTIVE_ESTIMATE_KEY,
        customer_contact_select_options,
        customer_filter_options,
        customer_id_for_name,
        customer_location_select_options,
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
SELECTED_ESTIMATE_KEY = "selected_estimate_id"
SHOW_ESTIMATE_MODAL_KEY = "show_estimate_detail_modal"
_ALL_ESTIMATE_IDS_KEY = "_ips_estimates_visible_ids"
_ESTIMATE_COLS = [0.35, 1.2, 3.2, 2.1, 1.2, 1.6, 1.3, 1.3, 1.2]
_ESTIMATE_HEADERS = [
    "",
    "ESTIMATE #",
    "PROJECT / DESCRIPTION",
    "CUSTOMER",
    "STATUS",
    "CREATED BY",
    "ESTIMATE DATE",
    "EXPIRATION DATE",
    "TOTAL",
]
_STATUS_FILTER_OPTS = [
    "All Statuses",
    "Draft",
    "Pending",
    "Sent",
    "Approved",
    "Awarded",
    "Rejected",
    "Expired",
    "Cancelled",
]


def _default_estimate_date_range() -> tuple[date, date]:
    today = date.today()
    return today.replace(day=1), today


def _as_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _normalize_estimate_status(raw: object) -> str:
    s = str(raw or "").strip().lower().replace("_", " ")
    mapping = {
        "": "Draft",
        "draft": "Draft",
        "pending": "Pending",
        "sent": "Sent",
        "approved": "Approved",
        "awarded": "Awarded",
        "rejected": "Rejected",
        "expired": "Expired",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
    }
    if s in mapping:
        return mapping[s]
    label = str(raw or "").strip()
    return label if label else "Draft"


def _estimate_number(row: dict) -> str:
    val = str(row.get("estimate_number") or row.get("number") or "").strip()
    return val or "—"


def _estimate_project(row: dict) -> str:
    for key in ("project_name", "project_description", "description"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _estimate_customer(row: dict) -> str:
    for key in ("customer_name", "customer"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _estimate_created_by(row: dict) -> str:
    val = str(row.get("created_by") or row.get("created_by_name") or "").strip()
    return val or "—"


def _estimate_status_pill_html(status: str) -> str:
    cls_map = {
        "Draft": "ips-estimate-status-draft",
        "Pending": "ips-estimate-status-pending",
        "Sent": "ips-estimate-status-sent",
        "Approved": "ips-estimate-status-approved",
        "Awarded": "ips-estimate-status-awarded",
        "Rejected": "ips-estimate-status-rejected",
        "Expired": "ips-estimate-status-expired",
        "Cancelled": "ips-estimate-status-cancelled",
    }
    cls = cls_map.get(status, "ips-estimate-status-draft")
    return f'<span class="ips-estimate-status-pill {cls}">{html.escape(status)}</span>'


def _estimate_select_key(estimate_id: str) -> str:
    return f"estimate_select_{estimate_id}"


def _clear_estimate_selection(estimate_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_ESTIMATE_KEY] = None
    st.session_state[SHOW_ESTIMATE_MODAL_KEY] = False
    ids = list(estimate_ids or [])
    for eid in ids:
        st.session_state[_estimate_select_key(eid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("estimate_select_"):
            st.session_state[key] = False


def _on_estimate_checkbox_change(estimate_id: str, all_estimate_ids: list[str]) -> None:
    key = _estimate_select_key(estimate_id)
    if st.session_state.get(key):
        for eid in all_estimate_ids:
            if eid != estimate_id:
                st.session_state[_estimate_select_key(eid)] = False
        st.session_state[SELECTED_ESTIMATE_KEY] = estimate_id
        st.session_state[SHOW_ESTIMATE_MODAL_KEY] = True
        cache = st.session_state.get(_ESTIMATES_CACHE_KEY) or {}
        estimate = cache.get(estimate_id) if isinstance(cache, dict) else None
        _open_estimates_detail_modal(estimate_id, estimate)
    elif st.session_state.get(SELECTED_ESTIMATE_KEY) == estimate_id:
        st.session_state[SELECTED_ESTIMATE_KEY] = None
        st.session_state[SHOW_ESTIMATE_MODAL_KEY] = False


def _render_custom_estimates_table(filtered: list[dict]) -> list[str]:
    if not filtered:
        st.info("No estimates match your filters.")
        st.session_state[_ALL_ESTIMATE_IDS_KEY] = []
        return []

    all_estimate_ids = [
        str(e.get("id") or "").strip() for e in filtered if str(e.get("id") or "").strip()
    ]
    st.session_state[_ALL_ESTIMATE_IDS_KEY] = all_estimate_ids

    with st.container(key="estimates_table_wrap"):
        st.markdown('<div class="ips-estimates-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_ESTIMATE_COLS, gap="small", vertical_alignment="center")
        for col, label in zip(header_cols, _ESTIMATE_HEADERS):
            with col:
                st.markdown(
                    f'<div class="ips-estimates-header-row ips-estimates-cell">{html.escape(label)}</div>',
                    unsafe_allow_html=True,
                )

        for est in filtered:
            eid = str(est.get("id") or "").strip()
            if not eid:
                continue

            est_no = _estimate_number(est)
            project = _estimate_project(est)
            customer = _estimate_customer(est)
            status = _normalize_estimate_status(est.get("status"))
            created_by = _estimate_created_by(est)
            est_date = fmt_date(est.get("estimate_date"))
            exp_date = fmt_date(est.get("expiration_date"))
            total = fmt_currency(est.get("total"))

            cols = st.columns(_ESTIMATE_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                st.checkbox(
                    "",
                    key=_estimate_select_key(eid),
                    label_visibility="collapsed",
                    on_change=_on_estimate_checkbox_change,
                    args=(eid, all_estimate_ids),
                )

            with cols[1]:
                st.markdown(
                    f'<div class="ips-estimates-number">{html.escape(est_no)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[2]:
                st.markdown(
                    f'<div class="ips-estimates-title">{html.escape(project)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(
                    f'<div class="ips-estimates-cell">{html.escape(customer)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(_estimate_status_pill_html(status), unsafe_allow_html=True)

            with cols[5]:
                st.markdown(
                    f'<div class="ips-estimates-cell ips-estimates-muted">{html.escape(created_by)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[6]:
                st.markdown(
                    f'<div class="ips-estimates-cell ips-estimates-muted">{html.escape(est_date)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[7]:
                st.markdown(
                    f'<div class="ips-estimates-cell ips-estimates-muted">{html.escape(exp_date)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[8]:
                st.markdown(
                    f'<div class="ips-estimates-cell">{html.escape(total)}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    return all_estimate_ids


def _contact_label_for_estimate(est: dict) -> str:
    ccid = str(est.get("customer_contact_id") or "").strip()
    if not ccid:
        return "—"
    cid = customer_id_for_name(str(est.get("customer") or ""))
    for label, contact_id in customer_contact_select_options(cid):
        if contact_id == ccid:
            return label
    return "—"


def _customer_location_select(
    *,
    customer_name: str,
    session_key: str,
    prev_customer_key: str,
    initial_location_id: str = "",
) -> str:
    cust = str(customer_name or "").strip()
    if st.session_state.get(prev_customer_key) != cust:
        st.session_state.pop(session_key, None)
        st.session_state[prev_customer_key] = cust

    cid = customer_id_for_name(cust)
    if not cust or not cid:
        st.selectbox("Location", ["— Select customer first —"], disabled=True, key=session_key)
        return ""

    pairs = customer_location_select_options(cid)
    if not pairs:
        st.warning("Add a customer location before assigning contacts/jobs.")
        st.selectbox("Location", ["— No locations —"], disabled=True, key=session_key)
        return ""

    labels = ["— Select location —", *[label for label, _ in pairs]]
    ids = ["", *[loc_id for _, loc_id in pairs]]
    if session_key not in st.session_state and initial_location_id:
        try:
            st.session_state[session_key] = ids.index(initial_location_id)
        except ValueError:
            st.session_state[session_key] = 0
    idx = st.selectbox(
        "Location",
        range(len(labels)),
        format_func=lambda i: labels[i],
        key=session_key,
    )
    return str(ids[int(idx)])


def _customer_contact_select(
    *,
    customer_name: str,
    location_id: str,
    session_key: str,
    prev_customer_key: str,
    prev_location_key: str,
    initial_contact_id: str = "",
) -> str:
    cust = str(customer_name or "").strip()
    loc_id = str(location_id or "").strip()
    if st.session_state.get(prev_customer_key) != cust:
        st.session_state.pop(session_key, None)
        st.session_state[prev_customer_key] = cust
    if st.session_state.get(prev_location_key) != loc_id:
        st.session_state.pop(session_key, None)
        st.session_state[prev_location_key] = loc_id

    cid = customer_id_for_name(cust)
    if not cust or not cid:
        st.selectbox("Contact", ["— Select customer first —"], disabled=True, key=session_key)
        return ""
    if not loc_id:
        st.selectbox("Contact", ["— Select location first —"], disabled=True, key=session_key)
        return ""

    pairs = customer_contact_select_options(cid, loc_id)
    if not pairs:
        st.selectbox("Contact", ["— No contacts for this location —"], disabled=True, key=session_key)
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


def _filter_rows(
    rows: list[dict],
    *,
    q: str,
    status: str,
    customer: str,
    created_by: str,
    date_range: tuple[date, date] | None,
) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            r
            for r in out
            if ql in _estimate_number(r).lower()
            or ql in _estimate_project(r).lower()
            or ql in _estimate_customer(r).lower()
            or ql in _estimate_created_by(r).lower()
            or ql in _normalize_estimate_status(r.get("status")).lower()
        ]
    if status and status != "All Statuses":
        out = [r for r in out if _normalize_estimate_status(r.get("status")) == status]
    if customer and customer != "All Customers":
        out = [r for r in out if _estimate_customer(r) == customer]
    if created_by and created_by != "All Created By":
        out = [r for r in out if _estimate_created_by(r) == created_by]
    if date_range and len(date_range) == 2:
        start, end = date_range
        filtered_range: list[dict] = []
        for row in out:
            est_date = _as_date(row.get("estimate_date"))
            if est_date is None or (start <= est_date <= end):
                filtered_range.append(row)
        out = filtered_range
    return out


def _clear_estimates_detail_modal() -> None:
    estimate_ids = st.session_state.get(_ALL_ESTIMATE_IDS_KEY) or []
    _clear_estimate_selection([str(eid) for eid in estimate_ids])
    clear_edit_modes(_MOD)
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
    st.session_state.pop(f"est_edit_location_{eid}", None)
    st.session_state.pop(f"est_edit_cust_prev_{eid}", None)
    st.session_state.pop(f"est_edit_loc_prev_{eid}", None)


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
        cust_name = str(st.session_state.get(f"est_edit_cust_{eid}") or est.get("customer") or "")
        location_id = _customer_location_select(
            customer_name=cust_name,
            session_key=f"est_edit_location_{eid}",
            prev_customer_key=f"est_edit_cust_prev_{eid}",
            initial_location_id=str(est.get("customer_location_id") or ""),
        )
        contact_id = _customer_contact_select(
            customer_name=cust_name,
            location_id=location_id,
            session_key=f"est_edit_contact_{eid}",
            prev_customer_key=f"est_edit_cust_prev_{eid}",
            prev_location_key=f"est_edit_loc_prev_{eid}",
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
                "customer_location_id": location_id or None,
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

    render_modal_edit_button(
        module=_MOD,
        record_key=rk,
        on_edit=lambda: _set_estimate_edit_mode(est),
        key_prefix=f"estimates_modal_{rk}",
    )

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
        exp_col, add_col = st.columns(2, gap="small")
        with exp_col:
            st.button("Export", key="est_export", use_container_width=True)
        with add_col:
            if st.button("+ New Estimate", key="est_new", type="primary", use_container_width=True):
                st.session_state["ips_est_form"] = True

    if st.session_state.get("ips_est_form"):
        with st.expander("New Estimate", expanded=True):
            nc1, nc2 = st.columns(2)
            with nc1:
                st.text_input("Estimate #", key="est_new_num")
                st.text_input("Project name", key="est_new_proj")
                st.selectbox("Customer", customer_filter_options(), key="est_new_cust")
                new_cust = str(st.session_state.get("est_new_cust") or "")
                new_location_id = _customer_location_select(
                    customer_name=new_cust,
                    session_key="est_new_location",
                    prev_customer_key=_NEW_CUST_PREV,
                )
                new_contact_id = _customer_contact_select(
                    customer_name=new_cust,
                    location_id=new_location_id,
                    session_key="est_new_contact",
                    prev_customer_key=_NEW_CUST_PREV,
                    prev_location_key="est_new_loc_prev",
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
                        "customer_location_id": new_location_id or None,
                        "customer_contact_id": new_contact_id or None,
                        "status": st.session_state.get("est_new_status"),
                        "total": st.session_state.get("est_new_total"),
                        "description": st.session_state.get("est_new_notes"),
                    }
                )
                if apply_persist_feedback(ok, msg, clear_keys=("ips_est_form",)):
                    st.rerun()

    created_by_opts = sorted(
        {_estimate_created_by(e) for e in rows if _estimate_created_by(e) != "—"}
    )

    def _filters() -> None:
        c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1, 1, 1, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search estimates...",
                key="est_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "Status",
                _STATUS_FILTER_OPTS,
                key="est_filter_status",
                label_visibility="collapsed",
            )
        with c3:
            st.selectbox(
                "Customer",
                ["All Customers", *customers],
                key="est_filter_customer",
                label_visibility="collapsed",
            )
        with c4:
            st.selectbox(
                "Created By",
                ["All Created By", *created_by_opts],
                key="est_filter_created_by",
                label_visibility="collapsed",
            )
        with c5:
            st.date_input(
                "Date range",
                value=_default_estimate_date_range(),
                key="est_filter_dates",
                label_visibility="collapsed",
            )
        with c6:
            if st.button("Clear", key="est_clear", use_container_width=True):
                st.session_state["est_search"] = ""
                st.session_state["est_filter_status"] = "All Statuses"
                st.session_state["est_filter_customer"] = "All Customers"
                st.session_state["est_filter_created_by"] = "All Created By"
                st.session_state["est_filter_dates"] = _default_estimate_date_range()
                st.rerun()

    layout_filter_bar(_filters)

    date_range = st.session_state.get("est_filter_dates")
    if not isinstance(date_range, tuple) or len(date_range) != 2:
        date_range = _default_estimate_date_range()

    filtered = _filter_rows(
        rows,
        q=str(st.session_state.get("est_search") or "").strip(),
        status=str(st.session_state.get("est_filter_status") or "All Statuses"),
        customer=str(st.session_state.get("est_filter_customer") or "All Customers"),
        created_by=str(st.session_state.get("est_filter_created_by") or "All Created By"),
        date_range=date_range,
    )

    st.caption(f"{len(filtered)} estimate(s)")

    build_modal_cache(filtered, cache_key=_ESTIMATES_CACHE_KEY)
    _render_custom_estimates_table(filtered)

    selected_estimate_id = st.session_state.get(SELECTED_ESTIMATE_KEY)
    if selected_estimate_id and st.session_state.get(SHOW_ESTIMATE_MODAL_KEY):
        _show_estimates_detail_modal()
