"""Rental equipment inspection form — checkout, daily, and return."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

try:
    from app.auth import current_profile
    from app.components.rental_equipment_inspection_launcher import (
        clear_rental_inspection_context,
        rental_inspection_context,
    )
    from app.components.signature_pad import render_signature_field
    from app.pages._core._access import begin_module
    from app.pages._core._data import load_assets, load_jobs
    from app.services.rental_equipment_inspection_service import (
        get_rental_inspection,
        inspection_type_label,
        new_inspection_payload,
        pdf_export_filename,
        photo_view_url,
        save_rental_inspection,
        upload_inspection_photo,
        validate_for_complete,
    )
    from app.services.rental_equipment_inspection_specs import (
        CHECKLIST_ITEMS,
        GENERAL_CONDITIONS,
        PHOTO_SLOT_LABELS,
        SIGNATURE_ROLE_LABELS,
        SIGNATURE_ROLES,
        normalize_checklist,
        required_photo_slots_for_checklist,
    )
except ImportError:
    from auth import current_profile  # type: ignore
    from components.rental_equipment_inspection_launcher import (  # type: ignore
        clear_rental_inspection_context,
        rental_inspection_context,
    )
    from components.signature_pad import render_signature_field  # type: ignore
    from pages._core._access import begin_module  # type: ignore
    from pages._core._data import load_assets, load_jobs  # type: ignore
    from services.rental_equipment_inspection_service import (  # type: ignore
        get_rental_inspection,
        inspection_type_label,
        new_inspection_payload,
        pdf_export_filename,
        photo_view_url,
        save_rental_inspection,
        upload_inspection_photo,
        validate_for_complete,
    )
    from services.rental_equipment_inspection_specs import (  # type: ignore
        CHECKLIST_ITEMS,
        GENERAL_CONDITIONS,
        PHOTO_SLOT_LABELS,
        SIGNATURE_ROLE_LABELS,
        SIGNATURE_ROLES,
        normalize_checklist,
        required_photo_slots_for_checklist,
    )

_DRAFT_KEY = "rental_insp_draft"


def _find_asset(asset_id: str | None) -> dict[str, Any] | None:
    aid = str(asset_id or "").strip()
    if not aid:
        return None
    for a in load_assets():
        if str(a.get("id") or "") == aid:
            return a
    return None


def _find_job(job_id: str | None) -> dict[str, Any] | None:
    jid = str(job_id or "").strip()
    if not jid:
        return None
    for j in load_jobs():
        if str(j.get("id") or "") == jid:
            return j
    return None


def _load_record(ctx: dict[str, str | None]) -> dict[str, Any]:
    iid = ctx.get("rental_insp_id")
    if iid:
        existing = get_rental_inspection(iid)
        if existing:
            return existing
    cached = st.session_state.get(_DRAFT_KEY)
    if isinstance(cached, dict):
        return cached
    asset = _find_asset(ctx.get("rental_insp_asset_id"))
    prof = current_profile() or {}
    job = _find_job(ctx.get("rental_insp_job_id") or (asset or {}).get("assigned_job_id"))
    return new_inspection_payload(
        asset_id=str((asset or {}).get("id") or ctx.get("rental_insp_asset_id") or ""),
        inspection_type=str(ctx.get("rental_insp_type") or "checkout"),
        job_id=str((job or {}).get("id") or "") or None,
        customer_id=str((job or {}).get("customer_id") or "") or None,
        performed_by_name=str(prof.get("full_name") or prof.get("name") or "").strip(),
        performed_by_user_id=str(prof.get("id") or "").strip() or None,
    )


def _photo_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for p in record.get("photo_attachments") or []:
        if isinstance(p, dict):
            slot = str(p.get("slot") or "").strip()
            if slot:
                out[slot] = p
    return out


def _render_photo_slot(
    record: dict[str, Any],
    slot: str,
    *,
    required: bool,
    key_prefix: str,
    user_id: str | None,
) -> dict[str, Any]:
    label = PHOTO_SLOT_LABELS.get(slot, slot)
    photos = _photo_map(record)
    existing = photos.get(slot) or {}
    st.markdown(f"**{label}**" + (" *" if required else ""))
    if existing.get("photo_url"):
        st.image(existing["photo_url"], width=140, caption="Attached")
    elif existing.get("photo_path"):
        st.caption("Photo saved.")
    iid = str(record.get("id") or "").strip()
    cam = st.camera_input("Take Photo", key=f"{key_prefix}_cam_{slot}")
    if cam is not None and iid:
        path, url = upload_inspection_photo(iid, slot, cam, uploaded_by=user_id)
        if path or url:
            st.rerun()
    upload = st.file_uploader(
        "Upload Photo",
        type=["png", "jpg", "jpeg", "webp"],
        key=f"{key_prefix}_up_{slot}",
        label_visibility="collapsed",
    )
    if upload is not None and iid:
        path, url = upload_inspection_photo(iid, slot, upload, uploaded_by=user_id)
        if path or url:
            st.rerun()
    refreshed = get_rental_inspection(iid) if iid else record
    return (_photo_map(refreshed or record).get(slot) or existing)


def render() -> None:
    ctx = rental_inspection_context()
    record = _load_record(ctx)
    st.session_state[_DRAFT_KEY] = record
    asset = _find_asset(str(record.get("asset_id") or ""))
    job = _find_job(str(record.get("job_id") or ""))
    prof = current_profile() or {}
    user_id = str(prof.get("id") or "").strip() or None
    itype = str(record.get("inspection_type") or "checkout")
    title = inspection_type_label(itype)
    begin_module(title, "Photo proof, checklist, damage report, and signatures required to complete.")

    if not str(record.get("asset_id") or "").strip():
        st.error("No rental asset selected.")
        if st.button("Back to Rental Equipment"):
            clear_rental_inspection_context()
            st.session_state.pop(_DRAFT_KEY, None)
            try:
                from app.navigation import set_nav_slug
            except ImportError:
                from navigation import set_nav_slug  # type: ignore
            set_nav_slug("rental_equipment")
            st.rerun()
        return

    st.markdown(f"**{asset.get('asset_name') if asset else 'Asset'}** · {asset.get('asset_number') if asset else '—'}")
    if job:
        st.caption(f"Job: {job.get('job_number') or ''} {job.get('job_name') or job.get('name') or ''}".strip())

    iid = str(record.get("id") or "").strip()
    if not iid:
        save_result = save_rental_inspection(record)
        if save_result.ok:
            record = get_rental_inspection(str((save_result.data or {}).get("id") or "")) or record
            st.session_state[_DRAFT_KEY] = record
            st.session_state["rental_insp_id"] = record.get("id")
            st.rerun()
        else:
            st.error(save_result.error or "Could not start inspection draft.")
            return

    key_prefix = f"rei_{iid}"
    checklist = normalize_checklist(record.get("checklist"))
    general = st.selectbox(
        "Overall Condition",
        [""] + list(GENERAL_CONDITIONS),
        index=([""] + list(GENERAL_CONDITIONS)).index(str(record.get("general_condition") or ""))
        if str(record.get("general_condition") or "") in GENERAL_CONDITIONS
        else 0,
        key=f"{key_prefix}_gen",
    )

    st.divider()
    st.markdown("#### Inspection Checklist")
    cols = st.columns(2)
    updated_checklist = dict(checklist)
    for idx, (key, label, options) in enumerate(CHECKLIST_ITEMS):
        with cols[idx % 2]:
            cur = updated_checklist.get(key) or ""
            sel_index = list(options).index(cur) if cur in options else 0
            updated_checklist[key] = st.selectbox(label, options, index=sel_index, key=f"{key_prefix}_cl_{key}")

    notes = st.text_area("Notes", value=str(record.get("notes") or ""), key=f"{key_prefix}_notes", height=80)

    st.divider()
    st.markdown("#### Required Photos")
    photo_required = itype in {"checkout", "return"}
    photo_slots = list(required_photo_slots_for_checklist(updated_checklist))
    photo_rows: dict[str, dict[str, Any]] = _photo_map(record)
    for slot in photo_slots:
        slot_photo = _render_photo_slot(
            record,
            slot,
            required=photo_required,
            key_prefix=key_prefix,
            user_id=user_id,
        )
        if slot_photo:
            photo_rows[slot] = slot_photo

    st.divider()
    st.markdown("#### Damage")
    if itype == "return":
        show_damage = general == "Damaged"
        if show_damage:
            st.info("Overall condition is Damaged — damage description and photo are required.")
    else:
        show_damage = st.checkbox(
            "Damage reported?",
            value=bool(record.get("damage_reported")),
            key=f"{key_prefix}_dmg",
        )
    damage_description = damage_location = repair_recommendation = ""
    if show_damage:
        damage_description = st.text_area(
            "Damage Description",
            value=str(record.get("damage_description") or ""),
            key=f"{key_prefix}_dmg_desc",
            height=60,
        )
        if itype != "return":
            damage_location = st.text_input(
                "Damage Location",
                value=str(record.get("damage_location") or ""),
                key=f"{key_prefix}_dmg_loc",
            )
            repair_recommendation = st.text_area(
                "Repair Recommendation",
                value=str(record.get("repair_recommendation") or ""),
                key=f"{key_prefix}_dmg_rec",
                height=60,
            )
        dmg_photo = _render_photo_slot(record, "damage_photo", required=True, key_prefix=key_prefix, user_id=user_id)
        if dmg_photo:
            photo_rows["damage_photo"] = dmg_photo

    fail_inspection = st.checkbox(
        "Fail inspection — mark equipment Out of Service",
        value=bool(record.get("fail_inspection")),
        key=f"{key_prefix}_fail",
    )

    st.divider()
    st.markdown("#### Signatures")
    signatures = dict(record.get("signatures") or {})
    for role in SIGNATURE_ROLES:
        existing = signatures.get(role) if isinstance(signatures.get(role), dict) else {}
        sig = render_signature_field(
            label=SIGNATURE_ROLE_LABELS.get(role, role),
            role_key=f"{key_prefix}_{role}",
            existing={
                "signer_name": existing.get("signer_name") or "",
                "signature_image": existing.get("signature_data") or existing.get("signature_image") or "",
                "signed_at": existing.get("signed_at") or "",
            },
            required=True,
        )
        signatures[role] = {
            "signer_name": sig.get("signer_name") or "",
            "signature_data": sig.get("signature_image") or "",
            "signed_at": sig.get("signed_at") or "",
        }

    st.caption(f"Date/time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    payload = {
        **record,
        "general_condition": general,
        "checklist": updated_checklist,
        "notes": notes,
        "damage_reported": show_damage,
        "damage_description": damage_description,
        "damage_location": damage_location,
        "repair_recommendation": repair_recommendation,
        "fail_inspection": fail_inspection,
        "signatures": signatures,
        "photo_attachments": list(photo_rows.values()),
        "performed_by_name": str(prof.get("full_name") or prof.get("name") or "").strip(),
        "performed_by_user_id": user_id,
    }
    st.session_state[_DRAFT_KEY] = payload

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Save Draft", use_container_width=True, key=f"{key_prefix}_save"):
            result = save_rental_inspection(payload, inspection_id=iid)
            if result.ok:
                st.success("Draft saved.")
            else:
                st.error(result.error or "Save failed.")
    with c2:
        if st.button("Complete Inspection", type="primary", use_container_width=True, key=f"{key_prefix}_done"):
            fresh = get_rental_inspection(iid) or payload
            merged = {**payload, "photo_attachments": fresh.get("photo_attachments") or payload.get("photo_attachments")}
            errs = validate_for_complete(merged)
            if errs:
                st.error(" · ".join(errs[:4]))
            else:
                result = save_rental_inspection(merged, inspection_id=iid, mark_complete=True)
                if result.ok:
                    st.success("Inspection completed and PDF generated.")
                    clear_rental_inspection_context()
                    st.session_state.pop(_DRAFT_KEY, None)
                    try:
                        from app.navigation import set_nav_slug
                    except ImportError:
                        from navigation import set_nav_slug  # type: ignore
                    set_nav_slug("rental_equipment")
                    st.rerun()
                else:
                    st.error(result.error or "Could not complete inspection.")
    with c3:
        completed = get_rental_inspection(iid)
        pdf_url = str((completed or {}).get("pdf_url") or "").strip()
        if pdf_url.startswith("http"):
            st.link_button("Download PDF", pdf_url, use_container_width=True)
        elif completed and completed.get("status") in {"complete", "failed"}:
            try:
                from app.services.rental_equipment_inspection_pdf import build_rental_inspection_pdf_bytes

                pdf_bytes = build_rental_inspection_pdf_bytes(completed)
                st.download_button(
                    "Download PDF",
                    data=pdf_bytes,
                    file_name=pdf_export_filename(completed),
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"{key_prefix}_pdf_dl",
                )
            except Exception:
                pass
