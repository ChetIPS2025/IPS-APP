"""Coupling Inspection & Torque Verification — IPS digital V7 form."""

from __future__ import annotations

import html
from datetime import date
from typing import Any
from uuid import uuid4

import streamlit as st

from app.auth import current_profile
from app.branding import header_logo_html
from app.components.coupling_inspection_launcher import coupling_inspection_context
from app.components.signature_pad import render_signature_field
from app.pages._core._access import begin_module
from app.pages._core._data import load_assets, load_jobs
from app.services.coupling_inspection_pdf import build_coupling_inspection_pdf_bytes
from app.services.coupling_inspection_service import (
    PHOTO_SLOTS,
    PHOTO_SLOT_LABELS,
    apply_task_link_to_payload,
    build_header_context,
    completion_percentage,
    fetch_job_task,
    get_coupling_inspection,
    list_coupling_inspections,
    list_job_tasks_for_job,
    new_inspection_payload,
    pdf_export_filename,
    photo_view_url,
    save_coupling_inspection,
    task_link_option_label,
    task_link_snapshot,
    upload_inspection_photo,
    validate_for_complete,
)
from app.services.coupling_inspection_specs import (
    COUPLING_MODEL_OPTIONS,
    FORM_VERSION,
    INSPECTION_RESULT_ITEMS,
    default_inspection_results,
    normalize_torque_rows,
    specs_for_model,
    torque_pattern_svg,
    torque_pass_labels,
    torque_sequence_caption,
)
from app.styles import inject_coupling_inspection_css
_DRAFT_KEY = "coupling_insp_draft"
_FORM_SIGNATURE_ROLES: tuple[str, ...] = ("technician", "supervisor")
_SIGNATURE_LABELS = {
    "technician": "Technician",
    "supervisor": "Supervisor",
}


def _find_job(job_id: str | None) -> dict[str, Any] | None:
    if not job_id:
        return None
    for j in load_jobs():
        if str(j.get("id") or "") == job_id:
            return j
    return None


def _find_equipment(equipment_id: str | None) -> dict[str, Any] | None:
    if not equipment_id:
        return None
    for a in load_assets():
        if str(a.get("id") or "") == equipment_id:
            return a
    return None


def _session_key(record: dict[str, Any]) -> str:
    return f"ci_{record.get('id') or 'new'}"


def _status_label(status: str) -> str:
    s = str(status or "draft").strip().lower()
    if s == "complete":
        return "Completed"
    if s == "exported":
        return "Exported"
    return "Draft"


def _load_draft(ctx: dict[str, str | None]) -> dict[str, Any]:
    insp_id = ctx.get("inspection_id")
    if insp_id:
        existing = get_coupling_inspection(insp_id)
        if existing:
            return existing
    cached = st.session_state.get(_DRAFT_KEY)
    if isinstance(cached, dict):
        return cached
    job = _find_job(ctx.get("job_id"))
    equip = _find_equipment(ctx.get("equipment_id"))
    job_task = fetch_job_task(ctx.get("task_id"))
    prof = current_profile() or {}
    tech = str(prof.get("full_name") or prof.get("name") or "").strip()
    header = build_header_context(job=job, equipment=equip, technician=tech, job_task=job_task)
    return new_inspection_payload(
        job_id=ctx.get("job_id"),
        equipment_id=ctx.get("equipment_id"),
        customer_id=str(job.get("customer_id") or "") if job else None,
        header=header,
        task_id=ctx.get("task_id"),
        job_task=job_task,
    )


def _apply_model_change(record: dict[str, Any], model: str) -> dict[str, Any]:
    out = dict(record)
    out["coupling_model"] = model
    out["specs"] = specs_for_model(model)
    fields = default_inspection_results()
    prev = dict(out.get("inspection_fields") or {})
    if isinstance(prev, dict):
        for key in fields:
            if key in prev and isinstance(prev[key], dict):
                fields[key] = prev[key]
    lub = out["specs"].get("lubricant_type_default") or ""
    if lub and not str(fields.get("lubricant_type", {}).get("value") or "").strip():
        fields["lubricant_type"]["value"] = lub
    out["inspection_fields"] = fields
    out["torque_rows"] = normalize_torque_rows([], model_key=model)
    return out


def _render_form_header(record: dict[str, Any]) -> None:
    status = _status_label(str(record.get("status") or "draft"))
    status_cls = status.lower().replace(" ", "-")
    hdr = record.get("header") or {}
    st.markdown(
        f'<div class="ips-coupling-v7-header">'
        f'{header_logo_html(height=52, alt="IPS")}'
        f'<div class="ips-coupling-v7-header-text">'
        f'<div class="ips-coupling-v7-title">IPS Coupling Inspection &amp; Torque Verification</div>'
        f'<div class="ips-coupling-v7-meta">'
        f'<span class="ips-coupling-v7-version">{html.escape(FORM_VERSION)}</span>'
        f'<span class="ips-coupling-v7-status ips-coupling-v7-status-{html.escape(status_cls)}">'
        f"{html.escape(status)}</span>"
        f"</div></div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="ips-coupling-v7-job-bar">'
        f"<span><strong>Customer:</strong> {html.escape(str(hdr.get('customer') or '—'))}</span>"
        f"<span><strong>Job #:</strong> {html.escape(str(hdr.get('job_number') or '—'))}</span>"
        f"<span><strong>WO #:</strong> {html.escape(str(hdr.get('work_order_number') or '—'))}</span>"
        f"<span><strong>Equipment:</strong> {html.escape(str(hdr.get('equipment_name') or '—'))}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    task_label = str(record.get("subjob_name") or hdr.get("subjob_name") or "").strip()
    task_title = str(record.get("task_title") or hdr.get("task_title") or "").strip()
    if task_label:
        extra = f" — {html.escape(task_title)}" if task_title and task_title != task_label else ""
        st.markdown(
            f'<div class="ips-coupling-v7-task-bar">'
            f"<span><strong>Task / Subjob:</strong> {html.escape(task_label)}{extra}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_task_link_section(
    record: dict[str, Any],
    *,
    sk: str,
    locked: bool,
    job_id: str | None,
) -> dict[str, Any]:
    """Pick the job task / subjob this inspection belongs to."""
    jid = str(job_id or record.get("job_id") or "").strip()
    if not jid:
        return record

    tasks = list_job_tasks_for_job(jid)
    if not tasks:
        st.caption("No tasks on this job yet. Add tasks under **Job Database → Tasks** to link this inspection.")
        return record

    options: list[str | None] = [None, *[str(t.get("id") or "").strip() for t in tasks]]
    labels = ["— Select task / subjob —"] + [task_link_option_label(t) for t in tasks]
    cur_tid = str(record.get("task_id") or record.get("subjob_id") or "").strip() or None
    try:
        pick_ix = options.index(cur_tid)
    except ValueError:
        pick_ix = 0

    picked = st.selectbox(
        "Task / Subjob",
        options,
        index=pick_ix,
        format_func=lambda tid, _labels=labels, _opts=options: _labels[_opts.index(tid)],
        disabled=locked,
        key=f"{sk}_task_link",
        help="Link this inspection to the correct PM task or subjob under the job.",
    )
    if picked:
        job_task = next((t for t in tasks if str(t.get("id") or "") == picked), None)
        if job_task:
            record = apply_task_link_to_payload(record, job_task=job_task, job_id=jid)
            hdr = dict(record.get("header") or {})
            snap = task_link_snapshot(job_task)
            hdr.update(
                {
                    "task_id": snap.get("task_id"),
                    "subjob_name": snap.get("subjob_name"),
                    "task_title": snap.get("task_title"),
                    "linked_task_status": snap.get("linked_task_status"),
                }
            )
            loc = str(job_task.get("location") or "").strip()
            if loc:
                hdr["location"] = loc
            record["header"] = hdr
            record["job_id"] = jid
    elif cur_tid:
        for key in ("task_id", "subjob_id", "subjob_name", "task_title", "linked_task_status"):
            record[key] = None if key.endswith("_id") else ""
    return record


def _render_header_section(record: dict[str, Any], *, sk: str, locked: bool) -> dict[str, Any]:
    st.markdown("## 1. Job Information")
    record = _render_task_link_section(
        record,
        sk=sk,
        locked=locked,
        job_id=str(record.get("job_id") or ""),
    )
    hdr = dict(record.get("header") or {})
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.text_input("Customer", value=str(hdr.get("customer") or ""), disabled=True, key=f"{sk}_hdr_customer")
        st.text_input("Job #", value=str(hdr.get("job_number") or ""), disabled=True, key=f"{sk}_hdr_job")
        st.text_input("Work Order #", value=str(hdr.get("work_order_number") or ""), disabled=True, key=f"{sk}_hdr_wo")
        st.text_input("Equipment", value=str(hdr.get("equipment_name") or ""), disabled=True, key=f"{sk}_hdr_eq")
        st.text_input("Asset #", value=str(hdr.get("asset_number") or ""), disabled=True, key=f"{sk}_hdr_asset")
    with c2:
        st.text_input("Location", value=str(hdr.get("location") or ""), disabled=True, key=f"{sk}_hdr_loc")
        insp_date = st.date_input(
            "Date",
            value=date.fromisoformat(str(hdr.get("inspection_date") or date.today().isoformat())[:10]),
            disabled=locked,
            key=f"{sk}_hdr_date",
        )
        hdr["inspection_date"] = insp_date.isoformat()
        hdr["technician"] = st.text_input(
            "Technician",
            value=str(hdr.get("technician") or ""),
            disabled=locked,
            key=f"{sk}_hdr_tech",
        ).strip()
        hdr["supervisor"] = st.text_input(
            "Supervisor",
            value=str(hdr.get("supervisor") or ""),
            disabled=locked,
            key=f"{sk}_hdr_sup",
        ).strip()
    record["header"] = hdr
    return record


def _spec_card(label: str, value: str) -> str:
    return (
        f'<div class="ips-coupling-spec-card">'
        f'<div class="ips-coupling-spec-label">{html.escape(label)}</div>'
        f'<div class="ips-coupling-spec-value">{html.escape(value)}</div>'
        f"</div>"
    )


def _render_specs_section(record: dict[str, Any], *, sk: str, locked: bool) -> dict[str, Any]:
    st.markdown("## 2. Coupling Specifications")
    model_ix = (
        COUPLING_MODEL_OPTIONS.index(record.get("coupling_model"))
        if record.get("coupling_model") in COUPLING_MODEL_OPTIONS
        else 0
    )
    model = st.selectbox(
        "Coupling model",
        COUPLING_MODEL_OPTIONS,
        index=model_ix,
        disabled=locked,
        key=f"{sk}_model",
    )
    if model != record.get("coupling_model"):
        record = _apply_model_change(record, model)

    specs = dict(record.get("specs") or specs_for_model(model))
    custom = model == "Manual/Custom Coupling"

    if custom:
        s1, s2 = st.columns(2, gap="small")
        with s1:
            specs["coupling_type"] = st.text_input("Coupling Type", value=str(specs.get("coupling_type") or ""), disabled=locked, key=f"{sk}_spec_type")
            specs["flange_bolts"] = st.text_input("Flange Bolts", value=str(specs.get("flange_bolts") or ""), disabled=locked, key=f"{sk}_spec_bolts")
        with s2:
            specs["final_torque_ft_lb"] = st.number_input("Final Torque (ft-lb)", value=float(specs.get("final_torque_ft_lb") or 150), disabled=locked, key=f"{sk}_spec_final")
            specs["standard_hub_gap_in"] = st.number_input("Standard Hub Gap (in)", value=float(specs.get("standard_hub_gap_in") or 0.188), format="%.3f", disabled=locked, key=f"{sk}_spec_gap")
    else:
        gap = specs.get("standard_hub_gap_in")
        lb = specs.get("lubricant_quantity_lb")
        oz = specs.get("lubricant_quantity_oz")
        cards = (
            _spec_card("Coupling Model", str(model))
            + _spec_card("Coupling Type", str(specs.get("coupling_type") or "—"))
            + _spec_card("Bolt Count", str(specs.get("bolt_count") or 8))
            + _spec_card("Bolt Size", str(specs.get("flange_bolts") or "—"))
            + _spec_card("Final Torque", f"{specs.get('final_torque_ft_lb', '—')} ft-lb / {specs.get('final_torque_nm', '—')} Nm")
            + _spec_card("Standard Hub Gap", f"{gap:g} in" if gap is not None else "—")
            + _spec_card("Lubricant Type", str(specs.get("lubricant_type_default") or "—"))
            + _spec_card("Lubricant Quantity", f"{lb:g} lb / {oz:g} oz" if lb is not None else "—")
        )
        st.markdown(f'<div class="ips-coupling-spec-grid">{cards}</div>', unsafe_allow_html=True)

    record["coupling_model"] = model
    record["specs"] = specs
    return record


def _render_torque_table(record: dict[str, Any], *, sk: str, locked: bool) -> dict[str, Any]:
    specs = record.get("specs") or {}
    p1_lbl, p2_lbl, pf_lbl = torque_pass_labels(specs)
    st.markdown("## 3. Torque Verification")
    st.caption(f"8-bolt sequence: {torque_sequence_caption()}")

    pat_col, _ = st.columns([1, 2], gap="medium")
    with pat_col:
        st.markdown(torque_pattern_svg(), unsafe_allow_html=True)

    rows = normalize_torque_rows(record.get("torque_rows"), model_key=str(record.get("coupling_model") or "1030G20"))
    updated: list[dict[str, Any]] = []

    hdr = st.columns([0.35, 0.75, 0.85, 0.85, 0.85, 0.9, 0.55, 0.55, 1.2])
    for col, lbl in zip(
        hdr,
        ["Bolt #", "Clock", p1_lbl, p2_lbl, pf_lbl, "Witness Initial", "Pass", "Fail", "Notes"],
    ):
        col.markdown(f"**{lbl}**")

    for i, row in enumerate(rows):
        rcols = st.columns([0.35, 0.75, 0.85, 0.85, 0.85, 0.9, 0.55, 0.55, 1.2], gap="small")
        with rcols[0]:
            st.markdown(f"**{row.get('order', i + 1)}**")
        with rcols[1]:
            st.markdown(str(row.get("clock_position") or ""))
        with rcols[2]:
            row["pass1_checked"] = st.checkbox("75", value=bool(row.get("pass1_checked")), disabled=locked, key=f"{sk}_p1_{i}", label_visibility="collapsed")
        with rcols[3]:
            row["pass2_checked"] = st.checkbox("112", value=bool(row.get("pass2_checked")), disabled=locked, key=f"{sk}_p2_{i}", label_visibility="collapsed")
        with rcols[4]:
            row["final_checked"] = st.checkbox("150", value=bool(row.get("final_checked")), disabled=locked, key=f"{sk}_pf_{i}", label_visibility="collapsed")
        with rcols[5]:
            row["witness_initials"] = st.text_input(
                "Initials",
                value=str(row.get("witness_initials") or ""),
                disabled=locked,
                key=f"{sk}_wit_{i}",
                label_visibility="collapsed",
                placeholder="Initials",
            ).strip()
        pf = row.get("pass_fail")
        with rcols[6]:
            pass_ok = st.checkbox("Pass", value=(pf == "pass"), disabled=locked, key=f"{sk}_pass_{i}", label_visibility="collapsed")
        with rcols[7]:
            fail_ok = st.checkbox("Fail", value=(pf == "fail"), disabled=locked, key=f"{sk}_fail_{i}", label_visibility="collapsed")
        if pass_ok and not fail_ok:
            row["pass_fail"] = "pass"
        elif fail_ok and not pass_ok:
            row["pass_fail"] = "fail"
        elif not pass_ok and not fail_ok:
            row["pass_fail"] = None
        with rcols[8]:
            row["notes"] = st.text_input("Notes", value=str(row.get("notes") or ""), disabled=locked, key=f"{sk}_notes_{i}", label_visibility="collapsed")
        updated.append(row)

    record["torque_rows"] = updated
    return record


def _render_inspection_results(record: dict[str, Any], *, sk: str, locked: bool) -> dict[str, Any]:
    st.markdown("## 4. Inspection Results")
    fields = dict(record.get("inspection_fields") or default_inspection_results())

    for field_key, label, kind in INSPECTION_RESULT_ITEMS:
        item = dict(fields.get(field_key) or {"value": "", "pass": False, "fail": False, "na": False, "notes": ""})
        st.markdown(f"**{label}**")
        cols = st.columns([1.4, 0.5, 0.5, 0.5, 1.6], gap="small")
        with cols[0]:
            if kind == "number":
                val = item.get("value")
                item["value"] = st.number_input(
                    label,
                    value=float(val) if val not in (None, "") else 0.0,
                    format="%.3f",
                    disabled=locked,
                    key=f"{sk}_insp_val_{field_key}",
                    label_visibility="collapsed",
                )
            elif kind == "bool":
                item["value"] = st.checkbox(
                    label,
                    value=bool(item.get("value")),
                    disabled=locked,
                    key=f"{sk}_insp_val_{field_key}",
                    label_visibility="collapsed",
                )
            else:
                item["value"] = st.text_input(
                    label,
                    value=str(item.get("value") or ""),
                    disabled=locked,
                    key=f"{sk}_insp_val_{field_key}",
                    label_visibility="collapsed",
                )
        with cols[1]:
            item["pass"] = st.checkbox("Pass", value=bool(item.get("pass")), disabled=locked, key=f"{sk}_insp_pass_{field_key}")
        with cols[2]:
            item["fail"] = st.checkbox("Fail", value=bool(item.get("fail")), disabled=locked, key=f"{sk}_insp_fail_{field_key}")
        with cols[3]:
            item["na"] = st.checkbox("N/A", value=bool(item.get("na")), disabled=locked, key=f"{sk}_insp_na_{field_key}")
        with cols[4]:
            item["notes"] = st.text_input(
                "Notes",
                value=str(item.get("notes") or ""),
                disabled=locked,
                key=f"{sk}_insp_notes_{field_key}",
                label_visibility="collapsed",
                placeholder="Notes",
            )
        fields[field_key] = item

    record["inspection_fields"] = fields
    return record


def _upload_record_id(record: dict[str, Any]) -> str:
    rid = str(record.get("id") or "").strip()
    if rid:
        return rid
    key = "coupling_insp_upload_id"
    if key not in st.session_state:
        st.session_state[key] = str(uuid4())
    return str(st.session_state[key])


def _render_photos_section(record: dict[str, Any], *, sk: str, locked: bool) -> dict[str, Any]:
    st.markdown("## 5. Photos / Attachments")
    attachments = list(record.get("photo_attachments") or [])
    rid = _upload_record_id(record)
    if not record.get("id"):
        st.caption("Save draft to link uploads to the inspection record.")

    for slot in PHOTO_SLOTS:
        label = PHOTO_SLOT_LABELS.get(slot, slot)
        existing = next((a for a in attachments if str(a.get("slot") or a.get("category") or "") == slot), None)
        st.markdown(f"**{label}**")
        if existing:
            url = photo_view_url(existing)
            cap = str(existing.get("caption") or label)
            if url:
                st.image(url, caption=cap, use_container_width=True)
            else:
                st.caption(f"{cap} — {existing.get('file_name') or 'on file'}")
        if not locked:
            caption = st.text_input(
                "Caption",
                value=str(existing.get("caption") or "") if existing else "",
                key=f"{sk}_photo_cap_{slot}",
                placeholder="Optional caption",
            )
            up = st.file_uploader(
                "Upload or capture photo",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"{sk}_photo_{slot}",
                help="Use iPad camera or photo library",
            )
            if up is not None:
                attachments, err = upload_inspection_photo(
                    inspection_id=rid,
                    slot=slot,
                    uploaded_file=up,
                    existing_attachments=attachments,
                    caption=caption,
                )
                if err:
                    st.error(err)
                else:
                    st.success(f"{label} uploaded.")
    record["photo_attachments"] = attachments
    return record


def _render_signatures_section(record: dict[str, Any], *, sk: str, locked: bool) -> dict[str, Any]:
    st.markdown("## 6. Signatures")
    meta = dict(record.get("signatures_meta") or {})
    updated: dict[str, Any] = dict(meta)
    for role in _FORM_SIGNATURE_ROLES:
        label = _SIGNATURE_LABELS.get(role, role.replace("_", " ").title())
        required = role == "technician"
        updated[role] = render_signature_field(
            label=label,
            role_key=f"{sk}_{role}",
            existing=meta.get(role),
            disabled=locked,
            required=required,
        )
    record["signatures_meta"] = updated
    record["technician_signature"] = updated["technician"]["signature_image"]
    record["supervisor_signature"] = updated["supervisor"]["signature_image"]
    cust = meta.get("customer_representative") if isinstance(meta.get("customer_representative"), dict) else {}
    record["customer_signature"] = str(cust.get("signature_image") or record.get("customer_signature") or "")
    return record


def _render_inspection_form(record: dict[str, Any]) -> None:
    sk = _session_key(record)
    locked = str(record.get("status") or "").lower() in {"complete", "exported"} and not st.session_state.get(
        f"{sk}_edit_mode"
    )
    _render_form_header(record)
    pct = completion_percentage(record)
    st.progress(min(pct / 100.0, 1.0), text=f"Completion: {pct}%")

    record = _render_header_section(record, sk=sk, locked=locked)
    record = _render_specs_section(record, sk=sk, locked=locked)
    record = _render_torque_table(record, sk=sk, locked=locked)
    record = _render_inspection_results(record, sk=sk, locked=locked)
    record = _render_photos_section(record, sk=sk, locked=locked)
    record = _render_signatures_section(record, sk=sk, locked=locked)
    st.session_state[_DRAFT_KEY] = record

    st.markdown("## 7. Final PDF Export")
    a1, a2, a3, a4 = st.columns(4, gap="small")
    save_draft = a1.button("Save Draft", type="secondary", use_container_width=True, key=f"{sk}_save", disabled=locked)
    mark_complete = a2.button("Mark Completed", type="primary", use_container_width=True, key=f"{sk}_complete", disabled=locked)
    gen_pdf = a3.button("Generate Final PDF", use_container_width=True, key=f"{sk}_pdf")
    if locked and a4.button("Reopen for Edit", use_container_width=True, key=f"{sk}_reopen"):
        st.session_state[f"{sk}_edit_mode"] = True
        st.rerun()

    if save_draft:
        if st.session_state.get(f"{sk}_edit_mode"):
            record["status"] = "draft"
            record["completed_at"] = None
        result = save_coupling_inspection(record, inspection_id=str(record.get("id") or "") or None)
        if result.ok and result.data:
            st.session_state[_DRAFT_KEY] = result.data
            st.session_state["coupling_insp_id"] = str(result.data.get("id") or "")
            st.success("Draft saved.")
            st.rerun()
        else:
            st.error(result.error or "Could not save draft.")

    if mark_complete:
        errors = validate_for_complete(record)
        if errors:
            for err in errors[:8]:
                st.error(err)
        else:
            result = save_coupling_inspection(record, inspection_id=str(record.get("id") or "") or None, mark_complete=True)
            if result.ok and result.data:
                st.session_state[_DRAFT_KEY] = result.data
                st.session_state.pop(f"{sk}_edit_mode", None)
                st.success("Inspection marked completed.")
                st.rerun()
            else:
                st.error(result.error or "Could not complete inspection.")

    if gen_pdf:
        try:
            pdf_bytes = build_coupling_inspection_pdf_bytes(record)
            if record.get("id"):
                save_coupling_inspection(record, inspection_id=str(record.get("id")), mark_exported=True)
            st.download_button(
                "Download IPS Coupling Inspection PDF",
                data=pdf_bytes,
                file_name=pdf_export_filename(record),
                mime="application/pdf",
                use_container_width=True,
                key=f"{sk}_pdf_dl",
            )
        except Exception as exc:
            st.error(f"PDF generation failed: {exc}")


def _render_existing_list(ctx: dict[str, str | None]) -> str | None:
    rows = list_coupling_inspections(
        job_id=ctx.get("job_id"),
        equipment_id=ctx.get("equipment_id"),
        task_id=ctx.get("task_id"),
    )
    if not rows:
        return None
    st.markdown("#### Existing inspections")

    def _row_label(r: dict[str, Any]) -> str:
        task = str(r.get("subjob_name") or "").strip()
        task_part = f" · {task}" if task else ""
        return (
            f"{r.get('header', {}).get('inspection_date', '—')} · "
            f"{_status_label(str(r.get('status') or 'draft'))} · "
            f"{r.get('coupling_model')}{task_part}"
        )

    options = ["— New inspection —"] + [_row_label(r) for r in rows]
    pick = st.selectbox("Open inspection", options, key="ci_pick_existing")
    if pick == "— New inspection —":
        return None
    return str(rows[options.index(pick) - 1].get("id") or "")


def _render_context_picker() -> None:
    """Let users pick job/equipment when opening Coupling Inspection from the sidebar."""
    from app.components.coupling_inspection_launcher import open_coupling_inspection
    from app.pages._core._data import load_assets, load_jobs
    from app.services.jobs_service import job_row_select_label
    st.info("Select a job and/or equipment record, then continue.")
    assets = [a for a in load_assets() if str(a.get("id") or "").strip()]
    job_opts = ["— Select job —"] + [job_row_select_label(j) for j in jobs]
    asset_opts = ["— Select equipment —"] + [
        f"{a.get('asset_number') or a.get('asset_tag') or '—'} — {a.get('name') or a.get('asset_name') or 'Asset'}"
        for a in assets
    ]
    c1, c2 = st.columns(2)
    with c1:
        job_pick = st.selectbox("Job", job_opts, key="ci_ctx_job_pick")
    with c2:
        asset_pick = st.selectbox("Equipment", asset_opts, key="ci_ctx_asset_pick")
    if st.button("Continue", key="ci_ctx_continue", type="primary"):
        job_id = None
        if job_pick != job_opts[0]:
            ix = job_opts.index(job_pick) - 1
            if 0 <= ix < len(jobs):
                job_id = str(jobs[ix].get("id") or "").strip() or None
        equip_id = None
        if asset_pick != asset_opts[0]:
            ix = asset_opts.index(asset_pick) - 1
            if 0 <= ix < len(assets):
                equip_id = str(assets[ix].get("id") or "").strip() or None
        if not job_id and not equip_id:
            st.warning("Select at least a job or an equipment record.")
            return
        open_coupling_inspection(job_id=job_id, equipment_id=equip_id)


def render() -> None:
    if not begin_module("coupling_inspection", inject_css=True):
        return
    inject_coupling_inspection_css()
    st.markdown('<span class="ips-page-coupling_inspection" aria-hidden="true"></span>', unsafe_allow_html=True)

    ctx = coupling_inspection_context()
    if not ctx.get("job_id") and not ctx.get("equipment_id") and not ctx.get("inspection_id"):
        _render_context_picker()
        return

    if not ctx.get("inspection_id"):
        picked = _render_existing_list(ctx)
        if picked:
            st.session_state["coupling_insp_id"] = picked
            st.rerun()

    if st.button("Start New Inspection", key="ci_new_insp", use_container_width=False):
        job = _find_job(ctx.get("job_id"))
        equip = _find_equipment(ctx.get("equipment_id"))
        job_task = fetch_job_task(ctx.get("task_id"))
        prof = current_profile() or {}
        header = build_header_context(
            job=job,
            equipment=equip,
            technician=str(prof.get("full_name") or prof.get("name") or ""),
            job_task=job_task,
        )
        st.session_state[_DRAFT_KEY] = new_inspection_payload(
            job_id=ctx.get("job_id"),
            equipment_id=ctx.get("equipment_id"),
            customer_id=str(job.get("customer_id") or "") if job else None,
            header=header,
            task_id=ctx.get("task_id"),
            job_task=job_task,
        )
        st.session_state.pop("coupling_insp_id", None)
        st.rerun()

    _render_inspection_form(_load_draft(ctx))
