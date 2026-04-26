"""Resize and normalize inventory item images for upload (thumbnails)."""

from __future__ import annotations

import io
from typing import Tuple

_MAX_SIDE = 480
_JPEG_QUALITY = 86


def resize_inventory_image_bytes(data: bytes, *, max_side: int = _MAX_SIDE) -> Tuple[bytes, str]:
    """
    Resize image bytes to a thumbnail (fit within ``max_side``), return (jpeg_bytes, image/jpeg).
    """
    from PIL import Image

    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    return buf.getvalue(), "image/jpeg"


def inventory_item_image_storage_path(item_id: str) -> str:
    """Stable storage key for an item thumbnail."""
    return f"inventory/items/{str(item_id).strip()}.jpg"
