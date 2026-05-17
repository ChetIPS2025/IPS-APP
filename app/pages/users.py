from __future__ import annotations

from datetime import datetime
import re

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
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        fetch_table_admin,
        invite_auth_user,
        resend_invite_by_email,
        update_auth_user_email_admin,
        update_profile_admin,
        update_rows,
        update_rows_admin,
    )
except ImportError:
    from auth import current_role  # type: ignore
    from db import (  # type: ignore
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_one,
        fetch_table,
        fetch_table_admin,
        invite_auth_user,
        resend_invite_by_email,
        update_auth_user_email_admin,
        update_profile_admin,
        update_rows,
        update_rows_admin,
    )

try:
    from app.ips_crud_list_styles import inject_ips_crud_list_styles
    from app.ui.page_shell import render_page_header
except ImportError:
    from ips_crud_list_styles import inject_ips_crud_list_styles  # type: ignore
    from ui.page_shell import render_page_header  # type: ignore

_ROLE_OPTIONS: tuple[str, ...] = ("viewer", "employee", "manager", "admin")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _norm_email(v: object) -> str:
    return " ".join(str(v or "").strip().lower().split())


def _email_domain_allowed(email: str) -> bool:
    em = _norm_email(email)
    if not em or "@" not in em:
        return False
    dom = em.split("@", 1)[1]
    allow = ""
    try:
        allow = str(getattr(settings, "allowed_email_domain", "") or getattr(settings, "company_email_domain", "") or "").strip().lower()  # type: ignore[attr-defined]
    except Exception:
        allow = ""
    if not allow:
        return True
    return dom == allow


def _employees_has_email_column() -> bool:
    try:
        fetch_table("employees", columns="id,email", limit=1)
        return True
    except Exception:
        return False


def _fetch_profile_row(profile_id):
    from app.db import get_client
    supabase = get_client()

    res = supabase.table("profiles") \
        .select("*") \
        .eq("id", profile_id) \
        .single() \
        .execute()

    return res.data if res.data else None


def _fmt_ts(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.isoformat(sep=" ", timespec="seconds")
    return str(v)


def render() -> None:
    render_page_header("Users", "Invite users, manage roles, and resend invites.")

    if current_role() != "admin":
        st.error("Unauthorized. Admin access required.")
        return

    inject_ips_crud_list_styles()

    with st.container(border=True):
        # Prefer employee-linked invites to prevent "unlinked login accounts".
        # Admin/viewer can be invited without an employee (override).
        employees_has_email = _employees_has_email_column()
        try:
            emp_cols = "id,name,email" if employees_has_email else "id,name"
            emp_rows = list(fetch_table("employees", columns=emp_cols, limit=5000, order_by="name") or [])
        except Exception:
            emp_rows = []

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

        c1, c2, c3, c4 = st.columns([2, 1, 1, 1.2], gap="small")
        picked_emp = c1.selectbox("Employee (recommended)", emp_labels, key="users_invite_emp_pick")
        invite_email = c2.text_input("Email (optional)", placeholder="name@company.com", key="users_invite_email")
        default_role = c3.selectbox("Default role", list(_ROLE_OPTIONS), index=_ROLE_OPTIONS.index("employee"))
        create_for_emp_clicked = c4.button(
            "Create Login for Employee",
            type="secondary",
            use_container_width=True,
            key="users_create_login_for_employee_btn",
        )

        allow_unlinked = st.checkbox(
            "Admin override: allow standalone login (no employee link)",
            value=False,
            help="Prefer linking to an employee to prevent unlinked accounts. Use only for admin/viewer or exceptional cases.",
            key="users_invite_allow_unlinked",
        )

        if create_for_emp_clicked:
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
            name = str(emp_row.get("name") or "").strip()
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
                        key="users_relink_existing_profile_confirm",
                    )
                    if not confirm:
                        st.stop()

                # Link existing profile/login to this employee (best-effort; columns may not exist yet)
                try:
                    update_profile_admin(prof_id, {"employee_id": str(eid)})
                except Exception:
                    # Column may not exist; ignore.
                    pass
                for col in ("profile_id", "auth_user_id"):
                    try:
                        update_rows_admin("employees", {col: prof_id}, {"id": str(eid)})
                        break
                    except Exception:
                        continue
                # Ensure employee email is set
                try:
                    update_rows_admin("employees", {"email": email}, {"id": str(eid)})
                except Exception:
                    pass

                st.success("Existing login found and linked to employee.")
                st.rerun()

            try:
                invited = invite_auth_user(
                    email=email,
                    role=emp_role,
                    employee_id=str(eid),
                    require_employee_link=False,
                )
            except Exception as exc:
                st.error(f"Could not create login: {exc}")
                st.stop()

            # Ensure employee email is set (source of truth for linking)
            try:
                update_rows_admin("employees", {"email": email}, {"id": str(eid)})
            except Exception:
                pass

            st.success("Login created and invite sent")
            st.rerun()

        if st.button("Send Invite", type="primary", use_container_width=True, key="users_send_invite_btn"):
            try:
                role_norm = str(default_role or "employee").strip().lower()
                if role_norm in {"pm", "estimator"}:
                    role_norm = "manager"
                employee_id = emp_id_by_label.get(picked_emp) if picked_emp and not picked_emp.startswith("—") else None
                email = str(invite_email or "").strip().lower()
                if employee_id and employees_has_email:
                    # Use employee email as source of truth when possible.
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
                st.success(f"Invite sent to {invited.get('email')}.")
                st.rerun()
            except Exception as exc:
                st.error("Could not send invite.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")

    try:
        rows = fetch_table_admin(
            "profiles",
            columns="id,email,phone_number,role,created_at,must_reset_password,is_active",
            limit=2000,
            order_by="email",
        )
    except Exception as exc:
        # Back-compat: phone_number column may not exist yet.
        try:
            rows = fetch_table_admin(
                "profiles",
                columns="id,email,role,created_at,must_reset_password,is_active",
                limit=2000,
                order_by="email",
            )
        except Exception:
            st.error("Could not load profiles. Check SUPABASE_SERVICE_ROLE_KEY and database permissions.")
            with st.expander("Technical details"):
                st.code(repr(exc), language="text")
            return

    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No users found.")
        return

    # Display table per spec: email, role, created_at
    view = df.copy()
    if "created_at" in view.columns:
        view["created_at"] = view["created_at"].map(_fmt_ts)
    for col in ("email", "role", "created_at"):
        if col not in view.columns:
            view[col] = ""
    if "phone_number" not in view.columns:
        view["phone_number"] = ""

    st.caption("Edit role/active status below and click **Save changes**.")
    edited = st.data_editor(
        view[["email", "phone_number", "role", "created_at", "must_reset_password", "is_active", "id"]],
        hide_index=True,
        use_container_width=True,
        disabled=["email", "created_at", "id"],
        column_config={
            "phone_number": st.column_config.TextColumn("phone_number"),
            "role": st.column_config.SelectboxColumn("role", options=list(_ROLE_OPTIONS), required=True),
            "must_reset_password": st.column_config.CheckboxColumn("must_reset_password"),
            "is_active": st.column_config.CheckboxColumn("is_active"),
            "id": st.column_config.TextColumn("id", disabled=True),
        },
        key="users_profiles_editor",
    )

    with st.expander("Edit login email (Supabase Auth)", expanded=False):
        st.caption("This updates **Auth** first, then syncs `public.profiles.email`.")
        id_to_email = {str(r.get("id") or ""): str(r.get("email") or "").strip().lower() for r in rows if r.get("id")}
        user_ids = [uid for uid in id_to_email.keys() if uid]
        user_ids.sort(key=lambda uid: id_to_email.get(uid, ""))
        pick_labels = [f"{id_to_email.get(uid, '')} · {uid[:8]}…" for uid in user_ids]
        picked = st.selectbox("User", pick_labels, key="users_edit_email_pick")
        picked_id = ""
        if picked:
            idx = pick_labels.index(picked)
            picked_id = user_ids[idx]
        cur_em = id_to_email.get(picked_id, "")
        new_em = st.text_input("New email", value=cur_em, key="users_edit_email_new")

        if st.button("Update email", type="primary", use_container_width=True, key="users_edit_email_go"):
            if current_role() != "admin":
                st.error("Unauthorized. Admin access required.")
                st.stop()
            uid = str(picked_id or "").strip()
            if not uid:
                st.error("Select a user.")
                st.stop()
            em = str(new_em or "").strip().lower()
            if not _EMAIL_RE.match(em):
                st.error("Enter a valid email address.")
                st.stop()
            # Uniqueness check (profiles mirror auth emails in this app)
            for pid, pemail in id_to_email.items():
                if pid != uid and str(pemail or "").strip().lower() == em:
                    st.error("That email is already used.")
                    st.stop()
            try:
                update_auth_user_email_admin(user_id=uid, new_email=em)
            except Exception as exc:
                msg = str(exc)
                if "already" in msg.lower() and "email" in msg.lower():
                    st.error("That email is already used.")
                else:
                    st.error("Could not update auth email.")
                    with st.expander("Technical details"):
                        st.code(repr(exc), language="text")
                st.stop()
            try:
                update_profile_admin(uid, {"email": em})
            except Exception as exc:
                st.warning("Auth email updated, but syncing profiles.email failed.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")
            st.success("Email updated.")
            st.rerun()

    # (Removed) Unlinked login/employee management UI:
    # linking is now handled automatically during invite/create flows.

    b1, b2 = st.columns([1, 1], gap="small")
    with b1:
        if st.button("Save changes", type="primary", use_container_width=True, key="users_save_changes"):
            try:
                # Compare row-by-row by id; apply only changed fields.
                base_by_id = {str(r.get("id")): r for r in rows if r.get("id")}
                changed = 0
                for _, erow in edited.iterrows():
                    uid = str(erow.get("id") or "").strip()
                    if not uid or uid not in base_by_id:
                        continue
                    before = base_by_id[uid]
                    new_role = str(erow.get("role") or "viewer").strip().lower()
                    if new_role in {"pm", "estimator"}:
                        new_role = "manager"
                    if new_role not in _ROLE_OPTIONS:
                        new_role = "viewer"
                    new_active = bool(erow.get("is_active", True))
                    new_mrpw = bool(erow.get("must_reset_password", False))
                    new_phone = str(erow.get("phone_number") or "").strip() or None
                    payload = {}
                    if str(before.get("role") or "").strip().lower() != new_role:
                        payload["role"] = new_role
                    if bool(before.get("is_active", True)) != new_active:
                        payload["is_active"] = new_active
                    if bool(before.get("must_reset_password", False)) != new_mrpw:
                        payload["must_reset_password"] = new_mrpw
                    if "phone_number" in before and str(before.get("phone_number") or "").strip() != str(new_phone or ""):
                        payload["phone_number"] = new_phone
                    if payload:
                        # Temporary debug (requested)
                        st.write("Updating profile:", payload)
                        st.write("User ID:", uid)
                        try:
                            clean = {
                                "role": str(payload.get("role") or "").strip() or None,
                                "must_reset_password": bool(payload.get("must_reset_password", False)),
                                "is_active": bool(payload.get("is_active", True)),
                            }
                            clean = {k: v for k, v in clean.items() if v is not None}
                            update_profile_admin(uid, clean)
                        except Exception as exc:
                            if "phone" in str(exc).lower() and ("column" in str(exc).lower() or "does not exist" in str(exc).lower()):
                                st.error("Could not save phone number — database is missing `profiles.phone_number`.")
                                st.stop()
                            st.error(f"Update failed: {exc}")
                            st.stop()
                        changed += 1
                if changed:
                    st.success("Access/Login updated.")
                else:
                    st.info("No changes to save.")
                st.rerun()
            except Exception as exc:
                st.error("Could not save changes.")
                st.exception(exc)
    with b2:
        sel_email = st.text_input("Resend invite to email", placeholder="name@company.com", key="users_resend_email")
        if st.button("Resend invite", use_container_width=True, key="users_resend_invite_btn"):
            try:
                resend_invite_by_email(email=sel_email)
                st.success("Invite sent.")
            except Exception as exc:
                st.error("Could not resend invite.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")
