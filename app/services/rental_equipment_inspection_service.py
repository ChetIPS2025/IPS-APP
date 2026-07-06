"""Rental equipment inspection persistence, validation, photos, and PDF export."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

try:
    from app.auth import current_profile
    from app.db import create_signed_url, upload_bytes_admin
    from app.services.rental_equipment_inspection_specs import (
        CHECKLIST_ITEMS,
        GENERAL_CONDITIONS,
        INSPECTION_TYPE_LABELS,
        PHOTO_SLOT_LABELS,
        SIGNATURE_ROLE_LABELS,
        SIGNATURE_ROLES,
        default_checklist,
        normalize_checklist,
        required_photo_slots_for_checklist,
    )
    from app.services.repository import ServiceResult, fetch_by_id, fetch_rows
    from app.services.task_photos import compress_image_bytes
except ImportError:
    from auth import current_profile  # type: ignore
    from db import create_signed_url, upload_bytes_admin  # type: ignore
    from services.rental_equipment_inspection_specs import (  # type: ignore
        CHECKLIST_ITEMS,
        GENERAL_CONDITIONS,
        INSPECTION_TYPE_LABELS,
        PHOTO_SLOT_LABELS,
        SIGNATURE_ROLE_LABELS,
        SIGNATURE_ROLES,
        default_checklist,
        normalize_checklist,
        required_photo_slots_for_checklist,
    )
    from services.repository import ServiceResult, fetch_by_id, fetch_rows  # type: ignore
    from services.task_photos import compress_image_bytes  # type: ignore

_LOG = logging.getLogger(__name__)

TABLE = "rental_equipment_inspections"
PHOTOS_TABLE = "rental_equipment_inspection_photos"
SIGNATURES_TABLE = "rental_equipment_inspection_signatures"
STORAGE_PREFIX = "rental-equipment-inspections"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_dict(v: Any) -> dict[str, Any]:
    if isinstance(v, dict):
        return dict(v)
    if isinstance(v, str) and v.strip():
        try:
            parsed = json.loads(v)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def is_rental_equipment(asset: dict[str, Any] | None) -> bool:
    if not asset:
        return False
    cat = str(asset.get("category") or asset.get("asset_category") or "").strip().casefold()
    if "rental equipment" in cat or cat in {"rental", "rentals"}:
        return True
    try:
        from app.services.phase2_modules_service import asset_is_rentable
    except ImportError:
        from services.phase2_modules_service import asset_is_rentable  # type: ignore
    return asset_is_rentable(asset)


def inspection_type_label(inspection_type: str) -> str:
    return INSPECTION_TYPE_LABELS.get(str(inspection_type or "").strip().lower(), "Inspection")


def new_inspection_payload(
    *,
    asset_id: str,
    inspection_type: str,
    job_id: str | None = None,
    customer_id: str | None = None,
    performed_by_name: str = "",
    performed_by_user_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": None,
        "asset_id": asset_id,
        "job_id": job_id,
        "customer_id": customer_id,
        "inspection_type": str(inspection_type or "checkout").strip().lower(),
        "status": "draft",
        "general_condition": "",
        "checklist": default_checklist(),
        "notes": "",
        "damage_reported": False,
        "damage_description": "",
        "damage_location": "",
        "repair_recommendation": "",
        "fail_inspection": False,
        "performed_by_name": performed_by_name,
        "performed_by_user_id": performed_by_user_id,
        "photo_attachments": [],
        "signatures": {role: {"signer_name": "", "signature_data": "", "signed_at": ""} for role in SIGNATURE_ROLES},
    }


def _hydrate_inspection(row: dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    data["checklist"] = normalize_checklist(data.get("checklist"))
    iid = str(data.get("id") or "")
    photos: list[dict[str, Any]] = []
    signatures = {role: {"signer_name": "", "signature_data": "", "signed_at": ""} for role in SIGNATURE_ROLES}
    if iid:
        try:
            from app.db import fetch_by_match_admin
        except ImportError:
            from db import fetch_by_match_admin  # type: ignore
        try:
            for p in fetch_by_match_admin(PHOTOS_TABLE, {"inspection_id": iid}, limit=50) or []:
                slot = str(p.get("slot_key") or "").strip()
                if not slot:
                    continue
                photos.append(
                    {
                        "slot": slot,
                        "photo_path": str(p.get("photo_path") or ""),
                        "photo_url": photo_view_url(str(p.get("photo_path") or "")),
                        "uploaded_at": str(p.get("uploaded_at") or ""),
                    }
                )
            for s in fetch_by_match_admin(SIGNATURES_TABLE, {"inspection_id": iid}, limit=10) or []:
                role = str(s.get("role") or "").strip()
                if role in signatures:
                    signatures[role] = {
                        "signer_name": str(s.get("signer_name") or ""),
                        "signature_data": str(s.get("signature_data") or ""),
                        "signed_at": str(s.get("signed_at") or ""),
                    }
        except Exception as exc:
            _LOG.warning("hydrate rental inspection failed: %s", exc)
    data["photo_attachments"] = photos
    data["signatures"] = signatures
    return data


def get_rental_inspection(inspection_id: str) -> dict[str, Any] | None:
    row = fetch_by_id(TABLE, str(inspection_id or "").strip())
    return _hydrate_inspection(row) if isinstance(row, dict) else None


def list_rental_inspections_for_asset(asset_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
    aid = str(asset_id or "").strip()
    if not aid:
        return []
    rows, _ = fetch_rows(TABLE, limit=limit, order_by="updated_at")
    return [_hydrate_inspection(r) for r in rows if str(r.get("asset_id") or "") == aid]


def list_open_inspection(
    asset_id: str,
    inspection_type: str,
    *,
    job_id: str | None = None,
) -> dict[str, Any] | None:
    for row in list_rental_inspections_for_asset(asset_id):
        if str(row.get("inspection_type") or "") != inspection_type:
            continue
        if str(row.get("status") or "") != "draft":
            continue
        if job_id and str(row.get("job_id") or "") != job_id:
            continue
        return row
    return None


def list_rental_equipment_assets(*, limit: int = 500) -> list[dict[str, Any]]:
    rows, _ = fetch_rows("assets", limit=limit, order_by="asset_name")
    return [r for r in rows if is_rental_equipment(r)]


def rental_inspection_dashboard_status(asset: dict[str, Any], inspections: list[dict[str, Any]] | None = None) -> str:
    aid = str(asset.get("id") or "")
    rows = inspections if inspections is not None else list_rental_inspections_for_asset(aid)
    assigned = bool(str(asset.get("assigned_job_id") or "").strip())
    open_checkout = any(r.get("inspection_type") == "checkout" and r.get("status") == "draft" for r in rows)
    open_return = any(r.get("inspection_type") == "return" and r.get("status") == "draft" for r in rows)
    damage = any(
        bool(r.get("damage_reported")) or bool(r.get("fail_inspection")) or r.get("status") == "failed"
        for r in rows
    )
    if damage:
        return "Damage Reported"
    if open_checkout or open_return:
        return "Awaiting Inspection"
    if assigned:
        return "Checked Out"
    if any(r.get("inspection_type") == "return" and r.get("status") == "complete" for r in rows):
        return "Returned"
    return "Available"


def photo_view_url(photo_path: str, *, expires_in: int = 3600) -> str:
    path = str(photo_path or "").strip()
    if not path:
        return ""
    try:
        url = create_signed_url(path, expires_in=expires_in)
        return url if str(url).startswith("http") else ""
    except Exception:
        return ""


def upload_inspection_photo(
    inspection_id: str,
    slot_key: str,
    uploaded_file: Any,
    *,
    uploaded_by: str | None = None,
) -> tuple[str, str]:
    iid = str(inspection_id or "").strip()
    slot = str(slot_key or "").strip()
    if not iid or not slot or uploaded_file is None:
        return "", ""
    raw = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else b""
    if not raw:
        return "", ""
    try:
        data, out_name = compress_image_bytes(raw)
    except Exception:
        data, out_name = raw, f"{slot}.jpg"
    safe = out_name.replace(" ", "_")[:80] or f"{slot}.jpg"
    storage_path = f"{STORAGE_PREFIX}/{iid}/{slot}_{uuid4().hex[:8]}_{safe}"
    try:
        upload_bytes_admin(storage_path, data, content_type="image/jpeg")
    except Exception:
        return "", ""
    url = photo_view_url(storage_path)
    prof = current_profile() or {}
    uid = uploaded_by or str(prof.get("id") or "").strip() or None
    try:
        from app.db import delete_row_admin, fetch_by_match_admin, insert_row_admin
    except ImportError:
        from db import delete_row_admin, fetch_by_match_admin, insert_row_admin  # type: ignore
    try:
        existing = fetch_by_match_admin(PHOTOS_TABLE, {"inspection_id": iid, "slot_key": slot}, limit=5) or []
        for row in existing:
            delete_row_admin(PHOTOS_TABLE, {"id": row.get("id")})
        insert_row_admin(
            PHOTOS_TABLE,
            {
                "inspection_id": iid,
                "slot_key": slot,
                "photo_path": storage_path,
                "photo_url": url or None,
                "uploaded_by": uid,
                "uploaded_at": _utc_now_iso(),
            },
        )
    except Exception as exc:
        _LOG.warning("rental inspection photo row failed: %s", exc)
    return storage_path, url


def _damage_validation_required(data: dict[str, Any]) -> bool:
    itype = str(data.get("inspection_type") or "checkout").strip().lower()
    if itype == "damage":
        return True
    if bool(data.get("damage_reported")):
        return True
    return str(data.get("general_condition") or "").strip() == "Damaged"


def validate_for_complete(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    itype = str(data.get("inspection_type") or "checkout").strip().lower()
    checklist = normalize_checklist(data.get("checklist"))
    photos = {str(p.get("slot") or ""): p for p in (data.get("photo_attachments") or []) if isinstance(p, dict)}

    if itype == "damage":
        if not str(data.get("damage_location") or "").strip():
            errors.append("Damaged item is required.")
        if not str(data.get("damage_description") or "").strip():
            errors.append("Damage notes are required.")
        dmg = photos.get("damage_photo") or {}
        if not str(dmg.get("photo_path") or dmg.get("photo_url") or "").strip():
            errors.append("Damage photo is required.")
        return errors

    if str(data.get("general_condition") or "").strip() not in GENERAL_CONDITIONS:
        errors.append("Overall condition is required.")
    for key, label, _opts in CHECKLIST_ITEMS:
        if not checklist.get(key):
            errors.append(f"{label} is required.")
    if itype in {"checkout", "return"}:
        for slot in required_photo_slots_for_checklist(checklist):
            p = photos.get(slot) or {}
            if not str(p.get("photo_path") or p.get("photo_url") or "").strip():
                label = PHOTO_SLOT_LABELS.get(slot, slot)
                errors.append(f"Photo required: {label}.")
    if _damage_validation_required(data):
        if not str(data.get("damage_description") or "").strip():
            errors.append("Damage description is required.")
        dmg = photos.get("damage_photo") or {}
        if not str(dmg.get("photo_path") or dmg.get("photo_url") or "").strip():
            errors.append("Damage photo is required.")
    sigs = _as_dict(data.get("signatures"))
    for role in SIGNATURE_ROLES:
        entry = _as_dict(sigs.get(role))
        if not str(entry.get("signature_data") or "").strip():
            errors.append(f"{SIGNATURE_ROLE_LABELS.get(role, role)} is required.")
        if not str(entry.get("signer_name") or "").strip():
            errors.append(f"{SIGNATURE_ROLE_LABELS.get(role, role)} name is required.")
    return errors


def _sync_child_records(inspection_id: str, data: dict[str, Any]) -> None:
    try:
        from app.db import delete_row_admin, insert_row_admin
    except ImportError:
        from db import delete_row_admin, insert_row_admin  # type: ignore
    sigs = _as_dict(data.get("signatures"))
    delete_row_admin(SIGNATURES_TABLE, {"inspection_id": inspection_id})
    for role in SIGNATURE_ROLES:
        entry = _as_dict(sigs.get(role))
        if not str(entry.get("signature_data") or "").strip():
            continue
        insert_row_admin(
            SIGNATURES_TABLE,
            {
                "inspection_id": inspection_id,
                "role": role,
                "signer_name": str(entry.get("signer_name") or ""),
                "signature_data": str(entry.get("signature_data") or ""),
                "signed_at": str(entry.get("signed_at") or _utc_now_iso()) or None,
            },
        )


def save_rental_inspection(
    data: dict[str, Any],
    *,
    inspection_id: str | None = None,
    mark_complete: bool = False,
) -> ServiceResult:
    payload: dict[str, Any] = {
        "asset_id": data.get("asset_id"),
        "job_id": data.get("job_id") or None,
        "customer_id": data.get("customer_id") or None,
        "inspection_type": str(data.get("inspection_type") or "checkout").strip().lower(),
        "general_condition": str(data.get("general_condition") or "").strip(),
        "checklist": normalize_checklist(data.get("checklist")),
        "notes": str(data.get("notes") or "").strip(),
        "damage_reported": bool(data.get("damage_reported")),
        "damage_description": str(data.get("damage_description") or "").strip(),
        "damage_location": str(data.get("damage_location") or "").strip(),
        "repair_recommendation": str(data.get("repair_recommendation") or "").strip(),
        "fail_inspection": bool(data.get("fail_inspection")),
        "performed_by_user_id": data.get("performed_by_user_id"),
        "performed_by_name": str(data.get("performed_by_name") or "").strip(),
        "updated_at": _utc_now_iso(),
    }
    if mark_complete:
        errors = validate_for_complete(data)
        if errors:
            return ServiceResult(ok=False, error="; ".join(errors))
        payload["status"] = "failed" if payload["fail_inspection"] else "complete"
        payload["completed_at"] = _utc_now_iso()
        payload["signed_at"] = _utc_now_iso()
    else:
        payload["status"] = "draft"

    rid = str(inspection_id or data.get("id") or "").strip()
    try:
        from app.db import insert_row_admin, update_row_admin
    except ImportError:
        from db import insert_row_admin, update_row_admin  # type: ignore

    try:
        if rid:
            result = update_row_admin(TABLE, payload, {"id": rid})
            iid = rid
        else:
            payload["created_at"] = _utc_now_iso()
            result = insert_row_admin(TABLE, payload)
            iid = str((result.data or {}).get("id") or "")
        if not result.ok or not iid:
            return ServiceResult(ok=False, error=result.error or "Could not save inspection.")
        _sync_child_records(iid, data)
        if mark_complete:
            try:
                from app.services.rental_equipment_inspection_pdf import build_rental_inspection_pdf_bytes

                record = get_rental_inspection(iid) or {**payload, "id": iid, **data}
                pdf_bytes = build_rental_inspection_pdf_bytes(record)
                pdf_path = f"{STORAGE_PREFIX}/{iid}/report_{date.today().isoformat()}.pdf"
                upload_bytes_admin(pdf_path, pdf_bytes, content_type="application/pdf")
                pdf_url = photo_view_url(pdf_path, expires_in=7200)
                update_row_admin(
                    TABLE,
                    {"pdf_path": pdf_path, "pdf_url": pdf_url, "status": payload["status"]},
                    {"id": iid},
                )
            except Exception as exc:
                _LOG.warning("rental inspection PDF export failed: %s", exc)
            if payload["inspection_type"] == "damage":
                try:
                    update_row_admin(
                        "assets",
                        {"condition": "Needs Repair", "updated_at": _utc_now_iso()},
                        {"id": str(data.get("asset_id") or "")},
                    )
                except Exception as exc:
                    _LOG.warning("mark rental asset needs repair failed: %s", exc)
            elif payload["fail_inspection"]:
                try:
                    update_row_admin(
                        "assets",
                        {"status": "Out of Service", "updated_at": _utc_now_iso()},
                        {"id": str(data.get("asset_id") or "")},
                    )
                except Exception as exc:
                    _LOG.warning("mark asset out of service failed: %s", exc)
        return ServiceResult(ok=True, data={"id": iid})
    except Exception as exc:
        _LOG.exception("save_rental_inspection failed")
        return ServiceResult(ok=False, error=str(exc))


def create_auto_inspection(
    *,
    asset_id: str,
    inspection_type: str,
    job_id: str | None = None,
    customer_id: str | None = None,
) -> ServiceResult:
    aid = str(asset_id or "").strip()
    itype = str(inspection_type or "").strip().lower()
    if not aid or itype not in {"checkout", "daily", "return", "damage"}:
        return ServiceResult(ok=False, error="Asset and inspection type are required.")
    asset = fetch_by_id("assets", aid)
    if not isinstance(asset, dict) or not is_rental_equipment(asset):
        return ServiceResult(ok=False, error="Not rental equipment.")
    if itype != "damage":
        existing = list_open_inspection(aid, itype, job_id=job_id)
        if existing:
            return ServiceResult(ok=True, data={"id": existing.get("id"), "existing": True})
    prof = current_profile() or {}
    payload = new_inspection_payload(
        asset_id=aid,
        inspection_type=itype,
        job_id=job_id,
        customer_id=customer_id,
        performed_by_name=str(prof.get("full_name") or prof.get("name") or "").strip(),
        performed_by_user_id=str(prof.get("id") or "").strip() or None,
    )
    return save_rental_inspection(payload)


def get_rental_equipment_dashboard_summary(asset: dict[str, Any]) -> dict[str, Any]:
    """Summary card data for a single rental asset (QR landing page)."""
    aid = str(asset.get("id") or "").strip()
    job_id = str(asset.get("assigned_job_id") or "").strip() or None
    job_label = "—"
    customer_name = "—"
    if job_id:
        job = fetch_by_id("jobs", job_id)
        if isinstance(job, dict):
            num = str(job.get("job_number") or job.get("number") or "").strip()
            name = str(job.get("job_name") or job.get("name") or "").strip()
            job_label = f"{num} — {name}".strip(" —") if num or name else job_id
            cid = str(job.get("customer_id") or "").strip()
            if cid:
                customer = fetch_by_id("customers", cid)
                if isinstance(customer, dict):
                    customer_name = str(
                        customer.get("customer_name") or customer.get("company_name") or customer.get("name") or "—"
                    ).strip() or "—"
    inspections = list_rental_inspections_for_asset(aid) if aid else []
    return {
        "asset_id": aid,
        "asset_name": str(asset.get("asset_name") or asset.get("name") or "Asset"),
        "asset_number": str(asset.get("asset_number") or asset.get("asset_id") or "—"),
        "asset_status": str(asset.get("status") or "—"),
        "rental_status": rental_inspection_dashboard_status(asset, inspections),
        "customer_name": customer_name,
        "job_label": job_label,
        "job_id": job_id,
        "inspection_count": len(inspections),
    }


def create_damage_report(
    *,
    asset_id: str,
    damaged_item: str,
    notes: str,
    job_id: str | None = None,
) -> ServiceResult:
    """Start a damage-report inspection draft."""
    aid = str(asset_id or "").strip()
    if not aid:
        return ServiceResult(ok=False, error="Asset is required.")
    asset = fetch_by_id("assets", aid)
    if not isinstance(asset, dict) or not is_rental_equipment(asset):
        return ServiceResult(ok=False, error="Not rental equipment.")
    jid = str(job_id or asset.get("assigned_job_id") or "").strip() or None
    prof = current_profile() or {}
    payload = new_inspection_payload(
        asset_id=aid,
        inspection_type="damage",
        job_id=jid,
        customer_id=_customer_id_for_job(jid),
        performed_by_name=str(prof.get("full_name") or prof.get("name") or "").strip(),
        performed_by_user_id=str(prof.get("id") or "").strip() or None,
    )
    payload["damage_reported"] = True
    payload["damage_location"] = str(damaged_item or "").strip()
    payload["damage_description"] = str(notes or "").strip()
    return save_rental_inspection(payload)


def _customer_id_for_job(job_id: str | None) -> str | None:
    jid = str(job_id or "").strip()
    if not jid:
        return None
    job = fetch_by_id("jobs", jid)
    if not isinstance(job, dict):
        return None
    cid = str(job.get("customer_id") or "").strip()
    return cid or None


def pdf_export_filename(record: dict[str, Any]) -> str:
    itype = str(record.get("inspection_type") or "inspection").strip()
    d = str(record.get("completed_at") or date.today().isoformat())[:10]
    return f"IPS_Rental_{itype}_{d}.pdf"
