"""Customer contact list and detail services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.customers_cache import customers_catalog_data_version, detail_cache_version
from app.services.customers_service import get_customer_contacts, normalize_customer_contact


@dataclass(frozen=True)
class CustomerContactsPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int


def _contact_sort_key(row: dict[str, Any]) -> tuple:
    return (
        0 if row.get("is_primary") else 1,
        str(row.get("last_name") or row.get("name") or "").lower(),
        str(row.get("id") or ""),
    )


def _attach_location_labels(contacts: list[dict[str, Any]], customer_id: str) -> list[dict[str, Any]]:
    from app.services.customers_service import get_customer_locations

    locs = {str(l.get("id") or ""): l for l in get_customer_locations(customer_id)}
    out: list[dict[str, Any]] = []
    for contact in contacts:
        row = dict(contact)
        lid = str(row.get("location_id") or row.get("customer_location_id") or "").strip()
        loc = locs.get(lid, {})
        row["location_name"] = str(loc.get("location_name") or loc.get("site_name") or "—").strip() or "—"
        out.append(row)
    return out


def list_customer_contacts(
    customer_id: str,
    *,
    location_id: str = "",
    page: int = 1,
    page_size: int = 25,
) -> CustomerContactsPage:
    from app.perf_debug import perf_span

    cid = str(customer_id or "").strip()
    lid_filter = str(location_id or "").strip()
    version = detail_cache_version(cid)
    cache_key = f"cust_contact:list:{cid}:loc{lid_filter}:v{version}:p{page}:s{page_size}"

    def _build() -> CustomerContactsPage:
        with perf_span("customers.detail.contacts"):
            rows = get_customer_contacts(cid, location_id=lid_filter or None)
            rows = sorted(rows, key=_contact_sort_key)
            enriched = _attach_location_labels(rows, cid)
            total = len(enriched)
            pg = max(1, int(page or 1))
            size = max(1, min(200, int(page_size or 25)))
            start = (pg - 1) * size
            return CustomerContactsPage(
                rows=enriched[start : start + size],
                total_count=total,
                page=pg,
                page_size=size,
            )

    return page_data_cache_get(cache_key, _build)


def get_customer_contact_detail(contact_id: str) -> dict[str, Any] | None:
    from app.perf_debug import perf_span

    ct_id = str(contact_id or "").strip()
    if not ct_id:
        return None
    version = customers_catalog_data_version()
    cache_key = f"cust_contact:detail:{ct_id}:v{version}"

    def _build() -> dict[str, Any] | None:
        with perf_span("customers.contact_lookup"):
            from app.services.customers_service import get_customer_contact

            row = get_customer_contact(ct_id)
            if not row:
                return None
            detail = normalize_customer_contact(dict(row))
            cid = str(detail.get("customer_id") or "").strip()
            lid = str(detail.get("location_id") or detail.get("customer_location_id") or "").strip()
            if cid:
                from app.services.customer_detail_service import get_customer_detail

                cust = get_customer_detail(cid)
                if cust:
                    detail["customer_label"] = str(
                        cust.get("customer_name") or cust.get("company_name") or ""
                    )
            if lid:
                from app.services.customer_locations_service import get_customer_location_detail

                loc = get_customer_location_detail(lid)
                if loc:
                    detail["location_label"] = str(
                        loc.get("location_name") or loc.get("site_name") or ""
                    )
            return detail

    return page_data_cache_get(cache_key, _build)
