"""One-off: add WD-40 12-pack from Amazon purchase screenshot to inventory."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageOps

def _trim_content(im: Image.Image, *, threshold: int = 245) -> Image.Image:
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
    return im.crop((max(0, minx - 1), max(0, miny - 1), min(w, maxx + 2), min(h, maxy + 2)))


def _crop_product_preview(im: Image.Image) -> Image.Image:
    """Tight crop of Amazon order-row product thumbnail (cans only, no price/text)."""
    w, _h = im.size
    base = im.crop((10, 14, min(86, w - 4), 200))
    trimmed = _trim_content(base)
    side = max(trimmed.size)
    return ImageOps.pad(trimmed, (side, side), color=(255, 255, 255), centering=(0.5, 0.5))

SCREENSHOT = Path(
    r"C:\Users\chetbreaux\.cursor\projects\c-IPS-APP\assets"
    r"\c__Users_chetbreaux_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images"
    r"_image-1dae516c-fad4-4205-bc1c-67fefe86a6e3.png"
)

ITEM = {
    "sku": "WD40-12PK-12OZ",
    "name": (
        "WD-40 Original Formula, Multi-Use Product with Smart Straw Sprays 2 Ways, "
        "12 OZ [12-Pack]"
    ),
    "category": "Consumables",
    "location": "Main Warehouse",
    "vendor": "Amazon",
    "unit_cost": 92.16,
    "qty_on_hand": 2,
    "status": "In Stock",
    "notes": "12-pack of 12 oz cans. Amazon purchase reference $92.16 per pack.",
}


class _BytesUpload:
    def __init__(self, data: bytes, *, name: str, mime: str) -> None:
        self._data = data
        self.name = name
        self.type = mime

    def getvalue(self) -> bytes:
        return self._data


def main() -> int:
    if not SCREENSHOT.is_file():
        print(f"Screenshot not found: {SCREENSHOT}")
        return 1

    im = Image.open(SCREENSHOT).convert("RGB")
    crop = _crop_product_preview(im)
    preview_path = ROOT / "assets" / "item_images" / "inventory" / f"{ITEM['sku']}.jpg"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(preview_path, format="JPEG", quality=92)
    print(f"Saved preview image: {preview_path} ({crop.size[0]}x{crop.size[1]})")

    from app.db import fetch_table_admin
    from app.services.inventory_images import upload_inventory_image
    from app.services.item_images import save_approved_local_image
    from app.services.phase2_modules_service import save_inventory_item
    from app.services.repository import clear_all_data_caches

    item_id = ""
    existing = fetch_table_admin("inventory_items", limit=5000) or []
    for row in existing:
        if str(row.get("sku") or "").strip().upper() == ITEM["sku"].upper():
            item_id = str(row.get("id") or "").strip()
            print(f"Inventory item already exists: {item_id}")
            break

    if not item_id:
        result = save_inventory_item(ITEM)
        if not result.ok:
            print(f"Insert failed: {result.error}")
            return 1
        item_id = str((result.data or {}).get("id") or "").strip()
        print(f"Inserted inventory item: {item_id}")

    image_bytes = preview_path.read_bytes()
    upload = upload_inventory_image(
        item_id,
        _BytesUpload(image_bytes, name=f"{ITEM['sku']}.jpg", mime="image/jpeg"),
        existing=next((r for r in existing if str(r.get("id")) == item_id), None),
        force=True,
    )
    if not upload.ok:
        print(f"Image upload failed: {upload.error}")
        return 1

    save_approved_local_image(
        {"sku": ITEM["sku"], "item_name": ITEM["name"]},
        image_bytes,
        f"{ITEM['sku']}.jpg",
        item_class="Inventory",
    )
    clear_all_data_caches()
    print("Inventory item ready with preview image.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
