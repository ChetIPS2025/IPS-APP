"""
Upload media strategy — preserve originals, serve web-friendly previews.

Original upload:
  Save exactly what the user uploaded (asset_documents) for evidence/history.

Display preview:
  Convert to browser-safe JPEG/PNG for thumbnails, lists, and vision/OCR.
  HEIC/HEIF and PDF are converted; raster uploads are normalized to JPEG previews.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from app.services.repository import ServiceResult
except ImportError:
    from services.repository import ServiceResult  # type: ignore

WEB_PREVIEW_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp"})
SOURCE_DOCUMENT_TYPE = "Source photo"
SOURCE_DOCUMENT_NOTES = "Original upload — preserved for evidence; app preview is a converted copy."

PHOTO_ROLE_SOURCE = "source"
PHOTO_ROLE_PREVIEW = "preview"
PHOTO_ROLE_PRIMARY = "primary"


class _BytesUpload:
    """Minimal Streamlit UploadedFile stand-in for storage helpers."""

    def __init__(self, data: bytes, name: str, *, mime: str = "") -> None:
        self._data = data
        self.name = name
        self.type = mime

    def getvalue(self) -> bytes:
        return self._data


def _ext(name: str) -> str:
    return Path(str(name or "")).suffix.lower()


def _guess_content_type(filename: str, content_type: str = "") -> str:
    mime = str(content_type or "").strip()
    if mime:
        return mime
    ext = _ext(filename)
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".heic": "image/heic",
        ".heif": "image/heif",
        ".pdf": "application/pdf",
    }.get(ext, "application/octet-stream")


def _sync_asset_primary_image(asset_id: str, existing: dict[str, Any] | None = None) -> None:
    try:
        from app.services.catalog_image_sync import sync_catalog_images_for_asset
    except ImportError:
        from services.catalog_image_sync import sync_catalog_images_for_asset  # type: ignore
    try:
        from app.pages._core._data import load_assets
    except ImportError:
        from pages._core._data import load_assets  # type: ignore
    aid = str(asset_id or "").strip()
    source = next((r for r in load_assets() if str(r.get("id") or "") == aid), None) or existing or {"id": aid}
    sync_catalog_images_for_asset(source)


def upload_asset_media(
    *,
    asset_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: str = "",
    uploaded_by: str | None = None,
    photo_role: str = PHOTO_ROLE_PRIMARY,
    make_primary: bool = True,
    replace_existing: bool = False,
    existing: dict[str, Any] | None = None,
) -> ServiceResult:
    """
    Shared asset media upload with a stable signature.

    - ``photo_role='source'`` → exact bytes on ``asset_documents`` (evidence/history)
    - ``make_primary=True`` → web-friendly raster on ``assets.image_path`` (tables/detail)
    - ``replace_existing=True`` → overwrite an approved primary image; otherwise skip when approved
    """
    aid = str(asset_id or "").strip()
    name = str(filename or "upload").strip() or "upload"
    if not aid:
        return ServiceResult(ok=False, error="Asset id is required.")
    if not file_bytes:
        return ServiceResult(ok=False, error="Uploaded file is empty.")

    role = str(photo_role or PHOTO_ROLE_PRIMARY).strip().casefold()
    mime = _guess_content_type(name, content_type)

    if role == PHOTO_ROLE_SOURCE:
        return persist_original_asset_upload(
            aid,
            _BytesUpload(file_bytes, name, mime=mime),
            uploaded_by=uploaded_by,
        )

    if not make_primary:
        return ServiceResult(ok=False, error="Set make_primary=True to save a list/detail thumbnail.")

    save_bytes, save_name = file_bytes, name
    if needs_display_conversion(name):
        try:
            save_bytes, save_name = build_display_preview(file_bytes, name)
        except ValueError as exc:
            return ServiceResult(ok=False, error=str(exc))

    try:
        from app.services.item_images import persist_item_image
    except ImportError:
        from services.item_images import persist_item_image  # type: ignore

    result = persist_item_image(
        table="assets",
        record_id=aid,
        entity_type="assets",
        image_bytes=save_bytes,
        filename=save_name,
        existing=existing,
        uploaded_by=uploaded_by,
        replace_existing=replace_existing,
    )
    if result.ok and not (isinstance(result.data, dict) and result.data.get("skipped")):
        try:
            _sync_asset_primary_image(aid, existing)
        except Exception:
            pass
    return result


def needs_display_conversion(filename: str) -> bool:
    """True when the raw file is not directly usable as a browser thumbnail (HEIC, PDF, etc.)."""
    return _ext(filename) not in WEB_PREVIEW_EXTENSIONS


def build_display_preview(file_bytes: bytes, file_name: str) -> tuple[bytes, str]:
    """
    Build a web-friendly preview image for thumbnails and vision/OCR.

    Returns ``(preview_bytes, preview_filename)`` — PNG from HEIC/PDF pipeline, JPEG for rasters.
    """
    if not file_bytes:
        raise ValueError(f"Empty file: {file_name!r}.")
    name = str(file_name or "upload").strip() or "upload"

    if needs_display_conversion(name):
        try:
            from app.services.asset_autofill_media import prepare_asset_autofill_inputs
        except ImportError:
            from services.asset_autofill_media import prepare_asset_autofill_inputs  # type: ignore
        prepared = prepare_asset_autofill_inputs([(file_bytes, name)])
        preview_bytes, preview_name = prepared[0]
        return preview_bytes, preview_name

    try:
        from app.services.item_images import resize_item_image_bytes
    except ImportError:
        from services.item_images import resize_item_image_bytes  # type: ignore
    preview_bytes, _mime = resize_item_image_bytes(file_bytes)
    stem = Path(name).stem or "preview"
    return preview_bytes, f"{stem}.jpg"


def vision_inputs_from_upload(file_bytes: bytes, file_name: str) -> list[tuple[bytes, str]]:
    """All raster pages/images for vision/OCR (never sends raw HEIC/PDF to the model)."""
    try:
        from app.services.asset_autofill_media import prepare_asset_autofill_inputs
    except ImportError:
        from services.asset_autofill_media import prepare_asset_autofill_inputs  # type: ignore
    return prepare_asset_autofill_inputs([(file_bytes, file_name)])


def persist_original_asset_upload(
    asset_id: str,
    uploaded: Any,
    *,
    uploaded_by: str | None = None,
    document_type: str = SOURCE_DOCUMENT_TYPE,
    notes: str = SOURCE_DOCUMENT_NOTES,
) -> ServiceResult:
    """Store the exact uploaded bytes on ``asset_documents`` for evidence/history."""
    aid = str(asset_id or "").strip()
    if not aid or uploaded is None:
        return ServiceResult(ok=False, error="Asset and upload are required.")
    raw = uploaded.getvalue()
    if not raw:
        return ServiceResult(ok=False, error="Uploaded file is empty.")
    try:
        from app.services.asset_document_util import persist_asset_document_upload
    except ImportError:
        from services.asset_document_util import persist_asset_document_upload  # type: ignore
    try:
        row = persist_asset_document_upload(
            asset_row={"id": aid},
            uploaded=uploaded,
            document_type=document_type,
            notes=notes,
            uploaded_by=uploaded_by,
        )
        return ServiceResult(ok=True, data={"document": row})
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))


def attach_asset_photo_with_preview(
    asset_id: str,
    uploaded: Any,
    *,
    uploaded_by: str | None = None,
    save_original: bool = True,
    replace_existing: bool = True,
    force_preview: bool | None = None,
) -> ServiceResult:
    """
    Dual-save strategy for tool/asset photos:

    1. Original file → ``asset_documents`` (exact bytes, original filename)
    2. Display preview → asset ``image_path`` (JPEG/PNG for UI and OCR)
    """
    aid = str(asset_id or "").strip()
    if not aid or uploaded is None:
        return ServiceResult(ok=False, error="Asset and photo are required.")

    raw = uploaded.getvalue()
    name = str(getattr(uploaded, "name", "") or "upload")
    if not raw:
        return ServiceResult(ok=False, error="Uploaded file is empty.")

    if force_preview is not None:
        replace_existing = force_preview

    original_result: ServiceResult | None = None
    if save_original:
        original_result = upload_asset_media(
            asset_id=aid,
            file_bytes=raw,
            filename=name,
            content_type=str(getattr(uploaded, "type", "") or ""),
            uploaded_by=uploaded_by,
            photo_role=PHOTO_ROLE_SOURCE,
            make_primary=False,
        )
        if not original_result.ok:
            return original_result

    try:
        preview_bytes, preview_name = build_display_preview(raw, name)
    except ValueError as exc:
        return ServiceResult(ok=False, error=str(exc))

    preview_result = upload_asset_media(
        asset_id=aid,
        file_bytes=preview_bytes,
        filename=preview_name,
        content_type="image/jpeg",
        uploaded_by=uploaded_by,
        photo_role=PHOTO_ROLE_PRIMARY,
        make_primary=True,
        replace_existing=replace_existing,
    )
    if not preview_result.ok:
        return preview_result

    data: dict[str, Any] = {"preview": preview_result.data}
    if original_result and original_result.data:
        data["original"] = original_result.data
    return ServiceResult(ok=True, data=data)


def attach_asset_photos_bundle(
    asset_id: str,
    uploads: list[Any],
    *,
    primary_preview_bytes: bytes | None = None,
    primary_preview_filename: str = "preview.jpg",
    uploaded_by: str | None = None,
    save_originals: bool = True,
) -> ServiceResult:
    """
    Save every upload as a source document and set one primary ``image_path`` preview.

    When ``primary_preview_bytes`` is provided (e.g. catalog product image), it becomes
    the asset thumbnail. Otherwise the best converted upload preview is used.
    """
    aid = str(asset_id or "").strip()
    if not aid:
        return ServiceResult(ok=False, error="Asset id is required.")
    if not uploads and not primary_preview_bytes:
        return ServiceResult(ok=False, error="At least one upload or preview image is required.")

    saved_sources = 0
    source_errors: list[str] = []
    if save_originals:
        total = len(uploads)
        for idx, upload in enumerate(uploads, start=1):
            note = (
                f"Source upload {idx} of {total} — original preserved for evidence; "
                "app preview may be a separate catalog or converted image."
            )
            result = upload_asset_media(
                asset_id=aid,
                file_bytes=upload.getvalue(),
                filename=str(getattr(upload, "name", "") or "upload"),
                content_type=str(getattr(upload, "type", "") or ""),
                uploaded_by=uploaded_by,
                photo_role=PHOTO_ROLE_SOURCE,
                make_primary=False,
            )
            if not result.ok:
                source_errors.append(result.error or f"Source upload {idx} failed.")
                continue
            # Preserve per-file evidence note on the document row when possible.
            try:
                from app.services.repository import update_row
            except ImportError:
                from services.repository import update_row  # type: ignore
            doc = (result.data or {}).get("document") if isinstance(result.data, dict) else None
            if isinstance(doc, dict) and doc.get("id"):
                update_row("asset_documents", {"notes": note}, {"id": doc["id"]})
            saved_sources += 1

    preview_bytes = primary_preview_bytes
    preview_name = str(primary_preview_filename or "preview.jpg").strip() or "preview.jpg"
    if not preview_bytes and uploads:
        try:
            best = uploads[0]
            raw = best.getvalue()
            name = str(getattr(best, "name", "") or "upload")
            preview_bytes, preview_name = build_display_preview(raw, name)
        except ValueError as exc:
            return ServiceResult(ok=False, error=str(exc))

    if not preview_bytes:
        if source_errors:
            return ServiceResult(ok=False, error="; ".join(source_errors[:3]))
        return ServiceResult(ok=False, error="Could not build a display preview.")

    preview_result = upload_asset_media(
        asset_id=aid,
        file_bytes=preview_bytes,
        filename=preview_name,
        content_type="image/jpeg",
        uploaded_by=uploaded_by,
        photo_role=PHOTO_ROLE_PRIMARY,
        make_primary=True,
        replace_existing=True,
    )
    if not preview_result.ok:
        return preview_result

    data: dict[str, Any] = {
        "preview": preview_result.data,
        "sources_saved": saved_sources,
        "source_errors": source_errors,
    }
    if source_errors and saved_sources == 0:
        return ServiceResult(ok=False, error="; ".join(source_errors[:3]), data=data)
    return ServiceResult(ok=True, data=data)


__all__ = [
    "PHOTO_ROLE_PRIMARY",
    "PHOTO_ROLE_PREVIEW",
    "PHOTO_ROLE_SOURCE",
    "SOURCE_DOCUMENT_NOTES",
    "SOURCE_DOCUMENT_TYPE",
    "WEB_PREVIEW_EXTENSIONS",
    "attach_asset_photo_with_preview",
    "attach_asset_photos_bundle",
    "build_display_preview",
    "needs_display_conversion",
    "persist_original_asset_upload",
    "upload_asset_media",
    "vision_inputs_from_upload",
]
