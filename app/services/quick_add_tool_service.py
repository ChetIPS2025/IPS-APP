"""Unified quick-add for Serialized Tools, Small Tools, and Inventory consumables."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

try:
    from app.services.asset_classification_service import _map_category_to_hand_tool
    from app.services.repository import ServiceResult, clear_all_data_caches
    from app.services.serialized_tool_service import create_serialized_tool
    from app.services.small_hand_tool_service import HAND_TOOL_CATEGORIES, save_hand_tool
except ImportError:
    from services.asset_classification_service import _map_category_to_hand_tool  # type: ignore
    from services.repository import ServiceResult, clear_all_data_caches  # type: ignore
    from services.serialized_tool_service import create_serialized_tool  # type: ignore
    from services.small_hand_tool_service import HAND_TOOL_CATEGORIES, save_hand_tool  # type: ignore

TOOL_KINDS: tuple[str, ...] = ("serialized", "small", "inventory")

TOOL_KIND_LABELS: dict[str, str] = {
    "serialized": "Serialized Tools",
    "small": "Small Tools",
    "inventory": "Inventory (consumables)",
}

_IMPORT_ALIASES: dict[str, str] = {
    "tool_name": "tool_name",
    "name": "tool_name",
    "asset_name": "tool_name",
    "item_name": "tool_name",
    "serial": "serial_number",
    "serial_number": "serial_number",
    "serial_no": "serial_number",
    "model": "model",
    "manufacturer": "manufacturer",
    "mfr": "manufacturer",
    "category": "category",
    "tool_type": "tool_kind",
    "type": "tool_kind",
    "tracking_type": "tool_kind",
    "quantity": "quantity",
    "qty": "quantity",
    "quantity_on_hand": "quantity",
    "unit_cost": "unit_cost",
    "unit_value": "unit_cost",
    "notes": "notes",
    "asset_number": "asset_number",
    "asset_type": "asset_type",
    "storage_location": "storage_location",
    "location": "storage_location",
    "vendor": "vendor",
    "trailer_asset_number": "trailer_asset_number",
}


def _clean(raw: object) -> str:
    return str(raw or "").strip()


def _norm_col(name: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().casefold()).strip("_")
    return _IMPORT_ALIASES.get(key, key)


def _norm_kind(raw: object) -> str:
    text = _clean(raw).casefold().replace(" ", "_").replace("-", "_")
    mapping = {
        "serialized": "serialized",
        "serialized_tool": "serialized",
        "serialized_tools": "serialized",
        "serial": "serialized",
        "milwaukee": "serialized",
        "small": "small",
        "small_tool": "small",
        "small_tools": "small",
        "quantity": "small",
        "hand_tool": "small",
        "inventory": "inventory",
        "consumable": "inventory",
        "consumables": "inventory",
    }
    return mapping.get(text, "")


def parse_bulk_import_file(data: bytes, filename: str) -> list[dict[str, Any]]:
    """Parse CSV or XLSX into normalized row dicts."""
    name = _clean(filename).casefold()
    rows: list[dict[str, Any]] = []

    if name.endswith((".xlsx", ".xls")):
        import pandas as pd

        df = pd.read_excel(io.BytesIO(data))
        raw_rows = df.to_dict(orient="records")
    else:
        text = data.decode("utf-8-sig", errors="replace")
        raw_rows = list(csv.DictReader(io.StringIO(text)))

    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        norm: dict[str, Any] = {}
        for col, val in raw.items():
            if val is None or (isinstance(val, float) and val != val):
                continue
            key = _norm_col(str(col))
            if key:
                norm[key] = val
        if norm:
            rows.append(norm)
    return rows


def _resolve_trailer_id(asset_number: str) -> str:
    num = _clean(asset_number)
    if not num:
        return ""
    try:
        from app.services.repository import fetch_rows
    except ImportError:
        from services.repository import fetch_rows  # type: ignore
    assets, _ = fetch_rows("assets", limit=5000)
    for row in assets or []:
        if not isinstance(row, dict):
            continue
        if _clean(row.get("asset_number")) == num or _clean(row.get("asset_id")) == num:
            return _clean(row.get("id"))
    return ""


EXISTING_ASSET_FOUND_CODE = "existing_asset_found"


def lookup_existing_serialized_by_serial(serial: str) -> dict[str, Any] | None:
    """Return existing serialized asset metadata when serial is already in use."""
    try:
        from app.services.serialized_tool_service import find_serialized_tool_by_serial
    except ImportError:
        from services.serialized_tool_service import find_serialized_tool_by_serial  # type: ignore

    cleaned = _clean(serial)
    if not cleaned:
        return None
    existing = find_serialized_tool_by_serial(cleaned)
    if not existing:
        return None
    return {
        "code": EXISTING_ASSET_FOUND_CODE,
        "existing_asset": existing,
        "serial_number": cleaned,
    }


def is_duplicate_serial_result(result: ServiceResult) -> bool:
    data = result.data if isinstance(result.data, dict) else {}
    return bool(data.get("duplicate")) or str(data.get("code") or "") in {
        "duplicate_serial",
        EXISTING_ASSET_FOUND_CODE,
    }


def check_serialized_serial_duplicate(serial: str) -> ServiceResult:
    """Pre-save guard when a serialized tool with this serial already exists."""
    found = lookup_existing_serialized_by_serial(serial)
    if not found:
        return ServiceResult(ok=True)
    existing = found.get("existing_asset") or {}
    cleaned = _clean(serial)
    asset_no = _clean(existing.get("asset_number") or existing.get("asset_id"))
    asset_name = _clean(existing.get("asset_name") or existing.get("name") or "Existing tool")
    label = f"{asset_no} · {asset_name}" if asset_no else asset_name
    return ServiceResult(
        ok=False,
        error=(
            f"Existing asset found for serial {cleaned}: {label}. "
            "Use View, Add photo, or Update missing info — or change the serial to create a new tool."
        ),
        data={**found, "duplicate": True},
    )


def merge_serialized_tool_from_intake(asset_id: str, data: dict[str, Any]) -> ServiceResult:
    try:
        from app.services.serialized_tool_service import merge_serialized_tool_fields
    except ImportError:
        from services.serialized_tool_service import merge_serialized_tool_fields  # type: ignore
    result = merge_serialized_tool_fields(asset_id, data)
    if result.ok:
        clear_all_data_caches()
    return result


def quick_add_tool(
    kind: str,
    data: dict[str, Any],
    *,
    trailer_id: str = "",
) -> ServiceResult:
    """Create one tool row in the correct bucket."""
    bucket = _norm_kind(kind) or _norm_kind(data.get("tool_kind"))
    if bucket not in TOOL_KINDS:
        return ServiceResult(ok=False, error="Choose Serialized Tools, Small Tools, or Inventory.")

    if bucket == "serialized":
        result = create_serialized_tool(
            {
                **data,
                "asset_name": data.get("tool_name") or data.get("asset_name"),
                "current_container_asset_id": trailer_id or data.get("trailer_id"),
            }
        )
        if result.ok and result.data:
            try:
                from app.services.repository import update_row
            except ImportError:
                from services.repository import update_row  # type: ignore
            tool_id = _clean((result.data or {}).get("id"))
            if tool_id:
                update_row("assets", {"tracking_type": "serialized"}, {"id": tool_id})
        return result

    if bucket == "small":
        tool_name = _clean(data.get("tool_name") or data.get("asset_name"))
        if not tool_name:
            return ServiceResult(ok=False, error="Tool name is required.")
        qty = float(data.get("quantity") or data.get("quantity_on_hand") or 1)
        cat = _clean(data.get("category"))
        if not cat or cat not in HAND_TOOL_CATEGORIES:
            cat = _map_category_to_hand_tool(cat, name=tool_name)
        return save_hand_tool(
            {
                "tool_name": tool_name,
                "category": cat,
                "description": _clean(data.get("description") or data.get("notes")),
                "quantity_on_hand": qty,
                "quantity_expected": float(data.get("quantity_expected") or qty),
                "unit_value": float(data.get("unit_cost") or data.get("unit_value") or 0),
                "storage_type": _clean(data.get("storage_type") or "Warehouse") or "Warehouse",
                "storage_location": _clean(data.get("storage_location")),
                "container_asset_id": trailer_id or data.get("container_asset_id"),
                "status": _clean(data.get("status") or "Available") or "Available",
                "condition": _clean(data.get("condition") or "Good") or "Good",
                "notes": _clean(data.get("notes")),
            }
        )

    # inventory consumables
    try:
        from app.services.phase2_modules_service import save_inventory_item
    except ImportError:
        from services.phase2_modules_service import save_inventory_item  # type: ignore

    item_name = _clean(data.get("tool_name") or data.get("item_name") or data.get("asset_name"))
    if not item_name:
        return ServiceResult(ok=False, error="Item name is required.")
    return save_inventory_item(
        {
            "name": item_name,
            "item_name": item_name,
            "category": _clean(data.get("category") or "Consumables") or "Consumables",
            "location": _clean(data.get("storage_location") or data.get("location")),
            "qty_on_hand": float(data.get("quantity") or data.get("quantity_on_hand") or 0),
            "unit_cost": float(data.get("unit_cost") or 0),
            "vendor": _clean(data.get("vendor")),
            "status": _clean(data.get("status") or "In Stock") or "In Stock",
            "description": _clean(data.get("notes") or data.get("description")),
        }
    )


def bulk_import_tools(
    rows: list[dict[str, Any]],
    *,
    default_kind: str = "serialized",
    default_trailer_id: str = "",
) -> ServiceResult:
    """Import many tools from parsed spreadsheet rows."""
    created = 0
    errors: list[str] = []

    for idx, row in enumerate(rows, start=1):
        kind = _norm_kind(row.get("tool_kind")) or _norm_kind(default_kind) or "serialized"
        trailer_id = default_trailer_id or _resolve_trailer_id(_clean(row.get("trailer_asset_number")))
        payload = dict(row)
        payload["tool_kind"] = kind
        if kind == "serialized" and not _clean(payload.get("serial_number")):
            errors.append(f"Row {idx}: serial number required for Serialized Tools.")
            continue
        result = quick_add_tool(kind, payload, trailer_id=trailer_id)
        if result.ok:
            created += 1
        else:
            errors.append(f"Row {idx}: {result.error or 'failed'}")

    if created == 0 and errors:
        return ServiceResult(ok=False, error="; ".join(errors[:5]), data={"created": 0, "errors": errors})

    clear_all_data_caches()
    return ServiceResult(
        ok=True,
        data={"created": created, "errors": errors, "message": f"Imported {created} item(s)."},
    )


def attach_tool_photo(asset_id: str, uploaded: Any, *, uploaded_by: str | None = None) -> ServiceResult:
    """Save original upload for evidence and a converted preview for thumbnails/OCR."""
    try:
        from app.services.upload_media_strategy import attach_asset_photo_with_preview
    except ImportError:
        from services.upload_media_strategy import attach_asset_photo_with_preview  # type: ignore
    return attach_asset_photo_with_preview(asset_id, uploaded, uploaded_by=uploaded_by)


def analyze_tool_photos(
    uploads: list[tuple[bytes, str]],
    *,
    kind_hint: str = "",
) -> ServiceResult:
    """Extract tool fields, default upload primary, and optional catalog product suggestions."""
    if not uploads:
        return ServiceResult(ok=False, error="Upload at least one photo or document.")
    try:
        from app.services.tool_intake_ai_service import extract_tool_from_photos
        from app.services.tool_preview_image_service import (
            find_product_image_suggestions,
            pick_best_upload_preview,
            preview_image_to_dict,
        )
    except ImportError:
        from services.tool_intake_ai_service import extract_tool_from_photos  # type: ignore
        from services.tool_preview_image_service import (  # type: ignore
            find_product_image_suggestions,
            pick_best_upload_preview,
            preview_image_to_dict,
        )

    try:
        extracted = extract_tool_from_photos(uploads, kind_hint=kind_hint)
        upload_preview = pick_best_upload_preview(uploads)
        suggestions = find_product_image_suggestions(extracted)
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))

    return ServiceResult(
        ok=True,
        data={
            "extracted": extracted,
            "preview_bytes": upload_preview.preview_bytes,
            "preview_filename": upload_preview.preview_filename,
            "preview_source": upload_preview.source,
            "preview_source_label": upload_preview.source_label,
            "product_suggestions": [preview_image_to_dict(s) for s in suggestions],
            "upload_count": len(uploads),
        },
    )


def attach_tool_photos_bundle(
    asset_id: str,
    uploads: list[Any],
    *,
    primary_preview_bytes: bytes | None = None,
    primary_preview_filename: str = "preview.jpg",
    uploaded_by: str | None = None,
) -> ServiceResult:
    """Save all source uploads and set the chosen primary preview on the asset."""
    try:
        from app.services.upload_media_strategy import attach_asset_photos_bundle
    except ImportError:
        from services.upload_media_strategy import attach_asset_photos_bundle  # type: ignore
    result = attach_asset_photos_bundle(
        asset_id,
        uploads,
        primary_preview_bytes=primary_preview_bytes,
        primary_preview_filename=primary_preview_filename,
        uploaded_by=uploaded_by,
    )
    if result.ok:
        clear_all_data_caches()
    return result


def attach_tool_receipt(asset: dict[str, Any], uploaded: Any, *, uploaded_by: str | None = None) -> ServiceResult:
    if not asset or uploaded is None:
        return ServiceResult(ok=False, error="Asset and receipt are required.")
    try:
        from app.services.asset_document_util import persist_asset_document_upload
    except ImportError:
        from services.asset_document_util import persist_asset_document_upload  # type: ignore
    try:
        persist_asset_document_upload(
            asset_row=asset,
            uploaded=uploaded,
            document_type="Receipt",
            notes="Quick Add Tool receipt",
            uploaded_by=uploaded_by,
        )
        clear_all_data_caches()
        return ServiceResult(ok=True, data={"attached": True})
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))


__all__ = [
    "TOOL_KIND_LABELS",
    "TOOL_KINDS",
    "analyze_tool_photos",
    "attach_tool_photo",
    "attach_tool_photos_bundle",
    "attach_tool_receipt",
    "bulk_import_tools",
    "EXISTING_ASSET_FOUND_CODE",
    "check_serialized_serial_duplicate",
    "is_duplicate_serial_result",
    "lookup_existing_serialized_by_serial",
    "merge_serialized_tool_from_intake",
    "parse_bulk_import_file",
    "quick_add_tool",
]
