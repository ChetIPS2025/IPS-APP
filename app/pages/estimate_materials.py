"""Manage the estimate quote material catalog (``estimate_materials``), separate from inventory stock."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

try:
    from app.ui.catalog_inventory_display import prepare_catalog_inventory_display_df
except ImportError:
    from ui.catalog_inventory_display import prepare_catalog_inventory_display_df  # type: ignore

try:
    from app.auth import current_role
    from app.ui.page_shell import render_page_header
    from app.db import (
        fetch_by_match_admin,
        fetch_table,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from app.services.estimate_materials_catalog import (
        clear_estimate_materials_catalog_cache,
        import_inventory_materials_into_estimate_catalog,
        sync_estimate_material_pricing_from_inventory,
    )
except ImportError:
    from auth import current_role  # type: ignore
    from ui.page_shell import render_page_header  # type: ignore
    from db import (  # type: ignore
        fetch_by_match_admin,
        fetch_table,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from services.estimate_materials_catalog import (  # type: ignore
        clear_estimate_materials_catalog_cache,
        import_inventory_materials_into_estimate_catalog,
        sync_estimate_material_pricing_from_inventory,
    )

try:
    from app.ui.modal import ensure_modal_styles, modal_wide_marker
except ImportError:
    from ui.modal import ensure_modal_styles, modal_wide_marker  # type: ignore

_EM_DLG_KEY = "em_catalog_dlg"
_UUID_SPLIT = re.compile(r"[\s,;]+")


def _em_on_dismiss_catalog_dlg() -> None:
    st.session_state.pop(_EM_DLG_KEY, None)


@st.dialog("Add material", width="large", on_dismiss=_em_on_dismiss_catalog_dlg)
def _em_add_material_dialog() -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Add material")
    with st.container(border=True):
        with st.form("em_add_form_dlg", clear_on_submit=True):
            ik = st.text_input("Item key", placeholder="Unique code or SKU")
            desc = st.text_input("Description")
            cat = st.text_input("Category", value="Quote Catalog")
            unit = st.text_input("Unit", value="EA")
            pp = st.number_input("Purchase price", min_value=0.0, value=0.0, step=0.01)
            sp = st.number_input("Sell price", min_value=0.0, value=0.0, step=0.01)
            vin = st.text_input("Vendor item #", value="")
            inv_ref = st.text_input(
                "Linked inventory row (optional UUID)",
                value="",
                help="When set, **Sync Pricing** can refresh purchase/sell from the matching inventory item.",
            )
            submitted = st.form_submit_button("Save material", type="primary", use_container_width=True)
    if st.button("Cancel", type="secondary", use_container_width=True, key="em_add_dlg_cancel"):
        st.session_state.pop(_EM_DLG_KEY, None)
        st.rerun()
    if submitted:
        key = str(ik or "").strip()
        if not key:
            st.error("Item key is required.")
            return
        if fetch_by_match_admin("estimate_materials", {"item_key": key}, limit=1):
            st.error("That item key already exists.")
            return
        payload: dict = {
            "item_key": key[:500],
            "description": str(desc or "")[:2000],
            "category": str(cat or "Quote Catalog")[:200],
            "subgroup": "",
            "unit": str(unit or "EA")[:32],
            "purchase_price": float(pp),
            "sell_price": float(sp),
            "vendor_item_number": str(vin or "")[:200],
            "is_active": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        ref = str(inv_ref or "").strip()
        if ref:
            payload["inventory_ref_id"] = ref
        insert_row_admin("estimate_materials", payload)
        clear_estimate_materials_catalog_cache()
        st.session_state.pop(_EM_DLG_KEY, None)
        st.success("Material added.")
        st.rerun()


@st.dialog("Manage categories", width="large", on_dismiss=_em_on_dismiss_catalog_dlg)
def _em_manage_categories_dialog() -> None:
    ensure_modal_styles()
    modal_wide_marker()
    st.markdown("### Manage categories")
    st.caption("Bulk rename: exact **from** category → **to** category on all matching rows.")
    with st.container(border=True):
        with st.form("em_cat_rename_dlg"):
            old_c = st.text_input("Rename from", placeholder="Exact category text")
            new_c = st.text_input("Rename to", placeholder="New category text")
            apply_sub = st.form_submit_button("Apply rename", type="primary", use_container_width=True)
    if st.button("Cancel", type="secondary", use_container_width=True, key="em_cat_dlg_cancel"):
        st.session_state.pop(_EM_DLG_KEY, None)
        st.rerun()
    if apply_sub:
        o = str(old_c or "").strip()
        n = str(new_c or "").strip()
        if not o or not n:
            st.error("Enter both values.")
            return
        rows = fetch_by_match_admin("estimate_materials", {"category": o}, limit=5000)
        for r in rows or []:
            rid = str((r or {}).get("id") or "").strip()
            if rid:
                update_rows_admin(
                    "estimate_materials",
                    {
                        "category": n[:200],
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    {"id": rid},
                )
        clear_estimate_materials_catalog_cache()
        st.session_state.pop(_EM_DLG_KEY, None)
        st.success(f"Updated {len(rows or [])} row(s).")
        st.rerun()


def _parse_inventory_uuid_selection(text: str) -> frozenset[str]:
    ids: set[str] = set()
    for part in _UUID_SPLIT.split(str(text or "")):
        p = part.strip()
        if len(p) >= 32:
            ids.add(p)
    return frozenset(ids)


@st.dialog("Import from inventory — preview", width="large")
def _dialog_em_inventory_import_preview() -> None:
    scope = st.session_state.get("em_inv_scope", "all_active")
    if scope not in ("all_active", "materials_only"):
        scope = "all_active"
    mode = st.session_state.get("em_inv_sel_mode", "all_eligible")
    selected: frozenset[str] | None = None
    if mode == "selected_uuids":
        selected = _parse_inventory_uuid_selection(str(st.session_state.get("em_imp_uuids") or ""))
        if not selected:
            st.warning(
                "Enter at least one **inventory_items.id** UUID (32+ hex characters) when using **Import selected**."
            )
            return
    with st.spinner("Computing preview…"):
        result = import_inventory_materials_into_estimate_catalog(
            fetch_table=fetch_table,
            insert_row_admin=insert_row_admin,
            update_rows_admin=update_rows_admin,
            fetch_table_admin=fetch_table_admin,
            dry_run=True,
            scope=scope,
            selected_inventory_ids=selected,
        )
    st.markdown(result.summary_text())


def render() -> None:
    render_page_header(
        "Estimate Materials",
        "Quote catalog for proposals — separate from stock on hand.",
    )

    st.session_state.setdefault(_EM_DLG_KEY, "")

    if current_role() not in {"admin", "manager"}:
        st.info("Only admin or manager can manage the estimate materials catalog.")
        try:
            rows = fetch_table("estimate_materials", limit=2000, order_by="item_key")
        except Exception:
            rows = []
        if rows:
            st.dataframe(
                prepare_catalog_inventory_display_df(
                    pd.DataFrame(rows),
                    extra_hidden=frozenset({"created_at"}),
                ),
                use_container_width=True,
                hide_index=True,
            )
        return

    st.markdown(
        '<div style="font-size:0.8rem;color:#334155;margin:0 0 0.35rem 0;">'
        "<strong>From inventory</strong> → copy / link → <strong>quote catalog row</strong> "
        "(<code>inventory_ref_id</code> is set from the inventory row so **Sync Pricing** can refresh costs).</div>",
        unsafe_allow_html=True,
    )

    st.session_state.setdefault("em_inv_scope", "all_active")
    st.session_state.setdefault("em_inv_sel_mode", "all_eligible")

    with st.expander("Import from inventory — options", expanded=False):
        st.radio(
            "Which inventory rows to include",
            options=["all_active", "materials_only"],
            key="em_inv_scope",
            horizontal=True,
            format_func=lambda v: (
                "All **active** items (every category)"
                if v == "all_active"
                else "**Materials** category only (legacy)"
            ),
        )
        st.radio(
            "Import mode",
            options=["all_eligible", "selected_uuids"],
            key="em_inv_sel_mode",
            horizontal=True,
            format_func=lambda v: (
                "**Import all** eligible rows (below)"
                if v == "all_eligible"
                else "**Import selected** UUIDs only"
            ),
        )
        if str(st.session_state.get("em_inv_sel_mode") or "") == "selected_uuids":
            st.text_area(
                "Inventory row UUIDs (`inventory_items.id`)",
                height=120,
                key="em_imp_uuids",
                placeholder="One UUID per line, or comma-separated",
                help="Only these rows are considered (still must be active unless you also narrow scope).",
            )

    a1, a2, a3, a4 = st.columns(4, gap="small")
    with a1:
        pv, imp = st.columns(2, gap="small")
        with pv:
            if st.button("Preview", use_container_width=True, key="em_imp_preview"):
                _dialog_em_inventory_import_preview()
        with imp:
            if st.button("Import", use_container_width=True, key="em_imp_inv"):
                scope = st.session_state.get("em_inv_scope", "all_active")
                if scope not in ("all_active", "materials_only"):
                    scope = "all_active"
                mode = st.session_state.get("em_inv_sel_mode", "all_eligible")
                selected_ids: frozenset[str] | None = None
                if mode == "selected_uuids":
                    selected_ids = _parse_inventory_uuid_selection(
                        str(st.session_state.get("em_imp_uuids") or "")
                    )
                    if not selected_ids:
                        st.error(
                            "Enter at least one inventory UUID for **Import selected**, "
                            "or switch to **Import all**."
                        )
                if mode != "selected_uuids" or selected_ids:
                    with st.spinner("Importing from inventory…"):
                        result = import_inventory_materials_into_estimate_catalog(
                            fetch_table=fetch_table,
                            insert_row_admin=insert_row_admin,
                            update_rows_admin=update_rows_admin,
                            fetch_table_admin=fetch_table_admin,
                            dry_run=False,
                            scope=scope,
                            selected_inventory_ids=selected_ids,
                        )
                    clear_estimate_materials_catalog_cache()
                    st.session_state.pop(_EM_DLG_KEY, None)
                    st.success("Import finished.")
                    with st.expander("Import summary", expanded=True):
                        st.markdown(result.summary_text())
                    st.rerun()
    with a2:
        if st.button("Sync Pricing", use_container_width=True, key="em_sync"):
            n = sync_estimate_material_pricing_from_inventory(
                fetch_table=fetch_table,
                fetch_table_admin=fetch_table_admin,
                update_rows_admin=update_rows_admin,
            )
            clear_estimate_materials_catalog_cache()
            st.session_state.pop(_EM_DLG_KEY, None)
            st.success(f"Updated pricing on {n} linked row(s).")
            st.rerun()
    with a3:
        if st.button(
            "Add Material",
            type="primary",
            use_container_width=True,
            key="em_btn_add",
        ):
            st.session_state[_EM_DLG_KEY] = "add"
            st.rerun()
    with a4:
        if st.button(
            "Manage Categories",
            type="secondary",
            use_container_width=True,
            key="em_btn_cats",
        ):
            st.session_state[_EM_DLG_KEY] = "cats"
            st.rerun()

    dlg = str(st.session_state.get(_EM_DLG_KEY) or "").strip()
    if dlg == "add":
        _em_add_material_dialog()
    elif dlg == "cats":
        _em_manage_categories_dialog()

    try:
        rows = list(fetch_table_admin("estimate_materials", limit=5000, order_by="item_key") or [])
    except Exception as exc:
        st.error(
            "Could not load **estimate_materials**. Apply migration **`sql/039_estimate_materials.sql`** "
            f"in Supabase, then refresh. ({exc})"
        )
        return

    if not rows:
        st.info(
            "No quote-catalog rows yet. Use **Import** (defaults to **all active** inventory) or **Add Material**."
        )
        return

    st.markdown("##### Catalog")
    st.dataframe(
        prepare_catalog_inventory_display_df(
            pd.DataFrame(rows),
            extra_hidden=frozenset({"created_at"}),
        ),
        use_container_width=True,
        hide_index=True,
    )
