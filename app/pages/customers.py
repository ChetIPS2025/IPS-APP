"""Customers module — company directory with sites and contacts."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
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
        render_modal_edit_button,
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
    from app.components.status import status_pill_html
    from app.components.tables import render_data_table
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._data import estimates_for_customer, jobs_for_customer
    from app.pages._core._session import select_key
    from app.services.customers_service import (
        CONTACT_ROLE_TYPES,
        LOCATION_TYPES,
        create_customer,
        create_customer_contact,
        create_customer_location,
        get_customer,
        get_customer_contact,
        get_customer_contacts,
        get_customer_location,
        get_customer_locations,
        get_customers,
        update_customer,
        update_customer_contact,
        update_customer_location,
    )
    from app.styles import inject_customers_module_css
except ImportError:
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
        render_modal_edit_button,
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
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._data import estimates_for_customer, jobs_for_customer  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from services.customers_service import (  # type: ignore
        CONTACT_ROLE_TYPES,
        LOCATION_TYPES,
        create_customer,
        create_customer_contact,
        create_customer_location,
        get_customer,
        get_customer_contact,
        get_customer_contacts,
        get_customer_location,
        get_customer_locations,
        get_customers,
        update_customer,
        update_customer_contact,
        update_customer_location,
    )
    from styles import inject_customers_module_css  # type: ignore

_SEL = select_key("customers")
_LOC_SEL = select_key("customer_locations")
_CT_SEL = select_key("customer_contacts")

_MOD = "customers"
_LOC_MOD = "customer_locations"
_CT_MOD = "customer_contacts"

_CUSTOMERS_TABLE_KEY = "customers_list"
_LOCATIONS_TABLE_KEY = "customer_locations_list"
_CONTACTS_TABLE_KEY = "customer_contacts_list"

_CUSTOMERS_MODAL_KEY = "ips_customers_detail_modal_id"
_LOCATION_MODAL_KEY = "ips_customer_location_detail_modal_id"
_CONTACT_MODAL_KEY = "ips_customer_contact_detail_modal_id"

_CUSTOMERS_CACHE_KEY = "_ips_customers_modal_by_id"
_LOCATIONS_CACHE_KEY = "_ips_customer_locations_modal_by_id"
_CONTACTS_CACHE_KEY = "_ips_customer_contacts_modal_by_id"

_CUSTOMER_TABS = [
    "Overview",
    "Locations",
    "Contacts",
    "Jobs",
    "Estimates",
    "Documents",
    "Notes",
    "Activity",
]

_LOCATION_TABS = [
    "Overview",
    "Contacts",
    "Jobs",
    "Estimates",
    "Documents",
    "Notes",
    "Activity",
]

_CONTACT_TABS = [
    "Overview",
    "Location",
    "Linked Jobs",
    "Linked Estimates",
    "Notes",
    "Activity",
]

_CLOSED_JOB_STATUSES = frozenset({"completed", "complete", "closed", "cancelled", "canceled"})
_CLOSED_EST_STATUSES = frozenset({"awarded", "completed", "complete", "closed", "cancelled", "canceled"})


def _service_feedback(result: Any, *, success: str) -> tuple[bool, str]:
    try:
        from app.services.repository import user_facing_error
    except ImportError:
        from services.repository import user_facing_error  # type: ignore
    err = user_facing_error(result)
    if err:
        return False, err
    return True, success


def _yes_dash(value: object) -> str:
    return "Yes" if bool(value) else "—"


def _enrich_list_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        cname = str(row.get("customer_name") or row.get("company_name") or "")
        jobs = jobs_for_customer(cname)
        ests = estimates_for_customer(cname)
        enriched = dict(row)
        enriched["open_jobs"] = sum(
            1 for j in jobs if str(j.get("status") or "").strip().lower() not in _CLOSED_JOB_STATUSES
        )
        enriched["open_estimates"] = sum(
            1 for e in ests if str(e.get("status") or "").strip().lower() not in _CLOSED_EST_STATUSES
        )
        out.append(enriched)
    return out


def _filter_customers(rows: list[dict], *, q: str, status: str, state: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            c
            for c in out
            if ql in str(c.get("customer_name") or c.get("company_name") or "").lower()
            or ql in str(c.get("primary_location_city") or c.get("city") or "").lower()
            or ql in str(c.get("primary_location_state") or c.get("state") or "").lower()
            or ql in str(c.get("primary_location_name") or "").lower()
        ]
    if status and status != "All Statuses":
        out = [c for c in out if str(c.get("status", "")) == status]
    if state and state != "All States":
        out = [
            c
            for c in out
            if str(c.get("primary_location_state") or c.get("state") or "") == state
        ]
    return out


def _location_name_map(locations: list[dict]) -> dict[str, dict]:
    return {str(loc.get("id") or "").strip(): loc for loc in locations if str(loc.get("id") or "").strip()}


def _contacts_with_location_names(contacts: list[dict], locations: list[dict]) -> list[dict]:
    loc_by_id = _location_name_map(locations)
    rows: list[dict] = []
    for contact in contacts:
        row = dict(contact)
        lid = str(contact.get("location_id") or contact.get("customer_location_id") or "").strip()
        loc = loc_by_id.get(lid, {})
        row["location_name"] = str(loc.get("location_name") or loc.get("site_name") or "—")
        rows.append(row)
    return rows


def _clear_customers_detail_modal() -> None:
    clear_record_modal(
        table_key=_CUSTOMERS_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_CUSTOMERS_MODAL_KEY,
        module=_MOD,
    )


def _clear_location_detail_modal() -> None:
    clear_record_modal(
        table_key=_LOCATIONS_TABLE_KEY,
        session_select_key=_LOC_SEL,
        modal_key=_LOCATION_MODAL_KEY,
        module=_LOC_MOD,
    )


def _clear_contact_detail_modal() -> None:
    clear_record_modal(
        table_key=_CONTACTS_TABLE_KEY,
        session_select_key=_CT_SEL,
        modal_key=_CONTACT_MODAL_KEY,
        module=_CT_MOD,
    )


def _open_customers_detail_modal(customer_id: str, customer: dict | None = None) -> None:
    open_record_modal(
        customer_id,
        customer,
        session_select_key=_SEL,
        modal_key=_CUSTOMERS_MODAL_KEY,
        module=_MOD,
        id_fields=("id", "customer_name"),
    )


def _open_location_detail_modal(location_id: str, location: dict | None = None) -> None:
    open_record_modal(
        location_id,
        location,
        session_select_key=_LOC_SEL,
        modal_key=_LOCATION_MODAL_KEY,
        module=_LOC_MOD,
        id_fields=("id", "location_name", "site_name"),
    )


def _open_contact_detail_modal(contact_id: str, contact: dict | None = None) -> None:
    open_record_modal(
        contact_id,
        contact,
        session_select_key=_CT_SEL,
        modal_key=_CONTACT_MODAL_KEY,
        module=_CT_MOD,
        id_fields=("id", "full_name", "contact_name"),
    )


def _list_display_cell(field: str, row: dict) -> str:
    if field == "status":
        return safe_value(row.get("status"))
    if field in ("is_primary", "is_billing", "is_shipping"):
        return _yes_dash(row.get(field))
    val = row.get(field)
    return str(val).strip() if val is not None and str(val).strip() else "—"


def _location_label(loc: dict) -> str:
    name = str(loc.get("location_name") or loc.get("site_name") or "—")
    city = str(loc.get("city") or "").strip()
    state = str(loc.get("state") or "").strip()
    tail = ", ".join(part for part in (city, state) if part)
    return f"{name} — {tail}" if tail else name


def _jobs_table(
    jobs: list[dict],
    *,
    session_key: str,
    location_id: str = "",
) -> None:
    if location_id:
        jobs = [
            j
            for j in jobs
            if str(j.get("customer_location_id") or j.get("location_id") or "").strip() == location_id
            or str(j.get("location") or "").strip() == location_id
        ]
    if not jobs:
        st.caption("No jobs linked yet.")
        return

    columns: list[tuple[str, str]] = [
        ("job_number", "JOB #"),
        ("job_name", "PROJECT"),
    ]
    if any(j.get("location") or j.get("customer_location") or j.get("site_name") for j in jobs):
        columns.append(("location", "LOCATION"))
    if any(j.get("contact_name") or j.get("customer_contact") for j in jobs):
        columns.append(("contact_name", "CONTACT"))
    columns.extend([("status", "STATUS"), ("supervisor", "SUPERVISOR")])

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "job_number":
            return (
                f'<span style="color:#2563eb;font-weight:600">'
                f'{html.escape(str(row.get("job_number") or ""))}</span>'
            )
        if field == "location":
            val = row.get("location") or row.get("customer_location") or row.get("site_name")
            return html.escape(str(val or "—"))
        if field == "contact_name":
            val = row.get("contact_name") or row.get("customer_contact")
            return html.escape(str(val or "—"))
        return html.escape(str(row.get(field) or "—"))

    render_data_table(
        jobs,
        columns,
        row_id_key="id",
        selected_id=None,
        session_select_key=session_key,
        hide_select=True,
        cell_renderer=_cell,
    )


def _estimates_table(
    estimates: list[dict],
    *,
    session_key: str,
    location_id: str = "",
) -> None:
    if location_id:
        estimates = [
            e
            for e in estimates
            if str(e.get("customer_location_id") or e.get("location_id") or "").strip() == location_id
            or str(e.get("location") or "").strip() == location_id
        ]
    if not estimates:
        st.caption("No estimates for this scope yet.")
        return

    columns: list[tuple[str, str]] = [
        ("estimate_number", "ESTIMATE #"),
        ("project_name", "PROJECT"),
    ]
    if any(e.get("location") or e.get("customer_location") or e.get("site_name") for e in estimates):
        columns.append(("location", "LOCATION"))
    if any(e.get("contact_name") or e.get("customer_contact") for e in estimates):
        columns.append(("contact_name", "CONTACT"))
    columns.extend([("status", "STATUS"), ("total", "TOTAL")])

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "location":
            val = row.get("location") or row.get("customer_location") or row.get("site_name")
            return html.escape(str(val or "—"))
        if field == "contact_name":
            val = row.get("contact_name") or row.get("customer_contact")
            return html.escape(str(val or "—"))
        return html.escape(str(row.get(field) or "—"))

    render_data_table(
        estimates,
        columns,
        row_id_key="id",
        selected_id=None,
        session_select_key=session_key,
        hide_select=True,
        cell_renderer=_cell,
    )


# --- Customer modal ---


def _seed_customer_edit_form(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    rk = record_session_key(customer, "id", "customer_name")
    st.session_state[f"cust_edit_company_{rk}"] = str(customer.get("company_name") or customer.get("customer_name") or "")
    st.session_state[f"cust_edit_number_{rk}"] = str(customer.get("customer_number") or "")
    st.session_state[f"cust_edit_website_{rk}"] = str(customer.get("website") or "")
    st.session_state[f"cust_edit_main_phone_{rk}"] = str(customer.get("main_phone") or "")
    st.session_state[f"cust_edit_main_email_{rk}"] = str(customer.get("main_email") or "")
    st.session_state[f"cust_edit_billing_email_{rk}"] = str(customer.get("billing_email") or "")
    st.session_state[f"cust_edit_status_{rk}"] = str(customer.get("status") or "Active")
    st.session_state[f"cust_edit_notes_{rk}"] = str(customer.get("notes") or "")
    st.session_state[f"cust_edit_addr_{rk}"] = str(customer.get("address") or "")
    st.session_state[f"cust_edit_city_{rk}"] = str(customer.get("city") or "")
    st.session_state[f"cust_edit_state_{rk}"] = str(customer.get("state") or "")
    st.session_state[f"cust_edit_zip_{rk}"] = str(customer.get("zip") or "")


def _set_customer_edit_mode(customer: dict) -> None:
    rk = record_session_key(customer, "id", "customer_name")
    set_edit_mode(_MOD, rk)
    _seed_customer_edit_form(customer)


def _render_customer_edit_form(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    rk = record_session_key(customer, "id", "customer_name")
    if f"cust_edit_company_{rk}" not in st.session_state:
        _seed_customer_edit_form(customer)

    render_edit_form_header("Edit Customer")
    if is_demo_id(cid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    ec1, ec2 = st.columns(2)
    with ec1:
        st.text_input("Company name", key=f"cust_edit_company_{rk}")
        st.text_input("Customer #", key=f"cust_edit_number_{rk}")
        st.text_input("Website", key=f"cust_edit_website_{rk}")
        st.text_input("Main phone", key=f"cust_edit_main_phone_{rk}")
    with ec2:
        st.text_input("Main email", key=f"cust_edit_main_email_{rk}")
        st.text_input("Billing email", key=f"cust_edit_billing_email_{rk}")
        st.selectbox("Status", ["Active", "Inactive"], key=f"cust_edit_status_{rk}")
    st.text_area("Notes", key=f"cust_edit_notes_{rk}", height=90)

    with st.expander("Legacy address (optional)", expanded=False):
        lc1, lc2 = st.columns(2)
        with lc1:
            st.text_input("Address", key=f"cust_edit_addr_{rk}")
            st.text_input("City", key=f"cust_edit_city_{rk}")
        with lc2:
            st.text_input("State", key=f"cust_edit_state_{rk}")
            st.text_input("ZIP", key=f"cust_edit_zip_{rk}")

    cancelled, saved = render_save_cancel_actions(
        module=_MOD,
        record_key=rk,
        cancel_key=f"cust_edit_cancel_{rk}",
        save_key=f"cust_edit_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved:
        payload = {
            "company_name": st.session_state.get(f"cust_edit_company_{rk}"),
            "customer_name": st.session_state.get(f"cust_edit_company_{rk}"),
            "customer_number": st.session_state.get(f"cust_edit_number_{rk}"),
            "website": st.session_state.get(f"cust_edit_website_{rk}"),
            "main_phone": st.session_state.get(f"cust_edit_main_phone_{rk}"),
            "main_email": st.session_state.get(f"cust_edit_main_email_{rk}"),
            "billing_email": st.session_state.get(f"cust_edit_billing_email_{rk}"),
            "status": st.session_state.get(f"cust_edit_status_{rk}"),
            "notes": st.session_state.get(f"cust_edit_notes_{rk}"),
            "address": st.session_state.get(f"cust_edit_addr_{rk}"),
            "city": st.session_state.get(f"cust_edit_city_{rk}"),
            "state": st.session_state.get(f"cust_edit_state_{rk}"),
            "zip": st.session_state.get(f"cust_edit_zip_{rk}"),
        }
        ok, msg = _service_feedback(update_customer(cid, payload), success="Customer saved.")
        if ok:
            set_view_mode(_MOD, rk)
            st.success(msg)
            st.rerun()
        st.error(msg or "Could not save customer.")


def _render_add_location_form(customer: dict, *, demo: bool) -> None:
    cid = str(customer.get("id") or "")
    pk = f"cust_new_loc_{cid}"
    if demo:
        st.caption("Add locations after saving this customer to Supabase.")
        return
    with st.expander("Add Location", expanded=bool(st.session_state.get(f"{pk}_open"))):
        lc1, lc2 = st.columns(2)
        with lc1:
            st.text_input("Location name", key=f"{pk}_name")
            st.selectbox("Type", LOCATION_TYPES, key=f"{pk}_type")
            st.text_input("Address line 1", key=f"{pk}_addr1")
            st.text_input("City", key=f"{pk}_city")
        with lc2:
            st.text_input("State", key=f"{pk}_state")
            st.text_input("ZIP", key=f"{pk}_zip")
            st.text_input("Phone", key=f"{pk}_phone")
            st.selectbox("Status", ["Active", "Inactive"], index=0, key=f"{pk}_status")
        st.text_input("Email", key=f"{pk}_email")
        flags = st.columns(3)
        with flags[0]:
            st.checkbox("Primary", key=f"{pk}_primary")
        with flags[1]:
            st.checkbox("Billing", key=f"{pk}_billing")
        with flags[2]:
            st.checkbox("Shipping", key=f"{pk}_shipping")
        st.text_area("Notes", key=f"{pk}_notes", height=70)
        sb1, sb2 = st.columns(2)
        with sb1:
            save = st.button("Save location", key=f"{pk}_save", type="primary", use_container_width=True)
        with sb2:
            if st.button("Cancel", key=f"{pk}_cancel", use_container_width=True):
                st.session_state.pop(f"{pk}_open", None)
                st.rerun()
        if save:
            payload = {
                "location_name": st.session_state.get(f"{pk}_name"),
                "location_type": st.session_state.get(f"{pk}_type"),
                "address_line_1": st.session_state.get(f"{pk}_addr1"),
                "city": st.session_state.get(f"{pk}_city"),
                "state": st.session_state.get(f"{pk}_state"),
                "zip": st.session_state.get(f"{pk}_zip"),
                "phone": st.session_state.get(f"{pk}_phone"),
                "email": st.session_state.get(f"{pk}_email"),
                "is_primary": st.session_state.get(f"{pk}_primary"),
                "is_billing": st.session_state.get(f"{pk}_billing"),
                "is_shipping": st.session_state.get(f"{pk}_shipping"),
                "status": st.session_state.get(f"{pk}_status"),
                "notes": st.session_state.get(f"{pk}_notes"),
            }
            ok, msg = _service_feedback(
                create_customer_location(cid, payload),
                success="Location added.",
            )
            if apply_persist_feedback(ok, msg, clear_keys=(f"{pk}_open",)):
                st.rerun()


def _render_customer_locations_tab(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    demo = is_demo_id(cid)
    locations = get_customer_locations(cid)
    _render_add_location_form(customer, demo=demo)

    if not locations:
        st.caption("No locations on file for this customer.")
        return

    build_modal_cache(locations, cache_key=_LOCATIONS_CACHE_KEY)
    render_clickable_table(
        locations,
        [
            ("location_name", "LOCATION"),
            ("location_type", "TYPE"),
            ("city", "CITY"),
            ("state", "STATE"),
            ("phone", "PHONE"),
            ("is_primary", "PRIMARY"),
            ("is_billing", "BILLING"),
            ("is_shipping", "SHIPPING"),
            ("status", "STATUS"),
        ],
        _LOCATIONS_TABLE_KEY,
        row_id_key="id",
        session_select_key=_LOC_SEL,
        format_cell=_list_display_cell,
        click_caption=f"{len(locations)} location(s) · Click a row for location details.",
        on_row_selected=_open_location_detail_modal,
    )
    show_modal_if_pending(_LOCATION_MODAL_KEY, _show_location_detail_modal)


def _render_add_contact_form(customer: dict, *, locations: list[dict], demo: bool) -> None:
    cid = str(customer.get("id") or "")
    pk = f"cust_new_ct_{cid}"
    if demo:
        st.caption("Add contacts after saving this customer to Supabase.")
        return

    loc_opts = [( _location_label(loc), str(loc.get("id") or "")) for loc in locations if str(loc.get("id") or "")]
    if not loc_opts:
        st.caption("Add a location before creating contacts.")
        return

    with st.expander("Add Contact", expanded=bool(st.session_state.get(f"{pk}_open"))):
        labels = [label for label, _ in loc_opts]
        ids = [lid for _, lid in loc_opts]
        if f"{pk}_loc" not in st.session_state:
            st.session_state[f"{pk}_loc"] = 0
        loc_idx = st.selectbox(
            "Location",
            range(len(labels)),
            format_func=lambda i: labels[i],
            key=f"{pk}_loc",
        )
        loc_id = ids[int(loc_idx)]

        nc1, nc2 = st.columns(2)
        with nc1:
            st.text_input("Full name", key=f"{pk}_name")
            st.text_input("Title", key=f"{pk}_title")
            st.selectbox("Role", CONTACT_ROLE_TYPES, key=f"{pk}_role")
            st.text_input("Email", key=f"{pk}_email")
        with nc2:
            st.text_input("Phone", key=f"{pk}_phone")
            st.text_input("Mobile", key=f"{pk}_mobile")
            st.selectbox("Status", ["Active", "Inactive"], index=0, key=f"{pk}_status")
            st.checkbox("Primary for location", key=f"{pk}_primary")
        st.text_area("Notes", key=f"{pk}_notes", height=70)
        sb1, sb2 = st.columns(2)
        with sb1:
            save = st.button("Save contact", key=f"{pk}_save", type="primary", use_container_width=True)
        with sb2:
            if st.button("Cancel", key=f"{pk}_cancel", use_container_width=True):
                st.session_state.pop(f"{pk}_open", None)
                st.rerun()
        if save:
            payload = {
                "full_name": st.session_state.get(f"{pk}_name"),
                "contact_name": st.session_state.get(f"{pk}_name"),
                "title": st.session_state.get(f"{pk}_title"),
                "role_type": st.session_state.get(f"{pk}_role"),
                "email": st.session_state.get(f"{pk}_email"),
                "phone": st.session_state.get(f"{pk}_phone"),
                "mobile": st.session_state.get(f"{pk}_mobile"),
                "status": st.session_state.get(f"{pk}_status"),
                "is_primary": st.session_state.get(f"{pk}_primary"),
                "notes": st.session_state.get(f"{pk}_notes"),
            }
            ok, msg = _service_feedback(
                create_customer_contact(cid, loc_id, payload),
                success="Contact added.",
            )
            if apply_persist_feedback(ok, msg, clear_keys=(f"{pk}_open",)):
                st.rerun()


def _render_customer_contacts_tab(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    demo = is_demo_id(cid)
    locations = get_customer_locations(cid)
    all_contacts = get_customer_contacts(cid)
    enriched = _contacts_with_location_names(all_contacts, locations)

    filter_labels = ["All Locations"]
    filter_ids = [""]
    for loc in locations:
        lid = str(loc.get("id") or "").strip()
        if lid:
            filter_labels.append(_location_label(loc))
            filter_ids.append(lid)

    pick_key = f"cust_ct_filter_{cid}"
    if pick_key not in st.session_state:
        st.session_state[pick_key] = 0
    pick = st.selectbox(
        "Filter by location",
        range(len(filter_labels)),
        format_func=lambda i: filter_labels[i],
        key=pick_key,
    )
    filter_loc = filter_ids[int(pick)]
    if filter_loc:
        contacts = [c for c in enriched if str(c.get("location_id") or c.get("customer_location_id") or "") == filter_loc]
    else:
        contacts = enriched

    _render_add_contact_form(customer, locations=locations, demo=demo)

    if not contacts:
        st.caption("No contacts match this filter.")
        return

    build_modal_cache(contacts, cache_key=_CONTACTS_CACHE_KEY)
    render_clickable_table(
        contacts,
        [
            ("full_name", "NAME"),
            ("title", "TITLE"),
            ("location_name", "LOCATION"),
            ("role_type", "ROLE"),
            ("email", "EMAIL"),
            ("phone", "PHONE"),
            ("mobile", "MOBILE"),
            ("is_primary", "PRIMARY"),
            ("status", "STATUS"),
        ],
        _CONTACTS_TABLE_KEY,
        row_id_key="id",
        session_select_key=_CT_SEL,
        format_cell=_list_display_cell,
        click_caption=f"{len(contacts)} contact(s) · Click a row for contact details.",
        on_row_selected=_open_contact_detail_modal,
    )
    show_modal_if_pending(_CONTACT_MODAL_KEY, _show_contact_detail_modal)


def _render_customer_detail_tabs(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    cname = str(customer.get("customer_name") or customer.get("company_name") or "")

    (
        tab_overview,
        tab_locations,
        tab_contacts,
        tab_jobs,
        tab_estimates,
        tab_documents,
        tab_notes,
        tab_activity,
    ) = st.tabs(_CUSTOMER_TABS)

    with tab_overview:
        status = safe_value(customer.get("status"))
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Company', customer.get('company_name') or cname)}"
            f"{detail_field_html('Customer #', customer.get('customer_number'))}"
            f"{detail_field_html('Website', customer.get('website'))}"
            f"{detail_field_html('Main Phone', customer.get('main_phone'))}"
            f"{detail_field_html('Main Email', customer.get('main_email'))}"
            f"{detail_field_html('Billing Email', customer.get('billing_email'))}"
            f'{detail_field_html("Status", status, html_value=modal_status_pill_html(status))}'
            f"</div>"
        )
        st.markdown(dialog_card_html("Company", overview_html), unsafe_allow_html=True)
        legacy = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Address', customer.get('address'))}"
            f"{detail_field_html('City', customer.get('city'))}"
            f"{detail_field_html('State', customer.get('state'))}"
            f"{detail_field_html('ZIP', customer.get('zip'))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Legacy Address", legacy), unsafe_allow_html=True)

    with tab_locations:
        _render_customer_locations_tab(customer)

    with tab_contacts:
        _render_customer_contacts_tab(customer)

    with tab_jobs:
        _jobs_table(jobs_for_customer(cname), session_key=f"_cust_jobs_{cid}")

    with tab_estimates:
        _estimates_table(estimates_for_customer(cname), session_key=f"_cust_est_{cid}")

    with tab_documents:
        placeholder_html("Customer documents will appear here when connected to Supabase.")

    with tab_notes:
        notes_text = safe_value(customer.get("notes"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Customer activity history will appear here when connected to Supabase.")


def render_customer_detail_dialog(customer: dict) -> None:
    rk = record_session_key(customer, "id", "customer_name")
    cname = safe_value(customer.get("customer_name") or customer.get("company_name"))
    status = safe_value(customer.get("status"))
    cid = str(customer.get("id") or "")

    render_modal_shell()
    render_modal_header(title=cname, subtitle="Customer", status=status)

    render_modal_edit_button(
        module=_MOD,
        record_key=rk,
        on_edit=lambda: _set_customer_edit_mode(customer),
        key_prefix=f"customers_modal_{rk}",
    )

    render_modal_meta_grid(
        [
            ("Primary Location", customer.get("primary_location_name")),
            ("City / State", f"{safe_value(customer.get('primary_location_city'), '')} / {safe_value(customer.get('primary_location_state'), '')}".strip(" /")),
            ("Locations", customer.get("location_count", 0)),
            ("Contacts", customer.get("contact_count", 0)),
            ("Open Jobs", customer.get("open_jobs", 0)),
            ("Open Estimates", customer.get("open_estimates", 0)),
        ]
    )

    if is_edit_mode(_MOD, rk):
        _render_customer_edit_form(customer)
    else:
        _render_customer_detail_tabs(customer)


@st.dialog("Customer Details", width="large", on_dismiss=_clear_customers_detail_modal)
def _show_customers_detail_modal() -> None:
    customer = get_modal_record(
        cache_key=_CUSTOMERS_CACHE_KEY,
        modal_key=_CUSTOMERS_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not customer:
        sel = str(st.session_state.get(_CUSTOMERS_MODAL_KEY) or st.session_state.get(_SEL) or "").strip()
        customer = get_customer(sel) if sel else None
    if not customer:
        render_missing_record(_clear_customers_detail_modal, close_key="customers_modal_missing_close")
        return
    render_customer_detail_dialog(customer)


# --- Location modal ---


def _seed_location_edit_form(location: dict) -> None:
    rk = record_session_key(location, "id", "location_name", "site_name")
    st.session_state[f"loc_edit_name_{rk}"] = str(location.get("location_name") or location.get("site_name") or "")
    st.session_state[f"loc_edit_type_{rk}"] = str(location.get("location_type") or "Other")
    st.session_state[f"loc_edit_addr1_{rk}"] = str(location.get("address_line_1") or location.get("address") or "")
    st.session_state[f"loc_edit_addr2_{rk}"] = str(location.get("address_line_2") or "")
    st.session_state[f"loc_edit_city_{rk}"] = str(location.get("city") or "")
    st.session_state[f"loc_edit_state_{rk}"] = str(location.get("state") or "")
    st.session_state[f"loc_edit_zip_{rk}"] = str(location.get("zip") or "")
    st.session_state[f"loc_edit_country_{rk}"] = str(location.get("country") or "USA")
    st.session_state[f"loc_edit_phone_{rk}"] = str(location.get("phone") or "")
    st.session_state[f"loc_edit_email_{rk}"] = str(location.get("email") or "")
    st.session_state[f"loc_edit_primary_{rk}"] = bool(location.get("is_primary"))
    st.session_state[f"loc_edit_billing_{rk}"] = bool(location.get("is_billing"))
    st.session_state[f"loc_edit_shipping_{rk}"] = bool(location.get("is_shipping"))
    st.session_state[f"loc_edit_status_{rk}"] = str(location.get("status") or "Active")
    st.session_state[f"loc_edit_notes_{rk}"] = str(location.get("notes") or "")


def _set_location_edit_mode(location: dict) -> None:
    rk = record_session_key(location, "id", "location_name", "site_name")
    set_edit_mode(_LOC_MOD, rk)
    _seed_location_edit_form(location)


def _render_location_edit_form(location: dict) -> None:
    lid = str(location.get("id") or "")
    cid = str(location.get("customer_id") or "")
    rk = record_session_key(location, "id", "location_name", "site_name")
    if f"loc_edit_name_{rk}" not in st.session_state:
        _seed_location_edit_form(location)

    render_edit_form_header("Edit Location")
    if is_demo_id(lid) or is_demo_id(cid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    lc1, lc2 = st.columns(2)
    with lc1:
        st.text_input("Location name", key=f"loc_edit_name_{rk}")
        st.selectbox("Type", LOCATION_TYPES, key=f"loc_edit_type_{rk}")
        st.text_input("Address line 1", key=f"loc_edit_addr1_{rk}")
        st.text_input("Address line 2", key=f"loc_edit_addr2_{rk}")
        st.text_input("City", key=f"loc_edit_city_{rk}")
    with lc2:
        st.text_input("State", key=f"loc_edit_state_{rk}")
        st.text_input("ZIP", key=f"loc_edit_zip_{rk}")
        st.text_input("Country", key=f"loc_edit_country_{rk}")
        st.text_input("Phone", key=f"loc_edit_phone_{rk}")
        st.text_input("Email", key=f"loc_edit_email_{rk}")
        st.selectbox("Status", ["Active", "Inactive"], key=f"loc_edit_status_{rk}")
    flags = st.columns(3)
    with flags[0]:
        st.checkbox("Primary", key=f"loc_edit_primary_{rk}")
    with flags[1]:
        st.checkbox("Billing", key=f"loc_edit_billing_{rk}")
    with flags[2]:
        st.checkbox("Shipping", key=f"loc_edit_shipping_{rk}")
    st.text_area("Notes", key=f"loc_edit_notes_{rk}", height=90)

    cancelled, saved = render_save_cancel_actions(
        module=_LOC_MOD,
        record_key=rk,
        cancel_key=f"loc_edit_cancel_{rk}",
        save_key=f"loc_edit_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved:
        payload = {
            "customer_id": cid,
            "location_name": st.session_state.get(f"loc_edit_name_{rk}"),
            "location_type": st.session_state.get(f"loc_edit_type_{rk}"),
            "address_line_1": st.session_state.get(f"loc_edit_addr1_{rk}"),
            "address_line_2": st.session_state.get(f"loc_edit_addr2_{rk}"),
            "city": st.session_state.get(f"loc_edit_city_{rk}"),
            "state": st.session_state.get(f"loc_edit_state_{rk}"),
            "zip": st.session_state.get(f"loc_edit_zip_{rk}"),
            "country": st.session_state.get(f"loc_edit_country_{rk}"),
            "phone": st.session_state.get(f"loc_edit_phone_{rk}"),
            "email": st.session_state.get(f"loc_edit_email_{rk}"),
            "is_primary": st.session_state.get(f"loc_edit_primary_{rk}"),
            "is_billing": st.session_state.get(f"loc_edit_billing_{rk}"),
            "is_shipping": st.session_state.get(f"loc_edit_shipping_{rk}"),
            "status": st.session_state.get(f"loc_edit_status_{rk}"),
            "notes": st.session_state.get(f"loc_edit_notes_{rk}"),
        }
        ok, msg = _service_feedback(update_customer_location(lid, payload), success="Location saved.")
        if ok:
            set_view_mode(_LOC_MOD, rk)
            st.success(msg)
            st.rerun()
        st.error(msg or "Could not save location.")


def _render_location_detail_tabs(location: dict, customer: dict | None) -> None:
    lid = str(location.get("id") or "")
    cid = str(location.get("customer_id") or "")
    cname = str((customer or {}).get("customer_name") or (customer or {}).get("company_name") or "")
    contacts = _contacts_with_location_names(
        get_customer_contacts(cid, location_id=lid),
        get_customer_locations(cid),
    )

    (
        tab_overview,
        tab_contacts,
        tab_jobs,
        tab_estimates,
        tab_documents,
        tab_notes,
        tab_activity,
    ) = st.tabs(_LOCATION_TABS)

    with tab_overview:
        status = safe_value(location.get("status"))
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Location', location.get('location_name') or location.get('site_name'))}"
            f"{detail_field_html('Type', location.get('location_type'))}"
            f"{detail_field_html('Address', location.get('address_line_1') or location.get('address'))}"
            f"{detail_field_html('Address 2', location.get('address_line_2'))}"
            f"{detail_field_html('City', location.get('city'))}"
            f"{detail_field_html('State', location.get('state'))}"
            f"{detail_field_html('ZIP', location.get('zip'))}"
            f"{detail_field_html('Country', location.get('country'))}"
            f"{detail_field_html('Phone', location.get('phone'))}"
            f"{detail_field_html('Email', location.get('email'))}"
            f"{detail_field_html('Primary', _yes_dash(location.get('is_primary')))}"
            f"{detail_field_html('Billing', _yes_dash(location.get('is_billing')))}"
            f"{detail_field_html('Shipping', _yes_dash(location.get('is_shipping')))}"
            f'{detail_field_html("Status", status, html_value=modal_status_pill_html(status))}'
            f"</div>"
        )
        st.markdown(dialog_card_html("Site", overview_html), unsafe_allow_html=True)

    with tab_contacts:
        if contacts:
            build_modal_cache(contacts, cache_key=_CONTACTS_CACHE_KEY)
            render_clickable_table(
                contacts,
                [
                    ("full_name", "NAME"),
                    ("title", "TITLE"),
                    ("role_type", "ROLE"),
                    ("email", "EMAIL"),
                    ("phone", "PHONE"),
                    ("is_primary", "PRIMARY"),
                    ("status", "STATUS"),
                ],
                _CONTACTS_TABLE_KEY,
                row_id_key="id",
                session_select_key=_CT_SEL,
                format_cell=_list_display_cell,
                click_caption=f"{len(contacts)} contact(s) at this location.",
                on_row_selected=_open_contact_detail_modal,
            )
            show_modal_if_pending(_CONTACT_MODAL_KEY, _show_contact_detail_modal)
        else:
            st.caption("No contacts assigned to this location.")

    with tab_jobs:
        _jobs_table(jobs_for_customer(cname), session_key=f"_loc_jobs_{lid}", location_id=lid)

    with tab_estimates:
        _estimates_table(estimates_for_customer(cname), session_key=f"_loc_est_{lid}", location_id=lid)

    with tab_documents:
        placeholder_html("Location documents will appear here when connected to Supabase.")

    with tab_notes:
        notes_text = safe_value(location.get("notes"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Location activity history will appear here when connected to Supabase.")


def render_location_detail_dialog(location: dict) -> None:
    rk = record_session_key(location, "id", "location_name", "site_name")
    title = safe_value(location.get("location_name") or location.get("site_name"))
    status = safe_value(location.get("status"))
    cid = str(location.get("customer_id") or "")
    customer = get_customer(cid) if cid else None
    cname = safe_value((customer or {}).get("customer_name"))

    render_modal_shell()
    render_modal_header(title=title, subtitle=f"{cname} · Location" if cname != "—" else "Location", status=status)

    render_modal_edit_button(
        module=_LOC_MOD,
        record_key=rk,
        on_edit=lambda: _set_location_edit_mode(location),
        key_prefix=f"location_modal_{rk}",
    )

    city_state = ", ".join(
        part for part in (str(location.get("city") or "").strip(), str(location.get("state") or "").strip()) if part
    )
    contacts = get_customer_contacts(cid, location_id=str(location.get("id") or "")) if cid else []
    render_modal_meta_grid(
        [
            ("Type", location.get("location_type")),
            ("City / State", city_state or "—"),
            ("Phone", location.get("phone")),
            ("Contacts", len(contacts)),
        ]
    )

    if is_edit_mode(_LOC_MOD, rk):
        _render_location_edit_form(location)
    else:
        _render_location_detail_tabs(location, customer)


@st.dialog("Location Details", width="large", on_dismiss=_clear_location_detail_modal)
def _show_location_detail_modal() -> None:
    location = get_modal_record(
        cache_key=_LOCATIONS_CACHE_KEY,
        modal_key=_LOCATION_MODAL_KEY,
        session_select_key=_LOC_SEL,
    )
    if not location:
        sel = str(st.session_state.get(_LOCATION_MODAL_KEY) or st.session_state.get(_LOC_SEL) or "").strip()
        location = get_customer_location(sel) if sel else None
    if not location:
        render_missing_record(_clear_location_detail_modal, close_key="location_modal_missing_close")
        return
    render_location_detail_dialog(location)


# --- Contact modal ---


def _seed_contact_edit_form(contact: dict) -> None:
    rk = record_session_key(contact, "id", "full_name", "contact_name")
    st.session_state[f"ct_edit_name_{rk}"] = str(contact.get("full_name") or contact.get("contact_name") or "")
    st.session_state[f"ct_edit_title_{rk}"] = str(contact.get("title") or "")
    st.session_state[f"ct_edit_role_{rk}"] = str(contact.get("role_type") or contact.get("title") or "Other")
    st.session_state[f"ct_edit_dept_{rk}"] = str(contact.get("department") or "")
    st.session_state[f"ct_edit_email_{rk}"] = str(contact.get("email") or "")
    st.session_state[f"ct_edit_phone_{rk}"] = str(contact.get("phone") or "")
    st.session_state[f"ct_edit_mobile_{rk}"] = str(contact.get("mobile") or "")
    st.session_state[f"ct_edit_primary_{rk}"] = bool(contact.get("is_primary"))
    st.session_state[f"ct_edit_status_{rk}"] = str(contact.get("status") or "Active")
    st.session_state[f"ct_edit_notes_{rk}"] = str(contact.get("notes") or "")


def _set_contact_edit_mode(contact: dict) -> None:
    rk = record_session_key(contact, "id", "full_name", "contact_name")
    set_edit_mode(_CT_MOD, rk)
    _seed_contact_edit_form(contact)


def _render_contact_edit_form(contact: dict, *, locations: list[dict]) -> None:
    ct_id = str(contact.get("id") or "")
    cid = str(contact.get("customer_id") or "")
    rk = record_session_key(contact, "id", "full_name", "contact_name")
    if f"ct_edit_name_{rk}" not in st.session_state:
        _seed_contact_edit_form(contact)

    render_edit_form_header("Edit Contact")
    if is_demo_id(ct_id) or is_demo_id(cid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    loc_opts = [(_location_label(loc), str(loc.get("id") or "")) for loc in locations if str(loc.get("id") or "")]
    labels = [label for label, _ in loc_opts]
    ids = [lid for _, lid in loc_opts]
    cur_loc = str(contact.get("location_id") or contact.get("customer_location_id") or "")
    if f"ct_edit_loc_{rk}" not in st.session_state and cur_loc in ids:
        st.session_state[f"ct_edit_loc_{rk}"] = ids.index(cur_loc)
    elif f"ct_edit_loc_{rk}" not in st.session_state and ids:
        st.session_state[f"ct_edit_loc_{rk}"] = 0

    if labels:
        loc_idx = st.selectbox(
            "Location",
            range(len(labels)),
            format_func=lambda i: labels[i],
            key=f"ct_edit_loc_{rk}",
        )
        loc_id = ids[int(loc_idx)]
    else:
        st.caption("No locations available.")
        loc_id = cur_loc

    ec1, ec2 = st.columns(2)
    with ec1:
        st.text_input("Full name", key=f"ct_edit_name_{rk}")
        st.text_input("Title", key=f"ct_edit_title_{rk}")
        st.selectbox("Role", CONTACT_ROLE_TYPES, key=f"ct_edit_role_{rk}")
        st.text_input("Department", key=f"ct_edit_dept_{rk}")
    with ec2:
        st.text_input("Email", key=f"ct_edit_email_{rk}")
        st.text_input("Phone", key=f"ct_edit_phone_{rk}")
        st.text_input("Mobile", key=f"ct_edit_mobile_{rk}")
        st.selectbox("Status", ["Active", "Inactive"], key=f"ct_edit_status_{rk}")
        st.checkbox("Primary for location", key=f"ct_edit_primary_{rk}")
    st.text_area("Notes", key=f"ct_edit_notes_{rk}", height=90)

    cancelled, saved = render_save_cancel_actions(
        module=_CT_MOD,
        record_key=rk,
        cancel_key=f"ct_edit_cancel_{rk}",
        save_key=f"ct_edit_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved and loc_id:
        payload = {
            "customer_id": cid,
            "location_id": loc_id,
            "customer_location_id": loc_id,
            "full_name": st.session_state.get(f"ct_edit_name_{rk}"),
            "contact_name": st.session_state.get(f"ct_edit_name_{rk}"),
            "title": st.session_state.get(f"ct_edit_title_{rk}"),
            "role_type": st.session_state.get(f"ct_edit_role_{rk}"),
            "department": st.session_state.get(f"ct_edit_dept_{rk}"),
            "email": st.session_state.get(f"ct_edit_email_{rk}"),
            "phone": st.session_state.get(f"ct_edit_phone_{rk}"),
            "mobile": st.session_state.get(f"ct_edit_mobile_{rk}"),
            "is_primary": st.session_state.get(f"ct_edit_primary_{rk}"),
            "status": st.session_state.get(f"ct_edit_status_{rk}"),
            "notes": st.session_state.get(f"ct_edit_notes_{rk}"),
        }
        ok, msg = _service_feedback(update_customer_contact(ct_id, payload), success="Contact saved.")
        if ok:
            set_view_mode(_CT_MOD, rk)
            st.success(msg)
            st.rerun()
        st.error(msg or "Could not save contact.")


def _render_contact_detail_tabs(contact: dict, customer: dict | None, location: dict | None) -> None:
    ct_id = str(contact.get("id") or "")
    cname = str((customer or {}).get("customer_name") or contact.get("customer_name") or "")

    (
        tab_overview,
        tab_location,
        tab_jobs,
        tab_estimates,
        tab_notes,
        tab_activity,
    ) = st.tabs(_CONTACT_TABS)

    with tab_overview:
        status = safe_value(contact.get("status"))
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Name', contact.get('full_name') or contact.get('contact_name'))}"
            f"{detail_field_html('Title', contact.get('title'))}"
            f"{detail_field_html('Role', contact.get('role_type'))}"
            f"{detail_field_html('Department', contact.get('department'))}"
            f"{detail_field_html('Email', contact.get('email'))}"
            f"{detail_field_html('Phone', contact.get('phone'))}"
            f"{detail_field_html('Mobile', contact.get('mobile'))}"
            f"{detail_field_html('Primary', _yes_dash(contact.get('is_primary')))}"
            f'{detail_field_html("Status", status, html_value=modal_status_pill_html(status))}'
            f"</div>"
        )
        st.markdown(dialog_card_html("Contact", overview_html), unsafe_allow_html=True)

    with tab_location:
        if location:
            loc_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Location', location.get('location_name') or location.get('site_name'))}"
                f"{detail_field_html('Type', location.get('location_type'))}"
                f"{detail_field_html('City', location.get('city'))}"
                f"{detail_field_html('State', location.get('state'))}"
                f"{detail_field_html('Phone', location.get('phone'))}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Assigned Location", loc_html), unsafe_allow_html=True)
        else:
            st.caption("No location assigned.")

    with tab_jobs:
        jobs = jobs_for_customer(cname)
        contact_name = str(contact.get("full_name") or contact.get("contact_name") or "").strip().lower()
        if contact_name:
            jobs = [
                j
                for j in jobs
                if str(j.get("contact_name") or j.get("customer_contact") or "").strip().lower() == contact_name
                or str(j.get("customer_contact_id") or j.get("contact_id") or "") == ct_id
            ]
        _jobs_table(jobs, session_key=f"_ct_jobs_{ct_id}")

    with tab_estimates:
        ests = estimates_for_customer(cname)
        contact_name = str(contact.get("full_name") or contact.get("contact_name") or "").strip().lower()
        if contact_name:
            ests = [
                e
                for e in ests
                if str(e.get("contact_name") or e.get("customer_contact") or "").strip().lower() == contact_name
                or str(e.get("customer_contact_id") or e.get("contact_id") or "") == ct_id
            ]
        _estimates_table(ests, session_key=f"_ct_est_{ct_id}")

    with tab_notes:
        notes_text = safe_value(contact.get("notes"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Contact activity history will appear here when connected to Supabase.")


def render_contact_detail_dialog(contact: dict) -> None:
    rk = record_session_key(contact, "id", "full_name", "contact_name")
    title = safe_value(contact.get("full_name") or contact.get("contact_name"))
    status = safe_value(contact.get("status"))
    cid = str(contact.get("customer_id") or "")
    customer = get_customer(cid) if cid else None
    lid = str(contact.get("location_id") or contact.get("customer_location_id") or "")
    location = get_customer_location(lid) if lid else None
    cname = safe_value((customer or {}).get("customer_name"))
    loc_name = safe_value((location or {}).get("location_name") or contact.get("location_name"))

    render_modal_shell()
    render_modal_header(
        title=title,
        subtitle=f"{cname} · {loc_name}" if cname != "—" else loc_name,
        status=status,
    )

    render_modal_edit_button(
        module=_CT_MOD,
        record_key=rk,
        on_edit=lambda: _set_contact_edit_mode(contact),
        key_prefix=f"contact_modal_{rk}",
    )

    render_modal_meta_grid(
        [
            ("Role", contact.get("role_type") or contact.get("title")),
            ("Location", loc_name),
            ("Email", contact.get("email")),
            ("Phone", contact.get("phone")),
        ]
    )

    if is_edit_mode(_CT_MOD, rk):
        locations = get_customer_locations(cid) if cid else []
        _render_contact_edit_form(contact, locations=locations)
    else:
        _render_contact_detail_tabs(contact, customer, location)


@st.dialog("Contact Details", width="large", on_dismiss=_clear_contact_detail_modal)
def _show_contact_detail_modal() -> None:
    contact = get_modal_record(
        cache_key=_CONTACTS_CACHE_KEY,
        modal_key=_CONTACT_MODAL_KEY,
        session_select_key=_CT_SEL,
    )
    if not contact:
        sel = str(st.session_state.get(_CONTACT_MODAL_KEY) or st.session_state.get(_CT_SEL) or "").strip()
        contact = get_customer_contact(sel) if sel else None
    if not contact:
        render_missing_record(_clear_contact_detail_modal, close_key="contact_modal_missing_close")
        return
    render_contact_detail_dialog(contact)


# --- Page render ---


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("customers"):
        return

    inject_customers_module_css()
    st.markdown(
        '<span class="ips-customers-page ips-module-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    all_rows = _enrich_list_rows(get_customers())
    states = sorted(
        {
            str(c.get("primary_location_state") or c.get("state") or "")
            for c in all_rows
            if c.get("primary_location_state") or c.get("state")
        }
    )

    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        render_page_header("Customers", "Manage customer companies, sites, and contacts.")
    with hdr_r:
        if st.button("+ New Customer", key="cust_new", type="primary", use_container_width=True):
            st.session_state["ips_cust_form"] = True

    if st.session_state.get("ips_cust_form"):
        with st.container(border=True):
            st.markdown(
                '<p class="ips-page-subtitle" style="margin:0 0 0.5rem;font-weight:600;color:#0f172a">New customer</p>',
                unsafe_allow_html=True,
            )
            nc1, nc2 = st.columns(2)
            with nc1:
                st.text_input("Company name", key="cust_new_company")
                st.text_input("Customer #", key="cust_new_number")
                st.text_input("Website", key="cust_new_website")
                st.text_input("Main phone", key="cust_new_main_phone")
            with nc2:
                st.text_input("Main email", key="cust_new_main_email")
                st.text_input("Billing email", key="cust_new_billing_email")
                st.selectbox("Status", ["Active", "Inactive"], key="cust_new_status")
            st.text_area("Notes", key="cust_new_notes")
            with st.expander("Legacy address (optional)", expanded=False):
                la1, la2 = st.columns(2)
                with la1:
                    st.text_input("Address", key="cust_new_addr")
                    st.text_input("City", key="cust_new_city")
                with la2:
                    st.text_input("State", key="cust_new_state")
                    st.text_input("ZIP", key="cust_new_zip")
            sb1, sb2 = st.columns(2)
            with sb1:
                if st.button("Save customer", key="cust_save_new", type="primary", use_container_width=True):
                    payload = {
                        "company_name": st.session_state.get("cust_new_company"),
                        "customer_name": st.session_state.get("cust_new_company"),
                        "customer_number": st.session_state.get("cust_new_number"),
                        "website": st.session_state.get("cust_new_website"),
                        "main_phone": st.session_state.get("cust_new_main_phone"),
                        "main_email": st.session_state.get("cust_new_main_email"),
                        "billing_email": st.session_state.get("cust_new_billing_email"),
                        "status": st.session_state.get("cust_new_status"),
                        "notes": st.session_state.get("cust_new_notes"),
                        "address": st.session_state.get("cust_new_addr"),
                        "city": st.session_state.get("cust_new_city"),
                        "state": st.session_state.get("cust_new_state"),
                        "zip": st.session_state.get("cust_new_zip"),
                    }
                    ok, msg = _service_feedback(create_customer(payload), success="Customer saved.")
                    if apply_persist_feedback(ok, msg, clear_keys=("ips_cust_form",)):
                        st.rerun()
            with sb2:
                if st.button("Cancel", key="cust_cancel_new", use_container_width=True):
                    st.session_state.pop("ips_cust_form", None)
                    st.rerun()

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

    build_modal_cache(filtered, cache_key=_CUSTOMERS_CACHE_KEY)

    render_clickable_table(
        filtered,
        [
            ("customer_name", "CUSTOMER"),
            ("primary_location_name", "PRIMARY SITE"),
            ("primary_location_city", "CITY"),
            ("primary_location_state", "STATE"),
            ("contact_count", "CONTACTS"),
            ("open_jobs", "OPEN JOBS"),
            ("open_estimates", "OPEN EST."),
            ("status", "STATUS"),
        ],
        _CUSTOMERS_TABLE_KEY,
        row_id_key="id",
        session_select_key=_SEL,
        format_cell=_list_display_cell,
        click_caption=f"{len(filtered)} customer(s) · Click a row to open details.",
        on_row_selected=_open_customers_detail_modal,
    )

    show_modal_if_pending(_CUSTOMERS_MODAL_KEY, _show_customers_detail_modal)
