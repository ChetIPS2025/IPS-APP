"""Daily Work Package metrics (task-first dashboard; no job-level health scoring)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from app.services import task_photos as _tp
from app.services.supervisor_planning import delay_reason_label
_TASK_TERMINAL = frozenset(
    {"complete", "duplicate", "electrical", "waiting_on_customer", "cancelled"}
)


def _task_terminal(st: str) -> bool:
    return str(st or "").strip().lower() in _TASK_TERMINAL


def _parse_date(v: Any) -> date | None:
    if v is None:
        return None
    s = str(v).strip()[:10]
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _norm_status(st: str) -> str:
    s = str(st or "").strip().lower()
    if s == "open":
        return "not_started"
    return s


def dashboard_dwp_snapshot(
    *,
    today: date,
    packages: list[dict[str, Any]],
    package_tasks: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    photo_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    KPIs scoped to tasks that appear on a **daily work package** dated ``today``.
    Idle jobs (no package today) do not contribute.
    """
    t_iso = today.isoformat()[:10]
    pkg_ids_today: set[str] = set()
    for p in packages or []:
        if not isinstance(p, dict):
            continue
        if str(p.get("work_date") or "")[:10] != t_iso:
            continue
        pid = str(p.get("id") or "").strip()
        if pid:
            pkg_ids_today.add(pid)

    work_packages_today = len(pkg_ids_today)
    assigned_task_ids: set[str] = set()
    for row in package_tasks or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("daily_work_package_id") or "").strip() not in pkg_ids_today:
            continue
        tid = str(row.get("job_task_id") or "").strip()
        if tid:
            assigned_task_ids.add(tid)

    tasks_assigned_today = len(assigned_task_ids)
    task_map = {str(t.get("id")): t for t in (tasks or []) if isinstance(t, dict) and str(t.get("id") or "").strip()}

    photos_scope = [
        r
        for r in (photo_rows or [])
        if isinstance(r, dict) and str(r.get("task_id") or "").strip() in assigned_task_ids
    ]
    photos_by = _tp.photos_by_task_id(photos_scope)

    completed_today = 0
    blocked = 0
    high_priority_open = 0
    missing_after_photo = 0

    for tid in assigned_task_ids:
        t = task_map.get(tid) or {}
        st = _norm_status(str(t.get("status") or ""))
        cd = str(t.get("completed_date") or "")[:10]
        pr = str(t.get("priority") or "").strip().lower()

        if st == "complete" and cd == t_iso:
            completed_today += 1
            if not _tp.task_has_after_photo(tid, t, photos_by):
                missing_after_photo += 1
        if st == "blocked":
            blocked += 1
        if pr in ("high", "critical") and not _task_terminal(st):
            high_priority_open += 1

    return {
        "work_packages_today": work_packages_today,
        "tasks_assigned_today": tasks_assigned_today,
        "tasks_completed_today": completed_today,
        "blocked": blocked,
        "high_priority_open": high_priority_open,
        "missing_after_photo": missing_after_photo,
    }


def repeated_eod_delay_reasons(
    *,
    packages: list[dict[str, Any]],
    executions: list[dict[str, Any]],
    today: date,
    days: int = 14,
) -> list[tuple[str, int]]:
    """Delay slugs from supervisor_daily_execution over distinct work dates (2+ days)."""
    start = today - timedelta(days=days - 1)
    pkg_by_id = {str(p.get("id") or "").strip(): p for p in (packages or []) if isinstance(p, dict) and p.get("id")}
    by_reason: dict[str, set[str]] = defaultdict(set)
    for ex in executions or []:
        if not isinstance(ex, dict):
            continue
        pid = str(ex.get("daily_work_package_id") or "").strip()
        p = pkg_by_id.get(pid)
        if not p:
            continue
        wd = _parse_date(p.get("work_date"))
        if wd is None or wd < start or wd > today:
            continue
        dr = str(ex.get("delay_reason") or "none").strip().lower()
        if not dr or dr == "none":
            continue
        by_reason[dr].add(wd.isoformat()[:10])
    pairs = [(delay_reason_label(k), len(v)) for k, v in by_reason.items() if len(v) >= 2]
    pairs.sort(key=lambda x: (-x[1], x[0]))
    return pairs[:10]
