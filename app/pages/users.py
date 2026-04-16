from __future__ import annotations

import re

import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.branding import render_header
    from app.db import create_auth_user, fetch_table, update_rows
except ImportError:
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import create_auth_user, fetch_table, update_rows  # type: ignore

_ROLE_OPTIONS: tuple[str, ...] = ("viewer", "estimator", "admin")
# Supabase Auth commonly enforces a minimum length (often 6); we enforce slightly higher for UX.
_MIN_PASSWORD_LENGTH = 8
_MAX_EMAIL_LENGTH = 320


def _normalize_email(raw: str) -> str:
    return " ".join(str(raw or "").strip().split()).lower()


def _email_looks_valid(email: str) -> bool:
    """Lightweight check; Supabase still validates on create."""
    s = email.strip()
    if not s or len(s) > _MAX_EMAIL_LENGTH:
        return False
    # Practical local-part + domain shape (not full RFC 5322).
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", s))


def _password_meets_policy(raw: str) -> bool:
    return len(str(raw or "").strip()) >= _MIN_PASSWORD_LENGTH


def _friendly_create_user_message(exc: BaseException) -> str:
    """Map Supabase/db errors to operator-readable messages (no secrets)."""
    chain: list[str] = []
    cur: BaseException | None = exc
    depth = 0
    while cur is not None and depth < 8:
        chain.append(str(cur).lower())
        cur = getattr(cur, "__cause__", None) or getattr(cur, "__context__", None)
        depth += 1
    blob = " ".join(chain)

    if any(
        x in blob
        for x in (
            "already registered",
            "already exists",
            "duplicate",
            "user already",
            "email address",
            "unique constraint",
        )
    ):
        return (
            "That email is already in use (Supabase Auth or profiles). "
            "Choose another email, or remove/reconcile the user in the Supabase dashboard."
        )
    if "password" in blob and any(
        x in blob for x in ("short", "least", "weak", "invalid", "characters", "length")
    ):
        return (
            f"Password was rejected. Use at least {_MIN_PASSWORD_LENGTH} characters "
            "(consider letters, numbers, and symbols)."
        )
    if "invalid" in blob and "email" in blob:
        return "Email format was rejected by Supabase. Check for typos and try again."
    if "profiles upsert failed" in blob or ("profiles" in blob and "failed" in blob):
        return (
            "The auth user may have been created, but saving the profile row failed. "
            "Check Supabase logs and the `profiles` table (RLS, triggers, constraints)."
        )
    return (
        "Could not create the user. See **Technical details** below for the exact error, "
        "or check Supabase Auth settings and network connectivity."
    )


def render() -> None:
    render_header("Users")

    if current_role() != "admin":
        st.error("Admin only")
        return

    try:
        users = fetch_table("profiles", limit=1000, order_by="email")
    except Exception as exc:
        st.error("Could not load user profiles from the database.")
        with st.expander("Technical details"):
            st.code(repr(exc), language="text")
        return

    df = pd.DataFrame(users)

    st.subheader("User Database")

    if df.empty:
        st.info("No users found.")
    else:
        show_cols = [c for c in ["email", "full_name", "role", "is_active"] if c in df.columns]
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Add User")

    c1, c2 = st.columns(2)
    new_email = c1.text_input("Email", key="add_user_email")
    new_password = c2.text_input("Temporary Password", type="password", key="add_user_password")

    c3, c4 = st.columns(2)
    new_full_name = c3.text_input("Full Name", key="add_user_full_name")
    new_role = c4.selectbox("Role", list(_ROLE_OPTIONS), key="add_user_role")

    st.caption(
        f"Password must be at least {_MIN_PASSWORD_LENGTH} characters. "
        "The user can change it after signing in if your app allows password updates."
    )

    if st.button("Add User", use_container_width=True, key="users_add_btn"):
        email_norm = _normalize_email(new_email)
        pw = str(new_password or "").strip()
        fn = str(new_full_name or "").strip()

        if not email_norm:
            st.error("Email is required.")
            st.stop()
        if not _email_looks_valid(email_norm):
            st.error("Enter a valid email address (e.g. name@company.com).")
            st.stop()
        if not _password_meets_policy(pw):
            st.error(
                f"Temporary password must be at least {_MIN_PASSWORD_LENGTH} characters."
            )
            st.stop()
        if new_role not in _ROLE_OPTIONS:
            st.error("Invalid role selected.")
            st.stop()

        existing_emails = {_normalize_email(str(u.get("email", ""))) for u in users if u.get("email")}
        if email_norm in existing_emails:
            st.error("A profile with that email already exists. Use another email or edit the existing user.")
            st.stop()

        try:
            created = create_auth_user(
                email=email_norm,
                password=pw,
                role=new_role,
                full_name=fn,
            )
        except Exception as exc:
            st.error(_friendly_create_user_message(exc))
            with st.expander("Technical details"):
                st.code(repr(exc), language="text")
            st.stop()

        st.success(f"User created: {created.get('email', email_norm)}")
        st.info("They can sign in immediately with the temporary password (if your Auth policy allows it).")
        st.rerun()

    st.markdown("---")
    st.subheader("Edit User")

    if not users:
        return

    selectable_users = [u for u in users if u.get("email")]
    if not selectable_users:
        st.info("No editable users found.")
        return

    user_map = {str(u["email"]).strip(): u["id"] for u in selectable_users}
    selected_email = st.selectbox("Select User", list(user_map.keys()), key="users_edit_select_email")

    selected_user = next(u for u in selectable_users if str(u.get("email", "")).strip() == selected_email)

    role_options = list(_ROLE_OPTIONS)
    current_user_role_value = str(selected_user.get("role", "viewer") or "viewer")
    if current_user_role_value not in role_options:
        current_user_role_value = "viewer"

    edit_role = st.selectbox(
        "Role",
        role_options,
        index=role_options.index(current_user_role_value),
        key="edit_user_role",
    )

    edit_active = st.checkbox(
        "Active",
        value=bool(selected_user.get("is_active", True)),
        key="edit_user_active",
    )

    if st.button("Update User", use_container_width=True, key="users_update_btn"):
        try:
            update_rows(
                "profiles",
                {
                    "role": edit_role,
                    "is_active": edit_active,
                },
                {"id": selected_user["id"]},
            )
        except Exception as exc:
            st.error("Could not save profile changes. Check RLS policies and database connectivity.")
            with st.expander("Technical details"):
                st.code(repr(exc), language="text")
            st.stop()

        st.success("User updated.")
        st.rerun()
