"""Unified Pricing Guide service — master estimating database."""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable

import streamlit as st

_LOG = logging.getLogger(__name__)

PRICING_ITEM_TYPES: tuple[str, ...] = (
    "Inventory",
    "Material",
    "Labor",
    "Equipment",
    "Travel",
    "Subcontractor",
    "Service",
    "Rental",
    "Consumable",
    "Assembly",
)

PRICING_ITEM_CLASSES: tuple[str, ...] = ("Inventory", "Asset", "Non-Inventory")

TYPE_PILL_CSS: dict[str, str] = {
    "Inventory": "ips-pg-type-inventory",
    "Material": "ips-pg-type-material",
    "Labor": "ips-pg-type-labor",
    "Equipment": "ips-pg-type-equipment",
    "Travel": "ips-pg-type-travel",
    "Subcontractor": "ips-pg-type-subcontractor",
    "Service": "ips-pg-type-service",
    "Rental": "ips-pg-type-rental",
    "Consumable": "ips-pg-type-consumable",
    "Assembly": "ips-pg-type-assembly",
}

_MATERIAL_LIKE_TYPES = frozenset(
    {"Inventory", "Material", "Consumable", "Rental", "Service", "Assembly"}
)


def calc_sell_price(cost: float, markup_percent: float) -> float:
    return round(float(cost or 0) + (float(cost or 0) * float(markup_percent or 0) / 100.0), 2)


def calc_markup_percent(cost: float, sell_price: float) -> float:
    cost = float(cost or 0)
    sell = float(sell_price or 0)
    if cost <= 0:
        return 0.0
    return round(((sell - cost) / cost) * 100.0, 2)


def slug_item_code(text: str, *, prefix: str = "") -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "-", str(text or "").strip().upper()).strip("-")
    if not base:
        base = "ITEM"
    if prefix:
        base = f"{prefix}-{base}"
    return base[:120]


def type_pill_html(item_type: str) -> str:
    t = str(item_type or "Material").strip() or "Material"
    cls = TYPE_PILL_CSS.get(t, "ips-pg-type-material")
    return f'<span class="ips-pg-type-pill {cls}">{html.escape(t)}</span>'


CLASS_PILL_CSS: dict[str, str] = {
    "Inventory": "ips-pg-type-inventory",
    "Asset": "ips-pg-type-equipment",
    "Non-Inventory": "ips-pg-type-material",
}


def class_pill_html(item_class: str) -> str:
    c = str(item_class or "Non-Inventory").strip() or "Non-Inventory"
    cls = CLASS_PILL_CSS.get(c, "ips-pg-type-material")
    return f'<span class="ips-pg-type-pill {cls}">{html.escape(c)}</span>'


def _legacy_material_to_row(raw: dict[str, Any]) -> dict[str, Any]:
    purchase = float(raw.get("purchase_price") or 0)
    sell_raw = raw.get("sell_price")
    if sell_raw not in (None, ""):
        sell = float(sell_raw)
    else:
        sell = calc_sell_price(purchase, 25.0)
    inv_ref = str(raw.get("inventory_ref_id") or "").strip() or None
    item_type = "Inventory" if inv_ref else "Material"
    return {
        "id": str(raw.get("id") or ""),
        "item_code": str(raw.get("item_key") or ""),
        "item_type": item_type,
        "description": str(raw.get("description") or raw.get("item_key") or ""),
        "category": str(raw.get("category") or "Pricing Guide"),
        "subcategory": str(raw.get("subgroup") or ""),
        "unit": str(raw.get("unit") or "EA"),
        "default_cost": purchase,
        "default_markup_percent": calc_markup_percent(purchase, sell),
        "default_sell_price": sell,
        "taxable": True,
        "is_active": raw.get("is_active") is not False,
        "inventory_item_id": inv_ref,
        "asset_id": None,
        "vendor_id": None,
        "labor_role": None,
        "equipment_type": None,
        "travel_type": None,
        "notes": str(raw.get("notes") or ""),
        "vendor_name": str(raw.get("vendor_item_number") or ""),
        "inventory_label": "",
        "asset_label": "",
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
        "_source": "estimate_materials",
    }


def normalize_pricing_row(
    raw: dict[str, Any],
    *,
    vendor_names: dict[str, str] | None = None,
    inventory_labels: dict[str, str] | None = None,
    asset_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    if raw.get("_source") == "estimate_materials":
        row = _legacy_material_to_row(raw)
    else:
        cost = float(raw.get("default_cost") or 0)
        markup = float(raw.get("default_markup_percent") or 0)
        sell_raw = raw.get("default_sell_price")
        if sell_raw not in (None, ""):
            sell = float(sell_raw)
        else:
            sell = calc_sell_price(cost, markup)
        vendor_id = str(raw.get("vendor_id") or "").strip() or None
        inv_id = str(raw.get("linked_inventory_id") or raw.get("inventory_item_id") or "").strip() or None
        asset_id = str(raw.get("linked_asset_id") or raw.get("asset_id") or "").strip() or None
        item_class = str(raw.get("item_class") or "").strip()
        if not item_class or item_class not in PRICING_ITEM_CLASSES:
            if inv_id:
                item_class = "Inventory"
            elif asset_id:
                item_class = "Asset"
            else:
                item_class = "Non-Inventory"
        vendors = vendor_names or {}
        invs = inventory_labels or {}
        assets = asset_labels or {}
        row = {
            **raw,
            "id": str(raw.get("id") or ""),
            "item_code": str(raw.get("item_code") or raw.get("sku") or ""),
            "item_type": str(raw.get("item_type") or "Material"),
            "item_class": item_class,
            "description": str(raw.get("description") or ""),
            "category": str(raw.get("category") or ""),
            "subcategory": str(raw.get("subcategory") or ""),
            "unit": str(raw.get("unit") or "EA"),
            "default_cost": cost,
            "default_markup_percent": markup if markup else calc_markup_percent(cost, sell),
            "default_sell_price": sell,
            "markup_percent": float(raw.get("markup_percent") or markup or 0),
            "sell_price": float(raw.get("sell_price") or sell or 0),
            "item_number": str(raw.get("item_number") or raw.get("item_code") or ""),
            "model_number": str(raw.get("model_number") or ""),
            "sku": str(raw.get("sku") or raw.get("item_code") or ""),
            "taxable": raw.get("taxable") is not False,
            "is_active": raw.get("is_active") is not False,
            "inventory_item_id": inv_id,
            "asset_id": asset_id,
            "linked_inventory_id": inv_id,
            "linked_asset_id": asset_id,
            "vendor_id": vendor_id,
            "vendor": str(raw.get("vendor") or ""),
            "labor_role": raw.get("labor_role"),
            "equipment_type": raw.get("equipment_type"),
            "travel_type": raw.get("travel_type"),
            "notes": str(raw.get("notes") or ""),
            "vendor_name": vendors.get(vendor_id or "", "") if vendor_id else str(raw.get("vendor") or ""),
            "inventory_label": invs.get(inv_id or "", "") if inv_id else "",
            "asset_label": assets.get(asset_id or "", "") if asset_id else "",
            "image_path": str(raw.get("image_path") or ""),
            "image_url": str(raw.get("image_url") or ""),
            "image_file_name": str(raw.get("image_file_name") or ""),
            "qr_code_url": str(raw.get("qr_code_url") or ""),
        }

    active = row.get("is_active") is not False
    live_cost = resolve_live_unit_cost(row)
    return {
        **row,
        "item": row["description"],
        "default_cost": live_cost,
        "markup_pct": float(row.get("default_markup_percent") or row.get("markup_percent") or 0),
        "customer_price": float(row.get("default_sell_price") or row.get("sell_price") or 0),
        "sell_price": float(row.get("default_sell_price") or row.get("sell_price") or 0),
        "vendor": str(row.get("vendor_name") or row.get("vendor") or row.get("vendor_item_number") or "—"),
        "status": "Active" if active else "Inactive",
    }


def _load_lookup_maps() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    vendor_names: dict[str, str] = {}
    inventory_labels: dict[str, str] = {}
    asset_labels: dict[str, str] = {}
    try:
        from app.db import fetch_table, fetch_table_admin
    except ImportError:
        from db import fetch_table, fetch_table_admin  # type: ignore

    fetcher = fetch_table_admin or fetch_table
    for table, target, name_fields in (
        ("vendors", vendor_names, ("vendor_name", "name")),
        ("inventory_items", inventory_labels, ("item_name", "name", "description")),
        ("assets", asset_labels, ("asset_name", "name")),
    ):
        try:
            rows = list(fetcher(table, limit=10000) or [])
        except Exception:
            rows = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            rid = str(r.get("id") or "").strip()
            if not rid:
                continue
            label = ""
            for nf in name_fields:
                label = str(r.get(nf) or "").strip()
                if label:
                    break
            target[rid] = label or rid[:8]

    return vendor_names, inventory_labels, asset_labels


def fetch_pricing_guide_rows(
    *,
    include_inactive: bool = True,
    fetch_table: Callable[..., list[dict[str, Any]]] | None = None,
    fetch_table_admin: Callable[..., list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    if fetch_table is None or fetch_table_admin is None:
        try:
            from app.db import fetch_table as _ft, fetch_table_admin as _fta
        except ImportError:
            from db import fetch_table as _ft, fetch_table_admin as _fta  # type: ignore
        fetch_table = _ft
        fetch_table_admin = _fta

    vendors, inv_labels, asset_labels = _load_lookup_maps()
    rows: list[dict[str, Any]] = []
    fetcher = fetch_table_admin or fetch_table
    try:
        rows = list(fetcher("pricing_guide_items", limit=10000, order_by="description") or [])
    except Exception as exc:
        _LOG.debug("pricing_guide_items fetch failed, falling back to estimate_materials: %s", exc)
        rows = []

    if rows:
        out = [
            normalize_pricing_row(
                r,
                vendor_names=vendors,
                inventory_labels=inv_labels,
                asset_labels=asset_labels,
            )
            for r in rows
            if isinstance(r, dict) and str(r.get("description") or r.get("item_code") or "").strip()
        ]
        if not include_inactive:
            out = [r for r in out if r.get("is_active") is not False]
        return out

    legacy: list[dict[str, Any]] = []
    try:
        legacy = list(fetcher("estimate_materials", limit=10000, order_by="item_key") or [])
    except Exception:
        try:
            legacy = list(fetch_table("estimate_materials", limit=10000, order_by="item_key") or [])
        except Exception:
            legacy = []
    out = [
        normalize_pricing_row(r)
        for r in legacy
        if isinstance(r, dict) and str(r.get("item_key") or "").strip()
    ]
    if not include_inactive:
        out = [r for r in out if r.get("is_active") is not False]
    return out


@st.cache_data(ttl=120, show_spinner=False)
def cached_pricing_guide_rows(*, include_inactive: bool = True) -> list[dict[str, Any]]:
    return fetch_pricing_guide_rows(include_inactive=include_inactive)


def clear_pricing_guide_cache() -> None:
    cached_pricing_guide_rows.clear()
    try:
        from app.services.item_images import clear_item_image_url_cache
        from app.services.pricing_guide_images import clear_pricing_guide_image_cache

        clear_pricing_guide_image_cache()
        clear_item_image_url_cache()
    except Exception:
        pass
    try:
        from app.services.estimate_materials_catalog import clear_estimate_materials_catalog_cache

        clear_estimate_materials_catalog_cache()
    except Exception:
        pass


def pricing_guide_summary(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    data = rows if rows is not None else cached_pricing_guide_rows(include_inactive=True)
    active = [r for r in data if r.get("is_active") is not False]
    markups = [float(r.get("markup_pct") or 0) for r in active if float(r.get("default_cost") or 0) > 0]
    last_updated = ""
    for r in data:
        ts = str(r.get("updated_at") or "")
        if ts and ts > last_updated:
            last_updated = ts
    return {
        "active_count": len(active),
        "inventory_linked": sum(
            1 for r in active if r.get("linked_inventory_id") or r.get("inventory_item_id")
        ),
        "asset_linked": sum(1 for r in active if r.get("linked_asset_id") or r.get("asset_id")),
        "inventory_class": sum(1 for r in active if r.get("item_class") == "Inventory"),
        "asset_class": sum(1 for r in active if r.get("item_class") == "Asset"),
        "non_inventory_class": sum(1 for r in active if r.get("item_class") == "Non-Inventory"),
        "labor_count": sum(1 for r in active if r.get("item_type") == "Labor"),
        "equipment_count": sum(1 for r in active if r.get("item_type") == "Equipment"),
        "travel_count": sum(1 for r in active if r.get("item_type") == "Travel"),
        "avg_markup": round(sum(markups) / len(markups), 1) if markups else 0.0,
        "last_updated": last_updated[:10] if last_updated else "—",
    }


def _record_price_history(
    *,
    pricing_item_id: str,
    old_cost: float,
    new_cost: float,
    changed_by: str = "",
    notes: str = "",
    insert_row_admin: Callable[..., dict[str, Any]],
) -> None:
    if abs(old_cost - new_cost) < 0.0001:
        return
    try:
        insert_row_admin(
            "pricing_guide_price_history",
            {
                "pricing_item_id": pricing_item_id,
                "old_cost": old_cost,
                "new_cost": new_cost,
                "changed_by": changed_by,
                "changed_at": datetime.now(timezone.utc).isoformat(),
                "notes": notes,
            },
        )
    except Exception as exc:
        _LOG.warning("Could not record pricing history: %s", exc)


def _sync_inventory_link(
    *,
    pricing_item_id: str,
    inventory_item_id: str | None,
    update_rows_admin: Callable[..., list[dict[str, Any]]],
) -> None:
    if not pricing_item_id or not inventory_item_id:
        return
    try:
        update_rows_admin(
            "inventory_items",
            {
                "pricing_item_id": pricing_item_id,
                "pricing_guide_id": pricing_item_id,
            },
            {"id": inventory_item_id},
        )
        update_rows_admin(
            "pricing_guide_items",
            {
                "inventory_item_id": inventory_item_id,
                "linked_inventory_id": inventory_item_id,
                "item_class": "Inventory",
            },
            {"id": pricing_item_id},
        )
    except Exception:
        pass


def _sync_asset_link(
    *,
    pricing_item_id: str,
    asset_id: str | None,
    update_rows_admin: Callable[..., list[dict[str, Any]]],
) -> None:
    if not pricing_item_id or not asset_id:
        return
    try:
        update_rows_admin(
            "assets",
            {
                "pricing_item_id": pricing_item_id,
                "pricing_guide_id": pricing_item_id,
            },
            {"id": asset_id},
        )
        update_rows_admin(
            "pricing_guide_items",
            {
                "asset_id": asset_id,
                "linked_asset_id": asset_id,
                "item_class": "Asset",
            },
            {"id": pricing_item_id},
        )
    except Exception:
        pass


def resolve_live_unit_cost(row: dict[str, Any]) -> float:
    """Pull current cost from linked inventory or asset rental rate when available."""
    base = float(row.get("default_cost") or 0)
    item_class = str(row.get("item_class") or "").strip()
    inv_id = str(row.get("linked_inventory_id") or row.get("inventory_item_id") or "").strip()
    ast_id = str(row.get("linked_asset_id") or row.get("asset_id") or "").strip()
    if item_class == "Inventory" and inv_id:
        try:
            from app.pages._core._data import load_inventory
        except ImportError:
            from pages._core._data import load_inventory  # type: ignore
        inv = next((r for r in load_inventory() if str(r.get("id")) == inv_id), None)
        if inv:
            for key in ("average_cost", "last_purchase_cost", "unit_cost"):
                val = inv.get(key)
                if val not in (None, ""):
                    try:
                        cost = float(val)
                        if cost > 0:
                            return cost
                    except (TypeError, ValueError):
                        continue
    if item_class == "Asset" and ast_id:
        try:
            from app.pages._core._data import load_assets
        except ImportError:
            from pages._core._data import load_assets  # type: ignore
        asset = next((r for r in load_assets() if str(r.get("id")) == ast_id), None)
        if asset:
            for key in ("daily_rate", "hourly_rate", "rental_daily_rate", "purchase_cost", "current_value"):
                val = asset.get(key)
                if val not in (None, ""):
                    try:
                        cost = float(val)
                        if cost > 0:
                            return cost
                    except (TypeError, ValueError):
                        continue
    return base


def save_pricing_item(
    data: dict[str, Any],
    *,
    row_id: str | None = None,
    changed_by: str = "",
) -> tuple[bool, str]:
    try:
        from app.db import insert_row_admin, update_rows_admin
        from app.pages._core._crud import is_demo_id
    except ImportError:
        from db import insert_row_admin, update_rows_admin  # type: ignore
        from pages._core._crud import is_demo_id  # type: ignore

    cost = float(data.get("default_cost") or data.get("purchase_price") or 0)
    markup = float(data.get("default_markup_percent") or data.get("markup_pct") or 0)
    sell = data.get("default_sell_price") or data.get("sell_price") or data.get("customer_price")
    if sell in (None, ""):
        sell = calc_sell_price(cost, markup)
    else:
        sell = float(sell)

    description = str(data.get("description") or data.get("item") or "").strip()
    if not description:
        return False, "Description is required."

    item_type = str(data.get("item_type") or "Material").strip()
    if item_type not in PRICING_ITEM_TYPES:
        item_type = "Material"

    inv_link = data.get("linked_inventory_id") or data.get("inventory_item_id")
    ast_link = data.get("linked_asset_id") or data.get("asset_id")
    item_class = str(data.get("item_class") or "").strip()
    if item_class not in PRICING_ITEM_CLASSES:
        if inv_link:
            item_class = "Inventory"
        elif ast_link:
            item_class = "Asset"
        else:
            item_class = "Non-Inventory"

    item_code = str(data.get("item_code") or data.get("item_key") or "").strip()
    if not item_code:
        prefix = {
            "Labor": "LABOR",
            "Equipment": "EQ",
            "Travel": "TRV",
            "Subcontractor": "SUB",
        }.get(item_type, "PG")
        item_code = slug_item_code(description, prefix=prefix)

    payload: dict[str, Any] = {
        "item_code": item_code[:500],
        "item_type": item_type,
        "item_class": str(data.get("item_class") or "Non-Inventory").strip()[:32],
        "description": description[:2000],
        "category": str(data.get("category") or "").strip()[:200],
        "subcategory": str(data.get("subcategory") or data.get("subgroup") or "").strip()[:200],
        "unit": str(data.get("unit") or "EA").strip()[:32],
        "default_cost": cost,
        "default_markup_percent": markup,
        "default_sell_price": float(sell),
        "markup_percent": markup,
        "sell_price": float(sell),
        "item_number": str(data.get("item_number") or item_code).strip()[:200],
        "model_number": str(data.get("model_number") or "").strip()[:200],
        "sku": str(data.get("sku") or item_code).strip()[:200],
        "taxable": bool(data.get("taxable", True)),
        "is_active": bool(data.get("is_active", True)),
        "inventory_item_id": data.get("linked_inventory_id") or data.get("inventory_item_id") or None,
        "asset_id": data.get("linked_asset_id") or data.get("asset_id") or None,
        "linked_inventory_id": data.get("linked_inventory_id") or data.get("inventory_item_id") or None,
        "linked_asset_id": data.get("linked_asset_id") or data.get("asset_id") or None,
        "vendor_id": data.get("vendor_id") or None,
        "vendor": str(data.get("vendor") or data.get("vendor_name") or "").strip()[:200],
        "asset_recommended": bool(data.get("asset_recommended", False)),
        "labor_role": str(data.get("labor_role") or "").strip()[:200] or None,
        "equipment_type": str(data.get("equipment_type") or "").strip()[:200] or None,
        "travel_type": str(data.get("travel_type") or "").strip()[:200] or None,
        "notes": str(data.get("notes") or "").strip(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    for key in ("image_path", "image_url", "image_file_name", "image_mime_type", "qr_code_url"):
        if key in data:
            payload[key] = str(data.get(key) or "").strip()

    old_cost = 0.0
    saved_id = str(row_id or "").strip()

    try:
        if saved_id and not is_demo_id(saved_id):
            try:
                from app.db import fetch_table_admin as _fta
            except ImportError:
                from db import fetch_table_admin as _fta  # type: ignore
            existing = [
                r
                for r in list(_fta("pricing_guide_items", limit=10000) or [])
                if isinstance(r, dict) and str(r.get("id")) == saved_id
            ]
            if existing:
                old_cost = float(existing[0].get("default_cost") or 0)
            update_rows_admin("pricing_guide_items", payload, {"id": saved_id})
            _record_price_history(
                pricing_item_id=saved_id,
                old_cost=old_cost,
                new_cost=cost,
                changed_by=changed_by,
                insert_row_admin=insert_row_admin,
            )
        else:
            payload["created_at"] = payload["updated_at"]
            inserted = insert_row_admin("pricing_guide_items", payload)
            saved_id = str((inserted or {}).get("id") or "")
    except Exception as exc:
        return _save_legacy_estimate_material(data, row_id=row_id, exc=str(exc))

    if saved_id:
        inv_link = payload.get("linked_inventory_id") or payload.get("inventory_item_id")
        if inv_link:
            _sync_inventory_link(
                pricing_item_id=saved_id,
                inventory_item_id=str(inv_link),
                update_rows_admin=update_rows_admin,
            )
        ast_link = payload.get("linked_asset_id") or payload.get("asset_id")
        if ast_link:
            _sync_asset_link(
                pricing_item_id=saved_id,
                asset_id=str(ast_link),
                update_rows_admin=update_rows_admin,
            )

    clear_pricing_guide_cache()
    return True, "Saved."


def _save_legacy_estimate_material(
    data: dict[str, Any],
    *,
    row_id: str | None,
    exc: str,
) -> tuple[bool, str]:
    """Fallback when pricing_guide_items table is not migrated yet."""
    try:
        from app.db import insert_row_admin, update_rows_admin
        from app.pages._core._crud import is_demo_id
    except ImportError:
        from db import insert_row_admin, update_rows_admin  # type: ignore
        from pages._core._crud import is_demo_id  # type: ignore

    purchase = float(data.get("default_cost") or data.get("purchase_price") or 0)
    markup = float(data.get("default_markup_percent") or data.get("markup_pct") or 0)
    sell = data.get("default_sell_price") or calc_sell_price(purchase, markup)
    payload = {
        "item_key": str(data.get("item_code") or data.get("item_key") or slug_item_code(data.get("description") or "ITEM"))[:500],
        "description": str(data.get("description") or "")[:2000],
        "category": str(data.get("category") or "Pricing Guide")[:200],
        "unit": str(data.get("unit") or "EA")[:32],
        "purchase_price": purchase,
        "sell_price": float(sell),
        "vendor_item_number": str(data.get("vendor") or data.get("vendor_name") or "")[:200],
        "inventory_ref_id": data.get("inventory_item_id") or None,
        "is_active": bool(data.get("is_active", True)),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        if row_id and not is_demo_id(row_id):
            update_rows_admin("estimate_materials", payload, {"id": row_id})
        else:
            payload["created_at"] = payload["updated_at"]
            insert_row_admin("estimate_materials", payload)
        clear_pricing_guide_cache()
        return True, "Saved (legacy catalog)."
    except Exception as inner:
        return False, exc or str(inner)


def fetch_price_history(pricing_item_id: str) -> list[dict[str, Any]]:
    pid = str(pricing_item_id or "").strip()
    if not pid:
        return []
    try:
        from app.db import fetch_table_admin
    except ImportError:
        from db import fetch_table_admin  # type: ignore
    try:
        rows = list(
            fetch_table_admin("pricing_guide_price_history", limit=5000, order_by="changed_at")
            or []
        )
        matched = [r for r in rows if isinstance(r, dict) and str(r.get("pricing_item_id")) == pid]
        return list(reversed(matched))
    except Exception:
        return []


def create_pricing_item_from_inventory(
    inventory_row: dict[str, Any],
    *,
    changed_by: str = "",
) -> tuple[bool, str, str | None]:
    iid = str(inventory_row.get("id") or "").strip()
    if not iid:
        return False, "Invalid inventory item.", None
    description = str(
        inventory_row.get("item_name")
        or inventory_row.get("name")
        or inventory_row.get("description")
        or "Inventory Item"
    ).strip()
    unit_cost = float(inventory_row.get("unit_cost") or 0)
    ok, msg = save_pricing_item(
        {
            "item_type": "Material",
            "item_class": "Inventory",
            "description": description,
            "category": str(inventory_row.get("category") or "Inventory"),
            "unit": str(inventory_row.get("unit") or "EA"),
            "default_cost": unit_cost,
            "default_markup_percent": 25.0,
            "inventory_item_id": iid,
            "linked_inventory_id": iid,
            "sku": str(inventory_row.get("sku") or ""),
            "is_active": inventory_row.get("is_active") is not False,
        },
        changed_by=changed_by,
    )
    if not ok:
        return False, msg, None
    rows = [r for r in cached_pricing_guide_rows() if str(r.get("inventory_item_id") or "") == iid]
    pid = str(rows[0].get("id") or "") if rows else None
    return True, msg, pid


def create_pricing_item_from_estimate_line(
    data: dict[str, Any],
    *,
    changed_by: str = "",
) -> tuple[bool, str, str | None]:
    """Create a Pricing Guide master item from a custom estimate line."""
    description = str(data.get("description") or "").strip()
    if not description:
        return False, "Description is required to save to the Pricing Guide.", None

    sku = str(data.get("sku") or data.get("item_code") or "").strip()
    item_code = sku or slug_item_code(description, prefix="PG")
    ok, msg = save_pricing_item(
        {
            "item_type": str(data.get("item_type") or "Material"),
            "item_code": item_code,
            "description": description,
            "category": str(data.get("category") or ""),
            "unit": str(data.get("unit") or "EA"),
            "default_cost": float(data.get("unit_cost") or 0),
            "default_markup_percent": float(data.get("markup_percent") or 0),
            "taxable": bool(data.get("taxable", True)),
            "vendor_id": data.get("vendor_id") or None,
            "inventory_item_id": data.get("inventory_item_id") or None,
            "notes": str(data.get("notes") or ""),
            "is_active": True,
        },
        changed_by=changed_by,
    )
    if not ok:
        return False, msg, None

    rows = cached_pricing_guide_rows(include_inactive=True)
    for row in rows:
        if str(row.get("item_code") or "") == item_code:
            return True, "Added to Pricing Guide.", str(row.get("id") or "") or None
    desc_key = description.lower()
    for row in rows:
        if str(row.get("description") or "").strip().lower() == desc_key:
            return True, "Added to Pricing Guide.", str(row.get("id") or "") or None
    return True, msg, None


def link_inventory_to_pricing_item(
    inventory_id: str,
    pricing_item_id: str,
    *,
    sync_cost: bool = False,
) -> tuple[bool, str]:
    try:
        from app.db import update_rows_admin
    except ImportError:
        from db import update_rows_admin  # type: ignore

    iid = str(inventory_id or "").strip()
    pid = str(pricing_item_id or "").strip()
    if not iid or not pid:
        return False, "Inventory and pricing item are required."

    inv_payload: dict[str, Any] = {"pricing_item_id": pid}
    if sync_cost:
        inv_payload["sync_cost_to_pricing"] = True

    try:
        update_rows_admin("inventory_items", inv_payload, {"id": iid})
        update_rows_admin(
            "pricing_guide_items",
            {
                "inventory_item_id": iid,
                "linked_inventory_id": iid,
                "item_type": "Inventory",
                "item_class": "Inventory",
            },
            {"id": pid},
        )
        if sync_cost:
            try:
                from app.pages._core._data import load_inventory
            except ImportError:
                from pages._core._data import load_inventory  # type: ignore
            inv = next((r for r in load_inventory() if str(r.get("id")) == iid), None)
            if inv:
                unit_cost = float(inv.get("unit_cost") or 0)
                update_rows_admin(
                    "pricing_guide_items",
                    {"default_cost": unit_cost, "updated_at": datetime.now(timezone.utc).isoformat()},
                    {"id": pid},
                )
        clear_pricing_guide_cache()
        return True, "Linked to pricing guide item."
    except Exception as exc:
        return False, str(exc)


def link_asset_to_pricing_item(asset_id: str, pricing_item_id: str) -> tuple[bool, str]:
    try:
        from app.db import update_rows_admin
    except ImportError:
        from db import update_rows_admin  # type: ignore

    aid = str(asset_id or "").strip()
    pid = str(pricing_item_id or "").strip()
    if not aid or not pid:
        return False, "Asset and pricing item are required."
    try:
        update_rows_admin("assets", {"pricing_item_id": pid, "pricing_guide_id": pid}, {"id": aid})
        update_rows_admin(
            "pricing_guide_items",
            {
                "asset_id": aid,
                "linked_asset_id": aid,
                "item_type": "Equipment",
                "item_class": "Asset",
            },
            {"id": pid},
        )
        clear_pricing_guide_cache()
        return True, "Linked to pricing guide item."
    except Exception as exc:
        return False, str(exc)


def pricing_item_to_estimate_option(row: dict[str, Any]) -> dict[str, Any]:
    """Map normalized pricing row → estimate picker option."""
    cost = resolve_live_unit_cost(row)
    markup = float(row.get("markup_pct") or row.get("markup_percent") or row.get("default_markup_percent") or 0)
    sell = float(row.get("default_sell_price") or row.get("sell_price") or row.get("customer_price") or calc_sell_price(cost, markup))
    item_type = str(row.get("item_type") or "Material")
    item_class = str(row.get("item_class") or "Non-Inventory")
    description = str(row.get("description") or "—").strip()
    inv_id = row.get("linked_inventory_id") or row.get("inventory_item_id")
    ast_id = row.get("linked_asset_id") or row.get("asset_id")
    return {
        "id": str(row.get("id") or ""),
        "pricing_item_id": str(row.get("id") or ""),
        "item_type": item_type,
        "item_class": item_class,
        "description": description,
        "item_key": str(row.get("item_code") or row.get("sku") or ""),
        "sku": str(row.get("sku") or row.get("item_code") or ""),
        "item_number": str(row.get("item_number") or ""),
        "model_number": str(row.get("model_number") or ""),
        "category": str(row.get("category") or ""),
        "subcategory": str(row.get("subcategory") or ""),
        "unit": str(row.get("unit") or "EA"),
        "unit_cost": cost,
        "markup_pct": markup,
        "sell_price": sell,
        "vendor_id": row.get("vendor_id"),
        "vendor": str(row.get("vendor") or row.get("vendor_name") or ""),
        "vendor_name": str(row.get("vendor") or row.get("vendor_name") or ""),
        "taxable": row.get("taxable") is not False,
        "inventory_item_id": inv_id,
        "asset_id": ast_id,
        "linked_inventory_id": inv_id,
        "linked_asset_id": ast_id,
        "labor_role": row.get("labor_role"),
        "equipment_type": row.get("equipment_type"),
        "travel_type": row.get("travel_type"),
        "label": f"{description} — {item_class}",
    }


def search_pricing_rows(rows: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    q = str(query or "").strip().lower()
    if not q:
        return rows
    out: list[dict[str, Any]] = []
    for r in rows:
        haystack = " ".join(
            str(r.get(k) or "")
            for k in (
                "description",
                "item_code",
                "item_type",
                "item_class",
                "item_number",
                "model_number",
                "sku",
                "category",
                "subcategory",
                "vendor",
                "vendor_name",
                "labor_role",
                "equipment_type",
                "travel_type",
                "inventory_label",
                "asset_label",
                "status",
            )
        ).lower()
        if q in haystack:
            out.append(r)
    return out


def delete_pricing_item(row_id: str) -> tuple[bool, str]:
    """Permanently remove a pricing guide item."""
    rid = str(row_id or "").strip()
    if not rid:
        return False, "Missing item id."
    try:
        from app.pages._core._crud import is_demo_id
        from app.services.repository import delete_row
    except ImportError:
        from pages._core._crud import is_demo_id  # type: ignore
        from services.repository import delete_row  # type: ignore
    if is_demo_id(rid):
        return False, "Demo records cannot be deleted."
    result = delete_row("pricing_guide_items", {"id": rid})
    if result.ok:
        clear_pricing_guide_cache()
        return True, "Pricing item deleted."
    return False, result.error or "Could not delete pricing item."
