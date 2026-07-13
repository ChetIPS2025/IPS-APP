"""Fetch and label ``customer_locations`` rows for estimates and jobs."""

from __future__ import annotations

from typing import Any

from app.db import fetch_by_match, fetch_by_match_admin, fetch_table, fetch_table_admin
def fetch_locations_for_customer(
    customer_id: str,
    *,
    admin_read: bool = False,
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    cid = str(customer_id or "").strip()
    if not cid:
        return []
    try:
        fn = fetch_by_match_admin if admin_read else fetch_by_match
        rows = fn("customer_locations", {"customer_id": cid}, limit=500)
    except Exception:
        return []
    rows = list(rows or [])
    if not include_inactive:
        rows = [r for r in rows if bool(r.get("is_active", True))]
    rows.sort(key=lambda r: (str(r.get("location_name") or "").lower(), str(r.get("id") or "")))
    return rows


def location_option_label(row: dict[str, Any]) -> str:
    name = str(row.get("location_name") or "").strip() or "—"
    city = str(row.get("city") or "").strip()
    st = str(row.get("state") or "").strip()
    tail = ", ".join(x for x in (city, st) if x)
    return f"{name} — {tail}" if tail else name


def location_display_name_city_state(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    name = str(row.get("location_name") or "").strip()
    city = str(row.get("city") or "").strip()
    st = str(row.get("state") or "").strip()
    cs = ", ".join(x for x in (city, st) if x)
    if name and cs:
        return f"{name} ({cs})"
    return name or cs


def fetch_all_locations_indexed(*, admin_read: bool = False) -> dict[str, dict[str, Any]]:
    """``location_id`` -> row (for job grid enrichment)."""
    try:
        fn = fetch_table_admin if admin_read else fetch_table
        rows = fn("customer_locations", limit=10000, order_by="created_at")
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for r in rows or []:
        lid = str(r.get("id") or "").strip()
        if lid:
            out[lid] = r
    return out
