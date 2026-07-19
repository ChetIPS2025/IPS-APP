"""Lightweight searchable reference options for Pricing Guide forms."""

from __future__ import annotations

from app.db import fetch_table, fetch_table_admin
from app.pages._core._data import assets_catalog_data_version, inventory_catalog_data_version
from app.pages._core.page_data_cache import page_data_cache_get


def _match_search(label: str, search: str) -> bool:
    query = str(search or "").strip().lower()
    if not query:
        return True
    return query in str(label or "").lower()


def search_inventory_link_options(
    *,
    search: str = "",
    limit: int = 100,
) -> list[dict[str, str]]:
    """Active inventory rows for link pickers — no transactions or photos."""
    from app.perf_debug import perf_span

    version = inventory_catalog_data_version()
    cache_key = f"pg_inv_link_opts:{version}:{search}:{limit}"

    def _build() -> list[dict[str, str]]:
        with perf_span("pricing_guide.reference.inventory"):
            from app.pages._core._data import load_inventory

            rows = load_inventory()
            out: list[dict[str, str]] = []
            for row in rows:
                if row.get("is_deleted") or row.get("is_active") is False:
                    continue
                iid = str(row.get("id") or "").strip()
                name = str(row.get("item_name") or row.get("name") or row.get("description") or "").strip()
                sku = str(row.get("sku") or "").strip()
                if not iid or not name:
                    continue
                label = f"{sku} — {name}" if sku else name
                if not _match_search(label, search):
                    continue
                out.append(
                    {
                        "id": iid,
                        "sku": sku,
                        "name": name,
                        "display_label": label,
                    }
                )
                if len(out) >= limit:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def search_asset_link_options(
    *,
    search: str = "",
    limit: int = 100,
) -> list[dict[str, str]]:
    """Active asset rows for link pickers — no full detail payloads."""
    from app.perf_debug import perf_span

    version = assets_catalog_data_version()
    cache_key = f"pg_asset_link_opts:{version}:{search}:{limit}"

    def _build() -> list[dict[str, str]]:
        with perf_span("pricing_guide.reference.assets"):
            from app.pages._core._data import load_assets

            rows = load_assets()
            out: list[dict[str, str]] = []
            for row in rows:
                if row.get("is_deleted") or row.get("is_active") is False:
                    continue
                aid = str(row.get("id") or "").strip()
                number = str(row.get("asset_number") or row.get("asset_id") or "").strip()
                name = str(row.get("asset_name") or row.get("name") or "").strip()
                if not aid or not name:
                    continue
                label = f"{number} — {name}" if number else name
                if not _match_search(label, search):
                    continue
                out.append(
                    {
                        "id": aid,
                        "asset_number": number,
                        "name": name,
                        "display_label": label,
                    }
                )
                if len(out) >= limit:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def search_vendor_options(
    *,
    search: str = "",
    limit: int = 100,
) -> list[dict[str, str]]:
    """Active vendor rows for subcontractor pickers."""
    from app.perf_debug import perf_span

    cache_key = f"pg_vendor_opts:{search}:{limit}"

    def _build() -> list[dict[str, str]]:
        with perf_span("pricing_guide.reference.vendors"):
            try:
                rows = list(fetch_table_admin("vendors", limit=max(limit * 5, 500), order_by="vendor_name") or [])
            except Exception:
                try:
                    rows = list(fetch_table("vendors", limit=max(limit * 5, 500), order_by="vendor_name") or [])
                except Exception:
                    rows = []
            out: list[dict[str, str]] = []
            for row in rows:
                if not isinstance(row, dict) or row.get("is_active") is False:
                    continue
                vid = str(row.get("id") or "").strip()
                name = str(row.get("vendor_name") or row.get("name") or "").strip()
                if not vid or not name:
                    continue
                if not _match_search(name, search):
                    continue
                out.append({"id": vid, "name": name, "display_label": name})
                if len(out) >= limit:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def ensure_option_for_id(
    options: list[dict[str, str]],
    *,
    record_id: str,
    display_label: str,
) -> list[dict[str, str]]:
    """Keep the currently linked record visible even when off-page."""
    rid = str(record_id or "").strip()
    if not rid:
        return options
    if any(str(o.get("id") or "") == rid for o in options):
        return options
    label = str(display_label or rid).strip() or rid
    return [{"id": rid, "display_label": label, "name": label}] + list(options)
