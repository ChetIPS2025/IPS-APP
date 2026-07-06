"""Tool Trailer Dashboard — spot audits, requests, inspections, and history."""

from __future__ import annotations

import random
import re
from datetime import datetime, timezone
from typing import Any

try:
    from app.services.asset_kits_service import (
        assign_asset_kit,
        create_asset_kit_item,
        create_asset_kit_transaction,
        delete_asset_kit_item,
        get_asset_kit_audits,
        get_asset_kit_items,
        get_asset_kit_summary,
        get_asset_kit_transactions,
        update_asset_kit_item,
    )
    from app.services.assets_service import create_asset_issue, get_asset, upload_asset_image
    from app.services.repository import ServiceResult, fetch_rows, insert_row
    from app.services.serialized_tool_service import audit_trailer_tools
except ImportError:
    from services.asset_kits_service import (  # type: ignore
        assign_asset_kit,
        create_asset_kit_item,
        create_asset_kit_transaction,
        delete_asset_kit_item,
        get_asset_kit_audits,
        get_asset_kit_items,
        get_asset_kit_summary,
        get_asset_kit_transactions,
        update_asset_kit_item,
    )
    from services.assets_service import create_asset_issue, get_asset, upload_asset_image  # type: ignore
    from services.repository import ServiceResult, fetch_rows, insert_row  # type: ignore
    from services.serialized_tool_service import audit_trailer_tools  # type: ignore

_TRAILER_REQUESTS = "trailer_tool_requests"
_TRAILER_BROKEN = "trailer_broken_tool_reports"
_TRAILER_INSPECTIONS = "trailer_inspections"
_TRAILER_PHOTOS = "trailer_photos"
_ASSETS = "assets"

SPOT_AUDIT_CONDITIONS = ("Excellent", "Good", "Fair", "Replace")
AUDIT_ITEM_STATUSES = ("Present", "Missing", "Damaged", "Needs Repair")
AUDIT_ITEM_CONDITIONS = ("New", "Good", "Fair", "Damaged", "Needs Repair")
REQUEST_PRIORITIES = ("Low", "Normal", "High", "Urgent")
INSPECTION_CHECKLIST = (
    ("tires_ok", "Tires"),
    ("lights_ok", "Lights"),
    ("jack_ok", "Jack"),
    ("chains_ok", "Chains"),
    ("fire_extinguisher_ok", "Fire Extinguisher"),
    ("first_aid_ok", "First Aid Kit"),
    ("locks_ok", "Locks"),
    ("registration_ok", "Registration"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(raw: object) -> str:
    return str(raw or "").strip()


def _f(val: object, default: float = 0.0) -> float:
    try:
        return float(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _job_label(job_id: object) -> str:
    jid = _clean(job_id)
    if not jid:
        return "—"
    try:
        from app.pages._core._data import load_jobs
    except ImportError:
        from pages._core._data import load_jobs  # type: ignore
    for job in load_jobs():
        if _clean(job.get("id")) == jid:
            num = _clean(job.get("job_number"))
            name = _clean(job.get("job_name") or job.get("name"))
            if num and name:
                return f"{num} · {name}"
            return num or name or jid
    return jid


def map_spot_audit_condition(condition: str) -> tuple[str, str]:
    """Map legacy supervisor spot-audit condition to kit item condition + status."""
    c = _clean(condition)
    if c == "Excellent":
        return "Good", "Present"
    if c == "Good":
        return "Good", "Present"
    if c == "Fair":
        return "Fair", "Present"
    if c == "Replace":
        return "Needs Repair", "Needs Replacement"
    return "Good", "Present"


def normalize_audit_item_status(status: str) -> str:
    """Map audit UI status to persisted kit item status."""
    s = _clean(status)
    if s.casefold() == "needs repair":
        return "Needs Replacement"
    return s or "Present"


def audit_item_requires_photo(status: str) -> bool:
    s = _clean(status).casefold()
    return s in {"present", "damaged", "needs repair"}


def audit_item_requires_missing_note(status: str) -> bool:
    return _clean(status).casefold() == "missing"


def validate_audit_item_line(line: dict[str, Any], *, item_label: str = "Item") -> str | None:
    status = _clean(line.get("status"))
    if not status:
        return f"{item_label}: status is required."
    if audit_item_requires_photo(status):
        if not _clean(line.get("photo_path")) and not _clean(line.get("photo_url")):
            return f"{item_label}: photo is required when status is {status}."
    if audit_item_requires_missing_note(status) and not _clean(line.get("notes")):
        return f"{item_label}: note is required when status is Missing (where expected / what was checked)."
    return None


def validate_audit_item_lines(lines: list[dict[str, Any]], *, labels: dict[str, str] | None = None) -> str | None:
    if not lines:
        return "No audit items to save."
    labels = labels or {}
    for line in lines:
        kid = _clean(line.get("kit_item_id"))
        label = labels.get(kid) or _clean(line.get("item_name")) or "Item"
        err = validate_audit_item_line(line, item_label=label)
        if err:
            return err
    return None


def upload_audit_item_photo(
    trailer_id: str,
    kit_item_id: str,
    uploaded_file: Any,
    *,
    uploaded_by: str | None = None,
    audit_id: str | None = None,
) -> tuple[str, str]:
    """Upload audit evidence photo tied to trailer + kit item (does not change trailer primary image)."""
    pid = _clean(trailer_id)
    kid = _clean(kit_item_id)
    if not pid or not kid or uploaded_file is None:
        return "", ""
    try:
        from app.config import settings
        from app.db import _storage_is_local, create_signed_url, upload_bytes, upload_bytes_admin
        from app.services.item_images import ASSET_IMAGE_BUCKET, resize_item_image_bytes
    except ImportError:
        from config import settings  # type: ignore
        from db import _storage_is_local, create_signed_url, upload_bytes, upload_bytes_admin  # type: ignore
        from services.item_images import ASSET_IMAGE_BUCKET, resize_item_image_bytes  # type: ignore

    raw = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else b""
    if not raw:
        return "", ""
    fname = str(getattr(uploaded_file, "name", "") or "audit-photo.jpg")
    try:
        data, out_name = resize_item_image_bytes(raw)
    except Exception:
        data, out_name = raw, fname

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe = re.sub(r"[^\w.-]+", "_", fname).strip("._")[:80] or "audit-photo"
    if not safe.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        safe = f"{safe}.jpg"
    audit_seg = _clean(audit_id) or "pending"
    user_seg = re.sub(r"[^\w.-]+", "_", _clean(uploaded_by))[:32] or "user"
    storage_path = f"assets/{pid}/kit_audits/{kid}/{audit_seg}/{ts}_{user_seg}_{safe}"
    bucket = str(getattr(settings, "storage_bucket", "") or ASSET_IMAGE_BUCKET)
    content_type = str(getattr(uploaded_file, "type", "") or "image/jpeg")
    upload_fn = upload_bytes_admin if _storage_is_local() else upload_bytes
    try:
        upload_fn(storage_path, data, content_type=content_type, bucket=bucket)
    except Exception:
        return "", ""
    try:
        url = create_signed_url(storage_path, expires_in=3600, bucket=bucket)
    except Exception:
        url = ""
    return storage_path, url if str(url).startswith("http") else ""


def get_trailer_inventory_items(trailer_id: str) -> list[dict[str, Any]]:
    """Active kit line items assigned to the trailer."""
    pid = _clean(trailer_id)
    if not pid:
        return []
    return get_asset_kit_items(pid)


def select_spot_audit_items(trailer_id: str, *, count: int = 5, seed: int | None = None) -> list[dict[str, Any]]:
    """Randomly sample kit inventory lines for a spot audit."""
    pool = get_trailer_inventory_items(trailer_id)
    if not pool:
        return []
    rng = random.Random(seed)
    sample_size = min(count, len(pool))
    return rng.sample(pool, sample_size)


def get_trailer_dashboard_summary(trailer_id: str, asset: dict[str, Any] | None = None) -> dict[str, Any]:
    """Header cards: status, job, supervisor, last audit, inventory counts."""
    row = asset or get_asset(_clean(trailer_id)) or {}
    summary = get_asset_kit_summary(_clean(trailer_id), row)
    job_id = _clean(row.get("assigned_job_id") or summary.get("assigned_job_id"))
    return {
        **summary,
        "trailer_name": _clean(row.get("asset_name") or row.get("name") or "Tool Trailer"),
        "trailer_number": _clean(row.get("asset_number") or row.get("asset_id") or "—"),
        "trailer_status": _clean(row.get("kit_status") or row.get("status") or "Active"),
        "assigned_job_label": _job_label(job_id) if job_id else "—",
        "assigned_supervisor": summary.get("assigned_supervisor") or _clean(row.get("assigned_to_name") or row.get("operator") or "—"),
        "last_audit": summary.get("last_audit") or _clean(row.get("last_kit_audit_at") or "")[:19] or "—",
        "inventory_total": summary.get("expected_items") or 0,
        "inventory_present": summary.get("present_items") or 0,
        "inventory_missing": summary.get("missing_items") or 0,
    }


def upload_trailer_photo(
    trailer_id: str,
    uploaded_file: Any,
    *,
    uploaded_by: str | None = None,
    caption: str = "",
) -> ServiceResult:
    """Store a dashboard photo on the trailer asset + trailer_photos row."""
    pid = _clean(trailer_id)
    if not pid or uploaded_file is None:
        return ServiceResult(ok=False, error="Trailer and photo are required.")
    upload = upload_asset_image(pid, uploaded_file, uploaded_by=uploaded_by, replace_existing=False)
    if not upload.ok:
        return upload
    data = upload.data if isinstance(upload.data, dict) else {}
    photo_path = _clean(data.get("image_path") or data.get("photo_path"))
    photo_url = _clean(data.get("image_url") or data.get("photo_url"))
    return insert_row(
        _TRAILER_PHOTOS,
        {
            "parent_asset_id": pid,
            "photo_path": photo_path or None,
            "photo_url": photo_url or None,
            "caption": _clean(caption),
            "uploaded_by_user_id": uploaded_by,
        },
    )


def complete_spot_audit(
    trailer_id: str,
    audit_data: dict[str, Any],
    audit_lines: list[dict[str, Any]],
) -> ServiceResult:
    """Save a spot audit with per-item status, condition, and photo proof."""
    pid = _clean(trailer_id)
    if not pid:
        return ServiceResult(ok=False, error="Trailer id is required.")

    labels = {
        _clean(line.get("kit_item_id")): _clean(line.get("item_name") or line.get("tool_name") or "Item")
        for line in audit_lines
    }
    validation_err = validate_audit_item_lines(audit_lines, labels=labels)
    if validation_err:
        return ServiceResult(ok=False, error=validation_err)

    normalized: list[dict[str, Any]] = []
    photo_paths: list[str] = []
    for line in audit_lines:
        kid = _clean(line.get("kit_item_id"))
        if not kid:
            continue
        cond = _clean(line.get("condition") or "Good")
        stat = normalize_audit_item_status(str(line.get("status") or "Present"))
        photo_path = _clean(line.get("photo_path"))
        photo_url = _clean(line.get("photo_url"))
        if photo_path:
            photo_paths.append(photo_path)
        normalized.append(
            {
                "kit_item_id": kid,
                "expected_quantity": _f(line.get("expected_quantity"), 1.0),
                "actual_quantity": _f(line.get("actual_quantity"), 1.0),
                "condition": cond,
                "status": stat,
                "notes": _clean(line.get("notes")),
                "photo_path": photo_path or None,
                "photo_url": photo_url or None,
            }
        )

    if not normalized:
        return ServiceResult(ok=False, error="No valid audit lines.")

    payload = {
        **audit_data,
        "audit_type": "Spot Check",
        "photo_paths": photo_paths,
        "notes": _clean(audit_data.get("notes") or "Tool trailer spot audit."),
    }
    return audit_trailer_tools(pid, payload, normalized)


def create_trailer_tool_request(trailer_id: str, data: dict[str, Any]) -> ServiceResult:
    pid = _clean(trailer_id)
    tool = _clean(data.get("tool_name"))
    if not pid:
        return ServiceResult(ok=False, error="Trailer id is required.")
    if not tool:
        return ServiceResult(ok=False, error="Tool name is required.")
    qty = _f(data.get("quantity"), 1.0)
    if qty <= 0:
        return ServiceResult(ok=False, error="Quantity must be greater than zero.")
    result = insert_row(
        _TRAILER_REQUESTS,
        {
            "parent_asset_id": pid,
            "kit_item_id": data.get("kit_item_id") or None,
            "tool_name": tool,
            "quantity": qty,
            "priority": _clean(data.get("priority") or "Normal") or "Normal",
            "reason": _clean(data.get("reason")),
            "job_id": data.get("job_id") or None,
            "requested_by_user_id": data.get("requested_by_user_id"),
            "requested_by_employee_id": data.get("requested_by_employee_id"),
            "requested_by_name": _clean(data.get("requested_by_name")),
            "requested_by_phone": _clean(data.get("requested_by_phone")),
            "status": "Open",
        },
    )
    if result.ok:
        create_asset_kit_transaction(
            {
                "parent_asset_id": pid,
                "transaction_type": "Tool Request",
                "job_id": data.get("job_id"),
                "performed_by_name": data.get("requested_by_name"),
                "performed_by_phone": data.get("requested_by_phone"),
                "notes": f"{tool} × {qty} ({data.get('priority') or 'Normal'}) — {_clean(data.get('reason'))}",
            }
        )
    return result


def report_broken_trailer_tool(trailer_id: str, data: dict[str, Any]) -> ServiceResult:
    """Report broken tool with photo; creates maintenance issue automatically."""
    pid = _clean(trailer_id)
    tool = _clean(data.get("tool_name"))
    problem = _clean(data.get("problem"))
    if not pid:
        return ServiceResult(ok=False, error="Trailer id is required.")
    if not tool:
        return ServiceResult(ok=False, error="Tool is required.")
    if not problem:
        return ServiceResult(ok=False, error="Problem description is required.")
    if not _clean(data.get("photo_path")) and not _clean(data.get("photo_url")):
        return ServiceResult(ok=False, error="Photo is required.")

    child_id = _clean(data.get("child_asset_id"))
    issue_asset_id = child_id or pid
    description = f"Broken tool on trailer: {tool}. Problem: {problem}"
    notes = _clean(data.get("notes"))
    if notes:
        description = f"{description} Notes: {notes}"

    issue_result = create_asset_issue(
        issue_asset_id,
        {
            "severity": "High",
            "description": description[:4000],
            "reported_by_name": data.get("reported_by_name"),
            "reported_by_phone": data.get("reported_by_phone"),
            "photo_path": data.get("photo_path"),
            "photo_url": data.get("photo_url"),
        },
    )
    if not issue_result.ok:
        return issue_result

    issue_id = ""
    if isinstance(issue_result.data, dict):
        issue_id = _clean(issue_result.data.get("id"))

    kit_item_id = _clean(data.get("kit_item_id"))
    if kit_item_id:
        update_asset_kit_item(
            kit_item_id,
            {
                "status": "Damaged",
                "condition": "Needs Repair",
                "performed_by_name": data.get("reported_by_name"),
            },
        )

    report = insert_row(
        _TRAILER_BROKEN,
        {
            "parent_asset_id": pid,
            "kit_item_id": kit_item_id or None,
            "child_asset_id": child_id or None,
            "tool_name": tool,
            "problem": problem,
            "notes": notes,
            "photo_path": _clean(data.get("photo_path")) or None,
            "photo_url": _clean(data.get("photo_url")) or None,
            "maintenance_issue_id": issue_id or None,
            "reported_by_user_id": data.get("reported_by_user_id"),
            "reported_by_employee_id": data.get("reported_by_employee_id"),
            "reported_by_name": _clean(data.get("reported_by_name")),
            "reported_by_phone": _clean(data.get("reported_by_phone")),
            "status": "Open",
        },
    )
    if report.ok:
        create_asset_kit_transaction(
            {
                "parent_asset_id": pid,
                "kit_item_id": kit_item_id or None,
                "transaction_type": "Mark Damaged",
                "performed_by_name": data.get("reported_by_name"),
                "performed_by_phone": data.get("reported_by_phone"),
                "notes": f"{tool}: {problem}",
            }
        )
    return report


def save_trailer_inspection(trailer_id: str, data: dict[str, Any]) -> ServiceResult:
    pid = _clean(trailer_id)
    if not pid:
        return ServiceResult(ok=False, error="Trailer id is required.")
    if not _clean(data.get("photo_path")) and not _clean(data.get("photo_url")):
        return ServiceResult(ok=False, error="Inspection photo is required.")

    payload = {
        "parent_asset_id": pid,
        "job_id": data.get("job_id") or None,
        "performed_by_user_id": data.get("performed_by_user_id"),
        "performed_by_employee_id": data.get("performed_by_employee_id"),
        "performed_by_name": _clean(data.get("performed_by_name")),
        "performed_by_phone": _clean(data.get("performed_by_phone")),
        "photo_path": _clean(data.get("photo_path")) or None,
        "photo_url": _clean(data.get("photo_url")) or None,
        "notes": _clean(data.get("notes")),
    }
    for field, _label in INSPECTION_CHECKLIST:
        payload[field] = bool(data.get(field))

    result = insert_row(_TRAILER_INSPECTIONS, payload)
    if result.ok:
        create_asset_kit_transaction(
            {
                "parent_asset_id": pid,
                "transaction_type": "Trailer Inspection",
                "job_id": data.get("job_id"),
                "performed_by_name": data.get("performed_by_name"),
                "performed_by_phone": data.get("performed_by_phone"),
                "notes": _clean(data.get("notes")),
            }
        )
    return result


def transfer_trailer(trailer_id: str, data: dict[str, Any]) -> ServiceResult:
    """Assign trailer to supervisor and/or job."""
    return assign_asset_kit(
        _clean(trailer_id),
        {
            **data,
            "job_id": data.get("job_id") or data.get("assigned_job_id"),
        },
    )


def add_tool_to_trailer(trailer_id: str, data: dict[str, Any]) -> ServiceResult:
    result = create_asset_kit_item(
        _clean(trailer_id),
        {
            "item_name": data.get("item_name") or data.get("tool_name"),
            "item_type": data.get("item_type") or "Tool",
            "category": data.get("category"),
            "quantity_expected": _f(data.get("quantity") or data.get("quantity_expected"), 1.0),
            "quantity_actual": _f(data.get("quantity") or data.get("quantity_actual"), 1.0),
            "unit_value": _f(data.get("unit_value"), 0.0),
            "serial_number": data.get("serial_number"),
            "condition": data.get("condition") or "Good",
            "status": "Present",
        },
    )
    if result.ok:
        create_asset_kit_transaction(
            {
                "parent_asset_id": _clean(trailer_id),
                "transaction_type": "Add Item",
                "quantity": _f(data.get("quantity"), 1.0),
                "performed_by_name": data.get("performed_by_name"),
                "notes": _clean(data.get("notes")),
            }
        )
    return result


def remove_tool_from_trailer(trailer_id: str, kit_item_id: str, *, performed_by_name: str = "", notes: str = "") -> ServiceResult:
    item = next((i for i in get_asset_kit_items(_clean(trailer_id)) if _clean(i.get("id")) == _clean(kit_item_id)), None)
    if not item:
        return ServiceResult(ok=False, error="Tool not found on this trailer.")
    result = delete_asset_kit_item(_clean(kit_item_id))
    if result.ok:
        create_asset_kit_transaction(
            {
                "parent_asset_id": _clean(trailer_id),
                "kit_item_id": _clean(kit_item_id),
                "transaction_type": "Remove Item",
                "performed_by_name": performed_by_name,
                "notes": notes or _clean(item.get("item_name")),
            }
        )
    return result


def _fetch_trailer_rows(table: str, trailer_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    pid = _clean(trailer_id)
    rows, _ = fetch_rows(table, limit=limit, order_by="created_at")
    return [r for r in rows if _clean(r.get("parent_asset_id")) == pid]


def get_trailer_history(trailer_id: str, *, limit: int = 40) -> list[dict[str, Any]]:
    """Unified timeline: audits, repairs, transfers, missing, requests, photos."""
    pid = _clean(trailer_id)
    events: list[dict[str, Any]] = []

    for row in get_asset_kit_audits(pid, limit=limit):
        events.append(
            {
                "kind": "Audit",
                "when": _clean(row.get("audit_date") or row.get("created_at")),
                "title": f"{_clean(row.get('audit_type') or 'Audit')} — {_clean(row.get('performed_by_name') or 'Supervisor')}",
                "detail": _clean(row.get("notes")),
            }
        )

    for row in get_asset_kit_transactions(pid, limit=limit):
        txn = _clean(row.get("transaction_type"))
        kind = "Transfer" if txn == "Assign Trailer" else txn or "Activity"
        if txn == "Mark Missing":
            kind = "Missing Tool"
        elif txn == "Mark Damaged":
            kind = "Repair"
        elif txn == "Tool Request":
            kind = "Request"
        events.append(
            {
                "kind": kind,
                "when": _clean(row.get("created_at")),
                "title": txn or "Trailer activity",
                "detail": _clean(row.get("notes")),
            }
        )

    for row in _fetch_trailer_rows(_TRAILER_BROKEN, pid, limit=limit):
        events.append(
            {
                "kind": "Repair",
                "when": _clean(row.get("created_at")),
                "title": f"Broken: {_clean(row.get('tool_name'))}",
                "detail": _clean(row.get("problem")),
            }
        )

    for row in _fetch_trailer_rows(_TRAILER_REQUESTS, pid, limit=limit):
        events.append(
            {
                "kind": "Request",
                "when": _clean(row.get("created_at")),
                "title": f"Request: {_clean(row.get('tool_name'))} × {_f(row.get('quantity'), 1)}",
                "detail": _clean(row.get("reason")),
            }
        )

    for row in _fetch_trailer_rows(_TRAILER_INSPECTIONS, pid, limit=limit):
        events.append(
            {
                "kind": "Inspection",
                "when": _clean(row.get("created_at")),
                "title": f"Trailer inspection — {_clean(row.get('performed_by_name') or 'Supervisor')}",
                "detail": _clean(row.get("notes")),
            }
        )

    for row in _fetch_trailer_rows(_TRAILER_PHOTOS, pid, limit=limit):
        events.append(
            {
                "kind": "Photo",
                "when": _clean(row.get("created_at")),
                "title": "Photo uploaded",
                "detail": _clean(row.get("caption")),
                "photo_url": _clean(row.get("photo_url")),
            }
        )

    events.sort(key=lambda e: _clean(e.get("when")), reverse=True)
    return events[:limit]


def list_trailer_photos(trailer_id: str, *, limit: int = 30) -> list[dict[str, Any]]:
    return _fetch_trailer_rows(_TRAILER_PHOTOS, _clean(trailer_id), limit=limit)


__all__ = [
    "AUDIT_ITEM_CONDITIONS",
    "AUDIT_ITEM_STATUSES",
    "INSPECTION_CHECKLIST",
    "REQUEST_PRIORITIES",
    "SPOT_AUDIT_CONDITIONS",
    "add_tool_to_trailer",
    "audit_item_requires_missing_note",
    "audit_item_requires_photo",
    "complete_spot_audit",
    "create_trailer_tool_request",
    "get_trailer_dashboard_summary",
    "get_trailer_history",
    "get_trailer_inventory_items",
    "list_trailer_photos",
    "map_spot_audit_condition",
    "normalize_audit_item_status",
    "remove_tool_from_trailer",
    "report_broken_trailer_tool",
    "save_trailer_inspection",
    "select_spot_audit_items",
    "transfer_trailer",
    "upload_audit_item_photo",
    "upload_trailer_photo",
    "validate_audit_item_line",
    "validate_audit_item_lines",
]
