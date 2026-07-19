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
from app.services.repository import ServiceResult, update_row
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
    "get_tasks_for_jobs",
    "list_tasks",
    "normalize_task",
    "save_task",
    "update_task",
]

_CLOSED_SUBJOB_STATUSES = frozenset(
    {"complete", "completed", "closed", "cancelled", "canceled", "duplicate"}
)
_TASKS_FOR_JOBS_CHUNK_SIZE = 100
_TASKS_FOR_JOBS_TABLES = ("todos", "tasks")


def get_tasks() -> list[dict[str, Any]]:
    """Load tasks for the Tasks page (demo fallback included)."""
    from app.pages._core._data import load_tasks
    return load_tasks()


def _tasks_by_job_index() -> dict[str, list[dict[str, Any]]]:
    import streamlit as st

    key = "_ips_tasks_by_job_index"
    cached = st.session_state.get(key)
    if isinstance(cached, dict):
        return cached
    idx: dict[str, list[dict[str, Any]]] = {}
    for task in get_tasks():
        jid = _resolve_task_job_id(task)
        if jid:
            idx.setdefault(jid, []).append(task)
    st.session_state[key] = idx
    return idx


def _resolve_task_job_id(task: dict[str, Any]) -> str | None:
    """Resolve a task's linked job id from job_id or friendly label."""
    jid = str(task.get("job_id") or "").strip()
    if jid:
        return jid
    label = str(task.get("linked_job") or task.get("job_label") or "").strip()
    if not label or label in {"— None —", "None", "—", "-"}:
        return None
    from app.services.jobs_service import resolve_job_id_from_label
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
    tasks = list(_tasks_by_job_index().get(jid, []))
    if include_closed:
        return tasks
    return [t for t in tasks if normalize_task_status(t.get("status")) == "Open"]


def _ordered_unique_job_ids(job_ids: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in job_ids:
        jid = str(raw or "").strip()
        if not jid or jid in seen:
            continue
        seen.add(jid)
        ordered.append(jid)
    return ordered


def _fetch_tasks_rows_for_job_id_chunk(job_ids: list[str]) -> list[dict[str, Any]]:
    if not job_ids:
        return []
    from app.db import get_client, run_user_supabase_operation

    chunk = list(job_ids)
    limit = max(500, len(chunk) * 50)

    def _query_table(table: str) -> list[dict[str, Any]]:
        def _run() -> list[dict[str, Any]]:
            resp = (
                get_client()
                .table(table)
                .select("*")
                .in_("job_id", chunk)
                .order("due_date")
                .limit(limit)
                .execute()
            )
            return list(resp.data or [])

        return run_user_supabase_operation(
            f"read {table} by job_id",
            _run,
            friendly_on_failure=False,
        )

    for table in _TASKS_FOR_JOBS_TABLES:
        try:
            rows = _query_table(table)
        except Exception:
            rows = []
        if rows:
            return rows
    return []


def _tasks_for_jobs_from_index(
    job_ids: list[str],
    *,
    include_closed: bool,
) -> dict[str, list[dict[str, Any]]]:
    """Fallback when batched DB reads are unavailable (demo/offline)."""
    wanted = set(job_ids)
    grouped: dict[str, list[dict[str, Any]]] = {jid: [] for jid in job_ids}
    for task in get_tasks():
        jid = _resolve_task_job_id(task)
        if not jid or jid not in wanted:
            continue
        if not include_closed and normalize_task_status(task.get("status")) != "Open":
            continue
        grouped.setdefault(jid, []).append(task)
    return grouped


def get_tasks_for_jobs(
    job_ids: list[str],
    *,
    include_closed: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    """Batch-load tasks for many jobs in one or few DB queries, grouped by job_id."""
    ordered_ids = _ordered_unique_job_ids(job_ids)
    if not ordered_ids:
        return {}

    grouped: dict[str, list[dict[str, Any]]] = {jid: [] for jid in ordered_ids}
    rows: list[dict[str, Any]] = []
    for start in range(0, len(ordered_ids), _TASKS_FOR_JOBS_CHUNK_SIZE):
        chunk = ordered_ids[start : start + _TASKS_FOR_JOBS_CHUNK_SIZE]
        rows.extend(_fetch_tasks_rows_for_job_id_chunk(chunk))

    if not rows:
        return _tasks_for_jobs_from_index(ordered_ids, include_closed=include_closed)

    for raw in rows:
        if not raw:
            continue
        task = normalize_task(raw)
        jid = str(task.get("job_id") or raw.get("job_id") or "").strip()
        if not jid or jid not in grouped:
            continue
        if not include_closed and normalize_task_status(task.get("status")) != "Open":
            continue
        task_no = str(raw.get("task_number") or raw.get("hazard_number") or "").strip()
        if task_no:
            task["task_number"] = task_no
        grouped[jid].append(task)
    return grouped


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
    import streamlit as st

    st.session_state.pop("_ips_tasks_by_job_index", None)
    from app.services.repository import clear_data_cache_for_table
    clear_data_cache_for_table("todos")


def delete_job_subjob(task_id: str, *, job_id: str | None = None) -> ServiceResult:
    """Hard-delete an IPS subjob (todo) after unlinking optional child associations."""
    tid = str(task_id or "").strip()
    if not tid:
        return ServiceResult(ok=False, error="Missing subjob id.")
    jid = str(job_id or "").strip() or None

    from app.services.coupling_inspection_service import (
        list_coupling_inspections,
        unlink_coupling_inspection_from_task,
    )
    for insp in list_coupling_inspections(job_id=jid, task_id=tid):
        iid = str(insp.get("id") or "").strip()
        if iid:
            unlink_coupling_inspection_from_task(iid)

    if jid:
        from app.services.job_photos import fetch_job_photos, unlink_job_photo_from_task
        from app.services.job_documents import fetch_job_documents, unlink_job_document_from_task
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
