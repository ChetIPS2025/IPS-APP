"""
Database access layer for Inventory.

All calls to Supabase go through this module — the UI and services layers
must not import from ``db`` directly.
"""

from __future__ import annotations

import streamlit as st

try:
    from app.db import (
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )
except ImportError:
    from db import (  # type: ignore
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )

_TABLE = "inventory_items"
_DATA_VERSION_KEY = "inv_data_version"


# ---------------------------------------------------------------------------
# Cached read helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def fetch_inventory_items(data_version: int) -> list[dict]:
    """Return all inventory items, ordered by name. Cached; bump version after writes."""
    return fetch_table_admin(_TABLE, limit=5000, order_by="item_name")


@st.cache_data(ttl=3300, show_spinner=False)
def fetch_inventory_image_signed_url_cached(image_url: str) -> str | None:
    """Long-lived cache for storage-path → signed URL conversions."""
    from app.pages.inventory.services import get_signed_image_url  # avoid circular at module level
    return get_signed_image_url(image_url)


def get_current_data_version() -> int:
    return int(st.session_state.get(_DATA_VERSION_KEY, 0))


def bump_data_version() -> None:
    """Increment the data version to invalidate ``fetch_inventory_items`` cache."""
    st.session_state[_DATA_VERSION_KEY] = get_current_data_version() + 1
    try:
        fetch_inventory_items.clear()
        fetch_inventory_image_signed_url_cached.clear()
    except Exception:
        pass
    try:
        from app.data_cache import clear_session_table_cache
        clear_session_table_cache()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Single-item lookup
# ---------------------------------------------------------------------------

def fetch_item_by_id(item_id: str) -> dict | None:
    rows = fetch_by_match_admin(_TABLE, {"id": str(item_id).strip()}, limit=1)
    if rows:
        return dict(rows[0])
    return None


def check_qr_value_in_use(value: str, *, exclude_item_id: str | None) -> bool:
    v = str(value or "").strip()
    if not v:
        return False
    rows = fetch_by_match_admin(_TABLE, {"qr_code_value": v}, limit=5)
    if not rows:
        return False
    if exclude_item_id is None:
        return True
    ex = str(exclude_item_id).strip()
    return any(str(r.get("id") or "").strip() != ex for r in rows)


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def create_inventory_item(payload: dict) -> dict:
    return insert_row_admin(_TABLE, payload)


def update_inventory_item(item_id: str, payload: dict) -> None:
    update_rows_admin(_TABLE, payload, {"id": str(item_id).strip()})


def delete_inventory_item(item_id: str) -> None:
    delete_rows_admin(_TABLE, {"id": str(item_id).strip()})


def deactivate_inventory_items(ids: list[str]) -> None:
    for iid in ids:
        update_rows_admin(_TABLE, {"is_active": False}, {"id": str(iid).strip()})


def fetch_all_qr_rows() -> list[dict]:
    """Fetch id+qr_code_value for all items (used by backfill/regen)."""
    return fetch_table_admin(_TABLE, columns="id,qr_code_value", limit=20000, order_by="item_name")
