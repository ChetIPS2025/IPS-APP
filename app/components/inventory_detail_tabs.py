"""Conditional Inventory Item Detail tab routing."""

from __future__ import annotations

import streamlit as st

from app.components.tabs import render_tabs
from app.perf_debug import perf_span

_INVENTORY_DETAIL_ACTIVE_TAB_KEY = "ips_inventory_detail_active_tab"
_INV_TAB_LABELS = [
    "Overview",
    "Stock History",
    "Transactions",
    "Purchase Orders",
    "Vendors",
    "Notes",
    "Attachments",
]


def inventory_detail_active_tab_key() -> str:
    return _INVENTORY_DETAIL_ACTIVE_TAB_KEY


def reset_inventory_detail_tab(*, default: str = "Overview") -> None:
    st.session_state[_INVENTORY_DETAIL_ACTIVE_TAB_KEY] = default


def set_inventory_detail_tab_from_query(tab: str) -> None:
    raw = str(tab or "").strip()
    if not raw:
        return
    alias = {
        "overview": "Overview",
        "stock history": "Stock History",
        "transactions": "Transactions",
        "purchase orders": "Purchase Orders",
        "vendors": "Vendors",
        "notes": "Notes",
        "attachments": "Attachments",
    }
    st.session_state[_INVENTORY_DETAIL_ACTIVE_TAB_KEY] = alias.get(raw.lower(), raw)


def _tab_matches(active: str, *names: str) -> bool:
    base = str(active or "").split(" (")[0].strip().lower()
    return base in {n.lower() for n in names}


def render_inventory_detail_tabs(item: dict) -> None:
    from app.pages.inventory import (
        _inventory_description,
        _inventory_unit,
        _render_inventory_detail_overview,
        _render_inventory_transactions_tab,
    )

    active_tab = render_tabs(
        _INV_TAB_LABELS,
        session_key=_INVENTORY_DETAIL_ACTIVE_TAB_KEY,
        default="Overview",
    )

    if _tab_matches(active_tab, "Overview"):
        with perf_span("inventory.detail.overview"):
            _render_inventory_detail_overview(item)
    elif _tab_matches(active_tab, "Stock History"):
        from app.components.record_modal import placeholder_html

        placeholder_html("Stock History will connect to Supabase in a later phase.")
    elif _tab_matches(active_tab, "Transactions"):
        with perf_span("inventory.detail.transactions"):
            _render_inventory_transactions_tab(item)
    elif _tab_matches(active_tab, "Purchase Orders"):
        from app.components.record_modal import placeholder_html

        placeholder_html("Purchase Orders will connect to Supabase in a later phase.")
    elif _tab_matches(active_tab, "Vendors"):
        from app.components.record_modal import placeholder_html

        placeholder_html("Vendors will connect to Supabase in a later phase.")
    elif _tab_matches(active_tab, "Notes"):
        from app.components.record_modal import placeholder_html

        placeholder_html("Notes will connect to Supabase in a later phase.")
    elif _tab_matches(active_tab, "Attachments"):
        from app.components.record_modal import placeholder_html

        placeholder_html("Attachments will connect to Supabase in a later phase.")
