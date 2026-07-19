"""Job Subjobs HTML table."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlencode

from app.components.status import status_pill_html
from app.services.task_display_helpers import normalize_task_priority
from app.utils.formatting import fmt_date

_NAV_QUERY_KEY = "ips_nav"
_SUBJOB_DETAIL_KEY = "subjob_detail"


def subjob_detail_query_key() -> str:
    return _SUBJOB_DETAIL_KEY


def subjob_detail_href(job_id: str, task_id: str) -> str:
    params = {
        _NAV_QUERY_KEY: "jobs",
        "job_detail": str(job_id or "").strip(),
        "job_tab": "Tasks",
        _SUBJOB_DETAIL_KEY: str(task_id or "").strip(),
    }
    return "?" + urlencode(params)


def _priority_pill_html(priority: object) -> str:
    pri = normalize_task_priority(priority)
    css = {"High": "ips-priority-high", "Medium": "ips-priority-medium", "Low": "ips-priority-low"}[pri]
    return f'<span class="ips-priority-pill {css}">{html.escape(pri)}</span>'


def build_job_subjobs_html_table(rows: list[dict[str, Any]], *, job_id: str) -> str:
    if not rows:
        return ""
    headers = ["Subjob", "Status", "Priority", "Assigned To", "Due"]
    head = "".join(f'<th class="ips-subjob-th">{html.escape(h)}</th>' for h in headers)
    body = ""
    jid = html.escape(str(job_id or ""), quote=True)
    for row in rows:
        tid = str(row.get("id") or "").strip()
        title = str(row.get("title") or "Subjob")
        href = html.escape(subjob_detail_href(job_id, tid), quote=True)
        title_cell = f'<a class="ips-subjob-open-link" href="{href}" target="_self">{html.escape(title)}</a>'
        status = str(row.get("status") or "Open")
        cells = [
            title_cell,
            status_pill_html(status),
            _priority_pill_html(row.get("priority")),
            html.escape(str(row.get("assigned_to_display") or "—")),
            html.escape(fmt_date(row.get("due_date"))),
        ]
        tds = "".join(f'<td class="ips-subjob-td">{c}</td>' for c in cells)
        body += f'<tr data-job-id="{jid}">{tds}</tr>'
    return (
        f'<div class="ips-subjob-table-wrap"><table class="ips-subjob-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


__all__ = ["build_job_subjobs_html_table", "subjob_detail_href", "subjob_detail_query_key"]
