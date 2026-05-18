"""
Inventory page — main entry point.

Orchestrates state initialization, delete/deactivate flows,
dialog routing, and the list fragment.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.confirm_delete import (
        close_destructive_confirmation,
        destructive_confirm_open_key,
        render_destructive_confirmation,
    )
    from app.ui.page_shell import render_page_header
    from app.ui.streamlit_perf import ips_app_rerun
    from app.table_actions import TABLE_KEY_INVENTORY, clear_selected_ids
except ImportError:
    from auth import current_role  # type: ignore
    from confirm_delete import (  # type: ignore
        close_destructive_confirmation,
        destructive_confirm_open_key,
        render_destructive_confirmation,
    )
    from ui.page_shell import render_page_header  # type: ignore
    from ui.streamlit_perf import ips_app_rerun  # type: ignore
    from table_actions import TABLE_KEY_INVENTORY, clear_selected_ids  # type: ignore

from app.pages.inventory.components import (
    SK_EDIT_MODE,
    SK_FILTER_CATEGORY,
    SK_FILTER_STATUS,
    SK_SEARCH_QUERY,
    SK_SELECTED_ITEM_ID,
    SK_VIEW_MODE,
    _clear_inv_checkbox_keys,
    render_inventory_header,
    render_inventory_list_fragment,
)
from app.pages.inventory.dialogs import inventory_add_dialog, inventory_edit_dialog
from app.pages.inventory.queries import (
    bump_data_version,
    deactivate_inventory_items,
    delete_inventory_item,
    fetch_inventory_items,
    fetch_item_by_id,
    get_current_data_version,
)

_DELETE_CONFIRM_PREFIX = "inventory_delete"
_SELECTED_KEY = "selected_inventory_ids"


def _init_session_state() -> None:
    """Ensure all required session state keys are present."""
    # Standardized keys (spec requirement)
    st.session_state.setdefault(_SELECTED_KEY, [])
    st.session_state.setdefault(SK_SELECTED_ITEM_ID, None)
    st.session_state.setdefault(SK_VIEW_MODE, None)
    st.session_state.setdefault(SK_EDIT_MODE, False)
    st.session_state.setdefault(SK_FILTER_CATEGORY, "All")
    st.session_state.setdefault(SK_FILTER_STATUS, "All")
    st.session_state.setdefault(SK_SEARCH_QUERY, "")

    # Legacy keys kept for session continuity (old bookmarks / persisted state)
    st.session_state.setdefault("inventory_panel_mode", None)
    st.session_state.setdefault("inventory_panel_id", None)
    st.session_state.setdefault("inventory_edit_popup_open", False)
    st.session_state.setdefault("editing_inventory_id", None)

    # Migrate legacy keys → new standardized keys on first run after upgrade
    _migrate_legacy_state_keys()


def _migrate_legacy_state_keys() -> None:
    """One-time migration of old session-state keys → standardized keys."""
    # inventory_panel_mode → SK_VIEW_MODE
    if "inventory_panel_mode" in st.session_state and not st.session_state.get(SK_VIEW_MODE):
        old = st.session_state.get("inventory_panel_mode")
        if old:
            st.session_state[SK_VIEW_MODE] = old

    # inventory_edit_popup_open → SK_EDIT_MODE
    if st.session_state.get("inventory_edit_popup_open") and not st.session_state.get(SK_EDIT_MODE):
        st.session_state[SK_EDIT_MODE] = True

    # editing_inventory_id / inventory_panel_id → SK_SELECTED_ITEM_ID
    if not st.session_state.get(SK_SELECTED_ITEM_ID):
        legacy_id = (
            st.session_state.get("editing_inventory_id")
            or st.session_state.get("inventory_panel_id")
        )
        if legacy_id:
            st.session_state[SK_SELECTED_ITEM_ID] = str(legacy_id)


def render() -> None:
    render_page_header("Inventory", "Manage stock levels, materials, vendors, and usage.")
    render_inventory_header()

    # Show success flash then clear it
    msg = st.session_state.pop("inventory_success", None)
    if msg:
        st.success(msg)

    can_edit = current_role() == "admin"

    _init_session_state()

    # --- Fetch inventory data ---
    try:
        rows = fetch_inventory_items(get_current_data_version())
    except Exception:
        st.warning(
            "Inventory table is not available yet. "
            "Run migration **`sql/015_inventory_items.sql`** in the Supabase SQL editor, then refresh."
        )
        return

    df = pd.DataFrame(rows)

    # Validate that the current category filter is a valid option
    if not df.empty and "category" in df.columns:
        _raw_cats = [
            c
            for c in df.get("category", pd.Series(dtype=str))
            .dropna()
            .astype(str)
            .unique()
            .tolist()
            if str(c).strip()
        ]
        _cat_opts = sorted(set(["Materials"] + _raw_cats))
        _cur_fc = str(st.session_state.get(SK_FILTER_CATEGORY) or "All").strip()
        if _cur_fc != "All" and _cur_fc not in _cat_opts:
            st.session_state[SK_FILTER_CATEGORY] = "All"
    elif df.empty:
        _fc = str(st.session_state.get(SK_FILTER_CATEGORY) or "All").strip()
        if _fc not in ("All", "Materials"):
            st.session_state[SK_FILTER_CATEGORY] = "All"

    # --- Delete confirmation ---
    _del_open_key = destructive_confirm_open_key(_DELETE_CONFIRM_PREFIX)
    if st.session_state.get(_del_open_key):
        if not can_edit:
            close_destructive_confirmation(_DELETE_CONFIRM_PREFIX)
            st.session_state.pop("inventory_pending_delete_ids", None)
        else:
            pending = list(st.session_state.get("inventory_pending_delete_ids") or [])
            if not pending:
                close_destructive_confirmation(_DELETE_CONFIRM_PREFIX)
                st.session_state.pop("inventory_pending_delete_ids", None)
                ips_app_rerun()
                return

            id_to_label: dict[str, str] = {}
            for r in rows:
                rid = str(r.get("id"))
                id_to_label[rid] = str(r.get("item_name") or "").strip() or rid
            name_lines = [id_to_label.get(pid, pid[:10] + "…") for pid in pending]
            n_pending = len(pending)
            del_msg = (
                "Are you sure you want to delete this inventory item?"
                if n_pending == 1
                else f"Are you sure you want to delete these {n_pending} inventory items?"
            )

            def _on_confirm_delete() -> None:
                failed: list[str] = []
                for iid in pending:
                    try:
                        delete_inventory_item(iid)
                    except Exception as exc:
                        st.error(f"Could not delete {iid}: {exc}")
                        failed.append(iid)
                st.session_state.pop("inventory_pending_delete_ids", None)
                st.session_state[_SELECTED_KEY] = []
                _clear_inv_checkbox_keys()
                # Clear panel if the deleted item was selected
                panel_id = st.session_state.get(SK_SELECTED_ITEM_ID)
                if panel_id and str(panel_id) in {str(x) for x in pending}:
                    st.session_state.pop(SK_SELECTED_ITEM_ID, None)
                    st.session_state.pop("inventory_panel_id", None)
                bump_data_version()
                deleted = len(pending) - len(failed)
                if deleted > 0 and not failed:
                    st.session_state["inventory_success"] = (
                        "Inventory item deleted."
                        if deleted == 1
                        else f"{deleted} inventory items deleted."
                    )
                elif deleted > 0 and failed:
                    st.session_state["inventory_success"] = (
                        f"{deleted} item(s) deleted; {len(failed)} could not be deleted (see errors above)."
                    )

            def _on_cancel_delete() -> None:
                st.session_state.pop("inventory_pending_delete_ids", None)

            render_destructive_confirmation(
                key_prefix=_DELETE_CONFIRM_PREFIX,
                title="Confirm Delete",
                message=del_msg,
                confirm_label="Confirm Delete",
                cancel_label="Cancel",
                on_confirm=_on_confirm_delete,
                on_cancel=_on_cancel_delete,
                name_lines=name_lines,
            )
            return

    # --- Deactivate ---
    if st.session_state.pop("_inv_do_deactivate", False) and can_edit:
        sel_ids = [str(x) for x in (st.session_state.get(_SELECTED_KEY) or []) if str(x).strip()]
        if sel_ids:
            try:
                deactivate_inventory_items(sel_ids)
            except Exception as exc:
                st.error(f"Could not deactivate: {exc}")
            st.session_state[_SELECTED_KEY] = []
            _clear_inv_checkbox_keys()
            st.session_state.pop(SK_SELECTED_ITEM_ID, None)
            st.session_state.pop("inventory_panel_id", None)
            bump_data_version()
            st.session_state["inventory_success"] = "Selected inventory items deactivated."
            ips_app_rerun()

    # --- Vendor quote import (admin / PM) ---
    if current_role() in {"admin", "pm"}:
        with st.expander("Import vendor quote (adds stocked Materials rows)", expanded=False):
            st.caption(
                "Creates **inventory_items** in the **Materials** category for stock tracking. "
                "Copy into the quote catalog from **Estimate Materials** when needed."
            )
            try:
                from app.pages.material_quote_import import render_material_quote_import_form
            except ImportError:
                from pages.material_quote_import import render_material_quote_import_form  # type: ignore
            render_material_quote_import_form(return_to_materials=False)

    # --- Guard: if add mode was set but user is not an editor, clear it ---
    view_mode = str(st.session_state.get(SK_VIEW_MODE) or "").strip()
    if view_mode == "add" and not can_edit:
        st.session_state[SK_VIEW_MODE] = None
        view_mode = ""
    # Legacy compat
    if st.session_state.get("inventory_panel_mode") == "add" and not can_edit:
        st.session_state["inventory_panel_mode"] = None

    # --- Inventory list (fragment-isolated) ---
    render_inventory_list_fragment(df=df, can_edit=can_edit, selected_key=_SELECTED_KEY)

    # --- Add dialog (mutually exclusive with edit dialog) ---
    _should_add = (
        view_mode == "add"
        or st.session_state.get("inventory_panel_mode") == "add"
    )
    if _should_add and can_edit:
        inventory_add_dialog()

    # --- Edit dialog (only if add mode is NOT active) ---
    _edit_mode = bool(
        st.session_state.get(SK_EDIT_MODE)
        or st.session_state.get("inventory_edit_popup_open")
    )
    if not _should_add and _edit_mode:
        if not can_edit:
            st.session_state[SK_EDIT_MODE] = False
            st.session_state["inventory_edit_popup_open"] = False
            st.session_state[SK_SELECTED_ITEM_ID] = None
            st.session_state["editing_inventory_id"] = None
            ips_app_rerun()
            return

        eid = str(
            st.session_state.get(SK_SELECTED_ITEM_ID)
            or st.session_state.get("editing_inventory_id")
            or ""
        ).strip()
        if not eid:
            st.session_state[SK_EDIT_MODE] = False
            st.session_state["inventory_edit_popup_open"] = False
            ips_app_rerun()
            return

        panel_row = fetch_item_by_id(eid)
        if not panel_row:
            st.session_state[SK_EDIT_MODE] = False
            st.session_state[SK_SELECTED_ITEM_ID] = None
            st.session_state["inventory_edit_popup_open"] = False
            st.session_state["editing_inventory_id"] = None
            ips_app_rerun()
            return

        inventory_edit_dialog(panel_row)
