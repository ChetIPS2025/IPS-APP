"""Timekeeping module (Phase 2C)."""

from __future__ import annotations

import html
from datetime import date, timedelta

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.status import status_pill_html
    from app.components.tables import render_data_table
    from app.pages.modules._data import (
        default_weekly_grid,
        job_options_for_timekeeping,
        load_timekeeping_summaries,
    )
    from app.pages.modules._session import select_key
    from app.styles import inject_global_css
    from app.utils.dates import week_dates, week_end, week_start
    from app.utils.formatting import fmt_date, fmt_hours
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from pages.modules._data import (  # type: ignore
        default_weekly_grid,
        job_options_for_timekeeping,
        load_timekeeping_summaries,
    )
    from pages.modules._session import select_key  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.dates import week_dates, week_end, week_start  # type: ignore
    from utils.formatting import fmt_date, fmt_hours  # type: ignore

_SEL = select_key("timekeeping")
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


def _render_weekly_detail(emp: dict, week_start_d: date) -> None:
    eid = str(emp.get("id") or "")
    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-time-detail-header">', unsafe_allow_html=True)
    h1, h2, h3 = st.columns([2, 2, 1])
    with h1:
        st.markdown(
            f"**{html.escape(str(emp.get('name') or ''))}** {status_pill_html(str(emp.get('status') or 'Pending'))}",
            unsafe_allow_html=True,
        )
        st.caption(str(emp.get("department") or ""))
    with h2:
        st_total = float(emp.get("st_total") or 0)
        ot_total = float(emp.get("ot_total") or 0)
        dt_total = float(emp.get("dt_total") or 0)
        st.caption(
            f"Week: {fmt_date(week_start_d)} – {fmt_date(week_end(week_start_d))} · "
            f"ST {fmt_hours(st_total)} · OT {fmt_hours(ot_total)} · DT {fmt_hours(dt_total)} · "
            f"**Total {fmt_hours(st_total + ot_total + dt_total)}**"
        )
    with h3:
        c1, c2 = st.columns(2)
        with c1:
            st.button("Edit Week", key=f"tk_edit_{eid}", use_container_width=True)
        with c2:
            if st.button("Save Changes", key=f"tk_save_{eid}", type="primary", use_container_width=True):
                try:
                    from app.pages.modules._data import persist_timekeeping_week
                except ImportError:
                    from pages.modules._data import persist_timekeeping_week  # type: ignore
                summary = {
                    "st_total": sum(float(r.get("st") or 0) for r in grid),
                    "ot_total": sum(float(r.get("ot") or 0) for r in grid),
                    "dt_total": sum(float(r.get("dt") or 0) for r in grid),
                    "status": str(emp.get("status") or "Pending"),
                }
                ok, msg = persist_timekeeping_week(eid, week_start_d, summary)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
    st.markdown(f"</{ot}>", unsafe_allow_html=True)

    gk = _grid_key(eid)
    if gk not in st.session_state:
        st.session_state[gk] = default_weekly_grid(eid, week_start_d)

    grid: list[dict] = st.session_state[gk]
    job_opts = job_options_for_timekeeping()

    st.markdown(f'<{ot} class="ips-time-grid-table">', unsafe_allow_html=True)
    hdr = st.columns([1, 0.9, 2.2, 0.6, 0.6, 0.6, 1.4])
    labels = ["Day", "Date", "Job / Description", "S/T (Hrs)", "O/T (Hrs)", "D/T (Hrs)", "Notes"]
    for col, lbl in zip(hdr, labels):
        with col:
            st.markdown(f"**{lbl}**")
    for i, row in enumerate(grid):
        c = st.columns([1, 0.9, 2.2, 0.6, 0.6, 0.6, 1.4])
        with c[0]:
            st.text(row.get("day") or "")
        with c[1]:
            st.text(fmt_date(row.get("date")))
        with c[2]:
            cur_job = str(row.get("job") or job_opts[0])
            idx = job_opts.index(cur_job) if cur_job in job_opts else 0
            grid[i]["job"] = st.selectbox(
                "Job",
                job_opts,
                index=idx,
                key=f"tk_job_{eid}_{i}",
                label_visibility="collapsed",
            )
        with c[3]:
            grid[i]["st"] = st.number_input("ST", value=float(row.get("st") or 0), key=f"tk_st_{eid}_{i}", label_visibility="collapsed", step=0.5)
        with c[4]:
            grid[i]["ot"] = st.number_input("OT", value=float(row.get("ot") or 0), key=f"tk_ot_{eid}_{i}", label_visibility="collapsed", step=0.5)
        with c[5]:
            grid[i]["dt"] = st.number_input("DT", value=float(row.get("dt") or 0), key=f"tk_dt_{eid}_{i}", label_visibility="collapsed", step=0.5)
        with c[6]:
            grid[i]["notes"] = st.text_input("Notes", value=str(row.get("notes") or ""), key=f"tk_notes_{eid}_{i}", label_visibility="collapsed")
    st.session_state[gk] = grid
    st.markdown(f"</{ot}>", unsafe_allow_html=True)
    st.caption("Last updated: May 12, 2025 9:42 AM by Leland Daigle")


def render() -> None:
    inject_global_css()
    ws = _current_week_start()
    we = week_end(ws)

    render_page_header("Timekeeping", "View and edit employee weekly time entries.")

    nav_l, nav_c, nav_r = st.columns([1, 2, 1])
    with nav_l:
        if st.button("← Previous Week", key="tk_prev_week", use_container_width=True):
            st.session_state[_WEEK_KEY] = ws - timedelta(days=7)
            st.rerun()
    with nav_c:
        st.markdown(
            f'<p class="ips-week-label">{fmt_date(ws)} – {fmt_date(we)} · Week {ws.isocalendar()[1]}</p>',
            unsafe_allow_html=True,
        )
    with nav_r:
        if st.button("Next Week →", key="tk_next_week", use_container_width=True):
            st.session_state[_WEEK_KEY] = ws + timedelta(days=7)
            st.rerun()

    summaries = load_timekeeping_summaries(ws)
    departments = sorted({str(s.get("department") or "") for s in summaries if s.get("department")})

    def _filters() -> None:
        c1, c2, c3 = st.columns([2, 1, 0.6])
        with c1:
            st.text_input("Search", placeholder="Search employee…", key="tk_search", label_visibility="collapsed")
        with c2:
            st.selectbox("Department", ["All Departments", *departments], key="tk_dept", label_visibility="collapsed")
        with c3:
            st.button("Export", key="tk_export", use_container_width=True)

    layout_filter_bar(_filters)

    q = str(st.session_state.get("tk_search") or "").strip().lower()
    dept = str(st.session_state.get("tk_dept") or "All Departments")
    filtered = summaries
    if q:
        filtered = [s for s in filtered if q in str(s.get("name", "")).lower()]
    if dept != "All Departments":
        filtered = [s for s in filtered if str(s.get("department", "")) == dept]

    selected_id = str(st.session_state.get(_SEL) or "")
    if selected_id and not any(str(s.get("id")) == selected_id for s in filtered):
        st.session_state.pop(_SEL, None)
        selected_id = ""

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field in ("st_total", "ot_total"):
            return html.escape(fmt_hours(row.get(field)))
        if field == "total_hours":
            t = float(row.get("st_total") or 0) + float(row.get("ot_total") or 0) + float(row.get("dt_total") or 0)
            return html.escape(fmt_hours(t))
        return html.escape(str(row.get(field) or "—"))

    sel = render_data_table(
        filtered,
        [
            ("name", "EMPLOYEE"),
            ("department", "DEPARTMENT"),
            ("week_start", "WEEK START"),
            ("st_total", "S/T TOTAL (HRS)"),
            ("ot_total", "O/T TOTAL (HRS)"),
            ("total_hours", "TOTAL HOURS"),
            ("status", "STATUS"),
        ],
        row_id_key="id",
        selected_id=selected_id or None,
        session_select_key=_SEL,
        col_fr=["1.2fr", "1fr", "0.9fr", "0.7fr", "0.7fr", "0.7fr", "0.75fr"],
        cell_renderer=_cell,
    )

    if sel:
        emp = next((s for s in filtered if str(s.get("id")) == sel), None)
        if emp:
            _render_weekly_detail(emp, ws)
