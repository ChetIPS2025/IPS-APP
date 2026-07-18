"""Streamlit builder for weekly job timesheets — preview, edit, export, sign."""

from __future__ import annotations

import base64
import html
from datetime import date, timedelta
from io import BytesIO
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

import streamlit as st
import streamlit.components.v1 as components

from app.auth import current_profile, current_role, effective_role
from app.components.status import status_pill_html
from app.services.job_weekly_timesheets import monday_of_week, week_bounds
from app.services.weekly_job_timesheet_service import (
    TIMESHEET_TABLE_MISSING_MSG,
    TimesheetLine,
    WeeklyJobTimesheetData,
    build_timesheet_data,
    build_timesheet_pdf_bytes,
    fetch_timesheet_by_job_week,
    get_job_timesheet_header,
    list_timesheets_for_job,
    load_timesheet_data,
    render_timesheet_html,
    save_timesheet,
    signed_url_for_timesheet,
    timesheet_table_available,
)
from app.services.job_updates_service import (
    DAILY_UPDATES_MISSING_MSG,
    daily_updates_table_available,
)
from app.services.weekly_timesheet_service import (
    mark_timesheet_sent,
    timesheet_is_locked,
    void_timesheet,
)
from app.utils.permissions import can_manage_weekly_timesheets


def _pandas():
    import pandas as pd

    return pd


try:
    from streamlit_drawable_canvas import st_canvas
except ImportError:
    st_canvas = None  # type: ignore[misc, assignment]

_DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_LABOR_COLS = ["employee_equipment", "class_name"] + _DAY_KEYS + ["st_hours", "ot_hours"]
_MAT_COLS = ["description", "qty", "cost"]


def _session_data_key(job_id: str, week_start: date) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in job_id)
    return f"wjt_data_{safe}_{week_start.isoformat()}"


def _week_start_key(key_prefix: str) -> str:
    return f"{key_prefix}_week_start"


def _week_picker_key(key_prefix: str) -> str:
    return f"{key_prefix}_week_picker"


def _init_week_state(key_prefix: str) -> None:
    state_key = _week_start_key(key_prefix)
    legacy_keys = (f"{key_prefix}_week", "wjt_page_week")
    if state_key not in st.session_state:
        for legacy_key in legacy_keys:
            legacy = st.session_state.get(legacy_key)
            if isinstance(legacy, date):
                st.session_state[state_key] = monday_of_week(legacy)
                break
    if state_key not in st.session_state:
        st.session_state[state_key] = monday_of_week(date.today())


def _sync_week_picker(key_prefix: str, week_start: date) -> None:
    picker_key = _week_picker_key(key_prefix)
    if picker_key in st.session_state:
        st.session_state[picker_key] = week_start


def _previous_week(key_prefix: str) -> None:
    state_key = _week_start_key(key_prefix)
    cur = st.session_state.get(state_key, monday_of_week(date.today()))
    if not isinstance(cur, date):
        cur = monday_of_week(date.today())
    new_start = monday_of_week(cur) - timedelta(days=7)
    st.session_state[state_key] = new_start
    _sync_week_picker(key_prefix, new_start)


def _current_week(key_prefix: str) -> None:
    state_key = _week_start_key(key_prefix)
    new_start = monday_of_week(date.today())
    st.session_state[state_key] = new_start
    _sync_week_picker(key_prefix, new_start)


def _next_week(key_prefix: str) -> None:
    state_key = _week_start_key(key_prefix)
    cur = st.session_state.get(state_key, monday_of_week(date.today()))
    if not isinstance(cur, date):
        cur = monday_of_week(date.today())
    new_start = monday_of_week(cur) + timedelta(days=7)
    st.session_state[state_key] = new_start
    _sync_week_picker(key_prefix, new_start)


def _week_picker_changed(key_prefix: str) -> None:
    picker_key = _week_picker_key(key_prefix)
    state_key = _week_start_key(key_prefix)
    picked = st.session_state.get(picker_key)
    if isinstance(picked, date):
        mon = monday_of_week(picked)
        st.session_state[state_key] = mon
        if mon != picked:
            st.session_state[picker_key] = mon


def _lines_to_labor_df(lines: list[TimesheetLine]) -> pd.DataFrame:
    pd = _pandas()
    rows = []
    for ln in lines:
        if ln.line_type not in {"labor", "equipment"}:
            continue
        rows.append(
            {
                "employee_equipment": ln.description,
                "class_name": ln.class_name,
                "mon": ln.mon,
                "tue": ln.tue,
                "wed": ln.wed,
                "thu": ln.thu,
                "fri": ln.fri,
                "sat": ln.sat,
                "sun": ln.sun,
                "st_hours": ln.st_hours,
                "ot_hours": ln.ot_hours + ln.dt_hours,
            }
        )
    if not rows:
        rows.append({c: ("" if c in ("employee_equipment", "class_name") else 0.0) for c in _LABOR_COLS})
    return pd.DataFrame(rows)


def _lines_to_material_df(lines: list[TimesheetLine]) -> pd.DataFrame:
    pd = _pandas()
    rows = []
    for ln in lines:
        if ln.line_type not in {"material", "expense"}:
            continue
        rows.append({"description": ln.description, "qty": ln.qty, "cost": ln.cost})
    if not rows:
        rows.append({"description": "", "qty": 0.0, "cost": 0.0})
    return pd.DataFrame(rows)


def _labor_df_to_lines(df: pd.DataFrame) -> list[TimesheetLine]:
    lines: list[TimesheetLine] = []
    for rec in df.to_dict("records"):
        emp = str(rec.get("employee_equipment") or "").strip()
        cls = str(rec.get("class_name") or "").strip()
        if not emp and not cls and all(float(rec.get(k) or 0) == 0 for k in _DAY_KEYS + ["st_hours", "ot_hours"]):
            continue
        ln = TimesheetLine(line_type="labor", description=emp, class_name=cls)
        for k in _DAY_KEYS:
            setattr(ln, k, float(rec.get(k) or 0))
        ln.st_hours = float(rec.get("st_hours") or 0)
        ln.ot_hours = float(rec.get("ot_hours") or 0)
        lines.append(ln)
    return lines or [TimesheetLine(line_type="labor")]


def _material_df_to_lines(df: pd.DataFrame) -> list[TimesheetLine]:
    lines: list[TimesheetLine] = []
    for rec in df.to_dict("records"):
        desc = str(rec.get("description") or "").strip()
        qty = float(rec.get("qty") or 0)
        cost = float(rec.get("cost") or 0)
        if not desc and qty == 0 and cost == 0:
            continue
        lines.append(TimesheetLine(line_type="material", description=desc, qty=qty, cost=cost))
    return lines or [TimesheetLine(line_type="material")]


def _signature_from_canvas(canvas_result) -> str:
    if canvas_result is None or canvas_result.image_data is None:
        return ""
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return ""
    arr = canvas_result.image_data
    if arr.size == 0 or not np.any(arr[:, :, 3] > 0):
        return ""
    rgb = arr[:, :, :3].astype("uint8")
    img = Image.fromarray(rgb)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _compose_data_from_session(job_id: str, week_start: date) -> WeeklyJobTimesheetData | None:
    pd = _pandas()
    key = _session_data_key(job_id, week_start)
    raw = st.session_state.get(key)
    if not isinstance(raw, dict):
        return None
    labor_df = st.session_state.get(f"{key}_labor")
    mat_df = st.session_state.get(f"{key}_material")
    if not isinstance(labor_df, pd.DataFrame) or not isinstance(mat_df, pd.DataFrame):
        return None
    ws, we = week_bounds(monday_of_week(week_start))
    return WeeklyJobTimesheetData(
        job_id=job_id,
        job_number=str(raw.get("job_number") or ""),
        client_name=str(raw.get("client_name") or ""),
        job_name=str(raw.get("job_name") or ""),
        po_number=str(raw.get("po_number") or ""),
        sheet_date=str(raw.get("sheet_date") or we.isoformat()),
        week_start=ws.isoformat(),
        week_end=we.isoformat(),
        approved_by=str(raw.get("approved_by") or ""),
        work_performed=str(raw.get("work_performed") or ""),
        status=str(raw.get("status") or "Draft"),
        signature_data=str(raw.get("signature_data") or ""),
        labor_lines=_labor_df_to_lines(labor_df),
        material_lines=_material_df_to_lines(mat_df),
    )


def _store_session_data(data: WeeklyJobTimesheetData) -> None:
    ws = monday_of_week(_parse_date(data.week_start) or date.today())
    key = _session_data_key(data.job_id, ws)
    st.session_state[key] = {
        "job_number": data.job_number,
        "client_name": data.client_name,
        "job_name": data.job_name,
        "po_number": data.po_number,
        "sheet_date": data.sheet_date,
        "approved_by": data.approved_by,
        "work_performed": data.work_performed,
        "status": data.status,
        "signature_data": data.signature_data,
    }
    st.session_state[f"{key}_labor"] = _lines_to_labor_df(data.labor_lines)
    st.session_state[f"{key}_material"] = _lines_to_material_df(data.material_lines)


def _load_context_key(key_prefix: str) -> str:
    return f"{key_prefix}_loaded_context"


def _load_timesheet_from_sources(
    job_id: str,
    week_start: date,
    *,
    preserve_header: dict[str, Any] | None = None,
) -> None:
    hdr = preserve_header or {}
    try:
        data = build_timesheet_data(
            job_id,
            week_start,
            po_number=str(hdr.get("po_number") or ""),
            approved_by=str(hdr.get("approved_by") or ""),
            work_performed=str(hdr.get("work_performed") or ""),
        )
        _store_session_data(data)
    except Exception:
        _store_header_only_draft(job_id, week_start)


def _sync_timesheet_for_job_week(
    job_id: str,
    week_start: date,
    *,
    key_prefix: str,
    locked: bool,
    existing_row: dict[str, Any] | None,
) -> None:
    """Auto-load labor/materials when the selected job or week changes."""
    context = f"{job_id}|{monday_of_week(week_start).isoformat()}"
    context_key = _load_context_key(key_prefix)
    if locked and existing_row:
        loaded = load_timesheet_data(str(existing_row["id"]))
        if loaded:
            _store_session_data(loaded)
        st.session_state[context_key] = context
        return
    if st.session_state.get(context_key) == context:
        sk = _session_data_key(job_id, week_start)
        if sk in st.session_state:
            return
    sk = _session_data_key(job_id, week_start)
    preserve = st.session_state.get(sk, {}) if isinstance(st.session_state.get(sk), dict) else {}
    _load_timesheet_from_sources(job_id, week_start, preserve_header=preserve)
    st.session_state[context_key] = context


def _store_header_only_draft(job_id: str, week_start: date) -> None:
    ws = monday_of_week(week_start)
    _, we = week_bounds(ws)
    header = get_job_timesheet_header(job_id, ws)
    data = WeeklyJobTimesheetData(
        job_id=job_id,
        job_number=str(header.get("job_number") or ""),
        client_name=str(header.get("client_name") or ""),
        job_name=str(header.get("job_name") or ""),
        po_number=str(header.get("po_number") or ""),
        sheet_date=str(header.get("sheet_date") or we.isoformat()),
        week_start=str(header.get("week_start") or ws.isoformat()),
        week_end=str(header.get("week_end") or we.isoformat()),
        labor_lines=[TimesheetLine(line_type="labor")],
        material_lines=[TimesheetLine(line_type="material")],
    )
    _store_session_data(data)


def _parse_date(v: Any) -> date | None:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _timesheet_row_totals(row: dict[str, Any]) -> tuple[float, float]:
    snap = row.get("locked_snapshot")
    if isinstance(snap, dict):
        labor = snap.get("labor_lines") or []
        mats = snap.get("material_lines") or []
        hours = round(sum(float(ln.get("st_hours") or 0) + float(ln.get("ot_hours") or 0) + float(ln.get("dt_hours") or 0) for ln in labor), 2)
        mat_total = round(sum(float(ln.get("cost") or 0) for ln in mats), 2)
        return hours, mat_total
    tid = str(row.get("id") or "")
    data = load_timesheet_data(tid) if tid else None
    if not data:
        return 0.0, 0.0
    hours = round(sum(ln.total_hours for ln in data.labor_lines), 2)
    mat_total = round(sum(ln.cost for ln in data.material_lines), 2)
    return hours, mat_total


def _render_saved_timesheets_table(job_id: str, *, key_prefix: str, week_start: date) -> None:
    rows = sorted(list_timesheets_for_job(job_id), key=lambda r: str(r.get("week_start") or ""), reverse=True)
    st.markdown("**Saved weekly timesheets**")
    if not rows:
        st.caption("No saved timesheets yet. Select a week and click **Generate Weekly Timesheet**.")
        return
    head = (
        "<div class='ips-data-table-wrap'><div class='ips-data-table-html'>"
        "<div class='ips-data-row ips-data-table-header' style='grid-template-columns:1.1fr 0.8fr 0.7fr 0.9fr 1fr 0.9fr 1.4fr;'>"
        "<span>Week</span><span>Status</span><span>Total Hrs</span><span>Mat/Exp</span>"
        "<span>Approved By</span><span>Approved Date</span><span>Actions</span></div>"
    )
    body_parts: list[str] = []
    for row in rows:
        ws = str(row.get("week_start") or "")[:10]
        status = str(row.get("status") or "Draft")
        hours, mat_total = _timesheet_row_totals(row)
        approved = str(row.get("approved_by_name") or row.get("approved_by") or "—")
        approved_dt = str(row.get("approved_at") or row.get("signed_at") or "")[:10] or "—"
        pill = status_pill_html(status)
        body_parts.append(
            f"<div class='ips-data-row' style='grid-template-columns:1.1fr 0.8fr 0.7fr 0.9fr 1fr 0.9fr 1.4fr;'>"
            f"<span>{ws}</span><span>{pill}</span><span>{hours:g}</span><span>${mat_total:,.2f}</span>"
            f"<span>{approved}</span><span>{approved_dt}</span><span>Open week below</span></div>"
        )
    st.markdown(head + "".join(body_parts) + "</div></div>", unsafe_allow_html=True)

    act_cols = st.columns(min(len(rows), 4) or 1)
    for i, row in enumerate(rows[:4]):
        tid = str(row.get("id") or "")
        ws = str(row.get("week_start") or "")[:10]
        pdf = str(row.get("pdf_path") or row.get("pdf_file_url") or "")
        excel = str(row.get("excel_path") or row.get("excel_url") or "")
        with act_cols[i % len(act_cols)]:
            st.caption(f"Week {ws}")
            if pdf:
                url = signed_url_for_timesheet(pdf)
                if url:
                    st.link_button("PDF", url, key=f"{key_prefix}_pdf_{tid}", use_container_width=True)
            if excel:
                url = signed_url_for_timesheet(excel)
                if url:
                    st.link_button("Excel", url, key=f"{key_prefix}_xls_{tid}", use_container_width=True)
            if can_manage_weekly_timesheets(effective_role()) and not timesheet_is_locked(row):
                if st.button("Mark Sent", key=f"{key_prefix}_sent_{tid}", use_container_width=True):
                    mark_timesheet_sent(tid)
                    st.rerun()
            if can_manage_weekly_timesheets(effective_role()) and status not in {"Approved", "Signed", "Voided"}:
                if st.button("Void", key=f"{key_prefix}_void_{tid}", use_container_width=True):
                    void_timesheet(tid)
                    st.rerun()


def render_weekly_timesheet_builder(
    *,
    job_options: dict[str, str] | None = None,
    default_job_id: str = "",
    default_week_start: date | None = None,
    fixed_job_id: str = "",
    embedded: bool = False,
    key_prefix: str = "wjt",
) -> None:
    """IPS weekly timesheet builder — job/week controls, editable grid, preview, PDF/Excel."""
    kp = key_prefix
    role = effective_role()
    if not can_manage_weekly_timesheets(role):
        st.info("Weekly job timesheets can be generated by Admin, Supervisor, and Project Manager roles.")
        return

    if not timesheet_table_available(force=True):
        st.error(TIMESHEET_TABLE_MISSING_MSG)
        return

    jobs = job_options or {"": ""}
    job_id = str(fixed_job_id or "").strip()

    today_mon = monday_of_week(date.today())
    _init_week_state(kp)
    state_key = _week_start_key(kp)
    picker_key = _week_picker_key(kp)
    if default_week_start is not None and f"{kp}_week_prefilled" not in st.session_state:
        ws_seed = monday_of_week(default_week_start)
        st.session_state[state_key] = ws_seed
        st.session_state[picker_key] = ws_seed
        st.session_state[f"{kp}_week_prefilled"] = True
    week_start = st.session_state.get(state_key, today_mon)
    if not isinstance(week_start, date):
        week_start = today_mon
        st.session_state[state_key] = week_start
    week_start = monday_of_week(week_start)
    _, we = week_bounds(week_start)

    st.markdown('<span class="ips-wjt-toolbar-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
    wc1, wc2, wc3, wc4, wc5 = st.columns([0.85, 0.9, 0.85, 1.1, 1.35], gap="small")
    wc1.button(
        "◀ Previous Week",
        key=f"{kp}_prev",
        on_click=_previous_week,
        args=(kp,),
    )
    wc2.button(
        "Current Week",
        key=f"{kp}_curr",
        on_click=_current_week,
        args=(kp,),
    )
    wc3.button(
        "Next Week ▶",
        key=f"{kp}_next",
        on_click=_next_week,
        args=(kp,),
    )
    with wc4:
        st.markdown(
            f'<p class="ips-wjt-week-end">Week ending <strong>{html.escape(we.isoformat())}</strong></p>',
            unsafe_allow_html=True,
        )
    with wc5:
        st.date_input(
            "Week starting (Mon)",
            value=week_start,
            key=picker_key,
            on_change=_week_picker_changed,
            args=(kp,),
        )
    week_start = monday_of_week(st.session_state[state_key])
    _, we = week_bounds(week_start)

    if not job_id:
        job_labels = sorted((k for k in jobs if k), key=str.casefold)
        labels = [""] + job_labels
        default_label = ""
        for lab, jid in jobs.items():
            if str(jid) == str(default_job_id):
                default_label = lab
                break
        pick = st.selectbox(
            "Job",
            labels,
            index=labels.index(default_label) if default_label in labels else 0,
            key=f"{kp}_job",
            help=f"{len(job_labels)} job(s) available",
        )
        job_id = str(jobs.get(pick) or "").strip()

    if not job_id:
        st.info("Select a job to build a weekly timesheet.")
        return

    if not daily_updates_table_available(force=True):
        st.caption(DAILY_UPDATES_MISSING_MSG)

    if embedded or fixed_job_id:
        _render_saved_timesheets_table(job_id, key_prefix=kp, week_start=week_start)

    existing_row = fetch_timesheet_by_job_week(job_id, week_start)
    locked = timesheet_is_locked(existing_row)

    act1, act2, act3, act4 = st.columns(4, gap="small")
    if act1.button("Generate Weekly Timesheet", type="primary", use_container_width=True, key=f"{kp}_generate", disabled=locked):
        try:
            data = build_timesheet_data(job_id, week_start)
            _store_session_data(data)
            st.success("Timesheet draft generated from job, timekeeping, materials, and notes.")
            st.rerun()
        except Exception as exc:
            st.warning(f"Could not generate full timesheet: {exc}")
            _store_header_only_draft(job_id, week_start)
            st.rerun()
    if act2.button("Reload from timekeeping", use_container_width=True, key=f"{kp}_reload", disabled=locked):
        sk = _session_data_key(job_id, week_start)
        hdr = st.session_state.get(sk, {})
        _load_timesheet_from_sources(job_id, week_start, preserve_header=hdr if isinstance(hdr, dict) else {})
        st.success("Loaded labor, equipment, materials, and work performed.")
        st.rerun()
    if act3.button("Load saved", use_container_width=True, key=f"{kp}_load_saved"):
        row = fetch_timesheet_by_job_week(job_id, week_start)
        if not row:
            st.warning("No saved timesheet for this job and week.")
        else:
            loaded = load_timesheet_data(str(row["id"]))
            if loaded:
                _store_session_data(loaded)
                st.success("Loaded saved timesheet.")
                st.rerun()
    if act4.button("Clear grids", use_container_width=True, key=f"{kp}_clear"):
        sk = _session_data_key(job_id, week_start)
        st.session_state[f"{sk}_labor"] = _lines_to_labor_df([TimesheetLine(line_type="labor")])
        st.session_state[f"{sk}_material"] = _lines_to_material_df([TimesheetLine(line_type="material")])
        st.rerun()

    if locked:
        st.warning("This timesheet is approved/signed and locked. Void it to regenerate, or contact an admin.")

    _sync_timesheet_for_job_week(
        job_id,
        week_start,
        key_prefix=kp,
        locked=locked,
        existing_row=existing_row,
    )

    sk = _session_data_key(job_id, week_start)
    hdr = st.session_state.get(sk, {})
    if not str(hdr.get("job_number") or "").strip():
        hdr.update(get_job_timesheet_header(job_id, week_start))
        st.session_state[sk] = hdr

    h1, h2, h3, h4, h5 = st.columns(5, gap="small")
    hdr["job_number"] = h1.text_input("JOB #", value=str(hdr.get("job_number") or ""), key=f"{kp}_job_num", disabled=locked)
    hdr["client_name"] = h2.text_input("CLIENT", value=str(hdr.get("client_name") or ""), key=f"{kp}_client", disabled=locked)
    hdr["job_name"] = h3.text_input("JOB NAME", value=str(hdr.get("job_name") or ""), key=f"{kp}_jname", disabled=locked)
    hdr["po_number"] = h4.text_input("P.O. #", value=str(hdr.get("po_number") or ""), key=f"{kp}_po", disabled=locked)
    hdr["sheet_date"] = h5.text_input("DATE", value=str(hdr.get("sheet_date") or we.isoformat()), key=f"{kp}_sdate", disabled=locked)
    st.session_state[sk] = hdr

    labor_df = st.session_state.get(f"{sk}_labor", _lines_to_labor_df([TimesheetLine(line_type="labor")]))
    st.markdown("**Labor / equipment**")
    labor_edited = st.data_editor(
        labor_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        disabled=locked,
        key=f"{kp}_labor_editor",
        column_config={
            "employee_equipment": st.column_config.TextColumn("Employee / Equipment", width="large"),
            "class_name": st.column_config.TextColumn("Class", width="medium"),
            **{k: st.column_config.NumberColumn(k.upper(), format="%.2f", step=0.25) for k in _DAY_KEYS},
            "st_hours": st.column_config.NumberColumn("ST", format="%.2f"),
            "ot_hours": st.column_config.NumberColumn("OT", format="%.2f"),
        },
    )
    st.session_state[f"{sk}_labor"] = labor_edited
    if labor_edited.empty or (
        len(labor_edited) == 1
        and not str(labor_edited.iloc[0].get("employee_equipment") or "").strip()
    ):
        st.caption("No labor rows found from timekeeping.")

    mat_df = st.session_state.get(f"{sk}_material", _lines_to_material_df([TimesheetLine(line_type="material")]))
    st.markdown("**Materials / expenses**")
    mat_edited = st.data_editor(
        mat_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        disabled=locked,
        key=f"{kp}_mat_editor",
        column_config={
            "description": st.column_config.TextColumn("Description", width="large"),
            "qty": st.column_config.NumberColumn("Qty", format="%.2f"),
            "cost": st.column_config.NumberColumn("Cost", format="%.2f"),
        },
    )
    st.session_state[f"{sk}_material"] = mat_edited
    if mat_edited.empty or (
        len(mat_edited) == 1
        and not str(mat_edited.iloc[0].get("description") or "").strip()
    ):
        st.caption("No materials or expenses found for this week.")

    hdr["work_performed"] = st.text_area(
        "Work performed",
        value=str(hdr.get("work_performed") or ""),
        height=90,
        key=f"{kp}_work",
        disabled=locked,
    )
    hdr["approved_by"] = st.text_input("Approved by", value=str(hdr.get("approved_by") or ""), key=f"{kp}_approved", disabled=locked)
    st.session_state[sk] = hdr
    if not str(hdr.get("work_performed") or "").strip() and daily_updates_table_available():
        st.caption("No daily updates found for this week. Work performed can be entered manually.")

    st.markdown("**Customer signature**")
    sig_mode = st.radio("Sign mode", ["Digital signature", "Print & sign manually"], horizontal=True, key=f"{kp}_sig_mode")
    sig_data = str(hdr.get("signature_data") or "")
    if sig_mode == "Digital signature":
        if st_canvas is not None:
            canvas = st_canvas(
                fill_color="rgba(255,255,255,0)",
                stroke_width=2,
                stroke_color="#000000",
                background_color="#ffffff",
                height=160,
                width=700,
                drawing_mode="freedraw",
                key=f"{kp}_canvas",
            )
            sig_data = _signature_from_canvas(canvas) or sig_data
        else:
            up = st.file_uploader("Upload signature image (PNG)", type=["png"], key=f"{kp}_sig_up")
            if up:
                sig_data = "data:image/png;base64," + base64.b64encode(up.read()).decode("ascii")
    hdr["signature_data"] = sig_data
    st.session_state[sk] = hdr

    data = _compose_data_from_session(job_id, week_start)
    if not data:
        st.error("Could not compose timesheet data.")
        return

    existing = existing_row or fetch_timesheet_by_job_week(job_id, week_start)
    if existing:
        st.markdown(status_pill_html(str(existing.get("status") or "Draft")), unsafe_allow_html=True)
        token = str(existing.get("sign_token") or "").strip()
        if token:
            try:
                from app.config import settings
                base = str(getattr(settings, "app_base_url", "") or "").strip().rstrip("/")
            except ImportError:
                base = ""
            sign_link = f"{base}/?tsign={token}" if base else f"?tsign={token}"
            st.text_input("Customer signing link", value=sign_link, key=f"{kp}_sign_link")

    p1, p2, p3, p4, p5, p6 = st.columns(6, gap="small")
    preview = p1.button("Preview", type="primary", use_container_width=True, key=f"{kp}_preview")
    p2.download_button(
        "Download PDF",
        data=build_timesheet_pdf_bytes(data),
        file_name=f"weekly_timesheet_{data.job_number}_{week_start.isoformat()}.pdf",
        mime="application/pdf",
        use_container_width=True,
        key=f"{kp}_pdf",
    )
    try:
        from app.services.weekly_timesheet_export_service import export_data_to_excel_bytes

        xls_bytes = export_data_to_excel_bytes(data)
    except Exception:
        xls_bytes = b""
    if xls_bytes:
        p3.download_button(
            "Download Excel",
            data=xls_bytes,
            file_name=f"weekly_timesheet_{data.job_number}_{week_start.isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"{kp}_xlsx",
        )
    if p4.button("Print", use_container_width=True, key=f"{kp}_print"):
        st.session_state[f"{kp}_show_preview"] = True
    save_draft = p5.button("Save draft", use_container_width=True, key=f"{kp}_save", disabled=locked)
    finalize = p6.button("Approve / Lock", use_container_width=True, key=f"{kp}_finalize", disabled=locked)

    if save_draft or finalize:
        try:
            prof = current_profile()
            uid = str(prof.get("id") or "")
            if finalize:
                data.status = "Approved"
                if data.signature_data:
                    data.signed_at = date.today().isoformat()
                row = save_timesheet(data, created_by=uid, lock=True)
                from app.services.weekly_timesheet_service import _register_timesheet_documents
                _register_timesheet_documents(str(row.get("id")))
                st.success("Timesheet approved and locked.")
            else:
                data.status = "Generated"
                row = save_timesheet(data, created_by=uid, lock=False)
                st.success("Timesheet draft saved.")
            pdf_path = str(row.get("pdf_path") or row.get("pdf_file_url") or "")
            if pdf_path:
                url = signed_url_for_timesheet(pdf_path)
                if url:
                    st.markdown(f"[Open saved PDF]({url})")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    if preview or st.session_state.get(f"{kp}_show_preview"):
        st.session_state[f"{kp}_show_preview"] = True
        html_doc = render_timesheet_html(data, week_start=week_start, embed=True)
        st.markdown('<span class="ips-wt-preview-frame-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
        components.html(html_doc, height=1140, scrolling=True)
        st.download_button(
            "Download HTML preview",
            data=html_doc,
            file_name=f"weekly_timesheet_{data.job_number}_{week_start.isoformat()}.html",
            mime="text/html",
            key=f"{kp}_html_dl",
        )
        st.caption("Use browser Print on the preview for a print-friendly copy.")

    if not embedded and not fixed_job_id:
        _render_saved_timesheets_table(job_id, key_prefix=kp, week_start=week_start)


def _render_saved_list(job_id: str, *, key_prefix: str) -> None:
    _render_saved_timesheets_table(job_id, key_prefix=key_prefix, week_start=monday_of_week(date.today()))
