from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from auth import current_role
from db import (
    delete_rows_admin,
    fetch_by_match,
    fetch_by_match_admin,
    fetch_one,
    fetch_table_admin,
    fetch_table_with_order_fallback,
    insert_row_admin,
    update_rows_admin,
)

try:
    from services.customer_contacts import (
        delete_contact,
        insert_contact_row,
        set_primary_contact,
    )
except ImportError:
    from app.services.customer_contacts import (  # type: ignore
        delete_contact,
        insert_contact_row,
        set_primary_contact,
    )

from app.confirm_delete import (
    close_destructive_confirmation,
    destructive_confirm_open_key,
    open_destructive_confirmation,
)
from app.ips_crud_list_styles import inject_ips_modal_styles
from app.table_actions import (
    TABLE_KEY_CUSTOMERS,
    clear_selected_ids,
    get_selected_ids,
    inject_table_action_styles,
    set_selected_ids,
)
from app.ui.crud_actions import render_standard_toolbar
from app.ui.crud_confirm import render_delete_confirm
from app.ui.crud_detail import render_side_detail_panel
from app.ui.crud_filters import (
    apply_boolean_status_filter,
    apply_text_search,
    render_search_box,
    render_status_filter,
)
from app.ui.crud_framework import render_crud_page
from app.ui.crud_table import render_crud_table

_CUST_DELETE_CONFIRM_PREFIX = "customers_delete"
_CONTACT_DELETE_PREFIX = "customer_contact_delete"

# --- customers table: logical fields → possible physical column names (first match in DB wins) ---
_CUSTOMER_NAME_KEYS: tuple[str, ...] = ("customer_name", "name", "company_name")
_ADDRESS_KEYS: tuple[str, ...] = ("address", "street_address", "address_line1", "line1")
_CITY_KEYS: tuple[str, ...] = ("city",)
_STATE_KEYS: tuple[str, ...] = ("state", "region", "province")
_ZIP_KEYS: tuple[str, ...] = ("zip", "zip_code", "postal_code", "postcode")
_IS_ACTIVE_KEYS: tuple[str, ...] = ("is_active",)

_LOGICAL_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("customer_name", _CUSTOMER_NAME_KEYS),
    ("address", _ADDRESS_KEYS),
    ("city", _CITY_KEYS),
    ("state", _STATE_KEYS),
    ("zip", _ZIP_KEYS),
    ("is_active", _IS_ACTIVE_KEYS),
)

_MAX_CUSTOMER_NAME_LEN = 500
# Reasonable upper bound for single-line address fragments (DB is typically text).
_MAX_ADDRESS_FIELD_LEN = 2000


def _fetch_customers_list_rows(*, admin_read: bool) -> list[dict[str, Any]]:
    """Admin/pm uses service-role reads so rows written with admin policies stay visible (RLS)."""
    if admin_read:
        try:
            return fetch_table_admin("customers", limit=5000, order_by="customer_name")
        except Exception:
            return fetch_table_admin("customers", limit=5000, order_by=None)
    return fetch_table_with_order_fallback("customers", limit=5000, order_by="customer_name")


def _fetch_one_row(
    table_name: str,
    match: dict[str, Any],
    *,
    admin_read: bool,
) -> dict[str, Any] | None:
    if admin_read:
        rows = fetch_by_match_admin(table_name, match, limit=1)
        return rows[0] if rows else None
    return fetch_one(table_name, match)


def _fetch_contacts_for_customer_row(
    customer_id: str,
    *,
    admin_read: bool,
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    """Same ordering as ``fetch_contacts_for_customer`` but optional admin read for internal roles."""
    cid = str(customer_id or "").strip()
    if not cid:
        return []
    try:
        if admin_read:
            rows = fetch_by_match_admin("customer_contacts", {"customer_id": cid}, limit=500)
        else:
            rows = fetch_by_match("customer_contacts", {"customer_id": cid}, limit=500)
    except Exception:
        return []
    rows = list(rows or [])
    if not include_inactive:
        rows = [r for r in rows if bool(r.get("is_active", True))]

    def _sort_key(r: dict) -> tuple:
        prim = 0 if r.get("is_primary") else 1
        name = str(r.get("contact_name") or "").strip().lower()
        return (prim, name)

    rows.sort(key=_sort_key)
    return rows


def _contact_row_union_keys(contacts: list[dict]) -> set[str]:
    u: set[str] = set()
    for c in contacts:
        if isinstance(c, dict):
            u |= {str(k) for k in c.keys()}
    return u


def _contact_title_display(ct: dict) -> str:
    return str(ct.get("title") or ct.get("role") or "").strip()


def _contact_schema_keys(contacts: list[dict], edit_row: dict | None) -> set[str]:
    keys = _contact_row_union_keys(contacts)
    if isinstance(edit_row, dict):
        keys |= {str(k) for k in edit_row.keys()}
    return keys


def _build_contact_write_pair(
    *,
    contact_name: str,
    title_text: str,
    email: str,
    phone: str,
    mobile: str,
    notes: str,
    is_active: bool,
    is_primary: bool,
    customer_id: str | None,
    schema_keys: set[str],
    customer_location_id: str | None = None,
    set_customer_location_id: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    tt = str(title_text or "").strip()
    mob = str(mobile or "").strip()
    minimal: dict[str, Any] = {
        "contact_name": str(contact_name or "").strip(),
        "role": tt,
        "email": str(email or "").strip(),
        "phone": str(phone or "").strip(),
        "notes": str(notes or "").strip(),
        "is_active": bool(is_active),
        "is_primary": bool(is_primary),
    }
    if customer_id is not None:
        minimal["customer_id"] = str(customer_id).strip()
    full = dict(minimal)
    if "title" in schema_keys:
        full["title"] = tt
    if "mobile" in schema_keys:
        full["mobile"] = mob
    if set_customer_location_id:
        loc = str(customer_location_id or "").strip()
        full["customer_location_id"] = loc if loc else None
        minimal["customer_location_id"] = loc if loc else None
    return full, minimal


def _contacts_filtered_by_scope(
    rows: list[dict[str, Any]],
    scope_location_id: str | None,
) -> list[dict[str, Any]]:
    """``scope_location_id`` ``None`` = company-wide only (no site). Else match that site."""
    if scope_location_id is None:
        return [r for r in rows if not str(r.get("customer_location_id") or "").strip()]
    lid = str(scope_location_id).strip()
    return [r for r in rows if str(r.get("customer_location_id") or "").strip() == lid]


def _insert_contact_pair(full: dict[str, Any], minimal: dict[str, Any]) -> dict[str, Any]:
    try:
        return insert_contact_row(full)
    except Exception:
        try:
            ff = {k: v for k, v in full.items() if k != "customer_location_id"}
            mm = {k: v for k, v in minimal.items() if k != "customer_location_id"}
            return insert_contact_row(ff)
        except Exception:
            return insert_contact_row(minimal)


def _update_contact_pair(contact_id: str, full: dict[str, Any], minimal: dict[str, Any]) -> None:
    try:
        update_rows_admin("customer_contacts", full, {"id": contact_id})
    except Exception:
        update_rows_admin("customer_contacts", minimal, {"id": contact_id})


def _default_available_columns() -> set[str]:
    """When no rows exist yet, assume canonical IPS column names."""
    return {
        "id",
        _CUSTOMER_NAME_KEYS[0],
        _ADDRESS_KEYS[0],
        _CITY_KEYS[0],
        _STATE_KEYS[0],
        _ZIP_KEYS[0],
        _IS_ACTIVE_KEYS[0],
    }


def _infer_available_columns(df: pd.DataFrame, rows: list[dict[str, Any]]) -> set[str]:
    if not df.empty and len(df.columns):
        return set(df.columns.astype(str).tolist())
    if rows:
        return set(rows[0].keys())
    return _default_available_columns()


def _pick_physical(candidates: tuple[str, ...], available: set[str]) -> str:
    for c in candidates:
        if c in available:
            return c
    return candidates[0]


def _resolve_customer_columns(available: set[str]) -> dict[str, str]:
    """Map logical UI field names to actual table column names for this environment."""
    return {logical: _pick_physical(cands, available) for logical, cands in _LOGICAL_KEYS}


def _get_customer_field(row: dict[str, Any], logical: str, resolved: dict[str, str]) -> str:
    """Read a value from a row, tolerating legacy/alternate column names."""
    primary = resolved.get(logical)
    if primary and primary in row and row[primary] is not None:
        return str(row[primary]).strip()
    candidates = next((c for log, c in _LOGICAL_KEYS if log == logical), ())
    for c in candidates:
        if c in row and row[c] is not None:
            return str(row[c]).strip()
    return ""


def _build_customer_write_payload(
    *,
    customer_name: str,
    address: str,
    city: str,
    state: str,
    zip_value: str,
    is_active: bool | None,
    resolved: dict[str, str],
    available: set[str],
) -> dict[str, Any]:
    """Build insert/update payload using only columns that exist in the current schema."""
    payload: dict[str, Any] = {}
    name_col = resolved["customer_name"]
    if name_col not in available:
        raise ValueError("customers table has no recognized name column (expected customer_name or equivalent).")
    payload[name_col] = customer_name.strip()

    for logical, raw in (
        ("address", address),
        ("city", city),
        ("state", state),
        ("zip", zip_value),
    ):
        col = resolved[logical]
        if col in available:
            payload[col] = str(raw).strip()

    if is_active is not None and resolved["is_active"] in available:
        payload[resolved["is_active"]] = bool(is_active)

    return payload


def _validate_customer_name_text(name: str) -> str | None:
    t = str(name or "").strip()
    if not t:
        return "Customer name is required."
    if len(t) > _MAX_CUSTOMER_NAME_LEN:
        return f"Customer name is too long (max {_MAX_CUSTOMER_NAME_LEN} characters)."
    return None


def _validate_address_field(label: str, value: str) -> str | None:
    s = str(value or "")
    if len(s) > _MAX_ADDRESS_FIELD_LEN:
        return f"{label} is too long (max {_MAX_ADDRESS_FIELD_LEN} characters)."
    return None


def _friendly_customer_db_message(exc: BaseException) -> str:
    chain: list[str] = []
    cur: BaseException | None = exc
    depth = 0
    while cur is not None and depth < 10:
        chain.append(str(cur).lower())
        cur = getattr(cur, "__cause__", None) or getattr(cur, "__context__", None)
        depth += 1
    blob = " ".join(chain)

    if "permission" in blob or "rls" in blob or "policy" in blob or "42501" in blob:
        return "Saving was blocked by database permissions or RLS. Sign in as a user allowed to change customers."
    if "unique" in blob or "duplicate" in blob:
        return "This change conflicts with an existing row (duplicate value or unique constraint)."
    if "null value" in blob or "not null" in blob:
        return "A required database column was empty. Check customer name and address fields."
    if "column" in blob and ("does not exist" in blob or "unknown" in blob):
        return (
            "A column name in the request does not match this database. "
            "Compare your `customers` table with the app (address / ZIP column names)."
        )
    return "Could not save the customer. See **Technical details** below."


# --- IPS modal layout (st.dialog): header (title + subtitle/hint) | compact body | divider | footer (spacer | Cancel | Save) ---


def _ips_modal_subtitle(text: str) -> None:
    """IPS modal: short line under the dialog title (styled via inject_ips_modal_styles)."""
    inject_ips_modal_styles()
    st.markdown(
        f'<p class="ips-modal-subtitle">{html.escape(text)}</p>',
        unsafe_allow_html=True,
    )


def _ips_modal_hint(text: str) -> None:
    """IPS modal: smaller secondary note (e.g. schema limitations)."""
    inject_ips_modal_styles()
    st.markdown(
        f'<p class="ips-modal-hint">{html.escape(text)}</p>',
        unsafe_allow_html=True,
    )


def _ips_modal_header(*, subtitle: str | None = None, hint: str | None = None) -> None:
    """IPS modal header: optional helper + hint under the ``@st.dialog`` title."""
    if subtitle:
        _ips_modal_subtitle(subtitle)
    if hint:
        _ips_modal_hint(hint)


@st.dialog("Add Customer", width="small")
def _add_customer_dialog(
    *,
    existing_customer_names: set[str],
    resolved: dict[str, str],
    available: set[str],
) -> None:
    # --- header: @st.dialog title + subtitle / hint ---
    _ips_modal_header(
        subtitle="Company name is required · address optional",
        hint=(
            "No `is_active` column on this database — table default applies."
            if resolved["is_active"] not in available
            else None
        ),
    )

    with st.form("dlg_customer_add_form_v1", clear_on_submit=False):
        r0a, r0b = st.columns([2, 1], gap="small")
        with r0a:
            customer_name = st.text_input("Customer name", key="dlg_cust_add_name")
        with r0b:
            is_active_customer = st.checkbox("Active", value=True, key="dlg_cust_add_active")

        a1, a2 = st.columns(2, gap="small")
        with a1:
            address = st.text_input("Address", key="dlg_cust_add_addr")
            city = st.text_input("City", key="dlg_cust_add_city")
        with a2:
            state = st.text_input("State", key="dlg_cust_add_state")
            zip_code = st.text_input("ZIP", key="dlg_cust_add_zip")

        save = st.form_submit_button("Save", type="primary", use_container_width=True)

    if st.button("Cancel", type="secondary", use_container_width=True, key="dlg_cust_add_cancel"):
        st.rerun()

    if save:
        err = _validate_customer_name_text(customer_name)
        if err:
            st.error(err)
            st.stop()
        name_upper = str(customer_name).strip().upper()
        if name_upper in existing_customer_names:
            st.error("A customer with this name already exists.")
            st.stop()
        for label, val in (
            ("Address", address),
            ("City", city),
            ("State", state),
            ("ZIP", zip_code),
        ):
            ve = _validate_address_field(label, str(val))
            if ve:
                st.error(ve)
                st.stop()

        active_val: bool | None = bool(is_active_customer) if resolved["is_active"] in available else None
        try:
            payload = _build_customer_write_payload(
                customer_name=str(customer_name).strip(),
                address=str(address).strip(),
                city=str(city).strip(),
                state=str(state).strip(),
                zip_value=str(zip_code).strip(),
                is_active=active_val,
                resolved=resolved,
                available=available,
            )
            inserted = insert_row_admin("customers", payload)
        except Exception as exc:
            st.error(_friendly_customer_db_message(exc))
            with st.expander("Technical details"):
                st.code(repr(exc), language="text")
            st.stop()

        new_id = str((inserted or {}).get("id") or "").strip()
        st.session_state.pop("customer_contact_mode", None)
        st.session_state.pop("customer_contact_edit_id", None)
        st.session_state.pop("customer_contact_selected_id", None)
        if new_id:
            st.session_state["customer_mode"] = "edit"
            st.session_state["customer_edit_id"] = new_id
            set_selected_ids(TABLE_KEY_CUSTOMERS, [new_id])
        st.toast("Customer added.", icon="✅")
        st.rerun()


@st.dialog("Add Contact", width="small")
def _add_contact_dialog(
    cid: str,
    admin_read: bool,
    *,
    customer_location_id: str | None = None,
    set_customer_location_id: bool = False,
) -> None:
    loc_part = str(customer_location_id or "cw")
    key_show_inact = f"cust_ct_show_inactive_{cid}"
    load_inactive = bool(st.session_state.get(key_show_inact, False))
    contacts = _fetch_contacts_for_customer_row(cid, admin_read=admin_read, include_inactive=load_inactive)
    schema_keys = _contact_schema_keys(contacts, None)
    if set_customer_location_id:
        schema_keys = set(schema_keys) | {"customer_location_id"}
    pk = f"dlg_ct_{cid}_{loc_part}"

    # --- header: @st.dialog title + subtitle ---
    sub = (
        "New contact for this job site (saved with location link)."
        if customer_location_id
        else "New row in customer_contacts · company-wide · primary and active optional"
    )
    _ips_modal_header(subtitle=sub)

    with st.form(f"dlg_contact_add_form_{cid}_{loc_part}", clear_on_submit=False):
        r1a, r1b = st.columns(2, gap="small")
        with r1a:
            cn = st.text_input("Contact name", key=f"{pk}_name")
        with r1b:
            tl = st.text_input(
                "Title",
                key=f"{pk}_title",
                help="Job title or role (saved to title + role when supported)",
            )
        r2a, r2b = st.columns(2, gap="small")
        with r2a:
            em = st.text_input("Email", key=f"{pk}_email")
        with r2b:
            ph = st.text_input("Phone", key=f"{pk}_phone")
        r3a, r3b = st.columns(2, gap="small")
        with r3a:
            mob = st.text_input("Mobile", key=f"{pk}_mobile")
        with r3b:
            nt = st.text_area("Notes", key=f"{pk}_notes", height=56)
        r4a, r4b = st.columns(2, gap="small")
        with r4a:
            pr = st.checkbox("Primary contact", value=False, key=f"{pk}_prim")
        with r4b:
            act = st.checkbox("Active", value=True, key=f"{pk}_act")

        save = st.form_submit_button("Save", type="primary", use_container_width=True)

    if st.button("Cancel", type="secondary", use_container_width=True, key=f"{pk}_cancel"):
        st.rerun()

    if save:
        t = str(cn or "").strip()
        if not t:
            st.error("Contact name is required.")
            st.stop()
        pr_b = bool(pr)
        act_b = bool(act)
        if pr_b and not act_b:
            st.warning("Inactive contacts cannot be primary — saving without primary flag.")
            pr_b = False
        full, minimal = _build_contact_write_pair(
            contact_name=t,
            title_text=str(tl or ""),
            email=str(em or ""),
            phone=str(ph or ""),
            mobile=str(mob or ""),
            notes=str(nt or ""),
            is_active=act_b,
            is_primary=False,
            customer_id=cid,
            schema_keys=schema_keys,
            customer_location_id=str(customer_location_id).strip() if customer_location_id else None,
            set_customer_location_id=set_customer_location_id,
        )
        try:
            inserted = _insert_contact_pair(full, minimal)
        except Exception as exc:
            st.error("Could not save the contact.")
            with st.expander("Technical details"):
                st.code(repr(exc), language="text")
            st.stop()
        new_id = str((inserted or {}).get("id") or "")
        if pr_b and new_id:
            set_primary_contact(customer_id=cid, contact_id=new_id)
        st.session_state.pop("customer_contact_mode", None)
        st.session_state.pop("customer_contact_edit_id", None)
        if new_id:
            st.session_state["customer_contact_selected_id"] = new_id
        st.toast("Contact added.", icon="✅")
        st.rerun()


@st.dialog("Add Location", width="small")
def _add_location_dialog(cid: str) -> None:
    pk = f"dlg_loc_{cid}"
    _ips_modal_header(subtitle="Job site / ship-to address for this customer")
    with st.form(f"dlg_location_add_form_{cid}", clear_on_submit=False):
        nm = st.text_input("Location name", key=f"{pk}_name")
        ad = st.text_input("Address", key=f"{pk}_addr")
        r1a, r1b = st.columns(2, gap="small")
        with r1a:
            city = st.text_input("City", key=f"{pk}_city")
            stt = st.text_input("State", key=f"{pk}_state")
        with r1b:
            zip_c = st.text_input("ZIP", key=f"{pk}_zip")
        act = st.checkbox("Active", value=True, key=f"{pk}_act")
        save = st.form_submit_button("Save", type="primary", use_container_width=True)

    if st.button("Cancel", type="secondary", use_container_width=True, key=f"{pk}_cancel"):
        st.rerun()

    if save:
        t = str(nm or "").strip()
        if not t:
            st.error("Location name is required.")
            st.stop()
        try:
            insert_row_admin(
                "customer_locations",
                {
                    "customer_id": str(cid).strip(),
                    "location_name": t,
                    "address": str(ad or "").strip(),
                    "city": str(city or "").strip(),
                    "state": str(stt or "").strip(),
                    "zip": str(zip_c or "").strip(),
                    "is_active": bool(act),
                },
            )
        except Exception as exc:
            st.error("Could not save the location.")
            with st.expander("Technical details"):
                st.code(repr(exc), language="text")
            st.stop()
        st.session_state.pop("customer_location_mode", None)
        st.session_state.pop("customer_location_edit_id", None)
        st.toast("Location added.", icon="✅")
        st.rerun()


def _fetch_locations_for_customer_row(
    customer_id: str,
    *,
    admin_read: bool,
    include_inactive: bool,
) -> list[dict[str, Any]]:
    try:
        from services.customer_locations import fetch_locations_for_customer
    except ImportError:
        from app.services.customer_locations import fetch_locations_for_customer  # type: ignore

    return fetch_locations_for_customer(
        customer_id,
        admin_read=admin_read,
        include_inactive=include_inactive,
    )


def _clear_customer_mode() -> None:
    st.session_state.pop("customer_mode", None)
    st.session_state.pop("customer_edit_id", None)
    st.session_state.pop("customer_contact_mode", None)
    st.session_state.pop("customer_contact_edit_id", None)
    st.session_state.pop("customer_contact_selected_id", None)
    st.session_state.pop("customer_location_mode", None)
    st.session_state.pop("customer_location_edit_id", None)
    st.session_state.pop("customer_location_selected_id", None)
    st.session_state.pop("customer_location_pending_delete", None)


def _clear_contact_subpanel() -> None:
    st.session_state.pop("customer_contact_mode", None)
    st.session_state.pop("customer_contact_edit_id", None)
    st.session_state.pop("customer_contact_selected_id", None)


def _clear_location_subpanel() -> None:
    st.session_state.pop("customer_location_mode", None)
    st.session_state.pop("customer_location_edit_id", None)
    st.session_state.pop("customer_location_selected_id", None)
    st.session_state.pop("customer_location_pending_delete", None)


def _on_contact_pick_changed(cid: str, ctid: str, wkey: str) -> None:
    """Single-select: checked row becomes ``customer_contact_selected_id``; uncheck clears if same."""
    sel_key = "customer_contact_selected_id"
    prefix = f"cust_ct_pick_{cid}_"
    if st.session_state.get(wkey):
        st.session_state[sel_key] = ctid
        for k in list(st.session_state.keys()):
            if isinstance(k, str) and k.startswith(prefix) and k != wkey:
                st.session_state[k] = False
    else:
        if str(st.session_state.get(sel_key) or "") == ctid:
            st.session_state[sel_key] = None


def _contact_row_by_id(contacts: list[dict[str, Any]], ctid: str) -> dict[str, Any] | None:
    for c in contacts:
        if str(c.get("id") or "") == str(ctid):
            return c
    return None


def _on_location_pick_changed(cid: str, lid: str, wkey: str) -> None:
    sel_key = "customer_location_selected_id"
    prefix = f"cust_loc_pick_{cid}_"
    if st.session_state.get(wkey):
        st.session_state[sel_key] = lid
        for k in list(st.session_state.keys()):
            if isinstance(k, str) and k.startswith(prefix) and k != wkey:
                st.session_state[k] = False
    else:
        if str(st.session_state.get(sel_key) or "") == lid:
            st.session_state[sel_key] = None


def _location_row_by_id(locations: list[dict[str, Any]], lid: str) -> dict[str, Any] | None:
    for x in locations:
        if str(x.get("id") or "") == str(lid):
            return x
    return None


def _render_locations_section(*, customer_row: dict, can_edit: bool, admin_read: bool) -> None:
    cid = str(customer_row.get("id") or "")
    if not cid:
        return

    sel_key = "customer_location_selected_id"
    pend_key = "customer_location_pending_delete"

    st.markdown("##### Locations")
    st.caption("Job sites used on **Estimates** and **Jobs** (separate from the company address above).")

    mode = st.session_state.get("customer_location_mode")
    edit_raw = st.session_state.get("customer_location_edit_id")
    edit_id = str(edit_raw or "").strip() or None

    key_show_inact = f"cust_loc_show_inactive_{cid}"
    st.session_state.setdefault(key_show_inact, False)
    st.checkbox("Show inactive locations", key=key_show_inact)

    load_inactive = bool(st.session_state.get(key_show_inact, False) or (mode == "edit" and bool(edit_id)))
    locs = _fetch_locations_for_customer_row(cid, admin_read=admin_read, include_inactive=load_inactive)

    edit_row: dict[str, Any] | None = None
    if mode == "edit" and edit_id:
        edit_row = _location_row_by_id(locs, edit_id)
        if not edit_row:
            er = _fetch_one_row("customer_locations", {"id": edit_id}, admin_read=admin_read)
            if er and str(er.get("customer_id") or "") == cid:
                edit_row = er
                locs = [er] + [x for x in locs if str(x.get("id") or "") != edit_id]
            else:
                _clear_location_subpanel()
                st.warning("That location is not on this company.")
                st.rerun()
                return

    sid = str(st.session_state.get(sel_key) or "").strip()
    if sid and not any(str(x.get("id") or "") == sid for x in locs):
        st.session_state.pop(sel_key, None)
        sid = ""
    if mode == "edit" and edit_id:
        st.session_state[sel_key] = str(edit_id)

    pend = st.session_state.get(pend_key)
    if isinstance(pend, dict) and str(pend.get("cid") or "") == cid and str(pend.get("lid") or "").strip():
        plid = str(pend.get("lid") or "").strip()
        st.warning("Delete this location? Estimates or jobs that reference it will clear the site link (FK).")
        pc1, pc2 = st.columns(2)
        with pc1:
            if st.button("Confirm delete", type="primary", use_container_width=True, key=f"cust_loc_conf_{cid}"):
                try:
                    delete_rows_admin("customer_locations", {"id": plid})
                except Exception as exc:
                    st.error(f"Could not delete: {exc}")
                    st.stop()
                st.session_state.pop(pend_key, None)
                st.session_state.pop(sel_key, None)
                _clear_location_subpanel()
                st.success("Location deleted.")
                st.rerun()
        with pc2:
            if st.button("Cancel", use_container_width=True, key=f"cust_loc_canc_{cid}"):
                st.session_state.pop(pend_key, None)
                st.rerun()

    if can_edit:
        if st.button("Add Location", type="primary", use_container_width=True, key=f"cust_loc_add_{cid}"):
            _add_location_dialog(cid)

    if not locs:
        st.caption("No locations yet. Use **Add Location** (editors) to create a site.")
    else:
        for loc in locs:
            lid = str(loc.get("id") or "")
            nm = str(loc.get("location_name") or "").strip() or "—"
            addr = str(loc.get("address") or "").strip()
            city = str(loc.get("city") or "").strip()
            stt = str(loc.get("state") or "").strip()
            zp = str(loc.get("zip") or "").strip()
            tail = ", ".join(x for x in (addr, city, stt, zp) if x)
            line = f"**{html.escape(nm)}**"
            if tail:
                line += f" · {html.escape(tail)}"
            badges: list[str] = []
            if not bool(loc.get("is_active", True)):
                badges.append("Inactive")
            badge_s = " · ".join(badges)
            full_line = line + (f" · *{badge_s}*" if badge_s else "")

            if can_edit and lid:
                wkey = f"cust_loc_pick_{cid}_{lid}"
                sel_now = str(st.session_state.get(sel_key) or "")
                st.session_state[wkey] = sel_now == lid
                chk_col, body_col = st.columns([0.055, 0.945], gap="small")
                with chk_col:
                    st.checkbox(
                        "Select",
                        key=wkey,
                        on_change=_on_location_pick_changed,
                        args=(cid, lid, wkey),
                        label_visibility="collapsed",
                    )
                with body_col:
                    with st.container(border=True):
                        st.markdown(full_line, unsafe_allow_html=True)
                        if lid:
                            _render_location_contacts_block(
                                customer_id=cid,
                                location_id=lid,
                                location_name=nm,
                                can_edit=can_edit,
                                admin_read=admin_read,
                            )
            else:
                with st.container(border=True):
                    st.markdown(full_line, unsafe_allow_html=True)
                    if lid:
                        _render_location_contacts_block(
                            customer_id=cid,
                            location_id=lid,
                            location_name=nm,
                            can_edit=False,
                            admin_read=admin_read,
                        )

        if can_edit and locs:
            pick = str(st.session_state.get(sel_key) or "").strip()
            picked_row = _location_row_by_id(locs, pick) if pick else None
            if pick and picked_row is None:
                st.session_state.pop(sel_key, None)
                pick = ""
                picked_row = None

            st.caption("Select **one** location for **Edit** or **Delete**.")
            with st.container(border=True):
                r1a, r1b = st.columns(2, gap="small")
                with r1a:
                    if st.button(
                        "Edit Location",
                        type="primary",
                        use_container_width=True,
                        disabled=not pick,
                        key=f"cust_loc_tool_edit_{cid}",
                    ):
                        if not pick or _location_row_by_id(locs, pick) is None:
                            st.error("Select a location first.")
                            st.stop()
                        st.session_state["customer_location_mode"] = "edit"
                        st.session_state["customer_location_edit_id"] = pick
                        st.rerun()
                with r1b:
                    if st.button(
                        "Delete",
                        type="secondary",
                        use_container_width=True,
                        disabled=not pick,
                        key=f"cust_loc_tool_del_{cid}",
                    ):
                        if not pick or _location_row_by_id(locs, pick) is None:
                            st.error("Select a location first.")
                            st.stop()
                        st.session_state[pend_key] = {"cid": cid, "lid": pick}
                        st.rerun()

    if not can_edit:
        return

    if mode == "edit" and edit_id and edit_row:
        st.markdown("**Edit location**")
        pk = f"cust_loc_ed_{edit_id}"
        er = edit_row
        with st.form(f"cust_location_edit_form_{edit_id}", clear_on_submit=False):
            nm = st.text_input("Location name", value=str(er.get("location_name") or ""), key=f"{pk}_name")
            ad = st.text_input("Address", value=str(er.get("address") or ""), key=f"{pk}_addr")
            c1, c2 = st.columns(2)
            with c1:
                city = st.text_input("City", value=str(er.get("city") or ""), key=f"{pk}_city")
                stt = st.text_input("State", value=str(er.get("state") or ""), key=f"{pk}_state")
            with c2:
                zp = st.text_input("ZIP", value=str(er.get("zip") or ""), key=f"{pk}_zip")
            act = st.checkbox("Active", value=bool(er.get("is_active", True)), key=f"{pk}_act")
            submitted = st.form_submit_button("Update location", type="primary", use_container_width=True)

        if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
            _clear_location_subpanel()
            st.rerun()

        if submitted:
            t = str(nm or "").strip()
            if not t:
                st.error("Location name is required.")
                st.stop()
            try:
                update_rows_admin(
                    "customer_locations",
                    {
                        "location_name": t,
                        "address": str(ad or "").strip(),
                        "city": str(city or "").strip(),
                        "state": str(stt or "").strip(),
                        "zip": str(zp or "").strip(),
                        "is_active": bool(act),
                    },
                    {"id": er["id"]},
                )
            except Exception as exc:
                st.error("Could not update the location.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")
                st.stop()
            _clear_location_subpanel()
            st.success("Location updated.")
            st.rerun()


def _render_contacts_section(*, customer_row: dict, can_edit: bool, admin_read: bool) -> None:
    cid = str(customer_row.get("id") or "")
    if not cid:
        return

    sel_key = "customer_contact_selected_id"

    st.markdown("##### Company-wide contacts")
    st.caption(
        "People for the account when no job site applies (or as fallback). Site-specific contacts live under **Locations** below."
    )

    mode = st.session_state.get("customer_contact_mode")
    edit_ct_raw = st.session_state.get("customer_contact_edit_id")
    edit_ct = str(edit_ct_raw or "").strip() or None

    edit_row: dict[str, Any] | None = None
    if mode == "edit" and edit_ct:
        edit_row = _fetch_one_row("customer_contacts", {"id": edit_ct}, admin_read=admin_read)
        if not edit_row or str(edit_row.get("customer_id") or "") != cid:
            _clear_contact_subpanel()
            st.warning("That contact is not on this company.")
            st.rerun()
            return

    key_show_inact = f"cust_ct_show_inactive_{cid}"
    st.session_state.setdefault(key_show_inact, False)
    st.checkbox("Show inactive contacts", key=key_show_inact)

    load_inactive = bool(st.session_state.get(key_show_inact, False) or (mode == "edit" and bool(edit_ct)))
    all_contacts = _fetch_contacts_for_customer_row(cid, admin_read=admin_read, include_inactive=load_inactive)
    contacts = _contacts_filtered_by_scope(all_contacts, None)
    schema_keys = _contact_schema_keys(all_contacts, edit_row)
    schema_keys = set(schema_keys) | {"customer_location_id"}

    sid = str(st.session_state.get(sel_key) or "").strip()
    if sid and not any(str(c.get("id") or "") == sid for c in contacts):
        st.session_state.pop(sel_key, None)
        sid = ""
    if mode == "edit" and edit_ct:
        st.session_state[sel_key] = str(edit_ct)

    if can_edit:
        if st.button("Add Contact", type="primary", use_container_width=True, key=f"cust_ct_add_{cid}"):
            _add_contact_dialog(
                cid,
                admin_read,
                customer_location_id=None,
                set_customer_location_id=True,
            )

    if not contacts:
        st.caption("No contacts yet. Use **Add Contact** (editors) or add from the list once this company is saved.")
    else:
        for ct in contacts:
            ctid = str(ct.get("id") or "")
            nm = str(ct.get("contact_name") or "").strip() or "—"
            title = _contact_title_display(ct)
            em = str(ct.get("email") or "").strip()
            ph = str(ct.get("phone") or "").strip()
            mob = str(ct.get("mobile") or "").strip()
            prim = bool(ct.get("is_primary"))
            active = bool(ct.get("is_active", True))
            line = f"**{html.escape(nm)}**"
            if title:
                line += f" · *{html.escape(title)}*"
            if em:
                line += f" · {html.escape(em)}"
            if ph:
                line += f" · {html.escape(ph)}"
            if mob:
                line += f" · M {html.escape(mob)}"
            badges: list[str] = []
            if prim:
                badges.append("Primary")
            if not active:
                badges.append("Inactive")
            badge_s = " · ".join(badges)
            full_line = line + (f" · *{badge_s}*" if badge_s else "")

            if can_edit and ctid:
                wkey = f"cust_ct_pick_{cid}_{ctid}"
                sel_now = str(st.session_state.get(sel_key) or "")
                st.session_state[wkey] = sel_now == ctid
                chk_col, body_col = st.columns([0.055, 0.945], gap="small")
                with chk_col:
                    st.checkbox(
                        "Select",
                        key=wkey,
                        on_change=_on_contact_pick_changed,
                        args=(cid, ctid, wkey),
                        label_visibility="collapsed",
                    )
                with body_col:
                    with st.container(border=True):
                        st.markdown(full_line, unsafe_allow_html=True)
            else:
                with st.container(border=True):
                    st.markdown(full_line, unsafe_allow_html=True)

        if can_edit and contacts:
            pick = str(st.session_state.get(sel_key) or "").strip()
            picked_row = _contact_row_by_id(contacts, pick) if pick else None
            if pick and picked_row is None:
                st.session_state.pop(sel_key, None)
                pick = ""
                picked_row = None
            prim_p = bool((picked_row or {}).get("is_primary"))
            active_p = bool((picked_row or {}).get("is_active", True))

            st.caption(
                "Use the checkbox to select **one** contact. Actions below apply **only** to that selection."
            )
            with st.container(border=True):
                r1a, r1b, r1c, r1d = st.columns([1.2, 1.2, 1.2, 1.2], gap="small")
                with r1a:
                    if st.button(
                        "Edit Contact",
                        type="primary",
                        use_container_width=False,
                        disabled=not pick,
                        key=f"cust_ct_tool_edit_{cid}",
                    ):
                        if not pick or _contact_row_by_id(contacts, pick) is None:
                            st.error("Select a contact first.")
                            st.stop()
                        st.session_state["customer_contact_mode"] = "edit"
                        st.session_state["customer_contact_edit_id"] = pick
                        st.rerun()
                with r1b:
                    if st.button(
                        "Set Primary",
                        use_container_width=False,
                        disabled=(not pick or not active_p or prim_p),
                        key=f"cust_ct_tool_pri_{cid}",
                    ):
                        if not pick or _contact_row_by_id(contacts, pick) is None:
                            st.error("Select a contact first.")
                            st.stop()
                        set_primary_contact(customer_id=cid, contact_id=pick)
                        st.success("Primary contact updated.")
                        st.rerun()
                with r1c:
                    if st.button(
                        "Deactivate",
                        use_container_width=False,
                        disabled=(not pick or not active_p),
                        key=f"cust_ct_tool_deact_{cid}",
                    ):
                        if not pick or (pr := _contact_row_by_id(contacts, pick)) is None:
                            st.error("Select a contact first.")
                            st.stop()
                        try:
                            update_rows_admin("customer_contacts", {"is_active": False}, {"id": pick})
                        except Exception as exc:
                            st.error(f"Could not deactivate: {exc}")
                            st.stop()
                        if bool(pr.get("is_primary")):
                            try:
                                update_rows_admin("customer_contacts", {"is_primary": False}, {"id": pick})
                            except Exception:
                                pass
                        st.success("Contact deactivated.")
                        st.rerun()
                with r1d:
                    if st.button(
                        "Delete",
                        type="secondary",
                        use_container_width=False,
                        disabled=not pick,
                        key=f"cust_ct_tool_del_{cid}",
                    ):
                        if not pick or _contact_row_by_id(contacts, pick) is None:
                            st.error("Select a contact first.")
                            st.stop()
                        open_destructive_confirmation(_CONTACT_DELETE_PREFIX)
                        st.session_state["customer_contact_pending_delete_ids"] = [pick]
                        st.rerun()
                if pick and not active_p:
                    if st.button(
                        "Reactivate",
                        type="secondary",
                        use_container_width=False,
                        key=f"cust_ct_tool_react_{cid}",
                    ):
                        if not pick or _contact_row_by_id(contacts, pick) is None:
                            st.error("Select a contact first.")
                            st.stop()
                        try:
                            update_rows_admin("customer_contacts", {"is_active": True}, {"id": pick})
                        except Exception as exc:
                            st.error(f"Could not reactivate: {exc}")
                            st.stop()
                        st.success("Contact reactivated.")
                        st.rerun()

    if not can_edit:
        return

    if mode == "edit" and edit_ct and edit_row:
        st.markdown("**Edit contact**")
        pk = f"cust_ct_ed_{edit_ct}"
        er = edit_row
        with st.form(f"cust_contact_edit_form_{edit_ct}", clear_on_submit=False):
            cn = st.text_input("Contact name", value=str(er.get("contact_name") or ""), key=f"{pk}_name")
            tl = st.text_input(
                "Title",
                value=_contact_title_display(er),
                key=f"{pk}_title",
                help="Job title or role",
            )
            em = st.text_input("Email", value=str(er.get("email") or ""), key=f"{pk}_email")
            cph1, cph2 = st.columns(2)
            with cph1:
                ph = st.text_input("Phone", value=str(er.get("phone") or ""), key=f"{pk}_phone")
            with cph2:
                mob = st.text_input("Mobile", value=str(er.get("mobile") or ""), key=f"{pk}_mobile")
            nt = st.text_area("Notes", value=str(er.get("notes") or ""), height=56, key=f"{pk}_notes")
            pr = st.checkbox("Primary contact", value=bool(er.get("is_primary")), key=f"{pk}_prim")
            act = st.checkbox("Active", value=bool(er.get("is_active", True)), key=f"{pk}_act")
            submitted = st.form_submit_button("Update contact", type="primary", use_container_width=True)

        if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
            _clear_contact_subpanel()
            st.rerun()

        if submitted:
            t = str(cn or "").strip()
            if not t:
                st.error("Contact name is required.")
                st.stop()
            pr_b = bool(pr)
            act_b = bool(act)
            if pr_b and not act_b:
                st.warning("Inactive contacts cannot be primary — clearing primary flag.")
                pr_b = False
            full, minimal = _build_contact_write_pair(
                contact_name=t,
                title_text=str(tl or ""),
                email=str(em or ""),
                phone=str(ph or ""),
                mobile=str(mob or ""),
                notes=str(nt or ""),
                is_active=act_b,
                is_primary=pr_b,
                customer_id=None,
                schema_keys=schema_keys,
                customer_location_id=str(er.get("customer_location_id") or "").strip() or None,
                set_customer_location_id=True,
            )
            try:
                _update_contact_pair(str(er["id"]), full, minimal)
            except Exception as exc:
                st.error("Could not update the contact.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")
                st.stop()
            if pr_b:
                set_primary_contact(customer_id=cid, contact_id=str(er["id"]))
            _clear_contact_subpanel()
            st.success("Contact updated.")
            st.rerun()


def _on_loc_contact_pick_changed(cid: str, lid: str, ctid: str, wkey: str) -> None:
    sel_key = f"lc_sel_{cid}_{lid}"
    prefix = f"lc_pick_{cid}_{lid}_"
    if st.session_state.get(wkey):
        st.session_state[sel_key] = ctid
        for k in list(st.session_state.keys()):
            if isinstance(k, str) and k.startswith(prefix) and k != wkey:
                st.session_state[k] = False
    else:
        if str(st.session_state.get(sel_key) or "") == ctid:
            st.session_state[sel_key] = None


def _render_location_contacts_block(
    *,
    customer_id: str,
    location_id: str,
    location_name: str,
    can_edit: bool,
    admin_read: bool,
) -> None:
    """Contacts scoped to one job site (under Locations)."""
    cid = str(customer_id or "").strip()
    lid = str(location_id or "").strip()
    if not cid or not lid:
        return

    st.caption(f"**Contacts · {html.escape(location_name or 'Site')}**")
    mode = st.session_state.get(f"lc_mode_{cid}_{lid}")
    edit_ct = str(st.session_state.get(f"lc_edit_{cid}_{lid}") or "").strip() or None
    sel_key = f"lc_sel_{cid}_{lid}"

    key_show_inact = f"lc_show_inact_{cid}_{lid}"
    st.session_state.setdefault(key_show_inact, False)
    st.checkbox("Show inactive", key=key_show_inact)

    load_inactive = bool(st.session_state.get(key_show_inact, False) or (mode == "edit" and bool(edit_ct)))
    all_c = _fetch_contacts_for_customer_row(cid, admin_read=admin_read, include_inactive=load_inactive)
    loc_contacts = _contacts_filtered_by_scope(all_c, lid)
    edit_row: dict[str, Any] | None = None
    if mode == "edit" and edit_ct:
        edit_row = _contact_row_by_id(loc_contacts, edit_ct)
        if not edit_row:
            er = _fetch_one_row("customer_contacts", {"id": edit_ct}, admin_read=admin_read)
            if er and str(er.get("customer_id") or "") == cid and str(er.get("customer_location_id") or "") == lid:
                edit_row = er
                loc_contacts = [er] + [x for x in loc_contacts if str(x.get("id")) != edit_ct]
            else:
                st.session_state.pop(f"lc_mode_{cid}_{lid}", None)
                st.session_state.pop(f"lc_edit_{cid}_{lid}", None)
                st.warning("That contact is not on this site.")
                st.rerun()
                return

    schema_keys = _contact_schema_keys(loc_contacts, edit_row)
    schema_keys = set(schema_keys) | {"customer_location_id"}

    sid = str(st.session_state.get(sel_key) or "").strip()
    if sid and not any(str(c.get("id") or "") == sid for c in loc_contacts):
        st.session_state.pop(sel_key, None)
        sid = ""
    if mode == "edit" and edit_ct:
        st.session_state[sel_key] = str(edit_ct)

    if can_edit:
        if st.button(
            "Add Contact",
            type="primary",
            use_container_width=True,
            key=f"lc_add_{cid}_{lid}",
        ):
            _add_contact_dialog(
                cid,
                admin_read,
                customer_location_id=lid,
                set_customer_location_id=True,
            )

    if not loc_contacts:
        st.caption("No contacts at this site yet.")
    else:
        for ct in loc_contacts:
            ctid = str(ct.get("id") or "")
            nm = str(ct.get("contact_name") or "").strip() or "—"
            title = _contact_title_display(ct)
            em = str(ct.get("email") or "").strip()
            ph = str(ct.get("phone") or "").strip()
            mob = str(ct.get("mobile") or "").strip()
            prim = bool(ct.get("is_primary"))
            active = bool(ct.get("is_active", True))
            line = f"**{html.escape(nm)}**"
            if title:
                line += f" · *{html.escape(title)}*"
            if em:
                line += f" · {html.escape(em)}"
            if ph:
                line += f" · {html.escape(ph)}"
            if mob:
                line += f" · M {html.escape(mob)}"
            badges: list[str] = []
            if prim:
                badges.append("Primary")
            if not active:
                badges.append("Inactive")
            badge_s = " · ".join(badges)
            full_line = line + (f" · *{badge_s}*" if badge_s else "")

            if can_edit and ctid:
                wkey = f"lc_pick_{cid}_{lid}_{ctid}"
                sel_now = str(st.session_state.get(sel_key) or "")
                st.session_state[wkey] = sel_now == ctid
                chk_col, body_col = st.columns([0.055, 0.945], gap="small")
                with chk_col:
                    st.checkbox(
                        "Select",
                        key=wkey,
                        on_change=_on_loc_contact_pick_changed,
                        args=(cid, lid, ctid, wkey),
                        label_visibility="collapsed",
                    )
                with body_col:
                    with st.container(border=True):
                        st.markdown(full_line, unsafe_allow_html=True)
            else:
                with st.container(border=True):
                    st.markdown(full_line, unsafe_allow_html=True)

        if can_edit and loc_contacts:
            pick = str(st.session_state.get(sel_key) or "").strip()
            if pick and _contact_row_by_id(loc_contacts, pick) is None:
                st.session_state.pop(sel_key, None)
                pick = ""
            p1, p2, p3 = st.columns(3, gap="small")
            with p1:
                if st.button(
                    "Edit",
                    type="primary",
                    use_container_width=True,
                    disabled=not pick,
                    key=f"lc_tool_edit_{cid}_{lid}",
                ):
                    if not pick:
                        st.error("Select a contact first.")
                        st.stop()
                    st.session_state[f"lc_mode_{cid}_{lid}"] = "edit"
                    st.session_state[f"lc_edit_{cid}_{lid}"] = pick
                    st.rerun()
            with p2:
                if st.button(
                    "Set primary",
                    use_container_width=True,
                    disabled=not pick,
                    key=f"lc_tool_pri_{cid}_{lid}",
                ):
                    if not pick:
                        st.error("Select a contact first.")
                        st.stop()
                    set_primary_contact(customer_id=cid, contact_id=pick)
                    st.success("Primary updated.")
                    st.rerun()
            with p3:
                if st.button(
                    "Delete",
                    type="secondary",
                    use_container_width=True,
                    disabled=not pick,
                    key=f"lc_tool_del_{cid}_{lid}",
                ):
                    if not pick:
                        st.error("Select a contact first.")
                        st.stop()
                    open_destructive_confirmation(_CONTACT_DELETE_PREFIX)
                    st.session_state["customer_contact_pending_delete_ids"] = [pick]
                    st.rerun()

    if not can_edit:
        return

    if mode == "edit" and edit_ct and edit_row:
        st.markdown("**Edit site contact**")
        pk = f"lc_ed_{cid}_{lid}_{edit_ct}"
        er = edit_row
        with st.form(f"cust_site_contact_edit_form_{cid}_{lid}_{edit_ct}", clear_on_submit=False):
            cn = st.text_input("Contact name", value=str(er.get("contact_name") or ""), key=f"{pk}_name")
            tl = st.text_input(
                "Title",
                value=_contact_title_display(er),
                key=f"{pk}_title",
                help="Job title or role",
            )
            em = st.text_input("Email", value=str(er.get("email") or ""), key=f"{pk}_email")
            cph1, cph2 = st.columns(2)
            with cph1:
                ph = st.text_input("Phone", value=str(er.get("phone") or ""), key=f"{pk}_phone")
            with cph2:
                mob = st.text_input("Mobile", value=str(er.get("mobile") or ""), key=f"{pk}_mobile")
            nt = st.text_area("Notes", value=str(er.get("notes") or ""), height=56, key=f"{pk}_notes")
            pr = st.checkbox("Primary contact", value=bool(er.get("is_primary")), key=f"{pk}_prim")
            act = st.checkbox("Active", value=bool(er.get("is_active", True)), key=f"{pk}_act")
            submitted = st.form_submit_button("Update contact", type="primary", use_container_width=True)

        if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
            st.session_state.pop(f"lc_mode_{cid}_{lid}", None)
            st.session_state.pop(f"lc_edit_{cid}_{lid}", None)
            st.rerun()

        if submitted:
            t = str(cn or "").strip()
            if not t:
                st.error("Contact name is required.")
                st.stop()
            pr_b = bool(pr)
            act_b = bool(act)
            if pr_b and not act_b:
                st.warning("Inactive contacts cannot be primary — clearing primary flag.")
                pr_b = False
            full, minimal = _build_contact_write_pair(
                contact_name=t,
                title_text=str(tl or ""),
                email=str(em or ""),
                phone=str(ph or ""),
                mobile=str(mob or ""),
                notes=str(nt or ""),
                is_active=act_b,
                is_primary=pr_b,
                customer_id=None,
                schema_keys=schema_keys,
                customer_location_id=lid,
                set_customer_location_id=True,
            )
            try:
                _update_contact_pair(str(er["id"]), full, minimal)
            except Exception as exc:
                st.error("Could not update the contact.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")
                st.stop()
            if pr_b:
                set_primary_contact(customer_id=cid, contact_id=str(er["id"]))
            st.session_state.pop(f"lc_mode_{cid}_{lid}", None)
            st.session_state.pop(f"lc_edit_{cid}_{lid}", None)
            st.success("Contact updated.")
            st.rerun()


def _render_edit_form(
    row: dict,
    *,
    can_edit: bool,
    resolved: dict[str, str],
    available: set[str],
    admin_read: bool,
) -> None:
    cid = str(row.get("id") or "")
    st.caption(f"ID `{cid[:8]}…`")
    pk = f"cust_ed_{cid}"

    st.markdown("##### Company")
    with st.form(f"cust_customer_edit_form_{cid}", clear_on_submit=False):
        c1 = st.columns(1)[0]
        en = c1.text_input(
            "Customer Name",
            value=_get_customer_field(row, "customer_name", resolved),
            key=f"{pk}_name",
        )

        c5, c6, c7, c8 = st.columns(4)
        eaddr = c5.text_input(
            "Address",
            value=_get_customer_field(row, "address", resolved),
            key=f"{pk}_addr",
        )
        ecity = c6.text_input(
            "City",
            value=_get_customer_field(row, "city", resolved),
            key=f"{pk}_city",
        )
        est = c7.text_input(
            "State",
            value=_get_customer_field(row, "state", resolved),
            key=f"{pk}_state",
        )
        ezip = c8.text_input(
            "ZIP",
            value=_get_customer_field(row, "zip", resolved),
            key=f"{pk}_zip",
        )

        if resolved["is_active"] in row:
            default_active = bool(row.get(resolved["is_active"], True))
        elif "is_active" in row:
            default_active = bool(row.get("is_active", True))
        else:
            default_active = True

        ea = st.checkbox("Active", value=default_active, key=f"{pk}_active")
        submitted = st.form_submit_button("Update Customer", type="primary", use_container_width=True)

    if resolved["is_active"] not in available:
        st.caption("Note: this database has no `is_active` column; the Active toggle is shown for reference only.")

    if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
        _clear_customer_mode()
        st.rerun()

    if submitted:
        err = _validate_customer_name_text(en)
        if err:
            st.error(err)
            st.stop()
        for label, val in (
            ("Address", eaddr),
            ("City", ecity),
            ("State", est),
            ("ZIP", ezip),
        ):
            ve = _validate_address_field(label, str(val))
            if ve:
                st.error(ve)
                st.stop()

        active_val: bool | None = bool(ea) if resolved["is_active"] in available else None
        try:
            payload = _build_customer_write_payload(
                customer_name=str(en).strip(),
                address=str(eaddr).strip(),
                city=str(ecity).strip(),
                state=str(est).strip(),
                zip_value=str(ezip).strip(),
                is_active=active_val,
                resolved=resolved,
                available=available,
            )
            update_rows_admin("customers", payload, {"id": row["id"]})
        except Exception as exc:
            st.error(_friendly_customer_db_message(exc))
            with st.expander("Technical details"):
                st.code(repr(exc), language="text")
            st.stop()

        _clear_customer_mode()
        st.success("Customer updated.")
        st.rerun()

    st.markdown("---")
    _render_contacts_section(customer_row=row, can_edit=can_edit, admin_read=admin_read)
    st.markdown("---")
    _render_locations_section(customer_row=row, can_edit=can_edit, admin_read=admin_read)


def _render_customer_side_panel_body(
    *,
    resolved: dict[str, str],
    available: set[str],
    admin_read: bool,
) -> None:
    eid = st.session_state.get("customer_edit_id")
    er = _fetch_one_row("customers", {"id": eid}, admin_read=admin_read) if eid else None
    if not er:
        st.warning("Customer not found.")
        _clear_customer_mode()
    else:
        can_edit = current_role() in {"admin", "pm"}
        _render_edit_form(
            er,
            can_edit=can_edit,
            resolved=resolved,
            available=available,
            admin_read=admin_read,
        )


def _render_customer_side_panel(
    *,
    resolved: dict[str, str],
    available: set[str],
    admin_read: bool,
) -> None:
    render_side_detail_panel(
        title="Customer detail",
        body=lambda: _render_customer_side_panel_body(
            resolved=resolved,
            available=available,
            admin_read=admin_read,
        ),
    )


def _visible_customer_columns(filtered: pd.DataFrame, resolved: dict[str, str]) -> list[str]:
    # Never show id or is_active in the main list; filters and actions still use them from ``filtered``.
    order = ["customer_name", "address", "city", "state", "zip"]
    out: list[str] = []
    for logical in order:
        phys = resolved.get(logical)
        if phys and phys in filtered.columns:
            out.append(phys)
    ia = resolved.get("is_active")
    out = [c for c in out if c != "id" and c != ia]
    return out


def _render_customers_main(
    *,
    df: pd.DataFrame,
    can_add: bool,
    resolved: dict[str, str],
    available: set[str],
    existing_customer_names: set[str],
    show_contacts_preview: bool = True,
) -> None:
    if df.empty:
        st.info("No customers found.")
        if can_add:
            if st.button("Add Customer", type="primary", use_container_width=True, key="cust_empty_add"):
                _add_customer_dialog(
                    existing_customer_names=existing_customer_names,
                    resolved=resolved,
                    available=available,
                )
        return

    f1, f2 = st.columns([2, 1], gap="small")
    with f1:
        st.markdown(
            '<span class="ips-crud-filter-row-start" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        search = render_search_box(
            key="cust_search",
            placeholder="Customer name, address, city, state, ZIP",
        )
    active_options = ["All", "Active only", "Inactive only"]
    selected_active = render_status_filter(key="cust_status", options=active_options)

    filtered = df.copy()
    is_active_col = resolved.get("is_active")
    if is_active_col and is_active_col in filtered.columns:
        filtered = apply_boolean_status_filter(
            filtered,
            column=is_active_col,
            selected=selected_active,
        )
    filtered = apply_text_search(filtered, search)

    show_cols = _visible_customer_columns(filtered, resolved)

    st.caption(
        "Checkbox column on the **left**; selection is stored as **selected_customers_ids**."
    )

    if filtered.empty:
        st.warning("No customers match your filters.")
        if can_add:
            inject_table_action_styles()
            if st.button("Add Customer", type="primary", use_container_width=True, key="cust_filtered_empty_add"):
                _add_customer_dialog(
                    existing_customer_names=existing_customer_names,
                    resolved=resolved,
                    available=available,
                )
    elif "id" not in filtered.columns:
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)
    else:

        def _on_add_customer() -> None:
            _add_customer_dialog(
                existing_customer_names=existing_customer_names,
                resolved=resolved,
                available=available,
            )

        def _on_edit_customer(cid: str) -> None:
            st.session_state["customer_mode"] = "edit"
            st.session_state["customer_edit_id"] = cid
            _clear_contact_subpanel()
            _clear_location_subpanel()
            st.rerun()

        def _on_deactivate_customers(_ids: list[str]) -> None:
            st.session_state["_cust_do_deactivate"] = True
            st.rerun()

        def _on_delete_customers(s: list[str]) -> None:
            open_destructive_confirmation(_CUST_DELETE_CONFIRM_PREFIX)
            st.session_state["customers_pending_delete_ids"] = [str(x) for x in s]
            st.rerun()

        def _toolbar(sel: list[str]) -> None:
            render_standard_toolbar(
                selected_ids=sel,
                can_add=can_add,
                add_label="Add Customer",
                on_add=_on_add_customer,
                on_edit=_on_edit_customer,
                on_deactivate=_on_deactivate_customers,
                on_delete=_on_delete_customers,
                key_prefix="cust_btn",
            )

        sel = render_crud_table(
            filtered,
            table_key=TABLE_KEY_CUSTOMERS,
            id_column="id",
            columns=show_cols,
            editor_key="cust_sel_editor",
            hide_id_column=True,
            toolbar_above=True,
            action_bar=_toolbar,
        )

        if show_contacts_preview and len(sel) == 1:
            one_cid = str(sel[0]).strip()
            name_col = resolved.get("customer_name") or "customer_name"
            row_match = filtered.loc[filtered["id"].astype(str) == one_cid] if "id" in filtered.columns else None
            cust_title = one_cid
            if row_match is not None and not row_match.empty and name_col in row_match.columns:
                cust_title = str(row_match.iloc[0].get(name_col) or "").strip() or one_cid
            st.markdown(f"##### Contacts — **{cust_title}**")
            admin_read = can_add
            contacts = _fetch_contacts_for_customer_row(one_cid, admin_read=admin_read, include_inactive=False)
            if not contacts:
                st.caption("No active contacts for this customer.")
            else:
                cdf = pd.DataFrame(contacts)
                pref = ["contact_name", "title", "role", "phone", "mobile", "email", "notes"]
                disp = [c for c in pref if c in cdf.columns]
                if not disp:
                    disp = list(cdf.columns)
                st.dataframe(cdf[disp], use_container_width=True, hide_index=True)


def render_customers() -> None:
    can_add = current_role() in {"admin", "pm"}
    if st.session_state.get("customer_mode") == "add":
        st.session_state.pop("customer_mode", None)
    mode = st.session_state.get("customer_mode")

    load_error: BaseException | None = None
    try:
        rows = _fetch_customers_list_rows(admin_read=can_add)
    except Exception as exc:
        load_error = exc
        rows = []

    df = pd.DataFrame(rows)
    available = _infer_available_columns(df, rows)
    resolved = _resolve_customer_columns(available)

    existing_names: set[str] = set()
    name_col = resolved["customer_name"]
    if not df.empty and name_col in df.columns:
        for _, c in df.iterrows():
            nm = str(c.get(name_col, "")).strip().upper()
            if nm:
                existing_names.add(nm)

    panel_open = bool(can_add and mode == "edit")

    def _before_main() -> None:
        if load_error is not None:
            st.error("Could not load customers from the database. The list below may be empty.")
            with st.expander("Technical details"):
                st.code(repr(load_error), language="text")

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
            name_col2 = resolved["customer_name"]
            if not df.empty and "id" in df.columns and name_col2 in df.columns:
                for _, r in df.iterrows():
                    rid = str(r["id"])
                    id_to_name[rid] = str(r.get(name_col2) or "").strip() or rid
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
                        st.error(f"Could not delete this customer ({cid[:8]}…). {_friendly_customer_db_message(exc)}")
                        with st.expander("Technical details"):
                            st.code(repr(exc), language="text")
                st.session_state.pop("customers_pending_delete_ids", None)
                clear_selected_ids(TABLE_KEY_CUSTOMERS)
                edit_id = st.session_state.get("customer_edit_id")
                if edit_id and str(edit_id) in {str(x) for x in pending}:
                    _clear_customer_mode()
                st.success("Customer(s) deleted where permitted.")

            def _on_cancel_delete() -> None:
                st.session_state.pop("customers_pending_delete_ids", None)

            render_delete_confirm(
                key_prefix=_CUST_DELETE_CONFIRM_PREFIX,
                title="Confirm Delete",
                message=msg,
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

            render_delete_confirm(
                key_prefix=_CONTACT_DELETE_PREFIX,
                title="Confirm Delete",
                message="Delete this contact? Estimates/jobs referencing it will clear the contact link.",
                on_confirm=_on_confirm_ct_delete,
                on_cancel=_on_cancel_ct_delete,
                name_lines=[str(x)[:12] + "…" for x in pending_ct],
            )

        if st.session_state.pop("_cust_do_deactivate", False) and can_add:
            if resolved["is_active"] not in available:
                st.warning("Deactivation is not available: the database has no `is_active` column on customers.")
            else:
                sel_ids = get_selected_ids(TABLE_KEY_CUSTOMERS)
                if sel_ids:
                    failures: list[BaseException] = []
                    for cid in sel_ids:
                        try:
                            update_rows_admin("customers", {resolved["is_active"]: False}, {"id": cid})
                        except Exception as exc:
                            failures.append(exc)
                            st.error(
                                f"Could not deactivate customer `{str(cid)[:8]}…`. "
                                f"{_friendly_customer_db_message(exc)}"
                            )
                            with st.expander("Technical details"):
                                st.code(repr(exc), language="text")
                    clear_selected_ids(TABLE_KEY_CUSTOMERS)
                    if not failures:
                        st.success("Selected customers deactivated.")
                        st.rerun()

    def _main() -> None:
        _render_customers_main(
            df=df,
            can_add=can_add,
            resolved=resolved,
            available=available,
            existing_customer_names=existing_names,
            show_contacts_preview=not panel_open,
        )

    def _side() -> None:
        _render_customer_side_panel(
            resolved=resolved,
            available=available,
            admin_read=can_add,
        )

    render_crud_page(
        title="Customers",
        subtitle="Manage customer companies and billing addresses. Contacts are stored per company.",
        panel_open=panel_open,
        before_main=_before_main,
        main_body=_main,
        side_body=_side if panel_open else None,
    )

    if not can_add:
        st.info("Only admin or pm users can manage customers.")
