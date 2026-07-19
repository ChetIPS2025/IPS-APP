"""Lazy Job Subjob detail subsections."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.components.record_modal import detail_field_html, dialog_card_html, status_pill_html
from app.utils.formatting import fmt_date

_SUBJOB_SECTION_KEY = "ips_subjob_detail_section"


def subjob_section_key(task_id: str) -> str:
    return f"{_SUBJOB_SECTION_KEY}_{task_id}"


def render_job_subjob_detail_sections(
    task: dict[str, Any],
    job: dict[str, Any],
    *,
    assignee_label: str = "",
) -> None:
    from app.perf_debug import perf_span

    tid = str(task.get("id") or "")
    sk = subjob_section_key(tid)
    section = str(st.session_state.get(sk) or "Overview")
    sections = ("Overview", "Photos", "Documents", "Coupling Inspection", "Notes")
    cols = st.columns(len(sections), gap="small")
    for col, name in zip(cols, sections):
        with col:
            if st.button(name, key=f"subjob_sec_{tid}_{name}", use_container_width=True):
                st.session_state[sk] = name
                st.rerun()

    if section == "Overview":
        with perf_span("tasks.subjob.detail_lookup"):
            title = str(task.get("title") or "—")
            status = str(task.get("status") or "Open")
            priority = str(task.get("priority") or "Medium")
            assignee = assignee_label or str(task.get("assigned_to_display") or "Unassigned")
            due = fmt_date(task.get("due_date"))
            job_number = str(job.get("job_number") or "—")
            description = str(task.get("description") or "No description.")
            overview_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Subjob', title)}"
                f'{detail_field_html("Status", status, html_value=status_pill_html(status))}'
                f"{detail_field_html('Priority', priority)}"
                f"{detail_field_html('Assigned To', assignee)}"
                f"{detail_field_html('Due Date', due)}"
                f"{detail_field_html('Parent Job', job_number)}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Overview", overview_html), unsafe_allow_html=True)
            desc_html = (
                f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
                f"{html.escape(description)}</p>"
            )
            st.markdown(dialog_card_html("Description / Scope", desc_html), unsafe_allow_html=True)
    elif section == "Photos":
        with perf_span("tasks.subjob.photos"):
            from app.components.subjob_photos_documents import render_subjob_photos_section

            render_subjob_photos_section(task, job)
    elif section == "Documents":
        with perf_span("tasks.subjob.documents"):
            from app.components.subjob_photos_documents import render_subjob_documents_section

            render_subjob_documents_section(task, job)
    elif section == "Coupling Inspection":
        with perf_span("tasks.subjob.coupling"):
            from app.components.subjob_coupling_inspection import render_subjob_coupling_inspection_section

            render_subjob_coupling_inspection_section(task, job)
    elif section == "Notes":
        notes = str(task.get("notes") or "").strip()
        if notes:
            notes_html = (
                f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
                f"{html.escape(notes)}</p>"
            )
            st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)
        else:
            st.caption("No notes entered.")


__all__ = ["render_job_subjob_detail_sections", "subjob_section_key"]
