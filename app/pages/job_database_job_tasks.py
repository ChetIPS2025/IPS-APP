"""Job detail tabs: Tasks, Daily Plan, Daily Review, Photos, Cost — task-first workflow."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Callable

import pandas as pd
import streamlit as st

try:
    from app.db import (
        create_signed_url,
        delete_rows,
        delete_rows_admin,
        fetch_by_match,
        fetch_by_match_admin,
        insert_row,
        insert_row_admin,
        update_rows,
        update_rows_admin,
        upload_bytes,
        upload_bytes_admin,
    )
except ImportError:
    from db import (  # type: ignore
        create_signed_url,
        delete_rows,
        delete_rows_admin,
        fetch_by_match,
        fetch_by_match_admin,
        insert_row,
        insert_row_admin,
        update_rows,
        update_rows_admin,
        upload_bytes,
        upload_bytes_admin,
    )

try:
    from app.services.supervisor_planning import TASK_STATUSES, delay_reason_label
except ImportError:
    from services.supervisor_planning import TASK_STATUSES, delay_reason_label  # type: ignore

try:
    from app.services import task_photos as _tp_svc
except ImportError:
    import services.task_photos as _tp_svc  # type: ignore

try:
    from app.pages import job_database_task_photos_ui as _tph
except ImportError:
    import pages.job_database_task_photos_ui as _tph  # type: ignore

try:
    from app.pages import job_database_mobile_task_ui as _mob
except ImportError:
    import pages.job_database_mobile_task_ui as _mob  # type: ignore

try:
    from app.ui.field_light_theme import inject_field_light_theme
except ImportError:
    from ui.field_light_theme import inject_field_light_theme  # type: ignore

try:
    from app.ui import IPS_NAV_PENDING_KEY
except ImportError:
    from ui import IPS_NAV_PENDING_KEY  # type: ignore

try:
    from app.utils.formatters import job_display_label as _job_display_label
except ImportError:
    from utils.formatters import job_display_label as _job_display_label  # type: ignore

# Review / end-of-day status choices (subset of TASK_STATUSES; labels for field UI)
_REVIEW_STATUS_LABELS: dict[str, str] = {
    "complete": "Complete",
    "partial": "Partial",
    "blocked": "Blocked",
    "not_started": "Not Started",
    "duplicate": "Duplicate",
    "electrical": "Electrical / other trade",
    "waiting_on_customer": "Waiting on customer",
}


_JDR_REVIEW_SLUGS: tuple[str, ...] = (
    "complete",
    "partial",
    "blocked",
    "not_started",
    "duplicate",
    "electrical",
    "waiting_on_customer",
)

_JDR_DELAY_REASONS: tuple[str, ...] = (
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


def _task_status_display(slug: str) -> str:
    s = str(slug or "").strip().lower()
    if s == "open":
        s = "not_started"
    return _REVIEW_STATUS_LABELS.get(s, s.replace("_", " ").title() or "—")


def _task_status_badge(slug: str) -> str:
    s = str(slug or "").strip().lower()
    if s == "open":
        s = "not_started"
    return (
        f'<span class="ips-status-badge ips-status-{html.escape(s)}">'
        f"{html.escape(_task_status_display(s))}</span>"
    )


def _fetch_tasks(job_id: str, *, admin: bool) -> list[dict[str, Any]]:
    fn = fetch_by_match_admin if admin else fetch_by_match
    try:
        return list(fn("job_tasks", {"job_id": str(job_id)}, limit=500) or [])
    except Exception:
        return []


def _fetch_plans_for_job(job_id: str, *, admin: bool) -> list[dict[str, Any]]:
    fn = fetch_by_match_admin if admin else fetch_by_match
    try:
        return list(fn("supervisor_daily_task_plans", {"job_id": str(job_id)}, limit=2000) or [])
    except Exception:
        return []


def _fetch_reviews_for_tasks(task_ids: list[str], *, admin: bool) -> list[dict[str, Any]]:
    if not task_ids:
        return []
    fn = fetch_by_match_admin if admin else fetch_by_match
    out: list[dict[str, Any]] = []
    # fetch_by_match single eq — batch by task in loop (small N per job)
    for tid in task_ids[:400]:
        try:
            out.extend(fn("job_task_daily_reviews", {"task_id": tid}, limit=120) or [])
        except Exception:
            continue
    return out


def _fetch_work_plan(job_id: str, work_date: str, *, admin: bool) -> dict[str, Any] | None:
    fn = fetch_by_match_admin if admin else fetch_by_match
    try:
        rows = fn(
            "job_daily_work_plans",
            {"job_id": str(job_id), "work_date": str(work_date)[:10]},
            limit=1,
        )
        return rows[0] if rows else None
    except Exception:
        return None


def _wrow(admin: bool) -> tuple[Callable, Callable, Callable]:
    if admin:
        return insert_row_admin, update_rows_admin, delete_rows_admin
    return insert_row, update_rows, delete_rows


def render_job_tasks_tab(
    *,
    job_id: str,
    job_label: str,
    can_edit_tasks: bool,
    admin_read: bool,
) -> None:
    inject_field_light_theme()
    st.caption("Jobs are containers — break work into **tasks**. Mobile-first: pick a task, then update status and photos.")
    rows = _fetch_tasks(job_id, admin=admin_read)
    today_iso = date.today().isoformat()[:10]

    filt = st.selectbox(
        "Filter",
        (
            "All",
            "Planned today",
            "High priority",
            "Blocked",
            "Complete",
            "Electrical",
            "Duplicate",
        ),
        key=f"jdt_filt_{job_id}",
    )

    def _match(t: dict[str, Any]) -> bool:
        stt = str(t.get("status") or "").strip().lower()
        pr = str(t.get("priority") or "").strip().lower()
        pd = str(t.get("planned_date") or "")[:10]
        if filt == "Planned today":
            return pd == today_iso
        if filt == "High priority":
            return pr in ("high", "critical") and stt not in ("complete", "cancelled", "duplicate")
        if filt == "Blocked":
            return stt == "blocked"
        if filt == "Complete":
            return stt == "complete"
        if filt == "Electrical":
            return stt == "electrical"
        if filt == "Duplicate":
            return stt == "duplicate"
        return True

    visible = [t for t in rows if isinstance(t, dict) and _match(t)]
    if not rows:
        st.info("No tasks yet. Add tasks with **Add task** below.")
    elif not visible:
        st.caption("No tasks match this filter.")

    ins, upd, _del = _wrow(admin_read)

    if visible:
        _mob.inject_mobile_field_css()

        def _task_pick_label(tt: dict[str, Any]) -> str:
            iss = str(tt.get("issue") or "").strip()
            snip = (iss[:36] + "…") if len(iss) > 36 else iss
            return (
                f"{tt.get('task_number') or '—'}/{tt.get('hazard_number') or '—'} · "
                f"{_task_status_display(str(tt.get('status')))} · {snip or '—'}"
            )

        pick_ix = st.selectbox(
            "Select task",
            options=list(range(len(visible))),
            format_func=lambda i: _task_pick_label(visible[int(i)]),
            key=f"jdt_pick_{job_id}_{filt}",
        )
        t = visible[int(pick_ix)]
        tid = str(t.get("id") or "").strip()
        if tid:
            st.caption(
                f"Supervisor **{str(t.get('assigned_supervisor_name') or '—').strip() or '—'}** · "
                f"Planned **{str(t.get('planned_date') or '—')[:10]}** · "
                f"Priority **{str(t.get('priority') or '—').title()}**"
            )
            with st.expander("Assign supervisor & read-only details", expanded=False):
                sup = st.text_input(
                    "Assigned supervisor",
                    value=str(t.get("assigned_supervisor_name") or ""),
                    key=f"jdt_asgn_{tid}",
                    disabled=not can_edit_tasks,
                )
                if can_edit_tasks and st.button("Save supervisor", key=f"jdt_asgn_save_{tid}"):
                    try:
                        upd(
                            "job_tasks",
                            {
                                "assigned_supervisor_name": " ".join(str(sup or "").split())[:200],
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                            },
                            {"id": tid},
                        )
                        st.success("Saved.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
                st.text_area(
                    "Action required",
                    value=str(t.get("action_required") or ""),
                    height=70,
                    disabled=True,
                    key=f"jdt_ar_{tid}",
                )
            try:
                _mob.render_mobile_task_detail_form(
                    task_row=t,
                    task_id=tid,
                    can_edit=can_edit_tasks,
                    admin_read=admin_read,
                    upd=upd,
                )
            except Exception as exc:
                st.error(str(exc))
                st.caption("Fallback: run **`sql/051_job_task_photos.sql`** / **`sql/052_job_task_photos_capture_meta.sql`**.")

    if can_edit_tasks:
        st.markdown("##### Add task")
        st.markdown('<span class="ips-job-add-task-anchor"></span>', unsafe_allow_html=True)
        a1, a2 = st.columns(2, gap="small")
        with a1:
            tn = st.text_input("Task #", key=f"jdt_add_tn_{job_id}")
            hn = st.text_input("Hazard #", key=f"jdt_add_hn_{job_id}")
        with a2:
            pr = st.selectbox(
                "Priority",
                ("low", "normal", "high", "critical"),
                index=1,
                format_func=lambda x: x.title(),
                key=f"jdt_add_pr_{job_id}",
            )
            pl = st.date_input("Planned date", value=date.today(), key=f"jdt_add_pl_{job_id}")
        a3, a4 = st.columns(2, gap="small")
        with a3:
            loc = st.text_input("Location", key=f"jdt_add_loc_{job_id}")
            iss = st.text_input("Issue (short)", key=f"jdt_add_iss_{job_id}")
        with a4:
            act = st.text_input("Action required", key=f"jdt_add_act_{job_id}")
            st.caption(" ")
        if st.button("Add task", type="primary", use_container_width=True, key=f"jdt_add_btn_{job_id}"):
            if not str(iss or "").strip():
                st.error("Enter an issue description.")
            else:
                try:
                    ins(
                        "job_tasks",
                        {
                            "job_id": str(job_id),
                            "task_number": str(tn or "").strip()[:200],
                            "hazard_number": str(hn or "").strip()[:200],
                            "priority": pr,
                            "location": str(loc or "").strip()[:500],
                            "issue": str(iss or "").strip()[:4000],
                            "action_required": str(act or "").strip()[:4000],
                            "status": "not_started",
                            "planned_date": str(pl) if pl is not None else None,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    st.success("Task added.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def render_job_daily_plan_tab(
    *,
    job_id: str,
    can_edit_tasks: bool,
    admin_read: bool,
) -> None:
    st.caption("Pick **today’s tasks**, assign the lead supervisor, and capture shift context.")
    wdate = st.date_input("Work date", value=date.today(), key=f"jdp_date_{job_id}")
    w_iso = wdate.isoformat()[:10]
    rows = _fetch_tasks(job_id, admin=admin_read)
    ids = [str(t.get("id") or "") for t in rows if str(t.get("id") or "").strip()]
    plans = _fetch_plans_for_job(job_id, admin=admin_read)
    planned_ids = {str(p.get("task_id")) for p in plans if str(p.get("work_date") or "")[:10] == w_iso}
    default = [i for i in ids if i in planned_ids]

    def _fmt(tid: str) -> str:
        tt = next((x for x in rows if str(x.get("id")) == tid), {})
        iss = str(tt.get("issue") or "")[:40]
        return f"{tt.get('task_number') or '—'}/{tt.get('hazard_number') or '—'} · {iss}"

    pick = st.multiselect(
        "Tasks for this day",
        options=ids,
        default=[i for i in default if i in ids],
        format_func=_fmt,
        key=f"jdp_pick_{job_id}_{w_iso}",
    )
    sup = st.text_input("Supervisor (lead)", key=f"jdp_sup_{job_id}_{w_iso}", placeholder="Field supervisor name")

    wp = _fetch_work_plan(job_id, w_iso, admin=admin_read) or {}
    crew = st.text_area("Crew plan", value=str(wp.get("crew_plan") or ""), height=68, key=f"jdp_crew_{job_id}")
    first = st.text_input("First task at start of shift", value=str(wp.get("first_task") or ""), key=f"jdp_first_{job_id}")
    tools = st.text_area("Tools / material needed", value=str(wp.get("tools_material") or ""), height=68, key=f"jdp_tools_{job_id}")
    block = st.text_area("Known blockers", value=str(wp.get("known_blockers") or ""), height=56, key=f"jdp_blk_{job_id}")
    risk = st.text_input("Biggest risk", value=str(wp.get("biggest_risk") or ""), key=f"jdp_risk_{job_id}")

    if not can_edit_tasks:
        st.info("You can view the plan; only field leads and office roles can edit.")
        return

    ins, upd, dlt = _wrow(admin_read)
    if st.button("Save daily plan", type="primary", key=f"jdp_save_{job_id}_{w_iso}"):
        if not str(sup or "").strip():
            st.error("Enter supervisor name.")
            st.stop()
        try:
            dlt("supervisor_daily_task_plans", {"job_id": str(job_id), "work_date": w_iso})
            sn = " ".join(str(sup or "").strip().split())[:200]
            for i, tid in enumerate(pick):
                if tid:
                    row_payload: dict[str, Any] = {
                        "job_id": str(job_id),
                        "work_date": w_iso,
                        "supervisor_name": sn,
                        "task_id": tid,
                        "sort_order": int(i),
                    }
                    try:
                        ins("supervisor_daily_task_plans", row_payload)
                    except Exception:
                        row_payload.pop("sort_order", None)
                        ins("supervisor_daily_task_plans", row_payload)
            summary = {
                "supervisor_name": sn,
                "crew_plan": str(crew or "").strip()[:8000],
                "first_task": str(first or "").strip()[:2000],
                "tools_material": str(tools or "").strip()[:8000],
                "known_blockers": str(block or "").strip()[:8000],
                "biggest_risk": str(risk or "").strip()[:2000],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            existing = _fetch_work_plan(job_id, w_iso, admin=admin_read)
            if existing:
                upd("job_daily_work_plans", summary, {"job_id": str(job_id), "work_date": w_iso})
            else:
                ins(
                    "job_daily_work_plans",
                    {
                        "job_id": str(job_id),
                        "work_date": w_iso,
                        **summary,
                    },
                )
            st.success("Saved.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def render_job_daily_review_tab(
    *,
    job_id: str,
    can_edit_tasks: bool,
    admin_read: bool,
) -> None:
    inject_field_light_theme()
    _mob.inject_mobile_field_css()
    st.caption(
        "Shows tasks **on the daily plan** for the review date or tasks with **planned date** set to that day. "
        "Submit once at the bottom."
    )
    rdate = st.date_input("Review date", value=date.today(), key=f"jdr_date_{job_id}")
    r_iso = rdate.isoformat()[:10]
    rows = _fetch_tasks(job_id, admin=admin_read)
    plans = _fetch_plans_for_job(job_id, admin=admin_read)
    planned_today = {
        str(p.get("task_id"))
        for p in plans
        if isinstance(p, dict) and str(p.get("work_date") or "")[:10] == r_iso
    }
    task_ids = [str(t.get("id") or "") for t in rows if str(t.get("id") or "").strip()]
    all_reviews = _fetch_reviews_for_tasks(task_ids, admin=admin_read)
    rev_by_task: dict[str, dict[str, Any]] = {}
    for rv in all_reviews:
        if not isinstance(rv, dict):
            continue
        if str(rv.get("review_date") or "")[:10] != r_iso:
            continue
        tid = str(rv.get("task_id") or "").strip()
        if tid:
            rev_by_task[tid] = rv

    candidates: list[dict[str, Any]] = []
    for t in rows:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip()
        if not tid:
            continue
        if tid in planned_today or str(t.get("planned_date") or "")[:10] == r_iso:
            candidates.append(t)
    candidates.sort(key=lambda x: str(x.get("task_number") or ""))

    if not candidates:
        st.info("No tasks planned for this date. Use **Daily Plan** or set the task **planned date**.")
        return

    ins, upd, _ = _wrow(admin_read)
    jk = re.sub(r"[^a-z0-9]+", "", str(job_id).lower())[:12]

    try:
        _tph.render_daily_review_progress_strip(
            job_id=str(job_id),
            review_date=r_iso,
            can_edit=can_edit_tasks,
            admin_read=admin_read,
        )
    except Exception as exc:
        st.caption(f"Shift photos unavailable ({exc}).")

    with st.form(f"jdr_batch_{job_id}_{r_iso}"):
        st.text_input(
            "Supervisor sign-off (name)",
            key=f"jdrf_sup_{jk}_{r_iso}",
            placeholder="Required to submit",
            disabled=not can_edit_tasks,
        )
        for t in candidates:
            tid = str(t.get("id") or "").strip()
            if not tid:
                continue
            prior = rev_by_task.get(tid) or {}
            iss = str(t.get("issue") or "").strip()
            snip = (iss[:56] + "…") if len(iss) > 56 else iss
            with st.container(border=True):
                st.markdown(f"**{t.get('task_number') or '—'}** · _{snip or '—'}_")
                cur_st = str(prior.get("status_after") or t.get("status") or "not_started").strip().lower()
                if cur_st not in _JDR_REVIEW_SLUGS:
                    cur_st = "not_started"
                st.selectbox(
                    "Status",
                    list(_JDR_REVIEW_SLUGS),
                    index=list(_JDR_REVIEW_SLUGS).index(cur_st),
                    format_func=lambda s: _REVIEW_STATUS_LABELS.get(s, s),
                    key=f"jdrf_st_{jk}_{tid}_{r_iso}",
                    disabled=not can_edit_tasks,
                )
                c1, c2 = st.columns(2, gap="small")
                with c1:
                    st.caption("Take photo (after)")
                    st.camera_input("a", key=f"jdrf_cam_{jk}_{tid}_{r_iso}", label_visibility="collapsed", disabled=not can_edit_tasks)
                with c2:
                    st.caption("Upload (after)")
                    st.file_uploader(
                        "u",
                        type=["jpg", "jpeg", "png", "webp"],
                        key=f"jdrf_up_{jk}_{tid}_{r_iso}",
                        label_visibility="collapsed",
                        disabled=not can_edit_tasks,
                    )
                dr_cur = str(prior.get("delay_reason") or "none").strip().lower()
                dr_ix = _JDR_DELAY_REASONS.index(dr_cur) if dr_cur in _JDR_DELAY_REASONS else 0
                st.selectbox(
                    "Delay reason",
                    list(_JDR_DELAY_REASONS),
                    index=dr_ix,
                    format_func=delay_reason_label,
                    key=f"jdrf_dr_{jk}_{tid}_{r_iso}",
                    disabled=not can_edit_tasks,
                )
                st.text_area(
                    "Notes",
                    value=str(prior.get("notes") or ""),
                    height=56,
                    key=f"jdrf_nt_{jk}_{tid}_{r_iso}",
                    disabled=not can_edit_tasks,
                )
        submitted = st.form_submit_button(
            "Submit Daily Review",
            type="primary",
            use_container_width=True,
            disabled=not can_edit_tasks,
        )

    if submitted and can_edit_tasks:
        supv = str(st.session_state.get(f"jdrf_sup_{jk}_{r_iso}") or "").strip()
        if not supv:
            st.error("Supervisor sign-off is required.")
            st.stop()
        supv = " ".join(supv.split())[:200]
        try:
            for t in candidates:
                tid = str(t.get("id") or "").strip()
                if not tid:
                    continue
                prior = rev_by_task.get(tid) or {}
                ns_raw = st.session_state.get(f"jdrf_st_{jk}_{tid}_{r_iso}")
                ns = str(ns_raw or "not_started").strip().lower()
                cam_raw = st.session_state.get(f"jdrf_cam_{jk}_{tid}_{r_iso}")
                up_raw = st.session_state.get(f"jdrf_up_{jk}_{tid}_{r_iso}")
                pending: bytes | None = None
                fn = "after.jpg"
                if cam_raw is not None and hasattr(cam_raw, "getvalue"):
                    pending = cam_raw.getvalue()
                    fn = "camera.jpg"
                elif up_raw is not None and hasattr(up_raw, "getvalue"):
                    pending = up_raw.getvalue()
                    fn = str(getattr(up_raw, "name", "") or "after.jpg")
                if ns == "complete" and not _tph.task_has_after_for_validation(
                    task_id=tid,
                    task_row=t,
                    prior_review=prior,
                    pending_upload_bytes=pending,
                    admin_read=admin_read,
                ):
                    st.error(f"Task {t.get('task_number') or tid}: After photo required to complete task.")
                    st.stop()
                photo_path = str(prior.get("after_photo_url") or "").strip()
                if pending:
                    photo_path = _tph.save_review_after_photo(
                        task_id=tid,
                        review_date=r_iso,
                        raw=pending,
                        fname=fn,
                        admin_read=admin_read,
                    )
                delay = str(st.session_state.get(f"jdrf_dr_{jk}_{tid}_{r_iso}") or "none").strip().lower()
                notes = str(st.session_state.get(f"jdrf_nt_{jk}_{tid}_{r_iso}") or "").strip()[:4000]
                payload_rev = {
                    "supervisor_name": supv,
                    "status_after": ns,
                    "delay_reason": delay,
                    "notes": notes,
                    "after_photo_url": photo_path[:2000],
                }
                if prior:
                    upd("job_task_daily_reviews", payload_rev, {"task_id": tid, "review_date": r_iso})
                else:
                    ins(
                        "job_task_daily_reviews",
                        {"task_id": tid, "review_date": r_iso, **payload_rev},
                    )
                task_upd: dict[str, Any] = {
                    "status": ns,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                if ns == "complete":
                    task_upd["completed_date"] = r_iso
                else:
                    task_upd["completed_date"] = None
                if photo_path:
                    task_upd["after_photo_url"] = photo_path[:2000]
                upd("job_tasks", task_upd, {"id": tid})
            st.success("Daily review saved.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def render_job_photos_tab(*, job_id: str, admin_read: bool) -> None:
    rows = _fetch_tasks(job_id, admin=admin_read)
    st.caption("Before / after / progress from **Tasks** and **Daily Review** (stored in Supabase).")
    by_tid: dict[str, list[dict[str, Any]]] = {}
    for t in rows:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip()
        if not tid:
            continue
        try:
            ph = _tph.fetch_task_photos(tid, admin=admin_read)
        except Exception:
            ph = []
        by_tid[tid] = list(ph or [])

    cmp_opts: list[tuple[str, str, str, str]] = []
    for t in rows:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip()
        if not tid:
            continue
        b, a = _tp_svc.before_after_storage_paths(t, by_tid.get(tid), task_id=tid)
        if b and a:
            lab = f"{t.get('task_number') or '—'} / {t.get('hazard_number') or '—'}"
            cmp_opts.append((lab, tid, b, a))

    if cmp_opts:
        with st.expander("Before / after comparison", expanded=False):
            ix = st.selectbox(
                "Task",
                options=range(len(cmp_opts)),
                format_func=lambda i: cmp_opts[i][0],
                key=f"jbapho_cmp_{job_id}",
            )
            lab, _tid, bp, ap = cmp_opts[int(ix)]
            st.caption(lab)
            u1, u2 = st.columns(2, gap="small")
            bu = _tph.sign_task_photo_url(bp, expires_in=2400) if bp and not bp.startswith("http") else bp
            au = _tph.sign_task_photo_url(ap, expires_in=2400) if ap and not ap.startswith("http") else ap
            with u1:
                st.caption("Before")
                if bu:
                    try:
                        st.image(bu, use_container_width=True)
                    except Exception:
                        st.caption("(could not render)")
            with u2:
                st.caption("After")
                if au:
                    try:
                        st.image(au, use_container_width=True)
                    except Exception:
                        st.caption("(could not render)")

    tiles: list[tuple[dict[str, Any], str, str, list[dict[str, Any]]]] = []
    for t in rows:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip()
        if not tid:
            continue
        phs = by_tid.get(tid) or []
        latest = _tp_svc.latest_photo_path_by_type(phs, task_id=tid)
        b = str(latest.get(_tp_svc.PHOTO_TYPES_BEFORE) or t.get("before_photo_url") or "").strip()
        a = str(latest.get(_tp_svc.PHOTO_TYPES_AFTER) or t.get("after_photo_url") or "").strip()
        prog = [r for r in phs if str((r or {}).get("photo_type") or "").lower() == _tp_svc.PHOTO_TYPES_PROGRESS]
        if b or a or prog:
            tiles.append((t, b, a, prog))
    if not tiles:
        st.info("No task photos yet. Use **Tasks** (before / progress / after) or **Daily Review**.")
        return
    for t, b, a, prog in tiles[:50]:
        label = f"{t.get('task_number') or '—'} / {t.get('hazard_number') or '—'}"
        st.markdown(f"**{label}**")
        c1, c2 = st.columns(2, gap="small")
        with c1:
            st.caption("Before")
            if b:
                url = _tph.sign_task_photo_url(b, expires_in=1800) if not b.startswith("http") else b
                if url:
                    try:
                        st.image(url, use_container_width=True)
                    except Exception:
                        st.caption("(could not render image)")
            else:
                st.caption("—")
        with c2:
            st.caption("After")
            if a:
                url = _tph.sign_task_photo_url(a, expires_in=1800) if not a.startswith("http") else a
                if url:
                    try:
                        st.image(url, use_container_width=True)
                    except Exception:
                        st.caption("(could not render image)")
            else:
                st.caption("—")
        if prog:
            st.caption("Progress")
            pc = st.columns(min(4, len(prog[:8])))
            for i, pr in enumerate(prog[:8]):
                pp = str((pr or {}).get("storage_path") or "").strip()
                with pc[i % len(pc)]:
                    if pp:
                        url = _tph.sign_task_photo_url(pp, expires_in=1800) if not pp.startswith("http") else pp
                        if url:
                            try:
                                st.image(url, use_container_width=True)
                            except Exception:
                                st.caption("—")


def render_job_cost_tab(*, job_id: str, job_row: dict[str, Any]) -> None:
    label = str(_job_display_label(job_row.get("job_number"), job_row.get("job_name"))).strip() or "Job"
    st.markdown(f"**{label}**")
    st.caption("Labor, materials, and equipment are tracked on **Job Costing**.")
    if st.button("Open Job Costing", type="primary", key=f"jcost_open_{job_id}"):
        st.session_state["jc_focus_job_id"] = str(job_id)
        st.session_state[IPS_NAV_PENDING_KEY] = "Job Costing"
        st.rerun()
