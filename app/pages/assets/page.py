"""Asset Manager page — main entry point.

Registered in main.py as:
    from pages import assets as assets_page
    "Asset Manager": assets_page.render,

Session-state keys used by this page:
    selected_asset_id        UUID of the asset being viewed or edited
    assets_edit_mode         bool — True when the edit dialog should appear
    assets_view_asset_id     UUID of the asset being previewed (view dialog)
    assets_show_create_dialog  bool — True when create dialog should appear
    assets_filter_status     str  — filter value, default "All"
    assets_filter_category   str  — filter value, default "All"
    assets_filter_type       str  — filter value, default "All"
    assets_filter_active     str  — "All" / "Active Only" / "Inactive Only"
    assets_search_query      str  — free-text search
    assets_view_mode         str  — "Cards" | "Table"
"""
from __future__ import annotations

import streamlit as st

try:
    from app.auth import current_role
    from app.ui import IPS_NAV_PENDING_KEY
except ImportError:
    from auth import current_role  # type: ignore
    from ui import IPS_NAV_PENDING_KEY  # type: ignore

try:
    from app.table_actions import (
        IPS_PENDING_DELETE,
        TABLE_KEY_ASSET_MANAGER,
        clear_selected_ids,
        inject_table_action_styles,
        render_selection_action_bar,
    )
except ImportError:
    from table_actions import (  # type: ignore
        IPS_PENDING_DELETE,
        TABLE_KEY_ASSET_MANAGER,
        clear_selected_ids,
        inject_table_action_styles,
        render_selection_action_bar,
    )

try:
    from app.pages.assets.components import (
        apply_assets_filters,
        render_asset_card_list,
        render_asset_empty_state,
        render_assets_filters,
        render_assets_header,
    )
    from app.pages.assets.dialogs import (
        show_create_asset_dialog,
        show_edit_asset_dialog,
        show_view_asset_dialog,
    )
    from app.pages.assets.queries import (
        build_emp_by_id,
        build_job_label_by_id,
        get_asset_by_id,
        get_assets,
        get_employees,
        get_jobs,
        prepare_assets_dataframe,
    )
    from app.pages.assets.services import check_asset_dependencies, delete_asset, deactivate_asset
except ImportError:
    from pages.assets.components import (  # type: ignore
        apply_assets_filters,
        render_asset_card_list,
        render_asset_empty_state,
        render_assets_filters,
        render_assets_header,
    )
    from pages.assets.dialogs import (  # type: ignore
        show_create_asset_dialog,
        show_edit_asset_dialog,
        show_view_asset_dialog,
    )
    from pages.assets.queries import (  # type: ignore
        build_emp_by_id,
        build_job_label_by_id,
        get_asset_by_id,
        get_assets,
        get_employees,
        get_jobs,
        prepare_assets_dataframe,
    )
    from pages.assets.services import check_asset_dependencies, delete_asset, deactivate_asset  # type: ignore


# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------

def _init_state() -> None:
    defaults: dict = {
        "selected_asset_id": None,
        "assets_edit_mode": False,
        "assets_view_asset_id": None,
        "assets_show_create_dialog": False,
        "assets_filter_status": "All",
        "assets_filter_category": "All",
        "assets_filter_type": "All",
        "assets_filter_active": "All",
        "assets_search_query": "",
        "assets_view_mode": "Table",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # Migrate legacy keys written by asset_detail.py → Asset Manager "Edit"
    legacy_view = st.session_state.get("assets_view")
    legacy_id = st.session_state.get("asset_edit_id")
    if legacy_view == "edit" and legacy_id:
        st.session_state["assets_edit_mode"] = True
        st.session_state["selected_asset_id"] = str(legacy_id)
        st.session_state.pop("assets_view", None)
        st.session_state.pop("asset_edit_id", None)

    # Also migrate asset_view_mode / asset_return_to used by older code paths
    legacy_vm = st.session_state.get("asset_view_mode")
    if legacy_vm == "edit" and st.session_state.get("selected_asset_id"):
        st.session_state["assets_edit_mode"] = True
        st.session_state.pop("asset_view_mode", None)


# ---------------------------------------------------------------------------
# Top action bar
# ---------------------------------------------------------------------------

def _render_view_toggle(vm: str, *, can_add: bool) -> None:
    """Cards / Table toggle + New Asset + Asset Scanner — single compact row."""
    if can_add:
        c1, c2, c3, c4 = st.columns(4, gap="small")
    else:
        c1, c2, c4 = st.columns(3, gap="small")

    if c1.button("Cards", type="primary" if vm == "Cards" else "secondary",
                 use_container_width=True, key="am_view_cards"):
        st.session_state["assets_view_mode"] = "Cards"
        st.rerun()
    if c2.button("Table", type="primary" if vm == "Table" else "secondary",
                 use_container_width=True, key="am_view_table"):
        st.session_state["assets_view_mode"] = "Table"
        st.rerun()
    if can_add:
        if c3.button("New Asset", type="primary", use_container_width=True, key="am_new_asset"):
            st.session_state["assets_show_create_dialog"] = True
            st.rerun()
    if c4.button("Asset Scanner", type="secondary", use_container_width=True, key="am_scanner"):
        st.session_state[IPS_NAV_PENDING_KEY] = "Asset Scanner"
        st.rerun()


# ---------------------------------------------------------------------------
# Delete handler
# ---------------------------------------------------------------------------

def _handle_pending_delete(
    actions: dict,
    sel: list[str],
    *,
    can_edit: bool,
) -> None:
    """Execute the confirmed delete/deactivate pass.

    Must only run when the action bar has emitted ``confirm_delete=True``
    (two-step confirmation).  Running on every rerun while pending ids exist
    would trigger immediate destructive deletes before the user confirms.
    """
    if not actions.get("confirm_delete"):
        return
    pend = st.session_state.get(IPS_PENDING_DELETE) or {}
    if not (pend.get(TABLE_KEY_ASSET_MANAGER) and can_edit):
        return

    ids_to_remove = [str(x).strip() for x in pend[TABLE_KEY_ASSET_MANAGER] if str(x).strip()]
    n_deleted = n_deactivated = n_blocked = 0
    errors: list[str] = []

    for aid in ids_to_remove:
        blocked, has_history = check_asset_dependencies(aid)
        if blocked:
            n_blocked += 1
            st.error("Cannot delete asset while checked out.")
            continue
        if has_history:
            try:
                deactivate_asset(aid)
                n_deactivated += 1
            except Exception as exc:
                errors.append(f"{aid}: {exc}")
            continue
        try:
            delete_asset(aid)
            n_deleted += 1
        except Exception as exc:
            errors.append(f"{aid}: {exc}")

    pend.pop(TABLE_KEY_ASSET_MANAGER, None)
    st.session_state[IPS_PENDING_DELETE] = pend
    clear_selected_ids(TABLE_KEY_ASSET_MANAGER)
    st.session_state.pop("am_sel_editor", None)

    for msg in errors[:8]:
        st.error(msg)
    if n_deleted:
        st.toast(f"Deleted {n_deleted} asset(s).", icon="✅")
    if n_deactivated:
        st.warning(f"{n_deactivated} asset(s) had history and were deactivated instead.")
    if n_blocked:
        st.info("One or more assets could not be deleted while checked out.")
    st.rerun()


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render() -> None:
    _init_state()
    render_assets_header()

    # pm mirrors the write permissions used in asset_detail.py and asset_database.py.
    can_edit = current_role() in {"admin", "manager", "pm"}

    # ── Fetch data ───────────────────────────────────────────────────────
    assets = get_assets()
    jobs = get_jobs()
    employees = get_employees()
    job_label_by_id = build_job_label_by_id(jobs)
    emp_by_id = build_emp_by_id(employees)
    df = prepare_assets_dataframe(assets)

    # ── Dialogs (shown before main body so they overlay correctly) ────────

    # Edit dialog
    edit_mode = bool(st.session_state.get("assets_edit_mode"))
    edit_id = st.session_state.get("selected_asset_id")
    if edit_mode and edit_id:
        asset_for_edit = get_asset_by_id(str(edit_id))
        if not asset_for_edit:
            st.session_state["assets_edit_mode"] = False
            st.session_state["selected_asset_id"] = None
            clear_selected_ids(TABLE_KEY_ASSET_MANAGER)
            st.warning("Asset not found.")
            st.rerun()
        else:
            show_edit_asset_dialog(asset_for_edit, jobs=jobs, can_edit=can_edit)

    # View dialog
    view_id = st.session_state.get("assets_view_asset_id")
    if view_id and not edit_mode:
        asset_for_view = get_asset_by_id(str(view_id))
        if not asset_for_view:
            st.session_state.pop("assets_view_asset_id", None)
        else:
            show_view_asset_dialog(
                asset_for_view,
                job_label_by_id=job_label_by_id,
                emp_by_id=emp_by_id,
                can_edit=can_edit,
            )

    # Create dialog
    if bool(st.session_state.get("assets_show_create_dialog")) and can_edit:
        show_create_asset_dialog(jobs=jobs, can_edit=can_edit)

    # ── Asset overview ───────────────────────────────────────────────────
    st.subheader("Asset Overview")

    if df.empty:
        render_asset_empty_state("no_assets", can_add=can_edit)
        return

    # Detect narrow viewport for mobile layout
    is_narrow = st.session_state.get("ips_viewport_narrow") is True

    vm = str(st.session_state.get("assets_view_mode") or "Table")

    # Top action row (Cards / Table / New Asset / Scanner)
    with st.container(border=True):
        _render_view_toggle(vm=vm, can_add=can_edit)

    # Filters
    st.divider()
    filters = render_assets_filters(df, mobile=is_narrow)
    filtered = apply_assets_filters(df, filters)

    if filtered.empty:
        render_asset_empty_state("no_match", can_add=can_edit)
        return

    st.caption(f"{len(filtered)} asset(s) shown.")

    # ── Cards view ───────────────────────────────────────────────────────
    if vm == "Cards":
        render_asset_card_list(
            filtered.to_dict("records"),
            key_prefix="am",
            show_category=True,
            mobile_layout=is_narrow,
            emp_by_id=emp_by_id,
            job_label_by_id=job_label_by_id,
        )
        return

    # ── Table view ───────────────────────────────────────────────────────
    inject_table_action_styles()

    try:
        from app.pages.assets.components import render_assets_table
    except ImportError:
        from pages.assets.components import render_assets_table  # type: ignore

    _, sel = render_assets_table(
        filtered,
        table_key=TABLE_KEY_ASSET_MANAGER,
        can_edit=can_edit,
        editor_key="am_sel_editor",
        job_label_by_id=job_label_by_id,
    )

    actions = render_selection_action_bar(
        TABLE_KEY_ASSET_MANAGER,
        sel,
        can_view=True,
        can_edit=can_edit,
        can_delete=can_edit,
        export_df=filtered,
        id_column="id",
        export_filename="assets_export.csv",
        view_label="View Asset",
        edit_label="Edit Asset",
        delete_label="Delete Asset",
        delete_selected_label="Delete Selected",
    )

    if actions.get("view") and sel:
        st.session_state["assets_view_asset_id"] = str(sel[0])
        clear_selected_ids(TABLE_KEY_ASSET_MANAGER)
        st.session_state.pop("am_sel_editor", None)
        st.rerun()

    if actions.get("edit") and sel and can_edit:
        st.session_state["assets_edit_mode"] = True
        st.session_state["selected_asset_id"] = str(sel[0])
        st.session_state.pop("asset_return_to", None)
        # Clear any open view dialog so it doesn't reappear after editing.
        st.session_state.pop("assets_view_asset_id", None)
        clear_selected_ids(TABLE_KEY_ASSET_MANAGER)
        st.session_state.pop("am_sel_editor", None)
        st.rerun()

    _handle_pending_delete(actions, sel, can_edit=can_edit)
