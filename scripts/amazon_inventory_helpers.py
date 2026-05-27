"""Shared helpers for adding inventory items from Amazon order screenshots."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


def trim_content(im: Image.Image, *, threshold: int = 245, pad: int = 4) -> Image.Image:
    rgb = im.convert("RGB")
    px = rgb.load()
    w, h = rgb.size
    minx, miny, maxx, maxy = w, h, 0, 0
    found = False
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r < threshold or g < threshold or b < threshold:
                found = True
                minx = min(minx, x)
                miny = min(miny, y)
                maxx = max(maxx, x)
                maxy = max(maxy, y)
    if not found:
        return im
    return im.crop(
        (
            max(0, minx - pad),
            max(0, miny - pad),
            min(w, maxx + pad + 1),
            min(h, maxy + pad + 1),
        )
    )


def crop_amazon_product_preview(im: Image.Image) -> Image.Image:
    """Tight crop of Amazon order-row product thumbnail."""
    w, h = im.size
    right = min(max(92, int(w * 0.20)), w - 4)
    if h <= 180:
        bottom = min(max(int(h * 0.62), 95), h - 8)
    else:
        bottom = min(max(int(h * 0.78), 105), h - 8)
    base = im.crop((8, 8, right, bottom))
    trimmed = trim_content(base)
    side = max(trimmed.size)
    return ImageOps.pad(trimmed, (side, side), color=(255, 255, 255), centering=(0.5, 0.5))


class BytesUpload:
    def __init__(self, data: bytes, *, name: str, mime: str) -> None:
        self._data = data
        self.name = name
        self.type = mime

    def getvalue(self) -> bytes:
        return self._data


def upsert_inventory_with_image(*, item: dict, screenshot: Path, root: Path) -> int:
    if not screenshot.is_file():
        print(f"Screenshot not found: {screenshot}")
        return 1

    sku = str(item["sku"])
    im = Image.open(screenshot).convert("RGB")
    crop = crop_amazon_product_preview(im)
    preview_path = root / "assets" / "item_images" / "inventory" / f"{sku}.jpg"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(preview_path, format="JPEG", quality=92)
    print(f"Saved preview image: {preview_path} ({crop.size[0]}x{crop.size[1]})")

    from app.db import fetch_table_admin
    from app.services.inventory_images import upload_inventory_image
    from app.services.item_images import save_approved_local_image
    from app.services.phase2_modules_service import save_inventory_item
    from app.services.repository import clear_all_data_caches

    existing_rows = fetch_table_admin("inventory_items", limit=5000) or []
    item_id = ""
    existing = None
    for row in existing_rows:
        if str(row.get("sku") or "").strip().upper() == sku.upper():
            item_id = str(row.get("id") or "").strip()
            existing = row
            print(f"Inventory item already exists: {item_id}")
            break

    if not item_id:
        result = save_inventory_item(item)
        if not result.ok:
            print(f"Insert failed: {result.error}")
            return 1
        item_id = str((result.data or {}).get("id") or "").strip()
        print(f"Inserted inventory item: {item_id}")

    image_bytes = preview_path.read_bytes()
    upload = upload_inventory_image(
        item_id,
        BytesUpload(image_bytes, name=f"{sku}.jpg", mime="image/jpeg"),
        existing=existing,
        force=True,
    )
    if not upload.ok:
        print(f"Image upload failed: {upload.error}")
        return 1

    save_approved_local_image(
        {"sku": sku, "item_name": item.get("name") or item.get("item_name")},
        image_bytes,
        f"{sku}.jpg",
        item_class="Inventory",
    )
    clear_all_data_caches()
    print("Inventory item ready with preview image.")
    return 0
