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
    "include_in_pricing_guide": (
        "include_in_pricing_guide",
        "pricing_guide",
        "billable",
        "billable_on_estimates",
    ),
    "vendor": ("vendor", "vendor_name"),
    "markup_percent": ("markup_percent", "markup", "default_markup_percent"),
    "taxable": ("taxable",),
    "notes": ("notes",),
    "item_code": ("item_code", "item_key"),
    "item_type": ("item_type", "estimate_line_type"),
    "product_type": ("product_type",),
    "connection_type": ("connection_type",),
    "pipe_size": ("pipe_size",),
    "dash_size": ("dash_size",),
    "pressure_class": ("pressure_class",),
    "body_shape": ("body_shape",),
    "material_grade": ("material_grade", "material"),
    "max_pressure_temp": ("max_pressure_temp", "max_pressure @ temp.", "max_pressure"),
    "max_steam_pressure_temp": (
        "max_steam_pressure_temp",
        "max_steam_pressure @ temp.",
        "max_steam_pressure",
    ),
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
    images_attached: int = 0
    images_skipped: int = 0
    qr_tokens_generated: int = 0
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


def asset_billable_for_pricing_guide(row: dict[str, Any]) -> bool:
    """True when an Asset-class catalog row should create or stay on Pricing Guide."""
    if normalize_item_class(row.get("item_class")) != "Asset":
        return False
    if _bool(row.get("include_in_pricing_guide")):
        return True
    return _bool(row.get("asset_recommended"))


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
        row_out: dict[str, Any] = {
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
            "include_in_pricing_guide": _bool(_row_get(raw, "include_in_pricing_guide")),
            "vendor": _str(_row_get(raw, "vendor")),
            "markup_percent": _num(_row_get(raw, "markup_percent")),
            "taxable": _bool(_row_get(raw, "taxable"), True),
            "notes": _str(_row_get(raw, "notes")),
            "item_type": _str(_row_get(raw, "item_type"))
            or infer_estimate_item_type(item_class, description=description),
            "item_code": _str(_row_get(raw, "item_code")),
        }
        for fitting_key in (
            "product_type",
            "connection_type",
            "pipe_size",
            "dash_size",
            "pressure_class",
            "body_shape",
            "material_grade",
            "max_pressure_temp",
            "max_steam_pressure_temp",
        ):
            val = _str(_row_get(raw, fitting_key))
            if val:
                row_out[fitting_key] = val
        out.append(row_out)
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
            ("item_code", "item_code"),
            ("model_number", "model_number"),
            ("item_number", "item_number"),
            ("description", "description"),
            ("sku", "model_number"),
            ("item_code", "model_number"),
            ("item_code", "item_number"),
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
            ("sku", "model_number"),
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
            ("asset_number", "model_number"),
            ("asset_id", "model_number"),
            ("asset_number", "item_number"),
            ("asset_id", "item_number"),
            ("asset_name", "description"),
        ),
    )


def _admin():
    from app.db import fetch_table_admin, insert_row_admin, update_rows_admin
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
    pg_patch: dict[str, Any] = {"updated_at": now}
    if inventory_id:
        pg_patch["linked_inventory_id"] = inventory_id
        pg_patch["inventory_item_id"] = inventory_id
    else:
        pg_patch["linked_inventory_id"] = None
        pg_patch["inventory_item_id"] = None
    if asset_id:
        pg_patch["linked_asset_id"] = asset_id
        pg_patch["asset_id"] = asset_id
    else:
        pg_patch["linked_asset_id"] = None
        pg_patch["asset_id"] = None
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


def _default_catalog_markup_percent(*, item_class: str = "Inventory") -> float:
    """Default markup from session app settings, fallback 25%."""
    fallback = 25.0
    try:
        import streamlit as st

        for prefix in ("ips_app_settings_admin", "ips_app_settings_settings"):
            for key_suffix in (
                "default_material_markup_pct",
                "default_equipment_markup_pct",
                "default_markup_pct",
            ):
                val = st.session_state.get(f"{prefix}_{key_suffix}")
                if val not in (None, ""):
                    return float(val)
            val = st.session_state.get(f"{prefix}_default_markup")
            if val not in (None, ""):
                return float(val)
    except Exception:
        pass
    if item_class == "Asset":
        return fallback
    return fallback


def _upsert_pricing_guide(
    row: dict[str, Any],
    existing: dict[str, Any] | None,
    *,
    changed_by: str = "",
) -> tuple[bool, str, str | None, bool]:
    from app.services.pricing_guide_service import calc_sell_price, save_pricing_item, slug_item_code
    cost = _num(row.get("unit_cost"))
    item_class = normalize_item_class(row.get("item_class"))
    markup = _num(row.get("markup_percent"))
    if not markup:
        markup = _default_catalog_markup_percent(item_class=item_class)
    sell = calc_sell_price(cost, markup)
    item_code = (
        _str(row.get("item_code"))
        or _str(row.get("sku") or row.get("model_number") or row.get("item_number"))
        or slug_item_code(row.get("description") or "ITEM")
    )
    payload: dict[str, Any] = {
        "item_code": item_code,
        "item_type": _str(row.get("item_type") or "Material"),
        "item_class": item_class,
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
        "sku": _str(row.get("sku") or row.get("model_number") or row.get("item_number") or item_code),
        "taxable": _bool(row.get("taxable"), True),
        "vendor": _str(row.get("vendor")),
        "notes": _str(row.get("notes")),
        "asset_recommended": _bool(row.get("asset_recommended")),
        "is_active": True,
    }
    from app.data.pricing_guide_fittings import FITTING_CATALOG_FIELD_NAMES
    for key in FITTING_CATALOG_FIELD_NAMES:
        if key in row and row.get(key) not in (None, ""):
            payload[key] = _str(row.get(key))
    row_id = str(existing.get("id") or "") if existing else None
    ok, msg = save_pricing_item(payload, row_id=row_id, changed_by=changed_by)
    if not ok:
        return False, msg, None, bool(existing)

    pid = row_id
    if not pid:
        from app.services.pricing_guide_service import cached_pricing_guide_rows
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
    qty = int(round(_num(row.get("qty_on_hand"))))
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
        "sku": _str(row.get("sku") or row.get("model_number") or row.get("item_number")),
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
            prev_qty = int(round(_num(existing.get("quantity_on_hand"))))
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


def _upsert_asset(
    row: dict[str, Any],
    pricing_item_id: str,
    existing: dict[str, Any] | None,
    *,
    include_in_pricing_guide: bool | None = None,
) -> tuple[bool, str, str | None, bool]:
    _, insert_row_admin, update_rows_admin = _admin()
    now = datetime.now(timezone.utc).isoformat()
    pid = str(pricing_item_id or "").strip()
    billable = include_in_pricing_guide
    if billable is None:
        billable = asset_billable_for_pricing_guide(row) if pid else False
    asset_no = (
        _str(row.get("model_number") or row.get("item_number") or row.get("sku"))
        or slug_asset_number(row.get("description") or "ASSET")
    )
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
        "pricing_guide_id": pid or None,
        "pricing_item_id": pid or None,
        "include_in_pricing_guide": bool(billable),
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
    from app.services.pricing_guide_service import slug_item_code
    return slug_item_code(text, prefix="AST")


def _build_import_image_index(
    image_files: list[tuple[str, bytes]] | None = None,
    *,
    include_local_folder: bool = True,
) -> dict[str, tuple[str, bytes]]:
    from app.services.item_images import build_uploaded_image_index, load_local_item_image_index
    index = build_uploaded_image_index(image_files or [])
    if include_local_folder:
        for key, val in load_local_item_image_index().items():
            index.setdefault(key, val)
    return index


def _attach_import_image(
    *,
    row: dict[str, Any],
    image_index: dict[str, tuple[str, bytes]],
    table: str,
    record_id: str | None,
    entity_type: str,
    existing: dict[str, Any] | None,
    result: CatalogImportResult,
    high_confidence_only: bool = True,
) -> None:
    if not record_id:
        return
    from app.services.item_images import find_image_match_for_row, persist_item_image
    match = find_image_match_for_row(row, image_index)
    if not match:
        return
    if high_confidence_only and match.confidence != "high":
        return
    filename, data = match.filename, match.data
    svc = persist_item_image(
        table=table,
        record_id=str(record_id),
        entity_type=entity_type,
        image_bytes=data,
        filename=filename,
        existing=existing,
        uploaded_by="catalog-import",
    )
    if not svc.ok:
        result.errors.append(f"Image for {table} {record_id}: {svc.error}")
        return
    if isinstance(svc.data, dict) and svc.data.get("skipped"):
        result.images_skipped += 1
    else:
        result.images_attached += 1


def _ensure_import_qr_codes(
    inventory_ids: set[str],
    asset_ids: set[str],
) -> int:
    """Generate QR tokens for imported inventory/asset rows missing them."""
    generated = 0
    from app.services.assets_service import ensure_asset_qr_tokens, get_asset
    from app.services.inventory_service import ensure_inventory_qr_tokens, get_inventory_item
    inv_rows = [get_inventory_item(iid) for iid in inventory_ids if get_inventory_item(iid)]
    if inv_rows:
        inv_result = ensure_inventory_qr_tokens(inv_rows)
        if inv_result.ok and isinstance(inv_result.data, dict):
            generated += int(inv_result.data.get("updated") or 0)

    ast_rows = [get_asset(aid) for aid in asset_ids if get_asset(aid)]
    if ast_rows:
        ast_result = ensure_asset_qr_tokens(ast_rows)
        if ast_result.ok and isinstance(ast_result.data, dict):
            generated += int(ast_result.data.get("updated") or 0)
    return generated


def import_catalog_csv(
    text: str,
    *,
    changed_by: str = "",
    image_files: list[tuple[str, bytes]] | None = None,
    include_local_image_folder: bool = False,
    attach_images: bool = False,
) -> CatalogImportResult:
    rows = parse_catalog_csv(text)
    if not rows:
        return CatalogImportResult(ok=False, message="No valid rows found in CSV.", skipped=0)

    pricing_rows = _fetch_all("pricing_guide_items")
    inventory_rows = _fetch_all("inventory_items")
    asset_rows = _fetch_all("assets")
    image_index = _build_import_image_index(
        image_files,
        include_local_folder=include_local_image_folder,
    )

    result = CatalogImportResult(ok=True, message="Import complete.")
    touched_inventory_ids: set[str] = set()
    touched_asset_ids: set[str] = set()
    for idx, row in enumerate(rows, start=1):
        item_class = normalize_item_class(row.get("item_class"))
        billable_asset = asset_billable_for_pricing_guide(row)

        if item_class == "Asset" and not billable_asset:
            ast_existing = find_matching_asset_item(row, asset_rows)
            ok_a, msg_a, ast_id, ast_upd = _upsert_asset(
                row,
                "",
                ast_existing,
                include_in_pricing_guide=False,
            )
            if not ok_a:
                result.errors.append(f"Row {idx} asset: {msg_a}")
                result.skipped += 1
            elif ast_upd:
                result.updated_assets += 1
            else:
                result.created_assets += 1
                if ast_id:
                    asset_rows.append({"id": ast_id, **row})
            if ast_id:
                touched_asset_ids.add(str(ast_id))
            continue

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
        inv_existing: dict[str, Any] | None = None
        ast_existing: dict[str, Any] | None = None

        if item_class == "Inventory":
            inv_existing = None
            if pg_existing and pg_existing.get("linked_inventory_id"):
                inv_existing = next((r for r in inventory_rows if str(r.get("id")) == str(pg_existing.get("linked_inventory_id"))), None)
            if not inv_existing:
                inv_existing = find_matching_inventory_item(row, inventory_rows)
            ok_i, msg_i, inv_id, inv_upd = _upsert_inventory(row, pid, inv_existing)
            if not ok_i:
                result.errors.append(f"Row {idx} inventory: {msg_i}")
            elif inv_upd:
                result.updated_inventory += 1
            else:
                result.created_inventory += 1
                if inv_id:
                    inventory_rows.append({"id": inv_id, **row})
            if inv_id:
                touched_inventory_ids.add(str(inv_id))

        elif item_class == "Asset":
            ast_existing = None
            if pg_existing and pg_existing.get("linked_asset_id"):
                ast_existing = next((r for r in asset_rows if str(r.get("id")) == str(pg_existing.get("linked_asset_id"))), None)
            if not ast_existing:
                ast_existing = find_matching_asset_item(row, asset_rows)
            ok_a, msg_a, ast_id, ast_upd = _upsert_asset(
                row,
                pid,
                ast_existing,
                include_in_pricing_guide=True,
            )
            if not ok_a:
                result.errors.append(f"Row {idx} asset: {msg_a}")
            elif ast_upd:
                result.updated_assets += 1
            else:
                result.created_assets += 1
                if ast_id:
                    asset_rows.append({"id": ast_id, **row})
            if ast_id:
                touched_asset_ids.add(str(ast_id))

        _sync_catalog_links(pricing_item_id=pid, inventory_id=inv_id, asset_id=ast_id)

        if attach_images:
            pg_record = pg_existing or next((r for r in pricing_rows if str(r.get("id")) == str(pid)), None)
            _attach_import_image(
                row=row,
                image_index=image_index,
                table="pricing_guide_items",
                record_id=pid,
                entity_type="pricing_guide",
                existing=pg_record if isinstance(pg_record, dict) else None,
                result=result,
                high_confidence_only=True,
            )
            if inv_id:
                inv_record = inv_existing or next((r for r in inventory_rows if str(r.get("id")) == str(inv_id)), None)
                _attach_import_image(
                    row=row,
                    image_index=image_index,
                    table="inventory_items",
                    record_id=inv_id,
                    entity_type="inventory",
                    existing=inv_record if isinstance(inv_record, dict) else None,
                    result=result,
                    high_confidence_only=True,
                )
            if ast_id:
                ast_record = ast_existing or next((r for r in asset_rows if str(r.get("id")) == str(ast_id)), None)
                _attach_import_image(
                    row=row,
                    image_index=image_index,
                    table="assets",
                    record_id=ast_id,
                    entity_type="assets",
                    existing=ast_record if isinstance(ast_record, dict) else None,
                    result=result,
                    high_confidence_only=True,
                )

        pg_row = {**row, "id": pid, "linked_inventory_id": inv_id, "linked_asset_id": ast_id, "item_class": item_class}
        if pg_existing:
            for i, ex in enumerate(pricing_rows):
                if str(ex.get("id")) == str(pg_existing.get("id")):
                    pricing_rows[i] = {**ex, **pg_row}
                    break
        else:
            pricing_rows.append(pg_row)

    from app.services.pricing_guide_service import clear_pricing_guide_cache
    clear_pricing_guide_cache()
    result.qr_tokens_generated = _ensure_import_qr_codes(touched_inventory_ids, touched_asset_ids)

    if result.errors:
        result.message = f"Imported with {len(result.errors)} warning(s)."
    else:
        result.message = (
            f"Pricing Guide: {result.created_pricing} created, {result.updated_pricing} updated. "
            f"Inventory: {result.created_inventory} created, {result.updated_inventory} updated. "
            f"Assets: {result.created_assets} created, {result.updated_assets} updated. "
            f"Images linked: {result.images_attached} ({result.images_skipped} skipped). "
            f"QR codes generated: {result.qr_tokens_generated}. "
            f"Use Import Review to approve item photos before attach."
        )
    return result
