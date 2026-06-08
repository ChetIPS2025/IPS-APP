"""Shared item photo storage, resolution, and catalog import image matching."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

_MAX_SIDE = 480
_JPEG_QUALITY = 86
ITEM_IMAGES_PREFIX = "assets/item_images"
_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"}
ITEM_IMAGE_UPLOAD_TYPES: tuple[str, ...] = ("png", "jpg", "jpeg", "webp", "avif")
INVENTORY_IMAGE_BUCKET = "inventory-images"
ASSET_IMAGE_BUCKET = "asset-images"

IMAGE_STATUS_MISSING = "missing"
IMAGE_STATUS_NEEDS_REVIEW = "needs_review"
IMAGE_STATUS_APPROVED = "approved"
IMAGE_STATUS_REJECTED = "rejected"
IMAGE_STATUSES: tuple[str, ...] = (
    IMAGE_STATUS_MISSING,
    IMAGE_STATUS_NEEDS_REVIEW,
    IMAGE_STATUS_APPROVED,
    IMAGE_STATUS_REJECTED,
)

ITEM_IMAGE_FIELDS: tuple[str, ...] = (
    "image_path",
    "image_url",
    "image_file_name",
    "image_mime_type",
    "image_uploaded_at",
    "image_uploaded_by",
    "image_status",
)

ITEM_IMAGE_URL_FIELDS: tuple[str, ...] = (
    "image_url",
    "photo_url",
    "thumbnail_url",
    "approved_photo_url",
    "primary_photo_url",
)

ITEM_IMAGE_PATH_FIELDS: tuple[str, ...] = (
    "image_path",
    "photo_path",
)

# Display resolution order (inventory + linked pricing guide).
CATALOG_IMAGE_FIELD_PRIORITY: tuple[str, ...] = (
    "image_url",
    "photo_url",
    "thumbnail_url",
    "image_path",
    "photo_path",
)

_INVALID_IMAGE_TOKENS = frozenset({"", "—", "-", "none", "null", "undefined"})

_HIGH_CONFIDENCE_FIELDS = frozenset({"model_number", "item_number", "sku"})

try:
    from app.config import ROOT_DIR
    from app.db import create_signed_url, update_rows_admin, upload_bytes_admin
    from app.services.repository import ServiceResult, clear_all_data_caches, filter_payload_to_table
except ImportError:
    from config import ROOT_DIR  # type: ignore
    from db import create_signed_url, update_rows_admin, upload_bytes_admin  # type: ignore
    from services.repository import ServiceResult, clear_all_data_caches, filter_payload_to_table  # type: ignore


@dataclass
class ImageMatchResult:
    filename: str
    data: bytes
    matched_field: str
    confidence: str  # high | low


def normalize_image_status(raw: Any) -> str:
    s = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    if s in ("missing", "none", ""):
        return IMAGE_STATUS_MISSING
    if s in ("needs_review", "needsreview", "review", "pending"):
        return IMAGE_STATUS_NEEDS_REVIEW
    if s in ("approved", "approve", "ok"):
        return IMAGE_STATUS_APPROVED
    if s in ("rejected", "reject", "skip", "skipped"):
        return IMAGE_STATUS_REJECTED
    if raw in IMAGE_STATUSES:
        return str(raw)
    return IMAGE_STATUS_MISSING


def is_image_approved(record: dict[str, Any] | None) -> bool:
    if not record:
        return False
    return normalize_image_status(record.get("image_status")) == IMAGE_STATUS_APPROVED


def normalize_image_match_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def description_image_match_key(description: Any) -> str:
    text = str(description or "").strip().lower()
    if not text:
        return ""
    words = re.findall(r"[a-z0-9]+", text)
    return "".join(words[:8])


def _safe_filename(name: str) -> str:
    base = str(name or "item-image").strip().replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return base[:180] or "item-image"


def _extension(name: str) -> str:
    dot = str(name or "").lower().rfind(".")
    if dot < 0:
        return ""
    return str(name[dot:]).lower()


def _local_folder_for_item_class(item_class: str) -> str:
    if str(item_class or "").strip().lower() == "asset":
        return "assets"
    return "inventory"


def approved_local_filename(row: dict[str, Any]) -> str:
    for field in ("model_number", "item_number", "sku", "item_code"):
        val = str(row.get(field) or "").strip()
        if val:
            return _safe_filename(val) + ".jpg"
    desc_key = description_image_match_key(row.get("description") or row.get("item_name") or row.get("asset_name"))
    if desc_key:
        return _safe_filename(desc_key) + ".jpg"
    return "item-image.jpg"


def save_approved_local_image(
    row: dict[str, Any],
    image_bytes: bytes,
    filename: str,
    *,
    item_class: str = "Inventory",
) -> Path | None:
    """Save an approved copy under assets/item_images/inventory/ or assets/."""
    folder = _local_folder_for_item_class(item_class)
    root = Path(ROOT_DIR) / "assets" / "item_images" / folder
    root.mkdir(parents=True, exist_ok=True)
    out_name = approved_local_filename(row) if not filename else _safe_filename(filename)
    if not out_name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        out_name = approved_local_filename(row)
    try:
        data, _ = resize_item_image_bytes(image_bytes)
        dest = root / out_name
        dest.write_bytes(data)
        return dest
    except OSError:
        return None


def resize_item_image_bytes(data: bytes, *, max_side: int = _MAX_SIDE) -> tuple[bytes, str]:
    from PIL import Image

    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    return buf.getvalue(), "image/jpeg"


def item_image_storage_path(entity_type: str, record_id: str, filename: str) -> str:
    rid = str(record_id or "").strip()
    if not rid:
        raise ValueError("Missing record id.")
    safe = _safe_filename(filename)
    if not safe.lower().endswith(".jpg"):
        safe = f"{safe.rsplit('.', 1)[0]}.jpg" if "." in safe else f"{safe}.jpg"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    et = str(entity_type or "").strip().lower()
    if et in ("inventory", "inventory_items"):
        folder = "inventory"
    elif et in ("assets", "asset"):
        folder = "assets"
    else:
        folder = "pricing_guide"
    return f"{ITEM_IMAGES_PREFIX}/{folder}/{rid}/{ts}_{safe}"


def _clean_image_token(raw: object) -> str:
    val = str(raw or "").strip()
    if val.casefold() in _INVALID_IMAGE_TOKENS:
        return ""
    return val


def has_stored_item_image(record: dict[str, Any] | None) -> bool:
    """True when any image metadata exists, regardless of approval status."""
    if not record:
        return False
    for key in ITEM_IMAGE_PATH_FIELDS + ITEM_IMAGE_URL_FIELDS:
        if _clean_image_token(record.get(key)):
            return True
    return False


def to_browser_image_src(raw: str | None, *, mime: str = "image/jpeg") -> str | None:
    """Return a URL suitable for HTML <img src> (http(s), data URL, or None)."""
    val = _clean_image_token(raw)
    if not val:
        return None
    lower = val.casefold()
    if lower.startswith("http://") or lower.startswith("https://") or lower.startswith("data:image"):
        return val
    path = Path(val)
    if path.is_file():
        try:
            data = path.read_bytes()
        except OSError:
            return None
        if not data:
            return None
        import base64

        ctype = mime if "/" in mime else "image/jpeg"
        return f"data:{ctype};base64,{base64.b64encode(data).decode('ascii')}"
    return None


def record_has_item_image(record: dict[str, Any] | None) -> bool:
    """True only when an approved item photo exists."""
    if not is_image_approved(record):
        return False
    return has_stored_item_image(record)


def can_apply_item_image(record: dict[str, Any] | None) -> bool:
    if not record:
        return True
    return not is_image_approved(record)


def item_image_metadata_payload(source: dict[str, Any]) -> dict[str, Any]:
    return {key: source.get(key) for key in ITEM_IMAGE_FIELDS if key in source}


def image_metadata_matches(left: dict[str, Any] | None, right: dict[str, Any] | None) -> bool:
    if not left or not right:
        return False
    return str(left.get("image_path") or "").strip() == str(right.get("image_path") or "").strip() and bool(
        str(left.get("image_path") or "").strip()
    )


def copy_item_image_metadata(
    source: dict[str, Any],
    *,
    table: str,
    record_id: str,
    existing: dict[str, Any] | None = None,
    force: bool = False,
) -> ServiceResult:
    """Copy stored image metadata to another catalog row without re-uploading bytes."""
    rid = str(record_id or "").strip()
    if not rid:
        return ServiceResult(ok=False, error="Missing record id.")
    if not has_stored_item_image(source):
        return ServiceResult(ok=True, data={"skipped": True})
    if existing and not force:
        if image_metadata_matches(existing, source):
            return ServiceResult(ok=True, data={"skipped": True})
        if record_has_item_image(existing):
            return ServiceResult(ok=True, data={"skipped": True})

    payload = item_image_metadata_payload(source)
    if not str(payload.get("image_path") or "").strip() and not str(payload.get("image_url") or "").strip():
        return ServiceResult(ok=True, data={"skipped": True})
    return _update_item_image_row(table, payload, rid)


def _bucket_for_image_path(path: str) -> str | None:
    p = str(path or "").strip().replace("\\", "/")
    if not p:
        return None
    if p.startswith(f"{ITEM_IMAGES_PREFIX}/") or p.startswith("inventory/items/"):
        return None
    if p.startswith("inventory-images/") or p.startswith(f"{INVENTORY_IMAGE_BUCKET}/"):
        return INVENTORY_IMAGE_BUCKET
    if p.startswith("asset-images/") or p.startswith(f"{ASSET_IMAGE_BUCKET}/"):
        return ASSET_IMAGE_BUCKET
    return None


@lru_cache(maxsize=1024)
def _signed_item_image_url_cached(storage_path: str, bucket: str) -> str:
    signed = create_signed_url(storage_path, expires_in=3600, bucket=bucket or None)
    return str(signed or "").strip()


def clear_item_image_url_cache() -> None:
    _signed_item_image_url_cached.cache_clear()


def _update_item_image_row(table: str, payload: dict[str, Any], record_id: str) -> ServiceResult:
    """Persist image metadata with the service-role client (matches storage upload permissions)."""
    rid = str(record_id or "").strip()
    if not rid:
        return ServiceResult(ok=False, error="Missing record id.")
    filtered = filter_payload_to_table(table, payload)
    try:
        rows = update_rows_admin(table, filtered, {"id": rid})
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))
    if not rows:
        return ServiceResult(
            ok=False,
            error=f"Could not save image metadata to {table} (no row updated).",
        )
    clear_all_data_caches()
    return ServiceResult(ok=True, data=rows[0])


def resolve_image_url_by_field_priority(
    record: dict[str, Any] | None,
    field_order: tuple[str, ...] | None = None,
    *,
    expires_in: int = 3600,
) -> str | None:
    """Resolve a browser image URL using an explicit field fallback order."""
    _ = expires_in
    if not record:
        return None
    order = field_order or CATALOG_IMAGE_FIELD_PRIORITY
    mime = str(record.get("image_mime_type") or "image/jpeg").strip() or "image/jpeg"
    path_keys = frozenset(ITEM_IMAGE_PATH_FIELDS)

    for key in order:
        val = _clean_image_token(record.get(key))
        if not val:
            continue
        if key in path_keys:
            bucket = _bucket_for_image_path(val)
            try:
                signed = _signed_item_image_url_cached(val, bucket or "")
                browser = to_browser_image_src(signed, mime=mime)
                if browser:
                    return browser
                if signed and str(signed).startswith("http"):
                    return signed
            except Exception:
                pass
            browser = to_browser_image_src(val, mime=mime)
            if browser:
                return browser
            continue
        if val.startswith("http"):
            return to_browser_image_src(val, mime=mime) or val
        try:
            signed = _signed_item_image_url_cached(val, "")
            browser = to_browser_image_src(signed, mime=mime)
            if browser:
                return browser
            if signed and str(signed).startswith("http"):
                return signed
        except Exception:
            continue
    return None


def resolve_stored_item_image_url(record: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    """Resolve a viewable URL for any stored item photo (never QR PNG fields)."""
    _ = expires_in
    if not has_stored_item_image(record):
        return None
    mime = str(record.get("image_mime_type") or "image/jpeg").strip() or "image/jpeg"

    for key in ITEM_IMAGE_URL_FIELDS:
        public = _clean_image_token(record.get(key))
        if public.startswith("http"):
            return to_browser_image_src(public, mime=mime) or public

    for key in ITEM_IMAGE_PATH_FIELDS:
        path = _clean_image_token(record.get(key))
        if not path:
            continue
        bucket = _bucket_for_image_path(path)
        try:
            signed = _signed_item_image_url_cached(path, bucket or "")
            browser = to_browser_image_src(signed, mime=mime)
            if browser:
                return browser
            if signed and str(signed).startswith("http"):
                return signed
        except Exception:
            continue

    for key in ITEM_IMAGE_URL_FIELDS:
        public = _clean_image_token(record.get(key))
        if not public or public.startswith("http"):
            continue
        try:
            signed = _signed_item_image_url_cached(public, "")
            browser = to_browser_image_src(signed, mime=mime)
            if browser:
                return browser
            if signed and str(signed).startswith("http"):
                return signed
        except Exception:
            continue
    return None


def resolve_item_image_url(record: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    """Resolve a viewable URL for an approved item photo (never QR PNG fields)."""
    _ = expires_in
    if not is_image_approved(record):
        return None
    return resolve_stored_item_image_url(record, expires_in=expires_in)


def build_uploaded_image_index(
    files: Iterable[tuple[str, bytes]] | None,
) -> dict[str, tuple[str, bytes]]:
    index: dict[str, tuple[str, bytes]] = {}
    for name, data in files or []:
        if not data:
            continue
        stem = Path(str(name or "")).stem
        key = normalize_image_match_key(stem)
        if key and key not in index:
            index[key] = (str(name), data)
        desc_key = description_image_match_key(stem.replace("_", " ").replace("-", " "))
        if desc_key and desc_key not in index:
            index[desc_key] = (str(name), data)
    return index


def load_local_item_image_index(directory: Path | str | None = None) -> dict[str, tuple[str, bytes]]:
    """Load approved local images from inventory/ and assets/ subfolders only."""
    root = Path(directory) if directory else (Path(ROOT_DIR) / "assets" / "item_images")
    if not root.is_dir():
        return {}
    pairs: list[tuple[str, bytes]] = []
    for sub in ("inventory", "assets"):
        subdir = root / sub
        if not subdir.is_dir():
            continue
        for path in sorted(subdir.iterdir()):
            if not path.is_file():
                continue
            if _extension(path.name) not in _ALLOWED_EXTENSIONS:
                continue
            try:
                pairs.append((path.name, path.read_bytes()))
            except OSError:
                continue
    return build_uploaded_image_index(pairs)


def find_image_match_for_row(
    row: dict[str, Any],
    index: dict[str, tuple[str, bytes]],
) -> ImageMatchResult | None:
    """Match uploaded/local images by model_number, item_number, sku, then description."""
    if not index:
        return None
    field_order: tuple[tuple[str, str], ...] = (
        ("model_number", "model_number"),
        ("item_number", "item_number"),
        ("sku", "sku"),
        ("item_code", "model_number"),
        ("item_code", "item_number"),
    )
    for field, row_key in field_order:
        needle = normalize_image_match_key(row.get(row_key))
        if not needle:
            continue
        hit = index.get(needle)
        if hit:
            filename, data = hit
            return ImageMatchResult(filename=filename, data=data, matched_field=field, confidence="high")

    desc_key = description_image_match_key(row.get("description") or row.get("item_name") or row.get("asset_name"))
    if desc_key:
        hit = index.get(desc_key)
        if hit:
            filename, data = hit
            return ImageMatchResult(filename=filename, data=data, matched_field="description", confidence="low")
    return None


def find_image_bytes_for_row(
    row: dict[str, Any],
    index: dict[str, tuple[str, bytes]],
) -> tuple[str, bytes] | None:
    match = find_image_match_for_row(row, index)
    if not match:
        return None
    return match.filename, match.data


def persist_item_image(
    *,
    table: str,
    record_id: str,
    entity_type: str,
    image_bytes: bytes,
    filename: str,
    existing: dict[str, Any] | None = None,
    uploaded_by: str | None = None,
    force: bool = False,
    image_status: str = IMAGE_STATUS_APPROVED,
) -> ServiceResult:
    rid = str(record_id or "").strip()
    if not rid:
        return ServiceResult(ok=False, error="Missing record id.")
    if not force and not can_apply_item_image(existing):
        return ServiceResult(ok=True, data={"skipped": True})

    ext = _extension(filename)
    if ext not in _ALLOWED_EXTENSIONS:
        return ServiceResult(ok=False, error="Unsupported image type.")

    try:
        data, mime = resize_item_image_bytes(image_bytes)
    except Exception as exc:
        return ServiceResult(ok=False, error=f"Could not process image: {exc}")

    storage_path = item_image_storage_path(entity_type, rid, filename)
    try:
        upload_bytes_admin(storage_path, data, mime, bucket=None)
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))

    status = normalize_image_status(image_status)
    payload: dict[str, Any] = {
        "image_path": storage_path,
        "image_url": "",
        "image_file_name": filename,
        "image_mime_type": mime,
        "image_uploaded_at": datetime.now(timezone.utc).isoformat(),
        "image_status": status,
    }
    if table == "pricing_guide_items":
        payload["image_uploaded_by"] = uploaded_by or ""
    elif uploaded_by:
        payload["image_uploaded_by"] = uploaded_by
    result = _update_item_image_row(table, payload, rid)
    if not result.ok:
        return ServiceResult(ok=False, error=result.error or "Could not save image metadata.")
    clear_item_image_url_cache()
    merged = {"image_path": storage_path, **payload}
    if isinstance(result.data, dict):
        merged = {**merged, **result.data}
    return ServiceResult(ok=True, data=merged)


def clear_item_image(*, table: str, record_id: str) -> ServiceResult:
    """Remove item photo metadata so the preview is cleared from lists and detail views."""
    rid = str(record_id or "").strip()
    if not rid:
        return ServiceResult(ok=False, error="Missing record id.")
    payload: dict[str, Any] = {
        "image_path": "",
        "image_url": "",
        "image_file_name": "",
        "image_mime_type": "",
        "image_uploaded_at": None,
        "image_status": IMAGE_STATUS_MISSING,
    }
    if table == "pricing_guide_items":
        payload["image_uploaded_by"] = ""
    result = _update_item_image_row(table, payload, rid)
    if not result.ok:
        return ServiceResult(ok=False, error=result.error or "Could not remove image.")
    clear_item_image_url_cache()
    return ServiceResult(ok=True, data=payload)


def set_image_status(table: str, record_id: str, status: str) -> ServiceResult:
    rid = str(record_id or "").strip()
    if not rid:
        return ServiceResult(ok=False, error="Missing record id.")
    st = normalize_image_status(status)
    payload: dict[str, Any] = {"image_status": st}
    if st == IMAGE_STATUS_MISSING:
        payload["image_url"] = ""
    result = _update_item_image_row(table, payload, rid)
    if not result.ok:
        return result
    clear_item_image_url_cache()
    return ServiceResult(ok=True, data=result.data or payload)
