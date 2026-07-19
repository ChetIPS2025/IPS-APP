"""Employee Resources data versioning and centralized cache invalidation."""

from __future__ import annotations

_FALLBACK_VERSIONS: dict[str, int] = {}


def _version_store() -> dict[str, int]:
    try:
        import streamlit as st

        return st.session_state.setdefault("_ips_employee_resources_versions", {})
    except Exception:
        return _FALLBACK_VERSIONS


def employee_resources_data_version() -> int:
    return int(_version_store().get("_global") or 0)


def invalidate_employee_resources_cache(resource_id: str | None = None) -> int:
    """Bump data version and clear derived caches after writes."""
    store = _version_store()
    new_version = int(store.get("_global") or 0) + 1
    store["_global"] = new_version
    if resource_id:
        rid = str(resource_id).strip()
        if rid:
            store[rid] = int(store.get(rid) or 0) + 1

    try:
        import streamlit as st

        for key in list(st.session_state.keys()):
            sk = str(key)
            if sk.startswith("ips_er_signed_") or sk.startswith("ips_er_form_seeded_"):
                st.session_state.pop(key, None)
    except Exception:
        pass

    try:
        from app.pages._core.page_data_cache import (
            clear_dashboard_page_data_cache,
            clear_page_data_cache_prefix,
        )

        clear_page_data_cache_prefix("employee_resources:")
        clear_page_data_cache_prefix("er_detail:")
        clear_dashboard_page_data_cache()
    except Exception:
        pass

    try:
        from app.services.repository import clear_data_cache_for_table

        clear_data_cache_for_table("employee_toolbox_links")
    except Exception:
        pass

    return new_version


def detail_cache_version(resource_id: str) -> int:
    rid = str(resource_id or "").strip()
    if not rid:
        return employee_resources_data_version()
    store = _version_store()
    return int(store.get(rid) or employee_resources_data_version())


def finalize_employee_resource_write(resource_id: str | None = None) -> None:
    """Invalidate employee/admin resource caches after a successful write."""
    invalidate_employee_resources_cache(resource_id)


__all__ = [
    "detail_cache_version",
    "employee_resources_data_version",
    "finalize_employee_resource_write",
    "invalidate_employee_resources_cache",
]
