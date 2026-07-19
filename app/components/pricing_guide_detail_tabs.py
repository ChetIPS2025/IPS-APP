"""Conditional Pricing Guide detail tab routing — only the active tab body executes."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.components.record_modal import detail_field_html, dialog_card_html, placeholder_html, safe_value
from app.components.tabs import render_tabs
from app.perf_debug import perf_span
from app.services.pricing_guide_detail_service import list_pricing_price_history
from app.services.pricing_guide_service import class_pill_html, type_pill_html
from app.utils.formatting import fmt_currency

_DETAIL_TABS = (
    "Overview",
    "Pricing",
    "Links",
    "Price History",
    "Notes",
)
_PG_DETAIL_ACTIVE_TAB_KEY = "ips_pg_detail_active_tab"
_PRICE_HISTORY_TABLE_KEY = "pg_price_history"


def pricing_guide_detail_active_tab_key() -> str:
    return _PG_DETAIL_ACTIVE_TAB_KEY


def reset_pricing_guide_detail_tab(*, default: str = "Overview") -> None:
    st.session_state[_PG_DETAIL_ACTIVE_TAB_KEY] = default


def set_pricing_guide_detail_tab_from_query(tab: str) -> None:
    raw = str(tab or "").strip()
    if not raw:
        return
    alias = {
        "overview": "Overview",
        "pricing": "Pricing",
        "links": "Links",
        "price history": "Price History",
        "history": "Price History",
        "notes": "Notes",
    }
    resolved = alias.get(raw.lower(), raw)
    if resolved in _DETAIL_TABS:
        st.session_state[_PG_DETAIL_ACTIVE_TAB_KEY] = resolved


def _fitting_detail_fields_html(row: dict[str, Any]) -> str:
    if not str(row.get("connection_type") or row.get("dash_size") or "").strip():
        return ""
    parts: list[str] = []
    for label, key in (
        ("Product type", "product_type"),
        ("Connection", "connection_type"),
        ("Pipe size", "pipe_size"),
        ("Dash size", "dash_size"),
        ("Pressure class", "pressure_class"),
        ("Body shape", "body_shape"),
        ("Material", "material_grade"),
        ("Max pressure", "max_pressure_temp"),
        ("Max steam pressure", "max_steam_pressure_temp"),
    ):
        val = str(row.get(key) or "").strip()
        if val:
            parts.append(detail_field_html(label, val))
    return "".join(parts)


def _status_pill_html(status: str) -> str:
    from app.components.record_modal import status_pill_html

    return status_pill_html(status)


def render_pricing_guide_detail_tabs(
    row: dict[str, Any],
    *,
    permissions: Any,
    render_overview_photo_fn: Any,
    render_links_panel_fn: Any,
) -> None:
    """Render one detail tab body based on render_tabs() selection."""
    rid = str(row.get("id") or "").strip()
    tab = render_tabs(
        list(_DETAIL_TABS),
        session_key=f"ips_pg_tab_{rid}",
        default=str(st.session_state.get(_PG_DETAIL_ACTIVE_TAB_KEY) or "Overview"),
    )
    st.session_state[_PG_DETAIL_ACTIVE_TAB_KEY] = tab

    if tab == "Overview":
        with perf_span("pricing_guide.detail.overview"):
            media, details = st.columns([1.0, 2.2])
            with media:
                st.markdown("**Item Image**")
                render_overview_photo_fn(row, permissions=permissions)
            with details:
                st.markdown(
                    dialog_card_html(
                        "Overview",
                        f"{detail_field_html('Description', row.get('item'))}"
                        f"{detail_field_html('Item code', row.get('item_code') or row.get('item_key'))}"
                        f'{detail_field_html("Class", row.get("item_class"), html_value=class_pill_html(str(row.get("item_class") or "")))}'
                        f'{detail_field_html("Estimate type", row.get("item_type"), html_value=type_pill_html(str(row.get("item_type") or "")))}'
                        f"{detail_field_html('SKU', row.get('sku') or '—')}"
                        f"{detail_field_html('Item #', row.get('item_number') or '—')}"
                        f"{detail_field_html('Model #', row.get('model_number') or '—')}"
                        f"{detail_field_html('Image status', row.get('image_status') or 'missing')}"
                        f"{detail_field_html('Category', row.get('category'))}"
                        f"{detail_field_html('Subcategory', row.get('subcategory') or '—')}"
                        f"{_fitting_detail_fields_html(row)}"
                        f"{detail_field_html('Unit', row.get('unit'))}"
                        f'{detail_field_html("Status", row.get("status"), html_value=_status_pill_html(str(row.get("status") or "")))}',
                    ),
                    unsafe_allow_html=True,
                )
    elif tab == "Pricing":
        with perf_span("pricing_guide.detail.pricing"):
            mk = float(row.get("markup_pct") or 0)
            st.markdown(
                dialog_card_html(
                    "Pricing",
                    f"{detail_field_html('Cost', fmt_currency(row.get('default_cost')))}"
                    f"{detail_field_html('Markup %', f'{mk:.1f}%')}"
                    f"{detail_field_html('Sell price', fmt_currency(row.get('customer_price')))}"
                    f"{detail_field_html('Taxable', 'Yes' if row.get('taxable') is not False else 'No')}",
                ),
                unsafe_allow_html=True,
            )
    elif tab == "Links":
        with perf_span("pricing_guide.detail.links"):
            render_links_panel_fn(row, permissions=permissions)
    elif tab == "Price History":
        with perf_span("pricing_guide.detail.price_history"):
            _render_price_history_tab(row)
    else:
        notes = safe_value(row.get("notes"), "No notes.")
        st.markdown(
            dialog_card_html("Notes", f"<p style='margin:0;font-size:0.875rem;'>{html.escape(notes)}</p>"),
            unsafe_allow_html=True,
        )


def _render_price_history_tab(row: dict[str, Any]) -> None:
    from app.components.table_pagination import (
        page_key,
        page_size_key,
        pagination_meta,
        render_table_pagination_footer,
        render_table_pagination_header,
    )

    rid = str(row.get("id") or "").strip()
    page_num = int(st.session_state.get(page_key(_PRICE_HISTORY_TABLE_KEY), 1))
    page_size = max(10, int(st.session_state.get(page_size_key(_PRICE_HISTORY_TABLE_KEY), 25)))
    history_page = list_pricing_price_history(rid, page=page_num, page_size=page_size)
    page_num, page_size, _ = pagination_meta(
        history_page.total_count,
        _PRICE_HISTORY_TABLE_KEY,
        default_page_size=25,
    )
    if page_num != history_page.page or page_size != history_page.page_size:
        history_page = list_pricing_price_history(rid, page=page_num, page_size=page_size)
    if not history_page.rows:
        st.markdown(
            dialog_card_html("Price History", placeholder_html("No price changes recorded yet.")),
            unsafe_allow_html=True,
        )
        return
    render_table_pagination_header(history_page.total_count, _PRICE_HISTORY_TABLE_KEY, item_label="change")
    rows_html = "".join(
        f"<tr><td>{html.escape(str(h.get('changed_at') or '')[:10])}</td>"
        f"<td>{html.escape(fmt_currency(h.get('old_cost')))}</td>"
        f"<td>{html.escape(fmt_currency(h.get('new_cost')))}</td>"
        f"<td>{html.escape(str(h.get('changed_by') or '—'))}</td></tr>"
        for h in history_page.rows
    )
    table = (
        '<table class="ips-est-line-table"><thead><tr>'
        "<th>Date</th><th>Old Cost</th><th>New Cost</th><th>Changed By</th>"
        f"</tr></thead><tbody>{rows_html}</tbody></table>"
    )
    st.markdown(dialog_card_html("Price History", table), unsafe_allow_html=True)
    render_table_pagination_footer(history_page.total_count, _PRICE_HISTORY_TABLE_KEY)
