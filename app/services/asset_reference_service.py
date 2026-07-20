"""Lightweight employee and job label lookups for Assets directory views."""

from __future__ import annotations

from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get


def _employees_version() -> int:
    try:
        from app.pages._core._data import employees_catalog_data_version

        return employees_catalog_data_version()
    except Exception:
        return 0


def _jobs_version() -> int:
    try:
        from app.pages._core._data import jobs_catalog_data_version

        return jobs_catalog_data_version()
    except Exception:
        return 0


def get_people_labels_by_ids(employee_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Return lightweight employee rows keyed by id for directory label hydration."""
    from app.perf_debug import perf_span

    unique = sorted({str(eid or "").strip() for eid in employee_ids if str(eid or "").strip()})
    if not unique:
        return {}
    cache_key = f"assets_ref:people:{_employees_version()}:{','.join(unique[:80])}"

    def _build() -> dict[str, dict[str, Any]]:
        with perf_span("assets.serialized.reference_people"):
            from app.services.repository import fetch_by_id

            out: dict[str, dict[str, Any]] = {}
            for eid in unique:
                row = fetch_by_id("employees", eid) or fetch_by_id("user_profiles", eid)
                if not isinstance(row, dict):
                    continue
                name = str(row.get("name") or row.get("full_name") or "").strip()
                out[eid] = {
                    "id": eid,
                    "name": name,
                    "full_name": name,
                    "employee_number": str(row.get("employee_number") or "").strip(),
                }
            return out

    return page_data_cache_get(cache_key, _build)


def get_job_labels_by_ids(job_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Return lightweight job rows keyed by id for directory label hydration."""
    from app.perf_debug import perf_span

    unique = sorted({str(jid or "").strip() for jid in job_ids if str(jid or "").strip()})
    if not unique:
        return {}
    cache_key = f"assets_ref:jobs:{_jobs_version()}:{','.join(unique[:80])}"

    def _build() -> dict[str, dict[str, Any]]:
        with perf_span("assets.serialized.reference_jobs"):
            from app.services.repository import fetch_by_id

            out: dict[str, dict[str, Any]] = {}
            for jid in unique:
                row = fetch_by_id("jobs", jid)
                if not isinstance(row, dict):
                    continue
                out[jid] = {
                    "id": jid,
                    "job_number": str(row.get("job_number") or "").strip(),
                    "job_name": str(row.get("job_name") or row.get("name") or "").strip(),
                    "name": str(row.get("job_name") or row.get("name") or "").strip(),
                    "status": str(row.get("status") or "").strip(),
                }
            return out

    return page_data_cache_get(cache_key, _build)


__all__ = [
    "get_job_labels_by_ids",
    "get_people_labels_by_ids",
]
