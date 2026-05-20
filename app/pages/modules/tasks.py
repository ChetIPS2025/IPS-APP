"""Tasks / To-Do module (Phase 2D)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.modals import render_record_detail_dialog
    from app.components.status import status_pill_html
    from app.components.tables import render_clickable_table, render_data_table
    from app.components.tabs import render_tabs
    from app.pages.modules._crud import apply_persist_feedback, is_demo_id
    from app.pages.modules._data import (
        get_task,
        load_tasks,
        lookup_options,
        persist_task,
        task_assignee_options,
        task_estimate_options,
        task_job_options,
    )
    from app.pages.modules._session import select_key, tab_key
    from app.utils.formatting import fmt_date
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.modals import render_record_detail_dialog  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_clickable_table, render_data_table  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages.modules._data import (  # type: ignore
        get_task,
        load_tasks,
        lookup_options,
        persist_task,
        task_assignee_options,
        task_estimate_options,
        task_job_options,
    )
    from pages.modules._session import select_key, tab_key  # type: ignore
    from utils.formatting import fmt_date  # type: ignore

_SEL = select_key("tasks")
_TAB = tab_key("tasks")


def _filter_tasks(rows: list[dict], *, q: str, status: str, priority: str, assignee: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            t
            for t in out
            if ql in str(t.get("title", "")).lower()
            or ql in str(t.get("description", "")).lower()
            or ql in str(t.get("linked_job", "")).lower()
        ]
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
    statuses = lookup_options("task_statuses")
    priorities = lookup_options("task_priorities")

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
                st_val = str(task.get("status") or statuses[0] if statuses else "Open")
                st.selectbox(
                    "Status",
                    statuses,
                    index=statuses.index(st_val) if st_val in statuses else 0,
                    key=f"task_status_{tid}",
                )
                pr_val = str(task.get("priority") or priorities[0] if priorities else "Medium")
                st.selectbox(
                    "Priority",
                    priorities,
                    index=priorities.index(pr_val) if pr_val in priorities else 0,
                    key=f"task_pri_{tid}",
                )
                st.selectbox("Assigned to", ["— Unassigned —", *task_assignee_options()], key=f"task_assign_{tid}")
            with c2:
                st.selectbox("Linked job", task_job_options(), key=f"task_job_{tid}")
                st.selectbox("Linked estimate", task_estimate_options(), key=f"task_est_{tid}")
                st.date_input("Due date", value=task.get("due_date") or None, key=f"task_due_{tid}")
            st.text_area("Description", value=str(task.get("description") or ""), key=f"task_desc_{tid}", height=100)
            if st.button("Save Changes", key=f"task_save_{tid}", type="primary"):
                assignee = st.session_state.get(f"task_assign_{tid}")
                if assignee == "— Unassigned —":
                    assignee = ""
                ui = {
                    "title": task.get("title"),
                    "description": st.session_state.get(f"task_desc_{tid}"),
                    "status": st.session_state.get(f"task_status_{tid}"),
                    "priority": st.session_state.get(f"task_pri_{tid}"),
                    "assigned_to": assignee,
                    "linked_job": st.session_state.get(f"task_job_{tid}"),
                    "linked_estimate": st.session_state.get(f"task_est_{tid}"),
                    "due_date": st.session_state.get(f"task_due_{tid}"),
                }
                row_id = None if is_demo_id(tid) else tid
                ok, msg = persist_task(ui, row_id=row_id)
                apply_persist_feedback(ok, msg)
                if ok:
                    st.rerun()
            return

        st.markdown("**Activity**")
        activity = list(task.get("activity") or [])
        for act in activity:
            st.markdown(
                f'<p class="ips-activity-item"><strong>{html.escape(str(act.get("who") or ""))}</strong> '
                f"· {html.escape(str(act.get('when') or ''))}<br>{html.escape(str(act.get('note') or ''))}</p>",
                unsafe_allow_html=True,
            )
        note_key = f"task_note_{tid}"
        st.text_area("Add note", key=note_key, placeholder="Add a note…")
        if st.button("Add Note", key=f"task_add_note_{tid}"):
            note = str(st.session_state.get(note_key) or "").strip()
            if note:
                activity.append({"when": "Just now", "who": "You", "note": note})
                task["activity"] = activity
                st.session_state[note_key] = ""
                st.success("Note added to activity (session).")
                st.rerun()

    render_record_detail_dialog(
        f"{title} — Task Details",
        module_name="tasks",
        session_select_key=_SEL,
        tabs_fn=_tabs,
        body_fn=_body,
    )


def render() -> None:
    try:
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
    if not begin_module("tasks"):
        return
    all_tasks = load_tasks()
    assignees = sorted({str(t.get("assigned_to") or "") for t in all_tasks if t.get("assigned_to")})
    statuses = lookup_options("task_statuses")
    priorities = lookup_options("task_priorities")

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Tasks", "Track to-dos, assignments, and linked jobs or estimates.")
    with act_r:
        if st.button("+ New Task", key="task_new", type="primary", use_container_width=True):
            st.session_state["ips_task_form"] = True

    def _filters() -> None:
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 0.6])
        with c1:
            st.text_input("Search", placeholder="Search tasks…", key="task_search", label_visibility="collapsed")
        with c2:
            st.selectbox("Status", ["All Statuses", *statuses], key="task_filter_status", label_visibility="collapsed")
        with c3:
            st.selectbox("Priority", ["All Priorities", *priorities], key="task_filter_priority", label_visibility="collapsed")
        with c4:
            st.selectbox("Assigned to", ["All Assignees", *assignees], key="task_filter_assignee", label_visibility="collapsed")
        with c5:
            if st.button("Clear", key="task_clear", use_container_width=True):
                st.session_state["task_search"] = ""
                st.session_state["task_filter_status"] = "All Statuses"
                st.session_state["task_filter_priority"] = "All Priorities"
                st.session_state["task_filter_assignee"] = "All Assignees"
                st.rerun()

    layout_filter_bar(_filters)

    if st.session_state.get("ips_task_form"):
        with st.expander("New task", expanded=True):
            st.text_input("Title", key="task_new_title")
            nc1, nc2 = st.columns(2)
            with nc1:
                st.selectbox("Status", statuses, key="task_new_status")
                st.selectbox("Priority", priorities, key="task_new_priority")
            with nc2:
                st.selectbox("Assigned to", ["— Unassigned —", *task_assignee_options()], key="task_new_assignee")
                st.date_input("Due date", key="task_new_due", value=None)
            st.selectbox("Linked job", task_job_options(), key="task_new_job")
            st.selectbox("Linked estimate", task_estimate_options(), key="task_new_est")
            st.text_area("Description", key="task_new_desc")
            if st.button("Create Task", key="task_create", type="primary"):
                assignee = st.session_state.get("task_new_assignee")
                if assignee == "— Unassigned —":
                    assignee = ""
                ui = {
                    "title": st.session_state.get("task_new_title"),
                    "description": st.session_state.get("task_new_desc"),
                    "status": st.session_state.get("task_new_status"),
                    "priority": st.session_state.get("task_new_priority"),
                    "assigned_to": assignee,
                    "linked_job": st.session_state.get("task_new_job"),
                    "linked_estimate": st.session_state.get("task_new_est"),
                    "due_date": st.session_state.get("task_new_due"),
                }
                ok, msg = persist_task(ui)
                if apply_persist_feedback(ok, msg, clear_keys=("ips_task_form",)):
                    st.rerun()

    filtered = _filter_tasks(
        all_tasks,
        q=str(st.session_state.get("task_search") or "").strip(),
        status=str(st.session_state.get("task_filter_status") or "All Statuses"),
        priority=str(st.session_state.get("task_filter_priority") or "All Priorities"),
        assignee=str(st.session_state.get("task_filter_assignee") or "All Assignees"),
    )

    selected_id = str(st.session_state.get(_SEL) or "")
    if selected_id and not any(str(t.get("id")) == selected_id for t in filtered):
        st.session_state.pop(_SEL, None)
        selected_id = ""

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field == "priority":
            pri = str(row.get("priority") or "")
            cls = "ips-status-danger" if pri == "Urgent" else "ips-status-pending" if pri == "High" else "ips-status-draft"
            return f'<span class="ips-status-pill {cls}">{html.escape(pri)}</span>'
        if field == "due_date":
            return html.escape(fmt_date(row.get("due_date")))
        return html.escape(str(row.get(field) or "—"))

    def _plain_cell(field: str, row: dict) -> str:
        if field == "due_date":
            return fmt_date(row.get("due_date"))
        return str(row.get(field) or "—")

    sel = render_clickable_table(
        filtered,
        [
            ("title", "TASK"),
            ("status", "STATUS"),
            ("priority", "PRIORITY"),
            ("assigned_to", "ASSIGNED TO"),
            ("linked_job", "JOB"),
            ("due_date", "DUE"),
        ],
        "tasks_list",
        row_id_key="id",
        session_select_key=_SEL,
        selected_id=selected_id or None,
        plain_cell=_plain_cell,
    )

    if sel:
        task = get_task(sel) or next((t for t in filtered if str(t.get("id")) == sel), None)
        if task:
            _render_detail(task)
