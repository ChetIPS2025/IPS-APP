"""Paginated Tasks directory — list projection, filters, and field visibility."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.task_display_helpers import normalize_task_priority, normalize_task_status
from app.services.task_reference_service import resolve_task_assignee_labels, resolve_task_job_labels
from app.services.tasks_cache import tasks_data_version

TASKS_DEFAULT_PAGE_SIZE = 25
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TaskRenderContext:
    today: date
    view: str
    field_job_id: str | None


@dataclass(frozen=True)
class TasksPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    filter_options: dict[str, list[str]]
    is_live: bool
    warning: str | None = None


def _priority_rank(priority: str) -> int:
    return {"High": 0, "Medium": 1, "Low": 2}.get(priority, 3)


def _sort_tasks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _key(row: dict[str, Any]) -> tuple:
        status = normalize_task_status(row.get("status"))
        open_first = 0 if status == "Open" else 1
        pri = _priority_rank(normalize_task_priority(row.get("priority")))
        due = str(row.get("due_date") or "9999-99-99")
        created = str(row.get("created_at") or "")
        title = str(row.get("title") or "").lower()
        return open_first, pri, due, created, title

    return sorted(rows, key=_key)


def _apply_view_filter(rows: list[dict[str, Any]], view: str, *, today: date) -> list[dict[str, Any]]:
    if view == "Due Today":
        today_s = today.isoformat()
        return [
            t
            for t in rows
            if normalize_task_status(t.get("status")) == "Open"
            and str(t.get("due_date") or "")[:10] == today_s
        ]
    if view == "Closed To-Dos":
        return [t for t in rows if normalize_task_status(t.get("status")) == "Closed"]
    if view == "Open To-Dos":
        return [t for t in rows if normalize_task_status(t.get("status")) == "Open"]
    return list(rows)


def _apply_search(rows: list[dict[str, Any]], search: str) -> list[dict[str, Any]]:
    q = str(search or "").strip().lower()
    if not q:
        return rows
    out: list[dict[str, Any]] = []
    for row in rows:
        hay = " ".join(
            str(row.get(k) or "")
            for k in (
                "title",
                "description",
                "job_display",
                "assigned_to_display",
                "priority_display",
            )
        ).lower()
        if q in hay:
            out.append(row)
    return out


def _apply_column_filters(
    rows: list[dict[str, Any]],
    *,
    priorities: list[str] | None,
    assignee_ids: list[str] | None,
    job_ids: list[str] | None,
) -> list[dict[str, Any]]:
    out = list(rows)
    if priorities:
        wanted = {str(p).strip() for p in priorities if str(p).strip()}
        if wanted:
            out = [r for r in out if str(r.get("priority_display") or "") in wanted]
    if assignee_ids:
        wanted = {str(a).strip().lower() for a in assignee_ids if str(a).strip()}
        if wanted:
            out = [
                r
                for r in out
                if str(r.get("assigned_to_display") or "").strip().lower() in wanted
                or str(r.get("assigned_to") or "").strip().lower() in wanted
            ]
    if job_ids:
        wanted = {str(j).strip() for j in job_ids if str(j).strip()}
        if wanted:
            out = [r for r in out if str(r.get("job_id") or "") in wanted]
    return out


def _task_matches_employee(task: dict[str, Any], match_ids: set[str]) -> bool:
    raw = str(task.get("assigned_to") or "").strip().lower()
    if not raw or raw in {"—", "— unassigned —"}:
        return False
    if raw in match_ids:
        return True
    display = str(task.get("assigned_to_display") or "").strip().lower()
    return bool(display and display in match_ids)


def _apply_field_visibility(
    rows: list[dict[str, Any]],
    *,
    field_job_id: str | None,
    current_user_match_ids: list[str] | None,
    is_field_employee: bool,
) -> list[dict[str, Any]]:
    out = list(rows)
    fid = str(field_job_id or "").strip()
    if fid:
        out = [t for t in out if str(t.get("job_id") or "").strip() == fid]
    if is_field_employee and current_user_match_ids:
        keys = {str(k).strip().lower() for k in current_user_match_ids if str(k).strip()}
        out = [t for t in out if _task_matches_employee(t, keys)]
    return out


def _to_list_row(task: dict[str, Any], *, assignee_map: dict[str, str], job_map: dict[str, str]) -> dict[str, Any]:
    aid = str(task.get("assigned_to") or "").strip()
    assignee_display = assignee_map.get(aid, "")
    if not assignee_display and aid and not _UUID_RE.match(aid):
        assignee_display = aid
    if not assignee_display:
        assignee_display = "—"
    jid = str(task.get("job_id") or "").strip()
    job_display = job_map.get(jid, "")
    if not job_display:
        raw = str(task.get("linked_job") or task.get("job_label") or "").strip()
        if raw and raw not in {"— None —", "None", "—", "-"} and not _UUID_RE.match(raw):
            job_display = raw
    if not job_display:
        job_display = "—"
    return {
        "id": str(task.get("id") or ""),
        "title": str(task.get("title") or ""),
        "description": str(task.get("description") or ""),
        "status": normalize_task_status(task.get("status")),
        "priority": normalize_task_priority(task.get("priority")),
        "priority_display": normalize_task_priority(task.get("priority")),
        "assigned_to": aid,
        "assigned_to_display": assignee_display,
        "job_id": jid or None,
        "job_display": job_display,
        "linked_estimate": str(task.get("linked_estimate") or "— None —"),
        "due_date": str(task.get("due_date") or "")[:10],
        "created_at": str(task.get("created_at") or ""),
        "notes": str(task.get("notes") or ""),
    }


def _merge_demo_overrides(tasks: list[dict[str, Any]], overrides: dict[str, dict]) -> list[dict[str, Any]]:
    if not overrides:
        return tasks
    merged: list[dict[str, Any]] = []
    for task in tasks:
        row = dict(task)
        tid = str(row.get("id") or "").strip()
        if tid and tid in overrides:
            row.update(overrides[tid])
        merged.append(row)
    return merged


def list_tasks_page(
    *,
    view: str = "Open To-Dos",
    search: str = "",
    priorities: list[str] | None = None,
    assignee_ids: list[str] | None = None,
    job_ids: list[str] | None = None,
    due_date: date | None = None,
    field_job_id: str | None = None,
    current_user_match_ids: list[str] | None = None,
    is_field_employee: bool = False,
    demo_overrides: dict[str, dict] | None = None,
    page: int = 1,
    page_size: int = TASKS_DEFAULT_PAGE_SIZE,
) -> TasksPage:
    from app.perf_debug import perf_span

    today = due_date or date.today()
    pg = max(1, int(page or 1))
    size = max(1, min(200, int(page_size or TASKS_DEFAULT_PAGE_SIZE)))
    version = tasks_data_version()
    cache_key = (
        f"tasks:dir:v{version}:{view}:{search}:{field_job_id}:{is_field_employee}:"
        f"p{pg}:s{size}:{','.join(current_user_match_ids or [])}"
    )

    def _build() -> TasksPage:
        with perf_span("tasks.list_query"):
            from app.services.tasks_service import get_tasks

            raw = _merge_demo_overrides(get_tasks(), demo_overrides or {})
            is_live = not any(str(r.get("id") or "").startswith("demo") for r in raw[:3])
            filtered = _apply_view_filter(raw, view, today=today)
            filtered = _apply_field_visibility(
                filtered,
                field_job_id=field_job_id,
                current_user_match_ids=current_user_match_ids,
                is_field_employee=is_field_employee,
            )
            assignee_ids_raw = [str(t.get("assigned_to") or "") for t in filtered]
            job_ids_raw = [str(t.get("job_id") or "") for t in filtered if t.get("job_id")]
            assignee_map = resolve_task_assignee_labels(assignee_ids_raw)
            job_map = resolve_task_job_labels(job_ids_raw)
            projected = [_to_list_row(t, assignee_map=assignee_map, job_map=job_map) for t in filtered]
            projected = _apply_column_filters(
                projected,
                priorities=priorities,
                assignee_ids=assignee_ids,
                job_ids=job_ids,
            )
            projected = _apply_search(projected, search)
            projected = _sort_tasks(projected)
            total = len(projected)
            start = (pg - 1) * size
            page_rows = projected[start : start + size]
            from app.services.task_reference_service import load_task_filter_options

            return TasksPage(
                rows=page_rows,
                total_count=total,
                page=pg,
                page_size=size,
                filter_options=load_task_filter_options(),
                is_live=is_live,
            )

    return page_data_cache_get(cache_key, _build)


def list_field_tasks_panel(
    *,
    job_id: str,
    employee_match_ids: list[str],
    due_date: date | None = None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    page = list_tasks_page(
        view="Due Today",
        field_job_id=job_id,
        current_user_match_ids=employee_match_ids,
        is_field_employee=True,
        due_date=due_date,
        page=1,
        page_size=limit,
    )
    return page.rows


__all__ = [
    "TASKS_DEFAULT_PAGE_SIZE",
    "TaskRenderContext",
    "TasksPage",
    "list_field_tasks_panel",
    "list_tasks_page",
]
