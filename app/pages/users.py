from __future__ import annotations

import re
from typing import Any

import pandas as pd
import streamlit as st

try:
    from app.auth import current_role
    from app.branding import render_header
    from app.db import create_auth_user, fetch_one, fetch_table, update_rows
except ImportError:
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import create_auth_user, fetch_one, fetch_table, update_rows  # type: ignore

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

try:
    from app.table_actions import (
        TABLE_KEY_USERS,
        clear_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )
except ImportError:
    from table_actions import (  # type: ignore
        TABLE_KEY_USERS,
        clear_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
    )

_ROLE_OPTIONS: tuple[str, ...] = ("viewer", "estimator", "admin")
_MIN_PASSWORD_LENGTH = 8
_MAX_EMAIL_LENGTH = 320

# Session: "add" opens Add User in the side panel; edit is driven by table selection (exactly one row).
_USERS_PANEL_MODE = "users_panel_mode"


def _normalize_email(raw: str) -> str:
    return " ".join(str(raw or "").strip().split()).lower()


def _email_looks_valid(email: str) -> bool:
    """Lightweight check; Supabase still validates on create."""
    s = email.strip()
    if not s or len(s) > _MAX_EMAIL_LENGTH:
        return False
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


def _clear_add_panel() -> None:
    st.session_state.pop(_USERS_PANEL_MODE, None)


def _fetch_profile_row(profile_id: str) -> dict[str, Any] | None:
    pid = str(profile_id or "").strip()
    if not pid:
        return None
    try:
        return fetch_one("profiles", {"id": pid})
    except Exception:
        return None


def _render_users_toolbar(*, sel: list[str]) -> None:
    """Toolbar: selection summary + Add User (matches Customers: primary list actions)."""
    inject_ips_crud_list_styles()
    inject_table_action_styles()
    n = len(sel)

    with st.container(border=True):
        st.markdown('<div class="ips-crud-toolbar-root"></div>', unsafe_allow_html=True)
        left, b0 = st.columns([1.1, 1], gap="small")
        with left:
            st.markdown(
                f'<span class="ips-ta-summary"><span class="ips-ta-num">{n}</span> selected</span>',
                unsafe_allow_html=True,
            )
        with b0:
            if st.button(
                "Add User",
                type="primary",
                use_container_width=True,
                key="users_btn_add",
            ):
                st.session_state[_USERS_PANEL_MODE] = "add"
                st.rerun()


def _render_add_user_panel(*, existing_emails: set[str]) -> None:
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Add user")
        st.caption(
            f"Password must be at least {_MIN_PASSWORD_LENGTH} characters. "
            "The user can change it after signing in if your app allows password updates."
        )

        c1, c2 = st.columns(2)
        new_email = c1.text_input("Email", key="users_add_email", max_chars=_MAX_EMAIL_LENGTH)
        new_password = c2.text_input("Temporary password", type="password", key="users_add_password")

        c3, c4 = st.columns(2)
        new_full_name = c3.text_input("Full name", key="users_add_full_name")
        new_role = c4.selectbox("Role", list(_ROLE_OPTIONS), key="users_add_role")

        s1, s2 = st.columns(2)
        with s1:
            if st.button("Add user", type="primary", use_container_width=True, key="users_add_save"):
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
                if email_norm in existing_emails:
                    st.error(
                        "A profile with that email already exists. Use another email or edit the existing user."
                    )
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
                st.info(
                    "They can sign in immediately with the temporary password (if your Auth policy allows it)."
                )
                _clear_add_panel()
                clear_selected_ids(TABLE_KEY_USERS)
                st.rerun()
        with s2:
            if st.button("Cancel", use_container_width=True, key="users_add_cancel"):
                _clear_add_panel()
                st.rerun()


def _render_edit_user_panel(*, profile_row: dict[str, Any]) -> None:
    """Side-panel editor: email (read-only), full_name, role, is_active, single Update User action."""
    inject_ips_crud_list_styles()
    uid = str(profile_row.get("id") or "")
    pk = f"users_ed_{uid}"

    role_options = list(_ROLE_OPTIONS)
    cur_role = str(profile_row.get("role") or "viewer")
    if cur_role not in role_options:
        cur_role = "viewer"

    email_display = str(profile_row.get("email") or "").strip()

    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### Edit user")
        st.caption(
            "Changes save to **profiles**. Login email is managed in **Supabase Auth** if you need to change it."
        )

        st.text_input(
            "Email",
            value=email_display or "—",
            disabled=True,
            key=f"{pk}_email_ro",
        )
        fn = st.text_input(
            "Full name",
            value=str(profile_row.get("full_name") or ""),
            key=f"{pk}_full_name",
        )
        edit_role = st.selectbox(
            "Role",
            role_options,
            index=role_options.index(cur_role),
            key=f"{pk}_role",
        )
        edit_active = st.checkbox(
            "Active",
            value=bool(profile_row.get("is_active", True)),
            key=f"{pk}_active",
        )

        if st.button("Update User", type="primary", use_container_width=True, key=f"{pk}_update"):
            try:
                update_rows(
                    "profiles",
                    {
                        "full_name": str(fn or "").strip(),
                        "role": edit_role,
                        "is_active": bool(edit_active),
                    },
                    {"id": profile_row["id"]},
                )
            except Exception as exc:
                st.error(
                    "Could not save profile changes. Check RLS policies and database connectivity."
                )
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")
                st.stop()

            st.success("User updated.")
            clear_selected_ids(TABLE_KEY_USERS)
            st.rerun()

        if st.button("Clear selection", use_container_width=True, key=f"{pk}_clear_sel"):
            clear_selected_ids(TABLE_KEY_USERS)
            st.rerun()


def _render_users_side_empty() -> None:
    """Placeholder when no single-row selection (Customers-style empty side state)."""
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### User")
        st.caption(
            "Select **exactly one** row in the table to load the editor here. "
            "Use **Add User** on the toolbar to create an account."
        )


def _render_users_side_panel(
    *,
    add_mode: bool,
    users: list[dict[str, Any]],
    sel: list[str],
) -> None:
    if add_mode:
        existing_emails = {_normalize_email(str(u.get("email", ""))) for u in users if u.get("email")}
        _render_add_user_panel(existing_emails=existing_emails)
        return

    if len(sel) == 1:
        row = _fetch_profile_row(sel[0])
        if not row:
            st.warning("User not found.")
            clear_selected_ids(TABLE_KEY_USERS)
            st.rerun()
            return
        _render_edit_user_panel(profile_row=row)
        return

    _render_users_side_empty()


def _render_users_main(*, df: pd.DataFrame) -> list[str]:
    """Filters + selectable table + toolbar. Returns selected profile ids from the table."""
    if df.empty:
        st.info("No users found.")
        if st.button("Add user", type="primary", use_container_width=True, key="users_empty_add"):
            st.session_state[_USERS_PANEL_MODE] = "add"
            st.rerun()
        return []

    f1, f2 = st.columns([2, 1], gap="small")
    with f1:
        st.markdown(
            '<span class="ips-crud-filter-row-start" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        search = st.text_input(
            "Search",
            placeholder="Email, name, role",
            key="users_list_search",
        )
    active_options = ["All", "Active only", "Inactive only"]
    selected_active = f2.selectbox("Status", active_options, key="users_list_status_filter")

    filtered = df.copy()
    if "is_active" in filtered.columns:
        if selected_active == "Active only":
            filtered = filtered[filtered["is_active"] == True]  # noqa: E712
        elif selected_active == "Inactive only":
            filtered = filtered[filtered["is_active"] == False]  # noqa: E712

    if search.strip():
        s = search.strip().lower()
        mask = filtered.astype(str).apply(
            lambda col: col.str.lower().str.contains(s, na=False, regex=False)
        )
        filtered = filtered[mask.any(axis=1)]

    show_cols = [c for c in ["email", "full_name", "role", "is_active"] if c in filtered.columns]

    if filtered.empty:
        st.warning("No users match your filters.")
        if st.button("Add user", type="primary", use_container_width=True, key="users_filtered_empty_add"):
            st.session_state[_USERS_PANEL_MODE] = "add"
            st.rerun()
        return []

    st.caption(
        "Checkbox column on the **left**. Select **one** row to edit in the side panel, or use **Add User**."
    )

    if "id" not in filtered.columns:
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)
        return []

    bar_ph = st.empty()
    _, sel = render_selectable_dataframe(
        filtered,
        table_key=TABLE_KEY_USERS,
        id_column="id",
        columns=show_cols,
        editor_key="users_sel_editor",
    )
    with bar_ph.container():
        _render_users_toolbar(sel=sel)

    return sel


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
    render_crud_list_subtitle(
        "Manage user accounts, roles, and status. Selecting one row opens the editor on the right."
    )

    add_mode = st.session_state.get(_USERS_PANEL_MODE) == "add"

    if df.empty:
        if add_mode:
            main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
            with main_col:
                st.info("No users found yet. Create the first account using the form.")
            with side_col:
                _render_users_side_panel(add_mode=True, users=users, sel=[])
        else:
            _render_users_main(df=df)
        return

    main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
    with main_col:
        sel = _render_users_main(df=df)
    with side_col:
        _render_users_side_panel(add_mode=add_mode, users=users, sel=sel)
