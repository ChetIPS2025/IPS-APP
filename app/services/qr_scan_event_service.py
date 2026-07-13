"""QR scan event log — separate from inventory/tool stock transactions."""

from __future__ import annotations

import logging
from typing import Any, Literal

_LOG = logging.getLogger(__name__)

_TABLE = "qr_scan_events"

QrScanResult = Literal["opened", "success", "failed", "unknown_item"]
QrItemType = Literal["inventory", "asset", "unknown"]

_RESULT_LABELS = {
    "opened": "Opened",
    "success": "Success",
    "failed": "Failed",
    "unknown_item": "Unknown item",
}


def qr_scan_result_label(result: str) -> str:
    key = str(result or "").strip().lower()
    return _RESULT_LABELS.get(key, key.replace("_", " ").title() or "—")


def qr_scan_summary_line(
    *,
    scanned_by_name: object,
    scanned_at: object,
    job_shop: object,
    item_name: object,
) -> str:
    """Display: ``Amanda • 2026-07-08 17:05 • J26101 — I/E Labor``."""
    from app.utils.formatting import fmt_datetime
    who = _clean(scanned_by_name) or "—"
    when = fmt_datetime(scanned_at, compact=True)
    job = _clean(job_shop)
    item = _clean(item_name) or "—"
    tail = f"{job} — {item}" if job and job != "—" else item
    return f"{who} • {when} • {tail}"


def _clean(raw: object) -> str:
    return str(raw or "").strip()


def record_qr_scan_event(
    *,
    qr_value: str,
    result: QrScanResult,
    item_type: QrItemType = "unknown",
    item_name: str = "",
    inventory_item_id: str | None = None,
    asset_id: str | None = None,
    action_taken: str | None = None,
    job_id: str | None = None,
    destination_type: str | None = None,
    scanned_by_user_id: str | None = None,
    scanned_by_name: str | None = None,
    scanned_by_phone: str | None = None,
    employee_id: str | None = None,
    device_label: str | None = None,
    source: str = "qr_scan",
    error_message: str | None = None,
    inventory_transaction_id: str | None = None,
    tool_transaction_id: str | None = None,
    quantity: float | None = None,
    unit: str | None = None,
) -> bool:
    """Persist a QR scan event. Returns False if table missing or insert fails — never raises."""
    payload: dict[str, Any] = {
        "qr_value": (_clean(qr_value) or "—")[:500],
        "item_type": _clean(item_type) or "unknown",
        "item_name": (_clean(item_name) or "—")[:500],
        "result": _clean(result) or "opened",
        "source": (_clean(source) or "qr_scan")[:50],
    }
    if inventory_item_id:
        payload["inventory_item_id"] = inventory_item_id
    if asset_id:
        payload["asset_id"] = asset_id
    if action_taken:
        payload["action_taken"] = _clean(action_taken)[:200]
    if job_id:
        payload["job_id"] = job_id
    if destination_type:
        payload["destination_type"] = _clean(destination_type)[:20]
    if scanned_by_user_id:
        payload["scanned_by_user_id"] = _clean(scanned_by_user_id)[:200]
    if scanned_by_name:
        payload["scanned_by_name"] = _clean(scanned_by_name)[:500]
    if scanned_by_phone:
        payload["scanned_by_phone"] = _clean(scanned_by_phone)[:50]
    if employee_id:
        payload["employee_id"] = employee_id
    if device_label:
        payload["device_label"] = _clean(device_label)[:200]
    if error_message:
        payload["error_message"] = _clean(error_message)[:2000]
    if inventory_transaction_id:
        payload["inventory_transaction_id"] = inventory_transaction_id
    if tool_transaction_id:
        payload["tool_transaction_id"] = tool_transaction_id
    if quantity is not None:
        from app.utils.inventory_quantity import parse_inventory_quantity
        payload["quantity"] = parse_inventory_quantity(quantity, allow_zero=False, field_name="Quantity")
    if unit:
        payload["unit"] = _clean(unit)[:20]

    try:
        from app.db import insert_row_admin
        from app.services.repository import filter_payload_to_table
        filtered = filter_payload_to_table(_TABLE, payload)
        insert_row_admin(_TABLE, filtered)
        return True
    except Exception as exc:
        _LOG.debug("qr_scan_events insert skipped: %s", exc)
        return False


def list_qr_scan_events(
    *,
    limit: int = 25,
    inventory_item_id: str | None = None,
) -> list[dict[str, Any]]:
    """Read recent QR scan events for dashboard / inventory history."""
    from app.services.job_service import job_row_select_label
    from app.services.repository import fetch_rows
    rows, err = fetch_rows(_TABLE, limit=max(limit, 50), order_by="created_at")
    if err or not rows:
        return []

    jobs_by_id: dict[str, dict[str, Any]] = {}
    job_rows, _ = fetch_rows("jobs", limit=5000)
    for row in job_rows:
        jid = _clean(row.get("id"))
        if jid:
            jobs_by_id[jid] = row

    item_filter = _clean(inventory_item_id)
    out: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: _clean(r.get("created_at")), reverse=True):
        if item_filter and _clean(row.get("inventory_item_id")) != item_filter:
            continue
        result_key = _clean(row.get("result")).lower() or "opened"
        if result_key == "opened":
            continue
        jid = _clean(row.get("job_id"))
        dest = _clean(row.get("destination_type")).casefold()
        if dest == "shop":
            job_shop = "Shop"
        elif jid and jid in jobs_by_id:
            job_shop = job_row_select_label(jobs_by_id[jid])
        elif jid:
            job_shop = jid[:8] + "…"
        else:
            job_shop = "—"

        device = _clean(row.get("device_label"))
        source = _clean(row.get("source"))
        device_source = " · ".join(p for p in (device, source or "QR scan") if p) or "QR scan"

        scanned_by = _clean(row.get("scanned_by_name")) or "—"
        scanned_at = row.get("created_at")
        item_name = _clean(row.get("item_name")) or "—"
        out.append({
            "scanned_at": scanned_at,
            "qr_value": _clean(row.get("qr_value")) or "—",
            "item_name": item_name,
            "item_type": {
                "inventory": "Inventory",
                "asset": "Asset / Tool",
            }.get(_clean(row.get("item_type")).lower(), _clean(row.get("item_type")) or "Unknown"),
            "result": qr_scan_result_label(result_key),
            "job_shop": job_shop,
            "scanned_by": scanned_by,
            "scanned_by_user_id": _clean(row.get("scanned_by_user_id")) or "",
            "device_source": device_source,
            "device_label": device,
            "action_taken": _clean(row.get("action_taken")) or "—",
            "summary": qr_scan_summary_line(
                scanned_by_name=scanned_by,
                scanned_at=scanned_at,
                job_shop=job_shop,
                item_name=item_name,
            ),
            "_sort_ts": _clean(row.get("created_at")),
        })
        if len(out) >= limit:
            break
    for row in out:
        row.pop("_sort_ts", None)
    return out


__all__ = [
    "list_qr_scan_events",
    "qr_scan_result_label",
    "qr_scan_summary_line",
    "record_qr_scan_event",
]
