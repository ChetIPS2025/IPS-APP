from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.branding import render_header
    from app.db import delete_rows_admin, fetch_one, fetch_table, insert_row, update_rows_admin
    from app.table_actions import (
        TABLE_KEY_MATERIALS,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )
except ImportError:
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import delete_rows_admin, fetch_one, fetch_table, insert_row, update_rows_admin  # type: ignore
    from table_actions import (  # type: ignore
        TABLE_KEY_MATERIALS,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )

try:
    from app.pages.material_quote_import import render_material_quote_import_form
except ImportError:
    from pages.material_quote_import import render_material_quote_import_form  # type: ignore

try:
    from app.confirm_delete import (
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
except ImportError:
    from confirm_delete import (  # type: ignore
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )

try:
    from app.ips_crud_list_styles import (
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )
except ImportError:
    from ips_crud_list_styles import (  # type: ignore
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )

MARKUP_PCT = 0.25
_MAT_DELETE_CONFIRM_PREFIX = "materials_delete"

# Hidden from the main catalog grid only (still in DB, selection, add/edit, filters, and search).
_MATERIAL_LIST_HIDDEN_COLS: frozenset[str] = frozenset(
    {"id", "is_active", "inventory_id", "item_key", "stock_length", "subgroup"}
)


def next_inventory_id(rows) -> str:
    nums = []
    for r in rows:
        inv = str(r.get("inventory_id", "")).strip().upper()
        if inv.startswith("INV-"):
            try:
                nums.append(int(inv.replace("INV-", "")))
            except Exception:
                pass
    next_num = max(nums) + 1 if nums else 1
    return f"INV-{next_num:03d}"


def _money(v) -> str:
    try:
        return f"${float(v or 0):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _clear_material_panel() -> None:
    st.session_state.pop("material_panel_mode", None)
    st.session_state.pop("material_panel_id", None)


def _category_subgroup_options(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    if df.empty:
        return [], []
    category_options = sorted(
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
    subgroup_options = sorted(
        [
            s
            for s in df.get("subgroup", pd.Series(dtype=str))
            .dropna()
            .astype(str)
            .unique()
            .tolist()
            if s.strip()
        ]
    )
    return category_options, subgroup_options


def _visible_material_list_columns(filtered: pd.DataFrame) -> list[str]:
    """Columns shown in the main selectable grid — user-facing fields only; never id / is_active / internal keys."""
    preferred_order = [
        "description",
        "category",
        "unit",
        "purchase_price",
        "sell_price",
    ]
    out = [c for c in preferred_order if c in filtered.columns and c not in _MATERIAL_LIST_HIDDEN_COLS]
    return [c for c in out if c not in ("id", "is_active")]


def _render_material_filter_row(*, df: pd.DataFrame, can_import: bool) -> None:
    """Full-width filters (Customers-style) — keeps the split main column to list + caption only."""
    if df.empty:
        return
    f1, f2 = st.columns([2, 1], gap="small")
    with f1:
        st.markdown(
            '<span class="ips-crud-filter-row-start" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        st.text_input(
            "Search",
            placeholder="Description, category, unit, pricing (includes hidden fields)",
            key="mat_f_search",
        )
    active_options = ["All", "Active Only", "Inactive Only"]
    with f2:
        st.selectbox("Status", active_options, key="mat_f_active")

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
    if can_import:
        cat_row_l, cat_row_r = st.columns([2, 1], gap="small")
        with cat_row_l:
            st.selectbox("Category", ["All"] + categories, key="mat_f_cat")
        with cat_row_r:
            if st.button("Import quote", type="secondary", use_container_width=True, key="mat_imp_quote"):
                _clear_material_panel()
                st.session_state["materials_quote_import_mode"] = True
                st.rerun()
    else:
        st.selectbox("Category", ["All"] + categories, key="mat_f_cat")


def _filtered_materials_df(df: pd.DataFrame) -> pd.DataFrame:
    search = str(st.session_state.get("mat_f_search", "") or "")
    selected_category = st.session_state.get("mat_f_cat", "All")
    selected_active = st.session_state.get("mat_f_active", "All")

    filtered = df.copy()
    if selected_category != "All" and "category" in filtered.columns:
        filtered = filtered[filtered["category"].astype(str) == selected_category]
    if selected_active == "Active Only" and "is_active" in filtered.columns:
        filtered = filtered[filtered["is_active"] == True]  # noqa: E712
    elif selected_active == "Inactive Only" and "is_active" in filtered.columns:
        filtered = filtered[filtered["is_active"] == False]  # noqa: E712
    if search.strip():
        s = search.strip().lower()
        mask = filtered.astype(str).apply(
            lambda col: col.str.lower().str.contains(s, na=False, regex=False),
        )
        filtered = filtered[mask.any(axis=1)]
    return filtered


def _sync_selection_to_panel(sel: list[str]) -> None:
    """Single selection drives browse + edit target; multi/clear exits edit."""
    if len(sel) == 1:
        sid = str(sel[0])
        st.session_state["material_selected_id"] = sid
        mode = st.session_state.get("material_panel_mode")
        if mode == "edit":
            st.session_state["material_panel_id"] = sid
        elif mode != "add":
            st.session_state["material_panel_id"] = sid
        return

    st.session_state.pop("material_selected_id", None)
    mode = st.session_state.get("material_panel_mode")
    if mode == "edit":
        _clear_material_panel()
    elif mode != "add":
        st.session_state.pop("material_panel_id", None)


def _render_material_right_actions(*, sel: list[str], can_import: bool) -> None:
    inject_ips_crud_list_styles()
    inject_table_action_styles()
    n = len(sel)
    one = n == 1
    none = n == 0

    with st.container(border=True):
        st.markdown('<div class="ips-crud-toolbar-root"></div>', unsafe_allow_html=True)
        left, b0, b1, b2, b3 = st.columns([1.05, 1, 1, 1, 1], gap="small")
        with left:
            st.markdown(
                f'<span class="ips-ta-summary"><span class="ips-ta-num">{n}</span> selected</span>',
                unsafe_allow_html=True,
            )
        with b0:
            if st.button(
                "Add",
                type="primary",
                use_container_width=True,
                disabled=not can_import,
                key="mat_btn_add",
            ):
                st.session_state["material_panel_mode"] = "add"
                st.session_state.pop("material_panel_id", None)
                st.rerun()
        with b1:
            if st.button(
                "Edit",
                type="secondary",
                use_container_width=True,
                disabled=not can_import or not one,
                key="mat_btn_edit",
            ):
                st.session_state["material_panel_mode"] = "edit"
                st.session_state["material_panel_id"] = str(sel[0])
                st.session_state["material_selected_id"] = str(sel[0])
                st.rerun()
        with b2:
            if st.button(
                "Deactivate",
                type="secondary",
                use_container_width=True,
                disabled=not can_import or none,
                key="mat_btn_deactivate",
            ):
                st.session_state["_mat_do_deactivate"] = True
                st.rerun()
        with b3:
            if st.button(
                "Delete",
                type="secondary",
                use_container_width=True,
                disabled=not can_import or none,
                key="mat_btn_delete",
            ):
                open_destructive_confirmation(_MAT_DELETE_CONFIRM_PREFIX)
                st.session_state["materials_pending_delete_ids"] = [str(x) for x in sel]
                st.rerun()


def _render_material_compact_details(row: dict) -> None:
    """Read-only summary (visible catalog fields only — matches hidden-column policy in the grid)."""
    st.markdown(f"**{row.get('description') or '—'}**")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Category")
        st.markdown(str(row.get("category") or "—"))
        st.caption("Unit")
        st.markdown(str(row.get("unit") or "—"))
    with c2:
        st.caption("Purchase / Sell")
        st.markdown(f"{_money(row.get('purchase_price'))} → {_money(row.get('sell_price'))}")
        active = row.get("is_active")
        st.caption("Status")
        st.markdown("Active" if active else "Inactive")


def _render_material_add_form(*, df: pd.DataFrame, rows: list) -> None:
    category_options, subgroup_options = _category_subgroup_options(df)

    c1, c2 = st.columns(2, gap="small")
    inventory_id = c1.text_input("Inventory ID (blank = auto)", key="mat_add_inv")
    item_key = c2.text_input("Item Key (blank = auto)", key="mat_add_key")

    c3, c4 = st.columns(2, gap="small")
    description = c3.text_input("Description", key="mat_add_desc")
    category = c4.selectbox("Category", options=[""] + category_options, key="mat_add_cat")

    c5, c6, c7, c8 = st.columns(4, gap="small")
    subgroup = c5.selectbox("Subgroup", options=[""] + subgroup_options, key="mat_add_sub")
    unit = c6.text_input("Unit", value="EA", key="mat_add_unit")
    stock_length = c7.text_input("Stock Length", key="mat_add_slen")
    purchase_price = c8.number_input(
        "Purchase Price",
        min_value=0.0,
        step=1.0,
        format="%.2f",
        key="mat_add_purch",
    )

    auto_sell_price = round(float(purchase_price or 0) * (1 + MARKUP_PCT), 2)
    st.number_input(
        "Sell Price (25% markup auto)",
        min_value=0.0,
        value=auto_sell_price,
        step=1.0,
        format="%.2f",
        disabled=True,
        key="mat_add_sell",
    )

    is_active = st.checkbox("Active", value=True, key="mat_add_act")

    u1, u2 = st.columns(2, gap="small")
    with u1:
        if st.button("Save Material", type="primary", use_container_width=True, key="mat_add_save"):
            if not str(description).strip():
                st.error("Description required")
                st.stop()
            final_item_key = str(item_key).strip() or str(description).strip().upper().replace(" ", "_")
            final_inventory_id = str(inventory_id).strip() or next_inventory_id(rows)
            final_sell_price = round(float(purchase_price or 0) * (1 + MARKUP_PCT), 2)
            payload = {
                "inventory_id": final_inventory_id,
                "item_key": final_item_key,
                "description": str(description).strip(),
                "category": str(category).strip(),
                "subgroup": str(subgroup).strip(),
                "unit": str(unit).strip() or "EA",
                "stock_length": str(stock_length).strip() or None,
                "purchase_price": float(purchase_price or 0),
                "sell_price": final_sell_price,
                "is_active": bool(is_active),
            }
            insert_row("materials_catalog", payload)
            _clear_material_panel()
            st.success(f"Added {final_inventory_id}")
            st.rerun()
    with u2:
        if st.button("Cancel", use_container_width=True, key="mat_add_cancel"):
            _clear_material_panel()
            st.rerun()


def _render_material_edit_form(row: dict) -> None:
    rid = str(row.get("id") or "")

    def pk(s: str) -> str:
        return f"mat_p_{rid}_{s}"

    st.caption(f"ID `{rid[:8]}…`")

    c1, c2 = st.columns(2, gap="small")
    inventory_id = c1.text_input(
        "Inventory ID",
        value=str(row.get("inventory_id") or ""),
        key=pk("inv"),
    )
    item_key = c2.text_input(
        "Item Key",
        value=str(row.get("item_key") or ""),
        key=pk("ikey"),
    )
    c3, c4 = st.columns(2, gap="small")
    description = c3.text_input(
        "Description",
        value=str(row.get("description") or ""),
        key=pk("desc"),
    )
    category = c4.text_input(
        "Category",
        value=str(row.get("category") or ""),
        key=pk("cat"),
    )

    c5, c6, c7, c8 = st.columns(4, gap="small")
    subgroup = c5.text_input(
        "Subgroup",
        value=str(row.get("subgroup") or ""),
        key=pk("sub"),
    )
    unit = c6.text_input("Unit", value=str(row.get("unit") or "EA"), key=pk("unit"))
    stock_length = c7.text_input(
        "Stock Length",
        value=str(row.get("stock_length") or ""),
        key=pk("slen"),
    )
    purchase_price = c8.number_input(
        "Purchase Price",
        min_value=0.0,
        value=float(row.get("purchase_price") or 0),
        step=1.0,
        format="%.2f",
        key=pk("purch"),
    )

    auto_sell = round(float(purchase_price or 0) * (1 + MARKUP_PCT), 2)
    st.number_input(
        "Sell Price (25% markup)",
        min_value=0.0,
        value=auto_sell,
        step=1.0,
        format="%.2f",
        disabled=True,
        key=pk("sell_disp"),
    )

    is_active = st.checkbox(
        "Active",
        value=bool(row.get("is_active")),
        key=pk("active"),
    )

    u1, u2 = st.columns(2, gap="small")
    with u1:
        if st.button("Update Material", type="primary", use_container_width=True, key=pk("save")):
            if not str(description).strip():
                st.error("Description required")
            else:
                final_sell = round(float(purchase_price or 0) * (1 + MARKUP_PCT), 2)
                payload = {
                    "inventory_id": str(inventory_id).strip() or None,
                    "item_key": str(item_key).strip() or str(description).strip().upper().replace(" ", "_"),
                    "description": str(description).strip(),
                    "category": str(category).strip(),
                    "subgroup": str(subgroup).strip(),
                    "unit": str(unit).strip() or "EA",
                    "stock_length": str(stock_length).strip() or None,
                    "purchase_price": float(purchase_price or 0),
                    "sell_price": final_sell,
                    "is_active": bool(is_active),
                }
                try:
                    update_rows_admin("materials_catalog", payload, {"id": row["id"]})
                    _clear_material_panel()
                    st.success("Material updated.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not save: {exc}")
    with u2:
        if st.button("Cancel", use_container_width=True, key=pk("cancel")):
            _clear_material_panel()
            st.rerun()


def _render_material_right_panel(
    *,
    df: pd.DataFrame,
    rows: list,
    can_import: bool,
    panel_mode: str | None,
    panel_row: dict | None,
) -> None:
    inject_ips_crud_list_styles()
    sel = get_selected_ids(TABLE_KEY_MATERIALS)

    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Material")

        _render_material_right_actions(sel=sel, can_import=can_import)

        if panel_mode == "add" and can_import:
            st.markdown("#### New catalog row")
            _render_material_add_form(df=df, rows=rows)
            return

        if panel_mode == "edit" and panel_row and can_import:
            st.markdown("#### Edit")
            _render_material_edit_form(panel_row)
            return

        st.markdown("#### Details")
        sid = st.session_state.get("material_panel_id") or st.session_state.get("material_selected_id")
        browse_row: dict | None = None
        if sid:
            browse_row = fetch_one("materials_catalog", {"id": sid})
        if browse_row:
            _render_material_compact_details(browse_row)
        elif sid:
            st.warning("Material not found (it may have been deleted).")
        elif len(sel) > 1:
            st.caption("Select a single row to see details here.")
        else:
            st.caption("Select a material in the table to load details.")


def _render_materials_table_main(
    *,
    filtered: pd.DataFrame,
    df: pd.DataFrame,
    can_import: bool,
) -> None:
    """Left column: caption + table only (filters live above the page split)."""
    inject_table_action_styles()

    if df.empty:
        st.info("No materials found.")
        if st.session_state.get("material_panel_mode") not in ("add", "edit"):
            st.session_state.pop("material_panel_id", None)
            st.session_state.pop("material_selected_id", None)
        if can_import and st.button(
            "Add Material", type="primary", use_container_width=True, key="mat_empty_add"
        ):
            st.session_state["material_panel_mode"] = "add"
            st.session_state.pop("material_panel_id", None)
            st.rerun()
        return

    show_cols = _visible_material_list_columns(filtered)

    st.caption(
        "Checkbox column on the **left**; selection is stored as **selected_materials_ids**."
    )

    if filtered.empty:
        st.warning("No materials match your filters.")
        if st.session_state.get("material_panel_mode") not in ("add", "edit"):
            st.session_state.pop("material_panel_id", None)
            st.session_state.pop("material_selected_id", None)
        if can_import and st.button(
            "Add Material", type="primary", use_container_width=True, key="mat_filtered_empty_add"
        ):
            st.session_state["material_panel_mode"] = "add"
            st.session_state.pop("material_panel_id", None)
            st.rerun()
        return

    if "id" not in filtered.columns:
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)
        if st.session_state.get("material_panel_mode") not in ("add", "edit"):
            st.session_state.pop("material_panel_id", None)
            st.session_state.pop("material_selected_id", None)
        return

    _, sel = render_selectable_dataframe(
        filtered,
        table_key=TABLE_KEY_MATERIALS,
        id_column="id",
        columns=show_cols,
        editor_key="mat_sel_editor",
        hide_id_column=True,
    )
    _sync_selection_to_panel(sel)


def render() -> None:
    render_header("Materials Catalog")
    render_crud_list_subtitle(
        "Filter above, catalog grid on the left, details and actions on the right — same rhythm as Customers."
    )

    st.session_state.setdefault("materials_quote_import_mode", False)
    st.session_state.setdefault("material_panel_mode", None)
    st.session_state.setdefault("material_panel_id", None)

    can_import = current_role() == "admin"

    if st.session_state.pop("materials_show_add", False) and can_import:
        st.session_state["material_panel_mode"] = "add"
        st.session_state.pop("material_panel_id", None)

    if st.session_state.get("material_edit_id"):
        mid = str(st.session_state.pop("material_edit_id"))
        st.session_state["material_panel_id"] = mid
        st.session_state["material_panel_mode"] = "edit"
        st.session_state["material_selected_id"] = mid
    elif st.session_state.get("material_view_id"):
        mid = str(st.session_state.pop("material_view_id"))
        st.session_state["material_panel_id"] = mid
        st.session_state["material_selected_id"] = mid
        st.session_state.pop("material_panel_mode", None)

    if can_import and st.session_state.get("materials_quote_import_mode"):
        if st.button("← Back to Materials catalog", use_container_width=True, key="mqi_back"):
            st.session_state["materials_quote_import_mode"] = False
            st.session_state["material_quote_result"] = None
            st.session_state["material_quote_file_meta"] = None
            st.rerun()
        st.caption("Upload a quote file, analyze, review the grid, then save to quotes and catalog.")
        st.subheader("Import vendor quote")
        render_material_quote_import_form(return_to_materials=True)
        return

    fetch_error: str | None = None
    try:
        rows = fetch_table("materials_catalog", limit=5000, order_by="item_key")
    except Exception as exc:
        fetch_error = str(exc)
        rows = []
    df = pd.DataFrame(rows)
    if fetch_error:
        st.warning(f"Could not load materials catalog: {fetch_error}")

    _mat_del_open = destructive_confirm_open_key(_MAT_DELETE_CONFIRM_PREFIX)
    if st.session_state.get(_mat_del_open) and not can_import:
        close_destructive_confirmation(_MAT_DELETE_CONFIRM_PREFIX)
        st.session_state.pop("materials_pending_delete_ids", None)
    elif st.session_state.get(_mat_del_open) and can_import:
        pending = list(st.session_state.get("materials_pending_delete_ids") or [])
        if not pending:
            close_destructive_confirmation(_MAT_DELETE_CONFIRM_PREFIX)
            st.session_state.pop("materials_pending_delete_ids", None)
            st.rerun()
        id_to_label: dict[str, str] = {}
        if not df.empty and "id" in df.columns:
            for _, r in df.iterrows():
                rid = str(r["id"])
                desc = str(r.get("description") or "").strip()
                ikey = str(r.get("item_key") or "").strip()
                id_to_label[rid] = desc or ikey or rid
        name_lines: list[str] = []
        for pid in pending:
            nm = id_to_label.get(pid)
            if nm:
                name_lines.append(nm)
            else:
                short = pid[:10] + "…" if len(pid) > 10 else pid
                name_lines.append(f"(unknown id) {short}")
        n_pending = len(pending)
        msg = (
            "Are you sure you want to delete this material?"
            if n_pending == 1
            else f"Are you sure you want to delete these {n_pending} materials?"
        )

        def _on_confirm_delete() -> None:
            for mid in pending:
                try:
                    delete_rows_admin("materials_catalog", {"id": mid})
                except Exception as exc:
                    st.error(f"Could not delete {mid}: {exc}")
            st.session_state.pop("materials_pending_delete_ids", None)
            clear_selected_ids(TABLE_KEY_MATERIALS)
            panel_id = st.session_state.get("material_panel_id")
            if panel_id and str(panel_id) in {str(x) for x in pending}:
                _clear_material_panel()
            st.success("Material(s) deleted where permitted.")

        def _on_cancel_delete() -> None:
            st.session_state.pop("materials_pending_delete_ids", None)

        render_destructive_confirmation(
            key_prefix=_MAT_DELETE_CONFIRM_PREFIX,
            title="Confirm Delete",
            message=msg,
            confirm_label="Confirm Delete",
            cancel_label="Cancel",
            on_confirm=_on_confirm_delete,
            on_cancel=_on_cancel_delete,
            name_lines=name_lines,
        )

    if st.session_state.pop("_mat_do_deactivate", False) and can_import:
        sel_ids = get_selected_ids(TABLE_KEY_MATERIALS)
        if sel_ids:
            for mid in sel_ids:
                try:
                    update_rows_admin("materials_catalog", {"is_active": False}, {"id": mid})
                except Exception as exc:
                    st.error(f"Could not deactivate {mid}: {exc}")
            clear_selected_ids(TABLE_KEY_MATERIALS)
            _clear_material_panel()
            st.success("Selected materials deactivated.")
            st.rerun()

    panel_mode = st.session_state.get("material_panel_mode")
    panel_id = st.session_state.get("material_panel_id")

    if panel_mode == "add" and not can_import:
        _clear_material_panel()
        panel_mode = None
        panel_id = None
    if panel_mode == "edit" and not can_import:
        _clear_material_panel()
        panel_mode = None
        panel_id = None

    panel_row: dict | None = None
    if panel_mode == "edit" and panel_id:
        panel_row = fetch_one("materials_catalog", {"id": panel_id})
        if not panel_row:
            _clear_material_panel()
            panel_mode = None
            panel_id = None

    _render_material_filter_row(df=df, can_import=can_import)
    filtered = _filtered_materials_df(df)

    main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
    with main_col:
        _render_materials_table_main(filtered=filtered, df=df, can_import=can_import)
    with side_col:
        _render_material_right_panel(
            df=df,
            rows=rows,
            can_import=can_import,
            panel_mode=(str(panel_mode) if panel_mode else None),
            panel_row=panel_row,
        )

    if not can_import:
        st.info("Only admin users can add, edit, deactivate, or delete catalog rows.")
