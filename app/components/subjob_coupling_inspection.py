"""Coupling Inspection section for Job Details subjob detail view."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.coupling_inspection_launcher import open_coupling_inspection
    from app.components.record_modal import detail_field_html, dialog_card_html, status_pill_html
    from app.services.coupling_inspection_service import (
        coupling_inspection_status_label,
        link_coupling_inspection_to_task,
        list_coupling_inspections,
        list_unlinked_coupling_inspections_for_job,
        unlink_coupling_inspection_from_task,
    )
except ImportError:
    from components.coupling_inspection_launcher import open_coupling_inspection  # type: ignore
    from components.record_modal import (  # type: ignore
        detail_field_html,
        dialog_card_html,
        status_pill_html,
    )
    from services.coupling_inspection_service import (  # type: ignore
        coupling_inspection_status_label,
        link_coupling_inspection_to_task,
        list_coupling_inspections,
        list_unlinked_coupling_inspections_for_job,
        unlink_coupling_inspection_from_task,
    )

JOB_SUBJOB_CI_LINK_MODE_KEY = "job_subjob_ci_link_mode"


def clear_job_subjob_coupling_state() -> None:
    st.session_state.pop(JOB_SUBJOB_CI_LINK_MODE_KEY, None)


def _link_mode_key(job_id: str, task_id: str) -> str:
    return f"{job_id}:{task_id}"


def _is_link_mode(job_id: str, task_id: str) -> bool:
    return str(st.session_state.get(JOB_SUBJOB_CI_LINK_MODE_KEY) or "") == _link_mode_key(job_id, task_id)


def _set_link_mode(job_id: str, task_id: str, active: bool) -> None:
    key = _link_mode_key(job_id, task_id)
    if active:
        st.session_state[JOB_SUBJOB_CI_LINK_MODE_KEY] = key
    elif st.session_state.get(JOB_SUBJOB_CI_LINK_MODE_KEY) == key:
        st.session_state.pop(JOB_SUBJOB_CI_LINK_MODE_KEY, None)


def _inspection_summary_label(insp: dict) -> str:
    hdr = insp.get("header") if isinstance(insp.get("header"), dict) else {}
    date_part = str(hdr.get("inspection_date") or insp.get("created_at") or "")[:10] or "—"
    status = coupling_inspection_status_label(str(insp.get("status") or "draft"))
    model = str(insp.get("coupling_model") or "Coupling Inspection").strip()
    return f"{date_part} · {status} · {model}"


def _inspection_detail_html(insp: dict) -> str:
    hdr = insp.get("header") if isinstance(insp.get("header"), dict) else {}
    status = coupling_inspection_status_label(str(insp.get("status") or "draft"))
    created = str(insp.get("created_at") or hdr.get("inspection_date") or "")[:10] or "—"
    completed = str(insp.get("completed_at") or "")[:10] or "—"
    technician = str(hdr.get("technician") or "").strip() or "—"
    notes = str(hdr.get("notes") or insp.get("notes") or "").strip()
    if not notes:
        fields = insp.get("inspection_fields")
        if isinstance(fields, dict):
            notes = str(fields.get("general_notes") or fields.get("comments") or "").strip()
    notes_display = html.escape(notes[:400] + ("…" if len(notes) > 400 else "")) if notes else "—"
    return (
        f'<div class="ips-detail-grid">'
        f"{detail_field_html('Type', 'Coupling Inspection')}"
        f'{detail_field_html("Status", status, html_value=status_pill_html(status))}'
        f"{detail_field_html('Inspection date', created)}"
        f"{detail_field_html('Completed', completed if completed != '—' else '—')}"
        f"{detail_field_html('Technician', technician)}"
        f"</div>"
        f'<p style="margin:0.75rem 0 0;font-size:0.875rem;color:#0f172a;line-height:1.5;">'
        f"<strong>Notes:</strong> {notes_display}</p>"
    )


def _render_link_existing_panel(*, job_id: str, task_id: str, task: dict, key_prefix: str) -> None:
    unlinked = list_unlinked_coupling_inspections_for_job(job_id)
    st.markdown(dialog_card_html("Coupling Inspection", "<p style=\"margin:0;font-size:0.875rem;color:#64748b;\">Select an existing inspection for this job.</p>"), unsafe_allow_html=True)
    if not unlinked:
        st.caption("No unlinked coupling inspections for this job.")
        if st.button("Cancel", key=f"{key_prefix}_link_cancel_empty"):
            _set_link_mode(job_id, task_id, False)
            st.rerun()
        return

    labels = [_inspection_summary_label(r) for r in unlinked]
    pick_ix = st.selectbox(
        "Coupling inspection",
        range(len(unlinked)),
        format_func=lambda i: labels[i],
        key=f"{key_prefix}_link_pick",
    )
    btn_l, btn_r = st.columns(2)
    with btn_l:
        if st.button("Save link", type="primary", key=f"{key_prefix}_link_save"):
            iid = str(unlinked[int(pick_ix)].get("id") or "").strip()
            if iid:
                result = link_coupling_inspection_to_task(iid, task, job_id=job_id)
                if result.ok:
                    _set_link_mode(job_id, task_id, False)
                    st.success("Coupling inspection linked.")
                    st.rerun()
                st.error(str(result.error or "Could not link inspection."))
    with btn_r:
        if st.button("Cancel", key=f"{key_prefix}_link_cancel"):
            _set_link_mode(job_id, task_id, False)
            st.rerun()


def _render_linked_inspection(insp: dict, *, job_id: str, task_id: str, key_prefix: str) -> None:
    iid = str(insp.get("id") or "").strip()
    st.markdown(dialog_card_html("Coupling Inspection", _inspection_detail_html(insp)), unsafe_allow_html=True)
    open_col, unlink_col = st.columns(2)
    with open_col:
        if st.button(
            "Open Inspection",
            key=f"{key_prefix}_open_{iid}",
            use_container_width=True,
        ):
            open_coupling_inspection(
                job_id=job_id,
                task_id=task_id,
                inspection_id=iid,
            )
    with unlink_col:
        if st.button(
            "Unlink",
            key=f"{key_prefix}_unlink_{iid}",
            use_container_width=True,
        ):
            result = unlink_coupling_inspection_from_task(iid)
            if result.ok:
                st.success("Inspection unlinked from this subjob.")
                st.rerun()
            st.error(str(result.error or "Could not unlink inspection."))


def render_subjob_coupling_inspection_section(
    task: dict,
    job: dict,
) -> None:
    """Coupling Inspection card inside Job Details subjob detail."""
    job_id = str(job.get("id") or "").strip()
    task_id = str(task.get("id") or "").strip()
    if not job_id or not task_id:
        return

    key_prefix = f"job_subjob_ci_{job_id}_{task_id}"
    linked = list_coupling_inspections(job_id=job_id, task_id=task_id)

    if _is_link_mode(job_id, task_id):
        _render_link_existing_panel(job_id=job_id, task_id=task_id, task=task, key_prefix=key_prefix)
        return

    if linked:
        for idx, insp in enumerate(linked[:5]):
            prefix = f"{key_prefix}_{idx}" if idx else key_prefix
            _render_linked_inspection(insp, job_id=job_id, task_id=task_id, key_prefix=prefix)
            if idx < len(linked[:5]) - 1:
                st.divider()
        return

    empty_html = (
        '<p style="margin:0;font-size:0.875rem;color:#64748b;">'
        "No coupling inspection linked yet.</p>"
    )
    st.markdown(dialog_card_html("Coupling Inspection", empty_html), unsafe_allow_html=True)
    btn_l, btn_r = st.columns(2)
    with btn_l:
        if st.button("+ Link Coupling Inspection", key=f"{key_prefix}_link", use_container_width=True):
            _set_link_mode(job_id, task_id, True)
            st.rerun()
    with btn_r:
        if st.button(
            "+ Create Coupling Inspection",
            type="primary",
            key=f"{key_prefix}_create",
            use_container_width=True,
        ):
            open_coupling_inspection(job_id=job_id, task_id=task_id)
