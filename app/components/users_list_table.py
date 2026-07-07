"""Shared HTML helpers and click bridge for the Users list table."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st


def user_list_link_html(
    user_id: str,
    label: str,
    *,
    extra_class: str = "",
) -> str:
    uid = html.escape(str(user_id or "").strip(), quote=True)
    text = html.escape(label)
    title = html.escape(label, quote=True)
    cls = f"ips-users-list-link ips-users-name-label ips-users-name {extra_class}".strip()
    return (
        f'<a href="#" class="{html.escape(cls)}" data-user-action="open" '
        f'data-user-id="{uid}" title="{title}">{text}</a>'
    )


def handle_users_table_action(
    raw: str,
    users_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str,
    open_user_fn: Callable[[dict[str, Any]], None],
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
    open_user = users_by_id.get(uid)
    if not open_user:
        return
    open_user_fn(open_user)


def render_users_table_link_bridge(
    users_by_id: dict[str, dict[str, Any]],
    *,
    component_key: str = "ips_users_list_bridge",
    hook_key: str = "ipsUsersList::action",
    last_action_key: str = "users_list_last_action",
    open_user_fn: Callable[[dict[str, Any]], None],
) -> None:
    """Zero-height bridge: user name link clicks open user detail."""
    try:
        from app.ui.clean_table import _components_html
    except ImportError:
        from ui.clean_table import _components_html  # type: ignore

    st.markdown(
        '<span class="ips-users-table-link-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    picked = _components_html(
        f"""
<script>
(function () {{
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = {hook_key!r};
  const sel = ".ips-users-list-link[data-user-id][data-user-action]";

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

  function bindTargets() {{
    doc.querySelectorAll(sel).forEach(function (el) {{
      if (el.dataset.ipsUsersTableBound === "1") return;
      el.dataset.ipsUsersTableBound = "1";
      el.addEventListener("click", function (e) {{
        e.preventDefault();
        e.stopPropagation();
        const id = el.getAttribute("data-user-id");
        const action = el.getAttribute("data-user-action") || "open";
        if (!id) return;
        sendValue(action + ":" + id);
      }});
    }});
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
}})();
</script>
        """,
        component_key=component_key,
        height=1,
    )
    action = str(picked or "").strip()
    if action:
        handle_users_table_action(
            action,
            users_by_id,
            last_action_key=last_action_key,
            open_user_fn=open_user_fn,
        )
