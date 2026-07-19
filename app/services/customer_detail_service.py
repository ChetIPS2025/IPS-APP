"""Focused Customer detail loading."""

from __future__ import annotations

from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.customer_relationships_service import (
    count_open_estimates_by_customer_ids,
    count_open_jobs_by_customer_ids,
)
from app.services.customers_cache import detail_cache_version
from app.services.customers_directory_service import to_list_row, _bulk_contact_counts, _bulk_location_summary


def get_customer_detail(customer_id: str) -> dict[str, Any] | None:
    from app.perf_debug import perf_span

    cid = str(customer_id or "").strip()
    if not cid:
        return None
    version = detail_cache_version(cid)
    cache_key = f"cust_detail:{cid}:v{version}"

    def _build() -> dict[str, Any] | None:
        with perf_span("customers.detail_lookup"):
            from app.services.customers_service import get_customers

            raw = next((r for r in get_customers(enrich=False) if str(r.get("id")) == cid), None)
            if not raw:
                return None
            name = str(raw.get("customer_name") or raw.get("company_name") or "")
            loc = _bulk_location_summary([cid]).get(cid, {})
            contacts = _bulk_contact_counts([cid]).get(cid, 0)
            open_jobs = count_open_jobs_by_customer_ids([(cid, name)]).get(cid, 0)
            open_ests = count_open_estimates_by_customer_ids([(cid, name)]).get(cid, 0)
            detail = dict(raw)
            detail.update(
                to_list_row(
                    raw,
                    location_summary=loc,
                    contact_count=contacts,
                    open_jobs=open_jobs,
                    open_estimates=open_ests,
                )
            )
            return detail

    return page_data_cache_get(cache_key, _build)


def put_customer_in_modal_cache(customer_id: str, customer: dict[str, Any]) -> None:
    import streamlit as st

    cid = str(customer_id or "").strip()
    if not cid:
        return
    store = st.session_state.setdefault("_ips_customers_modal_by_id", {})
    if not isinstance(store, dict):
        store = {}
    store[cid] = dict(customer)
    if len(store) > 50:
        for key in list(store.keys())[:-50]:
            if key != cid:
                store.pop(key, None)
    st.session_state["_ips_customers_modal_by_id"] = store
