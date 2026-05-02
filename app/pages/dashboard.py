from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st
from auth import current_profile, current_role
from branding import render_header
from data_cache import fetch_table_for_session

try:
    from app.db import create_signed_url, delete_rows_admin, fetch_table_admin, insert_row_admin, update_rows_admin
except ImportError:
    from db import create_signed_url, delete_rows_admin, fetch_table_admin, insert_row_admin, update_rows_admin  # type: ignore

try:
    from app.services.job_service import job_number_display, job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from services.job_service import job_number_display, job_row_select_label, sort_jobs_by_number_then_name  # type: ignore

try:
    from app.ui import IPS_NAV_PENDING_KEY, role_can_open_page
except ImportError:
    from ui import IPS_NAV_PENDING_KEY, role_can_open_page  # type: ignore

try:
    from app.services.supervisor_daily_reports import (
        dashboard_daily_report_snapshot,
        fetch_all_reports_since,
        labor_hours_actual_by_job,
    )
except ImportError:
    from services.supervisor_daily_reports import (  # type: ignore
        dashboard_daily_report_snapshot,
        fetch_all_reports_since,
        labor_hours_actual_by_job,
    )

try:
    from app.services import task_photos as _dash_task_photos
except ImportError:
    import services.task_photos as _dash_task_photos  # type: ignore

try:
    from app.ui.field_light_theme import inject_field_light_theme as _dash_field_light_theme
except ImportError:
    from ui.field_light_theme import inject_field_light_theme as _dash_field_light_theme  # type: ignore

try:
    from app.services.supervisor_planning import (
        dashboard_task_progress_snapshot,
        repeated_task_review_delay_reasons,
        task_row_active_for_dashboard,
    )
except ImportError:
    from services.supervisor_planning import (  # type: ignore
        dashboard_task_progress_snapshot,
        repeated_task_review_delay_reasons,
        task_row_active_for_dashboard,
    )


def _render_task_progress_dashboard(*, today: date, session_key: str, use_admin: bool) -> None:
    try:
        tasks = fetch_table_for_session(
            "job_tasks",
            session_key=session_key,
            limit=12000,
            order_by="planned_date",
            use_admin=use_admin,
        )
    except Exception:
        tasks = []
    if not tasks:
        return
    try:
        daily_plans = fetch_table_for_session(
            "supervisor_daily_task_plans",
            session_key=session_key,
            limit=12000,
            order_by="work_date",
            use_admin=use_admin,
        )
    except Exception:
        daily_plans = []
    try:
        daily_reviews = fetch_table_for_session(
            "job_task_daily_reviews",
            session_key=session_key,
            limit=12000,
            order_by="review_date",
            use_admin=use_admin,
        )
    except Exception:
        daily_reviews = []
    tp_new: list[dict[str, Any]] = []
    try:
        tp_new = fetch_table_for_session(
            "task_photos",
            session_key=session_key,
            limit=12000,
            order_by="created_at",
            use_admin=use_admin,
        )
    except Exception:
        tp_new = []
    try:
        task_photo_rows_legacy = fetch_table_for_session(
            "job_task_photos",
            session_key=session_key,
            limit=12000,
            order_by="created_at",
            use_admin=use_admin,
        )
    except Exception:
        task_photo_rows_legacy = []
    task_photo_rows: list[dict[str, Any]] = []
    for r in tp_new or []:
        if isinstance(r, dict):
            task_photo_rows.append({**r, "storage_path": str(r.get("file_url") or r.get("storage_path") or "")})
    task_photo_rows.extend([x for x in (task_photo_rows_legacy or []) if isinstance(x, dict)])
    active = [t for t in (tasks or []) if isinstance(t, dict) and task_row_active_for_dashboard(t, today=today)]
    active_ids = {str(t.get("id") or "").strip() for t in active if str(t.get("id") or "").strip()}
    photos_for_active = [
        r
        for r in (task_photo_rows or [])
        if isinstance(r, dict) and str(r.get("task_id") or "").strip() in active_ids
    ]
    by_tid: dict[str, list[dict[str, Any]]] = {}
    for r in photos_for_active:
        tid = str((r or {}).get("task_id") or "").strip()
        if tid:
            by_tid.setdefault(tid, []).append(r)
    ts = dashboard_task_progress_snapshot(
        today=today,
        tasks=active,
        daily_plans=list(daily_plans or []),
        active_task_ids=active_ids,
        photo_rows=list(task_photo_rows or []),
    )
    repeat = repeated_task_review_delay_reasons(list(daily_reviews or []), today=today)
    _dash_field_light_theme()
    with st.container(border=True):
        st.markdown("##### Tasks today")
        st.caption(
            "Active work only. Run **`sql/053_task_photos.sql`** and create bucket **task-photos** for new photo storage."
        )
        c1, c2, c3, c4 = st.columns(4, gap="small")
        c1.metric("Planned today", f"{ts.get('planned_today', 0):,}")
        c2.metric("Completed today", f"{ts.get('completed_today', 0):,}")
        c3.metric("Blocked", f"{ts.get('blocked', 0):,}")
        c4.metric("Missing after photos", f"{ts.get('missing_after_photo', 0):,}")
        if repeat:
            st.caption("Repeat delay reasons (14d): " + " · ".join(f"{a} ({b}×)" for a, b in repeat[:6])[:400])
        if role_can_open_page(current_role(), "Daily Tasks"):
            if st.button("Open Daily Tasks", key="dash_tasks_plan_open"):
                st.session_state[IPS_NAV_PENDING_KEY] = "Daily Tasks"
                st.rerun()


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


# Days out for dashboard "Who Has What" (match tool_dashboard overdue rule).
_DASH_OUT_OVERDUE_DAYS = 7
_KIT_REPL_WINDOW_DAYS = 90
_KIT_REPL_HOT_THRESHOLD = 3


def _dash_kf(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        s = str(v).strip()
        if not s:
            return default
        return float(s)
    except Exception:
        return default


def _kit_line_short_qty(it: dict) -> float:
    exp = _dash_kf((it or {}).get("quantity"))
    qoh = (it or {}).get("quantity_on_hand")
    if qoh is not None and str(qoh).strip() != "":
        return max(0.0, exp - _dash_kf(qoh))
    return max(0.0, _dash_kf((it or {}).get("missing_count")))


def _render_kit_theft_alerts_dashboard(
    assets: list[dict],
    kit_items: list[dict],
    replacements: list[dict],
    *,
    role: str,
) -> None:
    """Tool trailer kit lines: shortages, replacement churn, estimated missing value."""
    if not role_can_open_page(role, "Asset Database"):
        return
    trailers = {
        str(a.get("id") or "").strip(): a
        for a in (assets or [])
        if isinstance(a, dict) and str(a.get("asset_type") or "").strip().lower() == "tool trailer"
    }
    if not trailers:
        return
    tids = set(trailers.keys())
    lines = [
        it
        for it in (kit_items or [])
        if isinstance(it, dict)
        and str(it.get("parent_asset_id") or "").strip() in tids
        and bool((it or {}).get("is_active", True))
    ]
    now = datetime.now(timezone.utc).date()
    start = now - timedelta(days=_KIT_REPL_WINDOW_DAYS)
    repl_90: list[dict] = []
    for r in replacements or []:
        if not isinstance(r, dict):
            continue
        ds = str(r.get("replacement_date") or "").strip()[:10]
        if not ds:
            continue
        try:
            d = datetime.fromisoformat(ds).date()
        except ValueError:
            continue
        if d >= start:
            repl_90.append(r)
    n_repl_90 = len(repl_90)
    c_item = Counter(str(r.get("kit_item_id") or "").strip() for r in repl_90 if str(r.get("kit_item_id") or "").strip())
    n_hot = sum(1 for _k, v in c_item.items() if v >= _KIT_REPL_HOT_THRESHOLD)
    n_short_lines = sum(1 for it in lines if _kit_line_short_qty(it) > 0.0001)
    miss_val = sum(_kit_line_short_qty(it) * _dash_kf(it.get("replacement_cost")) for it in lines)

    with st.container(border=True):
        st.markdown("##### Kit theft / audit signals")
        st.caption(
            f"Tool trailer kit lines only. **Hot items** = ≥{_KIT_REPL_HOT_THRESHOLD} replacement rows in the last "
            f"{_KIT_REPL_WINDOW_DAYS} days. Missing value uses shortage × replacement cost."
        )
        m1, m2, m3, m4 = st.columns(4, gap="small")
        m1.metric("Kit lines with shortage", f"{n_short_lines:,}")
        m2.metric(f"Replacements ({_KIT_REPL_WINDOW_DAYS}d)", f"{n_repl_90:,}")
        m3.metric("Hot kit items (90d)", f"{n_hot:,}")
        m4.metric("Est. missing value", f"${miss_val:,.0f}")
        if n_short_lines or n_hot:
            st.warning("Review **Asset Database** → open a **Tool Trailer** → **Tool Kits** → **Count / Audit Kit**.")
        if role_can_open_page(role, "Asset Database"):
            if st.button("Open Asset Database", key="dash_kit_open_adb", help="Manage trailers and kit audits"):
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Database"
                st.rerun()


def _parse_co_ts(v: Any) -> datetime | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _days_out_value(last_co: Any) -> float | None:
    dt = _parse_co_ts(last_co)
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 86400.0)


def _asset_is_out(row: dict) -> bool:
    stt = str((row or {}).get("status") or "").strip()
    holder = str((row or {}).get("current_holder_employee_id") or "").strip()
    return stt == "Checked Out" or bool(holder)


def _render_who_has_what_dashboard(
    assets: list[dict],
    jobs: list[dict],
    employees: list[dict],
    *,
    role: str,
) -> None:
    """Summary of assets that are checked out or have a holder (see assets table)."""
    rows = [a for a in (assets or []) if isinstance(a, dict) and _asset_is_out(a)]
    jobs_sorted = sort_jobs_by_number_then_name(list(jobs or []))
    job_by_id = {str(j.get("id")): j for j in jobs_sorted if j.get("id")}
    emp_id_to_name = {
        str(e["id"]): str(e.get("name") or "").strip() or "—"
        for e in (employees or [])
        if isinstance(e, dict) and e.get("id")
    }

    n_out = len(rows)
    n_overdue = 0
    n_on_job = 0
    for r in rows:
        if str(r.get("assigned_job_id") or "").strip():
            n_on_job += 1
        dv = _days_out_value(r.get("last_checkout_at"))
        if dv is not None and dv > _DASH_OUT_OVERDUE_DAYS:
            n_overdue += 1

    with st.container(border=True):
        st.markdown("##### Who Has What")
        st.caption("Tools and assets with **Checked Out** status or an assigned holder.")

        m1, m2, m3 = st.columns(3, gap="small")
        m1.metric("Checked out tools", f"{n_out:,}")
        m2.metric("Overdue tools", f"{n_overdue:,}")
        m3.metric("Assigned to jobs", f"{n_on_job:,}")

        if not rows:
            st.caption("Nothing checked out or held right now.")
        else:
            disp: list[dict] = []
            for r in rows:
                eid = str(r.get("current_holder_employee_id") or "").strip()
                holder = emp_id_to_name.get(eid) or str(r.get("assigned_employee") or "").strip() or "—"
                jid = r.get("assigned_job_id")
                jl = "—"
                if jid and str(jid).strip() in job_by_id:
                    jl = job_row_select_label(job_by_id[str(jid).strip()])
                co = _parse_co_ts(r.get("last_checkout_at"))
                co_s = co.strftime("%Y-%m-%d %H:%M") if co else "—"
                dv = _days_out_value(r.get("last_checkout_at"))
                days_s = f"{int(dv)} d" if dv is not None and dv >= 1.0 else (f"{dv:.1f} d" if dv is not None else "—")
                disp.append(
                    {
                        "Tool / asset": str(r.get("asset_name") or "—").strip() or "—",
                        "Holder": holder,
                        "Job": jl,
                        "Checked out": co_s,
                        "Days out": days_s,
                        "Status": str(r.get("status") or "").strip() or "—",
                    }
                )
            df = pd.DataFrame(disp)
            df["_sort"] = [_days_out_value(x.get("last_checkout_at")) for x in rows]
            df = df.sort_values(by="_sort", ascending=False, na_position="last").drop(
                columns=["_sort"], errors="ignore"
            )
            st.dataframe(df, use_container_width=True, hide_index=True, height=min(420, 44 + 36 * len(df)))

        if role_can_open_page(role, "Who Has What"):
            if st.button("View all", key="dash_whw_view_all", help="Open the full Who Has What page"):
                st.session_state[IPS_NAV_PENDING_KEY] = "Who Has What"
                st.rerun()


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


def _render_supervisor_daily_reports_dashboard(
    *,
    today: date,
    jobs: list[dict],
    estimates: list[dict],
    session_key: str,
    use_admin: bool,
) -> None:
    """Supervisor daily report KPIs (requires ``sql/045_supervisor_daily_reports.sql``)."""
    try:
        since = today - timedelta(days=14)
        reports_recent = fetch_all_reports_since(since, admin=use_admin, limit=4000)
    except Exception:
        reports_recent = []
    t_iso = today.isoformat()[:10]
    reports_today = [r for r in reports_recent if isinstance(r, dict) and str(r.get("report_date") or "")[:10] == t_iso]
    try:
        te_rows = fetch_table_for_session(
            "time_entries",
            session_key=session_key,
            limit=20000,
            order_by=None,
            use_admin=use_admin,
        )
    except Exception:
        te_rows = []
    hours_by_job = labor_hours_actual_by_job(list(te_rows or []))
    estimates_by_id = {str(e.get("id")): e for e in (estimates or []) if isinstance(e, dict) and e.get("id")}
    snap = dashboard_daily_report_snapshot(
        today=today,
        jobs=list(jobs or []),
        reports_today=reports_today,
        reports_recent=list(reports_recent or []),
        hours_by_job=hours_by_job,
        estimates_by_id=estimates_by_id,
    )
    with st.container(border=True):
        st.markdown("##### Supervisor daily reports")
        st.caption("Field submissions from **Supervisor Daily Reports** and **Job Database** → Daily Reports.")
        d1, d2, d3, d4, d5 = st.columns(5, gap="small")
        d1.metric("Reports today", f"{snap['submitted_today']:,}")
        d2.metric("Missing today (active jobs)", f"{snap['missing_reports']:,}")
        d3.metric("Jobs w/ delays (14d)", f"{snap['jobs_with_delays']:,}")
        pairs = snap.get("repeated_delay_reasons") or []
        if pairs:
            lbl, n = pairs[0]
            short = (lbl[:26] + "…") if len(lbl) > 27 else lbl
            d4.metric(f"Top delay: {short}", f"{n:,}")
            if len(pairs) > 1:
                d4.caption(" · ".join(f"{a} ({b})" for a, b in pairs[1:4])[:200])
        else:
            d4.metric("Top delay (14d)", "—")
        d5.metric("Jobs over bid labor hrs", f"{len(snap['jobs_over_labor']):,}")
        if snap.get("missing_sample_labels") and snap["missing_reports"] > 0:
            st.caption("Examples: " + ", ".join(snap["missing_sample_labels"][:6]))
        if snap["jobs_over_labor"]:
            rows = [{"Job": lab, "Bid hrs": f"{est:.1f}", "Actual hrs": f"{act:.1f}"} for _jid, lab, est, act in snap["jobs_over_labor"][:10]]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=min(220, 40 + 28 * len(rows)))
        if role_can_open_page(current_role(), "Supervisor Daily Reports"):
            if st.button("Open Supervisor Daily Reports", key="dash_sdr_open"):
                st.session_state[IPS_NAV_PENDING_KEY] = "Supervisor Daily Reports"
                st.rerun()


def render() -> None:
    render_header(
        "IPS Dashboard",
        subtitle="Industrial Plant Solutions, LLC",
        help_text="A simple snapshot for office + field: jobs, low stock, checked-out tools, and your to-dos.",
    )

    sk = str(current_profile().get("id") or "anonymous")
    use_admin = current_role() in {"admin", "manager"}
    _lim = 5000
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
    try:
        assets = fetch_table_for_session(
            "assets", session_key=sk, limit=_lim, order_by="asset_name", use_admin=use_admin
        )
    except Exception:
        assets = []
    inv_rows: list[dict] = []
    if role_can_open_page(current_role(), "Inventory"):
        try:
            inv_rows = fetch_table_for_session(
                "inventory_items",
                session_key=sk,
                limit=12000,
                order_by="item_name",
                use_admin=use_admin,
            )
        except Exception:
            inv_rows = []

    low_n = 0
    if inv_rows:
        try:
            df_inv = pd.DataFrame(inv_rows)
            if "is_active" in df_inv.columns:
                df_inv = df_inv[df_inv["is_active"] != False]  # noqa: E712
            qoh = pd.to_numeric(df_inv.get("quantity_on_hand", 0), errors="coerce").fillna(0)
            rp = pd.to_numeric(df_inv.get("reorder_point", 0), errors="coerce").fillna(0)
            low_n = int((qoh <= rp).sum())
        except Exception:
            low_n = 0
    out_n = sum(
        1
        for a in (assets or [])
        if str((a or {}).get("status") or "").strip() == "Checked Out"
        or str((a or {}).get("current_holder_employee_id") or "").strip()
    )
    try:
        todos = fetch_table_for_session("todos", session_key=sk, limit=2000, order_by="created_at", use_admin=use_admin)
        open_todos = sum(1 for t in (todos or []) if str((t or {}).get("status") or "Open").strip() != "Complete")
    except Exception:
        open_todos = 0

    _dash_field_light_theme()
    with st.container(border=True):
        st.markdown("##### Operations snapshot")
        m3, m4, m5 = st.columns(3, gap="small")
        m3.metric("Low stock items", f"{low_n:,}")
        m4.metric("Checked out tools", f"{out_n:,}")
        m5.metric("Open to-dos", f"{open_todos:,}")

    _render_task_progress_dashboard(today=date.today(), session_key=sk, use_admin=use_admin)

    _render_supervisor_daily_reports_dashboard(
        today=date.today(),
        jobs=list(jobs or []),
        estimates=list(estimates or []),
        session_key=sk,
        use_admin=use_admin,
    )

    _render_who_has_what_dashboard(
        list(assets or []),
        list(jobs or []),
        list(employees or []),
        role=current_role(),
    )

    # Low stock alerts (keep simple; details belong on Inventory page).
    if inv_rows and low_n > 0:
        try:
            df_inv2 = pd.DataFrame(inv_rows)
            if "is_active" in df_inv2.columns:
                df_inv2 = df_inv2[df_inv2["is_active"] != False]  # noqa: E712
            qoh2 = pd.to_numeric(df_inv2.get("quantity_on_hand", 0), errors="coerce").fillna(0)
            rp2 = pd.to_numeric(df_inv2.get("reorder_point", 0), errors="coerce").fillna(0)
            low_df = df_inv2.loc[qoh2 <= rp2, :].copy()
            show_cols = [c for c in ("item_name", "sku", "category", "quantity_on_hand", "reorder_point") if c in low_df.columns]
            if show_cols:
                disp = low_df[show_cols].copy()
                disp = disp.rename(
                    columns={
                        "item_name": "Item",
                        "quantity_on_hand": "On Hand",
                        "reorder_point": "Reorder",
                        "unit_cost": "Unit Cost",
                        "qr_code_value": "QR Code",
                    }
                )
                with st.container(border=True):
                    st.markdown("##### Low Stock Alerts")
                    st.caption("Items at or below reorder point (based on current on-hand vs reorder settings).")
                    st.dataframe(disp, use_container_width=True, hide_index=True, height=min(360, 44 + 30 * len(disp)))
        except Exception:
            pass

    _render_todo_list(session_key=sk, use_admin=use_admin)

    st.markdown("##### Recent jobs")
    rj = _recent_jobs_rows(list(jobs or []))
    if not rj:
        st.caption("No jobs loaded yet.")
    else:
        st.dataframe(_jobs_display_df(rj), use_container_width=True, hide_index=True, height=320)
