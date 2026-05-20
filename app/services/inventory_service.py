"""
Inventory module — Supabase reads/writes.

Schema assumptions: ``inventory_items`` (or ``inventory``) with sku, item_name, category,
storage_location, quantity_on_hand, reorder_point, unit_cost, vendor, status.
"""

from __future__ import annotations

from app.services.phase2_modules_service import (
    delete_inventory_item,
    list_inventory,
    normalize_inventory,
    save_inventory_item,
)

__all__ = ["delete_inventory_item", "list_inventory", "normalize_inventory", "save_inventory_item"]
