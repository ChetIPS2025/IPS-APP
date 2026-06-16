"""Reusable Labor Rates management panel (Pricing Guide tab or standalone page)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.confirm_delete import (
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
    from app.db import delete_rows_admin, fetch_one, fetch_table, update_rows_admin
    from app.ips_crud_list_styles import (
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
    )
    from app.services.labor_rates_service import (
        make_unique_classification,
        save_labor_rate,
    )
    from app.table_actions import (
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )
    from app.ui.page_shell import render_page_header
except ImportError:
    from auth import current_role  # type: ignore
    from confirm_delete import (  # type: ignore
        close_destructive_confirmation,
        destructive_confirm_open_key,
        open_destructive_confirmation,
        render_destructive_confirmation,
    )
    from db import delete_rows_admin, fetch_one, fetch_table, update_rows_admin  # type: ignore
    from ips_crud_list_styles import (  # type: ignore
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
    )
    from services.labor_rates_service import (  # type: ignore
        make_unique_classification,
        save_labor_rate,
    )
    from table_actions import (  # type: ignore
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )
    from ui.page_shell import render_page_header  # type: ignore

LABOR_TABLE_COLUMNS: tuple[str, ...] = ("classification", "st_rate", "ot_rate")


def _money(v) -> str:
    try:
        return f"${float(v or 0):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _panel_mode_key(prefix: str) -> str:
    return f"{prefix}_panel_mode"


def _panel_id_key(prefix: str) -> str:
    return f"{prefix}_panel_id"


def _clear_panel(prefix: str) -> None:
    st.session_state.pop(_panel_mode_key(prefix), None)
    st.session_state.pop(_panel_id_key(prefix), None)


def _table_key(prefix: str) -> str:
    return f"labor_rates_{prefix}"


def _delete_prefix(prefix: str) -> str:
    return f"{prefix}_labor_delete"


def _render_filter_row(*, prefix: str, df: pd.DataFrame) -> None:
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
            placeholder="Classification, rates",
            key=f"{prefix}_f_search",
        )
    with f2:
        st.selectbox("Status", ["All", "Active Only", "Inactive Only"], key=f"{prefix}_f_active")


def _filtered_df(prefix: str, df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()
    selected_active = st.session_state.get(f"{prefix}_f_active", "All")
    if "is_active" in filtered.columns:
        if selected_active == "Active Only":
            filtered = filtered[filtered["is_active"] == True]  # noqa: E712
        elif selected_active == "Inactive Only":
            filtered = filtered[filtered["is_active"] == False]  # noqa: E712

    search = str(st.session_state.get(f"{prefix}_f_search", "") or "")
    if search.strip():
        s = search.strip().lower()
        search_cols = [c for c in LABOR_TABLE_COLUMNS if c in filtered.columns]
        if search_cols:
            mask = filtered[search_cols].astype(str).apply(
                lambda col: col.str.lower().str.contains(s, na=False, regex=False),
            )
            filtered = filtered[mask.any(axis=1)]
    return filtered


def _render_action_buttons(*, prefix: str, sel: list[str], can_add: bool) -> None:
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
                "Add Labor Rate",
                type="primary",
                use_container_width=True,
                disabled=not can_add,
                key=f"{prefix}_btn_add",
            ):
                st.session_state[_panel_mode_key(prefix)] = "add"
                st.session_state.pop(_panel_id_key(prefix), None)
                st.rerun()
        with b1:
            if st.button(
                "Edit",
                type="secondary",
                use_container_width=True,
                disabled=not can_add or not one,
                key=f"{prefix}_btn_edit",
            ):
                st.session_state[_panel_mode_key(prefix)] = "edit"
                st.session_state[_panel_id_key(prefix)] = str(sel[0])
                st.rerun()
        with b2:
            if st.button(
                "Deactivate",
                type="secondary",
                use_container_width=True,
                disabled=not can_add or none,
                key=f"{prefix}_btn_deactivate",
            ):
                st.session_state[f"_{prefix}_do_deactivate"] = True
                st.rerun()
        with b3:
            if st.button(
                "Delete",
                type="secondary",
                use_container_width=True,
                disabled=not can_add or none,
                key=f"{prefix}_btn_delete",
            ):
                open_destructive_confirmation(_delete_prefix(prefix))
                st.session_state[f"{prefix}_pending_delete_ids"] = [str(x) for x in sel]
                st.rerun()


def _render_add_form(*, prefix: str, rows_for_uniq: list) -> None:
    classification = st.text_input("Labor Classification", key=f"{prefix}_add_class")
    c1, c2 = st.columns(2, gap="small")
    st_rate = c1.number_input(
        "Straight Time Rate",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        key=f"{prefix}_add_st",
    )
    ot_rate = c2.number_input(
        "Overtime Rate",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        key=f"{prefix}_add_ot",
    )
    is_active = st.checkbox("Active", value=True, key=f"{prefix}_add_active")
    st.caption(
        "Default rates apply to **new** labor lines on estimates. Saved estimate lines keep the rates they were stored with."
    )

    s1, s2 = st.columns(2, gap="small")
    with s1:
        if st.button("Save Labor Rate", type="primary", use_container_width=True, key=f"{prefix}_add_save"):
            if not str(classification).strip():
                st.error("Labor Classification required.")
                st.stop()
            base_classification = str(classification).strip()
            final_classification = make_unique_classification(base_classification, rows_for_uniq)
            result = save_labor_rate(
                classification=final_classification,
                st_rate=float(st_rate or 0),
                ot_rate=float(ot_rate or 0),
                is_active=bool(is_active),
            )
            if not result.ok:
                st.error(str(result.error or "Could not add labor rate."))
                st.stop()
            _clear_panel(prefix)
            st.success(f"Added {final_classification}.")
            st.rerun()
    with s2:
        if st.button("Cancel", use_container_width=True, key=f"{prefix}_add_cancel"):
            _clear_panel(prefix)
            st.rerun()


def _render_edit_form(*, prefix: str, row: dict, rows_for_uniq: list) -> None:
    lid = str(row.get("id") or "")
    st.caption(f"ID `{lid[:8]}…`")
    pk = f"{prefix}_ed_{lid}"

    classification = st.text_input(
        "Labor Classification",
        value=str(row.get("classification") or ""),
        key=f"{pk}_class",
    )
    c1, c2 = st.columns(2, gap="small")
    st_rate = c1.number_input(
        "Straight Time Rate",
        min_value=0.0,
        value=float(row.get("st_rate") or 0),
        step=1.0,
        format="%.2f",
        key=f"{pk}_st",
    )
    ot_rate = c2.number_input(
        "Overtime Rate",
        min_value=0.0,
        value=float(row.get("ot_rate") or 0),
        step=1.0,
        format="%.2f",
        key=f"{pk}_ot",
    )
    is_active = st.checkbox("Active", value=bool(row.get("is_active")), key=f"{pk}_active")
    st.caption(
        "Updating a default rate affects **future** labor lines only. Edit labor lines on an estimate to change saved rates."
    )

    u1, u2 = st.columns(2, gap="small")
    with u1:
        if st.button("Update Labor Rate", type="primary", use_container_width=True, key=f"{pk}_save"):
            if not str(classification).strip():
                st.error("Labor Classification required.")
                st.stop()
            base = str(classification).strip()
            old_u = str(row.get("classification", "")).strip().upper()
            if base.upper() == old_u:
                final_classification = str(row.get("classification"))
            else:
                others = [r for r in rows_for_uniq if str(r.get("id")) != str(row.get("id"))]
                final_classification = make_unique_classification(base, others)
            result = save_labor_rate(
                classification=final_classification,
                st_rate=float(st_rate or 0),
                ot_rate=float(ot_rate or 0),
                is_active=bool(is_active),
                rate_id=lid,
            )
            if not result.ok:
                st.error(str(result.error or "Could not update labor rate."))
                st.stop()
            _clear_panel(prefix)
            st.success("Labor rate updated.")
            st.rerun()
    with u2:
        if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
            _clear_panel(prefix)
            st.rerun()


def _render_view_panel(*, prefix: str, row: dict) -> None:
    st.markdown(f"**Classification:** {row.get('classification') or '—'}")
    st.markdown(f"**Straight time:** {_money(row.get('st_rate'))}")
    st.markdown(f"**Overtime:** {_money(row.get('ot_rate'))}")
    active = row.get("is_active")
    st.markdown(f"**Status:** {'Active' if active else 'Inactive'}")
    if st.button("Close", use_container_width=True, key=f"{prefix}_view_close"):
        _clear_panel(prefix)
        st.rerun()


def _render_side_panel(*, prefix: str, mode: str, rows_for_uniq: list) -> None:
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        if mode == "add":
            st.markdown("### Add labor rate")
            _render_add_form(prefix=prefix, rows_for_uniq=rows_for_uniq)
        elif mode == "edit":
            st.markdown("### Edit labor rate")
            eid = st.session_state.get(_panel_id_key(prefix))
            er = fetch_one("labor_rates", {"id": eid}) if eid else None
            if not er:
                st.warning("Labor rate not found.")
                _clear_panel(prefix)
            else:
                _render_edit_form(prefix=prefix, row=er, rows_for_uniq=rows_for_uniq)
        elif mode == "view":
            st.markdown("### Labor rate")
            vid = st.session_state.get(_panel_id_key(prefix))
            vr = fetch_one("labor_rates", {"id": vid}) if vid else None
            if not vr:
                st.warning("Labor rate not found.")
                _clear_panel(prefix)
            else:
                _render_view_panel(prefix=prefix, row=vr)


def _render_table_block(*, prefix: str, filtered: pd.DataFrame, df: pd.DataFrame, can_add: bool) -> None:
    inject_table_action_styles()
    show_cols = [c for c in LABOR_TABLE_COLUMNS if c in filtered.columns]

    if df.empty:
        st.info("No labor rates found.")
        if can_add:
            inject_ips_crud_list_styles()
            if st.button("Add Labor Rate", type="primary", use_container_width=True, key=f"{prefix}_empty_add"):
                st.session_state[_panel_mode_key(prefix)] = "add"
                st.session_state.pop(_panel_id_key(prefix), None)
                st.rerun()
        return

    st.caption("Default ST/OT rates used when adding labor to new estimates.")

    if "id" not in filtered.columns:
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)
        return

    bar_ph = st.empty()
    tk = _table_key(prefix)
    _, sel = render_selectable_dataframe(
        filtered,
        table_key=tk,
        id_column="id",
        columns=show_cols,
        editor_key=f"{prefix}_sel_editor",
        hide_id_column=True,
    )
    with bar_ph.container():
        _render_action_buttons(prefix=prefix, sel=sel, can_add=can_add)


def render_labor_rates_panel(*, key_prefix: str = "labor", show_header: bool = True) -> None:
    """Render labor rate CRUD (embedded in Pricing Guide or standalone)."""
    prefix = key_prefix
    if show_header:
        render_page_header(
            "Labor Rates",
            "Straight-time and overtime defaults for Estimate Cost Builder and job costing.",
        )
    else:
        st.markdown("#### Labor Rates")
        st.caption(
            "Manage default ST/OT rates. New estimate labor lines start with these rates; "
            "saved lines keep the rate stored on the line."
        )

    can_add = current_role() == "admin"
    mode_key = _panel_mode_key(prefix)
    if st.session_state.get(mode_key) in ("add", "edit") and not can_add:
        _clear_panel(prefix)
    elif st.session_state.get(mode_key) == "view" and not can_add:
        _clear_panel(prefix)

    mode = st.session_state.get(mode_key)
    rows = fetch_table("labor_rates", limit=5000, order_by="classification")
    df = pd.DataFrame(rows)

    del_prefix = _delete_prefix(prefix)
    del_open = destructive_confirm_open_key(del_prefix)
    if st.session_state.get(del_open) and not can_add:
        close_destructive_confirmation(del_prefix)
        st.session_state.pop(f"{prefix}_pending_delete_ids", None)
    elif st.session_state.get(del_open) and can_add:
        pending = list(st.session_state.get(f"{prefix}_pending_delete_ids") or [])
        if not pending:
            close_destructive_confirmation(del_prefix)
            st.session_state.pop(f"{prefix}_pending_delete_ids", None)
            st.rerun()
        id_to_label: dict[str, str] = {}
        if not df.empty and "id" in df.columns:
            for _, r in df.iterrows():
                rid = str(r["id"])
                id_to_label[rid] = str(r.get("classification") or "").strip() or rid
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
            "Are you sure you want to delete this labor rate?"
            if n_pending == 1
            else f"Are you sure you want to delete these {n_pending} labor rates?"
        )

        def _on_confirm_delete() -> None:
            for lid in pending:
                try:
                    delete_rows_admin("labor_rates", {"id": lid})
                except Exception as exc:
                    st.error(f"Could not delete {lid}: {exc}")
            st.session_state.pop(f"{prefix}_pending_delete_ids", None)
            clear_selected_ids(_table_key(prefix))
            panel_id = st.session_state.get(_panel_id_key(prefix))
            if panel_id and str(panel_id) in {str(x) for x in pending}:
                _clear_panel(prefix)
            st.success("Labor rate(s) deleted where permitted.")

        def _on_cancel_delete() -> None:
            st.session_state.pop(f"{prefix}_pending_delete_ids", None)

        render_destructive_confirmation(
            key_prefix=del_prefix,
            title="Confirm Delete",
            message=msg,
            confirm_label="Confirm Delete",
            cancel_label="Cancel",
            on_confirm=_on_confirm_delete,
            on_cancel=_on_cancel_delete,
            name_lines=name_lines,
        )

    if st.session_state.pop(f"_{prefix}_do_deactivate", False) and can_add:
        sel_ids = get_selected_ids(_table_key(prefix))
        if sel_ids:
            for lid in sel_ids:
                try:
                    update_rows_admin("labor_rates", {"is_active": False}, {"id": lid})
                except Exception as exc:
                    st.error(f"Could not deactivate {lid}: {exc}")
            clear_selected_ids(_table_key(prefix))
            st.success("Selected labor rates deactivated.")
            st.rerun()

    _render_filter_row(prefix=prefix, df=df)
    filtered = _filtered_df(prefix, df)
    panel_open = bool(mode in ("add", "edit", "view"))

    if panel_open:
        main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
        with main_col:
            _render_table_block(prefix=prefix, filtered=filtered, df=df, can_add=can_add)
        with side_col:
            _render_side_panel(prefix=prefix, mode=str(mode), rows_for_uniq=rows)
    else:
        _render_table_block(prefix=prefix, filtered=filtered, df=df, can_add=can_add)

    if not can_add:
        st.info("Only admin users can add or edit labor rates.")
