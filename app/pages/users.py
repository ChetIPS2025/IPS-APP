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
        TABLE_KEY_PEOPLE,
        TABLE_KEY_USERS,
        clear_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        set_selected_ids,
    )
except ImportError:
    from table_actions import (  # type: ignore
        TABLE_KEY_PEOPLE,
        TABLE_KEY_USERS,
        clear_selected_ids,
        inject_table_action_styles,
        render_selectable_dataframe,
        set_selected_ids,
    )

_ROLE_OPTIONS: tuple[str, ...] = ("viewer", "estimator", "admin")
_MIN_PASSWORD_LENGTH = 8
_MAX_EMAIL_LENGTH = 320

# Legacy session key (People combined page may pop this after Add user dialog)
_USERS_PANEL_MODE = "users_panel_mode"

# Optional: persisted focus after Add (dialog / empty states) — table selection is source of truth for edit
USERS_EDIT_ID_KEY = "users_edit_id"


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


def _run_create_user(
    *,
    email_norm: str,
    pw: str,
    fn: str,
    new_role: str,
    existing_emails: set[str],
    clear_selection_table_key: str,
) -> bool:
    """Returns True if created successfully (caller reruns)."""
    if not email_norm:
        st.error("Email is required.")
        return False
    if not _email_looks_valid(email_norm):
        st.error("Enter a valid email address (e.g. name@company.com).")
        return False
    if not _password_meets_policy(pw):
        st.error(f"Temporary password must be at least {_MIN_PASSWORD_LENGTH} characters.")
        return False
    if new_role not in _ROLE_OPTIONS:
        st.error("Invalid role selected.")
        return False
    if email_norm in existing_emails:
        st.error(
            "A profile with that email already exists. Use another email or edit the existing user."
        )
        return False

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
        return False

    new_id = str((created or {}).get("id") or "").strip()
    if new_id:
        tkey = clear_selection_table_key
        sel_val = f"p:{new_id}" if tkey == TABLE_KEY_PEOPLE else new_id
        set_selected_ids(tkey, [sel_val])
        st.session_state[USERS_EDIT_ID_KEY] = new_id
    _clear_add_panel()
    em = str((created or {}).get("email") or email_norm)
    st.toast(f"User created · {em}", icon="✅")
    return True


@st.dialog("Add User")
def add_user_dialog(
    *,
    existing_emails: set[str],
    clear_selection_table_key: str | None = None,
) -> None:
    """Modal entry path (empty list, People page); same validation as inline Add user."""
    st.caption(f"Temporary password · min {_MIN_PASSWORD_LENGTH} characters")
    c1, c2 = st.columns(2)
    new_email = c1.text_input("Email", key="dlg_users_add_email", max_chars=_MAX_EMAIL_LENGTH)
    new_password = c2.text_input("Temporary password", type="password", key="dlg_users_add_password")
    c3, c4 = st.columns(2)
    new_full_name = c3.text_input("Full name", key="dlg_users_add_full_name")
    new_role = c4.selectbox("Role", list(_ROLE_OPTIONS), key="dlg_users_add_role")

    st.divider()
    bc, bs = st.columns(2, gap="small")
    with bc:
        if st.button("Cancel", type="secondary", use_container_width=True, key="dlg_users_add_cancel"):
            st.rerun()
    with bs:
        if st.button("Save", type="primary", use_container_width=True, key="dlg_users_add_save"):
            email_norm = _normalize_email(new_email)
            pw = str(new_password or "").strip()
            fn = str(new_full_name or "").strip()
            tkey = clear_selection_table_key or TABLE_KEY_USERS
            if _run_create_user(
                email_norm=email_norm,
                pw=pw,
                fn=fn,
                new_role=new_role,
                existing_emails=existing_emails,
                clear_selection_table_key=tkey,
            ):
                st.rerun()


def _fetch_profile_row(profile_id: str) -> dict[str, Any] | None:
    pid = str(profile_id or "").strip()
    if not pid:
        return None
    try:
        return fetch_one("profiles", {"id": pid})
    except Exception:
        return None


def _render_users_toolbar(*, sel: list[str], existing_emails: set[str]) -> None:
    """Customers-style bar: selection summary, Add User, Clear selection."""
    inject_ips_crud_list_styles()
    inject_table_action_styles()
    n = len(sel)

    with st.container(border=True):
        st.markdown('<div class="ips-crud-toolbar-root"></div>', unsafe_allow_html=True)
        left, b_add, b_clear = st.columns([1.15, 1, 1], gap="small")
        with left:
            st.markdown(
                f'<span class="ips-ta-summary"><span class="ips-ta-num">{n}</span> selected</span>',
                unsafe_allow_html=True,
            )
        with b_add:
            if st.button("Add User", type="primary", use_container_width=True, key="users_btn_add"):
                add_user_dialog(existing_emails=existing_emails, clear_selection_table_key=TABLE_KEY_USERS)
        with b_clear:
            if n and st.button("Clear selection", type="secondary", use_container_width=True, key="users_btn_clear_sel"):
                clear_selected_ids(TABLE_KEY_USERS)
                st.session_state.pop(USERS_EDIT_ID_KEY, None)
                st.rerun()


def _render_add_user_inline(*, existing_emails: set[str]) -> None:
    """Right panel — Add user (separate from edit)."""
    st.markdown("##### Add user")
    st.caption("New login: **Supabase Auth** account + **profiles** row. Temporary password required.")
    a1, a2 = st.columns(2, gap="small")
    in_email = a1.text_input(
        "Email",
        key="users_inline_add_email",
        max_chars=_MAX_EMAIL_LENGTH,
        placeholder="name@company.com",
    )
    in_pw = a2.text_input(
        "Temporary password",
        type="password",
        key="users_inline_add_password",
    )
    a3, a4 = st.columns(2, gap="small")
    in_name = a3.text_input("Full name", key="users_inline_add_full_name")
    in_role = a4.selectbox("Role", list(_ROLE_OPTIONS), key="users_inline_add_role")

    if st.button("Create user", type="primary", use_container_width=True, key="users_inline_add_submit"):
        email_norm = _normalize_email(in_email)
        pw = str(in_pw or "").strip()
        fn = str(in_name or "").strip()
        if _run_create_user(
            email_norm=email_norm,
            pw=pw,
            fn=fn,
            new_role=str(in_role),
            existing_emails=existing_emails,
            clear_selection_table_key=TABLE_KEY_USERS,
        ):
            st.rerun()


def _render_edit_user_panel(
    *,
    profile_row: dict[str, Any],
    clear_selection_table_key: str | None = None,
    embedded_in_people: bool = False,
    show_outer_heading: bool = True,
) -> None:
    """Editable fields for one profile; keys include user id so switching rows remounts widgets."""
    inject_ips_crud_list_styles()
    uid = str(profile_row.get("id") or "")
    pk = f"users_ed_{uid}"

    role_options = list(_ROLE_OPTIONS)
    cur_role = str(profile_row.get("role") or "viewer")
    if cur_role not in role_options:
        cur_role = "viewer"

    email_display = str(profile_row.get("email") or "").strip()

    if show_outer_heading and not embedded_in_people:
        st.markdown("##### Details")
    if not embedded_in_people:
        st.caption(
            "Updates **profiles**. Login email is changed in **Supabase Auth**, not here."
        )
    else:
        st.caption(
            "Profile fields · login email is managed in **Supabase Auth** if you need to change it."
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
    r1, r2 = st.columns(2, gap="small")
    with r1:
        edit_role = st.selectbox(
            "Role",
            role_options,
            index=role_options.index(cur_role),
            key=f"{pk}_role",
        )
    with r2:
        edit_active = st.checkbox(
            "Active",
            value=bool(profile_row.get("is_active", True)),
            key=f"{pk}_active",
            help="Inactive users cannot sign in.",
        )

    u1, u2 = st.columns(2, gap="small")
    with u1:
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
            clear_selected_ids(clear_selection_table_key or TABLE_KEY_USERS)
            st.rerun()
    with u2:
        if st.button("Clear selection", use_container_width=True, key=f"{pk}_clear_sel"):
            clear_selected_ids(clear_selection_table_key or TABLE_KEY_USERS)
            st.session_state.pop(USERS_EDIT_ID_KEY, None)
            st.rerun()


def _render_users_right_panel(
    *,
    sel: list[str],
    existing_emails: set[str],
) -> None:
    """Customers-like right column: Add user (top) + Selected user (bottom), always visible when split layout."""
    inject_ips_crud_list_styles()
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown("### User detail")

        _render_add_user_inline(existing_emails=existing_emails)

        st.divider()
        st.markdown("##### Selected user")
        st.caption("Click a row in the table — fields update for the selected account.")

        if len(sel) != 1:
            st.info("Select **exactly one** user in the table to edit name, role, and active status.")
            return

        uid = str(sel[0]).strip()
        row = _fetch_profile_row(uid)
        if not row:
            st.warning("User not found (it may have been removed).")
            clear_selected_ids(TABLE_KEY_USERS)
            st.session_state.pop(USERS_EDIT_ID_KEY, None)
            st.rerun()
            return

        _render_edit_user_panel(
            profile_row=row,
            clear_selection_table_key=TABLE_KEY_USERS,
            embedded_in_people=False,
            show_outer_heading=False,
        )


def _render_users_main(*, df: pd.DataFrame, existing_emails: set[str]) -> list[str]:
    """Filters + table + toolbar. Returns current selection ids."""
    if df.empty:
        st.info("No users found.")
        if st.button("Add User", type="primary", use_container_width=True, key="users_empty_add"):
            add_user_dialog(existing_emails=existing_emails, clear_selection_table_key=TABLE_KEY_USERS)
        return []

    f1, f2 = st.columns([2, 1], gap="small")
    with f1:
        st.markdown(
            '<span class="ips-crud-filter-row-start" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        st.text_input(
            "Search",
            placeholder="Email, name, role",
            key="users_list_search",
        )
    active_options = ["All", "Active only", "Inactive only"]
    f2.selectbox("Status", active_options, key="users_list_status_filter")

    search = str(st.session_state.get("users_list_search", "") or "")
    selected_active = str(st.session_state.get("users_list_status_filter", "All") or "All")

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
        if st.button("Add User", type="primary", use_container_width=True, key="users_filtered_empty_add"):
            add_user_dialog(existing_emails=existing_emails, clear_selection_table_key=TABLE_KEY_USERS)
        return []

    st.caption("Use the **checkbox** column to select a user — the **User panel** updates immediately.")

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
        _render_users_toolbar(sel=sel, existing_emails=existing_emails)

    return sel


def render_body(*, compact: bool = False) -> None:
    """Profiles / auth UI without page header (used by the ``Users`` combined page)."""
    if current_role() != "admin":
        st.error("Admin only")
        return

    if st.session_state.get(_USERS_PANEL_MODE) == "add":
        st.session_state.pop(_USERS_PANEL_MODE, None)

    try:
        users = fetch_table("profiles", limit=1000, order_by="email")
    except Exception as exc:
        st.error("Could not load user profiles from the database.")
        with st.expander("Technical details"):
            st.code(repr(exc), language="text")
        return

    df = pd.DataFrame(users)
    existing_emails = {_normalize_email(str(u.get("email", ""))) for u in users if u.get("email")}
    if not compact:
        render_crud_list_subtitle(
            "User list on the left; **Add user** and **Selected user** on the right. Select one row to edit."
        )

    if df.empty:
        _render_users_main(df=df, existing_emails=existing_emails)
        return

    main_col, side_col = st.columns(IPS_CRUD_LIST_PAGE_SPLIT, gap=IPS_CRUD_LIST_PAGE_GAP)
    with main_col:
        sel = _render_users_main(df=df, existing_emails=existing_emails)
    with side_col:
        _render_users_right_panel(sel=sel, existing_emails=existing_emails)


def render() -> None:
    render_header("Users")
    render_body(compact=False)
