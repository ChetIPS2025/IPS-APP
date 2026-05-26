"""Unified catalog CSV import — Pricing Guide, Inventory, and Assets."""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_LOG = logging.getLogger(__name__)

ITEM_CLASSES: tuple[str, ...] = ("Inventory", "Asset", "Non-Inventory")

CSV_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "description": ("description", "item", "item_name", "name"),
    "category": ("category",),
    "subcategory": ("subcategory", "sub_group", "subgroup"),
    "unit": ("unit", "uom"),
    "qty_on_hand": ("qty_on_hand", "quantity_on_hand", "quantity", "qty"),
    "unit_cost": ("unit_cost", "default_cost", "cost", "purchase_price"),
    "total_cost": ("total_cost",),
    "item_number": ("item_number", "item_no", "item_code"),
    "model_number": ("model_number", "model", "model_no"),
    "sku": ("sku", "vendor_sku"),
    "item_class": ("item_class", "class", "item_type_class"),
    "asset_recommended": ("asset_recommended", "asset_recommend", "recommend_asset"),
    "vendor": ("vendor", "vendor_name"),
    "markup_percent": ("markup_percent", "markup", "default_markup_percent"),
    "taxable": ("taxable",),
    "notes": ("notes",),
}


@dataclass
class CatalogImportResult:
    ok: bool
    message: str
    created_pricing: int = 0
    updated_pricing: int = 0
    created_inventory: int = 0
    updated_inventory: int = 0
    created_assets: int = 0
    updated_assets: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _norm_key(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _row_get(row: dict[str, Any], canonical: str) -> Any:
    aliases = CSV_FIELD_ALIASES.get(canonical, (canonical,))
    for alias in aliases:
        for key, val in row.items():
            if _norm_key(key) == _norm_key(alias):
                return val
    return None


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def _str(value: Any, default: str = "") -> str:
    return str(value or default).strip()


def normalize_item_class(raw: Any) -> str:
    s = _str(raw).lower().replace("_", " ").replace("-", " ")
    if s in ("inventory", "inv", "stock", "material", "consumable"):
        return "Inventory"
    if s in ("asset", "equipment", "tool", "rental"):
        return "Asset"
    if s in ("non inventory", "noninventory", "non-inventory", "estimate", "estimate only", "pricing only"):
        return "Non-Inventory"
    if raw in ITEM_CLASSES:
        return str(raw)
    return "Non-Inventory"


def infer_estimate_item_type(item_class: str, *, description: str = "") -> str:
    if item_class == "Inventory":
        return "Material"
    if item_class == "Asset":
        return "Equipment"
    desc = description.lower()
    if "labor" in desc or "weld" in desc and "rate" in desc:
        return "Labor"
    if "travel" in desc or "per diem" in desc or "hotel" in desc:
        return "Travel"
    if "subcontract" in desc:
        return "Subcontractor"
    return "Material"


def parse_catalog_csv(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    out: list[dict[str, Any]] = []
    for raw in reader:
        if not isinstance(raw, dict):
            continue
        description = _str(_row_get(raw, "description"))
        if not description:
            continue
        item_class = normalize_item_class(_row_get(raw, "item_class"))
        asset_rec = _bool(_row_get(raw, "asset_recommended"))
        if asset_rec and item_class == "Non-Inventory":
            item_class = "Asset"
        out.append(
            {
                "description": description,
                "category": _str(_row_get(raw, "category")),
                "subcategory": _str(_row_get(raw, "subcategory")),
                "unit": _str(_row_get(raw, "unit")) or "EA",
                "qty_on_hand": _num(_row_get(raw, "qty_on_hand")),
                "unit_cost": _num(_row_get(raw, "unit_cost")),
                "total_cost": _num(_row_get(raw, "total_cost")),
                "item_number": _str(_row_get(raw, "item_number")),
                "model_number": _str(_row_get(raw, "model_number")),
                "sku": _str(_row_get(raw, "sku")),
                "item_class": item_class,
                "asset_recommended": asset_rec,
                "vendor": _str(_row_get(raw, "vendor")),
                "markup_percent": _num(_row_get(raw, "markup_percent")),
                "taxable": _bool(_row_get(raw, "taxable"), True),
                "notes": _str(_row_get(raw, "notes")),
                "item_type": infer_estimate_item_type(item_class, description=description),
            }
        )
    return out


def _match_existing_row(
    row: dict[str, Any],
    existing: list[dict[str, Any]],
    *,
    field_map: tuple[tuple[str, str], ...],
) -> dict[str, Any] | None:
    """Match duplicate rows using ordered field/needle pairs."""
    for field, needle_key in field_map:
        needle = _str(row.get(needle_key)).lower()
        if not needle:
            continue
        for ex in existing:
            val = _str(ex.get(field)).lower()
            if val and val == needle:
                return ex
    return None


def find_matching_pricing_item(
    row: dict[str, Any],
    existing: list[dict[str, Any]],
) -> dict[str, Any] | None:
    return _match_existing_row(
        row,
        existing,
        field_map=(
            ("model_number", "model_number"),
            ("item_number", "item_number"),
            ("sku", "sku"),
            ("item_code", "sku"),
            ("item_code", "item_number"),
            ("description", "description"),
        ),
    )


def find_matching_inventory_item(
    row: dict[str, Any],
    existing: list[dict[str, Any]],
) -> dict[str, Any] | None:
    return _match_existing_row(
        row,
        existing,
        field_map=(
            ("sku", "sku"),
            ("sku", "item_number"),
            ("item_name", "description"),
            ("description", "description"),
        ),
    )


def find_matching_asset_item(
    row: dict[str, Any],
    existing: list[dict[str, Any]],
) -> dict[str, Any] | None:
    return _match_existing_row(
        row,
        existing,
        field_map=(
            ("model", "model_number"),
            ("asset_number", "item_number"),
            ("asset_id", "item_number"),
            ("serial_number", "sku"),
            ("asset_name", "description"),
        ),
    )


def _admin():
    try:
        from app.db import fetch_table_admin, insert_row_admin, update_rows_admin
    except ImportError:
        from db import fetch_table_admin, insert_row_admin, update_rows_admin  # type: ignore
    return fetch_table_admin, insert_row_admin, update_rows_admin


def _fetch_all(table: str) -> list[dict[str, Any]]:
    fetch_table_admin, _, _ = _admin()
    try:
        return [r for r in list(fetch_table_admin(table, limit=10000) or []) if isinstance(r, dict)]
    except Exception as exc:
        _LOG.warning("Could not fetch %s: %s", table, exc)
        return []


def _sync_catalog_links(
    *,
    pricing_item_id: str,
    inventory_id: str | None,
    asset_id: str | None,
) -> None:
    _, _, update_rows_admin = _admin()
    now = datetime.now(timezone.utc).isoformat()
    pg_patch: dict[str, Any] = {
        "linked_inventory_id": inventory_id,
        "linked_asset_id": asset_id,
        "inventory_item_id": inventory_id,
        "asset_id": asset_id,
        "updated_at": now,
    }
    try:
        update_rows_admin("pricing_guide_items", pg_patch, {"id": pricing_item_id})
    except Exception as exc:
        _LOG.warning("Could not sync pricing guide links: %s", exc)
    if inventory_id:
        try:
            update_rows_admin(
                "inventory_items",
                {"pricing_guide_id": pricing_item_id, "pricing_item_id": pricing_item_id, "updated_at": now},
                {"id": inventory_id},
            )
        except Exception as exc:
            _LOG.warning("Could not sync inventory pricing link: %s", exc)
    if asset_id:
        try:
            update_rows_admin(
                "assets",
                {"pricing_guide_id": pricing_item_id, "pricing_item_id": pricing_item_id, "updated_at": now},
                {"id": asset_id},
            )
        except Exception as exc:
            _LOG.warning("Could not sync asset pricing link: %s", exc)


def _upsert_pricing_guide(
    row: dict[str, Any],
    existing: dict[str, Any] | None,
    *,
    changed_by: str = "",
) -> tuple[bool, str, str | None, bool]:
    try:
        from app.services.pricing_guide_service import calc_sell_price, save_pricing_item, slug_item_code
    except ImportError:
        from services.pricing_guide_service import calc_sell_price, save_pricing_item, slug_item_code  # type: ignore

    cost = _num(row.get("unit_cost"))
    markup = _num(row.get("markup_percent"))
    sell = calc_sell_price(cost, markup) if cost or markup else 0.0
    item_code = _str(row.get("sku") or row.get("item_number")) or slug_item_code(row.get("description") or "ITEM")
    payload: dict[str, Any] = {
        "item_code": item_code,
        "item_type": _str(row.get("item_type") or "Material"),
        "item_class": normalize_item_class(row.get("item_class")),
        "description": _str(row.get("description")),
        "category": _str(row.get("category")),
        "subcategory": _str(row.get("subcategory")),
        "unit": _str(row.get("unit")) or "EA",
        "default_cost": cost,
        "default_markup_percent": markup,
        "default_sell_price": sell,
        "markup_percent": markup,
        "sell_price": sell,
        "item_number": _str(row.get("item_number")),
        "model_number": _str(row.get("model_number")),
        "sku": _str(row.get("sku") or item_code),
        "taxable": _bool(row.get("taxable"), True),
        "vendor": _str(row.get("vendor")),
        "notes": _str(row.get("notes")),
        "asset_recommended": _bool(row.get("asset_recommended")),
        "is_active": True,
    }
    row_id = str(existing.get("id") or "") if existing else None
    ok, msg = save_pricing_item(payload, row_id=row_id, changed_by=changed_by)
    if not ok:
        return False, msg, None, bool(existing)

    pid = row_id
    if not pid:
        try:
            from app.services.pricing_guide_service import cached_pricing_guide_rows
        except ImportError:
            from services.pricing_guide_service import cached_pricing_guide_rows  # type: ignore
        for pg in cached_pricing_guide_rows(include_inactive=True):
            if _str(pg.get("item_code")) == item_code:
                pid = str(pg.get("id") or "")
                break
            if _str(pg.get("description")).lower() == _str(row.get("description")).lower():
                pid = str(pg.get("id") or "")
                break
    return True, msg, pid or None, bool(existing)


def _upsert_inventory(row: dict[str, Any], pricing_item_id: str, existing: dict[str, Any] | None) -> tuple[bool, str, str | None, bool]:
    _, insert_row_admin, update_rows_admin = _admin()
    now = datetime.now(timezone.utc).isoformat()
    qty = _num(row.get("qty_on_hand"))
    cost = _num(row.get("unit_cost"))
    payload: dict[str, Any] = {
        "item_name": _str(row.get("description")),
        "category": _str(row.get("category")),
        "unit": _str(row.get("unit")) or "EA",
        "quantity_on_hand": qty,
        "unit_cost": cost,
        "last_purchase_cost": cost,
        "average_cost": cost,
        "vendor": _str(row.get("vendor")),
        "sku": _str(row.get("sku")),
        "stock_location": _str(row.get("stock_location")),
        "storage_location": _str(row.get("stock_location")),
        "pricing_guide_id": pricing_item_id,
        "pricing_item_id": pricing_item_id,
        "is_active": True,
        "updated_at": now,
    }
    try:
        if existing and str(existing.get("id") or ""):
            iid = str(existing["id"])
            prev_qty = _num(existing.get("quantity_on_hand"))
            payload["quantity_on_hand"] = prev_qty + qty if qty else prev_qty
            if cost > 0:
                payload["last_purchase_cost"] = cost
                prev_avg = _num(existing.get("average_cost") or existing.get("unit_cost"))
                payload["average_cost"] = cost if not prev_avg else round((prev_avg + cost) / 2.0, 4)
            update_rows_admin("inventory_items", payload, {"id": iid})
            return True, "Inventory updated.", iid, True
        payload["created_at"] = now
        inserted = insert_row_admin("inventory_items", payload)
        iid = str((inserted or {}).get("id") or "")
        return True, "Inventory created.", iid or None, False
    except Exception as exc:
        return False, str(exc), None, bool(existing)


def _upsert_asset(row: dict[str, Any], pricing_item_id: str, existing: dict[str, Any] | None) -> tuple[bool, str, str | None, bool]:
    _, insert_row_admin, update_rows_admin = _admin()
    now = datetime.now(timezone.utc).isoformat()
    asset_no = _str(row.get("item_number") or row.get("sku")) or slug_asset_number(row.get("description") or "ASSET")
    payload: dict[str, Any] = {
        "asset_id": asset_no,
        "asset_number": asset_no,
        "asset_name": _str(row.get("description")),
        "category": _str(row.get("category")),
        "subcategory": _str(row.get("subcategory")),
        "model": _str(row.get("model_number")),
        "serial_number": _str(row.get("sku")),
        "status": "Available",
        "purchase_cost": _num(row.get("unit_cost")),
        "current_value": _num(row.get("unit_cost")),
        "pricing_guide_id": pricing_item_id,
        "pricing_item_id": pricing_item_id,
        "notes": _str(row.get("notes")),
        "is_active": True,
        "updated_at": now,
    }
    try:
        if existing and str(existing.get("id") or ""):
            aid = str(existing["id"])
            patch = {**payload}
            if _num(row.get("unit_cost")) > 0:
                patch["purchase_cost"] = _num(row.get("unit_cost"))
                patch["current_value"] = _num(row.get("unit_cost"))
            update_rows_admin("assets", patch, {"id": aid})
            return True, "Asset updated.", aid, True
        payload["created_at"] = now
        inserted = insert_row_admin("assets", payload)
        aid = str((inserted or {}).get("id") or "")
        return True, "Asset created.", aid or None, False
    except Exception as exc:
        return False, str(exc), None, bool(existing)


def slug_asset_number(text: str) -> str:
    try:
        from app.services.pricing_guide_service import slug_item_code
    except ImportError:
        from services.pricing_guide_service import slug_item_code  # type: ignore
    return slug_item_code(text, prefix="AST")


def import_catalog_csv(
    text: str,
    *,
    changed_by: str = "",
) -> CatalogImportResult:
    rows = parse_catalog_csv(text)
    if not rows:
        return CatalogImportResult(ok=False, message="No valid rows found in CSV.", skipped=0)

    pricing_rows = _fetch_all("pricing_guide_items")
    inventory_rows = _fetch_all("inventory_items")
    asset_rows = _fetch_all("assets")

    result = CatalogImportResult(ok=True, message="Import complete.")
    for idx, row in enumerate(rows, start=1):
        item_class = normalize_item_class(row.get("item_class"))
        pg_existing = find_matching_pricing_item(row, pricing_rows)
        ok, msg, pid, was_update = _upsert_pricing_guide(row, pg_existing, changed_by=changed_by)
        if not ok or not pid:
            result.errors.append(f"Row {idx}: {msg}")
            result.skipped += 1
            continue
        if was_update:
            result.updated_pricing += 1
        else:
            result.created_pricing += 1

        inv_id: str | None = None
        ast_id: str | None = None

        if item_class == "Inventory":
            inv_existing = None
            if pg_existing and pg_existing.get("linked_inventory_id"):
                inv_existing = next((r for r in inventory_rows if str(r.get("id")) == str(pg_existing.get("linked_inventory_id"))), None)
            if not inv_existing:
                inv_existing = find_matching_pricing_item(row, inventory_rows)
            ok_i, msg_i, inv_id, inv_upd = _upsert_inventory(row, pid, inv_existing)
            if not ok_i:
                result.errors.append(f"Row {idx} inventory: {msg_i}")
            elif inv_upd:
                result.updated_inventory += 1
            else:
                result.created_inventory += 1
                if inv_id:
                    inventory_rows.append({"id": inv_id, **row})

        elif item_class == "Asset":
            ast_existing = None
            if pg_existing and pg_existing.get("linked_asset_id"):
                ast_existing = next((r for r in asset_rows if str(r.get("id")) == str(pg_existing.get("linked_asset_id"))), None)
            if not ast_existing:
                ast_existing = find_matching_asset_item(row, asset_rows)
            ok_a, msg_a, ast_id, ast_upd = _upsert_asset(row, pid, ast_existing)
            if not ok_a:
                result.errors.append(f"Row {idx} asset: {msg_a}")
            elif ast_upd:
                result.updated_assets += 1
            else:
                result.created_assets += 1
                if ast_id:
                    asset_rows.append({"id": ast_id, **row})

        _sync_catalog_links(pricing_item_id=pid, inventory_id=inv_id, asset_id=ast_id)

        pg_row = {**row, "id": pid, "linked_inventory_id": inv_id, "linked_asset_id": ast_id, "item_class": item_class}
        if pg_existing:
            for i, ex in enumerate(pricing_rows):
                if str(ex.get("id")) == str(pg_existing.get("id")):
                    pricing_rows[i] = {**ex, **pg_row}
                    break
        else:
            pricing_rows.append(pg_row)

    try:
        from app.services.pricing_guide_service import clear_pricing_guide_cache
    except ImportError:
        from services.pricing_guide_service import clear_pricing_guide_cache  # type: ignore
    clear_pricing_guide_cache()

    if result.errors:
        result.message = f"Imported with {len(result.errors)} warning(s)."
    else:
        result.message = (
            f"Pricing Guide: {result.created_pricing} created, {result.updated_pricing} updated. "
            f"Inventory: {result.created_inventory} created, {result.updated_inventory} updated. "
            f"Assets: {result.created_assets} created, {result.updated_assets} updated."
        )
    return result
