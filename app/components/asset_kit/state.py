"""Kit tab session keys, page data snapshot, and query-param helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.asset_kits_service import (
    get_asset_kit_audits,
    get_asset_kit_items,
    get_asset_kit_summary,
    kit_data_version,
)

KIT_ITEMS_TABLE_KEY = "asset_kit_items"
KIT_ITEMS_DEFAULT_PAGE_SIZE = 25
KIT_AUDIT_PAGE_SIZE = 10
MAX_KIT_UNIT_SERIAL_INPUTS = 25

KIT_ITEM_QUERY_KEY = "kit_item"
ASSET_TAB_QUERY_KEY = "asset_tab"


def sk(aid: str, suffix: str) -> str:
    return f"kit_{suffix}_{aid}"


def assignment_edit_key(aid: str) -> str:
    return f"kit_assignment_edit_{aid}"


def audits_loaded_key(aid: str) -> str:
    return f"kit_audits_loaded_{aid}"


def audit_page_key(aid: str) -> str:
    return f"kit_audit_page_{aid}"


@dataclass(frozen=True)
class KitPageData:
    asset_id: str
    items: list[dict[str, Any]]
    summary: dict[str, Any]
    recent_audits: list[dict[str, Any]] | None = None


def load_kit_page_data(
    asset: dict[str, Any],
    *,
    include_recent_audits: bool = False,
) -> KitPageData:
    """Load kit items and summary once per data version."""
    from app.perf_debug import perf_span

    aid = str(asset.get("id") or "").strip()
    version = kit_data_version(aid)

    def _load() -> KitPageData:
        with perf_span("asset_kit.items_query"):
            items = get_asset_kit_items(aid)
        with perf_span("asset_kit.summary"):
            summary = get_asset_kit_summary(aid, asset, items=items)
        audits: list[dict[str, Any]] | None = None
        if include_recent_audits:
            with perf_span("asset_kit.audit_history"):
                audits = get_asset_kit_audits(aid, limit=5)
        return KitPageData(
            asset_id=aid,
            items=items,
            summary=summary,
            recent_audits=audits,
        )

    return page_data_cache_get(f"kit_page_{aid}_v{version}", _load)


def kit_item_row_label(item: dict[str, Any], items: list[dict[str, Any]]) -> str:
    """Disambiguate duplicate item names when multiple units exist."""
    name = str(item.get("item_name") or "—").strip() or "—"
    serial = str(item.get("serial_number") or "").strip()
    same_name = [i for i in items if str(i.get("item_name") or "").strip() == name]
    if len(same_name) <= 1:
        return name
    if serial:
        return f"{name} · S/N {serial}"
    ordered = sorted(same_name, key=lambda r: str(r.get("id") or ""))
    unit_no = ordered.index(item) + 1 if item in ordered else 1
    return f"{name} (#{unit_no})"


def kit_item_select_label(item: dict[str, Any], items: list[dict[str, Any]]) -> str:
    """Display label for selectboxes — always unique by item id."""
    base = kit_item_row_label(item, items)
    iid = str(item.get("id") or "").strip()
    if iid and base:
        return f"{base} [{iid[:8]}]"
    return base or iid or "Item"


def apply_kit_item_query_param(asset_id: str, items: list[dict[str, Any]]) -> str | None:
    """Apply kit_item query param to session selection; return warning if invalid."""
    aid = str(asset_id or "").strip()
    raw = str(st.query_params.get(KIT_ITEM_QUERY_KEY) or "").strip()
    if not raw:
        return None
    valid_ids = {str(i.get("id") or "") for i in items}
    if raw not in valid_ids:
        if KIT_ITEM_QUERY_KEY in st.query_params:
            del st.query_params[KIT_ITEM_QUERY_KEY]
        return raw
    st.session_state[sk(aid, "sel")] = raw
    st.session_state[sk(aid, "view")] = "detail"
    return None


def clear_kit_item_query_param() -> None:
    if KIT_ITEM_QUERY_KEY in st.query_params:
        del st.query_params[KIT_ITEM_QUERY_KEY]


def selected_kit_item_id(asset_id: str) -> str:
    return str(st.session_state.get(sk(asset_id, "sel")) or "")


def set_kit_view(asset_id: str, view: str) -> None:
    st.session_state[sk(asset_id, "view")] = view


def kit_view(asset_id: str) -> str:
    return str(st.session_state.get(sk(asset_id, "view")) or "list")
