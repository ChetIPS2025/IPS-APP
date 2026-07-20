"""Two-way sync between kit items and master tool records (serialized assets / small hand tools)."""

from __future__ import annotations

import re
from typing import Any, Literal

from app.services.repository import ServiceResult, delete_row, fetch_by_id, update_row

_HAND_TOOL_TAG = re.compile(r"hand_tool:(\S+)", re.I)

_SYNCABLE_ITEM_TYPES = frozenset({"Tool", "Equipment", "Safety Gear", "Accessory", "Other"})
_NON_SYNC_ITEM_TYPES = frozenset({"Consumable", "Material"})

_KIT_TO_SERIALIZED_STATUS = {
    "present": "Available",
    "checked out": "Checked Out",
    "missing": "Missing",
    "damaged": "Damaged",
    "needs replacement": "Out of Service",
    "retired": "Retired",
}

_KIT_TO_HAND_STATUS = {
    "present": "Available",
    "checked out": "In Use",
    "missing": "Missing",
    "damaged": "Damaged",
    "needs replacement": "Out of Service",
    "retired": "Retired",
}

TrackingMode = Literal["serialized", "hand_tool"]


def _clean_text(raw: object) -> str:
    return str(raw or "").strip()


def _has_serial(raw: object) -> bool:
    serial = _clean_text(raw)
    return bool(serial and serial.casefold() not in {"—", "-", "none", "null"})


def hand_tool_id_from_notes(notes: object) -> str | None:
    match = _HAND_TOOL_TAG.search(_clean_text(notes))
    return match.group(1) if match else None


def append_hand_tool_tag(notes: str, hand_tool_id: str) -> str:
    hid = _clean_text(hand_tool_id)
    if not hid:
        return _clean_text(notes)
    if hand_tool_id_from_notes(notes) == hid:
        return _clean_text(notes)
    tag = f"hand_tool:{hid}"
    base = _clean_text(notes)
    return f"{base} {tag}".strip() if base else tag


def kit_item_should_sync_to_master(data: dict[str, Any]) -> bool:
    if data.get("skip_master_sync"):
        return False
    if _clean_text(data.get("child_asset_id")):
        return False
    if _clean_text(data.get("inventory_item_id")):
        return False
    if hand_tool_id_from_notes(data.get("notes")):
        return False
    item_type = _clean_text(data.get("item_type") or "Tool")
    if item_type in _NON_SYNC_ITEM_TYPES:
        return False
    return item_type in _SYNCABLE_ITEM_TYPES or not item_type


def resolve_kit_item_tracking_mode(data: dict[str, Any]) -> TrackingMode | None:
    if not kit_item_should_sync_to_master(data):
        return None
    qty = float(data.get("quantity_expected") or data.get("quantity") or 1)
    if qty == 1 and _has_serial(data.get("serial_number")):
        return "serialized"
    return "hand_tool"


def _map_kit_category(category: object, *, name: str = "") -> str:
    from app.services.asset_classification_service import _map_category_to_hand_tool

    mapped = _map_category_to_hand_tool(_clean_text(category), name=_clean_text(name))
    return mapped or "Other"


def _kit_status_to_serialized(status: object) -> str:
    return _KIT_TO_SERIALIZED_STATUS.get(_clean_text(status).casefold(), "Available")


def _kit_status_to_hand(status: object) -> str:
    return _KIT_TO_HAND_STATUS.get(_clean_text(status).casefold(), "Available")


def validate_serialized_serial_for_kit(serial: str) -> ServiceResult | None:
    from app.services.serialized_tool_service import find_serialized_tool_by_serial

    cleaned = _clean_text(serial)
    if not cleaned:
        return None
    existing = find_serialized_tool_by_serial(cleaned)
    if existing:
        asset_no = _clean_text(existing.get("asset_number") or existing.get("asset_id"))
        asset_name = _clean_text(existing.get("asset_name") or existing.get("name") or "Existing tool")
        label = f"{asset_no} · {asset_name}" if asset_no else asset_name
        return ServiceResult(
            ok=False,
            error=(
                f"Serial {cleaned} is already registered as a serialized tool ({label}). "
                "Use Link Existing Asset or change the serial."
            ),
        )
    return None


def _link_kit_item_fields(
    kit_item_id: str,
    *,
    child_asset_id: str | None = None,
    notes: str | None = None,
) -> None:
    payload: dict[str, Any] = {"updated_at": _now_iso()}
    if child_asset_id is not None:
        payload["child_asset_id"] = child_asset_id or None
    if notes is not None:
        payload["notes"] = notes
    update_row("asset_kit_items", payload, {"id": kit_item_id})


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def sync_master_from_kit_item_create(
    parent_asset_id: str,
    kit_item_id: str,
    row: dict[str, Any],
    *,
    backfill: bool = False,
) -> ServiceResult:
    """Create serialized tool or small hand tool for a kit item and link it back."""
    mode = resolve_kit_item_tracking_mode(row)
    if not mode:
        return ServiceResult(ok=True, data={"synced": False})

    pid = _clean_text(parent_asset_id)
    kid = _clean_text(kit_item_id)
    if not pid or not kid:
        return ServiceResult(ok=False, error="Missing kit item context for sync.")

    def _rollback_kit_item() -> None:
        if not backfill:
            delete_row("asset_kit_items", {"id": kid})

    if mode == "serialized":
        serial = _clean_text(row.get("serial_number"))
        dup = validate_serialized_serial_for_kit(serial)
        if dup:
            _rollback_kit_item()
            return dup

        from app.services.serialized_tool_service import create_serialized_tool

        tool_result = create_serialized_tool(
            {
                "asset_name": _clean_text(row.get("item_name")),
                "category": _clean_text(row.get("category") or "Tool") or "Tool",
                "serial_number": serial,
                "condition": _clean_text(row.get("condition") or "Good") or "Good",
                "status": _kit_status_to_serialized(row.get("status")),
                "unit_value": row.get("unit_value"),
                "notes": _clean_text(row.get("notes") or row.get("description")),
                "trailer_id": pid,
                "skip_kit_sync": True,
            }
        )
        if not tool_result.ok:
            _rollback_kit_item()
            return tool_result

        tool_id = _clean_text((tool_result.data or {}).get("id"))
        if tool_id:
            _link_kit_item_fields(kid, child_asset_id=tool_id)
        return ServiceResult(ok=True, data={"synced": True, "mode": "serialized", "master_id": tool_id})

    from app.services.small_hand_tool_service import save_hand_tool

    qty = float(row.get("quantity_expected") or row.get("quantity_actual") or row.get("quantity") or 1)
    hand_result = save_hand_tool(
        {
            "tool_name": _clean_text(row.get("item_name")),
            "category": _map_kit_category(row.get("category"), name=_clean_text(row.get("item_name"))),
            "description": _clean_text(row.get("description") or ""),
            "quantity_on_hand": qty,
            "quantity_expected": qty,
            "unit": _clean_text(row.get("unit") or "EA") or "EA",
            "unit_value": row.get("unit_value"),
            "storage_type": "Tool Trailer",
            "container_asset_id": pid,
            "status": _kit_status_to_hand(row.get("status")),
            "condition": _clean_text(row.get("condition") or "Good") or "Good",
            "notes": _clean_text(row.get("notes") or ""),
            "skip_kit_sync": True,
        }
    )
    if not hand_result.ok:
        _rollback_kit_item()
        return hand_result

    hand_id = _clean_text((hand_result.data or {}).get("id"))
    if hand_id:
        _link_kit_item_fields(kid, notes=append_hand_tool_tag(_clean_text(row.get("notes")), hand_id))
    return ServiceResult(ok=True, data={"synced": True, "mode": "hand_tool", "master_id": hand_id})


def sync_master_from_kit_item_update(row: dict[str, Any], *, previous: dict[str, Any] | None = None) -> ServiceResult:
    """Push kit item edits to linked serialized asset or small hand tool."""
    if row.get("skip_master_sync"):
        return ServiceResult(ok=True, data={"synced": False})

    child_id = _clean_text(row.get("child_asset_id"))
    hand_id = hand_tool_id_from_notes(row.get("notes"))

    if child_id:
        payload: dict[str, Any] = {
            "asset_name": _clean_text(row.get("item_name")),
            "category": _clean_text(row.get("category") or "Tool") or "Tool",
            "serial_number": _clean_text(row.get("serial_number")),
            "condition": _clean_text(row.get("condition") or "Good") or "Good",
            "status": _kit_status_to_serialized(row.get("status")),
            "notes": _clean_text(row.get("notes") or row.get("description")),
            "last_seen_at": _now_iso(),
        }
        holder = row.get("assigned_to_employee_id")
        status_cf = _clean_text(row.get("status")).casefold()
        if status_cf == "checked out" and holder:
            payload["current_holder_employee_id"] = holder
            payload["assigned_employee"] = _clean_text(row.get("assigned_to_name")) or None
        elif status_cf == "present":
            payload["current_holder_employee_id"] = None
            payload["assigned_employee"] = ""

        if _has_serial(payload["serial_number"]):
            from app.services.serialized_tool_service import find_serialized_tool_by_serial

            existing = find_serialized_tool_by_serial(payload["serial_number"])
            if existing and _clean_text(existing.get("id")) != child_id:
                other = _clean_text(existing.get("asset_name") or existing.get("name") or "another tool")
                return ServiceResult(
                    ok=False,
                    error=f"Serial {payload['serial_number']} is already used by {other}.",
                )

        result = update_row("assets", payload, {"id": child_id})
        if not result.ok:
            return result
        return ServiceResult(ok=True, data={"synced": True, "mode": "serialized"})

    if hand_id:
        qty = float(row.get("quantity_actual") or row.get("quantity_expected") or row.get("quantity") or 1)
        payload = {
            "tool_name": _clean_text(row.get("item_name")),
            "category": _map_kit_category(row.get("category"), name=_clean_text(row.get("item_name"))),
            "description": _clean_text(row.get("description") or ""),
            "quantity_on_hand": qty,
            "quantity_expected": float(row.get("quantity_expected") or qty),
            "unit": _clean_text(row.get("unit") or "EA") or "EA",
            "unit_value": row.get("unit_value"),
            "condition": _clean_text(row.get("condition") or "Good") or "Good",
            "status": _kit_status_to_hand(row.get("status")),
            "notes": _clean_text(row.get("notes")),
            "updated_at": _now_iso(),
        }
        result = update_row("small_hand_tools", payload, {"id": hand_id})
        if not result.ok:
            return result
        return ServiceResult(ok=True, data={"synced": True, "mode": "hand_tool"})

    if kit_item_should_sync_to_master(row):
        mode = resolve_kit_item_tracking_mode(row)
        if mode:
            return sync_master_from_kit_item_create(
                _clean_text(row.get("parent_asset_id")),
                _clean_text(row.get("id")),
                row,
                backfill=True,
            )
    return ServiceResult(ok=True, data={"synced": False})


def sync_master_on_kit_item_delete(row: dict[str, Any]) -> None:
    """Detach or deactivate master records when a synced kit item is removed."""
    child_id = _clean_text(row.get("child_asset_id"))
    if child_id:
        asset = fetch_by_id("assets", child_id) or {}
        parent_id = _clean_text(row.get("parent_asset_id"))
        if _clean_text(asset.get("current_container_asset_id")) == parent_id:
            update_row(
                "assets",
                {
                    "current_container_asset_id": None,
                    "assigned_trailer_id": None,
                    "last_seen_at": _now_iso(),
                },
                {"id": child_id},
            )
        return

    hand_id = hand_tool_id_from_notes(row.get("notes"))
    if hand_id:
        update_row(
            "small_hand_tools",
            {"is_active": False, "updated_at": _now_iso()},
            {"id": hand_id},
        )


__all__ = [
    "append_hand_tool_tag",
    "hand_tool_id_from_notes",
    "kit_item_should_sync_to_master",
    "resolve_kit_item_tracking_mode",
    "sync_master_from_kit_item_create",
    "sync_master_from_kit_item_update",
    "sync_master_on_kit_item_delete",
    "validate_serialized_serial_for_kit",
]
