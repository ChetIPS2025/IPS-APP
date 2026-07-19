"""Task permission snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from app.auth import current_profile, effective_role


@dataclass(frozen=True)
class TaskPermissions:
    role: str
    user_id: str
    employee_id: str
    user_name: str
    email: str
    can_create: bool
    can_edit: bool
    can_delete: bool
    can_reassign: bool
    can_view_all_tasks: bool
    is_field_employee: bool
    employee_match_ids: tuple[str, ...]


def load_task_permissions() -> TaskPermissions:
    role = str(effective_role() or "").strip()
    prof = current_profile() or {}
    try:
        import streamlit as st

        user = st.session_state.get("user") or {}
        auth_emp = st.session_state.get("auth_employee") or {}
    except Exception:
        user = {}
        auth_emp = {}
    user_id = str(user.get("id") or user.get("sub") or prof.get("id") or "").strip()
    employee_id = str(prof.get("employee_id") or auth_emp.get("id") or "").strip()
    user_name = str(prof.get("full_name") or prof.get("name") or user.get("name") or "").strip()
    email = str(prof.get("email") or user.get("email") or "").strip()
    role_lower = role.lower()
    is_field_employee = role_lower == "employee"
    can_manage = role_lower in {
        "admin",
        "administrator",
        "owner",
        "manager",
        "project manager",
        "supervisor",
        "estimator",
    }
    match_ids: set[str] = set()
    for val in (user_id, employee_id, email, user_name, prof.get("full_name"), prof.get("name")):
        s = str(val or "").strip().lower()
        if s:
            match_ids.add(s)
    if isinstance(auth_emp, dict):
        for val in (auth_emp.get("id"), auth_emp.get("name"), auth_emp.get("email")):
            s = str(val or "").strip().lower()
            if s:
                match_ids.add(s)
    return TaskPermissions(
        role=role,
        user_id=user_id,
        employee_id=employee_id,
        user_name=user_name,
        email=email,
        can_create=can_manage or not is_field_employee,
        can_edit=can_manage or not is_field_employee,
        can_delete=can_manage,
        can_reassign=can_manage,
        can_view_all_tasks=can_manage,
        is_field_employee=is_field_employee,
        employee_match_ids=tuple(sorted(match_ids)),
    )


__all__ = ["TaskPermissions", "load_task_permissions"]
