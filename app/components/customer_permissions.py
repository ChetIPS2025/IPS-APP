"""Customer permissions snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from app.auth import effective_role
from app.utils.permissions import normalize_role


@dataclass(frozen=True)
class CustomerPermissions:
    role: str
    user_id: str
    user_name: str
    can_create: bool
    can_edit_customer: bool
    can_edit_location: bool
    can_edit_contact: bool
    can_delete: bool
    can_view_documents: bool


def load_customer_permissions() -> CustomerPermissions:
    role = str(effective_role() or "").strip()
    norm = normalize_role(role)
    try:
        import streamlit as st

        user = st.session_state.get("user") or {}
    except Exception:
        user = {}
    user_id = str(user.get("id") or user.get("sub") or "")
    user_name = str(user.get("name") or user.get("email") or "")
    can_manage = norm in {"admin", "supervisor", "manager", "office"}
    return CustomerPermissions(
        role=role,
        user_id=user_id,
        user_name=user_name,
        can_create=can_manage,
        can_edit_customer=can_manage,
        can_edit_location=can_manage,
        can_edit_contact=can_manage,
        can_delete=norm in {"admin", "manager"},
        can_view_documents=can_manage,
    )
