"""Apply purchase-list quantities and unit prices to small hand tools and serialized assets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.data.hand_tools_purchase_list import purchase_items_for_batch
from app.services.repository import ServiceResult, fetch_rows, insert_row_admin, update_row_admin
from app.services.serialized_tool_service import is_serialized_tool_asset
from app.services.small_hand_tool_service import clear_hand_tools_list_cache, import_hand_tool_row

_HAND_TOOLS = "small_hand_tools"
_ASSETS = "assets"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(raw: object) -> str:
    return str(raw or "").strip()


def _f(val: object, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _normalize_name(raw: object) -> str:
    return _clean(raw).casefold()


def _load_hand_tools_index() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_model: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    rows, _ = fetch_rows(_HAND_TOOLS, limit=10000, order_by="tool_name")
    for row in rows or []:
        if not isinstance(row, dict) or row.get("is_active") is False:
            continue
        model_key = _normalize_name(row.get("model_number"))
        if model_key and model_key not in by_model:
            by_model[model_key] = row
        name_key = _normalize_name(row.get("tool_name"))
        if name_key and name_key not in by_name:
            by_name[name_key] = row
    return by_model, by_name


def _load_serialized_assets() -> list[dict[str, Any]]:
    rows, _ = fetch_rows(_ASSETS, limit=10000, order_by="asset_name")
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict) or row.get("is_active") is False:
            continue
        if is_serialized_tool_asset(row):
            out.append(row)
    return out


def find_hand_tool_match(
    item: dict[str, Any],
    *,
    by_model: dict[str, dict[str, Any]] | None = None,
    by_name: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    if by_model is None or by_name is None:
        by_model, by_name = _load_hand_tools_index()
    model_key = _normalize_name(item.get("model_number"))
    if model_key:
        match = by_model.get(model_key)
        if match:
            return match
    name_key = _normalize_name(item.get("tool_name"))
    if name_key:
        return by_name.get(name_key)
    return None


def _name_matches(asset_name: str, purchase_name: str) -> bool:
    asset_key = _normalize_name(asset_name)
    purchase_key = _normalize_name(purchase_name)
    if not asset_key or not purchase_key:
        return False
    if asset_key == purchase_key:
        return True
    return purchase_key in asset_key or asset_key in purchase_key


def find_serialized_matches(item: dict[str, Any], assets: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = assets if assets is not None else _load_serialized_assets()
    model_key = _normalize_name(item.get("model_number"))
    purchase_name = _clean(item.get("tool_name"))
    matches: list[dict[str, Any]] = []
    for row in rows:
        model = _normalize_name(row.get("model") or row.get("model_number"))
        if model_key and model == model_key:
            matches.append(row)
            continue
        if not model_key and _name_matches(_clean(row.get("asset_name")), purchase_name):
            matches.append(row)
    return matches


def _hand_tool_payload(
    item: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
    increment_qty: bool = False,
) -> dict[str, Any]:
    purchase_qty = max(0.0, _f(item.get("qty")))
    unit_value = max(0.0, _f(item.get("unit_value")))
    if existing and increment_qty:
        current_qty = max(0.0, _f(existing.get("quantity_on_hand")))
        qty = current_qty + purchase_qty
    else:
        qty = purchase_qty
    return {
        "tool_name": _clean(item.get("tool_name")),
        "category": _clean(item.get("category") or "Other") or "Other",
        "model_number": _clean(item.get("model_number")),
        "quantity_on_hand": qty,
        "quantity_expected": qty,
        "unit": "EA",
        "unit_value": unit_value,
        "storage_type": "Warehouse",
        "status": "Available",
        "condition": "Good",
        "notes": "Updated from purchase list sync.",
        "skip_kit_sync": True,
    }


def upsert_hand_tool_from_purchase(
    item: dict[str, Any],
    *,
    dry_run: bool = False,
    increment_qty: bool = False,
) -> ServiceResult:
    existing = find_hand_tool_match(item)
    payload = _hand_tool_payload(item, existing=existing, increment_qty=increment_qty)
    if not payload["tool_name"]:
        return ServiceResult(ok=False, error="tool_name is required.")

    if existing:
        row_id = _clean(existing.get("id"))
        if dry_run:
            return ServiceResult(
                ok=True,
                data={
                    "action": "update",
                    "row_id": row_id,
                    "payload": payload,
                    "increment_qty": increment_qty,
                },
            )
        result = update_row_admin(
            _HAND_TOOLS,
            {**payload, "updated_at": _now_iso()},
            {"id": row_id},
        )
        if result.ok:
            clear_hand_tools_list_cache()
            return ServiceResult(
                ok=True,
                data={"action": "updated", "row_id": row_id, "payload": payload, "increment_qty": increment_qty},
            )
        return result

    if dry_run:
        return ServiceResult(ok=True, data={"action": "create", "payload": payload})
    result = import_hand_tool_row(payload)
    if result.ok:
        clear_hand_tools_list_cache()
        return ServiceResult(ok=True, data={"action": "created", "payload": payload, "row": result.data})
    return result


def update_serialized_from_purchase(item: dict[str, Any], *, dry_run: bool = False) -> ServiceResult:
    unit_value = max(0.0, _f(item.get("unit_value")))
    qty_hint = max(0, int(_f(item.get("qty"))))
    matches = find_serialized_matches(item)
    if not matches:
        return ServiceResult(
            ok=True,
            data={
                "action": "not_found",
                "updated": 0,
                "expected_qty": qty_hint,
                "message": f"No serialized asset matched: {_clean(item.get('tool_name'))}",
            },
        )

    updated_ids: list[str] = []
    for row in matches:
        row_id = _clean(row.get("id"))
        if not row_id:
            continue
        if dry_run:
            updated_ids.append(row_id)
            continue
        result = update_row_admin(
            _ASSETS,
            {
                "current_value": unit_value,
                "value": unit_value,
                "updated_at": _now_iso(),
            },
            {"id": row_id},
        )
        if not result.ok:
            return result
        updated_ids.append(row_id)

    action = "would_update" if dry_run else "updated"
    data: dict[str, Any] = {
        "action": action,
        "updated": len(updated_ids),
        "asset_ids": updated_ids,
        "expected_qty": qty_hint,
        "matched_qty": len(matches),
    }
    if qty_hint > len(matches):
        data["warning"] = (
            f"Purchase qty {qty_hint} exceeds {len(matches)} matched serialized asset(s); "
            "values updated on existing assets only."
        )
    return ServiceResult(ok=True, data=data)


def sync_hand_tools_purchase_list(
    *,
    items: list[dict[str, Any]] | None = None,
    batch: int | str | None = None,
    dry_run: bool = False,
    increment_qty: bool = True,
) -> ServiceResult:
    source = list(items) if items is not None else list(purchase_items_for_batch(batch))
    summary: dict[str, Any] = {
        "dry_run": dry_run,
        "increment_qty": increment_qty,
        "batch": batch,
        "hand_tools_created": 0,
        "hand_tools_updated": 0,
        "serialized_updated": 0,
        "serialized_not_found": 0,
        "serialized_fallback_hand_tools": 0,
        "errors": [],
        "warnings": [],
        "details": [],
    }

    for item in source:
        tracking = _clean(item.get("tracking") or "quantity").casefold()
        label = _clean(item.get("tool_name")) or _clean(item.get("model_number")) or "item"
        try:
            if tracking == "serialized":
                result = update_serialized_from_purchase(item, dry_run=dry_run)
                data = result.data or {}
                if result.ok and data.get("action") == "not_found":
                    summary["serialized_not_found"] += 1
                    result = upsert_hand_tool_from_purchase(
                        item,
                        dry_run=dry_run,
                        increment_qty=increment_qty,
                    )
                    tracking = "quantity"
                    summary["serialized_fallback_hand_tools"] += 1
            else:
                result = upsert_hand_tool_from_purchase(
                    item,
                    dry_run=dry_run,
                    increment_qty=increment_qty,
                )
        except Exception as exc:  # pragma: no cover - defensive guard for batch script
            summary["errors"].append(f"{label}: {exc}")
            continue

        if not result.ok:
            summary["errors"].append(f"{label}: {result.error or 'failed'}")
            continue

        data = result.data or {}
        summary["details"].append({"item": label, **data})
        action = _clean(data.get("action"))
        if tracking == "serialized":
            if action in {"updated", "would_update"}:
                summary["serialized_updated"] += int(data.get("updated") or 0)
            warning = _clean(data.get("warning"))
            if warning:
                summary["warnings"].append(warning)
        elif action in {"created", "create"}:
            summary["hand_tools_created"] += 1
        elif action in {"updated", "update"}:
            summary["hand_tools_updated"] += 1

    ok = not summary["errors"]
    message = (
        f"Purchase sync {'preview' if dry_run else 'complete'}: "
        f"{summary['hand_tools_created']} hand tool(s) created, "
        f"{summary['hand_tools_updated']} updated, "
        f"{summary['serialized_updated']} serialized asset value(s) updated."
    )
    if summary["serialized_fallback_hand_tools"]:
        message += f" {summary['serialized_fallback_hand_tools']} serialized line(s) added as small hand tools."
    if summary["errors"]:
        message += f" {len(summary['errors'])} error(s)."
    return ServiceResult(ok=ok, data=summary, error=summary["errors"][0] if summary["errors"] else None)


__all__ = [
    "find_hand_tool_match",
    "find_serialized_matches",
    "sync_hand_tools_purchase_list",
    "update_serialized_from_purchase",
    "upsert_hand_tool_from_purchase",
]
