"""Add Hilti HIT-RE 500 V3 epoxy from Amazon purchase screenshot to inventory."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from amazon_inventory_helpers import upsert_inventory_with_image

SCREENSHOT = Path(
    r"C:\Users\chetbreaux\.cursor\projects\c-IPS-APP\assets"
    r"\c__Users_chetbreaux_AppData_Roaming_Cursor_User_workspaceStorage_empty-window_images"
    r"_image-fb2f7e52-d9c8-40aa-8e05-696e6d3e99c8.png"
)

ITEM = {
    "sku": "HILTI-HIT-RE500-V3-11OZ",
    "name": "Hilti HIT-RE 500 V3 11.1 fl. oz. Epoxy Adhesive",
    "category": "Consumables",
    "location": "Main Warehouse",
    "vendor": "Amazon",
    "unit_cost": 56.0,
    "qty_on_hand": 5,
    "status": "In Stock",
    "notes": "11.1 fl. oz. epoxy adhesive cartridge. Amazon purchase reference $56.00.",
}


if __name__ == "__main__":
    raise SystemExit(upsert_inventory_with_image(item=ITEM, screenshot=SCREENSHOT, root=ROOT))
