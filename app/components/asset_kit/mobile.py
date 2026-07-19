"""Mobile kit scan card — optimized tool list and missing reports."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.components.action_styles import danger_outline
from app.components.asset_kit.audit import render_audit_form
from app.components.asset_kit.state import (
    KIT_ITEMS_DEFAULT_PAGE_SIZE,
    kit_item_select_label,
    load_kit_page_data,
)
from app.components.asset_kit.styles import inject_kit_ui_styles, kit_badge_html, kit_item_status_pill_html
from app.components.table_pagination import (
    page_size_key,
    paginate_rows,
    render_table_pagination_footer,
    render_table_pagination_header,
)
from app.services.asset_kits_service import update_asset_kit_item
from app.ui.streamlit_perf import ips_app_rerun
from app.utils.formatting import fmt_currency

_MOBILE_TABLE_KEY = "kit_mobile_tools"


def render_mobile_kit_scan(asset: dict) -> None:
    """Kit-specific mobile QR card actions and compact tool list."""
    inject_kit_ui_styles()
    aid = str(asset.get("id") or "")
    from app.perf_debug import perf_span

    with perf_span("asset_kit.mobile"):
        page_data = load_kit_page_data(asset)
    items = page_data.items
    summary = page_data.summary
    view = str(st.session_state.get("_kit_scan_view") or "card")

    st.markdown(
        f'<div class="ips-asset-scan-title">{html.escape(str(asset.get("asset_name") or "—"))}</div>'
        f"{kit_badge_html()} "
        f"{kit_item_status_pill_html(str(asset.get('kit_status') or 'Active'))}",
        unsafe_allow_html=True,
    )
    st.caption(
        f"Supervisor: **{summary.get('assigned_supervisor')}** · "
        f"Items: {summary.get('present_items')}/{summary.get('expected_items')} present · "
        f"Value: {fmt_currency(summary.get('total_kit_value'))}"
    )

    if view == "audit":
        render_audit_form(asset, aid, items)
        return
    if view == "tools":
        st.markdown("#### Tool List")
        if page_size_key(_MOBILE_TABLE_KEY) not in st.session_state:
            st.session_state[page_size_key(_MOBILE_TABLE_KEY)] = KIT_ITEMS_DEFAULT_PAGE_SIZE
        render_table_pagination_header(len(items), _MOBILE_TABLE_KEY, item_label="tool")
        page_rows, _, _, _ = paginate_rows(
            items,
            _MOBILE_TABLE_KEY,
            default_page_size=KIT_ITEMS_DEFAULT_PAGE_SIZE,
        )
        for it in page_rows:
            serial = str(it.get("serial_number") or "").strip()
            sn = f" · S/N {html.escape(serial)}" if serial else ""
            st.markdown(
                f"**{html.escape(kit_item_select_label(it, items))}**{sn} · "
                f"Exp {it.get('quantity_expected')} / Act {it.get('quantity_actual')} · "
                f"{kit_item_status_pill_html(str(it.get('status') or ''))}",
                unsafe_allow_html=True,
            )
        render_table_pagination_footer(len(items), _MOBILE_TABLE_KEY, item_label="tool")
        if st.button("← Back", key="kit_scan_back_tools"):
            st.session_state["_kit_scan_view"] = "card"
            st.rerun()
        return
    if view == "missing":
        st.markdown("#### Report Missing Tool")
        if not items:
            st.caption("No kit items.")
        else:
            options = [(kit_item_select_label(it, items), str(it.get("id") or "")) for it in items]
            labels = [lbl for lbl, _ in options]
            id_by_label = {lbl: iid for lbl, iid in options}
            pick = st.selectbox("Tool", labels, key="kit_scan_missing_pick")
            note = st.text_area("Notes", key="kit_scan_missing_note")
            with danger_outline("kit_scan_mark_missing"):
                if st.button("Mark Missing", type="secondary", key="kit_scan_mark_missing"):
                    item_id = id_by_label.get(pick, "")
                    if item_id:
                        update_asset_kit_item(
                            item_id,
                            {
                                "status": "Missing",
                                "condition": "Missing",
                                "notes": note,
                            },
                        )
                        st.success("Marked missing.")
                        st.session_state["_kit_scan_view"] = "card"
                        ips_app_rerun()
        if st.button("← Back", key="kit_scan_back_missing"):
            st.session_state["_kit_scan_view"] = "card"
            st.rerun()
        return

    if st.button("Start Trailer Audit", type="primary", use_container_width=True, key="kit_scan_audit"):
        st.session_state["_kit_scan_view"] = "audit"
        st.rerun()
    if st.button("View Tool List", use_container_width=True, key="kit_scan_tools"):
        st.session_state["_kit_scan_view"] = "tools"
        st.rerun()
    with danger_outline("kit_scan_report_missing"):
        if st.button("Report Missing Tool", use_container_width=True, key="kit_scan_missing"):
            st.session_state["_kit_scan_view"] = "missing"
            st.rerun()

    st.markdown("---")
    st.markdown("#### Tools in Kit")
    preview = items[:10]
    for it in preview:
        cols = st.columns([3, 1, 1])
        with cols[0]:
            st.markdown(f"**{html.escape(kit_item_select_label(it, items))}**")
        with cols[1]:
            st.caption(f"{it.get('quantity_actual')}/{it.get('quantity_expected')}")
        with cols[2]:
            st.markdown(kit_item_status_pill_html(str(it.get("status") or "")), unsafe_allow_html=True)
    if len(items) > len(preview):
        st.caption(f"Showing {len(preview)} of {len(items)} — open Tool List for more.")
