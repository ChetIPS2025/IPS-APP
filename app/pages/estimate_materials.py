"""Manage the estimate quote material catalog (``estimate_materials``), separate from inventory stock."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.branding import render_header
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
    from branding import render_header  # type: ignore
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

_EM_ACTION_PANEL_KEY = "em_action_panel"


def render() -> None:
    render_header(
        "Estimate Materials",
        subtitle="Quote catalog — proposals, bundles, markup, and vendor pricing (not stock on hand).",
    )
    st.caption(
        "**Estimates** pull line items only from this catalog. "
        "**Inventory** (sidebar) is **stock tracking** (on-hand, scan, usage)."
    )

    st.session_state.setdefault(_EM_ACTION_PANEL_KEY, "")

    if current_role() not in {"admin", "manager"}:
        st.info("Only admin or manager can manage the estimate materials catalog.")
        try:
            rows = fetch_table("estimate_materials", limit=2000, order_by="item_key")
        except Exception:
            rows = []
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        return

    st.markdown(
        '<div style="font-size:0.8rem;color:#334155;margin:0 0 0.35rem 0;">'
        "<strong>From inventory</strong> → copy / link → <strong>quote catalog row</strong> "
        "(optional <code>inventory_ref_id</code> keeps pricing in sync).</div>",
        unsafe_allow_html=True,
    )

    a1, a2, a3, a4 = st.columns(4, gap="small")
    with a1:
        if st.button("Import From Inventory", use_container_width=True, key="em_imp_inv"):
            ins, sk = import_inventory_materials_into_estimate_catalog(
                fetch_table=fetch_table,
                insert_row_admin=insert_row_admin,
                fetch_by_match_admin=fetch_by_match_admin,
            )
            clear_estimate_materials_catalog_cache()
            st.session_state[_EM_ACTION_PANEL_KEY] = ""
            st.success(f"Imported {ins} row(s). Skipped {sk}.")
            st.rerun()
    with a2:
        if st.button("Sync Pricing", use_container_width=True, key="em_sync"):
            n = sync_estimate_material_pricing_from_inventory(
                fetch_table=fetch_table,
                fetch_table_admin=fetch_table_admin,
                update_rows_admin=update_rows_admin,
            )
            clear_estimate_materials_catalog_cache()
            st.session_state[_EM_ACTION_PANEL_KEY] = ""
            st.success(f"Updated pricing on {n} linked row(s).")
            st.rerun()
    with a3:
        panel = str(st.session_state.get(_EM_ACTION_PANEL_KEY) or "")
        add_primary = panel == "add"
        if st.button(
            "Add Material",
            use_container_width=True,
            key="em_btn_add",
            type="primary" if add_primary else "secondary",
        ):
            st.session_state[_EM_ACTION_PANEL_KEY] = "" if add_primary else "add"
            st.rerun()
    with a4:
        cat_primary = str(st.session_state.get(_EM_ACTION_PANEL_KEY) or "") == "cats"
        if st.button(
            "Manage Categories",
            use_container_width=True,
            key="em_btn_cats",
            type="primary" if cat_primary else "secondary",
        ):
            st.session_state[_EM_ACTION_PANEL_KEY] = "" if cat_primary else "cats"
            st.rerun()

    panel = str(st.session_state.get(_EM_ACTION_PANEL_KEY) or "")

    if panel == "add":
        with st.container():
            st.markdown("##### Add material")
            with st.form("em_add_form", clear_on_submit=True):
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
                submitted = st.form_submit_button("Save material", type="primary")
                if submitted:
                    key = str(ik or "").strip()
                    if not key:
                        st.error("Item key is required.")
                    elif fetch_by_match_admin("estimate_materials", {"item_key": key}, limit=1):
                        st.error("That item key already exists.")
                    else:
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
                        st.session_state[_EM_ACTION_PANEL_KEY] = ""
                        st.success("Material added.")
                        st.rerun()

    if panel == "cats":
        with st.container():
            st.markdown("##### Manage categories")
            st.caption("Bulk rename: exact **from** category → **to** category on all matching rows.")
            with st.form("em_cat_rename"):
                old_c = st.text_input("Rename from", placeholder="Exact category text")
                new_c = st.text_input("Rename to", placeholder="New category text")
                if st.form_submit_button("Apply rename", type="primary"):
                    o = str(old_c or "").strip()
                    n = str(new_c or "").strip()
                    if not o or not n:
                        st.error("Enter both values.")
                    else:
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
                        st.session_state[_EM_ACTION_PANEL_KEY] = ""
                        st.success(f"Updated {len(rows or [])} row(s).")
                        st.rerun()

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
            "No quote-catalog rows yet. Use **Import From Inventory** to copy stocked **Materials** lines, "
            "or **Add Material**."
        )
        return

    st.markdown("##### Catalog")
    show = pd.DataFrame(rows)
    show = show.drop(columns=[c for c in ("created_at",) if c in show.columns], errors="ignore")
    st.dataframe(show, use_container_width=True, hide_index=True)
