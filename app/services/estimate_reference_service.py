"""Lightweight searchable reference options for Estimates forms and Cost Builder."""

from __future__ import annotations

from typing import Any

from app.db import fetch_table, fetch_table_admin
from app.pages._core._data import assets_catalog_data_version, inventory_catalog_data_version, jobs_catalog_data_version
from app.pages._core.page_data_cache import page_data_cache_get


def _pricing_guide_version() -> int:
    try:
        from app.pages._core._data import pricing_guide_catalog_data_version

        return pricing_guide_catalog_data_version()
    except ImportError:
        return 0


def _match_search(label: str, search: str) -> bool:
    query = str(search or "").strip().lower()
    if not query:
        return True
    return query in str(label or "").lower()


def search_jobs_for_estimate_link(
    *,
    customer_id: str | None = None,
    customer_name: str = "",
    search: str = "",
    limit: int = 100,
) -> list[dict[str, str]]:
    from app.perf_debug import perf_span

    version = jobs_catalog_data_version()
    cache_key = f"est_job_link:{version}:{customer_id}:{customer_name}:{search}:{limit}"

    def _build() -> list[dict[str, str]]:
        with perf_span("estimates.reference.jobs"):
            from app.pages._core._data import load_jobs

            cid = str(customer_id or "").strip()
            cname = str(customer_name or "").strip()
            out: list[dict[str, str]] = []
            for job in load_jobs():
                if job.get("is_deleted"):
                    continue
                status = str(job.get("status") or "").strip().lower()
                if status in {"deleted", "archived", "cancelled", "canceled"}:
                    continue
                if cid and str(job.get("customer_id") or "") != cid:
                    jcust = str(job.get("customer_name") or job.get("customer") or "")
                    if jcust != cname:
                        continue
                jid = str(job.get("id") or "").strip()
                number = str(job.get("job_number") or job.get("number") or jid).strip()
                name = str(job.get("project_name") or job.get("job_name") or "").strip()
                label = f"{number} — {name}" if name else number
                if not jid or not label:
                    continue
                if not _match_search(label, search):
                    continue
                out.append(
                    {
                        "id": jid,
                        "job_number": number,
                        "job_name": name,
                        "customer_id": str(job.get("customer_id") or ""),
                        "customer_name": str(job.get("customer_name") or job.get("customer") or ""),
                        "display_label": label,
                    }
                )
                if len(out) >= limit:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def search_vendor_estimate_options(
    *,
    search: str = "",
    limit: int = 100,
) -> list[str]:
    from app.perf_debug import perf_span

    cache_key = f"est_vendor_opts:{search}:{limit}"

    def _build() -> list[str]:
        with perf_span("estimates.reference.vendors"):
            try:
                rows = list(fetch_table_admin("vendors", limit=max(limit * 5, 500), order_by="vendor_name") or [])
            except Exception:
                try:
                    rows = list(fetch_table("vendors", limit=max(limit * 5, 500), order_by="vendor_name") or [])
                except Exception:
                    rows = []
            out: list[str] = []
            for row in rows:
                if not isinstance(row, dict) or row.get("is_active") is False:
                    continue
                name = str(row.get("vendor_name") or row.get("name") or "").strip()
                if not name or not _match_search(name, search):
                    continue
                out.append(name)
                if len(out) >= limit:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def search_pricing_guide_estimate_options(
    *,
    search: str = "",
    item_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    from app.perf_debug import perf_span

    version = _pricing_guide_version()
    cache_key = f"est_pg_opts:{version}:{search}:{item_type}:{limit}"

    def _build() -> list[dict[str, Any]]:
        with perf_span("estimates.reference.pricing"):
            from app.services.pricing_guide_service import cached_pricing_guide_rows

            out: list[dict[str, Any]] = []
            for row in cached_pricing_guide_rows(include_inactive=False):
                if row.get("is_active") is False:
                    continue
                itype = str(row.get("item_type") or "").strip()
                if item_type and itype != item_type:
                    continue
                label = str(row.get("description") or row.get("item") or "").strip()
                if not label or not _match_search(label, search):
                    continue
                out.append(
                    {
                        "id": str(row.get("id") or ""),
                        "description": label,
                        "item_type": itype,
                        "display_label": label,
                    }
                )
                if len(out) >= limit:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def search_inventory_estimate_options(
    *,
    search: str = "",
    limit: int = 100,
) -> list[dict[str, str]]:
    from app.perf_debug import perf_span

    version = inventory_catalog_data_version()
    cache_key = f"est_inv_opts:{version}:{search}:{limit}"

    def _build() -> list[dict[str, str]]:
        with perf_span("estimates.reference.inventory"):
            from app.pages._core._data import load_inventory

            out: list[dict[str, str]] = []
            for row in load_inventory():
                if row.get("is_deleted") or row.get("is_active") is False:
                    continue
                iid = str(row.get("id") or "").strip()
                name = str(row.get("item_name") or row.get("name") or "").strip()
                sku = str(row.get("sku") or "").strip()
                if not iid or not name:
                    continue
                label = f"{sku} — {name}" if sku else name
                if not _match_search(label, search):
                    continue
                out.append({"id": iid, "sku": sku, "name": name, "display_label": label})
                if len(out) >= limit:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def search_asset_rental_options(
    *,
    search: str = "",
    limit: int = 100,
) -> list[dict[str, str]]:
    from app.perf_debug import perf_span

    version = assets_catalog_data_version()
    cache_key = f"est_asset_opts:{version}:{search}:{limit}"

    def _build() -> list[dict[str, str]]:
        with perf_span("estimates.reference.assets"):
            from app.pages._core._data import load_assets

            out: list[dict[str, str]] = []
            for row in load_assets():
                if row.get("is_deleted") or row.get("is_active") is False:
                    continue
                aid = str(row.get("id") or "").strip()
                name = str(row.get("asset_name") or row.get("name") or "").strip()
                number = str(row.get("asset_number") or row.get("asset_id") or "").strip()
                if not aid or not name:
                    continue
                label = f"{number} — {name}" if number else name
                if not _match_search(label, search):
                    continue
                out.append({"id": aid, "asset_number": number, "name": name, "display_label": label})
                if len(out) >= limit:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def ensure_option_label(options: list[dict[str, str]], *, record_id: str, display_label: str) -> list[dict[str, str]]:
    rid = str(record_id or "").strip()
    if not rid:
        return options
    if any(str(o.get("id") or "") == rid for o in options):
        return options
    label = str(display_label or rid).strip() or rid
    return [{"id": rid, "display_label": label, "name": label}] + list(options)
