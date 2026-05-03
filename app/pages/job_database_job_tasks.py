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
    from app.services.task_display import task_number_display
except ImportError:
    from services.task_display import task_number_display  # type: ignore

try:
    from app.pages import job_database_task_photos_ui as _tph
except ImportError:
    import pages.job_database_task_photos_ui as _tph  # type: ignore

try:
    from app.pages import job_database_mobile_task_ui as _mob
except ImportError:
    import pages.job_database_mobile_task_ui as _mob  # type: ignore

try:
    from app.pages import job_reference_attachments_ui as _jra_ui
except ImportError:
    import pages.job_reference_attachments_ui as _jra_ui  # type: ignore

try:
    from app.auth import current_role as _jra_role
except ImportError:
    from auth import current_role as _jra_role  # type: ignore

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


def _jdt_af_result_key(job_id: str) -> str:
    return f"jdt_af_result_{job_id}"


def _jdt_af_css_once() -> None:
    k = "ips_jdt_af_css_v1"
    if st.session_state.get(k):
        return
    st.session_state[k] = True
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-af-card) {
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 12px !important;
            padding: 16px !important;
            margin-bottom: 0.75rem !important;
            box-sizing: border-box !important;
            max-width: 100% !important;
            overflow-x: hidden !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-jdt-af-card) button[kind] {
            min-height: 3rem !important;
            padding-top: 0.65rem !important;
            padding-bottom: 0.65rem !important;
            font-size: 1.05rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _af_should_apply_text(existing: str, proposed: str | None, overwrite: bool) -> bool:
    if proposed is None or not str(proposed).strip():
        return False
    if overwrite:
        return True
    return not str(existing or "").strip()


def _apply_autofill_to_add_task_widgets(job_id: str, parsed: dict[str, Any], *, overwrite: bool) -> None:
    """Write Add task widget session keys (must run before those widgets on next rerun)."""

    def gtn() -> str:
        v = st.session_state.get(f"jdt_add_tn_{job_id}")
        return str(v or "").strip() if v is not None else ""

    def gloc() -> str:
        v = st.session_state.get(f"jdt_add_loc_{job_id}")
        return str(v or "").strip() if v is not None else ""

    def giss() -> str:
        v = st.session_state.get(f"jdt_add_iss_{job_id}")
        return str(v or "").strip() if v is not None else ""

    def gact() -> str:
        v = st.session_state.get(f"jdt_add_act_{job_id}")
        return str(v or "").strip() if v is not None else ""

    tn = str(parsed.get("task_number") or "").strip()
    if _af_should_apply_text(gtn(), tn, overwrite):
        st.session_state[f"jdt_add_tn_{job_id}"] = tn[:200]

    pr = str(parsed.get("priority") or "").strip().lower()
    if pr in ("low", "normal", "high", "critical"):
        pr_touched = bool(st.session_state.get(f"jdt_add_pr_touched_{job_id}"))
        if overwrite or not pr_touched:
            st.session_state[f"jdt_add_pr_{job_id}"] = pr

    loc = str(parsed.get("location") or "").strip()
    if _af_should_apply_text(gloc(), loc, overwrite):
        st.session_state[f"jdt_add_loc_{job_id}"] = loc[:500]

    iss = str(parsed.get("issue") or "").strip()
    if _af_should_apply_text(giss(), iss, overwrite):
        st.session_state[f"jdt_add_iss_{job_id}"] = iss[:4000]

    act = str(parsed.get("action_required") or "").strip()
    if _af_should_apply_text(gact(), act, overwrite):
        st.session_state[f"jdt_add_act_{job_id}"] = act[:4000]

    pd = parsed.get("planned_date")
    if isinstance(pd, date):
        cur_pl = st.session_state.get(f"jdt_add_pl_{job_id}", date.today())
        pl_touched = bool(st.session_state.get(f"jdt_add_pl_touched_{job_id}"))
        if isinstance(cur_pl, date):
            if overwrite or (not pl_touched and cur_pl == date.today()):
                st.session_state[f"jdt_add_pl_{job_id}"] = pd


def _render_add_task_autofill_from_attachment(*, job_id: str, admin_read: bool) -> None:
    try:
        from app.services import job_reference_attachments as _jra_svc
        from app.services import task_attachment_autofill as _taf
    except ImportError:
        import services.job_reference_attachments as _jra_svc  # type: ignore
        import services.task_attachment_autofill as _taf  # type: ignore

    _jdt_af_css_once()
    rk = _jdt_af_result_key(job_id)
    toast_k = f"jdt_af_applied_{job_id}"
    if st.session_state.pop(toast_k, None):
        try:
            st.toast("Applied — review **Add task** below.")
        except Exception:
            st.success("Applied — review **Add task** below.")
    bucket = _jra_svc.reference_bucket()
    fn = fetch_by_match_admin if admin_read else fetch_by_match
    try:
        att_rows = list(
            fn("job_reference_attachments", {"job_id": str(job_id).strip()}, limit=200) or []
        )
    except Exception:
        att_rows = []
    candidates = [
        r
        for r in att_rows
        if isinstance(r, dict) and _taf.is_autofill_supported_filename(str(r.get("file_name") or ""))
    ]
    id_to_row = {str(r.get("id")): r for r in candidates if str(r.get("id") or "").strip()}

    with st.container(border=True):
        st.markdown('<span class="ips-jdt-af-card"></span>', unsafe_allow_html=True)
        st.markdown("###### Auto fill from attachment")
        st.caption(
            "Pick a **saved reference** file or **upload** a PDF/image, then extract text to pre-fill **Add task** "
            "(best-effort; review before saving)."
        )
        ids = [str(r.get("id")) for r in candidates if str(r.get("id") or "").strip()]

        def _lbl(rid: str) -> str:
            if not rid:
                return "— Select saved reference —"
            row = id_to_row.get(rid) or {}
            return str(row.get("file_name") or rid)[:100]

        sel = st.selectbox(
            "Reference attachment",
            options=[""] + ids,
            format_func=_lbl,
            key=f"jdt_af_sel_{job_id}",
            label_visibility="visible",
        )
        up = st.file_uploader(
            "Or upload PDF / image (one-time, not saved as reference)",
            type=["jpg", "jpeg", "png", "webp", "pdf"],
            key=f"jdt_af_up_{job_id}",
            accept_multiple_files=False,
        )

        if st.button(
            "Auto Fill From Attachment",
            type="secondary",
            use_container_width=True,
            key=f"jdt_af_go_{job_id}",
        ):
            data: bytes | None = None
            fname = ""
            if up is not None:
                try:
                    data = up.getvalue()
                    fname = str(getattr(up, "name", "") or "upload")
                except Exception:
                    data = None
            elif str(sel or "").strip():
                row = id_to_row.get(str(sel).strip())
                if row:
                    data, fname = _taf.fetch_bytes_for_row(row, bucket=bucket)
            if not data:
                st.session_state[rk] = {
                    "ok": False,
                    "msg": "Choose a saved attachment or upload a file first.",
                }
                st.rerun()
            if not _taf.is_autofill_supported_filename(fname):
                st.session_state[rk] = {
                    "ok": False,
                    "msg": "Could not auto-fill from this attachment. Please enter task details manually.",
                }
                st.rerun()
            txt = _taf.extract_text_from_bytes(fname, data)
            if not str(txt or "").strip():
                st.session_state[rk] = {
                    "ok": False,
                    "msg": "Could not auto-fill from this attachment. Please enter task details manually.",
                }
                st.rerun()
            parsed = _taf.parse_hazard_sheet_text(txt)
            has_any = any(
                str(parsed.get(k) or "").strip()
                for k in ("task_number", "location", "issue", "action_required")
            ) or bool(parsed.get("priority")) or bool(parsed.get("planned_date"))
            if not has_any:
                st.session_state[rk] = {
                    "ok": False,
                    "msg": "Could not auto-fill from this attachment. Please enter task details manually.",
                }
                st.rerun()
            st.session_state[rk] = {"ok": True, "parsed": parsed}
            st.rerun()

    res = st.session_state.get(rk)
    if isinstance(res, dict):
        if not res.get("ok"):
            st.warning(str(res.get("msg") or "Could not auto-fill from this attachment."))
            if st.button("Dismiss", key=f"jdt_af_dismiss_{job_id}", use_container_width=True):
                st.session_state.pop(rk, None)
                st.rerun()
        else:
            parsed = dict(res.get("parsed") or {})
            with st.container(border=True):
                st.markdown('<span class="ips-jdt-af-card"></span>', unsafe_allow_html=True)
                pd = parsed.get("planned_date")
                pd_line = ""
                if isinstance(pd, date):
                    pd_line = f"- **Planned date:** {html.escape(pd.isoformat())}  \n"
                st.markdown(
                    "**Extracted preview**\n\n"
                    f"- **Task #:** {html.escape(str(parsed.get('task_number') or '—'))}  \n"
                    f"- **Priority:** {html.escape(str(parsed.get('priority') or '—'))}  \n"
                    f"{pd_line}"
                    f"- **Location:** {html.escape(str(parsed.get('location') or '—'))}  \n"
                    f"- **Issue:** {html.escape(str(parsed.get('issue') or '—'))}  \n"
                    f"- **Action required:** {html.escape(str(parsed.get('action_required') or '—'))}"
                )
                overwrite = st.checkbox(
                    "Replace fields I already filled",
                    value=False,
                    key=f"jdt_af_over_{job_id}",
                    help="When off, only empty Add task fields are updated.",
                )
                b1, b2 = st.columns(2, gap="small")
                with b1:
                    if st.button(
                        "Apply to Task Form",
                        type="primary",
                        use_container_width=True,
                        key=f"jdt_af_apply_{job_id}",
                    ):
                        _apply_autofill_to_add_task_widgets(job_id, parsed, overwrite=overwrite)
                        st.session_state.pop(rk, None)
                        st.session_state[f"jdt_af_applied_{job_id}"] = True
                        st.rerun()
                with b2:
                    if st.button("Cancel", type="secondary", use_container_width=True, key=f"jdt_af_cancel_{job_id}"):
                        st.session_state.pop(rk, None)
                        st.rerun()


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
            tno = html.escape(task_number_display(t))

            with st.container(border=True):
                st.markdown(
                    f'<p style="margin:0 0 0.25rem;font-size:1.45rem;font-weight:700;color:#0f172a;">{tno}</p>'
                    f'<div style="margin-bottom:0.4rem;display:flex;flex-wrap:wrap;gap:0.35rem;align-items:center;">'
                    f'{_priority_badge_html(t.get("priority"))}{_task_status_badge(stt)}</div>'
                    f'<p style="margin:0.15rem 0;color:#4b5563;font-size:0.9rem;"><strong>Location</strong> '
                    f"{html.escape(loc)}</p>"
                    f'<p style="margin:0.15rem 0;color:#4b5563;font-size:0.9rem;"><strong>Issue</strong> '
                    f"{html.escape(snip or '—')}</p>",
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

    st.divider()
    _jra_ui.render_job_reference_attachments_panel(
        job_id=job_id,
        tasks=list(rows or []),
        admin_read=admin_read,
        can_manage=str(_jra_role() or "").strip().lower() in {"admin", "manager"},
    )

    if can_edit_tasks:
        _inject_task_tab_add_form_css()
        st.markdown("##### Add task")
        _render_add_task_autofill_from_attachment(job_id=job_id, admin_read=admin_read)
        st.markdown('<span class="ips-job-add-task-anchor"></span>', unsafe_allow_html=True)
        tn = st.text_input("Task #", key=f"jdt_add_tn_{job_id}")
        a1, a2 = st.columns(2, gap="small")
        with a1:
            pr = st.selectbox(
                "Priority",
                ("low", "normal", "high", "critical"),
                index=1,
                format_func=lambda x: x.title(),
                key=f"jdt_add_pr_{job_id}",
                on_change=lambda: st.session_state.update({f"jdt_add_pr_touched_{job_id}": True}),
            )
        with a2:
            pl = st.date_input(
                "Planned date",
                value=date.today(),
                key=f"jdt_add_pl_{job_id}",
                on_change=lambda: st.session_state.update({f"jdt_add_pl_touched_{job_id}": True}),
            )
        a3, a4 = st.columns(2, gap="small")
        with a3:
            loc = st.text_input("Location", key=f"jdt_add_loc_{job_id}")
        with a4:
            iss = st.text_input("Issue (short)", key=f"jdt_add_iss_{job_id}")
        act = st.text_input("Action required", key=f"jdt_add_act_{job_id}")
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
        return f"{task_number_display(tt)} · {iss}"

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
            lab = task_number_display(t)
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
        label = task_number_display(t)
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
