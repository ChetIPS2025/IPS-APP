"""Task activity read service (no session-only fake persistence)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TaskActivityPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int


def list_task_activity(
    task_id: str,
    *,
    page: int = 1,
    page_size: int = 25,
) -> TaskActivityPage:
    tid = str(task_id or "").strip()
    from app.services.task_detail_service import get_task_detail

    task = get_task_detail(tid) or {}
    activity = list(task.get("activity") or [])
    pg = max(1, int(page or 1))
    size = max(1, int(page_size or 25))
    start = (pg - 1) * size
    rows = activity[start : start + size]
    return TaskActivityPage(rows=rows, total_count=len(activity), page=pg, page_size=size)


def add_task_activity_note(task_id: str, note: str) -> Any:
    from app.services.repository import ServiceResult

    return ServiceResult(ok=False, error="Task activity notes are not persisted yet.")


__all__ = ["TaskActivityPage", "add_task_activity_note", "list_task_activity"]
