"""Focused Task detail lookup."""

from __future__ import annotations

from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.task_display_helpers import normalize_task_priority, normalize_task_status
from app.services.task_reference_service import resolve_task_assignee_labels, resolve_task_job_labels
from app.services.tasks_cache import detail_cache_version


def get_task_detail(
    task_id: str,
    *,
    user_id: str = "",
    role: str = "",
    demo_overrides: dict[str, dict] | None = None,
) -> dict[str, Any] | None:
    from app.perf_debug import perf_span

    tid = str(task_id or "").strip()
    if not tid:
        return None
    version = detail_cache_version(tid)
    cache_key = f"task_detail:{tid}:v{version}:u{user_id}:r{role}"

    def _build() -> dict[str, Any] | None:
        with perf_span("tasks.detail_lookup"):
            from app.services.tasks_service import get_tasks

            overrides = demo_overrides or {}
            for task in get_tasks():
                row = dict(task)
                if str(row.get("id") or "") != tid:
                    continue
                if tid in overrides:
                    row.update(overrides[tid])
                aid = str(row.get("assigned_to") or "").strip()
                jid = str(row.get("job_id") or "").strip()
                assignee_map = resolve_task_assignee_labels([aid] if aid else [])
                job_map = resolve_task_job_labels([jid] if jid else [])
                assignee_label = assignee_map.get(aid, aid if aid and aid not in {"—", "— Unassigned —"} else "—")
                job_label = job_map.get(jid, str(row.get("linked_job") or "—"))
                return {
                    **row,
                    "status": normalize_task_status(row.get("status")),
                    "priority": normalize_task_priority(row.get("priority")),
                    "assignee_label": assignee_label,
                    "job_label": job_label,
                    "can_view": True,
                }
            if tid in overrides:
                patch = overrides[tid]
                return {**patch, "id": tid, "can_view": True}
            return None

    return page_data_cache_get(cache_key, _build)


__all__ = ["get_task_detail"]
