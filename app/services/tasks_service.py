"""
Tasks / to-do module.

Schema assumptions: ``todos`` (or ``tasks``) with title, description, status, priority,
due_date, assignee_name, job_id, job_label, estimate_label.
"""

from __future__ import annotations

from typing import Any

from app.services.phase2_modules_service import (
    delete_task,
    list_tasks,
    normalize_task,
    save_task,
)
from app.services.repository import ServiceResult, clear_all_data_caches, update_row
from app.services.task_display_helpers import (
    display_to_priority,
    display_to_status,
    normalize_task_status,
    priority_to_db,
    status_to_db,
)

__all__ = [
    "clear_tasks_cache",
    "count_open_subjobs_by_job_id",
    "delete_job_subjob",
    "delete_task",
    "get_closed_tasks",
    "get_open_tasks",
    "get_tasks",
    "get_tasks_by_job",
    "list_tasks",
    "normalize_task",
    "save_task",
    "update_task",
]

_CLOSED_SUBJOB_STATUSES = frozenset(
    {"complete", "completed", "closed", "cancelled", "canceled", "duplicate"}
)


def get_tasks() -> list[dict[str, Any]]:
    """Load tasks for the Tasks page (demo fallback included)."""
    try:
        from app.pages._core._data import _DEMO_TASKS
    except ImportError:
        from pages._core._data import _DEMO_TASKS  # type: ignore
    rows, _ = list_tasks(demo=list(_DEMO_TASKS))
    return rows


def _resolve_task_job_id(task: dict[str, Any]) -> str | None:
    """Resolve a task's linked job id from job_id or friendly label."""
    jid = str(task.get("job_id") or "").strip()
    if jid:
        return jid
    label = str(task.get("linked_job") or task.get("job_label") or "").strip()
    if not label or label in {"— None —", "None", "—", "-"}:
        return None
    try:
        from app.services.jobs_service import resolve_job_id_from_label
    except ImportError:
        from services.jobs_service import resolve_job_id_from_label  # type: ignore
    return resolve_job_id_from_label(label)


def _filter_tasks_by_view(tasks: list[dict[str, Any]], view: str) -> list[dict[str, Any]]:
    if view == "Closed Tasks":
        return [t for t in tasks if normalize_task_status(t.get("status")) == "Closed"]
    if view == "Open Tasks":
        return [t for t in tasks if normalize_task_status(t.get("status")) == "Open"]
    return list(tasks)


def get_open_tasks() -> list[dict[str, Any]]:
    """Return tasks whose normalized status is Open."""
    return _filter_tasks_by_view(get_tasks(), "Open Tasks")


def get_closed_tasks() -> list[dict[str, Any]]:
    """Return tasks whose normalized status is Closed."""
    return _filter_tasks_by_view(get_tasks(), "Closed Tasks")


def get_tasks_by_job(job_id: str, *, include_closed: bool = False) -> list[dict[str, Any]]:
    """Return tasks linked to a job. Open only by default; both when include_closed=True."""
    jid = str(job_id or "").strip()
    if not jid:
        return []
    out: list[dict[str, Any]] = []
    for task in get_tasks():
        if _resolve_task_job_id(task) != jid:
            continue
        if include_closed or normalize_task_status(task.get("status")) == "Open":
            out.append(task)
    return out


def count_open_subjobs_by_job_id() -> dict[str, int]:
    """Single pass over all tasks — open subjob count keyed by job id."""
    counts: dict[str, int] = {}
    for task in get_tasks():
        jid = _resolve_task_job_id(task)
        if not jid:
            continue
        if str(task.get("status") or "").strip().lower() in _CLOSED_SUBJOB_STATUSES:
            continue
        counts[jid] = counts.get(jid, 0) + 1
    return counts


def clear_tasks_cache() -> None:
    """Invalidate cached task reads after inline edits."""
    clear_all_data_caches()


def delete_job_subjob(task_id: str, *, job_id: str | None = None) -> ServiceResult:
    """Hard-delete an IPS subjob (todo) after unlinking optional child associations."""
    tid = str(task_id or "").strip()
    if not tid:
        return ServiceResult(ok=False, error="Missing subjob id.")
    jid = str(job_id or "").strip() or None

    try:
        from app.services.coupling_inspection_service import (
            list_coupling_inspections,
            unlink_coupling_inspection_from_task,
        )
    except ImportError:
        from services.coupling_inspection_service import (  # type: ignore
            list_coupling_inspections,
            unlink_coupling_inspection_from_task,
        )

    for insp in list_coupling_inspections(job_id=jid, task_id=tid):
        iid = str(insp.get("id") or "").strip()
        if iid:
            unlink_coupling_inspection_from_task(iid)

    if jid:
        try:
            from app.services.job_photos import fetch_job_photos, unlink_job_photo_from_task
            from app.services.job_documents import fetch_job_documents, unlink_job_document_from_task
        except ImportError:
            from services.job_photos import fetch_job_photos, unlink_job_photo_from_task  # type: ignore
            from services.job_documents import fetch_job_documents, unlink_job_document_from_task  # type: ignore

        for photo in fetch_job_photos(jid, task_id=tid, admin=True):
            pid = str(photo.get("id") or "").strip()
            if pid:
                try:
                    unlink_job_photo_from_task(pid, admin=True)
                except Exception:
                    pass
        for doc in fetch_job_documents(jid, task_id=tid, admin=True):
            did = str(doc.get("id") or "").strip()
            if did:
                try:
                    unlink_job_document_from_task(did, admin=True)
                except Exception:
                    pass

    result = delete_task(tid)
    if result.ok:
        clear_tasks_cache()
    return result


def update_task(task_id: str, update_data: dict[str, Any]) -> ServiceResult:
    """Partial update for inline task edits (status, priority, job link)."""
    tid = str(task_id or "").strip()
    if not tid:
        return ServiceResult(ok=False, error="Missing task id.")
    payload: dict[str, Any] = {}
    if "status" in update_data:
        payload["status"] = status_to_db(display_to_status(update_data["status"]))
    if "priority" in update_data:
        payload["priority"] = priority_to_db(display_to_priority(update_data["priority"]))
    if "job_id" in update_data:
        jid = update_data.get("job_id")
        payload["job_id"] = str(jid).strip() if jid else None
    if "job_label" in update_data:
        payload["job_label"] = str(update_data.get("job_label") or "")
    if not payload:
        return ServiceResult(ok=True)
    result = update_row("todos", payload, {"id": tid})
    if result.ok:
        clear_tasks_cache()
    return result
