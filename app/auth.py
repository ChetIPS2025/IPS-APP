from __future__ import annotations

import json
import urllib.parse
from typing import Any

import streamlit as st
from streamlit.components.v1 import html as components_html

try:
    from app.db import fetch_one, get_client
except ImportError:
    from db import fetch_one, get_client  # type: ignore

try:
    from app.config import settings
except ImportError:
    from config import settings  # type: ignore

# Browser cookie names (Supabase access / refresh JWTs; HttpOnly not available from Streamlit JS bridge).
_COOKIE_ACCESS = "ips_auth_at"
_COOKIE_REFRESH = "ips_auth_rt"
_COOKIE_PERSIST = "ips_auth_persist"  # "1" when user chose "Remember this device"


def init_session() -> None:
    # Canonical app auth state.
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("user_email", None)
    # Back-compat keys used throughout existing code
    st.session_state.setdefault("auth_user", None)
    st.session_state.setdefault("auth_profile", None)
    st.session_state.setdefault("auth_employee", None)
    st.session_state.setdefault("auth_role", None)

    # Migrate older in-memory sessions that predate the canonical flag.
    if st.session_state.get("auth_user") is not None and st.session_state.get("auth_profile") is not None:
        st.session_state["authenticated"] = True
        st.session_state["user"] = st.session_state.get("auth_user")
        profile = st.session_state.get("auth_profile") or {}
        st.session_state["auth_role"] = str(profile.get("role") or "viewer").strip().lower() or "viewer"
    elif st.session_state.get("authenticated"):
        _clear_authenticated_session()


def _clear_authenticated_session() -> None:
    st.session_state["authenticated"] = False
    st.session_state["user"] = None
    st.session_state["user_email"] = None
    st.session_state["auth_user"] = None
    st.session_state["auth_profile"] = None
    st.session_state["auth_employee"] = None
    st.session_state["auth_role"] = None


def _set_authenticated_session(
    *,
    user: Any,
    profile: dict,
    email_hint: str = "",
    employee: dict | None = None,
) -> None:
    user_email = getattr(user, "email", None)
    if user_email is None and isinstance(user, dict):
        user_email = user.get("email")

    st.session_state["authenticated"] = True
    st.session_state["auth_user"] = user
    st.session_state["auth_profile"] = profile
    st.session_state["auth_employee"] = employee
    st.session_state["auth_role"] = str(profile.get("role") or "viewer").strip().lower() or "viewer"
    st.session_state["user"] = user
    st.session_state["user_email"] = (
        str(user_email or profile.get("email") or email_hint or "").strip() or None
    )


def _cookie_secure_flag() -> bool:
    """Use ``Secure`` on cookies when the app is served over HTTPS."""
    if getattr(settings, "is_production", False):
        return True
    base = str(getattr(settings, "app_base_url", "") or "").strip().lower()
    if base.startswith("https://"):
        return True
    try:
        xf = str(st.context.headers.get("x-forwarded-proto") or "").lower()
        if xf == "https":
            return True
    except Exception:
        pass
    return False


def _auth_session_tokens(client: Any) -> tuple[str, str] | None:
    """Return ``(access_token, refresh_token)`` from the Supabase client, if any."""
    raw: Any = None
    try:
        raw = client.auth.get_session()
    except Exception:
        return None
    sess: Any = getattr(raw, "session", raw)
    if sess is None:
        return None
    at = getattr(sess, "access_token", None)
    rt = getattr(sess, "refresh_token", None)
    if at is None and isinstance(sess, dict):
        at = sess.get("access_token")
        rt = sess.get("refresh_token")
    at_s = str(at or "").strip()
    rt_s = str(rt or "").strip()
    if not at_s or not rt_s:
        return None
    return at_s, rt_s


def _norm_phone(v: str) -> str:
    s = str(v or "").strip()
    if not s:
        return ""
    keep = []
    for ch in s:
        if ch.isdigit() or ch == "+":
            keep.append(ch)
    out = "".join(keep)
    digits = "".join([c for c in out if c.isdigit()])
    if out.startswith("+"):
        return "+" + digits
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return digits


def _apply_user_and_profile_from_auth_user(user: Any, *, email_hint: str = "", phone_hint: str = "") -> None:
    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    uid = str(user_id or "").strip()
    if not uid:
        raise RuntimeError("Login failed: Supabase returned a user without an id.")

    profile = fetch_one("profiles", {"id": uid})
    if not profile:
        # Fallback match: allow admins to link a login to a profile by email/phone value,
        # but do NOT auto-create new profiles (no self-registration).
        em = str(email_hint or "").strip().lower()
        ph = _norm_phone(phone_hint)
        if em:
            profile = fetch_one("profiles", {"email": em})
        if not profile and ph:
            profile = fetch_one("profiles", {"phone_number": ph})
        if not profile:
            raise RuntimeError("No profile row found for this user. Ask an admin to invite you.")
        raise RuntimeError(
            "This login is not linked to a profile id yet. Ask an admin to link it (profiles.id must match the Auth user id)."
        )
    if not bool(profile.get("is_active", True)):
        raise RuntimeError("This user is inactive.")

    user_email = getattr(user, "email", None)
    if user_email is None and isinstance(user, dict):
        user_email = user.get("email")
    email = str(user_email or profile.get("email") or email_hint or "").strip() or None

    # Optional employee link (does not gate login)
    employee = None
    emp_id = str(profile.get("employee_id") or "").strip() if isinstance(profile, dict) else ""
    if emp_id:
        try:
            emp = fetch_one("employees", {"id": emp_id})
            if emp:
                employee = emp
        except Exception:
            employee = None

    _set_authenticated_session(user=user, profile=profile, email_hint=email, employee=employee)


def try_restore_supabase_session_from_cookies() -> None:
    """
    If the browser sent saved Supabase tokens, call ``set_session`` and load the profile.

    Skips when already logged in. Clears invalid cookie pairs by scheduling a clear bridge.
    """
    if require_login():
        return
    try:
        cookies = st.context.cookies
    except Exception:
        return
    at = urllib.parse.unquote(str(cookies.get(_COOKIE_ACCESS) or "").strip())
    rt = urllib.parse.unquote(str(cookies.get(_COOKIE_REFRESH) or "").strip())
    if not at or not rt:
        return
    client = get_client()
    try:
        sr = client.auth.set_session(at, rt)
    except Exception:
        st.session_state["_ips_auth_clear_pending"] = True
        return
    user = getattr(sr, "user", None) if sr is not None else None
    if user is None and sr is not None:
        sess = getattr(sr, "session", None)
        if sess is not None:
            user = getattr(sess, "user", None)
            if user is None and isinstance(sess, dict):
                user = sess.get("user")
    if not user:
        try:
            gu = client.auth.get_user()
            user = getattr(gu, "user", None)
            if user is None and isinstance(gu, dict):
                user = gu.get("user")
        except Exception:
            user = None
    if not user:
        st.session_state["_ips_auth_clear_pending"] = True
        return
    try:
        _apply_user_and_profile_from_auth_user(user)
    except Exception:
        st.session_state["_ips_auth_clear_pending"] = True
        return

    toks = _auth_session_tokens(client)
    if not toks:
        st.session_state["_ips_auth_clear_pending"] = True
        return
    fresh_at, fresh_rt = toks
    remember = str(cookies.get(_COOKIE_PERSIST) or "").strip() == "1"
    if fresh_at != at or fresh_rt != rt:
        _silent_write_auth_cookies(fresh_at, fresh_rt, remember_device=remember)


def _silent_write_auth_cookies(access_token: str, refresh_token: str, *, remember_device: bool) -> None:
    """Update browser cookies (no reload) after Supabase refresh-token rotation."""
    secure = _cookie_secure_flag()
    sec_js = "true" if secure else "false"
    ma = "2592000" if remember_device else ""
    at_lit = json.dumps(access_token)
    rt_lit = json.dumps(refresh_token)
    ma_lit = json.dumps(ma)
    rem_lit = "true" if remember_device else "false"
    script = f"""
(function() {{
  var sec = {sec_js};
  var base = "Path=/; SameSite=Lax" + (sec ? "; Secure" : "");
  var ma = {ma_lit};
  var attrsTok = base + (ma ? ("; Max-Age=" + ma) : "");
  document.cookie = "{_COOKIE_ACCESS}=" + encodeURIComponent({at_lit}) + "; " + attrsTok;
  document.cookie = "{_COOKIE_REFRESH}=" + encodeURIComponent({rt_lit}) + "; " + attrsTok;
  if ({rem_lit}) {{
    document.cookie = "{_COOKIE_PERSIST}=1; " + base + "; Max-Age=2592000";
  }} else {{
    document.cookie = "{_COOKIE_PERSIST}=; " + base + "; Max-Age=0";
  }}
}})();
"""
    components_html(f"<script>{script}</script>", height=0, width=0)


def _js_cookie_clear_reload(*, secure: bool) -> str:
    sec = "true" if secure else "false"
    return f"""
(function() {{
  var base = "Path=/; SameSite=Lax" + ({sec} ? "; Secure" : "");
  document.cookie = "{_COOKIE_ACCESS}=; " + base + "; Max-Age=0";
  document.cookie = "{_COOKIE_REFRESH}=; " + base + "; Max-Age=0";
  document.cookie = "{_COOKIE_PERSIST}=; " + base + "; Max-Age=0";
  window.parent.location.reload();
}})();
"""


def run_auth_browser_cookie_effects() -> None:
    """
    One-shot browser bridges: clear cookies after sign-out, or persist tokens after sign-in.

    Sign-in writes cookies silently so the authenticated in-memory session can continue immediately.
    """
    if st.session_state.pop("_ips_auth_clear_pending", False):
        st.info("Signing out — refreshing the page…")
        script = _js_cookie_clear_reload(secure=_cookie_secure_flag())
        components_html(f"<script>{script}</script>", height=8, width=1)
        st.stop()

    pending = st.session_state.pop("_ips_auth_persist_pending", None)
    if not pending:
        return
    at = str(pending.get("access_token") or "").strip()
    rt = str(pending.get("refresh_token") or "").strip()
    remember = bool(pending.get("remember_device"))
    if not at or not rt:
        return
    _silent_write_auth_cookies(at, rt, remember_device=remember)


def sign_in(email: str, password: str, *, remember_device: bool = False) -> None:
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

    _apply_user_and_profile_from_auth_user(user, email_hint=email)

    toks = _auth_session_tokens(client)
    if toks:
        at, rt = toks
        st.session_state["_ips_auth_persist_pending"] = {
            "access_token": at,
            "refresh_token": rt,
            "remember_device": remember_device,
        }


def start_phone_otp(*, phone_number: str) -> None:
    """Send an SMS OTP to a phone number via Supabase Auth."""
    ph = _norm_phone(phone_number)
    if not ph:
        raise RuntimeError("Enter a valid phone number.")
    client = get_client()
    try:
        fn = getattr(client.auth, "sign_in_with_otp", None)
        if fn is None:
            raise AttributeError("auth.sign_in_with_otp is not available in this Supabase client.")
        try:
            fn({"phone": ph})
        except TypeError:
            fn(phone=ph)
    except Exception as exc:
        raise RuntimeError(f"Could not send OTP: {exc}") from exc


def verify_phone_otp(*, phone_number: str, code: str, remember_device: bool = False) -> None:
    """Verify SMS OTP and set authenticated session."""
    ph = _norm_phone(phone_number)
    tok = "".join(ch for ch in str(code or "").strip() if ch.isdigit())
    if not ph:
        raise RuntimeError("Enter a valid phone number.")
    if len(tok) < 4:
        raise RuntimeError("Enter the verification code.")
    client = get_client()
    try:
        fn = getattr(client.auth, "verify_otp", None)
        if fn is None:
            raise AttributeError("auth.verify_otp is not available in this Supabase client.")
        try:
            resp = fn({"phone": ph, "token": tok, "type": "sms"})
        except TypeError:
            resp = fn(phone=ph, token=tok, type="sms")
    except Exception as exc:
        raise RuntimeError("Invalid code or expired OTP.") from exc

    user = getattr(resp, "user", None)
    if not user and resp is not None:
        sess = getattr(resp, "session", None)
        if sess is not None:
            user = getattr(sess, "user", None)
            if user is None and isinstance(sess, dict):
                user = sess.get("user")
    if not user:
        try:
            gu = client.auth.get_user()
            user = getattr(gu, "user", None)
            if user is None and isinstance(gu, dict):
                user = gu.get("user")
        except Exception:
            user = None
    if not user:
        raise RuntimeError("Login failed: no user returned from Supabase.")

    _apply_user_and_profile_from_auth_user(user, phone_hint=ph)

    toks = _auth_session_tokens(client)
    if toks:
        at, rt = toks
        st.session_state["_ips_auth_persist_pending"] = {
            "access_token": at,
            "refresh_token": rt,
            "remember_device": remember_device,
        }


def sign_out() -> None:
    client = get_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass
    _clear_authenticated_session()
    st.session_state["_ips_auth_clear_pending"] = True


def require_login() -> bool:
    return (
        st.session_state.get("authenticated") is True
        and st.session_state.get("auth_user") is not None
        and st.session_state.get("auth_profile") is not None
    )


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
    raw = str(st.session_state.get("auth_role") or current_profile().get("role", "viewer") or "viewer").strip().lower()
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
            from app.db import update_rows_admin
        except ImportError:
            from db import update_rows_admin  # type: ignore
        try:
            update_rows_admin("profiles", {"must_reset_password": False}, {"id": pid})
            st.session_state["auth_profile"] = {**prof, "must_reset_password": False}
        except Exception:
            # If RLS blocks it, user can still proceed; admin can clear later.
            st.session_state["auth_profile"] = {**prof, "must_reset_password": False}
