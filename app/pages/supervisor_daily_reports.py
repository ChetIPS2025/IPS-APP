from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from auth import current_profile, current_role
from branding import render_header

try:
    from app.db import create_signed_url, fetch_jobs_with_order_fallback
except ImportError:
    from db import create_signed_url, fetch_jobs_with_order_fallback  # type: ignore

try:
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore

try:
    from app.services.supervisor_daily_reports import (
        delay_labels_map,
        fetch_crew_lines,
        fetch_photos_for_report,
        fetch_report_for_job_date,
        fetch_reports_for_job,
        upsert_supervisor_daily_report,
    )
except ImportError:
    from services.supervisor_daily_reports import (  # type: ignore
        delay_labels_map,
        fetch_crew_lines,
        fetch_photos_for_report,
        fetch_report_for_job_date,
        fetch_reports_for_job,
        upsert_supervisor_daily_report,
    )

_LOG = logging.getLogger(__name__)

_PHOTO_EXT = re.compile(r"\.(jpe?g|png|gif|webp)$", re.IGNORECASE)


def _admin_read() -> bool:
    return current_role() in {"admin", "pm"}


def _safe_filename(name: str) -> str:
    base = Path(name or "photo").name
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", base).strip("._") or "photo.jpg"
    return base[:180]


def _prefill_key(job_id: str) -> str:
    return f"sdr_prefill_payload_{str(job_id or '').strip()}"


def _apply_prefill_if_any(job_id: str) -> None:
    key = _prefill_key(job_id)
    if key not in st.session_state:
        return
    payload = st.session_state.pop(key)
    if not isinstance(payload, dict):
        return
    jid = str(job_id or "").strip()
    p = payload.get("header") or {}
    if isinstance(p, dict):
        st.session_state[f"sdr_supervisor_{jid}"] = str(p.get("supervisor_name") or "")
        st.session_state[f"sdr_crew_size_{jid}"] = int(p.get("crew_size") or 0)
        st.session_state[f"sdr_main_goal_{jid}"] = str(p.get("main_goal") or "")
        st.session_state[f"sdr_midday_ok_{jid}"] = "Yes" if p.get("midday_on_track", True) else "No"
        st.session_state[f"sdr_midday_reason_{jid}"] = str(p.get("midday_reason") or "")
        st.session_state[f"sdr_done_{jid}"] = str(p.get("completed_today") or "")
        st.session_state[f"sdr_not_done_{jid}"] = str(p.get("not_completed") or "")
        st.session_state[f"sdr_not_done_why_{jid}"] = str(p.get("not_completed_reason") or "")
        st.session_state[f"sdr_tomorrow_{jid}"] = str(p.get("tomorrows_plan") or "")
        st.session_state[f"sdr_delay_other_notes_{jid}"] = str(p.get("delay_other_notes") or "")
        for fk in delay_labels_map().keys():
            st.session_state[f"sdr_{fk}_{jid}"] = bool(p.get(fk))
    crew = payload.get("crew")
    if isinstance(crew, list) and crew:
        st.session_state[f"sdr_crew_n_{jid}"] = min(25, max(1, len(crew)))
        for idx, line in enumerate(crew):
            if not isinstance(line, dict):
                continue
            try:
                h = float(line.get("hours") or 0)
            except (TypeError, ValueError):
                h = 0.0
            st.session_state[f"sdr_crew_name_{jid}_{idx}"] = str(line.get("employee_name") or "")
            st.session_state[f"sdr_crew_task_{jid}_{idx}"] = str(line.get("task") or "")
            st.session_state[f"sdr_crew_h_{jid}_{idx}"] = float(h)
            st.session_state[f"sdr_crew_notes_{jid}_{idx}"] = str(line.get("notes") or "")


def render_daily_reports_for_job(
    *,
    job_id: str,
    job_label: str,
    admin_read: bool | None = None,
    show_title: bool = True,
) -> None:
    """
    Collapsible supervisor daily report form + history for one job.
    Used from Job Database (edit panel) and the standalone Daily crew report page.
    """
    jid = str(job_id or "").strip()
    if not jid:
        return
    if admin_read is None:
        admin_read = _admin_read()
    title = "Daily Reports" if show_title else "Daily reports (this job)"
    with st.expander(title, expanded=False):
        st.caption(
            f"**{job_label}** — one report per calendar day. Summaries appear on **Dashboard**."
        )
        past = fetch_reports_for_job(jid, admin=admin_read, limit=60)
        if past:
            df = pd.DataFrame(
                [
                    {
                        "Date": str(r.get("report_date") or "")[:10],
                        "Supervisor": str(r.get("supervisor_name") or "").strip() or "—",
                        "Crew": int(r.get("crew_size") or 0),
                        "On track": "Yes" if r.get("midday_on_track") else "No",
                    }
                    for r in past[:40]
                    if isinstance(r, dict)
                ]
            )
            st.markdown("##### Recent reports")
            st.dataframe(df, use_container_width=True, hide_index=True, height=min(260, 48 + 28 * len(df)))
        else:
            st.caption("No reports filed for this job yet.")

        st.divider()
        load_opts = ["— Select to load —"] + [str(r.get("report_date") or "")[:10] for r in past if r.get("report_date")]
        st.selectbox(
            "Load existing report",
            load_opts,
            key=f"sdr_load_pick_{jid}",
            help="Pick a date, then tap **Load into form**.",
        )
        if st.button("Load into form", key=f"sdr_load_btn_{jid}"):
            pick = str(st.session_state.get(f"sdr_load_pick_{jid}") or "")
            if pick and pick != "— Select to load —":
                d = date.fromisoformat(pick)
                hdr = fetch_report_for_job_date(jid, d, admin=admin_read)
                if hdr and hdr.get("id"):
                    crew = fetch_crew_lines(str(hdr["id"]), admin=admin_read)
                    st.session_state[_prefill_key(jid)] = {
                        "header": hdr,
                        "crew": crew
                        or [{"employee_name": "", "task": "", "hours": 0.0, "notes": ""}],
                    }
                    st.session_state[f"sdr_report_date_{jid}"] = d
                    st.rerun()
                st.warning("Could not load that report.")

        _apply_prefill_if_any(jid)

        st.session_state.setdefault(f"sdr_report_date_{jid}", date.today())
        st.session_state.setdefault(f"sdr_midday_ok_{jid}", "Yes")
        for _fk in delay_labels_map().keys():
            st.session_state.setdefault(f"sdr_{_fk}_{jid}", False)
        st.session_state.setdefault(f"sdr_crew_n_{jid}", 4)
        for _ci in range(25):
            st.session_state.setdefault(f"sdr_crew_h_{jid}_{_ci}", 0.0)
            st.session_state.setdefault(f"sdr_crew_name_{jid}_{_ci}", "")
            st.session_state.setdefault(f"sdr_crew_task_{jid}_{_ci}", "")
            st.session_state.setdefault(f"sdr_crew_notes_{jid}_{_ci}", "")
        st.date_input(
            "Report date",
            key=f"sdr_report_date_{jid}",
        )

        rd_raw = st.session_state.get(f"sdr_report_date_{jid}")
        if isinstance(rd_raw, datetime):
            rd = rd_raw.date()
        elif isinstance(rd_raw, date):
            rd = rd_raw
        else:
            rd = date.today()

        existing = fetch_report_for_job_date(jid, rd, admin=admin_read)
        if existing:
            st.info(f"Saving will **update** the report for **{rd.isoformat()}**.")

        with st.expander("Basics", expanded=True):
            st.text_input("Supervisor", key=f"sdr_supervisor_{jid}", placeholder="Name")
            st.number_input("Crew size", min_value=0, max_value=500, step=1, key=f"sdr_crew_size_{jid}")
            st.text_area("Main goal for the day", key=f"sdr_main_goal_{jid}", height=68, placeholder="What success looks like today")

        with st.expander("Midday check", expanded=False):
            st.radio(
                "On track at midday?",
                ["Yes", "No"],
                horizontal=True,
                key=f"sdr_midday_ok_{jid}",
            )
            st.text_area(
                "If not on track, why?",
                key=f"sdr_midday_reason_{jid}",
                height=70,
                placeholder="Only if you selected No",
            )

        with st.expander("Completed & carryover", expanded=False):
            st.text_area("Completed today", key=f"sdr_done_{jid}", height=80)
            st.text_area("Not completed", key=f"sdr_not_done_{jid}", height=60)
            st.text_area("Reason not completed", key=f"sdr_not_done_why_{jid}", height=60)

        with st.expander("Delays / inefficiency", expanded=False):
            st.caption("Check all that applied today.")
            labels = delay_labels_map()
            keys = list(labels.keys())
            for i in range(0, len(keys), 2):
                c1, c2 = st.columns(2, gap="small")
                for col, k in zip((c1, c2), keys[i : i + 2]):
                    with col:
                        if k:
                            st.checkbox(labels[k], key=f"sdr_{k}_{jid}")

            st.text_area(
                "Other delay notes",
                key=f"sdr_delay_other_notes_{jid}",
                height=56,
                placeholder="Details for “Other” or extra context",
            )

        with st.expander("Crew assignments", expanded=True):
            st.number_input(
                "Number of rows",
                min_value=1,
                max_value=25,
                key=f"sdr_crew_n_{jid}",
            )
            n_crew = int(st.session_state.get(f"sdr_crew_n_{jid}") or 4)
            for idx in range(n_crew):
                st.markdown(f"**Person {idx + 1}**")
                a1, a2, a3 = st.columns((1.1, 1.1, 0.75), gap="small")
                with a1:
                    st.text_input("Name", key=f"sdr_crew_name_{jid}_{idx}", placeholder="Employee")
                with a2:
                    st.text_input("Task", key=f"sdr_crew_task_{jid}_{idx}", placeholder="Task")
                with a3:
                    st.number_input("Hours", min_value=0.0, max_value=24.0, step=0.25, key=f"sdr_crew_h_{jid}_{idx}")
                st.text_input("Notes", key=f"sdr_crew_notes_{jid}_{idx}", placeholder="Optional")

        with st.expander("Tomorrow’s plan", expanded=False):
            st.text_area("Plan", key=f"sdr_tomorrow_{jid}", height=72, placeholder="Tomorrow’s priorities")

        with st.expander("Photos", expanded=False):
            st.file_uploader(
                "Add photos (optional)",
                type=["jpg", "jpeg", "png", "gif", "webp"],
                accept_multiple_files=True,
                key=f"sdr_photos_{jid}",
                help="Uploads attach when you save.",
            )

        if existing and existing.get("id"):
            photos = fetch_photos_for_report(str(existing["id"]), admin=admin_read)
            if photos:
                st.caption("Existing photos")
                pc = st.columns(min(4, max(1, len(photos))))
                for i, ph in enumerate(photos[:8]):
                    with pc[i % len(pc)]:
                        pth = str(ph.get("storage_path") or "").strip()
                        url = create_signed_url(pth, expires_in=3600) if pth else ""
                        cap = str(ph.get("file_name") or "photo").strip() or "photo"
                        if url and (_PHOTO_EXT.search(cap.lower()) or _PHOTO_EXT.search(pth.lower())):
                            st.image(url, caption=cap[:40], use_container_width=True)
                        elif url:
                            st.caption(cap[:80])
                            st.link_button("Open", url, use_container_width=True)

        if st.button("Save report", type="primary", use_container_width=True, key=f"sdr_save_{jid}"):
            prof = current_profile() or {}
            uid = str(prof.get("id") or "").strip() or None
            midday_ok = str(st.session_state.get(f"sdr_midday_ok_{jid}") or "Yes") == "Yes"
            labels = delay_labels_map()
            delays = {k: bool(st.session_state.get(f"sdr_{k}_{jid}")) for k in labels.keys()}
            n_save = int(st.session_state.get(f"sdr_crew_n_{jid}") or 4)
            crew_out: list[dict[str, Any]] = []
            for idx in range(n_save):
                crew_out.append(
                    {
                        "employee_name": str(st.session_state.get(f"sdr_crew_name_{jid}_{idx}", "") or "").strip(),
                        "task": str(st.session_state.get(f"sdr_crew_task_{jid}_{idx}", "") or "").strip(),
                        "hours": float(st.session_state.get(f"sdr_crew_h_{jid}_{idx}") or 0),
                        "notes": str(st.session_state.get(f"sdr_crew_notes_{jid}_{idx}", "") or "").strip(),
                    }
                )
            uploads_raw = st.session_state.get(f"sdr_photos_{jid}")
            upload_payload: list[tuple[bytes, str, str]] = []
            if uploads_raw:
                files = uploads_raw if isinstance(uploads_raw, list) else [uploads_raw]
                for fi, up in enumerate(files):
                    if up is None:
                        continue
                    raw_name = _safe_filename(str(getattr(up, "name", "") or f"photo_{fi}.jpg"))
                    data = up.getvalue()
                    if not data:
                        continue
                    ctype = str(getattr(up, "type", "") or "").strip() or "image/jpeg"
                    upload_payload.append((data, ctype, raw_name))

            body: dict[str, Any] = {
                "supervisor_name": str(st.session_state.get(f"sdr_supervisor_{jid}") or "").strip(),
                "crew_size": int(st.session_state.get(f"sdr_crew_size_{jid}") or 0),
                "main_goal": str(st.session_state.get(f"sdr_main_goal_{jid}") or "").strip(),
                "midday_on_track": midday_ok,
                "midday_reason": str(st.session_state.get(f"sdr_midday_reason_{jid}") or "").strip(),
                "completed_today": str(st.session_state.get(f"sdr_done_{jid}") or "").strip(),
                "not_completed": str(st.session_state.get(f"sdr_not_done_{jid}") or "").strip(),
                "not_completed_reason": str(st.session_state.get(f"sdr_not_done_why_{jid}") or "").strip(),
                "tomorrows_plan": str(st.session_state.get(f"sdr_tomorrow_{jid}") or "").strip(),
                "delay_other_notes": str(st.session_state.get(f"sdr_delay_other_notes_{jid}") or "").strip(),
                **delays,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if uid:
                body["created_by"] = uid
            try:
                upsert_supervisor_daily_report(
                    job_id=jid,
                    report_date=rd,
                    payload=body,
                    crew_rows=crew_out,
                    new_photo_files=upload_payload,
                    admin=admin_read,
                )
            except Exception as exc:
                st.error(f"Could not save report: {exc}")
                _LOG.exception("supervisor daily report save failed")
            else:
                st.success("Report saved.")
                st.session_state.pop(f"sdr_photos_{jid}", None)
                st.rerun()


def render() -> None:
    render_header("Daily crew report", subtitle="Narrative crew summary by job and date — separate from task packages.")
    admin_read = _admin_read()
    jobs = []
    try:
        jobs = list(fetch_jobs_with_order_fallback(limit=5000, use_admin=admin_read) or [])
    except Exception:
        jobs = []
    jobs = sort_jobs_by_number_then_name([j for j in jobs if isinstance(j, dict) and j.get("id")])
    if not jobs:
        st.warning("No jobs loaded.")
        return
    labels = [job_row_select_label(j) for j in jobs]
    ids = [str(j.get("id")) for j in jobs]
    ix = st.selectbox(
        "Job",
        range(len(ids)),
        format_func=lambda i: labels[i],
        key="sdr_page_job_idx",
    )
    jid = ids[int(ix)]
    render_daily_reports_for_job(job_id=jid, job_label=labels[int(ix)], admin_read=admin_read, show_title=False)
