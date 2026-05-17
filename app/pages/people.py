from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from auth import current_role
from datetime import datetime

try:
    from app.ui.page_shell import render_page_header
except ImportError:
    from ui.page_shell import render_page_header  # type: ignore
from db import (
    delete_rows_admin,
    fetch_one,
    fetch_table,
    fetch_table_admin,
    get_admin_client,
    invite_auth_user,
    resend_invite_by_email,
    update_auth_user_email_admin,
    update_rows,
    update_rows_admin,
)

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
_PEOPLE_UNLINKED_LOGIN_DELETE_PREFIX = "people_unlinked_login_delete"
_PEOPLE_PANEL_KEY = "people_panel"  # "list" | "detail" | "add_emp" | "add_user"
_USERS_PANEL_MODE = getattr(usr_mod, "_USERS_PANEL_MODE", "users_panel_mode")


def _norm_join(s: str) -> str:
    return " ".join(str(s or "").strip().lower().split())


def _people_col_norm_token(name: str) -> str:
    """Normalize header for matching raw vs display spellings (e.g. ``Acct active`` vs ``Acct Active``)."""
    return "".join(ch.lower() for ch in str(name) if ch.isalnum())


# Never show ``unified_id`` in the grid; it must stay on the dataframe for ``id_column`` / selection.
HIDDEN_COLUMNS: frozenset[str] = frozenset({"unified_id"})
HIDDEN_FIELDS = HIDDEN_COLUMNS  # alias: visible-column filter + docs

# Also hidden by normalized header token (spellings like ``Acct active`` / ``Unified ID``).
_PEOPLE_TABLE_HIDDEN_TOKENS: frozenset[str] = frozenset(
    {
        "unifiedid",
        "acctactive",
        "empactive",
        "trade",
        "kind",
        "loginenabled",
        "mustresetpassword",
        "createdat",
        "phonenumber",
    }
)


def _people_visible_table_columns(columns: pd.Index | list[str]) -> list[str]:
    """Columns shown in the selectable table: preferred order, excluding internal / noisy fields."""
    col_list = [str(c) for c in columns]
    kept = [
        c
        for c in col_list
        if c not in HIDDEN_FIELDS and _people_col_norm_token(c) not in _PEOPLE_TABLE_HIDDEN_TOKENS
    ]
    # Visible columns (browsing only): hide internal ids/flags and login mechanics.
    preferred = ["Name", "Email", "Employee Job Role", "Hourly rate", "Access Role", "Is active"]
    ordered = [c for c in preferred if c in kept]
    tail = [c for c in kept if c not in ordered]
    return ordered + tail


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
    """Build an employee-primary directory with attached login/access fields by email."""

    def _norm_email(v: object) -> str:
        return " ".join(str(v or "").strip().lower().split())

    prof_by_email: dict[str, dict[str, Any]] = {}
    for p in profiles or []:
        em = _norm_email(p.get("email"))
        if em and em not in prof_by_email:
            prof_by_email[em] = p

    rows: list[dict[str, Any]] = []
    for e in employees or []:
        eid = str(e.get("id") or "").strip()
        if not eid:
            continue
        e_email = str(e.get("email") or "").strip()
        e_email_norm = _norm_email(e_email)

        prof = prof_by_email.get(e_email_norm) if e_email_norm else None
        if prof:
            raw_role = prof.get("role")
            role_norm = str(raw_role or "").strip().lower()
            access_role = "employee" if not role_norm else role_norm
            login_enabled = True
            must_reset_password = bool(prof.get("must_reset_password", False))
            acct_active = bool(prof.get("is_active", True))
        else:
            access_role = "No login"
            login_enabled = False
            must_reset_password = False
            acct_active = bool(e.get("is_active", True))

        rows.append(
            {
                "unified_id": f"e:{eid}",
                "kind": "Employee",
                "name": str(e.get("name") or "").strip(),
                "email": e_email,
                "employee_job_role": str(e.get("role") or "").strip(),
                "hourly_rate": e.get("hourly_rate"),
                "access_role": access_role,
                "login_enabled": bool(login_enabled),
                "must_reset_password": bool(must_reset_password),
                "is_active": bool(acct_active),
                "emp_is_active": bool(e.get("is_active", True)),
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
            ea, aa = r.get("emp_is_active"), r.get("is_active")
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
            ea, aa = r.get("emp_is_active"), r.get("is_active")
            if isinstance(ea, bool) and ea is False:
                return True
            if isinstance(aa, bool) and aa is False:
                return True
            return False

        out = out[out.apply(_row_inactive, axis=1)]
    return out


def _display_df_for_editor(filtered: pd.DataFrame) -> pd.DataFrame:
    disp = filtered.copy()
    if "hourly_rate" in disp.columns:
        disp["hourly_rate"] = disp["hourly_rate"].map(
            lambda v: emp_mod._money(v) if v is not None and str(v).strip() != "" else "—"
        )
    if "created_at" in disp.columns:
        def _fmt(v: object) -> str:
            if v is None or v == "":
                return ""
            if isinstance(v, datetime):
                return v.isoformat(sep=" ", timespec="seconds")
            return str(v)
        disp["created_at"] = disp["created_at"].map(_fmt)

    # Presentation-only column labels (keep internal keys stable for selection + filters).
    rename = {
        "kind": "Kind",
        "name": "Name",
        "email": "Email",
        "employee_job_role": "Employee Job Role",
        "access_role": "Access Role",
        "hourly_rate": "Hourly rate",
        "login_enabled": "Login enabled",
        "must_reset_password": "Must reset password",
        "is_active": "Is active",
    }
    disp.rename(columns={k: v for k, v in rename.items() if k in disp.columns}, inplace=True)
    return disp


def _delete_login_account_admin(*, user_id: str) -> None:
    uid = str(user_id or "").strip()
    if not uid:
        raise RuntimeError("Missing user id.")

    admin = get_admin_client()
    fn = getattr(admin.auth.admin, "delete_user", None)
    if fn is None:
        raise RuntimeError("Supabase Admin API delete_user is not available in this client.")
    try:
        fn(uid)
    except TypeError:
        fn({"uid": uid})

    # Best-effort cleanup of the linked profile row too.
    try:
        delete_rows_admin("profiles", {"id": uid})
    except Exception:
        pass


def _render_people_toolbar(
    *,
    sel: list[str],
    can_edit: bool,
    profiles: list[dict[str, Any]],
) -> None:
    inject_ips_crud_list_styles()
    inject_table_action_styles()
    n = len(sel)
    one = n == 1
    emp_ids = _employee_ids_from_selection(sel)
    stored = str(st.session_state.get(_PEOPLE_PANEL_KEY, "list"))
    back_disabled = stored == "list"

    with st.container(border=True):
        st.markdown('<div class="ips-crud-toolbar-root"></div>', unsafe_allow_html=True)
        left, b0, b2 = st.columns([1.2, 1, 1], gap="small")
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
                emp_mod.add_employee_dialog(selection_table_key=TABLE_KEY_PEOPLE)
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

        if len(sel) != 1:
            st.markdown("### Details")
            st.caption(
                "Select **one** row, then **Edit details** in the toolbar, or use **Add employee** / **Add user**."
            )
            return

        edit_mode = str(panel or "list") == "detail"

        uid = sel[0]
        eid, _ = _parse_unified_id(uid)
        st.markdown("### Edit selected" if edit_mode else "### Details")
        st.caption(f"Row `{uid[:18]}…`" if len(uid) > 18 else f"Row `{uid}`")

        if not eid:
            st.warning("Employee record not found.")
            return

        row = fetch_one("employees", {"id": eid})
        if not row:
            st.warning("Employee record not found.")
            return

        st.markdown("##### Employee")
        employees_has_email = False
        try:
            employees_has_email = bool(emp_mod.employees_table_has_email_column())
        except Exception:
            employees_has_email = False

        pk = f"people_emp_{eid}"
        ed_name = st.text_input(
            "Name",
            value=str(row.get("name") or ""),
            disabled=not edit_mode,
            key=f"{pk}_name",
        )
        ed_email = st.text_input(
            "Email",
            value=str(row.get("email") or ""),
            disabled=(not edit_mode) or (not employees_has_email),
            help=(
                "Changing email affects login linkage (match is by email). "
                "If employees.email is not enabled in the database yet, this field cannot be saved."
            ),
            key=f"{pk}_email",
        )
        ed_phone = st.text_input(
            "Phone number",
            value=str(row.get("phone_number") or ""),
            disabled=not edit_mode,
            help="Optional. Used for OTP login if linked to a login/profile.",
            key=f"{pk}_phone",
        )
        c1, c2 = st.columns(2, gap="small")
        ed_job_role = c1.text_input(
            "Employee Job Role",
            value=str(row.get("role") or ""),
            disabled=not edit_mode,
            key=f"{pk}_job_role",
        )
        ed_hr = c2.number_input(
            "Hourly rate",
            min_value=0.0,
            value=float(row.get("hourly_rate", 0) or 0),
            step=0.5,
            format="%.2f",
            disabled=not edit_mode,
            key=f"{pk}_hr",
        )

        # Linked login/profile (by email or phone)
        prof: dict[str, Any] | None = None
        prof_id: str | None = None
        prof_email: str = ""
        emp_email_norm = " ".join(str(ed_email or "").strip().lower().split())
        emp_phone_norm = "".join(ch for ch in str(ed_phone or "").strip() if ch.isdigit() or ch == "+")
        emp_phone_digits = "".join(ch for ch in emp_phone_norm if ch.isdigit())
        if emp_phone_norm.startswith("+"):
            emp_phone_norm = "+" + emp_phone_digits
        elif len(emp_phone_digits) == 10:
            emp_phone_norm = "+1" + emp_phone_digits
        else:
            emp_phone_norm = emp_phone_digits
        if emp_email_norm:
            for p in profiles or []:
                p_em = " ".join(str(p.get("email") or "").strip().lower().split())
                if p_em and p_em == emp_email_norm:
                    prof = p
                    prof_id = str(p.get("id") or "").strip() or None
                    prof_email = str(p.get("email") or "").strip()
                    break
        if (not prof) and emp_phone_norm:
            for p in profiles or []:
                p_ph = "".join(ch for ch in str(p.get("phone_number") or "").strip() if ch.isdigit() or ch == "+")
                p_digits = "".join(ch for ch in p_ph if ch.isdigit())
                if p_ph.startswith("+"):
                    p_ph = "+" + p_digits
                elif len(p_digits) == 10:
                    p_ph = "+1" + p_digits
                else:
                    p_ph = p_digits
                if p_ph and p_ph == emp_phone_norm:
                    prof = p
                    prof_id = str(p.get("id") or "").strip() or None
                    prof_email = str(p.get("email") or "").strip()
                    break

        st.divider()
        st.markdown("##### Access / Login")
        st.caption("Employee Job Role = payroll/work role · Access Role = app permissions")

        role_opts = ["admin", "manager", "employee", "viewer"]
        if prof:
            cur_role = str(prof.get("role") or "").strip().lower() or "employee"
            if cur_role not in role_opts:
                cur_role = "employee"
            access_role = st.selectbox("Access Role", role_opts, index=role_opts.index(cur_role), key=f"{pk}_access_role")
            must_reset = st.checkbox(
                "Must reset password",
                value=bool(prof.get("must_reset_password", False)),
                key=f"{pk}_mrpw",
            )
            acct_active = st.checkbox(
                "Is active",
                value=bool(prof.get("is_active", True)),
                key=f"{pk}_acct_active",
            )
            st.info(
                "Changing email for a login user may require updating **Supabase Auth** email too. "
                "This screen will update authentication email and may require re-login."
            )
            b0, b1 = st.columns(2, gap="small")
            with b0:
                if st.button(
                    "Resend Invite",
                    use_container_width=True,
                    disabled=not edit_mode,
                    key=f"{pk}_resend",
                ):
                    try:
                        resend_invite_by_email(email=prof_email)
                        st.success("Invite sent.")
                    except Exception as exc:
                        st.error("Could not resend invite.")
                        with st.expander("Technical details"):
                            st.code(repr(exc), language="text")
            with b1:
                if st.button(
                    "Save changes",
                    type="primary",
                    use_container_width=True,
                    disabled=not edit_mode,
                    key=f"{pk}_save",
                ):
                    try:
                        old_emp_email = str(row.get("email") or "").strip()
                        old_prof_email = str(prof_email or "").strip()
                        new_email = str(ed_email or "").strip()
                        email_changed = bool(employees_has_email) and (new_email.lower() != old_emp_email.lower())

                        # If linked login exists and email changes, update Auth email first to avoid partial DB updates
                        # when Auth update fails.
                        if email_changed and prof_id:
                            update_auth_user_email_admin(user_id=str(prof_id), new_email=new_email)

                        emp_payload = {
                            "name": str(ed_name or "").strip(),
                            "role": str(ed_job_role or "").strip(),
                            "hourly_rate": float(ed_hr or 0),
                        }
                        if employees_has_email:
                            emp_payload["email"] = str(ed_email or "").strip() or None
                        if str(ed_phone or "").strip():
                            emp_payload["phone_number"] = str(ed_phone or "").strip()
                        else:
                            emp_payload["phone_number"] = None
                        update_rows("employees", emp_payload, {"id": eid})
                        if prof_id:
                            prof_payload: dict[str, Any] = {
                                "role": str(access_role),
                                "must_reset_password": bool(must_reset),
                                "is_active": bool(acct_active),
                            }
                            if employees_has_email:
                                prof_payload["email"] = str(ed_email or "").strip() or None
                            # Keep profile phone in sync when column exists.
                            prof_payload["phone_number"] = str(ed_phone or "").strip() or None
                            try:
                                update_rows_admin("profiles", prof_payload, {"id": prof_id})
                            except Exception as exc:
                                if "phone" in str(exc).lower() and ("column" in str(exc).lower() or "does not exist" in str(exc).lower()):
                                    # Phone column missing; retry without it.
                                    prof_payload.pop("phone_number", None)
                                    update_rows_admin("profiles", prof_payload, {"id": prof_id})
                                else:
                                    raise
                        st.success("Saved.")
                        st.rerun()
                    except Exception as exc:
                        # Best-effort rollback if Auth email was updated but later DB update failed.
                        try:
                            if "email_changed" in locals() and email_changed and "prof_id" in locals() and prof_id:
                                if "old_prof_email" in locals() and old_prof_email and ("update_rows" in str(exc) or "profiles" in str(exc) or "employees" in str(exc)):
                                    update_auth_user_email_admin(user_id=str(prof_id), new_email=old_prof_email)
                        except Exception:
                            pass
                        st.error("Could not save changes.")
                        with st.expander("Technical details"):
                            st.code(repr(exc), language="text")
        else:
            st.text_input("Access Role", value="No login", disabled=True, key=f"{pk}_no_login_role")
            st.checkbox("Login enabled", value=False, disabled=True, key=f"{pk}_no_login_enabled")
            if st.button(
                "Enable Login / Send Invite",
                type="primary",
                use_container_width=True,
                disabled=not edit_mode,
                key=f"{pk}_enable_login",
            ):
                if not employees_has_email:
                    st.error("Cannot invite: `employees.email` column is not enabled in this database yet.")
                    return
                em = str(ed_email or "").strip()
                if not em or "@" not in em:
                    st.error("Enter a valid employee email before inviting.")
                    return
                try:
                    invite_auth_user(email=em, role="employee")
                    st.success("Invite sent and profile created.")
                    st.rerun()
                except Exception as exc:
                    st.error("Could not enable login for this employee.")
                    with st.expander("Technical details"):
                        st.code(repr(exc), language="text")


def render() -> None:
    """Employee directory with attached login access (profiles matched by email)."""
    render_page_header("Users", "Employee directory with login access by email.")

    if current_role() != "admin":
        st.error("Admin access required.")
        return

    if st.session_state.get(_PEOPLE_PANEL_KEY) in ("add_emp", "add_user"):
        st.session_state[_PEOPLE_PANEL_KEY] = "list"
    if st.session_state.get(_USERS_PANEL_MODE) == "add":
        st.session_state.pop(_USERS_PANEL_MODE, None)

    if st.session_state.get(_PEOPLE_PANEL_KEY) == "detail":
        if len(get_selected_ids(TABLE_KEY_PEOPLE)) != 1:
            st.session_state[_PEOPLE_PANEL_KEY] = "list"

    try:
        employees = list(fetch_table("employees", limit=5000, order_by="name") or [])
    except Exception as exc:
        st.error(f"Could not load employees: {exc}")
        employees = []

    try:
        profiles = list(
            fetch_table_admin(
                "profiles",
                columns="id,email,phone_number,role,must_reset_password,created_at,is_active,full_name",
                limit=2000,
                order_by="email",
            )
            or []
        )
    except Exception as exc:
        # Back-compat: phone_number column may not exist yet.
        try:
            profiles = list(
                fetch_table_admin(
                    "profiles",
                    columns="id,email,role,must_reset_password,created_at,is_active,full_name",
                    limit=2000,
                    order_by="email",
                )
                or []
            )
        except Exception as exc2:
            st.error(f"Could not load profiles: {exc2}")
            profiles = []

    unified = _build_unified_frame(employees, profiles)

    st.caption("Employee Job Role = payroll/work role")
    st.caption("Access Role = app permissions")

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
            st.info("No employees match your filters (or the directory is empty).")
            inject_table_action_styles()
            if st.button("Add employee", type="primary", use_container_width=True, key="people_empty_add_emp"):
                emp_mod.add_employee_dialog(selection_table_key=TABLE_KEY_PEOPLE)
        else:
            disp = _display_df_for_editor(filtered)
            show_cols = _people_visible_table_columns(disp.columns)
            bar_ph = st.empty()
            _, sel = render_selectable_dataframe(
                disp,
                table_key=TABLE_KEY_PEOPLE,
                id_column="unified_id",
                columns=show_cols,
                editor_key="people_unified_editor",
                hide_id_column=True,
            )
            with bar_ph.container():
                _render_people_toolbar(sel=sel, can_edit=True, profiles=profiles)

    with side_col:
        sel_ids = get_selected_ids(TABLE_KEY_PEOPLE)
        stored_panel = str(st.session_state.get(_PEOPLE_PANEL_KEY, "list"))
        if stored_panel == "detail" and len(sel_ids) == 1:
            eff_panel = "detail"
        else:
            eff_panel = "list"
        _render_right_panel(panel=eff_panel, sel=sel_ids, profiles=profiles)

    # (Removed) Unlinked Login Accounts / legacy admin overview.
    # Linking is now automatic on the Users page (employee-linked invites).
