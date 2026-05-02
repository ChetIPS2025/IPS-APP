"""PM Daily Work Packages vs supervisor execution (task-first workflow)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Callable

import streamlit as st

from auth import current_profile, current_role
from branding import render_header
from data_cache import fetch_table_for_session

try:
    from app.db import (
        fetch_by_match,
        fetch_by_match_admin,
        insert_row,
        insert_row_admin,
        update_rows,
        update_rows_admin,
    )
except ImportError:
    from db import (  # type: ignore
        fetch_by_match,
        fetch_by_match_admin,
        insert_row,
        insert_row_admin,
        update_rows,
        update_rows_admin,
    )

try:
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore

try:
    from app.pages import job_database_task_photos_ui as tph
except ImportError:
    import pages.job_database_task_photos_ui as tph  # type: ignore

try:
    from app.pages import job_database_mobile_task_ui as _mob
except ImportError:
    import pages.job_database_mobile_task_ui as _mob  # type: ignore

try:
    from app.ui.field_light_theme import inject_field_light_theme
except ImportError:
    from ui.field_light_theme import inject_field_light_theme  # type: ignore

try:
    from app.services import task_photos as tp
except ImportError:
    import services.task_photos as tp  # type: ignore

try:
    from app.services.supervisor_planning import TASK_STATUSES, delay_reason_label
except ImportError:
    from services.supervisor_planning import TASK_STATUSES, delay_reason_label  # type: ignore

_LOG = logging.getLogger(__name__)

_STATUS_LABELS: dict[str, str] = {
    "not_started": "Not started",
    "in_progress": "In progress",
    "complete": "Complete",
    "partial": "Partial",
    "blocked": "Blocked",
    "duplicate": "Duplicate",
    "electrical": "Electrical / trade",
    "waiting_on_customer": "Waiting on customer",
    "cancelled": "Cancelled",
}

_EOD_DELAY_SLUGS: tuple[str, ...] = (
    "none",
    "material",
    "tools",
    "direction",
    "rework",
    "customer",
    "safety",
    "equipment",
    "weather",
    "other",
)


def _is_pm() -> bool:
    return current_role() in {"admin", "manager"}


def _session_key() -> str:
    return str(current_profile().get("id") or "anonymous")


def _inject_field_touch_css() -> None:
    inject_field_light_theme()
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlock"] > div > div[data-testid="stButton"] button[kind="primary"] {
          min-height: 3rem !important;
          font-size: 1.05rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _fetch_table(name: str, *, use_admin: bool) -> list[dict[str, Any]]:
    try:
        return fetch_table_for_session(
            name,
            session_key=_session_key(),
            limit=12000,
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


def _profile_name_tokens() -> tuple[str, str]:
    prof = current_profile()
    fn = " ".join(str(prof.get("full_name") or "").split()).strip().lower()
    em = str(prof.get("email") or "").strip().lower()
    local = em.split("@", 1)[0] if em else ""
    return fn, local


def _plan_supervisor_matches(sup_on_plan: str) -> bool:
    sn = " ".join(str(sup_on_plan or "").split()).strip().lower()
    if not sn:
        return False
    fn, local = _profile_name_tokens()
    if fn and (sn in fn or fn in sn):
        return True
    if local and local in sn:
        return True
    return False


def _norm_task_status(st: str) -> str:
    s = str(st or "").strip().lower()
    if s == "open":
        return "not_started"
    return s


def _w_writes(use_admin: bool) -> tuple[Callable[..., Any], Callable[..., Any]]:
    if use_admin:
        return insert_row_admin, update_rows_admin
    return insert_row, update_rows


def _created_by_slug() -> str:
    prof = current_profile()
    for k in ("full_name", "display_name", "email"):
        v = str(prof.get(k) or "").strip()
        if v:
            return v[:200]
    return "unknown"


def _packages_for_supervisor(
    *,
    work_iso: str,
    packages: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    show_all: bool,
) -> list[dict[str, Any]]:
    by_job = {str(j.get("id")): j for j in jobs or [] if isinstance(j, dict) and j.get("id")}
    out: list[dict[str, Any]] = []
    for p in packages or []:
        if not isinstance(p, dict):
            continue
        if str(p.get("work_date") or "")[:10] != work_iso:
            continue
        if not show_all and not _plan_supervisor_matches(str(p.get("supervisor_name") or "")):
            continue
        jid = str(p.get("job_id") or "").strip()
        job = by_job.get(jid) or {}
        lbl = job_row_select_label(job) if job else jid[:8]
        out.append({**p, "_job_label": lbl})
    out.sort(key=lambda x: (str(x.get("_job_label") or ""), str(x.get("supervisor_name") or "")))
    return out


def _lines_for_package(pkg_id: str, lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        r
        for r in (lines or [])
        if isinstance(r, dict) and str(r.get("daily_work_package_id") or "").strip() == str(pkg_id).strip()
    ]
    rows.sort(key=lambda r: int(r.get("priority_order") or 0))
    return rows


def _fetch_execution_row(pkg_id: str, *, use_admin: bool) -> dict[str, Any]:
    fn = fetch_by_match_admin if use_admin else fetch_by_match
    try:
        rows = fn("supervisor_daily_execution", {"daily_work_package_id": str(pkg_id)}, limit=1) or []
        return dict(rows[0]) if rows else {}
    except Exception:
        return {}


def _render_package_task_row(
    *,
    pkg_id: str,
    task_row: dict[str, Any],
    can_edit: bool,
    use_admin: bool,
    work_iso: str,
) -> None:
    ins_tu, upd_jt = _w_writes(use_admin)
    tid = str(task_row.get("id") or "").strip()
    if not tid:
        return
    cur_st = _norm_task_status(str(task_row.get("status") or "not_started"))
    opts = [s for s in TASK_STATUSES if s != "cancelled"]
    ix = opts.index(cur_st) if cur_st in opts else 0

    with st.container(border=True):
        st.markdown(f"**{_task_label(task_row)}**")
        status = st.selectbox(
            "Status",
            opts,
            index=ix,
            format_func=lambda s: _STATUS_LABELS.get(str(s).lower(), str(s).replace("_", " ").title()),
            key=f"dwp_st_{pkg_id}_{tid}",
            disabled=not can_edit,
        )
        notes = st.text_area(
            "Task notes",
            value=str(task_row.get("notes") or ""),
            height=72,
            key=f"dwp_nt_{pkg_id}_{tid}",
            disabled=not can_edit,
        )
        st.caption("Photos")
        if can_edit:
            try:
                tph.render_task_photo_strip(
                    task_id=tid,
                    task_row=task_row,
                    can_edit=True,
                    admin_read=use_admin,
                    daily_work_package_id=str(pkg_id),
                )
            except Exception as exc:
                st.caption(f"Photos: {exc}")
        else:
            st.caption("Submitted — read only.")

        if not can_edit:
            return

        if st.button("Save task", type="primary", use_container_width=True, key=f"dwp_sv_{pkg_id}_{tid}"):
            ns = str(status or "").strip().lower()
            rows_ph = tph.fetch_task_photos(tid, admin=use_admin)
            by_tp = tp.photos_by_task_id(rows_ph)
            if ns == "complete" and not tp.task_has_after_photo(tid, task_row, by_tp):
                st.error("After photo is required before marking **Complete**.")
                st.stop()
            now = datetime.now(timezone.utc).isoformat()
            try:
                payload: dict[str, Any] = {
                    "status": ns,
                    "notes": str(notes or "").strip()[:4000],
                    "updated_at": now,
                }
                if ns == "complete":
                    payload["completed_date"] = str(work_iso or "")[:10] or date.today().isoformat()[:10]
                else:
                    payload["completed_date"] = None
                upd_jt("job_tasks", payload, {"id": tid})
                ins_tu(
                    "task_updates",
                    {
                        "job_task_id": tid,
                        "daily_work_package_id": str(pkg_id),
                        "status": ns,
                        "notes": str(notes or "").strip()[:4000],
                        "created_by": _created_by_slug(),
                    },
                )
                st.success("Saved.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def render_pm() -> None:
    render_header(
        "Assign Tasks (PM)",
        subtitle="Create a **Daily Work Package**: job, date, supervisor, tasks in order, and PM notes.",
    )
    _inject_field_touch_css()
    _mob.inject_mobile_field_css()

    if not _is_pm():
        st.info("Only **admin** and **manager** create daily work packages. Field staff use **Work & Plan (Supervisor)**.")
        return

    use_admin = True
    ins, upd = _w_writes(use_admin)
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
    if not job_tasks:
        st.warning("No **job_tasks** loaded. Add tasks in **Job Database**.")
        return

    labels, label_to_id = _job_options(list(jobs or []))
    today = date.today()

    wdate = st.date_input("Planned work date (package day)", value=today, key="pm_dwp_date")
    w_iso = wdate.isoformat()[:10]
    job_lb = st.selectbox("Job", options=labels or ["—"], key="pm_dwp_job", disabled=not labels)
    jid = label_to_id.get(str(job_lb), "")
    sup = st.text_input("Supervisor (field lead)", key="pm_dwp_sup", placeholder="Name as crew knows them")
    pkg_notes = st.text_area("PM notes (whole package)", height=64, key="pm_dwp_pkg_notes")

    t_for_job = [t for t in job_tasks if isinstance(t, dict) and str(t.get("job_id")) == str(jid)]
    ids = [str(t.get("id") or "") for t in t_for_job if str(t.get("id") or "").strip()]
    st.caption("Select tasks **in execution order** (first selected = first on site).")
    pick = st.multiselect(
        "Tasks",
        options=ids,
        default=[],
        format_func=lambda tid: _task_label(next((x for x in t_for_job if str(x.get("id")) == tid), {})),
        key="pm_dwp_pick",
    )

    for tid in pick:
        t = next((x for x in t_for_job if str(x.get("id")) == tid), {})
        st.text_input(f"PM notes · {_task_label(t)}", key=f"pm_dwp_line_{tid}", placeholder="Optional")

    if st.button("Create Daily Work Package", type="primary", use_container_width=True, key="pm_dwp_save"):
        if not jid:
            st.error("Pick a job.")
            st.stop()
        if not str(sup or "").strip():
            st.error("Enter supervisor name.")
            st.stop()
        if not pick:
            st.error("Select at least one task.")
            st.stop()
        try:
            sn = " ".join(str(sup or "").strip().split())[:200]
            row = ins(
                "daily_work_packages",
                {
                    "job_id": str(jid),
                    "work_date": w_iso,
                    "supervisor_name": sn,
                    "pm_notes": str(pkg_notes or "").strip()[:8000],
                    "status": "open",
                    "created_by": _created_by_slug(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            pkg_id = str((row or {}).get("id") or "").strip()
            if not pkg_id:
                st.error("Package insert returned no id.")
                st.stop()
            for i, tid in enumerate(pick):
                if not tid:
                    continue
                line_note = str(st.session_state.get(f"pm_dwp_line_{tid}") or "").strip()[:2000]
                ins(
                    "daily_work_package_tasks",
                    {
                        "daily_work_package_id": pkg_id,
                        "job_task_id": str(tid),
                        "priority_order": int(i),
                        "pm_notes": line_note,
                    },
                )
                upd(
                    "job_tasks",
                    {
                        "assigned_supervisor_name": sn,
                        "planned_date": w_iso,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    {"id": str(tid)},
                )
            st.success("Daily Work Package created.")
            st.rerun()
        except Exception as exc:
            st.error(
                f"{exc} — Run **`sql/055_daily_work_packages_workflow.sql`** if tables are missing."
            )


def render_supervisor() -> None:
    render_header(
        "Work & Plan (Supervisor)",
        subtitle="Your **Daily Work Package** for the selected day: plan the shift, execute tasks, submit end-of-day.",
    )
    _inject_field_touch_css()
    _mob.inject_mobile_field_css()

    use_admin = _is_pm()
    ins, upd = _w_writes(use_admin)

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

    packages = _fetch_table("daily_work_packages", use_admin=use_admin)
    pkg_tasks = _fetch_table("daily_work_package_tasks", use_admin=use_admin)
    job_tasks = _fetch_table("job_tasks", use_admin=use_admin)
    executions = _fetch_table("supervisor_daily_execution", use_admin=use_admin)

    if not packages and not pkg_tasks:
        st.info(
            "No **Daily Work Packages** yet. Your PM publishes assignments from **Assign Tasks (PM)** "
            "(run **`sql/055_daily_work_packages_workflow.sql`** if needed)."
        )
        return

    today = date.today()
    wdate = st.date_input("Work date", value=today, key="sv_dwp_wdate")
    w_iso = wdate.isoformat()[:10]

    show_all = bool(_is_pm() and st.checkbox("Show all crews (office)", value=True, key="sv_dwp_all"))

    scoped = _packages_for_supervisor(work_iso=w_iso, packages=packages, jobs=list(jobs or []), show_all=show_all)
    if not scoped:
        st.warning("No package for this date matches your name. Ask the PM to assign you, or enable **Show all crews**.")
        return

    opts_lbl = [
        f"{p.get('_job_label')} · {str(p.get('supervisor_name') or '')[:28]} · {str(p.get('status') or '')}"
        for p in scoped
    ]
    ix = st.selectbox("Daily Work Package", options=list(range(len(scoped))), format_func=lambda i: opts_lbl[int(i)], key="sv_dwp_pkg_ix")
    pkg = scoped[int(ix)]
    pkg_id = str(pkg.get("id") or "").strip()
    pkg_status = str(pkg.get("status") or "open").strip().lower()
    can_edit = pkg_status != "submitted"

    exec_row = _fetch_execution_row(pkg_id, use_admin=use_admin)
    if not exec_row:
        exec_row = next(
            (dict(e) for e in executions if str(e.get("daily_work_package_id") or "") == pkg_id),
            {},
        )

    st.divider()
    st.markdown("### Shift plan (how we work)")
    crew = st.text_area("Crew plan", value=str(exec_row.get("crew_plan") or ""), height=72, key=f"sv_crew_{pkg_id}")
    first = st.text_input("First task", value=str(exec_row.get("first_task") or ""), key=f"sv_first_{pkg_id}")
    block = st.text_area("Blockers", value=str(exec_row.get("known_blockers") or ""), height=64, key=f"sv_blk_{pkg_id}")
    tools = st.text_area("Tools / material", value=str(exec_row.get("tools_material") or ""), height=56, key=f"sv_tl_{pkg_id}")

    if st.button("Save shift plan", type="primary", use_container_width=True, key=f"sv_plan_{pkg_id}", disabled=not can_edit):
        try:
            now = datetime.now(timezone.utc).isoformat()
            payload = {
                "crew_plan": str(crew or "").strip()[:8000],
                "first_task": str(first or "").strip()[:2000],
                "known_blockers": str(block or "").strip()[:8000],
                "tools_material": str(tools or "").strip()[:8000],
                "updated_at": now,
            }
            ex_now = _fetch_execution_row(pkg_id, use_admin=use_admin)
            if ex_now:
                upd("supervisor_daily_execution", payload, {"daily_work_package_id": pkg_id})
            else:
                ins(
                    "supervisor_daily_execution",
                    {
                        "daily_work_package_id": pkg_id,
                        "eod_summary": "",
                        "delay_reason": "none",
                        "tomorrow_plan": "",
                        **payload,
                    },
                )
            st.success("Saved.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.markdown("### Tasks (execute)")
    st.caption("Assigned for this shift — update **status**, **photos**, and **notes**; complete **End of day** below.")
    lines = _lines_for_package(pkg_id, pkg_tasks)
    task_by_id = {str(t.get("id")): t for t in job_tasks if isinstance(t, dict) and t.get("id")}
    for ln in lines:
        tid = str(ln.get("job_task_id") or "").strip()
        t = task_by_id.get(tid) or {}
        if not t:
            st.warning(f"Task **{tid[:8]}…** is on the package but missing from **job_tasks**.")
            continue
        pm_line = str(ln.get("pm_notes") or "").strip()
        if pm_line:
            st.caption(f"PM: {pm_line[:500]}")
        _render_package_task_row(
            pkg_id=pkg_id, task_row=t, can_edit=can_edit, use_admin=use_admin, work_iso=w_iso
        )

    st.divider()
    st.markdown("### End of day")
    ex2 = _fetch_execution_row(pkg_id, use_admin=use_admin) or exec_row
    eod_sum = st.text_area(
        "Summary",
        value=str(ex2.get("eod_summary") or ""),
        height=88,
        key=f"sv_eod_{pkg_id}",
        disabled=not can_edit,
    )
    dr = str(ex2.get("delay_reason") or "none").strip().lower()
    dr_ix = _EOD_DELAY_SLUGS.index(dr) if dr in _EOD_DELAY_SLUGS else 0
    delay = st.selectbox(
        "Delay reason",
        options=list(_EOD_DELAY_SLUGS),
        index=dr_ix,
        format_func=lambda x: delay_reason_label(x),
        key=f"sv_dr_{pkg_id}",
        disabled=not can_edit,
    )
    tom = st.text_area(
        "Tomorrow plan",
        value=str(ex2.get("tomorrow_plan") or ""),
        height=72,
        key=f"sv_tm_{pkg_id}",
        disabled=not can_edit,
    )
    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("Save end of day", type="primary", use_container_width=True, key=f"sv_eod_sv_{pkg_id}", disabled=not can_edit):
            try:
                now = datetime.now(timezone.utc).isoformat()
                patch = {
                    "eod_summary": str(eod_sum or "").strip()[:8000],
                    "delay_reason": str(delay or "none").strip().lower()[:80],
                    "tomorrow_plan": str(tom or "").strip()[:8000],
                    "updated_at": now,
                }
                ex_eod = _fetch_execution_row(pkg_id, use_admin=use_admin)
                if ex_eod:
                    upd("supervisor_daily_execution", patch, {"daily_work_package_id": pkg_id})
                else:
                    ins(
                        "supervisor_daily_execution",
                        {
                            "daily_work_package_id": pkg_id,
                            "crew_plan": "",
                            "first_task": "",
                            "known_blockers": "",
                            "tools_material": "",
                            **patch,
                        },
                    )
                st.success("Saved.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with c2:
        if st.button("Submit daily review", type="primary", use_container_width=True, key=f"sv_sub_{pkg_id}", disabled=not can_edit):
            try:
                now = datetime.now(timezone.utc).isoformat()
                if not _fetch_execution_row(pkg_id, use_admin=use_admin):
                    ins(
                        "supervisor_daily_execution",
                        {
                            "daily_work_package_id": pkg_id,
                            "crew_plan": str(crew or "").strip()[:8000],
                            "first_task": str(first or "").strip()[:2000],
                            "known_blockers": str(block or "").strip()[:8000],
                            "tools_material": str(tools or "").strip()[:8000],
                            "eod_summary": str(eod_sum or "").strip()[:8000],
                            "delay_reason": str(delay or "none").strip().lower()[:80],
                            "tomorrow_plan": str(tom or "").strip()[:8000],
                            "submitted_at": now,
                            "updated_at": now,
                        },
                    )
                else:
                    upd(
                        "supervisor_daily_execution",
                        {
                            "eod_summary": str(eod_sum or "").strip()[:8000],
                            "delay_reason": str(delay or "none").strip().lower()[:80],
                            "tomorrow_plan": str(tom or "").strip()[:8000],
                            "submitted_at": now,
                            "updated_at": now,
                        },
                        {"daily_work_package_id": pkg_id},
                    )
                upd(
                    "daily_work_packages",
                    {"status": "submitted", "updated_at": now},
                    {"id": pkg_id},
                )
                st.success("Daily review submitted.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    if pkg_status == "submitted":
        st.caption("This package is **submitted** — edits are locked.")


def render() -> None:
    render_supervisor()
