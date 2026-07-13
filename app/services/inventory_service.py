"""
Inventory module — Supabase reads/writes.

Schema assumptions: ``inventory_items`` (or ``inventory``) with sku, item_name, category,
storage_location, quantity_on_hand, reorder_point, unit_cost, vendor, status, image fields,
qr_token, quantity_checked_out, quantity_allocated.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

_DISPLAY_SKU_ID_RE = re.compile(r"^INV-([0-9A-F]{8})$", re.I)

from app.services.inventory_images import (
    clear_inventory_image_url_cache,
    get_inventory_image_url,
    inventory_has_image,
    upload_inventory_image as _upload_inventory_image_storage,
)
from app.services.phase2_modules_service import (
    delete_inventory_item,
    list_inventory,
    normalize_inventory,
    save_inventory_item,
)
from app.services.repository import ServiceResult, fetch_rows, insert_row, update_row

from app.utils.inventory_quantity import parse_inventory_quantity, try_parse_inventory_quantity
from app.services.inventory_display_helpers import resolve_inventory_qr_value, resolve_inventory_sku
from app.services.qr_codes import generate_inventory_qr_token, inventory_qr_link_url
from app.config import settings
_INV_TABLE = "inventory_items"
_TXN_TABLE = "inventory_transactions"

INVENTORY_TXN_TYPES = (
    "check_out",
    "check_in",
    "issue_to_job",
    "return_from_job",
    "consume_on_job",
    "consume_in_shop",
    "adjustment",
)

from app.services.tracking_terminology import (
    INVENTORY_ACTION_LABELS,
    inventory_action_label,
)
_JOB_REQUIRED_TYPES = frozenset({"issue_to_job", "return_from_job", "consume_on_job"})
_DECREASE_ON_HAND = frozenset({"check_out", "issue_to_job", "consume_on_job", "consume_in_shop"})


__all__ = [
    "INVENTORY_ACTION_LABELS",
    "INVENTORY_TXN_TYPES",
    "can_manage_inventory_actions",
    "clear_inventory_cache",
    "deactivate_inventory_item",
    "delete_inventory_item",
    "remove_inventory_keep_pricing_item",
    "ensure_inventory_qr_tokens",
    "generate_inventory_qr_value",
    "get_inventory",
    "get_inventory_image_url",
    "get_inventory_item",
    "get_inventory_item_by_qr",
    "get_inventory_transactions",
    "inventory_action_label",
    "inventory_has_image",
    "list_inventory",
    "normalize_inventory",
    "record_inventory_transaction",
    "record_shop_inventory_consumption",
    "save_inventory_item",
    "update_inventory_item",
    "upload_inventory_image",
]


def clear_inventory_cache() -> None:
    from app.perf_debug import perf_span
    with perf_span("inventory.clear_cache"):
        from app.services.repository import clear_data_cache_for_table
        clear_data_cache_for_table("inventory_items")
        clear_inventory_image_url_cache()
        try:
            from app.services.pricing_guide_images import clear_catalog_image_maps_cache

            clear_catalog_image_maps_cache()
        except ImportError:
            pass


def can_manage_inventory_actions() -> bool:
    """Admin, manager, or supervisor may deactivate or delete inventory items."""
    from app.components.modal_delete import can_admin_mutate
    return can_admin_mutate()


def deactivate_inventory_item(item_id: str) -> ServiceResult:
    """Mark an inventory item as Discontinued."""
    iid = str(item_id or "").strip()
    if not iid:
        return ServiceResult(ok=False, error="Missing inventory item id.")
    result = update_row(_INV_TABLE, {"status": "Discontinued"}, {"id": iid})
    if result.ok:
        clear_inventory_cache()
    return result


def _linked_pricing_item_ids(inventory_id: str, inventory_row: dict[str, Any] | None) -> set[str]:
    iid = str(inventory_id or "").strip()
    if not iid:
        return set()
    pg_ids: set[str] = set()
    if inventory_row:
        for key in ("pricing_guide_id", "pricing_item_id"):
            pid = str(inventory_row.get(key) or "").strip()
            if pid:
                pg_ids.add(pid)
    from app.db import fetch_table_admin
    try:
        pg_rows = list(fetch_table_admin("pricing_guide_items", limit=10000) or [])
    except Exception:
        pg_rows = []
    for row in pg_rows:
        if not isinstance(row, dict):
            continue
        link = str(row.get("linked_inventory_id") or row.get("inventory_item_id") or "").strip()
        if link != iid:
            continue
        pid = str(row.get("id") or "").strip()
        if pid:
            pg_ids.add(pid)
    return pg_ids


def remove_inventory_keep_pricing_item(item_id: str) -> ServiceResult:
    """Delete the stock record and keep linked pricing guide item(s) as Non-Inventory."""
    iid = str(item_id or "").strip()
    if not iid:
        return ServiceResult(ok=False, error="Missing inventory item id.")
    from app.pages._core._crud import is_demo_id
    if is_demo_id(iid):
        return ServiceResult(ok=False, error="Demo records cannot be removed.")

    inv = get_inventory_item(iid)
    if not inv:
        return ServiceResult(ok=False, error="Inventory item not found.")

    pg_ids = _linked_pricing_item_ids(iid, inv)
    from app.services.repository import update_row_admin
    updated: list[str] = []
    now = datetime.now(timezone.utc).isoformat()
    for pid in sorted(pg_ids):
        res = update_row_admin(
            "pricing_guide_items",
            {
                "inventory_item_id": None,
                "linked_inventory_id": None,
                "item_class": "Non-Inventory",
                "updated_at": now,
            },
            {"id": pid},
        )
        if not res.ok:
            return ServiceResult(ok=False, error=res.error or f"Could not update pricing guide item.")
        updated.append(pid)

    delete_result = delete_inventory_item(iid)
    if not delete_result.ok:
        return delete_result

    try:
        from app.services.pricing_guide_service import clear_pricing_guide_cache

        clear_pricing_guide_cache()
    except Exception:
        pass
    clear_inventory_cache()

    if updated:
        msg = (
            f"Removed from inventory. Kept {len(updated)} pricing guide item(s) "
            "as Non-Inventory for estimating."
        )
    else:
        msg = "Removed from inventory. No linked pricing guide item was found."
    return ServiceResult(ok=True, data={"pricing_item_ids": updated, "message": msg})


def get_inventory() -> list[dict[str, Any]]:
    from app.pages._core._data import _DEMO_INVENTORY
    rows, _ = list_inventory(demo=list(_DEMO_INVENTORY))
    return rows


def get_inventory_item(item_id: str) -> dict[str, Any] | None:
    iid = str(item_id or "").strip()
    if not iid:
        return None
    for row in get_inventory():
        if str(row.get("id") or "") == iid:
            return row
    return None


def update_inventory_item(item_id: str, data: dict[str, Any]) -> ServiceResult:
    result = save_inventory_item(data, row_id=str(item_id or "").strip())
    if result.ok:
        clear_inventory_cache()
    return result


def upload_inventory_image(item_id: str, uploaded_file: Any, *, uploaded_by: str | None = None) -> ServiceResult:
    result = _upload_inventory_image_storage(item_id, uploaded_file, uploaded_by=uploaded_by)
    if result.ok:
        clear_inventory_cache()
    return result


def _db_fetch_by_match(table: str, match: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    from app.db import fetch_by_match_admin
    try:
        return fetch_by_match_admin(table, match, limit=limit) or []
    except Exception:
        return []


def _row_to_item(row: dict[str, Any]) -> dict[str, Any]:
    return normalize_inventory(row)


def _ensure_item_qr_token(row: dict[str, Any]) -> str:
    token = str(row.get("qr_token") or "").strip()
    if token:
        return token
    iid = str(row.get("id") or "").strip()
    if not iid:
        return ""
    token = generate_inventory_qr_token()
    update_row(_INV_TABLE, {"qr_token": token}, {"id": iid})
    clear_inventory_cache()
    return token


def generate_inventory_qr_value(item: dict[str, Any]) -> str:
    """Build scan URL using APP_BASE_URL, item id, sku, and qr_token."""
    row = dict(item or {})
    if not row.get("qr_token"):
        row["qr_token"] = _ensure_item_qr_token(row)
    sku = resolve_inventory_sku(row)
    token = str(row.get("qr_token") or "").strip()
    iid = str(row.get("id") or "").strip()
    base = str(getattr(settings, "app_base_url", "") or "").strip().rstrip("/")
    if base and token and (iid or sku):
        return inventory_qr_link_url(sku=sku, qr_token=token, app_base_url=base, item_id=iid)
    qrv = resolve_inventory_qr_value(row)
    if base and qrv:
        from app.services.qr_codes import inventory_scan_link_url
        return inventory_scan_link_url(qr_code_value=qrv, app_base_url=base)
    return qrv


def ensure_inventory_qr_tokens(items: list[dict[str, Any]] | None = None) -> ServiceResult:
    """Generate and persist missing qr_token values without rotating existing tokens."""
    rows = items if items is not None else get_inventory()
    updated = 0
    for row in rows:
        iid = str(row.get("id") or "").strip()
        if not iid or str(row.get("qr_token") or "").strip():
            continue
        token = generate_inventory_qr_token()
        norm = normalize_inventory({**row, "qr_token": token})
        scan_url = generate_inventory_qr_value(norm)
        payload: dict[str, Any] = {"qr_token": token}
        if scan_url:
            payload["qr_code_value"] = scan_url
        result = update_row(_INV_TABLE, payload, {"id": iid})
        if result.ok:
            updated += 1
    if updated:
        clear_inventory_cache()
    return ServiceResult(ok=True, data={"updated": updated})


def _rows_for_inventory_qr_sku(sku_s: str) -> tuple[list[dict[str, Any]], str]:
    """Match by DB sku, case-insensitive sku, or display SKU ``INV-XXXXXXXX`` id prefix."""
    rows = _db_fetch_by_match(_INV_TABLE, {"sku": sku_s}, limit=5)
    if len(rows) == 1:
        return rows, ""
    all_rows, _ = fetch_rows(_INV_TABLE, limit=8000, alt_tables=("inventory",))
    ci = [r for r in all_rows if str(r.get("sku") or "").strip().lower() == sku_s.lower()]
    if len(ci) == 1:
        return ci, ""
    if len(ci) > 1:
        return ci, "ambiguous"
    m = _DISPLAY_SKU_ID_RE.match(sku_s.strip())
    if m:
        prefix = m.group(1).lower()
        by_id = [
            r
            for r in all_rows
            if str(r.get("id") or "").replace("-", "").lower().startswith(prefix)
        ]
        if len(by_id) == 1:
            return by_id, ""
        if len(by_id) > 1:
            return by_id, "ambiguous"
    if rows:
        return rows, ""
    return [], "none"


def get_inventory_item_by_qr(
    *,
    sku: str | None = None,
    item_id: str | None = None,
    token: str | None = None,
) -> ServiceResult:
    """Resolve inventory item from QR params; validate qr_token when present."""
    sku_s = str(sku or "").strip()
    iid = str(item_id or "").strip()
    token_s = str(token or "").strip()
    rows: list[dict[str, Any]] = []

    if iid:
        rows = _db_fetch_by_match(_INV_TABLE, {"id": iid}, limit=3)
    elif sku_s:
        rows, sku_reason = _rows_for_inventory_qr_sku(sku_s)
        if sku_reason == "ambiguous":
            return ServiceResult(ok=False, error="Ambiguous inventory SKU.")
    elif token_s:
        rows = _db_fetch_by_match(_INV_TABLE, {"qr_token": token_s}, limit=3)
    else:
        return ServiceResult(ok=False, error="Missing inventory identifier.")

    if not rows:
        return ServiceResult(ok=False, error="Inventory item not found.")
    if len(rows) > 1:
        return ServiceResult(ok=False, error="Ambiguous inventory match.")

    item = _row_to_item(rows[0])
    stored_token = str(item.get("qr_token") or "").strip()
    if stored_token and token_s and token_s != stored_token:
        return ServiceResult(ok=False, error="Invalid inventory QR code.")
    if stored_token and not token_s and not iid:
        return ServiceResult(ok=False, error="Invalid inventory QR code.")
    if not stored_token:
        item["qr_token"] = _ensure_item_qr_token(item)
    return ServiceResult(ok=True, data=item)


def _legacy_txn_type(transaction_type: str) -> str:
    mapping = {
        "check_out": "OUT",
        "check_in": "IN",
        "issue_to_job": "TO_JOB",
        "return_from_job": "RETURN",
        "consume_on_job": "CONSUME",
        "consume_in_shop": "SHOP",
        "adjustment": "ADJUST",
    }
    return mapping.get(transaction_type, transaction_type.upper())


def record_shop_inventory_consumption(data: dict[str, Any]) -> ServiceResult:
    """Decrement on-hand inventory for shop use with a full transaction audit row."""
    payload = dict(data)
    payload["transaction_type"] = "consume_in_shop"
    payload["destination_type"] = "shop"
    payload["job_id"] = None
    return record_inventory_transaction(payload)


def record_inventory_transaction(data: dict[str, Any]) -> ServiceResult:
    """
    Insert inventory_transactions row and update inventory_items quantities.

    Expected keys: inventory_id, transaction_type, quantity, job_id (optional),
    destination_type (shop | job), scanned_by_user_id, scanned_by_employee_id,
    scanned_by_name, scanned_by_phone, phone_verified, source, device_info, notes,
    unit, allow_overdraw (admin).
    """
    iid = str(data.get("inventory_id") or data.get("inventory_item_id") or "").strip()
    txn_type = str(data.get("transaction_type") or "").strip().lower()
    qty, qty_err = try_parse_inventory_quantity(
        data.get("quantity"),
        allow_zero=False,
        field_name="Quantity",
    )
    if qty_err or qty is None:
        return ServiceResult(ok=False, error=qty_err or "Quantity must be greater than zero.")
    job_id = data.get("job_id") or None
    allow_overdraw = bool(data.get("allow_overdraw"))

    if not iid:
        return ServiceResult(ok=False, error="Inventory item is required.")
    if txn_type not in INVENTORY_TXN_TYPES:
        return ServiceResult(ok=False, error="Invalid transaction type.")
    if qty <= 0:
        return ServiceResult(ok=False, error="Quantity must be greater than zero.")
    if txn_type in _JOB_REQUIRED_TYPES and not job_id:
        return ServiceResult(ok=False, error="Job is required for this action.")

    rows = _db_fetch_by_match(_INV_TABLE, {"id": iid}, limit=1)
    if not rows:
        return ServiceResult(ok=False, error="Inventory item not found.")
    item = rows[0]
    prev_qoh = float(item.get("quantity_on_hand") or 0)
    prev_out = float(item.get("quantity_checked_out") or 0)
    prev_alloc = float(item.get("quantity_allocated") or 0)

    if txn_type in _DECREASE_ON_HAND and qty > prev_qoh and not allow_overdraw:
        return ServiceResult(ok=False, error="Quantity exceeds quantity on hand.")

    new_qoh = prev_qoh
    new_out = prev_out
    new_alloc = prev_alloc

    if txn_type == "check_out":
        new_qoh = prev_qoh - qty
        new_out = prev_out + qty
    elif txn_type == "check_in":
        new_qoh = prev_qoh + qty
        new_out = max(0.0, prev_out - qty)
    elif txn_type == "issue_to_job":
        new_qoh = prev_qoh - qty
        new_alloc = prev_alloc + qty
    elif txn_type == "return_from_job":
        new_qoh = prev_qoh + qty
        new_alloc = max(0.0, prev_alloc - qty)
    elif txn_type in {"consume_on_job", "consume_in_shop"}:
        new_qoh = prev_qoh - qty
    elif txn_type == "adjustment":
        signed_raw = data.get("signed_quantity") if data.get("signed_quantity") is not None else data.get("quantity_delta")
        if signed_raw is None:
            signed = qty
        else:
            signed, signed_err = try_parse_inventory_quantity(
                signed_raw,
                allow_zero=True,
                allow_negative=True,
                field_name="Adjustment quantity",
            )
            if signed_err or signed is None:
                return ServiceResult(ok=False, error=signed_err or "Adjustment quantity must be a whole number.")
        new_qoh = prev_qoh + float(signed)

    signed_qty = -qty if txn_type in _DECREASE_ON_HAND else qty
    if txn_type == "adjustment":
        signed_qty = float(signed)

    ts = datetime.now(timezone.utc).isoformat()
    from app.services.catalog_stock_policy_service import inventory_status_fields_for_qty
    inv_update = {
        "quantity_on_hand": new_qoh,
        "quantity_checked_out": new_out,
        "quantity_allocated": new_alloc,
        "updated_at": ts,
        **inventory_status_fields_for_qty(item, new_qoh),
    }
    upd = update_row(_INV_TABLE, inv_update, {"id": iid})
    if not upd.ok:
        return ServiceResult(ok=False, error=upd.error or "Could not update inventory.")

    payload: dict[str, Any] = {
        "inventory_item_id": iid,
        "qty": signed_qty,
        "quantity": qty,
        "transaction_type": txn_type,
        "txn_type": _legacy_txn_type(txn_type),
        "job_id": job_id,
        "unit": str(data.get("unit") or item.get("unit") or "EA"),
        "previous_quantity": prev_qoh,
        "new_quantity": new_qoh,
        "scanned_by_user_id": data.get("scanned_by_user_id"),
        "scanned_by_employee_id": data.get("scanned_by_employee_id"),
        "scanned_by_name": str(data.get("scanned_by_name") or "")[:500] or None,
        "scanned_by_phone": str(data.get("scanned_by_phone") or "")[:50] or None,
        "phone_verified": bool(data.get("phone_verified")),
        "source": str(data.get("source") or "qr_scan")[:50],
        "device_info": str(data.get("device_info") or "")[:500] or None,
        "notes": str(data.get("notes") or "")[:2000],
        "employee_id": data.get("scanned_by_employee_id"),
        "profile_id": data.get("scanned_by_user_id"),
        "created_by": str(data.get("scanned_by_name") or "")[:500] or None,
        "subjob_id": data.get("subjob_id"),
        "destination_type": str(data.get("destination_type") or "")[:20] or None,
    }
    device_label = str(data.get("device_label") or "").strip()
    if device_label:
        payload["device_label"] = device_label[:200]
    ins = insert_row(_TXN_TABLE, payload)
    if not ins.ok:
        update_row(_INV_TABLE, {
            "quantity_on_hand": prev_qoh,
            "quantity_checked_out": prev_out,
            "quantity_allocated": prev_alloc,
            "updated_at": ts,
            **inventory_status_fields_for_qty(item, prev_qoh),
        }, {"id": iid})
        return ServiceResult(ok=False, error=ins.error or "Could not record transaction.")

    clear_inventory_cache()
    txn_row = ins.data if isinstance(ins.data, dict) else payload
    return ServiceResult(
        ok=True,
        data={
            "transaction": txn_row,
            "inventory": {**item, **inv_update},
            "previous_quantity": prev_qoh,
            "new_quantity": new_qoh,
        },
    )


def get_inventory_transactions(
    *,
    inventory_id: str | None = None,
    job_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return transaction history with basic display labels."""
    rows, _ = fetch_rows(_TXN_TABLE, limit=limit, order_by="created_at")
    jobs_by_id: dict[str, dict[str, Any]] = {}
    items_by_id: dict[str, dict[str, Any]] = {}
    try:
        job_rows, _ = fetch_rows("jobs", limit=5000)
        jobs_by_id = {str(j.get("id") or ""): j for j in job_rows}
    except Exception:
        pass
    from app.services.job_service import job_row_select_label
    inv_filter = str(inventory_id or "").strip()
    job_filter = str(job_id or "").strip()
    out: list[dict[str, Any]] = []
    for row in rows:
        iid = str(row.get("inventory_item_id") or "")
        jid = str(row.get("job_id") or "")
        if inv_filter and iid != inv_filter:
            continue
        if job_filter and jid != job_filter:
            continue
        item = items_by_id.get(iid)
        if item is None and iid:
            match = _db_fetch_by_match(_INV_TABLE, {"id": iid}, limit=1)
            item = normalize_inventory(match[0]) if match else {}
            items_by_id[iid] = item
        job = jobs_by_id.get(jid, {})
        txn_type = str(row.get("transaction_type") or row.get("txn_type") or "").strip()
        out.append({
            **row,
            "transaction_type": txn_type,
            "item_name": str(item.get("name") or item.get("item_name") or "—"),
            "sku": resolve_inventory_sku(item) if item else "—",
            "job_label": job_row_select_label(job) if job else "—",
            "quantity_display": abs(
                parse_inventory_quantity(
                    row.get("quantity") if row.get("quantity") is not None else row.get("qty"),
                    allow_negative=True,
                    allow_zero=True,
                )
            ),
        })
    out.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return out
