from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from auth import current_role
from branding import render_header
from db import delete_rows_admin, fetch_one, fetch_table, insert_row, update_rows

try:
    from services.customer_contacts import (
        delete_contact,
        fetch_contacts_for_customer,
        insert_contact_row,
        set_primary_contact,
    )
except ImportError:
    from app.services.customer_contacts import (  # type: ignore
        delete_contact,
        fetch_contacts_for_customer,
        insert_contact_row,
        set_primary_contact,
    )

try:
    from table_actions import (
        TABLE_KEY_CUSTOMERS,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        TABLE_KEY_CUSTOMERS,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )

try:
    from app.confirm_delete import (
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
except ImportError:
    from confirm_delete import (  # type: ignore
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )

try:
    from app.ips_crud_list_styles import (
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )
except ImportError:
    from ips_crud_list_styles import (  # type: ignore
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )

_CUST_DELETE_CONFIRM_PREFIX = "customers_delete"
_CONTACT_DELETE_PREFIX = "customer_contact_delete"


def _clear_customer_mode() -> None:
    st.session_state.pop("customer_mode", None)
    st.session_state.pop("customer_edit_id", None)
    st.session_state.pop("customer_contact_mode", None)
    st.session_state.pop("customer_contact_edit_id", None)


def _clear_contact_subpanel() -> None:
    st.session_state.pop("customer_contact_mode", None)
    st.session_state.pop("customer_contact_edit_id", None)


def _render_action_buttons(*, sel: list[str], can_add: bool) -> None:
    inject_ips_crud_list_styles()
    inject_table_action_styles()
    n = len(sel)
    one = n == 1
    none = n == 0

    with st.container(border=True):
        st.markdown('<div class="ips-crud-toolbar-root"></div>', unsafe_allow_html=True)
        left, b0, b1, b2, b3 = st.columns([1.1, 1, 1, 1, 1], gap="small")
        with left:
            st.markdown(
                f'<span class="ips-ta-summary"><span class="ips-ta-num">{n}</span> selected</span>',
                unsafe_allow_html=True,
            )
        with b0:
            if st.button(
                "Add Customer",
                type="primary",
                use_container_width=True,
                disabled=not can_add,
                key="cust_btn_add",
            ):
                st.session_state["customer_mode"] = "add"
                st.session_state.pop("customer_edit_id", None)
                _clear_contact_subpanel()
                st.rerun()
        with b1:
            if st.button(
                "Edit",
                type="secondary",
                use_container_width=True,
                disabled=not can_add or not one,
                key="cust_btn_edit",
            ):
                st.session_state["customer_mode"] = "edit"
                st.session_state["customer_edit_id"] = str(sel[0])
                _clear_contact_subpanel()
                st.rerun()
        with b2:
            if st.button(
                "Deactivate",
                type="secondary",
                use_container_width=True,
                disabled=not can_add or none,
                key="cust_btn_deactivate",
            ):
                st.session_state["_cust_do_deactivate"] = True
                st.rerun()
        with b3:
            if st.button(
                "Delete",
                type="secondary",
                use_container_width=True,
                disabled=not can_add or none,
                key="cust_btn_delete",
            ):
                open_destructive_confirmation(_CUST_DELETE_CONFIRM_PREFIX)
                st.session_state["customers_pending_delete_ids"] = [str(x) for x in sel]
                st.rerun()


def _render_add_form(*, existing_customer_names: set[str]) -> None:
    c1 = st.columns(1)[0]
    customer_name = c1.text_input("Customer Name", key="cust_add_name")

    c5, c6, c7, c8 = st.columns(4)
    address = c5.text_input("Address", key="cust_add_addr")
    city = c6.text_input("City", key="cust_add_city")
    state = c7.text_input("State", key="cust_add_state")
    zip_code = c8.text_input("ZIP", key="cust_add_zip")

    is_active_customer = st.checkbox("Active Customer", value=True, key="cust_add_active")

    s1, s2 = st.columns(2)
    with s1:
        if st.button("Save Customer", type="primary", use_container_width=True, key="cust_add_save"):
            if not str(customer_name).strip():
                st.error("Customer Name required.")
                st.stop()
            if str(customer_name).strip().upper() in existing_customer_names:
                st.error("A customer with this name already exists.")
                st.stop()
            payload = {
                "customer_name": str(customer_name).strip(),
                "address": str(address).strip(),
                "city": str(city).strip(),
                "state": str(state).strip(),
                "zip": str(zip_code).strip(),
                "is_active": bool(is_active_customer),
            }
            insert_row("customers", payload)
            _clear_customer_mode()
            st.success("Customer added. Open **Edit** to add contacts.")
            st.rerun()
    with s2:
        if st.button("Cancel", use_container_width=True, key="cust_add_cancel"):
            _clear_customer_mode()
            st.rerun()


def _render_contacts_section(*, customer_row: dict, can_edit: bool) -> None:
    cid = str(customer_row.get("id") or "")
    if not cid:
        return

    st.markdown("##### Contacts")
    st.caption("People at this company — separate from billing address above.")

    mode = st.session_state.get("customer_contact_mode")
    edit_ct = st.session_state.get("customer_contact_edit_id")

    contacts = fetch_contacts_for_customer(cid)

    if can_edit:
        if st.button("Add Contact", type="primary", use_container_width=True, key=f"cust_ct_add_{cid}"):
            st.session_state["customer_contact_mode"] = "add"
            st.session_state.pop("customer_contact_edit_id", None)
            st.rerun()

    if not contacts and mode != "add":
        st.caption("No contacts yet. Use **Add Contact**.")
    else:
        for ct in contacts:
            ctid = str(ct.get("id") or "")
            nm = str(ct.get("contact_name") or "").strip() or "—"
            role = str(ct.get("role") or "").strip()
            em = str(ct.get("email") or "").strip()
            ph = str(ct.get("phone") or "").strip()
            prim = bool(ct.get("is_primary"))
            active = bool(ct.get("is_active", True))
            line = f"**{html.escape(nm)}**"
            if role:
                line += f" · {html.escape(role)}"
            if em:
                line += f" · {html.escape(em)}"
            if ph:
                line += f" · {html.escape(ph)}"
            badges = []
            if prim:
                badges.append("Primary")
            if not active:
                badges.append("Inactive")
            badge_s = " · ".join(badges)
            with st.container(border=True):
                st.markdown(line + (f" · *{badge_s}*" if badge_s else ""), unsafe_allow_html=True)
                if can_edit and ctid:
                    r1, r2, r3, r4 = st.columns([1, 1, 1, 1])
                    with r1:
                        if st.button("Edit", key=f"cust_ct_edbtn_{ctid}", use_container_width=True):
                            st.session_state["customer_contact_mode"] = "edit"
                            st.session_state["customer_contact_edit_id"] = ctid
                            st.rerun()
                    with r2:
                        if not prim:
                            if st.button("Set Primary", key=f"cust_ct_pri_{ctid}", use_container_width=True):
                                set_primary_contact(customer_id=cid, contact_id=ctid)
                                st.success("Primary contact updated.")
                                st.rerun()
                    with r3:
                        if st.button("Delete", key=f"cust_ct_del_{ctid}", use_container_width=True):
                            open_destructive_confirmation(_CONTACT_DELETE_PREFIX)
                            st.session_state["customer_contact_pending_delete_ids"] = [ctid]
                            st.rerun()

    if not can_edit:
        return

    if mode == "add":
        st.markdown("**New contact**")
        pk = f"cust_ct_new_{cid}"
        cn = st.text_input("Contact Name", key=f"{pk}_name")
        rl = st.text_input("Role", key=f"{pk}_role")
        em = st.text_input("Email", key=f"{pk}_email")
        ph = st.text_input("Phone", key=f"{pk}_phone")
        nt = st.text_area("Notes", key=f"{pk}_notes", height=56)
        pr = st.checkbox("Primary contact", value=False, key=f"{pk}_prim")
        act = st.checkbox("Active", value=True, key=f"{pk}_act")
        s1, s2 = st.columns(2)
        with s1:
            if st.button("Save Contact", type="primary", use_container_width=True, key=f"{pk}_save"):
                t = str(cn or "").strip()
                if not t:
                    st.error("Contact Name is required.")
                    st.stop()
                payload = {
                    "customer_id": cid,
                    "contact_name": t,
                    "role": str(rl or "").strip(),
                    "email": str(em or "").strip(),
                    "phone": str(ph or "").strip(),
                    "notes": str(nt or "").strip(),
                    "is_primary": False,
                    "is_active": bool(act),
                }
                inserted = insert_contact_row(payload)
                new_id = str((inserted or {}).get("id") or "")
                if pr and new_id:
                    set_primary_contact(customer_id=cid, contact_id=new_id)
                _clear_contact_subpanel()
                st.success("Contact added.")
                st.rerun()
        with s2:
            if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
                _clear_contact_subpanel()
                st.rerun()

    elif mode == "edit" and edit_ct:
        er = fetch_one("customer_contacts", {"id": edit_ct})
        if not er or str(er.get("customer_id")) != cid:
            _clear_contact_subpanel()
            st.rerun()
            return
        st.markdown("**Edit contact**")
        pk = f"cust_ct_ed_{edit_ct}"
        cn = st.text_input("Contact Name", value=str(er.get("contact_name") or ""), key=f"{pk}_name")
        rl = st.text_input("Role", value=str(er.get("role") or ""), key=f"{pk}_role")
        em = st.text_input("Email", value=str(er.get("email") or ""), key=f"{pk}_email")
        ph = st.text_input("Phone", value=str(er.get("phone") or ""), key=f"{pk}_phone")
        nt = st.text_area("Notes", value=str(er.get("notes") or ""), height=56, key=f"{pk}_notes")
        pr = st.checkbox("Primary contact", value=bool(er.get("is_primary")), key=f"{pk}_prim")
        act = st.checkbox("Active", value=bool(er.get("is_active", True)), key=f"{pk}_act")
        s1, s2 = st.columns(2)
        with s1:
            if st.button("Update Contact", type="primary", use_container_width=True, key=f"{pk}_save"):
                t = str(cn or "").strip()
                if not t:
                    st.error("Contact Name is required.")
                    st.stop()
                payload = {
                    "contact_name": t,
                    "role": str(rl or "").strip(),
                    "email": str(em or "").strip(),
                    "phone": str(ph or "").strip(),
                    "notes": str(nt or "").strip(),
                    "is_primary": bool(pr),
                    "is_active": bool(act),
                }
                update_rows("customer_contacts", payload, {"id": er["id"]})
                if pr:
                    set_primary_contact(customer_id=cid, contact_id=str(er["id"]))
                _clear_contact_subpanel()
                st.success("Contact updated.")
                st.rerun()
        with s2:
            if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
                _clear_contact_subpanel()
                st.rerun()


def _render_edit_form(row: dict, *, can_edit: bool) -> None:
    cid = str(row.get("id") or "")
    st.caption(f"ID `{cid[:8]}…`")
    pk = f"cust_ed_{cid}"

    st.markdown("##### Company")
    c1 = st.columns(1)[0]
    en = c1.text_input("Customer Name", value=str(row.get("customer_name") or ""), key=f"{pk}_name")

    c5, c6, c7, c8 = st.columns(4)
    eaddr = c5.text_input("Address", value=str(row.get("address") or ""), key=f"{pk}_addr")
    ecity = c6.text_input("City", value=str(row.get("city") or ""), key=f"{pk}_city")
    est = c7.text_input("State", value=str(row.get("state") or ""), key=f"{pk}_state")
    ezip = c8.text_input("ZIP", value=str(row.get("zip") or ""), key=f"{pk}_zip")

    ea = st.checkbox("Active", value=bool(row.get("is_active", True)), key=f"{pk}_active")

    u1, u2 = st.columns(2)
    with u1:
        if st.button("Update Customer", type="primary", use_container_width=True, key=f"{pk}_save"):
            if not str(en).strip():
                st.error("Customer Name required.")
                st.stop()
            update_rows(
                "customers",
                {
                    "customer_name": str(en).strip(),
                    "address": str(eaddr).strip(),
                    "city": str(ecity).strip(),
                    "state": str(est).strip(),
                    "zip": str(ezip).strip(),
                    "is_active": bool(ea),
                },
                {"id": row["id"]},
            )
            _clear_customer_mode()
            st.success("Customer updated.")
            st.rerun()
    with u2:
        if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
            _clear_customer_mode()
            st.rerun()

    st.markdown("---")
    _render_contacts_section(customer_row=row, can_edit=can_edit)


def _render_customer_side_panel(*, mode: str, existing_customer_names: set[str]) -> None:
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        if mode == "add":
            st.markdown("### Add customer")
            _render_add_form(existing_customer_names=existing_customer_names)
        elif mode == "edit":
            st.markdown("### Customer detail")
            eid = st.session_state.get("customer_edit_id")
            er = fetch_one("customers", {"id": eid}) if eid else None
            if not er:
                st.warning("Customer not found.")
                _clear_customer_mode()
            else:
                can_edit = current_role() in {"admin", "estimator"}
                _render_edit_form(er, can_edit=can_edit)


def _render_customers_main(*, df: pd.DataFrame, can_add: bool) -> None:
    if df.empty:
        st.info("No customers found.")
        if can_add:
            if st.button("Add Customer", type="primary", key="cust_empty_add"):
                st.session_state["customer_mode"] = "add"
                st.session_state.pop("customer_edit_id", None)
                _clear_contact_subpanel()
                st.rerun()
        return

    f1, f2 = st.columns([2, 1], gap="small")
    with f1:
        st.markdown(
            '<span class="ips-crud-filter-row-start" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        search = st.text_input(
            "Search",
            placeholder="Customer name, address, city, state, ZIP",
        )
    active_options = ["All", "Active only", "Inactive only"]
    selected_active = f2.selectbox("Status", active_options)

    filtered = df.copy()
    if "is_active" in filtered.columns:
        if selected_active == "Active only":
            filtered = filtered[filtered["is_active"] == True]  # noqa: E712
        elif selected_active == "Inactive only":
            filtered = filtered[filtered["is_active"] == False]  # noqa: E712

    if search.strip():
        s = search.strip().lower()
        mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
        filtered = filtered[mask.any(axis=1)]

    show_cols = [
        c
        for c in [
            "customer_name",
            "address",
            "city",
            "state",
            "zip",
            "is_active",
        ]
        if c in filtered.columns
    ]

    st.caption(
        "Checkbox column on the **left**; selection is stored as **selected_customers_ids**."
    )

    if filtered.empty:
        st.warning("No customers match your filters.")
        if can_add:
            inject_table_action_styles()
            if st.button("Add Customer", type="primary", key="cust_filtered_empty_add"):
                st.session_state["customer_mode"] = "add"
                st.session_state.pop("customer_edit_id", None)
                _clear_contact_subpanel()
                st.rerun()
    elif "id" not in filtered.columns:
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)
    else:
        bar_ph = st.empty()
        _, sel = render_selectable_dataframe(
            filtered,
            table_key=TABLE_KEY_CUSTOMERS,
            id_column="id",
            columns=show_cols,
            editor_key="cust_sel_editor",
        )
        with bar_ph.container():
            _render_action_buttons(sel=sel, can_add=can_add)


def render_customers() -> None:
    render_header("Customers")
    render_crud_list_subtitle("Manage customer companies and billing addresses. Contacts are stored per company.")

    can_add = current_role() in {"admin", "estimator"}
    mode = st.session_state.get("customer_mode")

    try:
        rows = fetch_table("customers", limit=5000, order_by="customer_name")
    except Exception:
        rows = []
    df = pd.DataFrame(rows)

    _cust_del_open = destructive_confirm_open_key(_CUST_DELETE_CONFIRM_PREFIX)
    if st.session_state.get(_cust_del_open) and not can_add:
        close_destructive_confirmation(_CUST_DELETE_CONFIRM_PREFIX)
        st.session_state.pop("customers_pending_delete_ids", None)
    elif st.session_state.get(_cust_del_open) and can_add:
        pending = list(st.session_state.get("customers_pending_delete_ids") or [])
        if not pending:
            close_destructive_confirmation(_CUST_DELETE_CONFIRM_PREFIX)
            st.session_state.pop("customers_pending_delete_ids", None)
            st.rerun()
        id_to_name: dict[str, str] = {}
        if not df.empty and "id" in df.columns:
            for _, r in df.iterrows():
                rid = str(r["id"])
                id_to_name[rid] = str(r.get("customer_name") or "").strip() or rid
        name_lines: list[str] = []
        for pid in pending:
            nm = id_to_name.get(pid)
            if nm:
                name_lines.append(nm)
            else:
                short = pid[:10] + "…" if len(pid) > 10 else pid
                name_lines.append(f"(unknown id) {short}")
        n_pending = len(pending)
        msg = (
            "Are you sure you want to delete this customer?"
            if n_pending == 1
            else f"Are you sure you want to delete these {n_pending} customers?"
        )

        def _on_confirm_delete() -> None:
            for cid in pending:
                try:
                    delete_rows_admin("customers", {"id": cid})
                except Exception as exc:
                    st.error(f"Could not delete {cid}: {exc}")
            st.session_state.pop("customers_pending_delete_ids", None)
            clear_selected_ids(TABLE_KEY_CUSTOMERS)
            edit_id = st.session_state.get("customer_edit_id")
            if edit_id and str(edit_id) in {str(x) for x in pending}:
                _clear_customer_mode()
            st.success("Customer(s) deleted where permitted.")

        def _on_cancel_delete() -> None:
            st.session_state.pop("customers_pending_delete_ids", None)

        render_destructive_confirmation(
            key_prefix=_CUST_DELETE_CONFIRM_PREFIX,
            title="Confirm Delete",
            message=msg,
            confirm_label="Confirm Delete",
            cancel_label="Cancel",
            on_confirm=_on_confirm_delete,
            on_cancel=_on_cancel_delete,
            name_lines=name_lines,
        )

    _ct_del_open = destructive_confirm_open_key(_CONTACT_DELETE_PREFIX)
    if st.session_state.get(_ct_del_open) and not can_add:
        close_destructive_confirmation(_CONTACT_DELETE_PREFIX)
        st.session_state.pop("customer_contact_pending_delete_ids", None)
    elif st.session_state.get(_ct_del_open) and can_add:
        pending_ct = list(st.session_state.get("customer_contact_pending_delete_ids") or [])
        if not pending_ct:
            close_destructive_confirmation(_CONTACT_DELETE_PREFIX)
            st.session_state.pop("customer_contact_pending_delete_ids", None)
            st.rerun()

        def _on_confirm_ct_delete() -> None:
            for x in pending_ct:
                try:
                    delete_contact(str(x))
                except Exception as exc:
                    st.error(f"Could not delete contact {x}: {exc}")
            st.session_state.pop("customer_contact_pending_delete_ids", None)
            _clear_contact_subpanel()
            st.success("Contact(s) deleted where permitted.")

        def _on_cancel_ct_delete() -> None:
            st.session_state.pop("customer_contact_pending_delete_ids", None)

        render_destructive_confirmation(
            key_prefix=_CONTACT_DELETE_PREFIX,
            title="Confirm Delete",
            message="Delete this contact? Estimates/jobs referencing it will clear the contact link.",
            confirm_label="Confirm Delete",
            cancel_label="Cancel",
            on_confirm=_on_confirm_ct_delete,
            on_cancel=_on_cancel_ct_delete,
            name_lines=[str(x)[:12] + "…" for x in pending_ct],
        )

    if st.session_state.pop("_cust_do_deactivate", False) and can_add:
        sel_ids = get_selected_ids(TABLE_KEY_CUSTOMERS)
        if sel_ids:
            for cid in sel_ids:
                try:
                    update_rows("customers", {"is_active": False}, {"id": cid})
                except Exception as exc:
                    st.error(f"Could not deactivate {cid}: {exc}")
            clear_selected_ids(TABLE_KEY_CUSTOMERS)
            st.success("Selected customers deactivated.")
            st.rerun()

    panel_open = bool(can_add and mode in ("add", "edit"))

    existing_names: set[str] = set()
    if not df.empty and "customer_name" in df.columns:
        for _, c in df.iterrows():
            nm = str(c.get("customer_name", "")).strip().upper()
            if nm:
                existing_names.add(nm)

    if panel_open:
        main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
        with main_col:
            _render_customers_main(df=df, can_add=can_add)
        with side_col:
            _render_customer_side_panel(mode=str(mode), existing_customer_names=existing_names)
    else:
        _render_customers_main(df=df, can_add=can_add)

    if not can_add:
        st.info("Only admin or estimator users can manage customers.")
