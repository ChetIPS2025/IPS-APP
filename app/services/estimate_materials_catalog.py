"""Estimate quote material catalog: ``estimate_materials`` table only (not raw inventory lists)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal

import streamlit as st

from app.services.materials_catalog_merge import (
    estimate_materials_payload_from_inventory,
    inventory_row_to_material_catalog_shape,
    is_inventory_materials_category,
    item_key_from_inventory_row,
)
_LOG = logging.getLogger(__name__)

_INV_FETCH_LIMIT = 100_000
_EM_FETCH_LIMIT = 100_000


@dataclass
class InventoryImportResult:
    """Result of inventory → ``estimate_materials`` import (or dry-run)."""

    total_inventory_fetched: int = 0
    eligible_active: int = 0
    skipped_inactive: int = 0
    skipped_materials_scope: int = 0
    skipped_not_in_selection: int = 0
    skipped_invalid: int = 0
    skipped_conflict: int = 0
    inserted: int = 0
    updated: int = 0
    dry_run: bool = False
    scope: str = "all_active"
    messages: list[str] = field(default_factory=list)

    def summary_text(self) -> str:
        scope_note = "all active categories" if self.scope == "all_active" else "**Materials** category only"
        total_written = self.inserted + self.updated
        lines: list[str] = []
        if self.dry_run:
            lines.append("_Preview only — no database changes._")
        lines.append(f"_Scope: {scope_note}_")
        lines.append(f"**Inventory rows loaded:** {self.total_inventory_fetched:,}")
        lines.append(f"**Eligible for this run:** {self.eligible_active:,}")
        if self.dry_run:
            lines.append(
                f"**Would import:** {total_written:,} catalog row(s) "
                f"({self.inserted:,} new, {self.updated:,} updates to existing links / keys)."
            )
        else:
            lines.append(
                f"**Imported {total_written:,}** catalog row(s) "
                f"({self.inserted:,} inserted, {self.updated:,} updated — duplicates merged, not double-inserted)."
            )
        if self.skipped_inactive:
            lines.append(f"**Skipped (inactive inventory):** {self.skipped_inactive:,}")
        if self.skipped_materials_scope:
            lines.append(f"**Skipped (outside Materials — scope filter):** {self.skipped_materials_scope:,}")
        if self.skipped_not_in_selection:
            lines.append(f"**Skipped (not in selected UUID list):** {self.skipped_not_in_selection:,}")
        if self.skipped_invalid:
            lines.append(f"**Skipped (invalid / missing description & SKU / no item key):** {self.skipped_invalid:,}")
        if self.skipped_conflict:
            lines.append(f"**Skipped (could not allocate unique item_key after 250 tries):** {self.skipped_conflict:,}")
        return "\n\n".join(lines)


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
        "category": str(row.get("category") or "Pricing Guide").strip() or "Pricing Guide",
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


def _pricing_row_to_catalog_shape(row: dict[str, Any]) -> dict[str, Any]:
    """Map unified ``pricing_guide_items`` row → legacy catalog shape."""
    pc = float(row.get("default_cost") or row.get("purchase_price") or 0)
    sp = float(row.get("default_sell_price") or row.get("sell_price") or row.get("customer_price") or 0)
    if not sp and pc:
        sp = round(pc * 1.25, 2)
    return {
        "id": row.get("id"),
        "item_key": str(row.get("item_code") or row.get("item_key") or "").strip(),
        "description": str(row.get("description") or "").strip(),
        "category": str(row.get("category") or "Pricing Guide").strip() or "Pricing Guide",
        "subgroup": str(row.get("subcategory") or row.get("subgroup") or "").strip(),
        "unit": str(row.get("unit") or "EA").strip() or "EA",
        "purchase_price": pc,
        "sell_price": sp,
        "vendor_item_number": str(row.get("vendor") or row.get("vendor_name") or "").strip(),
        "inventory_id": "",
        "is_active": bool(row.get("is_active", True)),
        "_source": "pricing_guide_items",
        "inventory_ref_id": row.get("inventory_item_id") or row.get("inventory_ref_id"),
        "item_type": str(row.get("item_type") or "Material"),
    }


def fetch_estimate_materials_catalog_rows(
    *,
    fetch_table: Callable[..., list[dict[str, Any]]],
    fetch_table_admin: Callable[..., list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    from app.services.pricing_guide_service import fetch_pricing_guide_rows
    unified = fetch_pricing_guide_rows(
        include_inactive=False,
        fetch_table=fetch_table,
        fetch_table_admin=fetch_table_admin,
    )
    if unified and unified[0].get("_source") != "estimate_materials":
        return [_pricing_row_to_catalog_shape(r) for r in unified]

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
    from app.db import fetch_table, fetch_table_admin

    return fetch_estimate_materials_catalog_rows(
        fetch_table=fetch_table,
        fetch_table_admin=fetch_table_admin,
    )


def clear_estimate_materials_catalog_cache() -> None:
    cached_estimate_materials_catalog_rows.clear()


def _load_inventory_for_import(
    *,
    fetch_table: Callable[..., list[dict[str, Any]]],
    fetch_table_admin: Callable[..., list[dict[str, Any]]] | None,
) -> list[dict[str, Any]]:
    fetcher = fetch_table_admin or fetch_table
    last_err: BaseException | None = None
    for ob in ("item_name", "sku", "created_at", None):
        try:
            return list(
                fetcher(
                    "inventory_items",
                    columns="*",
                    limit=_INV_FETCH_LIMIT,
                    order_by=ob,
                )
                or []
            )
        except Exception as exc:
            last_err = exc
            _LOG.debug("inventory_items fetch order_by=%r failed: %s", ob, exc)
    if last_err is not None:
        _LOG.warning("inventory_items import fetch failed after fallbacks: %s", last_err)
    return []


def _load_estimate_materials_for_import(
    *,
    fetch_table: Callable[..., list[dict[str, Any]]],
    fetch_table_admin: Callable[..., list[dict[str, Any]]] | None,
) -> list[dict[str, Any]]:
    fetcher = fetch_table_admin or fetch_table
    try:
        return list(
            fetcher(
                "estimate_materials",
                columns="*",
                limit=_EM_FETCH_LIMIT,
                order_by="item_key",
            )
            or []
        )
    except Exception as exc:
        _LOG.warning("estimate_materials preload failed: %s", exc)
        return []


def import_inventory_materials_into_estimate_catalog(
    *,
    fetch_table: Callable[..., list[dict[str, Any]]],
    insert_row_admin: Callable[..., dict[str, Any]],
    update_rows_admin: Callable[..., list[dict[str, Any]]],
    fetch_table_admin: Callable[..., list[dict[str, Any]]] | None = None,
    fetch_by_match_admin: Callable[..., list[dict[str, Any]]] | None = None,
    dry_run: bool = False,
    scope: Literal["all_active", "materials_only"] = "all_active",
    selected_inventory_ids: frozenset[str] | None = None,
) -> InventoryImportResult:
    """
    Copy / upsert **active** inventory rows into ``estimate_materials``.

    - **all_active** (default): every active inventory item (any category).
    - **materials_only**: legacy behavior — only ``category == Materials``.
    - **selected_inventory_ids**: when set, only those UUIDs (subset of active rows).

    Upsert: match by ``inventory_ref_id`` first, then by ``item_key``; updates existing
    rows instead of skipping when the link is empty or matches the same inventory row.

    ``fetch_by_match_admin`` is accepted for backward compatibility and ignored.
    """
    _ = fetch_by_match_admin
    result = InventoryImportResult(dry_run=dry_run, scope=scope)

    inv_rows = _load_inventory_for_import(fetch_table=fetch_table, fetch_table_admin=fetch_table_admin)
    result.total_inventory_fetched = len(inv_rows)

    em_rows = _load_estimate_materials_for_import(
        fetch_table=fetch_table,
        fetch_table_admin=fetch_table_admin,
    )
    by_ref: dict[str, dict[str, Any]] = {}
    by_key: dict[str, dict[str, Any]] = {}
    for em in em_rows:
        if not isinstance(em, dict):
            continue
        eid = str(em.get("id") or "").strip()
        if not eid:
            continue
        ref = str(em.get("inventory_ref_id") or "").strip()
        if ref:
            by_ref[ref] = em
        ik = str(em.get("item_key") or "").strip().upper()
        if ik:
            by_key[ik] = em

    now = datetime.now(timezone.utc).isoformat()

    for inv in inv_rows:
        if not isinstance(inv, dict):
            result.skipped_invalid += 1
            continue
        iid = str(inv.get("id") or "").strip()
        if not iid:
            result.skipped_invalid += 1
            continue

        if inv.get("is_active") is False:
            result.skipped_inactive += 1
            continue

        if selected_inventory_ids is not None and iid not in selected_inventory_ids:
            result.skipped_not_in_selection += 1
            continue

        if scope == "materials_only" and not is_inventory_materials_category(inv):
            result.skipped_materials_scope += 1
            continue

        nm = str(inv.get("item_name") or "").strip()
        sku = str(inv.get("sku") or "").strip()
        if not nm and not sku:
            result.skipped_invalid += 1
            continue

        base_ik = item_key_from_inventory_row(inv)
        if not str(base_ik or "").strip():
            result.skipped_invalid += 1
            continue

        result.eligible_active += 1

        payload = estimate_materials_payload_from_inventory(inv, item_key=base_ik)
        ik_upper = str(payload["item_key"] or "").strip().upper()

        em_by_ref = by_ref.get(iid)
        em_by_key = by_key.get(ik_upper)

        target: dict[str, Any] | None = None
        if em_by_ref is not None:
            target = em_by_ref
        elif em_by_key is not None:
            existing_ref = str(em_by_key.get("inventory_ref_id") or "").strip()
            if not existing_ref or existing_ref == iid:
                target = em_by_key
            else:
                # Same item_key already tied to a different inventory row — insert with a disambiguated key
                target = None

        write_payload = {
            **payload,
            "updated_at": now,
        }

        if target is not None:
            tid = str(target.get("id") or "").strip()
            if not tid:
                result.skipped_invalid += 1
                continue
            if dry_run:
                result.updated += 1
                continue
            update_rows_admin("estimate_materials", write_payload, {"id": tid})
            merged = {**target, **write_payload, "id": tid}
            old_key = str(target.get("item_key") or "").strip().upper()
            new_key = str(merged.get("item_key") or "").strip().upper()
            if old_key and old_key != new_key and by_key.get(old_key) is target:
                del by_key[old_key]
            by_ref[iid] = merged
            if new_key:
                by_key[new_key] = merged
            result.updated += 1
            continue

        # Insert — resolve item_key collisions when another inventory row already owns this key
        insert_key = str(payload["item_key"] or "").strip()
        suffix = 0
        while (
            insert_key.upper() in by_key
            and str(by_key[insert_key.upper()].get("inventory_ref_id") or "").strip() != iid
        ):
            suffix += 1
            insert_key = f"{base_ik}_{iid[:8]}" if suffix == 1 else f"{base_ik}_{iid[:8]}_{suffix}"
            if suffix > 250:
                insert_key = ""
                break
        if not insert_key:
            result.skipped_conflict += 1
            continue

        insert_payload = {
            **write_payload,
            "item_key": insert_key[:500],
            "description": str(write_payload.get("description") or insert_key)[:2000],
            "updated_at": now,
        }
        final_ku = str(insert_payload["item_key"] or "").strip().upper()

        if dry_run:
            result.inserted += 1
            phantom = {"id": f"dry-{iid}", **insert_payload}
            by_ref[iid] = phantom
            by_key[final_ku] = phantom
            continue

        inserted = insert_row_admin("estimate_materials", insert_payload)
        nid = str((inserted or {}).get("id") or "").strip()
        merged = {**insert_payload, "id": nid or iid}
        by_ref[iid] = merged
        by_key[final_ku] = merged
        result.inserted += 1

    result.messages = [
        f"scope={scope} dry_run={dry_run}",
        f"eligible={result.eligible_active} inserted={result.inserted} updated={result.updated}",
    ]
    _LOG.info(
        "inventory→estimate_materials import: fetched=%s eligible=%s ins=%s upd=%s "
        "skip_inactive=%s skip_materials_scope=%s skip_not_selected=%s skip_invalid=%s skip_conflict=%s dry_run=%s",
        result.total_inventory_fetched,
        result.eligible_active,
        result.inserted,
        result.updated,
        result.skipped_inactive,
        result.skipped_materials_scope,
        result.skipped_not_in_selection,
        result.skipped_invalid,
        result.skipped_conflict,
        dry_run,
    )
    return result


def sync_estimate_material_pricing_from_inventory(
    *,
    fetch_table: Callable[..., list[dict[str, Any]]],
    fetch_table_admin: Callable[..., list[dict[str, Any]]] | None,
    update_rows_admin: Callable[..., list[dict[str, Any]]],
) -> int:
    """Update purchase/sell on linked ``estimate_materials`` from ``inventory_items``."""
    fetcher = fetch_table_admin or fetch_table
    try:
        em_rows = list(fetcher("estimate_materials", limit=_EM_FETCH_LIMIT, order_by="item_key") or [])
    except Exception:
        return 0

    inv_by_id: dict[str, dict[str, Any]] = {}
    try:
        for r in _load_inventory_for_import(fetch_table=fetch_table, fetch_table_admin=fetch_table_admin):
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
