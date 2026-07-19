"""Paginated HTML kit item table."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlencode

import streamlit as st

from app.components.asset_kit.state import (
    KIT_ITEMS_DEFAULT_PAGE_SIZE,
    KIT_ITEMS_TABLE_KEY,
    kit_item_row_label,
)
from app.components.asset_kit.styles import kit_item_status_pill_html
from app.components.table_pagination import (
    page_size_key,
    paginate_rows,
    render_table_pagination_footer,
    render_table_pagination_header,
)
from app.services.asset_kits_service import CONDITIONS, ITEM_STATUSES, ITEM_TYPES, kit_data_version

_ASSETS_NAV = "assets"
_COLS = (
    ("name", "Item", 2.0),
    ("serial", "Serial", 1.0),
    ("type", "Type", 0.85),
    ("expected", "Expected", 0.55),
    ("actual", "Actual", 0.55),
    ("condition", "Condition", 0.95),
    ("status", "Status", 0.95),
    ("unit", "Unit Value", 0.8),
    ("total", "Total Value", 0.8),
    ("assigned", "Assigned To", 0.9),
)


def kit_item_detail_href(parent_asset_id: str, kit_item_id: str) -> str:
    return "?" + urlencode(
        {
            "ips_nav": _ASSETS_NAV,
            "asset_detail": str(parent_asset_id or "").strip(),
            "asset_tab": "kit",
            "kit_item": str(kit_item_id or "").strip(),
        }
    )


def build_kit_items_html_table(
    items: list[dict[str, Any]],
    *,
    asset_id: str,
    all_items: list[dict[str, Any]],
    selected_item_id: str = "",
) -> str:
    head = "".join(
        f'<th scope="col" class="ips-dash-est-th ips-kit-th-{html.escape(key)}">'
        f"{html.escape(label)}</th>"
        for key, label, _w in _COLS
    )
    body: list[str] = []
    for it in items:
        iid = str(it.get("id") or "")
        label = kit_item_row_label(it, all_items)
        href = html.escape(kit_item_detail_href(asset_id, iid), quote=True)
        selected_cls = " ips-kit-item-row-selected" if iid and iid == selected_item_id else ""
        name_cell = (
            f'<a class="ips-kit-item-open-link ips-dash-est-link" href="{href}" '
            f'target="_self" data-kit-item-id="{html.escape(iid, quote=True)}">'
            f"{html.escape(label)}</a>"
        )
        cells = [
            ("name", name_cell),
            ("serial", html.escape(str(it.get("serial_number") or "—"))),
            ("type", html.escape(str(it.get("item_type") or "—"))),
            ("expected", html.escape(str(it.get("quantity_expected") or 0))),
            ("actual", html.escape(str(it.get("quantity_actual") or 0))),
            ("condition", kit_item_status_pill_html(str(it.get("condition") or "—"))),
            ("status", kit_item_status_pill_html(str(it.get("status") or "—"))),
            ("unit", html.escape(str(it.get("unit_value") or 0))),
            ("total", html.escape(str(it.get("total_value") or 0))),
            ("assigned", html.escape(str(it.get("assigned_to_name") or "—"))),
        ]
        tds = "".join(
            f'<td class="ips-dash-est-td ips-kit-td-{html.escape(key)}">{val}</td>'
            for key, val in cells
        )
        body.append(
            f'<tr class="ips-dash-est-tr ips-kit-item-row{selected_cls}" '
            f'data-kit-item-id="{html.escape(iid, quote=True)}">{tds}</tr>'
        )
    return (
        '<div class="ips-dash-est-table-scroll">'
        '<table class="ips-dash-est-html-table ips-kit-items-html-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def _filter_kit_items(
    items: list[dict],
    *,
    type_f: str,
    cond_f: str,
    stat_f: str,
    assign_f: str,
) -> list[dict]:
    out = items
    if type_f and type_f != "All":
        out = [i for i in out if str(i.get("item_type") or "") == type_f]
    if cond_f and cond_f != "All":
        out = [i for i in out if str(i.get("condition") or "") == cond_f]
    if stat_f and stat_f != "All":
        out = [i for i in out if str(i.get("status") or "") == stat_f]
    if assign_f and assign_f != "All":
        out = [i for i in out if str(i.get("assigned_to_name") or "—") == assign_f]
    return out


def _build_filter_metadata(items: list[dict], asset_id: str) -> dict[str, list[str]]:
    from app.pages._core.page_data_cache import page_data_cache_get

    version = kit_data_version(asset_id)

    def _load() -> dict[str, list[str]]:
        assign = sorted({str(i.get("assigned_to_name") or "—") for i in items})
        return {
            "type": list(ITEM_TYPES),
            "condition": list(CONDITIONS),
            "status": list(ITEM_STATUSES),
            "assigned": assign,
        }

    return page_data_cache_get(f"kit_filter_meta_{asset_id}_v{version}", _load)


def render_kit_items_table(
    asset: dict,
    aid: str,
    items: list[dict],
    *,
    selected_item_id: str = "",
) -> list[dict]:
    """Render filter bar + paginated HTML table; return filtered items."""
    from app.components.asset_kit.state import sk
    from app.perf_debug import perf_span

    with perf_span("asset_kit.filter_metadata"):
        _build_filter_metadata(items, aid)

    fc1, fc2, fc3, fc4 = st.columns(4)
    type_f = fc1.selectbox("Type", ["All", *ITEM_TYPES], key=sk(aid, "f_type"), label_visibility="collapsed")
    cond_f = fc2.selectbox("Condition", ["All", *CONDITIONS], key=sk(aid, "f_cond"), label_visibility="collapsed")
    stat_f = fc3.selectbox("Status", ["All", *ITEM_STATUSES], key=sk(aid, "f_stat"), label_visibility="collapsed")
    assign_opts = ["All"] + sorted({str(i.get("assigned_to_name") or "—") for i in items})
    assign_f = fc4.selectbox("Assigned", assign_opts, key=sk(aid, "f_assign"), label_visibility="collapsed")

    with perf_span("asset_kit.filter_rows"):
        filtered = _filter_kit_items(items, type_f=type_f, cond_f=cond_f, stat_f=stat_f, assign_f=assign_f)

    with perf_span("asset_kit.pagination"):
        if page_size_key(KIT_ITEMS_TABLE_KEY) not in st.session_state:
            st.session_state[page_size_key(KIT_ITEMS_TABLE_KEY)] = KIT_ITEMS_DEFAULT_PAGE_SIZE
        render_table_pagination_header(len(filtered), KIT_ITEMS_TABLE_KEY, item_label="item")
        page_rows, _, _, _ = paginate_rows(
            filtered,
            KIT_ITEMS_TABLE_KEY,
            default_page_size=KIT_ITEMS_DEFAULT_PAGE_SIZE,
        )
        render_table_pagination_footer(
            len(filtered),
            KIT_ITEMS_TABLE_KEY,
        )

    with st.container(key="asset_kit_table_wrap"):
        with perf_span("asset_kit.table_html"):
            st.markdown(
                build_kit_items_html_table(
                    page_rows,
                    asset_id=aid,
                    all_items=items,
                    selected_item_id=selected_item_id,
                ),
                unsafe_allow_html=True,
            )

    return filtered
