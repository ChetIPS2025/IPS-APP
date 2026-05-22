"""Timekeeping module (Phase 2C)."""

from __future__ import annotations

import html
from datetime import date, timedelta

import streamlit as st

try:
    from app.components.clickable_table import render_clickable_table
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.record_modal import (
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        edit_mode_key,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_edit_mode,
        set_view_mode,
        show_modal_if_pending,
        status_pill_html,
    )
    from app.pages._core._data import (
        default_weekly_grid,
        job_options_for_timekeeping,
        load_timekeeping_summaries,
    )
    from app.pages._core._session import select_key
    from app.utils.dates import week_end, week_start
    from app.utils.formatting import fmt_date, fmt_hours
except ImportError:
    from components.clickable_table import render_clickable_table  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        edit_mode_key,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_edit_mode,
        set_view_mode,
        show_modal_if_pending,
        status_pill_html,
    )
    from pages._core._data import (  # type: ignore
        default_weekly_grid,
        job_options_for_timekeeping,
        load_timekeeping_summaries,
    )
    from pages._core._session import select_key  # type: ignore
    from utils.dates import week_end, week_start  # type: ignore
    from utils.formatting import fmt_date, fmt_hours  # type: ignore

_SEL = select_key("timekeeping")
_MODULE = "timekeeping"
_TABLE_KEY = "timekeeping_list"
_MODAL_KEY = "ips_timekeeping_detail_modal_id"
_CACHE_KEY = "_ips_timekeeping_modal_by_id"
_WEEK_KEY = "ips_timekeeping_week_start"


def _current_week_start() -> date:
    raw = st.session_state.get(_WEEK_KEY)
    if isinstance(raw, date):
        return raw
    ws = week_start()
    st.session_state[_WEEK_KEY] = ws
    return ws


def _grid_key(emp_id: str) -> str:
    return f"ips_time_grid_{emp_id}"


def _inject_timekeeping_styles() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-header-anchor),
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-filter-anchor) {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 14px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
            margin-bottom: 0.65rem !important;
        }
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-header-anchor) > div,
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-filter-anchor) > div {
            padding: 0.75rem 0.9rem !important;
        }
        .ips-time-header-inner {
            display: flex;
            align-items: flex-start;
            gap: 0.7rem;
        }
        .ips-time-header-icon {
            width: 2.4rem;
            height: 2.4rem;
            border-radius: 10px;
            background: #eff6ff;
            color: #2563eb;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            flex-shrink: 0;
        }
        .ips-time-title {
            margin: 0;
            color: #111827;
            font-size: 1.35rem;
            font-weight: 750;
            line-height: 1.1;
        }
        .ips-time-subtitle {
            margin: 0.18rem 0 0;
            color: #6b7280;
            font-size: 0.82rem;
            font-weight: 500;
        }
        .ips-time-week-label {
            margin: 0.25rem 0 0;
            text-align: right;
            color: #111827;
            font-size: 0.92rem;
            font-weight: 700;
        }
        .ips-time-week-sub {
            margin: 0.1rem 0 0;
            text-align: right;
            color: #6b7280;
            font-size: 0.78rem;
            font-weight: 600;
        }
        .ips-time-day-head {
            color: #9ca3af;
            font-size: 0.66rem;
            font-weight: 750;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid #e5eaf2;
            padding: 0.45rem 0;
        }
        .ips-time-day-row {
            border-bottom: 1px solid #f1f5f9;
            padding: 0.22rem 0;
            color: #111827;
            font-size: 0.82rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _clear_time_filters() -> None:
    st.session_state["tk_search"] = ""
    st.session_state["tk_dept"] = "All Departments"


def _short_day(value: str) -> str:
    return str(value or "")[:3]


def _clear_timekeeping_modal() -> None:
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _open_timekeeping_modal(emp_id: str, emp: dict | None = None) -> None:
    open_record_modal(
        emp_id,
        emp,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
        id_fields=("id",),
    )


def _emp_totals(emp: dict) -> tuple[float, float, float, float]:
    st_total = float(emp.get("st_total") or 0)
    ot_total = float(emp.get("ot_total") or 0)
    dt_total = float(emp.get("dt_total") or 0)
    return st_total, ot_total, dt_total, st_total + ot_total + dt_total


def _ensure_weekly_grid(emp: dict, week_start_d: date) -> list[dict]:
    eid = str(emp.get("id") or "")
    gk = _grid_key(eid)
    week_sig = week_start_d.isoformat()
    if st.session_state.get(f"{gk}_week") != week_sig:
        st.session_state[gk] = default_weekly_grid(eid, week_start_d)
        st.session_state[f"{gk}_week"] = week_sig
    return st.session_state[gk]


def _render_weekly_grid_readonly(emp: dict, week_start_d: date) -> None:
    grid = _ensure_weekly_grid(emp, week_start_d)
    header = st.columns([0.55, 0.7, 2.2, 0.85, 0.85, 0.85, 1.45])
    labels = ["Day", "Date", "Job / Description", "S/T (Hrs)", "O/T (Hrs)", "Total (Hrs)", "Notes"]
    for col, lbl in zip(header, labels):
        with col:
            st.markdown(f'<div class="ips-time-day-head">{html.escape(lbl)}</div>', unsafe_allow_html=True)
    for row in grid:
        c = st.columns([0.55, 0.7, 2.2, 0.85, 0.85, 0.85, 1.45])
        row_total = float(row.get("st") or 0) + float(row.get("ot") or 0) + float(row.get("dt") or 0)
        with c[0]:
            st.markdown(f'<div class="ips-time-day-row">{html.escape(_short_day(str(row.get("day") or "")))}</div>', unsafe_allow_html=True)
        with c[1]:
            st.markdown(f'<div class="ips-time-day-row">{html.escape(fmt_date(row.get("date")))}</div>', unsafe_allow_html=True)
        with c[2]:
            st.markdown(f'<div class="ips-time-day-row">{html.escape(str(row.get("job") or "—"))}</div>', unsafe_allow_html=True)
        with c[3]:
            st.markdown(f'<div class="ips-time-day-row">{html.escape(fmt_hours(row.get("st")))}</div>', unsafe_allow_html=True)
        with c[4]:
            st.markdown(f'<div class="ips-time-day-row">{html.escape(fmt_hours(row.get("ot")))}</div>', unsafe_allow_html=True)
        with c[5]:
            st.markdown(f'<div class="ips-time-day-row">{html.escape(fmt_hours(row_total))}</div>', unsafe_allow_html=True)
        with c[6]:
            st.markdown(f'<div class="ips-time-day-row">{html.escape(str(row.get("notes") or "—"))}</div>', unsafe_allow_html=True)


def _render_weekly_grid_edit(emp: dict, week_start_d: date) -> None:
    eid = str(emp.get("id") or "")
    gk = _grid_key(eid)
    week_sig = week_start_d.isoformat()
    grid = _ensure_weekly_grid(emp, week_start_d)
    job_opts = job_options_for_timekeeping()

    header = st.columns([0.55, 0.7, 2.2, 0.85, 0.85, 0.85, 1.45, 0.35])
    labels = ["Day", "Date", "Job / Description", "S/T (Hrs)", "O/T (Hrs)", "Total (Hrs)", "Notes", ""]
    for col, lbl in zip(header, labels):
        with col:
            st.markdown(f'<div class="ips-time-day-head">{html.escape(lbl)}</div>', unsafe_allow_html=True)

    for i, row in enumerate(grid):
        c = st.columns([0.55, 0.7, 2.2, 0.85, 0.85, 0.85, 1.45, 0.35])
        with c[0]:
            st.markdown(f'<div class="ips-time-day-row">{html.escape(_short_day(str(row.get("day") or "")))}</div>', unsafe_allow_html=True)
        with c[1]:
            st.markdown(f'<div class="ips-time-day-row">{html.escape(fmt_date(row.get("date")))}</div>', unsafe_allow_html=True)
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
            row_total = float(grid[i].get("st") or 0) + float(grid[i].get("ot") or 0) + float(grid[i].get("dt") or 0)
            st.markdown(f'<div class="ips-time-day-row">{html.escape(fmt_hours(row_total))}</div>', unsafe_allow_html=True)
        with c[6]:
            grid[i]["notes"] = st.text_input(
                "Notes",
                value=str(row.get("notes") or ""),
                key=f"tk_notes_{eid}_{week_sig}_{i}",
                label_visibility="collapsed",
                placeholder="Add notes...",
            )
        with c[7]:
            if st.button("🗑", key=f"tk_del_{eid}_{week_sig}_{i}", help="Clear row"):
                grid[i]["job"] = job_opts[0] if job_opts else "— No job —"
                grid[i]["st"] = 0.0
                grid[i]["ot"] = 0.0
                grid[i]["dt"] = 0.0
                grid[i]["notes"] = ""
                st.session_state[gk] = grid
                st.rerun()
    st.session_state[gk] = grid


def _save_timekeeping_week(emp: dict, week_start_d: date) -> None:
    eid = str(emp.get("id") or "")
    grid = _ensure_weekly_grid(emp, week_start_d)
    try:
        from app.pages._core._data import persist_timekeeping_days, persist_timekeeping_week
    except ImportError:
        from pages._core._data import persist_timekeeping_days, persist_timekeeping_week  # type: ignore
    summary = {
        "st_total": sum(float(r.get("st") or 0) for r in grid),
        "ot_total": sum(float(r.get("ot") or 0) for r in grid),
        "dt_total": sum(float(r.get("dt") or 0) for r in grid),
        "status": str(emp.get("status") or "Pending"),
    }
    ok, msg = persist_timekeeping_week(eid, week_start_d, summary)
    if ok:
        ok2, msg2 = persist_timekeeping_days(eid, week_start_d, grid)
        if ok2:
            st.success(msg)
        else:
            detail = f" {msg2}" if msg2 else ""
            st.warning(f"Week totals were saved, but daily entry details could not be saved.{detail}")
    else:
        st.error(msg)


def _render_timekeeping_view_tabs(emp: dict, week_start_d: date) -> None:
    st_total, ot_total, dt_total, total = _emp_totals(emp)
    tab_overview, tab_weekly, tab_notes = st.tabs(["Overview", "Weekly Entries", "Notes"])

    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Employee', emp.get('name'))}"
            f"{detail_field_html('Department', emp.get('department'))}"
            f'{detail_field_html("Status", emp.get("status"), html_value=status_pill_html(str(emp.get("status") or "Pending")))}'
            f"{detail_field_html('Week', f'{fmt_date(week_start_d)} – {fmt_date(week_end(week_start_d))}')}"
            f"{detail_field_html('S/T Total', fmt_hours(st_total))}"
            f"{detail_field_html('O/T Total', fmt_hours(ot_total))}"
            f"{detail_field_html('Total Hours', fmt_hours(total))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Week Summary", overview_html), unsafe_allow_html=True)

    with tab_weekly:
        _render_weekly_grid_readonly(emp, week_start_d)

    with tab_notes:
        placeholder_html("Timekeeping notes and approval history will appear here when connected to Supabase.")


def _render_timekeeping_edit_form(emp: dict, week_start_d: date) -> None:
    record_key = record_session_key(emp, "id")
    render_edit_form_header("Edit Weekly Time")
    _render_weekly_grid_edit(emp, week_start_d)
    cancelled, saved = render_save_cancel_actions(
        module=_MODULE,
        record_key=record_key,
        cancel_key=f"tk_edit_cancel_{record_key}",
        save_key=f"tk_edit_save_{record_key}",
    )
    if cancelled:
        st.rerun()
    if saved:
        _save_timekeeping_week(emp, week_start_d)
        set_view_mode(_MODULE, record_key)
        st.rerun()


def render_timekeeping_detail_dialog(emp: dict, week_start_d: date) -> None:
    record_key = record_session_key(emp, "id")
    st.session_state.setdefault(edit_mode_key(_MODULE, record_key), False)
    edit_mode = is_edit_mode(_MODULE, record_key)

    st_total, ot_total, _, total = _emp_totals(emp)
    render_modal_shell()
    render_modal_header(
        title=str(emp.get("name") or "Employee"),
        subtitle=str(emp.get("department") or ""),
        status=str(emp.get("status") or "Pending"),
    )
    render_modal_edit_button(
        module=_MODULE,
        record_key=record_key,
        key_prefix=f"tk_modal_{record_key}",
    )
    render_modal_meta_grid(
        [
            ("Week", f"{fmt_date(week_start_d)} – {fmt_date(week_end(week_start_d))}"),
            ("S/T Total", fmt_hours(st_total)),
            ("O/T Total", fmt_hours(ot_total)),
            ("Total Hours", fmt_hours(total)),
        ]
    )

    if edit_mode:
        _render_timekeeping_edit_form(emp, week_start_d)
    else:
        _render_timekeeping_view_tabs(emp, week_start_d)


@st.dialog("Weekly Time", width="large", on_dismiss=_clear_timekeeping_modal)
def _show_timekeeping_detail_modal() -> None:
    emp = get_modal_record(
        cache_key=_CACHE_KEY,
        modal_key=_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not emp:
        render_missing_record(_clear_timekeeping_modal, close_key="tk_modal_missing_close")
        return
    render_timekeeping_detail_dialog(emp, _current_week_start())


def _tk_display_cell(field: str, row: dict) -> str:
    if field == "week_start":
        return fmt_date(row.get("week_start"))
    if field in ("st_total", "ot_total", "total_hours"):
        return fmt_hours(row.get(field))
    if field == "status":
        return str(row.get("status") or "—")
    val = row.get(field)
    return str(val).strip() if val is not None and str(val).strip() else "—"


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("timekeeping"):
        return
    _inject_timekeeping_styles()
    st.markdown(
        '<span class="ips-timekeeping-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    ws = _current_week_start()
    we = week_end(ws)

    with st.container(border=True):
        st.markdown('<span class="ips-time-header-anchor"></span>', unsafe_allow_html=True)
        h1, h2, h3 = st.columns([2.5, 2.7, 1.7], gap="medium")
        with h1:
            st.markdown(
                '<div class="ips-time-header-inner">'
                '<div class="ips-time-header-icon">◷</div>'
                '<div><p class="ips-time-title">Timekeeping</p>'
                '<p class="ips-time-subtitle">View and edit employee weekly time entries.</p></div>'
                "</div>",
                unsafe_allow_html=True,
            )
        with h2:
            n1, n2, n3 = st.columns(3, gap="small")
            with n1:
                if st.button("‹  Previous Week", key="tk_prev_week", use_container_width=True):
                    st.session_state[_WEEK_KEY] = ws - timedelta(days=7)
                    st.rerun()
            with n2:
                if st.button("▣  Current Week", key="tk_current_week", use_container_width=True):
                    st.session_state[_WEEK_KEY] = week_start()
                    st.rerun()
            with n3:
                if st.button("Next Week  ›", key="tk_next_week", use_container_width=True):
                    st.session_state[_WEEK_KEY] = ws + timedelta(days=7)
                    st.rerun()
        with h3:
            st.markdown(
                f'<p class="ips-time-week-label">▣ {html.escape(fmt_date(ws))} – {html.escape(fmt_date(we))}</p>'
                f'<p class="ips-time-week-sub">Week {ws.isocalendar()[1]}</p>',
                unsafe_allow_html=True,
            )

    summaries = load_timekeeping_summaries(ws)
    departments = sorted({str(s.get("department") or "") for s in summaries if s.get("department")})

    with st.container(border=True):
        st.markdown('<span class="ips-time-filter-anchor"></span>', unsafe_allow_html=True)

        def _filters() -> None:
            c1, c2, c3 = st.columns([2, 1, 0.75])
            with c1:
                st.text_input("Search", placeholder="Search employee…", key="tk_search", label_visibility="collapsed")
            with c2:
                st.selectbox("Department", ["All Departments", *departments], key="tk_dept", label_visibility="collapsed")
            with c3:
                st.button("⇩ Export", key="tk_export", use_container_width=True)

        layout_filter_bar(_filters)

    q = str(st.session_state.get("tk_search") or "").strip().lower()
    dept = str(st.session_state.get("tk_dept") or "All Departments")
    filtered = summaries
    if q:
        filtered = [s for s in filtered if q in str(s.get("name", "")).lower()]
    if dept != "All Departments":
        filtered = [s for s in filtered if str(s.get("department", "")) == dept]

    table_rows: list[dict] = []
    for row in filtered:
        st_total, ot_total, dt_total, total = _emp_totals(row)
        table_rows.append(
            {
                **row,
                "week_start": row.get("week_start") or ws.isoformat(),
                "total_hours": total,
            }
        )

    st.caption(f"{len(table_rows)} employee(s)")

    build_modal_cache(table_rows, cache_key=_CACHE_KEY)

    render_clickable_table(
        table_rows,
        [
            ("name", "EMPLOYEE"),
            ("department", "DEPARTMENT"),
            ("week_start", "WEEK START"),
            ("st_total", "S/T TOTAL (HRS)"),
            ("ot_total", "O/T TOTAL (HRS)"),
            ("total_hours", "TOTAL HOURS"),
            ("status", "STATUS"),
        ],
        _TABLE_KEY,
        row_id_key="id",
        session_select_key=_SEL,
        format_cell=_tk_display_cell,
        click_caption="Click a row to open the weekly time modal.",
        on_row_selected=_open_timekeeping_modal,
    )

    show_modal_if_pending(_MODAL_KEY, _show_timekeeping_detail_modal)
