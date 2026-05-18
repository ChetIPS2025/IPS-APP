"""To-do list filtering, deduplication, and sorting (no UI)."""

from __future__ import annotations

from typing import Any

TODO_STATUSES = ("Open", "In Progress", "Pending", "Waiting", "Complete", "Closed")
TODO_VIEW_OPTIONS = ("Active Tasks", "Completed Tasks", "All Tasks")
TODO_TERMINAL_STATUS_SLUGS = frozenset({"complete", "completed", "closed"})
TODO_PRIORITIES = ("Low", "Normal", "High", "Urgent")
TODO_PRIORITY_RANK = {"Urgent": 0, "High": 1, "Normal": 2, "Low": 3}


def priority_rank(v: str) -> int:
    return int(TODO_PRIORITY_RANK.get(str(v or "Normal").strip().title(), 9))


def due_sort_key(v: Any) -> tuple[int, str]:
    if v is None or str(v).strip() == "":
        return (1, "9999-12-31")
    return (0, str(v).strip())


def status_slug(status: Any) -> str:
    return str(status or "").strip().lower()


def is_terminal_todo_status(status: Any) -> bool:
    return status_slug(status) in TODO_TERMINAL_STATUS_SLUGS


def sort_todos(rows: list[dict]) -> list[dict]:
    rows.sort(
        key=lambda r: (
            priority_rank(str(r.get("priority") or "Normal")),
            due_sort_key(r.get("due_date")),
            str(r.get("created_at") or ""),
        )
    )
    return rows


def norm_todo_id(val: Any) -> str:
    s = str(val or "").strip()
    return s.lower() if s else ""


def composite_todo_key(r: dict) -> str:
    return "cmp:" + "|".join(
        [
            str(r.get("title") or "").strip().lower(),
            str(r.get("due_date") or "").strip(),
            str(r.get("assigned_to") or "").strip(),
            status_slug(r.get("status")),
        ]
    )


def dedupe_todos(rows: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        nid = norm_todo_id(r.get("id"))
        key = f"id:{nid}" if nid else composite_todo_key(r)
        merged[key] = r
    return list(merged.values())


def filter_todos_for_view(todos: list[dict], view: str) -> tuple[list[dict], int]:
    deduped = dedupe_todos([t for t in (todos or []) if isinstance(t, dict)])
    valid = [t for t in deduped if str(t.get("id") or "").strip()]
    active_count = sum(1 for t in valid if not is_terminal_todo_status(t.get("status")))
    view_l = str(view or TODO_VIEW_OPTIONS[0]).strip()
    if view_l == "Completed Tasks":
        shown = [t for t in valid if is_terminal_todo_status(t.get("status"))]
    elif view_l == "All Tasks":
        shown = list(valid)
    else:
        shown = [t for t in valid if not is_terminal_todo_status(t.get("status"))]
    return sort_todos(shown), active_count


def apply_todo_search(rows: list[dict], q: str, id_to_label: dict[str, str]) -> list[dict]:
    qq = str(q or "").strip().lower()
    if not qq:
        return list(rows)
    out: list[dict] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        aid = str(r.get("assigned_to") or "").strip()
        blob = " ".join(
            [
                str(r.get("title") or ""),
                str(r.get("description") or ""),
                str(r.get("status") or ""),
                str(r.get("priority") or ""),
                id_to_label.get(aid, ""),
            ]
        ).lower()
        if qq in blob:
            out.append(r)
    return out
