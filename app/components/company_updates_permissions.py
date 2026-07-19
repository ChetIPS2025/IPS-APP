"""Company Updates permission snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from app.auth import effective_role
from app.utils.permissions import can_manage_company_updates, normalize_role


@dataclass(frozen=True)
class CompanyUpdatesPermissions:
    role: str
    user_id: str
    user_name: str
    can_manage: bool
    can_create: bool
    can_edit: bool
    can_delete: bool
    can_view_read_receipts: bool


def load_company_updates_permissions() -> CompanyUpdatesPermissions:
    role = str(effective_role() or "").strip()
    norm = normalize_role(role)
    try:
        import streamlit as st

        user = st.session_state.get("user") or {}
    except Exception:
        user = {}
    user_id = str(user.get("id") or user.get("sub") or "")
    user_name = str(user.get("name") or user.get("email") or "")
    can_manage = can_manage_company_updates(role)
    can_view_receipts = norm in {"admin", "supervisor", "manager"}
    return CompanyUpdatesPermissions(
        role=role,
        user_id=user_id,
        user_name=user_name,
        can_manage=can_manage,
        can_create=can_manage,
        can_edit=can_manage,
        can_delete=can_manage,
        can_view_read_receipts=can_view_receipts,
    )
