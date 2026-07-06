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


def job_status_table_label(raw: object) -> str:
    """Display label for Jobs table status pills (preserves Pending/Scheduled when stored)."""
    s = str(raw or "").strip().lower().replace("_", " ")
    display = {
        "pending": "Pending",
        "scheduled": "Scheduled",
        "on hold": "On Hold",
        "active": "Active",
        "awarded": "Active",
        "draft": "Pending",
        "planning": "Pending",
        "estimate pending": "Pending",
        "in progress": "Active",
        "open": "Active",
        "completed": "Complete",
        "complete": "Complete",
        "closed": "Closed",
        "cancelled": "Closed",
        "canceled": "Closed",
        "archived": "Closed",
        "deleted": "Closed",
    }
    if s in display:
        return display[s]
    normalized = normalize_job_status(raw)
    if normalized == "Completed":
        return "Complete"
    if normalized == "Cancelled":
        return "Closed"
    if normalized in {"Archived", "Deleted"}:
        return "Closed"
    return normalized


def job_status_pill_class(status: str) -> str:
    cls_map = {
        "Active": "ips-job-status-active",
        "Pending": "ips-job-status-pending",
        "Scheduled": "ips-job-status-scheduled",
        "On Hold": "ips-job-status-on-hold",
        "Complete": "ips-job-status-completed",
        "Completed": "ips-job-status-completed",
        "Closed": "ips-job-status-closed",
        "Cancelled": "ips-job-status-closed",
        "Deleted": "ips-job-status-closed",
        "Archived": "ips-job-status-closed",
    }
    return cls_map.get(status, "ips-job-status-active")


def job_status_pill_html(status: str) -> str:
    label = job_status_table_label(status)
    cls = job_status_pill_class(label)
    return f'<span class="ips-job-status-pill {cls}">{html.escape(label)}</span>'


ACTION_MENU_STATUS_OPTIONS: tuple[str, ...] = MANUAL_JOB_STATUSES


def action_display_to_backend_status(display: object) -> str:
    """Map Actions menu labels to persisted job status values."""
    return normalize_job_status(display)


def backend_to_action_display_status(status: object) -> str:
    """Map stored job status to Actions menu label."""
    return normalize_job_status(status)


def manual_job_status_options(current: object) -> list[str]:
    """Dropdown options for manual status changes."""
    cur = normalize_job_status(current)
    if cur in {"Deleted", "Archived"}:
        return [cur, *MANUAL_JOB_STATUSES]
    return list(MANUAL_JOB_STATUSES)


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
    current = normalize_job_status(job.get("status"))
    if st.session_state.get(f"{widget_key}_bound") != current:
        st.session_state[widget_key] = current
        st.session_state[f"{widget_key}_bound"] = current
    st.session_state[f"{widget_key}_action_menu"] = action_menu


def _apply_status_change(job_id: str, widget_key: str) -> None:
    raw = st.session_state.get(widget_key)
    new_status = normalize_job_status(raw)
    result = update_job_status(job_id, new_status)
    if result.ok:
        st.session_state[f"{widget_key}_bound"] = new_status
        st.session_state[widget_key] = new_status
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
    options = manual_job_status_options(job.get("status"))
    current = normalize_job_status(job.get("status"))
    index = options.index(current) if current in options else 0

    if action_menu:
        st.markdown(
            '<span class="job-row-actions-status-select" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
    st.selectbox(
        label,
        options,
        index=index,
        key=widget_key,
        label_visibility="visible",
        on_change=_apply_status_change,
        args=(jid, widget_key),
    )


def render_job_status_table_pill(
    job: dict[str, Any],
    *,
    key_prefix: str = "job_table",
    on_updated: Callable[[str, str], None] | None = None,
) -> None:
    """Read-only status pill in the Jobs table; managers click to change via popover."""
    jid = str(job.get("id") or "").strip()
    label = job_status_table_label(job.get("status"))
    archived = _job_is_archived(job)
    can_manage = can_manage_job_actions()

    if not jid or archived or not can_manage:
        st.markdown(
            f'<div class="ips-job-status-table-pill">{job_status_pill_html(job.get("status"))}</div>',
            unsafe_allow_html=True,
        )
        return

    job_key = _job_session_key(job)
    widget_key = f"{key_prefix}_status_select_{job_key}"
    _sync_status_widget(job, widget_key)
    if on_updated is not None:
        st.session_state[f"{widget_key}_on_updated"] = on_updated
    options = manual_job_status_options(job.get("status"))
    current = normalize_job_status(job.get("status"))
    index = options.index(current) if current in options else 0

    st.markdown(
        '<span class="ips-job-status-table-editor-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    with st.popover(
        label,
        help="Change job status",
        type="secondary",
        key=f"{key_prefix}_status_pop_{job_key}",
    ):
        st.markdown(
            '<span class="ips-job-status-change-panel ips-job-status-table-change-panel" aria-hidden="true"></span>',
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


def render_job_status_badge_editor(
    job: dict[str, Any],
    *,
    key_prefix: str = "job_detail",
    on_updated: Callable[[str, str], None] | None = None,
) -> None:
    """Clickable status badge that opens a dropdown and saves immediately."""
    jid = str(job.get("id") or "").strip()
    current = normalize_job_status(job.get("status"))
    display = job_status_table_label(job.get("status"))
    pill_cls = job_status_pill_class(display)
    archived = _job_is_archived(job)
    can_manage = can_manage_job_actions()

    if not jid or archived or not can_manage:
        st.markdown(
            f'<div class="ips-job-detail-header-actions">{job_status_pill_html(job.get("status"))}</div>',
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
        f'<span class="ips-job-status-badge-editor-marker ips-job-detail-header-actions '
        f'{pill_cls}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    with st.popover(
        display,
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
