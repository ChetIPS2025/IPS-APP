"""Paginated Estimates directory — list projection, filters, summary, and export."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

import streamlit as st

from app.components.estimates_list_table import filter_waiting_approval_rows
from app.components.table_filters import apply_column_filters, get_column_filter_values
from app.pages._core._data import estimates_catalog_data_version
from app.pages._core.page_data_cache import page_data_cache_get
from app.services.estimates_service import (
    estimate_visible_in_active_view,
    estimate_visible_in_approved_view,
    estimate_visible_in_archived_view,
    estimate_visible_in_draft_view,
    estimate_visible_in_rejected_view,
    estimate_visible_in_sent_view,
)

_ESTIMATES_FILTER_OPTIONS_CACHE_PREFIX = "estimates_filter_options:"
_ESTIMATES_TABLE_KEY = "estimates_list"
_ESTIMATES_DEFAULT_VIEW = "Waiting Approval"

_LIST_PROJECTION_KEYS: tuple[str, ...] = (
    "id",
    "estimate_number",
    "number",
    "quote_number",
    "project_name",
    "description",
    "customer",
    "customer_name",
    "created_by",
    "job_id",
    "job_number",
    "status",
    "estimate_date",
    "expiration_date",
    "total_cost",
    "customer_price",
    "total",
    "grand_total",
    "proposal_total",
    "final_bid",
    "gross_profit",
    "gross_margin_percent",
    "archived_from_estimates",
    "is_deleted",
    "revision_number",
    "revision_in_progress",
)


@dataclass(frozen=True)
class EstimatesPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    filter_options: dict[str, list[str]]
    summary: dict[str, Any]
    is_live: bool
    warning: str | None = None


def _estimate_number(row: dict[str, Any]) -> str:
    return str(row.get("estimate_number") or row.get("number") or row.get("quote_number") or "").strip() or "—"


def _estimate_project(row: dict[str, Any]) -> str:
    from app.services.phase2_modules_service import estimate_project_title

    return estimate_project_title(row)


def _estimate_customer(row: dict[str, Any]) -> str:
    for key in ("customer_name", "customer"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _estimate_created_by(row: dict[str, Any]) -> str:
    for key in ("created_by_name", "created_by", "estimator"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _normalize_estimate_status(raw: object) -> str:
    s = str(raw or "").strip().lower().replace("_", " ")
    mapping = {
        "": "Draft",
        "draft": "Draft",
        "pending": "Pending",
        "sent": "Sent",
        "approved": "Approved",
        "awarded": "Awarded",
        "rejected": "Rejected",
        "expired": "Expired",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
    }
    if s in mapping:
        return mapping[s]
    label = str(raw or "").strip()
    return label if label else "Draft"


def _as_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def stored_customer_price_amount(row: dict[str, Any]) -> float:
    """Persisted rollup columns only — no live Cost Builder reads."""
    for key in ("customer_price", "total", "grand_total", "proposal_total", "final_bid"):
        val = row.get(key)
        if val in (None, ""):
            continue
        try:
            amount = float(val)
        except (TypeError, ValueError):
            continue
        if amount != 0 or key in ("customer_price", "proposal_total", "final_bid"):
            return amount
    return 0.0


_ESTIMATE_COLUMN_FILTER_SPECS: list[tuple[str, Callable[[dict[str, Any]], str]]] = [
    ("customer", _estimate_customer),
    ("status", lambda r: _normalize_estimate_status(r.get("status"))),
]


def _catalog_cache_key() -> str:
    return f"estimates_catalog:{estimates_catalog_data_version()}"


def _load_catalog_rows() -> tuple[list[dict[str, Any]], bool]:
    from app.pages._core._data import load_estimates

    def _fetch() -> tuple[list[dict[str, Any]], bool]:
        rows = load_estimates()
        return rows, bool(rows)

    cached = page_data_cache_get(_catalog_cache_key(), _fetch)
    if isinstance(cached, tuple) and len(cached) == 2:
        return list(cached[0]), bool(cached[1])
    rows = load_estimates()
    return rows, bool(rows)


def _apply_estimate_view_filter(rows: list[dict[str, Any]], view_filter: str) -> list[dict[str, Any]]:
    vf = str(view_filter or _ESTIMATES_DEFAULT_VIEW).strip()
    if vf == "Waiting Approval":
        return filter_waiting_approval_rows(rows)
    if vf in {"Approved / Converted", "Approved Estimates"}:
        return [r for r in rows if estimate_visible_in_approved_view(r)]
    if vf in {"Rejected", "Rejected / Lost Estimates"}:
        return [r for r in rows if estimate_visible_in_rejected_view(r)]
    if vf == "All Estimates":
        return rows
    if vf == "Draft Estimates":
        return [r for r in rows if estimate_visible_in_draft_view(r)]
    if vf == "Sent Estimates":
        return [r for r in rows if estimate_visible_in_sent_view(r)]
    if vf == "Archived Estimates":
        return [r for r in rows if estimate_visible_in_archived_view(r)]
    return [r for r in rows if estimate_visible_in_active_view(r)]


def _filter_estimates_rows(
    rows: list[dict[str, Any]],
    *,
    view: str,
    search: str = "",
    customers: list[str] | None = None,
    statuses: list[str] | None = None,
    date_start: date | None = None,
    date_end: date | None = None,
    table_key: str = _ESTIMATES_TABLE_KEY,
) -> list[dict[str, Any]]:
    out = _apply_estimate_view_filter(rows, view)
    q = str(search or "").strip()
    if q:
        ql = q.lower()
        out = [
            r
            for r in out
            if ql in _estimate_number(r).lower()
            or ql in _estimate_project(r).lower()
            or ql in _estimate_customer(r).lower()
            or ql in _estimate_created_by(r).lower()
            or ql in _normalize_estimate_status(r.get("status")).lower()
        ]
    if date_start and date_end:
        filtered_range: list[dict[str, Any]] = []
        for row in out:
            est_date = _as_date(row.get("estimate_date"))
            if est_date is None or (date_start <= est_date <= date_end):
                filtered_range.append(row)
        out = filtered_range
    if customers:
        wanted = {str(c).strip() for c in customers if str(c).strip()}
        if wanted:
            out = [r for r in out if _estimate_customer(r) in wanted]
    if statuses:
        wanted = {_normalize_estimate_status(s) for s in statuses if str(s).strip()}
        if wanted:
            out = [r for r in out if _normalize_estimate_status(r.get("status")) in wanted]
    return apply_column_filters(out, table_key, _ESTIMATE_COLUMN_FILTER_SPECS)


def _list_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in _LIST_PROJECTION_KEYS}


def load_estimates_filter_options() -> dict[str, list[str]]:
    version = estimates_catalog_data_version()
    cache_key = f"{_ESTIMATES_FILTER_OPTIONS_CACHE_PREFIX}{version}"

    def _build() -> dict[str, list[str]]:
        from app.perf_debug import perf_span

        with perf_span("estimates.filter_options"):
            rows, _ = _load_catalog_rows()
            customers: set[str] = set()
            statuses: set[str] = set()
            for row in rows:
                cust = _estimate_customer(row)
                if cust and cust != "—":
                    customers.add(cust)
                statuses.add(_normalize_estimate_status(row.get("status")))
            return {"customer": sorted(customers), "status": sorted(statuses)}

    return page_data_cache_get(cache_key, _build)


def load_estimates_summary(
    *,
    view: str,
    search: str = "",
    customers: list[str] | None = None,
    statuses: list[str] | None = None,
    date_start: date | None = None,
    date_end: date | None = None,
    filtered_rows: list[dict[str, Any]] | None = None,
    table_key: str = _ESTIMATES_TABLE_KEY,
) -> dict[str, Any]:
    from app.perf_debug import perf_span

    with perf_span("estimates.summary"):
        rows = filtered_rows
        if rows is None:
            catalog, _ = _load_catalog_rows()
            rows = _filter_estimates_rows(
                catalog,
                view=view,
                search=search,
                customers=customers,
                statuses=statuses,
                date_start=date_start,
                date_end=date_end,
                table_key=table_key,
            )
        summary: dict[str, Any] = {
            "total": len(rows),
            "active": 0,
            "draft": 0,
            "sent": 0,
            "approved": 0,
            "total_customer_value": 0.0,
            "has_any_value": False,
        }
        for row in rows:
            if estimate_visible_in_active_view(row):
                summary["active"] += 1
            if estimate_visible_in_draft_view(row):
                summary["draft"] += 1
            if estimate_visible_in_sent_view(row):
                summary["sent"] += 1
            if estimate_visible_in_approved_view(row):
                summary["approved"] += 1
            amount = stored_customer_price_amount(row)
            if amount > 0:
                summary["has_any_value"] = True
                summary["total_customer_value"] = float(summary["total_customer_value"]) + amount
        return summary


def list_estimates_page(
    *,
    view: str,
    search: str = "",
    customers: list[str] | None = None,
    statuses: list[str] | None = None,
    date_start: date | None = None,
    date_end: date | None = None,
    page: int = 1,
    page_size: int = 25,
    table_key: str = _ESTIMATES_TABLE_KEY,
) -> EstimatesPage:
    from app.components.table_pagination import pagination_meta
    from app.perf_debug import perf_span

    with perf_span("estimates.list_query"):
        catalog, is_live = _load_catalog_rows()
        if customers is None and table_key:
            customers = get_column_filter_values(table_key, "customer") or None
        if statuses is None and table_key:
            statuses = get_column_filter_values(table_key, "status") or None
        filtered = _filter_estimates_rows(
            catalog,
            view=view,
            search=search,
            customers=customers,
            statuses=statuses,
            date_start=date_start,
            date_end=date_end,
            table_key=table_key,
        )
        summary = load_estimates_summary(
            view=view,
            search=search,
            customers=customers,
            statuses=statuses,
            date_start=date_start,
            date_end=date_end,
            filtered_rows=filtered,
            table_key=table_key,
        )
        filter_options = load_estimates_filter_options()
        page_num, size, _total_pages = pagination_meta(len(filtered), table_key)
        if page > 0 and page_size > 0:
            page_num = max(1, int(page))
            size = max(1, int(page_size))
        start = (page_num - 1) * size
        page_rows = [_list_projection(r) for r in filtered[start : start + size]]
        return EstimatesPage(
            rows=page_rows,
            total_count=len(filtered),
            page=page_num,
            page_size=size,
            filter_options=filter_options,
            summary=summary,
            is_live=is_live,
            warning=None,
        )


def list_estimates_export_rows(
    *,
    view: str,
    search: str = "",
    customers: list[str] | None = None,
    statuses: list[str] | None = None,
    date_start: date | None = None,
    date_end: date | None = None,
    table_key: str = _ESTIMATES_TABLE_KEY,
) -> list[dict[str, Any]]:
    from app.perf_debug import perf_span

    with perf_span("estimates.export"):
        catalog, _ = _load_catalog_rows()
        return _filter_estimates_rows(
            catalog,
            view=view,
            search=search,
            customers=customers,
            statuses=statuses,
            date_start=date_start,
            date_end=date_end,
            table_key=table_key,
        )


def invalidate_estimates_directory_cache() -> None:
    from app.pages._core._data import (
        _bump_estimates_catalog_data_version,
        clear_catalog_session_key,
        clear_dashboard_page_data_cache,
        clear_customers_page_data_cache,
        clear_estimates_list_cache,
    )

    _bump_estimates_catalog_data_version()
    clear_estimates_list_cache()
    clear_catalog_session_key("estimates")
    clear_dashboard_page_data_cache()
    clear_customers_page_data_cache()
    from app.services.estimate_detail_service import invalidate_estimate_detail_cache

    invalidate_estimate_detail_cache()
    st.session_state.pop("_ips_estimates_directory_filter_options", None)


def clear_estimates_list_cache() -> None:
    """Compatibility alias — prefer invalidate_estimates_directory_cache()."""
    invalidate_estimates_directory_cache()
