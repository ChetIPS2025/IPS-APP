"""Per-row action menu for the Jobs list table."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.auth import current_role
    from app.services.jobs_service import can_manage_job_actions
except ImportError:
    from auth import current_role  # type: ignore
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
        "complete": "Completed",
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


def _is_job_admin() -> bool:
    return str(current_role() or "").strip().lower() == "admin"


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
    on_open_tab: Callable[[str, dict[str, Any], str], None] | None = None,
    on_assign_employees: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    """Compact ⋮ menu: open, edit, documents, print, archive/close, delete."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        return
    job_key = "".join(ch if ch.isalnum() else "_" for ch in jid) or "job"
    archived = _job_is_archived(job)
    can_manage = can_manage_job_actions()
    is_admin = _is_job_admin()
    status = _normalize_status(job)

    st.markdown(
        '<span class="job-row-actions-menu job-actions-button ips-jobs-row-menu-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    with st.popover(
        "⋮",
        help="Job actions",
        type="secondary",
        key=f"job_row_menu_{job_key}",
    ):
        st.markdown(
            '<span class="job-row-actions-panel" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        if _action_button(
            marker="open",
            label="Open Job",
            key=f"job_row_open_{job_key}",
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

        if on_assign_employees is not None and _action_button(
            marker="assign",
            label="Assign Employees",
            key=f"job_row_assign_{job_key}",
        ):
            on_assign_employees(job)
            st.rerun()

        if on_open_tab is not None and _action_button(
            marker="documents",
            label="View Documents",
            key=f"job_row_docs_{job_key}",
        ):
            on_open_tab(jid, job, "Documents")
            st.rerun()

        if on_open_tab is not None and _action_button(
            marker="print",
            label="Print Job Packet",
            key=f"job_row_print_{job_key}",
        ):
            on_open_tab(jid, job, "IPS Forms")
            st.rerun()

        if not archived and can_manage:
            _actions_divider()

            if status not in {"Completed", "Closed"} and _action_button(
                marker="archive",
                label="Archive / Close Job",
                key=f"job_row_archive_{job_key}",
                tone="warning",
            ):
                st.session_state[_confirm_state_key(jid, "complete")] = True
                on_open(jid, job)
                st.rerun()

            if is_admin and _action_button(
                marker="delete",
                label="Delete",
                key=f"job_row_delete_{job_key}",
                tone="danger",
            ):
                st.session_state[_confirm_state_key(jid, "delete")] = True
                on_open(jid, job)
                st.rerun()
