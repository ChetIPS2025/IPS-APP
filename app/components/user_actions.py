"""User detail modal — activate, deactivate, and soft-delete action buttons."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.auth import current_profile
    from app.components.action_styles import danger_solid_button, success_solid_button, warning_solid_button
    from app.services.users_service import (
        activate_user,
        can_delete_user,
        can_manage_user_actions,
        deactivate_user,
        soft_delete_user,
    )
except ImportError:
    from auth import current_profile  # type: ignore
    from components.action_styles import danger_solid_button, success_solid_button, warning_solid_button  # type: ignore
    from services.users_service import (  # type: ignore
        activate_user,
        can_delete_user,
        can_manage_user_actions,
        deactivate_user,
        soft_delete_user,
    )


def _confirm_state_key(user_id: str, action: str) -> str:
    return f"confirm_{action}_user_{user_id}"


def _normalize_status(user: dict) -> str:
    raw = str(user.get("status") or "").strip().lower()
    if raw in {"active", "enabled", ""}:
        return "Active"
    if raw in {"inactive", "disabled"}:
        return "Inactive"
    if raw in {"deleted", "archived"}:
        return "Deleted"
    return str(user.get("status") or "Active").strip() or "Active"


def _render_confirm_card(
    *,
    user_id: str,
    action: str,
    title: str,
    message: str,
    confirm_label: str,
    confirm_fn: Callable[[str | None], bool],
    reason_key: str | None = None,
    reason_label: str | None = None,
) -> None:
    confirm_key = _confirm_state_key(user_id, action)
    st.markdown(
        f'<div class="ips-confirm-card">'
        f'<div class="ips-confirm-title">{html.escape(title)}</div>'
        f'<div class="ips-confirm-text">{html.escape(message)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    reason_value: str | None = None
    if reason_key and reason_label:
        reason_value = str(st.text_input(reason_label, key=reason_key) or "").strip() or None

    btn_cancel, btn_confirm = st.columns(2, gap="small")
    with btn_cancel:
        if st.button("Cancel", key=f"user_act_dismiss_{action}_{user_id}", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    with btn_confirm:
        clicked = False
        if action == "activate":
            clicked = success_solid_button(confirm_label, f"confirm_{action}_{user_id}", use_container_width=True)
        elif action == "deactivate":
            clicked = warning_solid_button(confirm_label, f"confirm_{action}_{user_id}", use_container_width=True)
        else:
            clicked = danger_solid_button(confirm_label, f"confirm_{action}_{user_id}", use_container_width=True)
        if clicked and confirm_fn(reason_value):
            st.session_state.pop(confirm_key, None)
            st.rerun()


def render_user_action_buttons(
    user: dict,
    *,
    on_activate: Callable[[], None] | None = None,
    on_deactivate: Callable[[], None] | None = None,
    on_delete: Callable[[], None] | None = None,
) -> None:
    """Render compact User Actions row with inline confirmation panels."""
    uid = str(user.get("id") or "").strip()
    if not uid:
        return

    if not can_manage_user_actions():
        st.caption("Only admin or supervisor can manage user status.")
        return

    check = can_delete_user(uid, current_user=current_profile())
    status = _normalize_status(user)
    user_key = "".join(ch if ch.isalnum() else "_" for ch in uid) or "user"
    actor = current_profile()
    actor_id = str(actor.get("id") or "").strip() or None

    for action in ("activate", "deactivate", "delete"):
        if st.session_state.get(_confirm_state_key(uid, action)):
            if action == "activate":
                _render_confirm_card(
                    user_id=uid,
                    action=action,
                    title="Activate User",
                    message="Are you sure you want to activate this user?",
                    confirm_label="Confirm Activate",
                    confirm_fn=lambda reason: _handle_activate(uid, actor_id, on_activate, reason=reason),
                )
            elif action == "deactivate":
                _render_confirm_card(
                    user_id=uid,
                    action=action,
                    title="Deactivate User",
                    message="Are you sure you want to deactivate this user?",
                    confirm_label="Confirm Deactivate",
                    confirm_fn=lambda reason: _handle_deactivate(
                        uid, actor_id, actor, on_deactivate, reason=reason, check=check
                    ),
                    reason_key=f"user_deactivate_reason_{user_key}",
                    reason_label="Deactivation reason (optional)",
                )
            else:
                _render_confirm_card(
                    user_id=uid,
                    action=action,
                    title="Delete User",
                    message=(
                        "Are you sure you want to delete/archive this user? "
                        "Historical records will be preserved."
                    ),
                    confirm_label="Confirm Delete User",
                    confirm_fn=lambda reason: _handle_delete(
                        uid, actor_id, actor, on_delete, reason=reason, check=check
                    ),
                    reason_key=f"user_delete_reason_{user_key}",
                    reason_label="Delete reason (optional)",
                )
            return

    show_activate = status != "Active"
    show_deactivate = status == "Active"
    action_specs: list[tuple[str, Any, str, str]] = []
    if show_activate:
        action_specs.append(("activate", success_solid_button, "Activate User", f"open_activate_{user_key}"))
    if show_deactivate:
        action_specs.append(
            ("deactivate", warning_solid_button, "Deactivate User", f"open_deactivate_{user_key}")
        )
    if status != "Deleted":
        action_specs.append(("delete", danger_solid_button, "Delete User", f"open_delete_{user_key}"))

    if not action_specs:
        st.caption("No user actions available for this status.")
        return

    with st.container(key=f"user_actions_{user_key}"):
        st.markdown('<span class="ips-user-actions-marker"></span>', unsafe_allow_html=True)
        st.markdown('<p class="ips-user-actions-title">User Actions</p>', unsafe_allow_html=True)
        cols = st.columns(len(action_specs), gap="small")
        for col, (action, btn_fn, label, suffix) in zip(cols, action_specs):
            with col:
                disabled = action in {"deactivate", "delete"} and not check.allowed
                help = check.reason if disabled and check.reason else None
                if btn_fn(label, suffix, use_container_width=False, disabled=disabled, help=help):
                    st.session_state[_confirm_state_key(uid, action)] = True
                    st.rerun()

    if not check.allowed and check.reason and status != "Deleted":
        st.caption(check.reason)


def _handle_activate(
    user_id: str,
    actor_id: str | None,
    on_activate: Callable[[], None] | None,
    *,
    reason: str | None = None,
) -> bool:
    _ = reason
    result = activate_user(user_id, activated_by=actor_id, actor=current_profile())
    if result.ok:
        if isinstance(result.data, dict) and result.data.get("warning"):
            st.session_state["users_action_flash"] = ("warning", f"User activated. {result.data['warning']}")
        else:
            st.session_state["users_action_flash"] = ("success", "User activated.")
        if on_activate:
            on_activate()
        return True
    st.error(result.error or "Could not activate user.")
    return False


def _handle_deactivate(
    user_id: str,
    actor_id: str | None,
    actor: dict,
    on_deactivate: Callable[[], None] | None,
    *,
    reason: str | None,
    check: Any,
) -> bool:
    if not check.allowed:
        st.error(check.reason or "Cannot deactivate user.")
        return False
    result = deactivate_user(user_id, reason=reason, deleted_by=actor_id, actor=actor)
    if result.ok:
        if isinstance(result.data, dict) and result.data.get("warning"):
            st.session_state["users_action_flash"] = ("warning", f"User deactivated. {result.data['warning']}")
        else:
            st.session_state["users_action_flash"] = ("success", "User deactivated.")
        if on_deactivate:
            on_deactivate()
        return True
    st.error(result.error or "Could not deactivate user.")
    return False


def _handle_delete(
    user_id: str,
    actor_id: str | None,
    actor: dict,
    on_delete: Callable[[], None] | None,
    *,
    reason: str | None,
    check: Any,
) -> bool:
    if not check.allowed:
        st.error(check.reason or "Cannot delete user.")
        return False
    result = soft_delete_user(user_id, reason=reason, deleted_by=actor_id, actor=actor)
    if result.ok:
        if isinstance(result.data, dict) and result.data.get("warning"):
            st.session_state["users_action_flash"] = ("warning", f"User archived. {result.data['warning']}")
        else:
            st.session_state["users_action_flash"] = ("success", "User archived.")
        if on_delete:
            on_delete()
        return True
    st.error(result.error or "Could not archive user.")
    return False
