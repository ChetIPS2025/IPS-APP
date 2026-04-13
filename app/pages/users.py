from __future__ import annotations

import pandas as pd
import streamlit as st

from auth import current_role
from branding import render_header
from db import fetch_table, update_rows, create_auth_user


def render() -> None:
    render_header("Users")

    if current_role() != "admin":
        st.error("Admin only")
        return

    users = fetch_table("profiles", limit=1000, order_by="email")
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
    new_role = c4.selectbox("Role", ["viewer", "estimator", "admin"], key="add_user_role")

    if st.button("Add User", use_container_width=True):
        if not new_email.strip():
            st.error("Email required")
            st.stop()

        if not new_password.strip():
            st.error("Temporary Password required")
            st.stop()

        existing_emails = {str(u.get("email", "")).strip().lower() for u in users}
        if new_email.strip().lower() in existing_emails:
            st.error("A user with that email already exists.")
            st.stop()

        created = create_auth_user(
            email=new_email.strip(),
            password=new_password.strip(),
            role=new_role,
            full_name=new_full_name.strip(),
        )

        st.success(f"User created: {created['email']}")
        st.info("They can sign in immediately with the temporary password.")
        st.rerun()

    st.markdown("---")
    st.subheader("Edit User")

    if not users:
        return

    selectable_users = [u for u in users if u.get("email")]
    if not selectable_users:
        st.info("No editable users found.")
        return

    user_map = {u["email"]: u["id"] for u in selectable_users}
    selected_email = st.selectbox("Select User", list(user_map.keys()))

    selected_user = next(u for u in selectable_users if u.get("email") == selected_email)

    role_options = ["viewer", "estimator", "admin"]
    current_user_role_value = selected_user.get("role", "viewer")
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

    if st.button("Update User", use_container_width=True):
        update_rows(
            "profiles",
            {
                "role": edit_role,
                "is_active": edit_active,
            },
            {"id": selected_user["id"]},
        )
        st.success("User updated")
        st.rerun()