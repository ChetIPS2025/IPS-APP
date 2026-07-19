"""HTML Users list table with native detail links."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

from app.components.users_list_table import (
    USERS_TABLE_COL_WIDTHS_PX,
    USERS_TABLE_HEADERS,
    user_avatar_html,
    user_status_pill_html,
)

_USER_DETAIL_QUERY_KEY = "user_detail"
_NAV_SLUG = "employees"


def user_detail_href(user_id: str) -> str:
    """Build a native navigation URL that opens User Details."""
    uid = str(user_id or "").strip()
    params = {"ips_nav": _NAV_SLUG, _USER_DETAIL_QUERY_KEY: uid}
    return "?" + urlencode(params)


def _user_name_link_html(user_id: str, label: str) -> str:
    uid = str(user_id or "").strip()
    text = html.escape(label)
    href = html.escape(user_detail_href(uid), quote=True)
    aria = html.escape(f"Open details for {label}", quote=True)
    return (
        f'<a class="ips-users-open-link ips-users-name-link ips-users-list-link" '
        f'href="{href}" target="_self" aria-label="{aria}">{text}</a>'
    )


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-est-cell ips-dash-est-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def _text_cell(value: str, *, muted: bool = False) -> str:
    text = str(value or "—").strip() or "—"
    cls = "ips-users-muted-cell" if muted else "ips-users-text-cell"
    return f'<span class="{cls}" title="{html.escape(text, quote=True)}">{html.escape(text)}</span>'


def build_people_directory_table(
    rows: list[dict[str, Any]],
    *,
    display_name_fn: Callable[[dict[str, Any]], str] | None = None,
    display_email_fn: Callable[[dict[str, Any]], str] | None = None,
    display_role_fn: Callable[[dict[str, Any]], str] | None = None,
    display_phone_fn: Callable[[dict[str, Any]], str] | None = None,
    display_last_login_fn: Callable[[dict[str, Any]], str] | None = None,
    display_status_fn: Callable[[dict[str, Any]], str] | None = None,
) -> str:
    from app.components.users_list_table import user_display_name

    name_fn = display_name_fn or user_display_name
    email_fn = display_email_fn or (lambda u: str(u.get("email") or "—").strip() or "—")
    role_fn = display_role_fn or (
        lambda u: str(u.get("permission_role") or u.get("role") or u.get("role_name") or "—").strip() or "—"
    )
    phone_fn = display_phone_fn or (lambda u: "—")
    last_login_fn = display_last_login_fn or (lambda u: "—")
    status_fn = display_status_fn or (lambda u: "Active")

    col_parts = [
        f'<col class="ips-dash-est-col-{html.escape(key)}" style="width:{px}px;" />'
        for key, px in USERS_TABLE_COL_WIDTHS_PX.items()
    ]
    head_parts = [
        (
            f'<th scope="col" class="ips-dash-est-th ips-dash-est-th-{html.escape(key)}" '
            f'style="width:{USERS_TABLE_COL_WIDTHS_PX[key]}px;max-width:{USERS_TABLE_COL_WIDTHS_PX[key]}px;">'
            f"{html.escape(label)}</th>"
        )
        for key, label in USERS_TABLE_HEADERS
    ]

    body_rows: list[str] = []
    for row_idx, user in enumerate(rows):
        uid = str(user.get("id") or "").strip()
        if not uid:
            continue

        name = name_fn(user)
        open_label = name if name and name != "—" else "View user"
        email = email_fn(user)
        role = role_fn(user)
        phone = phone_fn(user)
        last_login = last_login_fn(user)
        status = status_fn(user)
        row_parity = "even" if row_idx % 2 else "odd"

        cells = [
            (
                "avatar",
                "center",
                _cell_wrapper(
                    user_avatar_html(user),
                    extra_class="ips-users-avatar-cell",
                    align="center",
                ),
            ),
            (
                "name",
                "left",
                _cell_wrapper(
                    _user_name_link_html(uid, open_label),
                    extra_class="ips-users-name-cell",
                ),
            ),
            ("email", "left", _cell_wrapper(_text_cell(email))),
            ("role", "left", _cell_wrapper(_text_cell(role))),
            (
                "status",
                "center",
                _cell_wrapper(user_status_pill_html(status), align="center"),
            ),
            ("phone", "left", _cell_wrapper(_text_cell(phone, muted=True))),
            ("last_login", "left", _cell_wrapper(_text_cell(last_login, muted=True))),
            (
                "actions",
                "center",
                _cell_wrapper(
                    _user_name_link_html(uid, "View"),
                    align="center",
                ),
            ),
        ]

        tds = "".join(
            (
                f'<td class="ips-dash-est-td ips-dash-est-td-{html.escape(key)}" '
                f'style="width:{USERS_TABLE_COL_WIDTHS_PX[key]}px;max-width:{USERS_TABLE_COL_WIDTHS_PX[key]}px;">'
                f"{content}</td>"
            )
            for key, _align, content in cells
        )
        body_rows.append(
            f'<tr class="ips-dash-est-tr ips-dash-est-row-{row_parity}" '
            f'data-user-id="{html.escape(uid, quote=True)}" data-row-id="{html.escape(uid, quote=True)}">'
            f"{tds}"
            f"</tr>"
        )

    min_width = sum(USERS_TABLE_COL_WIDTHS_PX.values())
    return (
        f'<div class="ips-dash-est-table-scroll" style="min-width:0;">'
        f'<table class="ips-dash-est-html-table ips-users-html-list-table" '
        f'style="min-width:{min_width}px;">'
        f"<colgroup>{''.join(col_parts)}</colgroup>"
        f'<thead><tr class="ips-dash-est-tr ips-dash-est-head-row">{"".join(head_parts)}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
        "</div>"
    )


__all__ = ["build_people_directory_table", "user_detail_href"]
