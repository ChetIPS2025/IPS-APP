from __future__ import annotations

import streamlit as st
from app.db import fetch_one, get_client


def init_session() -> None:
    # Canonical app auth state (requested keys)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("user_email", None)
    # Back-compat keys used throughout existing code
    st.session_state.setdefault("auth_user", None)
    st.session_state.setdefault("auth_profile", None)


def sign_in(email: str, password: str) -> None:
    client = get_client()
    try:
        resp = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:
        low = str(exc).lower()
        if any(
            x in low
            for x in (
                "invalid login",
                "invalid credentials",
                "invalid email",
                "wrong password",
                "email not confirmed",
            )
        ):
            raise RuntimeError("Invalid email or password.") from exc
        raise RuntimeError(
            f"Could not sign in ({exc.__class__.__name__}). "
            "Confirm SUPABASE_URL and the publishable/anon key are set in the environment "
            "(e.g. Render Dashboard → Environment), then try again."
        ) from exc
    user = getattr(resp, "user", None)
    if not user:
        raise RuntimeError("Login failed: no user returned from Supabase.")

    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    uid = str(user_id or "").strip()
    if not uid:
        raise RuntimeError("Login failed: Supabase returned a user without an id.")

    # Load the profile row (role, access control, must_reset_password, etc.)
    profile = fetch_one("profiles", {"id": uid})
    if not profile:
        raise RuntimeError("No profile row found for this user. Ask an admin to invite you.")
    if not bool(profile.get("is_active", True)):
        raise RuntimeError("This user is inactive.")

    st.session_state["auth_user"] = user
    st.session_state["auth_profile"] = profile

    # Requested session keys
    st.session_state["user"] = user
    user_email = getattr(user, "email", None)
    if user_email is None and isinstance(user, dict):
        user_email = user.get("email")
    st.session_state["user_email"] = str(user_email or profile.get("email") or email or "").strip() or None


def sign_out() -> None:
    client = get_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass
    st.session_state["user"] = None
    st.session_state["user_email"] = None
    st.session_state["auth_user"] = None
    st.session_state["auth_profile"] = None


def require_login() -> bool:
    return st.session_state.get("user") is not None or st.session_state.get("auth_user") is not None


def current_profile() -> dict:
    return st.session_state.get("auth_profile") or {}


def current_role() -> str:
    """
    Normalized app role.

    Supported roles:
    - admin
    - manager
    - employee
    - viewer

    Legacy compatibility:
    - pm, estimator -> manager
    """
    raw = str(current_profile().get("role", "viewer") or "viewer").strip().lower()
    if raw in {"estimator", "pm"}:
        return "manager"
    if raw in {"admin", "manager", "employee", "viewer"}:
        return raw
    return "viewer"


def get_current_user_role() -> str:
    """Helper requested by spec."""
    return current_role()


def must_reset_password() -> bool:
    prof = current_profile()
    return bool(prof.get("must_reset_password", False))


def update_password(new_password: str) -> None:
    """
    Set the currently authenticated user's password.

    Requires an active session created via sign_in_with_password or invite link flow.
    """
    pw = str(new_password or "").strip()
    if len(pw) < 8:
        raise RuntimeError("Password must be at least 8 characters.")
    client = get_client()
    try:
        client.auth.update_user({"password": pw})
    except Exception as exc:
        raise RuntimeError("Could not update password. Try again, or ask an admin for a new invite.") from exc

    # Best-effort: clear must_reset_password in the profile row (RLS may restrict; see db update in admin path).
    prof = current_profile()
    pid = str(prof.get("id") or "").strip()
    if pid:
        try:
            from app.db import update_rows
        except ImportError:
            from db import update_rows  # type: ignore
        try:
            update_rows("profiles", {"must_reset_password": False}, {"id": pid})
            st.session_state["auth_profile"] = {**prof, "must_reset_password": False}
        except Exception:
            # If RLS blocks it, user can still proceed; admin can clear later.
            st.session_state["auth_profile"] = {**prof, "must_reset_password": False}
