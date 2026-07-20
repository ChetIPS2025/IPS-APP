"""Timekeeping module (Phase 2C)."""

from __future__ import annotations

import html
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlencode

import streamlit as st

from app.components.table_filters import (
    apply_column_filters,
    build_filter_options,
    render_table_header_cell,
)
from app.components.table_pagination import (
    paginate_rows,
    render_table_pagination_footer,
    render_table_pagination_header,
    reset_table_page,
)
from app.components.timekeeping_allocation import (
    AllocationRenderDeps,
    DayAllocationCardContext,
    allocation_panel_scope_key,
    render_allocation_days_panel,
    render_allocation_panel_intro,
    render_day_allocation_card,
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
    show_modal_if_pending,
)
from app.pages._core._data import (
    build_timekeeping_grid_from_day_rows,
    default_weekly_grid,
    load_jobs,
    load_timekeeping_grid,
    load_timekeeping_summaries,
    persist_timekeeping_approve,
    persist_timekeeping_days,
    persist_timekeeping_day_approve,
    persist_timekeeping_day_approve_for_date,
    persist_timekeeping_day_reject,
    persist_timekeeping_day_reject_for_date,
    persist_timekeeping_day_submit,
    persist_timekeeping_day_submit_for_date,
    persist_timekeeping_reject,
    persist_timekeeping_submit,
)
from app.pages._core._session import select_key
from app.styles import (
    _inject_timekeeping_daily_hour_focus_script,
    inject_timekeeping_module_css,
)
from app.utils.dates import DATE_INPUT_FORMAT, normalize_date, week_dates, week_end, week_start
from app.utils.field_context import get_field_job_id, is_field_context, render_field_job_bar
from app.utils.formatting import fmt_date
from app.ui.streamlit_perf import (
    fragment,
    fragment_rerun,
    inject_scroll_preserve,
    ips_app_rerun,
)

_SEL = select_key("timekeeping")
_MODULE = "timekeeping"
_TABLE_KEY = "timekeeping_list"
_TK_LIST_PAGE_SIZE = 25
_TK_WEEK_DAYS_KEY = "ips_tk_week_days_by_employee"
_TK_WEEK_DAYS_SIG_KEY = "ips_tk_week_days_sig"
_MODAL_KEY = "ips_timekeeping_detail_modal_id"
_CACHE_KEY = "_ips_timekeeping_modal_by_id"
_WEEK_KEY = "ips_timekeeping_week_start"
_TK_ASSIGNMENT_OPTS_KEY = "ips_tk_assignment_options"
_TK_ASSIGNMENT_OPTS_SIG_KEY = "ips_tk_assignment_options_sig"
SELECTED_TIMECARD_KEY = "selected_timecard_id"
SHOW_TIMECARD_MODAL_KEY = "show_timecard_detail_modal"
_ALL_TIMECARD_IDS_KEY = "_ips_timekeeping_visible_ids"
TIMEKEEPING_MODAL_EMPLOYEE_ID_KEY = "timekeeping_modal_employee_id"
TIMEKEEPING_MODAL_DATE_KEY = "timekeeping_modal_date"
TIMEKEEPING_MODAL_TIMECARD_KEY = "timekeeping_modal_timecard_id"
SHOW_TIMEKEEPING_DAY_MODAL_KEY = "show_timekeeping_day_modal"
SELECTED_TIME_EMPLOYEE_ID_KEY = "selected_time_employee_id"
SELECTED_TIME_DATE_KEY = "selected_time_date"
_TIMEKEEPING_NAV_QUERY_KEY = "ips_nav"
_TIMEKEEPING_NAV_SLUG = "timekeeping"
_TIMEKEEPING_DAY_EMPLOYEE_QUERY_KEY = "tk_employee"
_TIMEKEEPING_DAY_DATE_QUERY_KEY = "tk_date"
_TIMEKEEPING_DAY_TIMECARD_QUERY_KEY = "tk_timecard"
_TIMEKEEPING_DETAIL_TAB_KEY = "ips_timekeeping_detail_tab"
_TK_DETAIL_TAB_EMP_KEY = "ips_timekeeping_detail_tab_employee"
_TK_DETAIL_TAB_REQUEST_KEY = "ips_timekeeping_detail_tab_request"
_TIMEKEEPING_DETAIL_TABS = (
    "Weekly Timecard",
    "Daily Entries",
    "Approval",
    "Notes",
    "Activity",
)
_TK_PERMISSIONS_KEY = "ips_timekeeping_permissions"
_TK_PERMISSIONS_FP_KEY = "ips_timekeeping_permissions_fp"
_TK_WEEKEND_COUNTS_KEY = "ips_timekeeping_weekend_counts_toward_40"
_EXPANDED_TIMECARD_KEY = "ips_timekeeping_expanded_id"
_TS_EXPAND = 32
_TS_EMPLOYEE = 180
_TS_DAY = 140
_TS_WEEK = 70
_TS_LIST_HANDLE = 28
_TS_LIST_EXPAND = 38
_TS_LIST_EMPLOYEE = 190
_TS_LIST_DAY = 92
_TS_LIST_TOTAL = 58
_TS_LIST_OVERTIME = 58
_TS_LIST_BILLED = 58
_TS_LIST_STATUS = 70
_HGRID_COLS = [_TS_EMPLOYEE] + [_TS_DAY] * 7 + [_TS_WEEK]
_WEEKLY_TS_LIST_ROW_COLS = [
    2.85,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    0.7,
    0.7,
    0.75,
    0.85,
]


def _is_narrow_viewport() -> bool:
    from app.mobile_ui import IPS_VIEWPORT_NARROW_KEY
    return bool(st.session_state.get(IPS_VIEWPORT_NARROW_KEY))


def _is_day_panel_open() -> bool:
    eid = str(st.session_state.get(SELECTED_TIME_EMPLOYEE_ID_KEY) or "").strip()
    iso = str(st.session_state.get(SELECTED_TIME_DATE_KEY) or "").strip()[:10]
    return bool(eid and iso) and not _is_narrow_viewport()


def _is_day_cell_selected(eid: str, iso: str) -> bool:
    sel_eid = str(st.session_state.get(SELECTED_TIME_EMPLOYEE_ID_KEY) or "").strip()
    sel_iso = str(st.session_state.get(SELECTED_TIME_DATE_KEY) or "").strip()[:10]
    return sel_eid == str(eid or "").strip() and sel_iso == str(iso or "").strip()[:10]


def _timekeeping_day_href(
    *,
    employee_id: str,
    work_date: date,
    timecard_id: str,
) -> str:
    eid = str(employee_id or "").strip()
    tid = str(timecard_id or "").strip()
    if not eid:
        return "#"
    params: dict[str, str] = {
        _TIMEKEEPING_NAV_QUERY_KEY: _TIMEKEEPING_NAV_SLUG,
        _TIMEKEEPING_DAY_EMPLOYEE_QUERY_KEY: eid,
        _TIMEKEEPING_DAY_DATE_QUERY_KEY: work_date.isoformat(),
    }
    if tid:
        params[_TIMEKEEPING_DAY_TIMECARD_QUERY_KEY] = tid
    return "?" + urlencode(params)


def _clear_timekeeping_day_query_params() -> None:
    try:
        qp = st.query_params
    except Exception:
        return
    for key in (
        _TIMEKEEPING_DAY_EMPLOYEE_QUERY_KEY,
        _TIMEKEEPING_DAY_DATE_QUERY_KEY,
        _TIMEKEEPING_DAY_TIMECARD_QUERY_KEY,
    ):
        if key in qp:
            del qp[key]


def _capture_timekeeping_day_query() -> None:
    try:
        employee_id = str(
            st.query_params.get(_TIMEKEEPING_DAY_EMPLOYEE_QUERY_KEY) or ""
        ).strip()
        date_raw = str(
            st.query_params.get(_TIMEKEEPING_DAY_DATE_QUERY_KEY) or ""
        ).strip()[:10]
        timecard_id = str(
            st.query_params.get(_TIMEKEEPING_DAY_TIMECARD_QUERY_KEY) or ""
        ).strip()
    except Exception:
        return
    if not employee_id or not date_raw:
        return
    try:
        work_date = date.fromisoformat(date_raw)
    except ValueError:
        return
    target_week = week_start(work_date)
    if target_week != _current_week_start():
        st.session_state[_WEEK_KEY] = target_week
        clear_timekeeping_list_caches()
    _open_day_time_editor(
        eid=employee_id,
        work_date=work_date,
        timecard_id=timecard_id,
        week_start_d=target_week,
    )


def _is_day_editor_active() -> bool:
    if st.session_state.get(SHOW_TIMEKEEPING_DAY_MODAL_KEY):
        return True
    eid = str(
        st.session_state.get(SELECTED_TIME_EMPLOYEE_ID_KEY)
        or st.session_state.get(TIMEKEEPING_MODAL_EMPLOYEE_ID_KEY)
        or ""
    ).strip()
    iso = str(
        st.session_state.get(SELECTED_TIME_DATE_KEY)
        or st.session_state.get(TIMEKEEPING_MODAL_DATE_KEY)
        or ""
    ).strip()[:10]
    return bool(eid and iso)


def _timekeeping_app_rerun() -> None:
    """Rerun the full app (dialogs and page shell live outside list fragments)."""
    ips_app_rerun()


def _weekly_hours_widget_key(eid: str, work_date: date | str) -> str:
    """Stable list-row hour widget key (employee + work date)."""
    iso = work_date.isoformat() if isinstance(work_date, date) else str(work_date)[:10]
    return f"weekly_hours_{eid}_{iso}"


def _legacy_hours_widget_key(eid: str, week_sig: str, day_ix: int) -> str:
    return f"tk_hrs_{eid}_{week_sig}_{day_ix}"


def _hours_widget_session_value(
    *,
    eid: str,
    week_sig: str,
    day_ix: int,
    work_date: date | str,
) -> float | None:
    """Read list-row hours from the new or legacy widget key."""
    new_key = _weekly_hours_widget_key(eid, work_date)
    legacy_key = _legacy_hours_widget_key(eid, week_sig, day_ix)
    if new_key in st.session_state:
        return max(0.0, float(st.session_state[new_key] or 0))
    if legacy_key in st.session_state:
        return max(0.0, float(st.session_state[legacy_key] or 0))
    return None


def _apply_hours_widget_to_row(
    row: dict,
    *,
    eid: str,
    week_sig: str,
    day_ix: int,
) -> None:
    work_date = str(row.get("date") or "")[:10]
    if not work_date:
        return
    value = _hours_widget_session_value(
        eid=eid,
        week_sig=week_sig,
        day_ix=day_ix,
        work_date=work_date,
    )
    if value is not None:
        _set_day_job_hours(row, value)


def _render_timekeeping_inline_html(html_content: str) -> None:
    """Render list cell HTML without Streamlit <p> wrapper collapsing block layout."""
    if hasattr(st, "html"):
        st.html(html_content)
    else:
        st.markdown(html_content, unsafe_allow_html=True)


def _render_timekeeping_summary_column_header_html(label: str) -> str:
    return (
        f'<div class="ips-timekeeping-header-row ips-timekeeping-cell ips-timekeeping-row-column-header">'
        f'<div class="timekeeping-header-summary-label">{html.escape(str(label).upper())}</div>'
        f"</div>"
    )


def _render_timekeeping_employee_filter_header(
    filter_options: dict[str, list[str]],
    *,
    days: list[date],
) -> None:
    """Employee filter and summary column titles at the top of the list."""
    header_cols = st.columns(_WEEKLY_TS_LIST_ROW_COLS, gap="small")
    st.markdown(
        '<span class="timekeeping-list-header-marker timekeeping-weekly-table-header-marker" '
        'aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    with header_cols[0]:
        render_table_header_cell(
            "EMPLOYEE",
            table_key=_TABLE_KEY,
            filter_field="employee_name",
            filter_options=filter_options.get("employee_name", []),
            base_class="ips-timekeeping-header-row ips-timekeeping-cell",
        )
    for col, day_d in zip(header_cols[1:8], days):
        with col:
            st.markdown(
                f'<div class="timekeeping-day-header-label">'
                f"{html.escape(day_d.strftime('%a').upper())} "
                f"{html.escape(day_d.strftime('%m/%d'))}</div>",
                unsafe_allow_html=True,
            )
    for col, label in zip(header_cols[8:12], _LIST_VIEW_SUMMARY_LABELS):
        with col:
            st.markdown(
                f'<div class="timekeeping-summary-header-label">{html.escape(str(label).upper())}</div>',
                unsafe_allow_html=True,
            )


_STATUS_FILTER_OPTS = ["Draft", "Pending Approval", "Approved", "Rejected"]
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
_TK_HOUR_AUTOSAVE_DEBOUNCE_SEC = 1.0
_LIST_VIEW_SUMMARY_LABELS = ("ST (≤40)", "OT (>40)", "TOTAL HOURS", "STATUS")
_ALLOC_HOUR_TYPE_OPTS = ("Auto", "S/T", "O/T")
_ALLOC_TOLERANCE = 0.01
_ASSIGNMENT_LEGACY_ALIASES = {
    "ips shop": "Shop",
    "administrator": "Administrative",
    "admin": "Administrative",
    "— no job —": "— No assignment —",
    "no job": "— No assignment —",
    "— no assignment —": "— No assignment —",
    "no assignment": "— No assignment —",
    "— select assignment —": "— No assignment —",
    "select assignment": "— No assignment —",
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


_ASSIGNMENT_EXCLUDED_JOB_STATUSES = frozenset(
    {"Deleted", "Archived", "Completed", "Closed", "Cancelled"}
)


def _normalize_assignable_job_status(raw: object) -> str:
    from app.services.jobs_service import normalize_job_status
    return normalize_job_status(raw)


def _job_row_assignable_for_timekeeping(job: dict[str, Any]) -> bool:
    """Match Jobs list Active view: real rows only, not deleted/archived/closed-out."""
    from app.services.job_service import is_job_assignable_for_field_picker
    return is_job_assignable_for_field_picker(job)


def _job_assignment_label(job: dict[str, Any]) -> str:
    num = str(job.get("job_number") or "").strip()
    name = str(job.get("job_name") or job.get("name") or "").strip()
    if num and name:
        return f"{num} — {name}"
    return num or name


def _build_assignment_options_for_timekeeping() -> list[str]:
    """Build assignable job/subjob labels (uncached)."""
    import logging

    from app.perf_debug import perf_enabled, perf_span
    from app.services.tasks_service import (
        _TASKS_FOR_JOBS_CHUNK_SIZE,
        get_tasks_for_jobs,
    )

    _log = logging.getLogger("ips.perf")
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

    assignable_jobs: list[dict[str, Any]] = []
    job_ids: list[str] = []
    with perf_span("timekeeping.assignment_jobs"):
        for job in load_jobs():
            if not _job_row_assignable_for_timekeeping(job):
                continue
            assignable_jobs.append(job)
            jid = str(job.get("id") or "").strip()
            if jid:
                job_ids.append(jid)

    tasks_by_job: dict[str, list[dict[str, Any]]] = {}
    batch_count = 0
    with perf_span("timekeeping.assignment_tasks_batch"):
        if job_ids:
            batch_count = (len(job_ids) + _TASKS_FOR_JOBS_CHUNK_SIZE - 1) // _TASKS_FOR_JOBS_CHUNK_SIZE
            tasks_by_job = get_tasks_for_jobs(job_ids, include_closed=True)

    task_count = sum(len(rows) for rows in tasks_by_job.values())
    if perf_enabled():
        _log.warning(
            "[perf] timekeeping.assignment_jobs: jobs=%d",
            len(assignable_jobs),
        )
        _log.warning(
            "[perf] timekeeping.assignment_tasks_batch: tasks=%d batches=%d",
            task_count,
            batch_count,
        )

    with perf_span("timekeeping.assignment_options_build"):
        for job in assignable_jobs:
            job_label = _job_assignment_label(job)
            if not job_label:
                continue
            _add(job_label)
            jid = str(job.get("id") or "").strip()
            if jid:
                for task in tasks_by_job.get(jid, []):
                    _add(_subjob_assignment_label(task, job_label=job_label))

        for special in ("Shop", "Administrative", "Vacation"):
            _add(special)

    return opts


def _assignment_options_cache_sig(*, week_start_d: date | None = None) -> str:
    from app.pages._core._data import jobs_catalog_data_version, tasks_catalog_data_version

    ws = week_start_d or _current_week_start()
    return (
        f"{ws.isoformat()}:{jobs_catalog_data_version()}:{tasks_catalog_data_version()}"
    )


def clear_timekeeping_assignment_options_cache() -> None:
    st.session_state.pop(_TK_ASSIGNMENT_OPTS_KEY, None)
    st.session_state.pop(_TK_ASSIGNMENT_OPTS_SIG_KEY, None)


def clear_timekeeping_week_days_cache() -> None:
    st.session_state.pop(_TK_WEEK_DAYS_KEY, None)
    st.session_state.pop(_TK_WEEK_DAYS_SIG_KEY, None)


def clear_timekeeping_list_caches() -> None:
    clear_timekeeping_assignment_options_cache()
    clear_timekeeping_week_days_cache()
    from app.pages._core.page_data_cache import clear_timekeeping_summaries_page_data_cache
    from app.services.weekly_timekeeping_service import invalidate_weekly_timekeeping_page_cache

    clear_timekeeping_summaries_page_data_cache()
    invalidate_weekly_timekeeping_page_cache()


def _recalculate_visible_week_totals(week_start_d: date) -> None:
    """Reload week grids and overtime totals from saved data."""
    clear_timekeeping_list_caches()
    week_sig = week_start_d.isoformat()
    for key in list(st.session_state.keys()):
        if not isinstance(key, str):
            continue
        if key.startswith("ips_time_grid_") or key.startswith("ips_time_alloc_"):
            st.session_state.pop(key, None)
        elif key.endswith("_week") and str(st.session_state.get(key) or "") == week_sig:
            if key.startswith("ips_time_grid_") or key.startswith("ips_time_alloc_"):
                st.session_state.pop(key, None)


def _ensure_week_days_by_employee(week_start_d: date) -> dict[str, list[dict[str, Any]]]:
    """Batch-load day rows for the active week once per session/week."""
    from app.perf_debug import perf_span

    sig = week_start_d.isoformat()
    if st.session_state.get(_TK_WEEK_DAYS_SIG_KEY) == sig:
        cached = st.session_state.get(_TK_WEEK_DAYS_KEY)
        if isinstance(cached, dict):
            return cached
    with perf_span("timekeeping.week_days_batch"):
        from app.services.timekeeping_service import list_timekeeping_days_for_week

        rows = list_timekeeping_days_for_week(week_start_d)
    by_eid: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        eid = str(row.get("employee_id") or "").strip()
        if eid:
            by_eid.setdefault(eid, []).append(row)
    st.session_state[_TK_WEEK_DAYS_KEY] = by_eid
    st.session_state[_TK_WEEK_DAYS_SIG_KEY] = sig
    return by_eid


def _day_rows_for_employee(employee_id: str, week_start_d: date) -> list[dict[str, Any]]:
    eid = str(employee_id or "").strip()
    if not eid:
        return []
    return list(_ensure_week_days_by_employee(week_start_d).get(eid, []))


def _day_status_from_saved_rows(rows: list[dict[str, Any]]) -> str:
    """Aggregate day status from saved allocation/day rows."""
    if not rows:
        return "Draft"
    statuses = [_normalize_timecard_status(row.get("status")) for row in rows]
    if any(s == "Rejected" for s in statuses):
        return "Rejected"
    if any(s == "Pending" for s in statuses):
        return "Pending"
    if all(s == "Approved" for s in statuses):
        return "Approved"
    return "Draft"


def _list_display_day_rows(employee_id: str, week_start_d: date) -> list[dict[str, Any]]:
    """Lightweight 7-day rows for list UI — reads batch week cache, no session grid."""
    from app.services.weekly_timekeeping_service import aggregate_daily_display_rows

    eid = str(employee_id or "").strip()
    days = week_dates(week_start_d)
    if not eid:
        return aggregate_daily_display_rows([], week_start_d)

    saved_rows = _day_rows_for_employee(eid, week_start_d)
    return aggregate_daily_display_rows(saved_rows, week_start_d)


def _list_row_day_rows_for_display(employee_id: str, week_start_d: date) -> list[dict[str, Any]]:
    """Day rows for a list row — use loaded session grid when that employee is being edited."""
    eid = str(employee_id or "").strip()
    week_sig = week_start_d.isoformat()
    selected_eid = str(st.session_state.get(SELECTED_TIME_EMPLOYEE_ID_KEY) or "").strip()
    if eid and selected_eid == eid:
        gk = _grid_key(eid)
        if st.session_state.get(f"{gk}_week") == week_sig:
            grid = st.session_state.get(gk)
            if isinstance(grid, list) and grid:
                return grid
    return _list_display_day_rows(eid, week_start_d)


def _assignment_options_for_timekeeping(*, week_start_d: date | None = None) -> list[str]:
    """Assignable jobs from the jobs table, their subjobs, Shop, Administrative, and Vacation."""
    sig = _assignment_options_cache_sig(week_start_d=week_start_d)
    if (
        st.session_state.get(_TK_ASSIGNMENT_OPTS_SIG_KEY) == sig
        and isinstance(st.session_state.get(_TK_ASSIGNMENT_OPTS_KEY), list)
    ):
        return list(st.session_state[_TK_ASSIGNMENT_OPTS_KEY])
    opts = _build_assignment_options_for_timekeeping()
    st.session_state[_TK_ASSIGNMENT_OPTS_KEY] = opts
    st.session_state[_TK_ASSIGNMENT_OPTS_SIG_KEY] = sig
    return opts


def _coerce_assignment_label(saved: str, job_opts: list[str]) -> str:
    """Map stale/invalid saved labels to a valid dropdown option."""
    normalized = _normalize_assignment_label(saved)
    if normalized in job_opts:
        return normalized
    raw = str(saved or "").strip()
    if raw in job_opts:
        return raw
    for opt in job_opts:
        if opt.casefold() == raw.casefold():
            return opt
    return job_opts[0] if job_opts else "— No assignment —"


def _sync_assignment_job_widget(job_key: str, job_opts: list[str], saved: str) -> str:
    """Keep assignment select state on allowed options only (before widget render)."""
    coerced = _coerce_assignment_label(saved, job_opts)
    if job_key in st.session_state and st.session_state[job_key] not in job_opts:
        st.session_state[job_key] = coerced
    return coerced


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
    from app.services.jobs_service import get_job_options
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
    job_opts = _assignment_options_for_timekeeping(week_start_d=week_start_d)
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
                week_status = _week_status_from_grid(grid)
                editable = _day_hours_editable(day_status, week_status)
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


def _filter_summaries_for_current_user(summaries: list[dict]) -> list[dict]:
    """Supervisors see all crew; employees see only their own timecard."""
    from app.auth import current_profile, effective_role
    from app.utils.permissions import can_submit_timekeeping
    if can_submit_timekeeping(effective_role()):
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
            return []
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
    return filtered


def _filter_summaries_for_field_user(summaries: list[dict]) -> list[dict]:
    if not is_field_context():
        return _filter_summaries_for_current_user(summaries)
    return _filter_summaries_for_current_user(summaries)


def _timecard_is_editable(status: str) -> bool:
    if _can_admin_edit_approved_timekeeping():
        return True
    return _normalize_timecard_status(status) in ("Draft", "Rejected")


def _day_is_editable(status: str) -> bool:
    if _can_admin_edit_approved_timekeeping():
        return True
    return _normalize_timecard_status(status) in ("Draft", "Rejected")


def _day_hours_editable(day_status: str, week_status: str) -> bool:
    """Whether list-row / allocation hours may be edited for this day."""
    if not _can_submit_timekeeping():
        return False
    if _can_admin_edit_approved_timekeeping():
        return True
    day_norm = _normalize_timecard_status(day_status)
    week_norm = _normalize_timecard_status(week_status)
    if day_norm in ("Approved", "Pending"):
        return False
    if week_norm in ("Approved", "Pending"):
        return False
    return _day_is_editable(day_norm)


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


@dataclass(frozen=True)
class TimekeepingPermissions:
    role: str
    can_submit: bool
    can_approve: bool
    can_edit_approved: bool
    can_override_overtime: bool
    can_access_jobs: bool


def _permissions_fingerprint() -> str:
    from app.auth import AUTH_USER_ID_KEY, CURRENT_USER_PROFILE_KEY
    from app.utils.view_as import is_view_as_active, view_as_mode

    prof = (
        st.session_state.get("auth_profile")
        or st.session_state.get(CURRENT_USER_PROFILE_KEY)
        or {}
    )
    uid = str(
        st.session_state.get(AUTH_USER_ID_KEY)
        or prof.get("id")
        or prof.get("user_id")
        or ""
    ).strip()
    view_as = (
        f"{is_view_as_active()}:{view_as_mode()}"
        if is_view_as_active()
        else ""
    )
    return f"{uid}|{view_as}"


def _build_timekeeping_permissions() -> TimekeepingPermissions:
    from app.auth import effective_role
    from app.utils.permissions import (
        can_admin_edit_approved_timekeeping,
        can_approve_timekeeping,
        can_submit_timekeeping,
        normalize_role,
        role_can_access_page,
    )

    role = str(effective_role() or "").strip()
    norm = normalize_role(role)
    return TimekeepingPermissions(
        role=role,
        can_submit=can_submit_timekeeping(role),
        can_approve=can_approve_timekeeping(role),
        can_edit_approved=can_admin_edit_approved_timekeeping(role),
        can_override_overtime=norm == "admin",
        can_access_jobs=role_can_access_page(role, "jobs"),
    )


def _timekeeping_permissions(*, force: bool = False) -> TimekeepingPermissions:
    fp = _permissions_fingerprint()
    if not force:
        if st.session_state.get(_TK_PERMISSIONS_FP_KEY) == fp:
            snap = st.session_state.get(_TK_PERMISSIONS_KEY)
            if isinstance(snap, TimekeepingPermissions):
                return snap
    snap = _build_timekeeping_permissions()
    st.session_state[_TK_PERMISSIONS_KEY] = snap
    st.session_state[_TK_PERMISSIONS_FP_KEY] = fp
    return snap


def clear_timekeeping_permissions_snapshot() -> None:
    st.session_state.pop(_TK_PERMISSIONS_KEY, None)
    st.session_state.pop(_TK_PERMISSIONS_FP_KEY, None)
    st.session_state.pop(_TK_WEEKEND_COUNTS_KEY, None)


def _init_timekeeping_render_context() -> TimekeepingPermissions:
    from app.perf_debug import perf_span

    st.session_state.pop(_TK_WEEKEND_COUNTS_KEY, None)
    with perf_span("timekeeping.permissions"):
        perms = _timekeeping_permissions(force=True)
    _load_weekend_counts_toward_40()
    return perms


def _cached_auth_profile() -> dict[str, Any]:
    from app.auth import CURRENT_USER_PROFILE_KEY

    prof = (
        st.session_state.get("auth_profile")
        or st.session_state.get(CURRENT_USER_PROFILE_KEY)
        or {}
    )
    return dict(prof) if isinstance(prof, dict) else {}


def _current_user_id() -> str | None:
    prof = _cached_auth_profile()
    uid = str(prof.get("id") or prof.get("user_id") or "").strip()
    return uid or None


def _current_user_name() -> str:
    prof = _cached_auth_profile()
    return str(prof.get("name") or prof.get("email") or "User").strip() or "User"


def _can_approve_timekeeping() -> bool:
    return _timekeeping_permissions().can_approve


def _can_submit_timekeeping() -> bool:
    return _timekeeping_permissions().can_submit


def _can_admin_edit_approved_timekeeping() -> bool:
    return _timekeeping_permissions().can_edit_approved


def _can_override_overtime_allocation() -> bool:
    return _timekeeping_permissions().can_override_overtime


def _load_weekend_counts_toward_40() -> bool:
    from app.services.company_settings_service import load_app_settings

    settings = load_app_settings()
    value = bool(settings.get("timekeeping_weekend_counts_toward_40"))
    st.session_state[_TK_WEEKEND_COUNTS_KEY] = value
    return value


def _weekend_counts_toward_40() -> bool:
    cached = st.session_state.get(_TK_WEEKEND_COUNTS_KEY)
    if isinstance(cached, bool):
        return cached
    return _load_weekend_counts_toward_40()


def _handle_day_submit_for_date(emp: dict, week_start_d: date, work_date: str) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    wd = str(work_date or "")[:10]
    if not wd:
        st.error("Missing work date.")
        return False
    saved, save_msg = _save_allocation_week(
        emp, week_start_d, show_message=False, focus_iso=wd
    )
    if not saved:
        st.error(save_msg or "Could not save hours for this day.")
        return False
    ok, msg = persist_timekeeping_day_submit_for_date(eid, week_start_d, wd)
    if ok:
        _invalidate_weekly_grid(emp, week_start_d)
        _patch_timecard_cache(emp, week_start_d, {"status": "Pending"})
        st.success(msg)
        return True
    st.error(msg)
    return False


def _handle_day_approve_for_date(emp: dict, week_start_d: date, work_date: str) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    approver = _current_user_id()
    if not approver:
        st.error("Your profile is missing an approver id.")
        return False
    if not _save_allocation_week(emp, week_start_d, show_message=False)[0]:
        _save_timekeeping_week(emp, week_start_d, show_message=False)
    ok, msg = persist_timekeeping_day_approve_for_date(
        eid, week_start_d, work_date, approved_by=approver
    )
    if ok:
        _invalidate_weekly_grid(emp, week_start_d)
        st.success(msg)
        return True
    st.error(msg)
    return False


def _handle_day_reject_for_date(emp: dict, week_start_d: date, work_date: str) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    approver = _current_user_id()
    if not approver:
        st.error("Your profile is missing an approver id.")
        return False
    ok, msg = persist_timekeeping_day_reject_for_date(
        eid, week_start_d, work_date, approved_by=approver
    )
    if ok:
        _invalidate_weekly_grid(emp, week_start_d)
        _patch_timecard_cache(emp, week_start_d, {"status": "Rejected"})
        st.success(msg)
        return True
    st.error(msg)
    return False


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
    from app.services.weekly_timekeeping_service import invalidate_weekly_timekeeping_page_cache

    invalidate_weekly_timekeeping_page_cache(week_start_d)


def _alloc_state_key(emp_id: str) -> str:
    return f"ips_time_alloc_{emp_id}"


def _load_saved_allocations_by_date(employee_id: str, week_start_d: date) -> dict[str, list[dict[str, Any]]]:
    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in _day_rows_for_employee(employee_id, week_start_d):
        iso = str(row.get("work_date") or "")[:10]
        if not iso:
            continue
        line_id = str(row.get("id") or "")
        job = _normalize_assignment_label(str(row.get("job_label") or ""))
        notes = str(row.get("notes") or "")
        status = _normalize_timecard_status(row.get("status"))
        st_h = float(row.get("st_hours") or 0)
        ot_h = float(row.get("ot_hours") or 0) + float(row.get("dt_hours") or 0)
        meta = _overtime_meta_from_db_row(row)
        selected = _selected_time_type_from_line({**meta, "status": status})
        if st_h > 0 and ot_h > 0:
            by_date.setdefault(iso, []).append(
                _new_allocation_line(
                    **{
                        **meta,
                        "line_id": line_id,
                        "job": job,
                        "hours": st_h,
                        "notes": notes,
                        "status": status,
                        "selected_time_type": selected,
                        "final_time_type": "ST",
                    }
                )
            )
            by_date.setdefault(iso, []).append(
                _new_allocation_line(
                    **{
                        **meta,
                        "line_id": line_id,
                        "job": job,
                        "hours": ot_h,
                        "notes": notes,
                        "status": status,
                        "selected_time_type": selected,
                        "final_time_type": "OT",
                    }
                )
            )
        elif st_h > 0 or ot_h > 0:
            hours = st_h + ot_h
            final_type = meta.get("final_time_type") or ("OT" if ot_h > 0 and st_h <= 0 else "ST")
            by_date.setdefault(iso, []).append(
                _new_allocation_line(
                    **{
                        **meta,
                        "line_id": line_id,
                        "job": job,
                        "hour_type": final_type,
                        "hours": hours,
                        "notes": notes,
                        "status": status,
                        "selected_time_type": selected,
                        "final_time_type": final_type,
                    }
                )
            )
        if st_h <= 0 and ot_h <= 0:
            by_date.setdefault(iso, []).append(
                _new_allocation_line(
                    **{
                        **meta,
                        "line_id": line_id,
                        "job": job,
                        "hours": 0.0,
                        "notes": notes,
                        "status": status,
                        "selected_time_type": selected,
                    }
                )
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
    work_date = str(grid_row.get("date") or "")[:10]
    if work_date:
        value = _hours_widget_session_value(
            eid=eid,
            week_sig=week_sig,
            day_ix=day_ix,
            work_date=work_date,
        )
        if value is not None:
            return value
    legacy_key = _legacy_hours_widget_key(eid, week_sig, day_ix)
    if legacy_key in st.session_state:
        return max(0.0, float(st.session_state[legacy_key] or 0))
    return _day_hours_total(grid_row)


def _normalize_alloc_hour_type(raw: object) -> str:
    s = str(raw or "ST").strip()
    if not s:
        return "ST"
    compact = s.upper().replace(".", "").replace(" ", "").replace("/", "")
    if compact in {"AUTO", "AUTOMATIC"}:
        return "AUTO"
    if compact in {"OT", "OVERTIME"}:
        return "OT"
    return "ST"


def _selected_time_type_from_line(line: dict[str, Any]) -> str:
    """Return AUTO, ST, or OT for the Time Type dropdown."""
    explicit = str(line.get("selected_time_type") or "").strip()
    if explicit:
        return _normalize_alloc_hour_type(explicit)
    if line.get("overtime_override"):
        return _normalize_alloc_hour_type(line.get("final_time_type") or line.get("hour_type"))
    status = _normalize_timecard_status(line.get("status"))
    if status in ("Approved", "Pending"):
        return _normalize_alloc_hour_type(line.get("final_time_type") or line.get("hour_type"))
    return "AUTO"


def _selected_time_type_widget_label(selected: str) -> str:
    token = _normalize_alloc_hour_type(selected)
    if token == "AUTO":
        return "Auto"
    return _alloc_hour_type_label(token)


def _alloc_hour_type_label(hour_type: str) -> str:
    token = _normalize_alloc_hour_type(hour_type)
    if token == "AUTO":
        return "Auto"
    return "O/T" if token == "OT" else "S/T"


def _alloc_hour_type_select_index(hour_type: str) -> int:
    label = _selected_time_type_widget_label(hour_type)
    if label in _ALLOC_HOUR_TYPE_OPTS:
        return _ALLOC_HOUR_TYPE_OPTS.index(label)
    return 0


def _alloc_time_type_hint_html(line: dict[str, Any], iso: str) -> str:
    """Show calculated S/T or O/T under the Auto Time Type dropdown."""
    selected = _selected_time_type_from_line(line)
    if selected != "AUTO":
        return ""
    calculated = _normalize_alloc_hour_type(line.get("calculated_time_type") or "ST")
    from app.services.timekeeping_overtime_service import time_type_calculation_reason
    try:
        work_date = date.fromisoformat(str(iso)[:10])
    except ValueError:
        work_date = date.today()
    reason = time_type_calculation_reason(work_date=work_date, calculated=calculated)
    calc_label = _alloc_hour_type_label(calculated)
    text = f"Calculated: {calc_label}"
    if reason:
        text += f" — {reason}"
    return (
        f'<div class="timekeeping-alloc-type-hint">'
        f"Auto → {html.escape(calc_label)}"
        f"{f' ({html.escape(reason)})' if reason else ''}"
        f"</div>"
    )


def _overtime_meta_from_db_row(row: dict[str, Any]) -> dict[str, Any]:
    final_raw = row.get("final_time_type")
    calc_raw = row.get("calculated_time_type")
    final = _normalize_alloc_hour_type(final_raw) if final_raw else ""
    calculated = _normalize_alloc_hour_type(calc_raw) if calc_raw else ""
    return {
        "calculated_time_type": calculated or final or "ST",
        "final_time_type": final or calculated or "ST",
        "overtime_override": bool(row.get("overtime_override")),
        "overtime_override_by": row.get("overtime_override_by"),
        "overtime_override_at": row.get("overtime_override_at"),
        "overtime_override_reason": row.get("overtime_override_reason"),
    }


def _new_allocation_line(**extra: Any) -> dict[str, Any]:
    from app.services.timekeeping_overtime_service import new_allocation_line_defaults
    return new_allocation_line_defaults(**extra)


def _recalculate_week_overtime(
    by_date: dict[str, list[dict[str, Any]]],
    week_start_d: date,
) -> dict[str, list[dict[str, Any]]]:
    from app.services.timekeeping_overtime_service import recalculate_week_allocations
    return recalculate_week_allocations(
        by_date,
        week_start_d,
        week_dates_fn=week_dates,
        weekend_counts_toward_40=_weekend_counts_toward_40(),
        preserve_locked=True,
    )


def _overtime_policy_note() -> str:
    from app.services.timekeeping_overtime_service import overtime_policy_note
    return overtime_policy_note(weekend_counts_toward_40=_weekend_counts_toward_40())


def _summarize_week_allocation_hours(by_date: dict[str, list[dict[str, Any]]]) -> dict[str, float]:
    from app.services.timekeeping_overtime_service import summarize_week_hours
    return summarize_week_hours(by_date)


def _sync_alloc_type_widgets_from_lines(
    by_date: dict[str, list[dict[str, Any]]],
    *,
    eid: str,
    week_sig: str,
) -> None:
    """Prime type selectbox session keys before widgets render for this run."""
    try:
        from streamlit.errors import StreamlitAPIException
    except ImportError:
        StreamlitAPIException = Exception  # type: ignore[misc,assignment]

    for iso, lines in by_date.items():
        for lix, line in enumerate(lines):
            type_key = f"tk_alloc_type_{eid}_{week_sig}_{iso}_{lix}"
            label = _selected_time_type_widget_label(_selected_time_type_from_line(line))
            try:
                st.session_state[type_key] = label
            except StreamlitAPIException:
                # Widget already instantiated this run (e.g. save clicked mid-render).
                continue


def _week_allocation_totals_html(by_date: dict[str, list[dict[str, Any]]]) -> str:
    totals = _summarize_week_allocation_hours(by_date)
    return (
        '<div class="weekly-allocation-totals timekeeping-alloc-week-totals">'
        f'<span class="weekly-allocation-total-item"><strong>S/T:</strong> '
        f"{html.escape(_fmt_day_hours(totals['st_total']))}</span>"
        f'<span class="weekly-allocation-total-item"><strong>O/T:</strong> '
        f"{html.escape(_fmt_day_hours(totals['ot_total']))}</span>"
        f'<span class="weekly-allocation-total-item"><strong>Total:</strong> '
        f"{html.escape(_fmt_day_hours(totals['total_hours']))}</span>"
        "</div>"
    )


def _overtime_override_badge_html(line: dict[str, Any]) -> str:
    if not line.get("overtime_override"):
        return ""
    return (
        '<span class="timekeeping-alloc-override-badge" '
        'title="Administrator manually changed the calculated overtime type">'
        "Admin Override</span>"
    )


def _handle_alloc_type_change(
    eid: str,
    week_sig: str,
    iso: str,
    lix: int,
    *,
    can_override: bool,
) -> None:
    if not can_override:
        return
    ak = _alloc_state_key(eid)
    by_date = st.session_state.get(ak)
    if not isinstance(by_date, dict):
        return
    lines = list(by_date.get(iso) or [])
    if lix >= len(lines):
        return
    type_key = f"tk_alloc_type_{eid}_{week_sig}_{iso}_{lix}"
    raw_pick = str(st.session_state.get(type_key) or "").strip()
    line = dict(lines[lix])
    calculated = _normalize_alloc_hour_type(line.get("calculated_time_type") or "ST")
    if raw_pick == "Auto":
        line["selected_time_type"] = "AUTO"
        line["overtime_override"] = False
        line["overtime_override_by"] = None
        line["overtime_override_at"] = None
        line["overtime_override_reason"] = None
    else:
        picked = _normalize_alloc_hour_type(raw_pick)
        line["selected_time_type"] = picked
        line["overtime_override"] = True
        line["overtime_override_by"] = _current_user_id() or None
        line["overtime_override_at"] = datetime.now(timezone.utc).isoformat()
        line["final_time_type"] = picked
        line["hour_type"] = picked
    lines[lix] = line
    by_date[iso] = lines
    try:
        week_start_d = date.fromisoformat(week_sig)
        by_date = _recalculate_week_overtime(by_date, week_start_d)
        _sync_alloc_type_widgets_from_lines(by_date, eid=eid, week_sig=week_sig)
    except ValueError:
        pass
    st.session_state[ak] = by_date
    _set_alloc_autosave_status(eid, iso, "unsaved")


def _user_picked_allocation_overtime(
    *,
    eid: str,
    week_sig: str,
    iso: str,
    lix: int,
) -> bool:
    """True only when the Type widget is set to O/T for this row."""
    type_key = f"tk_alloc_type_{eid}_{week_sig}_{iso}_{lix}"
    if type_key not in st.session_state:
        return False
    return _normalize_alloc_hour_type(st.session_state[type_key]) == "OT"


def _ensure_alloc_type_widget_label(type_key: str, hour_type: str) -> None:
    """Keep Streamlit select state on Auto / S/T / O/T (not legacy ST/OT tokens)."""
    if type_key not in st.session_state:
        return
    raw = str(st.session_state[type_key] or "").strip()
    if raw in {"ST", "OT", "AUTO"}:
        st.session_state[type_key] = _selected_time_type_widget_label(raw)
    elif raw and raw not in _ALLOC_HOUR_TYPE_OPTS:
        st.session_state[type_key] = _selected_time_type_widget_label(raw)


def _line_allocated_hours(line: dict[str, Any]) -> float:
    return max(0.0, float(line.get("hours") or 0))


def _is_placeholder_assignment(label: object) -> bool:
    """True for empty, — No assignment —, — Select assignment —, and similar placeholders."""
    job = _normalize_assignment_label(str(label or "")).strip().casefold()
    if not job:
        return True
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
        return True
    return (
        "no job" in job
        or "no assignment" in job
        or "select assignment" in job
    )


def _valid_allocated_hours_sum(lines: list[dict[str, Any]]) -> float:
    return sum(
        _line_allocated_hours(line)
        for line in lines
        if _allocation_line_has_valid_assignment(line)
    )


def _allocated_hours_sum(lines: list[dict[str, Any]]) -> float:
    return sum(_line_allocated_hours(line) for line in lines)


def _daily_total_from_allocation_lines(lines: list[dict[str, Any]]) -> float:
    """Sum of allocation row hours — used when the day editor has no separate daily total."""
    return _allocated_hours_sum(lines)


def _bootstrap_day_editor_allocation_lines(
    by_date: dict[str, list[dict[str, Any]]],
    *,
    iso: str,
    grid_row: dict,
    job_opts: list[str],
) -> list[dict[str, Any]]:
    """Ensure at least one editable assignment row exists in the day editor."""
    lines = list(by_date.get(iso) or [])
    if not lines:
        lines = [
            _new_allocation_line(
                job=_default_allocation_job(grid_row, job_opts),
                hours=0.0,
                status=_normalize_timecard_status(grid_row.get("status")),
            )
        ]
        by_date[iso] = lines
    return lines


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
    """True when hours are tied to a job, subjob, Shop, Administrative, or Vacation."""
    return not _is_placeholder_assignment(line.get("job"))


def _allocation_line_hour_type_valid(line: dict[str, Any], hours: float) -> bool:
    if hours <= _ALLOC_TOLERANCE:
        return True
    final = _normalize_alloc_hour_type(line.get("final_time_type") or line.get("hour_type"))
    return final in {"ST", "OT"}


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
        if line.get("overtime_override") and type_key in st.session_state:
            live["hour_type"] = _normalize_alloc_hour_type(st.session_state[type_key])
            live["selected_time_type"] = _normalize_alloc_hour_type(st.session_state[type_key])
        elif _selected_time_type_from_line(line) == "AUTO":
            live["hour_type"] = _normalize_alloc_hour_type(line.get("final_time_type") or "ST")
            live["selected_time_type"] = "AUTO"
        elif line.get("final_time_type"):
            live["hour_type"] = _normalize_alloc_hour_type(line.get("final_time_type"))
            live["selected_time_type"] = _normalize_alloc_hour_type(line.get("final_time_type"))
        if hrs_key in st.session_state:
            live["hours"] = float(st.session_state[hrs_key] or 0)
        out.append(live)
    return out


def _get_day_allocation_state(
    day_total: float,
    allocations: list[dict[str, Any]],
    *,
    allocation_is_source: bool = False,
) -> dict[str, Any]:
    line_total = 0.0
    allocated_total = 0.0
    allocated_st = 0.0
    allocated_ot = 0.0
    placeholder_hours = 0.0

    for row in allocations or []:
        hours = _line_allocated_hours(row)
        if hours <= _ALLOC_TOLERANCE:
            continue
        line_total += hours
        if not _allocation_line_has_valid_assignment(row):
            placeholder_hours += hours
            continue
        if not _allocation_line_hour_type_valid(row, hours):
            placeholder_hours += hours
            continue
        allocated_total += hours
        if _normalize_alloc_hour_type(row.get("final_time_type") or row.get("hour_type")) == "OT":
            allocated_ot += hours
        else:
            allocated_st += hours

    has_invalid_assignment = placeholder_hours > _ALLOC_TOLERANCE
    if allocation_is_source:
        remaining = 0.0
        effective_total = line_total
        if line_total <= _ALLOC_TOLERANCE:
            state = "no_hours"
        elif has_invalid_assignment:
            state = "needs_assignment"
        elif allocated_total > _ALLOC_TOLERANCE:
            state = "complete"
        else:
            state = "incomplete"
    else:
        effective_total = float(day_total or 0)
        remaining = effective_total - allocated_total
        if day_total <= _ALLOC_TOLERANCE:
            state = "no_hours"
        elif line_total - day_total > _ALLOC_TOLERANCE:
            state = "overallocated"
        elif (
            abs(remaining) <= _ALLOC_TOLERANCE
            and allocated_total > _ALLOC_TOLERANCE
            and not has_invalid_assignment
        ):
            state = "complete"
        elif has_invalid_assignment:
            state = "needs_assignment"
        else:
            state = "incomplete"

    return {
        "state": state,
        "allocated_total": allocated_total,
        "allocated_st": allocated_st,
        "allocated_ot": allocated_ot,
        "remaining": remaining,
        "line_total": line_total,
        "effective_total": effective_total,
        "has_invalid_assignment": has_invalid_assignment,
        "placeholder_hours": placeholder_hours,
    }


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
    eid: str = "",
    week_sig: str = "",
) -> list[dict[str, Any]]:
    lines = list(by_date.get(iso) or [])
    if daily_total > 0 and not lines:
        lines.append(
            _new_allocation_line(
                job=_default_allocation_job(grid_row, job_opts),
                hours=daily_total,
                status=_normalize_timecard_status(grid_row.get("status")),
            )
        )
    elif len(lines) == 1 and daily_total > 0:
        only = dict(lines[0])
        if float(only.get("hours") or 0) <= 0:
            only["hours"] = daily_total
        lines = [only]
    by_date[iso] = lines
    return lines


def _bootstrap_week_allocation_lines(
    by_date: dict[str, list[dict[str, Any]]],
    *,
    week_start_d: date,
    source_grid: list[dict],
    job_opts: list[str],
    eid: str,
    week_sig: str,
) -> None:
    """Ensure allocation rows exist for every day that has top-row hours."""
    for day_ix, day_d in enumerate(week_dates(week_start_d)):
        iso = day_d.isoformat()
        grid_row = source_grid[day_ix] if day_ix < len(source_grid) else {}
        daily_total = _daily_total_from_list_row(
            eid=eid,
            week_sig=week_sig,
            day_ix=day_ix,
            grid_row=grid_row,
        )
        if daily_total > _ALLOC_TOLERANCE:
            _ensure_day_allocation_lines(
                by_date,
                iso=iso,
                daily_total=daily_total,
                grid_row=grid_row,
                job_opts=job_opts,
                eid=eid,
                week_sig=week_sig,
            )


def _grid_only_persist_row(
    *,
    day_d: date,
    iso: str,
    grid_row: dict,
    daily_total: float,
    no_job: str,
) -> dict[str, Any]:
    """Persist one day from the top-row total when not running full allocation validation."""
    day_id = str(grid_row.get("day_id") or "").strip()
    st_h = float(grid_row.get("st") or 0)
    ot_h = float(grid_row.get("ot") or 0)
    dt_h = float(grid_row.get("dt") or 0)
    if daily_total > _ALLOC_TOLERANCE and st_h + ot_h + dt_h <= _ALLOC_TOLERANCE:
        st_h = daily_total
        ot_h = 0.0
        dt_h = 0.0
    return {
        "day_id": day_id,
        "day": day_d.strftime("%A"),
        "date": iso,
        "job": str(grid_row.get("job") or no_job),
        "st": st_h,
        "ot": ot_h,
        "dt": dt_h,
        "notes": str(grid_row.get("notes") or ""),
        "status": str(grid_row.get("status") or "Draft"),
    }


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
                raw_pick = str(st.session_state[type_key] or "").strip()
                if raw_pick == "Auto":
                    line["selected_time_type"] = "AUTO"
                    line["overtime_override"] = False
                elif line.get("overtime_override") or raw_pick in {"S/T", "O/T"}:
                    picked = _normalize_alloc_hour_type(raw_pick)
                    line["selected_time_type"] = picked
                    line["hour_type"] = picked
                    line["final_time_type"] = picked
                    line["overtime_override"] = True
            if hrs_key in st.session_state:
                line["hours"] = float(st.session_state[hrs_key] or 0)
            if notes_key in st.session_state:
                line["notes"] = st.session_state[notes_key]


def _alloc_autosave_status_key(eid: str, iso: str) -> str:
    return f"tk_alloc_autosave_{eid}_{iso}"


def _set_alloc_autosave_status(eid: str, iso: str, status: str) -> None:
    st.session_state[_alloc_autosave_status_key(eid, iso)] = str(status or "").strip()


def _alloc_autosave_status_html(eid: str, iso: str) -> str:
    status = str(st.session_state.get(_alloc_autosave_status_key(eid, iso)) or "").strip().lower()
    if status == "saving":
        return (
            '<span class="timekeeping-alloc-autosave-status '
            'timekeeping-alloc-autosave-saving">Saving...</span>'
        )
    if status == "saved":
        return (
            '<span class="timekeeping-alloc-autosave-status '
            'timekeeping-alloc-autosave-saved">Saved</span>'
        )
    if status == "unsaved":
        return (
            '<span class="timekeeping-alloc-autosave-status '
            'timekeeping-alloc-autosave-unsaved">Unsaved changes</span>'
        )
    return ""


def _mark_allocation_dirty(emp: dict, week_start_d: date, iso: str) -> None:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    wd = str(iso or "")[:10]
    if not eid or not wd:
        return
    _set_alloc_autosave_status(eid, wd, "unsaved")


def _save_allocation_day(emp: dict, week_start_d: date, iso: str) -> None:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    wd = str(iso or "")[:10]
    if not eid or not wd:
        return
    _set_alloc_autosave_status(eid, wd, "saving")
    ok, _msg = _save_allocation_week(
        emp,
        week_start_d,
        show_message=False,
        focus_iso=wd,
        allow_incomplete=True,
    )
    _set_alloc_autosave_status(eid, wd, "saved" if ok else "unsaved")


def _allocation_lines_to_persist_grid(
    by_date: dict[str, list[dict[str, Any]]],
    *,
    week_start_d: date,
    eid: str,
    week_sig: str,
    source_grid: list[dict],
    focus_iso: str | None = None,
    allow_incomplete: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Flatten allocation lines for persist_timekeeping_days; auto-fill unassigned remainder."""
    errors: list[str] = []
    persist_rows: list[dict[str, Any]] = []
    job_opts = _assignment_options_for_timekeeping(week_start_d=week_start_d)
    no_job = job_opts[0] if job_opts else "— No assignment —"
    focus = str(focus_iso or "")[:10] or None

    for day_ix, day_d in enumerate(week_dates(week_start_d)):
        iso = day_d.isoformat()
        grid_row = source_grid[day_ix] if day_ix < len(source_grid) else {}
        if focus and iso != focus:
            continue
        lines = list(by_date.get(iso) or [])
        allocation_is_source = bool(focus and iso == focus)
        if allocation_is_source:
            lines = _live_allocation_lines_for_day(
                lines,
                eid=eid,
                week_sig=week_sig,
                iso=iso,
            )
            daily_total = _daily_total_from_allocation_lines(lines)
        else:
            daily_total = _daily_total_from_list_row(
                eid=eid,
                week_sig=week_sig,
                day_ix=day_ix,
                grid_row=grid_row,
            )
        if daily_total <= 0:
            day_id = str(grid_row.get("day_id") or "").strip()
            if not day_id:
                for line in lines:
                    lid = str(line.get("line_id") or "").strip()
                    if lid:
                        day_id = lid
                        break
            persist_rows.append(
                {
                    "day_id": day_id,
                    "day": day_d.strftime("%A"),
                    "date": iso,
                    "job": str(grid_row.get("job") or no_job),
                    "st": 0.0,
                    "ot": 0.0,
                    "dt": 0.0,
                    "notes": str(grid_row.get("notes") or ""),
                    "status": str(grid_row.get("status") or "Draft"),
                }
            )
            by_date[iso] = []
            continue
        if not lines:
            errors.append(f"{day_d.strftime('%A')}: add at least one assignment row.")
            continue
        line_total = _allocated_hours_sum(lines)
        valid_allocated = _valid_allocated_hours_sum(lines)
        placeholder_hours = sum(
            _line_allocated_hours(line)
            for line in lines
            if not _allocation_line_has_valid_assignment(line)
        )
        if placeholder_hours > _ALLOC_TOLERANCE:
            errors.append(
                f"{day_d.strftime('%A')}: select a valid assignment — "
                f"— No assignment — does not count as allocated time."
            )
            continue
        if not allocation_is_source and line_total > daily_total + 0.01:
            errors.append(
                f"{day_d.strftime('%A')}: allocated {_fmt_day_hours(line_total)} exceeds "
                f"{_fmt_day_hours(daily_total)} entered in the row above."
            )
            continue
        remainder = round(daily_total - valid_allocated, 2)
        if not allocation_is_source and remainder > 0.01 and not allow_incomplete:
            errors.append(
                f"{day_d.strftime('%A')}: assign the remaining "
                f"{_fmt_day_hours(remainder)} to a job, subjob, Shop, Administrative, or Vacation."
            )
            continue
        out_lines = [dict(line) for line in lines]
        merged: dict[tuple[str, str], dict[str, Any]] = {}
        for line in out_lines:
            hrs = _line_allocated_hours(line)
            if hrs <= 0:
                continue
            job_label = _coerce_assignment_label(str(line.get("job") or no_job), job_opts)
            line["job"] = job_label
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
            if _normalize_alloc_hour_type(line.get("final_time_type") or line.get("hour_type")) == "OT":
                bucket["ot"] = float(bucket["ot"]) + hrs
            else:
                bucket["st"] = float(bucket["st"]) + hrs
            if line.get("overtime_override"):
                bucket["overtime_override"] = True
                bucket["overtime_override_by"] = line.get("overtime_override_by")
                bucket["overtime_override_at"] = line.get("overtime_override_at")
                bucket["overtime_override_reason"] = line.get("overtime_override_reason")
            calc = str(line.get("calculated_time_type") or "").strip()
            if calc:
                bucket["calculated_time_type"] = calc
            final = _normalize_alloc_hour_type(line.get("final_time_type") or line.get("hour_type"))
            bucket["final_time_type"] = final
        for bucket in merged.values():
            if float(bucket.get("st") or 0) > 0 and float(bucket.get("ot") or 0) > 0:
                bucket["final_time_type"] = "MIXED"
                bucket["calculated_time_type"] = bucket.get("calculated_time_type") or "MIXED"
        persist_rows.extend(merged.values())
    return persist_rows, errors


def _save_allocation_week(
    emp: dict,
    week_start_d: date,
    *,
    show_message: bool = True,
    focus_iso: str | None = None,
    allow_incomplete: bool = False,
) -> tuple[bool, str]:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    week_sig = week_start_d.isoformat()
    focus = str(focus_iso or "")[:10] or None
    by_date = _ensure_allocation_state(emp, week_start_d)
    _sync_allocation_from_widgets(by_date, eid=eid, week_sig=week_sig)
    grid = _ensure_weekly_grid(emp, week_start_d)
    _apply_row_hrs_to_grid(grid, eid=eid, week_sig=week_sig)
    job_opts = _assignment_options_for_timekeeping(week_start_d=week_start_d)
    _bootstrap_week_allocation_lines(
        by_date,
        week_start_d=week_start_d,
        source_grid=grid,
        job_opts=job_opts,
        eid=eid,
        week_sig=week_sig,
    )
    by_date = _recalculate_week_overtime(by_date, week_start_d)
    st.session_state[_alloc_state_key(eid)] = by_date
    if focus and not allow_incomplete:
        day_ix = next(
            (i for i, day_d in enumerate(week_dates(week_start_d)) if day_d.isoformat() == focus),
            -1,
        )
        if day_ix < 0:
            return False, "Invalid work date for this week."
        grid_row = grid[day_ix] if day_ix < len(grid) else {}
        lines = _live_allocation_lines_for_day(
            list(by_date.get(focus) or []),
            eid=eid,
            week_sig=week_sig,
            iso=focus,
        )
        daily_total = _daily_total_from_allocation_lines(lines)
        if daily_total <= _ALLOC_TOLERANCE:
            return False, "Enter hours for this day before submitting."
        alloc_state = _get_day_allocation_state(
            daily_total,
            lines,
            allocation_is_source=True,
        )
        state = str(alloc_state.get("state") or "")
        if state == "needs_assignment":
            return False, "Select a valid assignment for all hours — — No assignment — is not allowed."
        if state != "complete":
            return False, "Enter hours and assign them to valid jobs before submitting."
    persist_rows, errors = _allocation_lines_to_persist_grid(
        by_date,
        week_start_d=week_start_d,
        eid=eid,
        week_sig=week_sig,
        source_grid=grid,
        focus_iso=focus,
        allow_incomplete=allow_incomplete,
    )
    if errors:
        if show_message:
            for err in errors[:3]:
                st.error(err)
        return False, errors[0]
    if not persist_rows:
        if allow_incomplete:
            return True, ""
        if show_message:
            st.info("Enter daily hours in the row above, then assign them here.")
        return False, "Enter daily hours in the row above, then assign them here."
    if focus:
        for row in persist_rows:
            row["status"] = "Draft"
    ok, msg = persist_timekeeping_days(
        eid, week_start_d, persist_rows, only_work_date=focus
    )
    if ok:
        _invalidate_weekly_grid(emp, week_start_d)
        st.session_state[_grid_key(eid)] = load_timekeeping_grid(eid, week_start_d)
        st.session_state[f"{_grid_key(eid)}_week"] = week_sig
        if show_message:
            st.success(msg or "Allocations saved.")
        return True, msg or "Allocations saved."
    err = msg or "Could not save allocations."
    if show_message:
        st.warning(err)
    return False, err


def _resolve_saved_allocation_line_id(
    employee_id: str,
    week_start_d: date,
    work_date: str,
    line: dict[str, Any],
) -> str:
    """Find persisted day-row id for an allocation line after save."""
    wd = str(work_date or "")[:10]
    if not wd:
        return ""
    job_opts = _assignment_options_for_timekeeping(week_start_d=week_start_d)
    job = _coerce_assignment_label(str(line.get("job") or ""), job_opts)
    hrs = _line_allocated_hours(line)
    if hrs <= _ALLOC_TOLERANCE:
        return ""
    hour_type = _normalize_alloc_hour_type(line.get("hour_type"))
    from app.services.timekeeping_service import list_timekeeping_days
    for row in list_timekeeping_days(employee_id, week_start_d):
        if str(row.get("work_date") or "")[:10] != wd:
            continue
        row_job = _coerce_assignment_label(str(row.get("job_label") or ""), job_opts)
        if row_job != job:
            continue
        st_h = float(row.get("st_hours") or 0)
        ot_h = float(row.get("ot_hours") or 0) + float(row.get("dt_hours") or 0)
        if hour_type == "OT":
            if abs(ot_h - hrs) <= 0.02:
                return str(row.get("id") or "").strip()
        elif abs(st_h - hrs) <= 0.02 and ot_h <= 0.02:
            return str(row.get("id") or "").strip()
    return ""


def _handle_alloc_line_submit(
    emp: dict,
    week_start_d: date,
    day_id: str,
    work_date: str,
    line: dict[str, Any],
) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    wd = str(work_date or "")[:10]
    if not wd:
        st.error("Missing work date.")
        return False
    saved, save_msg = _save_allocation_week(
        emp, week_start_d, show_message=False, focus_iso=wd
    )
    if not saved:
        st.error(save_msg or "Could not save hours for this day.")
        return False
    if not day_id:
        day_id = _resolve_saved_allocation_line_id(eid, week_start_d, wd, line)
    if not day_id:
        ok, msg = persist_timekeeping_day_submit_for_date(eid, week_start_d, wd)
        if ok:
            _invalidate_weekly_grid(emp, week_start_d)
            _patch_timecard_cache(emp, week_start_d, {"status": "Pending"})
            st.success(msg)
            return True
        st.error(msg)
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
    normalized = normalize_date(raw)
    if normalized is not None:
        if normalized != raw:
            st.session_state[_WEEK_KEY] = normalized
        return normalized
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


def _fmt_list_summary_hours(val: object) -> str:
    """Compact list-row totals (whole hours without trailing zeros)."""
    try:
        num = float(val)
        if abs(num - round(num)) < 0.001:
            return str(int(round(num)))
        text = f"{num:.1f}".rstrip("0").rstrip(".")
        return text or "0"
    except (TypeError, ValueError):
        return "0"


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
    return not _is_placeholder_assignment(day_row.get("job"))


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
    hrs_key = _weekly_hours_widget_key(eid, str(row.get("date") or "")[:10] or week_sig)
    legacy_key = _legacy_hours_widget_key(eid, week_sig, index)
    if hrs_key in st.session_state:
        merged = dict(merged)
        _set_day_job_hours(merged, float(st.session_state[hrs_key] or 0))
    elif legacy_key in st.session_state:
        merged = dict(merged)
        _set_day_job_hours(merged, float(st.session_state[legacy_key] or 0))
    return merged


def _sync_row_hrs_from_grid(grid: list[dict], *, eid: str, week_sig: str) -> None:
    """Merge ST/OT widget edits into the grid without writing tk_hrs widget keys."""
    for i, row in enumerate(grid):
        st_key = f"tk_st_{eid}_{week_sig}_{i}"
        ot_key = f"tk_ot_{eid}_{week_sig}_{i}"
        if st_key in st.session_state or ot_key in st.session_state:
            if st_key in st.session_state:
                row["st"] = float(st.session_state[st_key] or 0)
            if ot_key in st.session_state:
                row["ot"] = float(st.session_state[ot_key] or 0)
            _set_day_job_hours(row, _day_hours_total(row))


def _apply_row_hrs_to_grid(grid: list[dict], *, eid: str, week_sig: str) -> None:
    """Apply inline day-box hour inputs to the weekly grid."""
    for i, row in enumerate(grid):
        _apply_hours_widget_to_row(row, eid=eid, week_sig=week_sig, day_ix=i)


def _hour_pending_autosave_key(eid: str, week_sig: str, day_ix: int) -> str:
    return f"tk_hrs_pending_{eid}_{week_sig}_{day_ix}"


def _hour_flushed_autosave_key(eid: str, week_sig: str, day_ix: int) -> str:
    return f"tk_hrs_flushed_{eid}_{week_sig}_{day_ix}"


def _hour_save_status_key(eid: str, week_sig: str, day_ix: int) -> str:
    return f"tk_hrs_save_status_{eid}_{week_sig}_{day_ix}"


def hour_autosave_is_due(
    *,
    pending_at: float,
    flushed_at: float,
    now: float,
    debounce_sec: float = _TK_HOUR_AUTOSAVE_DEBOUNCE_SEC,
) -> bool:
    """True when a debounced autosave should run for a pending hour edit."""
    if pending_at <= 0:
        return False
    if pending_at <= flushed_at:
        return False
    return (now - pending_at) >= debounce_sec


def _set_hour_save_status(eid: str, week_sig: str, day_ix: int, status: str) -> None:
    st.session_state[_hour_save_status_key(eid, week_sig, day_ix)] = str(status or "").strip()


def _hour_save_status_html(eid: str, week_sig: str, day_ix: int) -> str:
    status = str(
        st.session_state.get(_hour_save_status_key(eid, week_sig, day_ix)) or ""
    ).strip().lower()
    if status == "saving":
        return (
            '<span class="timekeeping-hour-save-indicator timekeeping-hour-save-saving" '
            'title="Saving hours">Saving…</span>'
        )
    if status == "saved":
        return (
            '<span class="timekeeping-hour-save-indicator timekeeping-hour-save-saved" '
            'title="Hours saved">Saved</span>'
        )
    if status == "error":
        return (
            '<span class="timekeeping-hour-save-indicator timekeeping-hour-save-error" '
            'title="Could not save hours">Save failed</span>'
        )
    if status == "pending":
        return (
            '<span class="timekeeping-hour-save-indicator timekeeping-hour-save-pending" '
            'title="Will save shortly">…</span>'
        )
    return ""


def _mark_hour_pending_autosave(eid: str, week_sig: str, day_ix: int) -> None:
    st.session_state[_hour_pending_autosave_key(eid, week_sig, day_ix)] = time.monotonic()
    _set_hour_save_status(eid, week_sig, day_ix, "pending")


def _sync_hour_widget_to_grid(
    grid: list[dict],
    *,
    eid: str,
    week_sig: str,
    day_ix: int,
) -> None:
    if day_ix < 0 or day_ix >= len(grid):
        return
    _apply_hours_widget_to_row(grid[day_ix], eid=eid, week_sig=week_sig, day_ix=day_ix)


def _refresh_grid_day_id_from_db(
    grid: list[dict],
    *,
    eid: str,
    week_start_d: date,
    day_ix: int,
    work_date: str,
) -> None:
    if day_ix < 0 or day_ix >= len(grid):
        return
    from app.services.timekeeping_service import list_timekeeping_days
    for saved in list_timekeeping_days(eid, week_start_d):
        if str(saved.get("work_date") or "")[:10] == work_date:
            grid[day_ix]["day_id"] = str(saved.get("id") or grid[day_ix].get("day_id") or "")
            if saved.get("status"):
                grid[day_ix]["status"] = _normalize_timecard_status(saved.get("status"))
            break


def _autosave_employee_day_hours(
    emp: dict,
    week_start_d: date,
    day_ix: int,
) -> tuple[bool, str]:
    """Persist one list-row day without invalidating the in-memory weekly grid."""
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    if not eid:
        return False, "Missing employee id."
    week_sig = week_start_d.isoformat()
    grid = _ensure_weekly_grid(emp, week_start_d)
    grid = _sync_grid_from_widget_keys(grid, eid=eid, week_sig=week_sig)
    if day_ix < 0 or day_ix >= len(grid):
        return False, "Invalid work day."
    day_row = grid[day_ix]
    day_status = _normalize_timecard_status(day_row.get("status"))
    week_status = _week_status_from_grid(grid)
    if not _day_hours_editable(day_status, week_status):
        return False, "This day is locked."
    work_date = str(day_row.get("date") or "")[:10]
    if not work_date:
        return False, "Missing work date."
    st.session_state[_grid_key(eid)] = grid
    ok, msg = persist_timekeeping_days(eid, week_start_d, grid, only_work_date=work_date)
    if ok:
        st_total, ot_total, total_hours = _row_totals_from_grid(grid)
        _patch_timecard_cache(
            emp,
            week_start_d,
            {
                "st_total": st_total,
                "ot_total": ot_total,
                "total_hours": total_hours,
                "status": _week_status_from_grid(grid),
            },
        )
        _refresh_grid_day_id_from_db(
            grid,
            eid=eid,
            week_start_d=week_start_d,
            day_ix=day_ix,
            work_date=work_date,
        )
        st.session_state[_grid_key(eid)] = grid
    return ok, msg or ""


def _employee_has_pending_hour_autosave(eid: str, week_sig: str) -> bool:
    if not eid:
        return False
    for day_ix in range(7):
        pending_at = float(
            st.session_state.get(_hour_pending_autosave_key(eid, week_sig, day_ix)) or 0
        )
        flushed_at = float(
            st.session_state.get(_hour_flushed_autosave_key(eid, week_sig, day_ix)) or 0
        )
        if pending_at > 0 and pending_at > flushed_at:
            return True
    return False


def _flush_debounced_hour_autosaves(emp: dict, week_start_d: date) -> None:
    """Background-save pending hour edits for one employee row."""
    if not _can_submit_timekeeping():
        return
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    if not eid:
        return
    week_sig = week_start_d.isoformat()
    now = time.monotonic()
    for day_ix in range(7):
        pending_at = float(st.session_state.get(_hour_pending_autosave_key(eid, week_sig, day_ix)) or 0)
        flushed_at = float(st.session_state.get(_hour_flushed_autosave_key(eid, week_sig, day_ix)) or 0)
        if not hour_autosave_is_due(pending_at=pending_at, flushed_at=flushed_at, now=now):
            continue
        _set_hour_save_status(eid, week_sig, day_ix, "saving")
        ok, _msg = _autosave_employee_day_hours(emp, week_start_d, day_ix)
        st.session_state[_hour_flushed_autosave_key(eid, week_sig, day_ix)] = pending_at
        if ok:
            _set_hour_save_status(eid, week_sig, day_ix, "saved")
        else:
            _set_hour_save_status(eid, week_sig, day_ix, "error")


def _on_list_row_hour_changed(
    emp_id: str,
    week_sig: str,
    day_ix: int,
) -> None:
    """Optimistic session update when a list-row hour widget changes."""
    grid_key = _grid_key(emp_id)
    grid = st.session_state.get(grid_key)
    if isinstance(grid, list):
        _sync_hour_widget_to_grid(grid, eid=emp_id, week_sig=week_sig, day_ix=day_ix)
        st.session_state[grid_key] = grid
    _mark_hour_pending_autosave(emp_id, week_sig, day_ix)


def _bump_list_row_hours(
    widget_key: str,
    *,
    step: float,
    direction: int,
    fallback: float,
    emp_id: str,
    week_sig: str,
    day_ix: int,
    max_value: float = 24.0,
    decimals: int = 1,
) -> None:
    _bump_streamlit_hours(
        widget_key,
        step=step,
        direction=direction,
        fallback=fallback,
        max_value=max_value,
        decimals=decimals,
    )
    _on_list_row_hour_changed(emp_id, week_sig, day_ix)


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


def _bump_streamlit_hours(
    widget_key: str,
    *,
    step: float,
    direction: int,
    fallback: float,
    max_value: float = 24.0,
    decimals: int = 1,
) -> None:
    """Button callback: adjust a number_input key before the widget renders."""
    cur = float(st.session_state.get(widget_key, fallback))
    if direction > 0:
        st.session_state[widget_key] = min(max_value, round(cur + step, decimals))
    else:
        st.session_state[widget_key] = max(0.0, round(cur - step, decimals))


def _render_list_day_hour_input(
    *,
    value: float,
    emp_id: str,
    work_date: date,
    day_label: str,
    week_sig: str,
    day_ix: int,
    hour_autosave: bool = False,
) -> float:
    """List view: compact centered number_input (no separate arrow buttons)."""
    widget_key = _weekly_hours_widget_key(emp_id, work_date)
    legacy_key = _legacy_hours_widget_key(emp_id, week_sig, day_ix)
    if widget_key not in st.session_state and legacy_key in st.session_state:
        st.session_state[widget_key] = float(st.session_state[legacy_key] or 0)

    with st.container(key=f"tk_list_hrs_{emp_id}_{work_date.isoformat()}"):
        st.markdown(
            '<span class="day-summary-input-marker timekeeping-hour-input-marker '
            'timekeeping-list-daily-hour-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        hour_kwargs: dict[str, Any] = {
            "label": f"{day_label} hours",
            "value": float(value),
            "key": widget_key,
            "label_visibility": "collapsed",
            "step": _LIST_VIEW_HOUR_STEP,
            "min_value": 0.0,
            "max_value": 24.0,
            "format": "%.1f",
        }
        if hour_autosave and emp_id and week_sig:
            hour_kwargs["on_change"] = _on_list_row_hour_changed
            hour_kwargs["args"] = (emp_id, week_sig, day_ix)
        return max(0.0, float(st.number_input(**hour_kwargs)))


def _render_list_day_hour_stepper(
    *,
    value: float,
    widget_key: str,
    day_label: str,
    alloc_state: str = "",
    day_status: str = "Draft",
    emp_id: str = "",
    week_sig: str = "",
    day_ix: int = 0,
    hour_autosave: bool = False,
) -> float:
    """List view: centered hour input with a compact ▲/▼ button strip."""
    step = _LIST_VIEW_HOUR_STEP
    down_key = f"{widget_key}_dn"
    up_key = f"{widget_key}_up"
    spin_key = f"tk_list_hour_spin_{widget_key}"
    norm = _normalize_timecard_status(day_status)
    if _day_fully_approved_and_allocated(alloc_state, day_status):
        spin_marker_cls = " timekeeping-list-hour-spin-approved-complete"
    elif norm == "Draft":
        spin_marker_cls = _top_row_hour_spin_marker_class(alloc_state) + _day_approval_spin_marker_class(day_status)
    else:
        spin_marker_cls = _day_approval_spin_marker_class(day_status)

    with st.container(key=spin_key):
        st.markdown(
            f'<span class="timekeeping-list-hour-spinner-marker timekeeping-hour-spinner-marker{spin_marker_cls}" '
            f'aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        inp_col, btns_col = st.columns([72, 28], gap="xxsmall", vertical_alignment="center")
        bump_kwargs = {
            "widget_key": widget_key,
            "step": step,
            "fallback": float(value),
            "max_value": 24.0,
            "decimals": 1,
            "emp_id": emp_id,
            "week_sig": week_sig,
            "day_ix": day_ix,
        }
        with inp_col:
            st.markdown(
                '<span class="timekeeping-hour-input-marker timekeeping-list-daily-hour-marker" '
                'aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            hour_kwargs: dict[str, Any] = {
                "label": f"{day_label} hours",
                "value": float(value),
                "key": widget_key,
                "label_visibility": "collapsed",
                "step": step,
                "min_value": 0.0,
                "max_value": 24.0,
                "format": "%.1f",
            }
            if hour_autosave and emp_id and week_sig:
                hour_kwargs["on_change"] = _on_list_row_hour_changed
                hour_kwargs["args"] = (emp_id, week_sig, day_ix)
            hours = st.number_input(**hour_kwargs)
        with btns_col:
            st.markdown(
                '<span class="timekeeping-spinner-buttons-marker" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            if hour_autosave and emp_id and week_sig:
                st.button(
                    "▲",
                    key=up_key,
                    use_container_width=False,
                    help=f"Increase {day_label} hours",
                    on_click=_bump_list_row_hours,
                    kwargs={**bump_kwargs, "direction": 1},
                )
                st.button(
                    "▼",
                    key=down_key,
                    use_container_width=False,
                    help=f"Decrease {day_label} hours",
                    on_click=_bump_list_row_hours,
                    kwargs={**bump_kwargs, "direction": -1},
                )
            else:
                st.button(
                    "▲",
                    key=up_key,
                    use_container_width=False,
                    help=f"Increase {day_label} hours",
                    on_click=_bump_streamlit_hours,
                    kwargs={
                        "widget_key": widget_key,
                        "step": step,
                        "fallback": float(value),
                        "max_value": 24.0,
                        "decimals": 1,
                        "direction": 1,
                    },
                )
                st.button(
                    "▼",
                    key=down_key,
                    use_container_width=False,
                    help=f"Decrease {day_label} hours",
                    on_click=_bump_streamlit_hours,
                    kwargs={
                        "widget_key": widget_key,
                        "step": step,
                        "fallback": float(value),
                        "max_value": 24.0,
                        "decimals": 1,
                        "direction": -1,
                    },
                )
    return max(0.0, float(hours))


def _render_collapsed_list_day_cell(
    *,
    day_d: date,
    day_ix: int,
    day_row: dict,
) -> None:
    """Collapsed list row weekday column using native Streamlit widgets only."""
    day_status = _normalize_timecard_status(day_row.get("status"))
    total = _day_hours_total(day_row)
    day_title = f'{day_d.strftime("%a").upper()} {day_d.strftime("%m/%d")}'
    st.markdown(f"**{day_title}**")
    st.caption(_timecard_status_display(day_status).upper())
    weekend_cls = " timekeeping-collapsed-hour-weekend" if day_ix >= 5 else ""
    st.markdown(
        f'<div class="timekeeping-collapsed-hour-value{weekend_cls}">'
        f"{html.escape(_fmt_day_hours(total))}</div>",
        unsafe_allow_html=True,
    )


def _render_collapsed_list_summary_cell(*, label: str, value: str) -> None:
    """Collapsed list row summary column (ST, OT, Total, Status)."""
    st.markdown(
        f'<div class="timekeeping-summary-value" title="{html.escape(label)}">'
        f"<strong>{html.escape(value)}</strong></div>",
        unsafe_allow_html=True,
    )


def _render_modal_day_stats_box(
    *,
    allocated: float,
    remaining: float,
    st_total: float,
    ot_total: float,
    daily_total: float,
    show_remaining: bool = True,
) -> None:
    """Right-side allocation summary box in the day editor modal."""
    st.markdown(
        '<span class="timekeeping-modal-stats-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    stats = [
        ("Total Hours", _fmt_day_hours(daily_total)),
        ("S/T Total", _fmt_day_hours(st_total)),
        ("O/T Total", _fmt_day_hours(ot_total)),
    ]
    if show_remaining:
        stats = [
            ("Allocated", _fmt_day_hours(allocated)),
            ("Remaining", _fmt_day_hours(remaining)),
            *stats[1:],
            ("Daily Total", _fmt_day_hours(daily_total)),
        ]
    cells = "".join(
        f'<div class="timekeeping-modal-stat">'
        f'<span class="timekeeping-modal-stat-label">{html.escape(label)}</span>'
        f'<span class="timekeeping-modal-stat-value">{html.escape(val)}</span>'
        f"</div>"
        for label, val in stats
    )
    st.markdown(
        f'<div class="timekeeping-modal-stats-box">{cells}</div>',
        unsafe_allow_html=True,
    )


def _render_weekly_timekeeping_toolbar(week_start_d: date, week_end_d: date) -> None:
    """Week navigation row and helper text matching the weekly mockup."""
    st.markdown(
        '<span class="ips-timekeeping-week-toolbar-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    week_label = f"Week of {fmt_date(week_start_d)} – {fmt_date(week_end_d)}"
    with st.container(key="tk_week_range"):
        with st.popover(week_label, help="Pick a date to jump to that week", use_container_width=True):
            picked = st.date_input(
                "Jump to week",
                value=week_start_d,
                key="tk_week_range_picker",
                label_visibility="collapsed",
                format=DATE_INPUT_FORMAT,
            )
    if isinstance(picked, date):
        new_start = week_start(picked)
        if new_start != week_start_d:
            st.session_state[_WEEK_KEY] = new_start
            reset_table_page(_TABLE_KEY)
            _clear_expanded_timecard()
            _clear_day_time_selection()
            clear_timekeeping_list_caches()
            st.rerun()
    st.markdown(
        '<p class="ips-timekeeping-week-helper">Click any day\'s hours to view or edit details.</p>',
        unsafe_allow_html=True,
    )


def _list_row_day_cell_readonly_html(
    *,
    day_d: date,
    day_ix: int,
    day_row: dict,
) -> str:
    """HTML for a collapsed list day cell (label, status, hours stacked)."""
    day_status = _normalize_timecard_status(day_row.get("status"))
    total = _day_hours_total(day_row)
    has_hours = total > _ALLOC_TOLERANCE
    filled_marker = _list_day_box_marker_classes(
        day_status=day_status,
        alloc_state="",
        has_hours=has_hours,
    )
    grid_marker = " timesheet-list-days-marker" if day_ix == 0 else ""
    status_text = html.escape(_timecard_status_display(day_status).upper())
    day_title = f'{day_d.strftime("%a").upper()} {day_d.strftime("%m/%d")}'
    hours_cls = "timesheet-day-hours timekeeping-hour-input-ro timekeeping-list-hour-value"
    hours_cls += _day_approval_ro_hour_class(day_status)
    return (
        f'<span class="timesheet-list-day-marker day-block-marker timekeeping-day-cell-marker{grid_marker}{filled_marker}" '
        f'aria-hidden="true"></span>'
        f'<div class="timesheet-day-cell">'
        f'<div class="timesheet-day-label">{html.escape(day_title)}</div>'
        f'<div class="timesheet-day-status">{status_text}</div>'
        f'<div class="{hours_cls}">{html.escape(_fmt_day_hours(total))}</div>'
        f"</div>"
    )


def _render_list_row_day_cell_readonly(
    *,
    day_d: date,
    day_ix: int,
    day_row: dict,
) -> None:
    """Collapsed list row: markdown-only day cell (no hour widgets)."""
    _render_timekeeping_inline_html(
        _list_row_day_cell_readonly_html(day_d=day_d, day_ix=day_ix, day_row=day_row)
    )


def _render_list_row_summary_cell_readonly(
    *,
    label: str,
    value_html: str,
    value_class: str,
) -> None:
    """Collapsed list row summary column with tooltip label."""
    _render_timekeeping_inline_html(
        f'<div class="weekly-timecard-summary-cell timekeeping-list-summary-wrap" title="{html.escape(label)}">'
        f'<div class="{value_class} timesheet-list-summary-cell weekly-timecard-summary-value">'
        f"{value_html}</div>"
        f"</div>"
    )


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
    """Expanded summary row: stacked day label, date, and hour input."""
    day_status = _normalize_timecard_status(day_row.get("status"))
    total = _day_hours_total(day_row)
    has_hours = total > _ALLOC_TOLERANCE
    filled_marker = _list_day_box_marker_classes(
        day_status=day_status,
        alloc_state=_list_day_allocation_state(
            eid=emp_id,
            week_sig=week_sig,
            day_ix=day_ix,
            day_d=day_d,
            grid_row=day_row,
            alloc_by_date=alloc_by_date,
        ),
        has_hours=has_hours,
    )
    grid_marker = " timesheet-list-days-marker" if day_ix == 0 else ""
    day_name = day_d.strftime("%a").upper()
    day_date = day_d.strftime("%m/%d")

    with st.container(key=f"tk_list_day_{emp_id}_{week_sig}_{day_ix}"):
        st.markdown(
            f'<span class="day-summary-cell day-summary-cell-marker timesheet-list-day-marker '
            f"day-block-marker timekeeping-day-cell-marker{grid_marker}{filled_marker}\" "
            f'aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**{day_name}**")
        st.caption(day_date)
        if editable:
            save_html = _hour_save_status_html(emp_id, week_sig, day_ix)
            if save_html:
                st.markdown(
                    f'<div class="timekeeping-hour-save-wrap">{save_html}</div>',
                    unsafe_allow_html=True,
                )
            hrs = _render_list_day_hour_input(
                value=total,
                emp_id=emp_id,
                work_date=day_d,
                day_label=day_d.strftime("%A"),
                week_sig=week_sig,
                day_ix=day_ix,
                hour_autosave=_can_submit_timekeeping(),
            )
            _set_day_job_hours(day_row, hrs)
            return hrs
        ro_cls = "timekeeping-hour-input timekeeping-hour-input-ro timekeeping-collapsed-hour-value"
        ro_cls += _day_approval_ro_hour_class(day_status)
        st.markdown(
            f'<div class="{ro_cls} timekeeping-list-hour-value">'
            f"{html.escape(_fmt_day_hours(total))}</div>",
            unsafe_allow_html=True,
        )
        return total


def _render_list_row_summary_cell(
    *,
    label: str,
    value_html: str,
    value_class: str,
    show_label: bool = True,
) -> None:
    """List row: optional summary label stacked above value (header row carries labels)."""
    label_html = (
        f'<div class="timekeeping-day-label timekeeping-summary-label">'
        f"{html.escape(label.upper())}</div>"
        if show_label
        else ""
    )
    st.markdown(
        f'<div class="timekeeping-day-cell timekeeping-list-summary-wrap">'
        f"{label_html}"
        f'<div class="{value_class} timesheet-list-summary-cell">'
        f"{value_html}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


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
    week_status = _week_status_from_grid(grid)
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
        editable = _day_hours_editable(day_status, week_status)
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
    """Apply in-flight list-row hour widgets before save or summary totals."""
    for i, row in enumerate(grid):
        _apply_hours_widget_to_row(row, eid=eid, week_sig=week_sig, day_ix=i)
        if _hours_widget_session_value(
            eid=eid,
            week_sig=week_sig,
            day_ix=i,
            work_date=str(row.get("date") or "")[:10] or week_sig,
        ) is not None:
            continue
        st_key = f"tk_st_{eid}_{week_sig}_{i}"
        ot_key = f"tk_ot_{eid}_{week_sig}_{i}"
        if st_key in st.session_state:
            row["st"] = float(st.session_state[st_key] or 0)
        if ot_key in st.session_state:
            row["ot"] = float(st.session_state[ot_key] or 0)
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
    bump_kwargs = {
        "widget_key": widget_key,
        "step": step,
        "fallback": float(value),
        "max_value": max_value,
        "decimals": 2,
    }
    with dn_col:
        st.button(
            down_label,
            key=down_key,
            use_container_width=True,
            help=f"Decrease {label}",
            on_click=_bump_streamlit_hours,
            kwargs={**bump_kwargs, "direction": -1},
        )
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
        st.button(
            up_label,
            key=up_key,
            use_container_width=True,
            help=f"Increase {label}",
            on_click=_bump_streamlit_hours,
            kwargs={**bump_kwargs, "direction": 1},
        )
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
        job_key = f"tk_job_{emp_id}_{week_sig}_{day_ix}"
        cur_job = _sync_assignment_job_widget(
            job_key,
            job_opts,
            str(day_row.get("job") or (job_opts[0] if job_opts else "— No assignment —")),
        )
        job_ix = _assignment_option_index(job_opts, cur_job)
        st.markdown(
            '<span class="weekly-timesheet-job-marker weekly-timesheet-job-select job-select" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        day_row["job"] = st.selectbox(
            "Assignment",
            job_opts,
            index=job_ix,
            key=job_key,
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
    if s in ("pending", "pending approval"):
        return "Pending"
    if s == "rejected":
        return "Rejected"
    return str(raw or "Draft").strip().title() or "Draft"


def _timecard_status_display(status: str) -> str:
    norm = _normalize_timecard_status(status)
    labels = {
        "Draft": "Draft",
        "Pending": "Pending Approval",
        "Approved": "Approved",
        "Rejected": "Rejected",
    }
    return labels.get(norm, norm)


def _timecard_status_pill_html(status: str, *, compact: bool = False) -> str:
    norm = _normalize_timecard_status(status)
    cls_map = {
        "Draft": "ips-timekeeping-status-draft",
        "Pending": "ips-timekeeping-status-pending",
        "Approved": "ips-timekeeping-status-approved",
        "Rejected": "ips-timekeeping-status-rejected",
    }
    cls = cls_map.get(norm, "ips-timekeeping-status-draft")
    compact_cls = " ips-timekeeping-status-pill-compact" if compact else ""
    return (
        f'<span class="ips-timekeeping-status-pill {cls}{compact_cls}">'
        f"{html.escape(_timecard_status_display(norm))}</span>"
    )


def _day_fully_approved_and_allocated(alloc_state: str, day_status: str) -> bool:
    from app.services.timekeeping_day_ui import day_fully_approved_and_allocated
    return day_fully_approved_and_allocated(alloc_state, day_status)


def _day_approval_marker_class(day_status: str, *, has_hours: bool, alloc_state: str = "") -> str:
    from app.services.timekeeping_day_ui import day_approval_marker_class
    return day_approval_marker_class(day_status, has_hours=has_hours, alloc_state=alloc_state)


def _list_day_box_marker_classes(
    *,
    day_status: str,
    alloc_state: str,
    has_hours: bool,
) -> str:
    from app.services.timekeeping_day_ui import list_day_box_marker_classes
    return list_day_box_marker_classes(
        day_status=day_status,
        alloc_state=alloc_state,
        has_hours=has_hours,
    )


def _list_day_status_badge_html(day_status: str, alloc_state: str) -> str:
    from app.services.timekeeping_day_ui import list_day_status_badge_html
    return list_day_status_badge_html(day_status, alloc_state)


def _day_approval_spin_marker_class(day_status: str) -> str:
    norm = _normalize_timecard_status(day_status)
    mapping = {
        "Draft": " timekeeping-list-hour-spin-draft",
        "Pending": " timekeeping-list-hour-spin-pending",
        "Approved": " timekeeping-list-hour-spin-approved",
        "Rejected": " timekeeping-list-hour-spin-rejected",
    }
    return mapping.get(norm, "")


def _day_approval_ro_hour_class(day_status: str) -> str:
    norm = _normalize_timecard_status(day_status)
    mapping = {
        "Draft": " timekeeping-list-hour-ro-draft",
        "Pending": " timekeeping-list-hour-ro-pending",
        "Approved": " timekeeping-list-hour-ro-approved",
        "Rejected": " timekeeping-list-hour-ro-rejected",
    }
    return mapping.get(norm, "")


def _timecard_id_for_row(row: dict, ws: date) -> str:
    eid = str(row.get("id") or row.get("employee_id") or "").strip()
    week_start_str = str(row.get("week_start") or ws.isoformat())[:10]
    return f"{eid}_{week_start_str}"


def _week_status_from_grid(grid: list[dict[str, Any]]) -> str:
    """Aggregate employee/week status from day-level statuses (not stale weekly summary)."""
    statuses: list[str] = []
    for day_row in grid:
        norm = _normalize_timecard_status(day_row.get("status"))
        if _row_has_hours(day_row) or norm in ("Approved", "Pending", "Rejected"):
            statuses.append(norm)
    if not statuses:
        return "Draft"
    if any(s == "Rejected" for s in statuses):
        return "Rejected"
    if any(s == "Pending" for s in statuses):
        return "Pending"
    if all(s == "Approved" for s in statuses):
        return "Approved"
    return "Draft"


def _resolved_week_status(
    emp: dict,
    week_start_d: date,
    *,
    grid: list[dict[str, Any]] | None = None,
) -> str:
    """Row status for display/actions — always derived from day grid when available."""
    if grid is not None:
        return _week_status_from_grid(grid)
    eid = str(emp.get("id") or emp.get("employee_id") or "").strip()
    if not eid:
        return _normalize_timecard_status(emp.get("status"))
    try:
        saved_rows = _day_rows_for_employee(eid, week_start_d)
        if saved_rows:
            loaded = build_timekeeping_grid_from_day_rows(eid, week_start_d, saved_rows)
            return _week_status_from_grid(loaded)
        loaded = load_timekeeping_grid(eid, week_start_d)
        if loaded:
            return _week_status_from_grid(loaded)
    except Exception:
        pass
    return _week_status_from_grid(_ensure_weekly_grid(emp, week_start_d))


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
        _prepare_timecard_detail_modal(timecard_id)
    elif st.session_state.get(SELECTED_TIMECARD_KEY) == timecard_id:
        st.session_state[SELECTED_TIMECARD_KEY] = None
        st.session_state[SHOW_TIMECARD_MODAL_KEY] = False


def _prepare_timecard_detail_modal(
    timecard_id: str,
    *,
    requested_tab: str | None = None,
) -> None:
    tid = str(timecard_id or "").strip()
    if not tid:
        return
    if requested_tab and requested_tab in _TIMEKEEPING_DETAIL_TABS:
        st.session_state[_TK_DETAIL_TAB_REQUEST_KEY] = requested_tab
    prev_tid = str(st.session_state.get(_TK_DETAIL_TAB_EMP_KEY) or "")
    if prev_tid and prev_tid != tid and not requested_tab:
        st.session_state[_TIMEKEEPING_DETAIL_TAB_KEY] = "Weekly Timecard"


def _timecard_detail_modal_pending() -> bool:
    return bool(
        st.session_state.get(SELECTED_TIMECARD_KEY)
        and st.session_state.get(SHOW_TIMECARD_MODAL_KEY)
    )


def _ensure_selected_timecard_modal_cache(week_start_d: date) -> bool:
    tid = str(st.session_state.get(SELECTED_TIMECARD_KEY) or "").strip()
    if not tid:
        return False
    cache = st.session_state.get(_CACHE_KEY)
    if isinstance(cache, dict) and isinstance(cache.get(tid), dict):
        return True
    summaries = _filter_summaries_for_field_user(load_timekeeping_summaries(week_start_d))
    for row in summaries:
        built = _build_timecard_row(row, week_start_d)
        if str(built.get("timecard_id") or "") == tid:
            st.session_state[_CACHE_KEY] = {tid: built}
            return True
    return False


def _sync_timekeeping_detail_tab(emp: dict) -> None:
    tid = str(
        st.session_state.get(SELECTED_TIMECARD_KEY)
        or st.session_state.get(_MODAL_KEY)
        or ""
    ).strip()
    eid = str(emp.get("employee_id") or emp.get("id") or "").strip()
    tab_key = tid or eid
    explicit = str(st.session_state.pop(_TK_DETAIL_TAB_REQUEST_KEY, "") or "").strip()
    prev = str(st.session_state.get(_TK_DETAIL_TAB_EMP_KEY) or "")
    if explicit in _TIMEKEEPING_DETAIL_TABS:
        st.session_state[_TIMEKEEPING_DETAIL_TAB_KEY] = explicit
    elif prev and tab_key and prev != tab_key:
        st.session_state[_TIMEKEEPING_DETAIL_TAB_KEY] = "Weekly Timecard"
    elif _TIMEKEEPING_DETAIL_TAB_KEY not in st.session_state:
        st.session_state[_TIMEKEEPING_DETAIL_TAB_KEY] = "Weekly Timecard"
    if tab_key:
        st.session_state[_TK_DETAIL_TAB_EMP_KEY] = tab_key


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
            saved_rows = _day_rows_for_employee(eid, week_start_d)
            if saved_rows:
                st.session_state[gk] = build_timekeeping_grid_from_day_rows(eid, week_start_d, saved_rows)
            else:
                st.session_state[gk] = default_weekly_grid(eid, week_start_d)
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


def _render_weekly_grid_edit(
    emp: dict,
    week_start_d: date,
    *,
    perms: TimekeepingPermissions | None = None,
) -> None:
    perms = perms or _timekeeping_permissions()
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    gk = _grid_key(eid)
    week_sig = week_start_d.isoformat()
    grid = _ensure_weekly_grid(emp, week_start_d)
    job_opts = _assignment_options_for_timekeeping(week_start_d=week_start_d)
    can_approve = perms.can_approve
    can_submit = perms.can_submit

    st.markdown(
        '<span class="ips-time-day-edit-marker timekeeping-detail-grid-marker timekeeping-detail-grid-edit" '
        'aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    grid = _sync_grid_from_widget_keys(grid, eid=eid, week_sig=week_sig)
    week_status = _week_status_from_grid(grid)

    edit_cols = _DAY_GRID_EDIT_COLS
    _render_day_grid_header(edit_mode=True)

    for i, row in enumerate(grid):
        day_status = _normalize_timecard_status(row.get("status"))
        row_editable = _day_hours_editable(day_status, week_status)
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
            job_key = f"tk_job_{eid}_{week_sig}_{i}"
            cur_job = _sync_assignment_job_widget(
                job_key,
                job_opts,
                str(live_row.get("job") or row.get("job") or job_opts[0]),
            )
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
                if can_submit and day_status in ("Draft", "Rejected") and st.button(
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
                fragment_rerun()
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
                fragment_rerun()
    st.session_state[gk] = grid


def _save_timekeeping_week(
    emp: dict,
    week_start_d: date,
    *,
    status: str | None = None,
    show_message: bool = True,
) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    week_sig = week_start_d.isoformat()
    grid = _ensure_weekly_grid(emp, week_start_d)
    grid = _sync_grid_from_widget_keys(grid, eid=eid, week_sig=week_sig)
    st.session_state[_grid_key(eid)] = grid
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


def _render_list_allocation_detail(
    emp: dict,
    week_start_d: date,
    *,
    panel_scope: str = "",
) -> None:
    """List expand: assign hours entered in the top row to jobs/tasks/shop/admin."""
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    week_sig = week_start_d.isoformat()
    scope = str(panel_scope or eid or week_sig).strip()
    admin_edit = _can_admin_edit_approved_timekeeping()
    can_override_ot = _can_override_overtime_allocation()
    job_opts = _assignment_options_for_timekeeping(week_start_d=week_start_d)
    can_approve = _can_approve_timekeeping()
    can_submit = _can_submit_timekeeping()
    grid = _ensure_weekly_grid(emp, week_start_d)
    _apply_row_hrs_to_grid(grid, eid=eid, week_sig=week_sig)
    week_status = _resolved_week_status(emp, week_start_d, grid=grid)
    week_locked = week_status == "Approved" and not admin_edit
    by_date = _ensure_allocation_state(emp, week_start_d)
    _sync_allocation_from_widgets(by_date, eid=eid, week_sig=week_sig)
    _bootstrap_week_allocation_lines(
        by_date,
        week_start_d=week_start_d,
        source_grid=grid,
        job_opts=job_opts,
        eid=eid,
        week_sig=week_sig,
    )
    by_date = _recalculate_week_overtime(by_date, week_start_d)
    _sync_alloc_type_widgets_from_lines(by_date, eid=eid, week_sig=week_sig)
    st.session_state[_alloc_state_key(eid)] = by_date

    render_allocation_panel_intro(
        policy_note=_overtime_policy_note(),
        week_totals_html=_week_allocation_totals_html(by_date),
    )

    alloc_deps = AllocationRenderDeps(
        fmt_day_hours=_fmt_day_hours,
        coerce_assignment_label=_coerce_assignment_label,
        assignment_option_index=_assignment_option_index,
        sync_assignment_job_widget=_sync_assignment_job_widget,
        normalize_alloc_hour_type=_normalize_alloc_hour_type,
        ensure_alloc_type_widget_label=_ensure_alloc_type_widget_label,
        alloc_hour_type_label=_alloc_hour_type_label,
        timecard_status_pill_html=_timecard_status_pill_html,
        allocated_hours_sum=_valid_allocated_hours_sum,
        alloc_state_key=_alloc_state_key,
        day_is_editable=_day_is_editable,
        day_hours_editable=_day_hours_editable,
        handle_alloc_line_submit=_handle_alloc_line_submit,
        handle_alloc_line_approve=_handle_alloc_line_approve,
        handle_alloc_line_reject=_handle_alloc_line_reject,
        handle_day_submit_for_date=_handle_day_submit_for_date,
        handle_day_approve_for_date=_handle_day_approve_for_date,
        handle_day_reject_for_date=_handle_day_reject_for_date,
        mark_allocation_dirty=lambda iso: _mark_allocation_dirty(emp, week_start_d, iso),
        save_allocation_day=lambda iso: _save_allocation_day(emp, week_start_d, iso),
        alloc_autosave_status_html=lambda iso: _alloc_autosave_status_html(eid, iso),
        can_override_overtime=can_override_ot,
        handle_alloc_type_change=(
            (lambda iso, lix: _handle_alloc_type_change(
                eid,
                week_sig,
                iso,
                lix,
                can_override=can_override_ot,
            ))
            if can_override_ot
            else None
        ),
        overtime_badge_html=_overtime_override_badge_html,
        overtime_policy_note=_overtime_policy_note(),
        selected_time_type_from_line=_selected_time_type_from_line,
        selected_time_type_widget_label=_selected_time_type_widget_label,
        alloc_time_type_hint_html=_alloc_time_type_hint_html,
    )

    if admin_edit and week_status == "Approved":
        st.warning("Administrator edit mode — save each day with **Save day** after editing hours.")
    elif week_locked:
        st.info("This week is approved and locked.")

    if not eid:
        st.warning("Employee id is missing for this row; daily allocations cannot be edited.")
        return

    days_with_hours = 0
    with render_allocation_days_panel(panel_scope=scope, compact=True):
        for day_ix, day_d in enumerate(week_dates(week_start_d)):
            iso = day_d.isoformat()
            grid_row = grid[day_ix] if day_ix < len(grid) else {}
            day_status = _normalize_timecard_status(grid_row.get("status"))
            daily_total = _daily_total_from_list_row(
                eid=eid,
                week_sig=week_sig,
                day_ix=day_ix,
                grid_row=grid_row,
            )
            if daily_total <= _ALLOC_TOLERANCE:
                continue
            days_with_hours += 1
            lines = _ensure_day_allocation_lines(
                by_date,
                iso=iso,
                daily_total=daily_total,
                grid_row=grid_row,
                job_opts=job_opts,
                eid=eid,
                week_sig=week_sig,
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
            type_bits = []
            if st_part > 0:
                type_bits.append(f"S/T {_fmt_day_hours(st_part)}")
            if ot_part > 0:
                type_bits.append(f"O/T {_fmt_day_hours(ot_part)}")
            type_summary = f" ({' · '.join(type_bits)})" if type_bits else ""

            render_day_allocation_card(
                deps=alloc_deps,
                ctx=DayAllocationCardContext(
                    eid=eid,
                    week_sig=week_sig,
                    panel_scope=scope,
                    iso=iso,
                    day_name=day_name,
                    daily_total=daily_total,
                    allocated=allocated,
                    remaining=remaining,
                    type_summary=type_summary,
                    alloc_state=str(alloc_state["state"]),
                    lines=lines,
                    week_locked=week_locked,
                    job_opts=job_opts,
                    can_approve=can_approve,
                    can_submit=can_submit,
                    emp=emp,
                    week_start_d=week_start_d,
                    by_date=by_date,
                    record_key=record_session_key(emp, "id"),
                    week_status=week_status,
                    day_status=day_status,
                    include_notes=False,
                ),
                normalize_timecard_status=_normalize_timecard_status,
            )

            if day_ix < len(grid) and lines:
                grid[day_ix]["job"] = str(lines[0].get("job") or grid[day_ix].get("job") or "")

    if days_with_hours == 0:
        st.caption("Enter hours for each day in the employee row above to assign jobs.")

    st.session_state[_grid_key(eid)] = grid
    st.session_state[_alloc_state_key(eid)] = by_date

    if week_locked:
        return

    record_key = record_session_key(emp, "id")
    footer_scope = allocation_panel_scope_key(scope)
    with st.container(key=f"tk_alloc_week_footer_{footer_scope}"):
        st.markdown(
            '<span class="timekeeping-allocation-week-footer-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        if can_submit and week_status in ("Draft", "Rejected") and st.button(
            "Submit all for approval",
            key=f"tk_submit_alloc_{record_key}",
        ):
            if _save_allocation_week(emp, week_start_d, show_message=False)[0] and _submit_timekeeping_week(
                emp, week_start_d
            ):
                fragment_rerun()
        if week_status == "Pending" and can_approve:
            reject_notes = st.text_input(
                "Rejection notes (optional)",
                key=f"tk_list_reject_notes_{record_key}",
                placeholder="Rejection notes (optional)",
                label_visibility="collapsed",
            )
            approve_col, reject_col = st.columns(2)
            with approve_col:
                if st.button(
                    "Approve time",
                    key=f"tk_approve_week_{record_key}",
                    type="primary",
                    use_container_width=True,
                ):
                    if _approve_timekeeping_week(emp, week_start_d):
                        fragment_rerun()
            with reject_col:
                if st.button(
                    "Reject",
                    key=f"tk_reject_week_{record_key}",
                    use_container_width=True,
                ):
                    if _reject_timekeeping_week(emp, week_start_d, reject_notes):
                        fragment_rerun()
        elif week_status == "Pending":
            st.caption("Pending approval — waiting for an administrator to approve or reject.")
        st.caption(
            "Totals in the row above are the source of truth. Use Submit day / Approve day on each day card, "
            "or approve the full week below. Hours on — No assignment — do not count as allocated — pick a job, subjob, Shop, Administrative, or Vacation before submitting."
        )


def _render_inline_daily_entries(row: dict, week_start_d: date) -> None:
    emp = _emp_from_timecard_row(row)
    timecard_id = str(row.get("timecard_id") or "").strip()
    _render_list_allocation_detail(emp, week_start_d, panel_scope=timecard_id)
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
            _prepare_timecard_detail_modal(timecard_id)
            _timekeeping_app_rerun()


@fragment
def _render_timekeeping_expand_fragment(row: dict, week_start_d: date) -> None:
    """Expanded allocation panel — local reruns when assigning jobs/hours per day."""
    timecard_id = str(row.get("timecard_id") or "").strip()
    with st.container(key=f"tk_expand_detail_{timecard_id}"):
        st.markdown(
            '<span class="timekeeping-expand-detail-panel timekeeping-detail-expand-host '
            'timesheet-employee-expand-detail ips-timekeeping-row-expand" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        _render_inline_daily_entries(row, week_start_d)


def _render_daily_entries_tab(
    emp: dict,
    week_start_d: date,
    *,
    perms: TimekeepingPermissions | None = None,
) -> None:
    perms = perms or _timekeeping_permissions()
    week_status = _resolved_week_status(emp, week_start_d)
    admin_edit = perms.can_edit_approved
    if week_status == "Approved" and not admin_edit:
        _render_weekly_grid_readonly(emp, week_start_d)
        st.info("This week is approved and locked.")
        return

    if week_status == "Approved" and admin_edit:
        st.warning("Administrator edit mode — approved days can be corrected here.")
    _render_weekly_grid_edit(emp, week_start_d, perms=perms)
    action_left, action_right = st.columns([1, 1])
    record_key = record_session_key(emp, "id")
    with action_left:
        if st.button("Save Hours", key=f"tk_save_hours_{record_key}", type="primary"):
            if _save_timekeeping_week(emp, week_start_d):
                fragment_rerun()
    with action_right:
        if perms.can_submit and week_status in ("Draft", "Rejected") and st.button(
            "Submit All for Approval",
            key=f"tk_submit_{record_key}",
        ):
            if _submit_timekeeping_week(emp, week_start_d):
                fragment_rerun()
    st.caption(
        "Enter hours on the grid, assign jobs per day, then submit each day or the full week."
    )


def _render_approval_tab(
    emp: dict,
    week_start_d: date,
    *,
    perms: TimekeepingPermissions | None = None,
) -> None:
    perms = perms or _timekeeping_permissions()
    status = _resolved_week_status(emp, week_start_d)
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

    if status == "Pending" and perms.can_approve:
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
                    fragment_rerun()
        with reject_col:
            if st.button("Reject Timecard", key=f"tk_reject_{record_session_key(emp, 'id')}"):
                if _reject_timekeeping_week(emp, week_start_d, reject_notes):
                    fragment_rerun()
    elif status == "Pending":
        st.caption("Submitted for approval. An administrator can approve or reject from the expanded list row or below.")
    elif status == "Draft":
        st.caption("Enter hours on the Daily Entries tab, then submit each day or the full week for approval.")
    elif status == "Rejected":
        st.caption("Update hours on the Daily Entries tab and submit again for approval.")
    elif status == "Approved":
        st.caption(f"Approved by {_current_user_name() if not approved_at else 'supervisor'}.")


@fragment
def _render_timekeeping_detail_tabs_fragment(
    emp: dict,
    week_start_d: date,
    *,
    perms: TimekeepingPermissions | None = None,
) -> None:
    """Timecard modal tabs — local reruns for hour edits and allocation saves."""
    _render_timekeeping_view_tabs(emp, week_start_d, perms=perms)


def _render_timekeeping_view_tabs(
    emp: dict,
    week_start_d: date,
    *,
    perms: TimekeepingPermissions | None = None,
) -> None:
    from app.components.tabs import render_tabs
    from app.perf_debug import perf_span

    perms = perms or _timekeeping_permissions()
    _sync_timekeeping_detail_tab(emp)
    st_total, ot_total, _dt_total, total = _emp_totals(emp)
    status = _resolved_week_status(emp, week_start_d)

    active_tab = render_tabs(
        list(_TIMEKEEPING_DETAIL_TABS),
        session_key=_TIMEKEEPING_DETAIL_TAB_KEY,
        default="Weekly Timecard",
    )

    if active_tab == "Weekly Timecard":
        with perf_span("timekeeping.modal.summary"):
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
    elif active_tab == "Daily Entries":
        with perf_span("timekeeping.modal.daily_entries"):
            _render_daily_entries_tab(emp, week_start_d, perms=perms)
    elif active_tab == "Approval":
        with perf_span("timekeeping.modal.approval"):
            _render_approval_tab(emp, week_start_d, perms=perms)
    elif active_tab == "Notes":
        note_text = str(emp.get("notes") or "").strip()
        if note_text:
            st.markdown(dialog_card_html("Notes", detail_field_html("Notes", note_text)), unsafe_allow_html=True)
        else:
            placeholder_html("No notes on this timecard yet.")
    elif active_tab == "Activity":
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


def render_timekeeping_detail_dialog(
    emp: dict,
    week_start_d: date,
    *,
    perms: TimekeepingPermissions | None = None,
) -> None:
    perms = perms or _timekeeping_permissions()
    st_total, ot_total, dt_total, total = _emp_totals(emp)
    status = _resolved_week_status(emp, week_start_d)
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
    _render_timekeeping_detail_tabs_fragment(emp, week_start_d, perms=perms)


@st.dialog("Timecard Details", width="large", on_dismiss=_clear_timecard_modal)
def _show_timecard_detail_modal() -> None:
    tc = _get_selected_timecard()
    if not tc:
        render_missing_record(_clear_timecard_modal, close_key="tk_modal_missing_close")
        return
    render_timekeeping_detail_dialog(tc, _week_start_from_row(tc))


def _filter_timecards(
    built_rows: list[dict],
) -> list[dict]:
    return apply_column_filters(built_rows, _TABLE_KEY, _TK_COLUMN_FILTER_SPECS)


def _render_timekeeping_list_fragment(
    page_rows: list[dict],
    *,
    filter_options: dict[str, list[str]],
    week_start_d: date,
) -> list[str]:
    """Weekly timecard list table (fragment isolates filter/pagination widget reruns)."""
    return _render_custom_timekeeping_table(
        page_rows,
        filter_options=filter_options,
        week_start_d=week_start_d,
    )


def _format_modal_day_title(day_d: date) -> str:
    return f"{day_d.strftime('%A, %B')} {day_d.day}, {day_d.year}"


def _clear_day_time_modal() -> None:
    """Dismiss day editor — unsaved widget edits are discarded (no auto-save on close)."""
    eid = str(st.session_state.get(TIMEKEEPING_MODAL_EMPLOYEE_ID_KEY) or "").strip()
    iso = str(st.session_state.get(TIMEKEEPING_MODAL_DATE_KEY) or "").strip()[:10]
    if eid and iso:
        _set_alloc_autosave_status(eid, iso, "")
    st.session_state.pop(TIMEKEEPING_MODAL_EMPLOYEE_ID_KEY, None)
    st.session_state.pop(TIMEKEEPING_MODAL_DATE_KEY, None)
    st.session_state.pop(TIMEKEEPING_MODAL_TIMECARD_KEY, None)
    st.session_state.pop(SELECTED_TIME_EMPLOYEE_ID_KEY, None)
    st.session_state.pop(SELECTED_TIME_DATE_KEY, None)
    st.session_state[SHOW_TIMEKEEPING_DAY_MODAL_KEY] = False
    _clear_timekeeping_day_query_params()


def _clear_day_time_selection() -> None:
    """Clear inline panel and mobile modal selection."""
    _clear_day_time_modal()


def _open_day_time_editor(
    *,
    eid: str,
    work_date: date,
    timecard_id: str,
    week_start_d: date | None = None,
) -> None:
    eid_s = str(eid or "").strip()
    iso = work_date.isoformat()
    st.session_state[SELECTED_TIME_EMPLOYEE_ID_KEY] = eid_s
    st.session_state[SELECTED_TIME_DATE_KEY] = iso
    st.session_state[TIMEKEEPING_MODAL_EMPLOYEE_ID_KEY] = eid_s
    st.session_state[TIMEKEEPING_MODAL_DATE_KEY] = iso
    st.session_state[TIMEKEEPING_MODAL_TIMECARD_KEY] = str(timecard_id or "").strip()
    ws = week_start_d or week_start(work_date)
    if eid_s:
        _ensure_weekly_grid({"id": eid_s, "employee_id": eid_s}, ws)
    if _is_narrow_viewport():
        st.session_state[SHOW_TIMEKEEPING_DAY_MODAL_KEY] = True
    else:
        st.session_state[SHOW_TIMEKEEPING_DAY_MODAL_KEY] = False


def _open_day_time_modal(
    *,
    eid: str,
    work_date: date,
    timecard_id: str,
) -> None:
    _open_day_time_editor(eid=eid, work_date=work_date, timecard_id=timecard_id)


def _get_day_panel_context() -> tuple[dict, date, str, dict] | None:
    """Return (emp, week_start, iso, timecard_row) for the selected day panel."""
    eid = str(st.session_state.get(SELECTED_TIME_EMPLOYEE_ID_KEY) or "").strip()
    iso = str(st.session_state.get(SELECTED_TIME_DATE_KEY) or "").strip()[:10]
    if not eid or not iso:
        return None
    return _get_day_modal_context_from_ids(eid, iso)


def _get_day_modal_context() -> tuple[dict, date, str, dict] | None:
    """Return (emp, week_start, iso, timecard_row) for the open day modal."""
    eid = str(st.session_state.get(TIMEKEEPING_MODAL_EMPLOYEE_ID_KEY) or "").strip()
    iso = str(st.session_state.get(TIMEKEEPING_MODAL_DATE_KEY) or "").strip()[:10]
    if not eid or not iso:
        return None
    return _get_day_modal_context_from_ids(eid, iso)


def _get_day_modal_context_from_ids(eid: str, iso: str) -> tuple[dict, date, str, dict] | None:
    """Resolve employee/timecard row for a selected employee/day."""
    week_start_d = _current_week_start()
    cache = st.session_state.get(_CACHE_KEY) or {}
    row: dict | None = None
    if isinstance(cache, dict):
        tid = str(st.session_state.get(TIMEKEEPING_MODAL_TIMECARD_KEY) or "").strip()
        if tid and isinstance(cache.get(tid), dict):
            row = cache[tid]
        if row is None:
            for rec in cache.values():
                if not isinstance(rec, dict):
                    continue
                if str(rec.get("employee_id") or rec.get("id") or "").strip() == eid:
                    row = rec
                    break
    if row is None:
        row = {"employee_id": eid, "id": eid, "employee_name": "Employee"}
    emp = _emp_from_timecard_row(row)
    return emp, week_start_d, iso, row


def _on_modal_day_hours_changed(eid: str, week_start_d: date, day_ix: int, iso: str) -> None:
    week_sig = week_start_d.isoformat()
    gk = _grid_key(eid)
    grid = st.session_state.get(gk)
    if not isinstance(grid, list) or day_ix < 0 or day_ix >= len(grid):
        return
    hours = max(
        0.0,
        float(st.session_state.get(_weekly_hours_widget_key(eid, iso), 0) or 0),
    )
    _set_day_job_hours(grid[day_ix], hours)
    st.session_state[gk] = grid
    by_date = st.session_state.get(_alloc_state_key(eid))
    if isinstance(by_date, dict):
        week_start_d = date.fromisoformat(week_sig)
        _bootstrap_week_allocation_lines(
            by_date,
            week_start_d=week_start_d,
            source_grid=grid,
            job_opts=_assignment_options_for_timekeeping(week_start_d=week_start_d),
            eid=eid,
            week_sig=week_sig,
        )
        by_date = _recalculate_week_overtime(by_date, week_start_d)
        st.session_state[_alloc_state_key(eid)] = by_date
    _mark_allocation_dirty(_emp_from_timecard_row({"employee_id": eid, "id": eid}), week_start_d, iso)


def _make_allocation_render_deps(emp: dict, week_start_d: date) -> AllocationRenderDeps:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    week_sig = week_start_d.isoformat()
    can_override_ot = _can_override_overtime_allocation()
    return AllocationRenderDeps(
        fmt_day_hours=_fmt_day_hours,
        coerce_assignment_label=_coerce_assignment_label,
        assignment_option_index=_assignment_option_index,
        sync_assignment_job_widget=_sync_assignment_job_widget,
        normalize_alloc_hour_type=_normalize_alloc_hour_type,
        ensure_alloc_type_widget_label=_ensure_alloc_type_widget_label,
        alloc_hour_type_label=_alloc_hour_type_label,
        timecard_status_pill_html=_timecard_status_pill_html,
        allocated_hours_sum=_valid_allocated_hours_sum,
        alloc_state_key=_alloc_state_key,
        day_is_editable=_day_is_editable,
        day_hours_editable=_day_hours_editable,
        handle_alloc_line_submit=_handle_alloc_line_submit,
        handle_alloc_line_approve=_handle_alloc_line_approve,
        handle_alloc_line_reject=_handle_alloc_line_reject,
        handle_day_submit_for_date=_handle_day_submit_for_date,
        handle_day_approve_for_date=_handle_day_approve_for_date,
        handle_day_reject_for_date=_handle_day_reject_for_date,
        mark_allocation_dirty=lambda iso: _mark_allocation_dirty(emp, week_start_d, iso),
        save_allocation_day=lambda iso: _save_allocation_day(emp, week_start_d, iso),
        alloc_autosave_status_html=lambda iso: _alloc_autosave_status_html(eid, iso),
        can_override_overtime=can_override_ot,
        handle_alloc_type_change=(
            (lambda iso, lix: _handle_alloc_type_change(
                eid,
                week_sig,
                iso,
                lix,
                can_override=can_override_ot,
            ))
            if can_override_ot
            else None
        ),
        overtime_badge_html=_overtime_override_badge_html,
        overtime_policy_note=_overtime_policy_note(),
        selected_time_type_from_line=_selected_time_type_from_line,
        selected_time_type_widget_label=_selected_time_type_widget_label,
        alloc_time_type_hint_html=_alloc_time_type_hint_html,
    )


def _render_single_day_allocation_modal(
    emp: dict,
    week_start_d: date,
    *,
    iso: str,
    panel_scope: str,
    alloc_deps: AllocationRenderDeps,
) -> None:
    """One-day allocation editor for the day modal."""
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    week_sig = week_start_d.isoformat()
    scope = str(panel_scope or eid or week_sig).strip()
    admin_edit = _can_admin_edit_approved_timekeeping()
    can_approve = _can_approve_timekeeping()
    can_submit = _can_submit_timekeeping()
    job_opts = _assignment_options_for_timekeeping(week_start_d=week_start_d)
    grid = _ensure_weekly_grid(emp, week_start_d)
    _apply_row_hrs_to_grid(grid, eid=eid, week_sig=week_sig)
    week_status = _resolved_week_status(emp, week_start_d, grid=grid)
    week_locked = week_status == "Approved" and not admin_edit
    by_date = _ensure_allocation_state(emp, week_start_d)
    _sync_allocation_from_widgets(by_date, eid=eid, week_sig=week_sig)
    _bootstrap_week_allocation_lines(
        by_date,
        week_start_d=week_start_d,
        source_grid=grid,
        job_opts=job_opts,
        eid=eid,
        week_sig=week_sig,
    )
    by_date = _recalculate_week_overtime(by_date, week_start_d)
    _sync_alloc_type_widgets_from_lines(by_date, eid=eid, week_sig=week_sig)
    st.session_state[_alloc_state_key(eid)] = by_date

    day_ix = next(
        (i for i, day_d in enumerate(week_dates(week_start_d)) if day_d.isoformat() == iso),
        -1,
    )
    if day_ix < 0:
        st.error("That date is not in the current week.")
        return
    day_d = week_dates(week_start_d)[day_ix]
    grid_row = grid[day_ix] if day_ix < len(grid) else {}
    day_status = _normalize_timecard_status(grid_row.get("status"))
    lines = _bootstrap_day_editor_allocation_lines(
        by_date,
        iso=iso,
        grid_row=grid_row,
        job_opts=job_opts,
    )
    live_lines = _live_allocation_lines_for_day(lines, eid=eid, week_sig=week_sig, iso=iso)
    daily_total = _daily_total_from_allocation_lines(live_lines)
    alloc_state = _get_day_allocation_state(
        daily_total,
        live_lines,
        allocation_is_source=True,
    )
    allocated = alloc_state["allocated_total"]
    st_part = alloc_state["allocated_st"]
    ot_part = alloc_state["allocated_ot"]
    remaining = max(0.0, round(float(alloc_state["remaining"]), 2))
    day_name = _detail_day_label({"day": day_d.strftime("%A"), "date": iso})
    type_bits = []
    if st_part > 0:
        type_bits.append(f"S/T {_fmt_day_hours(st_part)}")
    if ot_part > 0:
        type_bits.append(f"O/T {_fmt_day_hours(ot_part)}")
    type_summary = f" ({' · '.join(type_bits)})" if type_bits else ""

    render_day_allocation_card(
        deps=alloc_deps,
        ctx=DayAllocationCardContext(
            eid=eid,
            week_sig=week_sig,
            panel_scope=scope,
            iso=iso,
            day_name=day_name,
            daily_total=daily_total,
            allocated=allocated,
            remaining=remaining,
            type_summary=type_summary,
            alloc_state=str(alloc_state["state"]),
            lines=lines,
            week_locked=week_locked,
            job_opts=job_opts,
            can_approve=can_approve,
            can_submit=can_submit,
            emp=emp,
            week_start_d=week_start_d,
            by_date=by_date,
            record_key=record_session_key(emp, "id"),
            week_status=week_status,
            day_status=day_status,
            include_notes=True,
            modal_host=True,
            daily_hours_label="total hrs",
        ),
        normalize_timecard_status=_normalize_timecard_status,
    )
    if lines and day_ix < len(grid):
        grid[day_ix]["job"] = str(lines[0].get("job") or grid[day_ix].get("job") or "")
    st.session_state[_grid_key(eid)] = grid
    st.session_state[_alloc_state_key(eid)] = by_date


def _discard_day_modal_edits(emp: dict, week_start_d: date) -> None:
    _invalidate_weekly_grid(emp, week_start_d)
    _ensure_weekly_grid(emp, week_start_d)


def _sync_grid_row_from_allocation_lines(
    grid_row: dict,
    lines: list[dict[str, Any]],
) -> None:
    """Write allocation line totals back to the weekly grid row."""
    alloc_state = _get_day_allocation_state(
        0.0,
        lines,
        allocation_is_source=True,
    )
    grid_row["st"] = float(alloc_state.get("allocated_st") or 0)
    grid_row["ot"] = float(alloc_state.get("allocated_ot") or 0)
    grid_row["dt"] = 0.0


def _save_day_from_modal(emp: dict, week_start_d: date, iso: str) -> bool:
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    week_sig = week_start_d.isoformat()
    day_ix = next(
        (i for i, day_d in enumerate(week_dates(week_start_d)) if day_d.isoformat() == iso),
        -1,
    )
    grid = _ensure_weekly_grid(emp, week_start_d)
    by_date = _ensure_allocation_state(emp, week_start_d)
    _sync_allocation_from_widgets(by_date, eid=eid, week_sig=week_sig)
    live_lines = _live_allocation_lines_for_day(
        list(by_date.get(iso) or []),
        eid=eid,
        week_sig=week_sig,
        iso=iso,
    )
    if day_ix >= 0 and day_ix < len(grid):
        _sync_grid_row_from_allocation_lines(grid[day_ix], live_lines)
        st.session_state[_grid_key(eid)] = grid
    _set_alloc_autosave_status(eid, iso, "saving")
    ok, _msg = _save_allocation_week(
        emp,
        week_start_d,
        show_message=True,
        focus_iso=iso,
        allow_incomplete=True,
    )
    if ok:
        grid = _ensure_weekly_grid(emp, week_start_d)
        st_total, ot_total, total_hours = _row_totals_from_grid(grid)
        status = _week_status_from_grid(grid)
        _patch_timecard_cache(
            emp,
            week_start_d,
            {
                "st_total": st_total,
                "ot_total": ot_total,
                "total_hours": total_hours,
                "status": status,
            },
        )
        _set_alloc_autosave_status(eid, iso, "saved")
        _clear_day_time_modal()
        return True
    _set_alloc_autosave_status(eid, iso, "unsaved")
    return False


def _render_day_panel_header(emp: dict, day_d: date, *, eid: str, iso: str) -> None:
    """Right-side panel title row with close control."""
    name = str(emp.get("name") or emp.get("employee_name") or "Employee")
    title_col, close_col = st.columns([5.5, 0.45], gap="small", vertical_alignment="center")
    with title_col:
        st.markdown(
            f'<div class="timekeeping-day-panel-title">{html.escape(name)}</div>'
            f'<div class="timekeeping-day-panel-date">{html.escape(_format_modal_day_title(day_d))}</div>',
            unsafe_allow_html=True,
        )
    with close_col:
        if st.button("✕", key=f"time_close_{eid}_{iso}", help="Close"):
            _clear_day_time_selection()
            _timekeeping_app_rerun()


def _render_day_time_editor_core(emp: dict, week_start_d: date, iso: str) -> None:
    """Shared day editor body for inline panel and mobile modal."""
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    week_sig = week_start_d.isoformat()
    day_ix = next(
        (i for i, day_d in enumerate(week_dates(week_start_d)) if day_d.isoformat() == iso),
        -1,
    )
    if day_ix < 0:
        st.error("That date is not in the current week.")
        return
    day_d = week_dates(week_start_d)[day_ix]
    grid = _ensure_weekly_grid(emp, week_start_d)
    grid_row = grid[day_ix] if day_ix < len(grid) else {}
    week_status = _resolved_week_status(emp, week_start_d, grid=grid)
    day_status = _normalize_timecard_status(grid_row.get("status"))
    hours_editable = _day_hours_editable(day_status, week_status)
    job_opts = _assignment_options_for_timekeeping(week_start_d=week_start_d)

    unsaved_html = _alloc_autosave_status_html(eid, iso)
    if unsaved_html:
        st.markdown(unsaved_html, unsafe_allow_html=True)

    by_date_preview = _ensure_allocation_state(emp, week_start_d)
    _sync_allocation_from_widgets(by_date_preview, eid=eid, week_sig=week_sig)
    _bootstrap_day_editor_allocation_lines(
        by_date_preview,
        iso=iso,
        grid_row=grid_row,
        job_opts=job_opts,
    )
    lines_preview = list(by_date_preview.get(iso) or [])
    live_preview = _live_allocation_lines_for_day(lines_preview, eid=eid, week_sig=week_sig, iso=iso)
    daily_total = _daily_total_from_allocation_lines(live_preview)
    alloc_preview = _get_day_allocation_state(
        daily_total,
        live_preview,
        allocation_is_source=True,
    )

    if not hours_editable and day_status == "Approved":
        st.caption("This day is approved and locked.")

    _render_modal_day_stats_box(
        allocated=float(alloc_preview.get("allocated_total") or 0),
        remaining=max(0.0, float(alloc_preview.get("remaining") or 0)),
        st_total=float(alloc_preview.get("allocated_st") or 0),
        ot_total=float(alloc_preview.get("allocated_ot") or 0),
        daily_total=float(alloc_preview.get("effective_total") or daily_total),
        show_remaining=False,
    )

    st.markdown(
        '<div class="timekeeping-modal-section-title">Time Allocations</div>',
        unsafe_allow_html=True,
    )
    alloc_deps = _make_allocation_render_deps(emp, week_start_d)
    timecard_id = str(st.session_state.get(TIMEKEEPING_MODAL_TIMECARD_KEY) or eid).strip()
    _render_single_day_allocation_modal(
        emp,
        week_start_d,
        iso=iso,
        panel_scope=f"panel_{timecard_id}_{iso}",
        alloc_deps=alloc_deps,
    )

    admin_edit = _can_admin_edit_approved_timekeeping()
    if admin_edit and week_status == "Approved":
        st.warning("Administrator edit mode — use **Save Day** to persist corrections.")
    elif week_status == "Approved":
        st.info("This week is approved and locked.")

    status_hint = "Changes will be saved as Draft." if hours_editable else ""
    st.markdown(
        f'<div class="timekeeping-modal-status-row">'
        f'<span class="timekeeping-modal-status-label">Status</span> '
        f"{_timecard_status_pill_html(day_status)}"
        f"</div>",
        unsafe_allow_html=True,
    )
    if status_hint:
        st.caption(status_hint)
    elif hours_editable:
        st.caption("Changes are not saved until you click Save Day.")

    footer_col, cancel_col, save_col = st.columns([2.2, 1, 1], gap="small")
    with cancel_col:
        if st.button(
            "Cancel",
            key=f"time_cancel_{eid}_{iso}",
            use_container_width=True,
        ):
            _discard_day_modal_edits(emp, week_start_d)
            _clear_day_time_selection()
            _timekeeping_app_rerun()
    with save_col:
        if hours_editable and st.button(
            "Save Day",
            key=f"time_save_{eid}_{iso}",
            type="primary",
            use_container_width=True,
        ):
            if _save_day_from_modal(emp, week_start_d, iso):
                _timekeeping_app_rerun()


def _render_day_time_entry_panel(emp: dict, week_start_d: date, iso: str) -> None:
    """Desktop right-side Day Time Entry editor."""
    day_ix = next(
        (i for i, day_d in enumerate(week_dates(week_start_d)) if day_d.isoformat() == iso),
        -1,
    )
    if day_ix < 0:
        st.error("That date is not in the current week.")
        return
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    day_d = week_dates(week_start_d)[day_ix]
    with st.container(key="timekeeping_day_entry_panel"):
        st.markdown(
            '<span class="timekeeping-day-entry-panel timekeeping-day-entry-panel-marker" '
            'aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        _render_day_panel_header(emp, day_d, eid=eid, iso=iso)
        _render_day_time_editor_core(emp, week_start_d, iso)


def render_day_time_dialog_body(emp: dict, week_start_d: date, iso: str) -> None:
    """Modal body: daily hours, allocations, cancel/save."""
    day_ix = next(
        (i for i, day_d in enumerate(week_dates(week_start_d)) if day_d.isoformat() == iso),
        -1,
    )
    if day_ix < 0:
        st.error("That date is not in the current week.")
        return
    day_d = week_dates(week_start_d)[day_ix]
    grid = _ensure_weekly_grid(emp, week_start_d)
    grid_row = grid[day_ix] if day_ix < len(grid) else {}
    day_status = _normalize_timecard_status(grid_row.get("status"))

    render_modal_shell()
    render_modal_header(
        title=str(emp.get("name") or emp.get("employee_name") or "Employee"),
        subtitle=_format_modal_day_title(day_d),
        status=day_status,
    )
    eid = str(emp.get("id") or emp.get("employee_id") or "").strip()
    if eid:
        from app.services.scheduling_service import schedule_suggestion_for_employee_day

        suggestion = schedule_suggestion_for_employee_day(eid, day_d)
        if suggestion:
            st.info(
                "**Scheduled Assignment** — "
                f"{suggestion.get('title', 'Work')} · "
                f"{suggestion.get('expected_hours', 0)} planned hrs · "
                f"Shift: {suggestion.get('shift') or '—'}. "
                "Actual time entry remains editable below."
            )
    _render_day_time_editor_core(emp, week_start_d, iso)


@st.dialog("Day Time Entry", width="large", on_dismiss=_clear_day_time_modal)
def _show_day_time_dialog() -> None:
    ctx = _get_day_modal_context()
    if not ctx:
        render_missing_record(_clear_day_time_modal, close_key="tk_day_modal_missing_close")
        return
    emp, week_start_d, iso, _row = ctx
    render_day_time_dialog_body(emp, week_start_d, iso)


def _clickable_list_day_cell_html(
    *,
    day_d: date,
    day_ix: int,
    day_row: dict,
    eid: str,
    timecard_id: str,
) -> str:
    iso = day_d.isoformat()
    day_status = _normalize_timecard_status(day_row.get("status"))
    total = _day_hours_total(day_row)
    hours_unknown = bool(day_row.get("hours_unknown"))
    has_hours = total > _ALLOC_TOLERANCE and not hours_unknown
    filled_marker = _list_day_box_marker_classes(
        day_status=day_status,
        alloc_state="",
        has_hours=has_hours,
    )
    weekend_cls = " timekeeping-day-cell-weekend" if day_ix >= 5 else ""
    selected_cls = (
        " timekeeping-day-cell-selected-marker"
        if _is_day_cell_selected(eid, iso)
        else ""
    )
    hours_cls = "timekeeping-day-cell-hours" + _day_approval_ro_hour_class(day_status)
    href = _timekeeping_day_href(
        employee_id=eid,
        work_date=day_d,
        timecard_id=timecard_id,
    )
    aria = f"Open {day_d.strftime('%A %m/%d')} time entry"
    status_html = _list_day_status_badge_html(day_status, "")
    if not status_html.strip():
        status_html = (
            f'<span class="timekeeping-day-cell-status">'
            f"{html.escape(_timecard_status_display(day_status).upper())}"
            f"</span>"
        )
    hours_display = "—" if hours_unknown else _fmt_day_hours(total)
    return (
        f'<span class="timekeeping-day-cell-clickable-marker{weekend_cls}{selected_cls}{filled_marker}" '
        f'aria-hidden="true"></span>'
        f'<div class="timekeeping-day-cell-card">'
        f'<div class="timekeeping-day-cell-date">'
        f"{html.escape(day_d.strftime('%a').upper())} {html.escape(day_d.strftime('%m/%d'))}"
        f"</div>"
        f'<a class="timekeeping-day-native-link" href="{html.escape(href, quote=True)}" '
        f'target="_self" aria-label="{html.escape(aria, quote=True)}">'
        f"{status_html}"
        f'<span class="{html.escape(hours_cls.strip())}">'
        f'<div class="timekeeping-list-day-value">{html.escape(hours_display)}</div>'
        f"</span>"
        f"</a>"
        f"</div>"
    )


def _render_clickable_list_day_cell(
    *,
    day_d: date,
    day_ix: int,
    day_row: dict,
    eid: str,
    timecard_id: str,
    week_start_d: date,
) -> None:
    """Compact day cell — native link opens the day editor without Streamlit widgets."""
    del week_start_d
    _render_timekeeping_inline_html(
        _clickable_list_day_cell_html(
            day_d=day_d,
            day_ix=day_ix,
            day_row=day_row,
            eid=eid,
            timecard_id=timecard_id,
        )
    )


def _render_timekeeping_employee_row_collapsed(
    row: dict,
    *,
    week_start_d: date,
    days: list[date],
    timecard_id: str,
    emp: dict,
    employee_name: str,
    eid: str,
) -> None:
    """Compact read-only weekly timecard row using native Streamlit columns."""
    st_total = float(row.get("st_total") or 0)
    ot_total = float(row.get("ot_total") or 0)
    total_hours = float(row.get("total_hours") or 0)
    status = _normalize_timecard_status(row.get("status"))
    day_rows: list[dict] | None = None
    if eid:
        embedded = row.get("_daily_display_rows")
        if isinstance(embedded, list):
            day_rows = embedded
        else:
            day_rows = _list_row_day_rows_for_display(eid, week_start_d)

    with st.container(key=f"tk_row_{timecard_id}"):
        st.markdown(
            '<span class="timekeeping-weekly-row-marker employee-timesheet-row weekly-employee-row" '
            'aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        row_cols = st.columns(_WEEKLY_TS_LIST_ROW_COLS, gap="small")
        with row_cols[0]:
            st.markdown(
                f'<div class="timekeeping-employee-name">{html.escape(employee_name)}</div>',
                unsafe_allow_html=True,
            )

        if eid and day_rows is not None:
            for day_ix, (col, day_d) in enumerate(zip(row_cols[1:8], days)):
                day_row = day_rows[day_ix] if day_ix < len(day_rows) else {}
                with col:
                    _render_clickable_list_day_cell(
                        day_d=day_d,
                        day_ix=day_ix,
                        day_row=day_row,
                        eid=eid,
                        timecard_id=timecard_id,
                        week_start_d=week_start_d,
                    )
        else:
            for day_ix, (col, day_d) in enumerate(zip(row_cols[1:8], days)):
                with col:
                    st.markdown(
                        f'<div class="timekeeping-day-cell-card">'
                        f'<div class="timekeeping-day-cell-date">'
                        f"{html.escape(day_d.strftime('%a').upper())} {html.escape(day_d.strftime('%m/%d'))}"
                        f"</div>"
                        f'<div class="timekeeping-day-cell-status">DRAFT</div>'
                        f'<div class="timekeeping-day-cell-hours">—</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        with row_cols[8]:
            _render_collapsed_list_summary_cell(
                label=_LIST_VIEW_SUMMARY_LABELS[0],
                value=_fmt_list_summary_hours(st_total),
            )
        with row_cols[9]:
            _render_collapsed_list_summary_cell(
                label=_LIST_VIEW_SUMMARY_LABELS[1],
                value=_fmt_list_summary_hours(ot_total),
            )
        with row_cols[10]:
            _render_collapsed_list_summary_cell(
                label=_LIST_VIEW_SUMMARY_LABELS[2],
                value=_fmt_list_summary_hours(total_hours),
            )
        with row_cols[11]:
            _render_collapsed_list_summary_cell(
                label=_LIST_VIEW_SUMMARY_LABELS[3],
                value=_timecard_status_display(status),
            )


def _render_timekeeping_employee_row_body(
    row: dict,
    *,
    week_start_d: date,
    days: list[date],
) -> None:
    """Render one compact employee weekly row (day cells open the editor modal)."""
    timecard_id = str(row.get("timecard_id") or "").strip()
    if not timecard_id:
        return

    emp = _emp_from_timecard_row(row)
    employee_name = str(row.get("employee_name") or "—")
    eid = str(emp.get("id") or emp.get("employee_id") or "")
    _render_timekeeping_employee_row_collapsed(
        row,
        week_start_d=week_start_d,
        days=days,
        timecard_id=timecard_id,
        emp=emp,
        employee_name=employee_name,
        eid=eid,
    )


def _render_timekeeping_employee_row(
    row: dict,
    *,
    week_start_d: date,
    days: list[date],
) -> None:
    """One employee list row (HTML day cells — no per-day Streamlit widgets)."""
    _render_timekeeping_employee_row_body(row, week_start_d=week_start_d, days=days)


@fragment
def _render_timekeeping_table_area(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
    week_start_d: date,
) -> list[str]:
    """Weekly grid table with pagination — local reruns for filters and paging."""
    if not filtered:
        st.info("No timecards match your filters.")
        st.session_state[_ALL_TIMECARD_IDS_KEY] = []
        return []

    render_table_pagination_header(len(filtered), _TABLE_KEY, item_label="employee")
    page_rows, page_num, page_size, _total_pages = paginate_rows(
        filtered, _TABLE_KEY, default_page_size=_TK_LIST_PAGE_SIZE
    )
    _render_timekeeping_list_fragment(page_rows, filter_options=filter_options, week_start_d=week_start_d)
    _inject_timekeeping_daily_hour_focus_script()
    render_table_pagination_footer(len(filtered), _TABLE_KEY)
    if filtered:
        start = (page_num - 1) * page_size + 1
        end = min(page_num * page_size, len(filtered))
        st.markdown(
            f'<p class="ips-timekeeping-page-range">Showing {start} to {end} of '
            f"{len(filtered)} employees</p>",
            unsafe_allow_html=True,
        )
    return [
        str(r.get("timecard_id") or "").strip()
        for r in filtered
        if str(r.get("timecard_id") or "").strip()
    ]


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
            '<span class="timekeeping-list-scroll ips-timekeeping-table-wrap '
            'timekeeping-weekly-table-card" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        _render_timekeeping_employee_filter_header(filter_options, days=days)

        for row in filtered:
            _render_timekeeping_employee_row(row, week_start_d=week_start_d, days=days)

    return all_timecard_ids


def _render_weekly_customer_timesheets_footer(
    filtered: list[dict] | None = None,
    *,
    perms: TimekeepingPermissions | None = None,
) -> None:
    perms = perms or _timekeeping_permissions()
    if not perms.can_access_jobs:
        return
    st.divider()
    st.markdown("**Weekly customer timesheets**")
    st.caption("Generate and send weekly timesheets from the job's **Weekly Timesheets** tab in Job Detail.")
    if st.button("Open Job Weekly Timesheets", key="tk_open_weekly_ts", use_container_width=False):
        from app.navigation import navigate_to_weekly_timesheet
        prefill_job = ""
        tc_id = str(st.session_state.get(SELECTED_TIMECARD_KEY) or "").strip()
        rows = filtered or []
        if tc_id:
            for row in rows:
                if str(row.get("id") or "") == tc_id:
                    prefill_job = str(row.get("primary_job_id") or row.get("job_id") or "").strip()
                    break
        if not prefill_job:
            from app.utils.field_context import get_field_job_id
            prefill_job = str(get_field_job_id() or "").strip()
        navigate_to_weekly_timesheet(
            job_id=prefill_job,
            week_start=_current_week_start().isoformat(),
        )
        st.rerun()


def render() -> None:
    from app.pages._core._access import begin_module
    if not begin_module("timekeeping"):
        return

    from app.navigation import TK_PREFILL_WEEK_KEY
    pre_week_raw = str(st.session_state.pop(TK_PREFILL_WEEK_KEY, "") or "").strip()[:10]
    if pre_week_raw:
        try:
            st.session_state[_WEEK_KEY] = date.fromisoformat(pre_week_raw)
            clear_timekeeping_list_caches()
        except ValueError:
            pass

    _capture_timekeeping_day_query()

    perms = _init_timekeeping_render_context()

    ws = _current_week_start()
    we = week_end(ws)

    def _on_refresh() -> None:
        _recalculate_visible_week_totals(ws)

    from app.ui.page_header import render_page_header

    render_page_header(
        "Weekly Timekeeping",
        "View and manage weekly employee time entries.",
        show_refresh=True,
        refresh_key="tk_hdr_refresh",
        on_refresh=_on_refresh,
    )

    inject_timekeeping_module_css()
    inject_scroll_preserve("timekeeping")
    from app.mobile_ui import ensure_narrow_viewport_detected
    ensure_narrow_viewport_detected()
    st.markdown(
        '<span class="ips-timekeeping-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    can_enter = perms.can_submit

    if not can_enter:
        st.info(
            "Your supervisor enters job time for the crew. You can view your weekly hours below; "
            "contact a supervisor or admin if a correction is needed."
        )

    active_job_id = ""
    from app.utils.field_context import get_field_job_id
    active_job_id = str(get_field_job_id() or "").strip()
    if active_job_id:
        from app.db import fetch_by_match_admin
        job_rows = fetch_by_match_admin("jobs", {"id": active_job_id}, limit=1) or []
        if job_rows:
            j = job_rows[0]
            label = f"{j.get('job_number') or 'Job'} — {j.get('job_name') or ''}".strip(" —")
            st.caption(f"Active job filter: **{label}** · week {fmt_date(ws)} – {fmt_date(we)}")

    if is_field_context():
        from app.db import fetch_jobs_with_order_fallback
        from app.services.job_service import sort_jobs_by_number_then_name
        if perms.role in {"admin", "manager", "supervisor", "project manager", "pm"}:
            jobs = sort_jobs_by_number_then_name(
                list(fetch_jobs_with_order_fallback(limit=3000, use_admin=True) or [])
            )
            if jobs:
                render_field_job_bar(jobs, key_prefix="tk")

    _render_weekly_timekeeping_toolbar(ws, we)

    if _is_day_editor_active():
        panel_ctx = _get_day_panel_context() or _get_day_modal_context()
        with st.container(key="weekly_timekeeping_layout"):
            st.markdown(
                '<span class="weekly-timekeeping-layout-marker" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            if panel_ctx and not _is_narrow_viewport():
                emp, week_start_d, iso, _row = panel_ctx
                from app.perf_debug import perf_span
                with perf_span("timekeeping.day_editor"):
                    _render_day_time_entry_panel(emp, week_start_d, iso)
        show_modal_if_pending(SHOW_TIMEKEEPING_DAY_MODAL_KEY, _show_day_time_dialog)
        _render_weekly_customer_timesheets_footer(filtered=None, perms=perms)
        return

    if _timecard_detail_modal_pending():
        _ensure_selected_timecard_modal_cache(ws)
        if st.session_state.get(SELECTED_TIMECARD_KEY) and st.session_state.get(SHOW_TIMECARD_MODAL_KEY):
            _show_timecard_detail_modal()
        _render_weekly_customer_timesheets_footer(filtered=None, perms=perms)
        return

    from app.services.weekly_timekeeping_service import load_weekly_timekeeping_page, seed_week_days_session_cache

    with st.spinner("Loading weekly timecards…"):
        from app.perf_debug import perf_span

        with perf_span("timekeeping.page_shell"):
            page_snapshot = load_weekly_timekeeping_page(
                week_start=ws,
                role=perms.role,
            )
    if page_snapshot.warning:
        st.warning(page_snapshot.warning)
    if page_snapshot.week_days_by_employee:
        seed_week_days_session_cache(ws, page_snapshot.week_days_by_employee)
    built_rows = _filter_summaries_for_field_user(page_snapshot.employees)
    filter_options = build_filter_options(built_rows, _TK_COLUMN_FILTER_SPECS)

    filtered = _filter_timecards(built_rows)

    build_modal_cache(filtered, row_id_key="timecard_id", cache_key=_CACHE_KEY)

    panel_ctx = _get_day_panel_context()
    show_panel = panel_ctx is not None and not _is_narrow_viewport()

    with st.container(key="weekly_timekeeping_layout"):
        st.markdown(
            '<span class="weekly-timekeeping-layout-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        if show_panel:
            table_col, panel_col = st.columns([1.9, 1.0], gap="medium")
            with table_col:
                st.markdown(
                    '<span class="weekly-timekeeping-left-panel" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                from app.perf_debug import perf_span
                with perf_span("timekeeping.table_rows"):
                    _render_timekeeping_table_area(
                        filtered,
                        filter_options=filter_options,
                        week_start_d=ws,
                    )
            with panel_col:
                emp, week_start_d, iso, _row = panel_ctx
                from app.perf_debug import perf_span
                with perf_span("timekeeping.day_editor"):
                    _render_day_time_entry_panel(emp, week_start_d, iso)
        else:
            from app.perf_debug import perf_span
            with perf_span("timekeeping.table_rows"):
                _render_timekeeping_table_area(
                    filtered,
                    filter_options=filter_options,
                    week_start_d=ws,
                )

    if st.session_state.get(SELECTED_TIMECARD_KEY) and st.session_state.get(SHOW_TIMECARD_MODAL_KEY):
        _show_timecard_detail_modal()

    show_modal_if_pending(SHOW_TIMEKEEPING_DAY_MODAL_KEY, _show_day_time_dialog)

    _render_weekly_customer_timesheets_footer(filtered=filtered, perms=perms)


def render_field_time_panel(*, key_prefix: str = "ftp") -> None:
    """Compact weekly time view for the field day shell (supervisors edit in Timekeeping module)."""
    inject_timekeeping_module_css()
    ws = _current_week_start()
    we = week_end(ws)
    summaries = _filter_summaries_for_field_user(load_timekeeping_summaries(ws))
    _ensure_week_days_by_employee(ws)
    rows = [_build_timecard_row(row, ws) for row in summaries]
    if not rows:
        st.info("No timecard loaded for this week yet.")
        return
    if not _can_submit_timekeeping():
        st.caption(f"{fmt_date(ws)} – {fmt_date(we)} · your approved hours (read-only).")
        for row in rows:
            emp = _emp_from_timecard_row(row)
            _render_weekly_grid_readonly(emp, ws)
        return
    st.caption(f"{fmt_date(ws)} – {fmt_date(we)} · job + hours for all seven days.")
    _render_horizontal_week_grid(rows, week_start_d=ws, key_prefix=key_prefix)
