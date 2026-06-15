"""Manual job status controls — list Actions menu and Job Details badge editor."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.services.jobs_service import (
        MANUAL_JOB_STATUSES,
        can_manage_job_actions,
        normalize_job_status,
        update_job_status,
    )
except ImportError:
    from services.jobs_service import (  # type: ignore
        MANUAL_JOB_STATUSES,
        can_manage_job_actions,
        normalize_job_status,
        update_job_status,
    )


def job_status_pill_class(status: str) -> str:
    cls_map = {
        "Draft": "ips-job-status-draft",
        "Pending": "ips-job-status-pending",
        "Planning": "ips-job-status-planning",
        "Scheduled": "ips-job-status-scheduled",
        "Active": "ips-job-status-active",
        "Awarded": "ips-job-status-awarded",
        "On Hold": "ips-job-status-on-hold",
        "Completed": "ips-job-status-completed",
        "Closed": "ips-job-status-closed",
        "Cancelled": "ips-job-status-cancelled",
        "Deleted": "ips-job-status-deleted",
        "Archived": "ips-job-status-archived",
        "Estimate Pending": "ips-job-status-estimate-pending",
    }
    return cls_map.get(status, "ips-job-status-draft")


def job_status_pill_html(status: str) -> str:
    label = normalize_job_status(status)
    cls = job_status_pill_class(label)
    return f'<span class="ips-job-status-pill {cls}">{html.escape(label)}</span>'


ACTION_MENU_STATUS_OPTIONS: tuple[str, ...] = (
    "Draft",
    "Pending Review",
    "Approved",
    "Awarded",
    "Active",
    "In Progress",
    "On Hold",
    "Completed",
    "Cancelled",
)


def action_display_to_backend_status(display: object) -> str:
    """Map Actions menu labels to persisted job status values."""
    label = str(display or "").strip()
    mapping = {
        "Draft": "Draft",
        "Pending Review": "Pending",
        "Approved": "Awarded",
        "Awarded": "Awarded",
        "Active": "Active",
        "In Progress": "Active",
        "On Hold": "On Hold",
        "Completed": "Completed",
        "Cancelled": "Cancelled",
    }
    if label in mapping:
        return mapping[label]
    return normalize_job_status(display)


def backend_to_action_display_status(status: object) -> str:
    """Map stored job status to Actions menu label."""
    norm = normalize_job_status(status)
    mapping = {
        "Draft": "Draft",
        "Pending": "Pending Review",
        "Awarded": "Awarded",
        "Active": "Active",
        "On Hold": "On Hold",
        "Completed": "Completed",
        "Cancelled": "Cancelled",
        "Planning": "Approved",
        "Scheduled": "Active",
        "Closed": "Completed",
        "Estimate Pending": "Pending Review",
    }
    display = mapping.get(norm, norm)
    if display in ACTION_MENU_STATUS_OPTIONS:
        return display
    return "Draft"


def manual_job_status_options(current: object) -> list[str]:
    """Dropdown options for manual status changes."""
    cur = normalize_job_status(current)
    opts = list(MANUAL_JOB_STATUSES)
    if cur and cur not in opts and cur not in {"Deleted", "Archived"}:
        return [cur, *[o for o in opts if o != cur]]
    return opts


def _job_is_archived(job: dict[str, Any]) -> bool:
    if bool(job.get("is_deleted")):
        return True
    return normalize_job_status(job.get("status")) in {"Deleted", "Archived"}


def _job_session_key(job: dict[str, Any]) -> str:
    jid = str(job.get("id") or job.get("job_number") or "job").strip()
    return "".join(ch if ch.isalnum() else "_" for ch in jid) or "job"


def _sync_status_widget(
    job: dict[str, Any],
    widget_key: str,
    *,
    action_menu: bool = False,
) -> None:
    if action_menu:
        current = backend_to_action_display_status(job.get("status"))
    else:
        current = normalize_job_status(job.get("status"))
    if st.session_state.get(f"{widget_key}_bound") != current:
        st.session_state[widget_key] = current
        st.session_state[f"{widget_key}_bound"] = current
    st.session_state[f"{widget_key}_action_menu"] = action_menu


def _apply_status_change(job_id: str, widget_key: str) -> None:
    raw = st.session_state.get(widget_key)
    if st.session_state.get(f"{widget_key}_action_menu"):
        new_status = action_display_to_backend_status(raw)
        bound_value = backend_to_action_display_status(new_status)
    else:
        new_status = normalize_job_status(raw)
        bound_value = new_status
    result = update_job_status(job_id, new_status)
    if result.ok:
        st.session_state[f"{widget_key}_bound"] = bound_value
        st.session_state[widget_key] = bound_value
        on_updated = st.session_state.get(f"{widget_key}_on_updated")
        if callable(on_updated):
            on_updated(job_id, new_status)
        st.toast(f"Status updated to {new_status}.")
        st.rerun()
    else:
        st.error(result.error or "Could not update job status.")


def render_job_status_change_select(
    job: dict[str, Any],
    *,
    key_prefix: str,
    on_updated: Callable[[str, str], None] | None = None,
    action_menu: bool = False,
    label: str = "Change status",
) -> None:
    """Selectbox that saves immediately when the value changes."""
    jid = str(job.get("id") or "").strip()
    if not jid or not can_manage_job_actions() or _job_is_archived(job):
        return

    job_key = _job_session_key(job)
    widget_key = f"{key_prefix}_status_select_{job_key}"
    _sync_status_widget(job, widget_key, action_menu=action_menu)
    if on_updated is not None:
        st.session_state[f"{widget_key}_on_updated"] = on_updated
    if action_menu:
        options = list(ACTION_MENU_STATUS_OPTIONS)
        current = backend_to_action_display_status(job.get("status"))
    else:
        options = manual_job_status_options(job.get("status"))
        current = normalize_job_status(job.get("status"))
    index = options.index(current) if current in options else 0

    st.selectbox(
        label,
        options,
        index=index,
        key=widget_key,
        label_visibility="visible",
        on_change=_apply_status_change,
        args=(jid, widget_key),
    )


def render_job_status_badge_editor(
    job: dict[str, Any],
    *,
    key_prefix: str = "job_detail",
    on_updated: Callable[[str, str], None] | None = None,
) -> None:
    """Clickable status badge that opens a dropdown and saves immediately."""
    jid = str(job.get("id") or "").strip()
    current = normalize_job_status(job.get("status"))
    archived = _job_is_archived(job)
    can_manage = can_manage_job_actions()

    if not jid or archived or not can_manage:
        st.markdown(
            f'<div class="ips-job-detail-header-actions">{job_status_pill_html(current)}</div>',
            unsafe_allow_html=True,
        )
        return

    job_key = _job_session_key(job)
    widget_key = f"{key_prefix}_status_select_{job_key}"
    _sync_status_widget(job, widget_key)
    if on_updated is not None:
        st.session_state[f"{widget_key}_on_updated"] = on_updated
    options = manual_job_status_options(job.get("status"))
    index = options.index(current) if current in options else 0

    st.markdown(
        '<span class="ips-job-status-badge-editor-marker ips-job-detail-header-actions" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    with st.popover(
        current,
        help="Change job status",
        type="secondary",
        key=f"{key_prefix}_status_pop_{job_key}",
    ):
        st.markdown(
            '<span class="ips-job-status-change-panel" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        st.caption("Select a new status — saves immediately.")
        st.selectbox(
            "Status",
            options,
            index=index,
            key=widget_key,
            label_visibility="collapsed",
            on_change=_apply_status_change,
            args=(jid, widget_key),
        )
