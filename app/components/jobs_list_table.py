"""Shared HTML helpers and click bridge for the Jobs list table."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st


def job_list_link_html(
    job_id: str,
    label: str,
    *,
    extra_class: str = "",
) -> str:
    jid = html.escape(str(job_id or "").strip(), quote=True)
    text = html.escape(label)
    title = html.escape(label, quote=True)
    cls = f"ips-jobs-list-link {extra_class}".strip()
    return (
        f'<a href="#" class="{html.escape(cls)}" data-job-action="open" '
        f'data-job-id="{jid}" title="{title}">{text}</a>'
    )


def render_jobs_table_link_bridge(
    *,
    component_key: str = "ips_jobs_list_bridge",
    hook_key: str = "ipsJobsList::action",
    last_action_key: str = "jobs_list_last_action",
) -> str | None:
    """Zero-height bridge: job # / project link clicks open job detail."""
    try:
        from app.ui.clean_table import _components_html
    except ImportError:
        from ui.clean_table import _components_html  # type: ignore

    st.markdown(
        '<span class="ips-jobs-table-link-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    picked = _components_html(
        f"""
<script>
(function () {{
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = {hook_key!r};
  const sel = "[data-job-id][data-job-action]";

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
      if (el.dataset.ipsJobsTableBound === "1") return;
      el.dataset.ipsJobsTableBound = "1";
      el.addEventListener("click", function (e) {{
        e.preventDefault();
        e.stopPropagation();
        const id = el.getAttribute("data-job-id");
        const action = el.getAttribute("data-job-action") || "open";
        if (!id) return;
        sendValue(action + ":" + id);
      }});
    }});
  }}

  if (!doc.ipsJobsTableRegistry) doc.ipsJobsTableRegistry = {{}};
  doc.ipsJobsTableRegistry[hookKey] = {{ bind: bindTargets }};
  bindTargets();
  if (!doc.ipsJobsTableBindObserver) {{
    doc.ipsJobsTableBindObserver = new MutationObserver(function () {{
      Object.values(doc.ipsJobsTableRegistry || {{}}).forEach(function (cfg) {{
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      }});
    }});
    doc.ipsJobsTableBindObserver.observe(doc.body, {{ childList: true, subtree: true }});
  }}
}})();
</script>
        """,
        component_key=component_key,
        height=0,
    )
    action = str(picked or "").strip()
    if not action:
        return None
    if action == str(st.session_state.get(last_action_key) or ""):
        return None
    st.session_state[last_action_key] = action
    if action.startswith("open:"):
        return action.split(":", 1)[1].strip()
    return None


def resolve_jobs_table_link_action(
    action: str | None,
    jobs_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    job_id = str(action or "").strip()
    if not job_id:
        return None
    return jobs_by_id.get(job_id)
