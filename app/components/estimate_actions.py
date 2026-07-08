"""Estimate detail modal — approve and delete action buttons."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.auth import current_role, effective_role
    from app.components.action_styles import danger_solid_button, success_solid_button
    from app.components.modal_delete import can_admin_mutate
    from app.pages._core._crud import is_demo_id
    from app.services.estimate_job_workflow_service import (
        approve_estimate_and_sync_job,
        can_approve_estimates,
        estimate_status_approvable,
        estimate_visible_in_approved_view,
    )
    from app.services.repository import clear_data_cache_for_table
except ImportError:
    from auth import current_role, effective_role  # type: ignore
    from components.action_styles import danger_solid_button, success_solid_button  # type: ignore
    from components.modal_delete import can_admin_mutate  # type: ignore
    from pages._core._crud import is_demo_id  # type: ignore
    from services.estimate_job_workflow_service import (  # type: ignore
        approve_estimate_and_sync_job,
        can_approve_estimates,
        estimate_status_approvable,
        estimate_visible_in_approved_view,
    )
    from services.repository import clear_data_cache_for_table  # type: ignore


def _confirm_state_key(estimate_id: str, action: str) -> str:
    return f"confirm_{action}_estimate_{estimate_id}"


def _can_show_approve(est: dict) -> bool:
    if not can_approve_estimates(effective_role()):
        return False
    eid = str(est.get("id") or "").strip()
    if not eid or is_demo_id(eid):
        return False
    if estimate_visible_in_approved_view(est):
        return False
    return estimate_status_approvable(est.get("status"))


def _render_confirm_card(
    *,
    estimate_id: str,
    action: str,
    title: str,
    message: str,
    confirm_label: str,
    confirm_fn: Callable[[], bool],
) -> None:
    confirm_key = _confirm_state_key(estimate_id, action)
    st.markdown(
        f'<div class="ips-confirm-card">'
        f'<div class="ips-confirm-title">{html.escape(title)}</div>'
        f'<div class="ips-confirm-text">{html.escape(message)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    btn_cancel, btn_confirm = st.columns(2, gap="small")
    with btn_cancel:
        if st.button("Cancel", key=f"est_act_dismiss_{action}_{estimate_id}", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    with btn_confirm:
        clicked = False
        if action == "approve":
            clicked = success_solid_button(confirm_label, f"confirm_{action}_{estimate_id}", use_container_width=True)
        else:
            clicked = danger_solid_button(confirm_label, f"confirm_{action}_{estimate_id}", use_container_width=True)
        if clicked and confirm_fn():
            st.session_state.pop(confirm_key, None)
            st.rerun()


def render_estimate_action_buttons(
    est: dict,
    *,
    on_approve: Callable[[], None] | None = None,
    on_delete: Callable[[], None] | None = None,
) -> None:
    """Render compact Estimate Actions row with inline confirmation panels."""
    eid = str(est.get("id") or "").strip()
    if not eid or is_demo_id(eid):
        return

    est_key = "".join(ch if ch.isalnum() else "_" for ch in eid) or "est"
    can_delete = can_admin_mutate()
    show_approve = _can_show_approve(est)

    if not show_approve and not can_delete:
        if not can_approve_estimates(effective_role()) and not can_delete:
            st.caption("You do not have permission to change this estimate.")
        return

    for action in ("approve", "delete"):
        if st.session_state.get(_confirm_state_key(eid, action)):
            if action == "approve":
                _render_confirm_card(
                    estimate_id=eid,
                    action=action,
                    title="Approve Estimate",
                    message=(
                        "Are you sure you want to approve this estimate and activate the linked job? "
                        "The estimate will move to Approved / Converted."
                    ),
                    confirm_label="Confirm Approve",
                    confirm_fn=lambda: _handle_approve(eid, on_approve),
                )
            else:
                _render_confirm_card(
                    estimate_id=eid,
                    action=action,
                    title="Delete Estimate",
                    message=(
                        "Are you sure you want to delete this estimate? "
                        "Linked jobs will be unlinked first."
                    ),
                    confirm_label="Confirm Delete",
                    confirm_fn=lambda: _handle_delete(eid, on_delete),
                )
            return

    action_specs: list[tuple[str, Any, str, str]] = []
    if show_approve:
        action_specs.append(("approve", success_solid_button, "Approve Estimate", f"open_approve_{est_key}"))
    if can_delete:
        action_specs.append(("delete", danger_solid_button, "Delete Estimate", f"open_delete_{est_key}"))

    if not action_specs:
        return

    with st.container(key=f"estimate_actions_{est_key}"):
        st.markdown('<span class="ips-estimate-actions-marker"></span>', unsafe_allow_html=True)
        st.markdown('<p class="ips-estimate-actions-title">Estimate Actions</p>', unsafe_allow_html=True)
        cols = st.columns(len(action_specs), gap="small")
        for col, (action, btn_fn, label, suffix) in zip(cols, action_specs):
            with col:
                if btn_fn(label, suffix, use_container_width=False):
                    st.session_state[_confirm_state_key(eid, action)] = True
                    st.rerun()


def _handle_approve(estimate_id: str, on_approve: Callable[[], None] | None) -> bool:
    res = approve_estimate_and_sync_job(estimate_id)
    if res.ok:
        clear_data_cache_for_table("estimates")
        st.success(res.message or "Estimate approved and linked job activated.")
        if on_approve:
            on_approve()
        return True
    st.error(res.message or "Could not approve estimate.")
    return False


def _handle_delete(estimate_id: str, on_delete: Callable[[], None] | None) -> bool:
    try:
        from app.services.delete_safety import delete_estimate_unlink_first
    except ImportError:
        from services.delete_safety import delete_estimate_unlink_first  # type: ignore
    try:
        delete_estimate_unlink_first(estimate_id)
        clear_data_cache_for_table("estimates")
        st.success("Estimate deleted.")
        if on_delete:
            on_delete()
        return True
    except Exception as exc:
        st.error(f"Could not delete estimate: {exc}")
        return False
