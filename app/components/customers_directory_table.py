"""Customers directory native navigation links."""

from __future__ import annotations

import html
from urllib.parse import urlencode

_NAV_QUERY_KEY = "ips_nav"
_CUSTOMER_DETAIL_QUERY_KEY = "customer_detail"
_CUSTOMER_DETAIL_TAB_QUERY_KEY = "customer_tab"
_LOCATION_DETAIL_QUERY_KEY = "location_detail"
_CONTACT_DETAIL_QUERY_KEY = "contact_detail"


def customer_detail_query_key() -> str:
    return _CUSTOMER_DETAIL_QUERY_KEY


def customer_tab_query_key() -> str:
    return _CUSTOMER_DETAIL_TAB_QUERY_KEY


def location_detail_query_key() -> str:
    return _LOCATION_DETAIL_QUERY_KEY


def contact_detail_query_key() -> str:
    return _CONTACT_DETAIL_QUERY_KEY


def customer_detail_href(customer_id: str, *, tab: str = "") -> str:
    cid = str(customer_id or "").strip()
    params: dict[str, str] = {_NAV_QUERY_KEY: "customers", _CUSTOMER_DETAIL_QUERY_KEY: cid}
    tab_val = str(tab or "").strip()
    if tab_val:
        params[_CUSTOMER_DETAIL_TAB_QUERY_KEY] = tab_val
    return "?" + urlencode(params)


def nested_contact_detail_href(customer_id: str, contact_id: str) -> str:
    params = {
        _NAV_QUERY_KEY: "customers",
        _CUSTOMER_DETAIL_QUERY_KEY: str(customer_id or "").strip(),
        _CUSTOMER_DETAIL_TAB_QUERY_KEY: "contacts",
        _CONTACT_DETAIL_QUERY_KEY: str(contact_id or "").strip(),
    }
    return "?" + urlencode(params)


def nested_location_detail_href(customer_id: str, location_id: str) -> str:
    params = {
        _NAV_QUERY_KEY: "customers",
        _CUSTOMER_DETAIL_QUERY_KEY: str(customer_id or "").strip(),
        _CUSTOMER_DETAIL_TAB_QUERY_KEY: "locations",
        _LOCATION_DETAIL_QUERY_KEY: str(location_id or "").strip(),
    }
    return "?" + urlencode(params)


def customer_name_link_html(customer_id: str, label: str) -> str:
    cid = str(customer_id or "").strip()
    text = html.escape(str(label or "Customer"))
    href = html.escape(customer_detail_href(cid), quote=True)
    aria = html.escape(f"Open customer details for {label or 'customer'}", quote=True)
    return (
        f'<a class="ips-customers-open-link ips-dash-est-desc-link" href="{href}" '
        f'target="_self" aria-label="{aria}">{text}</a>'
    )
