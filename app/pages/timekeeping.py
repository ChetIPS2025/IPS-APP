"""Timekeeping module (Phase 2C)."""

from __future__ import annotations

import html
from datetime import date, timedelta
from typing import Any

import streamlit as st

try:
    from app.components.headers import render_page_brand_header
    from app.components.table_filters import (
        apply_column_filters,
        build_filter_options,
        render_table_header_cell,
    )
    from app.components.record_modal import (
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        placeholder_html,
        record_session_key,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
    )
    from app.pages._core._data import (
        default_weekly_grid,
        job_options_for_timekeeping,
        load_timekeeping_grid,
        load_timekeeping_summaries,
        persist_timekeeping_approve,
        persist_timekeeping_days,
        persist_timekeeping_reject,
        persist_timekeeping_submit,
        persist_timekeeping_week,
    )
    from app.pages._core._session import select_key
    from app.styles import inject_timekeeping_module_css
    from app.utils.dates import week_end, week_start
    from app.utils.formatting import fmt_date
except ImportError:
    from components.headers import render_page_brand_header  # type: ignore
    from components.table_filters import (  # type: ignore
        apply_column_filters,
        build_filter_options,
        render_table_header_cell,
    )
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        placeholder_html,
        record_session_key,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
    )
    from pages._core._data import (  # type: ignore
        default_weekly_grid,
        job_options_for_timekeeping,
        load_timekeeping_grid,
        load_timekeeping_summaries,
        persist_timekeeping_approve,
        persist_timekeeping_days,
        persist_timekeeping_reject,
        persist_timekeeping_submit,
        persist_timekeeping_week,
    )
    from pages._core._session import select_key  # type: ignore
    from styles import inject_timekeeping_module_css  # type: ignore
    from utils.dates import week_end, week_start  # type: ignore
    from utils.formatting import fmt_date  # type: ignore

_SEL = select_key("timekeeping")
_MODULE = "timekeeping"
_TABLE_KEY = "timekeeping_list"
_MODAL_KEY = "ips_timekeeping_detail_modal_id"
_CACHE_KEY = "_ips_timekeeping_modal_by_id"
_WEEK_KEY = "ips_timekeeping_week_start"
SELECTED_TIMECARD_KEY = "selected_timecard_id"
SHOW_TIMECARD_MODAL_KEY = "show_timecard_detail_modal"
_ALL_TIMECARD_IDS_KEY = "_ips_timekeeping_visible_ids"
_TK_COLS = [0.35, 2.4, 1.8, 1.4, 1.0, 1.0, 1.0, 1.2, 1.3]
_TK_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("EMPLOYEE", "employee_name"),
    ("DEPARTMENT", "department"),
    ("WEEK START", "week_start"),
    ("ST TOTAL", None),
    ("OT TOTAL", None),
    ("DT TOTAL", None),
    ("TOTAL HOURS", None),
    ("STATUS", "status"),
]
_STATUS_FILTER_OPTS = ["Draft", "Pending", "Approved", "Rejected"]
_TK_COLUMN_FILTER_SPECS: list[tuple[str, Any]] = [
    ("employee_name", None),
    ("department", None),
    ("week_start", lambda r: fmt_date(r.get("week_start"))),
    ("status", lambda r: _normalize_timecard_status(r.get("status"))),
]
_DAY_GRID_COLS = [0.55, 0.7, 2.0, 0.75, 0.75, 0.75, 0.75, 1.3]
_DAY_GRID_LABELS = [
    "Day",
    "Date",
    "Job",
    "ST (Hrs)",
    "OT (Hrs)",
    "DT (Hrs)",
    "Total (Hrs)",
    "Notes",
]


def _timecard_is_editable(status: str) -> bool:
    return status in ("Draft", "Pending", "Rejected")


def _db_status_for_save(status: str) -> str:
    normalized = _normalize_timecard_status(status)
    if normalized == "Approved":
        return "Approved"
    if normalized == "Rejected":
        return "Rejected"
    return "Pending"


def _current_user_id() -> str | None:
    try:
        from app.auth import current_profile
    except ImportError:
        from auth import current_profile  # type: ignore
    uid = str(current_profile().get("id") or "").strip()
    return uid or None


def _current_user_name() -> str:
    try:
        from app.auth import current_profile
    except ImportError:
        from auth import current_profile  # type: ignore
    profile = current_profile()
    return str(profile.get("name") or profile.get("email") or "User").strip() or "User"


def _can_approve_timekeeping() -> bool:
    try:
        from app.auth import current_role
        from app.utils.permissions import can_approve_timekeeping
    except ImportError:
        from auth import current_role  # type: ignore
        from utils.permissions import can_approve_timekeeping  # type: ignore
    return can_approve_timekeeping(current_role())


def _patch_timecard_cache(emp: dict, week_start_d: date, updates: dict[str, Any]) -> None:
    tid = _timecard_id_for_row(emp, week_start_d)
    cache = st.session_state.get(_CACHE_KEY) or {}
    if not isinstance(cache, dict):
        return
    existing = cache.get(tid)
    if isinstance(existing, dict):
        cache[tid] = {**existing, **updates}
        st.session_state[_CACHE_KEY] = cache


def _invalidate_weekly_grid(emp: dict, week_start_d: date) -> None:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    gk = _grid_key(eid)
    st.session_state.pop(gk, None)
    st.session_state.pop(f"{gk}_week", None)


def _current_week_start() -> date:
    raw = st.session_state.get(_WEEK_KEY)
    if isinstance(raw, date):
        return raw
    ws = week_start()
    st.session_state[_WEEK_KEY] = ws
    return ws


def _week_start_from_row(row: dict) -> date:
    raw = row.get("week_start")
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return _current_week_start()


def _grid_key(emp_id: str) -> str:
    return f"ips_time_grid_{emp_id}"


def _short_day(value: str) -> str:
    return str(value or "")[:3]


def _fmt_table_hours(val: object) -> str:
    try:
        return f"{float(val):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _normalize_timecard_status(raw: object) -> str:
    s = str(raw or "").strip().lower()
    if s in ("", "draft"):
        return "Draft"
    if s == "approved":
        return "Approved"
    if s == "pending":
        return "Pending"
    if s == "rejected":
        return "Rejected"
    return str(raw or "Draft").strip().title() or "Draft"


def _timecard_status_pill_html(status: str) -> str:
    cls_map = {
        "Draft": "ips-timekeeping-status-draft",
        "Pending": "ips-timekeeping-status-pending",
        "Approved": "ips-timekeeping-status-approved",
        "Rejected": "ips-timekeeping-status-rejected",
    }
    cls = cls_map.get(status, "ips-timekeeping-status-draft")
    return (
        f'<span class="ips-timekeeping-status-pill {cls}">'
        f"{html.escape(status)}</span>"
    )


def _timecard_id_for_row(row: dict, ws: date) -> str:
    eid = str(row.get("id") or row.get("employee_id") or "").strip()
    week_start_str = str(row.get("week_start") or ws.isoformat())[:10]
    return f"{eid}_{week_start_str}"


def _build_timecard_row(row: dict, ws: date) -> dict:
    st_total, ot_total, dt_total, total = _emp_totals(row)
    status = _normalize_timecard_status(row.get("status"))
    return {
        **row,
        "timecard_id": _timecard_id_for_row(row, ws),
        "employee_id": str(row.get("id") or "").strip(),
        "employee_name": str(row.get("name") or row.get("employee_name") or "—"),
        "department": str(row.get("department") or row.get("department_name") or "—") or "—",
        "week_start": str(row.get("week_start") or ws.isoformat())[:10],
        "st_total": st_total,
        "ot_total": ot_total,
        "dt_total": dt_total,
        "total_hours": total,
        "status": status,
    }


def _timecard_select_key(timecard_id: str) -> str:
    return f"timecard_select_{timecard_id}"


def _clear_timecard_selection(timecard_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_TIMECARD_KEY] = None
    st.session_state[SHOW_TIMECARD_MODAL_KEY] = False
    ids = list(timecard_ids or [])
    for tid in ids:
        st.session_state[_timecard_select_key(tid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("timecard_select_"):
            st.session_state[key] = False


def _on_timecard_checkbox_change(timecard_id: str, all_timecard_ids: list[str]) -> None:
    key = _timecard_select_key(timecard_id)
    if st.session_state.get(key):
        for tid in all_timecard_ids:
            if tid != timecard_id:
                st.session_state[_timecard_select_key(tid)] = False
        st.session_state[SELECTED_TIMECARD_KEY] = timecard_id
        st.session_state[SHOW_TIMECARD_MODAL_KEY] = True
        st.session_state[_MODAL_KEY] = timecard_id
    elif st.session_state.get(SELECTED_TIMECARD_KEY) == timecard_id:
        st.session_state[SELECTED_TIMECARD_KEY] = None
        st.session_state[SHOW_TIMECARD_MODAL_KEY] = False


def _clear_timecard_modal() -> None:
    timecard_ids = st.session_state.get(_ALL_TIMECARD_IDS_KEY) or []
    _clear_timecard_selection([str(tid) for tid in timecard_ids])
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _get_selected_timecard() -> dict | None:
    tid = st.session_state.get(SELECTED_TIMECARD_KEY)
    if not tid:
        return None
    cache = st.session_state.get(_CACHE_KEY) or {}
    if isinstance(cache, dict):
        rec = cache.get(str(tid))
        if isinstance(rec, dict):
            return rec
    return None


def _emp_totals(emp: dict) -> tuple[float, float, float, float]:
    st_total = float(emp.get("st_total") or 0)
    ot_total = float(emp.get("ot_total") or 0)
    dt_total = float(emp.get("dt_total") or 0)
    return st_total, ot_total, dt_total, st_total + ot_total + dt_total


def _ensure_weekly_grid(emp: dict, week_start_d: date) -> list[dict]:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    gk = _grid_key(eid)
    week_sig = week_start_d.isoformat()
    if st.session_state.get(f"{gk}_week") != week_sig:
        try:
            st.session_state[gk] = load_timekeeping_grid(eid, week_start_d)
        except Exception:
            st.session_state[gk] = default_weekly_grid(eid, week_start_d)
        st.session_state[f"{gk}_week"] = week_sig
    return st.session_state[gk]


def _render_day_grid_header() -> None:
    header = st.columns(_DAY_GRID_COLS)
    for col, lbl in zip(header, _DAY_GRID_LABELS):
        with col:
            st.markdown(
                f'<div class="ips-time-day-head">{html.escape(lbl)}</div>',
                unsafe_allow_html=True,
            )


def _render_weekly_grid_readonly(emp: dict, week_start_d: date) -> None:
    grid = _ensure_weekly_grid(emp, week_start_d)
    _render_day_grid_header()
    for row in grid:
        c = st.columns(_DAY_GRID_COLS)
        row_total = (
            float(row.get("st") or 0)
            + float(row.get("ot") or 0)
            + float(row.get("dt") or 0)
        )
        with c[0]:
            st.markdown(
                f'<div class="ips-time-day-row">{html.escape(_short_day(str(row.get("day") or "")))}</div>',
                unsafe_allow_html=True,
            )
        with c[1]:
            st.markdown(
                f'<div class="ips-time-day-row">{html.escape(fmt_date(row.get("date")))}</div>',
                unsafe_allow_html=True,
            )
        with c[2]:
            st.markdown(
                f'<div class="ips-time-day-row">{html.escape(str(row.get("job") or "—"))}</div>',
                unsafe_allow_html=True,
            )
        with c[3]:
            st.markdown(
                f'<div class="ips-time-day-row">{html.escape(_fmt_table_hours(row.get("st")))}</div>',
                unsafe_allow_html=True,
            )
        with c[4]:
            st.markdown(
                f'<div class="ips-time-day-row">{html.escape(_fmt_table_hours(row.get("ot")))}</div>',
                unsafe_allow_html=True,
            )
        with c[5]:
            st.markdown(
                f'<div class="ips-time-day-row">{html.escape(_fmt_table_hours(row.get("dt")))}</div>',
                unsafe_allow_html=True,
            )
        with c[6]:
            st.markdown(
                f'<div class="ips-time-day-row">{html.escape(_fmt_table_hours(row_total))}</div>',
                unsafe_allow_html=True,
            )
        with c[7]:
            st.markdown(
                f'<div class="ips-time-day-row">{html.escape(str(row.get("notes") or "—"))}</div>',
                unsafe_allow_html=True,
            )


def _render_weekly_grid_edit(emp: dict, week_start_d: date) -> None:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    gk = _grid_key(eid)
    week_sig = week_start_d.isoformat()
    grid = _ensure_weekly_grid(emp, week_start_d)
    job_opts = job_options_for_timekeeping()

    edit_cols = [0.55, 0.7, 2.0, 0.75, 0.75, 0.75, 0.75, 1.3, 0.35]
    header = st.columns(edit_cols)
    labels = [* _DAY_GRID_LABELS, ""]
    for col, lbl in zip(header, labels):
        with col:
            st.markdown(
                f'<div class="ips-time-day-head">{html.escape(lbl)}</div>',
                unsafe_allow_html=True,
            )

    for i, row in enumerate(grid):
        c = st.columns(edit_cols)
        with c[0]:
            st.markdown(
                f'<div class="ips-time-day-row">{html.escape(_short_day(str(row.get("day") or "")))}</div>',
                unsafe_allow_html=True,
            )
        with c[1]:
            st.markdown(
                f'<div class="ips-time-day-row">{html.escape(fmt_date(row.get("date")))}</div>',
                unsafe_allow_html=True,
            )
        with c[2]:
            cur_job = str(row.get("job") or job_opts[0])
            idx = job_opts.index(cur_job) if cur_job in job_opts else 0
            grid[i]["job"] = st.selectbox(
                "Job",
                job_opts,
                index=idx,
                key=f"tk_job_{eid}_{week_sig}_{i}",
                label_visibility="collapsed",
            )
        with c[3]:
            grid[i]["st"] = st.number_input(
                "ST",
                value=float(row.get("st") or 0),
                key=f"tk_st_{eid}_{week_sig}_{i}",
                label_visibility="collapsed",
                step=0.5,
                format="%.2f",
            )
        with c[4]:
            grid[i]["ot"] = st.number_input(
                "OT",
                value=float(row.get("ot") or 0),
                key=f"tk_ot_{eid}_{week_sig}_{i}",
                label_visibility="collapsed",
                step=0.5,
                format="%.2f",
            )
        with c[5]:
            grid[i]["dt"] = st.number_input(
                "DT",
                value=float(row.get("dt") or 0),
                key=f"tk_dt_{eid}_{week_sig}_{i}",
                label_visibility="collapsed",
                step=0.5,
                format="%.2f",
            )
        with c[6]:
            row_total = (
                float(grid[i].get("st") or 0)
                + float(grid[i].get("ot") or 0)
                + float(grid[i].get("dt") or 0)
            )
            st.markdown(
                f'<div class="ips-time-day-row">{html.escape(_fmt_table_hours(row_total))}</div>',
                unsafe_allow_html=True,
            )
        with c[7]:
            grid[i]["notes"] = st.text_input(
                "Notes",
                value=str(row.get("notes") or ""),
                key=f"tk_notes_{eid}_{week_sig}_{i}",
                label_visibility="collapsed",
                placeholder="Add notes...",
            )
        with c[8]:
            if st.button("🗑", key=f"tk_del_{eid}_{week_sig}_{i}", help="Clear row"):
                grid[i]["job"] = job_opts[0] if job_opts else "— No job —"
                grid[i]["st"] = 0.0
                grid[i]["ot"] = 0.0
                grid[i]["dt"] = 0.0
                grid[i]["notes"] = ""
                st.session_state[gk] = grid
                st.rerun()
    st.session_state[gk] = grid


def _save_timekeeping_week(
    emp: dict,
    week_start_d: date,
    *,
    status: str | None = None,
    show_message: bool = True,
) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    grid = _ensure_weekly_grid(emp, week_start_d)
    current_status = _normalize_timecard_status(emp.get("status"))
    save_status = _db_status_for_save(status or current_status)
    summary = {
        "st_total": sum(float(r.get("st") or 0) for r in grid),
        "ot_total": sum(float(r.get("ot") or 0) for r in grid),
        "dt_total": sum(float(r.get("dt") or 0) for r in grid),
        "status": save_status,
        "notes": str(emp.get("notes") or ""),
    }
    ok, msg = persist_timekeeping_week(eid, week_start_d, summary)
    if not ok:
        st.error(msg)
        return False
    ok2, msg2 = persist_timekeeping_days(eid, week_start_d, grid)
    if ok2:
        _patch_timecard_cache(
            emp,
            week_start_d,
            {
                **summary,
                "status": _normalize_timecard_status(save_status),
                "total_hours": summary["st_total"] + summary["ot_total"] + summary["dt_total"],
            },
        )
        _invalidate_weekly_grid(emp, week_start_d)
        if show_message:
            st.success(msg)
        return True
    detail = f" {msg2}" if msg2 else ""
    st.warning(f"Week totals were saved, but daily entry details could not be saved.{detail}")
    return False


def _submit_timekeeping_week(emp: dict, week_start_d: date) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    if not _save_timekeeping_week(emp, week_start_d, status="Pending", show_message=False):
        return False
    ok, msg = persist_timekeeping_submit(eid, week_start_d)
    if ok:
        _patch_timecard_cache(emp, week_start_d, {"status": "Pending"})
        _invalidate_weekly_grid(emp, week_start_d)
        st.success(msg)
        return True
    st.error(msg)
    return False


def _approve_timekeeping_week(emp: dict, week_start_d: date) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    approver = _current_user_id()
    if not approver:
        st.error("Your profile is missing an approver id.")
        return False
    ok, msg = persist_timekeeping_approve(eid, week_start_d, approved_by=approver)
    if ok:
        _patch_timecard_cache(
            emp,
            week_start_d,
            {
                "status": "Approved",
                "approved_by": approver,
                "approved_at": fmt_date(date.today()),
            },
        )
        st.success(msg)
        return True
    st.error(msg)
    return False


def _reject_timekeeping_week(emp: dict, week_start_d: date, notes: str) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    approver = _current_user_id()
    if not approver:
        st.error("Your profile is missing an approver id.")
        return False
    ok, msg = persist_timekeeping_reject(
        eid,
        week_start_d,
        approved_by=approver,
        notes=notes,
    )
    if ok:
        _patch_timecard_cache(
            emp,
            week_start_d,
            {
                "status": "Rejected",
                "notes": notes,
                "approved_by": approver,
            },
        )
        _invalidate_weekly_grid(emp, week_start_d)
        st.success(msg)
        return True
    st.error(msg)
    return False


def _render_daily_entries_tab(emp: dict, week_start_d: date) -> None:
    status = _normalize_timecard_status(emp.get("status"))
    if _timecard_is_editable(status):
        _render_weekly_grid_edit(emp, week_start_d)
        action_left, action_right = st.columns([1, 1])
        record_key = record_session_key(emp, "id")
        with action_left:
            if st.button("Save Hours", key=f"tk_save_hours_{record_key}", type="primary"):
                if _save_timekeeping_week(emp, week_start_d):
                    st.rerun()
        with action_right:
            if status in ("Draft", "Rejected") and st.button(
                "Submit for Approval",
                key=f"tk_submit_{record_key}",
            ):
                if _submit_timekeeping_week(emp, week_start_d):
                    st.rerun()
        if status == "Pending":
            st.caption("Hours can still be edited while pending approval. Save changes, then wait for a supervisor to approve.")
        elif status == "Rejected":
            st.caption("This timecard was rejected. Update the hours and submit again for approval.")
    else:
        _render_weekly_grid_readonly(emp, week_start_d)
        st.info("This week is approved and locked.")


def _render_approval_tab(emp: dict, week_start_d: date) -> None:
    status = _normalize_timecard_status(emp.get("status"))
    approved_at = str(emp.get("approved_at") or "").strip()
    notes = str(emp.get("notes") or "").strip()
    st.markdown(
        dialog_card_html(
            "Approval Status",
            f'<div class="ips-detail-grid">'
            f'{detail_field_html("Status", status, html_value=_timecard_status_pill_html(status))}'
            f"{detail_field_html('Employee', emp.get('name') or emp.get('employee_name'))}"
            f"{detail_field_html('Week', f'{fmt_date(week_start_d)} – {fmt_date(week_end(week_start_d))}')}"
            f"{detail_field_html('Reviewed At', fmt_date(approved_at) if approved_at else '—')}"
            f"{detail_field_html('Reviewer Notes', notes or '—')}"
            f"</div>",
        ),
        unsafe_allow_html=True,
    )

    if status == "Pending" and _can_approve_timekeeping():
        reject_notes = st.text_area(
            "Rejection notes (optional)",
            key=f"tk_reject_notes_{record_session_key(emp, 'id')}",
            height=80,
            placeholder="Explain what needs to be corrected…",
        )
        approve_col, reject_col = st.columns(2)
        with approve_col:
            if st.button("Approve Timecard", key=f"tk_approve_{record_session_key(emp, 'id')}", type="primary"):
                if _approve_timekeeping_week(emp, week_start_d):
                    st.rerun()
        with reject_col:
            if st.button("Reject Timecard", key=f"tk_reject_{record_session_key(emp, 'id')}"):
                if _reject_timekeeping_week(emp, week_start_d, reject_notes):
                    st.rerun()
    elif status == "Pending":
        st.caption("Waiting for supervisor approval.")
    elif status == "Draft":
        st.caption("Enter hours on the Daily Entries tab, then submit for approval.")
    elif status == "Rejected":
        st.caption("Update hours on the Daily Entries tab and submit again for approval.")
    elif status == "Approved":
        st.caption(f"Approved by {_current_user_name() if not approved_at else 'supervisor'}.")


def _render_timekeeping_view_tabs(emp: dict, week_start_d: date) -> None:
    st_total, ot_total, dt_total, total = _emp_totals(emp)
    status = _normalize_timecard_status(emp.get("status"))
    tab_weekly, tab_daily, tab_approval, tab_notes, tab_activity = st.tabs(
        ["Weekly Timecard", "Daily Entries", "Approval", "Notes", "Activity"]
    )

    with tab_weekly:
        overview_html = (
            '<div class="ips-detail-grid">'
            f"{detail_field_html('Employee', emp.get('name') or emp.get('employee_name'))}"
            f"{detail_field_html('Department', emp.get('department'))}"
            f'{detail_field_html("Status", status, html_value=_timecard_status_pill_html(status))}'
            f"{detail_field_html('Week', f'{fmt_date(week_start_d)} – {fmt_date(week_end(week_start_d))}')}"
            f"{detail_field_html('ST Total', _fmt_table_hours(st_total))}"
            f"{detail_field_html('OT Total', _fmt_table_hours(ot_total))}"
            f"{detail_field_html('DT Total', _fmt_table_hours(dt_total))}"
            f"{detail_field_html('Total Hours', _fmt_table_hours(total))}"
            "</div>"
        )
        st.markdown(dialog_card_html("Week Summary", overview_html), unsafe_allow_html=True)

    with tab_daily:
        _render_daily_entries_tab(emp, week_start_d)

    with tab_approval:
        _render_approval_tab(emp, week_start_d)

    with tab_notes:
        note_text = str(emp.get("notes") or "").strip()
        if note_text:
            st.markdown(dialog_card_html("Notes", detail_field_html("Notes", note_text)), unsafe_allow_html=True)
        else:
            placeholder_html("No notes on this timecard yet.")

    with tab_activity:
        activity_lines: list[str] = []
        if approved_at := str(emp.get("approved_at") or "").strip():
            activity_lines.append(f"{fmt_date(approved_at)} — Status changed to {status}")
        if activity_lines:
            st.markdown(
                dialog_card_html("Activity", "".join(detail_field_html("Event", line) for line in activity_lines)),
                unsafe_allow_html=True,
            )
        else:
            placeholder_html("Activity will appear after approval actions are recorded.")


def render_timekeeping_detail_dialog(emp: dict, week_start_d: date) -> None:
    st_total, ot_total, dt_total, total = _emp_totals(emp)
    status = _normalize_timecard_status(emp.get("status"))
    render_modal_shell()
    render_modal_header(
        title=str(emp.get("name") or emp.get("employee_name") or "Employee"),
        subtitle=str(emp.get("department") or ""),
        status=status,
    )
    render_modal_meta_grid(
        [
            ("Week", f"{fmt_date(week_start_d)} – {fmt_date(week_end(week_start_d))}"),
            ("ST Total", _fmt_table_hours(st_total)),
            ("OT Total", _fmt_table_hours(ot_total)),
            ("DT Total", _fmt_table_hours(dt_total)),
            ("Total Hours", _fmt_table_hours(total)),
        ]
    )
    _render_timekeeping_view_tabs(emp, week_start_d)


@st.dialog("Timecard Details", width="large", on_dismiss=_clear_timecard_modal)
def _show_timecard_detail_modal() -> None:
    tc = _get_selected_timecard()
    if not tc:
        render_missing_record(_clear_timecard_modal, close_key="tk_modal_missing_close")
        return
    render_timekeeping_detail_dialog(tc, _week_start_from_row(tc))


def _filter_timecards(
    summaries: list[dict],
    ws: date,
) -> list[dict]:
    rows = [_build_timecard_row(row, ws) for row in summaries]
    return apply_column_filters(rows, _TABLE_KEY, _TK_COLUMN_FILTER_SPECS)


def _render_custom_timekeeping_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
) -> list[str]:
    if not filtered:
        st.info("No timecards match your filters.")
        st.session_state[_ALL_TIMECARD_IDS_KEY] = []
        return []

    all_timecard_ids = [
        str(r.get("timecard_id") or "").strip()
        for r in filtered
        if str(r.get("timecard_id") or "").strip()
    ]
    st.session_state[_ALL_TIMECARD_IDS_KEY] = all_timecard_ids

    with st.container(key="timekeeping_table_wrap"):
        st.markdown('<div class="ips-timekeeping-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_TK_COLS, gap="small", vertical_alignment="center")
        for col, (label, field) in zip(header_cols, _TK_HEADER_SPECS):
            with col:
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-timekeeping-header-row ips-timekeeping-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-timekeeping-header-row ips-timekeeping-cell",
                    )

        for row in filtered:
            timecard_id = str(row.get("timecard_id") or "").strip()
            if not timecard_id:
                continue

            employee_name = str(row.get("employee_name") or "—")
            department = str(row.get("department") or "—")
            week_label = fmt_date(row.get("week_start"))
            status = _normalize_timecard_status(row.get("status"))

            cols = st.columns(_TK_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                st.checkbox(
                    "",
                    key=_timecard_select_key(timecard_id),
                    label_visibility="collapsed",
                    on_change=_on_timecard_checkbox_change,
                    args=(timecard_id, all_timecard_ids),
                )

            with cols[1]:
                st.markdown(
                    f'<div class="ips-timekeeping-employee">{html.escape(employee_name)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[2]:
                st.markdown(
                    f'<div class="ips-timekeeping-muted ips-timekeeping-cell">'
                    f"{html.escape(department)}</div>",
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(
                    f'<div class="ips-timekeeping-cell">{html.escape(week_label)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(
                    f'<div class="ips-timekeeping-hours ips-timekeeping-cell">'
                    f"{html.escape(_fmt_table_hours(row.get('st_total')))}</div>",
                    unsafe_allow_html=True,
                )

            with cols[5]:
                st.markdown(
                    f'<div class="ips-timekeeping-hours ips-timekeeping-cell">'
                    f"{html.escape(_fmt_table_hours(row.get('ot_total')))}</div>",
                    unsafe_allow_html=True,
                )

            with cols[6]:
                st.markdown(
                    f'<div class="ips-timekeeping-hours ips-timekeeping-cell">'
                    f"{html.escape(_fmt_table_hours(row.get('dt_total')))}</div>",
                    unsafe_allow_html=True,
                )

            with cols[7]:
                st.markdown(
                    f'<div class="ips-timekeeping-hours ips-timekeeping-cell">'
                    f"{html.escape(_fmt_table_hours(row.get('total_hours')))}</div>",
                    unsafe_allow_html=True,
                )

            with cols[8]:
                st.markdown(_timecard_status_pill_html(status), unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    return all_timecard_ids


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("timekeeping"):
        return

    inject_timekeeping_module_css()
    st.markdown(
        '<span class="ips-timekeeping-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    ws = _current_week_start()
    we = week_end(ws)
    summaries = load_timekeeping_summaries(ws)
    all_rows = [_build_timecard_row(row, ws) for row in summaries]
    filter_options = build_filter_options(all_rows, _TK_COLUMN_FILTER_SPECS)

    def _tk_export() -> None:
        st.button("Export", key="tk_export", use_container_width=True)

    render_page_brand_header(
        "Timekeeping",
        "View and edit employee weekly time entries.",
        actions=[_tk_export],
    )

    nav1, nav2, nav3, week_col = st.columns([1, 1, 1, 2.2], gap="small")
    with nav1:
        if st.button("Previous Week", key="tk_prev_week", use_container_width=True):
            st.session_state[_WEEK_KEY] = ws - timedelta(days=7)
            st.rerun()
    with nav2:
        if st.button("Current Week", key="tk_current_week", use_container_width=True):
            st.session_state[_WEEK_KEY] = week_start()
            st.rerun()
    with nav3:
        if st.button("Next Week", key="tk_next_week", use_container_width=True):
            st.session_state[_WEEK_KEY] = ws + timedelta(days=7)
            st.rerun()
    with week_col:
        st.markdown(
            f'<p class="ips-time-week-range">{html.escape(fmt_date(ws))} – {html.escape(fmt_date(we))}</p>'
            f'<p class="ips-time-week-sub">Week {ws.isocalendar()[1]}</p>',
            unsafe_allow_html=True,
        )

    filtered = _filter_timecards(summaries, ws)

    st.caption(f"{len(filtered)} timecard(s)")

    build_modal_cache(filtered, row_id_key="timecard_id", cache_key=_CACHE_KEY)
    _render_custom_timekeeping_table(filtered, filter_options=filter_options)

    if st.session_state.get(SELECTED_TIMECARD_KEY) and st.session_state.get(SHOW_TIMECARD_MODAL_KEY):
        _show_timecard_detail_modal()

    try:
        from app.auth import current_role
        from app.utils.permissions import role_can_access_page
    except ImportError:
        from auth import current_role  # type: ignore
        from utils.permissions import role_can_access_page  # type: ignore
    if role_can_access_page(current_role(), "weekly_timesheets"):
        st.divider()
        st.markdown("**Weekly job timesheets**")
        st.caption("Build customer-facing weekly timesheets from timekeeping hours and job expenses.")
        if st.button("Open Weekly Timesheets", key="tk_open_weekly_ts", use_container_width=False):
            st.session_state["ips_nav_page"] = "weekly_timesheets"
            st.rerun()
