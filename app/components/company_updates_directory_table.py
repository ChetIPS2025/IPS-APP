"""Company Updates list HTML table with native detail links."""

from __future__ import annotations

import html
from urllib.parse import urlencode

_NAV_QUERY_KEY = "ips_nav"
_COMPANY_UPDATE_DETAIL_QUERY_KEY = "update_detail"
_COMPANY_UPDATE_TAB_QUERY_KEY = "update_tab"


def company_update_detail_query_key() -> str:
    return _COMPANY_UPDATE_DETAIL_QUERY_KEY


def company_update_tab_query_key() -> str:
    return _COMPANY_UPDATE_TAB_QUERY_KEY


def company_update_detail_href(update_id: str, *, tab: str = "") -> str:
    uid = str(update_id or "").strip()
    params: dict[str, str] = {_NAV_QUERY_KEY: "company_updates", _COMPANY_UPDATE_DETAIL_QUERY_KEY: uid}
    tab_val = str(tab or "").strip()
    if tab_val:
        params[_COMPANY_UPDATE_TAB_QUERY_KEY] = tab_val
    return "?" + urlencode(params)


def _category_pill_html(category: str) -> str:
    cls_map = {
        "Announcement": "ips-update-category-announcement",
        "Safety Alert": "ips-update-category-safety-alert",
        "Event": "ips-update-category-event",
        "HR Update": "ips-update-category-hr-update",
        "Project Update": "ips-update-category-project-update",
        "General": "ips-update-category-general",
    }
    cls = cls_map.get(category, "ips-update-category-general")
    return f'<span class="ips-update-pill {cls}">{html.escape(category)}</span>'


def _status_pill_html(status: str) -> str:
    cls_map = {
        "Published": "ips-update-status-published",
        "Draft": "ips-update-status-draft",
        "Scheduled": "ips-update-status-scheduled",
        "Archived": "ips-update-status-archived",
    }
    cls = cls_map.get(status, "ips-update-status-published")
    return f'<span class="ips-update-pill {cls}">{html.escape(status)}</span>'


def company_update_title_link_html(update_id: str, title: str, *, is_pinned: bool) -> str:
    uid = str(update_id or "").strip()
    label = html.escape(str(title or "Untitled Update"))
    href = html.escape(company_update_detail_href(uid), quote=True)
    pinned = '<span class="ips-update-pinned">Pinned</span>' if is_pinned else ""
    aria = html.escape(f"Open company update details for {title or 'update'}", quote=True)
    return (
        f'<a class="ips-company-update-open-link ips-updates-title" href="{href}" '
        f'target="_self" aria-label="{aria}">{label}{pinned}</a>'
    )


def build_company_updates_html_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    head = "".join(
        f'<th class="ips-updates-th">{html.escape(h)}</th>'
        for h in ("TITLE", "CATEGORY", "AUDIENCE", "STATUS", "EVENT DATE", "CREATED BY", "CREATED")
    )
    body = ""
    for row in rows:
        uid = str(row.get("id") or "")
        title = company_update_title_link_html(
            uid,
            str(row.get("title") or "Untitled Update"),
            is_pinned=bool(row.get("is_pinned")),
        )
        cells = [
            title,
            _category_pill_html(str(row.get("category") or "General")),
            f'<span class="ips-updates-muted ips-updates-cell">{html.escape(str(row.get("audience") or "—"))}</span>',
            _status_pill_html(str(row.get("status") or "Published")),
            html.escape(str(row.get("event_date_display") or "—")),
            html.escape(str(row.get("created_by_display") or "—")),
            f'<span class="ips-updates-muted ips-updates-cell">{html.escape(str(row.get("created_display") or "—"))}</span>',
        ]
        tds = "".join(f'<td class="ips-updates-td">{c}</td>' for c in cells)
        body += f'<tr class="ips-updates-tr">{tds}</tr>'
    return (
        f'<div class="ips-updates-table-wrap"><table class="ips-updates-html-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )
