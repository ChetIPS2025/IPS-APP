"""Helpers for ``public.customer_contacts`` (people tied to a customer company)."""

from __future__ import annotations

import html
import hashlib
from typing import Any

import streamlit as st

try:
    from db import (
        delete_rows,
        delete_rows_admin,
        fetch_by_match,
        insert_row,
        insert_row_admin,
        update_rows,
        update_rows_admin,
    )
except ImportError:
    from app.db import (  # type: ignore
        delete_rows,
        delete_rows_admin,
        fetch_by_match,
        insert_row,
        insert_row_admin,
        update_rows,
        update_rows_admin,
    )


def fetch_contacts_for_customer(customer_id: str, *, include_inactive: bool = False) -> list[dict[str, Any]]:
    """Fetch contacts for a customer. Default: active only, primary first."""
    cid = str(customer_id or "").strip()
    if not cid:
        return []
    try:
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


def _contact_row_location_id(r: dict[str, Any]) -> str:
    return str(r.get("customer_location_id") or "").strip()


def fetch_contacts_for_customer_scope(
    customer_id: str,
    customer_location_id: str | None,
    *,
    admin_read: bool = False,
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    """
    Contacts for Estimates / Jobs.

    - **No location selected:** all contacts for the customer (backward compatible).
    - **Location selected:** contacts for that site plus company-wide rows
      (``customer_location_id`` is null), sorted with site-specific first.
    """
    cid = str(customer_id or "").strip()
    if not cid:
        return []
    fn = fetch_by_match_admin if admin_read else fetch_by_match
    try:
        rows = fn("customer_contacts", {"customer_id": cid}, limit=500)
    except Exception:
        try:
            rows = fetch_by_match_admin("customer_contacts", {"customer_id": cid}, limit=500)
        except Exception:
            return []
    rows = list(rows or [])
    if not include_inactive:
        rows = [r for r in rows if bool(r.get("is_active", True))]

    loc = str(customer_location_id or "").strip()
    if not loc:
        def _sort_key_all(r: dict) -> tuple:
            prim = 0 if r.get("is_primary") else 1
            name = str(r.get("contact_name") or "").strip().lower()
            return (prim, name)

        rows.sort(key=_sort_key_all)
        return rows

    scoped: list[dict] = []
    for r in rows:
        rl = _contact_row_location_id(r)
        if rl == loc or not rl:
            scoped.append(r)

    def _sort_key_scoped(r: dict) -> tuple:
        rl = _contact_row_location_id(r)
        site_first = 0 if rl == loc else 1
        prim = 0 if r.get("is_primary") else 1
        name = str(r.get("contact_name") or "").strip().lower()
        return (site_first, prim, name)

    scoped.sort(key=_sort_key_scoped)
    return scoped


_CONTACT_PICKER_STYLE_KEY = "ips_contact_picker_styles_injected"


def inject_contact_picker_styles() -> None:
    """IPS dark-theme polish for contact preview + quick-add (Estimates / Jobs)."""
    if st.session_state.get(_CONTACT_PICKER_STYLE_KEY):
        return
    st.session_state[_CONTACT_PICKER_STYLE_KEY] = True
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-contact-quick-add) {
            background: rgba(15, 23, 42, 0.55) !important;
            border: 1px solid rgba(100, 116, 139, 0.42) !important;
            border-radius: 10px !important;
            padding: 10px 12px 12px 12px !important;
            margin-top: 6px !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
        }
        .ips-contact-quick-add-title {
            color: #e2e8f0 !important;
            font-size: 0.82rem !important;
            font-weight: 650 !important;
            margin: 0 0 6px 0 !important;
            letter-spacing: -0.01em;
        }
        .ips-contact-preview {
            margin-top: 6px;
            padding: 8px 10px;
            border-radius: 8px;
            border: 1px solid rgba(71, 85, 105, 0.55);
            background: rgba(15, 23, 42, 0.45);
        }
        .ips-contact-preview .ips-cp-name {
            color: #f1f5f9;
            font-size: 0.88rem;
            font-weight: 600;
            margin: 0 0 4px 0;
        }
        .ips-contact-preview .ips-cp-role {
            color: #cbd5e1;
            font-size: 0.8rem;
            font-weight: 500;
            margin: 0 0 6px 0;
        }
        .ips-contact-preview .ips-cp-line {
            color: #94a3b8;
            font-size: 0.78rem;
            line-height: 1.45;
            margin: 0;
        }
        .ips-contact-preview .ips-cp-label {
            color: #64748b;
            font-weight: 600;
            margin-right: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _contact_key_suffix(customer_id: str) -> str:
    raw = str(customer_id or "").strip()
    if not raw:
        return "x"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]


def contact_none_option_label() -> str:
    return "— No contact —"


def contact_option_label(c: dict) -> str:
    """Dropdown label: ``Name — Title/role`` (primary contacts sort first via :func:`fetch_contacts_for_customer`)."""
    name = str(c.get("contact_name") or "").strip() or "—"
    title = str(c.get("title") or c.get("role") or "").strip()
    if title:
        return f"{name} — {title}"
    return name


def render_contact_detail_preview(picked: dict | None) -> None:
    """Title/role + email / phone / mobile preview under the contact field."""
    if not picked:
        return
    inject_contact_picker_styles()
    nm = str(picked.get("contact_name") or "").strip() or "—"
    title = str(picked.get("title") or picked.get("role") or "").strip()
    em = str(picked.get("email") or "").strip()
    ph = str(picked.get("phone") or "").strip()
    mob = str(picked.get("mobile") or "").strip()
    if not title and not em and not ph and not mob:
        return
    role_html = f'<p class="ips-cp-role">{html.escape(title)}</p>' if title else ""
    lines = []
    if em:
        lines.append(
            f'<p class="ips-cp-line"><span class="ips-cp-label">Email</span>{html.escape(em)}</p>'
        )
    if ph:
        lines.append(
            f'<p class="ips-cp-line"><span class="ips-cp-label">Phone</span>{html.escape(ph)}</p>'
        )
    if mob:
        lines.append(
            f'<p class="ips-cp-line"><span class="ips-cp-label">Mobile</span>{html.escape(mob)}</p>'
        )
    st.markdown(
        f'<div class="ips-contact-preview">'
        f'<p class="ips-cp-name">{html.escape(nm)}</p>'
        f"{role_html}"
        f'{"".join(lines)}'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_contact_quick_add_when_empty(
    *,
    customer_id: str,
    key_prefix: str,
    disabled: bool,
    customer_location_id: str | None = None,
) -> None:
    """Compact add form when a customer has no active contacts for the current scope."""
    if disabled or not str(customer_id or "").strip():
        return
    inject_contact_picker_styles()
    suf = _contact_key_suffix(customer_id) + _contact_key_suffix(str(customer_location_id or ""))
    with st.container(border=True):
        st.markdown('<span class="ips-contact-quick-add"></span>', unsafe_allow_html=True)
        st.markdown(
            '<p class="ips-contact-quick-add-title">Add contact</p>',
            unsafe_allow_html=True,
        )
        st.caption("No contacts yet — add someone for this customer.")
        n1 = st.text_input("Name", key=f"{key_prefix}_qc_name_{suf}")
        n2 = st.text_input("Title", key=f"{key_prefix}_qc_title_{suf}", help="Job title or role")
        n3 = st.text_input("Email", key=f"{key_prefix}_qc_email_{suf}")
        n4 = st.text_input("Phone", key=f"{key_prefix}_qc_phone_{suf}")
        n5 = st.text_input("Mobile", key=f"{key_prefix}_qc_mobile_{suf}")
        prim = st.checkbox("Set as primary contact", value=True, key=f"{key_prefix}_qc_prim_{suf}")
        if st.button("Save contact", type="primary", use_container_width=True, key=f"{key_prefix}_qc_save_{suf}"):
            t = str(n1 or "").strip()
            if not t:
                st.error("Name is required.")
                st.stop()
            tt = str(n2 or "").strip()
            payload = {
                "customer_id": str(customer_id).strip(),
                "contact_name": t,
                "role": tt,
                "title": tt,
                "email": str(n3 or "").strip(),
                "phone": str(n4 or "").strip(),
                "mobile": str(n5 or "").strip(),
                "notes": "",
                "is_primary": False,
                "is_active": True,
            }
            loc = str(customer_location_id or "").strip()
            if loc:
                payload["customer_location_id"] = loc
            try:
                inserted = insert_contact_row(payload)
            except Exception:
                payload.pop("customer_location_id", None)
                try:
                    inserted = insert_contact_row(payload)
                except Exception:
                    payload.pop("title", None)
                    payload.pop("mobile", None)
                    inserted = insert_contact_row(payload)
            new_id = str((inserted or {}).get("id") or "")
            if prim and new_id:
                set_primary_contact(customer_id=str(customer_id).strip(), contact_id=new_id)
            st.success("Contact added.")
            st.rerun()


def clear_primary_for_customer_except(*, customer_id: str, keep_contact_id: str) -> None:
    """Ensure at most one primary per customer (app-enforced)."""
    cid = str(customer_id or "").strip()
    keep = str(keep_contact_id or "").strip()
    if not cid or not keep:
        return
    rows = fetch_contacts_for_customer(cid)
    for r in rows:
        rid = str(r.get("id") or "")
        if not rid or rid == keep:
            continue
        if r.get("is_primary"):
            try:
                update_rows_admin("customer_contacts", {"is_primary": False}, {"id": rid})
            except Exception:
                update_rows("customer_contacts", {"is_primary": False}, {"id": rid})


def set_primary_contact(*, customer_id: str, contact_id: str) -> None:
    clear_primary_for_customer_except(customer_id=customer_id, keep_contact_id=contact_id)
    try:
        update_rows_admin("customer_contacts", {"is_primary": True}, {"id": contact_id})
    except Exception:
        update_rows("customer_contacts", {"is_primary": True}, {"id": contact_id})


def insert_contact_row(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return insert_row("customer_contacts", payload)
    except Exception:
        return insert_row_admin("customer_contacts", payload)


def delete_contact(contact_id: str) -> None:
    try:
        delete_rows_admin("customer_contacts", {"id": contact_id})
    except Exception:
        delete_rows("customer_contacts", {"id": contact_id})
