from __future__ import annotations

from datetime import datetime
import html
import re
from typing import Any

import pandas as pd
import streamlit as st

try:
    from app.config import settings
except ImportError:
    try:
        from config import settings  # type: ignore
    except Exception:
        settings = None  # type: ignore

try:
    from app.auth import current_role
    from app.db import (
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        fetch_table_admin,
        invite_auth_user,
        list_auth_users_admin,
        resend_invite_by_email,
        update_auth_user_email_admin,
        update_profile_admin,
        update_rows_admin,
    )
except ImportError:
    from auth import current_role  # type: ignore
    from db import (  # type: ignore
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        fetch_table_admin,
        invite_auth_user,
        list_auth_users_admin,
        resend_invite_by_email,
        update_auth_user_email_admin,
        update_profile_admin,
        update_rows_admin,
    )

try:
    from app.ui.users_components import (
        dept_pills_html,
        detail_header_row_html,
        inject_users_page_styles,
        render_users_header_inner_html,
        role_badge_html,
        role_permissions_card_html,
        status_badge_html,
        summary_card_html,
        table_header_html,
        user_info_card_html,
    )
    from app.ui.modal import ensure_modal_styles
except ImportError:
    from ui.users_components import (  # type: ignore
        dept_pills_html,
        detail_header_row_html,
        inject_users_page_styles,
        render_users_header_inner_html,
        role_badge_html,
        role_permissions_card_html,
        status_badge_html,
        summary_card_html,
        table_header_html,
        user_info_card_html,
    )
    from ui.modal import ensure_modal_styles  # type: ignore

_ROLE_OPTIONS: tuple[str, ...] = ("viewer", "employee", "manager", "admin")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_ALL_PERMISSIONS: tuple[str, ...] = (
    "View Dashboard",
    "Create & Edit Jobs",
    "View & Edit Timekeeping",
    "View Estimates",
    "Manage Inventory",
    "View Reports",
)

_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset(_ALL_PERMISSIONS),
    "manager": frozenset(
        {
            "View Dashboard",
            "Create & Edit Jobs",
            "View & Edit Timekeeping",
            "View Estimates",
            "View Reports",
        }
    ),
    "employee": frozenset({"View Dashboard", "View & Edit Timekeeping"}),
    "viewer": frozenset({"View Dashboard", "View Estimates", "View Reports"}),
}

_USERS_NEW_DIALOG_KEY = "users_show_new_dialog"


def _norm_email(v: object) -> str:
    return " ".join(str(v or "").strip().lower().split())


def _email_domain_allowed(email: str) -> bool:
    em = _norm_email(email)
    if not em or "@" not in em:
        return False
    dom = em.split("@", 1)[1]
    allow = ""
    try:
        allow = str(
            getattr(settings, "allowed_email_domain", "")
            or getattr(settings, "company_email_domain", "")
            or ""
        ).strip().lower()  # type: ignore[attr-defined]
    except Exception:
        allow = ""
    if not allow:
        return True
    return dom == allow


def _safe_str(val: object) -> str:
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    return str(val).strip()


def _fmt_ts(v: object) -> str:
    if v is None:
        return "—"
    if isinstance(v, datetime):
        return v.strftime("%b %d, %Y %I:%M %p")
    s = str(v).strip()
    if not s:
        return "—"
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        pass
    return s[:19] if len(s) > 19 else s


def _fmt_date(v: object) -> str:
    if v is None:
        return "—"
    if isinstance(v, datetime):
        return v.strftime("%b %d, %Y")
    s = str(v).strip()
    if not s:
        return "—"
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%b %d, %Y")
        return datetime.fromisoformat(s[:10]).strftime("%b %d, %Y")
    except Exception:
        return s[:10]


@st.cache_data(ttl=60, show_spinner=False)
def _employees_has_email_column_cached() -> bool:
    try:
        fetch_table("employees", columns="id,email", limit=1)
        return True
    except Exception:
        return False


@st.cache_data(ttl=120, show_spinner=False)
def _fetch_employees_map_cached() -> dict[str, dict[str, Any]]:
    cols = "id,name,email,role,trade,is_active"
    try:
        rows = list(fetch_table("employees", columns=cols, limit=5000, order_by="name") or [])
    except Exception:
        try:
            rows = list(fetch_table("employees", columns="id,name,role,trade,is_active", limit=5000, order_by="name") or [])
        except Exception:
            return {}
    return {str(r.get("id") or "").strip(): r for r in rows if str(r.get("id") or "").strip()}


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_profiles_cached() -> list[dict[str, Any]]:
    col_sets = (
        "id,email,phone_number,role,created_at,must_reset_password,is_active,full_name,employee_id,updated_at",
        "id,email,phone_number,role,created_at,must_reset_password,is_active,full_name,employee_id",
        "id,email,phone_number,role,created_at,must_reset_password,is_active,employee_id",
        "id,email,role,created_at,must_reset_password,is_active",
    )
    last_exc: Exception | None = None
    for cols in col_sets:
        try:
            return list(
                fetch_table_admin("profiles", columns=cols, limit=2000, order_by="email") or []
            )
        except Exception as exc:
            last_exc = exc
    if last_exc:
        raise last_exc
    return []


@st.cache_data(ttl=120, show_spinner=False)
def _auth_last_sign_in_map_cached() -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        for u in list_auth_users_admin(page=1, per_page=500) or []:
            uid = _safe_str(u.get("id"))
            if not uid:
                continue
            for key in ("last_sign_in_at", "last_sign_in", "updated_at"):
                if u.get(key):
                    out[uid] = _fmt_ts(u.get(key))
                    break
    except Exception:
        pass
    return out


def _norm_role(role: object) -> str:
    r = str(role or "viewer").strip().lower()
    if r in {"pm", "estimator"}:
        return "manager"
    if r not in _ROLE_OPTIONS:
        return "viewer"
    return r


def _role_display(role: object, *, emp_row: dict[str, Any] | None = None) -> tuple[str, str]:
    """Return (label, color_key) for badge."""
    emp_role = str((emp_row or {}).get("role") or "").strip().lower()
    if "supervisor" in emp_role or "foreman" in emp_role:
        return "Supervisor", "supervisor"
    r = _norm_role(role)
    mapping = {
        "admin": ("Administrator", "administrator"),
        "manager": ("Project Manager", "project manager"),
        "employee": ("Field Employee", "field employee"),
        "viewer": ("Accounting", "accounting"),
    }
    return mapping.get(r, (r.title(), r))


def _user_status(row: dict[str, Any]) -> str:
    if not bool(row.get("is_active", True)):
        return "Inactive"
    if bool(row.get("must_reset_password", False)):
        return "Pending"
    return "Active"


def _display_name(row: dict[str, Any], emp: dict[str, Any] | None) -> str:
    fn = _safe_str(row.get("full_name"))
    if fn:
        return fn
    if emp and _safe_str(emp.get("name")):
        return str(emp.get("name"))
    em = _safe_str(row.get("email"))
    if em and "@" in em:
        return em.split("@", 1)[0].replace(".", " ").title()
    return em or "User"


def _initials(name: str) -> str:
    parts = [p for p in str(name or "").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _department(row: dict[str, Any], emp: dict[str, Any] | None) -> str:
    if emp:
        trade = _safe_str(emp.get("trade"))
        if trade:
            return trade
        er = _safe_str(emp.get("role"))
        if er:
            return er
    return "—"


def _departments_list(row: dict[str, Any], emp: dict[str, Any] | None) -> list[str]:
    dept = _department(row, emp)
    if dept and dept != "—":
        return [dept]
    return []


def _username(row: dict[str, Any]) -> str:
    em = _safe_str(row.get("email"))
    if em and "@" in em:
        return em.split("@", 1)[0]
    return "—"


def _permission_summary(role: str) -> str:
    perms = _ROLE_PERMISSIONS.get(role, frozenset())
    n = len(perms)
    total = len(_ALL_PERMISSIONS)
    return f"{n} of {total} permissions enabled"


def _enrich_rows(
    rows: list[dict[str, Any]],
    *,
    emp_map: dict[str, dict[str, Any]],
    auth_sign_in: dict[str, str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        eid = _safe_str(row.get("employee_id"))
        emp = emp_map.get(eid) if eid else None
        role_norm = _norm_role(row.get("role"))
        role_lbl, role_key = _role_display(role_norm, emp_row=emp)
        status = _user_status(row)
        name = _display_name(row, emp)
        dept = _department(row, emp)
        uid = _safe_str(row.get("id"))
        last_login = auth_sign_in.get(uid) or "—"
        row["_display"] = {
            "name": name,
            "role_label": role_lbl,
            "role_key": role_key,
            "role_norm": role_norm,
            "status": status,
            "department": dept,
            "last_login": last_login,
            "emp": emp,
            "initials": _initials(name),
            "departments": _departments_list(row, emp),
            "permissions": _ROLE_PERMISSIONS.get(role_norm, frozenset()),
        }
        out.append(row)
    return out


def _clear_users_filters() -> None:
    for k in ("users_search", "users_role_f", "users_status_f", "users_dept_f"):
        st.session_state.pop(k, None)


def _filter_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    search = _safe_str(st.session_state.get("users_search")).lower()
    role_f = st.session_state.get("users_role_f", "All Roles")
    status_f = st.session_state.get("users_status_f", "All Statuses")
    dept_f = st.session_state.get("users_dept_f", "All Departments")

    out = rows
    if search:
        out = [
            r
            for r in out
            if search in _safe_str(r.get("email")).lower()
            or search in str((r.get("_display") or {}).get("name", "")).lower()
            or search in str((r.get("_display") or {}).get("department", "")).lower()
        ]
    if role_f and role_f != "All Roles":
        out = [r for r in out if (r.get("_display") or {}).get("role_label") == role_f]
    if status_f and status_f != "All Statuses":
        out = [r for r in out if (r.get("_display") or {}).get("status") == status_f]
    if dept_f and dept_f != "All Departments":
        out = [r for r in out if (r.get("_display") or {}).get("department") == dept_f]
    return out


def _invalidate_users_cache() -> None:
    _fetch_profiles_cached.clear()
    _fetch_employees_map_cached.clear()
    _auth_last_sign_in_map_cached.clear()


@st.dialog("New User", width="large", on_dismiss=lambda: st.session_state.pop(_USERS_NEW_DIALOG_KEY, None))
def _new_user_dialog() -> None:
    ensure_modal_styles()
    st.markdown("### Invite a new user")
    st.caption("Link to an employee when possible · magic-link invite via Supabase Auth")

    employees_has_email = _employees_has_email_column_cached()
    emp_map = _fetch_employees_map_cached()
    emp_rows = list(emp_map.values())
    emp_opts: list[tuple[str, str]] = []
    for e in emp_rows:
        eid = str(e.get("id") or "").strip()
        if not eid:
            continue
        nm = str(e.get("name") or "").strip() or "—"
        em = str(e.get("email") or "").strip() if employees_has_email else ""
        label = f"{nm} · {em}" if em else nm
        emp_opts.append((eid, label))
    emp_opts.sort(key=lambda t: t[1].lower())
    emp_labels = ["— Select employee —"] + [l for _, l in emp_opts]
    emp_id_by_label = {l: eid for eid, l in emp_opts}

    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1.2, 1], gap="small")
        picked_emp = c1.selectbox("Employee (recommended)", emp_labels, key="users_invite_emp_pick_dlg")
        invite_email = c2.text_input("Email (optional)", placeholder="name@company.com", key="users_invite_email_dlg")
        default_role = c3.selectbox("Default role", list(_ROLE_OPTIONS), index=_ROLE_OPTIONS.index("employee"), key="users_invite_role_dlg")

        allow_unlinked = st.checkbox(
            "Admin override: allow standalone login (no employee link)",
            value=False,
            help="Prefer linking to an employee. Use only for admin/viewer or exceptional cases.",
            key="users_invite_allow_unlinked_dlg",
        )

        b1, b2 = st.columns(2, gap="small")
        with b1:
            create_for_emp_clicked = st.button(
                "Create Login for Employee",
                type="secondary",
                use_container_width=True,
                key="users_create_login_for_employee_btn_dlg",
            )
        with b2:
            send_invite_clicked = st.button(
                "Send Invite",
                type="primary",
                use_container_width=True,
                key="users_send_invite_btn_dlg",
            )

    if create_for_emp_clicked:
        _handle_create_login_for_employee(picked_emp, emp_id_by_label, emp_rows, employees_has_email)
    if send_invite_clicked:
        _handle_send_invite(picked_emp, emp_id_by_label, emp_rows, employees_has_email, invite_email, default_role, allow_unlinked)


def _handle_create_login_for_employee(
    picked_emp: str,
    emp_id_by_label: dict[str, str],
    emp_rows: list[dict[str, Any]],
    employees_has_email: bool,
) -> None:
    if not picked_emp or picked_emp.startswith("—"):
        st.error("Select an employee first.")
        st.stop()
    eid = emp_id_by_label.get(picked_emp)
    emp_row = next((e for e in emp_rows if str(e.get("id") or "").strip() == str(eid)), None) or {}
    raw_email = str(emp_row.get("email") or "").strip().lower()
    if not raw_email or "@" not in raw_email:
        st.error("Employee must have an email to create login")
        st.stop()
    email = raw_email.strip().lower()
    if "indfustrial" in email:
        st.warning("Check spelling of company domain (found 'indfustrial').")
    if not _email_domain_allowed(email):
        st.warning("Check spelling of company domain / allowed domains.")
    emp_role = str(emp_row.get("role") or "employee").strip().lower() or "employee"
    if emp_role in {"pm", "estimator"}:
        emp_role = "manager"
    if emp_role not in _ROLE_OPTIONS:
        emp_role = "employee"

    existing = []
    try:
        existing = fetch_by_match_admin(
            "profiles",
            {"email": email},
            columns="id,email,employee_id,role,is_active,must_reset_password",
            limit=1,
        )
    except Exception:
        existing = []
    if existing:
        prof = existing[0] or {}
        prof_id = str(prof.get("id") or "").strip()
        linked_emp = str(prof.get("employee_id") or "").strip()
        if linked_emp and str(linked_emp) != str(eid):
            st.warning("Existing login is already linked to another employee.")
            confirm = st.checkbox(
                "Admin confirm: re-link this login to the selected employee",
                value=False,
                key="users_relink_existing_profile_confirm_dlg",
            )
            if not confirm:
                st.stop()
        try:
            update_profile_admin(prof_id, {"employee_id": str(eid)})
        except Exception:
            pass
        for col in ("profile_id", "auth_user_id"):
            try:
                update_rows_admin("employees", {col: prof_id}, {"id": str(eid)})
                break
            except Exception:
                continue
        try:
            update_rows_admin("employees", {"email": email}, {"id": str(eid)})
        except Exception:
            pass
        _invalidate_users_cache()
        st.session_state.pop(_USERS_NEW_DIALOG_KEY, None)
        st.success("Existing login found and linked to employee.")
        st.rerun()

    try:
        invite_auth_user(
            email=email,
            role=emp_role,
            employee_id=str(eid),
            require_employee_link=False,
        )
    except Exception as exc:
        st.error(f"Could not create login: {exc}")
        st.stop()

    try:
        update_rows_admin("employees", {"email": email}, {"id": str(eid)})
    except Exception:
        pass
    _invalidate_users_cache()
    st.session_state.pop(_USERS_NEW_DIALOG_KEY, None)
    st.success("Login created and invite sent")
    st.rerun()


def _handle_send_invite(
    picked_emp: str,
    emp_id_by_label: dict[str, str],
    emp_rows: list[dict[str, Any]],
    employees_has_email: bool,
    invite_email: str,
    default_role: str,
    allow_unlinked: bool,
) -> None:
    try:
        role_norm = str(default_role or "employee").strip().lower()
        if role_norm in {"pm", "estimator"}:
            role_norm = "manager"
        employee_id = emp_id_by_label.get(picked_emp) if picked_emp and not picked_emp.startswith("—") else None
        email = str(invite_email or "").strip().lower()
        if employee_id and employees_has_email:
            emp_row = next((e for e in emp_rows if str(e.get("id") or "").strip() == str(employee_id)), None) or {}
            emp_email = str(emp_row.get("email") or "").strip().lower()
            if emp_email:
                email = emp_email
        if not email:
            st.error("Email is required (or select an employee with an email).")
            st.stop()
        if "indfustrial" in email:
            st.warning("Check spelling of company domain (found 'indfustrial').")
        if not _email_domain_allowed(email):
            st.warning("Check spelling of company domain / allowed domains.")
        require_emp = not (allow_unlinked or role_norm in {"admin", "viewer"})
        invited = invite_auth_user(
            email=email,
            role=str(role_norm),
            employee_id=str(employee_id) if employee_id else None,
            require_employee_link=bool(require_emp),
        )
        _invalidate_users_cache()
        st.session_state.pop(_USERS_NEW_DIALOG_KEY, None)
        st.success(f"Invite sent to {invited.get('email')}.")
        st.rerun()
    except Exception as exc:
        st.error("Could not send invite.")
        with st.expander("Technical details"):
            st.code(repr(exc), language="text")


@st.dialog("Edit User", width="large")
def _edit_user_dialog(row: dict[str, Any]) -> None:
    ensure_modal_styles()
    uid = _safe_str(row.get("id"))
    disp = row.get("_display") or {}
    st.markdown(f"### {html.escape(str(disp.get('name') or 'User'))}")
    st.caption(_safe_str(row.get("email")))

    pk = f"usr_ed_{uid[:8]}"
    with st.form(f"users_edit_form_{uid}", clear_on_submit=False):
        ed_phone = st.text_input(
            "Phone",
            value=_safe_str(row.get("phone_number")),
            key=f"{pk}_phone",
        )
        ed_role = st.selectbox(
            "Access role",
            list(_ROLE_OPTIONS),
            index=list(_ROLE_OPTIONS).index(str(disp.get("role_norm") or "employee")),
            key=f"{pk}_role",
        )
        ed_active = st.checkbox("Active", value=bool(row.get("is_active", True)), key=f"{pk}_active")
        ed_mrpw = st.checkbox(
            "Must reset password on next login",
            value=bool(row.get("must_reset_password", False)),
            key=f"{pk}_mrpw",
        )
        save = st.form_submit_button("Save changes", type="primary", use_container_width=True)

    if save:
        new_role = _norm_role(ed_role)
        payload: dict[str, Any] = {}
        if _norm_role(row.get("role")) != new_role:
            payload["role"] = new_role
        if bool(row.get("is_active", True)) != ed_active:
            payload["is_active"] = ed_active
        if bool(row.get("must_reset_password", False)) != ed_mrpw:
            payload["must_reset_password"] = ed_mrpw
        new_phone = str(ed_phone or "").strip() or None
        if "phone_number" in row and str(row.get("phone_number") or "").strip() != str(new_phone or ""):
            payload["phone_number"] = new_phone
        if payload:
            try:
                clean = {
                    k: v
                    for k, v in {
                        "role": payload.get("role"),
                        "must_reset_password": payload.get("must_reset_password"),
                        "is_active": payload.get("is_active"),
                        "phone_number": payload.get("phone_number"),
                    }.items()
                    if v is not None
                }
                update_profile_admin(uid, clean)
                _invalidate_users_cache()
                st.success("User updated.")
                st.rerun()
            except Exception as exc:
                if "phone" in str(exc).lower() and (
                    "column" in str(exc).lower() or "does not exist" in str(exc).lower()
                ):
                    st.error("Could not save phone — database is missing `profiles.phone_number`.")
                else:
                    st.error(f"Update failed: {exc}")
        else:
            st.info("No changes to save.")


def _render_users_table(filtered: list[dict[str, Any]]) -> None:
    selected_id = _safe_str(st.session_state.get("users_selected_id"))

    with st.container(border=True):
        st.markdown('<span class="ips-users-table-anchor"></span>', unsafe_allow_html=True)
        weights = [1.35, 1.5, 0.95, 0.9, 0.75, 0.95, 0.65]
        head = st.columns(weights)
        for col, lbl in zip(
            head,
            ("User", "Email", "Role", "Department", "Status", "Last Login", "Actions"),
        ):
            with col:
                if lbl == "User":
                    st.markdown('<span class="ips-users-th-row" aria-hidden="true"></span>', unsafe_allow_html=True)
                if lbl == "Actions":
                    st.markdown('<p class="ips-users-th">Actions</p>', unsafe_allow_html=True)
                else:
                    st.markdown(table_header_html(lbl), unsafe_allow_html=True)

        for row in filtered:
            uid = _safe_str(row.get("id"))
            if not uid:
                continue
            disp = row.get("_display") or {}
            is_sel = uid == selected_id

            name = str(disp.get("name") or "—")
            email = _safe_str(row.get("email")) or "—"
            role_html = role_badge_html(str(disp.get("role_label") or "—"), color_key=str(disp.get("role_key") or ""))
            status_html = status_badge_html(str(disp.get("status") or "—"))
            dept = str(disp.get("department") or "—")
            last_login = str(disp.get("last_login") or "—")

            row_cls = "usr-row selected" if is_sel else "usr-row"

            with st.container():
                st.markdown('<span class="usr-row-wrap" aria-hidden="true"></span>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="{row_cls}">'
                    f'<span class="usr-name-cell" title="{html.escape(name, quote=True)}">{html.escape(name)}</span>'
                    f'<span class="usr-cell email" title="{html.escape(email, quote=True)}">{html.escape(email)}</span>'
                    f'<span class="usr-cell">{role_html}</span>'
                    f'<span class="usr-cell muted">{html.escape(dept)}</span>'
                    f'<span class="usr-cell">{status_html}</span>'
                    f'<span class="usr-cell muted">{html.escape(last_login)}</span>'
                    f'<span class="usr-act-slot"></span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown('<span class="usr-row-select-btn" aria-hidden="true"></span>', unsafe_allow_html=True)
                if st.button(
                    "\u200b",
                    key=f"users_pick_{uid}",
                    use_container_width=True,
                    help=f"Select {name}",
                ):
                    st.session_state["users_selected_id"] = uid
                    st.session_state.pop("users_detail_collapsed", None)
                    st.rerun()

                st.markdown('<span class="usr-actcol" aria-hidden="true"></span>', unsafe_allow_html=True)
                a1, a2 = st.columns(2, gap="small")
                with a1:
                    if st.button("👁", key=f"users_view_{uid}", help="View user", use_container_width=True):
                        st.session_state["users_selected_id"] = uid
                        st.session_state.pop("users_detail_collapsed", None)
                        st.rerun()
                with a2:
                    with st.popover("⋯", use_container_width=True):
                        if st.button("Edit user", key=f"users_more_edit_{uid}", use_container_width=True):
                            _edit_user_dialog(row)
                        if st.button("Resend invite", key=f"users_more_resend_{uid}", use_container_width=True):
                            try:
                                resend_invite_by_email(email=email)
                                st.success("Invite sent.")
                            except Exception as exc:
                                st.error("Could not resend invite.")
                                with st.expander("Technical details"):
                                    st.code(repr(exc), language="text")
                        if st.button(
                            "Reset password flag",
                            key=f"users_more_reset_{uid}",
                            use_container_width=True,
                        ):
                            try:
                                update_profile_admin(uid, {"must_reset_password": True})
                                _invalidate_users_cache()
                                st.success("User will be prompted to reset password on next login.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Could not update: {exc}")


def _render_user_detail_panel(row: dict[str, Any]) -> None:
    uid = _safe_str(row.get("id"))
    disp = row.get("_display") or {}
    emp = disp.get("emp") if isinstance(disp.get("emp"), dict) else None
    name = str(disp.get("name") or "User")
    status = str(disp.get("status") or "Active")
    role_lbl = str(disp.get("role_label") or "—")
    dept = str(disp.get("department") or "—")
    email = _safe_str(row.get("email")) or "—"
    phone = _safe_str(row.get("phone_number")) or "—"
    last_login = str(disp.get("last_login") or "—")
    role_norm = str(disp.get("role_norm") or "viewer")
    perms = disp.get("permissions") or frozenset()
    departments = list(disp.get("departments") or [])
    active = status == "Active"

    with st.container(border=True):
        st.markdown('<span class="ips-users-detail-anchor"></span>', unsafe_allow_html=True)

        hdr_main, top_act = st.columns([4.2, 1.35], gap="medium")
        with hdr_main:
            st.markdown(
                detail_header_row_html(
                    initials=str(disp.get("initials") or "?"),
                    name=name,
                    status_html=status_badge_html(status),
                    role=role_lbl,
                    department=dept,
                    active=active,
                    email=email,
                    phone=phone,
                    last_login=last_login,
                ),
                unsafe_allow_html=True,
            )
        with top_act:
            st.markdown('<div style="height:0.2rem"></div>', unsafe_allow_html=True)
            if st.button("Edit User", key=f"users_det_edit_{uid}", use_container_width=True):
                _edit_user_dialog(row)
            if st.button(
                "🔒 Reset Password",
                type="primary",
                key=f"users_det_reset_{uid}",
                use_container_width=True,
            ):
                try:
                    update_profile_admin(uid, {"must_reset_password": True})
                    _invalidate_users_cache()
                    st.success("Password reset required on next login.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not update: {exc}")
            more_c, collapse_c = st.columns(2, gap="small")
            with more_c:
                with st.popover("⋯ More", use_container_width=True):
                    em = _safe_str(row.get("email"))
                    new_em = st.text_input("New auth email", value=em, key=f"users_det_new_email_{uid}")
                    if st.button("Update email", key=f"users_det_email_go_{uid}", use_container_width=True):
                        _update_auth_email(uid, em, new_em, rows_context=row)
                    if st.button("Resend invite", key=f"users_det_resend_{uid}", use_container_width=True):
                        try:
                            resend_invite_by_email(email=em)
                            st.success("Invite sent.")
                        except Exception as exc:
                            st.error("Could not resend invite.")
                            with st.expander("Technical details"):
                                st.code(repr(exc), language="text")
            with collapse_c:
                if st.button("⌃", key=f"users_det_collapse_{uid}", help="Collapse panel", use_container_width=True):
                    st.session_state["users_detail_collapsed"] = True
                    st.rerun()

        tabs = st.tabs(
            [
                "Overview",
                "Role & Permissions",
                "Departments",
                "Activity Log",
                "Assigned Jobs",
                "Documents",
            ]
        )

        with tabs[0]:
            _render_overview_tab(row, disp=disp, emp=emp, role_lbl=role_lbl, role_norm=role_norm, perms=perms, departments=departments)
        with tabs[1]:
            _render_permissions_tab(role_norm, perms)
        with tabs[2]:
            _render_departments_tab(row, emp=emp, departments=departments)
        with tabs[3]:
            _render_activity_tab(uid)
        with tabs[4]:
            _render_assigned_jobs_tab(row, emp=emp)
        with tabs[5]:
            _render_documents_tab(uid)


def _render_overview_tab(
    row: dict[str, Any],
    *,
    disp: dict[str, Any],
    emp: dict[str, Any] | None,
    role_lbl: str,
    role_norm: str,
    perms: frozenset[str],
    departments: list[str],
) -> None:
    status = str(
        disp.get("status")
        or row.get("status")
        or row.get("Status")
        or "Inactive"
    )
    st.markdown('<div class="ips-users-overview-grid">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.2, 1.1, 0.9], gap="medium")
    notes = ""
    if emp:
        notes = _safe_str(emp.get("notes"))
    role_key = str(disp.get("role_key") or "")
    status_lbl = status
    badge_html = {
        "Role": role_badge_html(role_lbl, color_key=role_key),
        "Status": status_badge_html(status_lbl),
    }
    with c1:
        st.markdown(
            user_info_card_html(
                rows=[
                    ("Full Name", str(disp.get("name") or "—")),
                    ("Email", _safe_str(row.get("email"))),
                    ("Phone", _safe_str(row.get("phone_number")) or "—"),
                    ("Role", role_lbl),
                    ("Department", str(disp.get("department") or "—")),
                    ("Status", status_lbl),
                    ("Username", _username(row)),
                    ("Member Since", _fmt_date(row.get("created_at"))),
                    ("Notes", notes or "—"),
                ],
                html_values=badge_html,
                created=_fmt_date(row.get("created_at")),
                created_by="System Administrator",
                updated=_fmt_date(row.get("updated_at")) if row.get("updated_at") else "—",
                updated_by="Admin",
            ),
            unsafe_allow_html=True,
        )
    with c2:
        granted_list = [p for p in _ALL_PERMISSIONS if p in perms]
        st.markdown(
            role_permissions_card_html(
                role_lbl=role_lbl,
                role_key=role_key,
                perm_summary=_permission_summary(role_norm),
                granted=granted_list,
            ),
            unsafe_allow_html=True,
        )
        if st.button("View all permissions", key=f"users_view_perms_{row.get('id')}"):
            st.session_state["users_detail_tab_hint"] = "permissions"
    with c3:
        st.markdown('<div class="ips-users-card-stack">', unsafe_allow_html=True)
        tfa_label = "Enabled" if status == "Active" else "Not configured"
        st.markdown(
            summary_card_html(
                title="Security",
                rows=[
                    ("Password", "••••••••"),
                    ("Last Password Change", "—"),
                    ("Two-Factor Authentication", tfa_label),
                    ("Failed Login Attempts", "0"),
                    ("Account Locked", "No"),
                ],
                html_values={"Two-Factor Authentication": status_badge_html(tfa_label)},
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="ips-users-summary-card"><h4>Assigned Departments</h4>{dept_pills_html(departments)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_permissions_tab(role_norm: str, perms: frozenset[str]) -> None:
    st.caption(_permission_summary(role_norm))
    for p in _ALL_PERMISSIONS:
        granted = p in perms
        st.checkbox(p, value=granted, disabled=True, key=f"users_perm_{role_norm}_{p}")


def _render_departments_tab(row: dict[str, Any], *, emp: dict[str, Any] | None, departments: list[str]) -> None:
    st.markdown(dept_pills_html(departments), unsafe_allow_html=True)
    if emp:
        st.caption(f"Linked employee: {emp.get('name') or '—'}")
    else:
        st.info("No employee linked to this login. Link during invite or from the People page.")


def _render_activity_tab(profile_id: str) -> None:
    rows: list[dict[str, Any]] = []
    for table, cols, order in (
        ("company_updates", "id,title,posted_at,created_at", "created_at"),
        ("todos", "id,title,status,created_at", "created_at"),
    ):
        try:
            chunk = fetch_table_admin(table, columns=cols, limit=20, order_by=order)
            for r in chunk or []:
                if str(r.get("posted_by") or r.get("created_by") or r.get("user_id") or "") == profile_id:
                    rows.append({"source": table, **r})
        except Exception:
            continue
    if not rows:
        st.info("No recent activity recorded for this user.")
        return
    df = pd.DataFrame(rows[:25])
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_assigned_jobs_tab(row: dict[str, Any], *, emp: dict[str, Any] | None) -> None:
    eid = _safe_str(row.get("employee_id")) or (str(emp.get("id")) if emp else "")
    job_rows: list[dict[str, Any]] = []
    if eid:
        try:
            te = fetch_by_match_admin(
                "time_entries",
                {"employee_id": eid},
                columns="job_id",
                limit=500,
            )
            job_ids = sorted({str(r.get("job_id") or "") for r in (te or []) if r.get("job_id")})
            for jid in job_ids[:40]:
                try:
                    j = fetch_one("jobs", {"id": jid})
                    if j:
                        job_rows.append(j)
                except Exception:
                    continue
        except Exception:
            pass
    if not job_rows:
        st.info("No jobs found for this user (via time entries).")
        return
    df = pd.DataFrame(job_rows)
    show = [c for c in ("job_number", "job_name", "status", "customer_name") if c in df.columns]
    st.dataframe(df[show] if show else df, use_container_width=True, hide_index=True)


def _render_documents_tab(profile_id: str) -> None:
    docs: list[dict[str, Any]] = []
    try:
        docs = list(
            fetch_table_admin(
                "job_reference_attachments",
                columns="id,file_name,created_at,uploaded_by",
                limit=100,
                order_by="created_at",
            )
            or []
        )
        docs = [d for d in docs if str(d.get("uploaded_by") or "") == profile_id]
    except Exception:
        docs = []
    if not docs:
        st.info("No documents linked to this user.")
        return
    st.dataframe(pd.DataFrame(docs), use_container_width=True, hide_index=True)


def _update_auth_email(uid: str, cur_em: str, new_em: str, *, rows_context: dict[str, Any] | None = None) -> None:
    if current_role() != "admin":
        st.error("Unauthorized. Admin access required.")
        return
    em = str(new_em or "").strip().lower()
    if not _EMAIL_RE.match(em):
        st.error("Enter a valid email address.")
        return
    try:
        rows = _fetch_profiles_cached()
    except Exception:
        rows = [rows_context] if rows_context else []
    id_to_email = {str(r.get("id") or ""): str(r.get("email") or "").strip().lower() for r in rows if r.get("id")}
    for pid, pemail in id_to_email.items():
        if pid != uid and str(pemail or "").strip().lower() == em:
            st.error("That email is already used.")
            return
    try:
        update_auth_user_email_admin(user_id=uid, new_email=em)
        update_profile_admin(uid, {"email": em})
        _invalidate_users_cache()
        st.success("Email updated.")
        st.rerun()
    except Exception as exc:
        msg = str(exc)
        if "already" in msg.lower() and "email" in msg.lower():
            st.error("That email is already used.")
        else:
            st.error("Could not update auth email.")
            with st.expander("Technical details"):
                st.code(repr(exc), language="text")


def render() -> None:
    if current_role() != "admin":
        st.error("Unauthorized. Admin access required.")
        return

    inject_users_page_styles()
    st.markdown('<span class="ips-users-page ips-page-shell-marker" aria-hidden="true"></span>', unsafe_allow_html=True)

    try:
        raw_rows = _fetch_profiles_cached()
    except Exception as exc:
        st.error("Could not load profiles. Check SUPABASE_SERVICE_ROLE_KEY and database permissions.")
        with st.expander("Technical details"):
            st.code(repr(exc), language="text")
        return

    if not raw_rows:
        st.info("No users found.")
        if st.button("+ New User", type="primary", key="users_empty_new"):
            st.session_state[_USERS_NEW_DIALOG_KEY] = True
            _new_user_dialog()
        return

    emp_map = _fetch_employees_map_cached()
    auth_sign_in = _auth_last_sign_in_map_cached()
    rows = _enrich_rows(raw_rows, emp_map=emp_map, auth_sign_in=auth_sign_in)

    header_slot = st.container(border=True)
    filter_slot = st.container(border=True)

    roles = sorted({str((r.get("_display") or {}).get("role_label") or "") for r in rows if (r.get("_display") or {}).get("role_label")})
    statuses = sorted({str((r.get("_display") or {}).get("status") or "") for r in rows if (r.get("_display") or {}).get("status")})
    depts = sorted({str((r.get("_display") or {}).get("department") or "") for r in rows if (r.get("_display") or {}).get("department") and (r.get("_display") or {}).get("department") != "—"})

    with filter_slot:
        st.markdown('<span class="ips-users-filter-anchor"></span>', unsafe_allow_html=True)
        f1, f2, f3, f4, f5 = st.columns([2.2, 1.0, 1.0, 1.0, 0.75], gap="small")
        with f1:
            st.text_input("Search", placeholder="Search users...", key="users_search", label_visibility="collapsed")
        with f2:
            st.selectbox("Role", ["All Roles"] + roles, key="users_role_f", label_visibility="collapsed")
        with f3:
            st.selectbox("Status", ["All Statuses"] + statuses, key="users_status_f", label_visibility="collapsed")
        with f4:
            st.selectbox("Department", ["All Departments"] + depts, key="users_dept_f", label_visibility="collapsed")
        with f5:
            st.markdown('<div style="height:1.55rem"></div>', unsafe_allow_html=True)
            if st.button("Clear Filters", key="users_clear_filters", use_container_width=True, type="secondary"):
                _clear_users_filters()
                st.rerun()

    filtered = _filter_rows(rows)

    with header_slot:
        st.markdown('<span class="ips-users-header-anchor"></span>', unsafe_allow_html=True)
        hc1, hc2 = st.columns([5.5, 2.2], gap="small")
        with hc1:
            render_users_header_inner_html()
        with hc2:
            st.markdown('<div style="height:1.55rem"></div>', unsafe_allow_html=True)
            hb1, hb2 = st.columns(2, gap="small")
            with hb1:
                if filtered:
                    export_df = pd.DataFrame(
                        [
                            {
                                "Name": (r.get("_display") or {}).get("name"),
                                "Email": r.get("email"),
                                "Role": (r.get("_display") or {}).get("role_label"),
                                "Department": (r.get("_display") or {}).get("department"),
                                "Status": (r.get("_display") or {}).get("status"),
                                "Last Login": (r.get("_display") or {}).get("last_login"),
                            }
                            for r in filtered
                        ]
                    )
                    st.download_button(
                        "⬇ Export",
                        data=export_df.to_csv(index=False).encode("utf-8"),
                        file_name="users_export.csv",
                        mime="text/csv",
                        key="users_hdr_export",
                        use_container_width=True,
                        type="secondary",
                    )
            with hb2:
                if st.button("+ New User", type="primary", use_container_width=True, key="users_hdr_new"):
                    st.session_state[_USERS_NEW_DIALOG_KEY] = True
                    _new_user_dialog()

    if filtered and not _safe_str(st.session_state.get("users_selected_id")):
        st.session_state["users_selected_id"] = _safe_str(filtered[0].get("id"))

    _render_users_table(filtered)

    selected_id = _safe_str(st.session_state.get("users_selected_id"))
    if selected_id and not st.session_state.get("users_detail_collapsed"):
        sel_row = next((r for r in rows if _safe_str(r.get("id")) == selected_id), None)
        if sel_row:
            _render_user_detail_panel(sel_row)

    if st.session_state.get(_USERS_NEW_DIALOG_KEY):
        _new_user_dialog()
