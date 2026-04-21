from __future__ import annotations

from functools import lru_cache

import pandas as pd
import streamlit as st

from auth import current_role
from branding import render_header
from db import delete_rows_admin, fetch_one, fetch_table, insert_row, update_rows

try:
    from table_actions import (
        TABLE_KEY_EMPLOYEES,
        TABLE_KEY_PEOPLE,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        set_selected_ids,
    )
except ImportError:
    from app.table_actions import (  # type: ignore
        TABLE_KEY_EMPLOYEES,
        TABLE_KEY_PEOPLE,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        set_selected_ids,
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

_EMP_DELETE_CONFIRM_PREFIX = "employees_delete"


@lru_cache(maxsize=1)
def employees_table_has_email_column() -> bool:
    """True only when ``public.employees.email`` exists (PostgREST schema); cached per process."""
    try:
        fetch_table("employees", columns="id,email", limit=1)
        return True
    except Exception:
        return False


def _employees_email_input_help() -> str:
    if employees_table_has_email_column():
        return "Saved on the **employees** row as ``email``."
    # Email is shown in UI but not stored on employees; linked login email lives on **profiles** / Auth.
    return (
        "Shown for reference only — **employees** has no ``email`` column yet, so this value is not saved here. "
        "For linked accounts, use the **User account** section on the People page to view profile email."
    )


def _money(v) -> str:
    try:
        return f"${float(v or 0):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _clear_employee_mode() -> None:
    st.session_state.pop("employee_mode", None)
    st.session_state.pop("employee_edit_id", None)


@st.dialog("Add Employee")
def add_employee_dialog(*, selection_table_key: str | None = None) -> None:
    st.caption("Job info and pay rates · time tracking / roster")
    n1, n2 = st.columns(2)
    new_name = n1.text_input("Name", key="dlg_emp_add_name")
    new_role = n2.text_input("Role", key="dlg_emp_add_role", placeholder="e.g. Foreman, Welder")
    new_trade = st.text_input("Trade (optional)", key="dlg_emp_add_trade")
    new_email = st.text_input("Email (optional)", key="dlg_emp_add_email")
    r1, r2 = st.columns(2)
    new_hr = r1.number_input("Hourly rate", min_value=0.0, value=0.0, step=0.5, format="%.2f", key="dlg_emp_add_hr")
    new_ot = r2.number_input(
        "Overtime rate (optional)",
        min_value=0.0,
        value=0.0,
        step=0.5,
        format="%.2f",
        key="dlg_emp_add_ot",
        help="Leave 0 to use 1.5 × hourly rate for overtime.",
    )
    new_notes = st.text_area("Notes (optional)", key="dlg_emp_add_notes", height=56)

    st.divider()
    bc, bs = st.columns(2, gap="small")
    with bc:
        if st.button("Cancel", type="secondary", use_container_width=True, key="dlg_emp_add_cancel"):
            st.rerun()
    with bs:
        if st.button("Save", type="primary", use_container_width=True, key="dlg_emp_add_save"):
            if not str(new_name).strip():
                st.error("Name is required.")
                st.stop()
            add_email = str(new_email).strip()
            if employees_table_has_email_column():
                if add_email and "@" not in add_email:
                    st.warning("Email should contain '@'. Fix the address or clear the field before saving.")
                    st.stop()
            payload = {
                "name": str(new_name).strip(),
                "role": str(new_role).strip(),
                "trade": str(new_trade).strip(),
                "hourly_rate": float(new_hr or 0),
                "overtime_rate": float(new_ot) if float(new_ot or 0) > 0 else None,
                "is_active": True,
                "notes": str(new_notes).strip(),
            }
            if employees_table_has_email_column():
                payload["email"] = add_email or None
            row = insert_row("employees", payload)
            new_id = str((row or {}).get("id") or "").strip()
            if new_id:
                tkey = selection_table_key or TABLE_KEY_EMPLOYEES
                sel_val = f"e:{new_id}" if tkey == TABLE_KEY_PEOPLE else new_id
                set_selected_ids(tkey, [sel_val])
            _clear_employee_mode()
            st.toast("Employee added.", icon="✅")
            st.rerun()


def _render_action_buttons(*, sel: list[str], can_edit: bool) -> None:
    """Inline actions: Add (primary), Edit (secondary), Deactivate (warning), Delete (danger)."""
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
                "Add Employee",
                type="primary",
                use_container_width=True,
                disabled=not can_edit,
                key="emp_btn_add",
            ):
                add_employee_dialog()
        with b1:
            if st.button(
                "Edit",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or not one,
                key="emp_btn_edit",
            ):
                st.session_state["employee_mode"] = "edit"
                st.session_state["employee_edit_id"] = str(sel[0])
                st.rerun()
        with b2:
            if st.button(
                "Deactivate",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or none,
                key="emp_btn_deactivate",
            ):
                st.session_state["_emp_do_deactivate"] = True
                st.rerun()
        with b3:
            if st.button(
                "Delete",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or none,
                key="emp_btn_delete",
            ):
                open_destructive_confirmation(_EMP_DELETE_CONFIRM_PREFIX)
                st.session_state["employees_pending_delete_ids"] = [str(x) for x in sel]
                st.rerun()


def _render_edit_form(row: dict) -> None:
    eid = str(row.get("id") or "")
    st.caption(f"ID `{eid[:8]}…`")

    pk = f"emp_ed_{eid}"
    ed_name = st.text_input("Name", value=str(row.get("name") or ""), key=f"{pk}_name")
    ed_email = st.text_input(
        "Email",
        value=str(row.get("email") or ""),
        key=f"user_email_{eid}",
        help=_employees_email_input_help(),
    )
    e2, e3 = st.columns(2)
    ed_role = e2.text_input("Role", value=str(row.get("role") or ""), key=f"{pk}_role")
    ed_trade = e3.text_input("Trade", value=str(row.get("trade") or ""), key=f"{pk}_trade")

    u1, u2 = st.columns(2)
    ot_val = row.get("overtime_rate")
    try:
        ot_default = float(ot_val) if ot_val is not None and str(ot_val).strip() != "" else 0.0
    except (TypeError, ValueError):
        ot_default = 0.0
    ed_hr = u1.number_input(
        "Hourly rate",
        min_value=0.0,
        value=float(row.get("hourly_rate", 0) or 0),
        step=0.5,
        format="%.2f",
        key=f"{pk}_hr",
    )
    ed_ot = u2.number_input(
        "Overtime rate (0 = use 1.5× hourly)",
        min_value=0.0,
        value=ot_default,
        step=0.5,
        format="%.2f",
        key=f"{pk}_ot",
    )
    ed_notes = st.text_area(
        "Notes",
        value=str(row.get("notes") or ""),
        height=56,
        key=f"{pk}_notes",
    )
    ed_active = st.checkbox("Active", value=bool(row.get("is_active", True)), key=f"{pk}_active")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Update Employee", type="primary", use_container_width=True, key=f"{pk}_save"):
            if not str(ed_name).strip():
                st.error("Name is required.")
                st.stop()
            email_val = str(ed_email).strip()
            if employees_table_has_email_column():
                if email_val and "@" not in email_val:
                    st.warning("Email should contain '@'. Fix the address or clear the field before saving.")
                    st.stop()
            payload = {
                "name": str(ed_name).strip(),
                "role": str(ed_role).strip(),
                "trade": str(ed_trade).strip(),
                "hourly_rate": float(ed_hr or 0),
                "overtime_rate": float(ed_ot) if float(ed_ot or 0) > 0 else None,
                "notes": str(ed_notes).strip(),
                "is_active": bool(ed_active),
            }
            if employees_table_has_email_column():
                payload["email"] = email_val or None
            update_rows("employees", payload, {"id": row["id"]})
            _clear_employee_mode()
            st.success("Employee updated.")
            st.rerun()
    with c2:
        if st.button("Cancel", use_container_width=True, key=f"{pk}_cancel"):
            _clear_employee_mode()
            st.rerun()


def _render_employee_side_panel(*, mode: str) -> None:
    """Right column: bordered panel for edit."""
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        if mode == "edit":
            st.markdown("### Edit employee")
            eid = st.session_state.get("employee_edit_id")
            er = fetch_one("employees", {"id": eid}) if eid else None
            if not er:
                st.warning("Employee not found.")
                _clear_employee_mode()
            else:
                _render_edit_form(er)


def _render_employees_main(
    *,
    df: pd.DataFrame,
    can_edit: bool,
) -> None:
    """Main column: filters, table, action bar — no form."""
    if df.empty:
        st.info("No employees yet. Run `sql/008_employees.sql` in Supabase if the table is missing.")
        if can_edit:
            if st.button("Add Employee", type="primary", use_container_width=True, key="emp_empty_add"):
                add_employee_dialog()
        return

    f1, f2 = st.columns([2, 1], gap="small")
    with f1:
        st.markdown(
            '<span class="ips-crud-filter-row-start" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        search = st.text_input("Search", placeholder="Name, role, trade, notes")
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
            "name",
            "email",
            "role",
            "trade",
            "hourly_rate",
            "overtime_rate",
            "is_active",
            "notes",
        ]
        if c in filtered.columns
    ]

    st.caption(
        "Checkbox column on the **left**; selection is stored as **selected_employees_ids**."
    )

    if filtered.empty:
        st.warning("No employees match your filters.")
        if can_edit:
            inject_table_action_styles()
            if st.button("Add Employee", type="primary", use_container_width=True, key="emp_filtered_empty_add"):
                add_employee_dialog()
    elif "id" not in filtered.columns:
        disp = filtered[show_cols].copy()
        if "hourly_rate" in disp.columns:
            disp["hourly_rate"] = disp["hourly_rate"].map(_money)
        if "overtime_rate" in disp.columns:
            disp["overtime_rate"] = disp["overtime_rate"].map(
                lambda x: _money(x) if x is not None and str(x).strip() != "" else "— (1.5× ST)"
            )
        st.dataframe(disp, use_container_width=True, hide_index=True)
    else:
        bar_ph = st.empty()
        _, sel = render_selectable_dataframe(
            filtered,
            table_key=TABLE_KEY_EMPLOYEES,
            id_column="id",
            columns=show_cols,
            editor_key="emp_sel_editor",
        )
        with bar_ph.container():
            _render_action_buttons(sel=sel, can_edit=can_edit)


def render_body() -> None:
    """Full employees CRUD without page header (used by the ``Users`` combined page)."""
    can_edit = current_role() == "admin"
    if st.session_state.get("employee_mode") == "add":
        st.session_state.pop("employee_mode", None)
    mode = st.session_state.get("employee_mode")

    try:
        rows = fetch_table("employees", limit=5000, order_by="name")
    except Exception:
        rows = []
    df = pd.DataFrame(rows)

    # Delete confirmation panel (near top; visibility: employees_delete_confirm_open)
    _emp_del_open = destructive_confirm_open_key(_EMP_DELETE_CONFIRM_PREFIX)
    if st.session_state.get(_emp_del_open) and not can_edit:
        close_destructive_confirmation(_EMP_DELETE_CONFIRM_PREFIX)
        st.session_state.pop("employees_pending_delete_ids", None)
    elif st.session_state.get(_emp_del_open) and can_edit:
        pending = list(st.session_state.get("employees_pending_delete_ids") or [])
        if not pending:
            close_destructive_confirmation(_EMP_DELETE_CONFIRM_PREFIX)
            st.session_state.pop("employees_pending_delete_ids", None)
            st.rerun()
        id_to_name: dict[str, str] = {}
        if not df.empty and "id" in df.columns:
            for _, r in df.iterrows():
                rid = str(r["id"])
                id_to_name[rid] = str(r.get("name") or "").strip() or rid
        name_lines: list[str] = []
        for pid in pending:
            nm = id_to_name.get(pid)
            if nm:
                name_lines.append(nm)
            else:
                short = pid[:10] + "…" if len(pid) > 10 else pid
                name_lines.append(f"(unknown id) {short}")
        n_pending = len(pending)
        msg = (
            "Are you sure you want to delete this employee?"
            if n_pending == 1
            else f"Are you sure you want to delete these {n_pending} employees?"
        )

        def _on_confirm_delete() -> None:
            for eid in pending:
                try:
                    delete_rows_admin("employees", {"id": eid})
                except Exception as exc:
                    st.error(f"Could not delete {eid}: {exc}")
            st.session_state.pop("employees_pending_delete_ids", None)
            clear_selected_ids(TABLE_KEY_EMPLOYEES)
            edit_id = st.session_state.get("employee_edit_id")
            if edit_id and str(edit_id) in {str(x) for x in pending}:
                st.session_state.pop("employee_mode", None)
                st.session_state.pop("employee_edit_id", None)
            st.success("Employee(s) deleted where permitted.")

        def _on_cancel_delete() -> None:
            st.session_state.pop("employees_pending_delete_ids", None)

        render_destructive_confirmation(
            key_prefix=_EMP_DELETE_CONFIRM_PREFIX,
            title="Confirm Delete",
            message=msg,
            confirm_label="Confirm Delete",
            cancel_label="Cancel",
            on_confirm=_on_confirm_delete,
            on_cancel=_on_cancel_delete,
            name_lines=name_lines,
        )

    # Bulk deactivate (from action bar)
    if st.session_state.pop("_emp_do_deactivate", False) and can_edit:
        sel_ids = get_selected_ids(TABLE_KEY_EMPLOYEES)
        if sel_ids:
            for eid in sel_ids:
                try:
                    update_rows("employees", {"is_active": False}, {"id": eid})
                except Exception as exc:
                    st.error(f"Could not deactivate {eid}: {exc}")
            clear_selected_ids(TABLE_KEY_EMPLOYEES)
            st.success("Selected employees deactivated.")
            st.rerun()

    panel_open = bool(can_edit and mode == "edit")

    if panel_open:
        main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
        with main_col:
            _render_employees_main(df=df, can_edit=can_edit)
        with side_col:
            _render_employee_side_panel(mode=str(mode))
    else:
        _render_employees_main(df=df, can_edit=can_edit)

    if not can_edit:
        st.info("Only admin users can manage employees.")


def render() -> None:
    render_header("Employees")
    render_crud_list_subtitle("Search, filter, and manage employee records, roles, and pay rates.")
    render_body()
