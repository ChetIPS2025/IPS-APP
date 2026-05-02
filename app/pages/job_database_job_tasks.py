"""Job detail tabs: Tasks, Daily Plan, Photos, Cost — task-first workflow (field review in Work & Plan)."""

from __future__ import annotations

import html
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

# Task status labels for badges / pickers
_REVIEW_STATUS_LABELS: dict[str, str] = {
    "complete": "Complete",
    "partial": "Partial",
    "blocked": "Blocked",
    "not_started": "Not Started",
    "duplicate": "Duplicate",
    "electrical": "Electrical / other trade",
    "waiting_on_customer": "Waiting on customer",
}


def _task_status_display(slug: str) -> str:
    s = str(slug or "").strip().lower()
    if s == "open":
        s = "not_started"
    return _REVIEW_STATUS_LABELS.get(s, s.replace("_", " ").title() or "—")


def _task_status_badge(slug: str) -> str:
    s = str(slug or "").strip().lower()
    if s == "open":
        s = "not_started"
    colors = {
        "complete": "#16a34a",
        "in_progress": "#f59e0b",
        "partial": "#f59e0b",
        "blocked": "#dc2626",
        "not_started": "#64748b",
        "duplicate": "#64748b",
        "electrical": "#7c3aed",
        "waiting_on_customer": "#0891b2",
        "cancelled": "#64748b",
    }
    col = colors.get(s, "#64748b")
    return (
        f'<span class="ips-status-badge" style="--ips-status-color:{html.escape(col)};">'
        f"{html.escape(_task_status_display(s))}</span>"
    )


def _priority_badge_html(priority: Any) -> str:
    pr = str(priority or "normal").strip().lower()
    if pr not in ("low", "normal", "high", "critical"):
        pr = "normal"
    label = pr.title()
    return f'<span class="ips-priority-badge {html.escape(pr)}">{html.escape(label)}</span>'


def _inject_task_tab_add_form_css() -> None:
    key = "ips_job_task_add_form_css_v1"
    if st.session_state.get(key):
        return
    st.session_state[key] = True
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-add-task-anchor)
            div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.65rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-add-task-anchor)
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            flex: 1 1 calc(50% - 0.65rem) !important;
            max-width: calc(50% - 0.35rem) !important;
            min-width: min(280px, 100%) !important;
        }
        @media (max-width: 700px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-add-task-anchor)
                div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
                width: 100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
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
    st.caption(
        "Jobs are containers — break work into **tasks**. "
        "Supervisors run status, photos, and end-of-day review in **Work & Plan (Supervisor)** (no separate report page)."
    )
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
        expand_key = f"jdt_expand_{job_id}"
        st.session_state.setdefault(expand_key, "")
        vis_ids = {str(t.get("id") or "").strip() for t in visible if str(t.get("id") or "").strip()}
        cur_ex = str(st.session_state.get(expand_key) or "").strip()
        if cur_ex and cur_ex not in vis_ids:
            st.session_state[expand_key] = ""

        st.markdown("##### Tasks")
        st.caption("Each task is a white card — use **Open / Edit** to update status, photos, and notes.")

        for t in visible:
            tid = str(t.get("id") or "").strip()
            if not tid:
                continue
            stt = str(t.get("status") or "not_started").strip().lower()
            if stt == "open":
                stt = "not_started"
            iss = str(t.get("issue") or "").strip()
            snip = (iss[:140] + "…") if len(iss) > 140 else iss
            loc = str(t.get("location") or "").strip() or "—"
            sup = str(t.get("assigned_supervisor_name") or "").strip() or "—"
            planned = str(t.get("planned_date") or "").strip()[:10] or "—"
            tn = str(t.get("task_number") or "—").strip()
            hn = str(t.get("hazard_number") or "—").strip()
            quote_po = str(t.get("quote_po") or t.get("po_number") or "").strip()

            with st.container(border=True):
                extra = ""
                if quote_po:
                    extra = f'<p style="margin:0.15rem 0;color:#4b5563;font-size:0.85rem;"><strong>Quote/PO</strong> {html.escape(quote_po)}</p>'
                st.markdown(
                    f'<p style="margin:0 0 0.35rem;font-size:1rem;font-weight:700;color:#111827;">'
                    f"Task {html.escape(tn)} / Hazard {html.escape(hn)}</p>"
                    f'<div style="margin-bottom:0.35rem;">{_task_status_badge(stt)}{_priority_badge_html(t.get("priority"))}</div>'
                    f'<p style="margin:0.15rem 0;color:#4b5563;font-size:0.9rem;"><strong>Location</strong> '
                    f"{html.escape(loc)}</p>"
                    f'<p style="margin:0.15rem 0;color:#4b5563;font-size:0.9rem;"><strong>Issue</strong> '
                    f"{html.escape(snip or '—')}</p>"
                    f'<p style="margin:0.15rem 0;color:#4b5563;font-size:0.85rem;"><strong>Supervisor</strong> '
                    f"{html.escape(sup)} · <strong>Planned</strong> {html.escape(planned)}</p>"
                    f"{extra}",
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Open / Edit",
                    key=f"jdt_card_open_{job_id}_{tid}",
                    use_container_width=True,
                ):
                    st.session_state[expand_key] = tid
                    st.rerun()

            if str(st.session_state.get(expand_key) or "").strip() == tid:
                with st.container(border=True):
                    st.markdown("#### Edit task")
                    if st.button("Close", key=f"jdt_panel_close_{job_id}_{tid}"):
                        st.session_state[expand_key] = ""
                        st.rerun()
                    with st.expander("Assign supervisor & action required", expanded=False):
                        supw = st.text_input(
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
                                        "assigned_supervisor_name": " ".join(str(supw or "").split())[:200],
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
                        st.caption(
                            "Fallback: run **`sql/051_job_task_photos.sql`** / **`sql/052_job_task_photos_capture_meta.sql`**."
                        )

    if can_edit_tasks:
        _inject_task_tab_add_form_css()
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
    st.caption(
        "Pick **today’s tasks**, assign the lead supervisor, and capture shift context. "
        "Supervisors execute and close the day in **Work & Plan (Supervisor)** — one screen."
    )
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


def render_job_photos_tab(*, job_id: str, admin_read: bool) -> None:
    rows = _fetch_tasks(job_id, admin=admin_read)
    st.caption("Before / after / progress from **Tasks** and **Work & Plan (Supervisor)** (stored in Supabase).")
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
        st.info("No task photos yet. Use **Tasks** (before / progress / after) or **Work & Plan (Supervisor)**.")
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
