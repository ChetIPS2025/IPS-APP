"""Recent QR scan activity from inventory and tool transaction logs."""

from __future__ import annotations

from typing import Any

try:
    from app.services.inventory_display_helpers import resolve_inventory_qr_value
    from app.services.inventory_service import normalize_inventory
    from app.services.job_service import job_row_select_label
    from app.services.repository import fetch_rows
    from app.services.tracking_terminology import (
        inventory_action_label,
        serialized_tool_action_label,
    )
except ImportError:
    from services.inventory_display_helpers import resolve_inventory_qr_value  # type: ignore
    from services.inventory_service import normalize_inventory  # type: ignore
    from services.job_service import job_row_select_label  # type: ignore
    from services.repository import fetch_rows  # type: ignore
    from services.tracking_terminology import (  # type: ignore
        inventory_action_label,
        serialized_tool_action_label,
    )

_INV_TXN = "inventory_transactions"
_TOOL_TXN = "tool_transactions"
_INV_ITEMS = "inventory_items"
_ASSETS = "assets"
_JOBS = "jobs"
_EMPLOYEES = "employees"


def _clean(raw: object) -> str:
    return str(raw or "").strip()


def _norm_type(raw: object) -> str:
    return _clean(raw).upper().replace("-", "_")


def _is_qr_inventory_scan(row: dict[str, Any]) -> bool:
    source = _clean(row.get("source")).casefold()
    if source == "qr_scan":
        return True
    if row.get("scanned_by_name") or row.get("device_label") or row.get("scanned_by_user_id"):
        return True
    if _clean(row.get("destination_type")).casefold() in {"shop", "job"}:
        return True
    if _clean(row.get("device_info")):
        return True
    return False


def _job_shop_label(
    *,
    job_id: str,
    destination_type: str,
    jobs_by_id: dict[str, dict[str, Any]],
) -> str:
    dest = _clean(destination_type).casefold()
    if dest == "shop":
        return "Shop"
    if job_id and job_id in jobs_by_id:
        return job_row_select_label(jobs_by_id[job_id])
    if job_id:
        return job_id[:8] + "…"
    if dest == "job":
        return "Job"
    return "—"


def _device_source(row: dict[str, Any]) -> str:
    parts: list[str] = []
    device = _clean(row.get("device_label") or row.get("device_info"))
    source = _clean(row.get("source"))
    if device:
        parts.append(device)
    if source and source.casefold() not in {"", "qr_scan", "job_materials", "inventory_detail"}:
        parts.append(source)
    elif source.casefold() == "qr_scan":
        parts.append("QR scan")
    return " · ".join(parts) if parts else "QR scan"


def _inventory_scan_record(
    row: dict[str, Any],
    *,
    items_by_id: dict[str, dict[str, Any]],
    jobs_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    iid = _clean(row.get("inventory_item_id"))
    item = items_by_id.get(iid, {})
    name = _clean(item.get("name") or item.get("item_name")) or "Unknown item"
    qr_value = resolve_inventory_qr_value(item) if item else "—"
    txn_type = _norm_type(row.get("transaction_type") or row.get("txn_type"))
    action = inventory_action_label(txn_type)
    jid = _clean(row.get("job_id"))
    dest = _clean(row.get("destination_type"))
    who = _clean(row.get("scanned_by_name") or row.get("created_by")) or "—"
    return {
        "scanned_at": row.get("created_at"),
        "qr_value": qr_value or "—",
        "item_name": name,
        "item_type": "Inventory",
        "result": "Success",
        "job_shop": _job_shop_label(job_id=jid, destination_type=dest, jobs_by_id=jobs_by_id),
        "scanned_by": who,
        "device_source": _device_source(row),
        "action_taken": action,
        "_sort_ts": _clean(row.get("created_at")),
    }


def _tool_scan_record(
    row: dict[str, Any],
    *,
    assets_by_id: dict[str, dict[str, Any]],
    jobs_by_id: dict[str, dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    tid = _clean(row.get("tool_id"))
    asset = assets_by_id.get(tid, {})
    name = _clean(asset.get("asset_name") or asset.get("name")) or "Unknown tool"
    qr_value = _clean(asset.get("qr_code_value") or asset.get("asset_id")) or "—"
    txn_type = _norm_type(row.get("transaction_type"))
    action = serialized_tool_action_label(txn_type)
    jid = _clean(row.get("job_id"))
    eid = _clean(row.get("employee_id"))
    emp = employees_by_id.get(eid, {})
    who = _clean(emp.get("name") or emp.get("full_name")) or "—"
    notes = _clean(row.get("notes"))
    device = notes if notes.lower().startswith("device") else "QR scan"
    return {
        "scanned_at": row.get("created_at"),
        "qr_value": qr_value,
        "item_name": name,
        "item_type": "Asset / Tool",
        "result": "Success",
        "job_shop": _job_shop_label(job_id=jid, destination_type="job" if jid else "", jobs_by_id=jobs_by_id),
        "scanned_by": who,
        "device_source": device,
        "action_taken": action,
        "_sort_ts": _clean(row.get("created_at")),
    }


def recent_qr_scans(
    *,
    limit: int = 25,
    inventory_item_id: str | None = None,
) -> list[dict[str, Any]]:
    """Last N QR scan events; falls back to transaction adapter when events table is empty."""
    try:
        from app.services.qr_scan_event_service import list_qr_scan_events
    except ImportError:
        from services.qr_scan_event_service import list_qr_scan_events  # type: ignore
    events = list_qr_scan_events(limit=limit, inventory_item_id=inventory_item_id)
    if events:
        return events
    return _recent_qr_scans_from_transactions(limit=limit, inventory_item_id=inventory_item_id)


def _recent_qr_scans_from_transactions(
    *,
    limit: int = 25,
    inventory_item_id: str | None = None,
) -> list[dict[str, Any]]:
    """Legacy adapter — inventory_transactions + tool_transactions (pre-migration)."""
    inv_txns, _ = fetch_rows(_INV_TXN, limit=120, order_by="created_at")
    tool_txns, _ = fetch_rows(_TOOL_TXN, limit=120, order_by="created_at")

    items_by_id: dict[str, dict[str, Any]] = {}
    inv_rows, _ = fetch_rows(_INV_ITEMS, limit=5000, order_by="item_name", alt_tables=("inventory",))
    for row in inv_rows:
        norm = normalize_inventory(row)
        iid = _clean(norm.get("id"))
        if iid:
            items_by_id[iid] = norm

    assets_by_id: dict[str, dict[str, Any]] = {}
    asset_rows, _ = fetch_rows(_ASSETS, limit=5000, order_by="asset_name", alt_tables=("asset_database",))
    for row in asset_rows:
        aid = _clean(row.get("id"))
        if aid:
            assets_by_id[aid] = row

    jobs_by_id: dict[str, dict[str, Any]] = {}
    job_rows, _ = fetch_rows(_JOBS, limit=5000)
    for row in job_rows:
        jid = _clean(row.get("id"))
        if jid:
            jobs_by_id[jid] = row

    employees_by_id: dict[str, dict[str, Any]] = {}
    emp_rows, _ = fetch_rows(_EMPLOYEES, limit=5000, order_by="name")
    for row in emp_rows:
        eid = _clean(row.get("id"))
        if eid:
            employees_by_id[eid] = row

    item_filter = _clean(inventory_item_id)
    events: list[dict[str, Any]] = []

    for row in inv_txns:
        if not _is_qr_inventory_scan(row):
            continue
        iid = _clean(row.get("inventory_item_id"))
        if item_filter and iid != item_filter:
            continue
        events.append(
            _inventory_scan_record(row, items_by_id=items_by_id, jobs_by_id=jobs_by_id)
        )

    if not item_filter:
        for row in tool_txns:
            events.append(
                _tool_scan_record(
                    row,
                    assets_by_id=assets_by_id,
                    jobs_by_id=jobs_by_id,
                    employees_by_id=employees_by_id,
                )
            )

    events.sort(key=lambda e: str(e.get("_sort_ts") or ""), reverse=True)
    out = events[:limit]
    for row in out:
        row.pop("_sort_ts", None)
    return out


__all__ = ["recent_qr_scans"]
