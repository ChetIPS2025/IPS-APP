from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from auth import current_role
from branding import render_header
from db import delete_rows_admin, fetch_one, fetch_table, update_rows

try:
    from ui import IPS_NAV_PAGE_KEY
except ImportError:
    from app.ui import IPS_NAV_PAGE_KEY  # type: ignore

try:
    from pages import employees as emp_mod
    from pages import users as usr_mod
except ImportError:
    from app.pages import employees as emp_mod  # type: ignore
    from app.pages import users as usr_mod  # type: ignore

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
    )
except ImportError:
    from ips_crud_list_styles import (  # type: ignore
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        inject_ips_crud_list_styles,
    )

try:
    from app.table_actions import (
        TABLE_KEY_PEOPLE,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )
except ImportError:
    from table_actions import (  # type: ignore
        TABLE_KEY_PEOPLE,
        clear_selected_ids,
        get_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )

_PEOPLE_EMP_DELETE_PREFIX = "people_emp_delete"
_PEOPLE_PANEL_KEY = "people_panel"  # "list" | "detail" | "add_emp" | "add_user"
_USERS_PANEL_MODE = getattr(usr_mod, "_USERS_PANEL_MODE", "users_panel_mode")


def _norm_join(s: str) -> str:
    return " ".join(str(s or "").strip().lower().split())


def _parse_unified_id(uid: str) -> tuple[str | None, str | None]:
    """Return (employee_id, profile_id) from unified row id."""
    u = str(uid or "").strip()
    if u.startswith("m:"):
        rest = u[2:]
        parts = rest.split(":", 1)
        if len(parts) == 2:
            e, p = parts[0].strip(), parts[1].strip()
            return (e or None, p or None)
        return (None, None)
    if u.startswith("e:"):
        return (u[2:].strip() or None, None)
    if u.startswith("p:"):
        return (None, u[2:].strip() or None)
    return (None, None)


def _employee_ids_from_selection(sel: list[str]) -> list[str]:
    out: list[str] = []
    for u in sel:
        eid, _ = _parse_unified_id(u)
        if eid:
            out.append(eid)
    return out


def _build_unified_frame(employees: list[dict[str, Any]], profiles: list[dict[str, Any]]) -> pd.DataFrame:
    """Merge rows where ``profiles.full_name`` matches ``employees.name`` (case-insensitive)."""
    emp_by_name: dict[str, dict[str, Any]] = {}
    for e in employees or []:
        k = _norm_join(str(e.get("name") or ""))
        if k and k not in emp_by_name:
            emp_by_name[k] = e

    matched_emp: set[str] = set()
    rows: list[dict[str, Any]] = []

    for p in profiles or []:
        pid = str(p.get("id") or "").strip()
        if not pid:
            continue
        fn_key = _norm_join(str(p.get("full_name") or ""))
        em = emp_by_name.get(fn_key) if fn_key else None
        eid = str(em.get("id") or "").strip() if isinstance(em, dict) else ""

        if em and eid and eid not in matched_emp:
            matched_emp.add(eid)
            rows.append(
                {
                    "unified_id": f"m:{eid}:{pid}",
                    "Kind": "Linked",
                    "Name": str(p.get("full_name") or em.get("name") or "").strip(),
                    "Email": str(p.get("email") or "").strip(),
                    "Job role": str(em.get("role") or "").strip(),
                    "Trade": str(em.get("trade") or "").strip(),
                    "Hourly": em.get("hourly_rate"),
                    "App role": str(p.get("role") or "").strip(),
                    "Emp active": bool(em.get("is_active", True)),
                    "Acct active": bool(p.get("is_active", True)),
                }
            )
        else:
            rows.append(
                {
                    "unified_id": f"p:{pid}",
                    "Kind": "Account",
                    "Name": str(p.get("full_name") or "").strip(),
                    "Email": str(p.get("email") or "").strip(),
                    "Job role": "",
                    "Trade": "",
                    "Hourly": None,
                    "App role": str(p.get("role") or "").strip(),
                    "Emp active": "",
                    "Acct active": bool(p.get("is_active", True)),
                }
            )

    for e in employees or []:
        eid = str(e.get("id") or "").strip()
        if not eid or eid in matched_emp:
            continue
        rows.append(
            {
                "unified_id": f"e:{eid}",
                "Kind": "Employee",
                "Name": str(e.get("name") or "").strip(),
                "Email": "",
                "Job role": str(e.get("role") or "").strip(),
                "Trade": str(e.get("trade") or "").strip(),
                "Hourly": e.get("hourly_rate"),
                "App role": "",
                "Emp active": bool(e.get("is_active", True)),
                "Acct active": "",
            }
        )

    return pd.DataFrame(rows)


def _apply_people_filters(df: pd.DataFrame, *, search: str, status: str) -> pd.DataFrame:
    out = df.copy()
    if search.strip():
        s = search.strip().lower()
        blob = out.astype(str).apply(lambda col: col.str.lower().str.contains(s, na=False, regex=False))
        out = out[blob.any(axis=1)]
    if status == "Active only":
        def _row_active(r: pd.Series) -> bool:
            ea, aa = r.get("Emp active"), r.get("Acct active")
            ok_e = ea == "" or ea is True or ea is None
            ok_a = aa == "" or aa is True or aa is None
            if isinstance(ea, bool) and isinstance(aa, bool):
                return ea and aa
            if isinstance(ea, bool):
                return ea
            if isinstance(aa, bool):
                return aa
            return True

        out = out[out.apply(_row_active, axis=1)]
    elif status == "Inactive only":

        def _row_inactive(r: pd.Series) -> bool:
            ea, aa = r.get("Emp active"), r.get("Acct active")
            if isinstance(ea, bool) and ea is False:
                return True
            if isinstance(aa, bool) and aa is False:
                return True
            return False

        out = out[out.apply(_row_inactive, axis=1)]
    return out


def _display_df_for_editor(filtered: pd.DataFrame) -> pd.DataFrame:
    disp = filtered.copy()
    if "Hourly" in disp.columns:
        disp["Hourly"] = disp["Hourly"].map(
            lambda v: emp_mod._money(v) if v is not None and str(v).strip() != "" else "—"
        )
    return disp


def _render_people_toolbar(*, sel: list[str], can_edit: bool) -> None:
    inject_ips_crud_list_styles()
    inject_table_action_styles()
    n = len(sel)
    one = n == 1
    emp_ids = _employee_ids_from_selection(sel)
    stored = str(st.session_state.get(_PEOPLE_PANEL_KEY, "list"))
    back_disabled = stored == "list"

    with st.container(border=True):
        st.markdown('<div class="ips-crud-toolbar-root"></div>', unsafe_allow_html=True)
        left, b0, b1, b2 = st.columns([1.05, 1, 1, 1], gap="small")
        with left:
            st.markdown(
                f'<span class="ips-ta-summary"><span class="ips-ta-num">{n}</span> selected</span>',
                unsafe_allow_html=True,
            )
        with b0:
            if st.button(
                "Add employee",
                type="primary",
                use_container_width=True,
                disabled=not can_edit,
                key="people_btn_add_emp",
            ):
                st.session_state.pop(_USERS_PANEL_MODE, None)
                st.session_state[_PEOPLE_PANEL_KEY] = "add_emp"
                st.rerun()
        with b1:
            if st.button(
                "Add user",
                type="primary",
                use_container_width=True,
                disabled=not can_edit,
                key="people_btn_add_user",
            ):
                st.session_state[_PEOPLE_PANEL_KEY] = "add_user"
                st.session_state[_USERS_PANEL_MODE] = "add"
                emp_mod._clear_employee_mode()
                st.rerun()
        with b2:
            if st.button(
                "Edit details",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or not one,
                key="people_btn_edit_detail",
            ):
                st.session_state[_PEOPLE_PANEL_KEY] = "detail"
                st.rerun()

        r2b0, r2b1, r2b2 = st.columns(3, gap="small")
        with r2b0:
            if st.button(
                "Deactivate employees",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or not emp_ids,
                key="people_btn_deactivate",
            ):
                for eid in emp_ids:
                    try:
                        update_rows("employees", {"is_active": False}, {"id": eid})
                    except Exception as exc:
                        st.error(f"Could not deactivate {eid}: {exc}")
                clear_selected_ids(TABLE_KEY_PEOPLE)
                st.success("Deactivated where permitted.")
                st.rerun()
        with r2b1:
            if st.button(
                "Delete employees",
                type="secondary",
                use_container_width=True,
                disabled=not can_edit or not emp_ids,
                key="people_btn_delete",
            ):
                open_destructive_confirmation(_PEOPLE_EMP_DELETE_PREFIX)
                st.session_state["people_pending_emp_delete_ids"] = list(emp_ids)
                st.rerun()
        with r2b2:
            if st.button(
                "Back to list",
                type="secondary",
                use_container_width=True,
                disabled=back_disabled,
                key="people_btn_back",
            ):
                st.session_state[_PEOPLE_PANEL_KEY] = "list"
                st.session_state.pop(_USERS_PANEL_MODE, None)
                emp_mod._clear_employee_mode()
                clear_selected_ids(TABLE_KEY_PEOPLE)
                st.rerun()


def _render_delete_confirm(*, df: pd.DataFrame) -> None:
    open_k = destructive_confirm_open_key(_PEOPLE_EMP_DELETE_PREFIX)
    if not st.session_state.get(open_k):
        return
    pending = list(st.session_state.get("people_pending_emp_delete_ids") or [])
    if not pending:
        close_destructive_confirmation(_PEOPLE_EMP_DELETE_PREFIX)
        st.session_state.pop("people_pending_emp_delete_ids", None)
        st.rerun()
        return

    id_to_name: dict[str, str] = {}
    if not df.empty and "unified_id" in df.columns:
        for _, r in df.iterrows():
            uid = str(r.get("unified_id") or "")
            eid, _ = _parse_unified_id(uid)
            if eid:
                id_to_name[eid] = str(r.get("Name") or "").strip() or eid

    name_lines: list[str] = []
    for pid in pending:
        nm = id_to_name.get(pid)
        name_lines.append(nm or pid[:10] + "…")

    def _on_confirm() -> None:
        for eid in pending:
            try:
                delete_rows_admin("employees", {"id": eid})
            except Exception as exc:
                st.error(f"Could not delete {eid}: {exc}")
        st.session_state.pop("people_pending_emp_delete_ids", None)
        close_destructive_confirmation(_PEOPLE_EMP_DELETE_PREFIX)
        clear_selected_ids(TABLE_KEY_PEOPLE)
        emp_mod._clear_employee_mode()
        st.success("Deleted where permitted.")
        st.rerun()

    def _on_cancel() -> None:
        st.session_state.pop("people_pending_emp_delete_ids", None)
        close_destructive_confirmation(_PEOPLE_EMP_DELETE_PREFIX)

    render_destructive_confirmation(
        key_prefix=_PEOPLE_EMP_DELETE_PREFIX,
        title="Confirm delete",
        message=f"Delete **{len(pending)}** employee record(s)? This cannot be undone.",
        confirm_label="Confirm delete",
        cancel_label="Cancel",
        on_confirm=_on_confirm,
        on_cancel=_on_cancel,
        name_lines=name_lines,
    )


def _render_right_panel(
    *,
    panel: str,
    sel: list[str],
    profiles: list[dict[str, Any]],
) -> None:
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)

        if panel == "add_emp":
            st.markdown("### Add employee")
            st.caption("Pay rates and job role for time tracking / PM matrix.")
            emp_mod._render_add_form()
            return

        if panel == "add_user":
            st.markdown("### Add user account")
            emails = {usr_mod._normalize_email(str(u.get("email", ""))) for u in profiles if u.get("email")}
            usr_mod._render_add_user_panel(
                existing_emails=emails,
                clear_selection_table_key=TABLE_KEY_PEOPLE,
            )
            return

        if len(sel) != 1:
            st.markdown("### Details")
            st.caption(
                "Select **one** row, then **Edit details** in the toolbar, or use **Add employee** / **Add user**."
            )
            return

        uid = sel[0]
        eid, pid = _parse_unified_id(uid)
        st.markdown("### Edit selected")
        st.caption(f"Row `{uid[:18]}…`" if len(uid) > 18 else f"Row `{uid}`")

        if eid:
            row = fetch_one("employees", {"id": eid})
            if row:
                st.markdown("##### Employee")
                emp_mod._render_edit_form(row)
            else:
                st.warning("Employee record not found.")

        if pid:
            prow = usr_mod._fetch_profile_row(pid)
            if prow:
                st.markdown("##### User account")
                usr_mod._render_edit_user_panel(
                    profile_row=prow,
                    clear_selection_table_key=TABLE_KEY_PEOPLE,
                )
            else:
                st.warning("Profile not found.")


def render() -> None:
    """Unified roster: employees + login profiles, with shared filters and a single detail panel."""
    render_header("People")

    if current_role() != "admin":
        st.error("Admin access required.")
        return

    inject_ips_crud_list_styles()

    if st.session_state.get(_PEOPLE_PANEL_KEY) == "detail":
        if len(get_selected_ids(TABLE_KEY_PEOPLE)) != 1:
            st.session_state[_PEOPLE_PANEL_KEY] = "list"

    try:
        employees = list(fetch_table("employees", limit=5000, order_by="name") or [])
    except Exception as exc:
        st.error(f"Could not load employees: {exc}")
        employees = []

    try:
        profiles = list(fetch_table("profiles", limit=1000, order_by="email") or [])
    except Exception as exc:
        st.error(f"Could not load profiles: {exc}")
        profiles = []

    st.caption(
        "One directory: **Employee** rows (time tracking), **Account** rows (sign-in), and **Linked** when "
        "the profile **full name** matches the employee **name** (case-insensitive)."
    )

    unified = _build_unified_frame(employees, profiles)

    _render_delete_confirm(df=unified)

    f1, f2 = st.columns([2, 1], gap="small")
    with f1:
        st.text_input("Search", placeholder="Name, email, roles, kind…", key="people_search")
    with f2:
        st.selectbox("Status", ["All", "Active only", "Inactive only"], key="people_status_filter")

    search = str(st.session_state.get("people_search", "") or "")
    status = str(st.session_state.get("people_status_filter", "All") or "All")
    filtered = _apply_people_filters(unified, search=search, status=status)

    main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)

    with main_col:
        if filtered.empty:
            st.info("No people match your filters (or the directory is empty).")
            inject_table_action_styles()
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Add employee", type="primary", use_container_width=True, key="people_empty_add_emp"):
                    st.session_state[_PEOPLE_PANEL_KEY] = "add_emp"
                    st.rerun()
            with c2:
                if st.button("Add user", type="primary", use_container_width=True, key="people_empty_add_user"):
                    st.session_state[_PEOPLE_PANEL_KEY] = "add_user"
                    st.session_state[_USERS_PANEL_MODE] = "add"
                    st.rerun()
        else:
            show_cols = [c for c in filtered.columns if c != "unified_id"]
            disp = _display_df_for_editor(filtered)
            bar_ph = st.empty()
            _, sel = render_selectable_dataframe(
                disp,
                table_key=TABLE_KEY_PEOPLE,
                id_column="unified_id",
                columns=show_cols,
                editor_key="people_unified_editor",
            )
            with bar_ph.container():
                _render_people_toolbar(sel=sel, can_edit=True)

    with side_col:
        sel_ids = get_selected_ids(TABLE_KEY_PEOPLE)
        stored_panel = str(st.session_state.get(_PEOPLE_PANEL_KEY, "list"))
        if stored_panel in ("add_emp", "add_user"):
            eff_panel = stored_panel
        elif stored_panel == "detail" and len(sel_ids) == 1:
            eff_panel = "detail"
        else:
            eff_panel = "list"
        _render_right_panel(panel=eff_panel, sel=sel_ids, profiles=profiles)

    st.divider()
    with st.expander("Database overview (legacy Admin)", expanded=False):
        st.caption("Profiles, attachments, and estimate revisions.")
        if st.button("Open Admin overview", key="people_nav_to_admin"):
            st.session_state[IPS_NAV_PAGE_KEY] = "Admin"
            st.rerun()
