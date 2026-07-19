"""Paginated Job Subjobs and focused subjob detail."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.task_display_helpers import normalize_task_priority, normalize_task_status
from app.services.task_reference_service import resolve_task_assignee_labels
from app.services.tasks_cache import tasks_data_version

SUBJOBS_DEFAULT_PAGE_SIZE = 25


@dataclass(frozen=True)
class JobSubjobsPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int


def _sort_subjobs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _key(row: dict[str, Any]) -> tuple:
        status = normalize_task_status(row.get("status"))
        open_first = 0 if status == "Open" else 1
        pri = {"High": 0, "Medium": 1, "Low": 2}.get(normalize_task_priority(row.get("priority")), 3)
        due = str(row.get("due_date") or "9999-99-99")
        return open_first, pri, due, str(row.get("title") or "").lower()

    return sorted(rows, key=_key)


def list_job_subjobs(
    job_id: str,
    *,
    view: str = "Open",
    demo_overrides: dict[str, dict] | None = None,
    page: int = 1,
    page_size: int = SUBJOBS_DEFAULT_PAGE_SIZE,
) -> JobSubjobsPage:
    from app.perf_debug import perf_span

    jid = str(job_id or "").strip()
    pg = max(1, int(page or 1))
    size = max(1, min(200, int(page_size or SUBJOBS_DEFAULT_PAGE_SIZE)))
    version = tasks_data_version()
    cache_key = f"job_subjobs:{jid}:v{version}:{view}:p{pg}:s{size}"

    def _build() -> JobSubjobsPage:
        with perf_span("tasks.subjobs.query"):
            from app.services.tasks_service import get_tasks_by_job

            rows = list(get_tasks_by_job(jid, include_closed=True))
            overrides = demo_overrides or {}
            merged: list[dict[str, Any]] = []
            for task in rows:
                row = dict(task)
                tid = str(row.get("id") or "").strip()
                if tid and tid in overrides:
                    row.update(overrides[tid])
                merged.append(row)
            if view == "Closed":
                merged = [t for t in merged if normalize_task_status(t.get("status")) == "Closed"]
            elif view == "Open":
                merged = [t for t in merged if normalize_task_status(t.get("status")) == "Open"]
            assignee_map = resolve_task_assignee_labels(
                [str(t.get("assigned_to") or "") for t in merged]
            )
            projected = []
            for task in merged:
                aid = str(task.get("assigned_to") or "").strip()
                lbl = assignee_map.get(aid, aid if aid and aid not in {"—", "— Unassigned —"} else "—")
                projected.append(
                    {
                        **task,
                        "status": normalize_task_status(task.get("status")),
                        "priority": normalize_task_priority(task.get("priority")),
                        "assigned_to_display": lbl,
                    }
                )
            projected = _sort_subjobs(projected)
            total = len(projected)
            start = (pg - 1) * size
            return JobSubjobsPage(
                rows=projected[start : start + size],
                total_count=total,
                page=pg,
                page_size=size,
            )

    return page_data_cache_get(cache_key, _build)


def get_job_subjob_detail(
    job_id: str,
    task_id: str,
    *,
    demo_overrides: dict[str, dict] | None = None,
) -> dict[str, Any] | None:
    from app.perf_debug import perf_span

    jid = str(job_id or "").strip()
    tid = str(task_id or "").strip()
    if not jid or not tid:
        return None
    version = tasks_data_version()
    cache_key = f"job_subjob_detail:{jid}:{tid}:v{version}"

    def _build() -> dict[str, Any] | None:
        with perf_span("tasks.subjob.detail_lookup"):
            from app.services.tasks_service import get_tasks_by_job

            overrides = demo_overrides or {}
            for task in get_tasks_by_job(jid, include_closed=True):
                if str(task.get("id") or "") != tid:
                    continue
                row = dict(task)
                if tid in overrides:
                    row.update(overrides[tid])
                return row
            return None

    return page_data_cache_get(cache_key, _build)


__all__ = [
    "JobSubjobsPage",
    "SUBJOBS_DEFAULT_PAGE_SIZE",
    "get_job_subjob_detail",
    "list_job_subjobs",
]
