from __future__ import annotations

import html
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from app.auth import current_profile, current_role, effective_role
from app.ui.page_shell import render_page_header
from app.branding import render_header

from app.db import create_signed_url, fetch_jobs_with_order_fallback
from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
from app.services.supervisor_daily_reports import (
    delay_labels_map,
    fetch_crew_lines,
    fetch_photos_for_report,
    fetch_report_for_job_date,
    fetch_reports_for_job,
    review_daily_report,
    submit_daily_report,
    upsert_supervisor_daily_report,
)
from app.ui.components.badges import render_badge
_LOG = logging.getLogger(__name__)

_PHOTO_EXT = re.compile(r"\.(jpe?g|png|gif|webp)$", re.IGNORECASE)


def _admin_read() -> bool:
    return effective_role() in {"admin", "pm"}


def _safe_filename(name: str) -> str:
    base = Path(name or "photo").name
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", base).strip("._") or "photo.jpg"
    return base[:180]


def _prefill_key(job_id: str) -> str:
    return f"sdr_prefill_payload_{str(job_id or '').strip()}"


def _render_sdr_wizard_nav(job_id: str, step: int) -> None:
    from app.utils.field_context import inject_field_day_shell_css, set_sdr_wizard_step
    inject_field_day_shell_css()
    labels = ["Check-in & basics", "Crew & work", "Photos & submit"]
    pills = ""
    for i, label in enumerate(labels):
        cls = "is-active" if i == step else "is-done" if i < step else ""
        pills += f'<span class="ips-field-wizard-step {cls}">{i + 1}. {html.escape(label)}</span>'
    st.markdown(f'<div class="ips-field-wizard-steps">{pills}</div>', unsafe_allow_html=True)
    back_col, next_col, _ = st.columns([1, 1, 2], gap="small")
    with back_col:
        if step > 0 and st.button("Back", key=f"sdr_wiz_back_{job_id}", use_container_width=True):
            set_sdr_wizard_step(job_id, step - 1)
            st.rerun()
    with next_col:
        if step < 2 and st.button("Next", key=f"sdr_wiz_next_{job_id}", use_container_width=True):
            set_sdr_wizard_step(job_id, step + 1)
            st.rerun()


def _show_sdr_section(
    title: str,
    *,
    wizard: bool,
    step: int,
    target_step: int,
    expanded: bool,
    render_fn,
) -> None:
    if wizard:
        if step != target_step:
            return
        st.markdown(f"##### {title}")
        render_fn()
        return
    with st.expander(title, expanded=expanded):
        render_fn()


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
        st.session_state[f"sdr_weather_{jid}"] = str(p.get("weather") or "")
        st.session_state[f"sdr_hours_worked_{jid}"] = float(p.get("hours_worked") or 0)
        st.session_state[f"sdr_safety_{jid}"] = str(p.get("safety_notes") or "")
        st.session_state[f"sdr_equipment_{jid}"] = str(p.get("equipment_used") or "")
        st.session_state[f"sdr_materials_{jid}"] = str(p.get("materials_used") or "")
        st.session_state[f"sdr_customer_{jid}"] = str(p.get("customer_conversations") or "")
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
    inline: bool = False,
    expand_sections: bool = False,
    wizard: bool = False,
    checkin_block=None,
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
    section_open = expand_sections
    if wizard:
        from app.utils.field_context import sdr_wizard_step
        wiz_step = sdr_wizard_step(jid)
    else:
        wiz_step = -1

    def _body() -> None:
        if wizard:
            _render_sdr_wizard_nav(jid, wiz_step)

        if not wizard or wiz_step == 0:
            st.caption(
                f"**{job_label}** — one report per calendar day. Summaries appear on **Dashboard**."
            )
            if wizard and callable(checkin_block):
                checkin_block()

            past = fetch_reports_for_job(jid, admin=admin_read, limit=60)
            if past:
                df = pd.DataFrame(
                    [
                        {
                            "Date": str(r.get("report_date") or "")[:10],
                            "Status": str(r.get("status") or "Draft"),
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
            load_opts = ["— Select to load —"] + [
                str(r.get("report_date") or "")[:10] for r in past if r.get("report_date")
            ]
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

        if not wizard or wiz_step == 0:
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
        if existing and (not wizard or wiz_step in (0, 2)):
            st.info(f"Saving will **update** the report for **{rd.isoformat()}**.")
            rep_status = str(existing.get("status") or "Draft").strip()
            tone = "success" if rep_status == "Reviewed" else "warning" if rep_status == "Submitted" else "neutral"
            render_badge(rep_status, tone=tone)

        def _basics_fields() -> None:
            st.text_input("Supervisor", key=f"sdr_supervisor_{jid}", placeholder="Name")
            st.number_input("Crew size", min_value=0, max_value=500, step=1, key=f"sdr_crew_size_{jid}")
            st.text_area(
                "Main goal for the day",
                key=f"sdr_main_goal_{jid}",
                height=68,
                placeholder="What success looks like today",
            )

        def _midday_fields() -> None:
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

        _show_sdr_section(
            "Basics",
            wizard=wizard,
            step=wiz_step,
            target_step=0,
            expanded=True,
            render_fn=_basics_fields,
        )
        _show_sdr_section(
            "Midday check",
            wizard=wizard,
            step=wiz_step,
            target_step=0,
            expanded=section_open,
            render_fn=_midday_fields,
        )

        def _weather_fields() -> None:
            st.text_input("Weather", key=f"sdr_weather_{jid}", placeholder="Clear, rain, heat…")
            st.number_input(
                "Total hours worked (crew)",
                min_value=0.0,
                max_value=999.0,
                step=0.25,
                key=f"sdr_hours_worked_{jid}",
            )
            st.text_area("Safety notes", key=f"sdr_safety_{jid}", height=56)
            st.text_area("Equipment used", key=f"sdr_equipment_{jid}", height=56)
            st.text_area("Materials used", key=f"sdr_materials_{jid}", height=56)
            st.text_area("Customer conversations", key=f"sdr_customer_{jid}", height=56)

        def _completed_fields() -> None:
            st.text_area("Completed today", key=f"sdr_done_{jid}", height=80)
            st.text_area("Not completed", key=f"sdr_not_done_{jid}", height=60)
            st.text_area("Reason not completed", key=f"sdr_not_done_why_{jid}", height=60)

        def _delay_fields() -> None:
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

        def _crew_fields() -> None:
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
                    st.number_input(
                        "Hours",
                        min_value=0.0,
                        max_value=24.0,
                        step=0.25,
                        key=f"sdr_crew_h_{jid}_{idx}",
                    )
                st.text_input("Notes", key=f"sdr_crew_notes_{jid}_{idx}", placeholder="Optional")

        _show_sdr_section(
            "Weather & field notes",
            wizard=wizard,
            step=wiz_step,
            target_step=1,
            expanded=section_open,
            render_fn=_weather_fields,
        )
        _show_sdr_section(
            "Completed & carryover",
            wizard=wizard,
            step=wiz_step,
            target_step=1,
            expanded=section_open,
            render_fn=_completed_fields,
        )
        _show_sdr_section(
            "Delays / inefficiency",
            wizard=wizard,
            step=wiz_step,
            target_step=1,
            expanded=section_open,
            render_fn=_delay_fields,
        )
        _show_sdr_section(
            "Crew assignments",
            wizard=wizard,
            step=wiz_step,
            target_step=1,
            expanded=True,
            render_fn=_crew_fields,
        )

        def _tomorrow_fields() -> None:
            st.text_area("Plan", key=f"sdr_tomorrow_{jid}", height=72, placeholder="Tomorrow’s priorities")

        def _photo_fields() -> None:
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

        _show_sdr_section(
            "Tomorrow’s plan",
            wizard=wizard,
            step=wiz_step,
            target_step=2,
            expanded=section_open,
            render_fn=_tomorrow_fields,
        )
        _show_sdr_section(
            "Photos",
            wizard=wizard,
            step=wiz_step,
            target_step=2,
            expanded=section_open,
            render_fn=_photo_fields,
        )

        if not wizard or wiz_step == 2:
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
                            "employee_name": str(
                                st.session_state.get(f"sdr_crew_name_{jid}_{idx}", "") or ""
                            ).strip(),
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
                    "weather": str(st.session_state.get(f"sdr_weather_{jid}") or "").strip(),
                    "hours_worked": float(st.session_state.get(f"sdr_hours_worked_{jid}") or 0),
                    "safety_notes": str(st.session_state.get(f"sdr_safety_{jid}") or "").strip(),
                    "equipment_used": str(st.session_state.get(f"sdr_equipment_{jid}") or "").strip(),
                    "materials_used": str(st.session_state.get(f"sdr_materials_{jid}") or "").strip(),
                    "customer_conversations": str(
                        st.session_state.get(f"sdr_customer_{jid}") or ""
                    ).strip(),
                    "status": str((existing or {}).get("status") or "Draft"),
                    "main_goal": str(st.session_state.get(f"sdr_main_goal_{jid}") or "").strip(),
                    "midday_on_track": midday_ok,
                    "midday_reason": str(st.session_state.get(f"sdr_midday_reason_{jid}") or "").strip(),
                    "completed_today": str(st.session_state.get(f"sdr_done_{jid}") or "").strip(),
                    "not_completed": str(st.session_state.get(f"sdr_not_done_{jid}") or "").strip(),
                    "not_completed_reason": str(
                        st.session_state.get(f"sdr_not_done_why_{jid}") or ""
                    ).strip(),
                    "tomorrows_plan": str(st.session_state.get(f"sdr_tomorrow_{jid}") or "").strip(),
                    "delay_other_notes": str(
                        st.session_state.get(f"sdr_delay_other_notes_{jid}") or ""
                    ).strip(),
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

            if existing and existing.get("id"):
                rid = str(existing["id"])
                b1, b2, _b3 = st.columns(3, gap="small")
                with b1:
                    if str(existing.get("status") or "Draft") == "Draft" and st.button(
                        "Submit report", use_container_width=True, key=f"sdr_submit_{jid}"
                    ):
                        try:
                            submit_daily_report(rid, admin=admin_read)
                            st.success("Submitted to office.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
                with b2:
                    if effective_role() in {"admin", "manager"} and str(existing.get("status") or "") == "Submitted":
                        if st.button("Mark reviewed", use_container_width=True, key=f"sdr_review_{jid}"):
                            try:
                                prof = current_profile() or {}
                                review_daily_report(
                                    rid,
                                    reviewed_by=str(prof.get("id") or "").strip() or None,
                                    admin=admin_read,
                                )
                                st.success("Marked reviewed.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))

    if inline:
        _body()
    else:
        with st.expander(title, expanded=expand_sections):
            _body()


def render() -> None:
    render_page_header("Daily crew report", "Crew narrative summaries by job and date.")
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
