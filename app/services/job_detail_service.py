"""Focused Job detail lookup and bounded modal cache."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.pages._core._data import jobs_catalog_data_version
from app.pages._core.page_data_cache import page_data_cache_get
from app.services.phase2_modules_service import normalize_job

_MODAL_CACHE_KEY = "_ips_jobs_modal_by_id"
_DETAIL_CACHE_PREFIX = "job_detail:"
_MAX_MODAL_CACHE = 50


def get_job_detail(job_id: str) -> dict[str, Any] | None:
    """Load base job record for header/overview/edit — no tab payloads."""
    jid = str(job_id or "").strip()
    if not jid:
        return None
    version = jobs_catalog_data_version()
    cache_key = f"{_DETAIL_CACHE_PREFIX}{jid}:{version}"

    def _fetch() -> dict[str, Any] | None:
        from app.services.repository import fetch_by_id

        row = fetch_by_id("jobs", jid)
        if not row:
            return None
        return normalize_job(row)

    detail = page_data_cache_get(cache_key, _fetch)
    if isinstance(detail, dict):
        put_job_in_modal_cache(jid, detail)
    return detail if isinstance(detail, dict) else None


def put_job_in_modal_cache(job_id: str, job: dict[str, Any] | None) -> None:
    """Bounded modal cache: current page, selected, and recently opened jobs."""
    jid = str(job_id or "").strip()
    if not jid or not isinstance(job, dict):
        return
    cache = st.session_state.get(_MODAL_CACHE_KEY)
    if not isinstance(cache, dict):
        cache = {}
    else:
        cache = dict(cache)
    cache[jid] = job
    if len(cache) > _MAX_MODAL_CACHE:
        drop = max(0, len(cache) - _MAX_MODAL_CACHE)
        for key in list(cache.keys())[:drop]:
            if key != jid:
                cache.pop(key, None)
    st.session_state[_MODAL_CACHE_KEY] = cache


def get_job_from_modal_cache(job_id: str) -> dict[str, Any] | None:
    jid = str(job_id or "").strip()
    if not jid:
        return None
    cache = st.session_state.get(_MODAL_CACHE_KEY)
    if isinstance(cache, dict):
        row = cache.get(jid)
        if isinstance(row, dict):
            return row
    return get_job_detail(jid)


def invalidate_job_detail_cache(job_id: str = "") -> None:
    jid = str(job_id or "").strip()
    cache = st.session_state.get(_MODAL_CACHE_KEY)
    if isinstance(cache, dict):
        updated = dict(cache)
        if jid:
            updated.pop(jid, None)
        else:
            updated.clear()
        st.session_state[_MODAL_CACHE_KEY] = updated


def list_job_equipment(job_id: str) -> list[dict[str, Any]]:
    """Equipment rows for one job with lightweight asset fields."""
    jid = str(job_id or "").strip()
    if not jid:
        return []
    from app.db import fetch_by_match_admin

    rows = fetch_by_match_admin("job_equipment", {"job_id": jid}, limit=200) or []
    if not rows:
        return []
    asset_ids = {str(r.get("asset_id") or "").strip() for r in rows if str(r.get("asset_id") or "").strip()}
    assets: dict[str, dict[str, Any]] = {}
    for aid in asset_ids:
        from app.services.repository import fetch_by_id

        asset = fetch_by_id("assets", aid)
        if asset:
            assets[aid] = asset
    out: list[dict[str, Any]] = []
    for row in rows:
        aid = str(row.get("asset_id") or "").strip()
        asset = assets.get(aid) or {}
        out.append(
            {
                **row,
                "asset_number": str(asset.get("asset_number") or asset.get("asset_id") or ""),
                "asset_name": str(asset.get("asset_name") or row.get("asset_label") or ""),
                "category": str(asset.get("category") or asset.get("asset_category") or ""),
                "status": str(asset.get("status") or ""),
            }
        )
    return out
