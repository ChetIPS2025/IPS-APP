"""Office-scoped management reminders (``todos`` rows without a linked job)."""

from __future__ import annotations

from datetime import date
from typing import Any

try:
    from app.services.task_display_helpers import normalize_task_status
    from app.services.tasks_service import _resolve_task_job_id
except ImportError:
    from services.task_display_helpers import normalize_task_status  # type: ignore
    from services.tasks_service import _resolve_task_job_id  # type: ignore

_MANAGEMENT_ROLES = frozenset({"admin", "project manager", "supervisor"})

__all__ = [
    "can_create_management_reminder",
    "complete_management_reminder",
    "create_management_reminder",
    "due_date_badge",
    "filter_dashboard_reminders",
    "is_office_reminder",
]


def is_office_reminder(row: dict[str, Any]) -> bool:
    """True when the todo is not linked to a job (management reminder, not a subjob)."""
    return _resolve_task_job_id(row) is None


def is_open_reminder(row: dict[str, Any]) -> bool:
    return normalize_task_status(row.get("status")) == "Open"


def _assignee_label(row: dict[str, Any]) -> str:
    return str(row.get("assigned_to") or row.get("assignee_name") or "").strip()


def _profile_display_names(profile: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    full = str(profile.get("full_name") or "").strip()
    if full:
        names.add(full.casefold())
    email = str(profile.get("email") or "").strip()
    if email:
        names.add(email.casefold())
        local = email.split("@", 1)[0].strip()
        if local:
            names.add(local.casefold())
    return names


def _matches_profile(row: dict[str, Any], profile: dict[str, Any]) -> bool:
    assignee = _assignee_label(row)
    if not assignee or assignee in {"—", "— Select —", "-", "— None —"}:
        return False
    key = assignee.casefold()
    names = _profile_display_names(profile)
    if key in names:
        return True
    for name in names:
        if name and (name in key or key in name):
            return True
    return False


def visible_to_user(row: dict[str, Any], *, profile: dict[str, Any], role: str) -> bool:
    if not is_office_reminder(row) or not is_open_reminder(row):
        return False
    role_key = str(role or "viewer").strip().lower()
    if role_key in _MANAGEMENT_ROLES:
        return True
    return _matches_profile(row, profile)


def _due_sort_key(row: dict[str, Any]) -> tuple[int, str, str]:
    raw = str(row.get("due_date") or "")[:10]
    overdue_rank = 1
    if raw:
        try:
            due = date.fromisoformat(raw)
            today = date.today()
            if due < today:
                overdue_rank = 0
            elif due == today:
                overdue_rank = 1
            else:
                overdue_rank = 2
        except ValueError:
            raw = "9999-99-99"
    else:
        raw = "9999-99-99"
        overdue_rank = 3
    return (overdue_rank, raw, str(row.get("title") or "").casefold())


def filter_dashboard_reminders(
    rows: list[dict[str, Any]],
    *,
    profile: dict[str, Any],
    role: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    visible = [r for r in rows if visible_to_user(r, profile=profile, role=role)]
    visible.sort(key=_due_sort_key)
    return visible[: max(0, int(limit))]


def due_date_badge(due_raw: object) -> tuple[str, str]:
    """Return (label, css level: danger|warn|ok)."""
    raw = str(due_raw or "")[:10]
    if not raw:
        return "No due date", "ok"
    try:
        due = date.fromisoformat(raw)
    except ValueError:
        return raw, "ok"
    today = date.today()
    delta = (due - today).days
    if delta < 0:
        return f"Overdue {abs(delta)}d", "danger"
    if delta == 0:
        return "Due today", "warn"
    if delta <= 7:
        return f"Due in {delta}d", "warn"
    return due.strftime("%b %d"), "ok"


def can_create_management_reminder(role: str) -> bool:
    return str(role or "").strip().lower() in _MANAGEMENT_ROLES


def create_management_reminder(
    *,
    title: str,
    assignee_name: str,
    due_date: date | None = None,
) -> tuple[bool, str]:
    title_clean = str(title or "").strip()
    if not title_clean:
        return False, "Enter a reminder title."
    assignee = str(assignee_name or "").strip()
    if not assignee or assignee in {"—", "— Select —"}:
        return False, "Choose an assignee."

    try:
        from app.pages._core._data import persist_task
    except ImportError:
        from pages._core._data import persist_task  # type: ignore

    ok, msg = persist_task(
        {
            "title": title_clean,
            "description": "",
            "status": "Open",
            "priority": "Medium",
            "due_date": due_date.isoformat() if due_date else None,
            "assigned_to": assignee,
            "linked_job": "— None —",
            "job_id": None,
            "linked_estimate": "— None —",
        }
    )
    if ok:
        try:
            from app.services.tasks_service import clear_tasks_cache
        except ImportError:
            from services.tasks_service import clear_tasks_cache  # type: ignore
        clear_tasks_cache()
    return ok, msg if not ok else "Reminder saved."


def complete_management_reminder(task_id: str) -> tuple[bool, str]:
    tid = str(task_id or "").strip()
    if not tid:
        return False, "Missing reminder id."
    try:
        from app.pages._core._crud import is_demo_id
    except ImportError:
        from pages._core._crud import is_demo_id  # type: ignore
    if is_demo_id(tid):
        return False, "Demo reminders cannot be saved."

    try:
        from app.services.tasks_service import clear_tasks_cache, update_task
        from app.services.repository import user_facing_error
    except ImportError:
        from services.tasks_service import clear_tasks_cache, update_task  # type: ignore
        from services.repository import user_facing_error  # type: ignore

    result = update_task(tid, {"status": "Complete"})
    err = user_facing_error(result)
    if err:
        return False, err
    clear_tasks_cache()
    return True, "Reminder completed."
