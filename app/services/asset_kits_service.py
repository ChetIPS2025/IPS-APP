"""Asset kits / tool trailers — kit items, audits, transactions, accountability."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.repository import ServiceResult, delete_row, fetch_rows, insert_row, update_row

_KIT_ITEMS = "asset_kit_items"
_KIT_AUDITS = "asset_kit_audits"
_KIT_AUDIT_ITEMS = "asset_kit_audit_items"
_KIT_TXN = "asset_kit_transactions"
_ASSETS = "assets"

KIT_TYPES = (
    "Enclosed Tool Trailer",
    "Tool Trailer",
    "Gang Box",
    "Job Box",
    "Welding Rig",
    "Service Truck Kit",
    "Crew Tool Kit",
    "Other Kit",
)

ITEM_TYPES = ("Tool", "Equipment", "Safety Gear", "Consumable", "Material", "Accessory", "Other")
CONDITIONS = ("New", "Good", "Fair", "Damaged", "Needs Repair", "Missing", "Retired")
ITEM_STATUSES = ("Present", "Missing", "Checked Out", "Damaged", "Needs Replacement", "Retired")
TXN_TYPES = (
    "Add Item",
    "Remove Item",
    "Check Out Tool",
    "Return Tool",
    "Mark Missing",
    "Mark Damaged",
    "Repair Completed",
    "Replace Item",
    "Assign Trailer",
    "Return Trailer",
    "Audit Completed",
)

_KIT_CATEGORY_HINTS = (
    "tool trailer",
    "enclosed trailer",
    "gang box",
    "job box",
    "welding rig",
    "service truck kit",
    "crew tool kit",
)

_trailer_kit_parent_ids_cache: set[str] | None = None


def _tool_trailer_kit_parent_asset_ids() -> set[str]:
    """Asset ids registered as kit/trailer containers in tool_trailer_kits."""
    global _trailer_kit_parent_ids_cache
    if _trailer_kit_parent_ids_cache is not None:
        return _trailer_kit_parent_ids_cache
    ids: set[str] = set()
    try:
        rows, _ = fetch_rows("tool_trailer_kits", limit=5000)
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            pid = str(row.get("parent_asset_id") or "").strip()
            if pid:
                ids.add(pid)
    except Exception:
        pass
    _trailer_kit_parent_ids_cache = ids
    return ids


def clear_trailer_kit_parent_cache() -> None:
    global _trailer_kit_parent_ids_cache
    _trailer_kit_parent_ids_cache = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _f(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def normalize_kit_item(row: dict[str, Any]) -> dict[str, Any]:
    qty_exp = _f(row.get("quantity_expected") or row.get("quantity") or 1, 1.0)
    qty_act = _f(row.get("quantity_actual") or row.get("quantity_on_hand") or qty_exp, qty_exp)
    unit_val = _f(row.get("unit_value") or 0)
    total = _f(row.get("total_value") or qty_exp * unit_val)
    status = str(row.get("status") or "Present").strip() or "Present"
    condition = str(row.get("condition") or "Good").strip() or "Good"
    return {
        **row,
        "id": str(row.get("id") or ""),
        "parent_asset_id": str(row.get("parent_asset_id") or ""),
        "item_name": str(row.get("item_name") or "—"),
        "item_type": str(row.get("item_type") or "Tool"),
        "category": str(row.get("category") or ""),
        "description": str(row.get("description") or ""),
        "quantity_expected": qty_exp,
        "quantity_actual": qty_act,
        "quantity": qty_exp,
        "quantity_on_hand": qty_act,
        "unit": str(row.get("unit") or "EA"),
        "unit_value": unit_val,
        "total_value": total,
        "condition": condition,
        "status": status,
        "serial_number": str(row.get("serial_number") or ""),
        "child_asset_id": str(row.get("child_asset_id") or "").strip() or None,
        "inventory_item_id": str(row.get("inventory_item_id") or "").strip() or None,
        "assigned_to_name": str(row.get("assigned_to_name") or ""),
        "assigned_to_employee_id": row.get("assigned_to_employee_id"),
        "notes": str(row.get("notes") or ""),
        "is_active": row.get("is_active") is not False,
        "qr_token": str(row.get("qr_token") or ""),
        "qr_value": str(row.get("qr_value") or row.get("qr_code_value") or ""),
    }


def asset_is_kit(asset: dict[str, Any]) -> bool:
    """True for container kits/trailers — not individual tools with 'kit' in the name."""
    if asset.get("is_kit") is True:
        return True
    aid = str(asset.get("id") or "").strip()
    if aid and aid in _tool_trailer_kit_parent_asset_ids():
        return True
    cat = str(asset.get("category") or asset.get("asset_type") or "").lower()
    name = str(asset.get("asset_name") or asset.get("name") or "").lower()
    return any(h in cat or h in name for h in _KIT_CATEGORY_HINTS)


def infer_kit_type(asset: dict[str, Any]) -> str:
    kt = str(asset.get("kit_type") or "").strip()
    if kt:
        return kt
    cat = str(asset.get("category") or "").lower()
    name = str(asset.get("asset_name") or "").lower()
    for label, hints in (
        ("Enclosed Tool Trailer", ("enclosed trailer", "enclosed tool trailer")),
        ("Tool Trailer", ("tool trailer",)),
        ("Gang Box", ("gang box",)),
        ("Job Box", ("job box",)),
        ("Welding Rig", ("welding",)),
        ("Service Truck Kit", ("service truck",)),
        ("Crew Tool Kit", ("crew tool",)),
    ):
        if any(h in cat or h in name for h in hints):
            return label
    return "Tool Trailer"


def list_all_kit_items_enriched(
    assets_by_id: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """All active kit items with parent asset context for cross-kit lists."""
    rows, _ = fetch_rows(_KIT_ITEMS, limit=10000, order_by="item_name")
    if assets_by_id is None:
        from app.services.phase2_modules_service import list_assets, normalize_asset
        assets_by_id = {
            str(a.get("id") or "").strip(): normalize_asset(a)
            for a in list_assets()
            if str(a.get("id") or "").strip()
        }
    out: list[dict[str, Any]] = []
    for r in rows or []:
        if not isinstance(r, dict) or r.get("is_active") is False:
            continue
        item = normalize_kit_item(r)
        pid = str(item.get("parent_asset_id") or "").strip()
        parent = assets_by_id.get(pid) or {}
        parent_name = str(parent.get("asset_name") or parent.get("name") or "—").strip() or "—"
        parent_number = str(parent.get("asset_number") or parent.get("asset_id") or "—").strip() or "—"
        parent_loc = str(parent.get("location") or "—").strip() or "—"
        out.append(
            {
                **item,
                "row_type": "kit_item",
                "parent_asset_name": parent_name,
                "parent_asset_number": parent_number,
                "parent_location": parent_loc,
            }
        )
    return sorted(
        out,
        key=lambda x: (
            str(x.get("parent_asset_name") or "").lower(),
            str(x.get("item_name") or "").lower(),
        ),
    )


def get_asset_kit_items(parent_asset_id: str) -> list[dict[str, Any]]:
    pid = str(parent_asset_id or "").strip()
    if not pid:
        return []
    rows, _ = fetch_rows(_KIT_ITEMS, limit=10000, order_by="item_name")
    out = [
        normalize_kit_item(r)
        for r in rows
        if str(r.get("parent_asset_id") or "") == pid and r.get("is_active") is not False
    ]
    return sorted(out, key=lambda x: str(x.get("item_name") or "").lower())


def get_asset_kit_item(item_id: str) -> dict[str, Any] | None:
    iid = str(item_id or "").strip()
    if not iid:
        return None
    rows, _ = fetch_rows(_KIT_ITEMS, limit=10000)
    for r in rows:
        if str(r.get("id") or "") == iid:
            return normalize_kit_item(r)
    return None


def recalculate_asset_kit_value(parent_asset_id: str) -> ServiceResult:
    pid = str(parent_asset_id or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing parent asset id.")
    items = get_asset_kit_items(pid)
    total = sum(_f(i.get("total_value")) for i in items)
    present_val = sum(
        _f(i.get("total_value"))
        for i in items
        if str(i.get("status") or "").lower() in {"present", "checked out"}
    )
    missing_val = sum(
        _f(i.get("unit_value")) * max(0, _f(i.get("quantity_expected")) - _f(i.get("quantity_actual")))
        for i in items
        if str(i.get("status") or "").lower() in {"missing", "needs replacement"}
        or _f(i.get("quantity_actual")) < _f(i.get("quantity_expected"))
    )
    damaged_val = sum(
        _f(i.get("unit_value")) * _f(i.get("quantity_actual"))
        for i in items
        if str(i.get("status") or "").lower() in {"damaged", "needs repair", "needs replacement"}
    )
    payload = {
        "total_kit_value": round(total, 2),
        "value": round(total, 2),
        "current_value": round(total, 2),
    }
    result = update_row(_ASSETS, payload, {"id": pid})
    return ServiceResult(
        ok=result.ok,
        data={
            "total_kit_value": total,
            "present_value": present_val,
            "missing_value": missing_val,
            "damaged_value": damaged_val,
            "replacement_cost": missing_val + damaged_val,
        },
        error=result.error,
    )


def get_asset_kit_summary(parent_asset_id: str, asset: dict[str, Any] | None = None) -> dict[str, Any]:
    items = get_asset_kit_items(parent_asset_id)
    expected = len(items)
    present = sum(1 for i in items if str(i.get("status") or "").lower() == "present")
    missing = sum(1 for i in items if str(i.get("status") or "").lower() == "missing")
    damaged = sum(
        1
        for i in items
        if str(i.get("status") or "").lower() in {"damaged", "needs repair", "needs replacement"}
    )
    total_val = sum(_f(i.get("total_value")) for i in items)
    missing_val = sum(
        _f(i.get("unit_value")) * max(0, _f(i.get("quantity_expected")) - _f(i.get("quantity_actual")))
        for i in items
    )
    damaged_val = sum(
        _f(i.get("unit_value")) * _f(i.get("quantity_actual"))
        for i in items
        if str(i.get("status") or "").lower() in {"damaged", "needs repair", "needs replacement"}
    )
    row = asset or {}
    return {
        "total_kit_value": _f(row.get("total_kit_value") or total_val),
        "expected_items": expected,
        "present_items": present,
        "missing_items": missing,
        "damaged_items": damaged,
        "missing_value": round(missing_val, 2),
        "damaged_value": round(damaged_val, 2),
        "replacement_cost": round(missing_val + damaged_val, 2),
        "assigned_supervisor": str(row.get("assigned_to_name") or row.get("operator") or "—"),
        "assigned_job_id": str(row.get("assigned_job_id") or ""),
        "last_audit": str(row.get("last_kit_audit_at") or "")[:19],
        "kit_status": str(row.get("kit_status") or row.get("status") or "Active"),
    }


def convert_asset_to_kit(asset_id: str, kit_type: str | None = None) -> ServiceResult:
    aid = str(asset_id or "").strip()
    if not aid:
        return ServiceResult(ok=False, error="Missing asset id.")
    from app.services.assets_service import get_asset, clear_assets_cache

    asset = get_asset(aid) or {}
    kt = str(kit_type or infer_kit_type(asset)).strip()
    payload = {
        "is_kit": True,
        "kit_type": kt,
        "kit_status": str(asset.get("kit_status") or "Active"),
    }
    result = update_row(_ASSETS, payload, {"id": aid})
    if result.ok:
        clear_assets_cache()
        recalculate_asset_kit_value(aid)
    return result


def _kit_serial_taken(parent_asset_id: str, serial: str, *, exclude_item_id: str | None = None) -> bool:
    sn = str(serial or "").strip().lower()
    if not sn:
        return False
    for it in get_asset_kit_items(parent_asset_id):
        if exclude_item_id and str(it.get("id") or "") == exclude_item_id:
            continue
        if str(it.get("serial_number") or "").strip().lower() == sn:
            return True
    return False


def create_asset_kit_items_multi(parent_asset_id: str, data: dict[str, Any]) -> ServiceResult:
    """
    Create one or more kit item rows. When quantity > 1, creates one row per physical unit
    (qty 1 each) with a distinct serial number per unit.
    """
    pid = str(parent_asset_id or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing parent asset id.")
    qty = int(max(1, round(_f(data.get("quantity_expected") or data.get("quantity") or 1))))
    serials_raw = data.get("unit_serials")
    if isinstance(serials_raw, list) and (qty > 1 or len(serials_raw) > 0):
        serials = [str(s or "").strip() for s in serials_raw]
    else:
        serials = [str(data.get("serial_number") or "").strip()]

    if qty > 1:
        if len(serials) != qty:
            return ServiceResult(
                ok=False,
                error=f"Enter a serial number for each of the {qty} units.",
            )
        for idx, serial in enumerate(serials, start=1):
            if not serial:
                return ServiceResult(ok=False, error=f"Serial number is required for unit {idx}.")
        lowered = [s.lower() for s in serials]
        if len(set(lowered)) != len(lowered):
            return ServiceResult(ok=False, error="Serial numbers must be unique for each unit.")
        for serial in serials:
            if _kit_serial_taken(pid, serial):
                return ServiceResult(
                    ok=False,
                    error=f"Serial {serial!r} is already on this kit.",
                )
        created: list[Any] = []
        for serial in serials:
            unit_data = {
                **data,
                "quantity_expected": 1.0,
                "quantity_actual": 1.0,
                "quantity": 1.0,
                "serial_number": serial,
            }
            unit_data.pop("unit_serials", None)
            result = create_asset_kit_item(pid, unit_data)
            if not result.ok:
                return result
            created.append(result.data)
        return ServiceResult(ok=True, data={"created": created, "count": len(created)})

    serial = serials[0] if serials else str(data.get("serial_number") or "").strip()
    if serial and _kit_serial_taken(pid, serial):
        return ServiceResult(ok=False, error=f"Serial {serial!r} is already on this kit.")
    single = {**data, "quantity_expected": float(qty), "quantity_actual": float(qty), "serial_number": serial}
    single.pop("unit_serials", None)
    return create_asset_kit_item(pid, single)


def create_asset_kit_item(parent_asset_id: str, data: dict[str, Any]) -> ServiceResult:
    pid = str(parent_asset_id or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing parent asset id.")
    name = str(data.get("item_name") or "").strip()
    if not name:
        return ServiceResult(ok=False, error="Item name is required.")
    qty_exp = _f(data.get("quantity_expected") or data.get("quantity") or 1, 1.0)
    qty_act = _f(data.get("quantity_actual") or qty_exp, qty_exp)
    unit_val = _f(data.get("unit_value") or 0)
    payload: dict[str, Any] = {
        "parent_asset_id": pid,
        "item_name": name,
        "item_type": str(data.get("item_type") or "Tool"),
        "category": str(data.get("category") or ""),
        "description": str(data.get("description") or ""),
        "quantity": qty_exp,
        "quantity_expected": qty_exp,
        "quantity_actual": qty_act,
        "quantity_on_hand": qty_act,
        "unit": str(data.get("unit") or "EA"),
        "unit_value": unit_val,
        "replacement_cost": _f(data.get("replacement_cost") or unit_val),
        "condition": str(data.get("condition") or "Good"),
        "status": str(data.get("status") or "Present"),
        "serial_number": str(data.get("serial_number") or ""),
        "child_asset_id": data.get("child_asset_id") or None,
        "inventory_item_id": data.get("inventory_item_id") or None,
        "assigned_to_name": str(data.get("assigned_to_name") or ""),
        "assigned_to_employee_id": data.get("assigned_to_employee_id"),
        "notes": str(data.get("notes") or ""),
        "is_active": True,
        "updated_at": _now_iso(),
    }
    if data.get("qr_token"):
        payload["qr_token"] = data["qr_token"]
        payload["qr_code_value"] = data.get("qr_value") or data.get("qr_code_value") or ""
    result = insert_row(_KIT_ITEMS, payload)
    if result.ok:
        recalculate_asset_kit_value(pid)
        create_asset_kit_transaction(
            {
                "parent_asset_id": pid,
                "kit_item_id": (result.data or {}).get("id") if isinstance(result.data, dict) else None,
                "transaction_type": "Add Item",
                "quantity": qty_exp,
                "performed_by_name": data.get("performed_by_name"),
                "performed_by_phone": data.get("performed_by_phone"),
                "new_status": payload["status"],
                "notes": f"Added kit item: {name}",
            }
        )
    return result


def update_asset_kit_item(item_id: str, data: dict[str, Any]) -> ServiceResult:
    iid = str(item_id or "").strip()
    if not iid:
        return ServiceResult(ok=False, error="Missing kit item id.")
    existing = get_asset_kit_item(iid) or {}
    pid = str(existing.get("parent_asset_id") or data.get("parent_asset_id") or "")
    qty_exp = _f(data.get("quantity_expected") or data.get("quantity") or existing.get("quantity_expected") or 1)
    qty_act = _f(data.get("quantity_actual") or existing.get("quantity_actual") or qty_exp)
    unit_val = _f(data.get("unit_value") if "unit_value" in data else existing.get("unit_value"))
    payload: dict[str, Any] = {
        "item_name": str(data.get("item_name") or existing.get("item_name") or ""),
        "item_type": str(data.get("item_type") or existing.get("item_type") or "Tool"),
        "category": str(data.get("category") or existing.get("category") or ""),
        "description": str(data.get("description") or existing.get("description") or ""),
        "quantity": qty_exp,
        "quantity_expected": qty_exp,
        "quantity_actual": qty_act,
        "quantity_on_hand": qty_act,
        "unit": str(data.get("unit") or existing.get("unit") or "EA"),
        "unit_value": unit_val,
        "condition": str(data.get("condition") or existing.get("condition") or "Good"),
        "status": str(data.get("status") or existing.get("status") or "Present"),
        "serial_number": str(data.get("serial_number") or existing.get("serial_number") or ""),
        "child_asset_id": data.get("child_asset_id", existing.get("child_asset_id")),
        "inventory_item_id": data.get("inventory_item_id", existing.get("inventory_item_id")),
        "assigned_to_name": str(data.get("assigned_to_name") or existing.get("assigned_to_name") or ""),
        "assigned_to_employee_id": data.get("assigned_to_employee_id", existing.get("assigned_to_employee_id")),
        "notes": str(data.get("notes") or existing.get("notes") or ""),
        "updated_at": _now_iso(),
    }
    serial = str(payload.get("serial_number") or "").strip()
    if serial and pid and _kit_serial_taken(pid, serial, exclude_item_id=iid):
        return ServiceResult(ok=False, error=f"Serial {serial!r} is already on this kit.")
    prev_status = str(existing.get("status") or "")
    result = update_row(_KIT_ITEMS, payload, {"id": iid})
    if result.ok and pid:
        recalculate_asset_kit_value(pid)
        if payload["status"] != prev_status:
            create_asset_kit_transaction(
                {
                    "parent_asset_id": pid,
                    "kit_item_id": iid,
                    "transaction_type": _status_to_txn(payload["status"]),
                    "quantity": qty_act,
                    "previous_status": prev_status,
                    "new_status": payload["status"],
                    "performed_by_name": data.get("performed_by_name"),
                    "performed_by_phone": data.get("performed_by_phone"),
                }
            )
    return result


def _status_to_txn(status: str) -> str:
    s = str(status or "").lower()
    if s == "missing":
        return "Mark Missing"
    if s == "damaged":
        return "Mark Damaged"
    if s == "checked out":
        return "Check Out Tool"
    if s == "present":
        return "Return Tool"
    return "Add Item"


def delete_asset_kit_item(item_id: str) -> ServiceResult:
    iid = str(item_id or "").strip()
    existing = get_asset_kit_item(iid) or {}
    pid = str(existing.get("parent_asset_id") or "")
    result = delete_row(_KIT_ITEMS, {"id": iid})
    if result.ok and pid:
        recalculate_asset_kit_value(pid)
    return result


def create_asset_kit_transaction(data: dict[str, Any]) -> ServiceResult:
    pid = str(data.get("parent_asset_id") or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing parent asset id.")
    payload = {
        "parent_asset_id": pid,
        "kit_item_id": data.get("kit_item_id"),
        "job_id": data.get("job_id"),
        "transaction_type": str(data.get("transaction_type") or "Add Item"),
        "quantity": _f(data.get("quantity") or 1, 1.0),
        "performed_by_user_id": data.get("performed_by_user_id"),
        "performed_by_employee_id": data.get("performed_by_employee_id"),
        "performed_by_name": str(data.get("performed_by_name") or ""),
        "performed_by_phone": str(data.get("performed_by_phone") or ""),
        "assigned_to_employee_id": data.get("assigned_to_employee_id"),
        "assigned_to_name": str(data.get("assigned_to_name") or ""),
        "previous_status": data.get("previous_status"),
        "new_status": data.get("new_status"),
        "notes": str(data.get("notes") or ""),
    }
    return insert_row(_KIT_TXN, payload)


def get_asset_kit_transactions(parent_asset_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
    pid = str(parent_asset_id or "").strip()
    rows, _ = fetch_rows(_KIT_TXN, limit=limit, order_by="created_at")
    return [r for r in rows if str(r.get("parent_asset_id") or "") == pid]


def get_asset_kit_audits(parent_asset_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    pid = str(parent_asset_id or "").strip()
    rows, _ = fetch_rows(_KIT_AUDITS, limit=limit, order_by="audit_date")
    return [r for r in rows if str(r.get("parent_asset_id") or "") == pid]


def create_asset_kit_audit(
    parent_asset_id: str,
    audit_data: dict[str, Any],
    audit_items: list[dict[str, Any]],
) -> ServiceResult:
    pid = str(parent_asset_id or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing parent asset id.")
    items = get_asset_kit_items(pid)
    by_id = {str(i.get("id")): i for i in items}

    from app.services.trailer_dashboard_service import normalize_audit_item_status, validate_audit_item_lines
    labels = {str(i.get("id") or ""): str(i.get("item_name") or "Item") for i in items}
    for line in audit_items:
        kid = str(line.get("kit_item_id") or "").strip()
        if kid and not line.get("item_name"):
            line["item_name"] = labels.get(kid, "Item")
    validation_err = validate_audit_item_lines(list(audit_items), labels=labels)
    if validation_err:
        return ServiceResult(ok=False, error=validation_err)

    exp_count = len(items)
    present_count = 0
    missing_count = 0
    damaged_count = 0
    exp_val = sum(_f(i.get("total_value")) for i in items)
    miss_val = 0.0
    dmg_val = 0.0

    audit_payload = {
        "parent_asset_id": pid,
        "audit_date": audit_data.get("audit_date") or _now_iso(),
        "performed_by_user_id": audit_data.get("performed_by_user_id"),
        "performed_by_employee_id": audit_data.get("performed_by_employee_id"),
        "performed_by_name": str(audit_data.get("performed_by_name") or ""),
        "performed_by_phone": str(audit_data.get("performed_by_phone") or ""),
        "assigned_supervisor_id": audit_data.get("assigned_supervisor_id"),
        "assigned_supervisor_name": str(audit_data.get("assigned_supervisor_name") or ""),
        "job_id": audit_data.get("job_id"),
        "status": str(audit_data.get("status") or "Completed"),
        "notes": str(audit_data.get("notes") or ""),
        "audit_type": str(audit_data.get("audit_type") or "Full"),
        "photo_paths": audit_data.get("photo_paths") or [],
    }
    audit_result = insert_row(_KIT_AUDITS, audit_payload)
    if not audit_result.ok:
        return audit_result
    audit_id = str((audit_result.data or {}).get("id") or "")

    for line in audit_items:
        kid = str(line.get("kit_item_id") or "").strip()
        base = by_id.get(kid) or {}
        exp_q = _f(line.get("expected_quantity") or base.get("quantity_expected") or 1)
        act_q = _f(line.get("actual_quantity") or exp_q)
        cond = str(line.get("condition") or base.get("condition") or "Good")
        stat = normalize_audit_item_status(str(line.get("status") or base.get("status") or "Present"))
        miss_q = max(0.0, exp_q - act_q)
        dmg_q = act_q if stat.lower() in {"damaged", "needs repair", "needs replacement"} else 0.0
        unit_v = _f(base.get("unit_value"))

        if stat.lower() == "present" and act_q >= exp_q:
            present_count += 1
        if stat.lower() == "missing" or miss_q > 0:
            missing_count += 1
            miss_val += unit_v * miss_q
        if stat.lower() in {"damaged", "needs repair", "needs replacement"}:
            damaged_count += 1
            dmg_val += unit_v * max(dmg_q, 1)

        insert_row(
            _KIT_AUDIT_ITEMS,
            {
                "audit_id": audit_id,
                "kit_item_id": kid,
                "expected_quantity": exp_q,
                "actual_quantity": act_q,
                "condition": cond,
                "status": stat,
                "missing_quantity": miss_q,
                "damaged_quantity": dmg_q,
                "notes": str(line.get("notes") or ""),
                "photo_path": str(line.get("photo_path") or "") or None,
                "photo_url": str(line.get("photo_url") or "") or None,
            },
        )
        update_asset_kit_item(
            kid,
            {
                "quantity_actual": act_q,
                "quantity_on_hand": act_q,
                "condition": cond,
                "status": stat,
                "missing_count": miss_q,
                "last_counted_at": _now_iso(),
                "performed_by_name": audit_data.get("performed_by_name"),
                "performed_by_phone": audit_data.get("performed_by_phone"),
            },
        )

    update_row(
        _KIT_AUDITS,
        {
            "expected_item_count": exp_count,
            "present_item_count": present_count,
            "missing_item_count": missing_count,
            "damaged_item_count": damaged_count,
            "expected_value": exp_val,
            "missing_value": miss_val,
            "damaged_value": dmg_val,
        },
        {"id": audit_id},
    )
    update_row(
        _ASSETS,
        {"last_kit_audit_at": _now_iso(), "kit_status": "Audited"},
        {"id": pid},
    )
    recalculate_asset_kit_value(pid)
    create_asset_kit_transaction(
        {
            "parent_asset_id": pid,
            "transaction_type": "Audit Completed",
            "performed_by_name": audit_data.get("performed_by_name"),
            "performed_by_phone": audit_data.get("performed_by_phone"),
            "notes": audit_data.get("notes"),
        }
    )
    return ServiceResult(
        ok=True,
        data={
            "audit_id": audit_id,
            "missing_value": miss_val,
            "damaged_value": dmg_val,
            "missing_count": missing_count,
            "damaged_count": damaged_count,
        },
    )


def assign_asset_kit(parent_asset_id: str, data: dict[str, Any]) -> ServiceResult:
    pid = str(parent_asset_id or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing parent asset id.")
    payload = {
        "assigned_to_employee_id": data.get("assigned_to_employee_id"),
        "assigned_to_name": str(data.get("assigned_to_name") or data.get("supervisor_name") or ""),
        "assigned_to_phone": str(data.get("assigned_to_phone") or data.get("supervisor_phone") or ""),
        "assigned_job_id": data.get("job_id") or data.get("assigned_job_id"),
        "kit_status": "Assigned",
        "operator": str(data.get("assigned_to_name") or data.get("supervisor_name") or ""),
    }
    result = update_row(_ASSETS, payload, {"id": pid})
    if result.ok:
        create_asset_kit_transaction(
            {
                "parent_asset_id": pid,
                "transaction_type": "Assign Trailer",
                "job_id": payload.get("assigned_job_id"),
                "assigned_to_employee_id": payload.get("assigned_to_employee_id"),
                "assigned_to_name": payload.get("assigned_to_name"),
                "performed_by_name": data.get("performed_by_name"),
                "performed_by_phone": data.get("performed_by_phone"),
                "notes": data.get("notes"),
            }
        )
    return result


def get_tool_trailers() -> list[dict[str, Any]]:
    from app.services.assets_service import get_assets

    return [a for a in get_assets() if asset_is_kit(a)]


def get_overdue_kit_audits(*, days: int = 30) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out: list[dict[str, Any]] = []
    for asset in get_tool_trailers():
        last = str(asset.get("last_kit_audit_at") or "").strip()
        overdue = True
        if last:
            try:
                dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                overdue = dt < cutoff
            except ValueError:
                overdue = True
        if overdue:
            out.append({**asset, "_audit_overdue": True})
    return out


def get_missing_tools_report() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in get_tool_trailers():
        summary = get_asset_kit_summary(str(asset.get("id") or ""), asset)
        if summary.get("missing_items") or summary.get("missing_value"):
            rows.append(
                {
                    "asset_id": asset.get("id"),
                    "asset_name": asset.get("asset_name"),
                    "asset_number": asset.get("asset_number"),
                    "supervisor": summary.get("assigned_supervisor"),
                    "missing_items": summary.get("missing_items"),
                    "missing_value": summary.get("missing_value"),
                    "damaged_value": summary.get("damaged_value"),
                    "last_audit": summary.get("last_audit"),
                }
            )
    return rows


def kit_item_names_by_parent() -> dict[str, list[str]]:
    """Map parent_asset_id -> item names (for asset search)."""
    rows, _ = fetch_rows(_KIT_ITEMS, limit=10000)
    out: dict[str, list[str]] = {}
    for r in rows:
        if r.get("is_active") is False:
            continue
        pid = str(r.get("parent_asset_id") or "")
        if not pid:
            continue
        out.setdefault(pid, []).append(str(r.get("item_name") or "").lower())
    return out


def generate_kit_item_qr_token() -> str:
    return secrets.token_urlsafe(16)
