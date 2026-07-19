"""Conditional Task detail tabs (no st.tabs)."""

from __future__ import annotations

import html
from typing import Any, Callable

import streamlit as st

from app.components.record_modal import detail_field_html, dialog_card_html, placeholder_html, status_pill_html
from app.utils.formatting import fmt_date

_TASK_TABS = ("Overview", "Linked Records", "Assignment", "Notes", "Activity")
_TASK_DETAIL_ACTIVE_TAB_KEY = "ips_task_detail_active_tab"


def task_detail_active_tab_key(task_id: str) -> str:
    return f"{_TASK_DETAIL_ACTIVE_TAB_KEY}_{task_id}"


def render_task_detail_tabs(
    task: dict[str, Any],
    *,
    active_tab: str | None = None,
    on_tab_change: Callable[[str], None] | None = None,
) -> None:
    from app.perf_debug import perf_span

    tid = str(task.get("id") or "")
    tab_key = task_detail_active_tab_key(tid)
    current = str(active_tab or st.session_state.get(tab_key) or "Overview")
    if current not in _TASK_TABS:
        current = "Overview"

    cols = st.columns(len(_TASK_TABS), gap="small")
    for col, tab in zip(cols, _TASK_TABS):
        with col:
            if st.button(tab, key=f"task_tab_{tid}_{tab}", use_container_width=True):
                st.session_state[tab_key] = tab
                if on_tab_change:
                    on_tab_change(tab)
                st.rerun()

    title = str(task.get("title") or "—")
    status = str(task.get("status") or "Open")
    priority = str(task.get("priority") or "Medium")
    assignee = str(task.get("assignee_label") or task.get("assigned_to_display") or "Unassigned")
    linked_job = str(task.get("job_label") or task.get("job_display") or "—")
    linked_est = str(task.get("linked_estimate") or "— None —")
    due = fmt_date(task.get("due_date"))
    description = str(task.get("description") or "No description.")
    notes_text = str(task.get("notes") or "No notes entered.")

    if current == "Overview":
        with perf_span("tasks.detail.overview"):
            overview_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Title', title)}"
                f'{detail_field_html("Status", status, html_value=status_pill_html(status))}'
                f"{detail_field_html('Priority', priority)}"
                f"{detail_field_html('Due Date', due)}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Overview", overview_html), unsafe_allow_html=True)
            desc_html = (
                f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
                f"{html.escape(description)}</p>"
            )
            st.markdown(dialog_card_html("Description", desc_html), unsafe_allow_html=True)
    elif current == "Linked Records":
        with perf_span("tasks.detail.linked"):
            linked_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Linked Job', linked_job)}"
                f"{detail_field_html('Linked Estimate', linked_est)}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Linked Records", linked_html), unsafe_allow_html=True)
    elif current == "Assignment":
        with perf_span("tasks.detail.assignment"):
            assign_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Assigned To', assignee)}"
                f"{detail_field_html('Due Date', due)}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Assignment", assign_html), unsafe_allow_html=True)
    elif current == "Notes":
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)
    elif current == "Activity":
        with perf_span("tasks.detail.activity"):
            from app.services.task_activity_service import list_task_activity

            activity_page = list_task_activity(tid, page=1, page_size=25)
            if not activity_page.rows:
                placeholder_html("No activity recorded yet.")
            else:
                for act in activity_page.rows:
                    st.markdown(
                        f'<p class="ips-activity-item"><strong>{html.escape(str(act.get("who") or ""))}</strong> '
                        f"· {html.escape(str(act.get('when') or ''))}<br>{html.escape(str(act.get('note') or ''))}</p>",
                        unsafe_allow_html=True,
                    )
            st.caption("Activity notes are read-only until persistent activity storage is connected.")


__all__ = ["render_task_detail_tabs", "task_detail_active_tab_key"]
