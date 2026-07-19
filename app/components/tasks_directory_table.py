"""Tasks directory native navigation links and HTML table."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlencode

from app.components.status import status_pill_html
from app.services.task_display_helpers import normalize_task_priority, normalize_task_status
from app.utils.formatting import fmt_date

_NAV_QUERY_KEY = "ips_nav"
_TASK_DETAIL_QUERY_KEY = "task_detail"
_TASK_DETAIL_TAB_QUERY_KEY = "task_tab"
_TASK_STATUS_ACTION_KEY = "task_status"


def task_detail_query_key() -> str:
    return _TASK_DETAIL_QUERY_KEY


def task_detail_tab_query_key() -> str:
    return _TASK_DETAIL_TAB_QUERY_KEY


def task_status_action_query_key() -> str:
    return _TASK_STATUS_ACTION_KEY


def task_detail_href(task_id: str, *, tab: str = "") -> str:
    params: dict[str, str] = {_NAV_QUERY_KEY: "tasks", _TASK_DETAIL_QUERY_KEY: str(task_id or "").strip()}
    tab_val = str(tab or "").strip()
    if tab_val:
        params[_TASK_DETAIL_TAB_QUERY_KEY] = tab_val
    return "?" + urlencode(params)


def task_status_action_href(task_id: str) -> str:
    params = {
        _NAV_QUERY_KEY: "tasks",
        _TASK_STATUS_ACTION_KEY: str(task_id or "").strip(),
    }
    return "?" + urlencode(params)


def task_title_link_html(task_id: str, title: str) -> str:
    text = html.escape(str(title or "Task"))
    href = html.escape(task_detail_href(task_id), quote=True)
    aria = html.escape(f"Open task details for {title or 'task'}", quote=True)
    return (
        f'<a class="ips-task-open-link" href="{href}" target="_self" aria-label="{aria}">{text}</a>'
    )


def _priority_pill_html(priority: object) -> str:
    pri = normalize_task_priority(priority)
    css = {
        "High": "ips-priority-high",
        "Medium": "ips-priority-medium",
        "Low": "ips-priority-low",
    }[pri]
    return f'<span class="ips-priority-pill {css}">{html.escape(pri)}</span>'


def build_tasks_html_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    headers = ["Task", "Status", "Priority", "Assigned To", "Job", "Due"]
    head = "".join(f'<th class="ips-task-th">{html.escape(h)}</th>' for h in headers)
    body = ""
    for row in rows:
        tid = str(row.get("id") or "").strip()
        status = normalize_task_status(row.get("status"))
        status_href = html.escape(task_status_action_href(tid), quote=True)
        status_cell = (
            f'<a class="ips-task-status-link" href="{status_href}" target="_self">'
            f"{status_pill_html(status)}</a>"
        )
        title_cell = task_title_link_html(tid, str(row.get("title") or "Task"))
        cells = [
            title_cell,
            status_cell,
            _priority_pill_html(row.get("priority")),
            html.escape(str(row.get("assigned_to_display") or "—")),
            html.escape(str(row.get("job_display") or "—")),
            html.escape(fmt_date(row.get("due_date"))),
        ]
        tds = "".join(f'<td class="ips-task-td">{c}</td>' for c in cells)
        body += f"<tr>{tds}</tr>"
    return (
        f'<div class="ips-task-table-wrap"><table class="ips-task-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


__all__ = [
    "build_tasks_html_table",
    "task_detail_href",
    "task_detail_query_key",
    "task_detail_tab_query_key",
    "task_status_action_href",
    "task_status_action_query_key",
    "task_title_link_html",
]
