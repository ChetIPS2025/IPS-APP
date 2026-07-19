"""Customers catalog versioning and cache invalidation."""

from __future__ import annotations

_FALLBACK_VERSIONS: dict[str, int] = {}


def _version_store() -> dict[str, int]:
    try:
        import streamlit as st

        return st.session_state.setdefault("_ips_customers_catalog_versions", {})
    except Exception:
        return _FALLBACK_VERSIONS


def customers_catalog_data_version() -> int:
    return int(_version_store().get("_global") or 0)


def invalidate_customers_directory_cache(customer_id: str | None = None) -> int:
    """Bump catalog version and clear derived caches after writes."""
    store = _version_store()
    new_version = int(store.get("_global") or 0) + 1
    store["_global"] = new_version
    if customer_id:
        cid = str(customer_id).strip()
        store[cid] = int(store.get(cid) or 0) + 1

    try:
        from app.pages._core._data import clear_customers_catalog_cache

        clear_customers_catalog_cache()
    except Exception:
        pass

    try:
        from app.pages._core.page_data_cache import (
            clear_customers_page_data_cache,
            clear_page_data_cache_prefix,
        )

        clear_page_data_cache_prefix("customers:")
        clear_page_data_cache_prefix("cust_detail:")
        clear_page_data_cache_prefix("cust_loc:")
        clear_page_data_cache_prefix("cust_contact:")
        clear_page_data_cache_prefix("cust_rel:")
        clear_customers_page_data_cache()
    except Exception:
        pass

    try:
        import streamlit as st

        for key in list(st.session_state.keys()):
            sk = str(key)
            if sk.startswith("customers_enriched"):
                st.session_state.pop(key, None)
    except Exception:
        pass

    return new_version


def detail_cache_version(customer_id: str) -> int:
    cid = str(customer_id or "").strip()
    if not cid:
        return customers_catalog_data_version()
    store = _version_store()
    return int(store.get(cid) or customers_catalog_data_version())
