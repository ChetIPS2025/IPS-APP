"""
Reusable checkbox row selection + action bar for Streamlit data tables.

**Session state — selected row IDs** (one list per logical ``table_key``)::

    st.session_state[f"selected_{table_key}_ids"]  # -> list[str]

Examples: ``selected_assets_ids``, ``selected_jobs_ids``, ``selected_estimates_ids``,
``selected_customers_ids``.

Helpers: :func:`get_selected_ids`, :func:`set_selected_ids`, :func:`clear_selected_ids`.
Main UI: :func:`render_selectable_dataframe` (checkbox column first) and
:func:`render_table_action_bar` (alias :func:`render_selection_action_bar`).

**Placement:** Render the data editor first, then the action bar, so the bar shows an
accurate selection count for the current run.

**Pending delete confirmation**::

    st.session_state["ips_table_pending_delete"] -> dict[table_key, list[str]]
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import streamlit as st

# Legacy: dict-based storage (migrated on read into selected_<table_key>_ids)
IPS_ROW_SELECTIONS = "ips_row_selections"

IPS_PENDING_DELETE = "ips_table_pending_delete"
IPS_ACTION_BAR_CSS = "ips_table_action_bar_injected"

# Canonical table_key values -> session key ``selected_{table_key}_ids``
# Asset Database page uses ``assets`` -> ``selected_assets_ids`` (see Asset Manager for separate key).
TABLE_KEY_ASSETS = "assets"
TABLE_KEY_ASSET_MANAGER = "asset_manager"
TABLE_KEY_EQUIPMENT = "equipment"
TABLE_KEY_JOBS = "jobs"
TABLE_KEY_ESTIMATES = "estimates"
TABLE_KEY_CUSTOMERS = "customers"
TABLE_KEY_USERS = "users"
TABLE_KEY_MATERIALS = "materials"
TABLE_KEY_LABOR = "labor"
TABLE_KEY_PO_EXPENSES = "po_expenses"
TABLE_KEY_EMPLOYEES = "employees"
# Time Tracking flat table -> ``selected_time_entries_ids``; Weekly Timesheet saved headers -> ``selected_timesheets_ids``
TABLE_KEY_TIME_ENTRIES = "time_entries"
TABLE_KEY_TIMESHEETS = "timesheets"
TABLE_KEY_INVENTORY_SUPPLIES = "inventory_supplies"
TABLE_KEY_INVENTORY = "inventory"

# Backward compatibility: old dict keys -> canonical table_key
_LEGACY_TABLE_KEY_MAP: dict[str, str] = {
    "asset_manager": TABLE_KEY_ASSET_MANAGER,
    "assets": TABLE_KEY_ASSET_MANAGER,  # legacy Asset Manager used key "assets"
    "asset_database": TABLE_KEY_ASSETS,
    "job_database": TABLE_KEY_JOBS,
    "estimates_list": TABLE_KEY_ESTIMATES,
    "labor_rates": TABLE_KEY_LABOR,
}


def selected_row_session_key(table_key: str) -> str:
    """Return session state key for selected IDs, e.g. ``selected_jobs_ids``."""
    return f"selected_{table_key}_ids"


def _migrate_direct_session_keys_for_table(table_key: str) -> None:
    """Migrate renamed session keys (e.g. ``selected_asset_database_ids`` -> ``selected_assets_ids``)."""
    k = selected_row_session_key(table_key)
    if k in st.session_state:
        return
    if table_key == TABLE_KEY_ASSETS:
        old_db = "selected_asset_database_ids"
        if old_db in st.session_state:
            st.session_state[k] = st.session_state.pop(old_db)


def get_selected_ids(table_key: str) -> list[str]:
    """Return selected row id strings for this table (isolated per ``table_key``)."""
    _migrate_direct_session_keys_for_table(table_key)
    _migrate_legacy_selection_for_table(table_key)
    k = selected_row_session_key(table_key)
    v = st.session_state.get(k)
    if not isinstance(v, list):
        return []
    return [str(x) for x in v if x is not None and str(x).strip()]


def set_selected_ids(table_key: str, ids: list[str]) -> None:
    st.session_state[selected_row_session_key(table_key)] = [
        str(x) for x in ids if x is not None and str(x).strip()
    ]


def clear_selected_ids(table_key: str) -> None:
    k = selected_row_session_key(table_key)
    if k in st.session_state:
        del st.session_state[k]


def _migrate_legacy_pending_keys(pending: dict) -> None:
    """Map old table_key strings in pending-delete dict to canonical keys."""
    for old_k, new_k in _LEGACY_TABLE_KEY_MAP.items():
        if old_k not in pending:
            continue
        if new_k not in pending:
            pending[new_k] = pending.pop(old_k)
        else:
            pending.pop(old_k, None)


def _migrate_legacy_selection_for_table(table_key: str) -> None:
    """One-time style migration from ``ips_row_selections`` dict."""
    k = selected_row_session_key(table_key)
    if k in st.session_state:
        return
    legacy = st.session_state.get(IPS_ROW_SELECTIONS)
    if not isinstance(legacy, dict):
        return
    # Map old key -> this canonical table_key
    for old_key, canon in _LEGACY_TABLE_KEY_MAP.items():
        if canon == table_key and old_key in legacy:
            raw = legacy.pop(old_key)
            if isinstance(raw, list):
                set_selected_ids(table_key, [str(x) for x in raw])
            if not legacy:
                del st.session_state[IPS_ROW_SELECTIONS]
            return
    if table_key in legacy:
        raw = legacy.pop(table_key)
        if isinstance(raw, list):
            set_selected_ids(table_key, [str(x) for x in raw])
        if not legacy:
            del st.session_state[IPS_ROW_SELECTIONS]


def inject_table_action_styles() -> None:
    """
    IPS dark-theme chrome for (1) table selection action bars and (2) list-page top toolbars.

    Pages mark toolbars with ``.ips-list-top-anchor`` inside ``st.container(border=True)``.
    Action bars use ``.ips-ta-bar-anchor`` (injected by :func:`render_table_action_bar`).
    """
    if st.session_state.get(IPS_ACTION_BAR_CSS):
        return
    st.session_state[IPS_ACTION_BAR_CSS] = True
    st.markdown(
        """
        <style>
        /* ----- List-page top actions (Estimates, Asset Database, Materials) ----- */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor) {
            padding: 8px 10px 10px 10px !important;
            margin-bottom: 10px !important;
            background: rgba(15, 23, 42, 0.55) !important;
            border-color: rgba(100, 116, 139, 0.4) !important;
            border-radius: 10px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor)
            div[data-testid="stHorizontalBlock"] {
            gap: 0.5rem !important;
            align-items: stretch !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor) button {
            min-height: 2.35rem !important;
            border-radius: 8px !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
            padding: 0.4rem 0.85rem !important;
            line-height: 1.25 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor)
            button[data-testid="baseButton-primary"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-list-top-anchor)
            button[kind="primary"] {
            font-weight: 600 !important;
        }

        /* ----- Table action bar (under data_editor) ----- */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ta-bar-anchor) {
            padding: 8px 10px 10px 10px !important;
            margin-bottom: 10px !important;
            margin-top: 4px !important;
            background: rgba(15, 23, 42, 0.72) !important;
            border-color: rgba(100, 116, 139, 0.42) !important;
            border-radius: 10px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ta-bar-anchor)
            div[data-testid="stHorizontalBlock"] {
            gap: 0.45rem !important;
            align-items: stretch !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ta-bar-anchor) button {
            min-height: 2.35rem !important;
            border-radius: 8px !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
            padding: 0.4rem 0.75rem !important;
            line-height: 1.25 !important;
        }

        .ips-table-actions-bar {
            padding: 10px 12px;
            margin-bottom: 10px;
            background: rgba(15, 23, 42, 0.78);
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 8px;
        }
        .ips-ta-summary {
            color: #94a3b8;
            font-size: 12px;
            font-weight: 500;
            letter-spacing: 0.02em;
        }
        .ips-ta-summary .ips-ta-num {
            color: #e2e8f0;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _visible_id_list(
    export_df: pd.DataFrame | None,
    visible_df: pd.DataFrame | None,
    id_column: str,
) -> list[str] | None:
    """IDs of rows currently shown (e.g. after filters). Used for Select All Visible."""
    src = visible_df if visible_df is not None else export_df
    if src is None or src.empty or id_column not in src.columns:
        return None
    out = [str(x).strip() for x in src[id_column].tolist() if str(x).strip()]
    return out or None


def _prepare_editor_df(
    df: pd.DataFrame,
    id_column: str,
    table_key: str,
    columns: list[str] | None,
) -> pd.DataFrame:
    if id_column not in df.columns:
        raise ValueError(f"Column {id_column!r} not in dataframe")
    show = list(columns) if columns else [c for c in df.columns if c != id_column]
    show = [c for c in show if c in df.columns and c != id_column]
    base = df[show + [id_column]].copy()
    base[id_column] = base[id_column].astype(str)
    sel_stored = set(get_selected_ids(table_key))
    base.insert(0, "__select__", base[id_column].isin(sel_stored))
    return base


def render_selectable_dataframe(
    df: pd.DataFrame,
    *,
    table_key: str,
    id_column: str = "id",
    columns: list[str] | None = None,
    editor_key: str,
    num_rows: str = "fixed",
) -> tuple[pd.DataFrame, list[str]]:
    """
    Renders a ``data_editor`` with first-column checkboxes. Persists selection under
    ``selected_<table_key>_ids``.

    Returns (edited dataframe including ``__select__`` and id column, list of selected ids).
    """
    inject_table_action_styles()
    ed_base = _prepare_editor_df(df, id_column, table_key, columns)
    disabled = [c for c in ed_base.columns if c != "__select__"]
    edited = st.data_editor(
        ed_base,
        key=editor_key,
        num_rows=num_rows,
        use_container_width=True,
        hide_index=True,
        disabled=disabled,
        column_config={
            "__select__": st.column_config.CheckboxColumn(" ", default=False, width="small"),
        },
    )
    if edited is None or edited.empty:
        set_selected_ids(table_key, [])
        return ed_base, []

    sel_mask = edited["__select__"] == True  # noqa: E712
    selected = edited.loc[sel_mask, id_column].astype(str).tolist()
    set_selected_ids(table_key, selected)
    return edited, selected


def render_table_action_bar(
    table_key: str,
    selected_ids: list[str],
    *,
    can_view: bool = True,
    can_edit: bool = True,
    can_delete: bool = False,
    export_df: pd.DataFrame | None = None,
    visible_df: pd.DataFrame | None = None,
    id_column: str = "id",
    export_filename: str = "export.csv",
    view_label: str = "View",
    edit_label: str = "Edit",
    delete_label: str = "Delete",
    delete_selected_label: str = "Delete Selected",
    on_bulk_selection_change: Callable[[], None] | None = None,
) -> dict:
    """
    IPS action bar: summary on the **left**, actions on the **right**.

    - 0 selected: show ``0 selected``; primary actions disabled (export / clear as before).
    - 1 selected: **View** | **Edit** | **Delete** | **Export Selected** | …
    - 2+ selected: **Delete Selected** | **Export Selected** | … (View/Edit not shown).

    ``on_bulk_selection_change`` runs after **Select All Visible** or **Clear selection** updates
    stored IDs (e.g. to reset per-row checkbox widget keys that mirror selection).

    Returns flags: ``view``, ``edit``, ``confirm_delete``, ``cancel_delete``.
    """
    inject_table_action_styles()
    n = len(selected_ids)
    pending = st.session_state.get(IPS_PENDING_DELETE)
    if not isinstance(pending, dict):
        pending = {}
        st.session_state[IPS_PENDING_DELETE] = pending
    else:
        _migrate_legacy_pending_keys(pending)

    out: dict = {
        "view": False,
        "edit": False,
        "confirm_delete": False,
        "cancel_delete": False,
    }

    vis_ids = _visible_id_list(export_df, visible_df, id_column)
    show_select_all = vis_ids is not None and len(vis_ids) > 0
    sel_set = {str(x) for x in selected_ids}
    vis_set = set(vis_ids) if vis_ids is not None else set()
    all_visible_selected = bool(vis_set) and sel_set == vis_set

    def _summary_html(count: int) -> str:
        return (
            f'<span class="ips-ta-summary">'
            f'<span class="ips-ta-num">{count}</span> selected'
            f"</span>"
        )

    bulk = n >= 2

    exp_ok = bool(
        export_df is not None
        and id_column in export_df.columns
        and n >= 1
    )
    data = b""
    if exp_ok and export_df is not None:
        sub = export_df[export_df[id_column].astype(str).isin([str(x) for x in selected_ids])]
        data = sub.to_csv(index=False).encode("utf-8")

    with st.container(border=True):
        st.markdown('<span class="ips-ta-bar-anchor"></span>', unsafe_allow_html=True)
        left, right = st.columns([1.35, 5.0])

        with left:
            st.markdown('<span class="ips-ta-bar-root"></span>', unsafe_allow_html=True)
            st.markdown(_summary_html(n), unsafe_allow_html=True)

        with right:
            if bulk:
                b1, b2, b3, b4 = st.columns([1, 1, 1, 1])
                with b1:
                    del_multi_dis = not (n >= 1 and can_delete)
                    if st.button(
                        delete_selected_label,
                        disabled=del_multi_dis,
                        type="secondary",
                        use_container_width=True,
                        key=f"ips_ta_del_multi_{table_key}",
                    ):
                        pending[table_key] = list(selected_ids)
                        st.rerun()
                with b2:
                    st.download_button(
                        label="Export Selected",
                        data=data,
                        file_name=export_filename,
                        mime="text/csv",
                        use_container_width=True,
                        disabled=not exp_ok,
                        key=f"ips_export_{table_key}",
                    )
                if show_select_all:
                    with b3:
                        if st.button(
                            "Select All Visible",
                            use_container_width=True,
                            disabled=all_visible_selected,
                            key=f"ips_sel_all_{table_key}",
                        ):
                            set_selected_ids(table_key, list(vis_ids or []))
                            if on_bulk_selection_change:
                                on_bulk_selection_change()
                            st.rerun()
                    with b4:
                        if st.button("Clear selection", use_container_width=True, key=f"ips_ta_clr_{table_key}"):
                            clear_selected_ids(table_key)
                            pending.pop(table_key, None)
                            if on_bulk_selection_change:
                                on_bulk_selection_change()
                            st.rerun()
                else:
                    with b3:
                        if st.button("Clear selection", use_container_width=True, key=f"ips_ta_clr_{table_key}"):
                            clear_selected_ids(table_key)
                            pending.pop(table_key, None)
                            if on_bulk_selection_change:
                                on_bulk_selection_change()
                            st.rerun()
            else:
                b1, b2, b3, b4, b5, b6 = st.columns([1, 1, 1, 1, 1, 1])
                view_dis = not (n == 1 and can_view)
                edit_dis = not (n == 1 and can_edit)
                del_dis = not (n == 1 and can_delete)
                exp_single_ok = exp_ok and n == 1

                with b1:
                    if st.button(view_label, disabled=view_dis, use_container_width=True, key=f"ips_ta_view_{table_key}"):
                        out["view"] = True
                with b2:
                    if st.button(edit_label, disabled=edit_dis, use_container_width=True, key=f"ips_ta_edit_{table_key}"):
                        out["edit"] = True
                with b3:
                    if st.button(
                        delete_label,
                        disabled=del_dis,
                        type="secondary",
                        use_container_width=True,
                        key=f"ips_ta_del_{table_key}",
                    ):
                        pending[table_key] = list(selected_ids)
                        st.rerun()
                with b4:
                    st.download_button(
                        label="Export Selected",
                        data=data,
                        file_name=export_filename,
                        mime="text/csv",
                        use_container_width=True,
                        disabled=not exp_single_ok,
                        key=f"ips_export_{table_key}",
                    )
                if show_select_all:
                    with b5:
                        if st.button(
                            "Select All Visible",
                            use_container_width=True,
                            disabled=all_visible_selected,
                            key=f"ips_sel_all_{table_key}",
                        ):
                            set_selected_ids(table_key, list(vis_ids or []))
                            if on_bulk_selection_change:
                                on_bulk_selection_change()
                            st.rerun()
                    with b6:
                        clr_dis = n < 1
                        if st.button(
                            "Clear selection",
                            disabled=clr_dis,
                            use_container_width=True,
                            key=f"ips_ta_clr_{table_key}",
                        ):
                            clear_selected_ids(table_key)
                            pending.pop(table_key, None)
                            if on_bulk_selection_change:
                                on_bulk_selection_change()
                            st.rerun()
                else:
                    with b5:
                        clr_dis = n < 1
                        if st.button(
                            "Clear selection",
                            disabled=clr_dis,
                            use_container_width=True,
                            key=f"ips_ta_clr_{table_key}",
                        ):
                            clear_selected_ids(table_key)
                            pending.pop(table_key, None)
                            if on_bulk_selection_change:
                                on_bulk_selection_change()
                            st.rerun()

    pend_ids = pending.get(table_key)
    if pend_ids:
        st.warning(f"Delete **{len(pend_ids)}** row(s)? This cannot be undone.")
        dc1, dc2 = st.columns(2)
        with dc1:
            if st.button("Confirm delete", type="primary", key=f"ips_ta_del_y_{table_key}"):
                out["confirm_delete"] = True
        with dc2:
            if st.button("Cancel", key=f"ips_ta_del_n_{table_key}"):
                pending.pop(table_key, None)
                out["cancel_delete"] = True
                st.rerun()

    return out


# Preferred alias for new code (same as :func:`render_table_action_bar`).
render_selection_action_bar = render_table_action_bar

# Deprecated aliases (avoid breaking older imports)
selection_get = get_selected_ids
selection_set = set_selected_ids
selection_clear = clear_selected_ids
