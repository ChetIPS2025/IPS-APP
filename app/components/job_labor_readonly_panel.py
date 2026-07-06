"""Read-only labor summary and customer weekly timesheets on Job Detail."""

from __future__ import annotations

import html
from datetime import date, timedelta
from typing import Any
from urllib.parse import quote

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from app.auth import current_profile, current_role
    from app.components.status import status_pill_html
    from app.services.job_labor_summary_service import get_job_labor_summary
    from app.services.job_weekly_timesheets import monday_of_week, week_bounds
    from app.services.weekly_job_timesheet_service import (
        TIMESHEET_TABLE_MISSING_MSG,
        build_timesheet_data,
        build_timesheet_pdf_bytes,
        fetch_timesheet_by_job_week,
        list_timesheets_for_job,
        load_timesheet_data,
        render_timesheet_html,
        save_timesheet,
        signed_url_for_timesheet,
        timesheet_table_available,
    )
    from app.services.weekly_timesheet_service import mark_timesheet_sent
    from app.utils.formatting import fmt_currency, fmt_date, fmt_hours
    from app.utils.permissions import can_submit_timekeeping
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from services.job_labor_summary_service import get_job_labor_summary  # type: ignore
    from services.job_weekly_timesheets import monday_of_week, week_bounds  # type: ignore
    from services.weekly_job_timesheet_service import (  # type: ignore
        TIMESHEET_TABLE_MISSING_MSG,
        build_timesheet_data,
        build_timesheet_pdf_bytes,
        fetch_timesheet_by_job_week,
        list_timesheets_for_job,
        load_timesheet_data,
        render_timesheet_html,
        save_timesheet,
        signed_url_for_timesheet,
        timesheet_table_available,
    )
    from services.weekly_timesheet_service import mark_timesheet_sent  # type: ignore
    from utils.formatting import fmt_currency, fmt_date, fmt_hours  # type: ignore
    from utils.permissions import can_submit_timekeeping  # type: ignore


def _week_start_key(key_prefix: str) -> str:
    return f"{key_prefix}_week_start"


def _init_week_state(key_prefix: str) -> date:
    state_key = _week_start_key(key_prefix)
    prefill_key = f"{key_prefix}_week_prefilled"
    if prefill_key not in st.session_state:
        try:
            from app.navigation import WJT_PREFILL_WEEK_KEY
        except ImportError:
            from navigation import WJT_PREFILL_WEEK_KEY  # type: ignore
        pre_week = str(st.session_state.pop(WJT_PREFILL_WEEK_KEY, "") or "").strip()[:10]
        if pre_week:
            try:
                st.session_state[state_key] = monday_of_week(date.fromisoformat(pre_week))
                st.session_state[prefill_key] = True
            except ValueError:
                pass
    if state_key not in st.session_state:
        st.session_state[state_key] = monday_of_week(date.today())
    raw = st.session_state[state_key]
    if not isinstance(raw, date):
        raw = monday_of_week(date.today())
        st.session_state[state_key] = raw
    ws = monday_of_week(raw)
    st.session_state[state_key] = ws
    return ws


def _can_edit_time_in_timekeeping() -> bool:
    role = current_role()
    return can_submit_timekeeping(role) or str(role or "").strip().lower() == "admin"


def _navigate_edit_timekeeping(job_id: str, week_start: date) -> None:
    try:
        from app.navigation import navigate_to_timekeeping
    except ImportError:
        from navigation import navigate_to_timekeeping  # type: ignore
    navigate_to_timekeeping(job_id=job_id, week_start=week_start.isoformat())
    st.rerun()


def _customer_email_for_job(job: dict[str, Any]) -> str:
    for key in ("customer_email", "billing_email", "contact_email", "email"):
        val = str(job.get(key) or "").strip()
        if val and "@" in val:
            return val
    return ""


def _mailto_customer_timesheet(
    *,
    job: dict[str, Any],
    week_start: date,
    week_end: date,
    pdf_url: str = "",
) -> str:
    job_num = str(job.get("job_number") or "Job").strip()
    job_name = str(job.get("job_name") or "").strip()
    subject = quote(f"Weekly Timesheet — {job_num} — week ending {week_end.isoformat()}")
    lines = [
        f"Please find the weekly timesheet for {job_num}",
        f"({job_name})" if job_name else "",
        f"for the week of {week_start.isoformat()} through {week_end.isoformat()}.",
    ]
    if pdf_url:
        lines.append(f"\nPDF: {pdf_url}")
    else:
        lines.append("\nThe timesheet PDF is attached separately.")
    body = quote("\n".join(p for p in lines if p))
    to = quote(_customer_email_for_job(job))
    return f"mailto:{to}?subject={subject}&body={body}" if to else f"mailto:?subject={subject}&body={body}"


def render_job_labor_summary_section(job: dict[str, Any], *, key_prefix: str) -> None:
    """Read-only approved labor rollup for a job."""
    jid = str(job.get("id") or "").strip()
    st.markdown("### Labor Summary")
    st.caption("Totals from **approved** Timekeeping entries only. Hours are entered in Timekeeping.")

    summary = get_job_labor_summary(jid)
    m1, m2, m3, m4, m5 = st.columns(5, gap="small")
    m1.metric("Approved hours", fmt_hours(summary.get("total_approved_hours")))
    m2.metric("ST", fmt_hours(summary.get("st_hours")))
    m3.metric("OT", fmt_hours(summary.get("ot_hours")))
    m4.metric("Labor cost", fmt_currency(summary.get("labor_cost")))
    m5.metric("Last updated", str(summary.get("last_updated_display") or "—"))

    by_emp = summary.get("by_employee") or []
    if by_emp:
        st.markdown("**Hours by employee**")
        df_emp = pd.DataFrame(by_emp)
        show_cols = ["employee_name", "st_hours", "ot_hours", "total_hours", "labor_cost"]
        df_emp = df_emp[[c for c in show_cols if c in df_emp.columns]]
        df_emp = df_emp.rename(
            columns={
                "employee_name": "Employee",
                "st_hours": "ST",
                "ot_hours": "OT",
                "total_hours": "Total",
                "labor_cost": "Cost",
            }
        )
        st.dataframe(df_emp, use_container_width=True, hide_index=True)
    else:
        st.info("No approved timekeeping hours recorded for this job yet.")

    by_week = summary.get("by_week") or []
    if by_week:
        st.markdown("**Hours by week**")
        df_wk = pd.DataFrame(by_week)
        show_wk = ["week_start", "week_end", "st_hours", "ot_hours", "total_hours", "labor_cost"]
        df_wk = df_wk[[c for c in show_wk if c in df_wk.columns]]
        df_wk = df_wk.rename(
            columns={
                "week_start": "Week start",
                "week_end": "Week end",
                "st_hours": "ST",
                "ot_hours": "OT",
                "total_hours": "Total",
                "labor_cost": "Cost",
            }
        )
        st.dataframe(df_wk, use_container_width=True, hide_index=True)


def render_job_weekly_timesheets_tab(job: dict[str, Any], *, key_prefix: str) -> None:
    """Weekly customer timesheets for one job (view/generate/export only)."""
    jid = str(job.get("id") or "").strip()
    kp = key_prefix

    st.markdown(
        '<span class="ips-job-weekly-ts-tab-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Customer weekly timesheets for this job only — built from approved Timekeeping. "
        "Supervisors enter hours in Timekeeping; edit time here via **Edit Time in Timekeeping**."
    )

    if not timesheet_table_available(force=True):
        st.warning(TIMESHEET_TABLE_MISSING_MSG)
        return

    week_start = _init_week_state(kp)
    _, week_end_d = week_bounds(week_start)
    picker_key = f"{kp}_week_picker"

    wc1, wc2, wc3, wc4 = st.columns([0.85, 0.9, 0.85, 1.4], gap="small")
    if wc1.button("◀ Previous Week", key=f"{kp}_prev"):
        st.session_state[_week_start_key(kp)] = week_start - timedelta(days=7)
        st.rerun()
    if wc2.button("Current Week", key=f"{kp}_curr"):
        st.session_state[_week_start_key(kp)] = monday_of_week(date.today())
        st.rerun()
    if wc3.button("Next Week ▶", key=f"{kp}_next"):
        st.session_state[_week_start_key(kp)] = week_start + timedelta(days=7)
        st.rerun()
    with wc4:
        picked = st.date_input(
            "Week starting (Mon)",
            value=week_start,
            key=picker_key,
        )
        if isinstance(picked, date):
            st.session_state[_week_start_key(kp)] = monday_of_week(picked)
            week_start = monday_of_week(picked)
            _, week_end_d = week_bounds(week_start)

    if _can_edit_time_in_timekeeping():
        if st.button(
            "Edit Time in Timekeeping",
            type="primary",
            key=f"{kp}_edit_tk",
            help="Open Timekeeping filtered to this job and week.",
        ):
            _navigate_edit_timekeeping(jid, week_start)

    saved = fetch_timesheet_by_job_week(jid, week_start)
    if saved:
        st.markdown(status_pill_html(str(saved.get("status") or "Draft")), unsafe_allow_html=True)

    try:
        data = build_timesheet_data(jid, week_start, approved_timekeeping_only=True)
    except Exception as exc:
        st.warning(f"Could not build timesheet preview: {html.escape(str(exc))}")
        return

    labor_count = sum(1 for ln in data.labor_lines if ln.total_hours > 0)

    gen1, gen2 = st.columns([1.2, 2], gap="small")
    with gen1:
        if st.button(
            "Generate Timesheet",
            type="primary",
            use_container_width=True,
            key=f"{kp}_generate",
            disabled=labor_count == 0,
            help="Save a weekly timesheet from approved Timekeeping for this job and week.",
        ):
            try:
                prof = current_profile() or {}
                uid = str(prof.get("id") or "")
                data.status = "Generated"
                save_timesheet(data, created_by=uid, lock=False)
                st.success("Weekly timesheet generated from approved Timekeeping.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    if labor_count == 0:
        st.info(
            "No **approved** timekeeping hours for this job and week. "
            "Supervisors enter crew time in Timekeeping; customer timesheets update after approval."
        )
        if _can_edit_time_in_timekeeping():
            if st.button("Enter time in Timekeeping", key=f"{kp}_enter_tk_empty"):
                _navigate_edit_timekeeping(jid, week_start)
        return

    preview_key = f"{kp}_show_preview"
    pdf_bytes = build_timesheet_pdf_bytes(data)
    pdf_name = f"weekly_timesheet_{data.job_number}_{week_start.isoformat()}.pdf"

    a1, a2, a3, a4, a5 = st.columns(5, gap="small")
    if a1.button("View", type="primary", use_container_width=True, key=f"{kp}_view"):
        st.session_state[preview_key] = True
    a2.download_button(
        "Generate PDF",
        data=pdf_bytes,
        file_name=pdf_name,
        mime="application/pdf",
        use_container_width=True,
        key=f"{kp}_pdf",
    )
    if a3.button("Print", use_container_width=True, key=f"{kp}_print"):
        st.session_state[preview_key] = True
        st.session_state[f"{kp}_print_hint"] = True

    pdf_url = ""
    if saved:
        pdf_path = str(saved.get("pdf_path") or saved.get("pdf_file_url") or "")
        pdf_url = signed_url_for_timesheet(pdf_path) or ""

    mailto = _mailto_customer_timesheet(
        job=job,
        week_start=week_start,
        week_end=week_end_d,
        pdf_url=pdf_url,
    )
    a4.link_button("Email Customer", mailto, use_container_width=True)

    if saved and str(saved.get("status") or "").lower() not in {"sent", "approved", "signed"}:
        if a5.button("Mark Sent", use_container_width=True, key=f"{kp}_sent"):
            mark_timesheet_sent(str(saved.get("id") or ""))
            st.rerun()

    if st.session_state.get(preview_key):
        html_doc = render_timesheet_html(data, week_start=week_start, embed=True)
        st.markdown(
            '<span class="ips-wt-preview-frame-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        components.html(html_doc, height=1140, scrolling=True)
        if st.session_state.pop(f"{kp}_print_hint", False):
            st.caption("Use your browser **Print** dialog on the preview above.")
        st.download_button(
            "Download HTML preview",
            data=html_doc,
            file_name=f"weekly_timesheet_{data.job_number}_{week_start.isoformat()}.html",
            mime="text/html",
            key=f"{kp}_html_dl",
        )

    rows = list_timesheets_for_job(jid)
    if rows:
        st.markdown("**Saved timesheets for this job**")
        for row in sorted(rows, key=lambda r: str(r.get("week_start") or ""), reverse=True)[:8]:
            ws = str(row.get("week_start") or "")[:10]
            status = str(row.get("status") or "Draft")
            c1, c2, c3 = st.columns([1.2, 1, 1], gap="small")
            with c1:
                st.caption(f"Week of {fmt_date(ws)} · {status}")
            with c2:
                pdf_path = str(row.get("pdf_path") or row.get("pdf_file_url") or "")
                url = signed_url_for_timesheet(pdf_path) if pdf_path else ""
                if url:
                    st.link_button("PDF", url, key=f"{kp}_saved_pdf_{row.get('id')}", use_container_width=True)
            with c3:
                tid = str(row.get("id") or "")
                loaded = load_timesheet_data(tid) if tid else None
                if loaded and st.button("View", key=f"{kp}_saved_view_{tid}", use_container_width=True):
                    st.session_state[preview_key] = True
                    st.session_state[f"{kp}_saved_preview_data"] = loaded
                    st.rerun()


def render_job_labor_summary_tab(job: dict[str, Any], *, key_prefix: str) -> None:
    """Approved labor rollup for one job."""
    st.markdown(
        '<span class="ips-job-labor-readonly-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    render_job_labor_summary_section(job, key_prefix=f"{key_prefix}_summary")


def render_job_labor_and_timesheets_tab(job: dict[str, Any], *, key_prefix: str) -> None:
    """Legacy combined tab — prefer separate Labor Summary and Weekly Timesheets tabs."""
    render_job_labor_summary_tab(job, key_prefix=key_prefix)
    st.divider()
    render_job_weekly_timesheets_tab(job, key_prefix=f"{key_prefix}_wts")
