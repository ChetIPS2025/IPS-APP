from __future__ import annotations

import streamlit as st
from app.db import get_client, fetch_table


def init_session() -> None:
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
    st.session_state["auth_user"] = user

    profiles = fetch_table("profiles", columns="id,email,full_name,role,is_active", limit=1000)
    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    uid = str(user_id or "")
    match = next((p for p in profiles if str(p.get("id")) == uid), None)
    if not match:
        raise RuntimeError("No profile row found for this user. Create a row in public.profiles first.")
    if not match.get("is_active", True):
        raise RuntimeError("This user is inactive.")
    st.session_state["auth_profile"] = match


def sign_out() -> None:
    client = get_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass
    st.session_state["auth_user"] = None
    st.session_state["auth_profile"] = None


def require_login() -> bool:
    return st.session_state.get("auth_user") is not None


def current_profile() -> dict:
    return st.session_state.get("auth_profile") or {}


def current_role() -> str:
    """
    Normalized app role.

    Supported roles:
    - admin
    - pm
    - employee
    - viewer

    Legacy compatibility:
    - estimator -> pm
    """
    raw = str(current_profile().get("role", "viewer") or "viewer").strip().lower()
    if raw == "estimator":
        return "pm"
    if raw in {"admin", "pm", "employee", "viewer"}:
        return raw
    return "viewer"
