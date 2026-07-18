"""Shared HTML Users list table (aligned with Inventory list design)."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

USERS_TABLE_LAST_ACTION_KEY = "users_list_last_action"

_AVATAR_URL_KEYS = (
    "photo_url",
    "image_url",
    "avatar_url",
    "profile_image_url",
    "picture",
    "photo_path",
)

USERS_TABLE_HEADERS: tuple[tuple[str, str], ...] = (
    ("avatar", ""),
    ("name", "NAME"),
    ("email", "EMAIL"),
    ("role", "ROLE"),
    ("status", "STATUS"),
    ("phone", "PHONE"),
    ("last_login", "LAST LOGIN"),
    ("actions", "ACTIONS"),
)

USERS_TABLE_COL_WIDTHS_PX: dict[str, int] = {
    "avatar": 64,
    "name": 200,
    "email": 220,
    "role": 128,
    "status": 108,
    "phone": 128,
    "last_login": 148,
    "actions": 88,
}


def user_bridge_button_key(row: dict[str, Any]) -> str:
    raw = str(row.get("id") or row.get("email") or "user").strip()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw) or "user"
    return f"user_bridge_open_{safe}"


def user_initials(name: str) -> str:
    parts = [p for p in str(name or "").strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _looks_like_image_url(value: str) -> bool:
    v = str(value or "").strip().lower()
    return v.startswith(("http://", "https://", "data:image", "/"))


def resolve_user_avatar_url(user: dict[str, Any]) -> str:
    for key in _AVATAR_URL_KEYS:
        raw = str(user.get(key) or "").strip()
        if raw and _looks_like_image_url(raw):
            return raw
    return ""


def user_display_name(user: dict[str, Any]) -> str:
    for key in ("full_name", "name", "username", "email"):
        val = str(user.get(key) or "").strip()
        if val:
            return val
    return "Unnamed User"


def user_avatar_html(user: dict[str, Any]) -> str:
    name = user_display_name(user)
    url = resolve_user_avatar_url(user)
    if url:
        return (
            f'<img class="ips-users-avatar" src="{html.escape(url, quote=True)}" '
            f'alt="{html.escape(name)}" />'
        )
    initials = user_initials(name)
    return (
        f'<span class="ips-users-avatar-initials" aria-label="{html.escape(name)}">'
        f"{html.escape(initials)}</span>"
    )


def user_list_link_html(
    user_id: str,
    label: str,
    *,
    extra_class: str = "",
    bridge_key: str = "",
) -> str:
    """Backward-compatible name link for tests and legacy callers."""
    return _user_link_html(user_id, label, extra_class=extra_class, bridge_key=bridge_key)


def _user_link_html(
    uid: str,
    label: str,
    *,
    extra_class: str = "",
    bridge_key: str = "",
    action: str = "open",
) -> str:
    row_id = html.escape(str(uid or "").strip(), quote=True)
    text = html.escape(label)
    title = html.escape(label, quote=True)
    cls = f"ips-users-open-link ips-users-name-link ips-users-list-link {extra_class}".strip()
    bridge_attr = ""
    if bridge_key:
        bridge_attr = f' data-bridge-key="{html.escape(bridge_key, quote=True)}"'
    return (
        f'<span role="button" tabindex="0" class="{html.escape(cls)}" '
        f'data-user-action="{html.escape(action)}" data-user-id="{row_id}" '
        f'data-row-id="{row_id}"{bridge_attr} title="{title}">{text}</span>'
    )


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-est-cell ips-dash-est-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def _text_cell(value: str, *, muted: bool = False) -> str:
    text = str(value or "—").strip() or "—"
    cls = "ips-users-muted-cell" if muted else "ips-users-text-cell"
    return f'<span class="{cls}" title="{html.escape(text, quote=True)}">{html.escape(text)}</span>'


def user_status_pill_html(status: str) -> str:
    cls_map = {
        "Active": "ips-user-status-active",
        "Inactive": "ips-user-status-inactive",
        "Deleted": "ips-user-status-deleted",
        "Locked": "ips-user-status-locked",
        "Pending": "ips-user-status-pending",
    }
    cls = cls_map.get(status, "ips-user-status-active")
    return f'<span class="ips-user-pill {cls}">{html.escape(status)}</span>'


def build_users_html_table(
    rows: list[dict[str, Any]],
    *,
    display_name_fn: Callable[[dict[str, Any]], str] | None = None,
    display_email_fn: Callable[[dict[str, Any]], str] | None = None,
    display_role_fn: Callable[[dict[str, Any]], str] | None = None,
    display_phone_fn: Callable[[dict[str, Any]], str] | None = None,
    display_last_login_fn: Callable[[dict[str, Any]], str] | None = None,
    display_status_fn: Callable[[dict[str, Any]], str] | None = None,
) -> str:
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

        bridge_key = user_bridge_button_key(user)
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
                    _user_link_html(uid, open_label, bridge_key=bridge_key),
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
                    _user_link_html(uid, "View", bridge_key=bridge_key, extra_class="ips-users-action-link"),
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
            f'data-user-id="{html.escape(uid, quote=True)}" data-row-id="{html.escape(uid, quote=True)}" '
            f'data-bridge-key="{html.escape(bridge_key, quote=True)}">'
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


def handle_users_table_action(
    raw: str,
    users_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str,
    open_user_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    val = str(raw or "").strip()
    if not val:
        return
    if val == str(st.session_state.get(last_action_key) or ""):
        return
    st.session_state[last_action_key] = val

    uid = val.split(":", 1)[1].strip() if val.startswith("open:") else val
    if not uid:
        return
    row = users_by_id.get(uid)
    if not row:
        return
    open_user_fn(uid, row)
    from app.ui.streamlit_perf import ips_app_rerun
    ips_app_rerun()


def render_users_table_open_buttons(
    rows: list[dict[str, Any]],
    *,
    open_user_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    with st.container(key="users_open_button_harness"):
        for row in rows:
            uid = str(row.get("id") or "").strip()
            if not uid:
                continue
            bridge_key = user_bridge_button_key(row)

            def _open(_uid: str = uid, _row: dict = row) -> None:
                open_user_fn(_uid, _row)

            st.button(
                "Open user",
                key=bridge_key,
                type="tertiary",
                on_click=_open,
            )


def render_users_table_bridge(
    *,
    component_key: str = "ips_users_list_bridge",
    hook_key: str = "ipsUsersList::action",
) -> str | None:
    from app.ui.clean_table import _components_html
    return _components_html(
        f"""
<script>
(function () {{
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = {hook_key!r};
  const wrapSel = ".st-key-users_table_wrap";
  const openSel = wrapSel + " [data-user-action='open'][data-user-id]";
  const rowSel = wrapSel + " tbody tr[data-row-id]";

  function sendValue(action) {{
    const payload = {{ type: "streamlit:setComponentValue", value: action }};
    const frames = [window, window.parent, w].filter(function (f, i, arr) {{
      return f && arr.indexOf(f) === i;
    }});
    for (var i = 0; i < frames.length; i++) {{
      try {{
        if (frames[i].Streamlit && typeof frames[i].Streamlit.setComponentValue === "function") {{
          frames[i].Streamlit.setComponentValue(action);
          return;
        }}
      }} catch (err) {{}}
    }}
    for (var j = 0; j < frames.length; j++) {{
      try {{ frames[j].postMessage(payload, "*"); }} catch (err) {{}}
    }}
  }}

  function clickBridgeButton(bridgeKey) {{
    if (!bridgeKey) return false;
    const host = doc.querySelector(".st-key-" + bridgeKey);
    const btn = host && host.querySelector('[data-testid="stButton"] > button');
    if (!btn) return false;
    btn.click();
    return true;
  }}

  function openItem(id, bridgeKey) {{
    if (!id) return;
    if (bridgeKey && clickBridgeButton(bridgeKey)) return;
    sendValue("open:" + id);
  }}

  function isInteractive(target) {{
    return !!(target && target.closest && target.closest(
      "button, [role='button'], input, select, textarea, label, a, [data-testid='stButton'], [data-testid='stPopover'], [data-testid='stCheckbox']"
    ));
  }}

  function bindTargets() {{
    doc.querySelectorAll(openSel).forEach(function (link) {{
      if (link.dataset.ipsUsersOpenBound === "1") return;
      link.dataset.ipsUsersOpenBound = "1";
      link.addEventListener("click", function (e) {{
        e.preventDefault();
        e.stopPropagation();
        const id = link.getAttribute("data-user-id") || link.getAttribute("data-row-id");
        openItem(id, link.getAttribute("data-bridge-key") || "");
      }});
    }});
    doc.querySelectorAll(rowSel).forEach(function (row) {{
      if (row.dataset.ipsUsersRowBound === "1") return;
      row.dataset.ipsUsersRowBound = "1";
      row.addEventListener("click", function (e) {{
        if (isInteractive(e.target)) return;
        const id = row.getAttribute("data-row-id") || row.getAttribute("data-user-id");
        if (!id) return;
        e.preventDefault();
        e.stopPropagation();
        openItem(id, row.getAttribute("data-bridge-key") || "");
      }}, true);
    }});
  }}

  if (!doc.ipsUsersTableDocClick) {{
    doc.ipsUsersTableDocClick = true;
    doc.addEventListener("click", function (e) {{
      const t = e.target;
      if (!t || !t.closest) return;
      const wrap = doc.querySelector(wrapSel);
      if (!wrap || !wrap.contains(t)) return;
      const link = t.closest("[data-user-action='open'][data-user-id]");
      if (link && wrap.contains(link)) {{
        e.preventDefault();
        e.stopPropagation();
        const id = link.getAttribute("data-user-id") || link.getAttribute("data-row-id");
        openItem(id, link.getAttribute("data-bridge-key") || "");
        return;
      }}
      if (isInteractive(t)) return;
      const row = t.closest("tbody tr[data-row-id]");
      if (!row || !wrap.contains(row)) return;
      const id = row.getAttribute("data-row-id") || row.getAttribute("data-user-id");
      if (!id) return;
      e.preventDefault();
      e.stopPropagation();
      openItem(id, row.getAttribute("data-bridge-key") || "");
    }}, true);
  }}

  if (!doc.ipsUsersTableRegistry) doc.ipsUsersTableRegistry = {{}};
  doc.ipsUsersTableRegistry[hookKey] = {{ bind: bindTargets }};
  bindTargets();
  if (!doc.ipsUsersTableBindObserver) {{
    doc.ipsUsersTableBindObserver = new MutationObserver(function () {{
      Object.values(doc.ipsUsersTableRegistry || {{}}).forEach(function (cfg) {{
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      }});
    }});
    doc.ipsUsersTableBindObserver.observe(doc.body, {{ childList: true, subtree: true }});
  }}
  try {{
    w.postMessage({{ type: "streamlit:componentReady", apiVersion: 1 }}, "*");
  }} catch (err) {{}}
}})();
</script>
        """,
        component_key=component_key,
        height=0,
    )


def apply_users_table_bridge_action(
    action: str | None,
    users_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str = USERS_TABLE_LAST_ACTION_KEY,
    open_user_fn: Callable[[str, dict[str, Any]], None],
) -> bool:
    raw = str(action or "").strip()
    if not raw:
        return False
    handle_users_table_action(
        raw,
        users_by_id,
        last_action_key=last_action_key,
        open_user_fn=open_user_fn,
    )
    return raw.startswith("open:")


def render_users_table_bridge_legacy(
    users_by_id: dict[str, dict[str, Any]],
    *,
    component_key: str = "ips_users_list_bridge",
    hook_key: str = "ipsUsersList::action",
    last_action_key: str = USERS_TABLE_LAST_ACTION_KEY,
    open_user_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    st.markdown(
        '<span class="ips-users-table-link-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    picked = render_users_table_bridge(
        component_key=component_key,
        hook_key=hook_key,
    )
    apply_users_table_bridge_action(
        picked,
        users_by_id,
        last_action_key=last_action_key,
        open_user_fn=open_user_fn,
    )
