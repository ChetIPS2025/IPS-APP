"""Job detail modal — complete, cancel, and soft-delete action buttons."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.components.action_styles import danger_solid_button, success_solid_button, warning_solid_button
    from app.services.jobs_service import (
        cancel_job,
        can_manage_job_actions,
        complete_job,
        soft_delete_job,
    )
except ImportError:
    from components.action_styles import danger_solid_button, success_solid_button, warning_solid_button  # type: ignore
    from services.jobs_service import (  # type: ignore
        cancel_job,
        can_manage_job_actions,
        complete_job,
        soft_delete_job,
    )


def _confirm_state_key(job_id: str, action: str) -> str:
    return f"confirm_{action}_job_{job_id}"


def _job_is_archived(job: dict) -> bool:
    if bool(job.get("is_deleted")):
        return True
    status = str(job.get("status") or "").strip().lower()
    return status in {"deleted", "archived"}


def _normalize_status(job: dict) -> str:
    raw = str(job.get("status") or "").strip().lower().replace("_", " ")
    mapping = {
        "completed": "Completed",
        "closed": "Closed",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
        "archived": "Archived",
        "deleted": "Deleted",
    }
    return mapping.get(raw, str(job.get("status") or "Draft").strip() or "Draft")


def _render_confirm_card(
    *,
    job_id: str,
    action: str,
    title: str,
    message: str,
    confirm_label: str,
    confirm_fn: Callable[[str | None], bool],
    reason_key: str | None = None,
    reason_label: str | None = None,
) -> None:
    confirm_key = _confirm_state_key(job_id, action)
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
        if st.button("Cancel", key=f"job_act_dismiss_{action}_{job_id}", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    with btn_confirm:
        clicked = False
        if action == "complete":
            clicked = success_solid_button(confirm_label, f"confirm_{action}_{job_id}", use_container_width=True)
        elif action == "cancel":
            clicked = warning_solid_button(confirm_label, f"confirm_{action}_{job_id}", use_container_width=True)
        else:
            clicked = danger_solid_button(confirm_label, f"confirm_{action}_{job_id}", use_container_width=True)
        if clicked and confirm_fn(reason_value):
            st.session_state.pop(confirm_key, None)
            st.rerun()


def render_job_lifecycle_confirmations(
    job: dict,
    *,
    on_complete: Callable[[], None] | None = None,
    on_cancel: Callable[[], None] | None = None,
    on_delete: Callable[[], None] | None = None,
) -> bool:
    """Render confirm cards when triggered from the header menu. Returns True if a confirm is showing."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        return False

    job_key = "".join(ch if ch.isalnum() else "_" for ch in jid) or "job"

    for action in ("complete", "cancel", "delete"):
        if st.session_state.get(_confirm_state_key(jid, action)):
            if action == "complete":
                _render_confirm_card(
                    job_id=jid,
                    action=action,
                    title="Complete Job",
                    message="Are you sure you want to mark this job as complete?",
                    confirm_label="Confirm Complete",
                    confirm_fn=lambda reason: _handle_complete(jid, on_complete),
                )
            elif action == "cancel":
                _render_confirm_card(
                    job_id=jid,
                    action=action,
                    title="Cancel Job",
                    message="Are you sure you want to cancel this job?",
                    confirm_label="Confirm Cancel Job",
                    confirm_fn=lambda reason: _handle_cancel(jid, on_cancel, reason=reason),
                    reason_key=f"job_cancel_reason_{job_key}",
                    reason_label="Cancellation reason (optional)",
                )
            else:
                _render_confirm_card(
                    job_id=jid,
                    action=action,
                    title="Archive Job",
                    message=(
                        "Are you sure you want to archive this job? "
                        "Historical records will be preserved."
                    ),
                    confirm_label="Confirm Archive",
                    confirm_fn=lambda reason: _handle_delete(jid, on_delete, reason=reason),
                    reason_key=f"job_delete_reason_{job_key}",
                    reason_label="Archive reason (optional)",
                )
            return True
    return False


def render_job_action_buttons(
    job: dict,
    *,
    on_edit: Callable[[dict], None] | None = None,
    edit_key: str | None = None,
    on_complete: Callable[[], None] | None = None,
    on_cancel: Callable[[], None] | None = None,
    on_delete: Callable[[], None] | None = None,
) -> None:
    """Render Job Details action row: Edit, Complete, Cancel, Delete."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        return

    job_key = "".join(ch if ch.isalnum() else "_" for ch in jid) or "job"
    archived = _job_is_archived(job)
    can_manage = can_manage_job_actions()

    for action in ("complete", "cancel", "delete"):
        if st.session_state.get(_confirm_state_key(jid, action)):
            if action == "complete":
                _render_confirm_card(
                    job_id=jid,
                    action=action,
                    title="Complete Job",
                    message="Are you sure you want to mark this job as complete?",
                    confirm_label="Confirm Complete",
                    confirm_fn=lambda reason: _handle_complete(jid, on_complete),
                )
            elif action == "cancel":
                _render_confirm_card(
                    job_id=jid,
                    action=action,
                    title="Cancel Job",
                    message="Are you sure you want to cancel this job?",
                    confirm_label="Confirm Cancel Job",
                    confirm_fn=lambda reason: _handle_cancel(jid, on_cancel, reason=reason),
                    reason_key=f"job_cancel_reason_{job_key}",
                    reason_label="Cancellation reason (optional)",
                )
            else:
                _render_confirm_card(
                    job_id=jid,
                    action=action,
                    title="Delete Job",
                    message=(
                        "Are you sure you want to delete/archive this job? "
                        "Historical records will be preserved."
                    ),
                    confirm_label="Confirm Delete Job",
                    confirm_fn=lambda reason: _handle_delete(jid, on_delete, reason=reason),
                    reason_key=f"job_delete_reason_{job_key}",
                    reason_label="Delete reason (optional)",
                )
            return

    action_specs: list[tuple[str, Any, str, str]] = []
    if on_edit is not None:
        action_specs.append(("edit", None, "Edit", edit_key or f"job_detail_edit_{job_key}"))

    if not archived and can_manage:
        status = _normalize_status(job)
        show_complete = status not in {"Completed", "Closed"}
        show_cancel = status != "Cancelled"
        if show_complete:
            action_specs.append(("complete", success_solid_button, "Job Complete", f"open_complete_{job_key}"))
        if show_cancel:
            action_specs.append(("cancel", warning_solid_button, "Cancel Job", f"open_cancel_{job_key}"))
        action_specs.append(("delete", danger_solid_button, "Delete Job", f"open_delete_{job_key}"))

    if not action_specs:
        if archived:
            st.caption("This job is archived. Restore is not yet available.")
        elif not can_manage:
            st.caption("Only admin, supervisor, or project manager can change job status.")
        return

    with st.container(key=f"job_actions_{job_key}"):
        st.markdown(
            '<span class="job-detail-actions-row-marker ips-job-actions-marker"></span>',
            unsafe_allow_html=True,
        )
        cols = st.columns(len(action_specs), gap="small")
        for col, (action, btn_fn, label, suffix) in zip(cols, action_specs):
            with col:
                if action == "edit":
                    st.markdown('<span class="job-detail-edit-marker"></span>', unsafe_allow_html=True)
                    st.button(
                        label,
                        key=suffix,
                        type="secondary",
                        use_container_width=False,
                        on_click=on_edit,
                        args=(job,),
                    )
                elif btn_fn(label, suffix, use_container_width=False):
                    st.session_state[_confirm_state_key(jid, action)] = True
                    st.rerun()

    if archived and on_edit is not None:
        st.caption("This job is archived. Restore is not yet available.")
    elif not can_manage and on_edit is not None:
        st.caption("Only admin, supervisor, or project manager can change job status.")


def _handle_complete(job_id: str, on_complete: Callable[[], None] | None, *, reason: str | None = None) -> bool:
    _ = reason
    result = complete_job(job_id)
    if result.ok:
        st.success("Job marked complete.")
        if on_complete:
            on_complete()
        return True
    st.error(result.error or "Could not complete job.")
    return False


def _handle_cancel(job_id: str, on_cancel: Callable[[], None] | None, *, reason: str | None = None) -> bool:
    result = cancel_job(job_id, reason=reason or None)
    if result.ok:
        st.success("Job cancelled.")
        if on_cancel:
            on_cancel()
        return True
    st.error(result.error or "Could not cancel job.")
    return False


def _handle_delete(job_id: str, on_delete: Callable[[], None] | None, *, reason: str | None = None) -> bool:
    result = soft_delete_job(job_id, reason=reason or None)
    if result.ok:
        st.success("Job archived.")
        if on_delete:
            on_delete()
        return True
    st.error(result.error or "Could not archive job.")
    return False
