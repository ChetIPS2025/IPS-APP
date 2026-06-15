"""Per-row action menu for the Jobs list table."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.services.jobs_service import can_manage_job_actions
except ImportError:
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


def render_job_row_actions(
    job: dict[str, Any],
    *,
    on_open: Callable[[str, dict[str, Any]], None],
    on_edit: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    """Popover: View Details, Edit, and existing lifecycle actions."""
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
        if st.button("View Details", key=f"job_row_view_{job_key}", use_container_width=True):
            on_open(jid, job)
            st.rerun()
        if on_edit is not None and st.button("Edit Job", key=f"job_row_edit_{job_key}", use_container_width=True):
            on_edit(job)
            on_open(jid, job)
            st.rerun()
        if not archived and can_manage:
            if status not in {"Completed", "Closed"} and st.button(
                "Job Complete",
                key=f"job_row_complete_{job_key}",
                use_container_width=True,
            ):
                st.session_state[_confirm_state_key(jid, "complete")] = True
                on_open(jid, job)
                st.rerun()
            if status != "Cancelled" and st.button(
                "Cancel Job",
                key=f"job_row_cancel_{job_key}",
                use_container_width=True,
            ):
                st.session_state[_confirm_state_key(jid, "cancel")] = True
                on_open(jid, job)
                st.rerun()
            if st.button("Delete Job", key=f"job_row_delete_{job_key}", use_container_width=True):
                st.session_state[_confirm_state_key(jid, "delete")] = True
                on_open(jid, job)
                st.rerun()
