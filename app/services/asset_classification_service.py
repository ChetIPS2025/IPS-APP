"""Classify assets into Equipment, Serialized Tools, or Small Tools tabs."""

from __future__ import annotations

from typing import Any, Literal

try:
    from app.services.asset_kits_service import asset_is_kit
    from app.services.repository import ServiceResult, clear_all_data_caches, fetch_rows, update_row
    from app.services.small_hand_tool_service import save_hand_tool
except ImportError:
    from services.asset_kits_service import asset_is_kit  # type: ignore
    from services.repository import ServiceResult, clear_all_data_caches, fetch_rows, update_row  # type: ignore
    from services.small_hand_tool_service import save_hand_tool  # type: ignore

TrackingType = Literal["equipment", "serialized", "quantity"]

TRACKING_TYPES: tuple[str, ...] = ("equipment", "serialized", "quantity")

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
    serial_number: str = "",
    quantity_on_hand: float = 1.0,
    quantity_expected: float = 1.0,
    storage_type: str = "Warehouse",
    storage_location: str = "",
    container_asset_id: str = "",
    notes: str = "",
) -> ServiceResult:
    """Move an existing asset between Equipment, Serialized Tools, and Small Tools."""
    try:
        from app.services.repository import fetch_by_id
    except ImportError:
        from services.repository import fetch_by_id  # type: ignore

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
        serial = _clean_text(serial_number) or _clean_text(asset.get("serial_number"))
        if not _has_serial(serial):
            return ServiceResult(
                ok=False,
                error="Serialized tools require a serial number. Enter one before reclassifying.",
            )
        payload.update(
            {
                "serial_number": serial,
                "is_serialized_tool": True,
                "is_checkout_item": True,
                "status": _clean_text(asset.get("status")) or "Available",
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
            try:
                from app.services.assets_service import rebuild_asset_qr
            except ImportError:
                from services.assets_service import rebuild_asset_qr  # type: ignore
            merged = {**asset, **payload}
            rebuild_asset_qr(merged)
        clear_all_data_caches()
        data = dict(result.data or {})
        data["tracking_type"] = bucket
        data["tab"] = TRACKING_TAB_LABELS[bucket]
        return ServiceResult(ok=True, data=data)
    return result


def reclassify_assets_bulk(asset_ids: list[str], target: str) -> ServiceResult:
    """Move multiple assets to the same tab. Skips kits and invalid rows; reports per-item errors."""
    bucket = _normalize_tracking_type(target)
    if bucket not in TRACKING_TYPES:
        return ServiceResult(ok=False, error="Choose Equipment, Serialized Tools, or Small Tools.")

    ids = [_clean_text(aid) for aid in asset_ids if _clean_text(aid)]
    if not ids:
        return ServiceResult(ok=False, error="Select at least one asset.")

    moved: list[str] = []
    unchanged: list[str] = []
    skipped: list[dict[str, str]] = []

    for aid in ids:
        result = reclassify_asset(aid, bucket)
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
    "TRACKING_TAB_LABELS",
    "TRACKING_TYPES",
    "asset_belongs_to_tab",
    "is_equipment_tab_asset",
    "is_serialized_tab_asset",
    "reclassify_asset",
    "reclassify_assets_bulk",
    "resolve_tracking_type",
    "tracking_type_label",
]
