"""Per-row action menu for the Jobs list table."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.components.job_status_ui import render_job_status_change_select
    from app.services.jobs_service import can_manage_job_actions
except ImportError:
    from components.job_status_ui import render_job_status_change_select  # type: ignore
    from services.jobs_service import can_manage_job_actions  # type: ignore


def _confirm_state_key(job_id: str, action: str) -> str:
    return f"confirm_{action}_job_{job_id}"


def _job_is_archived(job: dict[str, Any]) -> bool:
    if bool(job.get("is_deleted")):
        return True
    status = str(job.get("status") or "").strip().lower()
    return status in {"deleted", "archived"}


def _normalize_status(job: dict[str, Any]) -> str:
    raw = str(job.get("status") or "").strip().lower().replace("_", " ")
    mapping = {
        "completed": "Completed",
        "closed": "Closed",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
        "archived": "Archived",
        "deleted": "Deleted",
        "active": "Active",
        "awarded": "Awarded",
        "draft": "Draft",
    }
    return mapping.get(raw, str(job.get("status") or "Draft").strip() or "Draft")


def _actions_divider() -> None:
    st.markdown('<hr class="job-row-actions-divider" aria-hidden="true">', unsafe_allow_html=True)


def _action_button(
    *,
    marker: str,
    label: str,
    key: str,
    tone: str = "default",
) -> bool:
    st.markdown(
        f'<span class="job-row-action-marker job-row-action-{marker} '
        f'job-row-action-tone-{tone}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    return st.button(label, key=key, use_container_width=True)


def render_job_row_actions(
    job: dict[str, Any],
    *,
    on_open: Callable[[str, dict[str, Any]], None],
    on_edit: Callable[[dict[str, Any]], None] | None = None,
    on_status_updated: Callable[[str, str], None] | None = None,
) -> None:
    """Popover: View Details, Edit, status change, and lifecycle actions."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        return
    job_key = "".join(ch if ch.isalnum() else "_" for ch in jid) or "job"
    archived = _job_is_archived(job)
    can_manage = can_manage_job_actions()
    status = _normalize_status(job)

    st.markdown(
        '<span class="job-row-actions-menu job-actions-button" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    with st.popover(
        "Actions",
        help="Row actions",
        type="secondary",
        key=f"job_row_menu_{job_key}",
    ):
        st.markdown(
            '<span class="job-row-actions-panel" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        if _action_button(
            marker="view",
            label="View Details",
            key=f"job_row_view_{job_key}",
        ):
            on_open(jid, job)
            st.rerun()

        if on_edit is not None and _action_button(
            marker="edit",
            label="Edit Job",
            key=f"job_row_edit_{job_key}",
        ):
            on_edit(job)
            on_open(jid, job)
            st.rerun()

        if not archived and can_manage:
            _actions_divider()

            st.markdown(
                '<div class="job-row-actions-section">'
                '<span class="job-row-action-marker job-row-action-status" aria-hidden="true"></span>'
                '<p class="job-row-actions-section-title">Change Status</p>'
                "</div>",
                unsafe_allow_html=True,
            )
            render_job_status_change_select(
                job,
                key_prefix=f"job_row_{job_key}",
                on_updated=on_status_updated,
                action_menu=True,
                label="Select new status",
            )

            _actions_divider()

            if status not in {"Completed", "Closed"} and _action_button(
                marker="complete",
                label="Job Complete",
                key=f"job_row_complete_{job_key}",
                tone="success",
            ):
                st.session_state[_confirm_state_key(jid, "complete")] = True
                on_open(jid, job)
                st.rerun()

            if status != "Cancelled" and _action_button(
                marker="cancel",
                label="Cancel Job",
                key=f"job_row_cancel_{job_key}",
                tone="warning",
            ):
                st.session_state[_confirm_state_key(jid, "cancel")] = True
                on_open(jid, job)
                st.rerun()

            _actions_divider()

            if _action_button(
                marker="delete",
                label="Delete Job",
                key=f"job_row_delete_{job_key}",
                tone="danger",
            ):
                st.session_state[_confirm_state_key(jid, "delete")] = True
                on_open(jid, job)
                st.rerun()
