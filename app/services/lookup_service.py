"""Lookup values for dropdowns (Supabase ips_lookup_* with constants fallback)."""

from __future__ import annotations

import logging
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
    "asset_categories": "ASSET_CATEGORIES",
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


def load_lookup_values(slug: str) -> tuple[list[str], bool]:
    """
    Return (values, from_constants_only).

    Tries ``ips_lookup_values`` joined by ``ips_lookup_tables.slug``; falls back to constants.
    """
    slug = str(slug or "").strip().lower()
    if not slug:
        return [], True

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
        values_rows, _ = fetch_rows(
            "ips_lookup_values",
            limit=500,
            order_by="sort_order",
        )
        vals = [
            str(v.get("value") or "").strip()
            for v in values_rows or []
            if str(v.get("lookup_table_id") or "") == str(table_id)
            and v.get("is_active", True)
            and str(v.get("value") or "").strip()
        ]
        if vals:
            return vals, False

    return _constants_fallback(slug), True


def load_lookup_for_label(label: str) -> list[str]:
    slug = _LOOKUP_LABEL_TO_SLUG.get(label, label.lower().replace(" ", "_"))
    values, _ = load_lookup_values(slug)
    return values


def all_lookup_slugs() -> list[str]:
    return list(_LOOKUP_SLUGS.keys())
