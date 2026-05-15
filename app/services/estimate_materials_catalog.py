"""Estimate quote material catalog: ``estimate_materials`` table only (not raw inventory lists)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import streamlit as st

from app.services.materials_catalog_merge import (
    inventory_row_to_material_catalog_shape,
    is_inventory_materials_category,
)


def estimate_material_row_to_catalog_shape(row: dict[str, Any]) -> dict[str, Any]:
    """Map ``estimate_materials`` row → shape expected by ``compute_totals`` / editor pickers."""
    pc = float(row.get("purchase_price") or 0)
    raw_sell = row.get("sell_price")
    if raw_sell is not None and str(raw_sell).strip() != "":
        try:
            sp = float(raw_sell)
        except (TypeError, ValueError):
            sp = round(pc * 1.25, 2) if pc else 0.0
    else:
        sp = round(pc * 1.25, 2) if pc else 0.0

    return {
        "id": row.get("id"),
        "item_key": str(row.get("item_key") or "").strip(),
        "description": str(row.get("description") or "").strip(),
        "category": str(row.get("category") or "Quote Catalog").strip() or "Quote Catalog",
        "subgroup": str(row.get("subgroup") or "").strip(),
        "unit": str(row.get("unit") or "EA").strip() or "EA",
        "purchase_price": pc,
        "sell_price": sp,
        "vendor_item_number": str(row.get("vendor_item_number") or "").strip(),
        "inventory_id": "",
        "is_active": bool(row.get("is_active", True)),
        "_source": "estimate_materials",
        "inventory_ref_id": row.get("inventory_ref_id"),
    }


def fetch_estimate_materials_catalog_rows(
    *,
    fetch_table: Callable[..., list[dict[str, Any]]],
    fetch_table_admin: Callable[..., list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fetcher = fetch_table_admin or fetch_table
    try:
        rows = list(
            fetcher("estimate_materials", limit=10000, order_by="item_key")
            or []
        )
    except Exception:
        rows = []
    out: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        if not str(r.get("item_key") or "").strip():
            continue
        if r.get("is_active") is False:
            continue
        out.append(estimate_material_row_to_catalog_shape(r))
    return out


@st.cache_data(ttl=120, show_spinner=False)
def cached_estimate_materials_catalog_rows() -> list[dict[str, Any]]:
    from db import fetch_table, fetch_table_admin

    return fetch_estimate_materials_catalog_rows(
        fetch_table=fetch_table,
        fetch_table_admin=fetch_table_admin,
    )


def clear_estimate_materials_catalog_cache() -> None:
    cached_estimate_materials_catalog_rows.clear()


def import_inventory_materials_into_estimate_catalog(
    *,
    fetch_table: Callable[..., list[dict[str, Any]]],
    insert_row_admin: Callable[..., dict[str, Any]],
    fetch_by_match_admin: Callable[..., list[dict[str, Any]]],
) -> tuple[int, int]:
    """
    Copy stocked **Materials** inventory rows into ``estimate_materials`` when not already linked.

    Returns (inserted_count, skipped_count).
    """
    try:
        inv_rows = list(fetch_table("inventory_items", limit=5000, order_by="item_name") or [])
    except Exception:
        inv_rows = []

    inserted = 0
    skipped_linked = 0
    skipped_other = 0
    for inv in inv_rows:
        if not isinstance(inv, dict) or not is_inventory_materials_category(inv):
            continue
        iid = str(inv.get("id") or "").strip()
        if not iid:
            skipped_other += 1
            continue
        existing = fetch_by_match_admin("estimate_materials", {"inventory_ref_id": iid}, limit=5)
        if existing:
            skipped_linked += 1
            continue
        shape = inventory_row_to_material_catalog_shape(inv)
        ik = str(shape.get("item_key") or "").strip()
        if not ik:
            skipped_other += 1
            continue
        dup = fetch_by_match_admin("estimate_materials", {"item_key": ik}, limit=1)
        if dup:
            skipped_other += 1
            continue
        insert_row_admin(
            "estimate_materials",
            {
                "item_key": ik,
                "description": str(shape.get("description") or "")[:2000],
                "category": "Quote Catalog",
                "subgroup": str(shape.get("subgroup") or "")[:500],
                "unit": str(shape.get("unit") or "EA")[:32],
                "purchase_price": float(shape.get("purchase_price") or 0),
                "sell_price": float(shape.get("sell_price") or 0),
                "vendor_item_number": str(shape.get("vendor_item_number") or "")[:200],
                "is_active": True,
                "inventory_ref_id": iid,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        inserted += 1
    return inserted, skipped_linked + skipped_other


def sync_estimate_material_pricing_from_inventory(
    *,
    fetch_table: Callable[..., list[dict[str, Any]]],
    fetch_table_admin: Callable[..., list[dict[str, Any]]] | None,
    update_rows_admin: Callable[..., list[dict[str, Any]]],
) -> int:
    """Update purchase/sell on linked ``estimate_materials`` from ``inventory_items``."""
    fetcher = fetch_table_admin or fetch_table
    try:
        em_rows = list(fetcher("estimate_materials", limit=10000, order_by="item_key") or [])
    except Exception:
        return 0

    inv_by_id: dict[str, dict[str, Any]] = {}
    try:
        for r in fetch_table("inventory_items", limit=5000, order_by="item_name") or []:
            if isinstance(r, dict) and r.get("id"):
                inv_by_id[str(r["id"])] = r
    except Exception:
        pass

    updated = 0
    now = datetime.now(timezone.utc).isoformat()
    for em in em_rows:
        if not isinstance(em, dict):
            continue
        ref = str(em.get("inventory_ref_id") or "").strip()
        if not ref:
            continue
        inv = inv_by_id.get(ref)
        if not inv:
            continue
        shape = inventory_row_to_material_catalog_shape(inv)
        update_rows_admin(
            "estimate_materials",
            {
                "purchase_price": float(shape.get("purchase_price") or 0),
                "sell_price": float(shape.get("sell_price") or 0),
                "updated_at": now,
            },
            {"id": str(em.get("id"))},
        )
        updated += 1
    return updated
