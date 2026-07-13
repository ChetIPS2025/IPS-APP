"""Field crew time entry — supervisor batch submit (Phase 1)."""

from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from app.auth import current_profile, current_role, effective_role

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
from app.services.job_service import sort_jobs_by_number_then_name
from app.utils.field_context import render_field_job_bar
def _admin() -> bool:
    return effective_role() in {"admin", "manager"}


def render_crew_time_for_job(
    job_id: str,
    *,
    admin: bool,
    uid: str | None,
    sup_name: str,
    key_prefix: str = "fct",
) -> None:
    """Batch crew hours for one job (embedded in field day shell or standalone page)."""
    jid = str(job_id or "").strip()
    if not jid:
        st.warning("Select a job first.")
        return

    wd = st.date_input("Work date", value=date.today(), key=f"{key_prefix}_work_date")
    if isinstance(wd, datetime):
        wd = wd.date()

    batch = fetch_batch_for_job_date(jid, wd, admin=admin)
    status = str((batch or {}).get("status") or "draft").lower()
    st.caption(f"Batch status: **{status}**")

    employees = fetch_table_for_session(
        "employees",
        session_key=str(uid or "anonymous"),
        use_admin=admin,
        limit=5000,
    )
    emp_opts = {
        str(e.get("id") or ""): str(e.get("name") or e.get("email") or "Employee")
        for e in (employees or [])
        if isinstance(e, dict) and e.get("id")
    }
    emp_ids = list(emp_opts.keys())
    if not emp_ids:
        st.warning("No employees loaded.")
        return

    rows_key = f"{key_prefix}_rows"
    loaded_key = f"{key_prefix}_loaded_batch"
    st.session_state.setdefault(rows_key, 4)
    if batch and batch.get("id"):
        existing = fetch_batch_lines(str(batch["id"]), admin=admin)
        if existing and loaded_key not in st.session_state:
            st.session_state[rows_key] = min(25, max(1, len(existing)))
            for i, line in enumerate(existing):
                st.session_state[f"{key_prefix}_emp_{i}"] = str(line.get("employee_id") or emp_ids[0])
                st.session_state[f"{key_prefix}_tt_{i}"] = str(line.get("time_type") or "ST")
                st.session_state[f"{key_prefix}_h_{i}"] = float(line.get("hours") or 0)
                st.session_state[f"{key_prefix}_notes_{i}"] = str(line.get("notes") or "")
            st.session_state[loaded_key] = str(batch["id"])

    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("Copy yesterday's crew", use_container_width=True, key=f"{key_prefix}_copy_y"):
            lines = copy_yesterday_lines(jid, wd, admin=admin)
            if not lines:
                st.info("No crew time from yesterday for this job.")
            else:
                st.session_state[rows_key] = min(25, len(lines))
                for i, line in enumerate(lines):
                    st.session_state[f"{key_prefix}_emp_{i}"] = line["employee_id"]
                    st.session_state[f"{key_prefix}_tt_{i}"] = line["time_type"]
                    st.session_state[f"{key_prefix}_h_{i}"] = line["hours"]
                    st.session_state[f"{key_prefix}_notes_{i}"] = line["notes"]
                st.rerun()
    with c2:
        st.number_input("Rows", min_value=1, max_value=25, key=rows_key)

    n = int(st.session_state.get(rows_key) or 4)
    lines_out: list[dict] = []
    for i in range(n):
        st.markdown(f"**Row {i + 1}**")
        a, b, c = st.columns((1.4, 0.7, 0.9), gap="small")
        with a:
            st.selectbox(
                "Employee",
                emp_ids,
                format_func=lambda eid, _m=emp_opts: _m.get(eid, eid),
                key=f"{key_prefix}_emp_{i}",
                label_visibility="collapsed",
            )
        with b:
            st.selectbox("Type", TIME_TYPES, key=f"{key_prefix}_tt_{i}", label_visibility="collapsed")
        with c:
            st.number_input(
                "Hrs",
                min_value=0.0,
                max_value=24.0,
                step=0.25,
                key=f"{key_prefix}_h_{i}",
                label_visibility="collapsed",
            )
        st.text_input("Notes", key=f"{key_prefix}_notes_{i}", placeholder="Optional")
        lines_out.append(
            {
                "employee_id": st.session_state.get(f"{key_prefix}_emp_{i}"),
                "time_type": st.session_state.get(f"{key_prefix}_tt_{i}"),
                "hours": float(st.session_state.get(f"{key_prefix}_h_{i}") or 0),
                "notes": str(st.session_state.get(f"{key_prefix}_notes_{i}") or ""),
            }
        )

    for w in overtime_warnings(lines_out):
        st.warning(w)

    notes = st.text_area("Batch notes", key=f"{key_prefix}_batch_notes", height=60)

    if status != "approved":
        if st.button("Save draft", type="primary", use_container_width=True, key=f"{key_prefix}_save"):
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
                st.session_state[loaded_key] = None
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        if st.button("Submit for approval", use_container_width=True, key=f"{key_prefix}_submit"):
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
        if st.button(
            "Approve & sync to payroll",
            type="primary",
            use_container_width=True,
            key=f"{key_prefix}_approve",
        ):
            try:
                n_sync = approve_batch_and_sync_time_entries(
                    str(batch["id"]), approved_by=uid, admin=True
                )
                st.success(f"Approved — {n_sync} line(s) synced to Time Tracking.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def render() -> None:
    from app.pages._core._access import begin_module
    if not begin_module("field_crew_time"):
        return

    ensure_narrow_viewport_detected()
    st.markdown(
        '<span class="ips-field-crew-time-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    from app.utils.permissions import can_submit_timekeeping
    if not can_submit_timekeeping(effective_role()):
        render_page_brand_header(
            "Crew Time",
            "Supervisors enter crew hours in Timekeeping.",
        )
        st.info(
            "Crew time entry has moved to the **Timekeeping** module. "
            "Your supervisor enters hours for the crew; you can view your own time there."
        )
        if st.button("Open Timekeeping", type="primary", key="fct_go_tk"):
            from app.navigation import navigate_to_timekeeping
            navigate_to_timekeeping()
            st.rerun()
        return

    render_page_brand_header(
        "Crew Time",
        "Legacy batch entry — use Timekeeping for all crew hours.",
    )
    st.warning(
        "Enter crew hours in **Timekeeping** (single source of truth). "
        "This page is retained for reference only."
    )
    if st.button("Open Timekeeping", type="primary", key="fct_go_tk_super"):
        from app.navigation import navigate_to_timekeeping
        jid = ""
        from app.utils.field_context import get_field_job_id
        jid = str(get_field_job_id() or "").strip()
        navigate_to_timekeeping(job_id=jid)
        st.rerun()
