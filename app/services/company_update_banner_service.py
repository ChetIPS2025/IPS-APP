"""Optional banner images for company announcements."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.db import create_signed_url, delete_storage_object_admin, update_rows_admin, upload_bytes_admin
from app.services.item_images import to_browser_image_src
from app.services.repository import ServiceResult, clear_data_cache_for_table
BANNER_UPLOAD_TYPES: tuple[str, ...] = ("jpg", "jpeg", "png", "webp")
_ALLOWED_EXTENSIONS = {f".{ext}" for ext in BANNER_UPLOAD_TYPES}
_MAX_BYTES = 5 * 1024 * 1024
_STORAGE_PREFIX = "company_updates"


def _extension(filename: str) -> str:
    return Path(str(filename or "")).suffix.lower()


def _safe_filename(name: str) -> str:
    base = str(name or "banner").strip().replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", base).strip("._") or "banner"
    return base[:160]


def _resolve_mime_type(filename: str, streamlit_type: object = None) -> str:
    ext = _extension(filename)
    by_ext = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    if ext in by_ext:
        return by_ext[ext]
    raw = str(streamlit_type or "").strip().lower()
    if raw.startswith("image/"):
        return raw
    return "image/jpeg"


def validate_banner_upload(uploaded_file: Any) -> tuple[bytes, str, str] | str:
    """Return (bytes, filename, mime) or an error message."""
    if uploaded_file is None:
        return "Choose a banner image to upload."
    filename = _safe_filename(str(getattr(uploaded_file, "name", "") or "banner.jpg"))
    ext = _extension(filename)
    if ext not in _ALLOWED_EXTENSIONS:
        return "Unsupported image type. Upload JPG, PNG, or WEBP (max 5 MB)."
    try:
        data = uploaded_file.getvalue()
    except Exception:
        return "Could not read the uploaded image."
    if not data:
        return "Uploaded image is empty."
    if len(data) > _MAX_BYTES:
        return "Banner image must be 5 MB or smaller."
    return data, filename, _resolve_mime_type(filename, getattr(uploaded_file, "type", None))


def has_company_update_banner(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    if str(row.get("banner_view_url") or "").strip().startswith("http"):
        return True
    return bool(str(row.get("banner_path") or "").strip())


def resolve_company_update_banner_url(row: dict[str, Any] | None, *, expires_in: int = 3600) -> str | None:
    """Return a browser-ready banner URL when a banner exists."""
    if not row:
        return None
    direct = str(row.get("banner_view_url") or "").strip()
    if direct.startswith("http"):
        return direct
    path = str(row.get("banner_path") or "").strip()
    if not path:
        return None
    mime = str(row.get("banner_mime_type") or "image/jpeg").strip() or "image/jpeg"
    try:
        bucket = getattr(settings, "storage_bucket", "ips-storage")
        signed = create_signed_url(path, expires_in=expires_in, bucket=bucket)
        browser = to_browser_image_src(signed, mime=mime)
        if browser:
            return browser
        if signed.startswith("http"):
            return signed
        return to_browser_image_src(path, mime=mime) or signed or None
    except Exception:
        return to_browser_image_src(path, mime=mime)


def enrich_company_update_banner(row: dict[str, Any]) -> dict[str, Any]:
    url = resolve_company_update_banner_url(row)
    if not url:
        return row
    return {**row, "banner_view_url": url}


def _banner_storage_path(update_id: str, filename: str) -> str:
    uid = str(update_id or "").strip()
    if not uid:
        raise ValueError("Missing update id.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe = _safe_filename(filename)
    return f"{_STORAGE_PREFIX}/{uid}/banner_{stamp}_{safe}"


def _clear_banner_fields() -> dict[str, Any]:
    return {
        "banner_path": "",
        "banner_file_name": "",
        "banner_mime_type": "",
        "banner_caption": "",
        "banner_uploaded_at": None,
    }


def _delete_existing_banner(row: dict[str, Any] | None) -> None:
    path = str((row or {}).get("banner_path") or "").strip()
    if not path:
        return
    try:
        bucket = getattr(settings, "storage_bucket", "ips-storage")
        delete_storage_object_admin(path, bucket=bucket)
    except Exception:
        pass


def upload_company_update_banner(
    update_id: str,
    uploaded_file: Any,
    *,
    caption: str = "",
    existing_row: dict[str, Any] | None = None,
) -> ServiceResult:
    validated = validate_banner_upload(uploaded_file)
    if isinstance(validated, str):
        return ServiceResult(ok=False, error=validated)
    data, filename, mime = validated
    uid = str(update_id or "").strip()
    if not uid:
        return ServiceResult(ok=False, error="Missing update id.")

    _delete_existing_banner(existing_row)
    storage_path = _banner_storage_path(uid, filename)
    bucket = getattr(settings, "storage_bucket", "ips-storage")
    try:
        upload_bytes_admin(storage_path, data, mime, bucket=bucket)
    except Exception as exc:
        return ServiceResult(ok=False, error=f"Banner upload failed: {exc}")

    payload = {
        "banner_path": storage_path,
        "banner_file_name": filename,
        "banner_mime_type": mime,
        "banner_caption": str(caption or "").strip()[:500],
        "banner_uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        update_rows_admin("company_updates", payload, {"id": uid})
    except Exception as exc:
        try:
            delete_storage_object_admin(storage_path, bucket=bucket)
        except Exception:
            pass
        return ServiceResult(ok=False, error=f"Could not save banner metadata: {exc}")
    clear_data_cache_for_table("company_updates")
    return ServiceResult(ok=True, data={"banner_path": storage_path, **payload})


def remove_company_update_banner(update_id: str, *, existing_row: dict[str, Any] | None = None) -> ServiceResult:
    uid = str(update_id or "").strip()
    if not uid:
        return ServiceResult(ok=False, error="Missing update id.")
    _delete_existing_banner(existing_row)
    try:
        update_rows_admin("company_updates", _clear_banner_fields(), {"id": uid})
    except Exception as exc:
        return ServiceResult(ok=False, error=f"Could not remove banner: {exc}")
    clear_data_cache_for_table("company_updates")
    return ServiceResult(ok=True, data={"message": "Banner removed."})


def save_company_update_banner_caption(update_id: str, caption: str) -> ServiceResult:
    uid = str(update_id or "").strip()
    if not uid:
        return ServiceResult(ok=False, error="Missing update id.")
    try:
        update_rows_admin(
            "company_updates",
            {"banner_caption": str(caption or "").strip()[:500]},
            {"id": uid},
        )
    except Exception as exc:
        return ServiceResult(ok=False, error=f"Could not save banner caption: {exc}")
    clear_data_cache_for_table("company_updates")
    return ServiceResult(ok=True, data={"message": "Banner caption saved."})
