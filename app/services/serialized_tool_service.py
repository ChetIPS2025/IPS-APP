"""Serialized Milwaukee / cordless tool tracking in Tool Trailers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    from app.services.asset_kits_service import (
        ITEM_STATUSES,
        assign_asset_kit,
        asset_is_kit,
        create_asset_kit_audit,
        create_asset_kit_item,
        create_asset_kit_items_multi,
        create_asset_kit_transaction,
        get_asset_kit_items,
        update_asset_kit_item,
    )
    from app.services.assets_service import ensure_asset_qr_tokens
    from app.services.repository import ServiceResult, clear_all_data_caches, fetch_rows, insert_row, update_row
except ImportError:
    from services.asset_kits_service import (  # type: ignore
        ITEM_STATUSES,
        assign_asset_kit,
        asset_is_kit,
        create_asset_kit_audit,
        create_asset_kit_item,
        create_asset_kit_items_multi,
        create_asset_kit_transaction,
        get_asset_kit_items,
        update_asset_kit_item,
    )
    from services.assets_service import ensure_asset_qr_tokens  # type: ignore
    from services.repository import ServiceResult, clear_all_data_caches, fetch_rows, insert_row, update_row  # type: ignore

_ASSETS = "assets"
_TOOL_TXN = "tool_transactions"

SERIALIZED_TOOL_STATUSES = (
    "Available",
    "In Service",
    "Checked Out",
    "Assigned",
    "Missing",
    "Damaged",
    "Out of Service",
    "In Repair",
    "Retired",
)

MILWAUKEE_TOOL_TYPES = (
    "Drill",
    "Impact",
    "Grinder",
    "Saw",
    "Rotary Hammer",
    "Light",
    "Charger",
    "Battery",
    "Other",
)

_PLACEHOLDER_VALUES = frozenset({"—", "-", "none", "null", ""})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(raw: object) -> str:
    return str(raw or "").strip()


def _clean_serial(raw: object) -> str:
    serial = _clean_text(raw)
    if serial.casefold() in _PLACEHOLDER_VALUES:
        return ""
    return serial


def _employee_name(employees_by_id: dict[str, dict[str, Any]], employee_id: object) -> str:
    eid = _clean_text(employee_id)
    if not eid:
        return ""
    emp = employees_by_id.get(eid) or {}
    return _clean_text(emp.get("name") or emp.get("full_name"))


def _job_label(jobs_by_id: dict[str, dict[str, Any]], job_id: object) -> str:
    jid = _clean_text(job_id)
    if not jid:
        return ""
    job = jobs_by_id.get(jid) or {}
    number = _clean_text(job.get("job_number"))
    name = _clean_text(job.get("job_name") or job.get("name"))
    if number and name:
        return f"{number} · {name}"
    return number or name


def _trailer_label(assets_by_id: dict[str, dict[str, Any]], trailer_id: object) -> str:
    tid = _clean_text(trailer_id)
    if not tid:
        return ""
    trailer = assets_by_id.get(tid) or {}
    number = _clean_text(trailer.get("asset_number"))
    name = _clean_text(trailer.get("asset_name") or trailer.get("name"))
    if number and name:
        return f"{number} · {name}"
    return number or name


def serialized_tool_view(
    row: dict[str, Any],
    *,
    assets_by_id: dict[str, dict[str, Any]] | None = None,
    employees_by_id: dict[str, dict[str, Any]] | None = None,
    jobs_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Normalize asset or enriched kit item into the serialized-tool field set."""
    assets_by_id = assets_by_id or {}
    employees_by_id = employees_by_id or {}
    jobs_by_id = jobs_by_id or {}

    if str(row.get("row_type") or "") == "kit_item":
        trailer_id = _clean_text(row.get("parent_asset_id"))
        holder_id = _clean_text(row.get("assigned_to_employee_id"))
        job_id = _clean_text(row.get("assigned_job_id") or row.get("job_id"))
        if not job_id:
            parent = assets_by_id.get(trailer_id) or {}
            job_id = _clean_text(parent.get("assigned_job_id"))
        return {
            "id": _clean_text(row.get("id")),
            "row_type": "kit_item",
            "asset_number": _clean_serial(row.get("serial_number")) or "—",
            "asset_name": _clean_text(row.get("item_name")) or "—",
            "category": _clean_text(row.get("category") or row.get("item_type") or "Tool"),
            "manufacturer": _clean_text(row.get("manufacturer") or "Milwaukee"),
            "model": _clean_text(row.get("model") or row.get("description") or ""),
            "serial_number": _clean_serial(row.get("serial_number")),
            "asset_type": _clean_text(row.get("item_type") or "Tool"),
            "status": _clean_text(row.get("status") or "Present"),
            "condition": _clean_text(row.get("condition") or "Good"),
            "current_location": _clean_text(row.get("parent_location") or row.get("location") or ""),
            "current_container_asset_id": trailer_id or None,
            "current_container_label": _trailer_label(assets_by_id, trailer_id) or _clean_text(row.get("parent_asset_name")),
            "current_job_id": job_id or None,
            "current_job_label": _job_label(jobs_by_id, job_id),
            "current_employee_id": holder_id or None,
            "current_operator": _clean_text(row.get("assigned_to_name")) or _employee_name(employees_by_id, holder_id),
            "last_seen_at": _clean_text(row.get("last_counted_at") or row.get("updated_at") or ""),
            "last_audited_at": _clean_text(row.get("last_counted_at") or ""),
            "notes": _clean_text(row.get("notes") or ""),
            "child_asset_id": _clean_text(row.get("child_asset_id")) or None,
            "parent_asset_id": trailer_id or None,
        }

    holder_id = _clean_text(row.get("current_holder_employee_id") or row.get("current_employee_id"))
    trailer_id = _clean_text(row.get("current_container_asset_id") or row.get("assigned_trailer_id"))
    job_id = _clean_text(row.get("assigned_job_id") or row.get("current_job_id"))
    operator = _clean_text(row.get("operator") or row.get("assigned_employee") or row.get("assigned_to_name"))
    if not operator and holder_id:
        operator = _employee_name(employees_by_id, holder_id)

    return {
        "id": _clean_text(row.get("id")),
        "row_type": "asset",
        "asset_number": _clean_text(row.get("asset_number") or row.get("asset_id") or ""),
        "asset_name": _clean_text(row.get("asset_name") or row.get("name") or "—"),
        "category": _clean_text(row.get("category") or row.get("asset_type") or "Tool"),
        "manufacturer": _clean_text(row.get("manufacturer") or ""),
        "model": _clean_text(row.get("model") or ""),
        "serial_number": _clean_serial(row.get("serial_number")),
        "asset_type": _clean_text(row.get("asset_type") or row.get("category") or "Tool"),
        "status": _clean_text(row.get("status") or "Available"),
        "condition": _clean_text(row.get("condition") or "Good"),
        "current_location": _clean_text(row.get("location") or ""),
        "current_container_asset_id": trailer_id or None,
        "current_container_label": _trailer_label(assets_by_id, trailer_id),
        "current_job_id": job_id or None,
        "current_job_label": _job_label(jobs_by_id, job_id),
        "current_employee_id": holder_id or None,
        "current_operator": operator,
        "last_seen_at": _clean_text(
            row.get("last_seen_at") or row.get("last_checkout_at") or row.get("last_checkin_at") or ""
        ),
        "last_audited_at": _clean_text(row.get("last_audited_at") or row.get("last_kit_audit_at") or ""),
        "notes": _clean_text(row.get("notes") or row.get("description") or ""),
        "is_serialized_tool": bool(row.get("is_serialized_tool") or row.get("is_checkout_item")),
        "is_checkout_item": bool(row.get("is_checkout_item")),
        "child_asset_id": None,
        "parent_asset_id": trailer_id or None,
    }


def is_serialized_tool_asset(asset: dict[str, Any]) -> bool:
    """True for individually serial-tracked tools (not quantity hand tools)."""
    try:
        from app.services.asset_classification_service import is_serialized_tab_asset
    except ImportError:
        from services.asset_classification_service import is_serialized_tab_asset  # type: ignore
    return is_serialized_tab_asset(asset)


def _find_kit_item_for_child(parent_asset_id: str, child_asset_id: str) -> dict[str, Any] | None:
    for item in get_asset_kit_items(parent_asset_id):
        if _clean_text(item.get("child_asset_id")) == child_asset_id:
            return item
    return None


def _sync_kit_item_for_tool(
    tool_id: str,
    trailer_id: str,
    *,
    tool_row: dict[str, Any],
    status: str = "Present",
) -> ServiceResult | None:
    existing = _find_kit_item_for_child(trailer_id, tool_id)
    if existing:
        return update_asset_kit_item(
            str(existing.get("id")),
            {
                "status": status,
                "serial_number": _clean_serial(tool_row.get("serial_number")),
                "item_name": _clean_text(tool_row.get("asset_name")),
                "manufacturer": _clean_text(tool_row.get("manufacturer")),
                "model": _clean_text(tool_row.get("model")),
                "child_asset_id": tool_id,
            },
        )
    return create_asset_kit_item(
        trailer_id,
        {
            "item_name": _clean_text(tool_row.get("asset_name")),
            "item_type": "Tool",
            "category": _clean_text(tool_row.get("category") or "Tool"),
            "serial_number": _clean_serial(tool_row.get("serial_number")),
            "child_asset_id": tool_id,
            "quantity_expected": 1,
            "quantity_actual": 1,
            "status": status,
            "condition": _clean_text(tool_row.get("condition") or "Good"),
            "unit_value": float(tool_row.get("current_value") or tool_row.get("value") or 0),
            "description": _clean_text(tool_row.get("model")),
        },
    )


def create_serialized_tool(data: dict[str, Any]) -> ServiceResult:
    """Create a Milwaukee-style serialized tool asset; optionally link to a Tool Trailer."""
    serial = _clean_serial(data.get("serial_number"))
    name = _clean_text(data.get("asset_name") or data.get("name"))
    if not name:
        return ServiceResult(ok=False, error="Tool name is required.")
    if not serial:
        return ServiceResult(ok=False, error="Serial number is required for serialized tools.")

    trailer_id = _clean_text(data.get("current_container_asset_id") or data.get("trailer_id"))
    if trailer_id:
        try:
            from app.services.repository import fetch_by_id
        except ImportError:
            from services.repository import fetch_by_id  # type: ignore
        trailer = fetch_by_id(_ASSETS, trailer_id) or {}
        if not asset_is_kit(trailer):
            return ServiceResult(ok=False, error="Selected container is not a Tool Trailer / kit.")

    asset_tag = _clean_text(data.get("asset_number")) or _clean_text(data.get("asset_id"))
    if not asset_tag:
        try:
            from app.services.asset_service import next_asset_id
        except ImportError:
            from services.asset_service import next_asset_id  # type: ignore
        existing_assets, _ = fetch_rows(_ASSETS, limit=5000, order_by="asset_id")
        asset_tag = next_asset_id(existing_assets)

    payload = {
        "asset_name": name,
        "asset_id": asset_tag,
        "category": _clean_text(data.get("category") or data.get("asset_type") or "Tool"),
        "asset_type": _clean_text(data.get("asset_type") or data.get("category") or "Tool"),
        "manufacturer": _clean_text(data.get("manufacturer") or "Milwaukee"),
        "model": _clean_text(data.get("model") or ""),
        "serial_number": serial,
        "status": _clean_text(data.get("status") or "Available"),
        "condition": _clean_text(data.get("condition") or "Good"),
        "location": _clean_text(data.get("current_location") or data.get("location") or "Tool Trailer"),
        "notes": _clean_text(data.get("notes") or ""),
        "description": _clean_text(data.get("notes") or ""),
        "is_serialized_tool": True,
        "is_checkout_item": True,
        "tracking_type": "serialized",
        "current_container_asset_id": trailer_id or None,
        "assigned_trailer_id": trailer_id or None,
        "assigned_job_id": data.get("current_job_id") or data.get("assigned_job_id"),
        "last_seen_at": _now_iso(),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    result = insert_row(_ASSETS, payload)
    if not result.ok:
        return result

    tool_id = str((result.data or {}).get("id") or "")
    if tool_id:
        ensure_asset_qr_tokens([result.data or {}])
        if trailer_id:
            kit_result = _sync_kit_item_for_tool(tool_id, trailer_id, tool_row=result.data or payload)
            if not kit_result or not kit_result.ok:
                warning = (kit_result.error if kit_result else "Could not link tool to trailer.")
                return ServiceResult(ok=True, data={**(result.data or {}), "warning": warning})
    clear_all_data_caches()
    return result


def assign_tool_to_trailer(tool_id: str, trailer_id: str) -> ServiceResult:
    tid = _clean_text(tool_id)
    pid = _clean_text(trailer_id)
    if not tid or not pid:
        return ServiceResult(ok=False, error="Tool and Tool Trailer are required.")

    try:
        from app.services.repository import fetch_by_id
    except ImportError:
        from services.repository import fetch_by_id  # type: ignore

    tool = fetch_by_id(_ASSETS, tid) or {}
    trailer = fetch_by_id(_ASSETS, pid) or {}
    if not tool:
        return ServiceResult(ok=False, error="Tool not found.")
    if not asset_is_kit(trailer):
        return ServiceResult(ok=False, error="Container must be a Tool Trailer / kit.")

    trailer_loc = _clean_text(trailer.get("location"))
    result = update_row(
        _ASSETS,
        {
            "current_container_asset_id": pid,
            "assigned_trailer_id": pid,
            "location": trailer_loc or _clean_text(tool.get("location")),
            "last_seen_at": _now_iso(),
        },
        {"id": tid},
    )
    if not result.ok:
        return result

    kit_result = _sync_kit_item_for_tool(tid, pid, tool_row=tool)
    if kit_result and not kit_result.ok:
        return ServiceResult(ok=False, error=kit_result.error or "Tool saved but trailer link failed.")
    clear_all_data_caches()
    return ServiceResult(ok=True, data={"tool_id": tid, "trailer_id": pid})


def dispatch_trailer_to_job(
    trailer_id: str,
    *,
    job_id: str | None = None,
    employee_id: str | None = None,
    employee_name: str = "",
    performed_by_name: str = "",
    notes: str = "",
) -> ServiceResult:
    """Assign trailer to a job and propagate job context to serialized tools inside."""
    pid = _clean_text(trailer_id)
    if not pid:
        return ServiceResult(ok=False, error="Tool Trailer is required.")

    result = assign_asset_kit(
        pid,
        {
            "job_id": job_id,
            "assigned_job_id": job_id,
            "assigned_to_employee_id": employee_id,
            "assigned_to_name": employee_name,
            "performed_by_name": performed_by_name,
            "notes": notes,
        },
    )
    if not result.ok:
        return result

    if job_id:
        for item in get_asset_kit_items(pid):
            child_id = _clean_text(item.get("child_asset_id"))
            if child_id:
                update_row(
                    _ASSETS,
                    {
                        "assigned_job_id": job_id,
                        "last_seen_at": _now_iso(),
                        "status": "Assigned",
                    },
                    {"id": child_id},
                )
            else:
                update_asset_kit_item(
                    str(item.get("id")),
                    {"status": "Present"},
                )
    clear_all_data_caches()
    return result


def checkout_serialized_tool(
    tool_id: str,
    *,
    employee_id: str,
    employee_name: str = "",
    job_id: str | None = None,
    notes: str = "",
) -> ServiceResult:
    tid = _clean_text(tool_id)
    eid = _clean_text(employee_id)
    if not tid or not eid:
        return ServiceResult(ok=False, error="Tool and employee are required.")

    ts = _now_iso()
    payload = {
        "status": "Checked Out",
        "current_holder_employee_id": eid,
        "assigned_employee": employee_name[:500] if employee_name else None,
        "assigned_job_id": job_id,
        "last_checkout_at": ts,
        "last_seen_at": ts,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    result = update_row(_ASSETS, payload, {"id": tid})
    if not result.ok:
        return result

    insert_row(
        _TOOL_TXN,
        {
            "tool_id": tid,
            "transaction_type": "CHECK_OUT",
            "employee_id": eid,
            "job_id": job_id,
            "notes": notes,
        },
    )

    trailer_id = _clean_text((result.data or {}).get("current_container_asset_id"))
    if trailer_id:
        kit_item = _find_kit_item_for_child(trailer_id, tid)
        if kit_item:
            update_asset_kit_item(
                str(kit_item.get("id")),
                {
                    "status": "Checked Out",
                    "assigned_to_employee_id": eid,
                    "assigned_to_name": employee_name,
                },
            )
    clear_all_data_caches()
    return result


def checkin_serialized_tool(tool_id: str, *, notes: str = "") -> ServiceResult:
    tid = _clean_text(tool_id)
    if not tid:
        return ServiceResult(ok=False, error="Tool id is required.")

    ts = _now_iso()
    result = update_row(
        _ASSETS,
        {
            "status": "Available",
            "current_holder_employee_id": None,
            "assigned_employee": "",
            "last_checkin_at": ts,
            "last_seen_at": ts,
        },
        {"id": tid},
    )
    if not result.ok:
        return result

    insert_row(
        _TOOL_TXN,
        {
            "tool_id": tid,
            "transaction_type": "CHECK_IN",
            "notes": notes,
        },
    )

    trailer_id = _clean_text((result.data or {}).get("current_container_asset_id"))
    if trailer_id:
        kit_item = _find_kit_item_for_child(trailer_id, tid)
        if kit_item:
            update_asset_kit_item(
                str(kit_item.get("id")),
                {
                    "status": "Present",
                    "assigned_to_employee_id": None,
                    "assigned_to_name": "",
                },
            )
    clear_all_data_caches()
    return result


def mark_serialized_tool_status(
    tool_id: str,
    *,
    status: str,
    condition: str | None = None,
    notes: str = "",
) -> ServiceResult:
    tid = _clean_text(tool_id)
    if not tid:
        return ServiceResult(ok=False, error="Tool id is required.")
    stat = _clean_text(status)
    if not stat:
        return ServiceResult(ok=False, error="Status is required.")

    payload: dict[str, Any] = {"status": stat, "last_seen_at": _now_iso()}
    if condition:
        payload["condition"] = _clean_text(condition)
    if notes:
        payload["notes"] = _clean_text(notes)
    if stat.casefold() in {"missing", "lost"}:
        payload["condition"] = condition or "Missing"
    if stat.casefold() in {"damaged", "out of service", "in repair"}:
        payload["condition"] = condition or stat

    result = update_row(_ASSETS, payload, {"id": tid})
    if not result.ok:
        return result

    trailer_id = _clean_text((result.data or {}).get("current_container_asset_id"))
    if trailer_id:
        kit_item = _find_kit_item_for_child(trailer_id, tid)
        if kit_item:
            kit_status = stat if stat in ITEM_STATUSES else (
                "Missing" if stat.casefold() in {"missing", "lost"} else "Damaged"
            )
            update_asset_kit_item(
                str(kit_item.get("id")),
                {
                    "status": kit_status,
                    "condition": payload.get("condition") or _clean_text(kit_item.get("condition")),
                },
            )
    clear_all_data_caches()
    return result


def audit_trailer_tools(
    trailer_id: str,
    audit_data: dict[str, Any],
    audit_items: list[dict[str, Any]],
) -> ServiceResult:
    """End-of-job trailer audit — verify every serial-numbered tool."""
    result = create_asset_kit_audit(trailer_id, audit_data, audit_items)
    if not result.ok:
        return result

    ts = _now_iso()
    for item in get_asset_kit_items(trailer_id):
        child_id = _clean_text(item.get("child_asset_id"))
        if not child_id:
            continue
        stat = _clean_text(item.get("status") or "Present")
        asset_status = "Available"
        if stat.casefold() == "missing":
            asset_status = "Missing"
        elif stat.casefold() == "damaged":
            asset_status = "Damaged"
        elif stat.casefold() == "checked out":
            asset_status = "Checked Out"
        update_row(
            _ASSETS,
            {
                "status": asset_status,
                "condition": _clean_text(item.get("condition") or "Good"),
                "last_audited_at": ts,
                "last_seen_at": ts,
            },
            {"id": child_id},
        )
    clear_all_data_caches()
    return result


def import_serialized_tools(rows: list[dict[str, Any]], *, trailer_id: str = "") -> ServiceResult:
    created = 0
    errors: list[str] = []
    for idx, row in enumerate(rows, start=1):
        data = {
            **row,
            "current_container_asset_id": _clean_text(row.get("trailer_id") or trailer_id) or None,
        }
        result = create_serialized_tool(data)
        if result.ok:
            created += 1
        else:
            errors.append(f"Row {idx}: {result.error or 'failed'}")
    if created == 0 and errors:
        return ServiceResult(ok=False, error="; ".join(errors[:5]))
    return ServiceResult(
        ok=True,
        data={"created": created, "errors": errors},
    )


__all__ = [
    "MILWAUKEE_TOOL_TYPES",
    "SERIALIZED_TOOL_STATUSES",
    "assign_tool_to_trailer",
    "audit_trailer_tools",
    "checkin_serialized_tool",
    "checkout_serialized_tool",
    "create_serialized_tool",
    "dispatch_trailer_to_job",
    "import_serialized_tools",
    "is_serialized_tool_asset",
    "mark_serialized_tool_status",
    "serialized_tool_view",
]
