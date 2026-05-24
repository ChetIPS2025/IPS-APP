from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.ui.catalog_inventory_display import (
        drop_hidden_system_columns,
        order_display_columns,
        rename_display_headers,
    )
except ImportError:
    from ui.catalog_inventory_display import (  # type: ignore
        drop_hidden_system_columns,
        order_display_columns,
        rename_display_headers,
    )

try:
    from app.auth import current_role
    from app.ui.page_shell import render_page_header
    from app.db import (
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from app.table_actions import (
        TABLE_KEY_INVENTORY_SUPPLIES,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )
except ImportError:
    from auth import current_role  # type: ignore
    from ui.page_shell import render_page_header  # type: ignore
    from db import (  # type: ignore
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from table_actions import (  # type: ignore
        TABLE_KEY_INVENTORY_SUPPLIES,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )

try:
    from app.components.action_styles import danger_outline
    from app.confirm_delete import (
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
except ImportError:
    from components.action_styles import danger_outline  # type: ignore
    from confirm_delete import (  # type: ignore
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )

try:
    from app.ips_crud_list_styles import inject_ips_crud_list_styles
    from app.ui.modal import ensure_modal_styles, modal_wide_marker
except ImportError:
    from ips_crud_list_styles import inject_ips_crud_list_styles  # type: ignore
    from ui.modal import ensure_modal_styles, modal_wide_marker  # type: ignore

_TABLE = "inventory_items"
_INV_DELETE_PREFIX = "inventory_supplies_delete"


def _money(v) -> str:
    try:
        if v is None or str(v).strip() == "":
            return "—"
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _clear_inventory_panel() -> None:
    st.session_state.pop("inv_panel_mode", None)
    st.session_state.pop("inv_panel_id", None)


def _inv_supplies_add_on_dismiss() -> None:
    _clear_inventory_panel()


def _inv_supplies_edit_on_dismiss() -> None:
    _clear_inventory_panel()


@st.dialog("Add inventory item", width="large", on_dismiss=_inv_supplies_add_on_dismiss)
def _inv_supplies_add_dialog() -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Add inventory item")
    with st.container(border=True):
        with st.form("inv_supplies_add_dlg_f", clear_on_submit=True):
            t1 = st.text_input("Item name", key="inv_add_name")
            c1, c2 = st.columns(2)
            category = c1.text_input("Category", key="inv_add_cat", placeholder="e.g. Fasteners, PPE, Office")
            unit = c2.text_input("Unit", value="EA", key="inv_add_unit")

            r1, r2, r3 = st.columns(3)
            qty = r1.number_input(
                "Quantity on hand", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="inv_add_qty"
            )
            reorder = r2.number_input(
                "Reorder point", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="inv_add_reorder"
            )
            unit_cost = r3.number_input(
                "Unit cost (optional)",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                key="inv_add_cost",
            )

            v1, v2 = st.columns(2)
            vendor = v1.text_input("Vendor", key="inv_add_vendor")
            location = v2.text_input("Storage location", key="inv_add_loc")

            notes = st.text_area("Notes", key="inv_add_notes", height=72)
            is_active = st.checkbox("Active", value=True, key="inv_add_active")
            submitted = st.form_submit_button("Create item", type="primary", use_container_width=True)

    if st.button("Cancel", type="secondary", use_container_width=True, key="inv_supplies_add_cancel_dlg"):
        _clear_inventory_panel()
        st.rerun()

    if submitted:
        name = str(t1 or "").strip()
        if not name:
            st.error("Item name is required.")
            return
        payload = {
            "item_name": name,
            "category": str(category or "").strip(),
            "unit": str(unit or "").strip() or "EA",
            "quantity_on_hand": float(qty or 0),
            "reorder_point": float(reorder or 0),
            "unit_cost": float(unit_cost) if float(unit_cost or 0) > 0 else None,
            "vendor": str(vendor or "").strip(),
            "storage_location": str(location or "").strip(),
            "notes": str(notes or "").strip(),
            "is_active": bool(is_active),
        }
        try:
            insert_row_admin(_TABLE, payload)
        except Exception as exc:
            st.error(f"Could not save: {exc}")
            return
        _clear_inventory_panel()
        st.success("Item added.")
        st.rerun()


@st.dialog("Edit inventory item", width="large", on_dismiss=_inv_supplies_edit_on_dismiss)
def _inv_supplies_edit_dialog(row: dict) -> None:
    ensure_modal_styles()
    modal_wide_marker()
    rid = str(row.get("id") or "")
    pk = f"inv_ed_{rid}"
    st.markdown("### Edit inventory item")
    st.caption(f"ID `{rid[:8]}…`")
    with st.container(border=True):
        with st.form(f"inv_supplies_edit_dlg_{rid}", clear_on_submit=False):
            t1 = st.text_input("Item name", value=str(row.get("item_name") or ""), key=f"{pk}_name")
            c1, c2 = st.columns(2)
            category = c1.text_input("Category", value=str(row.get("category") or ""), key=f"{pk}_cat")
            unit = c2.text_input("Unit", value=str(row.get("unit") or "EA"), key=f"{pk}_unit")

            r1, r2, r3 = st.columns(3)
            qty = r1.number_input(
                "Quantity on hand",
                min_value=0.0,
                value=float(row.get("quantity_on_hand") or 0),
                step=1.0,
                format="%.2f",
                key=f"{pk}_qty",
            )
            reorder = r2.number_input(
                "Reorder point",
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
                "Unit cost (optional)",
                min_value=0.0,
                value=uc_default,
                step=0.01,
                format="%.2f",
                key=f"{pk}_cost",
            )

            v1, v2 = st.columns(2)
            vendor = v1.text_input("Vendor", value=str(row.get("vendor") or ""), key=f"{pk}_vendor")
            location = v2.text_input("Storage location", value=str(row.get("storage_location") or ""), key=f"{pk}_loc")

            notes = st.text_area("Notes", value=str(row.get("notes") or ""), height=72, key=f"{pk}_notes")
            is_active = st.checkbox("Active", value=bool(row.get("is_active", True)), key=f"{pk}_active")
            submitted = st.form_submit_button("Save", type="primary", use_container_width=True)

    if st.button("Cancel", type="secondary", use_container_width=True, key=f"{pk}_cancel_dlg"):
        _clear_inventory_panel()
        st.rerun()

    if submitted:
        name = str(t1 or "").strip()
        if not name:
            st.error("Item name is required.")
            return
        payload = {
            "item_name": name,
            "category": str(category or "").strip(),
            "unit": str(unit or "").strip() or "EA",
            "quantity_on_hand": float(qty or 0),
            "reorder_point": float(reorder or 0),
            "unit_cost": float(unit_cost) if float(unit_cost or 0) > 0 else None,
            "vendor": str(vendor or "").strip(),
            "storage_location": str(location or "").strip(),
            "notes": str(notes or "").strip(),
            "is_active": bool(is_active),
        }
        try:
            update_rows_admin(_TABLE, payload, {"id": row["id"]})
        except Exception as exc:
            st.error(f"Could not update: {exc}")
            return
        _clear_inventory_panel()
        st.success("Item updated.")
        st.rerun()


def _row_is_low_stock(row: dict) -> bool:
    try:
        q = float(row.get("quantity_on_hand") or 0)
        r = float(row.get("reorder_point") or 0)
        return r > 0 and q <= r
    except (TypeError, ValueError):
        return False


def _render_action_buttons(*, sel: list[str], can_edit: bool) -> None:
    inject_ips_crud_list_styles()
    inject_table_action_styles()
    n = len(sel)
    one = n == 1
    none = n == 0

    with st.container(border=True):
        st.markdown('<div class="ips-crud-toolbar-root"></div>', unsafe_allow_html=True)
        left, b0, b1, b2, b3 = st.columns([1.1, 1, 1, 1, 1], gap="small")
        with left:
            st.markdown(
                f'<span class="ips-ta-summary"><span class="ips-ta-num">{n}</span> selected</span>',
                unsafe_allow_html=True,
            )
        with b0:
            if st.button(
                "Add Item",
                type="primary",
                use_container_width=True,
                disabled=not can_edit,
                key="inv_btn_add",
            ):
                st.session_state["inv_panel_mode"] = "add"
                st.session_state.pop("inv_panel_id", None)
                st.rerun()
        with b1:
            if st.button(
                "Edit",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or not one,
                key="inv_btn_edit",
            ):
                st.session_state["inv_panel_mode"] = "edit"
                st.session_state["inv_panel_id"] = str(sel[0])
                st.rerun()
        with b2:
            with danger_outline("inv_btn_deactivate"):
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
            with danger_outline("inv_btn_delete"):
                if st.button(
                    "Delete",
                    type="secondary",
                    use_container_width=True,
                    disabled=not can_edit or none,
                    key="inv_btn_delete",
                ):
                    open_destructive_confirmation(_INV_DELETE_PREFIX)
                    st.session_state["inv_pending_delete_ids"] = [str(x) for x in sel]
                    st.rerun()


def _prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "is_active" in out.columns and "status" not in out.columns:
        out["status"] = out["is_active"].map(lambda x: "Active" if bool(x) else "Inactive")
    out["alert"] = out.apply(lambda r: "⚠ Low" if _row_is_low_stock(r.to_dict()) else "", axis=1)
    if "unit_cost" in out.columns:
        out["unit_cost"] = out["unit_cost"].apply(_money)
    for col in ("quantity_on_hand", "reorder_point"):
        if col in out.columns:
            out[col] = out[col].apply(
                lambda x: f"{float(x or 0):,.2f}" if pd.notna(x) else "0.00",
            )
    return out


def _inventory_supplies_visible_df(df: pd.DataFrame) -> pd.DataFrame:
    """Drop system columns (keep ``id`` for selection), order and rename for display/editor."""
    if df.empty:
        return df
    vis = drop_hidden_system_columns(df, keep=frozenset({"id"}))
    vis = order_display_columns(vis)
    return rename_display_headers(vis)


def _render_inventory_main(*, df: pd.DataFrame, rows: list[dict], can_edit: bool) -> None:
    inject_table_action_styles()

    st.caption(
        "Checkbox column on the **left**; selection is stored as **selected_inventory_supplies_ids**."
    )

    if df.empty:
        st.info("No inventory items yet. Use **Add Item** to create stocked supplies.")
        if can_edit:
            inject_table_action_styles()
            if st.button("Add Item", type="primary", use_container_width=True, key="inv_empty_add"):
                st.session_state["inv_panel_mode"] = "add"
                st.session_state.pop("inv_panel_id", None)
                st.rerun()
        return

    filter_cols = st.columns([1, 2, 1, 1])
    categories = sorted(
        [
            c
            for c in df.get("category", pd.Series(dtype=str))
            .dropna()
            .astype(str)
            .unique()
            .tolist()
            if str(c).strip()
        ]
    )
    filter_cols[0].selectbox("Filter category", ["All"] + categories, key="inv_f_cat")
    filter_cols[1].text_input(
        "Search",
        placeholder="Search name, category, vendor, location, notes",
        key="inv_f_search",
    )
    active_options = ["All", "Active Only", "Inactive Only"]
    filter_cols[2].selectbox("Status", active_options, key="inv_f_active")
    filter_cols[3].selectbox(
        "Stock",
        ["All", "OK", "At or below reorder"],
        key="inv_f_stock",
        help="Low = quantity on hand is at or below reorder point (when reorder > 0).",
    )

    selected_category = st.session_state.get("inv_f_cat", "All")
    search = st.session_state.get("inv_f_search", "")
    selected_active = st.session_state.get("inv_f_active", "All")
    stock_filter = st.session_state.get("inv_f_stock", "All")

    filtered = df.copy()
    if selected_category != "All" and "category" in filtered.columns:
        filtered = filtered[filtered["category"].astype(str) == selected_category]
    if selected_active == "Active Only" and "is_active" in filtered.columns:
        filtered = filtered[filtered["is_active"] == True]  # noqa: E712
    elif selected_active == "Inactive Only" and "is_active" in filtered.columns:
        filtered = filtered[filtered["is_active"] == False]  # noqa: E712
    if stock_filter == "At or below reorder":
        mask = filtered.apply(
            lambda r: _row_is_low_stock(r.to_dict()),
            axis=1,
        )
        filtered = filtered[mask]
    elif stock_filter == "OK":
        mask = filtered.apply(
            lambda r: not _row_is_low_stock(r.to_dict()),
            axis=1,
        )
        filtered = filtered[mask]

    if search.strip():
        s = search.strip().lower()
        mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
        filtered = filtered[mask.any(axis=1)]

    if filtered.empty:
        st.warning("No items match your filters.")
        if can_edit:
            inject_table_action_styles()
            if st.button("Add Item", type="primary", use_container_width=True, key="inv_filtered_empty_add"):
                st.session_state["inv_panel_mode"] = "add"
                st.session_state.pop("inv_panel_id", None)
                st.rerun()
        return

    display_df = _inventory_supplies_visible_df(_prepare_display_df(filtered))

    if "id" not in filtered.columns:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        return

    bar_ph = st.empty()
    editor_cols = [c for c in display_df.columns if c != "id"]
    _, sel = render_selectable_dataframe(
        display_df,
        table_key=TABLE_KEY_INVENTORY_SUPPLIES,
        id_column="id",
        columns=editor_cols,
        editor_key="inv_sel_editor",
        hide_id_column=True,
    )
    with bar_ph.container():
        _render_action_buttons(sel=sel, can_edit=can_edit)


def render() -> None:
    render_page_header(
        "Inventory / Supplies",
        "Stocked consumables and supplies — separate from tracked assets.",
    )

    can_edit = current_role() == "admin"

    try:
        rows = fetch_table_admin(_TABLE, limit=5000, order_by="item_name")
    except Exception:
        st.warning(
            "Inventory table is not available yet. Run migration **`sql/015_inventory_items.sql`** "
            "in the Supabase SQL editor, then refresh."
        )
        return

    df = pd.DataFrame(rows)

    _del_open = destructive_confirm_open_key(_INV_DELETE_PREFIX)
    if st.session_state.get(_del_open) and not can_edit:
        close_destructive_confirmation(_INV_DELETE_PREFIX)
        st.session_state.pop("inv_pending_delete_ids", None)
    elif st.session_state.get(_del_open) and can_edit:
        pending = list(st.session_state.get("inv_pending_delete_ids") or [])
        if not pending:
            close_destructive_confirmation(_INV_DELETE_PREFIX)
            st.session_state.pop("inv_pending_delete_ids", None)
            st.rerun()

        id_to_label: dict[str, str] = {}
        for r in rows:
            rid = str(r.get("id"))
            id_to_label[rid] = str(r.get("item_name") or "").strip() or rid

        name_lines = [id_to_label.get(pid, pid[:10] + "…") for pid in pending]
        n_pending = len(pending)
        msg = (
            "Delete this inventory item? This cannot be undone."
            if n_pending == 1
            else f"Delete these {n_pending} inventory items? This cannot be undone."
        )

        def _on_confirm_delete() -> None:
            for iid in pending:
                try:
                    delete_rows_admin(_TABLE, {"id": iid})
                except Exception as exc:
                    st.error(f"Could not delete {iid}: {exc}")
            st.session_state.pop("inv_pending_delete_ids", None)
            clear_selected_ids(TABLE_KEY_INVENTORY_SUPPLIES)
            eid = st.session_state.get("inv_panel_id")
            if eid and str(eid) in {str(x) for x in pending}:
                _clear_inventory_panel()
            st.success("Deleted where permitted.")

        def _on_cancel_delete() -> None:
            st.session_state.pop("inv_pending_delete_ids", None)

        render_destructive_confirmation(
            key_prefix=_INV_DELETE_PREFIX,
            title="Confirm Delete",
            message=msg,
            confirm_label="Delete",
            cancel_label="Cancel",
            on_confirm=_on_confirm_delete,
            on_cancel=_on_cancel_delete,
            name_lines=name_lines,
        )

    if st.session_state.pop("_inv_do_deactivate", False) and can_edit:
        sel_ids = get_selected_ids(TABLE_KEY_INVENTORY_SUPPLIES)
        if sel_ids:
            for iid in sel_ids:
                try:
                    update_rows_admin(_TABLE, {"is_active": False}, {"id": iid})
                except Exception as exc:
                    st.error(f"Could not deactivate {iid}: {exc}")
            clear_selected_ids(TABLE_KEY_INVENTORY_SUPPLIES)
            _clear_inventory_panel()
            st.success("Selected items deactivated.")
            st.rerun()

    panel_mode = st.session_state.get("inv_panel_mode")
    panel_id = st.session_state.get("inv_panel_id")

    if panel_mode == "add" and not can_edit:
        _clear_inventory_panel()
        panel_mode = None
        panel_id = None
    if panel_mode == "edit" and not can_edit:
        _clear_inventory_panel()
        panel_mode = None
        panel_id = None

    panel_row: dict | None = None
    if panel_mode == "edit" and panel_id:
        pr = fetch_by_match_admin(_TABLE, {"id": panel_id}, limit=1)
        panel_row = pr[0] if pr else None
        if not panel_row:
            _clear_inventory_panel()
            panel_mode = None
            panel_id = None

    _render_inventory_main(df=df, rows=rows, can_edit=can_edit)

    if panel_mode == "add" and can_edit:
        _inv_supplies_add_dialog()
    elif panel_mode == "edit" and can_edit and panel_row is not None:
        _inv_supplies_edit_dialog(dict(panel_row))
