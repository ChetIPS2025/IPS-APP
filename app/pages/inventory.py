from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.branding import render_header
    from app.confirm_delete import (
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
    from app.db import delete_rows_admin, fetch_by_match_admin, fetch_table_admin, insert_row_admin, update_rows_admin
    from app.ips_crud_list_styles import (
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )
    from app.table_actions import (
        TABLE_KEY_INVENTORY,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        set_selected_ids,
    )
except ImportError:
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from confirm_delete import (  # type: ignore
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
    from db import (  # type: ignore
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from ips_crud_list_styles import (  # type: ignore
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )
    from table_actions import (  # type: ignore
        TABLE_KEY_INVENTORY,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        set_selected_ids,
    )

_TABLE = "inventory_items"
_DELETE_CONFIRM_PREFIX = "inventory_delete"


def _money(v) -> str:
    try:
        if v is None or str(v).strip() == "":
            return "—"
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _clear_panel() -> None:
    st.session_state.pop("inventory_panel_mode", None)
    st.session_state.pop("inventory_panel_id", None)


def _render_inventory_action_bar(*, df_all: pd.DataFrame, visible_df: pd.DataFrame, can_edit: bool) -> None:
    """
    Materials-style bar (same sizing/spacing), extended with export/select-all/clear.

    Selection storage is handled by table_actions via TABLE_KEY_INVENTORY → selected_inventory_ids.
    """
    inject_ips_crud_list_styles()
    inject_table_action_styles()

    sel = get_selected_ids(TABLE_KEY_INVENTORY)
    n = len(sel)
    one = n == 1
    none = n == 0

    # Export data (selected rows from currently loaded table)
    exp_ok = bool(not df_all.empty and "id" in df_all.columns and n >= 1)
    csv_bytes = b""
    if exp_ok:
        sub = df_all[df_all["id"].astype(str).isin([str(x) for x in sel])]
        csv_bytes = sub.to_csv(index=False).encode("utf-8")

    vis_ids: list[str] = []
    if not visible_df.empty and "id" in visible_df.columns:
        vis_ids = visible_df["id"].astype(str).tolist()
    sel_set = {str(x) for x in sel}
    vis_set = set(vis_ids)
    all_visible_selected = bool(vis_set) and sel_set == vis_set

    with st.container(border=True):
        st.markdown('<div class="ips-crud-toolbar-root"></div>', unsafe_allow_html=True)
        left, b0, b1, b2, b3, b4, b5, b6 = st.columns([1.1, 1, 1, 1, 1, 1, 1, 1], gap="small")
        with left:
            st.markdown(
                f'<span class="ips-ta-summary"><span class="ips-ta-num">{n}</span> selected</span>',
                unsafe_allow_html=True,
            )
        with b0:
            if st.button(
                "Add Inventory Item",
                type="primary",
                use_container_width=True,
                disabled=not can_edit,
                key="inv_btn_add",
            ):
                st.session_state["inventory_panel_mode"] = "add"
                st.session_state["inventory_panel_id"] = None
                st.rerun()
        with b1:
            if st.button(
                "Edit",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or not one,
                key="inv_btn_edit",
            ):
                st.session_state["inventory_panel_mode"] = "edit"
                st.session_state["inventory_panel_id"] = str(sel[0])
                st.rerun()
        with b2:
            if st.button(
                "Deactivate",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or none,
                key="inv_btn_deactivate",
            ):
                st.session_state["_inv_do_deactivate"] = True
                st.rerun()
        with b3:
            if st.button(
                "Delete",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or none,
                key="inv_btn_delete",
            ):
                open_destructive_confirmation(_DELETE_CONFIRM_PREFIX)
                st.session_state["inventory_pending_delete_ids"] = [str(x) for x in sel]
                st.rerun()
        with b4:
            st.download_button(
                "Export Selected",
                data=csv_bytes,
                file_name="inventory_export.csv",
                mime="text/csv",
                use_container_width=True,
                disabled=not exp_ok,
                key="inv_btn_export",
            )
        with b5:
            if st.button(
                "Select All Visible",
                use_container_width=True,
                disabled=not vis_ids or all_visible_selected,
                key="inv_btn_sel_all",
            ):
                set_selected_ids(TABLE_KEY_INVENTORY, list(vis_ids))
                st.rerun()
        with b6:
            if st.button(
                "Clear selection",
                use_container_width=True,
                disabled=none,
                key="inv_btn_clear",
            ):
                clear_selected_ids(TABLE_KEY_INVENTORY)
                st.session_state.pop("inventory_pending_delete_ids", None)
                st.rerun()


def _render_add_panel() -> None:
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Add inventory item")

        name = st.text_input("Item Name", key="inv_add_name")
        c1, c2 = st.columns(2)
        category = c1.text_input("Category", key="inv_add_cat")
        unit = c2.text_input("Unit", value="EA", key="inv_add_unit")

        r1, r2, r3 = st.columns(3)
        qty = r1.number_input(
            "Quantity on Hand", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="inv_add_qty"
        )
        reorder = r2.number_input(
            "Reorder Point", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="inv_add_reorder"
        )
        unit_cost = r3.number_input(
            "Unit Cost",
            min_value=0.0,
            value=0.0,
            step=0.01,
            format="%.2f",
            key="inv_add_cost",
        )

        v1, v2 = st.columns(2)
        vendor = v1.text_input("Vendor", key="inv_add_vendor")
        storage_location = v2.text_input("Storage Location", key="inv_add_loc")

        notes = st.text_area("Notes", key="inv_add_notes", height=72)
        is_active = st.checkbox("Active", value=True, key="inv_add_active")

        u1, u2 = st.columns(2)
        with u1:
            if st.button("Save Inventory Item", type="primary", use_container_width=True, key="inv_add_save"):
                t = str(name or "").strip()
                if not t:
                    st.error("Item Name is required.")
                    st.stop()
                payload = {
                    "item_name": t,
                    "category": str(category or "").strip(),
                    "unit": str(unit or "").strip() or "EA",
                    "quantity_on_hand": float(qty or 0),
                    "reorder_point": float(reorder or 0),
                    "unit_cost": float(unit_cost) if float(unit_cost or 0) > 0 else None,
                    "vendor": str(vendor or "").strip(),
                    "storage_location": str(storage_location or "").strip(),
                    "notes": str(notes or "").strip(),
                    "is_active": bool(is_active),
                }
                try:
                    insert_row_admin(_TABLE, payload)
                except Exception as exc:
                    st.error(f"Could not save: {exc}")
                    st.stop()
                _clear_panel()
                st.success("Inventory item added.")
                st.rerun()
        with u2:
            if st.button("Cancel", use_container_width=True, key="inv_add_cancel"):
                _clear_panel()
                st.rerun()


def _render_edit_panel(row: dict) -> None:
    inject_ips_crud_list_styles()
    rid = str(row.get("id") or "")
    pk = f"inv_ed_{rid}"
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Edit inventory item")
        st.caption(f"ID `{rid[:8]}…`")

        name = st.text_input("Item Name", value=str(row.get("item_name") or ""), key=f"{pk}_name")
        c1, c2 = st.columns(2)
        category = c1.text_input("Category", value=str(row.get("category") or ""), key=f"{pk}_cat")
        unit = c2.text_input("Unit", value=str(row.get("unit") or "EA"), key=f"{pk}_unit")

        r1, r2, r3 = st.columns(3)
        qty = r1.number_input(
            "Quantity on Hand",
            min_value=0.0,
            value=float(row.get("quantity_on_hand") or 0),
            step=1.0,
            format="%.2f",
            key=f"{pk}_qty",
        )
        reorder = r2.number_input(
            "Reorder Point",
            min_value=0.0,
            value=float(row.get("reorder_point") or 0),
            step=1.0,
            format="%.2f",
            key=f"{pk}_reorder",
        )
        uc_val = row.get("unit_cost")
        try:
            uc_default = float(uc_val) if uc_val is not None and str(uc_val).strip() != "" else 0.0
        except (TypeError, ValueError):
            uc_default = 0.0
        unit_cost = r3.number_input(
            "Unit Cost",
            min_value=0.0,
            value=uc_default,
            step=0.01,
            format="%.2f",
            key=f"{pk}_cost",
        )

        v1, v2 = st.columns(2)
        vendor = v1.text_input("Vendor", value=str(row.get("vendor") or ""), key=f"{pk}_vendor")
        storage_location = v2.text_input(
            "Storage Location", value=str(row.get("storage_location") or ""), key=f"{pk}_loc"
        )

        notes = st.text_area("Notes", value=str(row.get("notes") or ""), height=72, key=f"{pk}_notes")
        is_active = st.checkbox("Active", value=bool(row.get("is_active", True)), key=f"{pk}_active")

        u1, u2 = st.columns(2)
        with u1:
            if st.button("Update Inventory Item", type="primary", use_container_width=True, key=f"{pk}_save"):
                t = str(name or "").strip()
                if not t:
                    st.error("Item Name is required.")
                    st.stop()
                payload = {
                    "item_name": t,
                    "category": str(category or "").strip(),
                    "unit": str(unit or "").strip() or "EA",
                    "quantity_on_hand": float(qty or 0),
                    "reorder_point": float(reorder or 0),
                    "unit_cost": float(unit_cost) if float(unit_cost or 0) > 0 else None,
                    "vendor": str(vendor or "").strip(),
                    "storage_location": str(storage_location or "").strip(),
                    "notes": str(notes or "").strip(),
                    "is_active": bool(is_active),
                }
                try:
                    update_rows_admin(_TABLE, payload, {"id": row["id"]})
                except Exception as exc:
                    st.error(f"Could not update: {exc}")
                    st.stop()
                _clear_panel()
                st.success("Inventory item updated.")
                st.rerun()
        with u2:
            if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
                _clear_panel()
                st.rerun()


def render() -> None:
    render_header("Inventory")
    render_crud_list_subtitle(
        "Stocked supplies and consumables — managed separately from individually tracked assets."
    )

    can_edit = current_role() == "admin"

    # Ensure required session keys exist (explicitly requested by spec)
    st.session_state.setdefault("inventory_panel_mode", None)
    st.session_state.setdefault("inventory_panel_id", None)

    try:
        rows = fetch_table_admin(_TABLE, limit=5000, order_by="item_name")
    except Exception:
        st.warning(
            "Inventory table is not available yet. Run migration **`sql/015_inventory_items.sql`** "
            "in the Supabase SQL editor, then refresh."
        )
        return

    df = pd.DataFrame(rows)

    # --- Delete confirmation (matches Materials pattern) ---
    _del_open = destructive_confirm_open_key(_DELETE_CONFIRM_PREFIX)
    if st.session_state.get(_del_open) and not can_edit:
        close_destructive_confirmation(_DELETE_CONFIRM_PREFIX)
        st.session_state.pop("inventory_pending_delete_ids", None)
    elif st.session_state.get(_del_open) and can_edit:
        pending = list(st.session_state.get("inventory_pending_delete_ids") or [])
        if not pending:
            close_destructive_confirmation(_DELETE_CONFIRM_PREFIX)
            st.session_state.pop("inventory_pending_delete_ids", None)
            st.rerun()

        id_to_label: dict[str, str] = {}
        for r in rows:
            rid = str(r.get("id"))
            id_to_label[rid] = str(r.get("item_name") or "").strip() or rid
        name_lines = [id_to_label.get(pid, pid[:10] + "…") for pid in pending]
        n_pending = len(pending)
        msg = (
            "Are you sure you want to delete this inventory item?"
            if n_pending == 1
            else f"Are you sure you want to delete these {n_pending} inventory items?"
        )

        def _on_confirm_delete() -> None:
            for iid in pending:
                try:
                    delete_rows_admin(_TABLE, {"id": iid})
                except Exception as exc:
                    st.error(f"Could not delete {iid}: {exc}")
            st.session_state.pop("inventory_pending_delete_ids", None)
            clear_selected_ids(TABLE_KEY_INVENTORY)
            pid = st.session_state.get("inventory_panel_id")
            if pid and str(pid) in {str(x) for x in pending}:
                _clear_panel()
            st.success("Inventory item(s) deleted where permitted.")

        def _on_cancel_delete() -> None:
            st.session_state.pop("inventory_pending_delete_ids", None)

        render_destructive_confirmation(
            key_prefix=_DELETE_CONFIRM_PREFIX,
            title="Confirm Delete",
            message=msg,
            confirm_label="Confirm Delete",
            cancel_label="Cancel",
            on_confirm=_on_confirm_delete,
            on_cancel=_on_cancel_delete,
            name_lines=name_lines,
        )

    # --- Deactivate (matches Materials pattern) ---
    if st.session_state.pop("_inv_do_deactivate", False) and can_edit:
        sel_ids = get_selected_ids(TABLE_KEY_INVENTORY)
        if sel_ids:
            for iid in sel_ids:
                try:
                    update_rows_admin(_TABLE, {"is_active": False}, {"id": iid})
                except Exception as exc:
                    st.error(f"Could not deactivate {iid}: {exc}")
            clear_selected_ids(TABLE_KEY_INVENTORY)
            _clear_panel()
            st.success("Selected inventory items deactivated.")
            st.rerun()

    # --- Panel routing ---
    panel_mode = st.session_state.get("inventory_panel_mode")
    panel_id = st.session_state.get("inventory_panel_id")

    if panel_mode in ("add", "edit", "view") and not can_edit:
        _clear_panel()
        panel_mode = None
        panel_id = None

    panel_row: dict | None = None
    if panel_mode in ("edit", "view") and panel_id:
        pr = fetch_by_match_admin(_TABLE, {"id": panel_id}, limit=1)
        panel_row = pr[0] if pr else None
        if not panel_row:
            _clear_panel()
            panel_mode = None
            panel_id = None

    panel_open = bool(
        (panel_mode == "add" and can_edit)
        or (panel_mode in ("edit", "view") and panel_row is not None)
    )

    # --- Main list (Materials layout) ---
    def _render_main() -> None:
        inject_table_action_styles()

        st.caption("Checkbox column on the **left**; selection is stored as **selected_inventory_ids**.")

        if df.empty:
            st.info("No inventory items found.")
            if can_edit and st.button("Add Inventory Item", type="primary", key="inv_empty_add"):
                st.session_state["inventory_panel_mode"] = "add"
                st.session_state["inventory_panel_id"] = None
                st.rerun()
            return

        filter_cols = st.columns([1, 2, 1])
        categories = sorted(
            [
                c
                for c in df.get("category", pd.Series(dtype=str))
                .dropna()
                .astype(str)
                .unique()
                .tolist()
                if c.strip()
            ]
        )
        filter_cols[0].selectbox("Filter Category", ["All"] + categories, key="inv_f_cat")
        filter_cols[1].text_input(
            "Search Inventory",
            placeholder="Search item name, category, vendor, location, notes",
            key="inv_f_search",
        )
        active_options = ["All", "Active Only", "Inactive Only"]
        filter_cols[2].selectbox("Status", active_options, key="inv_f_active")

        selected_category = st.session_state.get("inv_f_cat", "All")
        search = st.session_state.get("inv_f_search", "")
        selected_active = st.session_state.get("inv_f_active", "All")

        filtered = df.copy()
        if selected_category != "All" and "category" in filtered.columns:
            filtered = filtered[filtered["category"].astype(str) == selected_category]
        if selected_active == "Active Only" and "is_active" in filtered.columns:
            filtered = filtered[filtered["is_active"] == True]  # noqa: E712
        elif selected_active == "Inactive Only" and "is_active" in filtered.columns:
            filtered = filtered[filtered["is_active"] == False]  # noqa: E712
        if search.strip():
            s = search.strip().lower()
            mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
            filtered = filtered[mask.any(axis=1)]

        show_cols = [
            c
            for c in [
                "item_name",
                "category",
                "unit",
                "quantity_on_hand",
                "reorder_point",
                "unit_cost",
                "vendor",
                "storage_location",
                "is_active",
            ]
            if c in filtered.columns
        ]

        if filtered.empty:
            st.warning("No inventory items match your filters.")
            if can_edit and st.button("Add Inventory Item", type="primary", key="inv_filtered_empty_add"):
                st.session_state["inventory_panel_mode"] = "add"
                st.session_state["inventory_panel_id"] = None
                st.rerun()
            return

        # Display formatting (mirrors Materials-style minimal formatting)
        display_df = filtered.copy()
        if "unit_cost" in display_df.columns:
            display_df["unit_cost"] = display_df["unit_cost"].apply(_money)

        bar_ph = st.empty()
        _, _sel = render_selectable_dataframe(
            display_df,
            table_key=TABLE_KEY_INVENTORY,
            id_column="id",
            columns=show_cols,
            editor_key="inv_sel_editor",
        )
        with bar_ph.container():
            _render_inventory_action_bar(df_all=df, visible_df=filtered, can_edit=can_edit)

    if panel_open:
        main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
        with main_col:
            _render_main()
        with side_col:
            if panel_mode == "add":
                _render_add_panel()
            elif panel_mode == "edit" and panel_row:
                _render_edit_panel(panel_row)
            elif panel_mode == "view" and panel_row:
                _render_edit_panel(panel_row)
    else:
        _render_main()
