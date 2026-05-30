"""Coupling Inspection & Torque Verification — digital V6 form."""

from __future__ import annotations

import html
from datetime import date
from typing import Any
from uuid import uuid4

import streamlit as st

try:
    from app.auth import current_profile
    from app.components.coupling_inspection_launcher import coupling_inspection_context
    from app.components.signature_pad import render_compact_signature_pad, render_signature_pad
    from app.pages._core._access import begin_module
    from app.pages._core._data import load_assets, load_jobs
    from app.services.coupling_inspection_pdf import build_coupling_inspection_pdf_bytes
    from app.services.coupling_inspection_service import (
        PHOTO_SLOTS,
        build_header_context,
        completion_percentage,
        get_coupling_inspection,
        list_coupling_inspections,
        new_inspection_payload,
        photo_view_url,
        save_coupling_inspection,
        upload_inspection_photo,
        validate_for_complete,
        PHOTO_SLOT_LABELS,
    )
    from app.services.coupling_inspection_specs import (
        COUPLING_MODEL_OPTIONS,
        normalize_torque_rows,
        specs_for_model,
        torque_pattern_svg,
        torque_sequence_caption,
        torque_pass_labels,
    )
    from app.styles import inject_coupling_inspection_css
    from app.ui.page_shell import render_page_header
except ImportError:
    from auth import current_profile  # type: ignore
    from components.coupling_inspection_launcher import coupling_inspection_context  # type: ignore
    from components.signature_pad import render_compact_signature_pad, render_signature_pad  # type: ignore
    from pages._core._access import begin_module  # type: ignore
    from pages._core._data import load_assets, load_jobs  # type: ignore
    from services.coupling_inspection_pdf import build_coupling_inspection_pdf_bytes  # type: ignore
    from services.coupling_inspection_service import (  # type: ignore
        PHOTO_SLOTS,
        build_header_context,
        completion_percentage,
        get_coupling_inspection,
        list_coupling_inspections,
        new_inspection_payload,
        photo_view_url,
        save_coupling_inspection,
        upload_inspection_photo,
        validate_for_complete,
        PHOTO_SLOT_LABELS,
    )
    from services.coupling_inspection_specs import (  # type: ignore
        COUPLING_MODEL_OPTIONS,
        normalize_torque_rows,
        specs_for_model,
        torque_pattern_svg,
        torque_sequence_caption,
        torque_pass_labels,
    )
    from styles import inject_coupling_inspection_css  # type: ignore
    from ui.page_shell import render_page_header  # type: ignore

_DRAFT_KEY = "coupling_insp_draft"


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
    prof = current_profile() or {}
    tech = str(prof.get("full_name") or prof.get("name") or "").strip()
    header = build_header_context(job=job, equipment=equip, technician=tech)
    return new_inspection_payload(
        job_id=ctx.get("job_id"),
        equipment_id=ctx.get("equipment_id"),
        customer_id=str(job.get("customer_id") or "") if job else None,
        header=header,
    )


def _apply_model_change(record: dict[str, Any], model: str) -> dict[str, Any]:
    out = dict(record)
    out["coupling_model"] = model
    out["specs"] = specs_for_model(model)
    fields = dict(out.get("inspection_fields") or {})
    if not fields.get("lubricant_type"):
        fields["lubricant_type"] = out["specs"].get("lubricant_type_default") or ""
    out["inspection_fields"] = fields
    out["torque_rows"] = normalize_torque_rows([], model_key=model)
    return out


def _render_header_section(record: dict[str, Any], *, sk: str, locked: bool) -> dict[str, Any]:
    hdr = dict(record.get("header") or {})
    st.markdown("### Job & Equipment")
    c1, c2 = st.columns(2, gap="small")
    with c1:
        st.text_input("Customer", value=str(hdr.get("customer") or ""), disabled=True, key=f"{sk}_hdr_customer")
        st.text_input("Job number", value=str(hdr.get("job_number") or ""), disabled=True, key=f"{sk}_hdr_job")
        st.text_input("Work order #", value=str(hdr.get("work_order_number") or ""), disabled=True, key=f"{sk}_hdr_wo")
        st.text_input("Equipment", value=str(hdr.get("equipment_name") or ""), disabled=True, key=f"{sk}_hdr_eq")
    with c2:
        st.text_input("Asset #", value=str(hdr.get("asset_number") or ""), disabled=True, key=f"{sk}_hdr_asset")
        st.text_input("Location", value=str(hdr.get("location") or ""), disabled=True, key=f"{sk}_hdr_loc")
        insp_date = st.date_input(
            "Inspection date",
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
    record["header"] = hdr
    return record


def _render_specs_section(record: dict[str, Any], *, sk: str, locked: bool) -> dict[str, Any]:
    st.markdown("### Coupling Specification")
    model_ix = (
        COUPLING_MODEL_OPTIONS.index(record.get("coupling_model"))
        if record.get("coupling_model") in COUPLING_MODEL_OPTIONS
        else 0
    )
    model = st.selectbox(
        "Coupling spec",
        COUPLING_MODEL_OPTIONS,
        index=model_ix,
        disabled=locked,
        key=f"{sk}_model",
    )
    if model != record.get("coupling_model"):
        record = _apply_model_change(record, model)

    specs = dict(record.get("specs") or specs_for_model(model))
    custom = model == "Manual/Custom Coupling"
    s1, s2 = st.columns(2, gap="small")
    with s1:
        specs["coupling_type"] = st.text_input(
            "Coupling type",
            value=str(specs.get("coupling_type") or ""),
            disabled=locked and not custom,
            key=f"{sk}_spec_type",
        )
        specs["flange_bolts"] = st.text_input(
            "Flange bolts",
            value=str(specs.get("flange_bolts") or ""),
            disabled=locked and not custom,
            key=f"{sk}_spec_bolts",
        )
        gap_val = specs.get("standard_hub_gap_in")
        specs["standard_hub_gap_in"] = st.number_input(
            "Standard hub gap (in)",
            value=float(gap_val) if gap_val not in (None, "") else 0.0,
            format="%.3f",
            disabled=locked and not custom,
            key=f"{sk}_spec_gap",
        )
    with s2:
        specs["pass1_torque_ft_lb"] = st.number_input(
            "Pass 1 torque (ft-lb)",
            value=float(specs.get("pass1_torque_ft_lb") or 75),
            disabled=locked and not custom,
            key=f"{sk}_spec_p1",
        )
        specs["pass2_torque_ft_lb"] = st.number_input(
            "Pass 2 torque (ft-lb)",
            value=float(specs.get("pass2_torque_ft_lb") or 112),
            disabled=locked and not custom,
            key=f"{sk}_spec_p2",
        )
        specs["final_torque_ft_lb"] = st.number_input(
            "Final torque (ft-lb)",
            value=float(specs.get("final_torque_ft_lb") or 150),
            disabled=locked and not custom,
            key=f"{sk}_spec_final",
        )
        specs["final_torque_nm"] = st.number_input(
            "Final torque (Nm)",
            value=float(specs.get("final_torque_nm") or 203),
            disabled=locked and not custom,
            key=f"{sk}_spec_nm",
        )
    record["coupling_model"] = model
    record["specs"] = specs
    return record


def _render_torque_table(record: dict[str, Any], *, sk: str, locked: bool) -> dict[str, Any]:
    specs = record.get("specs") or {}
    p1_lbl, p2_lbl, pf_lbl = torque_pass_labels(specs)
    st.markdown("### Torque Verification")
    st.caption(f"8-bolt sequence: {torque_sequence_caption()}")

    pat_col, seq_col = st.columns([1, 1.6], gap="medium")
    with pat_col:
        st.markdown("**Torque pattern (8-bolt crisscross)**", unsafe_allow_html=True)
        st.markdown(torque_pattern_svg(), unsafe_allow_html=True)
    with seq_col:
        st.markdown("**Torque order**")
        for row in normalize_torque_rows(
            record.get("torque_rows"),
            model_key=str(record.get("coupling_model") or "1030G20"),
        ):
            st.markdown(f"{row.get('order')}. **{row.get('clock_position')}**")

    rows = normalize_torque_rows(
        record.get("torque_rows"),
        model_key=str(record.get("coupling_model") or "1030G20"),
    )
    updated: list[dict[str, Any]] = []

    hdr_cols = st.columns([0.4, 0.9, 1.1, 1.1, 1.1, 1.1, 1.4])
    for col, lbl in zip(hdr_cols, ["#", "Clock", p1_lbl, p2_lbl, pf_lbl, "Witness", "Initial"]):
        col.markdown(f"**{lbl}**")

    for i, row in enumerate(rows):
        rcols = st.columns([0.4, 0.9, 1.1, 1.1, 1.1, 1.1, 1.4], gap="small")
        with rcols[0]:
            st.markdown(f"**{row.get('order', i + 1)}**")
        with rcols[1]:
            st.markdown(str(row.get("clock_position") or ""))
        with rcols[2]:
            row["pass1_checked"] = st.checkbox(
                "P1", value=bool(row.get("pass1_checked")), disabled=locked, key=f"{sk}_p1_{i}", label_visibility="collapsed"
            )
        with rcols[3]:
            row["pass2_checked"] = st.checkbox(
                "P2", value=bool(row.get("pass2_checked")), disabled=locked, key=f"{sk}_p2_{i}", label_visibility="collapsed"
            )
        with rcols[4]:
            row["final_checked"] = st.checkbox(
                "Final", value=bool(row.get("final_checked")), disabled=locked, key=f"{sk}_pf_{i}", label_visibility="collapsed"
            )
        with rcols[5]:
            row["witness_mark_checked"] = st.checkbox(
                "W", value=bool(row.get("witness_mark_checked")), disabled=locked, key=f"{sk}_w_{i}", label_visibility="collapsed"
            )
        with rcols[6]:
            row["initial_signature"] = render_compact_signature_pad(
                label="",
                key=f"{sk}_bolt_sig_{i}",
                existing_data=str(row.get("initial_signature") or ""),
                disabled=locked,
            )
        updated.append(row)

    record["torque_rows"] = updated
    return record


def _render_inspection_fields(record: dict[str, Any], *, sk: str, locked: bool) -> dict[str, Any]:
    st.markdown("### Inspection Fields")
    fields = dict(record.get("inspection_fields") or {})
    teeth_opts = ["", "Good", "Fair", "Worn", "Damaged"]
    grease_opts = ["", "Good", "Dry", "Contaminated", "Replace"]
    seal_opts = ["", "Good", "Fair", "Leaking", "Replace"]

    f1, f2 = st.columns(2, gap="small")
    with f1:
        hub_val = fields.get("actual_hub_gap_in")
        fields["actual_hub_gap_in"] = st.number_input(
            "Actual hub gap (in) *",
            value=float(hub_val) if hub_val not in (None, "") else 0.0,
            format="%.3f",
            disabled=locked,
            key=f"{sk}_hub_gap",
        )
        fields["lubricant_type"] = st.text_input(
            "Lubricant type", value=str(fields.get("lubricant_type") or ""), disabled=locked, key=f"{sk}_lub_type"
        )
        fields["lubricant_quantity_added"] = st.text_input(
            "Lubricant quantity added",
            value=str(fields.get("lubricant_quantity_added") or ""),
            disabled=locked,
            key=f"{sk}_lub_qty",
        )
        teeth_ix = teeth_opts.index(str(fields.get("coupling_teeth_condition") or "")) if str(fields.get("coupling_teeth_condition") or "") in teeth_opts else 0
        fields["coupling_teeth_condition"] = st.selectbox(
            "Coupling teeth condition", teeth_opts, index=teeth_ix, disabled=locked, key=f"{sk}_teeth"
        )
    with f2:
        grease_ix = grease_opts.index(str(fields.get("grease_condition") or "")) if str(fields.get("grease_condition") or "") in grease_opts else 0
        fields["grease_condition"] = st.selectbox(
            "Grease condition", grease_opts, index=grease_ix, disabled=locked, key=f"{sk}_grease"
        )
        seal_ix = seal_opts.index(str(fields.get("seal_condition") or "")) if str(fields.get("seal_condition") or "") in seal_opts else 0
        fields["seal_condition"] = st.selectbox(
            "Seal condition", seal_opts, index=seal_ix, disabled=locked, key=f"{sk}_seal"
        )
        fields["cover_installed"] = st.checkbox(
            "Cover installed", value=bool(fields.get("cover_installed")), disabled=locked, key=f"{sk}_cover"
        )
        fields["fasteners_witness_marked"] = st.checkbox(
            "Fasteners witness marked",
            value=bool(fields.get("fasteners_witness_marked")),
            disabled=locked,
            key=f"{sk}_fast_wit",
        )
        fields["guard_installed"] = st.checkbox(
            "Guard installed", value=bool(fields.get("guard_installed")), disabled=locked, key=f"{sk}_guard"
        )
    fields["notes"] = st.text_area(
        "Notes / comments", value=str(fields.get("notes") or ""), height=100, disabled=locked, key=f"{sk}_notes"
    )
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
    st.markdown("### Photo Attachments")
    attachments = list(record.get("photo_attachments") or [])
    rid = _upload_record_id(record)
    if not record.get("id"):
        st.caption("Photos upload immediately. Save draft to link them to the inspection record.")

    for slot in PHOTO_SLOTS:
        label = PHOTO_SLOT_LABELS.get(slot, slot)
        existing = next((a for a in attachments if str(a.get("slot") or "") == slot), None)
        if existing:
            url = photo_view_url(existing)
            if url:
                st.image(url, caption=label, use_container_width=True)
            else:
                st.caption(f"{label}: {existing.get('file_name') or 'on file'}")
        if not locked:
            up = st.file_uploader(label, type=["jpg", "jpeg", "png", "webp"], key=f"{sk}_photo_{slot}")
            if up is not None:
                attachments, err = upload_inspection_photo(
                    inspection_id=rid,
                    slot=slot,
                    uploaded_file=up,
                    existing_attachments=attachments,
                )
                if err:
                    st.error(err)
    record["photo_attachments"] = attachments
    return record


def _render_signatures_section(record: dict[str, Any], *, sk: str, locked: bool) -> dict[str, Any]:
    st.markdown("### Signatures")
    record["technician_signature"] = render_signature_pad(
        label="Technician signature *",
        key=f"{sk}_sig_tech",
        existing_data=str(record.get("technician_signature") or ""),
        disabled=locked,
        width=680,
        height=140,
    )
    record["supervisor_signature"] = render_signature_pad(
        label="Supervisor signature",
        key=f"{sk}_sig_sup",
        existing_data=str(record.get("supervisor_signature") or ""),
        disabled=locked,
        width=680,
        height=120,
    )
    record["customer_signature"] = render_signature_pad(
        label="Customer representative signature *",
        key=f"{sk}_sig_cust",
        existing_data=str(record.get("customer_signature") or ""),
        disabled=locked,
        width=680,
        height=140,
    )
    return record


def _render_inspection_form(record: dict[str, Any]) -> None:
    sk = _session_key(record)
    locked = str(record.get("status") or "").lower() in {"complete", "exported"} and not st.session_state.get(
        f"{sk}_edit_mode"
    )
    pct = completion_percentage(record)
    st.progress(min(pct / 100.0, 1.0), text=f"Completion: {pct}%")
    st.caption(f"Status: **{html.escape(str(record.get('status') or 'draft').title())}**")

    record = _render_header_section(record, sk=sk, locked=locked)
    record = _render_specs_section(record, sk=sk, locked=locked)
    record = _render_torque_table(record, sk=sk, locked=locked)
    record = _render_inspection_fields(record, sk=sk, locked=locked)
    record = _render_photos_section(record, sk=sk, locked=locked)
    record = _render_signatures_section(record, sk=sk, locked=locked)
    st.session_state[_DRAFT_KEY] = record

    a1, a2, a3, a4 = st.columns(4, gap="small")
    save_draft = a1.button("Save draft", type="secondary", use_container_width=True, key=f"{sk}_save", disabled=locked)
    mark_complete = a2.button("Mark complete", type="primary", use_container_width=True, key=f"{sk}_complete", disabled=locked)
    gen_pdf = a3.button("Generate PDF", use_container_width=True, key=f"{sk}_pdf")
    if locked:
        if a4.button("Reopen for edit", use_container_width=True, key=f"{sk}_reopen"):
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
            for err in errors[:6]:
                st.error(err)
        else:
            result = save_coupling_inspection(
                record, inspection_id=str(record.get("id") or "") or None, mark_complete=True
            )
            if result.ok and result.data:
                st.session_state[_DRAFT_KEY] = result.data
                st.session_state.pop(f"{sk}_edit_mode", None)
                st.success("Inspection marked complete.")
                st.rerun()
            else:
                st.error(result.error or "Could not complete inspection.")

    if gen_pdf:
        try:
            pdf_bytes = build_coupling_inspection_pdf_bytes(record)
            if record.get("id"):
                save_coupling_inspection(record, inspection_id=str(record.get("id")), mark_exported=True)
            st.download_button(
                "Download Coupling Inspection PDF",
                data=pdf_bytes,
                file_name=f"coupling_inspection_{record.get('id') or 'draft'}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key=f"{sk}_pdf_dl",
            )
        except Exception as exc:
            st.error(f"PDF generation failed: {exc}")


def _render_existing_list(ctx: dict[str, str | None]) -> str | None:
    rows = list_coupling_inspections(job_id=ctx.get("job_id"), equipment_id=ctx.get("equipment_id"))
    if not rows:
        return None
    st.markdown("#### Existing inspections")
    options = ["— New inspection —"] + [
        f"{r.get('header', {}).get('inspection_date', '—')} · {str(r.get('status') or 'draft').title()} · {r.get('coupling_model')}"
        for r in rows
    ]
    pick = st.selectbox("Open inspection", options, key="ci_pick_existing")
    if pick == "— New inspection —":
        return None
    return str(rows[options.index(pick) - 1].get("id") or "")


def render() -> None:
    if not begin_module("coupling_inspection", inject_css=True):
        return
    inject_coupling_inspection_css()
    render_page_header(
        "Coupling Inspection",
        "Torque verification, photos, signatures, and IPS V6 PDF export.",
    )

    ctx = coupling_inspection_context()
    if not ctx.get("job_id") and not ctx.get("equipment_id") and not ctx.get("inspection_id"):
        st.warning("Open Coupling Inspection from a **Job** or **Equipment** record (Inspection Forms).")
        return

    if not ctx.get("inspection_id"):
        picked = _render_existing_list(ctx)
        if picked:
            st.session_state["coupling_insp_id"] = picked
            st.rerun()

    if st.button("Start new inspection", key="ci_new_insp"):
        job = _find_job(ctx.get("job_id"))
        equip = _find_equipment(ctx.get("equipment_id"))
        prof = current_profile() or {}
        header = build_header_context(
            job=job,
            equipment=equip,
            technician=str(prof.get("full_name") or prof.get("name") or ""),
        )
        st.session_state[_DRAFT_KEY] = new_inspection_payload(
            job_id=ctx.get("job_id"),
            equipment_id=ctx.get("equipment_id"),
            customer_id=str(job.get("customer_id") or "") if job else None,
            header=header,
        )
        st.session_state.pop("coupling_insp_id", None)
        st.rerun()

    _render_inspection_form(_load_draft(ctx))
