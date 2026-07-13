"""Office-scoped management reminders (``todos`` rows without a linked job)."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.services.task_display_helpers import normalize_task_status
from app.services.tasks_service import _resolve_task_job_id
_OFFICE_REMINDER_CREATE_ROLES = frozenset({"admin", "project manager", "supervisor", "employee"})

__all__ = [
    "can_create_management_reminder",
    "can_create_office_reminder",
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


def _profile_assignee_keys(profile: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for val in (
        profile.get("id"),
        profile.get("employee_id"),
        profile.get("email"),
        profile.get("full_name"),
        profile.get("name"),
    ):
        text = str(val or "").strip()
        if not text:
            continue
        keys.add(text.casefold())
        if "@" in text:
            local = text.split("@", 1)[0].strip()
            if local:
                keys.add(local.casefold())
    return keys


def _matches_profile(row: dict[str, Any], profile: dict[str, Any]) -> bool:
    keys = _profile_assignee_keys(profile)
    if not keys:
        return False

    candidates: list[str] = []
    for field in (
        "assigned_to",
        "assigned_to_email",
        "assigned_to_employee_id",
        "assignee_name",
        "assignee_email",
        "assignee_id",
    ):
        val = str(row.get(field) or "").strip()
        if val and val not in {"—", "— Select —", "-", "— None —", "— Unassigned —"}:
            candidates.append(val.casefold())

    for candidate in candidates:
        if candidate in keys:
            return True
        for key in keys:
            if key and (key in candidate or candidate in key):
                return True
    return False


def visible_to_user(row: dict[str, Any], *, profile: dict[str, Any], role: str) -> bool:
    del role
    if not is_office_reminder(row) or not is_open_reminder(row):
        return False
    return _matches_profile(row, profile)


def _created_sort_ts(row: dict[str, Any]) -> float:
    for key in ("created_at", "updated_at"):
        raw = str(row.get(key) or "").strip()
        if not raw:
            continue
        try:
            from datetime import datetime

            if "T" in raw:
                return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
            return datetime.fromisoformat(raw[:10]).timestamp()
        except ValueError:
            continue
    activity = row.get("activity")
    if isinstance(activity, list) and activity:
        raw = str(activity[0].get("when") or "").strip()
        if raw:
            try:
                from datetime import datetime

                return datetime.strptime(raw[:16], "%Y-%m-%d %H:%M").timestamp()
            except ValueError:
                pass
    return 0.0


def _due_sort_key(row: dict[str, Any]) -> tuple[int, str, float, str]:
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
    return (
        overdue_rank,
        raw,
        -_created_sort_ts(row),
        str(row.get("title") or "").casefold(),
    )


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


def can_create_office_reminder(role: str) -> bool:
    return str(role or "").strip().lower() in _OFFICE_REMINDER_CREATE_ROLES


def can_create_management_reminder(role: str) -> bool:
    """Backward-compatible alias for dashboard create permission."""
    return can_create_office_reminder(role)


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

    from app.pages._core._data import persist_task
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
        from app.services.tasks_service import clear_tasks_cache
        clear_tasks_cache()
    return ok, msg if not ok else "Reminder saved."


def complete_management_reminder(task_id: str) -> tuple[bool, str]:
    tid = str(task_id or "").strip()
    if not tid:
        return False, "Missing reminder id."
    from app.pages._core._crud import is_demo_id
    if is_demo_id(tid):
        return False, "Demo reminders cannot be saved."

    from app.services.tasks_service import clear_tasks_cache, update_task
    from app.services.repository import user_facing_error
    result = update_task(tid, {"status": "Complete"})
    err = user_facing_error(result)
    if err:
        return False, err
    clear_tasks_cache()
    return True, "Reminder completed."
