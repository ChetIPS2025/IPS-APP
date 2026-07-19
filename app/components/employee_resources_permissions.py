"""Employee Resources permission snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from app.auth import effective_role
from app.utils.permissions import normalize_role


@dataclass(frozen=True)
class EmployeeResourcesPermissions:
    role: str
    user_id: str
    user_name: str
    is_admin: bool
    can_manage: bool
    can_create: bool
    can_edit: bool
    can_delete: bool


def load_employee_resources_permissions() -> EmployeeResourcesPermissions:
    from app.perf_debug import perf_span

    with perf_span("employee_resources.permissions"):
        role = str(effective_role() or "").strip()
        norm = normalize_role(role)
        try:
            import streamlit as st

            user = st.session_state.get("user") or {}
        except Exception:
            user = {}
        user_id = str(user.get("id") or user.get("sub") or "")
        user_name = str(user.get("name") or user.get("email") or "")
        is_admin = norm == "admin"
        return EmployeeResourcesPermissions(
            role=role,
            user_id=user_id,
            user_name=user_name,
            is_admin=is_admin,
            can_manage=is_admin,
            can_create=is_admin,
            can_edit=is_admin,
            can_delete=is_admin,
        )
