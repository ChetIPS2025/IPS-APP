"""Employee Portal data versioning and cache invalidation."""

from __future__ import annotations

_FALLBACK_VERSIONS: dict[str, int] = {}


def _version_store() -> dict[str, int]:
    try:
        import streamlit as st

        return st.session_state.setdefault("_ips_employee_portal_versions", {})
    except Exception:
        return _FALLBACK_VERSIONS


def employee_portal_data_version(employee_id: str | None = None) -> int:
    store = _version_store()
    if employee_id:
        eid = str(employee_id).strip()
        if eid:
            return int(store.get(eid) or store.get("_global") or 0)
    return int(store.get("_global") or 0)


def invalidate_employee_portal_cache(
    employee_id: str | None = None,
    *,
    section: str | None = None,
) -> int:
    store = _version_store()
    new_global = int(store.get("_global") or 0) + 1
    store["_global"] = new_global
    if employee_id:
        eid = str(employee_id).strip()
        if eid:
            store[eid] = int(store.get(eid) or 0) + 1
    if section:
        store[f"sec:{section}"] = int(store.get(f"sec:{section}") or 0) + 1

    try:
        from app.pages._core.page_data_cache import (
            clear_dashboard_page_data_cache,
            clear_page_data_cache_prefix,
        )

        clear_page_data_cache_prefix("employee_portal:")
        clear_dashboard_page_data_cache()
    except Exception:
        pass

    return new_global


def invalidate_portal_updates_cache() -> None:
    invalidate_employee_portal_cache(section="updates")
    try:
        from app.services.company_updates_cache import invalidate_company_updates_cache

        invalidate_company_updates_cache()
    except Exception:
        pass


def invalidate_portal_jobs_cache(employee_id: str | None = None) -> None:
    invalidate_employee_portal_cache(employee_id, section="jobs")


def invalidate_portal_certifications_cache(employee_id: str | None = None) -> None:
    invalidate_employee_portal_cache(employee_id, section="certifications")


def invalidate_portal_schedule_cache(employee_id: str | None = None) -> None:
    invalidate_employee_portal_cache(employee_id, section="schedule")


def invalidate_portal_bids_cache() -> None:
    invalidate_employee_portal_cache(section="bids")


__all__ = [
    "employee_portal_data_version",
    "invalidate_employee_portal_cache",
    "invalidate_portal_bids_cache",
    "invalidate_portal_certifications_cache",
    "invalidate_portal_jobs_cache",
    "invalidate_portal_schedule_cache",
    "invalidate_portal_updates_cache",
]
