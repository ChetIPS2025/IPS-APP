"""Paginated Jobs directory — list projection, filters, and summary aggregates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import streamlit as st

from app.components.table_filters import apply_column_filters
from app.pages._core._data import jobs_catalog_data_version, load_jobs
from app.pages._core.page_data_cache import page_data_cache_get
from app.services.job_financial_ui import job_list_financials_from_row
from app.services.jobs_service import normalize_job_status

_JOBS_FILTER_OPTIONS_CACHE_PREFIX = "jobs_filter_options:"
_JOBS_TABLE_KEY = "jobs_list"

_JOBS_DEFAULT_VIEW = "Active Jobs"
_CLOSED_SUBJOB_STATUSES = frozenset(
    {"complete", "completed", "closed", "cancelled", "canceled", "duplicate"}
)


@dataclass(frozen=True)
class JobsPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    filter_options: dict[str, list[str]]
    summary: dict[str, Any]
    is_live: bool
    warning: str | None = None


def invalidate_jobs_directory_cache() -> None:
    """Centralized Jobs directory cache invalidation."""
    from app.pages._core._data import (
        _bump_jobs_catalog_data_version,
        clear_catalog_session_key,
        clear_jobs_list_cost_cache,
        clear_jobs_list_cache,
    )

    _bump_jobs_catalog_data_version()
    clear_jobs_list_cache()
    clear_catalog_session_key("jobs")
    clear_jobs_list_cost_cache()
    st.session_state.pop("_ips_jobs_directory_filter_options", None)
    from app.services.job_detail_service import invalidate_job_detail_cache

    invalidate_job_detail_cache()


def clear_jobs_list_cache() -> None:
    """Compatibility alias — prefer invalidate_jobs_directory_cache()."""
    invalidate_jobs_directory_cache()


def _job_customer(row: dict[str, Any]) -> str:
    for key in ("customer_name", "customer"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _job_supervisor(row: dict[str, Any]) -> str:
    return str(row.get("supervisor") or row.get("supervisor_name") or "—").strip() or "—"


def _job_number(row: dict[str, Any]) -> str:
    for key in ("job_number", "number"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _job_project(row: dict[str, Any]) -> str:
    for key in ("job_name", "project_name", "project_description", "description"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


_JOB_COLUMN_FILTER_SPECS: list[tuple[str, Callable[[dict[str, Any]], str]]] = [
    ("customer", _job_customer),
    ("supervisor", _job_supervisor),
    ("status", lambda r: normalize_job_status(r.get("status"))),
]


def _apply_jobs_view_filter(rows: list[dict[str, Any]], view: str) -> list[dict[str, Any]]:
    view_norm = str(view or _JOBS_DEFAULT_VIEW).strip()
    if view_norm == "All Jobs":
        return rows
    if view_norm == "Deleted/Archived Jobs":
        return [
            r
            for r in rows
            if bool(r.get("is_deleted"))
            or normalize_job_status(r.get("status")) in {"Deleted", "Archived"}
        ]
    alive = [
        r
        for r in rows
        if not bool(r.get("is_deleted"))
        and normalize_job_status(r.get("status")) not in {"Deleted", "Archived"}
    ]
    if view_norm == "Completed Jobs":
        return [r for r in alive if normalize_job_status(r.get("status")) == "Completed"]
    if view_norm == "Cancelled Jobs":
        return [r for r in alive if normalize_job_status(r.get("status")) == "Cancelled"]
    return [
        r
        for r in alive
        if normalize_job_status(r.get("status")) not in {"Completed", "Cancelled"}
    ]


def _apply_jobs_search_filter(rows: list[dict[str, Any]], q: str) -> list[dict[str, Any]]:
    query = str(q or "").strip()
    if not query:
        return rows
    ql = query.lower()
    return [
        r
        for r in rows
        if ql in _job_number(r).lower()
        or ql in _job_project(r).lower()
        or ql in _job_customer(r).lower()
        or ql in _job_supervisor(r).lower()
    ]


def _filter_jobs_rows(
    rows: list[dict[str, Any]],
    *,
    view: str,
    search: str = "",
    customers: list[str] | None = None,
    supervisors: list[str] | None = None,
    statuses: list[str] | None = None,
) -> list[dict[str, Any]]:
    out = _apply_jobs_view_filter(rows, view)
    out = _apply_jobs_search_filter(out, search)
    if customers:
        wanted = {str(c).strip() for c in customers if str(c).strip()}
        if wanted:
            out = [r for r in out if _job_customer(r) in wanted]
    if supervisors:
        wanted = {str(s).strip() for s in supervisors if str(s).strip()}
        if wanted:
            out = [r for r in out if _job_supervisor(r) in wanted]
    if statuses:
        wanted = {normalize_job_status(s) for s in statuses if str(s).strip()}
        if wanted:
            out = [r for r in out if normalize_job_status(r.get("status")) in wanted]
    return apply_column_filters(out, _JOBS_TABLE_KEY, _JOB_COLUMN_FILTER_SPECS)


def load_jobs_filter_options() -> dict[str, list[str]]:
    """Distinct filter values cached by jobs catalog data version."""
    version = jobs_catalog_data_version()
    cache_key = f"{_JOBS_FILTER_OPTIONS_CACHE_PREFIX}{version}"

    def _build() -> dict[str, list[str]]:
        rows = load_jobs()
        customers: set[str] = set()
        supervisors: set[str] = set()
        statuses: set[str] = set()
        for row in rows:
            cust = _job_customer(row)
            if cust and cust != "—":
                customers.add(cust)
            sup = _job_supervisor(row)
            if sup and sup != "—":
                supervisors.add(sup)
            statuses.add(normalize_job_status(row.get("status")))
        return {
            "customer": sorted(customers),
            "supervisor": sorted(supervisors),
            "status": sorted(statuses),
        }

    return page_data_cache_get(cache_key, _build)


def load_jobs_summary(
    *,
    view: str,
    search: str = "",
    customers: list[str] | None = None,
    supervisors: list[str] | None = None,
    statuses: list[str] | None = None,
    subjob_counts: dict[str, int] | None = None,
    filtered_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate summary cards for all jobs matching current filters."""
    rows = filtered_rows
    if rows is None:
        rows = _filter_jobs_rows(
            load_jobs(),
            view=view,
            search=search,
            customers=customers,
            supervisors=supervisors,
            statuses=statuses,
        )
    counts = subjob_counts if subjob_counts is not None else _load_subjob_counts_safe()

    summary: dict[str, Any] = {
        "total": len(rows),
        "active": 0,
        "on_hold": 0,
        "completed": 0,
        "cancelled": 0,
        "open_subjobs": 0,
        "total_contract": 0.0,
        "total_actual": 0.0,
        "total_profit": 0.0,
        "avg_profit_pct": 0.0,
        "has_any_contract": False,
        "has_any_actual": False,
    }
    for job in rows:
        status = normalize_job_status(job.get("status"))
        if status == "Active":
            summary["active"] += 1
        elif status == "On Hold":
            summary["on_hold"] += 1
        elif status == "Completed":
            summary["completed"] += 1
        elif status == "Cancelled":
            summary["cancelled"] += 1
        jid = str(job.get("id") or "").strip()
        if jid:
            summary["open_subjobs"] += int(counts.get(jid, 0))
        fin = job_list_financials_from_row(job)
        summary["total_contract"] = float(summary["total_contract"]) + float(fin["contract_value"])
        summary["total_actual"] = float(summary["total_actual"]) + float(fin["actual_cost"])
        summary["total_profit"] = float(summary["total_profit"]) + float(fin["profit"])
        if fin.get("has_contract"):
            summary["has_any_contract"] = True
        if fin.get("has_actual"):
            summary["has_any_actual"] = True
    total_contract = float(summary["total_contract"])
    total_profit = float(summary["total_profit"])
    if total_contract > 0:
        summary["avg_profit_pct"] = round((total_profit / total_contract) * 100.0, 1)
    return summary


def _load_subjob_counts_safe() -> dict[str, int]:
    from app.services.tasks_service import count_open_subjobs_by_job_id

    try:
        return count_open_subjobs_by_job_id()
    except Exception:
        return {}


def list_jobs_page(
    *,
    view: str,
    search: str = "",
    customers: list[str] | None = None,
    supervisors: list[str] | None = None,
    statuses: list[str] | None = None,
    page: int = 1,
    page_size: int = 25,
    table_key: str = _JOBS_TABLE_KEY,
) -> JobsPage:
    """Return one page of list projection rows plus filter metadata and summary."""
    from app.components.table_pagination import pagination_meta
    from app.perf_debug import perf_span

    with perf_span("jobs.list_query"):
        all_jobs = load_jobs()
        is_live = True
        warning: str | None = None
        filter_options = load_jobs_filter_options()
        filtered = _filter_jobs_rows(
            all_jobs,
            view=view,
            search=search,
            customers=customers,
            supervisors=supervisors,
            statuses=statuses,
        )
        subjob_counts = _load_subjob_counts_safe()
        summary = load_jobs_summary(
            view=view,
            search=search,
            customers=customers,
            supervisors=supervisors,
            statuses=statuses,
            subjob_counts=subjob_counts,
            filtered_rows=filtered,
        )
        page_num, size, _total_pages = pagination_meta(len(filtered), table_key)
        if page > 0 and page_size > 0:
            page_num = max(1, int(page))
            size = max(1, int(page_size))
        start = (page_num - 1) * size
        page_rows = filtered[start : start + size]
        return JobsPage(
            rows=page_rows,
            total_count=len(filtered),
            page=page_num,
            page_size=size,
            filter_options=filter_options,
            summary=summary,
            is_live=is_live,
            warning=warning,
        )


def list_page_subjob_counts(job_ids: list[str]) -> dict[str, int]:
    """Open subjob counts for current-page job IDs only."""
    from app.services.tasks_service import count_open_subjobs_by_job_ids

    return count_open_subjobs_by_job_ids(job_ids)


def build_page_list_financials(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Stored-column financial projection for current-page rows only."""
    cache: dict[str, dict[str, Any]] = {}
    for job in rows:
        jid = str(job.get("id") or "").strip()
        if not jid or jid in cache:
            continue
        cache[jid] = job_list_financials_from_row(job)
    return cache
