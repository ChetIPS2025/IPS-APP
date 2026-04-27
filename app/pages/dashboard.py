from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st
from auth import current_profile, current_role
from branding import render_header
from data_cache import fetch_table_for_session

try:
    from app.db import delete_rows_admin, fetch_table_admin, insert_row_admin, update_rows_admin
except ImportError:
    from db import delete_rows_admin, fetch_table_admin, insert_row_admin, update_rows_admin  # type: ignore

try:
    from app.services.job_service import job_number_display
except ImportError:
    from services.job_service import job_number_display  # type: ignore


def _norm_status(v) -> str:
    return " ".join(str(v or "").strip().split()).casefold()


_AWARDED_STATUS_TOKENS = {
    "awarded",
    "won",
    "active",
}

_BIDDING_STATUS_TOKENS = {
    "bidding",
    "estimating",
    "proposal",
    "quoted",
    # Job Database lifecycle (pre-award / in-flight work) — title-cased in DB, matched case-insensitively
    "draft",
    "submitted",
    "approved",
    "scheduled",
    "in progress",
    "on hold",
}


def _job_status_bucket(status_value) -> str | None:
    """
    Centralized job status normalization + classification.

    - trims whitespace and compares case-insensitively
    - treats substring matches as valid (handles inconsistent status text)
    - returns: "awarded" | "bidding" | None
    """
    s = _norm_status(status_value)
    if not s:
        return None
    if s in _AWARDED_STATUS_TOKENS or any(tok in s for tok in _AWARDED_STATUS_TOKENS):
        return "awarded"
    if s in _BIDDING_STATUS_TOKENS or any(tok in s for tok in _BIDDING_STATUS_TOKENS):
        return "bidding"
    return None


def count_awarded_jobs(jobs: list[dict]) -> int:
    return sum(1 for j in (jobs or []) if _job_status_bucket((j or {}).get("status")) == "awarded")


def count_bidding_jobs(jobs: list[dict]) -> int:
    return sum(1 for j in (jobs or []) if _job_status_bucket((j or {}).get("status")) == "bidding")


def count_active_employees(employees: list[dict]) -> int:
    rows = employees or []
    if not rows:
        return 0
    has_is_active = any(isinstance(r, dict) and "is_active" in r for r in rows)
    if not has_is_active:
        return len(rows)
    return sum(1 for r in rows if bool((r or {}).get("is_active", False)))


def _row_ts(row: dict) -> str:
    for k in ("updated_at", "modified_at", "created_at"):
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _recent_jobs_rows(jobs: list[dict], *, limit: int = 12) -> list[dict]:
    if not jobs:
        return []
    rows = sorted(jobs, key=_row_ts, reverse=True)
    return rows[:limit]


def _recent_estimates_rows(estimates: list[dict], *, limit: int = 12) -> list[dict]:
    if not estimates:
        return []
    rows = sorted(estimates, key=_row_ts, reverse=True)
    return rows[:limit]


def _jobs_display_df(rows: list[dict]) -> pd.DataFrame:
    out: list[dict] = []
    for j in rows:
        if not isinstance(j, dict):
            continue
        jn = job_number_display(j.get("job_number"))
        out.append(
            {
                "Job #": jn or "—",
                "Name": str(j.get("job_name") or "").strip() or "—",
                "Status": str(j.get("status") or "").strip() or "—",
            }
        )
    return pd.DataFrame(out)


def _estimates_display_df(rows: list[dict]) -> pd.DataFrame:
    out: list[dict] = []
    for e in rows:
        if not isinstance(e, dict):
            continue
        ts = _row_ts(e)
        ts_disp = ts[:19].replace("T", " ") if ts else "—"
        try:
            if "T" in ts and len(ts) >= 10:
                ts_disp = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        except Exception:
            ts_disp = ts[:16] if ts else "—"
        out.append(
            {
                "Quote": str(e.get("quote_number") or "").strip() or "—",
                "Status": str(e.get("status") or "").strip() or "—",
                "Updated": ts_disp,
            }
        )
    return pd.DataFrame(out)

_TODO_STATUSES = ("Open", "In Progress", "Complete")
_TODO_PRIORITIES = ("Low", "Normal", "High", "Urgent")
_TODO_PRIORITY_RANK = {"Urgent": 0, "High": 1, "Normal": 2, "Low": 3}


def _todo_priority_rank(v: str) -> int:
    return int(_TODO_PRIORITY_RANK.get(str(v or "Normal").strip().title(), 9))


def _todo_due_sort_key(v) -> tuple[int, str]:
    """None due dates sort last."""
    if v is None or str(v).strip() == "":
        return (1, "9999-12-31")
    s = str(v).strip()
    return (0, s)


def _profiles_for_todo_assign(session_key: str, *, use_admin: bool) -> tuple[dict[str, str], list[str]]:
    """Return (id->label, ordered_ids) for assigned_to choices."""
    try:
        profs = fetch_table_for_session(
            "profiles",
            session_key=session_key,
            limit=5000,
            order_by="email",
            use_admin=use_admin,
        )
    except Exception:
        profs = []
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


def _render_todo_list(*, session_key: str, use_admin: bool) -> None:
    prof = current_profile()
    me = str(prof.get("id") or "").strip()

    with st.container(border=True):
        st.markdown("##### To-Do List")

        # Filters
        f1, f2 = st.columns([1.2, 1.8], gap="small")
        scope = f1.selectbox("Filter", ["My tasks", "All open tasks", "Completed"], key="dash_todo_scope")
        show_completed = scope == "Completed"

        id_to_label, ordered_ids = _profiles_for_todo_assign(session_key, use_admin=use_admin)
        assignee_pick = None
        if scope == "My tasks" and me:
            assignee_pick = me

        # Fetch todos (prefer admin for office roles; falls back through db helper if needed)
        try:
            todos = fetch_table_for_session(
                "todos",
                session_key=session_key,
                limit=2000,
                order_by="created_at",
                use_admin=use_admin,
            )
        except Exception:
            todos = []

        rows: list[dict] = []
        for t in todos or []:
            if not isinstance(t, dict):
                continue
            status = str(t.get("status") or "Open").strip() or "Open"
            if show_completed:
                if status != "Complete":
                    continue
            else:
                if status == "Complete":
                    continue
            if assignee_pick and str(t.get("assigned_to") or "").strip() != assignee_pick:
                continue
            rows.append(t)

        # Sort: urgent first, then due date
        rows.sort(
            key=lambda r: (
                _todo_priority_rank(str(r.get("priority") or "Normal")),
                _todo_due_sort_key(r.get("due_date")),
                str(r.get("created_at") or ""),
            )
        )

        # Add task UI
        with st.expander("Add task", expanded=False):
            title = st.text_input("Title", key="dash_todo_add_title")
            desc = st.text_area("Description", key="dash_todo_add_desc", height=72)
            c1, c2, c3 = st.columns(3, gap="small")
            due = c1.date_input("Due date", value=None, key="dash_todo_add_due")
            priority = c2.selectbox("Priority", list(_TODO_PRIORITIES), index=1, key="dash_todo_add_pri")
            status = c3.selectbox("Status", list(_TODO_STATUSES), index=0, key="dash_todo_add_status")
            assignee_opts = ["— Unassigned —"] + [id_to_label[i] for i in ordered_ids]
            assignee_label = st.selectbox("Assigned to", assignee_opts, key="dash_todo_add_assignee")
            assigned_to = None
            if assignee_label and not assignee_label.startswith("—"):
                for pid, lbl in id_to_label.items():
                    if lbl == assignee_label:
                        assigned_to = pid
                        break

            if st.button("Add task", type="primary", use_container_width=True, key="dash_todo_add_btn"):
                t = str(title or "").strip()
                if not t:
                    st.error("Title is required.")
                    st.stop()
                payload = {
                    "title": t,
                    "description": str(desc or "").strip() or None,
                    "priority": str(priority or "Normal").strip() or "Normal",
                    "status": str(status or "Open").strip() or "Open",
                    "created_by": me or None,
                    "assigned_to": assigned_to,
                }
                if due is not None:
                    payload["due_date"] = str(due)
                insert_row_admin("todos", payload)
                st.success("Task added.")
                st.rerun()

        if not rows:
            st.caption("No tasks to show.")
            return

        st.caption("Urgent tasks sort first. Completed tasks are hidden by default.")

        for t in rows:
            tid = str(t.get("id") or "").strip()
            if not tid:
                continue
            title = str(t.get("title") or "").strip() or "—"
            priority = str(t.get("priority") or "Normal").strip() or "Normal"
            status = str(t.get("status") or "Open").strip() or "Open"
            due = str(t.get("due_date") or "").strip() or "—"
            assigned_to = str(t.get("assigned_to") or "").strip()
            assigned_lbl = id_to_label.get(assigned_to, "—")

            r1, r2, r3, r4, r5 = st.columns([0.55, 3.4, 1.1, 1.3, 1.7], gap="small")
            with r1:
                done = st.checkbox(" ", value=False, key=f"todo_done_{tid}")
            with r2:
                st.markdown(f"**{title}**")
                if status and status != "Open":
                    st.caption(status)
            with r3:
                st.caption(priority)
            with r4:
                st.caption(due)
            with r5:
                st.caption(assigned_lbl)

            if done and status != "Complete":
                update_rows_admin(
                    "todos",
                    {"status": "Complete", "completed_at": datetime.utcnow().isoformat()},
                    {"id": tid},
                )
                st.rerun()

            with st.expander("Edit / details", expanded=False):
                et = st.text_input("Title", value=title, key=f"todo_edit_title_{tid}")
                ed = st.text_area("Description", value=str(t.get("description") or ""), key=f"todo_edit_desc_{tid}", height=72)
                c1, c2, c3 = st.columns(3, gap="small")
                # date_input can't take an arbitrary string; keep it optional via text to avoid crash
                due_s = c1.text_input("Due date (YYYY-MM-DD)", value="" if due == "—" else due, key=f"todo_edit_due_{tid}")
                epri = c2.selectbox("Priority", list(_TODO_PRIORITIES), index=max(0, list(_TODO_PRIORITIES).index(priority)) if priority in _TODO_PRIORITIES else 1, key=f"todo_edit_pri_{tid}")
                estat = c3.selectbox("Status", list(_TODO_STATUSES), index=max(0, list(_TODO_STATUSES).index(status)) if status in _TODO_STATUSES else 0, key=f"todo_edit_status_{tid}")
                assignee_opts = ["— Unassigned —"] + [id_to_label[i] for i in ordered_ids]
                cur_assignee_lbl = id_to_label.get(assigned_to, "— Unassigned —") if assigned_to else "— Unassigned —"
                assignee_label = st.selectbox("Assigned to", assignee_opts, index=max(0, assignee_opts.index(cur_assignee_lbl)) if cur_assignee_lbl in assignee_opts else 0, key=f"todo_edit_asg_{tid}")
                new_assigned_to = None
                if assignee_label and not assignee_label.startswith("—"):
                    for pid, lbl in id_to_label.items():
                        if lbl == assignee_label:
                            new_assigned_to = pid
                            break

                b1, b2 = st.columns(2, gap="small")
                with b1:
                    if st.button("Save", type="primary", use_container_width=True, key=f"todo_save_{tid}"):
                        payload: dict = {
                            "title": str(et or "").strip() or "—",
                            "description": str(ed or "").strip() or None,
                            "priority": str(epri or "Normal").strip() or "Normal",
                            "status": str(estat or "Open").strip() or "Open",
                            "assigned_to": new_assigned_to,
                        }
                        ds = str(due_s or "").strip()
                        payload["due_date"] = ds if ds else None
                        if payload["status"] == "Complete":
                            payload["completed_at"] = datetime.utcnow().isoformat()
                        update_rows_admin("todos", payload, {"id": tid})
                        st.success("Saved.")
                        st.rerun()
                with b2:
                    if st.button("Delete", type="secondary", use_container_width=True, key=f"todo_del_{tid}"):
                        delete_rows_admin("todos", {"id": tid})
                        st.success("Deleted.")
                        st.rerun()


def render() -> None:
    render_header(
        "IPS Dashboard",
        subtitle="Industrial Plant Solutions, LLC",
        help_text="Pipeline snapshot, customers on file, and recent jobs and estimates — use the sidebar for every module.",
    )

    sk = str(current_profile().get("id") or "anonymous")
    use_admin = current_role() in {"admin", "pm"}
    _lim = 5000
    try:
        customers = fetch_table_for_session(
            "customers", session_key=sk, limit=_lim, order_by="customer_name", use_admin=use_admin
        )
    except Exception:
        customers = []
    try:
        jobs = fetch_table_for_session(
            "jobs", session_key=sk, limit=_lim, order_by="job_number", use_admin=use_admin
        )
    except Exception:
        jobs = []
    try:
        estimates = fetch_table_for_session(
            "estimates", session_key=sk, limit=_lim, order_by="quote_number", use_admin=use_admin
        )
    except Exception:
        estimates = []
    try:
        employees = fetch_table_for_session(
            "employees", session_key=sk, limit=_lim, order_by="name", use_admin=use_admin
        )
    except Exception:
        employees = []

    with st.container(border=True):
        st.markdown('<span class="ips-dash-metrics"></span>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4, gap="small")
        c1.metric("Customers", len(customers or []))
        c2.metric("Jobs awarded", count_awarded_jobs(jobs))
        c3.metric("Jobs bidding", count_bidding_jobs(jobs))
        c4.metric("Active employees", count_active_employees(employees))

    _render_todo_list(session_key=sk, use_admin=use_admin)

    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown("##### Recent jobs")
        rj = _recent_jobs_rows(list(jobs or []))
        if not rj:
            st.caption("No jobs loaded yet.")
        else:
            st.dataframe(_jobs_display_df(rj), use_container_width=True, hide_index=True, height=320)

    with right:
        st.markdown("##### Recent estimates")
        re = _recent_estimates_rows(list(estimates or []))
        if not re:
            st.caption("No estimates loaded yet.")
        else:
            st.dataframe(_estimates_display_df(re), use_container_width=True, hide_index=True, height=320)
