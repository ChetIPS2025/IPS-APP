"""Focused Company Update detail loading."""

from __future__ import annotations

from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.company_updates_cache import detail_cache_version
from app.services.company_updates_directory_service import (
    normalize_update_audience,
    normalize_update_category,
    normalize_update_status,
    to_list_row,
)


def _load_raw_update(update_id: str) -> dict[str, Any] | None:
    uid = str(update_id or "").strip()
    if not uid:
        return None
    from app.services.updates_service import list_company_updates

    try:
        from app.pages._core._data import _DEMO_COMPANY_UPDATES
    except ImportError:
        _DEMO_COMPANY_UPDATES = []

    rows, _ = list_company_updates(category="All Updates", demo=list(_DEMO_COMPANY_UPDATES))
    for row in rows:
        if str(row.get("id") or "") == uid:
            return dict(row)
    return None


def get_company_update_detail(
    update_id: str,
    *,
    role: str = "",
    user_id: str = "",
) -> dict[str, Any] | None:
    from app.perf_debug import perf_span

    uid = str(update_id or "").strip()
    if not uid:
        return None
    version = detail_cache_version(uid)
    cache_key = f"cu_detail:{uid}:v{version}:role{role}"

    def _build() -> dict[str, Any] | None:
        with perf_span("company_updates.detail_lookup"):
            raw = _load_raw_update(uid)
            if not raw:
                return None
            from app.services.company_updates_directory_service import resolve_update_author_labels

            author_id = str(raw.get("created_by") or raw.get("posted_by") or "").strip()
            lookup = resolve_update_author_labels([author_id] if author_id else [])
            detail = dict(raw)
            detail.update(to_list_row(raw, author_lookup=lookup))
            detail["category"] = normalize_update_category(detail.get("category"))
            detail["status"] = normalize_update_status(detail.get("status"), is_active=detail.get("is_active"))
            detail["audience"] = normalize_update_audience(detail.get("audience") or detail.get("visibility"))
            return detail

    return page_data_cache_get(cache_key, _build)


def get_company_update_banner_preview(update: dict[str, Any]) -> str:
    """Return a cached preview URL for list/overview; resolves signed URL once per version."""
    uid = str(update.get("id") or "").strip()
    if not uid:
        return ""
    if not str(update.get("banner_path") or update.get("banner_file_name") or "").strip():
        if not str(update.get("banner_view_url") or "").strip():
            return ""
    version = detail_cache_version(uid)
    cache_key = f"cu_banner:{uid}:v{version}"

    def _build() -> str:
        from app.perf_debug import perf_span
        from app.services.updates_service import resolve_company_update_banner_url

        with perf_span("company_updates.banner_preview"):
            return str(resolve_company_update_banner_url(update) or "").strip()

    return page_data_cache_get(cache_key, _build)


def put_update_in_modal_cache(update_id: str, update: dict[str, Any]) -> None:
    """Bounded modal cache — selected update plus current page only."""
    import streamlit as st

    uid = str(update_id or "").strip()
    if not uid:
        return
    store = st.session_state.setdefault("_ips_cu_modal_by_id", {})
    if not isinstance(store, dict):
        store = {}
    store[uid] = dict(update)
    if len(store) > 50:
        for key in list(store.keys())[:-50]:
            if key != uid:
                store.pop(key, None)
    st.session_state["_ips_cu_modal_by_id"] = store
