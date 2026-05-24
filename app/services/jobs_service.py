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
    "cancel_job",
    "can_manage_job_actions",
    "complete_job",
    "delete_job",
    "get_job_options",
    "list_jobs",
    "normalize_job",
    "resolve_job_id_from_label",
    "save_job",
    "soft_delete_job",
]

_OPEN_JOB_STATUSES = frozenset(
    {"active", "awarded", "in progress", "open", "scheduled", "pending", "draft"}
)

_JOB_ACTION_ROLES = frozenset({"admin", "supervisor", "project manager", "manager", "pm"})


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
