"""Resize, upload, and resolve asset images."""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Tuple

_MAX_SIDE = 480
_JPEG_QUALITY = 86
ASSET_IMAGE_BUCKET = "asset-images"
_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

try:
    from app.db import create_signed_url, upload_bytes_admin
    from app.services.repository import ServiceResult, update_row
except ImportError:
    from db import create_signed_url, upload_bytes_admin  # type: ignore
    from services.repository import ServiceResult, update_row  # type: ignore


def resize_asset_image_bytes(data: bytes, *, max_side: int = _MAX_SIDE) -> Tuple[bytes, str]:
    """Resize image bytes to a thumbnail (fit within ``max_side``), return (jpeg_bytes, image/jpeg)."""
    from PIL import Image

    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    return buf.getvalue(), "image/jpeg"


def _safe_filename(name: str) -> str:
    base = str(name or "asset-image").strip().replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return base[:180] or "asset-image"


def _extension(name: str) -> str:
    dot = str(name or "").lower().rfind(".")
    if dot < 0:
        return ""
    return str(name[dot:]).lower()


def _storage_not_configured_message(exc: Exception) -> str:
    msg = str(exc or "").lower()
    if any(token in msg for token in ("bucket", "not found", "does not exist", "404")):
        return "Storage bucket asset-images is not configured."
    return str(exc)


def asset_has_image(asset: dict[str, Any]) -> bool:
    return bool(
        str(asset.get("image_path") or "").strip()
        or str(asset.get("image_url") or "").strip()
        or str(asset.get("photo_path") or "").strip()
        or str(asset.get("photo_url") or "").strip()
    )


def _storage_path_for_asset(asset_id: str, filename: str) -> str:
    aid = str(asset_id or "").strip()
    if not aid:
        raise ValueError("Missing asset id.")
    safe = _safe_filename(filename)
    if not safe.lower().endswith(".jpg"):
        safe = f"{safe.rsplit('.', 1)[0]}.jpg" if "." in safe else f"{safe}.jpg"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"asset-images/{aid}/{ts}_{safe}"


@lru_cache(maxsize=512)
def _signed_asset_image_url_cached(storage_path: str, bucket: str) -> str:
    signed = create_signed_url(storage_path, expires_in=3600, bucket=bucket or None)
    return str(signed or "").strip()


def clear_asset_image_url_cache() -> None:
    _signed_asset_image_url_cached.cache_clear()


def get_asset_image_url(asset: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    """Return a viewable URL for an asset image."""
    _ = expires_in
    public = str(asset.get("image_url") or asset.get("photo_url") or "").strip()
    if public.startswith("http"):
        return public

    path = str(asset.get("image_path") or "").strip()
    if path:
        try:
            signed = _signed_asset_image_url_cached(path, ASSET_IMAGE_BUCKET)
            return signed or None
        except Exception:
            return None

    legacy_path = str(asset.get("photo_path") or "").strip()
    if legacy_path:
        try:
            signed = _signed_asset_image_url_cached(legacy_path, "")
            return signed or None
        except Exception:
            return None

    if public:
        try:
            signed = _signed_asset_image_url_cached(public, "")
            return signed or None
        except Exception:
            return None

    return None


def upload_asset_image(
    asset_id: str,
    uploaded_file: Any,
    *,
    uploaded_by: str | None = None,
) -> ServiceResult:
    """Upload asset image to asset-images bucket and persist metadata."""
    aid = str(asset_id or "").strip()
    if not aid:
        return ServiceResult(ok=False, error="Missing asset id.")
    if uploaded_file is None:
        return ServiceResult(ok=False, error="No file provided.")

    filename = str(getattr(uploaded_file, "name", "") or "asset-image")
    ext = _extension(filename)
    if ext not in _ALLOWED_EXTENSIONS:
        return ServiceResult(
            ok=False,
            error="Unsupported file type. Upload PNG, JPG, JPEG, or WEBP.",
        )

    raw = uploaded_file.getvalue()
    if not raw:
        return ServiceResult(ok=False, error="Uploaded file is empty.")

    try:
        data, mime = resize_asset_image_bytes(raw)
    except Exception as exc:
        return ServiceResult(ok=False, error=f"Could not process image: {exc}")

    storage_path = _storage_path_for_asset(aid, filename)

    try:
        upload_bytes_admin(storage_path, data, mime, bucket=ASSET_IMAGE_BUCKET)
    except Exception as exc:
        return ServiceResult(ok=False, error=_storage_not_configured_message(exc))

    payload = {
        "image_path": storage_path,
        "image_url": "",
        "image_file_name": filename,
        "image_mime_type": mime,
        "image_uploaded_at": datetime.now(timezone.utc).isoformat(),
        "image_uploaded_by": uploaded_by or None,
    }
    result = update_row("assets", payload, {"id": aid})
    if not result.ok:
        return ServiceResult(ok=False, error=result.error or "Could not save image metadata.")
    clear_asset_image_url_cache()
    return ServiceResult(ok=True, data={"image_path": storage_path, **payload})
