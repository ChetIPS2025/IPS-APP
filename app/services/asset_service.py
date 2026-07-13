from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

_LOG = logging.getLogger(__name__)

from app.db import (
    delete_rows_admin,
    delete_storage_object_admin,
    fetch_by_match,
    fetch_table,
    fetch_one,
    insert_row_admin,
    update_rows_admin,
    upload_bytes_admin,
)
from app.services.asset_duplicate_service import find_possible_duplicates
from app.services.asset_maintenance_service import calculate_next_service
def next_asset_id(assets: list[dict]) -> str:
    nums: list[int] = []
    for asset in assets:
        asset_id = str(asset.get("asset_id", "")).upper().replace("AST-", "").strip()
        if asset_id.isdigit():
            nums.append(int(asset_id))
    next_num = max(nums) + 1 if nums else 1
    return f"AST-{next_num:04d}"


def make_unique_asset_name(name: str, assets: list[dict]) -> str:
    existing = {str(a.get("asset_name", "")).strip().lower() for a in assets}
    final_name = name.strip() or "Unnamed Asset"
    if final_name.lower() not in existing:
        return final_name

    idx = 2
    base_name = final_name
    while f"{base_name} {idx}".lower() in existing:
        idx += 1
    return f"{base_name} {idx}"


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def clean_numeric(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        text = str(value).replace(",", "").replace("$", "").strip()
        return float(text)
    except Exception:
        return default


def optional_numeric(value: Any) -> float | None:
    """Parse a number for nullable DB columns; empty input becomes None."""
    try:
        if value in (None, ""):
            return None
        text = str(value).replace(",", "").replace("$", "").strip()
        if text == "":
            return None
        return float(text)
    except Exception:
        return None


_GENERIC_PHOTO_TYPES = frozenset({"", "overview", "general", "photo", "image"})


def _safe_asset_id_segment(asset_id: str) -> str:
    s = clean_text(asset_id)
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", s)
    return s or "asset"


def _slug_description_segment(text: str, max_len: int = 40) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"[^a-z0-9]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    if len(t) > max_len:
        t = t[:max_len].rstrip("_")
    return t


def _storage_description_hint(file_info: dict[str, Any], original_file_name: str) -> str:
    d = clean_text(file_info.get("description"))
    if d:
        return d
    pt = clean_text(file_info.get("photo_type")) or ""
    if pt.lower() not in _GENERIC_PHOTO_TYPES:
        return pt
    stem = Path(original_file_name).stem if original_file_name else ""
    return stem


def _build_asset_photo_storage_basename(
    asset_id_str: str,
    file_info: dict[str, Any],
    original_file_name: str,
    index: int,
    ext: str,
) -> str:
    """
    Readable storage filename, e.g. AST-0001_handrail_section_01.jpg
    (asset id, optional slug from description / type / original name, zero-padded index).
    """
    aid = _safe_asset_id_segment(asset_id_str)
    hint = _storage_description_hint(file_info, original_file_name)
    slug = _slug_description_segment(hint)
    idx = f"{int(index):02d}"
    ext_clean = str(ext or "jpg").lower().lstrip(".")
    if slug:
        return f"{aid}_{slug}_{idx}.{ext_clean}"
    return f"{aid}_{idx}.{ext_clean}"


def build_qr_value(asset_id: str) -> str:
    return f"IPS-{asset_id}"


def find_duplicates_for_asset(payload: dict) -> list[dict]:
    assets = fetch_table("assets", limit=5000, order_by="asset_name")
    return find_possible_duplicates(payload, assets)


def save_asset(
    payload: dict,
    photo_files: list[dict] | None = None,
    created_by: str | None = None,
) -> dict:
    """
    Persist asset row and optional photos. Files are stored via ``upload_bytes_admin`` (Supabase
    Storage when ``STORAGE_BACKEND=supabase``, or on disk under ``LOCAL_STORAGE_ROOT`` / ``data/ips_storage``
    when ``STORAGE_BACKEND=local``). ``asset_photos.file_path`` holds the same logical key in both modes.
    """
    assets = fetch_table("assets", limit=5000, order_by="asset_name")

    final_asset_id = clean_text(payload.get("asset_id")) or next_asset_id(assets)
    final_asset_name = make_unique_asset_name(clean_text(payload.get("asset_name")), assets)

    asset_payload = {
        "asset_id": final_asset_id,
        "asset_name": final_asset_name,
        "asset_type": clean_text(payload.get("asset_type")),
        "manufacturer": clean_text(payload.get("manufacturer")),
        "model": clean_text(payload.get("model")),
        "serial_number": clean_text(payload.get("serial_number")),
        "year": clean_text(payload.get("year")),
        "category": clean_text(payload.get("category")),
        "subcategory": clean_text(payload.get("subcategory")),
        "status": clean_text(payload.get("status")) or "Available",
        "condition": clean_text(payload.get("condition")),
        "location": clean_text(payload.get("location")),
        "yard_location": clean_text(payload.get("yard_location")),
        "assigned_employee": clean_text(payload.get("assigned_employee")),
        "assigned_job_id": payload.get("assigned_job_id"),
        "department": clean_text(payload.get("department")),
        "purchase_date": payload.get("purchase_date") or None,
        "purchase_cost": clean_numeric(payload.get("purchase_cost")),
        "current_value": clean_numeric(payload.get("current_value")),
        "hour_meter": clean_numeric(payload.get("hour_meter")),
        "mileage": clean_numeric(payload.get("mileage")),
        "license_plate": clean_text(payload.get("license_plate")),
        "vin": clean_text(payload.get("vin")),
        "qr_code_value": build_qr_value(final_asset_id),
        "photo_path": "",
        "notes": clean_text(payload.get("notes")),
        "is_active": bool(payload.get("is_active", True)),
        "is_rental": bool(payload.get("is_rental", False)),
        "is_rentable": bool(payload.get("is_rentable", payload.get("is_rental", False))),
        "rental_daily_rate": optional_numeric(payload.get("rental_daily_rate")),
        "rental_weekly_rate": optional_numeric(payload.get("rental_weekly_rate")),
        "rental_monthly_rate": optional_numeric(payload.get("rental_monthly_rate")),
        "rental_notes": clean_text(payload.get("rental_notes")),
        "created_by": created_by,
    }

    # Use admin write helper here because Streamlit server-side writes
    # are not consistently carrying the authenticated JWT for RLS inserts.
    asset_row = insert_row_admin("assets", asset_payload)

    primary_photo_path = ""
    if photo_files:
        for index, file_info in enumerate(photo_files, start=1):
            file_name = clean_text(file_info.get("file_name")) or f"asset_{index}.jpg"
            file_bytes = file_info.get("file_bytes")
            photo_type = clean_text(file_info.get("photo_type")) or "overview"

            if not file_bytes:
                continue

            ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "jpg"
            stored_base = _build_asset_photo_storage_basename(
                final_asset_id, file_info, file_name, index, ext
            )
            storage_path = f"assets/{final_asset_id}/{stored_base}"

            upload_bytes_admin(
                storage_path,
                file_bytes,
                content_type="application/octet-stream",
            )

            insert_row_admin(
                "asset_photos",
                {
                    "asset_id": asset_row["id"],
                    "file_name": stored_base,
                    "file_path": storage_path,
                    "photo_type": photo_type,
                    "uploaded_by": created_by,
                },
            )

            if not primary_photo_path:
                primary_photo_path = storage_path

    if primary_photo_path:
        update_rows_admin(
            "assets",
            {"photo_path": primary_photo_path},
            {"id": asset_row["id"]},
        )
        asset_row["photo_path"] = primary_photo_path

    if clean_text(payload.get("assigned_employee")) or payload.get("assigned_job_id"):
        insert_row_admin(
            "asset_assignments",
            {
                "asset_id": asset_row["id"],
                "assigned_to": clean_text(payload.get("assigned_employee")),
                "assigned_job_id": payload.get("assigned_job_id"),
                "assigned_location": clean_text(payload.get("location")),
                "check_out_at": datetime.utcnow().isoformat(),
                "notes": clean_text(payload.get("assignment_notes")),
                "created_by": created_by,
            },
        )

    return asset_row


def append_asset_photos(
    asset: dict[str, Any],
    photo_files: list[dict],
    uploaded_by: str | None = None,
) -> str | None:
    """Upload photos to the same storage layout as save_asset and append asset_photos rows."""
    asset_uuid = asset.get("id")
    if not asset_uuid:
        raise ValueError("Asset row must include id")

    final_asset_id = clean_text(asset.get("asset_id"))
    primary_photo_path = ""

    for index, file_info in enumerate(photo_files, start=1):
        file_name = clean_text(file_info.get("file_name")) or f"asset_{index}.jpg"
        file_bytes = file_info.get("file_bytes")
        photo_type = clean_text(file_info.get("photo_type")) or "overview"

        if not file_bytes:
            continue

        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "jpg"
        stored_base = _build_asset_photo_storage_basename(
            final_asset_id, file_info, file_name, index, ext
        )
        storage_path = f"assets/{final_asset_id}/{stored_base}"

        upload_bytes_admin(
            storage_path,
            file_bytes,
            content_type="application/octet-stream",
        )

        insert_row_admin(
            "asset_photos",
            {
                "asset_id": asset_uuid,
                "file_name": stored_base,
                "file_path": storage_path,
                "photo_type": photo_type,
                "uploaded_by": uploaded_by,
            },
        )

        if not primary_photo_path:
            primary_photo_path = storage_path

    if primary_photo_path:
        update_rows_admin(
            "assets",
            {"photo_path": primary_photo_path},
            {"id": asset_uuid},
        )
    return primary_photo_path


def _recompute_asset_primary_photo(asset_uuid: str) -> None:
    rows = fetch_by_match("asset_photos", {"asset_id": asset_uuid}, limit=500)
    rows.sort(key=lambda r: str(r.get("created_at") or ""))
    new_primary = clean_text(rows[0].get("file_path")) if rows else ""
    update_rows_admin("assets", {"photo_path": new_primary}, {"id": asset_uuid})


def set_asset_primary_photo(asset: dict[str, Any], file_path: str) -> None:
    """Persist ``assets.photo_path`` so list views and the asset profile use this image."""
    asset_uuid = asset.get("id")
    if not asset_uuid:
        raise ValueError("asset row missing id")
    fp = clean_text(file_path)
    if not fp:
        raise ValueError("file_path is empty")
    update_rows_admin("assets", {"photo_path": fp}, {"id": asset_uuid})


def delete_asset_photo(photo_row: dict[str, Any], asset: dict[str, Any]) -> None:
    """Remove file from storage, delete ``asset_photos`` row, refresh ``assets.photo_path`` if needed."""
    rid = photo_row.get("id")
    if not rid:
        raise ValueError("asset_photos row missing id")
    path = clean_text(photo_row.get("file_path"))
    asset_uuid = asset.get("id")
    if not asset_uuid:
        raise ValueError("asset row missing id")
    was_primary = clean_text(asset.get("photo_path")) == path
    if path:
        try:
            delete_storage_object_admin(path)
        except Exception as exc:
            _LOG.warning("Storage delete failed for %s (DB row still removed): %s", path, exc)
    delete_rows_admin("asset_photos", {"id": rid})
    if was_primary:
        _recompute_asset_primary_photo(str(asset_uuid))


def apply_extraction_to_asset(asset: dict[str, Any], extracted: dict[str, Any]) -> None:
    """Apply normalized AI extraction onto an existing asset; non-empty extracted values win."""
    payload: dict[str, Any] = {
        "hour_meter": clean_numeric(extracted.get("hour_meter")),
        "mileage": clean_numeric(extracted.get("mileage")),
    }
    for key in (
        "asset_name",
        "asset_type",
        "manufacturer",
        "model",
        "serial_number",
        "location",
        "condition",
    ):
        new_v = clean_text(extracted.get(key))
        if new_v:
            payload[key] = new_v
    new_notes = clean_text(extracted.get("notes"))
    if new_notes:
        payload["notes"] = new_notes
    update_rows_admin("assets", payload, {"id": asset["id"]})


_CHILD_TABLES_BY_ASSET = (
    "asset_photos",
    "asset_documents",
    "asset_maintenance",
    "asset_assignments",
    "asset_inspections",
)


def delete_asset_and_related(asset_uuid: str) -> None:
    """Remove dependent rows then the asset. Does not delete storage objects (DB-safe cascade)."""
    for table in _CHILD_TABLES_BY_ASSET:
        delete_rows_admin(table, {"asset_id": asset_uuid})
    delete_rows_admin("assets", {"id": asset_uuid})


def save_maintenance_record(payload: dict, created_by: str | None = None) -> dict:
    asset = fetch_one("assets", {"id": payload["asset_id"]})
    rule = fetch_one("asset_service_rules", {"asset_type": asset.get("asset_type", "")}) if asset else None

    next_service = calculate_next_service(
        payload.get("service_date"),
        payload.get("hour_meter"),
        payload.get("mileage"),
        rule,
    )

    record = {
        "asset_id": payload["asset_id"],
        "service_type": clean_text(payload.get("service_type")),
        "service_date": payload.get("service_date"),
        "hour_meter": clean_numeric(payload.get("hour_meter")),
        "mileage": clean_numeric(payload.get("mileage")),
        "vendor": clean_text(payload.get("vendor")),
        "cost": clean_numeric(payload.get("cost")),
        "po_number": clean_text(payload.get("po_number")),
        "performed_by": clean_text(payload.get("performed_by")),
        "notes": clean_text(payload.get("notes")),
        "next_service_date": next_service.get("next_service_date"),
        "next_service_hours": next_service.get("next_service_hours"),
        "next_service_mileage": next_service.get("next_service_mileage"),
        "created_by": created_by,
    }

    return insert_row_admin("asset_maintenance", record)
