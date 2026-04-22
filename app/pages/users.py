from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.branding import render_header
    from app.db import fetch_table_admin, invite_auth_user, resend_invite_by_email, update_rows_admin
except ImportError:
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import fetch_table_admin, invite_auth_user, resend_invite_by_email, update_rows_admin  # type: ignore

try:
    from app.ips_crud_list_styles import inject_ips_crud_list_styles, render_crud_list_subtitle
except ImportError:
    from ips_crud_list_styles import inject_ips_crud_list_styles, render_crud_list_subtitle  # type: ignore

_ROLE_OPTIONS: tuple[str, ...] = ("viewer", "employee", "manager", "admin")


def _fmt_ts(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.isoformat(sep=" ", timespec="seconds")
    return str(v)


def render() -> None:
    render_header("Users")

    if current_role() != "admin":
        st.error("Unauthorized. Admin access required.")
        return

    inject_ips_crud_list_styles()
    render_crud_list_subtitle("Invite users, manage roles, deactivate accounts, and resend invites.")

    with st.container(border=True):
        c1, c2 = st.columns([2, 1], gap="small")
        invite_email = c1.text_input("Email", placeholder="name@company.com", key="users_invite_email")
        default_role = c2.selectbox("Default role", list(_ROLE_OPTIONS), index=_ROLE_OPTIONS.index("employee"))
        if st.button("Send Invite", type="primary", use_container_width=True, key="users_send_invite_btn"):
            try:
                invited = invite_auth_user(email=invite_email, role=str(default_role))
                st.success(f"Invite sent to {invited.get('email')}.")
                st.rerun()
            except Exception as exc:
                st.error("Could not send invite.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")

    try:
        rows = fetch_table_admin(
            "profiles",
            columns="id,email,role,created_at,must_reset_password,is_active",
            limit=2000,
            order_by="email",
        )
    except Exception as exc:
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

    st.caption("Edit role/active status below and click **Save changes**.")
    edited = st.data_editor(
        view[["email", "role", "created_at", "must_reset_password", "is_active", "id"]],
        hide_index=True,
        use_container_width=True,
        disabled=["email", "created_at", "id"],
        column_config={
            "role": st.column_config.SelectboxColumn("role", options=list(_ROLE_OPTIONS), required=True),
            "must_reset_password": st.column_config.CheckboxColumn("must_reset_password"),
            "is_active": st.column_config.CheckboxColumn("is_active"),
            "id": st.column_config.TextColumn("id", disabled=True),
        },
        key="users_profiles_editor",
    )

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
                    payload = {}
                    if str(before.get("role") or "").strip().lower() != new_role:
                        payload["role"] = new_role
                    if bool(before.get("is_active", True)) != new_active:
                        payload["is_active"] = new_active
                    if bool(before.get("must_reset_password", False)) != new_mrpw:
                        payload["must_reset_password"] = new_mrpw
                    if payload:
                        update_rows_admin("profiles", payload, {"id": uid})
                        changed += 1
                if changed:
                    st.success(f"Saved {changed} update(s).")
                else:
                    st.info("No changes to save.")
                st.rerun()
            except Exception as exc:
                st.error("Could not save changes.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")
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
