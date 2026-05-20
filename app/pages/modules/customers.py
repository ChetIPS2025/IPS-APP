"""Customers module — company directory with sites and contacts."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.layout import render_tab_placeholder
    from app.components.modals import render_record_detail_dialog
    from app.components.status import status_pill_html
    from app.components.tables import render_clickable_table, render_data_table
    from app.components.tabs import render_tabs
    from app.pages.modules._crud import apply_persist_feedback, is_demo_id
    from app.pages.modules._data import (
        estimates_for_customer,
        get_customer,
        jobs_for_customer,
        load_customer_contacts,
        load_customer_locations,
        load_customers,
        persist_customer,
    )
    from app.pages.modules._session import select_key, tab_key
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.layout import render_selected_detail_panel, render_tab_placeholder  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages.modules._data import (  # type: ignore
        estimates_for_customer,
        get_customer,
        jobs_for_customer,
        load_customer_contacts,
        load_customer_locations,
        load_customers,
        persist_customer,
    )
    from pages.modules._session import select_key, tab_key  # type: ignore

_SEL = select_key("customers")
_TAB = tab_key("customers")
_CUSTOMER_TABS = [
    "Overview",
    "Contacts",
    "Jobs",
    "Estimates",
    "Documents",
    "Notes",
    "Activity",
]


def _filter_customers(rows: list[dict], *, q: str, status: str, state: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            c
            for c in out
            if ql in str(c.get("customer_name", "")).lower()
            or ql in str(c.get("city", "")).lower()
            or ql in str(c.get("state", "")).lower()
        ]
    if status and status != "All Statuses":
        out = [c for c in out if str(c.get("status", "")) == status]
    if state and state != "All States":
        out = [c for c in out if str(c.get("state", "")) == state]
    return out


def _render_detail(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    title = str(customer.get("customer_name") or "Customer")
    cname = str(customer.get("customer_name") or "")

    def _tabs() -> None:
        render_tabs(_CUSTOMER_TABS, session_key=_TAB, default="Overview")

    def _body() -> None:
        tab = str(st.session_state.get(_TAB) or "Overview")
        ot = "d" + "iv"
        st.markdown(
            f'<{ot} class="ips-detail-meta-row">'
            f"<span>Status<br>{status_pill_html(str(customer.get('status') or ''))}</span>"
            f"<span>City<br><strong>{html.escape(str(customer.get('city') or '—'))}</strong></span>"
            f"<span>State<br><strong>{html.escape(str(customer.get('state') or '—'))}</strong></span>"
            f"</{ot}>",
            unsafe_allow_html=True,
        )

        if tab == "Overview":
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Company**")
                st.markdown(
                    f'<dl class="ips-info-grid">'
                    f"<dt>Name</dt><dd>{html.escape(cname)}</dd>"
                    f"<dt>Address</dt><dd>{html.escape(str(customer.get('address') or '—'))}</dd>"
                    f"<dt>City / State / ZIP</dt><dd>{html.escape(str(customer.get('city') or '—'))}, "
                    f"{html.escape(str(customer.get('state') or '—'))} {html.escape(str(customer.get('zip') or ''))}</dd>"
                    f"</dl>",
                    unsafe_allow_html=True,
                )
            with c2:
                locs = load_customer_locations(cid)
                contacts = load_customer_contacts(cid)
                st.markdown("**Summary**")
                st.markdown(
                    f'<dl class="ips-info-grid">'
                    f"<dt>Locations</dt><dd>{len(locs)}</dd>"
                    f"<dt>Contacts</dt><dd>{len(contacts)}</dd>"
                    f"<dt>Jobs</dt><dd>{len(jobs_for_customer(cname))}</dd>"
                    f"<dt>Estimates</dt><dd>{len(estimates_for_customer(cname))}</dd>"
                    f"</dl>",
                    unsafe_allow_html=True,
                )
            if not is_demo_id(cid):
                with st.expander("Edit customer", expanded=False):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        st.text_input("Company name", value=cname, key=f"cust_edit_name_{cid}")
                        st.text_input("Address", value=str(customer.get("address") or ""), key=f"cust_edit_addr_{cid}")
                        st.text_input("City", value=str(customer.get("city") or ""), key=f"cust_edit_city_{cid}")
                    with ec2:
                        st.text_input("State", value=str(customer.get("state") or ""), key=f"cust_edit_state_{cid}")
                        st.text_input("ZIP", value=str(customer.get("zip") or ""), key=f"cust_edit_zip_{cid}")
                        st.selectbox("Status", ["Active", "Inactive"], key=f"cust_edit_status_{cid}")
                    st.text_area("Notes", value=str(customer.get("notes") or ""), key=f"cust_edit_notes_{cid}")
                    if st.button("Save customer", key=f"cust_save_{cid}", type="primary"):
                        ok, msg = persist_customer(
                            {
                                "customer_name": st.session_state.get(f"cust_edit_name_{cid}"),
                                "address": st.session_state.get(f"cust_edit_addr_{cid}"),
                                "city": st.session_state.get(f"cust_edit_city_{cid}"),
                                "state": st.session_state.get(f"cust_edit_state_{cid}"),
                                "zip": st.session_state.get(f"cust_edit_zip_{cid}"),
                                "status": st.session_state.get(f"cust_edit_status_{cid}"),
                                "notes": st.session_state.get(f"cust_edit_notes_{cid}"),
                            },
                            row_id=cid,
                        )
                        if apply_persist_feedback(ok, msg):
                            st.rerun()
            return

        if tab == "Contacts":
            contacts = load_customer_contacts(cid)

            def _con_cell(field: str, row: dict) -> str:
                if field == "status":
                    return status_pill_html(str(row.get("status") or ""))
                if field == "contact_name" and row.get("is_primary"):
                    return (
                        f'{html.escape(str(row.get("contact_name") or ""))} '
                        f'<span class="ips-status-pill ips-status-sent" style="font-size:0.62rem;">PRIMARY</span>'
                    )
                return html.escape(str(row.get(field) or "—"))

            if contacts:
                render_data_table(
                    contacts,
                    [
                        ("contact_name", "NAME"),
                        ("title", "TITLE"),
                        ("email", "EMAIL"),
                        ("phone", "PHONE"),
                        ("status", "STATUS"),
                    ],
                    row_id_key="id",
                    selected_id=None,
                    session_select_key="_cust_con",
                    hide_select=True,
                    cell_renderer=_con_cell,
                )
            else:
                st.caption("No contacts on file for this customer.")
            return

        if tab == "Jobs":
            jobs = jobs_for_customer(cname)
            if jobs:

                def _job_cell(field: str, row: dict) -> str:
                    if field == "status":
                        return status_pill_html(str(row.get("status") or ""))
                    if field == "job_number":
                        return f'<span style="color:#2563eb;font-weight:600">{html.escape(str(row.get("job_number") or ""))}</span>'
                    return html.escape(str(row.get(field) or "—"))

                render_data_table(
                    jobs,
                    [
                        ("job_number", "JOB #"),
                        ("job_name", "PROJECT"),
                        ("status", "STATUS"),
                        ("supervisor", "SUPERVISOR"),
                    ],
                    row_id_key="id",
                    selected_id=None,
                    session_select_key="_cust_jobs",
                    hide_select=True,
                    cell_renderer=_job_cell,
                )
            else:
                st.caption("No jobs linked to this customer name yet.")
            return

        if tab == "Estimates":
            ests = estimates_for_customer(cname)
            if ests:

                def _est_cell(field: str, row: dict) -> str:
                    if field == "status":
                        return status_pill_html(str(row.get("status") or ""))
                    return html.escape(str(row.get(field) or "—"))

                render_data_table(
                    ests,
                    [
                        ("estimate_number", "ESTIMATE #"),
                        ("project_name", "PROJECT"),
                        ("status", "STATUS"),
                        ("total", "TOTAL"),
                    ],
                    row_id_key="id",
                    selected_id=None,
                    session_select_key="_cust_est",
                    hide_select=True,
                    cell_renderer=_est_cell,
                )
            else:
                st.caption("No estimates for this customer yet.")
            return

        if tab == "Notes":
            st.text_area("Customer notes", value=str(customer.get("notes") or ""), key=f"cust_notes_view_{cid}", height=120)
            if not is_demo_id(cid) and st.button("Save notes", key=f"cust_notes_save_{cid}", type="primary"):
                ok, msg = persist_customer(
                    {
                        "customer_name": cname,
                        "address": customer.get("address"),
                        "city": customer.get("city"),
                        "state": customer.get("state"),
                        "zip": customer.get("zip"),
                        "status": customer.get("status"),
                        "notes": st.session_state.get(f"cust_notes_view_{cid}"),
                    },
                    row_id=cid,
                )
                apply_persist_feedback(ok, msg)
            elif is_demo_id(cid):
                st.caption("Notes save requires a live customer record.")
            return

        if tab in ("Documents", "Activity"):
            render_tab_placeholder(f"{tab} will connect to Supabase in a later phase.")
            return

        render_tab_placeholder(f"{tab} content will connect in a later phase.")

    render_record_detail_dialog(
        f"{title} — Customer Details",
        module_name="customers",
        session_select_key=_SEL,
        tab_labels=_CUSTOMER_TABS,
        tab_session_key=_TAB,
        tabs_fn=_tabs,
        body_fn=_body,
    )


def render() -> None:
    try:
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
    if not begin_module("customers"):
        return

    ot, ct = "d" + "iv", "/" + "d" + "iv"
    st.markdown(f'<{ot} class="ips-module-page ips-customers-page">', unsafe_allow_html=True)

    all_rows = load_customers()
    states = sorted({str(c.get("state") or "") for c in all_rows if c.get("state")})

    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        render_page_header("Customers", "Manage customer companies, sites, and contacts.")
    with hdr_r:
        st.markdown(f'<{ot} class="ips-header-actions">', unsafe_allow_html=True)
        if st.button("+ New Customer", key="cust_new", type="primary", use_container_width=True):
            st.session_state["ips_cust_form"] = True
        st.markdown(f"</{ct}>", unsafe_allow_html=True)

    if st.session_state.get("ips_cust_form"):
        st.markdown(f'<{ot} class="ips-card ips-form-card">', unsafe_allow_html=True)
        st.markdown('<p class="ips-page-subtitle" style="margin:0 0 0.5rem;font-weight:600;color:#0f172a">New customer</p>', unsafe_allow_html=True)
        nc1, nc2 = st.columns(2)
        with nc1:
            st.text_input("Company name", key="cust_new_name")
            st.text_input("Address", key="cust_new_addr")
            st.text_input("City", key="cust_new_city")
        with nc2:
            st.text_input("State", key="cust_new_state")
            st.text_input("ZIP", key="cust_new_zip")
            st.selectbox("Status", ["Active", "Inactive"], key="cust_new_status")
        st.text_area("Notes", key="cust_new_notes")
        sb1, sb2 = st.columns(2)
        with sb1:
            if st.button("Save customer", key="cust_save_new", type="primary", use_container_width=True):
                ok, msg = persist_customer(
                    {
                        "customer_name": st.session_state.get("cust_new_name"),
                        "address": st.session_state.get("cust_new_addr"),
                        "city": st.session_state.get("cust_new_city"),
                        "state": st.session_state.get("cust_new_state"),
                        "zip": st.session_state.get("cust_new_zip"),
                        "status": st.session_state.get("cust_new_status"),
                        "notes": st.session_state.get("cust_new_notes"),
                    }
                )
                if apply_persist_feedback(ok, msg, clear_keys=("ips_cust_form",)):
                    st.rerun()
        with sb2:
            if st.button("Cancel", key="cust_cancel_new", use_container_width=True):
                st.session_state.pop("ips_cust_form", None)
                st.rerun()
        st.markdown(f"</{ct}>", unsafe_allow_html=True)

    def _filters() -> None:
        c1, c2, c3, c4 = st.columns([2, 1, 1, 0.7])
        with c1:
            st.text_input("Search", placeholder="Search customers…", key="cust_search", label_visibility="collapsed")
        with c2:
            st.selectbox(
                "Status",
                ["All Statuses", "Active", "Inactive"],
                key="cust_filter_status",
                label_visibility="collapsed",
            )
        with c3:
            st.selectbox(
                "State",
                ["All States", *states],
                key="cust_filter_state",
                label_visibility="collapsed",
            )
        with c4:
            if st.button("Clear", key="cust_clear", use_container_width=True):
                st.session_state["cust_search"] = ""
                st.session_state["cust_filter_status"] = "All Statuses"
                st.session_state["cust_filter_state"] = "All States"
                st.rerun()

    layout_filter_bar(_filters)

    filtered = _filter_customers(
        all_rows,
        q=str(st.session_state.get("cust_search") or "").strip(),
        status=str(st.session_state.get("cust_filter_status") or "All Statuses"),
        state=str(st.session_state.get("cust_filter_state") or "All States"),
    )

    selected_id = str(st.session_state.get(_SEL) or "")
    if selected_id and not any(str(c.get("id")) == selected_id for c in filtered):
        st.session_state.pop(_SEL, None)
        selected_id = ""

    def _plain_cell(field: str, row: dict) -> str:
        return str(row.get(field) or "—")

    sel = render_clickable_table(
        filtered,
        [
            ("customer_name", "CUSTOMER"),
            ("city", "CITY"),
            ("state", "STATE"),
            ("zip", "ZIP"),
            ("status", "STATUS"),
        ],
        "customers_list",
        row_id_key="id",
        session_select_key=_SEL,
        selected_id=selected_id or None,
        plain_cell=_plain_cell,
    )

    if sel:
        cust = get_customer(sel) or next((c for c in filtered if str(c.get("id")) == sel), None)
        if cust:
            _render_detail(cust)

    st.markdown(f"</{ct}>", unsafe_allow_html=True)
