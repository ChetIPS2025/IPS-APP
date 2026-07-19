"""Lightweight Scheduling reference lookups and searchable filter options."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from app.db import get_client, run_user_supabase_operation
from app.pages._core._data import employees_catalog_data_version, jobs_catalog_data_version
from app.pages._core.page_data_cache import page_data_cache_get
from app.perf_debug import perf_span

_JOB_COLUMNS = "id,job_number,job_name,project_name,customer_id,customer,customer_name,status,location,supervisor_id"
_EMPLOYEE_COLUMNS = "id,full_name,employee_name,name,employee_number,status,role,supervisor_id,is_active,is_deleted"
_ASSET_COLUMNS = "id,asset_number,asset_id,asset_name,name,status,category,is_active,is_deleted"
_CUSTOMER_COLUMNS = "id,customer_name,name,company_name,is_active,is_deleted"

_FILTER_OPTIONS_PREFIX = "scheduling_filter_options:"
_FORM_OPTIONS_PREFIX = "scheduling_form_options:"


def _unique_ids(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in ids:
        val = str(raw or "").strip()
        if val and val not in seen:
            seen.add(val)
            out.append(val)
    return out


def _match_search(label: str, search: str) -> bool:
    query = str(search or "").strip().lower()
    if not query:
        return True
    return query in str(label or "").lower()


def _fetch_rows_by_ids(
    table: str,
    *,
    columns: str,
    ids: list[str],
    operation: str,
) -> list[dict[str, Any]]:
    wanted = _unique_ids(ids)
    if not wanted:
        return []

    def _run() -> list[dict[str, Any]]:
        client = get_client()
        rows: list[dict[str, Any]] = []
        chunk_size = 100
        for idx in range(0, len(wanted), chunk_size):
            chunk = wanted[idx : idx + chunk_size]
            resp = (
                client.table(table)
                .select(columns)
                .in_("id", chunk)
                .execute()
            )
            rows.extend(list(resp.data or []))
        return rows

    try:
        return list(run_user_supabase_operation(operation, _run, friendly_on_failure=False) or [])
    except Exception:
        return []


def _demo_filter_rows(
    loader,
    ids: list[str],
    *,
    columns_keep: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    wanted = set(_unique_ids(ids))
    if not wanted:
        return []
    rows = loader()
    out: list[dict[str, Any]] = []
    for row in rows:
        rid = str(row.get("id") or "").strip()
        if rid not in wanted:
            continue
        if columns_keep:
            out.append({k: row.get(k) for k in columns_keep})
        else:
            out.append(dict(row))
    return out


def get_jobs_by_ids(job_ids: list[str]) -> list[dict[str, Any]]:
    with perf_span("scheduling.reference_jobs"):
        rows = _fetch_rows_by_ids("jobs", columns=_JOB_COLUMNS, ids=job_ids, operation="read scheduling jobs by id")
        if rows:
            return rows
        from app.pages._core._data import load_jobs

        return _demo_filter_rows(
            load_jobs,
            job_ids,
            columns_keep=tuple(_JOB_COLUMNS.split(",")),
        )


def get_people_by_ids(employee_ids: list[str]) -> list[dict[str, Any]]:
    with perf_span("scheduling.reference_employees"):
        rows = _fetch_rows_by_ids(
            "employees",
            columns=_EMPLOYEE_COLUMNS,
            ids=employee_ids,
            operation="read scheduling employees by id",
        )
        if rows:
            return rows
        from app.pages._core._data import load_employees

        return _demo_filter_rows(
            load_employees,
            employee_ids,
            columns_keep=tuple(_EMPLOYEE_COLUMNS.split(",")),
        )


def get_assets_by_ids(asset_ids: list[str]) -> list[dict[str, Any]]:
    with perf_span("scheduling.reference_assets"):
        rows = _fetch_rows_by_ids(
            "assets",
            columns=_ASSET_COLUMNS,
            ids=asset_ids,
            operation="read scheduling assets by id",
        )
        if rows:
            return rows
        from app.pages._core._data import load_assets

        return _demo_filter_rows(
            load_assets,
            asset_ids,
            columns_keep=tuple(_ASSET_COLUMNS.split(",")),
        )


def get_customers_by_ids(customer_ids: list[str]) -> list[dict[str, Any]]:
    with perf_span("scheduling.reference_customers"):
        rows = _fetch_rows_by_ids(
            "customers",
            columns=_CUSTOMER_COLUMNS,
            ids=customer_ids,
            operation="read scheduling customers by id",
        )
        if rows:
            return rows
        from app.pages._core._data import load_customers

        return _demo_filter_rows(
            load_customers,
            customer_ids,
            columns_keep=tuple(_CUSTOMER_COLUMNS.split(",")),
        )


def rows_to_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("id") or "").strip(): r for r in rows if str(r.get("id") or "").strip()}


def _job_filter_label(row: dict[str, Any]) -> str:
    num = str(row.get("job_number") or "—")
    name = str(row.get("job_name") or row.get("project_name") or "Job")
    return f"{num} — {name}"


def _employee_filter_label(row: dict[str, Any]) -> str:
    return str(row.get("full_name") or row.get("employee_name") or row.get("name") or row.get("id") or "—")


def list_schedule_job_filter_options(
    *,
    search: str = "",
    limit: int = 100,
) -> list[dict[str, str]]:
    version = jobs_catalog_data_version()
    cache_key = f"{_FILTER_OPTIONS_PREFIX}jobs:{version}:{search}:{limit}"

    def _build() -> list[dict[str, str]]:
        with perf_span("scheduling.filters.job_options"):
            from app.services.phase2_modules_service import list_jobs
            from app.pages._core._data import _DEMO_JOBS

            catalog, _ = list_jobs(demo=list(_DEMO_JOBS))
            out: list[dict[str, str]] = []
            for row in catalog:
                if row.get("is_deleted"):
                    continue
                status = str(row.get("status") or "").strip()
                if status in {"Deleted", "Archived", "Cancelled"}:
                    continue
                jid = str(row.get("id") or "").strip()
                if not jid:
                    continue
                label = _job_filter_label(row)
                if not _match_search(label, search):
                    continue
                out.append({"id": jid, "label": label})
                if len(out) >= limit:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def list_schedule_supervisor_filter_options(
    *,
    search: str = "",
    limit: int = 100,
) -> list[dict[str, str]]:
    version = employees_catalog_data_version()
    cache_key = f"{_FILTER_OPTIONS_PREFIX}supervisors:{version}:{search}:{limit}"

    def _build() -> list[dict[str, str]]:
        with perf_span("scheduling.filters.supervisor_options"):
            from app.services.phase2_modules_service import list_employees
            from app.pages._core._data import _DEMO_EMPLOYEES
            from app.utils.permissions import normalize_role

            catalog, _ = list_employees(demo=list(_DEMO_EMPLOYEES))
            allowed_roles = {"admin", "supervisor", "project manager", "foreman", "lead"}
            out: list[dict[str, str]] = []
            for row in catalog:
                if row.get("is_deleted") or row.get("is_active") is False:
                    continue
                role = normalize_role(str(row.get("role") or ""))
                if role not in allowed_roles and not row.get("is_supervisor"):
                    continue
                eid = str(row.get("id") or "").strip()
                if not eid:
                    continue
                label = _employee_filter_label(row)
                if not _match_search(label, search):
                    continue
                out.append({"id": eid, "label": label})
                if len(out) >= limit:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def search_schedulable_jobs(*, search: str = "", limit: int = 100) -> list[dict[str, str]]:
    return list_schedule_job_filter_options(search=search, limit=limit)


def search_schedulable_employees(*, search: str = "", limit: int = 100) -> list[dict[str, str]]:
    version = employees_catalog_data_version()
    cache_key = f"{_FORM_OPTIONS_PREFIX}employees:{version}:{search}:{limit}"

    def _build() -> list[dict[str, str]]:
        from app.services.phase2_modules_service import list_employees
        from app.pages._core._data import _DEMO_EMPLOYEES

        catalog, _ = list_employees(demo=list(_DEMO_EMPLOYEES))
        out: list[dict[str, str]] = []
        for row in catalog:
            if row.get("is_deleted") or row.get("is_active") is False:
                continue
            eid = str(row.get("id") or "").strip()
            if not eid:
                continue
            label = _employee_filter_label(row)
            if not _match_search(label, search):
                continue
            out.append({"id": eid, "label": label})
            if len(out) >= limit:
                break
        return out

    return page_data_cache_get(cache_key, _build)


def search_schedulable_assets(*, search: str = "", limit: int = 100) -> list[dict[str, str]]:
    version = jobs_catalog_data_version()
    cache_key = f"{_FORM_OPTIONS_PREFIX}assets:{version}:{search}:{limit}"

    def _build() -> list[dict[str, str]]:
        from app.services.phase2_modules_service import list_assets
        from app.pages._core._data import _DEMO_ASSETS

        catalog, _ = list_assets(demo=list(_DEMO_ASSETS))
        out: list[dict[str, str]] = []
        for row in catalog:
            if row.get("is_deleted") or row.get("is_active") is False:
                continue
            aid = str(row.get("id") or "").strip()
            if not aid:
                continue
            num = str(row.get("asset_number") or row.get("asset_id") or "").strip()
            name = str(row.get("asset_name") or row.get("name") or "").strip()
            label = f"{num} — {name}" if num and name else num or name or aid
            if not _match_search(label, search):
                continue
            out.append({"id": aid, "label": label})
            if len(out) >= limit:
                break
        return out

    return page_data_cache_get(cache_key, _build)


def search_customers(*, search: str = "", limit: int = 100) -> list[dict[str, str]]:
    cache_key = f"{_FORM_OPTIONS_PREFIX}customers:{search}:{limit}"

    def _build() -> list[dict[str, str]]:
        from app.services.phase2_modules_service import list_customers
        from app.pages._core._data import _DEMO_CUSTOMERS

        catalog, _ = list_customers(demo=list(_DEMO_CUSTOMERS))
        out: list[dict[str, str]] = []
        for row in catalog:
            if row.get("is_deleted") or row.get("is_active") is False:
                continue
            cid = str(row.get("id") or "").strip()
            if not cid:
                continue
            label = str(row.get("customer_name") or row.get("name") or row.get("company_name") or cid)
            if not _match_search(label, search):
                continue
            out.append({"id": cid, "label": label})
            if len(out) >= limit:
                break
        return out

    return page_data_cache_get(cache_key, _build)


def list_active_employee_roster(*, limit: int = 500) -> list[dict[str, Any]]:
    version = employees_catalog_data_version()
    cache_key = f"scheduling_active_employees:{version}:{limit}"

    def _build() -> list[dict[str, Any]]:
        from app.services.phase2_modules_service import list_employees
        from app.pages._core._data import _DEMO_EMPLOYEES

        catalog, _ = list_employees(demo=list(_DEMO_EMPLOYEES))
        out: list[dict[str, Any]] = []
        for row in catalog:
            if row.get("is_deleted") or row.get("is_active") is False:
                continue
            eid = str(row.get("id") or "").strip()
            if not eid:
                continue
            out.append(
                {
                    "id": eid,
                    "full_name": row.get("full_name") or row.get("employee_name") or row.get("name"),
                    "employee_name": row.get("employee_name") or row.get("name"),
                    "name": row.get("name"),
                    "employee_number": row.get("employee_number"),
                    "status": row.get("status"),
                }
            )
            if len(out) >= limit:
                break
        return out

    return page_data_cache_get(cache_key, _build)


def list_relevant_certifications(
    employee_ids: list[str],
    required_types: list[str],
) -> list[dict[str, Any]]:
    ids = _unique_ids(employee_ids)
    if not ids:
        return []
    with perf_span("scheduling.certifications"):
        from app.services.phase2_modules_service import list_all_certifications
        from app.pages._core._data import _DEMO_CERTIFICATIONS, _DEMO_EMPLOYEES

        employees = get_people_by_ids(ids)
        if not employees:
            employees, _ = __import__(
                "app.services.phase2_modules_service", fromlist=["list_employees"]
            ).list_employees(demo=list(_DEMO_EMPLOYEES))
        demo = [c for c in _DEMO_CERTIFICATIONS if str(c.get("employee_id") or "") in set(ids)]
        rows, _ = list_all_certifications(demo=demo, employees=employees)
        wanted = {str(t or "").strip().lower() for t in required_types if str(t or "").strip()}
        if not wanted:
            return [r for r in rows if str(r.get("employee_id") or "").strip() in set(ids)]
        filtered: list[dict[str, Any]] = []
        for row in rows:
            if str(row.get("employee_id") or "").strip() not in set(ids):
                continue
            ctype = str(row.get("cert_type") or "").strip().lower()
            if not wanted or any(w in ctype or ctype in w for w in wanted):
                filtered.append(row)
        return filtered


@dataclass(frozen=True)
class SchedulingFormOptions:
    jobs: list[dict[str, str]]
    employees: list[dict[str, str]]
    assets: list[dict[str, str]]
    customers: list[dict[str, str]]
    certification_types: tuple[str, ...]


def load_scheduling_form_options(
    *,
    include_jobs: bool = True,
    include_employees: bool = True,
    include_assets: bool = True,
    include_customers: bool = True,
    preserve_ids: list[str] | None = None,
) -> SchedulingFormOptions:
    preserve = set(_unique_ids(preserve_ids or []))
    jobs = search_schedulable_jobs(limit=100) if include_jobs else []
    employees = search_schedulable_employees(limit=100) if include_employees else []
    assets = search_schedulable_assets(limit=100) if include_assets else []
    customers = search_customers(limit=100) if include_customers else []

    def _ensure(options: list[dict[str, str]], table_loader, label_fn) -> list[dict[str, str]]:
        present = {o["id"] for o in options}
        missing = [pid for pid in preserve if pid and pid not in present]
        if not missing:
            return options
        extra_rows = table_loader(missing)
        extra_opts = [{"id": str(r.get("id")), "label": label_fn(r)} for r in extra_rows if r.get("id")]
        return extra_opts + options

    if include_jobs:
        jobs = _ensure(jobs, get_jobs_by_ids, _job_filter_label)
    if include_employees:
        employees = _ensure(employees, get_people_by_ids, _employee_filter_label)
    if include_assets:
        def _asset_label(row: dict[str, Any]) -> str:
            num = str(row.get("asset_number") or row.get("asset_id") or "").strip()
            name = str(row.get("asset_name") or row.get("name") or "").strip()
            return f"{num} — {name}" if num and name else num or name or str(row.get("id"))

        assets = _ensure(assets, get_assets_by_ids, _asset_label)

    cert_types = (
        "TWIC",
        "Site Orientation",
        "Forklift",
        "Welding Certification",
        "Supplied-Air Qualification",
    )
    return SchedulingFormOptions(
        jobs=jobs,
        employees=employees,
        assets=assets,
        customers=customers,
        certification_types=cert_types,
    )
