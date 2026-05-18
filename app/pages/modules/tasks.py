"""Tasks / To-Do module (Phase 2D)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.layout import render_selected_detail_panel
    from app.components.status import status_pill_html
    from app.components.tables import render_data_table
    from app.components.tabs import render_tabs
    from app.pages.modules._data import (
        get_task,
        load_tasks,
        task_assignee_options,
        task_estimate_options,
        task_job_options,
    )
    from app.pages.modules._session import select_key, tab_key
    from app.styles import inject_global_css
    from app.utils.constants import TASK_PRIORITIES, TASK_STATUSES
    from app.utils.formatting import fmt_date
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.layout import render_selected_detail_panel  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._data import (  # type: ignore
        get_task,
        load_tasks,
        task_assignee_options,
        task_estimate_options,
        task_job_options,
    )
    from pages.modules._session import select_key, tab_key  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.constants import TASK_PRIORITIES, TASK_STATUSES  # type: ignore
    from utils.formatting import fmt_date  # type: ignore

_SEL = select_key("tasks")
_TAB = tab_key("tasks")


def _filter_tasks(rows: list[dict], *, q: str, status: str, priority: str, assignee: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [t for t in out if ql in str(t.get("title", "")).lower() or ql in str(t.get("description", "")).lower()]
    if status and status != "All Statuses":
        out = [t for t in out if str(t.get("status", "")) == status]
    if priority and priority != "All Priorities":
        out = [t for t in out if str(t.get("priority", "")) == priority]
    if assignee and assignee != "All Assignees":
        out = [t for t in out if str(t.get("assigned_to", "")) == assignee]
    return out


def _render_detail(task: dict) -> None:
    tid = str(task.get("id") or "")
    title = str(task.get("title") or "Task")

    def _tabs() -> None:
        render_tabs(["Details", "Activity & Notes"], session_key=_TAB, default="Details")

    def _body() -> None:
        tab = str(st.session_state.get(_TAB) or "Details")
        ot = "d" + "iv"
        st.markdown(
            f'<{ot} class="ips-detail-meta-row">'
            f"<span>Status<br>{status_pill_html(str(task.get('status') or ''))}</span>"
            f"<span>Priority<br><strong>{html.escape(str(task.get('priority') or '—'))}</strong></span>"
            f"<span>Due<br><strong>{html.escape(fmt_date(task.get('due_date')))}</strong></span>"
            f"</{ot}>",
            unsafe_allow_html=True,
        )
        if tab == "Details":
            c1, c2 = st.columns(2)
            with c1:
                st_val = str(task.get("status") or "Open")
                st_idx = list(TASK_STATUSES).index(st_val) if st_val in TASK_STATUSES else 0
                st.selectbox("Status", TASK_STATUSES, index=st_idx, key=f"task_status_{tid}")
                pr_val = str(task.get("priority") or "Medium")
                pr_idx = list(TASK_PRIORITIES).index(pr_val) if pr_val in TASK_PRIORITIES else 1
                st.selectbox("Priority", TASK_PRIORITIES, index=pr_idx, key=f"task_pri_{tid}")
                st.selectbox("Assigned to", task_assignee_options(), key=f"task_assign_{tid}")
            with c2:
                st.selectbox("Linked job", task_job_options(), key=f"task_job_{tid}")
                st.selectbox("Linked estimate", task_estimate_options(), key=f"task_est_{tid}")
            st.markdown("**Description**")
            st.caption(str(task.get("description") or ""))
            if st.button("Save Changes", key=f"task_save_{tid}", type="primary"):
                try:
                    from app.pages.modules._data import persist_task
                except ImportError:
                    from pages.modules._data import persist_task  # type: ignore
                ui = {
                    "title": task.get("title"),
                    "description": task.get("description"),
                    "status": st.session_state.get(f"task_status_{tid}"),
                    "priority": st.session_state.get(f"task_pri_{tid}"),
                    "assigned_to": st.session_state.get(f"task_assign_{tid}"),
                    "linked_job": st.session_state.get(f"task_job_{tid}"),
                    "linked_estimate": st.session_state.get(f"task_est_{tid}"),
                    "due_date": task.get("due_date"),
                }
                ok, msg = persist_task(ui, row_id=tid if not str(tid).startswith("task") else None)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            return

        st.markdown("**Activity**")
        for act in task.get("activity") or []:
            st.markdown(
                f'<p class="ips-activity-item"><strong>{html.escape(str(act.get("who") or ""))}</strong> '
                f"· {html.escape(str(act.get('when') or ''))}<br>{html.escape(str(act.get('note') or ''))}</p>",
                unsafe_allow_html=True,
            )
        st.text_area("Add note", key=f"task_note_{tid}", placeholder="Add a note…")
        if st.button("Add Note", key=f"task_add_note_{tid}"):
            st.success("Note added (demo).")

    render_selected_detail_panel(title, tabs_fn=_tabs, body_fn=_body)


def render() -> None:
    inject_global_css()
    all_tasks = load_tasks()
    assignees = sorted({str(t.get("assigned_to") or "") for t in all_tasks if t.get("assigned_to")})

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Tasks", "Track to-dos, assignments, and linked jobs or estimates.")
    with act_r:
        if st.button("+ New Task", key="task_new", type="primary", use_container_width=True):
            st.session_state["ips_task_form"] = True

    def _filters() -> None:
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            st.text_input("Search", placeholder="Search tasks…", key="task_search", label_visibility="collapsed")
        with c2:
            st.selectbox("Status", ["All Statuses", *TASK_STATUSES], key="task_filter_status", label_visibility="collapsed")
        with c3:
            st.selectbox("Priority", ["All Priorities", *TASK_PRIORITIES], key="task_filter_priority", label_visibility="collapsed")
        with c4:
            st.selectbox("Assigned to", ["All Assignees", *assignees], key="task_filter_assignee", label_visibility="collapsed")

    layout_filter_bar(_filters)

    if st.session_state.get("ips_task_form"):
        with st.expander("New task", expanded=True):
            st.text_input("Title", key="task_new_title")
            nc1, nc2 = st.columns(2)
            with nc1:
                st.selectbox("Status", TASK_STATUSES, key="task_new_status")
                st.selectbox("Priority", TASK_PRIORITIES, key="task_new_priority")
            with nc2:
                st.selectbox("Assigned to", task_assignee_options(), key="task_new_assignee")
                st.date_input("Due date", key="task_new_due")
            st.selectbox("Linked job", task_job_options(), key="task_new_job")
            st.selectbox("Linked estimate", task_estimate_options(), key="task_new_est")
            st.text_area("Description", key="task_new_desc")
            if st.button("Create Task", key="task_create", type="primary"):
                try:
                    from app.pages.modules._data import persist_task
                except ImportError:
                    from pages.modules._data import persist_task  # type: ignore
                ui = {
                    "title": st.session_state.get("task_new_title"),
                    "description": st.session_state.get("task_new_desc"),
                    "status": st.session_state.get("task_new_status"),
                    "priority": st.session_state.get("task_new_priority"),
                    "assigned_to": st.session_state.get("task_new_assignee"),
                    "linked_job": st.session_state.get("task_new_job"),
                    "linked_estimate": st.session_state.get("task_new_est"),
                    "due_date": st.session_state.get("task_new_due"),
                }
                ok, msg = persist_task(ui)
                if ok:
                    st.success(msg)
                    st.session_state["ips_task_form"] = False
                    st.rerun()
                else:
                    st.error(msg)

    filtered = _filter_tasks(
        all_tasks,
        q=str(st.session_state.get("task_search") or ""),
        status=str(st.session_state.get("task_filter_status") or "All Statuses"),
        priority=str(st.session_state.get("task_filter_priority") or "All Priorities"),
        assignee=str(st.session_state.get("task_filter_assignee") or "All Assignees"),
    )

    selected_id = str(st.session_state.get(_SEL) or "")

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "priority":
            pri = str(row.get("priority") or "")
            cls = "ips-status-danger" if pri == "Urgent" else "ips-status-pending" if pri == "High" else "ips-status-draft"
            return f'<span class="ips-status-pill {cls}">{html.escape(pri)}</span>'
        return html.escape(str(row.get(field) or "—"))

    sel = render_data_table(
        filtered,
        [
            ("title", "TASK"),
            ("status", "STATUS"),
            ("priority", "PRIORITY"),
            ("assigned_to", "ASSIGNED TO"),
            ("linked_job", "JOB"),
            ("due_date", "DUE"),
        ],
        row_id_key="id",
        selected_id=selected_id or None,
        session_select_key=_SEL,
        col_fr=["1.5fr", "0.8fr", "0.75fr", "1fr", "1.2fr", "0.75fr"],
        cell_renderer=_cell,
    )

    if sel:
        task = get_task(sel) or next((t for t in filtered if str(t.get("id")) == sel), None)
        if task:
            _render_detail(task)
