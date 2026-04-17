from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from auth import current_role
from branding import render_header
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

try:
    from table_actions import (
        TABLE_KEY_CUSTOMERS,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        set_selected_ids,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        TABLE_KEY_CUSTOMERS,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        set_selected_ids,
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
        inject_ips_modal_styles,
        render_crud_list_subtitle,
    )
except ImportError:
    from ips_crud_list_styles import (  # type: ignore
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
        inject_ips_modal_styles,
        render_crud_list_subtitle,
    )

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
    """Admin/estimator uses service-role reads so rows written with admin policies stay visible (RLS)."""
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
    return full, minimal


def _insert_contact_pair(full: dict[str, Any], minimal: dict[str, Any]) -> dict[str, Any]:
    try:
        return insert_contact_row(full)
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

    # --- body: compact groups (2 columns where it fits) ---
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

    # --- footer: spacer | Cancel (secondary) | Save (primary), right-aligned ---
    st.divider()
    sp, fc, fs = st.columns([4, 1, 1], gap="small")
    with sp:
        st.empty()
    with fc:
        if st.button("Cancel", type="secondary", use_container_width=True, key="dlg_cust_add_cancel"):
            st.rerun()
    with fs:
        if st.button("Save", type="primary", use_container_width=True, key="dlg_cust_add_save"):
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
def _add_contact_dialog(cid: str, admin_read: bool) -> None:
    key_show_inact = f"cust_ct_show_inactive_{cid}"
    load_inactive = bool(st.session_state.get(key_show_inact, False))
    contacts = _fetch_contacts_for_customer_row(cid, admin_read=admin_read, include_inactive=load_inactive)
    schema_keys = _contact_schema_keys(contacts, None)
    pk = f"dlg_ct_{cid}"

    # --- header: @st.dialog title + subtitle ---
    _ips_modal_header(subtitle="New row in customer_contacts · primary and active optional")

    # --- body: compact groups (2 columns) ---
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

    # --- footer: spacer | Cancel (secondary) | Save (primary), right-aligned ---
    st.divider()
    sp, fc, fs = st.columns([4, 1, 1], gap="small")
    with sp:
        st.empty()
    with fc:
        if st.button("Cancel", type="secondary", use_container_width=True, key=f"{pk}_cancel"):
            st.rerun()
    with fs:
        if st.button("Save", type="primary", use_container_width=True, key=f"{pk}_save"):
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


def _clear_customer_mode() -> None:
    st.session_state.pop("customer_mode", None)
    st.session_state.pop("customer_edit_id", None)
    st.session_state.pop("customer_contact_mode", None)
    st.session_state.pop("customer_contact_edit_id", None)
    st.session_state.pop("customer_contact_selected_id", None)


def _clear_contact_subpanel() -> None:
    st.session_state.pop("customer_contact_mode", None)
    st.session_state.pop("customer_contact_edit_id", None)
    st.session_state.pop("customer_contact_selected_id", None)


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


def _render_action_buttons(
    *,
    sel: list[str],
    can_add: bool,
    existing_customer_names: set[str],
    resolved: dict[str, str],
    available: set[str],
) -> None:
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
                _add_customer_dialog(
                    existing_customer_names=existing_customer_names,
                    resolved=resolved,
                    available=available,
                )
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


def _render_contacts_section(*, customer_row: dict, can_edit: bool, admin_read: bool) -> None:
    cid = str(customer_row.get("id") or "")
    if not cid:
        return

    sel_key = "customer_contact_selected_id"

    st.markdown("##### Contacts")
    st.caption(
        "Multiple contacts per company — stored in **customer_contacts** (separate from the company row)."
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
    contacts = _fetch_contacts_for_customer_row(cid, admin_read=admin_read, include_inactive=load_inactive)
    schema_keys = _contact_schema_keys(contacts, edit_row)

    sid = str(st.session_state.get(sel_key) or "").strip()
    if sid and not any(str(c.get("id") or "") == sid for c in contacts):
        st.session_state.pop(sel_key, None)
        sid = ""
    if mode == "edit" and edit_ct:
        st.session_state[sel_key] = str(edit_ct)

    if can_edit:
        if st.button("Add Contact", type="primary", use_container_width=True, key=f"cust_ct_add_{cid}"):
            _add_contact_dialog(cid, admin_read)

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
                r1a, r1b, r1c, r1d = st.columns(4, gap="small")
                with r1a:
                    if st.button(
                        "Edit Contact",
                        type="primary",
                        use_container_width=True,
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
                        use_container_width=True,
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
                        use_container_width=True,
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
                        use_container_width=True,
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
        s1, s2 = st.columns(2)
        with s1:
            if st.button("Update contact", type="primary", use_container_width=True, key=f"{pk}_save"):
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
        with s2:
            if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
                _clear_contact_subpanel()
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
    if resolved["is_active"] not in available:
        st.caption("Note: this database has no `is_active` column; the Active toggle is shown for reference only.")

    u1, u2 = st.columns(2)
    with u1:
        if st.button("Update Customer", type="primary", use_container_width=True, key=f"{pk}_save"):
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
    with u2:
        if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
            _clear_customer_mode()
            st.rerun()

    st.markdown("---")
    _render_contacts_section(customer_row=row, can_edit=can_edit, admin_read=admin_read)


def _render_customer_side_panel(
    *,
    resolved: dict[str, str],
    available: set[str],
    admin_read: bool,
) -> None:
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Customer detail")
        eid = st.session_state.get("customer_edit_id")
        er = _fetch_one_row("customers", {"id": eid}, admin_read=admin_read) if eid else None
        if not er:
            st.warning("Customer not found.")
            _clear_customer_mode()
        else:
            can_edit = current_role() in {"admin", "estimator"}
            _render_edit_form(
                er,
                can_edit=can_edit,
                resolved=resolved,
                available=available,
                admin_read=admin_read,
            )


def _visible_customer_columns(filtered: pd.DataFrame, resolved: dict[str, str]) -> list[str]:
    order = ["customer_name", "address", "city", "state", "zip", "is_active"]
    out: list[str] = []
    for logical in order:
        phys = resolved.get(logical)
        if phys and phys in filtered.columns:
            out.append(phys)
    return out


def _render_customers_main(
    *,
    df: pd.DataFrame,
    can_add: bool,
    resolved: dict[str, str],
    available: set[str],
    existing_customer_names: set[str],
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
        search = st.text_input(
            "Search",
            placeholder="Customer name, address, city, state, ZIP",
        )
    active_options = ["All", "Active only", "Inactive only"]
    selected_active = f2.selectbox("Status", active_options)

    filtered = df.copy()
    is_active_col = resolved.get("is_active")
    if is_active_col and is_active_col in filtered.columns:
        if selected_active == "Active only":
            filtered = filtered[filtered[is_active_col] == True]  # noqa: E712
        elif selected_active == "Inactive only":
            filtered = filtered[filtered[is_active_col] == False]  # noqa: E712

    if search.strip():
        s = search.strip().lower()
        mask = filtered.astype(str).apply(
            lambda col: col.str.lower().str.contains(s, na=False, regex=False)
        )
        filtered = filtered[mask.any(axis=1)]

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
        bar_ph = st.empty()
        _, sel = render_selectable_dataframe(
            filtered,
            table_key=TABLE_KEY_CUSTOMERS,
            id_column="id",
            columns=show_cols,
            editor_key="cust_sel_editor",
        )
        with bar_ph.container():
            _render_action_buttons(
                sel=sel,
                can_add=can_add,
                existing_customer_names=existing_customer_names,
                resolved=resolved,
                available=available,
            )

        if len(sel) == 1:
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
    render_header("Customers")
    render_crud_list_subtitle("Manage customer companies and billing addresses. Contacts are stored per company.")

    can_add = current_role() in {"admin", "estimator"}
    if st.session_state.get("customer_mode") == "add":
        st.session_state.pop("customer_mode", None)
    mode = st.session_state.get("customer_mode")

    load_error: BaseException | None = None
    try:
        rows = _fetch_customers_list_rows(admin_read=can_add)
    except Exception as exc:
        load_error = exc
        rows = []

    if load_error is not None:
        st.error("Could not load customers from the database. The list below may be empty.")
        with st.expander("Technical details"):
            st.code(repr(load_error), language="text")

    df = pd.DataFrame(rows)
    available = _infer_available_columns(df, rows)
    resolved = _resolve_customer_columns(available)

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
        name_col = resolved["customer_name"]
        if not df.empty and "id" in df.columns and name_col in df.columns:
            for _, r in df.iterrows():
                rid = str(r["id"])
                id_to_name[rid] = str(r.get(name_col) or "").strip() or rid
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

    panel_open = bool(can_add and mode == "edit")

    existing_names: set[str] = set()
    name_col = resolved["customer_name"]
    if not df.empty and name_col in df.columns:
        for _, c in df.iterrows():
            nm = str(c.get(name_col, "")).strip().upper()
            if nm:
                existing_names.add(nm)

    if panel_open:
        main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
        with main_col:
            _render_customers_main(
                df=df,
                can_add=can_add,
                resolved=resolved,
                available=available,
                existing_customer_names=existing_names,
            )
        with side_col:
            _render_customer_side_panel(
                resolved=resolved,
                available=available,
                admin_read=can_add,
            )
    else:
        _render_customers_main(
            df=df,
            can_add=can_add,
            resolved=resolved,
            available=available,
            existing_customer_names=existing_names,
        )

    if not can_add:
        st.info("Only admin or estimator users can manage customers.")
