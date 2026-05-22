"""Tasks / To-Do module (Phase 2D)."""

from __future__ import annotations

import html
import re

import pandas as pd
import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.record_modal import (
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_missing_record,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_view_mode,
        show_modal_if_pending,
        status_pill_html,
    )
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._data import (
        load_employees,
        load_jobs,
        load_tasks,
        lookup_options,
        persist_task,
        task_assignee_options,
        task_estimate_options,
        task_job_options,
    )
    from app.pages._core._session import select_key
    from app.services.repository import user_facing_error
    from app.services.task_display_helpers import (
        display_to_priority,
        display_to_status,
        normalize_task_priority,
        normalize_task_status,
        priority_to_db,
        priority_to_display,
        status_to_db,
        status_to_display,
    )
    from app.services.tasks_service import update_task
    from app.styles import inject_tasks_module_css
    from app.utils.formatting import fmt_date
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_missing_record,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_view_mode,
        show_modal_if_pending,
        status_pill_html,
    )
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._data import (  # type: ignore
        load_employees,
        load_jobs,
        load_tasks,
        lookup_options,
        persist_task,
        task_assignee_options,
        task_estimate_options,
        task_job_options,
    )
    from pages._core._session import select_key  # type: ignore
    from services.repository import user_facing_error  # type: ignore
    from services.task_display_helpers import (  # type: ignore
        display_to_priority,
        display_to_status,
        normalize_task_priority,
        normalize_task_status,
        priority_to_db,
        priority_to_display,
        status_to_db,
        status_to_display,
    )
    from services.tasks_service import update_task  # type: ignore
    from styles import inject_tasks_module_css  # type: ignore
    from utils.formatting import fmt_date  # type: ignore

_SEL = select_key("tasks")
_TABLE_KEY = "tasks_list"
MODULE = "tasks"
MODAL_KEY = "ips_tasks_detail_modal_id"
CACHE_KEY = "_ips_tasks_modal_by_id"
_EDITOR_SNAPSHOT_KEY = "_ips_tasks_editor_snapshot"
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_TASK_TABS = [
    "Overview",
    "Linked Records",
    "Assignment",
    "Notes",
    "Activity",
]

_STATUS_FILTER_OPTS = ["All Statuses", "Open", "Closed"]
_PRIORITY_FILTER_OPTS = ["All Priorities", "High", "Medium", "Low"]


def _build_assignee_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for emp in load_employees():
        eid = str(emp.get("id") or "").strip()
        name = str(emp.get("name") or "").strip()
        if eid and name:
            lookup[eid] = name
    try:
        from app.services.users_service import list_profiles
    except ImportError:
        from services.users_service import list_profiles  # type: ignore
    try:
        for profile in list_profiles():
            pid = str(profile.get("id") or "").strip()
            name = str(profile.get("full_name") or profile.get("name") or "").strip()
            if pid and name:
                lookup.setdefault(pid, name)
    except Exception:
        pass
    return lookup


def _resolve_assignee_name(value: object, lookup: dict[str, str]) -> str:
    raw = str(value or "").strip()
    if not raw or raw in {"—", "— Unassigned —"}:
        return "—"
    if raw in lookup:
        return lookup[raw]
    if _UUID_RE.match(raw):
        return lookup.get(raw, "—")
    return raw


def _build_jobs_lookup() -> dict[str, dict]:
    return {str(j.get("id") or "").strip(): j for j in load_jobs() if j.get("id")}


def _format_job_label(task: dict, jobs_by_id: dict[str, dict]) -> str:
    raw = str(task.get("linked_job") or task.get("job_label") or "").strip()
    if raw and raw not in {"— None —", "None", "—", "-"}:
        if not _UUID_RE.match(raw):
            return raw
    job_id = str(task.get("job_id") or "").strip()
    if job_id and job_id in jobs_by_id:
        job = jobs_by_id[job_id]
        num = str(job.get("job_number") or "").strip()
        name = str(job.get("job_name") or "").strip()
        if num and name:
            return f"{num} — {name}"
        if num:
            return num
    if raw and not _UUID_RE.match(raw):
        return raw
    return "—"


def _filter_tasks(
    rows: list[dict],
    *,
    q: str,
    status: str,
    priority: str,
    assignee: str,
    assignee_lookup: dict[str, str],
    jobs_by_id: dict[str, dict],
) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            t
            for t in out
            if ql in str(t.get("title", "")).lower()
            or ql in str(t.get("description", "")).lower()
            or ql in _format_job_label(t, jobs_by_id).lower()
        ]
    if status and status != "All Statuses":
        out = [t for t in out if normalize_task_status(t.get("status")) == status]
    if priority and priority != "All Priorities":
        out = [t for t in out if normalize_task_priority(t.get("priority")) == priority]
    if assignee and assignee != "All Assignees":
        out = [
            t
            for t in out
            if _resolve_assignee_name(t.get("assigned_to"), assignee_lookup) == assignee
        ]
    return out


def _tasks_to_editor_df(
    tasks: list[dict],
    *,
    assignee_lookup: dict[str, str],
    jobs_by_id: dict[str, dict],
) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for task in tasks:
        due = fmt_date(task.get("due_date"))
        rows.append(
            {
                "_id": str(task.get("id") or ""),
                "Task": str(task.get("title") or ""),
                "Status": status_to_display(task.get("status")),
                "Priority": priority_to_display(task.get("priority")),
                "Assigned To": _resolve_assignee_name(task.get("assigned_to"), assignee_lookup),
                "Job": _format_job_label(task, jobs_by_id),
                "Due": due if due != "—" else "—",
            }
        )
    return pd.DataFrame(rows)


def _tasks_editor_column_config() -> dict:
    return {
        "_id": None,
        "Task": st.column_config.TextColumn("TASK", width="large", disabled=True),
        "Status": st.column_config.SelectboxColumn(
            "STATUS",
            options=["🔵 Open", "✅ Closed"],
            width="small",
            required=True,
        ),
        "Priority": st.column_config.SelectboxColumn(
            "PRIORITY",
            options=["🔴 High", "🟠 Medium", "🟢 Low"],
            width="small",
            required=True,
        ),
        "Assigned To": st.column_config.TextColumn("ASSIGNED TO", width="medium", disabled=True),
        "Job": st.column_config.TextColumn("JOB", width="medium", disabled=True),
        "Due": st.column_config.TextColumn("DUE", width="small", disabled=True),
    }


def _apply_inline_task_edits(edited: pd.DataFrame, previous: pd.DataFrame) -> bool:
    if edited.empty or len(edited) != len(previous):
        return False

    saved = False
    for idx in range(len(edited)):
        task_id = str(edited.iloc[idx]["_id"] or "").strip()
        if not task_id or is_demo_id(task_id):
            continue

        update_data: dict[str, str] = {}
        new_status = display_to_status(edited.iloc[idx]["Status"])
        old_status = display_to_status(previous.iloc[idx]["Status"])
        new_priority = display_to_priority(edited.iloc[idx]["Priority"])
        old_priority = display_to_priority(previous.iloc[idx]["Priority"])

        if new_status != old_status:
            update_data["status"] = new_status
        if new_priority != old_priority:
            update_data["priority"] = new_priority
        if not update_data:
            continue

        result = update_task(task_id, update_data)
        err = user_facing_error(result)
        if err:
            st.error(err)
            return False
        saved = True

    return saved


def _clear_task_modal() -> None:
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=MODAL_KEY,
        module=MODULE,
    )


def _open_task_modal(task_id: str, task: dict | None = None) -> None:
    open_record_modal(
        task_id,
        task,
        session_select_key=_SEL,
        modal_key=MODAL_KEY,
        module=MODULE,
        id_fields=("id", "title"),
    )


def _as_date(value: object):
    from datetime import date

    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _assignee_options(task: dict) -> list[str]:
    opts = ["— Unassigned —", *task_assignee_options()]
    cur = str(task.get("assigned_to") or "").strip()
    if cur and cur not in opts:
        opts = [cur, *opts]
    return opts


def _job_options(task: dict) -> list[str]:
    opts = task_job_options()
    cur = str(task.get("linked_job") or "").strip()
    if cur and cur not in opts:
        opts = [cur, *opts]
    return opts


def _estimate_options(task: dict) -> list[str]:
    opts = task_estimate_options()
    cur = str(task.get("linked_estimate") or "").strip()
    if cur and cur not in opts:
        opts = [cur, *opts]
    return opts


def _seed_task_edit_form(task: dict) -> None:
    rk = record_session_key(task, "id")
    statuses = lookup_options("task_statuses") or ["Open"]
    priorities = lookup_options("task_priorities") or ["Medium"]
    status = str(task.get("status") or statuses[0])
    priority = str(task.get("priority") or priorities[0])
    st.session_state[f"task_edit_status_{rk}"] = status if status in statuses else statuses[0]
    st.session_state[f"task_edit_pri_{rk}"] = priority if priority in priorities else priorities[0]
    assignee = str(task.get("assigned_to") or "").strip()
    assign_opts = _assignee_options(task)
    st.session_state[f"task_edit_assign_{rk}"] = assignee if assignee in assign_opts else assign_opts[0]
    job = str(task.get("linked_job") or "").strip()
    job_opts = _job_options(task)
    st.session_state[f"task_edit_job_{rk}"] = job if job in job_opts else job_opts[0]
    est = str(task.get("linked_estimate") or "").strip()
    est_opts = _estimate_options(task)
    st.session_state[f"task_edit_est_{rk}"] = est if est in est_opts else est_opts[0]
    st.session_state[f"task_edit_due_{rk}"] = _as_date(task.get("due_date"))
    st.session_state[f"task_edit_desc_{rk}"] = str(task.get("description") or "")


def _render_task_detail_tabs(task: dict, assignee_lookup: dict[str, str], jobs_by_id: dict[str, dict]) -> None:
    tid = str(task.get("id") or "")
    title = safe_value(task.get("title"))
    status = normalize_task_status(task.get("status"))
    priority = normalize_task_priority(task.get("priority"))
    assignee = _resolve_assignee_name(task.get("assigned_to"), assignee_lookup)
    if assignee == "—":
        assignee = "Unassigned"
    linked_job = _format_job_label(task, jobs_by_id)
    linked_est = safe_value(task.get("linked_estimate"))
    due = fmt_date(task.get("due_date"))
    description = safe_value(task.get("description"), "No description.")

    (
        tab_overview,
        tab_linked,
        tab_assignment,
        tab_notes,
        tab_activity,
    ) = st.tabs(_TASK_TABS)

    with tab_overview:
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
            f"{html.escape(description)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Description", desc_html), unsafe_allow_html=True)

    with tab_linked:
        linked_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Linked Job', linked_job)}"
            f"{detail_field_html('Linked Estimate', linked_est)}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Linked Records", linked_html), unsafe_allow_html=True)

    with tab_assignment:
        assign_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Assigned To', assignee)}"
            f"{detail_field_html('Due Date', due)}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Assignment", assign_html), unsafe_allow_html=True)

    with tab_notes:
        notes_text = safe_value(task.get("notes"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        activity = list(task.get("activity") or [])
        if not activity:
            placeholder_html("No activity yet.")
        else:
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


def _render_task_edit_form(task: dict) -> None:
    rk = record_session_key(task, "id")
    tid = str(task.get("id") or "")
    if f"task_edit_status_{rk}" not in st.session_state:
        _seed_task_edit_form(task)

    render_edit_form_header("Edit Task")
    if is_demo_id(tid):
        st.caption("Demo records cannot be saved to the database.")

    statuses = lookup_options("task_statuses") or ["Open"]
    priorities = lookup_options("task_priorities") or ["Medium"]

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.selectbox("Status", statuses, key=f"task_edit_status_{rk}")
        st.selectbox("Priority", priorities, key=f"task_edit_pri_{rk}")
        st.selectbox("Assigned to", _assignee_options(task), key=f"task_edit_assign_{rk}")
    with c2:
        st.selectbox("Linked job", _job_options(task), key=f"task_edit_job_{rk}")
        st.selectbox("Linked estimate", _estimate_options(task), key=f"task_edit_est_{rk}")
        st.date_input("Due date", key=f"task_edit_due_{rk}")

    st.text_area("Description", key=f"task_edit_desc_{rk}", height=100)

    cancelled, saved = render_save_cancel_actions(
        module=MODULE,
        record_key=rk,
        cancel_key=f"task_modal_cancel_{rk}",
        save_key=f"task_modal_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved:
        assignee = st.session_state.get(f"task_edit_assign_{rk}")
        if assignee == "— Unassigned —":
            assignee = ""
        ui = {
            "title": task.get("title"),
            "description": st.session_state.get(f"task_edit_desc_{rk}"),
            "status": st.session_state.get(f"task_edit_status_{rk}"),
            "priority": st.session_state.get(f"task_edit_pri_{rk}"),
            "assigned_to": assignee,
            "linked_job": st.session_state.get(f"task_edit_job_{rk}"),
            "linked_estimate": st.session_state.get(f"task_edit_est_{rk}"),
            "due_date": st.session_state.get(f"task_edit_due_{rk}"),
        }
        row_id = None if is_demo_id(tid) else tid
        ok, msg = persist_task(ui, row_id=row_id)
        if ok:
            set_view_mode(MODULE, rk)
            st.success(msg or "Task saved.")
            st.rerun()
        st.error(msg or "Could not save task.")


def render_task_detail_dialog(
    task: dict,
    *,
    assignee_lookup: dict[str, str],
    jobs_by_id: dict[str, dict],
) -> None:
    rk = record_session_key(task, "id", "title")
    title = safe_value(task.get("title"))
    status = normalize_task_status(task.get("status"))
    priority = normalize_task_priority(task.get("priority"))
    assignee = _resolve_assignee_name(task.get("assigned_to"), assignee_lookup)
    if assignee == "—":
        assignee = "Unassigned"
    due = fmt_date(task.get("due_date"))

    render_modal_shell()
    render_modal_header(
        title=title,
        subtitle=f"{priority} priority · due {due}",
        status=status,
    )
    render_modal_edit_button(
        module=MODULE,
        record_key=rk,
        key_prefix=f"task_modal_{rk}",
    )
    render_modal_meta_grid(
        [
            ("Status", status),
            ("Priority", priority),
            ("Assigned To", assignee),
            ("Due", due),
        ]
    )

    if is_edit_mode(MODULE, rk):
        _render_task_edit_form(task)
    else:
        _render_task_detail_tabs(task, assignee_lookup, jobs_by_id)


@st.dialog("Task Details", width="large", on_dismiss=_clear_task_modal)
def _show_task_modal(assignee_lookup: dict[str, str], jobs_by_id: dict[str, dict]) -> None:
    task = get_modal_record(
        cache_key=CACHE_KEY,
        modal_key=MODAL_KEY,
        session_select_key=_SEL,
    )
    if not task:
        render_missing_record(_clear_task_modal, close_key="task_modal_missing_close")
        return
    render_task_detail_dialog(task, assignee_lookup=assignee_lookup, jobs_by_id=jobs_by_id)


def _render_tasks_editor(filtered: list[dict], assignee_lookup: dict[str, str], jobs_by_id: dict[str, dict]) -> None:
    df = _tasks_to_editor_df(filtered, assignee_lookup=assignee_lookup, jobs_by_id=jobs_by_id)
    if df.empty:
        st.info("No tasks match your filters.")
        st.session_state.pop(_EDITOR_SNAPSHOT_KEY, None)
        return

    snapshot_key = f"{_EDITOR_SNAPSHOT_KEY}_{len(filtered)}"
    previous = st.session_state.get(snapshot_key)
    if previous is None or len(previous) != len(df):
        st.session_state[snapshot_key] = df.copy()

    st.markdown('<div class="ips-tasks-editor ips-tasks-table">', unsafe_allow_html=True)
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        column_config=_tasks_editor_column_config(),
        num_rows="fixed",
        key="tasks_editor",
        disabled=["Task", "Assigned To", "Job", "Due"],
    )
    st.markdown("</div>", unsafe_allow_html=True)

    previous_df = st.session_state.get(snapshot_key)
    if previous_df is not None and not edited.equals(previous_df):
        if _apply_inline_task_edits(edited, previous_df):
            st.session_state[snapshot_key] = edited.copy()
            st.success("Task updated.")
            st.rerun()
        st.session_state[snapshot_key] = edited.copy()


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("tasks"):
        return

    inject_tasks_module_css()
    st.markdown('<span class="ips-tasks-page ips-page-shell-marker" aria-hidden="true"></span>', unsafe_allow_html=True)

    assignee_lookup = _build_assignee_lookup()
    jobs_by_id = _build_jobs_lookup()
    all_tasks = load_tasks()
    assignees = sorted(
        {
            name
            for t in all_tasks
            if (name := _resolve_assignee_name(t.get("assigned_to"), assignee_lookup)) != "—"
        }
    )

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
            st.selectbox(
                "Status",
                _STATUS_FILTER_OPTS,
                key="task_filter_status",
                label_visibility="collapsed",
            )
        with c3:
            st.selectbox(
                "Priority",
                _PRIORITY_FILTER_OPTS,
                key="task_filter_priority",
                label_visibility="collapsed",
            )
        with c4:
            st.selectbox(
                "Assigned to",
                ["All Assignees", *assignees],
                key="task_filter_assignee",
                label_visibility="collapsed",
            )
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
                st.selectbox("Status", _STATUS_FILTER_OPTS[1:], key="task_new_status")
                st.selectbox("Priority", _PRIORITY_FILTER_OPTS[1:], key="task_new_priority")
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
                    "status": status_to_db(st.session_state.get("task_new_status")),
                    "priority": priority_to_db(st.session_state.get("task_new_priority")),
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
        assignee_lookup=assignee_lookup,
        jobs_by_id=jobs_by_id,
    )

    st.caption(f"{len(filtered)} task(s) · edit Status or Priority inline")

    build_modal_cache(filtered, cache_key=CACHE_KEY)
    _render_tasks_editor(filtered, assignee_lookup, jobs_by_id)

    if filtered:
        task_labels = {
            str(t.get("title") or "Untitled"): t for t in filtered if t.get("title")
        }
        detail_col1, detail_col2 = st.columns([3, 1])
        with detail_col1:
            picked = st.selectbox(
                "Open task details",
                options=[""] + list(task_labels.keys()),
                key="task_detail_picker",
                label_visibility="collapsed",
                placeholder="Open task details…",
            )
        with detail_col2:
            if st.button("View", key="task_open_detail", use_container_width=True, disabled=not picked):
                task = task_labels.get(picked)
                if task:
                    _open_task_modal(str(task.get("id")), task)

    show_modal_if_pending(
        MODAL_KEY,
        lambda: _show_task_modal(assignee_lookup, jobs_by_id),
    )
