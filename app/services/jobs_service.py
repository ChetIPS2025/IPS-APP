"""
Jobs module — Supabase reads/writes.

Schema assumptions: table ``jobs`` with columns job_number, job_name, customer_id,
status, start_date, target_completion_date, notes, supervisor (optional).
Lifecycle columns added in sql/084_jobs_lifecycle_fields.sql.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.services.phase2_modules_service import (
    delete_job,
    list_jobs,
    normalize_job,
    save_job,
)
from app.services.repository import ServiceResult, clear_all_data_caches, update_row

__all__ = [
    "MANUAL_JOB_STATUSES",
    "cancel_job",
    "can_manage_job_actions",
    "complete_job",
    "delete_job",
    "get_job_options",
    "list_jobs",
    "normalize_job",
    "normalize_job_status",
    "resolve_job_id_from_label",
    "save_job",
    "soft_delete_job",
    "update_job_status",
]

_OPEN_JOB_STATUSES = frozenset(
    {
        "active",
        "on hold",
        "awarded",
        "in progress",
        "open",
        "scheduled",
        "pending",
        "draft",
        "planning",
        "estimate pending",
    }
)

MANUAL_JOB_STATUSES = (
    "Active",
    "On Hold",
    "Completed",
    "Cancelled",
)

_LEGACY_JOB_STATUSES_TO_ACTIVE = frozenset(
    {
        "",
        "draft",
        "pending",
        "awarded",
        "planning",
        "scheduled",
        "in progress",
        "open",
        "estimate pending",
    }
)

_JOB_ACTION_ROLES = frozenset({"admin", "supervisor", "project manager", "manager", "pm"})


def normalize_job_status(raw: object) -> str:
    """Canonical job status labels used across Jobs UI, dashboard, and filters."""
    s = str(raw or "").strip().lower().replace("_", " ")
    mapping = {
        "active": "Active",
        "on hold": "On Hold",
        "completed": "Completed",
        "complete": "Completed",
        "closed": "Completed",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
        "archived": "Archived",
        "deleted": "Deleted",
    }
    if s in mapping:
        return mapping[s]
    if s in _LEGACY_JOB_STATUSES_TO_ACTIVE:
        return "Active"
    label = str(raw or "").strip()
    if label in MANUAL_JOB_STATUSES:
        return label
    if label in {"Archived", "Deleted"}:
        return label
    return "Active"


def _current_user_id() -> str | None:
    try:
        from app.auth import current_profile
    except ImportError:
        from auth import current_profile  # type: ignore
    pid = str(current_profile().get("id") or "").strip()
    return pid or None


def can_manage_job_actions() -> bool:
    """Admin, supervisor, project manager, or PM may complete/cancel/soft-delete jobs."""
    try:
        from app.auth import current_role
    except ImportError:
        from auth import current_role  # type: ignore
    role = str(current_role() or "").strip().lower()
    return role in _JOB_ACTION_ROLES


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def complete_job(job_id: str, *, completed_by: str | None = None) -> ServiceResult:
    """Mark a job Completed with audit timestamps."""
    jid = str(job_id or "").strip()
    if not jid:
        return ServiceResult(ok=False, error="Missing job id.")
    actor = str(completed_by or _current_user_id() or "").strip() or None
    now = _utc_now_iso()
    payload: dict[str, Any] = {
        "status": "Completed",
        "completed_at": now,
        "completed_date": date.today().isoformat(),
        "percent_complete": 100,
    }
    if actor:
        payload["completed_by"] = actor
    result = update_row("jobs", payload, {"id": jid})
    if result.ok:
        clear_all_data_caches()
    return result


def cancel_job(
    job_id: str,
    *,
    reason: str | None = None,
    cancelled_by: str | None = None,
) -> ServiceResult:
    """Mark a job Cancelled with optional reason."""
    jid = str(job_id or "").strip()
    if not jid:
        return ServiceResult(ok=False, error="Missing job id.")
    actor = str(cancelled_by or _current_user_id() or "").strip() or None
    payload: dict[str, Any] = {
        "status": "Cancelled",
        "cancelled_at": _utc_now_iso(),
    }
    if actor:
        payload["cancelled_by"] = actor
    reason_text = str(reason or "").strip()
    if reason_text:
        payload["cancellation_reason"] = reason_text
    result = update_row("jobs", payload, {"id": jid})
    if result.ok:
        clear_all_data_caches()
    return result


def soft_delete_job(
    job_id: str,
    *,
    reason: str | None = None,
    deleted_by: str | None = None,
) -> ServiceResult:
    """Archive a job (soft delete). Historical records are preserved."""
    jid = str(job_id or "").strip()
    if not jid:
        return ServiceResult(ok=False, error="Missing job id.")
    actor = str(deleted_by or _current_user_id() or "").strip() or None
    payload: dict[str, Any] = {
        "is_deleted": True,
        "status": "Archived",
        "deleted_at": _utc_now_iso(),
    }
    if actor:
        payload["deleted_by"] = actor
    reason_text = str(reason or "").strip()
    if reason_text:
        payload["delete_reason"] = reason_text
    result = update_row("jobs", payload, {"id": jid})
    if result.ok:
        clear_all_data_caches()
    return result


def update_job_status(
    job_id: str,
    new_status: str,
    *,
    changed_by: str | None = None,
    reason: str | None = None,
) -> ServiceResult:
    """Set job status manually (estimate-linked jobs may still be updated after creation)."""
    if not can_manage_job_actions():
        return ServiceResult(ok=False, error="You do not have permission to change job status.")
    jid = str(job_id or "").strip()
    if not jid:
        return ServiceResult(ok=False, error="Missing job id.")

    status = normalize_job_status(new_status)
    if status not in MANUAL_JOB_STATUSES:
        return ServiceResult(ok=False, error=f"Status '{status}' is not allowed.")

    try:
        from app.db import fetch_one
    except ImportError:
        from db import fetch_one  # type: ignore

    current_row = fetch_one("jobs", {"id": jid}) or {}
    if not current_row:
        return ServiceResult(ok=False, error="Job not found.")
    if bool(current_row.get("is_deleted")):
        return ServiceResult(ok=False, error="Archived jobs cannot be updated.")

    old_status = normalize_job_status(current_row.get("status"))
    if old_status in {"Deleted", "Archived"}:
        return ServiceResult(ok=False, error="Archived jobs cannot be updated.")
    if old_status == status and status != "Active":
        return ServiceResult(ok=True, data={"status": status})

    actor = str(changed_by or _current_user_id() or "").strip() or None
    now = _utc_now_iso()
    payload: dict[str, Any] = {"status": status, "updated_at": now}

    if status == "Completed":
        payload["completed_at"] = now
        payload["completed_date"] = date.today().isoformat()
        payload["percent_complete"] = 100
        if actor:
            payload["completed_by"] = actor
    elif status == "Cancelled":
        payload["cancelled_at"] = now
        if actor:
            payload["cancelled_by"] = actor
        reason_text = str(reason or "").strip()
        if reason_text:
            payload["cancellation_reason"] = reason_text

    if status == "Active":
        try:
            from app.services.estimate_job_workflow_service import award_job_and_sync_estimate
        except ImportError:
            from services.estimate_job_workflow_service import award_job_and_sync_estimate  # type: ignore

        sync = award_job_and_sync_estimate(
            jid,
            new_status=status,
            approved_by=actor,
            job_row=current_row,
        )
        if not sync.ok:
            return sync
        sync_data = sync.data if isinstance(sync.data, dict) else {}
        job_patch = sync_data.get("job_patch") or {}
        if isinstance(job_patch, dict):
            payload.update(job_patch)

    result = update_row("jobs", payload, {"id": jid})
    if not result.ok:
        return result

    clear_all_data_caches()
    try:
        from app.auth import current_profile
        from app.services.job_timeline import EVENT_STATUS, log_job_event
    except ImportError:
        from auth import current_profile  # type: ignore
        from services.job_timeline import EVENT_STATUS, log_job_event  # type: ignore

    profile = current_profile()
    desc = f"{old_status} → {status}"
    reason_text = str(reason or "").strip()
    if reason_text:
        desc = f"{desc}\n{reason_text}"
    log_job_event(
        job_id=jid,
        event_type=EVENT_STATUS,
        title=f"Status changed to {status}",
        description=desc,
        user_name=str(profile.get("name") or profile.get("email") or "").strip(),
        user_id=str(profile.get("id") or "").strip() or None,
        metadata={"from": old_status, "to": status},
        admin=True,
    )
    return ServiceResult(ok=True, data={"status": status, "from": old_status})


def get_job_options(*, include_all: bool = False) -> list[dict[str, Any]]:
    """Return job dropdown options as ``{id, label}`` rows for task linking."""
    try:
        from app.pages._core._data import load_jobs
    except ImportError:
        from pages._core._data import load_jobs  # type: ignore

    opts: list[dict[str, Any]] = [{"id": None, "label": "— None —"}]
    for job in load_jobs():
        jid = str(job.get("id") or "").strip()
        if not jid:
            continue
        if job.get("is_deleted"):
            continue
        status = str(job.get("status") or "").strip().lower()
        if not include_all and status and status not in _OPEN_JOB_STATUSES:
            continue
        num = str(job.get("job_number") or "").strip()
        name = str(job.get("job_name") or "").strip()
        if num and name:
            label = f"{num} — {name}"
        elif num:
            label = num
        elif name:
            label = name
        else:
            label = jid
        opts.append({"id": jid, "label": label})
    return opts


def resolve_job_id_from_label(label: str) -> str | None:
    """Map a friendly job label (e.g. ``J26047 — Project Name``) to job id."""
    raw = str(label or "").strip()
    if not raw or raw in {"— None —", "None", "—", "-"}:
        return None
    for opt in get_job_options(include_all=True):
        if str(opt.get("label") or "") == raw:
            jid = opt.get("id")
            return str(jid).strip() if jid else None
    try:
        from app.pages._core._data import load_jobs
    except ImportError:
        from pages._core._data import load_jobs  # type: ignore
    for job in load_jobs():
        num = str(job.get("job_number") or "").strip()
        name = str(job.get("job_name") or "").strip()
        friendly = f"{num} — {name}" if num and name else num or name
        if friendly == raw:
            jid = str(job.get("id") or "").strip()
            return jid or None
    return None

