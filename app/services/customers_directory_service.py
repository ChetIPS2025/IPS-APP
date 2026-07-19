"""Paginated Customers directory — list projection, filters, and counts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.components.customers_list_table import normalize_customer_status
from app.pages._core.page_data_cache import page_data_cache_get
from app.services.customer_relationships_service import (
    count_open_estimates_by_customer_ids,
    count_open_jobs_by_customer_ids,
)
from app.services.customers_cache import customers_catalog_data_version

CUSTOMERS_DEFAULT_PAGE_SIZE = 25


def _customer_display_name(row: dict[str, Any]) -> str:
    return str(row.get("customer_name") or row.get("company_name") or "").strip()


def _load_raw_customers() -> tuple[list[dict[str, Any]], bool]:
    from app.services.customers_service import get_customers

    rows = get_customers(enrich=False)
    is_live = not any(str(r.get("id") or "").startswith("demo") for r in rows[:3])
    return rows, is_live


def _bulk_location_summary(customer_ids: list[str]) -> dict[str, dict[str, Any]]:
    from app.services.customers_service import _bulk_locations_by_customer_id

    if not customer_ids:
        return {}
    all_locs = page_data_cache_get(
        f"customers:bulk_locs:v{customers_catalog_data_version()}",
        _bulk_locations_by_customer_id,
    )
    out: dict[str, dict[str, Any]] = {}
    wanted = set(customer_ids)
    for cid in wanted:
        locs = all_locs.get(cid, [])
        primary = next((loc for loc in locs if loc.get("is_primary")), None) or (locs[0] if locs else None)
        out[cid] = {
            "location_count": len(locs),
            "primary_location_name": str((primary or {}).get("location_name") or (primary or {}).get("site_name") or "—"),
            "primary_location_city": str((primary or {}).get("city") or "—"),
            "primary_location_state": str((primary or {}).get("state") or "—"),
        }
    return out


def _bulk_contact_counts(customer_ids: list[str]) -> dict[str, int]:
    from app.services.customers_service import _bulk_contacts_by_customer_id

    if not customer_ids:
        return {}
    all_cons = page_data_cache_get(
        f"customers:bulk_contacts:v{customers_catalog_data_version()}",
        _bulk_contacts_by_customer_id,
    )
    return {cid: len(all_cons.get(cid, [])) for cid in customer_ids}


def to_list_row(
    row: dict[str, Any],
    *,
    location_summary: dict[str, Any] | None = None,
    contact_count: int = 0,
    open_jobs: int = 0,
    open_estimates: int = 0,
) -> dict[str, Any]:
    loc = location_summary or {}
    return {
        "id": str(row.get("id") or ""),
        "customer_name": _customer_display_name(row) or "Unnamed Customer",
        "company_name": str(row.get("company_name") or row.get("customer_name") or ""),
        "customer_number": str(row.get("customer_number") or ""),
        "website": str(row.get("website") or ""),
        "main_phone": str(row.get("main_phone") or ""),
        "main_email": str(row.get("main_email") or ""),
        "billing_email": str(row.get("billing_email") or ""),
        "status": normalize_customer_status(row.get("status")),
        "primary_location_name": loc.get("primary_location_name", "—"),
        "primary_location_city": loc.get("primary_location_city", "—"),
        "primary_location_state": loc.get("primary_location_state", "—"),
        "location_count": int(loc.get("location_count") or 0),
        "contact_count": int(contact_count),
        "open_jobs": int(open_jobs),
        "open_estimates": int(open_estimates),
    }


def _apply_search(rows: list[dict[str, Any]], search: str) -> list[dict[str, Any]]:
    q = str(search or "").strip().lower()
    if not q:
        return rows
    out: list[dict[str, Any]] = []
    for r in rows:
        hay = " ".join(
            str(r.get(k) or "")
            for k in (
                "customer_name",
                "company_name",
                "customer_number",
                "city",
                "state",
                "main_email",
                "main_phone",
            )
        ).lower()
        if q in hay:
            out.append(r)
    return out


def _apply_status_filter(rows: list[dict[str, Any]], statuses: list[str] | None) -> list[dict[str, Any]]:
    stats = [s for s in (statuses or []) if s and s != "All Statuses"]
    if not stats:
        return rows
    return [r for r in rows if normalize_customer_status(r.get("status")) in stats]


def _sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda r: (_customer_display_name(r).lower(), str(r.get("id") or "")),
    )


@dataclass(frozen=True)
class CustomersPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    filter_options: dict[str, list[str]]
    is_live: bool
    warning: str | None = None


def load_customer_filter_options() -> dict[str, list[str]]:
    version = customers_catalog_data_version()

    def _build() -> dict[str, list[str]]:
        from app.perf_debug import perf_span

        with perf_span("customers.filter_options"):
            raw_rows, _ = _load_raw_customers()
            statuses = sorted({normalize_customer_status(r.get("status")) for r in raw_rows if r.get("status") is not None})
            if "Active" not in statuses:
                statuses = ["Active", *statuses]
            return {"status": statuses}

    return page_data_cache_get(f"customers:filter_opts:v{version}", _build)


def list_customers_page(
    *,
    search: str = "",
    statuses: list[str] | None = None,
    page: int = 1,
    page_size: int = CUSTOMERS_DEFAULT_PAGE_SIZE,
) -> CustomersPage:
    from app.perf_debug import perf_span

    version = customers_catalog_data_version()
    cache_key = f"customers:page:v{version}:s{search}:st{statuses}:p{page}:sz{page_size}"

    def _build() -> CustomersPage:
        with perf_span("customers.list_query"):
            raw_rows, is_live = _load_raw_customers()
            filtered = _apply_status_filter(_apply_search(raw_rows, search), statuses)
            sorted_rows = _sort_rows(filtered)
            total = len(sorted_rows)
            pg = max(1, int(page or 1))
            size = max(1, min(200, int(page_size or CUSTOMERS_DEFAULT_PAGE_SIZE)))
            start = (pg - 1) * size
            page_raw = sorted_rows[start : start + size]
            page_ids = [str(r.get("id") or "").strip() for r in page_raw if str(r.get("id") or "").strip()]
            loc_summary = _bulk_location_summary(page_ids)
            contact_counts = _bulk_contact_counts(page_ids)
            refs = [
                (cid, _customer_display_name(r))
                for r in page_raw
                for cid in [str(r.get("id") or "").strip()]
                if cid
            ]
            open_jobs = count_open_jobs_by_customer_ids(refs)
            open_ests = count_open_estimates_by_customer_ids(refs)
            page_rows = [
                to_list_row(
                    r,
                    location_summary=loc_summary.get(str(r.get("id") or "").strip(), {}),
                    contact_count=contact_counts.get(str(r.get("id") or "").strip(), 0),
                    open_jobs=open_jobs.get(str(r.get("id") or "").strip(), 0),
                    open_estimates=open_ests.get(str(r.get("id") or "").strip(), 0),
                )
                for r in page_raw
            ]
            filter_options = load_customer_filter_options()
            warning = None if is_live else "Showing sample customers — connect Supabase for live data."
            return CustomersPage(
                rows=page_rows,
                total_count=total,
                page=pg,
                page_size=size,
                filter_options=filter_options,
                is_live=is_live,
                warning=warning,
            )

    return page_data_cache_get(cache_key, _build)
