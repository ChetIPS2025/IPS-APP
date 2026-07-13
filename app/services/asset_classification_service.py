"""Classify assets into Equipment, Serialized Tools, or Small Tools tabs."""

from __future__ import annotations

from typing import Any, Literal

from app.services.asset_kits_service import asset_is_kit
from app.services.repository import ServiceResult, fetch_rows, update_row
from app.services.small_hand_tool_service import save_hand_tool
TrackingType = Literal["equipment", "serialized", "quantity"]

TRACKING_TYPES: tuple[str, ...] = ("equipment", "serialized", "quantity")
SERIAL_NEEDS_STATUS = "Needs Serial"

TRACKING_TAB_LABELS: dict[str, str] = {
    "equipment": "Equipment",
    "serialized": "Serialized Tools",
    "quantity": "Small Tools",
}

_HAND_TOOLS = "small_hand_tools"
_ASSETS = "assets"

_PLACEHOLDER_SERIAL = frozenset({"—", "-", "none", "null", ""})


def _clean_text(raw: object) -> str:
    return str(raw or "").strip()


def _has_serial(raw: object) -> bool:
    serial = _clean_text(raw)
    return bool(serial and serial.casefold() not in _PLACEHOLDER_SERIAL)


def find_asset_by_serial(serial: str, *, exclude_asset_id: str = "") -> dict[str, Any] | None:
    """Return another asset that already uses this serial number, if any."""
    serial_clean = _clean_text(serial)
    if not _has_serial(serial_clean):
        return None
    exclude = _clean_text(exclude_asset_id)
    serial_cf = serial_clean.casefold()
    rows, _ = fetch_rows(_ASSETS, limit=10000)
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        rid = _clean_text(row.get("id"))
        if exclude and rid == exclude:
            continue
        other = _clean_text(row.get("serial_number"))
        if other and other.casefold() == serial_cf:
            return row
    return None


def validate_serial_numbers_for_bulk(
    asset_ids: list[str],
    serial_by_id: dict[str, str],
    *,
    assets_by_id: dict[str, dict[str, Any]] | None = None,
) -> tuple[bool, str]:
    """Validate uniqueness for serials entered during bulk move; blank serials are allowed."""
    assets = assets_by_id or {}
    seen: dict[str, str] = {}
    for aid in asset_ids:
        asset = assets.get(aid) or {}
        inline = serial_by_id.get(aid)
        if inline is not None:
            serial = _clean_text(inline)
        else:
            serial = _clean_text(asset.get("serial_number"))
        if not _has_serial(serial):
            continue
        serial_cf = serial.casefold()
        if serial_cf in seen:
            return False, f"Duplicate serial number in this move: {serial}."
        seen[serial_cf] = aid
        existing = find_asset_by_serial(serial, exclude_asset_id=aid)
        if existing:
            other_label = _clean_text(existing.get("asset_name") or existing.get("name")) or "another asset"
            return False, f"Serial number {serial} is already assigned to {other_label}."
    return True, ""


def _normalize_tracking_type(raw: object) -> str:
    tt = _clean_text(raw).casefold().replace(" ", "_").replace("-", "_")
    aliases = {
        "equipment": "equipment",
        "serialized_tool": "serialized",
        "serialized": "serialized",
        "serial": "serialized",
        "small_tool": "quantity",
        "quantity": "quantity",
        "hand_tool": "quantity",
        "small_hand_tool": "quantity",
    }
    return aliases.get(tt, "")


def resolve_tracking_type(asset: dict[str, Any]) -> TrackingType:
    """Return which Assets tab this record belongs on."""
    explicit = _normalize_tracking_type(asset.get("tracking_type"))
    if explicit in TRACKING_TYPES:
        return explicit  # type: ignore[return-value]

    if asset_is_kit(asset):
        return "equipment"

    if asset.get("is_serialized_tool"):
        return "serialized"

    if asset.get("is_checkout_item") and _has_serial(asset.get("serial_number")):
        return "serialized"

    if _has_serial(asset.get("serial_number")):
        cat = _clean_text(asset.get("category") or asset.get("asset_type")).casefold()
        if cat == "tool":
            return "serialized"

    return "equipment"


def tracking_type_label(asset: dict[str, Any]) -> str:
    return TRACKING_TAB_LABELS.get(resolve_tracking_type(asset), "Equipment")


def asset_belongs_to_tab(asset: dict[str, Any], tab: TrackingType) -> bool:
    return resolve_tracking_type(asset) == tab


def is_equipment_tab_asset(asset: dict[str, Any]) -> bool:
    return asset_belongs_to_tab(asset, "equipment")


def is_serialized_tab_asset(asset: dict[str, Any]) -> bool:
    if asset_is_kit(asset):
        return False
    return asset_belongs_to_tab(asset, "serialized")


def _find_hand_tool_by_source(asset_id: str) -> dict[str, Any] | None:
    aid = _clean_text(asset_id)
    if not aid:
        return None
    rows, _ = fetch_rows(_HAND_TOOLS, limit=5000)
    for row in rows or []:
        if not isinstance(row, dict) or row.get("is_active") is False:
            continue
        if _clean_text(row.get("source_asset_id")) == aid:
            return row
    return None


def _deactivate_hand_tool_for_asset(asset_id: str) -> None:
    row = _find_hand_tool_by_source(asset_id)
    if row and row.get("id"):
        update_row(_HAND_TOOLS, {"is_active": False}, {"id": str(row["id"])})


def _map_category_to_hand_tool(category: str, *, name: str = "") -> str:
    haystack = f"{_clean_text(category)} {_clean_text(name)}".casefold()
    if not haystack.strip() or haystack.strip() == "—":
        return "Other"
    keyword_map = (
        ("pliers", "Pliers"),
        ("screwdriver", "Screwdrivers"),
        ("wrench", "Wrenches"),
        ("socket", "Sockets"),
        ("clamp", "Clamps"),
        ("hammer", "Hammers"),
        ("tape measure", "Tape Measures"),
        ("level", "Levels"),
        ("cutter", "Cutters"),
        ("tester", "Other"),
    )
    for needle, label in keyword_map:
        if needle in haystack:
            return label
    for opt in (
        "Pliers",
        "Screwdrivers",
        "Wrenches",
        "Clamps",
        "Hammers",
        "Tape Measures",
        "Levels",
        "Sockets",
        "Cutters",
    ):
        if opt.casefold() in haystack:
            return opt
    cat = _clean_text(category)
    if cat.casefold() == "tool":
        return "Other"
    return cat if len(cat) < 40 else "Other"


def reclassify_asset(
    asset_id: str,
    target: str,
    *,
    serial_number: str | None = None,
    quantity_on_hand: float = 1.0,
    quantity_expected: float = 1.0,
    storage_type: str = "Warehouse",
    storage_location: str = "",
    container_asset_id: str = "",
    notes: str = "",
) -> ServiceResult:
    """Move an existing asset between Equipment, Serialized Tools, and Small Tools."""
    from app.services.repository import fetch_by_id
    aid = _clean_text(asset_id)
    bucket = _normalize_tracking_type(target)
    if bucket not in TRACKING_TYPES:
        return ServiceResult(ok=False, error="Choose Equipment, Serialized Tools, or Small Tools.")

    asset = fetch_by_id(_ASSETS, aid) or {}
    if not asset:
        return ServiceResult(ok=False, error="Asset not found.")

    if asset_is_kit(asset) and bucket != "equipment":
        return ServiceResult(
            ok=False,
            error="Tool Trailers and kit containers must stay on the Equipment tab.",
        )

    current = resolve_tracking_type(asset)
    if current == bucket:
        return ServiceResult(ok=True, data={"asset_id": aid, "tracking_type": bucket, "unchanged": True})

    payload: dict[str, Any] = {"tracking_type": bucket}

    if bucket == "equipment":
        payload.update(
            {
                "is_serialized_tool": False,
                "is_checkout_item": False,
            }
        )
        _deactivate_hand_tool_for_asset(aid)

    elif bucket == "serialized":
        if serial_number is not None:
            serial = _clean_text(serial_number)
        else:
            serial = _clean_text(asset.get("serial_number"))
        if _has_serial(serial):
            existing = find_asset_by_serial(serial, exclude_asset_id=aid)
            if existing:
                other_label = _clean_text(existing.get("asset_name") or existing.get("name")) or "another asset"
                return ServiceResult(
                    ok=False,
                    error=f"Serial number {serial} is already assigned to {other_label}.",
                )
            status = _clean_text(asset.get("status")) or "Available"
            if status == SERIAL_NEEDS_STATUS:
                status = "Available"
            payload.update(
                {
                    "serial_number": serial,
                    "is_serialized_tool": True,
                    "is_checkout_item": True,
                    "status": status,
                }
            )
        else:
            payload.update(
                {
                    "serial_number": "",
                    "is_serialized_tool": True,
                    "is_checkout_item": True,
                    "status": SERIAL_NEEDS_STATUS,
                }
            )
        _deactivate_hand_tool_for_asset(aid)

    elif bucket == "quantity":
        payload.update(
            {
                "is_serialized_tool": False,
                "is_checkout_item": False,
            }
        )
        loc = _clean_text(storage_location) or _clean_text(asset.get("location"))
        storage = _clean_text(storage_type) or ("Warehouse" if not loc else "Shop")
        hand_result = save_hand_tool(
            {
                "tool_name": _clean_text(asset.get("asset_name") or asset.get("name")),
                "category": _map_category_to_hand_tool(
                    _clean_text(asset.get("category")),
                    name=_clean_text(asset.get("asset_name") or asset.get("name")),
                ),
                "description": _clean_text(asset.get("description") or asset.get("notes")),
                "quantity_on_hand": quantity_on_hand,
                "quantity_expected": quantity_expected,
                "unit_value": float(asset.get("current_value") or asset.get("value") or 0),
                "storage_type": storage,
                "storage_location": loc,
                "container_asset_id": _clean_text(container_asset_id) or None,
                "assigned_job_id": asset.get("assigned_job_id"),
                "status": "Available",
                "condition": _clean_text(asset.get("condition") or "Good") or "Good",
                "notes": (
                    f"{_clean_text(asset.get('notes') or asset.get('description'))} "
                    f"Reclassified from asset {aid}."
                ).strip(),
                "source_asset_id": aid,
            },
            row_id=str((_find_hand_tool_by_source(aid) or {}).get("id") or "") or None,
        )
        if not hand_result.ok:
            return ServiceResult(
                ok=False,
                error=hand_result.error or "Asset updated, but Small Tools row could not be created.",
            )

    result = update_row(_ASSETS, payload, {"id": aid})
    if result.ok:
        if bucket == "serialized":
            from app.services.assets_service import rebuild_asset_qr
            merged = {**asset, **payload}
            rebuild_asset_qr(merged)
        data = dict(result.data or {})
        data["tracking_type"] = bucket
        data["tab"] = TRACKING_TAB_LABELS[bucket]
        return ServiceResult(ok=True, data=data)
    return result


def reclassify_assets_bulk(
    asset_ids: list[str],
    target: str,
    *,
    serial_numbers: dict[str, str] | None = None,
) -> ServiceResult:
    """Move multiple assets to the same tab. Skips kits and invalid rows; reports per-item errors."""
    bucket = _normalize_tracking_type(target)
    if bucket not in TRACKING_TYPES:
        return ServiceResult(ok=False, error="Choose Equipment, Serialized Tools, or Small Tools.")

    ids = [_clean_text(aid) for aid in asset_ids if _clean_text(aid)]
    if not ids:
        return ServiceResult(ok=False, error="Select at least one asset.")

    serial_map = {_clean_text(k): _clean_text(v) for k, v in (serial_numbers or {}).items() if _clean_text(k)}

    moved: list[str] = []
    unchanged: list[str] = []
    skipped: list[dict[str, str]] = []

    for aid in ids:
        kwargs: dict[str, Any] = {}
        if bucket == "serialized" and aid in serial_map:
            kwargs["serial_number"] = serial_map[aid]
        result = reclassify_asset(aid, bucket, **kwargs)
        if result.ok:
            if result.data and result.data.get("unchanged"):
                unchanged.append(aid)
            else:
                moved.append(aid)
        else:
            skipped.append({"id": aid, "error": str(result.error or "Could not move asset.")})

    tab = TRACKING_TAB_LABELS[bucket]
    if not moved and not unchanged and skipped:
        first = skipped[0]["error"] if skipped else "No assets could be moved."
        return ServiceResult(
            ok=False,
            error=first,
            data={"moved": moved, "unchanged": unchanged, "skipped": skipped, "target": bucket},
        )

    parts: list[str] = []
    if moved:
        parts.append(f"Moved {len(moved)} to {tab}.")
    if unchanged:
        parts.append(f"{len(unchanged)} already on {tab}.")
    if skipped:
        parts.append(f"{len(skipped)} skipped.")

    return ServiceResult(
        ok=True,
        data={
            "moved": moved,
            "unchanged": unchanged,
            "skipped": skipped,
            "target": bucket,
            "message": " ".join(parts),
        },
    )


__all__ = [
    "SERIAL_NEEDS_STATUS",
    "TRACKING_TAB_LABELS",
    "TRACKING_TYPES",
    "asset_belongs_to_tab",
    "find_asset_by_serial",
    "is_equipment_tab_asset",
    "is_serialized_tab_asset",
    "reclassify_asset",
    "reclassify_assets_bulk",
    "resolve_tracking_type",
    "tracking_type_label",
    "validate_serial_numbers_for_bulk",
]
