"""
UI rendering components for Inventory.

All ``render_*`` functions here output Streamlit widgets.
They read from session state but do not write to the DB directly.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.ui.catalog_inventory_display import (
        prepare_catalog_inventory_display_df,
        sanitize_catalog_inventory_export_df,
    )
    from app.ui.compact_forms import field_marker
    from app.ui.page_shell import render_card, render_section_header
    from app.ui.streamlit_perf import fragment, inject_scroll_preserve, ips_app_rerun
    from app.ips_crud_list_styles import inject_ips_crud_list_styles
    from app.table_actions import (
        TABLE_KEY_INVENTORY,
        clear_selected_ids,
        inject_table_action_styles,
        set_selected_ids,
    )
except ImportError:
    from ui.catalog_inventory_display import (  # type: ignore
        prepare_catalog_inventory_display_df,
        sanitize_catalog_inventory_export_df,
    )
    from ui.compact_forms import field_marker  # type: ignore
    from ui.page_shell import render_card, render_section_header  # type: ignore
    from ui.streamlit_perf import fragment, inject_scroll_preserve, ips_app_rerun  # type: ignore
    from ips_crud_list_styles import inject_ips_crud_list_styles  # type: ignore
    from table_actions import (  # type: ignore
        TABLE_KEY_INVENTORY,
        clear_selected_ids,
        inject_table_action_styles,
        set_selected_ids,
    )

from app.pages.inventory.utils import (
    inv_thumb_html,
    render_inventory_status_badge,
    render_purchase_link,
    render_stock_level_badge,
)
from app.pages.inventory.queries import fetch_inventory_image_signed_url_cached

# State key constants (standardized per spec)
SK_SELECTED_IDS = "selected_inventory_ids"
SK_SELECTED_ITEM_ID = "selected_inventory_item_id"
SK_FILTER_CATEGORY = "inventory_filter_category"
SK_FILTER_STATUS = "inventory_filter_status"
SK_SEARCH_QUERY = "inventory_search_query"
SK_EDIT_MODE = "inventory_edit_mode"
SK_VIEW_MODE = "inventory_view_mode"

_INV_PAGE_SIZE_DEFAULT = 75


def _clear_inv_checkbox_keys() -> None:
    for k in list(st.session_state.keys()):
        if str(k).startswith("inv_select_"):
            del st.session_state[k]


def render_inventory_header() -> None:
    """Inject mobile-friendly inventory page CSS."""
    st.markdown(
        """
<style>
/* Compact inventory list spacing */
section[data-testid="stMain"]:has(.ips-inventory-list-anchor)
  [data-testid="stElementContainer"] {
  margin-bottom: 0.1rem !important;
}
section[data-testid="stMain"]:has(.ips-inventory-list-anchor)
  [data-testid="stHorizontalBlock"] {
  gap: 0.3rem !important;
  align-items: center !important;
}

/* Inventory card style */
.ips-inv-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.ips-inv-card-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: #0f172a;
  margin: 0;
  line-height: 1.3;
}
.ips-inv-card-meta {
  font-size: 0.78rem;
  color: #64748b;
  margin: 0;
}

/* QR wrap */
.ips-inv-qr-wrap { display:inline-block; }

/* Action bar toolbar compact */
.ips-inv-toolbar {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 8px 10px;
  margin-bottom: 8px;
}

/* Responsive: on small screens collapse to fewer columns */
@media (max-width: 768px) {
  .ips-inv-card { flex-wrap: wrap; }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_inventory_filters(df: pd.DataFrame) -> tuple[str, str, str]:
    """
    Render category/search/status filters.

    Returns ``(selected_category, search_query, status_filter)``.
    Uses standardized session state keys.
    """
    # Migrate old filter keys to new standardized keys
    if "inv_f_cat" in st.session_state and SK_FILTER_CATEGORY not in st.session_state:
        st.session_state[SK_FILTER_CATEGORY] = st.session_state.pop("inv_f_cat")
    if "inv_f_search" in st.session_state and SK_SEARCH_QUERY not in st.session_state:
        st.session_state[SK_SEARCH_QUERY] = st.session_state.pop("inv_f_search")
    if "inv_f_active" in st.session_state and SK_FILTER_STATUS not in st.session_state:
        st.session_state[SK_FILTER_STATUS] = st.session_state.pop("inv_f_active")

    categories = sorted(
        set(
            ["Materials"]
            + [
                c
                for c in df.get("category", pd.Series(dtype=str))
                .dropna()
                .astype(str)
                .unique()
                .tolist()
                if str(c).strip()
            ]
        )
    )

    st.markdown('<span class="ips-compact-form" aria-hidden="true"></span>', unsafe_allow_html=True)
    filter_cols = st.columns([1, 1.7, 1], gap="small")
    with filter_cols[0]:
        field_marker("medium")
        st.selectbox("Category", ["All"] + categories, key=SK_FILTER_CATEGORY)
    with filter_cols[1]:
        field_marker("search")
        st.text_input(
            "Search",
            placeholder="Name, SKU, QR, category, vendor, location…",
            key=SK_SEARCH_QUERY,
        )
    with filter_cols[2]:
        field_marker("medium")
        st.selectbox("Status", ["All", "Active Only", "Inactive Only"], key=SK_FILTER_STATUS)

    return (
        str(st.session_state.get(SK_FILTER_CATEGORY) or "All"),
        str(st.session_state.get(SK_SEARCH_QUERY) or ""),
        str(st.session_state.get(SK_FILTER_STATUS) or "All"),
    )


def _apply_filters(
    df: pd.DataFrame,
    *,
    selected_category: str,
    search: str,
    status_filter: str,
) -> pd.DataFrame:
    filtered = df.copy()
    if selected_category != "All" and "category" in filtered.columns:
        sc = str(selected_category).strip().lower()
        filtered = filtered[filtered["category"].astype(str).str.strip().str.lower() == sc]
    if status_filter == "Active Only" and "is_active" in filtered.columns:
        filtered = filtered[filtered["is_active"] == True]  # noqa: E712
    elif status_filter == "Inactive Only" and "is_active" in filtered.columns:
        filtered = filtered[filtered["is_active"] == False]  # noqa: E712
    if search.strip():
        s = search.strip().lower()
        mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
        filtered = filtered[mask.any(axis=1)]
    return filtered


def render_inventory_empty_state(can_edit: bool, *, filtered: bool = False) -> bool:
    """
    Render an appropriate empty state.

    Returns ``True`` if the user clicked the Add button (only when ``can_edit``).
    """
    try:
        from app.ui.components.empty_states import render_empty_state
    except ImportError:
        from ui.components.empty_states import render_empty_state  # type: ignore

    if filtered:
        if can_edit:
            return bool(
                render_empty_state(
                    "No items match filters",
                    "Clear filters or add a new inventory item.",
                    icon="🔍",
                    action_label="Add Inventory Item",
                    action_key="inv_filtered_empty_add",
                )
            )
        render_empty_state("No items match filters", "Try clearing search or category filters.", icon="🔍")
        return False
    else:
        if can_edit:
            return bool(
                render_empty_state(
                    "No inventory items found",
                    "Add your first item to start tracking stock.",
                    icon="📦",
                    action_label="Add Inventory Item",
                    action_key="inv_empty_add",
                )
            )
        render_empty_state("No inventory items found", "No items are available in the catalog yet.", icon="📦")
        return False


def render_inventory_card(row: dict) -> None:
    """Render a single inventory item as a compact card (for mobile/field use)."""
    name = str(row.get("item_name") or "—")
    sku = str(row.get("sku") or "")
    cat = str(row.get("category") or "")
    vendor = str(row.get("vendor") or "")
    qty = row.get("quantity_on_hand", 0)
    reorder = row.get("reorder_point", 0)
    is_active = bool(row.get("is_active", True))

    status_html = render_inventory_status_badge(is_active)
    stock_html = render_stock_level_badge(float(qty or 0), float(reorder or 0))
    thumb = inv_thumb_html(str(row.get("image_url") or ""), size=40)

    meta_parts = []
    if sku:
        meta_parts.append(f"SKU: {sku}")
    if cat:
        meta_parts.append(cat)
    if vendor:
        meta_parts.append(vendor)
    meta_html = " · ".join(meta_parts) if meta_parts else ""

    card_html = (
        f'<div class="ips-inv-card">'
        f"  {thumb}"
        f'  <div style="flex:1;min-width:0;">'
        f'    <p class="ips-inv-card-name">{name}</p>'
        f'    <p class="ips-inv-card-meta">{meta_html}</p>'
        f"  </div>"
        f'  <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">'
        f"    {stock_html}"
        f"    {status_html}"
        f'    <span style="font-size:0.78rem;color:#475569;">'
        f"      {float(qty or 0):.2g} / {float(reorder or 0):.2g}"
        f"    </span>"
        f"  </div>"
        f"</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_inventory_detail_panel(row: dict, can_edit: bool) -> None:
    """Render a detail view for a selected inventory item."""
    rid = str(row.get("id") or "")
    name = str(row.get("item_name") or "—")
    sku = str(row.get("sku") or "")
    category = str(row.get("category") or "")
    unit = str(row.get("unit") or "EA")
    vendor = str(row.get("vendor") or "")
    location = str(row.get("storage_location") or "")
    notes = str(row.get("notes") or "")
    is_active = bool(row.get("is_active", True))
    qty = float(row.get("quantity_on_hand") or 0)
    reorder = float(row.get("reorder_point") or 0)
    unit_cost = row.get("unit_cost")
    qr_value = str(row.get("qr_code_value") or "").strip()
    image_url = str(row.get("image_url") or "").strip()

    try:
        from app.ui.page_shell import render_card
    except ImportError:
        from ui.page_shell import render_card  # type: ignore

    with render_card():
        img_url = fetch_inventory_image_signed_url_cached(image_url) if image_url else None
        if img_url:
            c1, c2 = st.columns([1, 3], gap="small")
            with c1:
                st.image(img_url, width=100)
            with c2:
                st.markdown(f"**{name}**")
                st.markdown(
                    render_inventory_status_badge(is_active)
                    + "&nbsp;&nbsp;"
                    + render_stock_level_badge(qty, reorder),
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(f"### {name}")
            st.markdown(
                render_inventory_status_badge(is_active)
                + "&nbsp;&nbsp;"
                + render_stock_level_badge(qty, reorder),
                unsafe_allow_html=True,
            )

        st.divider()
        r1, r2, r3 = st.columns(3, gap="small")
        r1.metric("On Hand", f"{qty:.2g} {unit}")
        r2.metric("Reorder Point", f"{reorder:.2g}")
        if unit_cost is not None:
            try:
                r3.metric("Unit Cost", f"${float(unit_cost):.2f}")
            except (TypeError, ValueError):
                pass

        detail_items = []
        if sku:
            detail_items.append(("SKU", sku))
        if category:
            detail_items.append(("Category", category))
        if vendor:
            detail_items.append(("Vendor", vendor))
        if location:
            detail_items.append(("Location", location))

        if detail_items:
            cols = st.columns(2, gap="small")
            for i, (label, value) in enumerate(detail_items):
                cols[i % 2].markdown(f"**{label}:** {value}")

        if notes:
            st.markdown(f"**Notes:** {notes}")

        if can_edit:
            btn_cols = st.columns([1, 1, 2], gap="small")
            with btn_cols[0]:
                if st.button("Edit", type="primary", use_container_width=True, key=f"inv_detail_edit_{rid}"):
                    st.session_state[SK_EDIT_MODE] = True
                    st.session_state[SK_SELECTED_ITEM_ID] = rid
                    try:
                        from app.ui.streamlit_perf import ips_app_rerun
                    except ImportError:
                        from ui.streamlit_perf import ips_app_rerun  # type: ignore
                    ips_app_rerun()
            with btn_cols[1]:
                if st.button("Close", use_container_width=True, key=f"inv_detail_close_{rid}"):
                    st.session_state.pop(SK_SELECTED_ITEM_ID, None)
                    st.rerun()


def render_low_stock_section(filtered_df: pd.DataFrame) -> None:
    """Render the low-stock alert banner and expandable detail table."""
    qoh_s = pd.to_numeric(filtered_df.get("quantity_on_hand", 0), errors="coerce").fillna(0)
    rp_s = (
        pd.to_numeric(filtered_df["reorder_point"], errors="coerce").fillna(0)
        if "reorder_point" in filtered_df.columns
        else pd.Series(0.0, index=filtered_df.index)
    )
    low_mask = qoh_s <= rp_s
    n_low = int(low_mask.sum()) if len(filtered_df) else 0
    if n_low == 0:
        return

    st.markdown('<span class="ips-surface-soft" aria-hidden="true"></span>', unsafe_allow_html=True)
    render_section_header("Low stock alert", f"{n_low} visible item(s) at or below reorder point.")
    with st.expander("Low stock detail (visible filters)", expanded=False):
        cols_show = [
            c
            for c in ("item_name", "sku", "quantity_on_hand", "reorder_point", "vendor")
            if c in filtered_df.columns
        ]
        if cols_show:
            sub = filtered_df.loc[low_mask, cols_show].copy()
            if "quantity_on_hand" in sub.columns and "reorder_point" in sub.columns:
                qv = pd.to_numeric(sub["quantity_on_hand"], errors="coerce").fillna(0)
                rv = pd.to_numeric(sub["reorder_point"], errors="coerce").fillna(0)
                gap = (rv - qv).clip(lower=0)
                sub["suggest_qty"] = gap
                sub.loc[sub["suggest_qty"] <= 0, "suggest_qty"] = pd.NA
            if "image_url" in filtered_df.columns:
                from app.pages.inventory.utils import thumb_display_url
                sub["image_url"] = filtered_df.loc[low_mask, "image_url"].map(thumb_display_url).values
            disp = prepare_catalog_inventory_display_df(sub, extra_hidden=frozenset())
            img_cfg = {}
            if "Photo" in disp.columns:
                img_cfg["Photo"] = st.column_config.ImageColumn("Photo", width="small")
            st.dataframe(disp, use_container_width=True, hide_index=True, column_config=img_cfg or {})
            st.caption("**Suggest qty** = shortfall to reorder point (informational).")


def render_inventory_table(
    df: pd.DataFrame, *, can_edit: bool, selected_key: str
) -> None:
    """
    Render the paginated inventory table rows with checkbox selection.

    Reads/writes ``selected_key`` in session state.
    """
    inject_table_action_styles()

    page_size = int(st.session_state.get("inv_page_size", _INV_PAGE_SIZE_DEFAULT))
    page_size = max(25, min(150, page_size))
    total_rows = len(df)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page = int(st.session_state.get("inv_page", 0))
    page = max(0, min(page, total_pages - 1))
    if page != int(st.session_state.get("inv_page", 0)):
        st.session_state["inv_page"] = page

    # Pagination row
    pg1, pg2, pg3, pg4 = st.columns([1.2, 1, 1, 2.2], gap="small")
    with pg1:
        if st.button("← Prev", key="inv_page_prev", disabled=page <= 0, use_container_width=True):
            st.session_state["inv_page"] = page - 1
            st.rerun()
    with pg2:
        if st.button("Next →", key="inv_page_next", disabled=page >= total_pages - 1, use_container_width=True):
            st.session_state["inv_page"] = page + 1
            st.rerun()
    with pg3:
        st.caption(f"Page **{page + 1}** / **{total_pages}**")
    with pg4:
        st.caption(f"**{total_rows:,}** matching · **{page_size}** per page")

    page_df = df.iloc[page * page_size : (page + 1) * page_size]
    page_ids = [
        str(x) for x in page_df.get("id", pd.Series(dtype=str)).astype(str).tolist()
        if str(x).strip()
    ]

    cur_selected = [str(x) for x in (st.session_state.get(selected_key) or []) if str(x).strip()]
    sel_set = set(cur_selected)

    # Column header row
    header = st.columns([0.35, 0.5, 2.0, 0.9, 0.85, 1.05, 0.95], gap="small")
    for col, label in zip(header, ["**Sel**", "**Photo**", "**Item**", "**SKU**", "**On Hand**", "**Reorder**", "**Status**"]):
        col.markdown(label)

    for _, row in page_df.iterrows():
        item_id = str(row.get("id") or "").strip()
        if not item_id:
            continue
        ck_key = f"inv_select_{item_id}"
        if ck_key not in st.session_state:
            st.session_state[ck_key] = item_id in sel_set
        cols = st.columns([0.35, 0.5, 2.0, 0.9, 0.85, 1.05, 0.95], gap="small")
        with cols[0]:
            st.checkbox("", key=ck_key, label_visibility="collapsed")
        with cols[1]:
            st.markdown(inv_thumb_html(str(row.get("image_url") or "")), unsafe_allow_html=True)
        cols[2].write(str(row.get("item_name") or "—"))
        cols[3].write(str(row.get("sku") or "—"))
        cols[4].write(str(row.get("quantity_on_hand") or "0"))
        cols[5].write(str(row.get("reorder_point") or "0"))
        cols[6].markdown(
            render_inventory_status_badge(bool(row.get("is_active", True))),
            unsafe_allow_html=True,
        )

    # Reconcile checkbox state back into selected set
    for iid in page_ids:
        ck_key = f"inv_select_{iid}"
        if st.session_state.get(ck_key):
            sel_set.add(iid)
        else:
            sel_set.discard(iid)

    st.session_state[selected_key] = list(sel_set)


def render_inventory_action_bar(
    *,
    df_all: pd.DataFrame,
    visible_df: pd.DataFrame,
    can_edit: bool,
    selected_key: str,
) -> None:
    """
    Toolbar: Add / Edit / Deactivate / Delete / Export / Select-All / Clear.
    Also includes admin QR backfill tools.
    """
    inject_ips_crud_list_styles()
    inject_table_action_styles()

    sel = [str(x) for x in (st.session_state.get(selected_key) or []) if str(x).strip()]
    n = len(sel)
    one = n == 1
    none = n == 0

    # Build export CSV for selected rows
    exp_ok = bool(not df_all.empty and "id" in df_all.columns and n >= 1)
    csv_bytes = b""
    if exp_ok:
        sub = df_all[df_all["id"].astype(str).isin([str(x) for x in sel])]
        csv_bytes = sanitize_catalog_inventory_export_df(sub).to_csv(index=False).encode("utf-8")

    vis_ids: list[str] = []
    if not visible_df.empty and "id" in visible_df.columns:
        vis_ids = visible_df["id"].astype(str).tolist()
    sel_set = {str(x) for x in sel}
    vis_set = set(vis_ids)
    all_visible_selected = bool(vis_set) and sel_set == vis_set

    with render_card():
        st.markdown('<span class="ips-crud-toolbar-root"></span>', unsafe_allow_html=True)
        left, b0, b1, b2, b3, b4, b5, b6 = st.columns([1.1, 1, 1, 1, 1, 1, 1, 1], gap="small")
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
                st.session_state[SK_VIEW_MODE] = "add"
                st.session_state[SK_SELECTED_ITEM_ID] = None
                ips_app_rerun()
        with b1:
            if st.button(
                "Edit",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or not one,
                key="inv_btn_edit",
            ):
                st.session_state[SK_EDIT_MODE] = True
                st.session_state[SK_SELECTED_ITEM_ID] = str(sel[0])
                # Also keep legacy keys in sync for safety
                st.session_state["inventory_edit_popup_open"] = True
                st.session_state["editing_inventory_id"] = str(sel[0])
                ips_app_rerun()
        with b2:
            if st.button(
                "Deactivate",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or none,
                key="inv_btn_deactivate",
            ):
                st.session_state["_inv_do_deactivate"] = True
                ips_app_rerun()
        with b3:
            if st.button(
                "Delete",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or none,
                key="inv_btn_delete",
            ):
                try:
                    from app.confirm_delete import open_destructive_confirmation
                except ImportError:
                    from confirm_delete import open_destructive_confirmation  # type: ignore
                open_destructive_confirmation("inventory_delete")
                st.session_state["inventory_pending_delete_ids"] = [str(x) for x in sel]
                ips_app_rerun()
        with b4:
            st.download_button(
                "Export",
                data=csv_bytes,
                file_name="inventory_export.csv",
                mime="text/csv",
                use_container_width=True,
                disabled=not exp_ok,
                key="inv_btn_export",
            )
        with b5:
            if st.button(
                "Select All",
                use_container_width=True,
                disabled=not vis_ids or all_visible_selected,
                key="inv_btn_sel_all",
            ):
                st.session_state[selected_key] = list(vis_ids)
                set_selected_ids(TABLE_KEY_INVENTORY, list(vis_ids))
                _clear_inv_checkbox_keys()
                st.rerun()
        with b6:
            if st.button(
                "Clear",
                use_container_width=True,
                disabled=none,
                key="inv_btn_clear",
            ):
                st.session_state[selected_key] = []
                _clear_inv_checkbox_keys()
                clear_selected_ids(TABLE_KEY_INVENTORY)
                st.session_state.pop("inventory_pending_delete_ids", None)
                st.rerun()

        # Admin QR tools in a second row
        if can_edit:
            q1, q2 = st.columns(2, gap="small")
            with q1:
                if st.button(
                    "Generate missing QR codes",
                    use_container_width=True,
                    key="inv_btn_backfill_qr",
                    help="Assigns a unique INV-* QR to every item missing qr_code_value.",
                ):
                    try:
                        from app.pages.inventory.services import backfill_missing_qr_codes
                        n_gen = backfill_missing_qr_codes()
                        st.success(f"Generated QR codes for {n_gen} item(s).")
                    except Exception as exc:
                        st.error(f"Backfill failed: {exc}")
                    ips_app_rerun()
            with q2:
                if st.button(
                    "Regenerate QR PNGs (current URL)",
                    use_container_width=True,
                    key="inv_btn_regen_qr_png",
                    help="Re-uploads QR PNGs using APP_BASE_URL so scans open the live app.",
                ):
                    try:
                        from app.pages.inventory.services import regenerate_qr_pngs
                        n_reg = regenerate_qr_pngs()
                        st.success(f"Regenerated {n_reg} QR image(s). Reprint any physical labels.")
                    except Exception as exc:
                        st.error(f"Regenerate failed: {exc}")
                    ips_app_rerun()


def render_inventory_list_body(
    *, df: pd.DataFrame, can_edit: bool, selected_key: str
) -> None:
    """
    Filters → low-stock banner → paginated table → action bar.
    Called inside a ``@fragment`` to isolate reruns.
    """
    inject_table_action_styles()

    st.markdown('<span class="ips-inventory-list-anchor" aria-hidden="true"></span>', unsafe_allow_html=True)
    render_section_header("Inventory list", "Filter, select rows, and use the action bar below.")

    _sel_n = len([x for x in (st.session_state.get(selected_key) or []) if str(x).strip()])
    if _sel_n:
        st.caption(f"{_sel_n} row(s) selected")

    # Empty dataset (no items at all)
    if df.empty:
        st.selectbox("Category", ["All", "Materials"], key=SK_FILTER_CATEGORY)
        if render_inventory_empty_state(can_edit, filtered=False):
            st.session_state[SK_VIEW_MODE] = "add"
            st.session_state[SK_SELECTED_ITEM_ID] = None
            ips_app_rerun()
        return

    # --- Filters ---
    selected_category, search, status_filter = render_inventory_filters(df)

    # Synchronize filter change → reset page
    _filt_sig = (selected_category, search, status_filter)
    if st.session_state.get("inv_filter_sig") != _filt_sig:
        st.session_state["inv_filter_sig"] = _filt_sig
        st.session_state["inv_page"] = 0

    filtered = _apply_filters(df, selected_category=selected_category, search=search, status_filter=status_filter)

    # --- Low stock banner ---
    render_low_stock_section(filtered)

    # Empty after filters
    if filtered.empty:
        if render_inventory_empty_state(can_edit, filtered=True):
            st.session_state[SK_VIEW_MODE] = "add"
            st.session_state[SK_SELECTED_ITEM_ID] = None
            ips_app_rerun()
        return

    # --- Table rows ---
    render_inventory_table(filtered, can_edit=can_edit, selected_key=selected_key)

    # Sync selection to TABLE_KEY_INVENTORY
    selected_ids = list(st.session_state.get(selected_key) or [])
    with st.container():
        set_selected_ids(TABLE_KEY_INVENTORY, selected_ids)
        render_inventory_action_bar(
            df_all=df, visible_df=filtered, can_edit=can_edit, selected_key=selected_key
        )

    # Clear edit popup state if selection becomes 0 or 2+
    sel_ids = selected_ids
    if len(sel_ids) != 1:
        if st.session_state.get(SK_EDIT_MODE):
            st.session_state[SK_EDIT_MODE] = False
            st.session_state.pop(SK_SELECTED_ITEM_ID, None)
            st.session_state["inventory_edit_popup_open"] = False
            st.session_state["editing_inventory_id"] = None


@fragment
def render_inventory_list_fragment(
    *, df: pd.DataFrame, can_edit: bool, selected_key: str
) -> None:
    """Fragment-isolated render scope (filters, table, action bar)."""
    inject_scroll_preserve("inventory")
    render_inventory_list_body(df=df, can_edit=can_edit, selected_key=selected_key)
