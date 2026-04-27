from __future__ import annotations

from datetime import datetime
import re

import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.branding import render_header
    from app.db import (
        fetch_table_admin,
        invite_auth_user,
        resend_invite_by_email,
        update_auth_user_email_admin,
        update_rows_admin,
    )
except ImportError:
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import (  # type: ignore
        fetch_table_admin,
        invite_auth_user,
        resend_invite_by_email,
        update_auth_user_email_admin,
        update_rows_admin,
    )

try:
    from app.ips_crud_list_styles import inject_ips_crud_list_styles, render_crud_list_subtitle
except ImportError:
    from ips_crud_list_styles import inject_ips_crud_list_styles, render_crud_list_subtitle  # type: ignore

_ROLE_OPTIONS: tuple[str, ...] = ("viewer", "employee", "manager", "admin")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

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
                update_rows_admin("profiles", {"email": em}, {"id": uid})
            except Exception as exc:
                st.warning("Auth email updated, but syncing profiles.email failed.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")
            st.success("Email updated.")
            st.rerun()

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
                        try:
                            update_rows_admin("profiles", payload, {"id": uid})
                        except Exception as exc:
                            if "phone" in str(exc).lower() and ("column" in str(exc).lower() or "does not exist" in str(exc).lower()):
                                st.error("Could not save phone number — database is missing `profiles.phone_number`.")
                                st.stop()
                            raise
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
