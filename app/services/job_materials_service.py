"""
Job materials — issue inventory to jobs, manual costing lines, and reads for Job Details / Job Costing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.services.inventory_service import (
    get_inventory_item,
    get_inventory_item_by_qr,
    record_inventory_transaction,
)
from app.services.repository import ServiceResult, fetch_rows, insert_row

_JOB_MATERIALS_TABLE = "job_materials"
_COSTING_TXN_TYPES = frozenset({"issue_to_job", "consume_on_job"})

__all__ = [
    "add_manual_job_material",
    "add_pricing_guide_job_material",
    "fetch_job_materials",
    "get_pricing_guide_item",
    "issue_inventory_to_job",
    "job_material_line_total",
    "job_materials_total",
    "list_pricing_guide_job_options",
    "resolve_inventory_by_scan_code",
]


def _safe_float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def job_material_line_total(row: dict[str, Any]) -> float:
    for key in ("line_total", "total_cost"):
        if row.get(key) is not None and str(row.get(key)).strip() != "":
            return _safe_float(row.get(key))
    qty = _safe_float(row.get("quantity") if row.get("quantity") is not None else row.get("qty"))
    return qty * _safe_float(row.get("unit_cost"))


def job_materials_total(rows: list[dict[str, Any]]) -> float:
    return sum(job_material_line_total(r) for r in rows)


def fetch_job_materials(job_id: str, *, limit: int = 500) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    if not jid:
        return []
    rows, _ = fetch_rows(_JOB_MATERIALS_TABLE, limit=limit, order_by="created_at")
    out = [r for r in rows if str(r.get("job_id") or "") == jid]
    out.sort(key=lambda r: str(r.get("used_at") or r.get("created_at") or ""), reverse=True)
    return out


def _parse_inventory_scan_deeplink(raw: str) -> dict[str, str]:
    s = str(raw or "").strip()
    if not s:
        return {}
    try:
        if "://" in s or s.startswith("/") or s.startswith("?"):
            u = urlparse(s if "://" in s else f"https://placeholder.local{s if s.startswith('/') else '/' + s}")
            q = parse_qs(u.query)
        elif "scan=inventory" in s.lower() or "item_id=" in s.lower() or "token=" in s.lower():
            q = parse_qs(s.lstrip("?"))
        else:
            return {}
        out: dict[str, str] = {}
        for key in ("sku", "token", "item_id", "code"):
            vals = q.get(key) or []
            if vals:
                out[key] = str(vals[0]).strip()
        scan_vals = q.get("scan") or []
        if scan_vals and str(scan_vals[0]).strip().lower() == "inventory":
            out["scan"] = "inventory"
        return out
    except Exception:
        return {}


def resolve_inventory_by_scan_code(code: str) -> ServiceResult:
    """Resolve inventory item from SKU, QR value, or mobile use-form URL."""
    raw = str(code or "").strip()
    if not raw:
        return ServiceResult(ok=False, error="Enter an item code or scan link.")

    parsed = _parse_inventory_scan_deeplink(raw)
    if parsed.get("scan") == "inventory" or parsed.get("item_id") or parsed.get("token"):
        result = get_inventory_item_by_qr(
            sku=parsed.get("sku") or None,
            item_id=parsed.get("item_id") or None,
            token=parsed.get("token") or None,
        )
        if result.ok and result.data:
            return result
        return ServiceResult(ok=False, error=str(result.error or "Invalid inventory QR code."))

    try:
        from app.db import fetch_by_match_admin
    except ImportError:
        from db import fetch_by_match_admin  # type: ignore

    for field in ("qr_code_value", "sku"):
        rows = fetch_by_match_admin("inventory_items", {field: raw}, limit=5) or []
        if len(rows) == 1:
            item = get_inventory_item(str(rows[0].get("id") or ""))
            if item:
                return ServiceResult(ok=True, data=item)
        if len(rows) > 1:
            return ServiceResult(ok=False, error="Multiple inventory items matched this code.")

    return ServiceResult(ok=False, error="No inventory item found for this code.")


def _inventory_unit_cost(item: dict[str, Any]) -> float:
    for key in ("unit_cost", "average_cost", "last_purchase_cost"):
        val = _safe_float(item.get(key))
        if val > 0:
            return val
    return _safe_float(item.get("unit_cost"))


def _inventory_display_name(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("item_name") or "Material").strip() or "Material"


def _pricing_guide_unit_cost(row: dict[str, Any]) -> float:
    try:
        from app.services.pricing_guide_service import resolve_live_unit_cost
    except ImportError:
        from services.pricing_guide_service import resolve_live_unit_cost  # type: ignore
    cost = resolve_live_unit_cost(row)
    if cost > 0:
        return cost
    return _safe_float(row.get("default_cost"))


def _pricing_guide_display_name(row: dict[str, Any]) -> str:
    desc = str(row.get("description") or row.get("item") or "").strip()
    if desc:
        return desc
    return str(row.get("item_number") or row.get("sku") or row.get("item_code") or "Material").strip() or "Material"


def get_pricing_guide_item(item_id: str) -> dict[str, Any] | None:
    pid = str(item_id or "").strip()
    if not pid:
        return None
    for row in list_pricing_guide_job_options():
        if str(row.get("id") or "") == pid:
            return row
    return None


def list_pricing_guide_job_options(*, include_inactive: bool = False) -> list[dict[str, Any]]:
    """Active Pricing Guide rows suitable for job material costing (no inventory movement)."""
    try:
        from app.services.pricing_guide_service import (
            _MATERIAL_LIKE_TYPES,
            cached_pricing_guide_rows,
        )
    except ImportError:
        from services.pricing_guide_service import (  # type: ignore
            _MATERIAL_LIKE_TYPES,
            cached_pricing_guide_rows,
        )
    rows = cached_pricing_guide_rows(include_inactive=include_inactive)
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("is_active") is False:
            continue
        item_type = str(row.get("item_type") or "Material").strip()
        if item_type not in _MATERIAL_LIKE_TYPES:
            continue
        if not str(row.get("description") or row.get("item_number") or row.get("sku") or "").strip():
            continue
        out.append(row)
    out.sort(key=lambda r: str(r.get("description") or "").casefold())
    return out


def add_pricing_guide_job_material(
    *,
    job_id: str,
    pricing_guide_item_id: str,
    quantity: float,
    notes: str = "",
    subjob_id: str | None = None,
    employee_id: str | None = None,
    used_at: datetime | None = None,
    usage_source: str = "pricing_guide",
) -> ServiceResult:
    """Add a job costing line from Pricing Guide — does not change inventory on-hand."""
    jid = str(job_id or "").strip()
    pid = str(pricing_guide_item_id or "").strip()
    qty = float(quantity or 0)

    if not jid:
        return ServiceResult(ok=False, error="Job is required.")
    if not pid:
        return ServiceResult(ok=False, error="Pricing Guide item is required.")
    if qty <= 0:
        return ServiceResult(ok=False, error="Quantity must be greater than zero.")

    pg_row = get_pricing_guide_item(pid)
    if not pg_row:
        return ServiceResult(ok=False, error="Pricing Guide item not found.")

    unit_cost = _pricing_guide_unit_cost(pg_row)
    ts = (used_at or datetime.now(timezone.utc)).isoformat()
    payload: dict[str, Any] = {
        "job_id": jid,
        "pricing_guide_id": pid,
        "inventory_item_id": None,
        "item_name": _pricing_guide_display_name(pg_row)[:500],
        "quantity": qty,
        "unit_cost": unit_cost,
        "line_total": round(qty * unit_cost, 2),
        "notes": str(notes or "")[:2000],
        "subjob_id": subjob_id,
        "employee_id": employee_id,
        "used_at": ts,
        "usage_source": usage_source,
    }
    return _insert_job_material(payload)


def _insert_job_material(payload: dict[str, Any]) -> ServiceResult:
    result = insert_row(_JOB_MATERIALS_TABLE, payload)
    if result.ok and isinstance(result.data, dict):
        try:
            from app.services.job_cost_transaction_service import _safe_sync, sync_job_material
        except ImportError:
            from services.job_cost_transaction_service import _safe_sync, sync_job_material  # type: ignore
        _safe_sync(sync_job_material, result.data)
    return result


def issue_inventory_to_job(
    *,
    job_id: str,
    inventory_item_id: str,
    quantity: float,
    transaction_type: str = "consume_on_job",
    notes: str = "",
    subjob_id: str | None = None,
    employee_id: str | None = None,
    used_at: datetime | None = None,
    usage_source: str = "manual_inventory",
    allow_overdraw: bool = False,
    scanned_by_user_id: str | None = None,
    scanned_by_name: str | None = None,
    scanned_by_phone: str | None = None,
    scanned_by_employee_id: str | None = None,
    phone_verified: bool = False,
    source: str = "job_materials",
    unit: str | None = None,
) -> ServiceResult:
    """
    Decrement on-hand inventory, record audit transaction, and create a job_materials costing line.
    """
    jid = str(job_id or "").strip()
    iid = str(inventory_item_id or "").strip()
    txn_type = str(transaction_type or "consume_on_job").strip().lower()
    qty = float(quantity or 0)

    if not jid:
        return ServiceResult(ok=False, error="Job is required.")
    if not iid:
        return ServiceResult(ok=False, error="Inventory item is required.")
    if qty <= 0:
        return ServiceResult(ok=False, error="Quantity must be greater than zero.")
    if txn_type not in _COSTING_TXN_TYPES:
        return ServiceResult(ok=False, error="Invalid transaction type for job materials.")

    item = get_inventory_item(iid)
    if not item:
        return ServiceResult(ok=False, error="Inventory item not found.")

    txn_data: dict[str, Any] = {
        "inventory_id": iid,
        "transaction_type": txn_type,
        "quantity": qty,
        "job_id": jid,
        "destination_type": "job",
        "unit": unit or str(item.get("unit") or "EA"),
        "notes": notes,
        "allow_overdraw": allow_overdraw,
        "scanned_by_user_id": scanned_by_user_id,
        "scanned_by_employee_id": scanned_by_employee_id or employee_id,
        "scanned_by_name": scanned_by_name,
        "scanned_by_phone": scanned_by_phone,
        "phone_verified": phone_verified,
        "source": source,
    }
    if subjob_id:
        txn_data["subjob_id"] = subjob_id

    txn_result = record_inventory_transaction(txn_data)
    if not txn_result.ok:
        return txn_result

    unit_cost = _inventory_unit_cost(item)
    line_total = round(qty * unit_cost, 2)
    ts = (used_at or datetime.now(timezone.utc)).isoformat()
    txn_row = txn_result.data.get("transaction") if isinstance(txn_result.data, dict) else {}
    txn_id = str((txn_row or {}).get("id") or "").strip() or None

    mat_payload: dict[str, Any] = {
        "job_id": jid,
        "inventory_item_id": iid,
        "item_name": _inventory_display_name(item)[:500],
        "quantity": qty,
        "unit_cost": unit_cost,
        "line_total": line_total,
        "notes": str(notes or "")[:2000],
        "subjob_id": subjob_id,
        "employee_id": employee_id or scanned_by_employee_id,
        "inventory_transaction_id": txn_id,
        "used_at": ts,
        "usage_source": usage_source,
        "destination_type": "job",
    }
    mat_result = _insert_job_material(mat_payload)
    if not mat_result.ok:
        return ServiceResult(
            ok=False,
            error=mat_result.error or "Inventory moved but job costing line failed.",
            data=txn_result.data,
        )

    return ServiceResult(
        ok=True,
        data={
            "transaction": txn_row,
            "job_material": mat_result.data,
            "inventory": txn_result.data.get("inventory") if isinstance(txn_result.data, dict) else None,
            "line_total": line_total,
        },
    )


def add_manual_job_material(
    *,
    job_id: str,
    item_name: str,
    quantity: float,
    unit_cost: float,
    notes: str = "",
    subjob_id: str | None = None,
    employee_id: str | None = None,
    used_at: datetime | None = None,
    usage_source: str = "manual_entry",
) -> ServiceResult:
    """Add a costing line without inventory stock movement (non-stocked / field-purchased material)."""
    jid = str(job_id or "").strip()
    name = str(item_name or "").strip()
    qty = float(quantity or 0)
    uc = float(unit_cost or 0)

    if not jid:
        return ServiceResult(ok=False, error="Job is required.")
    if not name:
        return ServiceResult(ok=False, error="Material name is required.")
    if qty <= 0:
        return ServiceResult(ok=False, error="Quantity must be greater than zero.")

    ts = (used_at or datetime.now(timezone.utc)).isoformat()
    payload: dict[str, Any] = {
        "job_id": jid,
        "inventory_item_id": None,
        "item_name": name[:500],
        "quantity": qty,
        "unit_cost": uc,
        "line_total": round(qty * uc, 2),
        "notes": str(notes or "")[:2000],
        "subjob_id": subjob_id,
        "employee_id": employee_id,
        "used_at": ts,
        "usage_source": usage_source,
    }
    return _insert_job_material(payload)
