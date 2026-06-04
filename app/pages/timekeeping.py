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
        load_jobs,
        load_timekeeping_grid,
        load_timekeeping_summaries,
        persist_timekeeping_approve,
        persist_timekeeping_days,
        persist_timekeeping_day_approve,
        persist_timekeeping_day_reject,
        persist_timekeeping_day_submit,
        persist_timekeeping_reject,
        persist_timekeeping_submit,
        persist_timekeeping_week,
    )
    from app.pages._core._session import select_key
    from app.styles import (
        _inject_timekeeping_daily_hour_focus_script,
        inject_timekeeping_module_css,
    )
    from app.utils.dates import week_dates, week_end, week_start
    from app.utils.field_context import get_field_job_id, is_field_context, is_field_mode, render_field_job_bar
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
        load_jobs,
        load_timekeeping_grid,
        load_timekeeping_summaries,
        persist_timekeeping_approve,
        persist_timekeeping_days,
        persist_timekeeping_day_approve,
        persist_timekeeping_day_reject,
        persist_timekeeping_day_submit,
        persist_timekeeping_reject,
        persist_timekeeping_submit,
        persist_timekeeping_week,
    )
    from pages._core._session import select_key  # type: ignore
    from styles import (  # type: ignore
        _inject_timekeeping_daily_hour_focus_script,
        inject_timekeeping_module_css,
    )
    from utils.dates import week_dates, week_end, week_start  # type: ignore
    from utils.field_context import get_field_job_id, is_field_context, is_field_mode, render_field_job_bar  # type: ignore
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
_EXPANDED_TIMECARD_KEY = "ips_timekeeping_expanded_id"
_TS_EXPAND = 32
_TS_EMPLOYEE = 180
_TS_DAY = 140
_TS_WEEK = 70
_TS_LIST_HANDLE = 24
_TS_LIST_EXPAND = 32
_TS_LIST_EMPLOYEE = 220
_TS_LIST_DAY = 106
_TS_LIST_SPACER = 24
_TS_LIST_TOTAL = 76
_TS_LIST_OVERTIME = 68
_TS_LIST_BILLED = 78
_TS_LIST_STATUS = 104
_HGRID_COLS = [_TS_EMPLOYEE] + [_TS_DAY] * 7 + [_TS_WEEK]
_WEEKLY_TS_LIST_ROW_COLS = [
    _TS_LIST_HANDLE,
    _TS_LIST_EXPAND,
    _TS_LIST_EMPLOYEE,
    *([_TS_LIST_DAY] * 7),
    _TS_LIST_SPACER,
    _TS_LIST_TOTAL,
    _TS_LIST_OVERTIME,
    _TS_LIST_BILLED,
    _TS_LIST_STATUS,
]


def _render_timekeeping_list_spacer_cell() -> None:
    st.markdown(
        '<span class="timekeeping-list-spacer-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )


_STATUS_FILTER_OPTS = ["Draft", "Pending", "Approved", "Rejected"]
_TK_COLUMN_FILTER_SPECS: list[tuple[str, Any]] = [
    ("employee_name", None),
    ("week_start", lambda r: fmt_date(r.get("week_start"))),
    ("status", lambda r: _normalize_timecard_status(r.get("status"))),
]
_DAY_GRID_COLS = [0.32, 0.5, 3.2, 0.58, 0.58, 0.52, 0.68, 0.82, 1.1]
_DAY_GRID_EDIT_COLS = [*_DAY_GRID_COLS, 0.28]
_DAY_GRID_LABELS = [
    "Day",
    "Date",
    "Assignment",
    "ST Hours",
    "OT Hours",
    "Total Hours",
    "Status",
    "Actions",
    "Notes",
]
_LIST_VIEW_HOUR_STEP = 0.5
_ALLOC_HOUR_TYPE_OPTS = ["S/T", "O/T"]
_ALLOC_LINE_COLS = [2.15, 0.52, 0.72, 0.58, 0.65, 1.0, 0.38]
_ALLOC_LINE_COLS_PRIMARY = [2.15, 0.52, 0.72, 0.58, 0.65, 1.0, 1.75]
_ALLOC_TOLERANCE = 0.01
_ASSIGNMENT_LEGACY_ALIASES = {
    "ips shop": "Shop",
    "administrator": "Administrative",
    "admin": "Administrative",
    "— no job —": "— No assignment —",
    "no job": "— No assignment —",
    "— select assignment —": "— No assignment —",
}


def _normalize_assignment_label(label: str) -> str:
    raw = str(label or "").strip()
    if not raw:
        return raw
    return _ASSIGNMENT_LEGACY_ALIASES.get(raw.casefold(), raw)


def _subjob_assignment_label(task: dict[str, Any], *, job_label: str) -> str:
    title = str(task.get("title") or task.get("issue") or "").strip() or "Subjob"
    task_no = str(task.get("task_number") or task.get("hazard_number") or "").strip()
    suffix = f"{task_no}: {title}" if task_no else title
    return f"{job_label} · {suffix}"


def _assignment_options_for_timekeeping() -> list[str]:
    """Jobs, linked subjobs, Shop, and Administrative choices for daily allocation."""
    try:
        from app.services.tasks_service import get_tasks_by_job
    except ImportError:
        from services.tasks_service import get_tasks_by_job  # type: ignore

    opts: list[str] = ["— No assignment —"]
    seen: set[str] = {opts[0].casefold()}

    def _add(label: str) -> None:
        clean = _normalize_assignment_label(label)
        if not clean:
            return
        key = clean.casefold()
        if key in seen:
            return
        opts.append(clean)
        seen.add(key)

    for job in load_jobs():
        num = str(job.get("job_number") or "").strip()
        name = str(job.get("job_name") or job.get("name") or "").strip()
        if not num and not name:
            continue
        job_label = f"{num} — {name}" if num else name
        _add(job_label)
        jid = str(job.get("id") or "").strip()
        if jid:
            for task in get_tasks_by_job(jid, include_closed=True):
                _add(_subjob_assignment_label(task, job_label=job_label))

    for special in ("Shop", "Administrative", "Vacation"):
        _add(special)

    if len(opts) == 1:
        _add("J26047 — Maintenance Shop Bathroom Remodel")
    return opts


def _assignment_option_index(options: list[str], saved: str) -> int:
    normalized = _normalize_assignment_label(saved)
    if normalized in options:
        return options.index(normalized)
    raw = str(saved or "").strip()
    if raw in options:
        return options.index(raw)
    if raw.casefold() in {o.casefold() for o in options}:
        for i, opt in enumerate(options):
            if opt.casefold() == raw.casefold():
                return i
    return 0


def _active_field_job_label() -> str | None:
    jid = get_field_job_id()
    if not jid:
        return None
    try:
        from app.services.jobs_service import get_job_options
    except ImportError:
        from services.jobs_service import get_job_options  # type: ignore
    for opt in get_job_options(include_all=True):
        if str(opt.get("id") or "").strip() == jid:
            label = str(opt.get("label") or "").strip()
            return label or None
    return None


def _apply_active_field_job_to_grid(grid: list[dict[str, Any]]) -> None:
    job_label = _active_field_job_label()
    if not job_label:
        return
    for row in grid:
        if _day_is_editable(_normalize_timecard_status(row.get("status"))):
            row["job"] = job_label


def _save_all_timekeeping_grids(rows: list[dict], week_start_d: date) -> None:
    saved = 0
    failed = 0
    for row in rows:
        emp = _emp_from_timecard_row(row)
        if _save_timekeeping_week(emp, week_start_d, show_message=False):
            saved += 1
        else:
            failed += 1
    if failed:
        st.warning(f"Saved {saved} employee(s); {failed} could not be saved.")
    elif saved:
        st.success(f"Saved hours for {saved} employee(s).")
    else:
        st.info("No employees to save.")
    st.rerun()


def _render_horizontal_week_grid(
    filtered: list[dict],
    *,
    week_start_d: date,
    key_prefix: str = "tk_hgrid",
) -> None:
    """All employees × 7 days — job picker and hours per day."""
    if not filtered:
        st.info("No timecards for this week.")
        return

    days = week_dates(week_start_d)
    job_opts = _assignment_options_for_timekeeping()
    field_job = _active_field_job_label()

    toolbar_left, toolbar_right = st.columns([2.2, 1], gap="small")
    with toolbar_left:
        if field_job:
            st.caption(
                f"Active job **{field_job}** pre-fills open days. Pick a job and enter **hours** for each day."
            )
        else:
            st.caption("Pick the **job** and enter **hours** for each day. Scroll sideways if needed.")
    with toolbar_right:
        if st.button(
            "Save all hours",
            type="primary",
            key=f"{key_prefix}_save_all_top",
            use_container_width=True,
        ):
            _save_all_timekeeping_grids(filtered, week_start_d)

    with st.container(key=f"{key_prefix}_wrap"):
        st.markdown('<div class="ips-time-hgrid-scroll"><div class="ips-time-hgrid-wrap">', unsafe_allow_html=True)

        header = st.columns(_HGRID_COLS, gap="xxsmall")
        header_labels = ["Employee", *[d.strftime("%a %m/%d").upper() for d in days], "Week"]
        for col, label in zip(header, header_labels):
            with col:
                sub = ""
                if label not in ("Employee", "Week"):
                    sub = '<div class="ips-time-hgrid-head-sub">Job + Hrs</div>'
                st.markdown(
                    f'<div class="ips-time-hgrid-head">{html.escape(label)}{sub}</div>',
                    unsafe_allow_html=True,
                )

        for row in filtered:
            emp = _emp_from_timecard_row(row)
            eid = str(emp.get("id") or emp.get("employee_id") or "").strip()
            if not eid:
                continue
            gk = _grid_key(eid)
            week_sig = week_start_d.isoformat()
            grid = _ensure_weekly_grid(emp, week_start_d)
            _apply_active_field_job_to_grid(grid)

            cols = st.columns(_HGRID_COLS, gap="xxsmall")
            with cols[0]:
                st.markdown(
                    '<span class="weekly-timesheet-row-marker" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                name = str(row.get("employee_name") or "—")
                st.markdown(
                    f'<div class="weekly-timesheet-employee">'
                    f'<span class="employee-label">Employee</span>'
                    f'<div class="weekly-timesheet-employee-name employee-name ips-time-hgrid-employee" '
                    f'title="{html.escape(name)}">{html.escape(name)}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

            row_total = 0.0
            for day_ix, (day_d, col) in enumerate(zip(days, cols[1:8])):
                day_status = _normalize_timecard_status(grid[day_ix].get("status"))
                editable = _day_is_editable(day_status)
                with col:
                    _render_hgrid_day_cell(
                        day_d=day_d,
                        emp_id=eid,
                        week_sig=week_sig,
                        day_ix=day_ix,
                        grid=grid,
                        job_opts=job_opts,
                        editable=editable,
                        day_status=day_status,
                    )
                row_total += _day_hours_total(grid[day_ix])

            with cols[8]:
                st.markdown(
                    f'<div class="week-total weekly-timesheet-week-total ips-time-hgrid-total">'
                    f'{html.escape(_fmt_table_hours(row_total))}</div>',
                    unsafe_allow_html=True,
                )

            st.session_state[gk] = grid

        st.markdown("</div></div>", unsafe_allow_html=True)

    st.caption("Use **List** view for ST/OT split, notes, and per-day submit.")


def _filter_summaries_for_field_user(summaries: list[dict]) -> list[dict]:
    if not is_field_context():
        return summaries
    try:
        from app.auth import current_profile, current_role
    except ImportError:
        from auth import current_profile, current_role  # type: ignore
    if str(current_role() or "").strip().lower() != "employee":
        return summaries

    prof = current_profile() or {}
    match_ids: set[str] = set()
    for key in ("employee_id", "id"):
        val = str(prof.get(key) or "").strip()
        if val:
            match_ids.add(val)
    emp = st.session_state.get("auth_employee") or {}
    if isinstance(emp, dict):
        eid = str(emp.get("id") or "").strip()
        if eid:
            match_ids.add(eid)

    if not match_ids:
        name = str(prof.get("full_name") or prof.get("name") or "").strip().lower()
        if not name:
            return summaries
        return [
            row
            for row in summaries
            if name in str(row.get("name") or row.get("employee_name") or "").strip().lower()
        ]

    filtered: list[dict] = []
    for row in summaries:
        rid = str(row.get("id") or row.get("employee_id") or "").strip()
        if rid in match_ids:
            filtered.append(row)
    return filtered or summaries


def _timecard_is_editable(status: str) -> bool:
    return status in ("Draft", "Pending", "Rejected")


def _day_is_editable(status: str) -> bool:
    return _normalize_timecard_status(status) in ("Draft", "Pending", "Rejected")


def _default_st_for_day_index(day_index: int) -> float:
    return 0.0


def _row_has_hours(row: dict[str, Any]) -> bool:
    return (
        float(row.get("st") or 0)
        + float(row.get("ot") or 0)
        + float(row.get("dt") or 0)
    ) > 0


def _ensure_day_id(emp: dict, week_start_d: date, row_index: int) -> str:
    day_id = str(_ensure_weekly_grid(emp, week_start_d)[row_index].get("day_id") or "").strip()
    if day_id:
        return day_id
    if _save_timekeeping_week(emp, week_start_d, show_message=False):
        return str(_ensure_weekly_grid(emp, week_start_d)[row_index].get("day_id") or "").strip()
    return ""


def _handle_day_submit(emp: dict, week_start_d: date, row_index: int) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    day_id = _ensure_day_id(emp, week_start_d, row_index)
    if not day_id:
        st.error("Save the day before submitting for approval.")
        return False
    ok, msg = persist_timekeeping_day_submit(day_id, eid, week_start_d)
    if ok:
        _invalidate_weekly_grid(emp, week_start_d)
        _patch_timecard_cache(emp, week_start_d, {"status": "Pending"})
        st.success(msg)
        return True
    st.error(msg)
    return False


def _handle_day_approve(emp: dict, week_start_d: date, row_index: int) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    approver = _current_user_id()
    if not approver:
        st.error("Your profile is missing an approver id.")
        return False
    day_id = _ensure_day_id(emp, week_start_d, row_index)
    if not day_id:
        st.error("Save the day before approving.")
        return False
    ok, msg = persist_timekeeping_day_approve(day_id, eid, week_start_d, approved_by=approver)
    if ok:
        _invalidate_weekly_grid(emp, week_start_d)
        st.success(msg)
        return True
    st.error(msg)
    return False


def _handle_day_reject(emp: dict, week_start_d: date, row_index: int) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    approver = _current_user_id()
    if not approver:
        st.error("Your profile is missing an approver id.")
        return False
    day_id = _ensure_day_id(emp, week_start_d, row_index)
    if not day_id:
        st.error("Save the day before rejecting.")
        return False
    ok, msg = persist_timekeeping_day_reject(day_id, eid, week_start_d, approved_by=approver)
    if ok:
        _invalidate_weekly_grid(emp, week_start_d)
        _patch_timecard_cache(emp, week_start_d, {"status": "Rejected"})
        st.success(msg)
        return True
    st.error(msg)
    return False


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
    ak = _alloc_state_key(eid)
    st.session_state.pop(ak, None)
    st.session_state.pop(f"{ak}_week", None)


def _alloc_state_key(emp_id: str) -> str:
    return f"ips_time_alloc_{emp_id}"


def _load_saved_allocations_by_date(employee_id: str, week_start_d: date) -> dict[str, list[dict[str, Any]]]:
    try:
        from app.services.timekeeping_service import list_timekeeping_days
    except ImportError:
        from services.timekeeping_service import list_timekeeping_days  # type: ignore

    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in list_timekeeping_days(employee_id, week_start_d):
        iso = str(row.get("work_date") or "")[:10]
        if not iso:
            continue
        line_id = str(row.get("id") or "")
        job = _normalize_assignment_label(str(row.get("job_label") or ""))
        notes = str(row.get("notes") or "")
        status = _normalize_timecard_status(row.get("status"))
        st_h = float(row.get("st_hours") or 0)
        ot_h = float(row.get("ot_hours") or 0) + float(row.get("dt_hours") or 0)
        if st_h > 0:
            by_date.setdefault(iso, []).append(
                {
                    "line_id": line_id,
                    "job": job,
                    "hour_type": "ST",
                    "hours": st_h,
                    "notes": notes,
                    "status": status,
                }
            )
        if ot_h > 0:
            by_date.setdefault(iso, []).append(
                {
                    "line_id": line_id,
                    "job": job,
                    "hour_type": "OT",
                    "hours": ot_h,
                    "notes": notes,
                    "status": status,
                }
            )
        if st_h <= 0 and ot_h <= 0:
            by_date.setdefault(iso, []).append(
                {
                    "line_id": line_id,
                    "job": job,
                    "hour_type": "ST",
                    "hours": 0.0,
                    "notes": notes,
                    "status": status,
                }
            )
    return by_date


def _ensure_allocation_state(emp: dict, week_start_d: date) -> dict[str, list[dict[str, Any]]]:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    ak = _alloc_state_key(eid)
    week_sig = week_start_d.isoformat()
    if st.session_state.get(f"{ak}_week") != week_sig:
        by_date = _load_saved_allocations_by_date(eid, week_start_d)
        for day_d in week_dates(week_start_d):
            by_date.setdefault(day_d.isoformat(), [])
        st.session_state[ak] = by_date
        st.session_state[f"{ak}_week"] = week_sig
    return st.session_state[ak]


def _daily_total_from_list_row(
    *,
    eid: str,
    week_sig: str,
    day_ix: int,
    grid_row: dict,
) -> float:
    hrs_key = f"tk_hrs_{eid}_{week_sig}_{day_ix}"
    if hrs_key in st.session_state:
        return max(0.0, float(st.session_state[hrs_key] or 0))
    return _day_hours_total(grid_row)


def _normalize_alloc_hour_type(raw: object) -> str:
    s = str(raw or "ST").strip().upper().replace(".", "").replace(" ", "")
    if s in {"OT", "OVERTIME"}:
        return "OT"
    return "ST"


def _alloc_hour_type_label(hour_type: str) -> str:
    return "O/T" if _normalize_alloc_hour_type(hour_type) == "OT" else "S/T"


def _line_allocated_hours(line: dict[str, Any]) -> float:
    return max(0.0, float(line.get("hours") or 0))


def _allocated_hours_sum(lines: list[dict[str, Any]]) -> float:
    return sum(_line_allocated_hours(line) for line in lines)


def _allocated_st_ot_sum(lines: list[dict[str, Any]]) -> tuple[float, float]:
    st_total = 0.0
    ot_total = 0.0
    for line in lines:
        hrs = _line_allocated_hours(line)
        if _normalize_alloc_hour_type(line.get("hour_type")) == "OT":
            ot_total += hrs
        else:
            st_total += hrs
    return st_total, ot_total


def _allocation_line_has_valid_assignment(line: dict[str, Any]) -> bool:
    """True when hours are tied to a job, subjob, Shop, or Administrative."""
    return _day_has_job({"job": line.get("job")})


def _allocation_line_hour_type_valid(line: dict[str, Any], hours: float) -> bool:
    if hours <= _ALLOC_TOLERANCE:
        return True
    raw = str(line.get("hour_type") or "").strip()
    if not raw:
        return False
    norm = _normalize_alloc_hour_type(raw)
    return norm in {"ST", "OT"}


def _live_allocation_lines_for_day(
    lines: list[dict[str, Any]],
    *,
    eid: str,
    week_sig: str,
    iso: str,
) -> list[dict[str, Any]]:
    """Merge allocation widget values for completion checks before rerun."""
    out: list[dict[str, Any]] = []
    for lix, line in enumerate(lines):
        live = dict(line)
        job_key = f"tk_alloc_job_{eid}_{week_sig}_{iso}_{lix}"
        type_key = f"tk_alloc_type_{eid}_{week_sig}_{iso}_{lix}"
        hrs_key = f"tk_alloc_hrs_{eid}_{week_sig}_{iso}_{lix}"
        if job_key in st.session_state:
            live["job"] = st.session_state[job_key]
        if type_key in st.session_state:
            live["hour_type"] = _normalize_alloc_hour_type(st.session_state[type_key])
        if hrs_key in st.session_state:
            live["hours"] = float(st.session_state[hrs_key] or 0)
        out.append(live)
    return out


def _get_day_allocation_state(day_total: float, allocations: list[dict[str, Any]]) -> dict[str, Any]:
    allocated_total = 0.0
    allocated_st = 0.0
    allocated_ot = 0.0
    has_invalid_assignment = False

    for row in allocations or []:
        hours = _line_allocated_hours(row)
        if hours <= _ALLOC_TOLERANCE:
            continue
        allocated_total += hours
        if not _allocation_line_hour_type_valid(row, hours):
            has_invalid_assignment = True
        elif _normalize_alloc_hour_type(row.get("hour_type")) == "OT":
            allocated_ot += hours
        else:
            allocated_st += hours
        if not _allocation_line_has_valid_assignment(row):
            has_invalid_assignment = True

    remaining = float(day_total or 0) - allocated_total
    if day_total <= _ALLOC_TOLERANCE:
        state = "no_hours"
    elif allocated_total - day_total > _ALLOC_TOLERANCE:
        state = "overallocated"
    elif abs(remaining) <= _ALLOC_TOLERANCE and not has_invalid_assignment:
        state = "complete"
    elif has_invalid_assignment and allocated_total > _ALLOC_TOLERANCE:
        state = "needs_assignment"
    else:
        state = "incomplete"

    return {
        "state": state,
        "allocated_total": allocated_total,
        "allocated_st": allocated_st,
        "allocated_ot": allocated_ot,
        "remaining": remaining,
        "has_invalid_assignment": has_invalid_assignment,
    }


def _allocation_day_block_class(state: str) -> str:
    if state == "complete":
        return " timekeeping-alloc-day-complete"
    if state == "overallocated":
        return " timekeeping-alloc-day-overallocated"
    if state == "needs_assignment":
        return " timekeeping-alloc-day-needs-assignment"
    if state == "incomplete":
        return " timekeeping-alloc-day-incomplete"
    return ""


def _list_day_allocation_state(
    *,
    eid: str,
    week_sig: str,
    day_ix: int,
    day_d: date,
    grid_row: dict,
    alloc_by_date: dict[str, list[dict[str, Any]]] | None,
) -> str:
    """Allocation completeness for a list-row day (same rules as expanded panel)."""
    daily_total = _daily_total_from_list_row(
        eid=eid,
        week_sig=week_sig,
        day_ix=day_ix,
        grid_row=grid_row,
    )
    if daily_total <= _ALLOC_TOLERANCE:
        return "no_hours"
    if not isinstance(alloc_by_date, dict):
        return ""
    iso = day_d.isoformat()
    lines = _live_allocation_lines_for_day(
        list(alloc_by_date.get(iso) or []),
        eid=eid,
        week_sig=week_sig,
        iso=iso,
    )
    return str(_get_day_allocation_state(daily_total, lines)["state"])


def _top_row_day_marker_classes(state: str) -> str:
    if state == "complete":
        return " ips-time-week-day-filled ips-time-week-day-alloc-complete"
    if state == "overallocated":
        return " ips-time-week-day-alloc-over"
    if state in {"incomplete", "needs_assignment"}:
        return " ips-time-week-day-alloc-warn"
    return ""


def _top_row_hour_spin_marker_class(state: str) -> str:
    if state == "complete":
        return " timekeeping-list-hour-spin-complete"
    if state == "overallocated":
        return " timekeeping-list-hour-spin-over"
    if state in {"incomplete", "needs_assignment"}:
        return " timekeeping-list-hour-spin-warn"
    return ""


def _list_day_allocation_marker_class(
    *,
    eid: str,
    week_sig: str,
    day_ix: int,
    day_d: date,
    grid_row: dict,
    alloc_by_date: dict[str, list[dict[str, Any]]] | None,
) -> str:
    return _top_row_day_marker_classes(
        _list_day_allocation_state(
            eid=eid,
            week_sig=week_sig,
            day_ix=day_ix,
            day_d=day_d,
            grid_row=grid_row,
            alloc_by_date=alloc_by_date,
        )
    )


def _default_allocation_job(grid_row: dict, job_opts: list[str]) -> str:
    saved = _normalize_assignment_label(str(grid_row.get("job") or ""))
    if saved and saved in job_opts:
        return saved
    return job_opts[0] if job_opts else "— No assignment —"


def _ensure_day_allocation_lines(
    by_date: dict[str, list[dict[str, Any]]],
    *,
    iso: str,
    daily_total: float,
    grid_row: dict,
    job_opts: list[str],
) -> list[dict[str, Any]]:
    lines = list(by_date.get(iso) or [])
    if daily_total > 0 and not lines:
        lines.append(
            {
                "line_id": "",
                "job": _default_allocation_job(grid_row, job_opts),
                "hour_type": "ST",
                "hours": daily_total,
                "notes": "",
                "status": _normalize_timecard_status(grid_row.get("status")),
            }
        )
    elif len(lines) == 1 and daily_total > 0 and not str(lines[0].get("line_id") or "").strip():
        only = dict(lines[0])
        if float(only.get("hours") or 0) <= 0:
            only["hours"] = daily_total
        lines = [only]
    by_date[iso] = lines
    return lines


def _sync_allocation_from_widgets(
    by_date: dict[str, list[dict[str, Any]]],
    *,
    eid: str,
    week_sig: str,
) -> None:
    for iso, lines in by_date.items():
        for lix, line in enumerate(lines):
            job_key = f"tk_alloc_job_{eid}_{week_sig}_{iso}_{lix}"
            type_key = f"tk_alloc_type_{eid}_{week_sig}_{iso}_{lix}"
            hrs_key = f"tk_alloc_hrs_{eid}_{week_sig}_{iso}_{lix}"
            notes_key = f"tk_alloc_notes_{eid}_{week_sig}_{iso}_{lix}"
            if job_key in st.session_state:
                line["job"] = st.session_state[job_key]
            if type_key in st.session_state:
                line["hour_type"] = _normalize_alloc_hour_type(st.session_state[type_key])
            if hrs_key in st.session_state:
                line["hours"] = float(st.session_state[hrs_key] or 0)
            if notes_key in st.session_state:
                line["notes"] = st.session_state[notes_key]


def _allocation_lines_to_persist_grid(
    by_date: dict[str, list[dict[str, Any]]],
    *,
    week_start_d: date,
    eid: str,
    week_sig: str,
    source_grid: list[dict],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Flatten allocation lines for persist_timekeeping_days; auto-fill unassigned remainder."""
    errors: list[str] = []
    persist_rows: list[dict[str, Any]] = []
    job_opts = _assignment_options_for_timekeeping()
    no_job = job_opts[0] if job_opts else "— No assignment —"

    for day_ix, day_d in enumerate(week_dates(week_start_d)):
        iso = day_d.isoformat()
        daily_total = _daily_total_from_list_row(
            eid=eid,
            week_sig=week_sig,
            day_ix=day_ix,
            grid_row=source_grid[day_ix] if day_ix < len(source_grid) else {},
        )
        lines = list(by_date.get(iso) or [])
        if daily_total <= 0:
            continue
        if not lines:
            errors.append(f"{day_d.strftime('%A')}: add at least one assignment row.")
            continue
        allocated = _allocated_hours_sum(lines)
        if allocated > daily_total + 0.01:
            errors.append(
                f"{day_d.strftime('%A')}: allocated {_fmt_day_hours(allocated)} exceeds "
                f"{_fmt_day_hours(daily_total)} entered in the row above."
            )
            continue
        out_lines = [dict(line) for line in lines]
        remainder = round(daily_total - allocated, 2)
        if remainder > 0.01:
            out_lines.append(
                {
                    "line_id": "",
                    "job": no_job,
                    "hour_type": "ST",
                    "hours": remainder,
                    "notes": "",
                    "status": str(out_lines[0].get("status") or "Draft"),
                }
            )
        merged: dict[tuple[str, str], dict[str, Any]] = {}
        for line in out_lines:
            hrs = _line_allocated_hours(line)
            if hrs <= 0:
                continue
            job_label = str(line.get("job") or no_job)
            merge_key = (iso, job_label)
            bucket = merged.get(merge_key)
            if not bucket:
                bucket = {
                    "day_id": str(line.get("line_id") or ""),
                    "day": day_d.strftime("%A"),
                    "date": iso,
                    "job": job_label,
                    "st": 0.0,
                    "ot": 0.0,
                    "dt": 0.0,
                    "notes": str(line.get("notes") or ""),
                    "status": str(line.get("status") or "Draft"),
                }
                merged[merge_key] = bucket
            elif not bucket["day_id"] and str(line.get("line_id") or "").strip():
                bucket["day_id"] = str(line.get("line_id") or "")
            if _normalize_alloc_hour_type(line.get("hour_type")) == "OT":
                bucket["ot"] = float(bucket["ot"]) + hrs
            else:
                bucket["st"] = float(bucket["st"]) + hrs
        persist_rows.extend(merged.values())
    return persist_rows, errors


def _save_allocation_week(emp: dict, week_start_d: date, *, show_message: bool = True) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    week_sig = week_start_d.isoformat()
    by_date = _ensure_allocation_state(emp, week_start_d)
    _sync_allocation_from_widgets(by_date, eid=eid, week_sig=week_sig)
    grid = _ensure_weekly_grid(emp, week_start_d)
    _apply_row_hrs_to_grid(grid, eid=eid, week_sig=week_sig)
    persist_rows, errors = _allocation_lines_to_persist_grid(
        by_date,
        week_start_d=week_start_d,
        eid=eid,
        week_sig=week_sig,
        source_grid=grid,
    )
    if errors:
        for err in errors[:3]:
            st.error(err)
        return False
    if not persist_rows:
        if show_message:
            st.info("Enter daily hours in the row above, then assign them here.")
        return False
    ok, msg = persist_timekeeping_days(eid, week_start_d, persist_rows)
    if ok:
        _invalidate_weekly_grid(emp, week_start_d)
        st.session_state[_grid_key(eid)] = load_timekeeping_grid(eid, week_start_d)
        st.session_state[f"{_grid_key(eid)}_week"] = week_sig
        if show_message:
            st.success(msg or "Allocations saved.")
        return True
    if show_message:
        st.warning(msg or "Could not save allocations.")
    return False


def _handle_alloc_line_submit(emp: dict, week_start_d: date, day_id: str) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    if not day_id:
        st.error("Save allocations before submitting this day.")
        return False
    if not _save_allocation_week(emp, week_start_d, show_message=False):
        return False
    ok, msg = persist_timekeeping_day_submit(day_id, eid, week_start_d)
    if ok:
        _invalidate_weekly_grid(emp, week_start_d)
        _patch_timecard_cache(emp, week_start_d, {"status": "Pending"})
        st.success(msg)
        return True
    st.error(msg)
    return False


def _handle_alloc_line_approve(emp: dict, week_start_d: date, day_id: str) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    approver = _current_user_id()
    if not approver:
        st.error("Your profile is missing an approver id.")
        return False
    if not day_id:
        st.error("Save allocations before approving this day.")
        return False
    ok, msg = persist_timekeeping_day_approve(day_id, eid, week_start_d, approved_by=approver)
    if ok:
        _invalidate_weekly_grid(emp, week_start_d)
        st.success(msg)
        return True
    st.error(msg)
    return False


def _handle_alloc_line_reject(emp: dict, week_start_d: date, day_id: str) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    approver = _current_user_id()
    if not approver:
        st.error("Your profile is missing an approver id.")
        return False
    if not day_id:
        st.error("Save allocations before rejecting this day.")
        return False
    ok, msg = persist_timekeeping_day_reject(day_id, eid, week_start_d, approved_by=approver)
    if ok:
        _invalidate_weekly_grid(emp, week_start_d)
        _patch_timecard_cache(emp, week_start_d, {"status": "Rejected"})
        st.success(msg)
        return True
    st.error(msg)
    return False


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


_DAY_ABBREV_TO_FULL: dict[str, str] = {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}


def _detail_day_label(row: dict) -> str:
    """Full weekday name for expanded list detail rows."""
    raw = str(row.get("day") or "").strip()
    if len(raw) > 3:
        return raw
    if raw:
        return _DAY_ABBREV_TO_FULL.get(raw.casefold()[:3], raw)
    raw_date = row.get("date")
    if raw_date:
        try:
            if isinstance(raw_date, date):
                return raw_date.strftime("%A")
            return date.fromisoformat(str(raw_date)[:10]).strftime("%A")
        except (TypeError, ValueError):
            pass
    return "—"


def _fmt_table_hours(val: object) -> str:
    try:
        return f"{float(val):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _fmt_day_hours(val: object) -> str:
    try:
        return f"{float(val):.1f}"
    except (TypeError, ValueError):
        return "0.0"


def _day_hours_total(day_row: dict) -> float:
    return (
        float(day_row.get("st") or 0)
        + float(day_row.get("ot") or 0)
        + float(day_row.get("dt") or 0)
    )


def _day_has_job(day_row: dict) -> bool:
    job = _normalize_assignment_label(str(day_row.get("job") or "")).strip().lower()
    if not job:
        return False
    if job in {
        "—",
        "-",
        "— no job —",
        "no job",
        "— no assignment —",
        "no assignment",
        "— select assignment —",
        "select assignment",
    }:
        return False
    return (
        "no job" not in job
        and "no assignment" not in job
        and "select assignment" not in job
    )


def _day_entry_complete(day_row: dict) -> bool:
    """Legacy single-row check (grid view / detail grid without allocation panel)."""
    return _day_has_job(day_row) and _day_hours_total(day_row) > 0


def _day_row_with_widget_values(
    row: dict,
    *,
    eid: str,
    week_sig: str,
    index: int,
) -> dict:
    """Merge in-flight job/ST/OT/hours widgets for live complete-state styling."""
    merged = dict(row)
    job_key = f"tk_job_{eid}_{week_sig}_{index}"
    if job_key in st.session_state:
        merged["job"] = st.session_state[job_key]
    for field, prefix in (("st", "tk_st"), ("ot", "tk_ot")):
        key = f"{prefix}_{eid}_{week_sig}_{index}"
        if key in st.session_state:
            merged[field] = float(st.session_state[key] or 0)
    hrs_key = f"tk_hrs_{eid}_{week_sig}_{index}"
    if hrs_key in st.session_state:
        merged = dict(merged)
        _set_day_job_hours(merged, float(st.session_state[hrs_key] or 0))
    return merged


def _sync_row_hrs_from_grid(grid: list[dict], *, eid: str, week_sig: str) -> None:
    """Keep inline row hour widgets aligned when ST/OT is edited in the expanded grid."""
    for i, row in enumerate(grid):
        st_key = f"tk_st_{eid}_{week_sig}_{i}"
        ot_key = f"tk_ot_{eid}_{week_sig}_{i}"
        hrs_key = f"tk_hrs_{eid}_{week_sig}_{i}"
        if st_key in st.session_state or ot_key in st.session_state:
            st.session_state[hrs_key] = _day_hours_total(row)


def _apply_row_hrs_to_grid(grid: list[dict], *, eid: str, week_sig: str) -> None:
    """Apply inline day-box hour inputs to the weekly grid."""
    for i, row in enumerate(grid):
        hrs_key = f"tk_hrs_{eid}_{week_sig}_{i}"
        if hrs_key in st.session_state:
            _set_day_job_hours(row, float(st.session_state[hrs_key] or 0))


def _render_daily_hrs_input(
    *,
    value: float,
    widget_key: str,
    day_label: str,
    editable: bool = True,
    box_style: bool = False,
) -> float:
    """Compact daily hours control: HRS label left, spinner number_input right."""
    if not editable:
        if box_style:
            st.markdown(
                f'<div class="timesheet-list-hour-box timesheet-list-hour-box-ro">'
                f"{html.escape(_fmt_day_hours(value))}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="hours-row ips-day-hrs-row ips-day-hrs-row-ro">'
                f'<span class="hrs-label ips-day-hrs-label">HRS</span>'
                f'<span class="ips-day-hrs-value">{html.escape(_fmt_day_hours(value))}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
        return float(value)

    if box_style:
        st.markdown(
            '<span class="timesheet-list-hour-box-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        with st.container(key=f"tk_list_hrs_{widget_key}"):
            return float(
                st.number_input(
                    f"{day_label} hours",
                    value=float(value),
                    key=widget_key,
                    label_visibility="collapsed",
                    step=0.5,
                    min_value=0.0,
                    max_value=24.0,
                    format="%.1f",
                )
            )

    st.markdown(
        '<span class="ips-compact-hours-input-marker ips-day-hrs-row-marker hours-row" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    lbl_col, inp_col = st.columns([0.38, 1], gap="xxsmall", vertical_alignment="center")
    with lbl_col:
        st.markdown('<span class="hrs-label ips-day-hrs-label">HRS</span>', unsafe_allow_html=True)
    with inp_col:
        hours = st.number_input(
            f"{day_label} hours",
            value=float(value),
            key=widget_key,
            label_visibility="collapsed",
            step=0.5,
            min_value=0.0,
            max_value=24.0,
            format="%.1f",
        )
    return float(hours)


def _render_list_day_hour_stepper(
    *,
    value: float,
    widget_key: str,
    day_label: str,
    alloc_state: str = "",
) -> float:
    """List view: centered hour input with a compact ▲/▼ button strip."""
    step = _LIST_VIEW_HOUR_STEP
    down_key = f"{widget_key}_dn"
    up_key = f"{widget_key}_up"
    spin_key = f"tk_list_hour_spin_{widget_key}"
    spin_marker_cls = _top_row_hour_spin_marker_class(alloc_state)

    with st.container(key=spin_key):
        st.markdown(
            f'<span class="timekeeping-list-hour-spinner-marker{spin_marker_cls}" '
            f'aria-hidden="true"></span>'
            '<div class="timekeeping-hour-spinner">',
            unsafe_allow_html=True,
        )
        inp_col, btns_col = st.columns([1, 1], gap="xxsmall", vertical_alignment="center")
        with inp_col:
            st.markdown(
                '<span class="timekeeping-hour-input-marker timekeeping-list-daily-hour-marker" '
                'aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            hours = st.number_input(
                f"{day_label} hours",
                value=float(value),
                key=widget_key,
                label_visibility="collapsed",
                step=step,
                min_value=0.0,
                max_value=24.0,
                format="%.1f",
            )
        with btns_col:
            st.markdown(
                '<span class="timekeeping-spinner-buttons-marker" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            if st.button(
                "▲",
                key=up_key,
                use_container_width=True,
                help=f"Increase {day_label} hours",
            ):
                cur = float(st.session_state.get(widget_key, value))
                st.session_state[widget_key] = min(24.0, round(cur + step, 1))
                st.rerun()
            if st.button(
                "▼",
                key=down_key,
                use_container_width=True,
                help=f"Decrease {day_label} hours",
            ):
                cur = float(st.session_state.get(widget_key, value))
                st.session_state[widget_key] = max(0.0, round(cur - step, 1))
                st.rerun()
    return max(0.0, float(hours))


def _render_list_row_day_cell(
    *,
    day_d: date,
    day_ix: int,
    day_row: dict,
    emp_id: str,
    week_sig: str,
    editable: bool,
    alloc_by_date: dict[str, list[dict[str, Any]]] | None = None,
) -> float:
    """List row: centered day label stacked above hour stepper."""
    day_label = day_d.strftime("%a %m/%d").upper()
    widget_key = f"tk_hrs_{emp_id}_{week_sig}_{day_ix}"
    alloc_state = _list_day_allocation_state(
        eid=emp_id,
        week_sig=week_sig,
        day_ix=day_ix,
        day_d=day_d,
        grid_row=day_row,
        alloc_by_date=alloc_by_date,
    )
    filled_marker = _top_row_day_marker_classes(alloc_state)
    grid_marker = " timesheet-list-days-marker" if day_ix == 0 else ""
    total = _day_hours_total(day_row)

    with st.container(key=f"tk_list_day_{emp_id}_{week_sig}_{day_ix}"):
        st.markdown(
            f'<span class="timesheet-list-day-marker day-block-marker timekeeping-day-cell-marker{grid_marker}{filled_marker}" '
            f'aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="timekeeping-day-cell">'
            f'<div class="timekeeping-day-label">{html.escape(day_label)}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        if editable:
            hrs = _render_list_day_hour_stepper(
                value=total,
                widget_key=widget_key,
                day_label=day_d.strftime("%a"),
                alloc_state=alloc_state,
            )
            _set_day_job_hours(day_row, hrs)
            return hrs
        ro_cls = "timekeeping-hour-input timekeeping-hour-input-ro"
        if alloc_state == "complete":
            ro_cls += " timekeeping-list-hour-ro-complete"
        elif alloc_state == "overallocated":
            ro_cls += " timekeeping-list-hour-ro-over"
        elif alloc_state in {"incomplete", "needs_assignment"}:
            ro_cls += " timekeeping-list-hour-ro-warn"
        st.markdown(
            f'<div class="{ro_cls}">'
            f"{html.escape(_fmt_day_hours(total))}</div>",
            unsafe_allow_html=True,
        )
        return total


def _render_list_row_week_boxes(emp: dict, week_start_d: date) -> None:
    """Compact 7-day hour boxes — always visible on each list row."""
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    if not eid:
        return
    week_sig = week_start_d.isoformat()
    gk = _grid_key(eid)
    grid = _ensure_weekly_grid(emp, week_start_d)
    grid = _sync_grid_from_widget_keys(grid, eid=eid, week_sig=week_sig)
    _sync_row_hrs_from_grid(grid, eid=eid, week_sig=week_sig)
    week_status = _normalize_timecard_status(emp.get("status"))
    days = week_dates(week_start_d)

    st.markdown(
        '<span class="timesheet-days-inline-grid timesheet-days-grid-wrap timesheet-days-grid-marker-wrap" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    day_cols = st.columns(7, gap="xxsmall")

    for i, (col, day_d) in enumerate(zip(day_cols, days)):
        day_row = grid[i] if i < len(grid) else {}
        day_row = _day_row_with_widget_values(day_row, eid=eid, week_sig=week_sig, index=i)
        day_status = _normalize_timecard_status(day_row.get("status"))
        editable = week_status != "Approved" and _day_is_editable(day_status)
        total = _day_hours_total(day_row)
        filled_marker = "ips-time-week-day-filled" if _day_entry_complete(day_row) else ""
        grid_marker = " timesheet-days-grid-marker" if i == 0 else ""

        with col:
            st.markdown(
                f'<span class="day-block-marker day-card-marker ips-time-week-day-marker{grid_marker} {filled_marker}" aria-hidden="true"></span>'
                f'<div class="day-card">'
                f'<div class="day-date-line">'
                f'<span class="day-label ips-time-week-day-label">{html.escape(day_d.strftime("%a").upper())}</span>'
                f'<span class="day-date ips-time-week-day-date">{html.escape(day_d.strftime("%m/%d"))}</span>'
                f"</div></div>",
                unsafe_allow_html=True,
            )
            if editable:
                hrs = _render_daily_hrs_input(
                    value=total,
                    widget_key=f"tk_hrs_{eid}_{week_sig}_{i}",
                    day_label=day_d.strftime("%a"),
                )
                _set_day_job_hours(day_row, hrs)
            else:
                _render_daily_hrs_input(
                    value=total,
                    widget_key=f"tk_hrs_{eid}_{week_sig}_{i}",
                    day_label=day_d.strftime("%a"),
                    editable=False,
                )

    st.session_state[gk] = grid


def _row_totals_from_grid(grid: list[dict]) -> tuple[float, float, float]:
    st_total = sum(float(r.get("st") or 0) for r in grid)
    ot_total = sum(float(r.get("ot") or 0) for r in grid)
    dt_total = sum(float(r.get("dt") or 0) for r in grid)
    return st_total, ot_total, st_total + ot_total + dt_total


def _sync_grid_from_widget_keys(grid: list[dict], *, eid: str, week_sig: str) -> list[dict]:
    """Apply in-flight ST/OT widget values so the day summary bar updates immediately."""
    for i, row in enumerate(grid):
        for field, prefix in (("st", "tk_st"), ("ot", "tk_ot")):
            key = f"{prefix}_{eid}_{week_sig}_{i}"
            if key in st.session_state:
                row[field] = float(st.session_state[key] or 0)
    return grid


def _hour_stepper_input(
    *,
    label: str,
    value: float,
    widget_key: str,
    step: float = 0.5,
    max_value: float = 24.0,
    disabled: bool = False,
    fmt: str = "%.1f",
    down_label: str = "▼",
    up_label: str = "▲",
    compact: bool = False,
    detail_grid: bool = False,
) -> float:
    if disabled:
        st.markdown(
            f'<div class="ips-time-hour-readonly">{html.escape(_fmt_table_hours(value))}</div>',
            unsafe_allow_html=True,
        )
        return float(value)

    down_key = f"{widget_key}_dn"
    up_key = f"{widget_key}_up"
    if compact:
        detail_cls = " timekeeping-detail-hour-stepper" if detail_grid else ""
        st.markdown(
            f'<span class="weekly-timesheet-stepper-marker hours-control timekeeping-hours-control{detail_cls}" '
            f'aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
    dn_col, val_col, up_col = st.columns([0.24, 0.52, 0.24] if compact else [0.26, 0.48, 0.26], gap="small")
    with dn_col:
        if st.button(
            down_label,
            key=down_key,
            use_container_width=True,
            help=f"Decrease {label}",
        ):
            cur = float(st.session_state.get(widget_key, value))
            st.session_state[widget_key] = max(0.0, round(cur - step, 2))
            st.rerun()
    with val_col:
        hours = st.number_input(
            label,
            value=float(value),
            key=widget_key,
            label_visibility="collapsed",
            step=step,
            min_value=0.0,
            max_value=max_value,
            format=fmt,
        )
    with up_col:
        if st.button(
            up_label,
            key=up_key,
            use_container_width=True,
            help=f"Increase {label}",
        ):
            cur = float(st.session_state.get(widget_key, value))
            st.session_state[widget_key] = min(max_value, round(cur + step, 2))
            st.rerun()
    return float(hours)


def _render_weekly_compact_hrs_control(
    *,
    value: float,
    widget_key: str,
    editable: bool = True,
) -> float:
    """Compact HRS label + minus/value/plus control for weekly timesheet rows."""
    if not editable:
        st.markdown(
            f'<div class="hours-row">'
            f'<span class="hrs-label">HRS</span>'
            f'<span class="hours-value">{html.escape(_fmt_day_hours(value))}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
        return float(value)

    st.markdown(
        '<span class="weekly-timesheet-hrs-marker hours-row" aria-hidden="true"></span>'
        '<div class="timekeeping-hours-control-label"><span class="hrs-label">HRS</span></div>',
        unsafe_allow_html=True,
    )
    return _hour_stepper_input(
        label="Hours",
        value=float(value),
        widget_key=widget_key,
        down_label="−",
        up_label="+",
        compact=True,
    )


def _render_weekly_timesheet_day_cell(
    *,
    day_d: date,
    day_ix: int,
    day_row: dict,
    emp_id: str,
    week_sig: str,
    job_opts: list[str],
    editable: bool,
    day_status: str,
    show_day_header: bool = True,
) -> None:
    filled_marker = " ips-time-week-day-filled" if _day_entry_complete(day_row) else ""
    header_html = ""
    if show_day_header:
        header_html = (
            f'<div class="weekly-timesheet-day day-header">'
            f'<span class="weekly-timesheet-day-label day-label">'
            f'{html.escape(day_d.strftime("%a").upper())}</span>'
            f'<span class="weekly-timesheet-day-date day-date">'
            f'{html.escape(day_d.strftime("%m/%d"))}</span>'
            f"</div>"
        )
    st.markdown(
        f'<span class="weekly-timesheet-day-marker day-cell{filled_marker}" aria-hidden="true"></span>'
        f"{header_html}",
        unsafe_allow_html=True,
    )
    if editable:
        cur_job = str(day_row.get("job") or (job_opts[0] if job_opts else "— No assignment —"))
        job_ix = _assignment_option_index(job_opts, cur_job)
        st.markdown(
            '<span class="weekly-timesheet-job-marker weekly-timesheet-job-select job-select" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        day_row["job"] = st.selectbox(
            "Assignment",
            job_opts,
            index=job_ix,
            key=f"tk_job_{emp_id}_{week_sig}_{day_ix}",
            label_visibility="collapsed",
        )
        hrs = _render_weekly_compact_hrs_control(
            value=_day_hours_total(day_row),
            widget_key=f"tk_hrs_{emp_id}_{week_sig}_{day_ix}",
            editable=True,
        )
        _set_day_job_hours(day_row, hrs)
        return

    st.markdown(_hgrid_locked_day_html(day_row, status=day_status), unsafe_allow_html=True)


def _set_day_job_hours(day_row: dict, hours: float) -> None:
    """Grid entry: hours apply to the selected job (stored as ST)."""
    day_row["st"] = float(hours)
    day_row["ot"] = 0.0
    day_row["dt"] = 0.0


def _hgrid_day_total_html(total: float) -> str:
    cls = "ips-time-hgrid-day-total"
    if total > 0:
        cls += " ips-time-hgrid-day-total-active"
    return f'<div class="{cls}">{html.escape(_fmt_day_hours(total))}</div>'


def _hgrid_locked_day_html(day_row: dict, *, status: str) -> str:
    job = _normalize_assignment_label(str(day_row.get("job") or "— No assignment —")).strip()
    if len(job) > 28:
        job = job[:25] + "…"
    total = _day_hours_total(day_row)
    pill = _timecard_status_pill_html(status, compact=True)
    return (
        f'<div class="ips-time-hgrid-locked">'
        f'<div class="ips-time-hgrid-locked-job" title="{html.escape(str(day_row.get("job") or ""))}">'
        f"{html.escape(job)}</div>"
        f'<div class="ips-time-hgrid-locked-row">'
        f"{_hgrid_day_total_html(total)}"
        f"{pill}"
        f"</div></div>"
    )


def _render_hgrid_day_cell(
    *,
    day_d: date,
    emp_id: str,
    week_sig: str,
    day_ix: int,
    grid: list[dict],
    job_opts: list[str],
    editable: bool,
    day_status: str,
) -> None:
    day_row = grid[day_ix]
    _render_weekly_timesheet_day_cell(
        day_d=day_d,
        day_ix=day_ix,
        day_row=day_row,
        emp_id=emp_id,
        week_sig=week_sig,
        job_opts=job_opts,
        editable=editable,
        day_status=day_status,
    )


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


def _timecard_status_pill_html(status: str, *, compact: bool = False) -> str:
    cls_map = {
        "Draft": "ips-timekeeping-status-draft",
        "Pending": "ips-timekeeping-status-pending",
        "Approved": "ips-timekeeping-status-approved",
        "Rejected": "ips-timekeeping-status-rejected",
    }
    cls = cls_map.get(status, "ips-timekeeping-status-draft")
    compact_cls = " ips-timekeeping-status-pill-compact" if compact else ""
    return (
        f'<span class="ips-timekeeping-status-pill {cls}{compact_cls}">'
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


def _expanded_timecard_id() -> str | None:
    tid = str(st.session_state.get(_EXPANDED_TIMECARD_KEY) or "").strip()
    return tid or None


def _clear_expanded_timecard() -> None:
    st.session_state.pop(_EXPANDED_TIMECARD_KEY, None)


def _toggle_expanded_timecard(timecard_id: str) -> None:
    tid = str(timecard_id or "").strip()
    if not tid:
        return
    if _expanded_timecard_id() == tid:
        _clear_expanded_timecard()
    else:
        st.session_state[_EXPANDED_TIMECARD_KEY] = tid
        st.session_state[SELECTED_TIMECARD_KEY] = None
        st.session_state[SHOW_TIMECARD_MODAL_KEY] = False


def _emp_from_timecard_row(row: dict) -> dict:
    return {
        **row,
        "id": str(row.get("employee_id") or row.get("id") or "").strip(),
        "name": str(row.get("employee_name") or row.get("name") or "—"),
    }


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


def _render_day_grid_header(*, edit_mode: bool = False) -> None:
    header = st.columns(_DAY_GRID_EDIT_COLS if edit_mode else _DAY_GRID_COLS)
    labels = ([*_DAY_GRID_LABELS, ""] if edit_mode else _DAY_GRID_LABELS)
    for col_ix, (col, lbl) in enumerate(zip(header, labels)):
        with col:
            marker = (
                '<span class="timekeeping-detail-header-marker" aria-hidden="true"></span>'
                if col_ix == 0
                else ""
            )
            st.markdown(
                f"{marker}<div class=\"ips-time-day-head timekeeping-detail-head\">{html.escape(lbl)}</div>",
                unsafe_allow_html=True,
            )


def _render_weekly_grid_readonly(emp: dict, week_start_d: date) -> None:
    grid = _ensure_weekly_grid(emp, week_start_d)
    st.markdown(
        '<span class="timekeeping-detail-grid-marker timekeeping-detail-grid-readonly" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    _render_day_grid_header(edit_mode=False)
    for row in grid:
        c = st.columns(_DAY_GRID_COLS)
        row_total = (
            float(row.get("st") or 0)
            + float(row.get("ot") or 0)
            + float(row.get("dt") or 0)
        )
        with c[0]:
            st.markdown(
                f'<span class="timekeeping-detail-row-marker" aria-hidden="true"></span>'
                f'<div class="ips-time-day-row timekeeping-detail-cell timekeeping-detail-day-cell">'
                f"{html.escape(_detail_day_label(row))}</div>",
                unsafe_allow_html=True,
            )
        with c[1]:
            st.markdown(
                f'<div class="ips-time-day-row timekeeping-detail-cell timekeeping-detail-date-cell">'
                f"{html.escape(fmt_date(row.get('date')))}</div>",
                unsafe_allow_html=True,
            )
        with c[2]:
            st.markdown(
                f'<div class="ips-time-day-row timekeeping-detail-cell">{html.escape(str(row.get("job") or "—"))}</div>',
                unsafe_allow_html=True,
            )
        with c[3]:
            st.markdown(
                f'<div class="ips-time-day-row timekeeping-detail-cell">{html.escape(_fmt_table_hours(row.get("st")))}</div>',
                unsafe_allow_html=True,
            )
        with c[4]:
            st.markdown(
                f'<div class="ips-time-day-row timekeeping-detail-cell">{html.escape(_fmt_table_hours(row.get("ot")))}</div>',
                unsafe_allow_html=True,
            )
        with c[5]:
            st.markdown(
                f'<div class="ips-time-day-row timekeeping-detail-cell">{html.escape(_fmt_table_hours(row_total))}</div>',
                unsafe_allow_html=True,
            )
        with c[6]:
            day_status = _normalize_timecard_status(row.get("status"))
            st.markdown(_timecard_status_pill_html(day_status), unsafe_allow_html=True)
        with c[7]:
            st.markdown('<div class="ips-time-day-row timekeeping-detail-cell">—</div>', unsafe_allow_html=True)
        with c[8]:
            st.markdown(
                f'<div class="ips-time-day-row timekeeping-detail-cell">'
                f"{html.escape(str(row.get('notes') or '—'))}</div>",
                unsafe_allow_html=True,
            )


def _week_status_from_grid(grid: list[dict[str, Any]]) -> str:
    active = [_normalize_timecard_status(row.get("status")) for row in grid if _row_has_hours(row)]
    if not active:
        return "Draft"
    if all(status == "Approved" for status in active):
        return "Approved"
    if any(status == "Rejected" for status in active):
        return "Rejected"
    if any(status == "Pending" for status in active):
        return "Pending"
    return "Draft"


def _render_weekly_grid_edit(emp: dict, week_start_d: date) -> None:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    gk = _grid_key(eid)
    week_sig = week_start_d.isoformat()
    grid = _ensure_weekly_grid(emp, week_start_d)
    job_opts = _assignment_options_for_timekeeping()
    can_approve = _can_approve_timekeeping()

    st.markdown(
        '<span class="ips-time-day-edit-marker timekeeping-detail-grid-marker timekeeping-detail-grid-edit" '
        'aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    grid = _sync_grid_from_widget_keys(grid, eid=eid, week_sig=week_sig)

    edit_cols = _DAY_GRID_EDIT_COLS
    _render_day_grid_header(edit_mode=True)

    for i, row in enumerate(grid):
        day_status = _normalize_timecard_status(row.get("status"))
        row_editable = _day_is_editable(day_status)
        live_row = _day_row_with_widget_values(row, eid=eid, week_sig=week_sig, index=i)
        row_complete = _day_entry_complete(live_row)
        c = st.columns(edit_cols, gap="small")
        with c[0]:
            row_marker = "ips-time-day-row-filled" if row_complete else ""
            st.markdown(
                f'<span class="timekeeping-detail-row-marker" aria-hidden="true"></span>'
                f'<span class="ips-time-day-row-marker {row_marker}" aria-hidden="true"></span>'
                f'<div class="ips-time-day-row timekeeping-detail-cell timekeeping-detail-day-cell">'
                f"{html.escape(_detail_day_label(row))}</div>",
                unsafe_allow_html=True,
            )
        with c[1]:
            st.markdown(
                f'<div class="ips-time-day-row timekeeping-detail-cell timekeeping-detail-date-cell">'
                f"{html.escape(fmt_date(row.get('date')))}</div>",
                unsafe_allow_html=True,
            )
        with c[2]:
            marker_cls = "ips-time-day-job-filled" if row_complete else ""
            st.markdown(
                f'<span class="ips-time-day-job-marker timekeeping-detail-assignment-marker '
                f'{marker_cls}" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            cur_job = str(live_row.get("job") or row.get("job") or job_opts[0])
            idx = _assignment_option_index(job_opts, cur_job)
            grid[i]["job"] = st.selectbox(
                "Assignment",
                job_opts,
                index=idx,
                key=f"tk_job_{eid}_{week_sig}_{i}",
                label_visibility="collapsed",
                disabled=not row_editable,
            )
        with c[3]:
            grid[i]["st"] = _hour_stepper_input(
                label="ST",
                value=float(row.get("st") or 0),
                widget_key=f"tk_st_{eid}_{week_sig}_{i}",
                step=0.5,
                disabled=not row_editable,
                down_label="−",
                up_label="+",
                compact=True,
                detail_grid=True,
            )
        with c[4]:
            grid[i]["ot"] = _hour_stepper_input(
                label="OT",
                value=float(row.get("ot") or 0),
                widget_key=f"tk_ot_{eid}_{week_sig}_{i}",
                step=0.5,
                disabled=not row_editable,
                down_label="−",
                up_label="+",
                compact=True,
                detail_grid=True,
            )
        with c[5]:
            row_total = (
                float(grid[i].get("st") or 0)
                + float(grid[i].get("ot") or 0)
                + float(grid[i].get("dt") or 0)
            )
            st.markdown(
                f'<div class="ips-time-day-row timekeeping-detail-cell">{html.escape(_fmt_table_hours(row_total))}</div>',
                unsafe_allow_html=True,
            )
        with c[6]:
            st.markdown(_timecard_status_pill_html(day_status), unsafe_allow_html=True)
            grid[i]["status"] = day_status
        with c[7]:
            action_taken = False
            if row_editable and _row_has_hours(row):
                if day_status in ("Draft", "Rejected") and st.button(
                    "Submit",
                    key=f"tk_day_submit_{eid}_{week_sig}_{i}",
                    use_container_width=True,
                ):
                    action_taken = _handle_day_submit(emp, week_start_d, i)
                elif day_status == "Pending" and can_approve:
                    approve_col, reject_col = st.columns(2)
                    with approve_col:
                        if st.button("OK", key=f"tk_day_ok_{eid}_{week_sig}_{i}", use_container_width=True):
                            action_taken = _handle_day_approve(emp, week_start_d, i)
                    with reject_col:
                        if st.button("No", key=f"tk_day_no_{eid}_{week_sig}_{i}", use_container_width=True):
                            action_taken = _handle_day_reject(emp, week_start_d, i)
            if action_taken:
                st.rerun()
        with c[8]:
            grid[i]["notes"] = st.text_input(
                "Notes",
                value=str(row.get("notes") or ""),
                key=f"tk_notes_{eid}_{week_sig}_{i}",
                label_visibility="collapsed",
                placeholder="Add notes...",
                disabled=not row_editable,
            )
        with c[9]:
            if row_editable and st.button("🗑", key=f"tk_del_{eid}_{week_sig}_{i}", help="Clear row"):
                grid[i]["job"] = job_opts[0] if job_opts else "— No assignment —"
                grid[i]["st"] = _default_st_for_day_index(i)
                grid[i]["ot"] = 0.0
                grid[i]["dt"] = 0.0
                grid[i]["notes"] = ""
                grid[i]["status"] = "Draft"
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
    for row in grid:
        if not str(row.get("status") or "").strip():
            row["status"] = "Draft"
    ok2, msg2 = persist_timekeeping_days(eid, week_start_d, grid)
    if ok2:
        summary = {
            "st_total": sum(float(r.get("st") or 0) for r in grid),
            "ot_total": sum(float(r.get("ot") or 0) for r in grid),
            "dt_total": sum(float(r.get("dt") or 0) for r in grid),
            "status": _week_status_from_grid(grid),
            "notes": str(emp.get("notes") or ""),
        }
        _patch_timecard_cache(
            emp,
            week_start_d,
            {
                **summary,
                "total_hours": summary["st_total"] + summary["ot_total"] + summary["dt_total"],
            },
        )
        _invalidate_weekly_grid(emp, week_start_d)
        if show_message:
            st.success(msg2 or "Timekeeping saved.")
        return True
    st.warning(msg2 or "Could not save daily entry details.")
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


def _render_allocation_hours_input(
    *,
    value: float,
    widget_key: str,
    disabled: bool = False,
) -> float:
    """Single compact hours field for allocation rows (no nested stepper columns)."""
    st.markdown(
        '<span class="timekeeping-allocation-hours-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    if disabled:
        st.markdown(
            f'<div class="timekeeping-alloc-hours-readonly">{html.escape(_fmt_day_hours(value))}</div>',
            unsafe_allow_html=True,
        )
        return float(value)
    return float(
        st.number_input(
            "Allocated hrs",
            value=float(value),
            key=widget_key,
            label_visibility="collapsed",
            min_value=0.0,
            max_value=24.0,
            step=0.5,
            format="%.1f",
        )
    )


def _render_allocation_primary_row_actions(
    *,
    emp: dict,
    week_start_d: date,
    eid: str,
    week_sig: str,
    iso: str,
    lines: list[dict[str, Any]],
    line: dict[str, Any],
    lix: int,
    day_status: str,
    row_editable: bool,
    can_approve: bool,
    by_date: dict[str, list[dict[str, Any]]],
    daily_total: float,
    job_opts: list[str],
) -> None:
    """Submit / add-assignment controls on the right of the first allocation row."""
    st.markdown(
        '<span class="timekeeping-allocation-actions-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    line_id = str(line.get("line_id") or "").strip()
    line_hours = float(line.get("hours") or 0)
    action_taken = False

    if row_editable and day_status == "Pending" and can_approve and line_id and line_hours > 0:
        btn_cols = st.columns(2, gap="small")
        with btn_cols[0]:
            if st.button(
                "Approve",
                key=f"tk_alloc_ok_{eid}_{week_sig}_{iso}_{lix}",
                use_container_width=True,
            ):
                action_taken = _handle_alloc_line_approve(emp, week_start_d, line_id)
        with btn_cols[1]:
            if st.button(
                "Reject",
                key=f"tk_alloc_no_{eid}_{week_sig}_{iso}_{lix}",
                use_container_width=True,
            ):
                action_taken = _handle_alloc_line_reject(emp, week_start_d, line_id)
    else:
        show_remove = row_editable and len(lines) > 1
        btn_cols = (
            st.columns([1.35, 1.15, 0.75], gap="small")
            if show_remove
            else st.columns([1.45, 1.25], gap="small")
        )
        with btn_cols[0]:
            if (
                row_editable
                and line_id
                and line_hours > 0
                and day_status in ("Draft", "Rejected")
                and st.button(
                    "Submit day line",
                    key=f"tk_alloc_submit_{eid}_{week_sig}_{iso}_{lix}",
                    use_container_width=True,
                )
            ):
                action_taken = _handle_alloc_line_submit(emp, week_start_d, line_id)
        with btn_cols[1]:
            if row_editable and st.button(
                "+ Add assignment",
                key=f"tk_alloc_add_{eid}_{week_sig}_{iso}",
                use_container_width=True,
                help="Add another assignment row for this day",
            ):
                day_lines = list(by_date.get(iso) or [])
                remaining = max(0.0, round(daily_total - _allocated_hours_sum(day_lines), 2))
                day_lines.append(
                    {
                        "line_id": "",
                        "job": job_opts[0] if job_opts else "— No assignment —",
                        "hour_type": "ST",
                        "hours": remaining,
                        "notes": "",
                        "status": "Draft",
                    }
                )
                by_date[iso] = day_lines
                st.session_state[_alloc_state_key(eid)] = by_date
                st.rerun()
        if show_remove:
            with btn_cols[2]:
                if st.button(
                    "Remove",
                    key=f"tk_alloc_del_{eid}_{week_sig}_{iso}_{lix}",
                    use_container_width=True,
                    help="Remove this assignment row",
                ):
                    by_date[iso] = [ln for j, ln in enumerate(lines) if j != lix]
                    st.session_state[_alloc_state_key(eid)] = by_date
                    st.rerun()

    if action_taken:
        st.rerun()


def _render_allocation_line_header() -> None:
    cols = st.columns(_ALLOC_LINE_COLS_PRIMARY)
    labels = ["Assignment", "Type", "Hours", "Remaining", "Status", "Notes", "Actions"]
    for col, lbl in zip(cols, labels):
        with col:
            marker = (
                '<span class="timekeeping-allocation-header-marker" aria-hidden="true"></span>'
                if lbl == "Assignment"
                else ""
            )
            st.markdown(
                f"{marker}<div class=\"ips-time-day-head timekeeping-detail-head\">{html.escape(lbl)}</div>",
                unsafe_allow_html=True,
            )


def _render_list_allocation_detail(emp: dict, week_start_d: date) -> None:
    """List expand: assign hours entered in the top row to jobs/tasks/shop/admin."""
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    week_sig = week_start_d.isoformat()
    week_status = _normalize_timecard_status(emp.get("status"))
    week_locked = week_status == "Approved"
    job_opts = _assignment_options_for_timekeeping()
    can_approve = _can_approve_timekeeping()
    grid = _ensure_weekly_grid(emp, week_start_d)
    _apply_row_hrs_to_grid(grid, eid=eid, week_sig=week_sig)
    by_date = _ensure_allocation_state(emp, week_start_d)

    st.markdown(
        '<span class="timekeeping-allocation-panel-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="timekeeping-alloc-intro">'
        "<strong>Daily hours are entered in the employee row above.</strong> "
        "Split each day&rsquo;s total across jobs, subjobs, Shop, or Administrative, "
        "and mark each row as <strong>S/T</strong> (straight time) or <strong>O/T</strong> (overtime)."
        "</div>",
        unsafe_allow_html=True,
    )

    if week_locked:
        st.info("This week is approved and locked.")
    _render_allocation_line_header()

    for day_ix, day_d in enumerate(week_dates(week_start_d)):
        iso = day_d.isoformat()
        grid_row = grid[day_ix] if day_ix < len(grid) else {}
        daily_total = _daily_total_from_list_row(
            eid=eid,
            week_sig=week_sig,
            day_ix=day_ix,
            grid_row=grid_row,
        )
        lines = _ensure_day_allocation_lines(
            by_date,
            iso=iso,
            daily_total=daily_total,
            grid_row=grid_row,
            job_opts=job_opts,
        )
        live_lines = _live_allocation_lines_for_day(
            lines, eid=eid, week_sig=week_sig, iso=iso
        )
        alloc_state = _get_day_allocation_state(daily_total, live_lines)
        allocated = alloc_state["allocated_total"]
        st_part = alloc_state["allocated_st"]
        ot_part = alloc_state["allocated_ot"]
        remaining = max(0.0, round(float(alloc_state["remaining"]), 2))
        day_name = _detail_day_label({"day": day_d.strftime("%A"), "date": iso})
        balance_cls = _allocation_day_block_class(str(alloc_state["state"]))
        if str(alloc_state["state"]) == "overallocated":
            balance_cls += " timekeeping-alloc-day-unbalanced"
        type_bits = []
        if st_part > 0:
            type_bits.append(f"S/T {_fmt_day_hours(st_part)}")
        if ot_part > 0:
            type_bits.append(f"O/T {_fmt_day_hours(ot_part)}")
        type_summary = f" ({' · '.join(type_bits)})" if type_bits else ""

        st.markdown(
            f'<span class="timekeeping-alloc-day-state-marker timekeeping-alloc-day-state-'
            f'{html.escape(str(alloc_state["state"]))}" aria-hidden="true"></span>'
            f'<div class="timekeeping-alloc-day-block{balance_cls}">'
            f'<div class="timekeeping-alloc-day-head">'
            f'<span class="timekeeping-alloc-day-title">{html.escape(day_name)}</span>'
            f'<span class="timekeeping-alloc-day-date">{html.escape(fmt_date(iso))}</span>'
            f'<span class="timekeeping-alloc-day-total">'
            f'{html.escape(_fmt_day_hours(daily_total))} hrs in row above'
            f"</span>"
            f'<span class="timekeeping-alloc-day-split">'
            f"Allocated {_fmt_day_hours(allocated)} / {_fmt_day_hours(daily_total)}"
            f"{html.escape(type_summary)} · {_fmt_day_hours(remaining)} remaining"
            f"</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        if daily_total <= 0:
            st.caption("Enter hours for this day in the row above before assigning.")
            continue

        running_allocated = 0.0
        for lix, line in enumerate(lines):
            day_status = _normalize_timecard_status(line.get("status"))
            row_editable = not week_locked and _day_is_editable(day_status)
            live_job = str(line.get("job") or job_opts[0])
            job_key = f"tk_alloc_job_{eid}_{week_sig}_{iso}_{lix}"
            if job_key in st.session_state:
                live_job = str(st.session_state[job_key])
            hour_type = _normalize_alloc_hour_type(line.get("hour_type"))
            type_labels = list(_ALLOC_HOUR_TYPE_OPTS)
            type_key = f"tk_alloc_type_{eid}_{week_sig}_{iso}_{lix}"
            if type_key in st.session_state:
                hour_type = _normalize_alloc_hour_type(st.session_state[type_key])
            row_remaining = max(0.0, round(daily_total - running_allocated, 2))
            is_primary_row = lix == 0

            with st.container(key=f"tk_alloc_row_{eid}_{week_sig}_{iso}_{lix}"):
                if is_primary_row:
                    st.markdown(
                        '<span class="timekeeping-allocation-primary-row-marker" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    '<span class="timekeeping-allocation-line-marker" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                row_cols = st.columns(
                    _ALLOC_LINE_COLS_PRIMARY if is_primary_row else _ALLOC_LINE_COLS,
                    gap="small",
                )
                with row_cols[0]:
                    st.markdown(
                        '<span class="timekeeping-allocation-assignment-marker" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                    if row_editable:
                        line["job"] = st.selectbox(
                            "Assignment",
                            job_opts,
                            index=_assignment_option_index(job_opts, live_job),
                            key=job_key,
                            label_visibility="collapsed",
                        )
                    else:
                        st.markdown(
                            f'<div class="timekeeping-alloc-cell">'
                            f"{html.escape(str(line.get('job') or '—'))}</div>",
                            unsafe_allow_html=True,
                        )
                with row_cols[1]:
                    st.markdown(
                        '<span class="timekeeping-allocation-type-marker" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                    if row_editable:
                        type_lbl = _alloc_hour_type_label(hour_type)
                        picked = st.selectbox(
                            "Type",
                            type_labels,
                            index=type_labels.index(type_lbl) if type_lbl in type_labels else 0,
                            key=type_key,
                            label_visibility="collapsed",
                        )
                        line["hour_type"] = _normalize_alloc_hour_type(picked)
                    else:
                        st.markdown(
                            f'<div class="timekeeping-alloc-cell timekeeping-alloc-type-cell">'
                            f"{html.escape(_alloc_hour_type_label(hour_type))}</div>",
                            unsafe_allow_html=True,
                        )
                with row_cols[2]:
                    line["hours"] = _render_allocation_hours_input(
                        value=float(line.get("hours") or 0),
                        widget_key=f"tk_alloc_hrs_{eid}_{week_sig}_{iso}_{lix}",
                        disabled=not row_editable,
                    )
                with row_cols[3]:
                    st.markdown(
                        f'<div class="timekeeping-alloc-remaining-cell">'
                        f"{html.escape(_fmt_day_hours(row_remaining))}</div>",
                        unsafe_allow_html=True,
                    )
                with row_cols[4]:
                    st.markdown(
                        f'<div class="timekeeping-alloc-status-cell">'
                        f"{_timecard_status_pill_html(day_status)}</div>",
                        unsafe_allow_html=True,
                    )
                with row_cols[5]:
                    if row_editable:
                        line["notes"] = st.text_input(
                            "Notes",
                            value=str(line.get("notes") or ""),
                            key=f"tk_alloc_notes_{eid}_{week_sig}_{iso}_{lix}",
                            label_visibility="collapsed",
                            placeholder="Notes…",
                        )
                    else:
                        st.markdown(
                            f'<div class="timekeeping-alloc-cell">'
                            f"{html.escape(str(line.get('notes') or '—'))}</div>",
                            unsafe_allow_html=True,
                        )
                if is_primary_row:
                    with row_cols[6]:
                        _render_allocation_primary_row_actions(
                            emp=emp,
                            week_start_d=week_start_d,
                            eid=eid,
                            week_sig=week_sig,
                            iso=iso,
                            lines=lines,
                            line=line,
                            lix=lix,
                            day_status=day_status,
                            row_editable=row_editable,
                            can_approve=can_approve,
                            by_date=by_date,
                            daily_total=daily_total,
                            job_opts=job_opts,
                        )
                else:
                    with row_cols[6]:
                        line_id = str(line.get("line_id") or "").strip()
                        if row_editable and len(lines) > 1:
                            if st.button(
                                "Remove",
                                key=f"tk_alloc_del_{eid}_{week_sig}_{iso}_{lix}",
                                help="Remove this assignment row",
                            ):
                                by_date[iso] = [ln for j, ln in enumerate(lines) if j != lix]
                                st.session_state[_alloc_state_key(eid)] = by_date
                                st.rerun()

            if not is_primary_row:
                line_id = str(line.get("line_id") or "").strip()
                if row_editable and line_id and float(line.get("hours") or 0) > 0:
                    action_cols = st.columns([1.1, 1.1, 3.8])
                    action_taken = False
                    with action_cols[0]:
                        if day_status in ("Draft", "Rejected") and st.button(
                            "Submit day line",
                            key=f"tk_alloc_submit_{eid}_{week_sig}_{iso}_{lix}",
                            use_container_width=True,
                        ):
                            action_taken = _handle_alloc_line_submit(emp, week_start_d, line_id)
                    with action_cols[1]:
                        if day_status == "Pending" and can_approve:
                            approve_cols = st.columns(2)
                            with approve_cols[0]:
                                if st.button(
                                    "Approve",
                                    key=f"tk_alloc_ok_{eid}_{week_sig}_{iso}_{lix}",
                                    use_container_width=True,
                                ):
                                    action_taken = _handle_alloc_line_approve(
                                        emp, week_start_d, line_id
                                    )
                            with approve_cols[1]:
                                if st.button(
                                    "Reject",
                                    key=f"tk_alloc_no_{eid}_{week_sig}_{iso}_{lix}",
                                    use_container_width=True,
                                ):
                                    action_taken = _handle_alloc_line_reject(
                                        emp, week_start_d, line_id
                                    )
                    if action_taken:
                        st.rerun()

            running_allocated += _line_allocated_hours(line)
            line["hour_type"] = _normalize_alloc_hour_type(line.get("hour_type"))

        if day_ix < len(grid) and lines:
            grid[day_ix]["job"] = str(lines[0].get("job") or grid[day_ix].get("job") or "")

    st.session_state[_grid_key(eid)] = grid
    st.session_state[_alloc_state_key(eid)] = by_date

    if week_locked:
        return

    record_key = record_session_key(emp, "id")
    action_left, action_right = st.columns([1, 1])
    with action_left:
        if st.button("Save allocations", key=f"tk_save_alloc_{record_key}", type="primary"):
            if _save_allocation_week(emp, week_start_d):
                st.rerun()
    with action_right:
        if week_status in ("Draft", "Rejected", "Pending") and st.button(
            "Submit all for approval",
            key=f"tk_submit_alloc_{record_key}",
        ):
            if _save_allocation_week(emp, week_start_d, show_message=False) and _submit_timekeeping_week(
                emp, week_start_d
            ):
                st.rerun()
    st.caption(
        "Totals in the row above are the source of truth. Choose S/T or O/T on each row, then save. "
        "Unallocated time is saved to — No assignment — as S/T automatically."
    )


def _render_inline_daily_entries(row: dict, week_start_d: date) -> None:
    emp = _emp_from_timecard_row(row)
    timecard_id = str(row.get("timecard_id") or "").strip()
    _render_list_allocation_detail(emp, week_start_d)
    detail_col, _ = st.columns([1, 3])
    with detail_col:
        if st.button(
            "Approval, notes & activity",
            key=f"tk_open_modal_{timecard_id}",
            use_container_width=True,
        ):
            st.session_state[SELECTED_TIMECARD_KEY] = timecard_id
            st.session_state[SHOW_TIMECARD_MODAL_KEY] = True
            st.session_state[_MODAL_KEY] = timecard_id
            st.rerun()


def _render_daily_entries_tab(emp: dict, week_start_d: date) -> None:
    week_status = _normalize_timecard_status(emp.get("status"))
    if week_status == "Approved":
        _render_weekly_grid_readonly(emp, week_start_d)
        st.info("This week is approved and locked.")
        return

    _render_weekly_grid_edit(emp, week_start_d)
    action_left, action_right = st.columns([1, 1])
    record_key = record_session_key(emp, "id")
    with action_left:
        if st.button("Save Hours", key=f"tk_save_hours_{record_key}", type="primary"):
            if _save_timekeeping_week(emp, week_start_d):
                st.rerun()
    with action_right:
        if week_status in ("Draft", "Rejected", "Pending") and st.button(
            "Submit All for Approval",
            key=f"tk_submit_{record_key}",
        ):
            if _submit_timekeeping_week(emp, week_start_d):
                st.rerun()
    st.caption(
        "Enter hours on the grid, assign jobs per day, then submit each day or the full week."
    )


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
        st.caption("Approve individual days on the Daily Entries tab, or approve the full week below.")
    elif status == "Draft":
        st.caption("Enter hours on the Daily Entries tab, then submit each day or the full week for approval.")
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
    week_start_d: date,
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
    days = week_dates(week_start_d)

    with st.container(key="timekeeping_table_wrap"):
        st.markdown(
            '<div class="ips-timekeeping-table-wrap timekeeping-list-scroll">',
            unsafe_allow_html=True,
        )

        header_cols = st.columns(_WEEKLY_TS_LIST_ROW_COLS, gap="xxsmall")
        day_header_labels = [d.strftime("%a %m/%d").upper() for d in days]
        summary_header_labels = [
            "Total Hours",
            "Overtime",
            "Billed Hours",
            "STATUS",
        ]
        with header_cols[0]:
            st.markdown(
                '<span class="timekeeping-list-header-marker" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
        with header_cols[2]:
            render_table_header_cell(
                "EMPLOYEE",
                table_key=_TABLE_KEY,
                filter_field="employee_name",
                filter_options=filter_options.get("employee_name", []),
                base_class="ips-timekeeping-header-row ips-timekeeping-cell",
            )
        for col, label in zip(header_cols[3:10], day_header_labels):
            with col:
                render_table_header_cell(
                    label,
                    base_class="ips-timekeeping-header-row ips-timekeeping-cell",
                )
        with header_cols[10]:
            _render_timekeeping_list_spacer_cell()
        for col, label in zip(header_cols[11:15], summary_header_labels):
            with col:
                render_table_header_cell(
                    label,
                    base_class="ips-timekeeping-header-row ips-timekeeping-cell",
                )

        for row in filtered:
            timecard_id = str(row.get("timecard_id") or "").strip()
            if not timecard_id:
                continue

            employee_name = str(row.get("employee_name") or "—")
            status = _normalize_timecard_status(row.get("status"))
            expanded = _expanded_timecard_id() == timecard_id
            emp = _emp_from_timecard_row(row)
            eid = str(emp.get("id") or emp.get("employee_id") or "")
            week_sig = week_start_d.isoformat()
            grid = _ensure_weekly_grid(emp, week_start_d) if eid else []
            st_total = float(row.get("st_total") or 0)
            ot_total = float(row.get("ot_total") or 0)
            total_hours = float(row.get("total_hours") or 0)
            if eid:
                grid = _sync_grid_from_widget_keys(grid, eid=eid, week_sig=week_sig)
                _apply_row_hrs_to_grid(grid, eid=eid, week_sig=week_sig)
                _apply_active_field_job_to_grid(grid)

            with st.container(key=f"tk_row_{timecard_id}"):
                st.markdown(
                    '<span class="timesheet-employee-card-marker" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                row_cols = st.columns(_WEEKLY_TS_LIST_ROW_COLS, gap="xxsmall")

                with row_cols[0]:
                    st.markdown(
                        '<span class="weekly-timesheet-row-marker timesheet-list-row-marker '
                        'timekeeping-list-row-marker" aria-hidden="true"></span>'
                        '<span class="timekeeping-drag-cell timesheet-list-drag-handle" '
                        'aria-hidden="true">⋮⋮</span>',
                        unsafe_allow_html=True,
                    )
                with row_cols[1]:
                    st.markdown(
                        '<span class="weekly-timesheet-expand-marker weekly-timesheet-expand '
                        'timekeeping-expand-cell" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "▾" if expanded else "▸",
                        key=f"tk_expand_{timecard_id}",
                        help="Expand ST/OT detail, notes, and daily submit",
                    ):
                        _toggle_expanded_timecard(timecard_id)
                        st.rerun()

                with row_cols[2]:
                    st.markdown(
                        f'<div class="timekeeping-employee-cell weekly-timesheet-employee '
                        f'weekly-employee-cell timesheet-list-employee-cell">'
                        f'<div class="timesheet-list-name-input weekly-timesheet-employee-name '
                        f'employee-name ips-timekeeping-employee" '
                        f'title="{html.escape(employee_name)}">{html.escape(employee_name)}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                if eid:
                    alloc_by_date = _ensure_allocation_state(emp, week_start_d)
                    for day_ix, (col, day_d) in enumerate(zip(row_cols[3:10], days)):
                        day_row = grid[day_ix] if day_ix < len(grid) else {}
                        day_row = _day_row_with_widget_values(
                            day_row, eid=eid, week_sig=week_sig, index=day_ix
                        )
                        day_status = _normalize_timecard_status(day_row.get("status"))
                        week_status = _normalize_timecard_status(emp.get("status"))
                        editable = (
                            week_status != "Approved" and _day_is_editable(day_status)
                        )
                        with col:
                            _render_list_row_day_cell(
                                day_d=day_d,
                                day_ix=day_ix,
                                day_row=day_row,
                                emp_id=eid,
                                week_sig=week_sig,
                                editable=editable,
                                alloc_by_date=alloc_by_date,
                            )
                    st.session_state[_grid_key(eid)] = grid
                    st_total, ot_total, total_hours = _row_totals_from_grid(grid)
                else:
                    for col in row_cols[3:10]:
                        with col:
                            st.markdown(
                                '<div class="timekeeping-day-cell ips-timekeeping-hours">—</div>',
                                unsafe_allow_html=True,
                            )

                with row_cols[10]:
                    _render_timekeeping_list_spacer_cell()
                with row_cols[11]:
                    st.markdown(
                        f'<div class="timekeeping-total-cell ips-timekeeping-hours '
                        f'timesheet-list-summary-cell">'
                        f"{html.escape(_fmt_table_hours(st_total))}</div>",
                        unsafe_allow_html=True,
                    )
                with row_cols[12]:
                    st.markdown(
                        f'<div class="timekeeping-overtime-cell ips-timekeeping-hours '
                        f'timesheet-list-summary-cell">'
                        f"{html.escape(_fmt_table_hours(ot_total))}</div>",
                        unsafe_allow_html=True,
                    )
                with row_cols[13]:
                    st.markdown(
                        f'<div class="timekeeping-billed-cell ips-timekeeping-hours '
                        f'timesheet-list-summary-cell">'
                        f"{html.escape(_fmt_table_hours(total_hours))}</div>",
                        unsafe_allow_html=True,
                    )
                with row_cols[14]:
                    st.markdown(
                        f'<div class="timekeeping-status-cell timesheet-list-status-cell">'
                        f"{_timecard_status_pill_html(status)}</div>",
                        unsafe_allow_html=True,
                    )

            if expanded:
                with st.container(key=f"tk_expand_detail_{timecard_id}"):
                    st.markdown(
                        '<span class="timekeeping-expand-detail-panel timekeeping-detail-expand-host '
                        'timesheet-employee-expand-detail ips-timekeeping-row-expand" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                    _render_inline_daily_entries(row, week_start_d)

        st.markdown("</div>", unsafe_allow_html=True)

    _inject_timekeeping_daily_hour_focus_script()

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
    summaries = _filter_summaries_for_field_user(load_timekeeping_summaries(ws))
    all_rows = [_build_timecard_row(row, ws) for row in summaries]
    filter_options = build_filter_options(all_rows, _TK_COLUMN_FILTER_SPECS)

    def _tk_export() -> None:
        st.button("Export", key="tk_export", use_container_width=True)

    render_page_brand_header(
        "Timekeeping",
        "View and edit employee weekly time entries.",
        actions=[_tk_export],
    )

    if is_field_context():
        try:
            from app.db import fetch_jobs_with_order_fallback
            from app.services.job_service import sort_jobs_by_number_then_name
        except ImportError:
            from db import fetch_jobs_with_order_fallback  # type: ignore
            from services.job_service import sort_jobs_by_number_then_name  # type: ignore
        try:
            from app.auth import current_role as _tk_role
        except ImportError:
            from auth import current_role as _tk_role  # type: ignore
        if _tk_role() in {"admin", "manager", "supervisor", "project manager", "pm"}:
            jobs = sort_jobs_by_number_then_name(
                list(fetch_jobs_with_order_fallback(limit=3000, use_admin=True) or [])
            )
            if jobs:
                render_field_job_bar(jobs, key_prefix="tk")

    nav1, nav2, nav3, week_col = st.columns([1, 1, 1, 2.2], gap="small")
    with nav1:
        if st.button("Previous Week", key="tk_prev_week", use_container_width=True):
            st.session_state[_WEEK_KEY] = ws - timedelta(days=7)
            _clear_expanded_timecard()
            st.rerun()
    with nav2:
        if st.button("Current Week", key="tk_current_week", use_container_width=True):
            st.session_state[_WEEK_KEY] = week_start()
            _clear_expanded_timecard()
            st.rerun()
    with nav3:
        if st.button("Next Week", key="tk_next_week", use_container_width=True):
            st.session_state[_WEEK_KEY] = ws + timedelta(days=7)
            _clear_expanded_timecard()
            st.rerun()
    with week_col:
        st.markdown(
            f'<p class="ips-time-week-range">{html.escape(fmt_date(ws))} – {html.escape(fmt_date(we))}</p>'
            f'<p class="ips-time-week-sub">Week {ws.isocalendar()[1]}</p>',
            unsafe_allow_html=True,
        )

    filtered = _filter_timecards(summaries, ws)

    build_modal_cache(filtered, row_id_key="timecard_id", cache_key=_CACHE_KEY)

    st.caption(f"{len(filtered)} timecard(s) · Day boxes stay visible on each row. Expand for job/ST/OT detail.")
    _render_custom_timekeeping_table(filtered, filter_options=filter_options, week_start_d=ws)

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


def render_field_time_panel(*, key_prefix: str = "ftp") -> None:
    """Compact weekly hour entry for the field day shell."""
    inject_timekeeping_module_css()
    ws = _current_week_start()
    we = week_end(ws)
    summaries = _filter_summaries_for_field_user(load_timekeeping_summaries(ws))
    rows = [_build_timecard_row(row, ws) for row in summaries]
    if not rows:
        st.info("No timecard loaded for this week yet.")
        return
    st.caption(f"{fmt_date(ws)} – {fmt_date(we)} · job + hours for all seven days.")
    _render_horizontal_week_grid(rows, week_start_d=ws, key_prefix=key_prefix)
