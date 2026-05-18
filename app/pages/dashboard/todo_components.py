"""Dashboard to-do list UI and dialogs."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

import streamlit as st

try:
    from app.auth import current_profile
    from app.data_cache import clear_session_table_cache
    from app.db import delete_rows_admin, insert_row_admin, update_rows_admin
    from app.ui.modal import ensure_modal_styles
except ImportError:
    from auth import current_profile  # type: ignore
    from data_cache import clear_session_table_cache  # type: ignore
    from db import delete_rows_admin, insert_row_admin, update_rows_admin  # type: ignore
    from ui.modal import ensure_modal_styles  # type: ignore

from . import queries as q
from .todo_logic import (
    TODO_PRIORITIES,
    TODO_STATUSES,
    TODO_VIEW_OPTIONS,
    apply_todo_search,
    dedupe_todos,
    filter_todos_for_view,
    is_terminal_todo_status,
    norm_todo_id,
    sort_todos,
    status_slug,
)

TODO_LIST_CSS_KEY = "dash_todo_list_css_v6"


def inject_todo_list_css() -> None:
    if st.session_state.get(TODO_LIST_CSS_KEY):
        return
    st.session_state[TODO_LIST_CSS_KEY] = True
    st.markdown(
        """
        <style>
        .ips-todo-list-zone {
          position: absolute;
          width: 0;
          height: 0;
          overflow: hidden;
          pointer-events: none;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-todo-list-zone) {
          border: 1px solid rgba(15, 23, 42, 0.08) !important;
          box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05) !important;
          border-radius: 8px !important;
          padding: 0.4rem 0.5rem 0.48rem !important;
          margin-bottom: 0.32rem !important;
        }
        /* Scoped to the bordered To-Do block (contains hidden zone marker) */
        [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-todo-list-zone) div.stButton > button,
        [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-todo-list-zone) div.stButton > button[data-testid="baseButton-secondary"],
        [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-todo-list-zone) div.stButton > button[data-testid="baseButton-primary"] {
          white-space: nowrap !important;
          min-width: 54px;
          max-width: 72px;
          min-height: 36px;
          padding: 4px 8px !important;
          font-size: 12px !important;
          line-height: 1.15 !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-todo-list-zone) div.stButton > button p {
          white-space: nowrap !important;
          font-size: 12px !important;
          line-height: 1.15 !important;
          overflow: hidden;
          text-overflow: ellipsis;
          margin: 0 !important;
        }
        .ips-todo-sep {
          border: none;
          border-top: 1px solid #e2e8f0;
          margin: 0.35rem 0 0.45rem 0;
        }
        .ips-todo-title {
          font-weight: 700;
          font-size: 0.92rem;
          color: #0f172a;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          max-width: 100%;
          margin: 0 !important;
          line-height: 1.25 !important;
        }
        .ips-todo-assignee-wrap {
          display: block;
          max-width: 11rem;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .ips-todo-badge {
          display: inline-block;
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.03em;
          text-transform: uppercase;
          padding: 2px 7px;
          border-radius: 6px;
          border: 1px solid rgba(15, 23, 42, 0.12);
          line-height: 1.2;
          white-space: nowrap;
        }
        .ips-todo-badge-pri-low, .ips-todo-badge-pri-normal {
          background: #e2e8f0;
          color: #1e3a5f;
          border-color: #94a3b8;
        }
        .ips-todo-badge-pri-high {
          background: #fef3c7;
          color: #92400e;
          border-color: #fcd34d;
        }
        .ips-todo-badge-pri-urgent {
          background: #fee2e2;
          color: #991b1b;
          border-color: #f87171;
        }
        .ips-todo-badge-st-open {
          background: #dbeafe;
          color: #1e40af;
          border-color: #93c5fd;
        }
        .ips-todo-badge-st-in_progress {
          background: #ffedd5;
          color: #9a3412;
          border-color: #fdba74;
        }
        .ips-todo-badge-st-pending {
          background: #ede9fe;
          color: #5b21b6;
          border-color: #c4b5fd;
        }
        .ips-todo-badge-st-waiting {
          background: #f1f5f9;
          color: #475569;
          border-color: #cbd5e1;
        }
        .ips-todo-badge-st-terminal {
          background: #dcfce7;
          color: #166534;
          border-color: #86efac;
        }
        .ips-todo-badge-st-default {
          background: #f1f5f9;
          color: #334155;
          border-color: #cbd5e1;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def todo_pri_badge_html(priority: str) -> str:
    p = str(priority or "Normal").strip().title()
    slug = str(priority or "normal").strip().lower().replace(" ", "_")
    if slug in ("urgent",):
        cls = "ips-todo-badge ips-todo-badge-pri-urgent"
    elif slug in ("high",):
        cls = "ips-todo-badge ips-todo-badge-pri-high"
    else:
        cls = "ips-todo-badge ips-todo-badge-pri-normal"
    return f'<span class="{cls}">{html.escape(p)}</span>'


def todo_status_badge_html(status: str) -> str:
    s = str(status or "Open").strip()
    slug = status_slug(s).replace(" ", "_")
    if is_terminal_todo_status(s):
        cls = "ips-todo-badge ips-todo-badge-st-terminal"
    elif slug in ("open",):
        cls = "ips-todo-badge ips-todo-badge-st-open"
    elif slug in ("in_progress",):
        cls = "ips-todo-badge ips-todo-badge-st-in_progress"
    elif slug in ("waiting",):
        cls = "ips-todo-badge ips-todo-badge-st-waiting"
    elif slug in ("pending",):
        cls = "ips-todo-badge ips-todo-badge-st-pending"
    else:
        cls = "ips-todo-badge ips-todo-badge-st-default"
    return f'<span class="{cls}">{html.escape(s)}</span>'


def todo_trunc(s: str, n: int) -> str:
    t = str(s or "").strip()
    return t if len(t) <= n else (t[: max(0, n - 1)] + "…")


def dash_todo_on_dismiss_view() -> None:
    st.session_state.pop("dash_todo_dlg_view", None)


def dash_todo_on_dismiss_edit() -> None:
    st.session_state.pop("dash_todo_dlg_edit", None)


def dash_todo_on_dismiss_del() -> None:
    st.session_state.pop("dash_todo_dlg_del", None)


def dash_todo_on_dismiss_add() -> None:
    st.session_state.pop("dash_todo_open_add", None)


@st.dialog("Task details", width="small", on_dismiss=dash_todo_on_dismiss_view)
def dash_todo_view_dialog(*, row: dict[str, Any], id_to_label: dict[str, str]) -> None:
    ensure_modal_styles()
    tid = str(row.get("id") or "").strip()
    st.markdown(f"### {html.escape(str(row.get('title') or '—'))}")
    aid = str(row.get("assigned_to") or "").strip()
    st.markdown(
        "<p style='font-size:0.82rem;color:#475569;margin:0 0 0.5rem 0'>"
        f"<strong>Status</strong> {html.escape(str(row.get('status') or 'Open'))} · "
        f"<strong>Priority</strong> {html.escape(str(row.get('priority') or 'Normal'))} · "
        f"<strong>Due</strong> {html.escape(str(row.get('due_date') or '—'))} · "
        f"<strong>Assigned</strong> {html.escape(id_to_label.get(aid, '—'))}"
        "</p>",
        unsafe_allow_html=True,
    )
    desc = str(row.get("description") or "").strip()
    if desc:
        st.markdown("**Description**")
        st.markdown(f"<div style='white-space:pre-wrap;font-size:0.9rem;color:#1e293b'>{html.escape(desc)}</div>", unsafe_allow_html=True)
    else:
        st.caption("No description.")
    if st.button("Close", type="secondary", use_container_width=True, key=f"dash_todo_dlg_view_close_{tid}"):
        st.session_state.pop("dash_todo_dlg_view", None)
        st.rerun()


@st.dialog("Edit task", width="small", on_dismiss=dash_todo_on_dismiss_edit)
def dash_todo_edit_dialog(
    *,
    row: dict[str, Any],
    id_to_label: dict[str, str],
    ordered_ids: list[str],
    me: str,
) -> None:
    ensure_modal_styles()
    tid = str(row.get("id") or "").strip()
    title = str(row.get("title") or "").strip() or "—"
    priority = str(row.get("priority") or "Normal").strip() or "Normal"
    status = str(row.get("status") or "Open").strip() or "Open"
    due = str(row.get("due_date") or "").strip() or "—"
    assigned_to = str(row.get("assigned_to") or "").strip()
    assignee_opts = ["— Unassigned —"] + [id_to_label[i] for i in ordered_ids]
    cur_assignee_lbl = id_to_label.get(assigned_to, "— Unassigned —") if assigned_to else "— Unassigned —"
    st.markdown(f"### {html.escape(title)}")

    with st.form(f"dash_todo_edit_f_{tid}", clear_on_submit=False):
        et = st.text_input("Title", value=title, key=f"dash_todo_ed_title_{tid}")
        ed = st.text_area("Description", value=str(row.get("description") or ""), height=88, key=f"dash_todo_ed_desc_{tid}")
        c1, c2, c3 = st.columns(3, gap="small")
        with c1:
            due_s = st.text_input("Due date (YYYY-MM-DD)", value="" if due == "—" else due, key=f"dash_todo_ed_due_{tid}")
        with c2:
            epri = st.selectbox(
                "Priority",
                list(TODO_PRIORITIES),
                index=max(0, list(TODO_PRIORITIES).index(priority)) if priority in TODO_PRIORITIES else 1,
                key=f"dash_todo_ed_pri_{tid}",
            )
        with c3:
            status_ix = list(TODO_STATUSES).index(status) if status in TODO_STATUSES else 0
            estat = st.selectbox("Status", list(TODO_STATUSES), index=status_ix, key=f"dash_todo_ed_stat_{tid}")
        st.selectbox(
            "Assigned to",
            assignee_opts,
            index=max(0, assignee_opts.index(cur_assignee_lbl)) if cur_assignee_lbl in assignee_opts else 0,
            key=f"dash_todo_ed_asg_{tid}",
        )
        save = st.form_submit_button("Save", type="primary", use_container_width=True)
    if st.button("Cancel", type="secondary", use_container_width=True, key=f"dash_todo_ed_cancel_{tid}"):
        st.session_state.pop("dash_todo_dlg_edit", None)
        st.rerun()

    if save:
        et = str(st.session_state.get(f"dash_todo_ed_title_{tid}") or "").strip()
        ed = str(st.session_state.get(f"dash_todo_ed_desc_{tid}") or "").strip()
        due_s = str(st.session_state.get(f"dash_todo_ed_due_{tid}") or "").strip()
        epri = str(st.session_state.get(f"dash_todo_ed_pri_{tid}") or "Normal").strip()
        estat = str(st.session_state.get(f"dash_todo_ed_stat_{tid}") or "Open").strip()
        assignee_label = str(st.session_state.get(f"dash_todo_ed_asg_{tid}") or "")
        new_assigned_to = None
        if assignee_label and not assignee_label.startswith("—"):
            for pid, lbl in id_to_label.items():
                if lbl == assignee_label:
                    new_assigned_to = pid
                    break
        new_status = str(estat or "Open").strip() or "Open"
        payload: dict[str, Any] = {
            "title": et or "—",
            "description": ed or None,
            "priority": str(epri or "Normal").strip() or "Normal",
            "status": new_status,
            "assigned_to": new_assigned_to,
        }
        ds = str(due_s or "").strip()
        payload["due_date"] = ds if ds else None
        if is_terminal_todo_status(new_status):
            payload["completed_at"] = datetime.now(timezone.utc).isoformat()
        else:
            payload["completed_at"] = None
        try:
            update_rows_admin("todos", payload, {"id": tid})
            clear_session_table_cache()
            st.session_state.pop("dash_todo_dlg_edit", None)
            st.success("Saved.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


@st.dialog("Delete task?", width="small", on_dismiss=dash_todo_on_dismiss_del)
def dash_todo_delete_dialog(*, tid: str, title: str) -> None:
    ensure_modal_styles()
    st.markdown(f"Permanently delete **{html.escape(title)}**?")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("Delete", type="primary", use_container_width=True, key=f"dash_todo_del_go_{tid}"):
            try:
                delete_rows_admin("todos", {"id": tid})
                clear_session_table_cache()
                st.session_state.pop("dash_todo_dlg_del", None)
                st.success("Deleted.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with c2:
        if st.button("Cancel", type="secondary", use_container_width=True, key=f"dash_todo_del_no_{tid}"):
            st.session_state.pop("dash_todo_dlg_del", None)
            st.rerun()


@st.dialog("Add task", width="small", on_dismiss=dash_todo_on_dismiss_add)
def dash_todo_add_dialog(
    *,
    id_to_label: dict[str, str],
    ordered_ids: list[str],
    me: str,
) -> None:
    ensure_modal_styles()
    st.markdown("### Add task")
    with st.container(border=True):
        with st.form("dash_todo_add_f", clear_on_submit=True):
            st.text_input("Title", key="dash_todo_add_title_dlg")
            st.text_area("Description", key="dash_todo_add_desc_dlg", height=64)
            c1, c2, c3 = st.columns(3, gap="small")
            with c1:
                st.date_input("Due date", value=None, key="dash_todo_add_due_dlg")
            with c2:
                st.selectbox("Priority", list(TODO_PRIORITIES), index=1, key="dash_todo_add_pri_dlg")
            with c3:
                st.selectbox("Status", list(TODO_STATUSES), index=0, key="dash_todo_add_stat_dlg")
            assignee_opts = ["— Unassigned —"] + [id_to_label[i] for i in ordered_ids]
            st.selectbox("Assigned to", assignee_opts, key="dash_todo_add_asg_dlg")
            save = st.form_submit_button("Create task", type="primary", use_container_width=True)
    if st.button("Cancel", type="secondary", use_container_width=True, key="dash_todo_add_cancel_dlg"):
        st.session_state.pop("dash_todo_open_add", None)
        st.rerun()
    if save:
        t = str(st.session_state.get("dash_todo_add_title_dlg") or "").strip()
        desc = str(st.session_state.get("dash_todo_add_desc_dlg") or "").strip()
        due = st.session_state.get("dash_todo_add_due_dlg")
        priority = str(st.session_state.get("dash_todo_add_pri_dlg") or "Normal").strip() or "Normal"
        status = str(st.session_state.get("dash_todo_add_stat_dlg") or "Open").strip() or "Open"
        assignee_label = str(st.session_state.get("dash_todo_add_asg_dlg") or "")
        assigned_to = None
        if assignee_label and not assignee_label.startswith("—"):
            for pid, lbl in id_to_label.items():
                if lbl == assignee_label:
                    assigned_to = pid
                    break
        if not t:
            st.error("Title is required.")
            return
        payload: dict[str, Any] = {
            "title": t,
            "description": desc or None,
            "priority": priority,
            "status": status,
            "created_by": me or None,
            "assigned_to": assigned_to,
        }
        if due is not None:
            payload["due_date"] = str(due)
        if is_terminal_todo_status(payload["status"]):
            payload["completed_at"] = datetime.now(timezone.utc).isoformat()
        try:
            insert_row_admin("todos", payload)
            clear_session_table_cache()
            st.session_state.pop("dash_todo_open_add", None)
            st.success("Task added.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def profiles_for_todo_assign(session_key: str, *, use_admin: bool) -> tuple[dict[str, str], list[str]]:
    """Return (id->label, ordered_ids) for assigned_to choices."""
    profs = q.fetch_profiles(session_key, use_admin=use_admin)
    id_to_label: dict[str, str] = {}
    ordered: list[str] = []
    for p in profs or []:
        pid = str((p or {}).get("id") or "").strip()
        if not pid:
            continue
        email = str((p or {}).get("email") or "").strip()
        nm = str((p or {}).get("full_name") or "").strip()
        label = nm or email or pid[:8] + "…"
        id_to_label[pid] = label
        ordered.append(pid)
    return id_to_label, ordered


def render_todo_list(
    *,
    session_key: str,
    use_admin: bool,
    todos: list[dict] | None = None,
) -> None:
    prof = current_profile()
    me = str(prof.get("id") or "").strip()

    with st.container(border=True):
        st.markdown(
            '<div class="ips-todo-list-zone" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        inject_todo_list_css()
        id_to_label, ordered_ids = profiles_for_todo_assign(session_key, use_admin=use_admin)

        if todos is None:
            todos = q.fetch_todos(session_key, use_admin=use_admin)

        raw_list = [t for t in (todos or []) if isinstance(t, dict) and str(t.get("id") or "").strip()]
        valid_todos = sort_todos(dedupe_todos(raw_list))
        active_count = sum(1 for t in valid_todos if not is_terminal_todo_status(t.get("status")))

        h1, h2, h3 = st.columns([1.35, 1.25, 1], gap="small")
        with h1:
            ht1, ht2 = st.columns([1, 0.55], gap="small")
            with ht1:
                st.markdown(f"##### To-Do List ({active_count})")
            with ht2:
                if st.button(
                    "Add task",
                    type="primary",
                    use_container_width=True,
                    key="dash_todo_open_add_btn",
                ):
                    st.session_state["dash_todo_open_add"] = True
                    st.rerun()
        with h2:
            st.text_input(
                "Search",
                key="dash_todo_search_q",
                placeholder="Search…",
                label_visibility="collapsed",
            )
        with h3:
            view = st.selectbox(
                "Show",
                list(TODO_VIEW_OPTIONS),
                key="dash_todo_view",
                label_visibility="collapsed",
            )

        rows_base, _ = filter_todos_for_view(valid_todos, view)
        search_q = str(st.session_state.get("dash_todo_search_q") or "")
        rows = apply_todo_search(rows_base, search_q, id_to_label)
        rows = sort_todos(dedupe_todos(rows))

        if not rows:
            try:
                from app.ui.components.empty_states import render_empty_state
            except ImportError:
                from ui.components.empty_states import render_empty_state  # type: ignore
            if view == "Completed Tasks":
                render_empty_state("No completed tasks", "Completed tasks will appear here.", icon="✓")
            elif view == "All Tasks":
                if render_empty_state(
                    "No tasks yet",
                    "Add a task to track follow-ups and priorities.",
                    icon="☑",
                    action_label="Add task",
                    action_key="dash_todo_empty_add",
                ):
                    st.session_state["dash_todo_open_add"] = True
                    st.rerun()
            else:
                if render_empty_state(
                    "No active tasks",
                    "Add a task or switch to All Tasks to see everything.",
                    icon="☑",
                    action_label="Add task",
                    action_key="dash_todo_empty_add_active",
                ):
                    st.session_state["dash_todo_open_add"] = True
                    st.rerun()
        else:
            st.caption("Urgent / high priority sort first · row actions for details, edit, or delete.")
            for idx, t in enumerate(rows):
                tid = str(t.get("id") or "").strip()
                if not tid:
                    continue
                if idx:
                    st.markdown('<hr class="ips-todo-sep" />', unsafe_allow_html=True)
                title = str(t.get("title") or "").strip() or "—"
                priority = str(t.get("priority") or "Normal").strip() or "Normal"
                status = str(t.get("status") or "Open").strip() or "Open"
                due = str(t.get("due_date") or "").strip() or "—"
                assigned_to = str(t.get("assigned_to") or "").strip()
                assigned_lbl = id_to_label.get(assigned_to, "—")
                is_terminal = is_terminal_todo_status(status)
                title_esc = html.escape(todo_trunc(title, 80))
                full_title_esc = html.escape(title)
                asg_esc = html.escape(todo_trunc(assigned_lbl, 40))
                asg_full_esc = html.escape(assigned_lbl)

                with st.container(border=False):
                    c1, c2, c3, c4, c5, c6 = st.columns([2.05, 0.88, 0.62, 1.0, 0.82, 2.65], gap="small")
                    with c1:
                        st.markdown(
                            f'<p class="ips-todo-title" title="{full_title_esc}">{title_esc}</p>',
                            unsafe_allow_html=True,
                        )
                    with c2:
                        st.markdown(todo_pri_badge_html(priority), unsafe_allow_html=True)
                    with c3:
                        st.caption(due if due != "—" else "—")
                    with c4:
                        st.markdown(
                            f'<span class="ips-todo-assignee-wrap" title="{asg_full_esc}">{asg_esc}</span>',
                            unsafe_allow_html=True,
                        )
                    with c5:
                        st.markdown(todo_status_badge_html(status), unsafe_allow_html=True)
                    with c6:
                        a1, a2, a3, a4 = st.columns(4, gap="small")
                        with a1:
                            if st.button(
                                "View",
                                key=f"dash_todo_v_{tid}",
                                help="Details",
                                use_container_width=False,
                            ):
                                st.session_state["dash_todo_dlg_view"] = tid
                                st.rerun()
                        with a2:
                            if st.button(
                                "Edit",
                                key=f"dash_todo_e_{tid}",
                                help="Edit task",
                                use_container_width=False,
                            ):
                                st.session_state["dash_todo_dlg_edit"] = tid
                                st.rerun()
                        with a3:
                            if is_terminal:
                                if st.button(
                                    "Reopen",
                                    key=f"dash_todo_reopen_{tid}",
                                    help="Mark not complete",
                                    use_container_width=False,
                                ):
                                    update_rows_admin(
                                        "todos",
                                        {"status": "Open", "completed_at": None},
                                        {"id": tid},
                                    )
                                    clear_session_table_cache()
                                    st.rerun()
                            else:
                                if st.button(
                                    "Done",
                                    key=f"dash_todo_done_{tid}",
                                    help="Mark complete",
                                    use_container_width=False,
                                ):
                                    update_rows_admin(
                                        "todos",
                                        {
                                            "status": "Complete",
                                            "completed_at": datetime.now(timezone.utc).isoformat(),
                                        },
                                        {"id": tid},
                                    )
                                    clear_session_table_cache()
                                    st.rerun()
                        with a4:
                            if st.button(
                                "Del",
                                key=f"dash_todo_d_{tid}",
                                help="Delete task",
                                use_container_width=False,
                            ):
                                st.session_state["dash_todo_dlg_del"] = tid
                                st.rerun()

        by_id: dict[str, dict] = {}
        for x in valid_todos:
            nk = norm_todo_id(x.get("id"))
            if nk:
                by_id[nk] = x
        v = str(st.session_state.get("dash_todo_dlg_view") or "").strip()
        e = str(st.session_state.get("dash_todo_dlg_edit") or "").strip()
        d = str(st.session_state.get("dash_todo_dlg_del") or "").strip()
        vn = norm_todo_id(v)
        en = norm_todo_id(e)
        dn = norm_todo_id(d)
        if vn and vn in by_id:
            dash_todo_view_dialog(row=dict(by_id[vn]), id_to_label=id_to_label)
        elif en and en in by_id:
            dash_todo_edit_dialog(
                row=dict(by_id[en]),
                id_to_label=id_to_label,
                ordered_ids=ordered_ids,
                me=me,
            )
        elif dn and dn in by_id:
            dash_todo_delete_dialog(tid=str(by_id[dn].get("id") or "").strip(), title=str(by_id[dn].get("title") or "—"))
        elif st.session_state.get("dash_todo_open_add"):
            dash_todo_add_dialog(id_to_label=id_to_label, ordered_ids=ordered_ids, me=me)
