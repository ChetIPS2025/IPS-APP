"""Employee Resources admin HTML table and selected action panel."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlencode

from app.utils.formatting import fmt_date

_NAV_QUERY_KEY = "ips_nav"
_SELECT_QUERY_KEY = "er_select"
_MANAGE_QUERY_KEY = "er_manage"


def admin_select_query_key() -> str:
    return _SELECT_QUERY_KEY


def admin_manage_query_key() -> str:
    return _MANAGE_QUERY_KEY


def admin_select_href(resource_id: str) -> str:
    params = {
        _NAV_QUERY_KEY: "employee_resources",
        _MANAGE_QUERY_KEY: "1",
        _SELECT_QUERY_KEY: str(resource_id or "").strip(),
    }
    return "?" + urlencode(params)


def admin_title_link_html(resource_id: str, title: str) -> str:
    text = html.escape(str(title or "Resource"))
    href = html.escape(admin_select_href(resource_id), quote=True)
    aria = html.escape(f"Select resource {title or 'resource'} for management", quote=True)
    return (
        f'<a class="ips-er-admin-select-link" href="{href}" target="_self" aria-label="{aria}">{text}</a>'
    )


def _visibility_label(raw: object) -> str:
    text = str(raw or "").strip()
    return text if text else "All roles"


def build_employee_resources_admin_html_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    headers = ("Title", "Type", "Visibility", "Status", "Sort", "Updated")
    head = "".join(f'<th class="ips-er-admin-th">{html.escape(h)}</th>' for h in headers)
    body = ""
    for row in rows:
        rid = str(row.get("id") or "")
        title = admin_title_link_html(rid, str(row.get("title") or "Resource"))
        category = html.escape(str(row.get("category") or "—"))
        visibility = html.escape(_visibility_label(row.get("visible_to_roles")))
        status = "Active" if row.get("is_active", True) else "Hidden"
        status_cls = "ips-er-status-active" if row.get("is_active", True) else "ips-er-status-hidden"
        status_cell = f'<span class="{status_cls}">{html.escape(status)}</span>'
        sort_val = html.escape(str(int(row.get("sort_order") or 0)))
        updated = html.escape(fmt_date(str(row.get("updated_at") or row.get("created_at") or "")[:10]) or "—")
        body += (
            "<tr>"
            f"<td>{title}</td>"
            f"<td>{category}</td>"
            f"<td>{visibility}</td>"
            f"<td>{status_cell}</td>"
            f"<td>{sort_val}</td>"
            f"<td>{updated}</td>"
            "</tr>"
        )
    return (
        '<div class="ips-er-admin-table-wrap">'
        '<table class="ips-er-admin-table"><thead><tr>'
        f"{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )
