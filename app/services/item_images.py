"""Shared item photo storage, resolution, and catalog import image matching."""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

_MAX_SIDE = 480
_JPEG_QUALITY = 86
ITEM_IMAGES_PREFIX = "assets/item_images"
_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
INVENTORY_IMAGE_BUCKET = "inventory-images"
ASSET_IMAGE_BUCKET = "asset-images"

try:
    from app.config import ROOT_DIR
    from app.db import create_signed_url, upload_bytes_admin
    from app.services.repository import ServiceResult, update_row
except ImportError:
    from config import ROOT_DIR  # type: ignore
    from db import create_signed_url, upload_bytes_admin  # type: ignore
    from services.repository import ServiceResult, update_row  # type: ignore


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
    return f"{ITEM_IMAGES_PREFIX}/{entity_type}/{rid}/{ts}_{safe}"


def record_has_item_image(record: dict[str, Any] | None) -> bool:
    if not record:
        return False
    if str(record.get("image_path") or "").strip():
        return True
    url = str(record.get("image_url") or record.get("photo_url") or "").strip()
    if url.startswith("http"):
        return True
    if url:
        return True
    return bool(str(record.get("photo_path") or "").strip())


def can_apply_item_image(record: dict[str, Any] | None) -> bool:
    return not record_has_item_image(record)


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


def resolve_item_image_url(record: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    """Resolve a viewable URL for an item photo (never QR PNG fields)."""
    _ = expires_in
    public = str(record.get("image_url") or record.get("photo_url") or "").strip()
    if public.startswith("http"):
        return public

    path = str(record.get("image_path") or "").strip()
    if path:
        bucket = _bucket_for_image_path(path)
        try:
            signed = _signed_item_image_url_cached(path, bucket or "")
            return signed or None
        except Exception:
            return None

    legacy = str(record.get("photo_path") or "").strip()
    if legacy:
        try:
            signed = _signed_item_image_url_cached(legacy, "")
            return signed or None
        except Exception:
            return None

    if public:
        try:
            signed = _signed_item_image_url_cached(public, "")
            return signed or None
        except Exception:
            return None
    return None


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
    root = Path(directory) if directory else (Path(ROOT_DIR) / "assets" / "item_images")
    if not root.is_dir():
        return {}
    pairs: list[tuple[str, bytes]] = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        if _extension(path.name) not in _ALLOWED_EXTENSIONS:
            continue
        try:
            pairs.append((path.name, path.read_bytes()))
        except OSError:
            continue
    return build_uploaded_image_index(pairs)


def find_image_bytes_for_row(
    row: dict[str, Any],
    index: dict[str, tuple[str, bytes]],
) -> tuple[str, bytes] | None:
    if not index:
        return None
    candidates: list[str] = []
    for field in ("model_number", "item_number", "sku", "item_code"):
        val = row.get(field)
        key = normalize_image_match_key(val)
        if key:
            candidates.append(key)
    desc_key = description_image_match_key(row.get("description") or row.get("item_name") or row.get("asset_name"))
    if desc_key:
        candidates.append(desc_key)
    for key in candidates:
        hit = index.get(key)
        if hit:
            return hit
    return None


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

    payload = {
        "image_path": storage_path,
        "image_url": "",
        "image_file_name": filename,
        "image_mime_type": mime,
        "image_uploaded_at": datetime.now(timezone.utc).isoformat(),
        "image_uploaded_by": uploaded_by or None,
    }
    result = update_row(table, payload, {"id": rid})
    if not result.ok:
        return ServiceResult(ok=False, error=result.error or "Could not save image metadata.")
    clear_item_image_url_cache()
    return ServiceResult(ok=True, data={"image_path": storage_path, **payload})
