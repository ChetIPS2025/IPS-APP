"""Focused Estimate detail lookup and bounded modal cache."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from app.pages._core._data import estimates_catalog_data_version
from app.pages._core.page_data_cache import page_data_cache_get

_MODAL_CACHE_KEY = "_ips_estimates_modal_by_id"
_DETAIL_CACHE_PREFIX = "estimate_detail:"
_MAX_MODAL_CACHE = 50


@dataclass(frozen=True)
class EstimateDocumentsPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int


def get_estimate_detail(estimate_id: str) -> dict[str, Any] | None:
    """Load base estimate record for header/tabs/edit — no Cost Builder payloads."""
    from app.perf_debug import perf_span

    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    version = estimates_catalog_data_version()
    cache_key = f"{_DETAIL_CACHE_PREFIX}{eid}:{version}"

    def _fetch() -> dict[str, Any] | None:
        from app.services.repository import fetch_by_id
        from app.services.phase2_modules_service import normalize_estimate

        row = fetch_by_id("estimates", eid)
        if not row:
            return None
        try:
            from app.services.estimate_job_workflow_service import enrich_estimates_with_job_numbers

            enriched = enrich_estimates_with_job_numbers([row])
            if enriched:
                row = enriched[0]
        except Exception:
            pass
        return normalize_estimate(row)

    with perf_span("estimates.detail_lookup"):
        detail = page_data_cache_get(cache_key, _fetch)
    if isinstance(detail, dict):
        put_estimate_in_modal_cache(eid, detail)
    return detail if isinstance(detail, dict) else None


def put_estimate_in_modal_cache(estimate_id: str, row: dict[str, Any] | None) -> None:
    eid = str(estimate_id or "").strip()
    if not eid or not isinstance(row, dict):
        return
    cache = st.session_state.get(_MODAL_CACHE_KEY)
    if not isinstance(cache, dict):
        cache = {}
    else:
        cache = dict(cache)
    cache[eid] = row
    if len(cache) > _MAX_MODAL_CACHE:
        drop = max(0, len(cache) - _MAX_MODAL_CACHE)
        for key in list(cache.keys())[:drop]:
            if key != eid:
                cache.pop(key, None)
    st.session_state[_MODAL_CACHE_KEY] = cache


def get_estimate_from_modal_cache(estimate_id: str) -> dict[str, Any] | None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    cache = st.session_state.get(_MODAL_CACHE_KEY)
    if isinstance(cache, dict):
        row = cache.get(eid)
        if isinstance(row, dict):
            return row
    return get_estimate_detail(eid)


def invalidate_estimate_detail_cache(estimate_id: str = "") -> None:
    eid = str(estimate_id or "").strip()
    cache = st.session_state.get(_MODAL_CACHE_KEY)
    if isinstance(cache, dict):
        updated = dict(cache)
        if eid:
            updated.pop(eid, None)
        else:
            updated.clear()
        st.session_state[_MODAL_CACHE_KEY] = updated


def list_documents_for_estimate(
    estimate_id: str,
    *,
    estimate_number: str = "",
    linked_ref: str = "",
    page: int = 1,
    page_size: int = 25,
    role: str = "admin",
) -> EstimateDocumentsPage:
    """Documents linked to one estimate — not the full Documents Hub."""
    from app.perf_debug import perf_span

    eid = str(estimate_id or "").strip()
    if not eid:
        return EstimateDocumentsPage([], 0, 1, page_size)
    num = str(estimate_number or "").strip()
    ref = str(linked_ref or "").strip()
    version = estimates_catalog_data_version()
    cache_key = f"est_docs:{eid}:{version}:{role}:{page}:{page_size}"

    def _fetch() -> list[dict[str, Any]]:
        from app.db import fetch_by_match_admin

        rows: list[dict[str, Any]] = []
        try:
            matched = list(
                fetch_by_match_admin(
                    "documents",
                    {"linked_record_id": eid},
                    limit=500,
                    order_by="upload_date",
                )
                or []
            )
            rows.extend(r for r in matched if isinstance(r, dict))
        except Exception:
            pass
        if num or ref:
            try:
                legacy = list(fetch_by_match_admin("documents", {"linked_module": "estimates"}, limit=500) or [])
                for doc in legacy:
                    if not isinstance(doc, dict):
                        continue
                    linked_ref_val = str(doc.get("linked_ref") or "")
                    if str(doc.get("linked_record_id") or "") == eid:
                        rows.append(doc)
                    elif num and num in linked_ref_val:
                        rows.append(doc)
                    elif ref and ref in linked_ref_val:
                        rows.append(doc)
            except Exception:
                pass
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for doc in rows:
            did = str(doc.get("id") or "")
            if did and did in seen:
                continue
            if did:
                seen.add(did)
            mod = str(doc.get("linked_module") or "").strip().lower()
            if mod and mod not in {"estimates", "estimate", ""}:
                continue
            unique.append(doc)
        unique.sort(key=lambda r: str(r.get("upload_date") or r.get("created_at") or ""), reverse=True)
        return unique

    with perf_span("estimates.detail.documents"):
        all_rows = page_data_cache_get(cache_key, _fetch)
    total = len(all_rows)
    page_num = max(1, int(page))
    size = max(1, int(page_size))
    start = (page_num - 1) * size
    return EstimateDocumentsPage(all_rows[start : start + size], total, page_num, size)
