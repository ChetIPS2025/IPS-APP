"""Field crew time entry — supervisor batch submit (Phase 1)."""

from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from auth import current_profile, current_role

try:
    from app.components.headers import render_page_brand_header
    from app.data_cache import fetch_table_for_session
    from app.db import fetch_jobs_with_order_fallback
    from app.mobile_ui import ensure_narrow_viewport_detected
    from app.services.field_crew_time import (
        TIME_TYPES,
        approve_batch_and_sync_time_entries,
        copy_yesterday_lines,
        fetch_batch_for_job_date,
        fetch_batch_lines,
        overtime_warnings,
        submit_batch,
        upsert_crew_time_batch,
    )
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from components.headers import render_page_brand_header  # type: ignore
    from data_cache import fetch_table_for_session  # type: ignore
    from db import fetch_jobs_with_order_fallback  # type: ignore
    from mobile_ui import ensure_narrow_viewport_detected  # type: ignore
    from services.field_crew_time import (  # type: ignore
        TIME_TYPES,
        approve_batch_and_sync_time_entries,
        copy_yesterday_lines,
        fetch_batch_for_job_date,
        fetch_batch_lines,
        overtime_warnings,
        submit_batch,
        upsert_crew_time_batch,
    )
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore


def _admin() -> bool:
    return current_role() in {"admin", "manager"}


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("field_crew_time"):
        return

    ensure_narrow_viewport_detected()
    st.markdown(
        '<span class="ips-field-crew-time-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    render_page_brand_header(
        "Crew Time",
        "Batch crew hours by job — ST, OT, DT, travel, and per diem.",
    )

    admin = _admin()
    prof = current_profile() or {}
    uid = str(prof.get("id") or "").strip() or None
    sup_name = str(prof.get("full_name") or prof.get("email") or "").strip()

    jobs = sort_jobs_by_number_then_name(
        list(fetch_jobs_with_order_fallback(limit=3000, use_admin=admin) or [])
    )
    if not jobs:
        st.warning("No jobs loaded.")
        return
    labels = [job_row_select_label(j) for j in jobs]
    ids = [str(j.get("id")) for j in jobs]
    ix = st.selectbox("Job", range(len(ids)), format_func=lambda i: labels[i], key="fct_job_ix")
    jid = ids[int(ix)]
    wd = st.date_input("Work date", value=date.today(), key="fct_work_date")
    if isinstance(wd, datetime):
        wd = wd.date()

    batch = fetch_batch_for_job_date(jid, wd, admin=admin)
    status = str((batch or {}).get("status") or "draft").lower()
    st.caption(f"Batch status: **{status}**")

    employees = fetch_table_for_session("employees", admin=admin, limit=5000)
    emp_opts = {
        str(e.get("id") or ""): str(e.get("name") or e.get("email") or "Employee")
        for e in (employees or [])
        if isinstance(e, dict) and e.get("id")
    }
    emp_ids = list(emp_opts.keys())
    if not emp_ids:
        st.warning("No employees loaded.")
        return

    st.session_state.setdefault("fct_rows", 4)
    if batch and batch.get("id"):
        existing = fetch_batch_lines(str(batch["id"]), admin=admin)
        if existing and "fct_loaded_batch" not in st.session_state:
            st.session_state["fct_rows"] = min(25, max(1, len(existing)))
            for i, line in enumerate(existing):
                st.session_state[f"fct_emp_{i}"] = str(line.get("employee_id") or emp_ids[0])
                st.session_state[f"fct_tt_{i}"] = str(line.get("time_type") or "ST")
                st.session_state[f"fct_h_{i}"] = float(line.get("hours") or 0)
                st.session_state[f"fct_notes_{i}"] = str(line.get("notes") or "")
            st.session_state["fct_loaded_batch"] = str(batch["id"])

    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("Copy yesterday's crew", use_container_width=True, key="fct_copy_y"):
            lines = copy_yesterday_lines(jid, wd, admin=admin)
            if not lines:
                st.info("No crew time from yesterday for this job.")
            else:
                st.session_state["fct_rows"] = min(25, len(lines))
                for i, line in enumerate(lines):
                    st.session_state[f"fct_emp_{i}"] = line["employee_id"]
                    st.session_state[f"fct_tt_{i}"] = line["time_type"]
                    st.session_state[f"fct_h_{i}"] = line["hours"]
                    st.session_state[f"fct_notes_{i}"] = line["notes"]
                st.rerun()
    with c2:
        st.number_input("Rows", min_value=1, max_value=25, key="fct_rows")

    n = int(st.session_state.get("fct_rows") or 4)
    lines_out: list[dict] = []
    for i in range(n):
        st.markdown(f"**Row {i + 1}**")
        a, b, c = st.columns((1.4, 0.7, 0.9), gap="small")
        with a:
            st.selectbox(
                "Employee",
                emp_ids,
                format_func=lambda eid, _m=emp_opts: _m.get(eid, eid),
                key=f"fct_emp_{i}",
                label_visibility="collapsed",
            )
        with b:
            st.selectbox("Type", TIME_TYPES, key=f"fct_tt_{i}", label_visibility="collapsed")
        with c:
            st.number_input("Hrs", min_value=0.0, max_value=24.0, step=0.25, key=f"fct_h_{i}", label_visibility="collapsed")
        st.text_input("Notes", key=f"fct_notes_{i}", placeholder="Optional")
        lines_out.append(
            {
                "employee_id": st.session_state.get(f"fct_emp_{i}"),
                "time_type": st.session_state.get(f"fct_tt_{i}"),
                "hours": float(st.session_state.get(f"fct_h_{i}") or 0),
                "notes": str(st.session_state.get(f"fct_notes_{i}") or ""),
            }
        )

    for w in overtime_warnings(lines_out):
        st.warning(w)

    notes = st.text_area("Batch notes", key="fct_batch_notes", height=60)

    if status != "approved":
        if st.button("Save draft", type="primary", use_container_width=True, key="fct_save"):
            try:
                upsert_crew_time_batch(
                    job_id=jid,
                    work_date=wd,
                    supervisor_name=sup_name,
                    lines=lines_out,
                    notes=notes,
                    status="draft",
                    created_by=uid,
                    admin=admin,
                )
                st.success("Saved.")
                st.session_state["fct_loaded_batch"] = None
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        if st.button("Submit for approval", use_container_width=True, key="fct_submit"):
            try:
                row = upsert_crew_time_batch(
                    job_id=jid,
                    work_date=wd,
                    supervisor_name=sup_name,
                    lines=lines_out,
                    notes=notes,
                    status="draft",
                    created_by=uid,
                    admin=admin,
                )
                submit_batch(str(row.get("id") or batch.get("id") or ""), admin=admin)
                st.success("Submitted.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    if admin and batch and batch.get("id") and status == "submitted":
        if st.button("Approve & sync to payroll", type="primary", use_container_width=True, key="fct_approve"):
            try:
                n_sync = approve_batch_and_sync_time_entries(
                    str(batch["id"]), approved_by=uid, admin=True
                )
                st.success(f"Approved — {n_sync} line(s) synced to Time Tracking.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
