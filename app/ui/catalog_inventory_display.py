"""
Shared display helpers for catalog / inventory / estimate-material tables.

Drops internal columns before ``st.dataframe`` / CSV export so they never appear
in UI, exports, or previews. Optional friendly header renames and column order.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

# Columns never shown in user-facing tables, exports, or previews.
HIDDEN_SYSTEM_COLUMNS: frozenset[str] = frozenset(
    {
        "id",
        "item_key",
        "vendor_item_number",
        "is_active",
        "inventory_ref_id",
        "updated_at",
    }
)

# Preferred order (internal / snake_case keys). Others sort alphabetically after these.
_DISPLAY_ORDER_KEYS: tuple[str, ...] = (
    "image_url",
    "item_name",
    "description",
    "category",
    "subgroup",
    "unit",
    "purchase_price",
    "unit_cost",
    "sell_price",
    "sku",
    "vendor",
    "quantity_on_hand",
    "reorder_point",
    "suggest_qty",
    "status",
    "alert",
    "storage_location",
    "notes",
    "qr_code_value",
)

_COLUMN_LABELS: dict[str, str] = {
    "image_url": "Photo",
    "item_name": "Item",
    "description": "Description",
    "category": "Category",
    "subgroup": "Subgroup",
    "unit": "Unit",
    "purchase_price": "Purchase Price",
    "unit_cost": "Purchase Price",
    "sell_price": "Sell Price",
    "sku": "SKU",
    "vendor": "Vendor",
    "quantity_on_hand": "On Hand",
    "reorder_point": "Reorder",
    "suggest_qty": "Suggest Qty",
    "status": "Status",
    "alert": "Alert",
    "storage_location": "Storage Location",
    "notes": "Notes",
    "qr_code_value": "QR Code",
}


def _titleize_snake(name: str) -> str:
    s = str(name or "").strip()
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.replace("_", " ").strip()).title()


def add_status_from_is_active(df: pd.DataFrame) -> pd.DataFrame:
    """Add human-readable ``status`` from ``is_active`` when needed."""
    if df.empty or "status" in df.columns:
        return df
    if "is_active" not in df.columns:
        return df
    out = df.copy()
    out["status"] = out["is_active"].map(lambda x: "Active" if bool(x) else "Inactive")
    return out


def drop_hidden_system_columns(
    df: pd.DataFrame,
    *,
    extra_hidden: frozenset[str] | None = None,
    keep: frozenset[str] | None = None,
) -> pd.DataFrame:
    """Remove hidden/system columns. ``keep`` preserves keys even if listed as hidden."""
    if df.empty:
        return df
    drop_set = set(HIDDEN_SYSTEM_COLUMNS)
    if extra_hidden:
        drop_set |= set(extra_hidden)
    if keep:
        drop_set -= set(keep)
    to_drop = [c for c in df.columns if c in drop_set]
    return df.drop(columns=to_drop, errors="ignore")


def order_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Put known business columns first; remaining columns sorted alphabetically."""
    if df.empty:
        return df
    ordered = [c for c in _DISPLAY_ORDER_KEYS if c in df.columns]
    rest = sorted(c for c in df.columns if c not in ordered)
    return df[ordered + rest]


def rename_display_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Rename snake_case columns to Title Case / product labels; avoid duplicate display names."""
    if df.empty:
        return df
    seen: set[str] = set()
    mapping: dict[str, str] = {}
    for c in df.columns:
        label = _COLUMN_LABELS.get(c) or _titleize_snake(c)
        if label in seen:
            label = _titleize_snake(c)
        seen.add(label)
        mapping[c] = label
    return df.rename(columns=mapping)


def prepare_catalog_inventory_display_df(
    data: pd.DataFrame | list[dict[str, Any]] | None,
    *,
    add_status: bool = True,
    rename_headers: bool = True,
    prefer_column_order: bool = True,
    extra_hidden: frozenset[str] | None = None,
    keep: frozenset[str] | None = None,
) -> pd.DataFrame:
    """
    Build a viewer-safe DataFrame: optional ``status`` from ``is_active``, drop system
    columns, order columns, rename headers for display or CSV export.
    """
    d = pd.DataFrame(data) if not isinstance(data, pd.DataFrame) else data.copy()
    if d.empty:
        return d
    if add_status:
        d = add_status_from_is_active(d)
    d = drop_hidden_system_columns(d, extra_hidden=extra_hidden, keep=keep)
    if prefer_column_order:
        d = order_display_columns(d)
    if rename_headers:
        d = rename_display_headers(d)
    return d


def sanitize_catalog_inventory_export_df(
    data: pd.DataFrame | list[dict[str, Any]] | None,
    *,
    add_status: bool = True,
    extra_hidden: frozenset[str] | None = None,
) -> pd.DataFrame:
    """Same as display prep but always drops ``id`` and other hidden columns (export-safe)."""
    return prepare_catalog_inventory_display_df(
        data,
        add_status=add_status,
        rename_headers=True,
        prefer_column_order=True,
        extra_hidden=extra_hidden,
        keep=None,
    )
