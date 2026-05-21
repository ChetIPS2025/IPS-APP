"""
Assets module — Supabase reads/writes.

Schema assumptions: ``assets`` with asset_id, asset_name, category, location, department,
status, serial_number, manufacturer, model, notes, current_value.
"""

from __future__ import annotations

from app.services.phase2_modules_service import (
    delete_asset,
    list_assets,
    normalize_asset,
    save_asset,
)

__all__ = ["delete_asset", "list_assets", "normalize_asset", "save_asset"]
