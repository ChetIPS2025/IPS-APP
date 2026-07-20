"""Main Kit / Contents tab fragment renderer."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.asset_kit.assignment import render_assignment_section
from app.components.asset_kit.audit import render_audit_form, render_recent_audits_section
from app.components.asset_kit.exports import get_kit_export_bytes
from app.components.asset_kit.forms import (
    render_add_kit_item_form,
    render_import_hand_tools_form,
    render_import_inventory_form,
    render_link_asset_form,
)
from app.components.asset_kit.item_detail import render_kit_item_detail_inline
from app.components.asset_kit.item_table import render_kit_items_table
from app.components.asset_kit.state import (
    KitPageData,
    apply_kit_item_query_param,
    kit_view,
    load_kit_page_data,
    selected_kit_item_id,
    sk,
)
from app.components.asset_kit.styles import inject_kit_ui_styles
from app.components.asset_kit.summary import render_kit_summary_cards
from app.services.asset_kits_service import KIT_TYPES, asset_is_kit, convert_asset_to_kit
from app.ui.streamlit_perf import fragment, fragment_rerun, ips_app_rerun


@fragment
def render_kit_contents_fragment(asset: dict) -> None:
    """Kit tab body — filters, pagination, and forms isolated for fragment reruns."""
    from app.perf_debug import perf_span

    inject_kit_ui_styles()
    aid = str(asset.get("id") or "").strip()
    if not aid:
        st.warning("Missing asset id.")
        return

    is_kit = asset_is_kit(asset)
    view = kit_view(aid)

    if not is_kit:
        st.info("This asset is not a kit.")
        kt = st.selectbox("Kit type", KIT_TYPES, key=sk(aid, "convert_type"))
        if st.button("Convert to Kit", type="primary", key=sk(aid, "convert_btn")):
            result = convert_asset_to_kit(aid, kt)
            if result.ok:
                st.success(f"Converted to kit ({kt}).")
                ips_app_rerun()
            else:
                st.error(result.error or "Could not convert.")
        return

    with perf_span("asset_kit.page_data"):
        page_data = load_kit_page_data(asset)
    items = page_data.items
    summary = page_data.summary

    invalid_kit_item = apply_kit_item_query_param(aid, items)
    if invalid_kit_item:
        st.warning("The selected kit item could not be found and was removed from the link.")

    render_kit_summary_cards(asset, summary)
    render_assignment_section(asset, aid)

    if view == "add":
        render_add_kit_item_form(asset, aid)
        return
    if view == "import":
        render_import_inventory_form(asset, aid)
        return
    if view == "import_hand":
        render_import_hand_tools_form(asset, aid)
        return
    if view == "link":
        render_link_asset_form(asset, aid)
        return
    if view == "audit":
        render_audit_form(asset, aid, items)
        return

    b1, b2, b3, b4, b5, b6, b7 = st.columns(7, gap="small")
    if b1.button("+ Add Kit Item", key=f"kit_btn_add_{aid}", use_container_width=True):
        st.session_state[sk(aid, "view")] = "add"
        fragment_rerun()
    if b2.button("Import Inventory", key=f"kit_btn_imp_{aid}", use_container_width=True):
        st.session_state[sk(aid, "view")] = "import"
        fragment_rerun()
    if b3.button("Import Small Tools", key=f"kit_btn_imp_hand_{aid}", use_container_width=True):
        st.session_state[sk(aid, "view")] = "import_hand"
        fragment_rerun()
    if b4.button("Link Asset", key=f"kit_btn_link_{aid}", use_container_width=True):
        st.session_state[sk(aid, "view")] = "link"
        fragment_rerun()
    if b5.button("Start Audit", key=f"kit_btn_audit_{aid}", use_container_width=True):
        st.session_state[sk(aid, "view")] = "audit"
        fragment_rerun()

    with st.spinner("Preparing exports..."):
        from app.perf_debug import perf_span as _span

        with _span("asset_kit.exports"):
            checklist = get_kit_export_bytes(asset, items, export_kind="checklist").decode("utf-8")
            csv_bytes = get_kit_export_bytes(asset, items, export_kind="csv")

    b6.download_button(
        "Print Checklist",
        checklist.encode("utf-8"),
        file_name=f"kit_checklist_{asset.get('asset_number') or aid}.txt",
        mime="text/plain",
        key=f"kit_btn_print_{aid}",
        use_container_width=True,
    )
    b7.download_button(
        "Export List",
        csv_bytes,
        file_name=f"kit_items_{asset.get('asset_number') or aid}.csv",
        mime="text/csv",
        key=f"kit_btn_export_{aid}",
        use_container_width=True,
    )

    st.markdown("##### Kit Items")
    if not items:
        st.caption(
            "No kit items yet. Add items, import from inventory or small hand tools, or link an existing asset."
        )
    else:
        sel_id = selected_kit_item_id(aid)
        if sel_id and st.session_state.get(sk(aid, "view")) == "detail":
            item = next((i for i in items if str(i.get("id")) == sel_id), None)
            if item:
                render_kit_item_detail_inline(asset, aid, item, items=items)
            else:
                st.session_state[sk(aid, "sel")] = ""
                st.session_state[sk(aid, "view")] = "list"
        else:
            render_kit_items_table(asset, aid, items, selected_item_id=sel_id)

    render_recent_audits_section(aid)


def render_kit_contents_tab(asset: dict) -> None:
    """Public entry — Kit / Contents tab body inside Asset Details."""
    render_kit_contents_fragment(asset)
