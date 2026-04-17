from __future__ import annotations

import base64
from collections import defaultdict
from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

try:
    from streamlit_drawable_canvas import st_canvas
except ImportError:  # pragma: no cover
    st_canvas = None  # type: ignore[misc, assignment]

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[misc, assignment]

try:
    from auth import current_profile, current_role
    from branding import render_header
    from db import (
        delete_rows_admin,
        fetch_one,
        fetch_table,
        get_admin_client,
        insert_row_admin,
        update_rows_admin,
    )
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import (  # type: ignore
        delete_rows_admin,
        fetch_one,
        fetch_table,
        get_admin_client,
        insert_row_admin,
        update_rows_admin,
    )

try:
    from app.ips_crud_list_styles import render_crud_list_subtitle
except ImportError:
    from ips_crud_list_styles import render_crud_list_subtitle  # type: ignore

try:
    from services.job_service import job_display_primary, job_row_select_label
except ImportError:
    from app.services.job_service import job_display_primary, job_row_select_label  # type: ignore

try:
    from table_actions import (
        IPS_PENDING_DELETE,
        TABLE_KEY_TIMESHEETS,
        clear_selected_ids,
        render_selectable_dataframe,
        render_selection_action_bar,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_TIMESHEETS,
        clear_selected_ids,
        render_selectable_dataframe,
        render_selection_action_bar,
    )


def _lines_to_grid_records(lines: list[dict]) -> list[dict]:
    loaded: list[dict] = []
    for ln in lines:
        loaded.append(
            {
                "employee_equipment": str(ln.get("employee_equipment", "") or ""),
                "class_name": str(ln.get("class_name", "") or ""),
                "mon": float(ln.get("hours_mon", 0) or 0),
                "tue": float(ln.get("hours_tue", 0) or 0),
                "wed": float(ln.get("hours_wed", 0) or 0),
                "thu": float(ln.get("hours_thu", 0) or 0),
                "fri": float(ln.get("hours_fri", 0) or 0),
                "sat": float(ln.get("hours_sat", 0) or 0),
                "sun": float(ln.get("hours_sun", 0) or 0),
            }
        )
    return loaded


def _fetch_weekly_timesheet_by_job_week(job_id: str, week_start: date) -> dict | None:
    r = (
        get_admin_client()
        .table("weekly_timesheets")
        .select("*")
        .eq("job_id", job_id)
        .eq("week_start", week_start.isoformat())
        .limit(1)
        .execute()
    )
    rows = r.data or []
    return rows[0] if rows else None


def _fetch_timesheet_lines(timesheet_id: str) -> list[dict]:
    r = (
        get_admin_client()
        .table("weekly_timesheet_lines")
        .select("*")
        .eq("timesheet_id", timesheet_id)
        .execute()
    )
    lines = r.data or []
    return sorted(lines, key=lambda x: int(x.get("sort_order", 0) or 0))

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_LABELS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _parse_date(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    s = str(val).strip()[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _monday_of_week(d: date) -> date:
    """Week starting Monday containing date d."""
    return d - timedelta(days=d.weekday())


def _week_range(week_start: date) -> list[date]:
    return [week_start + timedelta(days=i) for i in range(7)]


def _build_rows_from_time_entries(
    entries: list[dict],
    week_start: date,
    job_id: str,
    employees_by_id: dict[str, dict] | None = None,
    grid_entries: list[dict] | None = None,
) -> list[dict]:
    week_end = week_start + timedelta(days=6)
    buckets: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0] * 7)
    emp_map = employees_by_id or {}

    for e in entries:
        if str(e.get("job_id") or "") != str(job_id):
            continue
        ed = _parse_date(e.get("entry_date"))
        if ed is None or ed < week_start or ed > week_end:
            continue
        idx = (ed - week_start).days
        if idx < 0 or idx > 6:
            continue
        eid = e.get("employee_id")
        if eid and str(eid) in emp_map:
            emp = str(emp_map[str(eid)].get("name") or "").strip() or "Unknown"
        else:
            emp = str(e.get("employee_name", "") or "").strip() or "Unknown"
        cls = str(e.get("labor_classification", "") or "").strip() or ""
        h = float(e.get("straight_time_hours", 0) or 0) + float(e.get("overtime_hours", 0) or 0)
        key = (emp, cls)
        buckets[key][idx] += h

    for g in grid_entries or []:
        if str(g.get("job_id") or "") != str(job_id):
            continue
        ed = _parse_date(g.get("work_date"))
        if ed is None or ed < week_start or ed > week_end:
            continue
        di = (ed - week_start).days
        if di < 0 or di > 6:
            continue
        geid = g.get("employee_id")
        if geid and str(geid) in emp_map:
            gemp = str(emp_map[str(geid)].get("name") or "").strip() or "Unknown"
        else:
            gemp = "Unknown"
        gcls = "Weekly grid"
        gh = float(g.get("hours", 0) or 0)
        gkey = (gemp, gcls)
        buckets[gkey][di] += gh

    rows: list[dict] = []
    for (emp, cls), hrs in sorted(buckets.items(), key=lambda x: (x[0][0].lower(), x[0][1].lower())):
        row = {"employee_equipment": emp, "class_name": cls}
        for i, k in enumerate(DAY_KEYS):
            row[k] = round(hrs[i], 2)
        rows.append(row)

    if not rows:
        rows.append(
            {
                "employee_equipment": "",
                "class_name": "",
                **{k: 0.0 for k in DAY_KEYS},
            }
        )
    return rows


def _rows_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    cols = ["employee_equipment", "class_name"] + DAY_KEYS
    if not rows:
        return pd.DataFrame([{c: "" if c in ("employee_equipment", "class_name") else 0.0 for c in cols}])
    return pd.DataFrame(rows)


def _signature_b64(canvas_result) -> str | None:
    if canvas_result is None or canvas_result.image_data is None or Image is None:
        return None
    arr = canvas_result.image_data
    if arr.size == 0 or not np.any(arr[:, :, 3] > 0):
        return None
    rgb = (arr[:, :, :3]).astype("uint8")
    img = Image.fromarray(rgb)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def render() -> None:
    render_header(
        "Weekly Timesheet",
        subtitle="Dense grid — same labor pool as Time Tracking",
    )

    if current_role() not in {"admin", "estimator", "project_manager"}:
        st.info("Only admin, estimator, or project manager users can use the weekly timesheet.")
        return

    render_crud_list_subtitle(
        "Hours can pull from **employee time entries**. Apply **sql/004_weekly_timesheets.sql** in Supabase before first save."
    )

    customers = fetch_table("customers", limit=5000, order_by="customer_name")
    jobs = fetch_table(
        "jobs",
        columns="id,customer_id,job_number,job_name,estimate_id",
        limit=5000,
        order_by="job_number",
    )
    estimates = fetch_table("estimates", columns="id,job_id,po_number", limit=5000)
    time_entries = fetch_table("employee_time_entries", limit=10000, order_by="entry_date")
    try:
        wt_emp_rows = fetch_table("employees", limit=5000, order_by="name")
    except Exception:
        wt_emp_rows = []
    wt_employees_by_id = {str(e.get("id")): e for e in wt_emp_rows if e.get("id")}
    try:
        all_grid_te = fetch_table("time_entries", limit=50000, order_by="work_date")
    except Exception:
        all_grid_te = []

    customer_name_by_id = {c.get("id"): str(c.get("customer_name", "") or "") for c in customers}
    job_by_id = {j.get("id"): j for j in jobs}
    est_by_job: dict[Any, Any] = {}
    for e in estimates:
        jid = e.get("job_id")
        if jid and jid not in est_by_job:
            est_by_job[jid] = e

    sv_id = st.session_state.get("wt_saved_view_id")
    if sv_id:
        hr = fetch_one("weekly_timesheets", {"id": sv_id})
        if not hr:
            st.session_state.pop("wt_saved_view_id", None)
        else:
            st.subheader("Saved timesheet detail")
            cva, cvb = st.columns(2)
            with cva:
                st.markdown(f"**Week start:** {hr.get('week_start') or '—'}")
                st.markdown(f"**Job #:** {hr.get('job_number') or '—'}")
                st.markdown(f"**Client:** {hr.get('client_name') or '—'}")
            with cvb:
                st.markdown(f"**Job name:** {hr.get('job_name') or '—'}")
                st.markdown(f"**P.O. #:** {hr.get('po_number') or '—'}")
                st.markdown(f"**Sheet date:** {hr.get('sheet_date') or '—'}")
            if st.button("← Back to editor", use_container_width=True, key="wt_saved_view_back"):
                st.session_state.pop("wt_saved_view_id", None)
                st.rerun()
            st.divider()

    today = date.today()
    default_week = _monday_of_week(today)

    c0, c1, c2 = st.columns([1, 1, 2])
    week_start = c0.date_input("Week starting (Monday)", value=default_week, key="wt_week_start")
    if week_start.weekday() != 0:
        st.warning("Timesheet weeks are Monday–Sunday. Adjusting to the Monday of the selected week.")
        week_start = _monday_of_week(week_start)
    week_dates = _week_range(week_start)
    week_end = week_dates[-1]
    grid_week: list[dict] = []
    for g in all_grid_te:
        pd = _parse_date(g.get("work_date"))
        if pd is not None and week_start <= pd <= week_end:
            grid_week.append(g)
    c1.date_input("Week ending (Sunday)", value=week_end, disabled=True, key="wt_week_end_ro")

    job_options = {
        f'{job_row_select_label(j)} | {customer_name_by_id.get(j.get("customer_id"), "") or "—"}': j.get("id")
        for j in jobs
        if str(j.get("job_name", "")).strip() or str(j.get("job_number", "")).strip()
    }
    job_labels = [""] + sorted(job_options.keys())
    pick = c2.selectbox("Job (for JOB # / CLIENT / JOB NAME / P.O. #)", job_labels, key="wt_job_pick")

    pending_ts = st.session_state.pop("wt_pending_ts_load", None)
    if pending_ts:
        hdr_row = fetch_one("weekly_timesheets", {"id": pending_ts})
        if hdr_row:
            ws = _parse_date(hdr_row.get("week_start"))
            if ws:
                st.session_state["wt_week_start"] = ws
            jid_hdr = hdr_row.get("job_id")
            for lab, jido in job_options.items():
                if str(jido) == str(jid_hdr):
                    st.session_state["wt_job_pick"] = lab
                    break
            ts_uuid = hdr_row.get("id")
            lines = _fetch_timesheet_lines(str(ts_uuid)) if ts_uuid else []
            loaded = _lines_to_grid_records(lines)
            st.session_state["wt_grid_df"] = _rows_to_dataframe(loaded if loaded else [{}])
            st.session_state["wt_job_number"] = str(hdr_row.get("job_number", "") or "")
            st.session_state["wt_client"] = str(hdr_row.get("client_name", "") or "")
            st.session_state["wt_job_name"] = str(hdr_row.get("job_name", "") or "")
            st.session_state["wt_po"] = str(hdr_row.get("po_number", "") or "")
            sd = _parse_date(hdr_row.get("sheet_date"))
            wk_end = _week_range(ws)[-1] if ws else None
            st.session_state["wt_date_str"] = sd.isoformat() if sd else (wk_end.isoformat() if wk_end else "")
            st.rerun()

    job_id = job_options.get(pick) if pick else None
    job_row = job_by_id.get(job_id) if job_id else None

    job_name = str(job_row.get("job_name", "") or "") if job_row else ""
    job_number_for_header = job_display_primary(job_row) if job_row else ""
    client_name = customer_name_by_id.get(job_row.get("customer_id"), "") if job_row else ""
    est = est_by_job.get(job_id) if job_id else None
    po_number = str(est.get("po_number", "") or "") if est else ""

    if st.session_state.get("wt_sel_job") != pick:
        st.session_state["wt_sel_job"] = pick
        st.session_state["wt_job_number"] = job_number_for_header
        st.session_state["wt_client"] = client_name
        st.session_state["wt_job_name"] = job_name
        st.session_state["wt_po"] = po_number
        st.session_state["wt_date_str"] = week_end.isoformat()

    st.markdown("##### Timesheet header")
    h1, h2, h3, h4, h5 = st.columns(5)
    v_job_num = h1.text_input("JOB #", key="wt_job_number")
    v_client = h2.text_input("CLIENT", key="wt_client")
    v_job_name = h3.text_input("JOB NAME", key="wt_job_name")
    v_po = h4.text_input("P.O. #", key="wt_po")
    v_date = h5.text_input("DATE", key="wt_date_str")

    st.markdown("##### Hours grid")
    day_note = " · ".join(f"{lbl} {d.strftime('%m/%d')}" for lbl, d in zip(DAY_LABELS, week_dates))
    st.caption(day_note)

    if "wt_grid_df" not in st.session_state:
        st.session_state["wt_grid_df"] = _rows_to_dataframe(
            _build_rows_from_time_entries([], week_start, job_id or "", wt_employees_by_id, [])
        )

    ac1, ac2, ac3 = st.columns(3)
    if ac1.button("Load hours from time entries", use_container_width=True, disabled=not job_id):
        st.session_state["wt_grid_df"] = _rows_to_dataframe(
            _build_rows_from_time_entries(
                time_entries, week_start, str(job_id), wt_employees_by_id, grid_week
            )
        )
        st.success("Grid filled from employee time entries for this job and week.")
        st.rerun()

    if ac2.button("Load saved timesheet (this job & week)", use_container_width=True, disabled=not job_id):
        if not job_id:
            st.error("Select a job first.")
        else:
            hdr_row = _fetch_weekly_timesheet_by_job_week(str(job_id), week_start)
            if not hdr_row:
                st.warning("No saved timesheet for this job and week.")
            else:
                ts_id = hdr_row.get("id")
                lines = _fetch_timesheet_lines(str(ts_id))
                loaded = _lines_to_grid_records(lines)
                st.session_state["wt_grid_df"] = _rows_to_dataframe(loaded if loaded else [{}])
                hdr = hdr_row
                if hdr:
                    st.session_state["wt_job_number"] = str(hdr.get("job_number", "") or "")
                    st.session_state["wt_client"] = str(hdr.get("client_name", "") or "")
                    st.session_state["wt_job_name"] = str(hdr.get("job_name", "") or "")
                    st.session_state["wt_po"] = str(hdr.get("po_number", "") or "")
                    sd = _parse_date(hdr.get("sheet_date"))
                    st.session_state["wt_date_str"] = sd.isoformat() if sd else week_end.isoformat()
                st.success("Loaded saved timesheet.")
                st.rerun()

    if ac3.button("Clear grid", use_container_width=True):
        st.session_state["wt_grid_df"] = _rows_to_dataframe([{}])
        st.rerun()

    col_conf = {
        "employee_equipment": st.column_config.TextColumn("EMPLOYEE / EQUIPMENT RENTAL", width="large"),
        "class_name": st.column_config.TextColumn("CLASS", width="medium"),
    }
    for k, lbl in zip(DAY_KEYS, DAY_LABELS):
        col_conf[k] = st.column_config.NumberColumn(lbl, min_value=0.0, format="%.2f", step=0.25)

    edited = st.data_editor(
        st.session_state["wt_grid_df"],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="wt_editor",
        column_config=col_conf,
    )
    e2 = edited.copy()
    for k in DAY_KEYS:
        if k in e2.columns:
            e2[k] = pd.to_numeric(e2[k], errors="coerce").fillna(0.0)
    for tcol in ("employee_equipment", "class_name"):
        if tcol in e2.columns:
            e2[tcol] = e2[tcol].fillna("").astype(str)
    st.session_state["wt_grid_df"] = e2

    df = st.session_state["wt_grid_df"].copy()
    for k in DAY_KEYS:
        if k not in df.columns:
            df[k] = 0.0
        df[k] = pd.to_numeric(df[k], errors="coerce").fillna(0.0)

    df["row_total"] = df[DAY_KEYS].sum(axis=1)
    total_row = {k: float(df[k].sum()) for k in DAY_KEYS}
    grand = float(sum(total_row.values()))

    with st.expander("Row totals (per line)", expanded=False):
        rt = df[["employee_equipment", "class_name", "row_total"]].copy()
        rt = rt.rename(columns={"row_total": "TOTAL HRS"})
        st.dataframe(rt, use_container_width=True, hide_index=True)

    tc = st.columns(7)
    for i, k in enumerate(DAY_KEYS):
        tc[i].metric(f"Total {DAY_LABELS[i]}", f"{total_row[k]:.2f}")
    st.metric("Grand total (all days)", f"{grand:.2f}")

    st.markdown("##### Saved weekly timesheets")
    st.caption(
        "Action bar above the grid. Checkbox on the **left**; selection: **selected_timesheets_ids**."
    )
    saved_ts_rows = fetch_table("weekly_timesheets", limit=500, order_by="week_start")
    if not saved_ts_rows:
        st.info("No saved weekly timesheets yet.")
    else:
        srows: list[dict] = []
        for s in saved_ts_rows:
            srows.append(
                {
                    "id": s.get("id"),
                    "week_start": str(s.get("week_start") or "")[:10],
                    "job_number": s.get("job_number") or "",
                    "client_name": s.get("client_name") or "",
                    "job_name": s.get("job_name") or "",
                    "po_number": s.get("po_number") or "",
                    "sheet_date": str(s.get("sheet_date") or "")[:10],
                }
            )
        ts_df = pd.DataFrame(srows)
        search_ts = st.text_input(
            "Search saved timesheets",
            key="wt_ts_search",
            placeholder="Filter by week, job, client…",
        )
        if search_ts.strip():
            q = search_ts.strip().lower()
            mask = ts_df.astype(str).apply(lambda col: col.str.lower().str.contains(q, na=False))
            ts_df = ts_df[mask.any(axis=1)]
        if ts_df.empty:
            st.warning("No saved timesheets match your search.")
        elif "id" not in ts_df.columns:
            st.dataframe(ts_df, use_container_width=True, hide_index=True)
        else:
            show_ts = [
                c
                for c in [
                    "week_start",
                    "job_number",
                    "client_name",
                    "job_name",
                    "po_number",
                    "sheet_date",
                ]
                if c in ts_df.columns
            ]
            bar_ph = st.empty()
            _, sel = render_selectable_dataframe(
                ts_df,
                table_key=TABLE_KEY_TIMESHEETS,
                id_column="id",
                columns=show_ts,
                editor_key="wt_saved_sel_editor",
            )
            with bar_ph.container():
                actions = render_selection_action_bar(
                    TABLE_KEY_TIMESHEETS,
                    sel,
                    can_view=True,
                    can_edit=True,
                    can_delete=True,
                    export_df=ts_df,
                    visible_df=ts_df,
                    id_column="id",
                    export_filename="weekly_timesheets_export.csv",
                    view_label="View Timesheet",
                    edit_label="Edit Timesheet",
                    delete_label="Delete Timesheet",
                    delete_selected_label="Delete Selected",
                )
            if actions.get("view") and sel and len(sel) == 1:
                st.session_state["wt_saved_view_id"] = str(sel[0])
                st.rerun()
            if actions.get("edit") and sel and len(sel) == 1:
                st.session_state["wt_pending_ts_load"] = str(sel[0])
                st.session_state.pop("wt_saved_view_id", None)
                st.rerun()
            pend = st.session_state.get(IPS_PENDING_DELETE) or {}
            if actions.get("confirm_delete") and pend.get(TABLE_KEY_TIMESHEETS):
                for tid in pend[TABLE_KEY_TIMESHEETS]:
                    try:
                        delete_rows_admin("weekly_timesheets", {"id": tid})
                    except Exception as exc:
                        st.error(f"Could not delete {tid}: {exc}")
                pend.pop(TABLE_KEY_TIMESHEETS, None)
                clear_selected_ids(TABLE_KEY_TIMESHEETS)
                st.success("Delete completed where permitted.")
                st.rerun()

    st.markdown("##### Signature")
    sig_b64: str | None = None
    if st_canvas is not None:
        st.caption("Sign below (works with touch on mobile).")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=2,
            stroke_color="#000000",
            background_color="#ffffff",
            update_streamlit=True,
            height=220,
            width=800,
            drawing_mode="freedraw",
            key="wt_signature_canvas",
        )
        sig_b64 = _signature_b64(canvas_result)
    else:
        st.warning("Install `streamlit-drawable-canvas` for signature capture, or save without a signature.")

    if st.button("Save timesheet to Supabase", type="primary", use_container_width=True):
        if not job_id:
            st.error("Select a job before saving.")
            st.stop()
        df_save = st.session_state["wt_grid_df"].copy()
        for k in DAY_KEYS:
            if k in df_save.columns:
                df_save[k] = pd.to_numeric(df_save[k], errors="coerce").fillna(0.0)
        records = df_save.to_dict("records")
        lines_out: list[dict] = []
        for i, rec in enumerate(records):
            emp = str(rec.get("employee_equipment", "") or "").strip()
            cls = str(rec.get("class_name", "") or "").strip()
            if not emp and not cls and all(float(rec.get(k, 0) or 0) == 0 for k in DAY_KEYS):
                continue
            lines_out.append(
                {
                    "sort_order": i,
                    "employee_equipment": emp,
                    "class_name": cls,
                    "hours_mon": float(rec.get("mon", 0) or 0),
                    "hours_tue": float(rec.get("tue", 0) or 0),
                    "hours_wed": float(rec.get("wed", 0) or 0),
                    "hours_thu": float(rec.get("thu", 0) or 0),
                    "hours_fri": float(rec.get("fri", 0) or 0),
                    "hours_sat": float(rec.get("sat", 0) or 0),
                    "hours_sun": float(rec.get("sun", 0) or 0),
                }
            )

        header_payload = {
            "job_id": job_id,
            "job_number": v_job_num.strip(),
            "client_name": v_client.strip(),
            "job_name": v_job_name.strip(),
            "po_number": v_po.strip(),
            "sheet_date": (_parse_date(v_date) or week_end).isoformat(),
            "week_start": week_start.isoformat(),
            "signature_png_base64": sig_b64,
            "created_by": current_profile().get("id"),
            "updated_at": datetime.utcnow().isoformat(),
        }

        try:
            existing_row = _fetch_weekly_timesheet_by_job_week(str(job_id), week_start)
            if existing_row:
                ts_id = existing_row["id"]
                upd_payload = {k: v for k, v in header_payload.items() if k != "created_by"}
                update_rows_admin("weekly_timesheets", upd_payload, {"id": ts_id})
                delete_rows_admin("weekly_timesheet_lines", {"timesheet_id": ts_id})
            else:
                ins = insert_row_admin("weekly_timesheets", header_payload)
                ts_id = ins.get("id")

            for line in lines_out:
                insert_row_admin(
                    "weekly_timesheet_lines",
                    {"timesheet_id": ts_id, **line},
                )
            st.success("Timesheet saved.")
            st.rerun()
        except Exception as exc:  # pragma: no cover
            st.error(f"Save failed: {exc}. If tables are missing, run sql/004_weekly_timesheets.sql in Supabase.")

