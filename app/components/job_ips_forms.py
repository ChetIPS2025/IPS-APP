"""IPS Forms tab — choose, create, and open IPS forms for a job."""

from __future__ import annotations

import streamlit as st

try:
    from app.components.coupling_inspection_launcher import open_coupling_inspection
    from app.components.record_modal import detail_field_html, dialog_card_html, status_pill_html
    from app.services.coupling_inspection_service import (
        coupling_inspection_status_label,
        list_coupling_inspections,
    )
    from app.services.tasks_service import get_tasks_by_job
except ImportError:
    from components.coupling_inspection_launcher import open_coupling_inspection  # type: ignore
    from components.record_modal import (  # type: ignore
        detail_field_html,
        dialog_card_html,
        status_pill_html,
    )
    from services.coupling_inspection_service import (  # type: ignore
        coupling_inspection_status_label,
        list_coupling_inspections,
    )
    from services.tasks_service import get_tasks_by_job  # type: ignore

IPS_FORM_TYPES: tuple[dict[str, str], ...] = (
    {
        "id": "coupling_inspection",
        "label": "Coupling Inspection",
        "description": (
            "Digital coupling inspection with torque verification, photos, signatures, and PDF export."
        ),
    },
)


def _subjob_select_options(job_id: str) -> tuple[list[str], list[str]]:
    labels: list[str] = []
    ids: list[str] = []
    for task in get_tasks_by_job(job_id, include_closed=True) or []:
        tid = str(task.get("id") or "").strip()
        if not tid:
            continue
        title = str(task.get("title") or "Subjob").strip() or "Subjob"
        labels.append(title)
        ids.append(tid)
    return labels, ids


def _coupling_inspection_summary(insp: dict) -> str:
    hdr = insp.get("header") if isinstance(insp.get("header"), dict) else {}
    date_part = str(hdr.get("inspection_date") or insp.get("created_at") or "")[:10] or "—"
    status = coupling_inspection_status_label(str(insp.get("status") or "draft"))
    model = str(insp.get("coupling_model") or "Coupling Inspection").strip()
    subjob = str(insp.get("subjob_name") or insp.get("task_title") or "").strip()
    subjob_part = f" · {subjob}" if subjob else ""
    return f"{date_part} · {status} · {model}{subjob_part}"


def _render_coupling_inspection_row(
    insp: dict,
    *,
    job_id: str,
    key_prefix: str,
    row_index: int,
) -> None:
    iid = str(insp.get("id") or "").strip()
    if not iid:
        return
    task_id = str(insp.get("task_id") or insp.get("subjob_id") or "").strip() or None
    status = coupling_inspection_status_label(str(insp.get("status") or "draft"))
    hdr = insp.get("header") if isinstance(insp.get("header"), dict) else {}
    subjob = str(insp.get("subjob_name") or insp.get("task_title") or "").strip() or "—"
    body = (
        f'<div class="ips-detail-grid">'
        f"{detail_field_html('Form', 'Coupling Inspection')}"
        f'{detail_field_html("Status", status, html_value=status_pill_html(status))}'
        f"{detail_field_html('Inspection date', str(hdr.get('inspection_date') or insp.get('created_at') or '')[:10] or '—')}"
        f"{detail_field_html('Subjob', subjob)}"
        f"</div>"
    )
    st.markdown(dialog_card_html(_coupling_inspection_summary(insp), body), unsafe_allow_html=True)
    if st.button(
        "Open form",
        key=f"{key_prefix}_open_{iid}_{row_index}",
        use_container_width=True,
    ):
        open_coupling_inspection(
            job_id=job_id,
            task_id=task_id,
            inspection_id=iid,
        )


def _render_existing_forms(*, job_id: str, form_type_id: str, key_prefix: str) -> None:
    st.markdown("#### Forms on this job")
    if form_type_id == "coupling_inspection":
        rows = list_coupling_inspections(job_id=job_id)
        if not rows:
            st.caption("No coupling inspection forms for this job yet.")
            return
        for idx, insp in enumerate(rows):
            _render_coupling_inspection_row(
                insp,
                job_id=job_id,
                key_prefix=key_prefix,
                row_index=idx,
            )
            if idx < len(rows) - 1:
                st.divider()
        return
    st.caption("No forms available for this type yet.")


def render_job_ips_forms_tab(job: dict) -> None:
    """IPS Forms tab inside Job Details."""
    job_id = str(job.get("id") or "").strip()
    if not job_id:
        st.info("Save this job before creating IPS forms.")
        return

    key_prefix = f"job_ips_forms_{job_id}"
    st.markdown(
        '<span class="ips-job-forms-tab-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Choose a form type, optionally link it to a subjob, then create a new form or open an existing one."
    )

    form_labels = [f["label"] for f in IPS_FORM_TYPES]
    form_ids = [f["id"] for f in IPS_FORM_TYPES]
    form_ix = st.selectbox(
        "Form type",
        range(len(form_labels)),
        format_func=lambda i: form_labels[i],
        key=f"{key_prefix}_type",
    )
    form_type = IPS_FORM_TYPES[int(form_ix)]
    st.caption(str(form_type.get("description") or ""))

    subjob_labels, subjob_ids = _subjob_select_options(job_id)
    link_labels = ["— Job-level (no subjob) —", *subjob_labels]
    link_ids = ["", *subjob_ids]
    link_ix = st.selectbox(
        "Link to subjob (optional)",
        range(len(link_labels)),
        format_func=lambda i: link_labels[i],
        key=f"{key_prefix}_subjob",
    )
    selected_task_id = str(link_ids[int(link_ix)] or "").strip() or None

    create_col, open_col = st.columns(2, gap="small")
    with create_col:
        if st.button(
            "Create new form",
            type="primary",
            key=f"{key_prefix}_create",
            use_container_width=True,
        ):
            if form_type["id"] == "coupling_inspection":
                open_coupling_inspection(job_id=job_id, task_id=selected_task_id)
            else:
                st.warning("This form type is not available yet.")
    with open_col:
        st.caption("Use the list below to reopen saved forms for this job.")

    st.divider()
    _render_existing_forms(
        job_id=job_id,
        form_type_id=str(form_ids[int(form_ix)]),
        key_prefix=key_prefix,
    )
