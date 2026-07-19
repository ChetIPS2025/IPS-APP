"""Pricing Guide — unified master estimating database (``pricing_guide_items``)."""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

import streamlit as st

from app.components.headers import render_page_brand_header
from app.components.labor_rates_panel import render_labor_rates_panel
from app.components.pricing_guide_actions import render_pricing_guide_action_buttons
from app.components.pricing_guide_detail_tabs import (
    render_pricing_guide_detail_tabs,
    reset_pricing_guide_detail_tab,
    set_pricing_guide_detail_tab_from_query,
)
from app.components.pricing_guide_edit_form import render_new_pricing_item_dialog, render_pricing_guide_edit_form
from app.components.pricing_guide_import_panel import render_pricing_guide_import_panel
from app.components.pricing_guide_links_panel import render_pricing_guide_links_panel
from app.components.pricing_guide_list_table import build_pricing_guide_html_table
from app.components.pricing_guide_page_layout import (
    close_pricing_guide_filter_bar_shell,
    inject_pricing_guide_page_layout_css,
    render_pricing_guide_filter_bar_shell,
)
from app.components.layout import render_filter_bar as layout_filter_bar
from app.components.record_modal import (
    clear_edit_modes,
    clear_record_modal,
    get_modal_record,
    is_edit_mode,
    open_record_modal,
    record_session_key,
    render_missing_record,
    render_modal_edit_button,
    render_modal_header,
    render_modal_meta_grid,
    render_modal_shell,
)
from app.components.table_filters import clear_table_filters, render_table_header_cell, sanitize_column_filters
from app.components.table_pagination import (
    render_table_pagination_footer,
    render_table_pagination_header,
    reset_table_page,
)
from app.components.tabs import render_tabs
from app.pages._core._session import select_key
from app.services.pricing_guide_detail_service import (
    get_pricing_guide_item_detail,
    put_pricing_guide_in_modal_cache,
)
from app.services.pricing_guide_directory_service import list_pricing_guide_page
from app.services.pricing_guide_images import get_pricing_guide_image_url
from app.services.pricing_guide_service import normalize_pricing_row, pricing_guide_fetch_status, save_pricing_item
from app.styles import inject_pricing_guide_module_css
from app.ui.streamlit_perf import fragment, fragment_rerun
from app.utils.formatting import fmt_currency

_SEL = select_key("pricing_guide")
_MODULE = "pricing_guide"
_TABLE_KEY = "pg_list"
_MODAL_KEY = "ips_pg_detail_modal_id"
_CACHE_KEY = "_ips_pg_modal_by_id"
SELECTED_PG_KEY = "selected_pricing_guide_id"
SHOW_PG_MODAL_KEY = "show_pricing_guide_detail_modal"
_PRICING_DETAIL_QUERY_KEY = "pricing_detail"
_PRICING_DETAIL_TAB_QUERY_KEY = "pricing_tab"
_PRICING_DETAIL_QUERY_ERROR_KEY = "_ips_pg_detail_query_error"
_PG_FILTER_SPECS: list[tuple[str, str]] = [
    ("CLASS", "item_class"),
    ("CATEGORY", "category"),
    ("VENDOR", "vendor"),
    ("STATUS", "status"),
]
_FILTER_FIELDS = ["item_class", "category", "vendor", "status"]


@dataclass(frozen=True)
class PricingGuidePermissions:
    role: str
    user_id: str
    user_name: str
    can_manage: bool
    can_edit: bool
    can_delete: bool
    can_import: bool
    can_manage_stock_policy: bool


def _pricing_permissions() -> PricingGuidePermissions:
    role = str(st.session_state.get("role") or st.session_state.get("user_role") or "").strip().lower()
    if not role:
        try:
            from app.auth import effective_role

            role = str(effective_role() or "").strip().lower()
        except Exception:
            role = ""
    user = st.session_state.get("user") if isinstance(st.session_state.get("user"), dict) else {}
    user_id = str(user.get("id") or st.session_state.get("user_id") or "").strip()
    user_name = str(user.get("name") or st.session_state.get("user_name") or "").strip()
    can_manage = role in {"admin", "supervisor", "manager"}
    return PricingGuidePermissions(
        role=role,
        user_id=user_id,
        user_name=user_name,
        can_manage=can_manage,
        can_edit=can_manage,
        can_delete=can_manage,
        can_import=can_manage,
        can_manage_stock_policy=can_manage,
    )


def _normalize_row(raw: dict[str, Any]) -> dict[str, Any]:
    return normalize_pricing_row(raw)


def _persist_row(data: dict[str, Any], row_id: str | None = None) -> tuple[bool, str]:
    return save_pricing_item(data, row_id=row_id)


def _render_catalog_status_banner(warning: str | None, *, fetch_failed: bool = False) -> None:
    if not warning:
        status = pricing_guide_fetch_status()
        if not status or not status.warning:
            return
        warning = status.warning
        fetch_failed = bool(status.fetch_failed)
    if fetch_failed:
        st.error(warning)
    else:
        st.warning(warning)


def _render_summary_cards(summary: dict[str, Any]) -> None:
    from app.perf_debug import perf_span

    with perf_span("pricing_guide.summary"):
        cards = [
            ("Active Items", str(summary.get("active_count", 0))),
            ("Inventory Class", str(summary.get("inventory_class", 0))),
            ("Asset Class", str(summary.get("asset_class", 0))),
            ("Non-Inventory", str(summary.get("non_inventory_class", 0))),
            ("Stock Linked", str(summary.get("inventory_linked", 0))),
            ("Asset Linked", str(summary.get("asset_linked", 0))),
            ("Avg Markup", f"{float(summary.get('avg_markup') or 0):.1f}%"),
        ]
        html_cards = "".join(
            f'<div class="ips-pg-summary-card"><div class="lbl">{html.escape(lbl)}</div>'
            f'<div class="val">{html.escape(val)}</div></div>'
            for lbl, val in cards
        )
        st.markdown(f'<div class="ips-pg-summary-grid">{html_cards}</div>', unsafe_allow_html=True)


def _clear_modal() -> None:
    _clear_pg_selection()
    clear_edit_modes(_MODULE)
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )
    if _PRICING_DETAIL_QUERY_KEY in st.query_params:
        del st.query_params[_PRICING_DETAIL_QUERY_KEY]
    if _PRICING_DETAIL_TAB_QUERY_KEY in st.query_params:
        del st.query_params[_PRICING_DETAIL_TAB_QUERY_KEY]


def _open_modal(row_id: str, row: dict | None = None) -> None:
    rid = str(row_id or "").strip()
    if not rid:
        return
    st.session_state[SELECTED_PG_KEY] = rid
    st.session_state[SHOW_PG_MODAL_KEY] = True
    open_record_modal(
        rid,
        row,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
        id_fields=("id",),
    )


def _clear_pg_selection() -> None:
    st.session_state[SELECTED_PG_KEY] = None
    st.session_state[SHOW_PG_MODAL_KEY] = False


def _pg_detail_pending() -> bool:
    return bool(
        st.session_state.get(SHOW_PG_MODAL_KEY)
        or str(st.session_state.get(_MODAL_KEY) or "").strip()
    )


def _capture_pricing_detail_query() -> None:
    from app.perf_debug import perf_span

    with perf_span("pricing_guide.detail_lookup"):
        requested_id = str(st.query_params.get(_PRICING_DETAIL_QUERY_KEY) or "").strip()
        if not requested_id:
            return
        current_modal_id = str(st.session_state.get(_MODAL_KEY) or "").strip()
        if requested_id == current_modal_id and st.session_state.get(SHOW_PG_MODAL_KEY):
            tab_focus = str(st.query_params.get(_PRICING_DETAIL_TAB_QUERY_KEY) or "").strip()
            if tab_focus:
                set_pricing_guide_detail_tab_from_query(tab_focus)
            return
        row = get_pricing_guide_item_detail(requested_id)
        if not row:
            st.session_state[_PRICING_DETAIL_QUERY_ERROR_KEY] = requested_id
            if _PRICING_DETAIL_QUERY_KEY in st.query_params:
                del st.query_params[_PRICING_DETAIL_QUERY_KEY]
            if _PRICING_DETAIL_TAB_QUERY_KEY in st.query_params:
                del st.query_params[_PRICING_DETAIL_TAB_QUERY_KEY]
            return
        tab_focus = str(st.query_params.get(_PRICING_DETAIL_TAB_QUERY_KEY) or "").strip()
        _open_modal(requested_id, row)
        reset_pricing_guide_detail_tab(default="Overview")
        if tab_focus:
            set_pricing_guide_detail_tab_from_query(tab_focus)


def _show_pricing_detail_query_error_if_any() -> None:
    if st.session_state.pop(_PRICING_DETAIL_QUERY_ERROR_KEY, None):
        st.warning("The selected Pricing Guide item could not be found.")


def _render_pricing_guide_table_column_filters(*, filter_options: dict[str, list[str]]) -> None:
    if not _PG_FILTER_SPECS:
        return
    st.markdown('<div class="ips-pg-table-filter-toolbar">', unsafe_allow_html=True)
    cols = st.columns(len(_PG_FILTER_SPECS), gap="small")
    for col, (label, field) in zip(cols, _PG_FILTER_SPECS):
        with col:
            render_table_header_cell(
                label,
                table_key=_TABLE_KEY,
                filter_field=field,
                filter_options=filter_options.get(field, []),
                base_class="ips-pg-filter-toolbar-cell",
            )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_custom_pricing_guide_table(
    page_rows: list[dict[str, Any]],
    *,
    filter_options: dict[str, list[str]],
) -> None:
    from app.perf_debug import perf_span

    if not page_rows:
        st.info("No pricing guide items match your filters.")
        return
    for row in page_rows:
        rid = str(row.get("id") or "").strip()
        if rid:
            put_pricing_guide_in_modal_cache(rid, row)
    with st.container(key="pricing_guide_table_wrap"):
        with perf_span("pricing_guide.table_html"):
            _render_pricing_guide_table_column_filters(filter_options=filter_options)
            st.markdown(build_pricing_guide_html_table(page_rows), unsafe_allow_html=True)


def _render_lazy_overview_photo(row: dict[str, Any], *, permissions: PricingGuidePermissions) -> None:
    rid = str(row.get("id") or "").strip()
    manage_key = f"ips_pg_manage_photo_{rid}"
    image_url = get_pricing_guide_image_url(row)
    if image_url:
        st.markdown(
            f'<img class="ips-pg-detail-image" src="{html.escape(image_url, quote=True)}" alt="" />',
            unsafe_allow_html=True,
        )
    else:
        st.caption("No photo on file.")
    if not permissions.can_manage:
        return
    if not st.session_state.get(manage_key):
        if st.button("Manage Photo", key=f"pg_manage_photo_btn_{rid}"):
            st.session_state[manage_key] = True
            fragment_rerun()
        return
    from app.components.pricing_guide_edit_form import render_pg_photo_manager

    with st.expander("Photo management", expanded=True):
        render_pg_photo_manager(
            row,
            cache_key=_CACHE_KEY,
            module=_MODULE,
            permissions=permissions,
            record_session_key_fn=record_session_key,
        )


def _render_pricing_actions_panel(row: dict[str, Any], *, permissions: PricingGuidePermissions) -> None:
    rk = record_session_key(row, "id")
    if is_edit_mode(_MODULE, rk):
        return
    render_pricing_guide_action_buttons(
        row,
        can_manage=permissions.can_manage,
        on_deactivate=_clear_modal,
        on_delete=_clear_modal,
    )


@st.dialog("Pricing Guide Item", width="large", on_dismiss=_clear_modal)
def _show_detail_modal() -> None:
    permissions = _pricing_permissions()
    row = get_modal_record(cache_key=_CACHE_KEY, modal_key=_MODAL_KEY, session_select_key=_SEL)
    if not row:
        render_missing_record(_clear_modal, close_key="pg_modal_missing_close")
        return
    row = _normalize_row(row)
    rk = record_session_key(row, "id")
    edit_mode = is_edit_mode(_MODULE, rk)
    render_modal_header(
        title=str(row.get("item") or "Pricing Item"),
        subtitle=str(row.get("item_code") or row.get("item_key") or ""),
        status=str(row.get("status") or ""),
    )
    if permissions.can_edit:
        render_modal_edit_button(module=_MODULE, record_key=rk)
    render_modal_meta_grid(
        [
            ("Class", row.get("item_class")),
            ("Estimate type", row.get("item_type")),
            ("Category", row.get("category")),
            ("Unit", row.get("unit")),
            ("Cost", fmt_currency(row.get("default_cost"))),
            ("Sell price", fmt_currency(row.get("customer_price"))),
        ]
    )
    render_modal_shell()
    if edit_mode:
        render_pricing_guide_edit_form(
            row,
            module=_MODULE,
            cache_key=_CACHE_KEY,
            permissions=permissions,
            record_session_key_fn=record_session_key,
            persist_fn=_persist_row,
        )
    else:
        _render_pricing_actions_panel(row, permissions=permissions)
        render_pricing_guide_detail_tabs(
            row,
            permissions=permissions,
            render_overview_photo_fn=_render_lazy_overview_photo,
            render_links_panel_fn=render_pricing_guide_links_panel,
        )


@fragment
def _render_pricing_guide_catalog_fragment(*, permissions: PricingGuidePermissions) -> None:
    """Pricing guide search, filters, summary, import, and catalog table — local reruns."""

    def _filters() -> None:
        c1, c2 = st.columns([5, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search description, class, category, vendor, SKU, model #…",
                key="pg_search",
                label_visibility="collapsed",
            )
        with c2:
            if st.button("Clear", key="pg_clear", use_container_width=True):
                clear_table_filters(_TABLE_KEY, _FILTER_FIELDS, extra_keys=["pg_search"])
                _clear_pg_selection()
                reset_table_page(_TABLE_KEY)
                fragment_rerun()

    render_pricing_guide_filter_bar_shell()
    layout_filter_bar(_filters)
    close_pricing_guide_filter_bar_shell()

    search = str(st.session_state.get("pg_search") or "").strip()
    pg_page = list_pricing_guide_page(search=search, table_key=_TABLE_KEY)
    if sanitize_column_filters(_TABLE_KEY, pg_page.filter_options, filter_fields=_FILTER_FIELDS):
        pg_page = list_pricing_guide_page(search=search, table_key=_TABLE_KEY)

    _render_summary_cards(pg_page.summary)
    render_pricing_guide_import_panel(can_import=permissions.can_import)

    with st.container():
        from app.perf_debug import perf_span

        with perf_span("pricing_guide.pagination"):
            render_table_pagination_header(pg_page.total_count, _TABLE_KEY, item_label="item")
            _render_custom_pricing_guide_table(pg_page.rows, filter_options=pg_page.filter_options)
            render_table_pagination_footer(pg_page.total_count, _TABLE_KEY)


def render() -> None:
    from app.pages._core._access import begin_module
    from app.perf_debug import perf_span

    if not begin_module("pricing_guide"):
        return

    with perf_span("pricing_guide.page_shell"):
        inject_pricing_guide_module_css()
        inject_pricing_guide_page_layout_css()
        st.markdown(
            '<span class="ips-pricing-guide-page ips-page-shell-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        permissions = _pricing_permissions()

        def _pg_new() -> None:
            if permissions.can_manage and st.button(
                "+ New Pricing Item",
                key="pg_add",
                type="primary",
                use_container_width=True,
            ):
                st.session_state["pg_new_dialog_open"] = True

        render_page_brand_header(
            "Pricing Guide",
            "Master estimating catalog: materials, asset rentals, default labor rates, travel, and estimate-only items.",
            actions=[_pg_new],
        )

        _capture_pricing_detail_query()
        _show_pricing_detail_query_error_if_any()

        if _pg_detail_pending():
            _show_detail_modal()
            return

        main_tab = render_tabs(
            ["Catalog", "Labor Rates"],
            session_key="pg_main_tab",
            default="Catalog",
        )

        if main_tab == "Labor Rates":
            with perf_span("pricing_guide.labor_rates"):
                render_labor_rates_panel(key_prefix="pg_labor", show_header=False)
            return

        _render_catalog_status_banner(None)
        _render_pricing_guide_catalog_fragment(permissions=permissions)

        if st.session_state.get("pg_new_dialog_open"):
            render_new_pricing_item_dialog(
                module=_MODULE,
                permissions=permissions,
                persist_fn=_persist_row,
            )

        if _pg_detail_pending():
            _show_detail_modal()
