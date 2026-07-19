"""Focused Jobs/Estimates queries scoped to customer, location, or contact."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.customers_cache import customers_catalog_data_version
from app.services.status_maps import (
    is_estimate_open_for_customer_count,
    is_job_open_for_customer_count,
)

_JOB_COUNT_COLUMNS = "id,customer_id,customer,status,is_deleted"
_EST_COUNT_COLUMNS = "id,customer_id,customer,status,is_active,is_deleted"


def _customer_name_key(row: dict[str, Any]) -> str:
    return str(row.get("customer_name") or row.get("company_name") or "").strip().lower()


def _job_matches_customer(
    job: dict[str, Any],
    *,
    customer_id: str,
    customer_name: str,
) -> bool:
    cid = str(customer_id or "").strip()
    if cid and str(job.get("customer_id") or "").strip() == cid:
        return True
    name = str(customer_name or "").strip().lower()
    if name and str(job.get("customer") or "").strip().lower() == name:
        return True
    return False


def _estimate_matches_customer(
    est: dict[str, Any],
    *,
    customer_id: str,
    customer_name: str,
) -> bool:
    cid = str(customer_id or "").strip()
    if cid and str(est.get("customer_id") or "").strip() == cid:
        return True
    name = str(customer_name or "").strip().lower()
    if name and str(est.get("customer") or "").strip().lower() == name:
        return True
    return False


def _fetch_job_count_rows() -> list[dict[str, Any]]:
    from app.services.repository import fetch_rows

    rows, err = fetch_rows("jobs", columns=_JOB_COUNT_COLUMNS, limit=5000)
    if err or not rows:
        try:
            from app.pages._core._data import _DEMO_JOBS
        except ImportError:
            _DEMO_JOBS = []
        return [
            {
                "id": j.get("id"),
                "customer_id": j.get("customer_id"),
                "customer": j.get("customer"),
                "status": j.get("status"),
                "is_deleted": j.get("is_deleted"),
            }
            for j in _DEMO_JOBS
        ]
    return rows


def _fetch_estimate_count_rows() -> list[dict[str, Any]]:
    from app.services.repository import fetch_rows

    rows, err = fetch_rows("estimates", columns=_EST_COUNT_COLUMNS, limit=5000)
    if err or not rows:
        try:
            from app.pages._core._data import _DEMO_ESTIMATES
        except ImportError:
            _DEMO_ESTIMATES = []
        return [
            {
                "id": e.get("id"),
                "customer_id": e.get("customer_id"),
                "customer": e.get("customer"),
                "status": e.get("status"),
                "is_active": e.get("is_active"),
                "is_deleted": e.get("is_deleted"),
            }
            for e in _DEMO_ESTIMATES
        ]
    return rows


def count_open_jobs_by_customer_ids(
    customer_refs: list[tuple[str, str]],
) -> dict[str, int]:
    """Return open job counts keyed by customer id for the given page refs (id, name)."""
    from app.perf_debug import perf_span

    ids = sorted({str(cid).strip() for cid, _ in customer_refs if str(cid).strip()})
    if not ids:
        return {}
    version = customers_catalog_data_version()
    cache_key = f"cust_rel:open_jobs:v{version}:{','.join(ids)}"

    def _build() -> dict[str, int]:
        with perf_span("customers.open_job_counts"):
            jobs = page_data_cache_get(
                f"cust_rel:job_proj:v{version}",
                _fetch_job_count_rows,
            )
            names_by_id = {str(cid): str(name or "").strip().lower() for cid, name in customer_refs}
            out: dict[str, int] = {cid: 0 for cid in ids}
            for job in jobs:
                for cid in ids:
                    if _job_matches_customer(
                        job,
                        customer_id=cid,
                        customer_name=names_by_id.get(cid, ""),
                    ) and is_job_open_for_customer_count(job):
                        out[cid] = out.get(cid, 0) + 1
            return out

    return page_data_cache_get(cache_key, _build)


def count_open_estimates_by_customer_ids(
    customer_refs: list[tuple[str, str]],
) -> dict[str, int]:
    """Return open estimate counts keyed by customer id."""
    from app.perf_debug import perf_span

    ids = sorted({str(cid).strip() for cid, _ in customer_refs if str(cid).strip()})
    if not ids:
        return {}
    version = customers_catalog_data_version()
    cache_key = f"cust_rel:open_ests:v{version}:{','.join(ids)}"

    def _build() -> dict[str, int]:
        with perf_span("customers.open_estimate_counts"):
            estimates = page_data_cache_get(
                f"cust_rel:est_proj:v{version}",
                _fetch_estimate_count_rows,
            )
            names_by_id = {str(cid): str(name or "").strip().lower() for cid, name in customer_refs}
            out: dict[str, int] = {cid: 0 for cid in ids}
            for est in estimates:
                for cid in ids:
                    if _estimate_matches_customer(
                        est,
                        customer_id=cid,
                        customer_name=names_by_id.get(cid, ""),
                    ) and is_estimate_open_for_customer_count(est):
                        out[cid] = out.get(cid, 0) + 1
            return out

    return page_data_cache_get(cache_key, _build)


@dataclass(frozen=True)
class CustomerRelationshipPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int


def _paginate(rows: list[dict[str, Any]], page: int, page_size: int) -> CustomerRelationshipPage:
    total = len(rows)
    pg = max(1, int(page or 1))
    size = max(1, min(200, int(page_size or 25)))
    start = (pg - 1) * size
    return CustomerRelationshipPage(
        rows=rows[start : start + size],
        total_count=total,
        page=pg,
        page_size=size,
    )


def list_jobs_for_customer(
    customer_id: str,
    *,
    customer_name: str = "",
    page: int = 1,
    page_size: int = 25,
) -> CustomerRelationshipPage:
    from app.perf_debug import perf_span

    cid = str(customer_id or "").strip()
    cname = str(customer_name or "").strip().lower()
    version = customers_catalog_data_version()
    cache_key = f"cust_rel:jobs:{cid}:v{version}:p{page}:s{page_size}"

    def _build() -> CustomerRelationshipPage:
        with perf_span("customers.detail.jobs"):
            jobs = page_data_cache_get(f"cust_rel:job_proj:v{version}", _fetch_job_count_rows)
            matched: list[dict[str, Any]] = []
            for job in jobs:
                if _job_matches_customer(job, customer_id=cid, customer_name=cname):
                    matched.append(job)
            matched.sort(
                key=lambda j: (
                    str(j.get("job_number") or j.get("id") or ""),
                ),
                reverse=True,
            )
            return _paginate(matched, page, page_size)

    return page_data_cache_get(cache_key, _build)


def list_estimates_for_customer(
    customer_id: str,
    *,
    customer_name: str = "",
    page: int = 1,
    page_size: int = 25,
) -> CustomerRelationshipPage:
    from app.perf_debug import perf_span

    cid = str(customer_id or "").strip()
    cname = str(customer_name or "").strip().lower()
    version = customers_catalog_data_version()
    cache_key = f"cust_rel:ests:{cid}:v{version}:p{page}:s{page_size}"

    def _build() -> CustomerRelationshipPage:
        with perf_span("customers.detail.estimates"):
            estimates = page_data_cache_get(f"cust_rel:est_proj:v{version}", _fetch_estimate_count_rows)
            matched: list[dict[str, Any]] = []
            for est in estimates:
                if _estimate_matches_customer(est, customer_id=cid, customer_name=cname):
                    matched.append(est)
            matched.sort(
                key=lambda e: str(e.get("estimate_number") or e.get("id") or ""),
                reverse=True,
            )
            return _paginate(matched, page, page_size)

    return page_data_cache_get(cache_key, _build)
