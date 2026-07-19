"""Estimate Cost Builder permission snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from app.auth import current_role


@dataclass(frozen=True)
class EstimateBuilderPermissions:
    role: str
    user_id: str
    user_name: str
    is_admin: bool
    can_edit: bool
    can_manage_default_rates: bool
    can_recalculate: bool
    can_generate_proposal: bool


def load_estimate_builder_permissions() -> EstimateBuilderPermissions:
    role = str(current_role() or "").strip()
    try:
        import streamlit as st

        user = st.session_state.get("user") or {}
    except Exception:
        user = {}
    user_id = str(user.get("id") or user.get("sub") or "")
    user_name = str(user.get("name") or user.get("email") or "")
    role_lower = role.lower()
    is_admin = role_lower in {"admin", "administrator", "owner"}
    can_edit = role_lower in {"admin", "administrator", "owner", "estimator", "manager", "project manager"}
    return EstimateBuilderPermissions(
        role=role,
        user_id=user_id,
        user_name=user_name,
        is_admin=is_admin,
        can_edit=can_edit,
        can_manage_default_rates=is_admin,
        can_recalculate=can_edit,
        can_generate_proposal=can_edit,
    )
