"""Inventory list native navigation links."""

from __future__ import annotations

from urllib.parse import urlencode

_INVENTORY_DETAIL_QUERY_KEY = "inventory_detail"
_INVENTORY_TAB_QUERY_KEY = "inventory_tab"
_NAV_QUERY_KEY = "ips_nav"


def inventory_detail_query_key() -> str:
    return _INVENTORY_DETAIL_QUERY_KEY


def inventory_detail_href(item_id: str, *, tab: str = "") -> str:
    """Same-app URL to open Inventory Item Details."""
    iid = str(item_id or "").strip()
    params: dict[str, str] = {_NAV_QUERY_KEY: "inventory", _INVENTORY_DETAIL_QUERY_KEY: iid}
    tab_val = str(tab or "").strip()
    if tab_val:
        params[_INVENTORY_TAB_QUERY_KEY] = tab_val
    return "?" + urlencode(params)
