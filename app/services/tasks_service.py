"""
Tasks / to-do module.

Schema assumptions: ``todos`` (or ``tasks``) with title, description, status, priority,
due_date, assignee_name, job_label, estimate_label.
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
    priority_to_db,
    status_to_db,
)

__all__ = [
    "delete_task",
    "list_tasks",
    "normalize_task",
    "save_task",
    "update_task",
]


def update_task(task_id: str, update_data: dict[str, Any]) -> ServiceResult:
    """Partial update for inline task edits (status/priority)."""
    tid = str(task_id or "").strip()
    if not tid:
        return ServiceResult(ok=False, error="Missing task id.")
    payload: dict[str, Any] = {}
    if "status" in update_data:
        payload["status"] = status_to_db(display_to_status(update_data["status"]))
    if "priority" in update_data:
        payload["priority"] = priority_to_db(display_to_priority(update_data["priority"]))
    if not payload:
        return ServiceResult(ok=True)
    return update_row("todos", payload, {"id": tid})
