"""Quantity-based small hand tools — no serial number required."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.asset_kits_service import asset_is_kit, get_asset_kit_items, list_all_kit_items_enriched
from app.services.repository import (
    ServiceResult,
    delete_row,
    fetch_rows,
    insert_row,
    insert_row_admin,
    update_row,
)
_TABLE = "small_hand_tools"

HAND_TOOL_CATEGORIES = (
    "Pliers",
    "Screwdrivers",
    "Wrenches",
    "Clamps",
    "Hammers",
    "Tape Measures",
    "Levels",
    "Sockets",
    "Cutters",
    "Other",
)

STORAGE_TYPES = ("Tool Trailer", "Shop", "Warehouse", "Job Site")

HAND_TOOL_STATUSES = ("Available", "In Use", "Low Stock", "Missing", "Damaged", "Out of Service", "Retired")

HAND_TOOL_CONDITIONS = ("New", "Good", "Fair", "Damaged", "Needs Repair", "Missing", "Retired")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _f(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _clean_text(raw: object) -> str:
    return str(raw or "").strip()


def _has_serial(raw: object) -> bool:
    serial = _clean_text(raw)
    return bool(serial and serial not in {"—", "-", "none", "null"})


def normalize_hand_tool(row: dict[str, Any]) -> dict[str, Any]:
    qty = _f(row.get("quantity_on_hand") or row.get("quantity_actual") or row.get("quantity") or 0)
    exp = _f(row.get("quantity_expected") or qty)
    unit_val = _f(row.get("unit_value") or 0)
    storage = _clean_text(row.get("storage_type") or "Warehouse") or "Warehouse"
    return {
        "id": _clean_text(row.get("id")),
        "row_type": str(row.get("row_type") or "hand_tool"),
        "tool_name": _clean_text(row.get("tool_name") or row.get("item_name") or "—"),
        "category": _clean_text(row.get("category") or "Other") or "Other",
        "model_number": _clean_text(row.get("model_number") or ""),
        "serial_number": _clean_text(row.get("serial_number") or ""),
        "description": _clean_text(row.get("description") or ""),
        "quantity_on_hand": qty,
        "quantity_expected": exp,
        "unit": _clean_text(row.get("unit") or "EA") or "EA",
        "unit_value": unit_val,
        "total_value": _f(row.get("total_value") or qty * unit_val),
        "storage_type": storage,
        "container_asset_id": _clean_text(row.get("container_asset_id") or row.get("parent_asset_id")) or None,
        "container_label": _clean_text(row.get("container_label") or row.get("parent_asset_name") or ""),
        "storage_location": _clean_text(row.get("storage_location") or row.get("parent_location") or ""),
        "assigned_job_id": _clean_text(row.get("assigned_job_id") or row.get("job_id")) or None,
        "job_label": _clean_text(row.get("job_label") or ""),
        "status": _clean_text(row.get("status") or "Available") or "Available",
        "condition": _clean_text(row.get("condition") or "Good") or "Good",
        "notes": _clean_text(row.get("notes") or ""),
        "is_active": row.get("is_active") is not False,
        "editable": row.get("row_type") != "kit_item",
        "kit_item_id": _clean_text(row.get("kit_item_id") or (row.get("id") if row.get("row_type") == "kit_item" else "")) or None,
        "source_asset_id": _clean_text(row.get("source_asset_id")) or None,
    }


def _job_label_from_map(jobs_by_id: dict[str, dict[str, Any]], job_id: object) -> str:
    jid = _clean_text(job_id)
    if not jid:
        return ""
    job = jobs_by_id.get(jid) or {}
    number = _clean_text(job.get("job_number"))
    name = _clean_text(job.get("job_name") or job.get("name"))
    if number and name:
        return f"{number} · {name}"
    return number or name


def _container_label_from_map(assets_by_id: dict[str, dict[str, Any]], container_id: object) -> str:
    cid = _clean_text(container_id)
    if not cid:
        return ""
    asset = assets_by_id.get(cid) or {}
    number = _clean_text(asset.get("asset_number"))
    name = _clean_text(asset.get("asset_name") or asset.get("name"))
    if number and name:
        return f"{number} · {name}"
    return number or name


def _location_display(tool: dict[str, Any]) -> str:
    storage = _clean_text(tool.get("storage_type"))
    if storage == "Tool Trailer":
        return tool.get("container_label") or tool.get("storage_location") or "Tool Trailer"
    if storage == "Job Site":
        return tool.get("job_label") or tool.get("storage_location") or "Job Site"
    loc = _clean_text(tool.get("storage_location"))
    return loc or storage or "—"


def list_hand_tools(
    *,
    assets_by_id: dict[str, dict[str, Any]] | None = None,
    jobs_by_id: dict[str, dict[str, Any]] | None = None,
    include_kit_items: bool = True,
) -> list[dict[str, Any]]:
    """All quantity small tools from DB plus non-serialized kit lines in trailers."""
    if assets_by_id is None:
        from app.services.phase2_modules_service import list_assets, normalize_asset
        assets_by_id = {
            str(a.get("id") or "").strip(): normalize_asset(a)
            for a in list_assets()
            if str(a.get("id") or "").strip()
        }
    if jobs_by_id is None:
        from app.pages._core._data import load_jobs
        jobs_by_id = {
            str(j.get("id") or "").strip(): j for j in load_jobs() if str(j.get("id") or "").strip()
        }

    out: list[dict[str, Any]] = []
    rows, _ = fetch_rows(_TABLE, limit=10000, order_by="tool_name")
    for row in rows or []:
        if not isinstance(row, dict) or row.get("is_active") is False:
            continue
        norm = normalize_hand_tool({**row, "row_type": "hand_tool"})
        cid = norm.get("container_asset_id")
        jid = norm.get("assigned_job_id")
        if cid:
            norm["container_label"] = _container_label_from_map(assets_by_id, cid)
        if jid:
            norm["job_label"] = _job_label_from_map(jobs_by_id, jid)
        norm["location_display"] = _location_display(norm)
        out.append(norm)

    if include_kit_items:
        for item in list_all_kit_items_enriched(assets_by_id):
            if _has_serial(item.get("serial_number")):
                continue
            if _clean_text(item.get("child_asset_id")):
                continue
            parent_id = _clean_text(item.get("parent_asset_id"))
            parent = assets_by_id.get(parent_id) or {}
            norm = normalize_hand_tool(
                {
                    **item,
                    "row_type": "kit_item",
                    "tool_name": item.get("item_name"),
                    "quantity_on_hand": item.get("quantity_actual") or item.get("quantity_expected"),
                    "quantity_expected": item.get("quantity_expected"),
                    "storage_type": "Tool Trailer",
                    "container_asset_id": parent_id,
                    "container_label": _container_label_from_map(assets_by_id, parent_id),
                    "storage_location": _clean_text(item.get("parent_location") or parent.get("location")),
                    "assigned_job_id": parent.get("assigned_job_id"),
                    "job_label": _job_label_from_map(jobs_by_id, parent.get("assigned_job_id")),
                    "kit_item_id": item.get("id"),
                    "editable": False,
                }
            )
            norm["location_display"] = _location_display(norm)
            out.append(norm)

    return sorted(out, key=lambda r: (str(r.get("tool_name") or "").casefold(), str(r.get("location_display") or "")))


def _hand_tool_payload_from_ui(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    """Build validated DB payload for insert/update; returns error ServiceResult on validation failure."""
    name = _clean_text(ui.get("tool_name"))
    if not name:
        return ServiceResult(ok=False, error="Tool name is required.")

    storage = _clean_text(ui.get("storage_type") or "Warehouse") or "Warehouse"
    container_id = _clean_text(ui.get("container_asset_id"))
    if storage == "Tool Trailer" and container_id:
        parent = None
        from app.services.repository import fetch_by_id
        parent = fetch_by_id("assets", container_id) or {}
        if parent and not asset_is_kit(parent):
            return ServiceResult(ok=False, error="Selected container is not a Tool Trailer / kit.")

    qty = max(0.0, _f(ui.get("quantity_on_hand")))
    payload: dict[str, Any] = {
        "tool_name": name,
        "category": _clean_text(ui.get("category") or "Other") or "Other",
        "model_number": _clean_text(ui.get("model_number") or ""),
        "serial_number": _clean_text(ui.get("serial_number") or ""),
        "description": _clean_text(ui.get("description") or ""),
        "quantity_on_hand": qty,
        "quantity_expected": max(0.0, _f(ui.get("quantity_expected") or qty)),
        "unit": _clean_text(ui.get("unit") or "EA") or "EA",
        "unit_value": max(0.0, _f(ui.get("unit_value"))),
        "storage_type": storage,
        "container_asset_id": container_id or None if storage == "Tool Trailer" else None,
        "storage_location": _clean_text(ui.get("storage_location") or ""),
        "assigned_job_id": _clean_text(ui.get("assigned_job_id")) or None,
        "status": _clean_text(ui.get("status") or "Available") or "Available",
        "condition": _clean_text(ui.get("condition") or "Good") or "Good",
        "notes": _clean_text(ui.get("notes") or ""),
        "is_active": True,
        "updated_at": _now_iso(),
    }
    source_asset_id = _clean_text(ui.get("source_asset_id"))
    if source_asset_id:
        payload["source_asset_id"] = source_asset_id
    if qty <= 0 and _clean_text(ui.get("status") or "Available") == "Available":
        payload["status"] = "Low Stock" if qty == 0 else payload["status"]

    return ServiceResult(ok=True, data={"payload": payload, "storage": storage, "container_id": container_id})


def save_hand_tool(ui: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    built = _hand_tool_payload_from_ui(ui, row_id=row_id)
    if not built.ok:
        return built
    data = built.data or {}
    payload = data.get("payload") or {}
    storage = data.get("storage") or "Warehouse"
    container_id = data.get("container_id") or ""

    if row_id:
        result = update_row(_TABLE, payload, {"id": row_id})
    else:
        payload["created_at"] = _now_iso()
        result = insert_row(_TABLE, payload)

    if result.ok and storage == "Tool Trailer" and container_id:
        _sync_kit_item_for_hand_tool(container_id, result.data or payload, row_id=row_id)
    return result


def import_hand_tool_row(ui: dict[str, Any]) -> ServiceResult:
    """Server-side insert for CSV bulk import (service role; avoids stale user JWT)."""
    built = _hand_tool_payload_from_ui(ui)
    if not built.ok:
        return built
    data = built.data or {}
    payload = data.get("payload") or {}
    storage = data.get("storage") or "Warehouse"
    container_id = data.get("container_id") or ""
    payload["created_at"] = _now_iso()
    result = insert_row_admin(_TABLE, payload)
    if result.ok and storage == "Tool Trailer" and container_id:
        row_id = _clean_text((result.data or {}).get("id"))
        _sync_kit_item_for_hand_tool(container_id, result.data or payload, row_id=row_id or None)
    return result


def _sync_kit_item_for_hand_tool(
    trailer_id: str,
    tool_row: dict[str, Any],
    *,
    row_id: str | None,
) -> None:
    """Mirror quantity hand tool into trailer kit inventory for audits."""
    from app.services.asset_kits_service import create_asset_kit_item, update_asset_kit_item
    name = _clean_text(tool_row.get("tool_name"))
    qty = _f(tool_row.get("quantity_on_hand") or 1, 1.0)
    hand_id = _clean_text(row_id or tool_row.get("id"))
    existing = None
    for item in get_asset_kit_items(trailer_id):
        if _clean_text(item.get("notes")).endswith(f"hand_tool:{hand_id}"):
            existing = item
            break
        if not _has_serial(item.get("serial_number")) and _clean_text(item.get("item_name")).casefold() == name.casefold():
            if hand_id and f"hand_tool:{hand_id}" in _clean_text(item.get("notes")):
                existing = item

    data = {
        "item_name": name,
        "item_type": "Tool",
        "category": _clean_text(tool_row.get("category") or "Other"),
        "description": _clean_text(tool_row.get("description") or ""),
        "quantity_expected": qty,
        "quantity_actual": qty,
        "unit_value": _f(tool_row.get("unit_value")),
        "condition": _clean_text(tool_row.get("condition") or "Good"),
        "status": "Present",
        "notes": f"{_clean_text(tool_row.get('notes'))} hand_tool:{hand_id}".strip(),
    }
    if existing:
        update_asset_kit_item(str(existing.get("id")), data)
    else:
        create_asset_kit_item(trailer_id, data)


def adjust_hand_tool_quantity(tool_id: str, delta: float, *, notes: str = "") -> ServiceResult:
    tid = _clean_text(tool_id)
    if not tid:
        return ServiceResult(ok=False, error="Tool id is required.")
    rows, _ = fetch_rows(_TABLE, limit=1)
    _ = rows
    from app.services.repository import fetch_by_id
    row = fetch_by_id(_TABLE, tid)
    if not row:
        return ServiceResult(ok=False, error="Hand tool not found.")
    new_qty = max(0.0, _f(row.get("quantity_on_hand")) + _f(delta))
    status = _clean_text(row.get("status") or "Available")
    if new_qty == 0 and status == "Available":
        status = "Low Stock"
    elif new_qty > 0 and status == "Low Stock":
        status = "Available"
    note_text = _clean_text(row.get("notes"))
    if notes:
        note_text = f"{note_text}\n{notes}".strip() if note_text else notes
    result = update_row(
        _TABLE,
        {
            "quantity_on_hand": new_qty,
            "status": status,
            "notes": note_text,
            "updated_at": _now_iso(),
        },
        {"id": tid},
    )
    if result.ok:
        cid = _clean_text(row.get("container_asset_id"))
        if cid:
            _sync_kit_item_for_hand_tool(cid, {**row, "quantity_on_hand": new_qty, "notes": note_text}, row_id=tid)
    return result


def delete_hand_tool(tool_id: str) -> ServiceResult:
    tid = _clean_text(tool_id)
    if not tid:
        return ServiceResult(ok=False, error="Tool id is required.")
    return update_row(_TABLE, {"is_active": False, "updated_at": _now_iso()}, {"id": tid})


__all__ = [
    "HAND_TOOL_CATEGORIES",
    "HAND_TOOL_CONDITIONS",
    "HAND_TOOL_STATUSES",
    "STORAGE_TYPES",
    "adjust_hand_tool_quantity",
    "delete_hand_tool",
    "list_hand_tools",
    "normalize_hand_tool",
    "import_hand_tool_row",
    "save_hand_tool",
]
