"""Dashboard preview cards — always-visible recent items (replaces collapsed expanders)."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.components.qr_scan_history_ui import inject_qr_scan_history_css
    from app.pages._core._data import load_recent_qr_scans, load_tasks
    from app.services.management_reminders_service import due_date_badge, filter_dashboard_reminders
    from app.utils.formatting import fmt_date, fmt_datetime
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from components.qr_scan_history_ui import inject_qr_scan_history_css  # type: ignore
    from pages._core._data import load_recent_qr_scans, load_tasks  # type: ignore
    from services.management_reminders_service import due_date_badge, filter_dashboard_reminders  # type: ignore
    from utils.formatting import fmt_date, fmt_datetime  # type: ignore


def _nav_slug(slug: str) -> None:
    try:
        from app.navigation import set_nav_slug
    except ImportError:
        from navigation import set_nav_slug  # type: ignore
    set_nav_slug(slug)
    st.rerun()


def _nav_job_costing() -> None:
    try:
        from app.navigation import open_jobs_job_costing
    except ImportError:
        from navigation import open_jobs_job_costing  # type: ignore
    open_jobs_job_costing()
    st.rerun()


def _priority_badge(priority: object) -> str:
    pri = str(priority or "Medium").strip() or "Medium"
    css = {
        "Urgent": "ips-dash-preview-priority-urgent",
        "High": "ips-dash-preview-priority-high",
        "Medium": "ips-dash-preview-priority-medium",
        "Low": "ips-dash-preview-priority-low",
    }.get(pri, "ips-dash-preview-priority-medium")
    return f'<span class="ips-dash-preview-badge {css}">{html.escape(pri)}</span>'


def _status_badge(status: object) -> str:
    val = str(status or "Open").strip() or "Open"
    low = val.casefold()
    if low in {"done", "complete", "completed", "closed"}:
        cls = "ips-dash-preview-status-done"
    elif low in {"blocked", "cancelled", "canceled"}:
        cls = "ips-dash-preview-status-blocked"
    elif low in {"in progress", "in_progress", "active"}:
        cls = "ips-dash-preview-status-active"
    else:
        cls = "ips-dash-preview-status-open"
    return f'<span class="ips-dash-preview-badge {cls}">{html.escape(val)}</span>'


def _todo_link_label(row: dict[str, Any]) -> str:
    job = str(row.get("linked_job") or "").strip()
    if job and job not in {"—", "— None —"}:
        return job
    est = str(row.get("linked_estimate") or "").strip()
    if est and est not in {"—", "— None —"}:
        return est
    customer = str(row.get("customer") or row.get("customer_name") or "").strip()
    return customer


def _todo_preview_rows(limit: int = 5) -> list[dict[str, Any]]:
    profile = current_profile() or {}
    return filter_dashboard_reminders(
        load_tasks(),
        profile=profile,
        role=current_role(),
        limit=limit,
    )


def _todo_assignee_label(row: dict[str, Any]) -> str:
    for field in ("assignee_name", "assigned_to", "assigned_to_email"):
        val = str(row.get(field) or "").strip()
        if val and val not in {"—", "— Select —", "-", "— None —", "— Unassigned —"}:
            return val
    return "Unassigned"


def _todo_preview_html(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="ips-dash-preview-empty">No open to-dos assigned to you.</p>'
    items: list[str] = []
    for row in rows:
        title = html.escape(str(row.get("title") or "Untitled"))
        due_raw = str(row.get("due_date") or "")[:10]
        due_txt = html.escape(fmt_date(due_raw) if due_raw else "No due date")
        due_label, due_level = due_date_badge(row.get("due_date"))
        assignee = html.escape(_todo_assignee_label(row))
        link = _todo_link_label(row)
        link_html = html.escape(link) if link else "—"
        items.append(
            '<li class="ips-dash-preview-row">'
            f'<div class="ips-dash-preview-row-main">'
            f'<p class="ips-dash-preview-row-title">{title}</p>'
            f'<p class="ips-dash-preview-row-sub">Due {due_txt}</p>'
            f"</div>"
            f'<div class="ips-dash-preview-row-meta">'
            f'<p class="ips-dash-preview-row-meta-line">'
            f'<span class="ips-dash-preview-row-meta-label">Assigned</span> {assignee}'
            f"</p>"
            f'<p class="ips-dash-preview-row-meta-line">'
            f'<span class="ips-dash-preview-row-meta-label">Link</span> {link_html}'
            f"</p>"
            f"</div>"
            f'<div class="ips-dash-preview-row-badges">'
            f'{_priority_badge(row.get("priority"))}'
            f'{_status_badge(row.get("status"))}'
            f'<span class="ips-deadline-badge {html.escape(due_level)}">{html.escape(due_label)}</span>'
            f"</div>"
            "</li>"
        )
    return f'<ul class="ips-dash-preview-list">{"".join(items)}</ul>'


def _analytics_preview_html() -> str:
    rows = [
        ("job_costing", "📊", "Job Costing", "Roll-up costs and margin by job"),
        ("timekeeping", "🕒", "Time Reports", "Weekly hours and labor summaries"),
        ("estimates", "📄", "Estimate Reports", "Pipeline and estimate status"),
        ("inventory", "📦", "Inventory Reports", "Stock movement and usage"),
    ]
    items: list[str] = []
    for action, icon, label, sub in rows:
        action_attr = html.escape(action, quote=True)
        items.append(
            '<button type="button" class="ips-dash-analytics-row" '
            f'data-nav-action="{action_attr}">'
            '<span class="ips-dash-analytics-row-body">'
            f'<span class="ips-dash-analytics-row-icon">{html.escape(icon)}</span>'
            '<span class="ips-dash-analytics-row-text">'
            f'<span class="ips-dash-analytics-row-title">{html.escape(label)}</span>'
            f'<span class="ips-dash-analytics-row-sub">{html.escape(sub)}</span>'
            "</span>"
            "</span>"
            '<span class="ips-dash-analytics-row-chevron" aria-hidden="true">›</span>'
            "</button>"
        )
    return f'<div class="ips-dash-analytics-list">{"".join(items)}</div>'


_ANALYTICS_NAV_LAST_KEY = "_ips_dash_analytics_nav_last"


def _handle_analytics_nav(action: str) -> None:
    picked = str(action or "").strip()
    if not picked:
        return
    if picked == str(st.session_state.get(_ANALYTICS_NAV_LAST_KEY) or ""):
        return
    st.session_state[_ANALYTICS_NAV_LAST_KEY] = picked
    if picked == "job_costing":
        _nav_job_costing()
    elif picked == "timekeeping":
        _nav_slug("timekeeping")
    elif picked == "estimates":
        _nav_slug("estimates")
    elif picked == "inventory":
        _nav_slug("inventory")


def _render_analytics_reports_nav_bridge() -> str | None:
    try:
        from app.ui.clean_table import _components_html
    except ImportError:
        from ui.clean_table import _components_html  # type: ignore

    picked = _components_html(
        """
<script>
(function () {
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = "ipsDashAnalytics::nav";
  const rowSel = ".ips-dash-analytics-row[data-nav-action]";

  function sendValue(action) {
    const payload = { type: "streamlit:setComponentValue", value: action };
    const frames = [window, window.parent, w].filter(function (f, i, arr) {
      return f && arr.indexOf(f) === i;
    });
    for (var i = 0; i < frames.length; i++) {
      try {
        if (frames[i].Streamlit && typeof frames[i].Streamlit.setComponentValue === "function") {
          frames[i].Streamlit.setComponentValue(action);
          return;
        }
      } catch (err) {}
    }
    for (var j = 0; j < frames.length; j++) {
      try { frames[j].postMessage(payload, "*"); } catch (err) {}
    }
  }

  function bindRows() {
    doc.querySelectorAll(rowSel).forEach(function (row) {
      if (row.dataset.ipsDashAnalyticsBound === "1") return;
      row.dataset.ipsDashAnalyticsBound = "1";
      row.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        const action = row.getAttribute("data-nav-action");
        if (action) sendValue(action);
      });
    });
  }

  if (!doc.ipsDashAnalyticsRegistry) doc.ipsDashAnalyticsRegistry = {};
  doc.ipsDashAnalyticsRegistry[hookKey] = { bind: bindRows };
  bindRows();
  if (!doc.ipsDashAnalyticsBindObserver) {
    doc.ipsDashAnalyticsBindObserver = new MutationObserver(function () {
      Object.values(doc.ipsDashAnalyticsRegistry || {}).forEach(function (cfg) {
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      });
    });
    doc.ipsDashAnalyticsBindObserver.observe(doc.body, { childList: true, subtree: true });
  }
})();
</script>
        """,
        component_key="ips_dash_analytics_nav",
        height=0,
    )
    action = str(picked or "").strip()
    return action or None


def _render_analytics_reports_card() -> None:
    st.markdown(
        '<div class="ips-dash-preview-card-head">'
        '<span class="ips-dash-preview-card-icon">📈</span>'
        '<p class="ips-dash-preview-card-title">Analytics &amp; Reports</p>'
        "</div>"
        f"{_analytics_preview_html()}",
        unsafe_allow_html=True,
    )
    action = _render_analytics_reports_nav_bridge()
    if action:
        _handle_analytics_nav(action)
    if st.button("View All Reports", key="ips_dash_preview_an_all", use_container_width=True):
        _nav_slug("reports")


def _qr_preview_html(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="ips-dash-preview-empty">No QR scans recorded yet.</p>'
    items: list[str] = []
    for row in rows[:5]:
        summary = html.escape(str(row.get("summary") or row.get("item_name") or "—"))
        items.append(
            '<li class="ips-dash-preview-row">'
            f'<div class="ips-dash-preview-row-main">'
            f'<p class="ips-dash-preview-row-title ips-qr-scan-summary">{summary}</p>'
            f"</div>"
            "</li>"
        )
    return f'<ul class="ips-dash-preview-list">{"".join(items)}</ul>'


def _render_preview_card_shell(
    *,
    icon: str,
    title: str,
    body_html: str,
    view_key: str,
    on_view_all,
) -> None:
    ot = "d" + "iv"
    st.markdown(
        f'<{ot} class="ips-dash-preview-card">'
        f'<{ot} class="ips-dash-preview-card-head">'
        f'<span class="ips-dash-preview-card-icon">{html.escape(icon)}</span>'
        f'<p class="ips-dash-preview-card-title">{html.escape(title)}</p>'
        f"</{ot}>"
        f'<{ot} class="ips-dash-preview-card-body">{body_html}</{ot}>'
        f"</{ot}>",
        unsafe_allow_html=True,
    )
    if st.button("View All", key=view_key, use_container_width=True):
        on_view_all()


def render_dashboard_preview_sections() -> None:
    """Two-column grid of always-visible preview cards."""
    inject_qr_scan_history_css()
    qr_rows, _qr_live = load_recent_qr_scans(limit=5)
    todo_rows = _todo_preview_rows(limit=5)

    with st.container(key="dashboard_preview_sections"):
        st.markdown(
            '<span class="ips-dash-preview-grid-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        left_col, right_col = st.columns(2, gap="medium")

        with left_col:
            with st.container(key="dashboard_preview_todos"):
                _render_preview_card_shell(
                    icon="✅",
                    title="My To-Do",
                    body_html=_todo_preview_html(todo_rows),
                    view_key="ips_dash_preview_todos_all",
                    on_view_all=lambda: _nav_slug("tasks"),
                )

            with st.container(key="dashboard_preview_qr"):
                _render_preview_card_shell(
                    icon="📱",
                    title="Recent QR Scans",
                    body_html=_qr_preview_html(qr_rows),
                    view_key="ips_dash_preview_qr_all",
                    on_view_all=lambda: _nav_slug("inventory"),
                )

        with right_col:
            with st.container(key="dashboard_preview_analytics"):
                _render_analytics_reports_card()

