"""Coupling inspection persistence, validation, and photo storage."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

try:
    from app.auth import current_profile
    from app.db import (
        create_signed_url,
        fetch_by_match_admin,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )
    from app.services.coupling_inspection_specs import (
        BOLT_COUNT,
        COUPLING_MODEL_OPTIONS,
        default_torque_rows,
        normalize_torque_rows,
        specs_for_model,
    )
    from app.services.repository import ServiceResult, clear_all_data_caches, fetch_by_id
    from app.services.task_photos import compress_image_bytes
except ImportError:
    from auth import current_profile  # type: ignore
    from db import (  # type: ignore
        create_signed_url,
        fetch_by_match_admin,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )
    from services.coupling_inspection_specs import (  # type: ignore
        BOLT_COUNT,
        COUPLING_MODEL_OPTIONS,
        default_torque_rows,
        normalize_torque_rows,
        specs_for_model,
    )
    from services.repository import ServiceResult, clear_all_data_caches, fetch_by_id  # type: ignore
    from services.task_photos import compress_image_bytes  # type: ignore

_LOG = logging.getLogger(__name__)

TABLE = "coupling_inspections"
STORAGE_PREFIX = "coupling-inspections"

PHOTO_SLOTS: tuple[str, ...] = (
    "before",
    "coupling",
    "torque_witness",
    "final",
    "additional",
)

PHOTO_SLOT_LABELS: dict[str, str] = {
    "before": "Before photo",
    "coupling": "Coupling inspection photo",
    "torque_witness": "Torque / witness mark photo",
    "final": "Final completed photo",
    "additional": "Additional photo",
}


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


def _as_list(v: Any) -> list[Any]:
    if isinstance(v, list):
        return list(v)
    if isinstance(v, str) and v.strip():
        try:
            parsed = json.loads(v)
            return list(parsed) if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def normalize_coupling_inspection(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["header"] = _as_dict(row.get("header"))
    out["specs"] = _as_dict(row.get("specs"))
    out["torque_rows"] = normalize_torque_rows(
        _as_list(row.get("torque_rows")),
        model_key=str(row.get("coupling_model") or "1030G20"),
    )
    out["inspection_fields"] = _as_dict(row.get("inspection_fields"))
    out["photo_attachments"] = _as_list(row.get("photo_attachments"))
    return out


def build_header_context(
    *,
    job: dict[str, Any] | None,
    equipment: dict[str, Any] | None,
    technician: str = "",
) -> dict[str, Any]:
    job = job or {}
    equipment = equipment or {}
    job_number = str(job.get("job_number") or "").strip()
    return {
        "customer": str(job.get("customer") or job.get("customer_name") or "").strip(),
        "job_number": job_number,
        "work_order_number": job_number,
        "equipment_name": str(equipment.get("asset_name") or equipment.get("name") or "").strip(),
        "asset_number": str(equipment.get("asset_number") or equipment.get("asset_id") or "").strip(),
        "location": str(job.get("location") or equipment.get("location") or "").strip(),
        "inspection_date": date.today().isoformat(),
        "technician": technician.strip(),
    }


def new_inspection_payload(
    *,
    job_id: str | None,
    equipment_id: str | None,
    customer_id: str | None,
    coupling_model: str = "1030G20",
    header: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model = coupling_model if coupling_model in COUPLING_MODEL_OPTIONS else "1030G20"
    specs = specs_for_model(model)
    prof = current_profile() or {}
    tech = str((header or {}).get("technician") or prof.get("full_name") or prof.get("name") or "").strip()
    hdr = dict(header or {})
    if tech and not hdr.get("technician"):
        hdr["technician"] = tech
    return {
        "job_id": job_id or None,
        "equipment_id": equipment_id or None,
        "customer_id": customer_id or None,
        "coupling_model": model,
        "header": hdr,
        "specs": specs,
        "torque_rows": default_torque_rows(model),
        "inspection_fields": {
            "actual_hub_gap_in": None,
            "lubricant_type": specs.get("lubricant_type_default") or "",
            "lubricant_quantity_added": "",
            "coupling_teeth_condition": "",
            "grease_condition": "",
            "seal_condition": "",
            "cover_installed": False,
            "fasteners_witness_marked": False,
            "guard_installed": False,
            "notes": "",
        },
        "photo_attachments": [],
        "technician_signature": "",
        "supervisor_signature": "",
        "customer_signature": "",
        "status": "draft",
        "created_by": prof.get("id"),
    }


def list_coupling_inspections(
    *,
    job_id: str | None = None,
    equipment_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    match: dict[str, Any] = {}
    if job_id:
        match["job_id"] = job_id
    if equipment_id:
        match["equipment_id"] = equipment_id
    try:
        rows = fetch_by_match_admin(TABLE, match, limit=limit) or []
    except Exception as exc:
        _LOG.warning("list_coupling_inspections failed: %s", exc)
        return []
    rows.sort(key=lambda r: str(r.get("updated_at") or r.get("created_at") or ""), reverse=True)
    return [normalize_coupling_inspection(r) for r in rows]


def get_coupling_inspection(inspection_id: str) -> dict[str, Any] | None:
    row = fetch_by_id(TABLE, inspection_id, normalize=normalize_coupling_inspection)
    return row


def save_coupling_inspection(
    data: dict[str, Any],
    *,
    inspection_id: str | None = None,
    mark_complete: bool = False,
    mark_exported: bool = False,
) -> ServiceResult:
    payload = {
        "job_id": data.get("job_id") or None,
        "equipment_id": data.get("equipment_id") or None,
        "customer_id": data.get("customer_id") or None,
        "coupling_model": str(data.get("coupling_model") or "1030G20"),
        "header": data.get("header") or {},
        "specs": data.get("specs") or {},
        "torque_rows": normalize_torque_rows(data.get("torque_rows") or [], model_key=str(data.get("coupling_model") or "1030G20")),
        "inspection_fields": data.get("inspection_fields") or {},
        "photo_attachments": data.get("photo_attachments") or [],
        "technician_signature": str(data.get("technician_signature") or ""),
        "supervisor_signature": str(data.get("supervisor_signature") or ""),
        "customer_signature": str(data.get("customer_signature") or ""),
        "updated_at": _utc_now_iso(),
    }
    status = str(data.get("status") or "draft").strip().lower()
    if mark_complete:
        errors = validate_for_complete(data)
        if errors:
            return ServiceResult(ok=False, error="; ".join(errors))
        payload["status"] = "complete"
        payload["completed_at"] = _utc_now_iso()
    elif mark_exported:
        payload["status"] = "exported"
    else:
        payload["status"] = status if status in {"draft", "complete", "exported"} else "draft"

    rid = str(inspection_id or data.get("id") or "").strip()
    try:
        if rid:
            rows = update_rows_admin(TABLE, payload, {"id": rid})
            clear_all_data_caches()
            row = rows[0] if rows else None
            return ServiceResult(ok=True, data=normalize_coupling_inspection(row) if row else None)
        payload["created_at"] = _utc_now_iso()
        if "created_by" not in payload or not payload.get("created_by"):
            payload["created_by"] = (current_profile() or {}).get("id")
        row = insert_row_admin(TABLE, payload)
        clear_all_data_caches()
        return ServiceResult(ok=True, data=normalize_coupling_inspection(row) if row else None)
    except Exception as exc:
        msg = f"Could not save coupling inspection: {exc}"
        _LOG.warning(msg)
        return ServiceResult(ok=False, error=msg)


def validate_for_complete(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = normalize_torque_rows(
        _as_list(data.get("torque_rows")),
        model_key=str(data.get("coupling_model") or "1030G20"),
    )
    if len(rows) != BOLT_COUNT:
        errors.append(f"All {BOLT_COUNT} bolt torque rows are required")
    else:
        for i, row in enumerate(rows, start=1):
            if not row.get("final_checked"):
                errors.append(f"Bolt {i}: final torque checkbox required")
            if not row.get("witness_mark_checked"):
                errors.append(f"Bolt {i}: witness mark checkbox required")
            if not str(row.get("initial_signature") or "").strip():
                errors.append(f"Bolt {i}: initial/signature required")

    if not str(data.get("technician_signature") or "").strip():
        errors.append("Technician signature is required")
    if not str(data.get("customer_signature") or "").strip():
        errors.append("Customer signature is required")

    photos = _as_list(data.get("photo_attachments"))
    if not photos:
        errors.append("At least one photo attachment is required")
    return errors


def completion_percentage(data: dict[str, Any]) -> float:
    """Weighted progress toward complete inspection (8-bolt pattern)."""
    total = float(BOLT_COUNT * 3 + 3)  # final + witness + initial per bolt, + tech + customer + photo
    done = 0.0
    rows = normalize_torque_rows(
        _as_list(data.get("torque_rows")),
        model_key=str(data.get("coupling_model") or "1030G20"),
    )
    for row in rows[:BOLT_COUNT]:
        if row.get("final_checked"):
            done += 1
        if row.get("witness_mark_checked"):
            done += 1
        if str(row.get("initial_signature") or "").strip():
            done += 1
    if str(data.get("technician_signature") or "").strip():
        done += 1
    if str(data.get("customer_signature") or "").strip():
        done += 1
    if _as_list(data.get("photo_attachments")):
        done += 1
    return round(min(100.0, (done / total) * 100.0), 1)


def upload_inspection_photo(
    *,
    inspection_id: str,
    slot: str,
    uploaded_file: Any,
    existing_attachments: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    if uploaded_file is None:
        return list(existing_attachments or []), None
    raw = uploaded_file.read()
    if not raw:
        return list(existing_attachments or []), "Empty file"
    blob, content_type, ext = compress_image_bytes(raw, str(getattr(uploaded_file, "name", "") or ""))
    fname = f"{slot}_{uuid4().hex[:8]}{ext}"
    storage_path = f"{STORAGE_PREFIX}/{inspection_id}/{fname}"
    try:
        upload_bytes_admin(storage_path, blob, content_type=content_type)
    except Exception as exc:
        return list(existing_attachments or []), f"Upload failed: {exc}"

    attachments = [a for a in (existing_attachments or []) if str(a.get("slot") or "") != slot]
    attachments.append(
        {
            "slot": slot,
            "storage_path": storage_path,
            "file_name": str(getattr(uploaded_file, "name", "") or fname),
            "uploaded_at": _utc_now_iso(),
        }
    )
    return attachments, None


def photo_view_url(attachment: dict[str, Any]) -> str | None:
    path = str(attachment.get("storage_path") or attachment.get("path") or "").strip()
    if not path:
        return None
    try:
        return create_signed_url(path, expires_in=3600)
    except Exception:
        return None
