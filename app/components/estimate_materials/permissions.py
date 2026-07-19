"""Estimate Materials permission snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from app.auth import current_role


@dataclass(frozen=True)
class EstimateMaterialsPermissions:
    role: str
    user_id: str
    user_name: str
    can_edit: bool
    can_delete: bool
    can_export: bool
    can_apply_markup: bool


def load_estimate_materials_permissions() -> EstimateMaterialsPermissions:
    role = str(current_role() or "").strip()
    try:
        import streamlit as st

        user = st.session_state.get("user") or {}
    except Exception:
        user = {}
    user_id = str(user.get("id") or user.get("sub") or "")
    user_name = str(user.get("name") or user.get("email") or "")
    role_lower = role.lower()
    can_edit = role_lower in {
        "admin",
        "administrator",
        "owner",
        "estimator",
        "manager",
        "project manager",
    }
    return EstimateMaterialsPermissions(
        role=role,
        user_id=user_id,
        user_name=user_name,
        can_edit=can_edit,
        can_delete=can_edit,
        can_export=True,
        can_apply_markup=can_edit,
    )


__all__ = ["EstimateMaterialsPermissions", "load_estimate_materials_permissions"]
