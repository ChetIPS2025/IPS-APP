"""Apply purchase-list quantities and unit prices to small hand tools and serialized assets."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.data.hand_tools_purchase_list import purchase_items_for_batch
from app.services.repository import (
    ServiceResult,
    fetch_rows_admin,
    insert_row_admin,
    update_row_admin,
)
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


def _normalize_tool_key(raw: object) -> str:
    text = _clean(raw).casefold()
    text = text.replace("–", "-").replace("—", "-")
    text = text.encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s/\"'.-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\bone-?key\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for suffix in (" vertical capacity", " vertical"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    text = text.replace(" padlocks", " padlock")
    if "ag1202fz" in text:
        return "flexzilla x3 blow gun ag1202fz"
    return text


def _load_hand_tools_index() -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    by_model: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    by_tool_key: dict[str, dict[str, Any]] = {}
    rows, _ = fetch_rows_admin(_HAND_TOOLS, limit=10000, order_by="tool_name")
    for row in rows or []:
        if not isinstance(row, dict) or row.get("is_active") is False:
            continue
        model_key = _normalize_name(row.get("model_number"))
        if model_key and model_key not in by_model:
            by_model[model_key] = row
        name_key = _normalize_name(row.get("tool_name"))
        if name_key and name_key not in by_name:
            by_name[name_key] = row
        tool_key = _normalize_tool_key(row.get("tool_name"))
        if tool_key and tool_key not in by_tool_key:
            by_tool_key[tool_key] = row
        if model_key and tool_key:
            composite = f"{model_key}|{tool_key}"
            if composite not in by_tool_key:
                by_tool_key[composite] = row
    return by_model, by_name, by_tool_key


def _load_serialized_assets() -> list[dict[str, Any]]:
    rows, _ = fetch_rows_admin(_ASSETS, limit=10000, order_by="asset_name")
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
    by_tool_key: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    if by_model is None or by_name is None or by_tool_key is None:
        by_model, by_name, by_tool_key = _load_hand_tools_index()
    model_key = _normalize_name(item.get("model_number"))
    if model_key:
        match = by_model.get(model_key)
        if match:
            return match
        composite = f"{model_key}|{_normalize_tool_key(item.get('tool_name'))}"
        match = by_tool_key.get(composite)
        if match:
            return match
    name_key = _normalize_name(item.get("tool_name"))
    if name_key:
        match = by_name.get(name_key)
        if match:
            return match
    tool_key = _normalize_tool_key(item.get("tool_name"))
    if tool_key:
        return by_tool_key.get(tool_key)
    return None


def consolidate_hand_tool_duplicates(*, dry_run: bool = False) -> ServiceResult:
    """Merge duplicate small hand tool rows that share a normalized tool key."""
    rows, err = fetch_rows_admin(_HAND_TOOLS, limit=10000, order_by="tool_name")
    if err:
        return ServiceResult(ok=False, error=err)
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows or []:
        if not isinstance(row, dict) or row.get("is_active") is False:
            continue
        key = _normalize_tool_key(row.get("tool_name"))
        if not key:
            continue
        groups.setdefault(key, []).append(row)

    merged = 0
    deactivated = 0
    for key, group in groups.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda r: str(r.get("created_at") or r.get("id") or ""))
        keeper = group[0]
        keeper_id = _clean(keeper.get("id"))
        if not keeper_id:
            continue
        total_qty = sum(max(0.0, _f(r.get("quantity_on_hand"))) for r in group)
        total_exp = sum(max(0.0, _f(r.get("quantity_expected"))) for r in group)
        unit_value = max(_f(r.get("unit_value")) for r in group)
        model_number = _clean(keeper.get("model_number"))
        for row in group:
            if not model_number:
                model_number = _clean(row.get("model_number"))
        if dry_run:
            merged += 1
            deactivated += len(group) - 1
            continue
        result = update_row_admin(
            _HAND_TOOLS,
            {
                "quantity_on_hand": total_qty,
                "quantity_expected": max(total_exp, total_qty),
                "unit_value": unit_value,
                "model_number": model_number or None,
                "updated_at": _now_iso(),
            },
            {"id": keeper_id},
        )
        if not result.ok:
            return result
        for row in group[1:]:
            row_id = _clean(row.get("id"))
            if not row_id:
                continue
            deactivate = update_row_admin(
                _HAND_TOOLS,
                {"is_active": False, "updated_at": _now_iso()},
                {"id": row_id},
            )
            if not deactivate.ok:
                return deactivate
            deactivated += 1
        merged += 1

    if merged and not dry_run:
        clear_hand_tools_list_cache()
    return ServiceResult(
        ok=True,
        data={
            "merged_groups": merged,
            "deactivated_rows": deactivated,
            "dry_run": dry_run,
        },
    )


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
    "consolidate_hand_tool_duplicates",
    "find_hand_tool_match",
    "find_serialized_matches",
    "sync_hand_tools_purchase_list",
    "update_serialized_from_purchase",
    "upsert_hand_tool_from_purchase",
]
