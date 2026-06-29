"""Lookup values for dropdowns (Supabase ips_lookup_* with constants fallback)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

_LOG = logging.getLogger(__name__)

# slug -> constants tuple name in app.utils.constants
_LOOKUP_SLUGS: dict[str, str] = {
    "customers": "CUSTOMERS",
    "vendors": "VENDORS",
    "departments": "DEPARTMENTS",
    "locations": "LOCATIONS",
    "crews": "CREWS",
    "job_statuses": "JOB_STATUSES",
    "estimate_statuses": "ESTIMATE_STATUSES",
    "inventory_categories": "INVENTORY_CATEGORIES",
    "inventory_statuses": "INVENTORY_STATUSES",
    "asset_categories": "ASSET_CATEGORIES",
    "asset_statuses": "ASSET_STATUSES",
    "units": "UNITS",
    "labor_types": "LABOR_TYPES",
    "certification_types": "CERTIFICATION_TYPES",
    "document_types": "DOCUMENT_TYPES",
    "user_roles": "ROLES",
    "permission_groups": "PERMISSION_GROUPS",
    "task_statuses": "TASK_STATUSES",
    "task_priorities": "TASK_PRIORITIES",
    "document_link_modules": "DOCUMENT_LINK_MODULES",
    "update_categories": "UPDATE_CATEGORIES",
}

# Human labels used in admin UI -> slug
_LOOKUP_LABEL_TO_SLUG: dict[str, str] = {
    "Customers": "customers",
    "Vendors": "vendors",
    "Departments": "departments",
    "Locations": "locations",
    "Crews": "crews",
    "Job Statuses": "job_statuses",
    "Estimate Statuses": "estimate_statuses",
    "Inventory Categories": "inventory_categories",
    "Asset Categories": "asset_categories",
    "Certification Types": "certification_types",
    "Document Types": "document_types",
    "User Roles": "user_roles",
    "Permission Groups": "permission_groups",
}


def _constants_fallback(slug: str) -> list[str]:
    try:
        from app.utils import constants as c
    except ImportError:
        from utils import constants as c  # type: ignore
    attr = _LOOKUP_SLUGS.get(slug, "")
    tup = getattr(c, attr, None) if attr else None
    if tup:
        return [str(x) for x in tup]
    return []


def slug_for_label(label: str) -> str:
    return _LOOKUP_LABEL_TO_SLUG.get(label, label.lower().replace(" ", "_"))


def clear_lookup_cache() -> None:
    """Invalidate DB read caches and admin session mirrors for lookup tables."""
    try:
        from app.services.repository import clear_data_cache_for_table
    except ImportError:
        from services.repository import clear_data_cache_for_table  # type: ignore
    clear_data_cache_for_table("ips_lookup_values")
    clear_data_cache_for_table("ips_lookup_tables")


def _resolve_table_id(slug: str, label: str) -> tuple[str | None, str | None]:
    try:
        from app.services.repository import ServiceResult, fetch_rows, insert_row
    except ImportError:
        from services.repository import ServiceResult, fetch_rows, insert_row  # type: ignore

    tables, err = fetch_rows("ips_lookup_tables", limit=200, order_by="sort_order")
    if err or not tables:
        return None, err or "Lookup tables not available."

    for t in tables or []:
        if str(t.get("slug") or "").lower() == slug:
            return str(t.get("id") or "").strip() or None, None

    ins: ServiceResult = insert_row(
        "ips_lookup_tables",
        {"slug": slug, "label": label, "sort_order": 0},
    )
    if ins.ok and ins.data:
        tid = str(ins.data.get("id") or "").strip()
        return tid or None, None
    return None, ins.error or f"Could not create lookup table for {label}."


def load_lookup_entries(slug: str) -> tuple[list[dict[str, Any]], str]:
    """
    Return active lookup rows for a slug.

    Each entry: ``{"id": "<uuid>", "value": "...", "from_db": True}``.
    Source is ``"database"``, ``"constants"``, or ``"empty"``.
    """
    slug = str(slug or "").strip().lower()
    if not slug:
        return [], "empty"

    try:
        from app.services.repository import fetch_rows
    except ImportError:
        from services.repository import fetch_rows  # type: ignore

    tables, _ = fetch_rows("ips_lookup_tables", limit=200, order_by="sort_order")
    table_id = None
    for t in tables or []:
        if str(t.get("slug") or "").lower() == slug:
            table_id = t.get("id")
            break

    if table_id:
        values_rows, _ = fetch_rows("ips_lookup_values", limit=500, order_by="sort_order")
        entries = [
            {
                "id": str(v.get("id") or "").strip(),
                "value": str(v.get("value") or "").strip(),
                "from_db": True,
            }
            for v in values_rows or []
            if str(v.get("lookup_table_id") or "") == str(table_id)
            and v.get("is_active", True)
            and str(v.get("value") or "").strip()
        ]
        if entries:
            return entries, "database"

    const_vals = _constants_fallback(slug)
    if const_vals:
        return [
            {"id": f"local-{i}", "value": val, "from_db": False}
            for i, val in enumerate(const_vals)
        ], "constants"
    return [], "empty"


def load_lookup_values(slug: str) -> tuple[list[str], bool]:
    """
    Return (values, from_constants_only).

    Tries ``ips_lookup_values`` joined by ``ips_lookup_tables.slug``; falls back to constants.
    """
    entries, source = load_lookup_entries(slug)
    if entries:
        return [str(e.get("value") or "") for e in entries], source == "constants"
    return [], True


def constants_fallback_for_label(label: str) -> list[str]:
    """Hardcoded defaults from ``app.utils.constants`` for admin / offline dev."""
    return _constants_fallback(slug_for_label(label))


def load_lookup_for_label(label: str) -> list[str]:
    slug = slug_for_label(label)
    try:
        values, _ = load_lookup_values(slug)
    except Exception as exc:
        _LOG.debug("load_lookup_for_label %s failed: %s", label, exc)
        values = []
    if values:
        return values
    return constants_fallback_for_label(label)


def load_lookup_entries_for_label(label: str) -> tuple[list[dict[str, Any]], str]:
    return load_lookup_entries(slug_for_label(label))


def all_lookup_slugs() -> list[str]:
    return list(_LOOKUP_SLUGS.keys())


def _new_local_id() -> str:
    return f"local-{uuid.uuid4().hex[:8]}"


def sync_lookup_for_label(label: str, entries: list[dict[str, Any]]) -> tuple[bool, str]:
    """
    Sync lookup values to Supabase: insert, rename, reorder, and deactivate removed rows.

    ``entries`` items use ``{"id": "...", "value": "..."}``; local ids start with ``local-``.
    """
    slug = slug_for_label(label)
    clean: list[dict[str, str]] = []
    seen_vals: set[str] = set()
    for ent in entries or []:
        val = str(ent.get("value") or "").strip()
        if not val or val.casefold() in seen_vals:
            continue
        seen_vals.add(val.casefold())
        eid = str(ent.get("id") or "").strip()
        if eid.startswith("local-"):
            eid = ""
        clean.append({"id": eid, "value": val})
    if not clean:
        return False, "Add at least one value."

    try:
        from app.services.repository import ServiceResult, fetch_rows, insert_row, update_row
    except ImportError:
        from services.repository import ServiceResult, fetch_rows, insert_row, update_row  # type: ignore

    table_id, err = _resolve_table_id(slug, label)
    if not table_id:
        return False, f"{err or 'Lookup tables not available.'} Values kept in this session only."

    values_rows, _ = fetch_rows("ips_lookup_values", limit=500, order_by="sort_order")
    db_rows = [
        v
        for v in values_rows or []
        if str(v.get("lookup_table_id") or "") == str(table_id)
    ]
    db_by_id = {str(v.get("id") or "").strip(): v for v in db_rows if str(v.get("id") or "").strip()}
    db_by_value = {
        str(v.get("value") or "").strip().casefold(): v
        for v in db_rows
        if str(v.get("value") or "").strip()
    }

    desired_ids: set[str] = set()
    changes = 0
    last_err: str | None = None

    for i, ent in enumerate(clean):
        val = ent["value"]
        eid = ent["id"]
        row = db_by_id.get(eid) if eid else None
        if not row:
            row = db_by_value.get(val.casefold())
            if row:
                eid = str(row.get("id") or "").strip()

        if eid and eid in db_by_id:
            desired_ids.add(eid)
            existing = db_by_id[eid]
            patch: dict[str, Any] = {"sort_order": i}
            if str(existing.get("value") or "") != val:
                patch["value"] = val
            if not existing.get("is_active", True):
                patch["is_active"] = True
            if patch.keys() - {"sort_order"} or existing.get("sort_order") != i:
                res = update_row("ips_lookup_values", patch, {"id": eid})
                if res.ok:
                    changes += 1
                else:
                    last_err = res.error
            continue

        res = insert_row(
            "ips_lookup_values",
            {"lookup_table_id": table_id, "value": val, "sort_order": i, "is_active": True},
        )
        if res.ok and res.data:
            changes += 1
            new_id = str(res.data.get("id") or "").strip()
            if new_id:
                desired_ids.add(new_id)
        else:
            last_err = res.error

    for rid, row in db_by_id.items():
        if rid in desired_ids:
            continue
        if not row.get("is_active", True):
            continue
        res = update_row("ips_lookup_values", {"is_active": False}, {"id": rid})
        if res.ok:
            changes += 1
        else:
            last_err = res.error

    clear_lookup_cache()
    if changes:
        return True, f"Saved {changes} change(s) to {label}."
    if last_err:
        return False, last_err
    return True, f"{label} is up to date ({len(clean)} values)."


def save_lookup_for_label(label: str, values: list[str]) -> tuple[bool, str]:
    """Backward-compatible save from a plain value list (preserves known DB ids by value)."""
    existing, _ = load_lookup_entries_for_label(label)
    by_val = {str(e.get("value") or "").strip().casefold(): e for e in existing}
    entries: list[dict[str, Any]] = []
    for raw in values:
        val = str(raw or "").strip()
        if not val:
            continue
        hit = by_val.get(val.casefold())
        entries.append(
            {
                "id": str(hit.get("id") or _new_local_id()) if hit else _new_local_id(),
                "value": val,
            }
        )
    return sync_lookup_for_label(label, entries)
