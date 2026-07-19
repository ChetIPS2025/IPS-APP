"""Estimate cost data versioning and session cache invalidation (no UI)."""

from __future__ import annotations

from typing import Any

_FALLBACK_VERSIONS: dict[str, int] = {}


def _version_store() -> dict[str, int]:
    try:
        import streamlit as st

        return st.session_state.setdefault("_ips_estimate_cost_versions", {})
    except Exception:
        return _FALLBACK_VERSIONS


def estimate_cost_data_version(estimate_id: str) -> int:
    eid = str(estimate_id or "").strip()
    if not eid:
        return 0
    return int(_version_store().get(eid) or 0)


def invalidate_estimate_cost_cache(estimate_id: str) -> int:
    """Bump cost data version and clear derived page caches for one estimate."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return 0
    store = _version_store()
    new_version = int(store.get(eid) or 0) + 1
    store[eid] = new_version
    try:
        from app.pages._core.page_data_cache import clear_page_data_cache_prefix

        clear_page_data_cache_prefix(f"est_cost:{eid}:")
        clear_page_data_cache_prefix(f"est_cb_snapshot:{eid}:")
        clear_page_data_cache_prefix(f"est_cb_totals:{eid}:")
        clear_page_data_cache_prefix(f"est_proposal:{eid}:")
    except Exception:
        pass
    try:
        import streamlit as st

        for key in list(st.session_state.keys()):
            sk = str(key)
            if sk.startswith(f"ecb_totals_{eid}_") or sk == f"ecb_totals_{eid}":
                st.session_state.pop(key, None)
            if sk.startswith(f"ecb_proposal_{eid}_"):
                st.session_state.pop(key, None)
    except Exception:
        pass
    return new_version


def totals_cache_key(estimate_id: str, *, tax_rate: float) -> str:
    eid = str(estimate_id or "").strip()
    version = estimate_cost_data_version(eid)
    return f"est_cb_totals:{eid}:v{version}:tax{float(tax_rate or 0):.4f}"


def read_cached_totals(estimate_id: str, *, tax_rate: float) -> dict[str, Any] | None:
    key = totals_cache_key(estimate_id, tax_rate=tax_rate)
    try:
        from app.pages._core.page_data_cache import page_data_cache_get

        cached = page_data_cache_get(key, lambda: None)
        if isinstance(cached, dict) and cached:
            return cached
    except Exception:
        pass
    return None


def write_cached_totals(estimate_id: str, *, tax_rate: float, totals: dict[str, Any]) -> None:
    if not totals:
        return
    key = totals_cache_key(estimate_id, tax_rate=tax_rate)
    try:
        import streamlit as st

        store = st.session_state.setdefault("_ips_page_data_cache", {})
        store[key] = dict(totals)
    except Exception:
        pass


def clear_proposal_bundle(estimate_id: str) -> None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    try:
        from app.pages._core.page_data_cache import clear_page_data_cache_prefix

        clear_page_data_cache_prefix(f"est_proposal:{eid}:")
    except Exception:
        pass
    try:
        import streamlit as st

        for key in list(st.session_state.keys()):
            if str(key).startswith(f"ecb_proposal_{eid}_"):
                st.session_state.pop(key, None)
    except Exception:
        pass
