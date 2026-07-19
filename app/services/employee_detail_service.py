"""Focused employee/user detail lookup and bounded modal cache."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

import streamlit as st

from app.pages._core.page_data_cache import page_data_cache_get

__all__ = [
    "cache_person_modal",
    "clear_person_modal_cache",
    "get_modal_person",
    "get_person_detail",
]

_DETAIL_CACHE_KEY = "_ips_employees_modal_by_id"
_MODAL_CACHE_MAX = 50


def _detail_cache_key(person_id: str) -> str:
    from app.pages._core._data import employees_catalog_data_version

    return f"people_detail:{person_id}:{employees_catalog_data_version()}"


def get_person_detail(person_id: str) -> dict[str, Any] | None:
    from app.perf_debug import perf_span
    from app.services.phase2_modules_service import normalize_employee

    pid = str(person_id or "").strip()
    if not pid:
        return None

    def _load() -> dict[str, Any] | None:
        from app.db import fetch_by_match
        from app.pages._core._data import _DEMO_EMPLOYEES, get_employee

        try:
            rows = fetch_by_match("employees", {"id": pid}, limit=1) or []
            if rows:
                return normalize_employee(rows[0])
        except Exception:
            pass
        cached = get_employee(pid)
        if cached:
            return cached
        for demo in _DEMO_EMPLOYEES:
            if str(demo.get("id") or "").strip() == pid:
                return normalize_employee(demo)
        return None

    with perf_span("people.detail_lookup"):
        return page_data_cache_get(_detail_cache_key(pid), _load)


def cache_person_modal(record: dict[str, Any]) -> None:
    pid = str(record.get("id") or "").strip()
    if not pid:
        return
    store: OrderedDict[str, dict[str, Any]] = st.session_state.setdefault(
        _DETAIL_CACHE_KEY,
        OrderedDict(),
    )
    if pid in store:
        store.move_to_end(pid)
    store[pid] = record
    while len(store) > _MODAL_CACHE_MAX:
        store.popitem(last=False)
    st.session_state[_DETAIL_CACHE_KEY] = store


def get_modal_person(person_id: str) -> dict[str, Any] | None:
    pid = str(person_id or "").strip()
    if not pid:
        return None
    store = st.session_state.get(_DETAIL_CACHE_KEY)
    if isinstance(store, dict) and pid in store:
        return store[pid]
    detail = get_person_detail(pid)
    if detail:
        cache_person_modal(detail)
    return detail


def clear_person_modal_cache(*, person_id: str | None = None) -> None:
    if person_id:
        store = st.session_state.get(_DETAIL_CACHE_KEY)
        if isinstance(store, dict):
            store.pop(str(person_id).strip(), None)
        from app.pages._core.page_data_cache import clear_page_data_cache_key

        clear_page_data_cache_key(_detail_cache_key(str(person_id).strip()))
        return
    st.session_state.pop(_DETAIL_CACHE_KEY, None)
