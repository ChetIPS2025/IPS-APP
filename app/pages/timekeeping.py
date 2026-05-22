"""Timekeeping module (Phase 2C)."""

from __future__ import annotations

import html
from datetime import date, timedelta

import streamlit as st

try:
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.status import status_pill_html
    from app.pages._core._data import (
        default_weekly_grid,
        job_options_for_timekeeping,
        load_timekeeping_summaries,
    )
    from app.pages._core._session import select_key
    from app.utils.dates import week_end, week_start
    from app.utils.formatting import fmt_date, fmt_hours
except ImportError:
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from pages._core._data import (  # type: ignore
        default_weekly_grid,
        job_options_for_timekeeping,
        load_timekeeping_summaries,
    )
    from pages._core._session import select_key  # type: ignore
    from utils.dates import week_end, week_start  # type: ignore
    from utils.formatting import fmt_date, fmt_hours  # type: ignore

_SEL = select_key("timekeeping")
_WEEK_KEY = "ips_timekeeping_week_start"
_COLLAPSED_KEY = "ips_timekeeping_detail_collapsed"
_TK_GRID = "1.2fr 1fr 1fr 0.85fr 0.85fr 0.85fr 0.8fr 0.55fr"


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
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-filter-anchor),
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-table-anchor),
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-detail-anchor) {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 14px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
            margin-bottom: 0.65rem !important;
        }
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-header-anchor) > div,
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-filter-anchor) > div,
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-table-anchor) > div,
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-detail-anchor) > div {
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
        .ips-time-table-head,
        .ips-time-row {
            display: grid;
            grid-template-columns: """ + _TK_GRID + """;
            align-items: center;
            gap: 0 12px;
            box-sizing: border-box;
        }
        .ips-time-table-head {
            min-height: 38px;
            border-bottom: 1px solid #e5eaf2;
            color: #9ca3af;
            font-size: 0.65rem;
            font-weight: 750;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .ips-time-row {
            padding: 10px 12px;
        }
        .ips-time-emp {
            color: #2563eb;
            font-size: 0.84rem;
            font-weight: 700;
        }
        .ips-time-cell {
            color: #111827;
            font-size: 0.82rem;
            font-weight: 500;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .ips-timekeeping-page .ips-time-summary-table.ips-data-table-html .ips-time-table-head,
        .ips-timekeeping-page .ips-time-summary-table.ips-data-table-html .ips-time-row {
            display: grid !important;
            box-sizing: border-box !important;
        }
        .ips-timekeeping-page .ips-time-summary-table.ips-data-table-html .ips-time-row {
            min-height: 2.75rem;
            cursor: pointer;
        }
        .ips-timekeeping-page .ips-time-summary-table.ips-data-table-html .ips-time-row:hover {
            background: #f8fafc;
        }
        .ips-timekeeping-page .ips-time-summary-table.ips-data-table-html .ips-time-row.selected {
            background: #eff6ff;
            box-shadow: inset 3px 0 0 #2563eb;
        }
        .ips-time-detail-top {
            border-bottom: 1px solid #e5eaf2;
            padding-bottom: 0.65rem;
            margin-bottom: 0.6rem;
        }
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-detail-anchor)
        > div > [data-testid="stHorizontalBlock"]:first-of-type {
            border-bottom: 1px solid #e5eaf2;
            padding-bottom: 0.65rem;
            margin-bottom: 0.55rem;
        }
        .ips-time-weekly-grid-section {
            display: block;
            width: 100%;
        }
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-detail-anchor)
        [data-testid="stNumberInput"] input,
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-detail-anchor)
        [data-testid="stSelectbox"] > div,
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-detail-anchor)
        [data-testid="stTextInput"] input {
            background: #f3f4f6 !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 8px !important;
            min-height: 2.1rem !important;
        }
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-detail-anchor)
        [data-testid="stHorizontalBlock"] {
            align-items: center !important;
        }
        .ips-time-detail-name {
            margin: 0;
            color: #111827;
            font-size: 1.05rem;
            font-weight: 750;
        }
        .ips-time-detail-dept {
            margin: 0.18rem 0 0;
            color: #6b7280;
            font-size: 0.82rem;
            font-weight: 600;
        }
        .ips-time-meta-strip {
            display: flex;
            gap: 2rem;
            align-items: flex-start;
            flex-wrap: wrap;
        }
        .ips-time-meta-label {
            display: block;
            color: #9ca3af;
            font-size: 0.65rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .ips-time-meta-value {
            display: block;
            color: #111827;
            font-size: 0.82rem;
            font-weight: 700;
            margin-top: 0.08rem;
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
        }
        .ips-tk-row-wrap,
        .ips-tk-row-select-btn,
        .ips-tk-actions {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
        }
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.ips-tk-row-wrap) {
            position: relative !important;
            min-height: 60px !important;
            gap: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.ips-tk-row-wrap) > [data-testid="stElementContainer"] {
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.ips-tk-row-wrap)
        > [data-testid="stElementContainer"]:has(.ips-tk-row-select-btn)
        + [data-testid="stElementContainer"]:has(.stButton) {
            position: absolute !important;
            inset: 0 !important;
            right: 62px !important;
            z-index: 2 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.ips-tk-row-wrap)
        > [data-testid="stElementContainer"]:has(.ips-tk-row-select-btn)
        + [data-testid="stElementContainer"]:has(.stButton) .stButton,
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.ips-tk-row-wrap)
        > [data-testid="stElementContainer"]:has(.ips-tk-row-select-btn)
        + [data-testid="stElementContainer"]:has(.stButton) .stButton > button {
            width: 100% !important;
            height: 60px !important;
            min-height: 60px !important;
            margin: 0 !important;
            padding: 0 !important;
            opacity: 0 !important;
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
            cursor: pointer !important;
        }
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.ips-tk-row-wrap)
        > [data-testid="stElementContainer"]:has(.ips-tk-actions)
        + [data-testid="stElementContainer"] {
            position: absolute !important;
            top: 11px !important;
            right: 12px !important;
            z-index: 4 !important;
            width: 42px !important;
        }
        section[data-testid="stMain"]:has(.ips-timekeeping-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-time-table-anchor)
        div[data-testid="stVerticalBlock"]:has(.ips-tk-row-wrap)
        > [data-testid="stElementContainer"]:has(.ips-tk-actions)
        + [data-testid="stElementContainer"] .stButton > button {
            width: 34px !important;
            min-width: 34px !important;
            height: 34px !important;
            min-height: 34px !important;
            padding: 0 !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
            background: #ffffff !important;
            color: #64748b !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
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


def _render_weekly_detail(emp: dict, week_start_d: date) -> None:
    eid = str(emp.get("id") or "")
    gk = _grid_key(eid)
    week_sig = week_start_d.isoformat()
    if st.session_state.get(f"{gk}_week") != week_sig:
        st.session_state[gk] = default_weekly_grid(eid, week_start_d)
        st.session_state[f"{gk}_week"] = week_sig
    grid: list[dict] = st.session_state[gk]
    job_opts = job_options_for_timekeeping()
    st_total = float(emp.get("st_total") or 0)
    ot_total = float(emp.get("ot_total") or 0)
    dt_total = float(emp.get("dt_total") or 0)
    total = st_total + ot_total + dt_total

    with st.container(border=True):
        st.markdown('<span class="ips-time-detail-anchor"></span>', unsafe_allow_html=True)
        h1, h2, h3 = st.columns([2.2, 4.2, 2.3], gap="medium")
        with h1:
            st.markdown(
                f'<p class="ips-time-detail-name">{html.escape(str(emp.get("name") or "Employee"))} '
                f'{status_pill_html(str(emp.get("status") or "Pending"))}</p>'
                f'<p class="ips-time-detail-dept">{html.escape(str(emp.get("department") or "—"))}</p>',
                unsafe_allow_html=True,
            )
        with h2:
            st.markdown(
                '<div class="ips-time-meta-strip">'
                f'<span><span class="ips-time-meta-label">Week</span><span class="ips-time-meta-value">{html.escape(fmt_date(week_start_d))} – {html.escape(fmt_date(week_end(week_start_d)))}</span></span>'
                f'<span><span class="ips-time-meta-label">S/T Total</span><span class="ips-time-meta-value">{html.escape(fmt_hours(st_total))}</span></span>'
                f'<span><span class="ips-time-meta-label">O/T Total</span><span class="ips-time-meta-value">{html.escape(fmt_hours(ot_total))}</span></span>'
                f'<span><span class="ips-time-meta-label">Total Hours</span><span class="ips-time-meta-value">{html.escape(fmt_hours(total))}</span></span>'
                "</div>",
                unsafe_allow_html=True,
            )
        with h3:
            b1, b2, b3 = st.columns([1.1, 1.35, 0.55], gap="small")
            with b1:
                st.button("✎ Edit Week", key=f"tk_edit_{eid}", use_container_width=True)
            with b2:
                if st.button("▣ Save Changes", key=f"tk_save_{eid}", type="primary", use_container_width=True):
                    try:
                        from app.pages._core._data import persist_timekeeping_week
                    except ImportError:
                        from pages._core._data import persist_timekeeping_week  # type: ignore
                    summary = {
                        "st_total": sum(float(r.get("st") or 0) for r in grid),
                        "ot_total": sum(float(r.get("ot") or 0) for r in grid),
                        "dt_total": sum(float(r.get("dt") or 0) for r in grid),
                        "status": str(emp.get("status") or "Pending"),
                    }
                    ok, msg = persist_timekeeping_week(eid, week_start_d, summary)
                    if ok:
                        try:
                            from app.pages._core._data import persist_timekeeping_days
                        except ImportError:
                            from pages._core._data import persist_timekeeping_days  # type: ignore
                        ok2, msg2 = persist_timekeeping_days(eid, week_start_d, grid)
                        if ok2:
                            st.success(msg)
                        else:
                            detail = f" {msg2}" if msg2 else ""
                            st.warning(
                                "Week totals were saved, but daily entry details could not be saved."
                                f"{detail}"
                            )
                    else:
                        st.error(msg)
            with b3:
                if st.button("⌃", key=f"tk_close_{eid}", use_container_width=True, help="Close details"):
                    st.session_state.pop(_SEL, None)
                    st.session_state[_COLLAPSED_KEY] = True
                    st.rerun()

        st.markdown('<span class="ips-time-weekly-grid-section"></span>', unsafe_allow_html=True)

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
        st.caption("Last updated: May 12, 2025 9:42 AM by Leland Daigle")


def _render_timekeeping_table(rows: list[dict], *, selected_id: str, week_start_d: date) -> None:
    try:
        from app.ui.clean_table import apply_clean_table_row_selection, render_clean_table_click_bridge
    except ImportError:
        from ui.clean_table import apply_clean_table_row_selection, render_clean_table_click_bridge  # type: ignore

    table_class = "ips-time-summary-table"
    row_parts: list[str] = []
    records_by_id: dict[str, dict] = {}

    for row in rows:
        eid = str(row.get("id") or "").strip()
        if not eid:
            continue
        records_by_id[eid] = row
        st_total = float(row.get("st_total") or 0)
        ot_total = float(row.get("ot_total") or 0)
        dt_total = float(row.get("dt_total") or 0)
        total = st_total + ot_total + dt_total
        selected = eid == selected_id
        row_cls = "ips-clean-row ips-time-row selected" if selected else "ips-clean-row ips-time-row"
        eid_attr = html.escape(eid, quote=True)
        row_parts.append(
            f'<div class="{row_cls}" data-row-id="{eid_attr}" role="button" tabindex="0">'
            f'<span class="ips-time-emp">{html.escape(str(row.get("name") or "—"))}</span>'
            f'<span class="ips-time-cell">{html.escape(str(row.get("department") or "—"))}</span>'
            f'<span class="ips-time-cell">{html.escape(fmt_date(row.get("week_start") or week_start_d))}</span>'
            f'<span class="ips-time-cell">{html.escape(fmt_hours(st_total))}</span>'
            f'<span class="ips-time-cell">{html.escape(fmt_hours(ot_total))}</span>'
            f'<span class="ips-time-cell">{html.escape(fmt_hours(total))}</span>'
            f'<span>{status_pill_html(str(row.get("status") or "Pending"))}</span>'
            f'<span class="ips-time-cell" title="View">👁</span>'
            "</div>"
        )

    with st.container(border=True):
        st.markdown('<span class="ips-time-table-anchor ips-clean-table"></span>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="ips-data-table-wrap ips-data-table-stable ips-data-table-html {table_class}">'
            f'<div class="ips-data-table-scroll">'
            f'<span class="ips-data-table-anchor {table_class}-anchor" aria-hidden="true"></span>'
            f'<div class="ips-time-table-head">'
            "<span>Employee ⇅</span>"
            "<span>Department ⇅</span>"
            "<span>Week Start ⇅</span>"
            "<span>S/T Total (Hrs) ⇅</span>"
            "<span>O/T Total (Hrs) ⇅</span>"
            "<span>Total Hours ⇅</span>"
            "<span>Status ⇅</span>"
            "<span>Actions</span>"
            "</div>"
            + "".join(row_parts)
            + "</div></div>",
            unsafe_allow_html=True,
        )

    picked = render_clean_table_click_bridge(
        table_selector=f".{table_class}",
        row_selector=".ips-time-row[data-row-id]",
        component_key="ips_timekeeping_row_bridge",
    )
    if picked:
        pid = str(picked).strip()
        if pid and pid in records_by_id:
            if apply_clean_table_row_selection(
                pid,
                session_select_key=_SEL,
                records_by_id=records_by_id,
                on_row_click=lambda _rid, _rec: st.session_state.pop(_COLLAPSED_KEY, None),
            ):
                st.rerun()


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

    st.caption(f"{len(filtered)} employee(s) · Click a row to open the weekly grid")

    selected_id = str(st.session_state.get(_SEL) or "")
    if selected_id and not any(str(s.get("id")) == selected_id for s in filtered):
        st.session_state.pop(_SEL, None)
        selected_id = ""

    _render_timekeeping_table(filtered, selected_id=selected_id, week_start_d=ws)

    sel = str(st.session_state.get(_SEL) or "")
    if sel and not st.session_state.get(_COLLAPSED_KEY):
        emp = next((s for s in summaries if str(s.get("id")) == sel), None)
        if emp:
            _render_weekly_detail(emp, ws)