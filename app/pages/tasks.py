"""Tasks / To-Do module (Phase 2D)."""

from __future__ import annotations

import html
import re
from datetime import date

import streamlit as st

try:
    from app.components.headers import render_page_brand_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.table_filters import (
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from app.components.record_modal import (
        build_modal_cache,
        clear_record_modal,
        clear_edit_modes,
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
        status_pill_html,
    )
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._data import (
        load_employees,
        load_jobs,
        lookup_options,
        persist_task,
        task_assignee_options,
        task_estimate_options,
    )
    from app.pages._core._session import select_key
    from app.services.jobs_service import get_job_options
    from app.services.repository import user_facing_error
    from app.services.task_display_helpers import (
        normalize_task_priority,
        normalize_task_status,
        priority_to_db,
        status_to_db,
    )
    from app.services.tasks_service import (
        clear_tasks_cache,
        get_tasks,
        get_tasks_by_job,
        update_task,
    )
    from app.styles import inject_tasks_module_css
    from app.utils.field_context import (
        FIELD_EXPANDED_TASK_KEY,
        clear_field_expanded,
        field_expanded_id,
        get_field_job_id,
        inject_field_row_expand_css,
        is_field_mode,
        render_field_job_bar,
        toggle_field_expanded,
    )
    from app.utils.formatting import fmt_date
except ImportError:
    from components.headers import render_page_brand_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.table_filters import (  # type: ignore
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_record_modal,
        clear_edit_modes,
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
        status_pill_html,
    )
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._data import (  # type: ignore
        load_employees,
        load_jobs,
        lookup_options,
        persist_task,
        task_assignee_options,
        task_estimate_options,
    )
    from pages._core._session import select_key  # type: ignore
    from services.jobs_service import get_job_options  # type: ignore
    from services.repository import user_facing_error  # type: ignore
    from services.task_display_helpers import (  # type: ignore
        normalize_task_priority,
        normalize_task_status,
        priority_to_db,
        status_to_db,
    )
    from services.tasks_service import (  # type: ignore
        clear_tasks_cache,
        get_tasks,
        get_tasks_by_job,
        update_task,
    )
    from styles import inject_tasks_module_css  # type: ignore
    from utils.field_context import get_field_job_id, is_field_mode, render_field_job_bar  # type: ignore
    from utils.field_context import (  # type: ignore
        FIELD_EXPANDED_TASK_KEY,
        clear_field_expanded,
        field_expanded_id,
        inject_field_row_expand_css,
        toggle_field_expanded,
    )
    from utils.formatting import fmt_date  # type: ignore

_SEL = select_key("tasks")
_TABLE_KEY = "tasks_list"
MODULE = "tasks"
MODAL_KEY = "ips_tasks_detail_modal_id"
CACHE_KEY = "_ips_tasks_modal_by_id"
SELECTED_TASK_KEY = "selected_task_id"
SHOW_MODAL_KEY = "show_task_detail_modal"
_LOCAL_OVERRIDES_KEY = "ips_task_local_overrides"
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_ALL_TASK_IDS_KEY = "_ips_tasks_visible_ids"
_TASK_COLS = [0.35, 4.8, 1.2, 1.2, 2.0, 2.8, 1.2]
_TASK_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("TASK", None),
    ("STATUS", None),
    ("PRIORITY", "priority_display"),
    ("ASSIGNED TO", "assigned_to_display"),
    ("JOB", "job_display"),
    ("DUE", None),
]
_FILTER_FIELDS = ["priority_display", "assigned_to_display", "job_display"]
_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("priority_display", None),
    ("assigned_to_display", None),
    ("job_display", None),
]

_TASK_TABS = [
    "Overview",
    "Linked Records",
    "Assignment",
    "Notes",
    "Activity",
]

_TASK_STATUS_OPTS = ["Open", "Closed"]
_PRIORITY_FILTER_OPTS = ["All Priorities", "High", "Medium", "Low"]
TASK_VIEW_KEY = "task_view_filter"
TASK_VIEW_OPTS = ["Open Tasks", "Closed Tasks", "All Tasks"]
FIELD_TASK_VIEW_OPTS = ["Due Today", *TASK_VIEW_OPTS]
JOB_TASK_VIEW_OPTS = ["Open", "Closed", "All"]


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


def _merge_task_overrides(tasks: list[dict]) -> list[dict]:
    overrides = st.session_state.get(_LOCAL_OVERRIDES_KEY) or {}
    if not overrides:
        return tasks
    merged: list[dict] = []
    for task in tasks:
        row = dict(task)
        tid = str(row.get("id") or "").strip()
        if tid and tid in overrides:
            row.update(overrides[tid])
        merged.append(row)
    return merged


def _resolve_task_job_id(
    task: dict,
    job_options: list[dict],
    jobs_by_id: dict[str, dict],
) -> str | None:
    jid = str(task.get("job_id") or "").strip()
    if jid:
        return jid
    label = str(task.get("linked_job") or task.get("job_label") or "").strip()
    if label and label not in {"— None —", "None", "—", "-"}:
        for opt in job_options:
            if str(opt.get("label") or "") == label:
                return opt.get("id")
        for job in jobs_by_id.values():
            num = str(job.get("job_number") or "").strip()
            name = str(job.get("job_name") or "").strip()
            friendly = f"{num} — {name}" if num and name else num or name
            if friendly == label:
                return str(job.get("id") or "").strip() or None
    return None


def _format_job_label(task: dict, jobs_by_id: dict[str, dict], job_options: list[dict]) -> str:
    jid = _resolve_task_job_id(task, job_options, jobs_by_id)
    if jid:
        for opt in job_options:
            if opt.get("id") == jid:
                return str(opt.get("label") or "—")
        job = jobs_by_id.get(jid)
        if job:
            num = str(job.get("job_number") or "").strip()
            name = str(job.get("job_name") or "").strip()
            if num and name:
                return f"{num} — {name}"
            if num:
                return num
    raw = str(task.get("linked_job") or task.get("job_label") or "").strip()
    if raw and raw not in {"— None —", "None", "—", "-"} and not _UUID_RE.match(raw):
        return raw
    return "—"


def _priority_pill_html(priority: object) -> str:
    pri = normalize_task_priority(priority)
    css = {
        "High": "ips-priority-high",
        "Medium": "ips-priority-medium",
        "Low": "ips-priority-low",
    }[pri]
    return f'<span class="ips-priority-pill {css}">{html.escape(pri)}</span>'


def _field_assignee_match_keys() -> set[str]:
    try:
        from app.auth import current_profile
    except ImportError:
        from auth import current_profile  # type: ignore
    prof = current_profile() or {}
    keys: set[str] = set()
    for val in (
        prof.get("id"),
        prof.get("employee_id"),
        prof.get("email"),
        prof.get("full_name"),
        prof.get("name"),
    ):
        s = str(val or "").strip().lower()
        if s:
            keys.add(s)
    emp = st.session_state.get("auth_employee") or {}
    if isinstance(emp, dict):
        for val in (emp.get("id"), emp.get("name"), emp.get("email")):
            s = str(val or "").strip().lower()
            if s:
                keys.add(s)
    return keys


def _task_matches_field_assignee(task: dict, assignee_lookup: dict[str, str]) -> bool:
    raw = str(task.get("assigned_to") or "").strip().lower()
    if not raw or raw in {"—", "— unassigned —"}:
        return False
    keys = _field_assignee_match_keys()
    if raw in keys:
        return True
    display = _resolve_assignee_name(task.get("assigned_to"), assignee_lookup).strip().lower()
    return bool(display and display in keys)


def _apply_field_task_filters(rows: list[dict], *, assignee_lookup: dict[str, str]) -> list[dict]:
    if not is_field_mode():
        return rows
    out = list(rows)
    fid = get_field_job_id()
    if fid:
        out = [t for t in out if str(t.get("job_id") or "").strip() == fid]
    try:
        from app.auth import current_role
    except ImportError:
        from auth import current_role  # type: ignore
    if str(current_role() or "").strip().lower() == "employee":
        out = [t for t in out if _task_matches_field_assignee(t, assignee_lookup)]
    return out


def _apply_task_view_filter(rows: list[dict], view: str) -> list[dict]:
    if view == "Due Today":
        today = date.today().isoformat()
        return [
            t
            for t in rows
            if normalize_task_status(t.get("status")) == "Open"
            and str(t.get("due_date") or "")[:10] == today
        ]
    if view == "Closed Tasks":
        return [t for t in rows if normalize_task_status(t.get("status")) == "Closed"]
    if view == "Open Tasks":
        return [t for t in rows if normalize_task_status(t.get("status")) == "Open"]
    return list(rows)


def _task_count_caption(count: int, view: str) -> str:
    if view == "Due Today":
        return f"{count} task(s) due today"
    if view == "Open Tasks":
        return f"{count} open task(s)"
    if view == "Closed Tasks":
        return f"{count} closed task(s)"
    return f"{count} task(s)"


def _render_task_view_selector() -> None:
    opts = FIELD_TASK_VIEW_OPTS if is_field_mode() else TASK_VIEW_OPTS
    if TASK_VIEW_KEY not in st.session_state:
        st.session_state[TASK_VIEW_KEY] = "Due Today" if is_field_mode() else "Open Tasks"
    current = str(st.session_state.get(TASK_VIEW_KEY) or "")
    if current not in opts:
        st.session_state[TASK_VIEW_KEY] = opts[0]
    st.markdown('<div class="ips-task-view-toggle">', unsafe_allow_html=True)
    if hasattr(st, "segmented_control"):
        st.segmented_control(
            "Task view",
            opts,
            key=TASK_VIEW_KEY,
            label_visibility="collapsed",
        )
    else:
        st.radio(
            "Task view",
            opts,
            key=TASK_VIEW_KEY,
            horizontal=True,
            label_visibility="collapsed",
        )
    st.markdown("</div>", unsafe_allow_html=True)


def _enrich_task_row(
    task: dict,
    *,
    assignee_lookup: dict[str, str],
    jobs_by_id: dict[str, dict],
    job_options: list[dict],
) -> dict:
    return {
        **task,
        "priority_display": normalize_task_priority(task.get("priority")),
        "assigned_to_display": _resolve_assignee_name(task.get("assigned_to"), assignee_lookup),
        "job_display": _format_job_label(task, jobs_by_id, job_options),
    }


def _filter_tasks(
    rows: list[dict],
    *,
    q: str,
) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            t
            for t in out
            if ql in str(t.get("title", "")).lower()
            or ql in str(t.get("description", "")).lower()
            or ql in str(t.get("job_display") or "").lower()
        ]
    return apply_column_filters(out, _TABLE_KEY, _COLUMN_FILTER_SPECS)


def _apply_local_task_update(task_id: str, updates: dict) -> None:
    tid = str(task_id or "").strip()
    if not tid:
        return
    overrides = dict(st.session_state.get(_LOCAL_OVERRIDES_KEY) or {})
    patch = dict(overrides.get(tid) or {})
    patch.update(updates)
    overrides[tid] = patch
    st.session_state[_LOCAL_OVERRIDES_KEY] = overrides

    cache = dict(st.session_state.get(CACHE_KEY) or {})
    if tid in cache:
        row = dict(cache[tid])
        row.update(patch)
        if "job_id" in patch:
            row["job_id"] = patch["job_id"]
            row["linked_job"] = patch.get("job_label") or "— None —"
        cache[tid] = row
        st.session_state[CACHE_KEY] = cache


def _demo_data_active() -> bool:
    return bool(st.session_state.get("ips_showing_demo_data"))


def _should_save_locally(task_id: str) -> bool:
    return is_demo_id(task_id) or _demo_data_active()


def _save_task_field(task_id: str, update_data: dict, *, job_options: list[dict] | None = None) -> None:
    tid = str(task_id or "").strip()
    if not tid or not update_data:
        return

    payload = dict(update_data)
    if "job_id" in payload and job_options is not None:
        jid = payload.get("job_id")
        label = "— None —"
        for opt in job_options:
            if opt.get("id") == jid:
                label = str(opt.get("label") or label)
                break
        payload["job_label"] = "" if jid is None else label
        payload["linked_job"] = label

    if _should_save_locally(tid):
        local_patch = dict(payload)
        if "status" in local_patch:
            local_patch["status"] = normalize_task_status(local_patch["status"])
        if "priority" in local_patch:
            local_patch["priority"] = normalize_task_priority(local_patch["priority"])
        _apply_local_task_update(tid, local_patch)
        st.rerun()
        return

    result = update_task(tid, payload)
    err = user_facing_error(result)
    if err:
        st.error(err)
        return
    clear_tasks_cache()
    st.rerun()


def _task_select_key(task_id: str) -> str:
    return f"task_select_{task_id}"


def _clear_task_selection(task_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_TASK_KEY] = None
    st.session_state[SHOW_MODAL_KEY] = False
    ids = list(task_ids or [])
    for tid in ids:
        st.session_state[_task_select_key(tid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("task_select_"):
            st.session_state[key] = False


def _on_task_checkbox_change(task_id: str, all_task_ids: list[str]) -> None:
    key = _task_select_key(task_id)
    if st.session_state.get(key):
        for tid in all_task_ids:
            if tid != task_id:
                st.session_state[_task_select_key(tid)] = False
        st.session_state[SELECTED_TASK_KEY] = task_id
        st.session_state[SHOW_MODAL_KEY] = True
        cache = st.session_state.get(CACHE_KEY) or {}
        task = cache.get(task_id) if isinstance(cache, dict) else None
        open_record_modal(
            task_id,
            task if isinstance(task, dict) else None,
            session_select_key=_SEL,
            modal_key=MODAL_KEY,
            module=MODULE,
            id_fields=("id", "title"),
        )
    elif st.session_state.get(SELECTED_TASK_KEY) == task_id:
        st.session_state[SELECTED_TASK_KEY] = None
        st.session_state[SHOW_MODAL_KEY] = False


def _clear_task_modal() -> None:
    task_ids = st.session_state.get(_ALL_TASK_IDS_KEY) or []
    _clear_task_selection([str(tid) for tid in task_ids])
    clear_edit_modes(MODULE)
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=MODAL_KEY,
        module=MODULE,
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


def _job_label_options(task: dict, job_options: list[dict]) -> list[str]:
    labels = [str(o.get("label") or "") for o in job_options]
    cur = _format_job_label(task, _build_jobs_lookup(), job_options)
    if cur and cur not in labels and cur != "—":
        labels = [cur, *labels]
    return labels


def _estimate_options(task: dict) -> list[str]:
    opts = ["— None —"]
    try:
        from app.pages._core._data import task_estimate_options
    except ImportError:
        from pages._core._data import task_estimate_options  # type: ignore
    opts = task_estimate_options()
    cur = str(task.get("linked_estimate") or "").strip()
    if cur and cur not in opts:
        opts = [cur, *opts]
    return opts


def _seed_task_edit_form(task: dict, job_options: list[dict]) -> None:
    rk = record_session_key(task, "id")
    status = normalize_task_status(task.get("status"))
    priority = normalize_task_priority(task.get("priority"))
    st.session_state[f"task_edit_status_{rk}"] = status
    st.session_state[f"task_edit_pri_{rk}"] = priority
    assignee = str(task.get("assigned_to") or "").strip()
    assign_opts = _assignee_options(task)
    st.session_state[f"task_edit_assign_{rk}"] = assignee if assignee in assign_opts else assign_opts[0]
    job_labels = _job_label_options(task, job_options)
    current_job = _format_job_label(task, _build_jobs_lookup(), job_options)
    if current_job == "—":
        current_job = "— None —"
    st.session_state[f"task_edit_job_{rk}"] = current_job if current_job in job_labels else job_labels[0]
    est = str(task.get("linked_estimate") or "").strip()
    est_opts = _estimate_options(task)
    st.session_state[f"task_edit_est_{rk}"] = est if est in est_opts else est_opts[0]
    st.session_state[f"task_edit_due_{rk}"] = _as_date(task.get("due_date"))
    st.session_state[f"task_edit_desc_{rk}"] = str(task.get("description") or "")
    st.session_state[f"task_edit_notes_{rk}"] = str(task.get("notes") or "")


def _render_task_detail_tabs(
    task: dict,
    assignee_lookup: dict[str, str],
    jobs_by_id: dict[str, dict],
    job_options: list[dict],
) -> None:
    tid = str(task.get("id") or "")
    title = safe_value(task.get("title"))
    status = normalize_task_status(task.get("status"))
    priority = normalize_task_priority(task.get("priority"))
    assignee = _resolve_assignee_name(task.get("assigned_to"), assignee_lookup)
    if assignee == "—":
        assignee = "Unassigned"
    linked_job = _format_job_label(task, jobs_by_id, job_options)
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


def _render_task_edit_form(task: dict, job_options: list[dict]) -> None:
    rk = record_session_key(task, "id")
    tid = str(task.get("id") or "")
    if f"task_edit_status_{rk}" not in st.session_state:
        _seed_task_edit_form(task, job_options)

    render_edit_form_header("Edit Task")
    if is_demo_id(tid):
        st.caption("Demo records cannot be saved to the database.")

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.selectbox("Status", _TASK_STATUS_OPTS, key=f"task_edit_status_{rk}")
        st.selectbox("Priority", _PRIORITY_FILTER_OPTS[1:], key=f"task_edit_pri_{rk}")
        st.selectbox("Assigned to", _assignee_options(task), key=f"task_edit_assign_{rk}")
    with c2:
        st.selectbox("Job", _job_label_options(task, job_options), key=f"task_edit_job_{rk}")
        st.selectbox("Linked estimate", _estimate_options(task), key=f"task_edit_est_{rk}")
        st.date_input("Due date", key=f"task_edit_due_{rk}")

    st.text_area("Description", key=f"task_edit_desc_{rk}", height=100)
    st.text_area("Notes", key=f"task_edit_notes_{rk}", height=80)

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
            "status": status_to_db(st.session_state.get(f"task_edit_status_{rk}")),
            "priority": priority_to_db(st.session_state.get(f"task_edit_pri_{rk}")),
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
    job_options: list[dict],
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
        _render_task_edit_form(task, job_options)
    else:
        _render_task_detail_tabs(task, assignee_lookup, jobs_by_id, job_options)


def _open_task_detail_modal(
    task: dict,
    *,
    assignee_lookup: dict[str, str],
    jobs_by_id: dict[str, dict],
    job_options: list[dict],
) -> None:
    tid = str(task.get("id") or "").strip()
    if not tid:
        return
    st.session_state[SELECTED_TASK_KEY] = tid
    st.session_state[SHOW_MODAL_KEY] = True
    open_record_modal(
        tid,
        task,
        session_select_key=_SEL,
        modal_key=MODAL_KEY,
        module=MODULE,
        id_fields=("id", "title"),
    )


def _render_task_expand_panel(
    task: dict,
    *,
    assignee_lookup: dict[str, str],
    jobs_by_id: dict[str, dict],
    job_options: list[dict],
) -> None:
    tid = str(task.get("id") or "").strip()
    description = safe_value(task.get("description"), "No description.")
    notes_text = safe_value(task.get("notes"), "No notes entered.")
    linked_job = _format_job_label(task, jobs_by_id, job_options)

    st.markdown(
        f'<p class="ips-timekeeping-expand-title">{html.escape(str(task.get("title") or "Task"))}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        dialog_card_html(
            "Description",
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(description)}</p>",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        dialog_card_html(
            "Notes",
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}</p>",
        ),
        unsafe_allow_html=True,
    )
    st.caption(f"Linked job: {linked_job}")
    if st.button("Full task details", key=f"task_full_modal_{tid}", use_container_width=True):
        _open_task_detail_modal(
            task,
            assignee_lookup=assignee_lookup,
            jobs_by_id=jobs_by_id,
            job_options=job_options,
        )
        st.rerun()


@st.dialog("Task Details", width="large", on_dismiss=_clear_task_modal)
def _show_task_modal(
    assignee_lookup: dict[str, str],
    jobs_by_id: dict[str, dict],
    job_options: list[dict],
) -> None:
    task = get_modal_record(
        cache_key=CACHE_KEY,
        modal_key=MODAL_KEY,
        session_select_key=_SEL,
    )
    if not task:
        render_missing_record(_clear_task_modal, close_key="task_modal_missing_close")
        return
    render_task_detail_dialog(
        task,
        assignee_lookup=assignee_lookup,
        jobs_by_id=jobs_by_id,
        job_options=job_options,
    )


def _render_custom_task_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
    assignee_lookup: dict[str, str],
    jobs_by_id: dict[str, dict],
    job_options: list[dict],
) -> list[str]:
    if not filtered:
        st.info("No tasks match your filters.")
        st.session_state[_ALL_TASK_IDS_KEY] = []
        return []

    all_task_ids = [str(t.get("id") or "").strip() for t in filtered if str(t.get("id") or "").strip()]
    st.session_state[_ALL_TASK_IDS_KEY] = all_task_ids

    with st.container(key="tasks_table_wrap"):
        st.markdown('<div class="ips-task-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_TASK_COLS, gap="small", vertical_alignment="center")
        for col, (label, field) in zip(header_cols, _TASK_HEADER_SPECS):
            with col:
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-task-header-row ips-task-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-task-header-row ips-task-cell",
                    )

        for task in filtered:
            tid = str(task.get("id") or "").strip()
            if not tid:
                continue

            status = normalize_task_status(task.get("status"))
            priority = normalize_task_priority(task.get("priority"))
            assignee = _resolve_assignee_name(task.get("assigned_to"), assignee_lookup)
            due = fmt_date(task.get("due_date"))
            current_job_id = _resolve_task_job_id(task, job_options, jobs_by_id)
            job_labels = [str(o.get("label") or "") for o in job_options]
            job_ids = [o.get("id") for o in job_options]
            current_job_label = "— None —"
            for opt in job_options:
                if opt.get("id") == current_job_id:
                    current_job_label = str(opt.get("label") or "— None —")
                    break
            if current_job_id is None and str(task.get("linked_job") or "") in job_labels:
                current_job_label = str(task.get("linked_job"))

            field_mode = is_field_mode()
            expanded = field_mode and field_expanded_id(FIELD_EXPANDED_TASK_KEY) == tid

            cols = st.columns(_TASK_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                if field_mode:
                    if st.button(
                        "▾" if expanded else "▸",
                        key=f"task_expand_{tid}",
                        help="Expand task details",
                    ):
                        toggle_field_expanded(FIELD_EXPANDED_TASK_KEY, tid)
                        st.rerun()
                else:
                    st.checkbox(
                        "",
                        key=_task_select_key(tid),
                        label_visibility="collapsed",
                        on_change=_on_task_checkbox_change,
                        args=(tid, all_task_ids),
                    )

            with cols[1]:
                st.markdown(
                    f'<div class="ips-task-title">{html.escape(str(task.get("title") or ""))}</div>',
                    unsafe_allow_html=True,
                )

            with cols[2]:
                status_wrap = (
                    f"task_status_open_{tid}"
                    if status == "Open"
                    else f"task_status_closed_{tid}"
                )
                with st.container(key=status_wrap):
                    if status == "Open":
                        if st.button("Open", key=f"task_status_{tid}"):
                            _save_task_field(tid, {"status": "Closed"})
                    else:
                        if st.button("Closed", key=f"task_status_{tid}"):
                            _save_task_field(tid, {"status": "Open"})

            with cols[3]:
                st.markdown(_priority_pill_html(priority), unsafe_allow_html=True)

            with cols[4]:
                st.markdown(
                    f'<div class="ips-task-cell">{html.escape(assignee)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[5]:
                try:
                    job_index = job_labels.index(current_job_label)
                except ValueError:
                    job_index = 0
                prev_key = f"task_job_prev_{tid}"
                picked_label = st.selectbox(
                    "Job",
                    job_labels,
                    index=job_index,
                    key=f"task_job_{tid}",
                    label_visibility="collapsed",
                )
                if prev_key not in st.session_state:
                    st.session_state[prev_key] = picked_label
                elif st.session_state.get(prev_key) != picked_label:
                    picked_id = job_ids[job_labels.index(picked_label)]
                    st.session_state[prev_key] = picked_label
                    _save_task_field(
                        tid,
                        {
                            "job_id": picked_id,
                            "job_label": picked_label if picked_label != "— None —" else "",
                        },
                        job_options=job_options,
                    )

            with cols[6]:
                st.markdown(
                    f'<div class="ips-task-cell ips-task-due">{html.escape(due)}</div>',
                    unsafe_allow_html=True,
                )

            if expanded:
                st.markdown('<div class="ips-field-row-expand">', unsafe_allow_html=True)
                _render_task_expand_panel(
                    task,
                    assignee_lookup=assignee_lookup,
                    jobs_by_id=jobs_by_id,
                    job_options=job_options,
                )
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    return all_task_ids


def _job_friendly_label(job: dict) -> str:
    num = str(job.get("job_number") or "").strip()
    name = str(job.get("job_name") or "").strip()
    if num and name:
        return f"{num} — {name}"
    return num or name or str(job.get("id") or "")


def _resolve_job_id_from_label(label: str, job_options: list[dict]) -> str | None:
    for opt in job_options:
        if str(opt.get("label") or "") == label:
            jid = opt.get("id")
            return str(jid).strip() if jid else None
    return None


def _render_job_task_status_button(task: dict) -> None:
    tid = str(task.get("id") or "").strip()
    if not tid:
        return
    status = normalize_task_status(task.get("status"))
    status_wrap = f"job_task_status_open_{tid}" if status == "Open" else f"job_task_status_closed_{tid}"
    with st.container(key=status_wrap):
        if status == "Open":
            if st.button("Open", key=f"job_task_status_{tid}"):
                _save_task_field(tid, {"status": "Closed"})
        else:
            if st.button("Closed", key=f"job_task_status_{tid}"):
                _save_task_field(tid, {"status": "Open"})


def _render_job_linked_tasks_table(
    tasks: list[dict],
    *,
    assignee_lookup: dict[str, str],
) -> None:
    cols = [4.8, 1.2, 1.2, 2.0, 1.2]
    headers = ["TASK", "STATUS", "PRIORITY", "ASSIGNED TO", "DUE"]
    st.markdown('<div class="ips-job-tasks-table">', unsafe_allow_html=True)
    with st.container(key="job_tasks_table_wrap"):
        header_cols = st.columns(cols, gap="small", vertical_alignment="center")
        for col, label in zip(header_cols, headers):
            with col:
                st.markdown(
                    f'<div class="ips-job-tasks-header-row ips-task-cell">{html.escape(label)}</div>',
                    unsafe_allow_html=True,
                )
        for task in tasks:
            tid = str(task.get("id") or "").strip()
            if not tid:
                continue
            status = normalize_task_status(task.get("status"))
            priority = normalize_task_priority(task.get("priority"))
            assignee = _resolve_assignee_name(task.get("assigned_to"), assignee_lookup)
            due = fmt_date(task.get("due_date"))
            row_cols = st.columns(cols, gap="small", vertical_alignment="center")
            with row_cols[0]:
                st.markdown(
                    f'<div class="ips-job-tasks-row ips-task-title">{html.escape(str(task.get("title") or ""))}</div>',
                    unsafe_allow_html=True,
                )
            with row_cols[1]:
                _render_job_task_status_button(task)
            with row_cols[2]:
                st.markdown(_priority_pill_html(priority), unsafe_allow_html=True)
            with row_cols[3]:
                st.markdown(
                    f'<div class="ips-job-tasks-row ips-task-cell">{html.escape(assignee)}</div>',
                    unsafe_allow_html=True,
                )
            with row_cols[4]:
                st.markdown(
                    f'<div class="ips-job-tasks-row ips-task-cell ips-task-due">{html.escape(due)}</div>',
                    unsafe_allow_html=True,
                )
    st.markdown("</div>", unsafe_allow_html=True)


def render_job_linked_tasks_tab(job: dict) -> None:
    """Tasks tab inside Job Details — linked IPS tasks for this job."""
    job_id = str(job.get("id") or "").strip()
    if not job_id:
        st.info("No job selected.")
        return

    assignee_lookup = _build_assignee_lookup()
    job_options = get_job_options(include_all=True)
    job_label = _job_friendly_label(job)
    view_key = f"job_tasks_view_{job_id}"
    form_key = f"job_task_form_{job_id}"

    if view_key not in st.session_state:
        st.session_state[view_key] = "Open"

    head_l, head_r = st.columns([3, 1])
    with head_l:
        st.markdown(
            '<div class="ips-task-view-toggle ips-job-tasks-view">',
            unsafe_allow_html=True,
        )
        if hasattr(st, "segmented_control"):
            st.segmented_control(
                "Job task view",
                JOB_TASK_VIEW_OPTS,
                key=view_key,
                label_visibility="collapsed",
            )
        else:
            st.radio(
                "Job task view",
                JOB_TASK_VIEW_OPTS,
                key=view_key,
                horizontal=True,
                label_visibility="collapsed",
            )
        st.markdown("</div>", unsafe_allow_html=True)
    with head_r:
        if st.button("+ Add Task", key=f"job_add_task_{job_id}", use_container_width=True):
            st.session_state[form_key] = True

    all_for_job = _merge_task_overrides(get_tasks_by_job(job_id, include_closed=True))
    view = str(st.session_state.get(view_key) or "Open")
    if view == "Closed":
        linked = [t for t in all_for_job if normalize_task_status(t.get("status")) == "Closed"]
    elif view == "Open":
        linked = [t for t in all_for_job if normalize_task_status(t.get("status")) == "Open"]
    else:
        linked = all_for_job

    if st.session_state.get(form_key):
        with st.expander("New task", expanded=True):
            st.text_input("Title", key=f"job_task_new_title_{job_id}")
            nc1, nc2 = st.columns(2)
            with nc1:
                st.selectbox("Status", _TASK_STATUS_OPTS, key=f"job_task_new_status_{job_id}")
                st.selectbox("Priority", _PRIORITY_FILTER_OPTS[1:], key=f"job_task_new_priority_{job_id}")
            with nc2:
                st.selectbox(
                    "Assigned to",
                    ["— Unassigned —", *task_assignee_options()],
                    key=f"job_task_new_assignee_{job_id}",
                )
                st.date_input("Due date", key=f"job_task_new_due_{job_id}", value=None)
            st.text_input("Linked job", value=job_label, disabled=True, key=f"job_task_new_job_display_{job_id}")
            st.text_area("Description", key=f"job_task_new_desc_{job_id}")
            btn_l, btn_r = st.columns(2)
            with btn_l:
                if st.button("Create Task", key=f"job_task_create_{job_id}", type="primary"):
                    assignee = st.session_state.get(f"job_task_new_assignee_{job_id}")
                    if assignee == "— Unassigned —":
                        assignee = ""
                    ui = {
                        "title": st.session_state.get(f"job_task_new_title_{job_id}"),
                        "description": st.session_state.get(f"job_task_new_desc_{job_id}"),
                        "status": status_to_db(st.session_state.get(f"job_task_new_status_{job_id}")),
                        "priority": priority_to_db(st.session_state.get(f"job_task_new_priority_{job_id}")),
                        "assigned_to": assignee,
                        "job_id": job_id,
                        "linked_job": job_label,
                        "linked_estimate": "— None —",
                        "due_date": st.session_state.get(f"job_task_new_due_{job_id}"),
                    }
                    ok, msg = persist_task(ui)
                    if apply_persist_feedback(ok, msg, clear_keys=(form_key,)):
                        clear_tasks_cache()
                        st.rerun()
            with btn_r:
                if st.button("Cancel", key=f"job_task_cancel_{job_id}"):
                    st.session_state[form_key] = False
                    st.rerun()

    if not linked:
        st.markdown(
            '<p class="ips-job-tasks-empty">No tasks linked to this job.</p>',
            unsafe_allow_html=True,
        )
        return

    _render_job_linked_tasks_table(linked, assignee_lookup=assignee_lookup)


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("tasks"):
        return

    inject_tasks_module_css()
    if is_field_mode():
        inject_field_row_expand_css()
    st.markdown('<span class="ips-tasks-page ips-page-shell-marker" aria-hidden="true"></span>', unsafe_allow_html=True)

    assignee_lookup = _build_assignee_lookup()
    jobs_by_id = _build_jobs_lookup()
    job_options = get_job_options(include_all=True)
    all_tasks = _merge_task_overrides(get_tasks())
    enriched_tasks = [
        _enrich_task_row(
            t,
            assignee_lookup=assignee_lookup,
            jobs_by_id=jobs_by_id,
            job_options=job_options,
        )
        for t in all_tasks
    ]
    filter_options = build_filter_options(enriched_tasks, _COLUMN_FILTER_SPECS)

    def _task_new() -> None:
        if st.button("+ New Task", key="task_new", type="primary", use_container_width=True):
            st.session_state["ips_task_form"] = True

    render_page_brand_header(
        "Tasks",
        "Track to-dos, assignments, and linked jobs or estimates.",
        actions=[_task_new],
    )

    if is_field_mode():
        try:
            from app.services.job_service import sort_jobs_by_number_then_name
        except ImportError:
            from services.job_service import sort_jobs_by_number_then_name  # type: ignore
        jobs = sort_jobs_by_number_then_name(load_jobs())
        if jobs:
            render_field_job_bar(jobs, key_prefix="tasks")

    def _filters() -> None:
        _render_task_view_selector()
        c1, c2 = st.columns([5, 0.6])
        with c1:
            st.text_input("Search", placeholder="Search tasks…", key="task_search", label_visibility="collapsed")
        with c2:
            if st.button("Clear", key="task_clear", use_container_width=True):
                clear_table_filters(
                    _TABLE_KEY,
                    _FILTER_FIELDS,
                    extra_keys=["task_search", TASK_VIEW_KEY],
                )
                _clear_task_selection(st.session_state.get(_ALL_TASK_IDS_KEY))
                clear_field_expanded(FIELD_EXPANDED_TASK_KEY)
                st.session_state[TASK_VIEW_KEY] = "Due Today" if is_field_mode() else "Open Tasks"
                st.rerun()

    layout_filter_bar(_filters)

    if st.session_state.get("ips_task_form"):
        pre_job_id = st.session_state.get("ips_task_form_job_id")
        pre_job_label = str(st.session_state.get("ips_task_form_job_label") or "").strip()
        job_labels = [str(o.get("label") or "") for o in job_options]
        default_job_label = pre_job_label if pre_job_label in job_labels else job_labels[0]
        if "task_new_job" not in st.session_state and pre_job_label:
            st.session_state["task_new_job"] = default_job_label
        with st.expander("New task", expanded=True):
            st.text_input("Title", key="task_new_title")
            nc1, nc2 = st.columns(2)
            with nc1:
                st.selectbox("Status", _TASK_STATUS_OPTS, key="task_new_status")
                st.selectbox("Priority", _PRIORITY_FILTER_OPTS[1:], key="task_new_priority")
            with nc2:
                st.selectbox("Assigned to", ["— Unassigned —", *task_assignee_options()], key="task_new_assignee")
                st.date_input("Due date", key="task_new_due", value=None)
            if pre_job_id:
                st.text_input("Linked job", value=default_job_label, disabled=True, key="task_new_job_locked")
                picked_job_label = default_job_label
                picked_job_id = pre_job_id
            else:
                picked_job_label = st.selectbox(
                    "Linked job",
                    job_labels,
                    key="task_new_job",
                )
                picked_job_id = _resolve_job_id_from_label(picked_job_label, job_options)
            st.selectbox("Linked estimate", _estimate_options({}), key="task_new_est")
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
                    "job_id": picked_job_id,
                    "linked_job": picked_job_label,
                    "linked_estimate": st.session_state.get("task_new_est"),
                    "due_date": st.session_state.get("task_new_due"),
                }
                ok, msg = persist_task(ui)
                if apply_persist_feedback(
                    ok,
                    msg,
                    clear_keys=("ips_task_form", "ips_task_form_job_id", "ips_task_form_job_label"),
                ):
                    clear_tasks_cache()
                    st.rerun()

    view = str(st.session_state.get(TASK_VIEW_KEY) or ("Due Today" if is_field_mode() else "Open Tasks"))
    view_opts = FIELD_TASK_VIEW_OPTS if is_field_mode() else TASK_VIEW_OPTS
    if view not in view_opts:
        view = view_opts[0]
        st.session_state[TASK_VIEW_KEY] = view

    viewed = _apply_task_view_filter(enriched_tasks, view)
    viewed = _apply_field_task_filters(viewed, assignee_lookup=assignee_lookup)
    filtered = _filter_tasks(
        viewed,
        q=str(st.session_state.get("task_search") or "").strip(),
    )

    st.caption(_task_count_caption(len(filtered), view))

    build_modal_cache(filtered, cache_key=CACHE_KEY)
    _render_custom_task_table(
        filtered,
        filter_options=filter_options,
        assignee_lookup=assignee_lookup,
        jobs_by_id=jobs_by_id,
        job_options=job_options,
    )

    selected_task_id = st.session_state.get(SELECTED_TASK_KEY)
    if selected_task_id and st.session_state.get(SHOW_MODAL_KEY):
        _show_task_modal(assignee_lookup, jobs_by_id, job_options)
