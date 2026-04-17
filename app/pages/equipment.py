from __future__ import annotations

# NOTE: This page is a filtered **Equipment** view over `assets` (category = Equipment).
# If equipment management is fully merged into Asset Database / Assets, the standalone
# "Equipment" nav entry could be removed in favor of deep links or filters.

import pandas as pd
import streamlit as st

try:
    from app.asset_responsive import inject_asset_workflow_mobile_css
    from app.auth import current_role
    from app.branding import render_header
    from app.ips_crud_list_styles import render_crud_list_subtitle
    from app.db import delete_rows_admin, fetch_table
    from app.pages.asset_database import (
        ASSET_TABLE_COLS,
        prepare_assets_dataframe,
        render_asset_database_card_list,
        _is_equipment_row_cat,
        _is_rental_row,
    )
    from app.ui import IPS_NAV_PENDING_KEY
except ImportError:
    from asset_responsive import inject_asset_workflow_mobile_css  # type: ignore
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from ips_crud_list_styles import render_crud_list_subtitle  # type: ignore
    from db import delete_rows_admin, fetch_table  # type: ignore
    from pages.asset_database import (  # type: ignore
        ASSET_TABLE_COLS,
        prepare_assets_dataframe,
        render_asset_database_card_list,
        _is_equipment_row_cat,
        _is_rental_row,
    )
    from ui import IPS_NAV_PENDING_KEY  # type: ignore

try:
    from app.table_actions import (
        IPS_PENDING_DELETE,
        TABLE_KEY_EQUIPMENT,
        clear_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        render_selection_action_bar,
    )
except ImportError:
    from table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_EQUIPMENT,
        clear_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        render_selection_action_bar,
    )


def render() -> None:
    """Filtered Asset Database view: ``category`` = Equipment only. Same card list as Asset Database."""
    inject_asset_workflow_mobile_css()
    render_header("Equipment")
    render_crud_list_subtitle(
        "Filtered Asset Database view (Equipment category only). Open a card for rental rates and details."
    )

    can_add = current_role() in {"admin", "estimator"}

    inject_table_action_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
        a1, a2, a3 = st.columns([1, 1, 2], gap="small")
        with a1:
            if st.button(
                "Add Equipment",
                type="primary",
                use_container_width=True,
                disabled=not can_add,
                key="eq_btn_add_equipment",
                help="Opens Asset Database in add mode with Category preset to Equipment.",
            ):
                st.session_state["asset_db_add_mode"] = True
                st.session_state["intake_category_default"] = "Equipment"
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Database"
                st.rerun()
        with a2:
            if st.button(
                "View All Assets",
                type="secondary",
                use_container_width=True,
                key="eq_btn_view_all_assets",
                help="Go to the full Asset Database.",
            ):
                st.session_state["asset_db_add_mode"] = False
                st.session_state[IPS_NAV_PENDING_KEY] = "Asset Database"
                st.rerun()
        with a3:
            st.caption("Same data as Asset Database — this page is the estimator-friendly equipment lens.")

    rows = fetch_table("assets", limit=5000, order_by="asset_name")
    df = prepare_assets_dataframe(rows)

    if df.empty:
        st.info("No assets found. Add assets from **Asset Database** or use **Add Equipment** above.")
        if not can_add:
            st.caption("Admin or estimator role required to add equipment.")
        return

    if "category" not in df.columns:
        st.warning("Assets are missing a **category** column; cannot filter Equipment.")
        return

    equipment_df = df[df["category"].map(_is_equipment_row_cat)].copy()

    if equipment_df.empty:
        st.info(
            'No equipment assets yet. Set **Category** to `Equipment` on an asset, or click **Add Equipment**.'
        )
        if not can_add:
            st.caption("Admin or estimator role required to add equipment.")
        return

    filter_cols = st.columns([1, 2, 1])
    statuses = sorted(
        [
            s
            for s in equipment_df.get("status", pd.Series(dtype=str))
            .dropna()
            .astype(str)
            .unique()
            .tolist()
            if str(s).strip()
        ]
    )
    selected_status = filter_cols[0].selectbox("Filter Status", ["All"] + statuses, key="eq_f_status")

    search = filter_cols[1].text_input(
        "Search equipment",
        placeholder="Asset id, name, manufacturer, model, serial, status",
        key="eq_f_search",
    )

    serial_options = ["All", "Has serial", "No serial"]
    selected_serial = filter_cols[2].selectbox("Serial #", serial_options, key="eq_f_serial")

    filter_rental = st.columns([1, 3])
    rental_scope = filter_rental[0].selectbox(
        "Show",
        ["All", "Rental only"],
        key="eq_f_rental",
        help="Rent to customer — same idea as Asset Database.",
    )
    filter_rental[1].caption("**Rental** badge = rent to customer. Rates are edited on the asset profile.")

    filtered = equipment_df.copy()

    if selected_status != "All" and "status" in filtered.columns:
        filtered = filtered[filtered["status"].astype(str) == selected_status]

    if selected_serial == "Has serial" and "serial_number" in filtered.columns:
        sn = filtered["serial_number"].astype(str).str.strip()
        filtered = filtered[sn.ne("") & sn.ne("nan") & filtered["serial_number"].notna()]
    elif selected_serial == "No serial" and "serial_number" in filtered.columns:
        sn = filtered["serial_number"].astype(str).str.strip()
        filtered = filtered[filtered["serial_number"].isna() | sn.eq("") | sn.eq("nan")]

    if rental_scope == "Rental only" and "is_rental" in filtered.columns:
        filtered = filtered[filtered["is_rental"].map(_is_rental_row)]

    if search.strip():
        s = search.strip().lower()
        search_cols = [c for c in ASSET_TABLE_COLS if c in filtered.columns]
        if search_cols:
            mask = filtered[search_cols].astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
            filtered = filtered[mask.any(axis=1)]

    if filtered.empty:
        st.warning("No equipment matches your filters.")
        return

    render_asset_database_card_list(
        filtered.to_dict("records"),
        key_prefix="eq_asset",
        show_category_in_caption=False,
    )

    st.subheader("Equipment table")
    st.caption(
        "Action bar above the grid. Checkbox on the **left**; selection: **selected_equipment_ids**."
    )
    table_cols = [
        c
        for c in [
            "asset_id",
            "asset_name",
            "manufacturer",
            "model",
            "serial_number",
            "status",
            "is_rental",
        ]
        if c in filtered.columns
    ]
    if "id" not in filtered.columns:
        st.dataframe(filtered[table_cols], use_container_width=True, hide_index=True)
    else:
        bar_placeholder = st.empty()
        _, sel = render_selectable_dataframe(
            filtered,
            table_key=TABLE_KEY_EQUIPMENT,
            id_column="id",
            columns=table_cols,
            editor_key="eq_sel_editor",
        )
        with bar_placeholder.container():
            actions = render_selection_action_bar(
                TABLE_KEY_EQUIPMENT,
                sel,
                can_view=True,
                can_edit=can_add,
                can_delete=can_add,
                export_df=filtered,
                visible_df=filtered,
                id_column="id",
                export_filename="equipment_export.csv",
                view_label="View Asset",
                edit_label="Edit Asset",
                delete_label="Delete Asset",
                delete_selected_label="Delete Selected",
            )
        if actions.get("view") and sel and len(sel) == 1:
            st.session_state["asset_detail_id"] = str(sel[0])
            st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
            st.rerun()
        if actions.get("edit") and sel and len(sel) == 1 and can_add:
            st.session_state["assets_view"] = "edit"
            st.session_state["asset_edit_id"] = str(sel[0])
            st.session_state.pop("asset_return_to", None)
            st.session_state[IPS_NAV_PENDING_KEY] = "Asset Manager"
            st.rerun()
        pend = st.session_state.get(IPS_PENDING_DELETE) or {}
        if actions.get("confirm_delete") and pend.get(TABLE_KEY_EQUIPMENT) and can_add:
            for aid in pend[TABLE_KEY_EQUIPMENT]:
                try:
                    delete_rows_admin("assets", {"id": aid})
                except Exception as exc:
                    st.error(f"Could not delete {aid}: {exc}")
            pend.pop(TABLE_KEY_EQUIPMENT, None)
            clear_selected_ids(TABLE_KEY_EQUIPMENT)
            st.success("Delete completed where permitted.")
            st.rerun()
