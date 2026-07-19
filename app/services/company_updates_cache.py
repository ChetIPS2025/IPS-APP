"""Company Updates data versioning and cache invalidation."""

from __future__ import annotations

_FALLBACK_VERSIONS: dict[str, int] = {}


def _version_store() -> dict[str, int]:
    try:
        import streamlit as st

        return st.session_state.setdefault("_ips_company_updates_versions", {})
    except Exception:
        return _FALLBACK_VERSIONS


def company_updates_data_version() -> int:
    return int(_version_store().get("_global") or 0)


def invalidate_company_updates_cache(update_id: str | None = None) -> int:
    """Bump data version and clear derived caches after writes."""
    store = _version_store()
    new_version = int(store.get("_global") or 0) + 1
    store["_global"] = new_version
    if update_id:
        uid = str(update_id).strip()
        store[uid] = int(store.get(uid) or 0) + 1

    try:
        from app.pages._core.page_data_cache import (
            clear_page_data_cache_prefix,
            clear_dashboard_page_data_cache,
        )

        clear_page_data_cache_prefix("company_updates:")
        clear_page_data_cache_prefix("cu_authors:")
        clear_page_data_cache_prefix("cu_detail:")
        clear_page_data_cache_prefix("cu_banner:")
        clear_dashboard_page_data_cache()
    except Exception:
        pass

    try:
        import streamlit as st

        for key in list(st.session_state.keys()):
            sk = str(key)
            if sk.startswith("cu_banner_preview_") or sk.startswith("ecb_proposal_"):
                st.session_state.pop(key, None)
    except Exception:
        pass

    try:
        from app.services.repository import clear_data_cache_for_table

        clear_data_cache_for_table("company_updates")
    except Exception:
        pass

    return new_version


def detail_cache_version(update_id: str) -> int:
    uid = str(update_id or "").strip()
    if not uid:
        return company_updates_data_version()
    store = _version_store()
    return int(store.get(uid) or company_updates_data_version())
