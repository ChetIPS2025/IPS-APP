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
        FORM_VERSION,
        default_inspection_results,
        default_torque_rows,
        normalize_torque_rows,
        specs_for_model,
    )
    from app.services.repository import ServiceResult, clear_data_cache_for_table, fetch_by_id
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
        FORM_VERSION,
        default_inspection_results,
        default_torque_rows,
        normalize_torque_rows,
        specs_for_model,
    )
    from services.repository import ServiceResult, clear_data_cache_for_table, fetch_by_id  # type: ignore
    from services.task_photos import compress_image_bytes  # type: ignore

_LOG = logging.getLogger(__name__)

try:
    from app.services.task_display import task_number_display
except ImportError:
    from services.task_display import task_number_display  # type: ignore

TABLE = "coupling_inspections"
JOB_TASKS_TABLE = "job_tasks"
IPS_TASK_TABLES: tuple[str, ...] = ("todos", "tasks")
TORQUE_TABLE = "coupling_torque_checks"
PHOTOS_TABLE = "coupling_inspection_photos"
SIGNATURES_TABLE = "coupling_inspection_signatures"
STORAGE_PREFIX = "coupling-inspections"

PHOTO_SLOTS: tuple[str, ...] = (
    "before_service",
    "coupling_teeth",
    "hub_gap",
    "grease_condition",
    "torque_verification",
    "witness_marks",
    "guard_installed",
    "final_condition",
)

PHOTO_SLOT_LABELS: dict[str, str] = {
    "before_service": "Coupling before service",
    "coupling_teeth": "Coupling teeth",
    "hub_gap": "Hub gap measurement",
    "grease_condition": "Grease/lubricant condition",
    "torque_verification": "Torque verification",
    "witness_marks": "Witness marks",
    "guard_installed": "Guard installed",
    "final_condition": "Final completed condition",
}

SIGNATURE_ROLES: tuple[str, ...] = ("technician", "supervisor", "customer_representative")
FORM_SIGNATURE_ROLES: tuple[str, ...] = ("technician", "supervisor")
SIGNATURE_ROLE_LABELS: dict[str, str] = {
    "technician": "Technician",
    "supervisor": "Supervisor",
    "customer_representative": "Customer Representative",
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


def normalize_inspection_results(raw: Any) -> dict[str, Any]:
    """Normalize V7 pass/fail/N/A inspection result rows."""
    base = default_inspection_results()
    if not isinstance(raw, dict):
        return base
    # Legacy flat V6 fields → migrate into structured results
    if "actual_hub_gap_in" in raw and not isinstance(raw.get("actual_hub_gap_in"), dict):
        legacy_map = {
            "actual_hub_gap_in": raw.get("actual_hub_gap_in"),
            "lubricant_type": raw.get("lubricant_type"),
            "lubricant_quantity_added": raw.get("lubricant_quantity_added"),
            "coupling_teeth_condition": raw.get("coupling_teeth_condition"),
            "grease_condition": raw.get("grease_condition"),
            "seal_condition": raw.get("seal_condition"),
            "cover_installed": raw.get("cover_installed"),
            "fasteners_witness_marked": raw.get("fasteners_witness_marked"),
            "guard_installed": raw.get("guard_installed"),
            "final_inspection_complete": raw.get("final_inspection_complete", False),
        }
        for key, val in legacy_map.items():
            if key not in base:
                continue
            base[key]["value"] = val if val is not None else base[key]["value"]
        notes = str(raw.get("notes") or "").strip()
        if notes and base.get("final_inspection_complete"):
            base["final_inspection_complete"]["notes"] = notes
        return base
    for key in base:
        item = raw.get(key)
        if isinstance(item, dict):
            base[key].update({k: item.get(k, base[key].get(k)) for k in ("value", "pass", "fail", "na", "notes")})
    return base


def normalize_signatures_meta(
    data: dict[str, Any],
    *,
    technician_signature: str = "",
    supervisor_signature: str = "",
    customer_signature: str = "",
) -> dict[str, dict[str, Any]]:
    raw = _as_dict(data.get("signatures_meta"))
    if not raw:
        hdr = _as_dict(data.get("header"))
        raw = _as_dict(hdr.get("signatures_meta"))
    out: dict[str, dict[str, Any]] = {}
    legacy = {
        "technician": technician_signature,
        "supervisor": supervisor_signature,
        "customer_representative": customer_signature,
    }
    hdr = _as_dict(data.get("header"))
    default_names = {
        "technician": str(hdr.get("technician") or ""),
        "supervisor": str(hdr.get("supervisor") or ""),
        "customer_representative": str(hdr.get("customer_representative") or ""),
    }
    for role in SIGNATURE_ROLES:
        entry = _as_dict(raw.get(role))
        img = str(entry.get("signature_image") or legacy.get(role) or "").strip()
        out[role] = {
            "signer_name": str(entry.get("signer_name") or default_names.get(role) or "").strip(),
            "signature_image": img,
            "signed_at": str(entry.get("signed_at") or "").strip(),
        }
    return out


def normalize_coupling_inspection(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["form_version"] = str(row.get("form_version") or FORM_VERSION)
    out["header"] = _as_dict(row.get("header"))
    out["specs"] = _as_dict(row.get("specs"))
    out["torque_rows"] = normalize_torque_rows(
        _as_list(row.get("torque_rows")),
        model_key=str(row.get("coupling_model") or "1030G20"),
    )
    out["inspection_fields"] = normalize_inspection_results(row.get("inspection_fields"))
    out["photo_attachments"] = _as_list(row.get("photo_attachments"))
    out["signatures_meta"] = normalize_signatures_meta(
        out,
        technician_signature=str(row.get("technician_signature") or ""),
        supervisor_signature=str(row.get("supervisor_signature") or ""),
        customer_signature=str(row.get("customer_signature") or ""),
    )
    out["technician_signature"] = out["signatures_meta"]["technician"]["signature_image"]
    out["supervisor_signature"] = out["signatures_meta"]["supervisor"]["signature_image"]
    out["customer_signature"] = out["signatures_meta"]["customer_representative"]["signature_image"]
    return out


def build_header_context(
    *,
    job: dict[str, Any] | None,
    equipment: dict[str, Any] | None,
    technician: str = "",
    job_task: dict[str, Any] | None = None,
) -> dict[str, Any]:
    job = job or {}
    equipment = equipment or {}
    job_number = str(job.get("job_number") or "").strip()
    hdr = {
        "customer": str(job.get("customer") or job.get("customer_name") or "").strip(),
        "job_number": job_number,
        "work_order_number": job_number,
        "equipment_name": str(equipment.get("asset_name") or equipment.get("name") or "").strip(),
        "asset_number": str(equipment.get("asset_number") or equipment.get("asset_id") or "").strip(),
        "location": str(job.get("location") or equipment.get("location") or "").strip(),
        "inspection_date": date.today().isoformat(),
        "technician": technician.strip(),
        "supervisor": "",
        "customer_representative": "",
    }
    if job_task:
        snap = task_link_snapshot(job_task)
        hdr["task_id"] = snap.get("task_id")
        hdr["subjob_name"] = snap.get("subjob_name")
        hdr["task_title"] = snap.get("task_title")
        hdr["linked_task_status"] = snap.get("linked_task_status")
    return hdr


def coupling_inspection_status_label(status: str) -> str:
    s = str(status or "draft").strip().lower()
    if s == "complete":
        return "Completed"
    if s == "exported":
        return "Exported"
    return "Draft"


def task_link_snapshot(job_task: dict[str, Any] | None) -> dict[str, Any]:
    """Denormalized task/subjob fields for coupling_inspections."""
    if not job_task:
        return {
            "task_id": None,
            "subjob_id": None,
            "subjob_name": "",
            "task_title": "",
            "linked_task_status": "",
        }
    tid = str(job_task.get("id") or "").strip() or None
    title = str(job_task.get("title") or "").strip()
    task_number = str(job_task.get("task_number") or job_task.get("hazard_number") or "").strip()
    if title and not task_number and not str(job_task.get("issue") or "").strip():
        status = str(job_task.get("status") or "Open").strip().lower()
        return {
            "task_id": tid,
            "subjob_id": tid,
            "subjob_name": title[:200],
            "task_title": title[:500],
            "linked_task_status": status,
        }
    subjob_name = task_number_display(job_task)
    issue = str(job_task.get("issue") or "").strip()
    action = str(job_task.get("action_required") or "").strip()
    task_title = issue or action or subjob_name
    status = str(job_task.get("status") or "not_started").strip().lower()
    if status == "open":
        status = "not_started"
    return {
        "task_id": tid,
        "subjob_id": tid,
        "subjob_name": subjob_name,
        "task_title": task_title[:500],
        "linked_task_status": status,
    }


def fetch_job_task(task_id: str | None) -> dict[str, Any] | None:
    tid = str(task_id or "").strip()
    if not tid:
        return None
    row = fetch_by_id(JOB_TASKS_TABLE, tid)
    if isinstance(row, dict):
        return row
    for table in IPS_TASK_TABLES:
        row = fetch_by_id(table, tid)
        if isinstance(row, dict):
            return row
    return None


def list_job_tasks_for_job(job_id: str | None, *, limit: int = 500) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    if not jid:
        return []
    try:
        rows = fetch_by_match_admin(JOB_TASKS_TABLE, {"job_id": jid}, limit=limit) or []
    except Exception as exc:
        _LOG.warning("list_job_tasks_for_job failed: %s", exc)
        return []
    rows = [r for r in rows if isinstance(r, dict)]
    rows.sort(key=lambda r: task_number_display(r).lower())
    return rows


def task_link_option_label(job_task: dict[str, Any]) -> str:
    snap = task_link_snapshot(job_task)
    name = str(snap.get("subjob_name") or "—")
    title = str(snap.get("task_title") or "").strip()
    if title and title != name:
        short = title if len(title) <= 60 else title[:57] + "…"
        return f"{name} — {short}"
    return name


def apply_task_link_to_payload(
    payload: dict[str, Any],
    *,
    job_task: dict[str, Any] | None,
    job_id: str | None = None,
) -> dict[str, Any]:
    out = dict(payload)
    snap = task_link_snapshot(job_task)
    if snap.get("task_id"):
        out["task_id"] = snap["task_id"]
        out["subjob_id"] = snap["subjob_id"]
        out["subjob_name"] = snap["subjob_name"]
        out["task_title"] = snap["task_title"]
        out["linked_task_status"] = snap["linked_task_status"]
        if job_id:
            out["job_id"] = str(job_id).strip() or out.get("job_id")
        elif job_task:
            out["job_id"] = str(job_task.get("job_id") or out.get("job_id") or "") or None
    return out


def new_inspection_payload(
    *,
    job_id: str | None,
    equipment_id: str | None,
    customer_id: str | None,
    coupling_model: str = "1030G20",
    header: dict[str, Any] | None = None,
    task_id: str | None = None,
    job_task: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model = coupling_model if coupling_model in COUPLING_MODEL_OPTIONS else "1030G20"
    specs = specs_for_model(model)
    prof = current_profile() or {}
    tech = str((header or {}).get("technician") or prof.get("full_name") or prof.get("name") or "").strip()
    hdr = dict(header or {})
    if tech and not hdr.get("technician"):
        hdr["technician"] = tech
    if not job_task and task_id:
        job_task = fetch_job_task(task_id)
    payload = {
        "job_id": job_id or None,
        "equipment_id": equipment_id or None,
        "customer_id": customer_id or None,
        "coupling_model": model,
        "form_version": FORM_VERSION,
        "header": hdr,
        "specs": specs,
        "torque_rows": default_torque_rows(model),
        "inspection_fields": default_inspection_results(),
        "photo_attachments": [],
        "signatures_meta": {
            role: {"signer_name": "", "signature_image": "", "signed_at": ""} for role in SIGNATURE_ROLES
        },
        "technician_signature": "",
        "supervisor_signature": "",
        "customer_signature": "",
        "status": "draft",
        "created_by": prof.get("id"),
        "task_id": None,
        "subjob_id": None,
        "subjob_name": "",
        "task_title": "",
        "linked_task_status": "",
    }
    return apply_task_link_to_payload(payload, job_task=job_task, job_id=job_id)


def _inspection_is_unlinked(row: dict[str, Any]) -> bool:
    return not str(row.get("task_id") or row.get("subjob_id") or "").strip()


def list_unlinked_coupling_inspections_for_job(
    job_id: str | None,
    *,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Coupling inspections on this job with no subjob/task link."""
    rows = list_coupling_inspections(job_id=job_id, limit=limit)
    unlinked = [r for r in rows if _inspection_is_unlinked(r)]
    unlinked.sort(key=lambda r: str(r.get("updated_at") or r.get("created_at") or ""), reverse=True)
    return unlinked


def link_coupling_inspection_to_task(
    inspection_id: str,
    task: dict[str, Any],
    *,
    job_id: str | None = None,
) -> ServiceResult:
    iid = str(inspection_id or "").strip()
    if not iid:
        return ServiceResult(ok=False, error="Missing inspection id")
    existing = get_coupling_inspection(iid)
    if not existing:
        return ServiceResult(ok=False, error="Coupling inspection not found")
    tid = str(task.get("id") or "").strip()
    job_task = fetch_job_task(tid) if tid else None
    if not job_task and isinstance(task, dict):
        job_task = task
    payload = apply_task_link_to_payload(
        dict(existing),
        job_task=job_task,
        job_id=job_id or str(existing.get("job_id") or ""),
    )
    req_job = str(job_id or "").strip()
    insp_job = str(payload.get("job_id") or "").strip()
    if req_job and insp_job and insp_job != req_job:
        return ServiceResult(ok=False, error="Inspection belongs to a different job")
    hdr = dict(payload.get("header") or {})
    snap = task_link_snapshot(job_task)
    if snap.get("subjob_name"):
        hdr["subjob_name"] = snap["subjob_name"]
    if snap.get("task_title"):
        hdr["task_title"] = snap["task_title"]
    if snap.get("task_id"):
        hdr["task_id"] = snap["task_id"]
    payload["header"] = hdr
    return save_coupling_inspection(payload, inspection_id=iid)


def unlink_coupling_inspection_from_task(inspection_id: str) -> ServiceResult:
    iid = str(inspection_id or "").strip()
    if not iid:
        return ServiceResult(ok=False, error="Missing inspection id")
    existing = get_coupling_inspection(iid)
    if not existing:
        return ServiceResult(ok=False, error="Coupling inspection not found")
    payload = dict(existing)
    for key in ("task_id", "subjob_id", "subjob_name", "task_title", "linked_task_status"):
        payload[key] = None
    hdr = dict(payload.get("header") or {})
    for key in ("task_id", "subjob_name", "task_title", "linked_task_status"):
        hdr.pop(key, None)
    payload["header"] = hdr
    return save_coupling_inspection(payload, inspection_id=iid)


def list_coupling_inspections(
    *,
    job_id: str | None = None,
    equipment_id: str | None = None,
    task_id: str | None = None,
    subjob_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    match: dict[str, Any] = {}
    if job_id:
        match["job_id"] = job_id
    if equipment_id:
        match["equipment_id"] = equipment_id
    tid = str(task_id or subjob_id or "").strip()
    if tid:
        try:
            by_task = fetch_by_match_admin(TABLE, {**match, "task_id": tid}, limit=limit) or []
            by_subjob = fetch_by_match_admin(TABLE, {**match, "subjob_id": tid}, limit=limit) or []
        except Exception as exc:
            _LOG.warning("list_coupling_inspections failed: %s", exc)
            return []
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for row in [*by_task, *by_subjob]:
            if not isinstance(row, dict):
                continue
            rid = str(row.get("id") or "").strip()
            if rid and rid in seen:
                continue
            if rid:
                seen.add(rid)
            rows.append(row)
        rows.sort(key=lambda r: str(r.get("updated_at") or r.get("created_at") or ""), reverse=True)
        return [normalize_coupling_inspection(r) for r in rows]
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


def _sync_child_records(inspection_id: str, data: dict[str, Any]) -> None:
    """Mirror JSON payload into V7 child tables (best-effort)."""
    if not inspection_id:
        return
    try:
        from app.db import delete_rows_admin, insert_row_admin
    except ImportError:
        from db import delete_rows_admin, insert_row_admin  # type: ignore

    try:
        delete_rows_admin(TORQUE_TABLE, {"inspection_id": inspection_id})
        for row in normalize_torque_rows(
            _as_list(data.get("torque_rows")),
            model_key=str(data.get("coupling_model") or "1030G20"),
        ):
            pf = row.get("pass_fail")
            insert_row_admin(
                TORQUE_TABLE,
                {
                    "inspection_id": inspection_id,
                    "bolt_order": int(row.get("order") or 0),
                    "clock_position": str(row.get("clock_position") or ""),
                    "pass1_checked": bool(row.get("pass1_checked")),
                    "pass2_checked": bool(row.get("pass2_checked")),
                    "final_checked": bool(row.get("final_checked")),
                    "witness_initials": str(row.get("witness_initials") or "").strip(),
                    "pass_fail": pf if pf in ("pass", "fail") else None,
                    "notes": str(row.get("notes") or "").strip(),
                    "updated_at": _utc_now_iso(),
                },
            )

        delete_rows_admin(PHOTOS_TABLE, {"inspection_id": inspection_id})
        prof = current_profile() or {}
        uploader = str(prof.get("full_name") or prof.get("name") or prof.get("email") or "").strip()
        for att in _as_list(data.get("photo_attachments")):
            slot = str(att.get("slot") or att.get("category") or "").strip()
            if not slot:
                continue
            insert_row_admin(
                PHOTOS_TABLE,
                {
                    "inspection_id": inspection_id,
                    "category": slot,
                    "storage_path": str(att.get("storage_path") or att.get("path") or ""),
                    "file_name": str(att.get("file_name") or ""),
                    "caption": str(att.get("caption") or ""),
                    "uploaded_by": str(att.get("uploaded_by") or uploader),
                    "uploaded_at": str(att.get("uploaded_at") or _utc_now_iso()),
                },
            )

        delete_rows_admin(SIGNATURES_TABLE, {"inspection_id": inspection_id})
        meta = normalize_signatures_meta(data)
        for role in SIGNATURE_ROLES:
            entry = meta.get(role) or {}
            if not str(entry.get("signature_image") or "").strip() and not str(entry.get("signer_name") or "").strip():
                continue
            signed_at = str(entry.get("signed_at") or "").strip() or None
            insert_row_admin(
                SIGNATURES_TABLE,
                {
                    "inspection_id": inspection_id,
                    "role": role,
                    "signer_name": str(entry.get("signer_name") or ""),
                    "signature_image": str(entry.get("signature_image") or ""),
                    "signed_at": signed_at,
                    "updated_at": _utc_now_iso(),
                },
            )
    except Exception as exc:
        _LOG.warning("coupling inspection child sync failed: %s", exc)


def pdf_export_filename(record: dict[str, Any]) -> str:
    hdr = _as_dict(record.get("header"))
    job_no = str(hdr.get("job_number") or "JOB").strip().replace(" ", "_")
    insp_date = str(hdr.get("inspection_date") or date.today().isoformat())[:10]
    return f"IPS_Coupling_Inspection_V7_{job_no}_{insp_date}.pdf"


def save_coupling_inspection(
    data: dict[str, Any],
    *,
    inspection_id: str | None = None,
    mark_complete: bool = False,
    mark_exported: bool = False,
) -> ServiceResult:
    sig_meta = normalize_signatures_meta(data)
    header = dict(data.get("header") or {})
    header["signatures_meta"] = sig_meta
    payload = {
        "job_id": data.get("job_id") or None,
        "equipment_id": data.get("equipment_id") or None,
        "customer_id": data.get("customer_id") or None,
        "task_id": data.get("task_id") or None,
        "subjob_id": data.get("subjob_id") or None,
        "subjob_name": str(data.get("subjob_name") or "").strip() or None,
        "task_title": str(data.get("task_title") or "").strip() or None,
        "linked_task_status": str(data.get("linked_task_status") or "").strip() or None,
        "coupling_model": str(data.get("coupling_model") or "1030G20"),
        "form_version": str(data.get("form_version") or FORM_VERSION),
        "header": header,
        "specs": data.get("specs") or {},
        "torque_rows": normalize_torque_rows(data.get("torque_rows") or [], model_key=str(data.get("coupling_model") or "1030G20")),
        "inspection_fields": normalize_inspection_results(data.get("inspection_fields")),
        "photo_attachments": data.get("photo_attachments") or [],
        "technician_signature": sig_meta["technician"]["signature_image"],
        "supervisor_signature": sig_meta["supervisor"]["signature_image"],
        "customer_signature": sig_meta["customer_representative"]["signature_image"],
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
            clear_data_cache_for_table(TABLE)
            row = rows[0] if rows else None
            if row and rid:
                _sync_child_records(rid, {**data, **payload, "signatures_meta": sig_meta})
            return ServiceResult(ok=True, data=normalize_coupling_inspection(row) if row else None)
        payload["created_at"] = _utc_now_iso()
        if "created_by" not in payload or not payload.get("created_by"):
            payload["created_by"] = (current_profile() or {}).get("id")
        row = insert_row_admin(TABLE, payload)
        clear_data_cache_for_table(TABLE)
        new_id = str(row.get("id") or "") if row else ""
        if new_id:
            _sync_child_records(new_id, {**data, **payload, "signatures_meta": sig_meta})
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
                errors.append(f"Bolt {i}: 150 ft-lb checkbox required")
            pf = row.get("pass_fail")
            if pf not in ("pass", "fail"):
                errors.append(f"Bolt {i}: Pass/Fail selection required")
            if not str(row.get("witness_initials") or "").strip():
                errors.append(f"Bolt {i}: witness initials required")

    sig = normalize_signatures_meta(data)
    if not str(sig["technician"]["signature_image"] or "").strip():
        errors.append("Technician signature is required")

    results = normalize_inspection_results(data.get("inspection_fields"))
    for key, item in results.items():
        if not (item.get("pass") or item.get("fail") or item.get("na")):
            errors.append(f"Inspection item '{key}': Pass, Fail, or N/A required")

    photos = _as_list(data.get("photo_attachments"))
    if not photos:
        errors.append("At least one photo attachment is required")
    return errors


def completion_percentage(data: dict[str, Any]) -> float:
    """Weighted progress toward complete inspection (8-bolt pattern)."""
    total = float(BOLT_COUNT * 3 + 2)  # final + witness + initial per bolt, + tech signature + photo
    done = 0.0
    rows = normalize_torque_rows(
        _as_list(data.get("torque_rows")),
        model_key=str(data.get("coupling_model") or "1030G20"),
    )
    for row in rows[:BOLT_COUNT]:
        if row.get("final_checked"):
            done += 1
        if row.get("pass_fail") in ("pass", "fail"):
            done += 1
        if str(row.get("witness_initials") or "").strip():
            done += 1
    sig = normalize_signatures_meta(data)
    if str(sig["technician"]["signature_image"] or "").strip():
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
    caption: str = "",
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

    attachments = [a for a in (existing_attachments or []) if str(a.get("slot") or a.get("category") or "") != slot]
    prof = current_profile() or {}
    uploader = str(prof.get("full_name") or prof.get("name") or prof.get("email") or "").strip()
    attachments.append(
        {
            "slot": slot,
            "category": slot,
            "storage_path": storage_path,
            "file_name": str(getattr(uploaded_file, "name", "") or fname),
            "caption": str(caption or "").strip(),
            "uploaded_by": uploader,
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
