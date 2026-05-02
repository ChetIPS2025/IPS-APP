"""Daily Tasks — plan work by task, assign supervisors (PM), end-of-day review."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import streamlit as st

from auth import current_profile, current_role
from branding import render_header
from data_cache import fetch_table_for_session

try:
    from app.db import delete_rows, fetch_by_match, insert_row, update_rows
except ImportError:
    from db import delete_rows, fetch_by_match, insert_row, update_rows  # type: ignore

try:
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore


try:
    from app.pages import job_database_task_photos_ui as _dt_task_photos_ui
except ImportError:
    import pages.job_database_task_photos_ui as _dt_task_photos_ui  # type: ignore

try:
    from app.pages import job_database_mobile_task_ui as _mob
except ImportError:
    import pages.job_database_mobile_task_ui as _mob  # type: ignore

try:
    from app.ui.field_light_theme import inject_field_light_theme
except ImportError:
    from ui.field_light_theme import inject_field_light_theme  # type: ignore

_LOG = logging.getLogger(__name__)

def _is_pm() -> bool:
    """Office roles that can assign supervisors and use elevated reads (see ``current_role()`` normalization)."""
    return current_role() in {"admin", "manager"}


def _session_key() -> str:
    return str(current_profile().get("id") or "anonymous")


def _fetch_table(name: str, *, use_admin: bool) -> list[dict[str, Any]]:
    try:
        return fetch_table_for_session(
            name,
            session_key=_session_key(),
            limit=8000,
            order_by="created_at",
            use_admin=use_admin,
        )
    except Exception as exc:
        _LOG.debug("fetch %s: %s", name, exc)
        return []


def _job_options(jobs: list[dict[str, Any]]) -> tuple[list[str], dict[str, str]]:
    rows = [j for j in (jobs or []) if isinstance(j, dict) and str(j.get("id") or "").strip()]
    rows = sort_jobs_by_number_then_name(rows)
    labels = [job_row_select_label(j) for j in rows]
    m = {job_row_select_label(j): str(j.get("id")) for j in rows}
    return labels, m


def _task_label(t: dict[str, Any]) -> str:
    iss = str(t.get("issue") or "")
    disp = (iss[:40] + "…") if len(iss) > 40 else (iss or "—")
    return f"{t.get('task_number') or '—'}/{t.get('hazard_number') or '—'} · {disp}"


def render() -> None:
    render_header(
        "Daily Tasks",
        subtitle="Plan tasks by day, assign supervisors (PM), and record end-of-day status.",
    )
    use_admin = _is_pm()
    try:
        jobs = fetch_table_for_session(
            "jobs",
            session_key=_session_key(),
            limit=5000,
            order_by="job_number",
            use_admin=use_admin,
        )
    except Exception:
        jobs = []

    job_tasks = _fetch_table("job_tasks", use_admin=use_admin)
    daily_plans = _fetch_table("supervisor_daily_task_plans", use_admin=use_admin)
    daily_reviews = _fetch_table("job_task_daily_reviews", use_admin=use_admin)

    if not job_tasks and not daily_plans and not daily_reviews:
        try:
            fetch_table_for_session(
                "job_tasks",
                session_key=_session_key(),
                limit=1,
                order_by=None,
                use_admin=use_admin,
            )
        except Exception as exc:
            st.error(f"Job tasks are not available: {exc}")
            st.caption(
                "Run **`sql/048_job_tasks_planning_links.sql`** and **`sql/049_task_workflow.sql`** in Supabase, then refresh."
            )
            return

    labels, label_to_id = _job_options(list(jobs or []))
    today = date.today()

    with st.expander("PM: Assign supervisor to tasks", expanded=_is_pm()):
        if not _is_pm():
            st.caption("Project managers assign a field supervisor name to each task.")
        else:
            st.caption("Sets **assigned supervisor** on `job_tasks` (who owns the task in the field).")
            job_lb = st.selectbox("Job", options=labels or ["—"], key="dt_pm_job", disabled=not labels)
            jid = label_to_id.get(str(job_lb), "")
            t_for_job = [t for t in job_tasks if isinstance(t, dict) and str(t.get("job_id")) == str(jid)]
            if not jid:
                st.warning("Pick a job.")
            elif not t_for_job:
                st.caption("No tasks for this job — add tasks in **Job Database**.")
            else:
                for t in t_for_job:
                    tid = str(t.get("id") or "")
                    if not tid:
                        continue
                    cur = str(t.get("assigned_supervisor_name") or "")
                    row1, row2 = st.columns((3, 1), gap="small")
                    with row1:
                        st.markdown(f"**{_task_label(t)}**")
                    with row2:
                        new_sup = st.text_input(
                            "Supervisor",
                            value=cur,
                            key=f"dt_asgn_{tid}",
                            label_visibility="collapsed",
                            placeholder="Name",
                        )
                    if st.button("Save", key=f"dt_asgn_save_{tid}"):
                        try:
                            update_rows(
                                "job_tasks",
                                {
                                    "assigned_supervisor_name": " ".join(str(new_sup or "").split())[:200],
                                    "updated_at": datetime.now(timezone.utc).isoformat(),
                                },
                                {"id": tid},
                            )
                            st.success("Updated.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

    with st.expander("Plan tasks for a work day", expanded=True):
        st.caption("Supervisor picks which tasks the crew will touch **today** (or another date).")
        wdate = st.date_input("Work date", value=today, key="dt_plan_date")
        job_lb2 = st.selectbox("Job", options=labels or ["—"], key="dt_plan_job", disabled=not labels)
        jid2 = label_to_id.get(str(job_lb2), "")
        sup_plan = st.text_input("Supervisor name (for this plan)", key="dt_plan_sup", placeholder="Who is leading")
        t_for_job2 = [t for t in job_tasks if isinstance(t, dict) and str(t.get("job_id")) == str(jid2)]
        ids2 = [str(t.get("id") or "") for t in t_for_job2 if str(t.get("id") or "").strip()]
        w_iso = wdate.isoformat()[:10]
        existing = {
            str(p.get("task_id"))
            for p in daily_plans
            if isinstance(p, dict)
            and str(p.get("job_id")) == str(jid2)
            and str(p.get("work_date") or "")[:10] == w_iso
        }
        default_pick = [i for i in ids2 if i in existing]
        pick = st.multiselect(
            "Tasks planned for this date",
            options=ids2,
            default=[i for i in default_pick if i in ids2],
            format_func=lambda tid: _task_label(next((x for x in t_for_job2 if str(x.get("id")) == tid), {})),
            key="dt_plan_pick",
        )
        if st.button("Save daily plan", type="primary", key="dt_plan_save"):
            if not jid2:
                st.error("Pick a job.")
            elif not str(sup_plan or "").strip():
                st.error("Enter supervisor name.")
            else:
                try:
                    delete_rows("supervisor_daily_task_plans", {"job_id": jid2, "work_date": w_iso})
                    sn = " ".join(str(sup_plan or "").strip().split())[:200]
                    for tid in pick:
                        if not tid:
                            continue
                        insert_row(
                            "supervisor_daily_task_plans",
                            {
                                "job_id": jid2,
                                "work_date": w_iso,
                                "supervisor_name": sn,
                                "task_id": tid,
                            },
                        )
                    st.success("Plan saved.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    with st.expander("Daily review (per task)", expanded=True):
        inject_field_light_theme()
        st.caption("End of day: status, delay reason, and notes. Updates the task row and today’s review record.")
        rdate = st.date_input("Review date", value=today, key="dt_rev_date")
        job_lb3 = st.selectbox("Job", options=labels or ["—"], key="dt_rev_job", disabled=not labels)
        jid3 = label_to_id.get(str(job_lb3), "")
        sup_rev = st.text_input("Supervisor name (sign-off)", key="dt_rev_sup", placeholder="Who is filing this")
        r_iso = rdate.isoformat()[:10]
        t_for_job3 = [t for t in job_tasks if isinstance(t, dict) and str(t.get("job_id")) == str(jid3)]
        planned_ids = {
            str(p.get("task_id"))
            for p in daily_plans
            if isinstance(p, dict)
            and str(p.get("job_id")) == str(jid3)
            and str(p.get("work_date") or "")[:10] == r_iso
        }
        rev_by_task: dict[str, dict[str, Any]] = {}
        for rv in daily_reviews:
            if not isinstance(rv, dict):
                continue
            if str(rv.get("review_date") or "")[:10] != r_iso:
                continue
            tid = str(rv.get("task_id") or "").strip()
            if tid:
                rev_by_task[tid] = rv

        if not jid3:
            st.warning("Pick a job.")
        elif not t_for_job3:
            st.caption("No tasks for this job.")
        else:
            ordered = [t for t in t_for_job3 if str(t.get("id") or "") in planned_ids] + [
                t for t in t_for_job3 if str(t.get("id") or "") not in planned_ids
            ]
            st.caption("Tasks **planned for the review date** are listed first, then other tasks on the job.")
            try:
                _dt_task_photos_ui.render_daily_review_progress_strip(
                    job_id=str(jid3),
                    review_date=r_iso,
                    can_edit=True,
                    admin_read=use_admin,
                )
            except Exception as exc:
                st.caption(f"Shift photos unavailable ({exc}). Run **sql/051_job_task_photos.sql** if needed.")
            _mob.inject_mobile_field_css()
            for t in ordered:
                tid = str(t.get("id") or "")
                if not tid:
                    continue
                prior = rev_by_task.get(tid) or {}
                with st.container(border=True):
                    try:
                        _mob.render_daily_review_row_mobile(
                            job_id=str(jid3),
                            r_iso=r_iso,
                            task_row=t,
                            prior=prior,
                            sup_day=str(sup_rev or ""),
                            can_edit=True,
                            admin_read=use_admin,
                            ins=insert_row,
                            upd=update_rows,
                        )
                    except Exception as exc:
                        st.error(str(exc))
