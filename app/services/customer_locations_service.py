"""Customer location list and detail services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.customers_cache import customers_catalog_data_version, detail_cache_version
from app.services.customers_service import get_customer_locations, normalize_customer_location


@dataclass(frozen=True)
class CustomerLocationsPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int


def _sort_locations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda r: (
            0 if r.get("is_primary") else 1,
            str(r.get("location_name") or r.get("site_name") or "").lower(),
            str(r.get("id") or ""),
        ),
    )


def list_customer_locations(
    customer_id: str,
    *,
    page: int = 1,
    page_size: int = 25,
) -> CustomerLocationsPage:
    from app.perf_debug import perf_span

    cid = str(customer_id or "").strip()
    version = detail_cache_version(cid)
    cache_key = f"cust_loc:list:{cid}:v{version}:p{page}:s{page_size}"

    def _build() -> CustomerLocationsPage:
        with perf_span("customers.detail.locations"):
            rows = _sort_locations(get_customer_locations(cid))
            total = len(rows)
            pg = max(1, int(page or 1))
            size = max(1, min(200, int(page_size or 25)))
            start = (pg - 1) * size
            return CustomerLocationsPage(
                rows=rows[start : start + size],
                total_count=total,
                page=pg,
                page_size=size,
            )

    return page_data_cache_get(cache_key, _build)


def get_customer_location_detail(location_id: str) -> dict[str, Any] | None:
    from app.perf_debug import perf_span

    lid = str(location_id or "").strip()
    if not lid:
        return None
    version = customers_catalog_data_version()
    cache_key = f"cust_loc:detail:{lid}:v{version}"

    def _build() -> dict[str, Any] | None:
        with perf_span("customers.location_lookup"):
            from app.services.customers_service import get_customer_location

            row = get_customer_location(lid)
            if not row:
                return None
            detail = normalize_customer_location(dict(row))
            cid = str(detail.get("customer_id") or "").strip()
            if cid:
                from app.services.customer_detail_service import get_customer_detail

                cust = get_customer_detail(cid)
                if cust:
                    detail["customer_label"] = str(
                        cust.get("customer_name") or cust.get("company_name") or ""
                    )
            contact_count = 0
            try:
                from app.services.repository import fetch_rows

                cons, _ = fetch_rows(
                    "customer_contacts",
                    columns="id,customer_location_id,location_id",
                    limit=5000,
                    alt_tables=("contacts",),
                )
                contact_count = sum(
                    1
                    for c in cons
                    if str(c.get("customer_location_id") or c.get("location_id") or "") == lid
                )
            except Exception:
                pass
            detail["contact_count"] = contact_count
            return detail

    return page_data_cache_get(cache_key, _build)
