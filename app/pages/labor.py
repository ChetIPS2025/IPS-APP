from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.branding import render_header
    from app.db import delete_rows_admin, fetch_one, fetch_table, insert_row, update_rows_admin
    from app.table_actions import (
        TABLE_KEY_LABOR,
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
        TABLE_KEY_LABOR,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )

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

_LABOR_DELETE_CONFIRM_PREFIX = "labor_delete"


def make_unique_classification(base_value: str, rows) -> str:
    existing = {str(r.get("classification", "")).strip().upper() for r in rows}
    if base_value.upper() not in existing:
        return base_value

    i = 2
    while True:
        candidate = f"{base_value}_{i}"
        if candidate.upper() not in existing:
            return candidate
        i += 1


def _money(v) -> str:
    try:
        return f"${float(v or 0):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _migrate_legacy_labor_session() -> None:
    if st.session_state.get("labor_edit_id"):
        st.session_state["labor_panel_mode"] = "edit"
        st.session_state["labor_panel_id"] = st.session_state.pop("labor_edit_id")
    if st.session_state.get("labor_view_id"):
        st.session_state["labor_panel_mode"] = "view"
        st.session_state["labor_panel_id"] = st.session_state.pop("labor_view_id")


def _clear_labor_panel() -> None:
    st.session_state.pop("labor_panel_mode", None)
    st.session_state.pop("labor_panel_id", None)


def _render_labor_action_buttons(*, sel: list[str], can_add: bool) -> None:
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
                key="labor_btn_add",
            ):
                st.session_state["labor_panel_mode"] = "add"
                st.session_state.pop("labor_panel_id", None)
                st.rerun()
        with b1:
            if st.button(
                "Edit",
                type="secondary",
                use_container_width=True,
                disabled=not can_add or not one,
                key="labor_btn_edit",
            ):
                st.session_state["labor_panel_mode"] = "edit"
                st.session_state["labor_panel_id"] = str(sel[0])
                st.rerun()
        with b2:
            if st.button(
                "Deactivate",
                type="secondary",
                use_container_width=True,
                disabled=not can_add or none,
                key="labor_btn_deactivate",
            ):
                st.session_state["_labor_do_deactivate"] = True
                st.rerun()
        with b3:
            if st.button(
                "Delete",
                type="secondary",
                use_container_width=True,
                disabled=not can_add or none,
                key="labor_btn_delete",
            ):
                open_destructive_confirmation(_LABOR_DELETE_CONFIRM_PREFIX)
                st.session_state["labor_pending_delete_ids"] = [str(x) for x in sel]
                st.rerun()


def _render_add_form(*, rows_for_uniq: list) -> None:
    classification = st.text_input("Labor Classification", key="labor_add_class")
    c1, c2 = st.columns(2)
    st_rate = c1.number_input(
        "Straight Time Rate",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        key="labor_add_st",
    )
    ot_rate = c2.number_input(
        "Overtime Rate",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        key="labor_add_ot",
    )
    is_active = st.checkbox("Active", value=True, key="labor_add_active")

    s1, s2 = st.columns(2)
    with s1:
        if st.button("Save Labor Rate", type="primary", use_container_width=True, key="labor_add_save"):
            if not str(classification).strip():
                st.error("Labor Classification required.")
                st.stop()
            base_classification = str(classification).strip()
            final_classification = make_unique_classification(base_classification, rows_for_uniq)
            payload = {
                "classification": final_classification,
                "st_rate": float(st_rate or 0),
                "ot_rate": float(ot_rate or 0),
                "is_active": bool(is_active),
            }
            try:
                insert_row("labor_rates", payload)
            except Exception as exc:
                st.error(f"Could not add labor rate: {exc}")
                st.stop()
            _clear_labor_panel()
            st.success(f"Added {final_classification}.")
            st.rerun()
    with s2:
        if st.button("Cancel", use_container_width=True, key="labor_add_cancel"):
            _clear_labor_panel()
            st.rerun()


def _render_edit_form(row: dict, rows_for_uniq: list) -> None:
    lid = str(row.get("id") or "")
    st.caption(f"ID `{lid[:8]}…`")
    pk = f"labor_ed_{lid}"

    classification = st.text_input(
        "Labor Classification",
        value=str(row.get("classification") or ""),
        key=f"{pk}_class",
    )
    c1, c2 = st.columns(2)
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

    u1, u2 = st.columns(2)
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
            payload = {
                "classification": final_classification,
                "st_rate": float(st_rate or 0),
                "ot_rate": float(ot_rate or 0),
                "is_active": bool(is_active),
            }
            try:
                update_rows_admin("labor_rates", payload, {"id": row["id"]})
            except Exception as exc:
                st.error(f"Could not update: {exc}")
                st.stop()
            _clear_labor_panel()
            st.success("Labor rate updated.")
            st.rerun()
    with u2:
        if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
            _clear_labor_panel()
            st.rerun()


def _render_view_panel(row: dict) -> None:
    st.markdown(f"**Classification:** {row.get('classification') or '—'}")
    st.markdown(f"**Straight time:** {_money(row.get('st_rate'))}")
    st.markdown(f"**Overtime:** {_money(row.get('ot_rate'))}")
    active = row.get("is_active")
    st.markdown(f"**Status:** {'Active' if active else 'Inactive'}")
    if st.button("Close", use_container_width=True, key="labor_view_close"):
        _clear_labor_panel()
        st.rerun()


def _render_labor_side_panel(*, mode: str, rows_for_uniq: list) -> None:
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        if mode == "add":
            st.markdown("### Add labor rate")
            _render_add_form(rows_for_uniq=rows_for_uniq)
        elif mode == "edit":
            st.markdown("### Edit labor rate")
            eid = st.session_state.get("labor_panel_id")
            er = fetch_one("labor_rates", {"id": eid}) if eid else None
            if not er:
                st.warning("Labor rate not found.")
                _clear_labor_panel()
            else:
                _render_edit_form(er, rows_for_uniq)
        elif mode == "view":
            st.markdown("### Labor rate")
            vid = st.session_state.get("labor_panel_id")
            vr = fetch_one("labor_rates", {"id": vid}) if vid else None
            if not vr:
                st.warning("Labor rate not found.")
                _clear_labor_panel()
            else:
                _render_view_panel(vr)


def _render_labor_main(*, df: pd.DataFrame, can_add: bool) -> None:
    if df.empty:
        st.info("No labor rates found.")
        if can_add:
            inject_ips_crud_list_styles()
            if st.button("Add Labor Rate", type="primary", key="labor_empty_add"):
                st.session_state["labor_panel_mode"] = "add"
                st.session_state.pop("labor_panel_id", None)
                st.rerun()
        return

    f1, f2 = st.columns([2, 1], gap="small")
    with f1:
        st.markdown(
            '<span class="ips-crud-filter-row-start" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        search = st.text_input(
            "Search",
            placeholder="Search classification, rates, status",
        )
    active_options = ["All", "Active only", "Inactive only"]
    selected_active = f2.selectbox("Status", active_options)

    filtered = df.copy()
    if "is_active" in filtered.columns:
        if selected_active == "Active only":
            filtered = filtered[filtered["is_active"] == True]
        elif selected_active == "Inactive only":
            filtered = filtered[filtered["is_active"] == False]

    if search.strip():
        s = search.strip().lower()
        mask = filtered.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False))
        filtered = filtered[mask.any(axis=1)]

    show_cols = [
        c
        for c in [
            "classification",
            "st_rate",
            "ot_rate",
            "is_active",
        ]
        if c in filtered.columns
    ]

    st.caption(
        "Checkbox column on the **left**; selection is stored as **selected_labor_ids**."
    )

    if filtered.empty:
        st.warning("No labor rates match your filters.")
        if can_add:
            inject_table_action_styles()
            if st.button("Add Labor Rate", type="primary", key="labor_filtered_empty_add"):
                st.session_state["labor_panel_mode"] = "add"
                st.session_state.pop("labor_panel_id", None)
                st.rerun()
    elif "id" not in filtered.columns:
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)
    else:
        bar_ph = st.empty()
        _, sel = render_selectable_dataframe(
            filtered,
            table_key=TABLE_KEY_LABOR,
            id_column="id",
            columns=show_cols,
            editor_key="labor_sel_editor",
        )
        with bar_ph.container():
            _render_labor_action_buttons(sel=sel, can_add=can_add)


def render() -> None:
    _migrate_legacy_labor_session()

    render_header("Labor Rates")
    render_crud_list_subtitle(
        "Manage straight-time and overtime classification rates used in estimates and job costing."
    )

    can_add = current_role() == "admin"
    if st.session_state.get("labor_panel_mode") in ("add", "edit") and not can_add:
        _clear_labor_panel()
    elif st.session_state.get("labor_panel_mode") == "view" and not can_add:
        _clear_labor_panel()

    mode = st.session_state.get("labor_panel_mode")

    rows = fetch_table("labor_rates", limit=5000, order_by="classification")
    df = pd.DataFrame(rows)

    _lab_del_open = destructive_confirm_open_key(_LABOR_DELETE_CONFIRM_PREFIX)
    if st.session_state.get(_lab_del_open) and not can_add:
        close_destructive_confirmation(_LABOR_DELETE_CONFIRM_PREFIX)
        st.session_state.pop("labor_pending_delete_ids", None)
    elif st.session_state.get(_lab_del_open) and can_add:
        pending = list(st.session_state.get("labor_pending_delete_ids") or [])
        if not pending:
            close_destructive_confirmation(_LABOR_DELETE_CONFIRM_PREFIX)
            st.session_state.pop("labor_pending_delete_ids", None)
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
            st.session_state.pop("labor_pending_delete_ids", None)
            clear_selected_ids(TABLE_KEY_LABOR)
            panel_id = st.session_state.get("labor_panel_id")
            if panel_id and str(panel_id) in {str(x) for x in pending}:
                _clear_labor_panel()
            st.success("Labor rate(s) deleted where permitted.")

        def _on_cancel_delete() -> None:
            st.session_state.pop("labor_pending_delete_ids", None)

        render_destructive_confirmation(
            key_prefix=_LABOR_DELETE_CONFIRM_PREFIX,
            title="Confirm Delete",
            message=msg,
            confirm_label="Confirm Delete",
            cancel_label="Cancel",
            on_confirm=_on_confirm_delete,
            on_cancel=_on_cancel_delete,
            name_lines=name_lines,
        )

    if st.session_state.pop("_labor_do_deactivate", False) and can_add:
        sel_ids = get_selected_ids(TABLE_KEY_LABOR)
        if sel_ids:
            for lid in sel_ids:
                try:
                    update_rows_admin("labor_rates", {"is_active": False}, {"id": lid})
                except Exception as exc:
                    st.error(f"Could not deactivate {lid}: {exc}")
            clear_selected_ids(TABLE_KEY_LABOR)
            st.success("Selected labor rates deactivated.")
            st.rerun()

    panel_open = bool(mode in ("add", "edit", "view"))

    if panel_open:
        main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
        with main_col:
            _render_labor_main(df=df, can_add=can_add)
        with side_col:
            _render_labor_side_panel(mode=str(mode), rows_for_uniq=rows)
    else:
        _render_labor_main(df=df, can_add=can_add)

    if not can_add:
        st.info("Only admin users can add or edit labor rates.")
