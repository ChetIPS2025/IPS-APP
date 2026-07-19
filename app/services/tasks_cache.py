"""Tasks data versioning and centralized cache invalidation."""

from __future__ import annotations

_FALLBACK_VERSIONS: dict[str, int] = {}


def _version_store() -> dict[str, int]:
    try:
        import streamlit as st

        return st.session_state.setdefault("_ips_tasks_versions", {})
    except Exception:
        return _FALLBACK_VERSIONS


def tasks_data_version() -> int:
    return int(_version_store().get("_global") or 0)


def invalidate_tasks_cache(
    task_id: str | None = None,
    *,
    job_id: str | None = None,
) -> int:
    """Bump tasks data version and clear derived caches after writes."""
    store = _version_store()
    new_version = int(store.get("_global") or 0) + 1
    store["_global"] = new_version
    if task_id:
        tid = str(task_id).strip()
        if tid:
            store[tid] = int(store.get(tid) or 0) + 1

    try:
        import streamlit as st

        st.session_state.pop("_ips_tasks_by_job_index", None)
    except Exception:
        pass

    try:
        from app.pages._core.page_data_cache import (
            clear_dashboard_page_data_cache,
            clear_page_data_cache_prefix,
        )

        clear_page_data_cache_prefix("tasks:")
        clear_page_data_cache_prefix("task_detail:")
        clear_page_data_cache_prefix("task_ref:")
        clear_page_data_cache_prefix("job_subjobs:")
        clear_dashboard_page_data_cache()
    except Exception:
        pass

    try:
        from app.services.repository import clear_data_cache_for_table

        clear_data_cache_for_table("todos")
        clear_data_cache_for_table("tasks")
    except Exception:
        pass

    if job_id:
        try:
            from app.services.jobs_service import clear_jobs_cache

            clear_jobs_cache()
        except Exception:
            pass

    return new_version


def finalize_task_write(
    task_id: str | None = None,
    *,
    job_id: str | None = None,
) -> None:
    """Invalidate task-related caches after a successful write."""
    invalidate_tasks_cache(task_id, job_id=job_id)
    try:
        from app.services.tasks_service import clear_tasks_cache

        clear_tasks_cache()
    except Exception:
        pass


def detail_cache_version(task_id: str) -> int:
    tid = str(task_id or "").strip()
    if not tid:
        return tasks_data_version()
    store = _version_store()
    return int(store.get(tid) or tasks_data_version())


__all__ = [
    "detail_cache_version",
    "finalize_task_write",
    "invalidate_tasks_cache",
    "tasks_data_version",
]
