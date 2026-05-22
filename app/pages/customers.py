"""Customers module — company directory with sites and contacts."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.clickable_table import render_clickable_table
    from app.components.record_modal import (
        build_modal_cache,
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
    from app.components.record_modal import clear_record_modal
    from app.components.status import status_pill_html
    from app.components.tables import render_data_table
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._data import (
        delete_customer_contact_row,
        delete_customer_location_row,
        estimates_for_customer,
        get_customer,
        jobs_for_customer,
        load_customer_contacts,
        load_customer_locations,
        load_customers,
        persist_customer,
        persist_customer_contact,
        persist_customer_location,
    )
    from app.pages._core._session import select_key
    from app.styles import inject_customers_module_css
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.clickable_table import render_clickable_table  # type: ignore
    from components.record_modal import (  # type: ignore
        build_modal_cache,
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
    from components.record_modal import clear_record_modal  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._data import (  # type: ignore
        delete_customer_contact_row,
        delete_customer_location_row,
        estimates_for_customer,
        get_customer,
        jobs_for_customer,
        load_customer_contacts,
        load_customer_locations,
        load_customers,
        persist_customer,
        persist_customer_contact,
        persist_customer_location,
    )
    from pages._core._session import select_key  # type: ignore
    from styles import inject_customers_module_css  # type: ignore

_SEL = select_key("customers")
_MOD = "customers"
_CUSTOMERS_MODAL_KEY = "ips_customers_detail_modal_id"
_CUSTOMERS_CACHE_KEY = "_ips_customers_modal_by_id"
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


def _clear_customers_detail_modal() -> None:
    clear_record_modal(
        table_key="customers_list",
        session_select_key=_SEL,
        modal_key=_CUSTOMERS_MODAL_KEY,
        module=_MOD,
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


def _location_label(location_id: str, locations: list[dict]) -> str:
    lid = str(location_id or "").strip()
    if not lid:
        return "Company-wide"
    loc = next((row for row in locations if str(row.get("id")) == lid), None)
    if not loc:
        return "—"
    name = str(loc.get("site_name") or "—")
    city = str(loc.get("city") or "").strip()
    state = str(loc.get("state") or "").strip()
    tail = ", ".join(part for part in (city, state) if part)
    return f"{name} — {tail}" if tail else name


def _location_select_options(locations: list[dict]) -> tuple[list[str], list[str]]:
    labels = ["Company-wide (all locations)"]
    ids = [""]
    for loc in locations:
        if str(loc.get("status") or "Active") != "Active":
            continue
        lid = str(loc.get("id") or "").strip()
        if not lid:
            continue
        labels.append(_location_label(lid, locations))
        ids.append(lid)
    return labels, ids


def _location_selectbox(
    *,
    locations: list[dict],
    key: str,
    initial_location_id: str = "",
) -> str:
    labels, ids = _location_select_options(locations)
    if key not in st.session_state and initial_location_id:
        try:
            st.session_state[key] = ids.index(initial_location_id)
        except ValueError:
            st.session_state[key] = 0
    idx = st.selectbox(
        "Location",
        range(len(labels)),
        format_func=lambda i: labels[i],
        key=key,
    )
    return ids[int(idx)]


def _location_form_payload(*, customer_id: str, key_prefix: str) -> dict:
    return {
        "customer_id": customer_id,
        "site_name": st.session_state.get(f"{key_prefix}_name"),
        "address": st.session_state.get(f"{key_prefix}_addr"),
        "city": st.session_state.get(f"{key_prefix}_city"),
        "state": st.session_state.get(f"{key_prefix}_state"),
        "zip": st.session_state.get(f"{key_prefix}_zip"),
        "status": st.session_state.get(f"{key_prefix}_status"),
        "notes": st.session_state.get(f"{key_prefix}_notes"),
    }


def _contact_form_payload(
    *,
    customer_id: str,
    key_prefix: str,
    location_key: str,
    locations: list[dict],
) -> dict:
    _, loc_ids = _location_select_options(locations)
    loc_idx = int(st.session_state.get(location_key) or 0)
    loc_id = loc_ids[loc_idx] if 0 <= loc_idx < len(loc_ids) else ""
    return {
        "customer_id": customer_id,
        "customer_location_id": loc_id or None,
        "contact_name": st.session_state.get(f"{key_prefix}_name"),
        "title": st.session_state.get(f"{key_prefix}_title"),
        "email": st.session_state.get(f"{key_prefix}_email"),
        "phone": st.session_state.get(f"{key_prefix}_phone"),
        "status": st.session_state.get(f"{key_prefix}_status"),
        "is_primary": st.session_state.get(f"{key_prefix}_primary"),
        "notes": st.session_state.get(f"{key_prefix}_notes"),
    }


def _contacts_for_location(contacts: list[dict], location_id: str) -> list[dict]:
    lid = str(location_id or "").strip()
    return [
        c
        for c in contacts
        if str(c.get("customer_location_id") or "").strip() == lid
    ]


def _contact_group_sections(contacts: list[dict], locations: list[dict]) -> list[tuple[str, str, list[dict]]]:
    sections: list[tuple[str, str, list[dict]]] = []
    for loc in locations:
        lid = str(loc.get("id") or "").strip()
        if not lid:
            continue
        rows = _contacts_for_location(contacts, lid)
        sections.append((_location_label(lid, locations), lid, rows))
    company_wide = _contacts_for_location(contacts, "")
    sections.append(("Company-wide", "", company_wide))
    return sections


def _begin_new_contact(customer_id: str, *, location_id: str = "") -> None:
    cid = str(customer_id or "").strip()
    st.session_state[f"cust_show_new_contact_{cid}"] = True
    st.session_state[f"cust_new_contact_loc_{cid}"] = str(location_id or "").strip()


def _clear_new_contact_fields(key_prefix: str) -> None:
    for suffix in ("name", "title", "email", "phone", "notes", "primary"):
        st.session_state.pop(f"{key_prefix}_{suffix}", None)


def _render_contact_table(contacts: list[dict], locations: list[dict], *, table_key: str) -> None:
    def _con_cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "contact_name" and row.get("is_primary"):
            return (
                f'{html.escape(str(row.get("contact_name") or ""))} '
                f'<span class="ips-status-pill ips-status-sent" style="font-size:0.62rem;">PRIMARY</span>'
            )
        return html.escape(str(row.get(field) or "—"))

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
        session_select_key=table_key,
        hide_select=True,
        cell_renderer=_con_cell,
    )


def _render_new_contact_form(
    customer: dict,
    *,
    locations: list[dict],
    demo: bool,
    preset_location_id: str = "",
) -> None:
    cid = str(customer.get("id") or "")
    pk = f"cust_new_ct_{cid}"
    loc_key = f"{pk}_location"
    preset = str(preset_location_id or st.session_state.pop(f"cust_new_contact_loc_{cid}", "") or "").strip()
    if loc_key not in st.session_state and preset:
        _, ids = _location_select_options(locations)
        try:
            st.session_state[loc_key] = ids.index(preset)
        except ValueError:
            st.session_state[loc_key] = 0

    with st.container(border=True):
        st.markdown("**New contact**")
        _location_selectbox(locations=locations, key=loc_key)
        nc1, nc2 = st.columns(2)
        with nc1:
            st.text_input("Name", key=f"{pk}_name")
            st.text_input("Title", key=f"{pk}_title")
            st.text_input("Email", key=f"{pk}_email")
        with nc2:
            st.text_input("Phone", key=f"{pk}_phone")
            st.selectbox("Status", ["Active", "Inactive"], index=0, key=f"{pk}_status")
            st.checkbox("Primary for this location", key=f"{pk}_primary")
        st.text_area("Notes", key=f"{pk}_notes")
        sb1, sb2, sb3 = st.columns(3)
        with sb1:
            save = st.button("Save contact", key=f"{pk}_save", type="primary", use_container_width=True)
        with sb2:
            save_another = st.button("Save & add another", key=f"{pk}_save_more", use_container_width=True)
        with sb3:
            if st.button("Cancel", key=f"{pk}_cancel", use_container_width=True):
                st.session_state.pop(f"cust_show_new_contact_{cid}", None)
                st.session_state.pop(f"cust_new_contact_loc_{cid}", None)
                st.rerun()

        if save or save_another:
            payload = _contact_form_payload(
                customer_id=cid,
                key_prefix=pk,
                location_key=loc_key,
                locations=locations,
            )
            ok, msg = persist_customer_contact(payload)
            if not ok:
                apply_persist_feedback(ok, msg)
                return
            if save_another:
                loc_id = str(payload.get("customer_location_id") or "")
                st.session_state[f"cust_show_new_contact_{cid}"] = True
                st.session_state[f"cust_new_contact_loc_{cid}"] = loc_id
                _clear_new_contact_fields(pk)
                st.toast(msg, icon="✅")
                st.rerun()
            if apply_persist_feedback(ok, msg, clear_keys=(f"cust_show_new_contact_{cid}", f"cust_new_contact_loc_{cid}")):
                st.rerun()


def _render_locations_section(customer: dict, *, demo: bool) -> None:
    cid = str(customer.get("id") or "")
    locations = load_customer_locations(cid)
    contacts = load_customer_contacts(cid)

    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        st.markdown("**Locations**")
        st.caption("Add sites for this customer, then assign multiple contacts to each location.")
    with hdr_r:
        if not demo and st.button("+ Add location", key=f"cust_add_loc_{cid}", type="primary", use_container_width=True):
            st.session_state[f"cust_show_new_loc_{cid}"] = True

    if not demo and st.session_state.get(f"cust_show_new_loc_{cid}"):
        pk = f"cust_new_loc_{cid}"
        with st.container(border=True):
            st.markdown("**New location**")
            lc1, lc2 = st.columns(2)
            with lc1:
                st.text_input("Location name", key=f"{pk}_name")
                st.text_input("Address", key=f"{pk}_addr")
                st.text_input("City", key=f"{pk}_city")
            with lc2:
                st.text_input("State", key=f"{pk}_state")
                st.text_input("ZIP", key=f"{pk}_zip")
                st.selectbox("Status", ["Active", "Inactive"], index=0, key=f"{pk}_status")
            st.text_area("Notes", key=f"{pk}_notes")
            sb1, sb2 = st.columns(2)
            with sb1:
                if st.button("Save location", key=f"{pk}_save", type="primary", use_container_width=True):
                    ok, msg = persist_customer_location(_location_form_payload(customer_id=cid, key_prefix=pk))
                    if apply_persist_feedback(ok, msg, clear_keys=(f"cust_show_new_loc_{cid}",)):
                        st.rerun()
            with sb2:
                if st.button("Cancel", key=f"{pk}_cancel", use_container_width=True):
                    st.session_state.pop(f"cust_show_new_loc_{cid}", None)
                    st.rerun()

    def _loc_cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "contact_count":
            count = len(_contacts_for_location(contacts, str(row.get("id") or "")))
            return html.escape(str(count))
        return html.escape(str(row.get(field) or "—"))

    if locations:
        render_data_table(
            locations,
            [
                ("site_name", "LOCATION"),
                ("address", "ADDRESS"),
                ("city", "CITY"),
                ("state", "STATE"),
                ("contact_count", "CONTACTS"),
                ("status", "STATUS"),
            ],
            row_id_key="id",
            selected_id=None,
            session_select_key=f"_cust_loc_{cid}",
            hide_select=True,
            cell_renderer=_loc_cell,
        )
    else:
        st.caption("No locations on file for this customer.")

    if locations and not demo:
        labels = ["— Select location to edit —"] + [
            f'{loc.get("site_name") or "—"} — {loc.get("city") or ""}, {loc.get("state") or ""}'.strip(" —,")
            for loc in locations
        ]
        ids = [""] + [str(loc.get("id") or "") for loc in locations]
        pick = st.selectbox(
            "Edit location",
            range(len(labels)),
            format_func=lambda i: labels[i],
            key=f"cust_edit_loc_pick_{cid}",
        )
        edit_id = ids[int(pick)]
        if edit_id:
            loc = next((row for row in locations if str(row.get("id")) == edit_id), None)
            if loc:
                pk = f"cust_edit_loc_{edit_id}"
                loc_contacts = _contacts_for_location(contacts, edit_id)
                with st.container(border=True):
                    st.markdown(f"**Edit — {html.escape(str(loc.get('site_name') or ''))}**", unsafe_allow_html=True)
                    st.caption(f"{len(loc_contacts)} contact(s) at this location.")
                    if loc_contacts:
                        _render_contact_table(loc_contacts, locations, table_key=f"_cust_loc_ct_{edit_id}")
                    elif not demo:
                        st.caption("No contacts assigned to this location yet.")
                    if not demo:
                        if st.button(
                            "+ Add contact at this location",
                            key=f"cust_add_ct_at_loc_{edit_id}",
                            type="primary",
                        ):
                            _begin_new_contact(cid, location_id=edit_id)
                            st.rerun()
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        st.text_input("Location name", value=str(loc.get("site_name") or ""), key=f"{pk}_name")
                        st.text_input("Address", value=str(loc.get("address") or ""), key=f"{pk}_addr")
                        st.text_input("City", value=str(loc.get("city") or ""), key=f"{pk}_city")
                    with ec2:
                        st.text_input("State", value=str(loc.get("state") or ""), key=f"{pk}_state")
                        st.text_input("ZIP", value=str(loc.get("zip") or ""), key=f"{pk}_zip")
                        st.selectbox(
                            "Status",
                            ["Active", "Inactive"],
                            index=0 if str(loc.get("status") or "Active") == "Active" else 1,
                            key=f"{pk}_status",
                        )
                    st.text_area("Notes", value=str(loc.get("notes") or ""), key=f"{pk}_notes", height=80)
                    eb1, eb2 = st.columns(2)
                    with eb1:
                        if st.button("Save changes", key=f"{pk}_save", type="primary", use_container_width=True):
                            ok, msg = persist_customer_location(
                                _location_form_payload(customer_id=cid, key_prefix=pk),
                                row_id=edit_id,
                            )
                            if apply_persist_feedback(ok, msg):
                                st.rerun()
                    with eb2:
                        if st.button("Remove location", key=f"{pk}_delete", use_container_width=True):
                            ok, msg = delete_customer_location_row(edit_id)
                            if apply_persist_feedback(ok, msg):
                                st.session_state[f"cust_edit_loc_pick_{cid}"] = 0
                                st.rerun()
    elif demo:
        st.caption("Add and edit locations after saving this customer to Supabase.")


def _render_contacts_section(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    contacts = load_customer_contacts(cid)
    locations = load_customer_locations(cid)
    demo = is_demo_id(cid)

    _render_locations_section(customer, demo=demo)

    st.divider()

    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        st.markdown("**Contacts**")
        st.caption("Each location can have multiple contacts. Company-wide contacts apply to all sites.")
    with hdr_r:
        if not demo and st.button("+ Add contact", key=f"cust_add_contact_{cid}", type="primary", use_container_width=True):
            _begin_new_contact(cid)

    if not demo and st.session_state.get(f"cust_show_new_contact_{cid}"):
        _render_new_contact_form(customer, locations=locations, demo=demo)

    if not contacts and not locations:
        st.caption("Add locations first, then assign contacts to each site.")
    elif not contacts:
        st.caption("No contacts yet. Use + Add contact at a location below or the button above.")

    for label, loc_id, rows in _contact_group_sections(contacts, locations):
        st.markdown(f"**{html.escape(label)}**", unsafe_allow_html=True)
        sub_l, sub_r = st.columns([3, 1])
        with sub_l:
            st.caption(f"{len(rows)} contact(s)")
        with sub_r:
            if not demo:
                if st.button(
                    "+ Add contact",
                    key=f"cust_add_ct_grp_{cid}_{loc_id or 'company'}",
                    use_container_width=True,
                ):
                    _begin_new_contact(cid, location_id=loc_id)
                    st.rerun()
        if rows:
            _render_contact_table(rows, locations, table_key=f"_cust_con_{cid}_{loc_id or 'company'}")
        else:
            st.caption("No contacts at this location yet.")

    if contacts and not demo:
        labels = ["— Select contact to edit —"] + [
            f'{c.get("contact_name") or "—"} — {_location_label(str(c.get("customer_location_id") or ""), locations)}'
            for c in contacts
        ]
        ids = [""] + [str(c.get("id") or "") for c in contacts]
        pick = st.selectbox(
            "Edit contact",
            range(len(labels)),
            format_func=lambda i: labels[i],
            key=f"cust_edit_ct_pick_{cid}",
        )
        edit_id = ids[int(pick)]
        if edit_id:
            ct = next((c for c in contacts if str(c.get("id")) == edit_id), None)
            if ct:
                pk = f"cust_edit_ct_{edit_id}"
                loc_key = f"{pk}_location"
                with st.container(border=True):
                    st.markdown(f"**Edit — {html.escape(str(ct.get('contact_name') or ''))}**", unsafe_allow_html=True)
                    _location_selectbox(
                        locations=locations,
                        key=loc_key,
                        initial_location_id=str(ct.get("customer_location_id") or ""),
                    )
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        st.text_input("Name", value=str(ct.get("contact_name") or ""), key=f"{pk}_name")
                        st.text_input("Title", value=str(ct.get("title") or ""), key=f"{pk}_title")
                        st.text_input("Email", value=str(ct.get("email") or ""), key=f"{pk}_email")
                    with ec2:
                        st.text_input("Phone", value=str(ct.get("phone") or ""), key=f"{pk}_phone")
                        st.selectbox(
                            "Status",
                            ["Active", "Inactive"],
                            index=0 if str(ct.get("status") or "Active") == "Active" else 1,
                            key=f"{pk}_status",
                        )
                        st.checkbox("Primary for this location", value=bool(ct.get("is_primary")), key=f"{pk}_primary")
                    st.text_area("Notes", value=str(ct.get("notes") or ""), key=f"{pk}_notes", height=80)
                    eb1, eb2 = st.columns(2)
                    with eb1:
                        if st.button("Save changes", key=f"{pk}_save", type="primary", use_container_width=True):
                            ok, msg = persist_customer_contact(
                                _contact_form_payload(
                                    customer_id=cid,
                                    key_prefix=pk,
                                    location_key=loc_key,
                                    locations=locations,
                                ),
                                row_id=edit_id,
                            )
                            if apply_persist_feedback(ok, msg):
                                st.rerun()
                    with eb2:
                        if st.button("Remove contact", key=f"{pk}_delete", use_container_width=True):
                            ok, msg = delete_customer_contact_row(edit_id)
                            if apply_persist_feedback(ok, msg):
                                st.session_state[f"cust_edit_ct_pick_{cid}"] = 0
                                st.rerun()
    elif demo:
        st.caption("Add and edit contacts after saving this customer to Supabase.")


def _seed_customer_edit_form(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    st.session_state[f"cust_edit_name_{cid}"] = str(customer.get("customer_name") or "")
    st.session_state[f"cust_edit_addr_{cid}"] = str(customer.get("address") or "")
    st.session_state[f"cust_edit_city_{cid}"] = str(customer.get("city") or "")
    st.session_state[f"cust_edit_state_{cid}"] = str(customer.get("state") or "")
    st.session_state[f"cust_edit_zip_{cid}"] = str(customer.get("zip") or "")
    st.session_state[f"cust_edit_status_{cid}"] = str(customer.get("status") or "Active")
    st.session_state[f"cust_edit_notes_{cid}"] = str(customer.get("notes") or "")


def _set_customer_view_mode(customer: dict) -> None:
    rk = record_session_key(customer, "id", "customer_name")
    set_view_mode(_MOD, rk)


def _set_customer_edit_mode(customer: dict) -> None:
    rk = record_session_key(customer, "id", "customer_name")
    set_edit_mode(_MOD, rk)
    _seed_customer_edit_form(customer)


def _render_customer_edit_form(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    rk = record_session_key(customer, "id", "customer_name")
    if f"cust_edit_name_{cid}" not in st.session_state:
        _seed_customer_edit_form(customer)

    render_edit_form_header("Edit Customer")

    if is_demo_id(cid):
        st.caption("Demo records cannot be edited until saved to Supabase.")
        return

    ec1, ec2 = st.columns(2)
    with ec1:
        st.text_input("Company name", key=f"cust_edit_name_{cid}")
        st.text_input("Address", key=f"cust_edit_addr_{cid}")
        st.text_input("City", key=f"cust_edit_city_{cid}")
    with ec2:
        st.text_input("State", key=f"cust_edit_state_{cid}")
        st.text_input("ZIP", key=f"cust_edit_zip_{cid}")
        st.selectbox("Status", ["Active", "Inactive"], key=f"cust_edit_status_{cid}")
    st.text_area("Notes", key=f"cust_edit_notes_{cid}", height=100)

    cancelled, saved = render_save_cancel_actions(
        module=_MOD,
        record_key=rk,
        cancel_key=f"cust_edit_cancel_{cid}",
        save_key=f"cust_edit_save_{cid}",
    )
    if cancelled:
        st.rerun()
    if saved:
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
        if ok:
            set_view_mode(_MOD, rk)
            st.success(msg or "Customer saved.")
            st.rerun()
        else:
            st.error(msg or "Could not save customer.")


def _render_customer_detail_tabs(customer: dict) -> None:
    cid = str(customer.get("id") or "")
    cname = str(customer.get("customer_name") or "")
    status = safe_value(customer.get("status"))

    (
        tab_overview,
        tab_contacts,
        tab_jobs,
        tab_estimates,
        tab_documents,
        tab_notes,
        tab_activity,
    ) = st.tabs(_CUSTOMER_TABS)

    with tab_overview:
        locs = load_customer_locations(cid)
        contacts = load_customer_contacts(cid)
        jobs_count = len(jobs_for_customer(cname))
        est_count = len(estimates_for_customer(cname))
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Company Name', cname)}"
            f"{detail_field_html('Address', customer.get('address'))}"
            f"{detail_field_html('City', customer.get('city'))}"
            f"{detail_field_html('State', customer.get('state'))}"
            f"{detail_field_html('ZIP', customer.get('zip'))}"
            f'{detail_field_html("Status", status, html_value=modal_status_pill_html(status))}'
            f"</div>"
        )
        st.markdown(dialog_card_html("Company", overview_html), unsafe_allow_html=True)
        summary_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Locations', len(locs))}"
            f"{detail_field_html('Contacts', len(contacts))}"
            f"{detail_field_html('Jobs', jobs_count)}"
            f"{detail_field_html('Estimates', est_count)}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Summary", summary_html), unsafe_allow_html=True)
        if locs:
            loc_rows = "".join(
                f"<li>{html.escape(_location_label(str(loc.get('id') or ''), locs))}</li>"
                for loc in locs[:8]
            )
            if len(locs) > 8:
                loc_rows += f"<li>… and {len(locs) - 8} more</li>"
            st.markdown(
                dialog_card_html("Locations", f'<ul style="margin:0;padding-left:1.1rem;">{loc_rows}</ul>'),
                unsafe_allow_html=True,
            )

    with tab_contacts:
        _render_contacts_section(customer)

    with tab_jobs:
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
                session_select_key=f"_cust_jobs_{cid}",
                hide_select=True,
                cell_renderer=_job_cell,
            )
        else:
            st.caption("No jobs linked to this customer name yet.")

    with tab_estimates:
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
                session_select_key=f"_cust_est_{cid}",
                hide_select=True,
                cell_renderer=_est_cell,
            )
        else:
            st.caption("No estimates for this customer yet.")

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
    cname = safe_value(customer.get("customer_name"))
    status = safe_value(customer.get("status"))
    city = safe_value(customer.get("city"))
    state = safe_value(customer.get("state"))
    cid = str(customer.get("id") or "")
    locs = load_customer_locations(cid)
    contacts = load_customer_contacts(cid)

    render_modal_shell()
    render_modal_header(title=cname, subtitle="Customer", status=status)

    def _on_edit() -> None:
        _set_customer_edit_mode(customer)

    st.markdown('<span class="ips-dialog-actions" aria-hidden="true"></span>', unsafe_allow_html=True)
    act1, act2, act3, act4 = st.columns([1, 1, 1, 1], gap="small")
    with act1:
        st.button("View", key=f"customers_modal_view_{rk}", on_click=_set_customer_view_mode, args=(customer,))
    with act2:
        st.button("Edit", key=f"customers_modal_edit_{rk}", on_click=_on_edit)
    with act3:
        st.button("More", key=f"customers_modal_more_{rk}")
    with act4:
        if st.button("Close", key=f"customers_modal_close_{rk}"):
            _clear_customers_detail_modal()
            st.rerun()

    render_modal_meta_grid(
        [
            ("City", city),
            ("State", state),
            ("Locations", len(locs)),
            ("Contacts", len(contacts)),
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

    all_rows = load_customers()
    states = sorted({str(c.get("state") or "") for c in all_rows if c.get("state")})

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

    def _display_cell(field: str, row: dict) -> str:
        val = row.get(field)
        return str(val).strip() if val is not None and str(val).strip() else "—"

    build_modal_cache(filtered, cache_key=_CUSTOMERS_CACHE_KEY)

    render_clickable_table(
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
        format_cell=_display_cell,
        click_caption=f"{len(filtered)} customer(s) · Click a row to open details.",
        on_row_selected=_open_customers_detail_modal,
    )

    show_modal_if_pending(_CUSTOMERS_MODAL_KEY, _show_customers_detail_modal)
