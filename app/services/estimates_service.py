"""
Estimates module — Supabase reads/writes.

Schema assumptions: table ``estimates`` with quote_number, project_name, customer_name,
status, total, subtotal, tax, markup, estimate_date, expiration_date, notes.
"""

from __future__ import annotations

from app.services.phase2_modules_service import (
    delete_estimate,
    delete_estimate_line_item,
    list_estimate_materials,
    list_estimates,
    normalize_estimate,
    normalize_material_line,
    save_estimate,
    save_estimate_line_item,
)

__all__ = [
    "delete_estimate",
    "delete_estimate_line_item",
    "list_estimate_materials",
    "list_estimates",
    "normalize_estimate",
    "normalize_material_line",
    "save_estimate",
    "save_estimate_line_item",
]
