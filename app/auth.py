from __future__ import annotations

import json
import logging
import os
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

_log = logging.getLogger(__name__)


def _auth_debug_enabled() -> bool:
    if os.getenv("IPS_AUTH_DEBUG", "").strip().lower() in ("1", "true", "yes"):
        return True
    return str(getattr(settings, "log_level", "") or "").upper() == "DEBUG"


def log_auth_state(reason: str) -> None:
    """Temporary diagnostics: set ``IPS_AUTH_DEBUG=1`` or log level DEBUG."""
    if not _auth_debug_enabled():
        return
    page = st.session_state.get("ips_nav_page") or st.session_state.get("page")
    _log.debug(
        "auth [%s] auth_checked=%s authenticated=%s is_authenticated=%s "
        "auth_user_set=%s email=%r page=%r pending_persist=%s pending_clear=%s",
        reason,
        st.session_state.get("auth_checked"),
        st.session_state.get("authenticated"),
        st.session_state.get("is_authenticated"),
        st.session_state.get("auth_user") is not None,
        st.session_state.get("user_email"),
        page,
        "_ips_auth_persist_pending" in st.session_state,
        bool(st.session_state.get("_ips_auth_clear_pending")),
    )


def init_session() -> None:
    """
    One-time defaults for auth-related session keys (do not overwrite existing values).

    Call at the very start of each run so downstream auth / cookie logic sees stable keys.
    Access control is enforced only from ``main.py``.
    """
    defaults: dict[str, Any] = {
        "auth_user": None,
        "auth_profile": None,
        "auth_checked": False,
        "authenticated": False,
        "is_authenticated": False,
        "auth_session": None,
        # Back-compat aliases used throughout the app
        "user": None,
        "user_email": None,
        "auth_employee": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    sync_auth_flags()


def sync_auth_flags() -> None:
    """Keep boolean auth flags aligned with ``auth_user`` (never clears ``auth_user``)."""
    authed = st.session_state.get("auth_user") is not None
    st.session_state["is_authenticated"] = authed
    st.session_state["authenticated"] = authed


def is_authenticated() -> bool:
    """True when a Supabase user is present. Only ``main.py`` should gate on this."""
    return st.session_state.get("auth_user") is not None


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


def _sync_auth_session_from_client(client: Any) -> None:
    """Store Supabase auth session on ``st.session_state`` (used after login / restore)."""
    try:
        raw = client.auth.get_session()
    except Exception:
        st.session_state["auth_session"] = None
        return
    sess: Any = getattr(raw, "session", raw)
    st.session_state["auth_session"] = sess


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

    st.session_state["auth_user"] = user
    st.session_state["auth_profile"] = profile
    st.session_state["user"] = user
    user_email = getattr(user, "email", None)
    if user_email is None and isinstance(user, dict):
        user_email = user.get("email")
    st.session_state["user_email"] = (
        str(user_email or profile.get("email") or email_hint or "").strip() or None
    )

    # Optional employee link (does not gate login)
    st.session_state["auth_employee"] = None
    emp_id = str(profile.get("employee_id") or "").strip() if isinstance(profile, dict) else ""
    if emp_id:
        try:
            emp = fetch_one("employees", {"id": emp_id})
            if emp:
                st.session_state["auth_employee"] = emp
        except Exception:
            st.session_state["auth_employee"] = None

    try:
        _sync_auth_session_from_client(get_client())
    except Exception:
        st.session_state["auth_session"] = None

    sync_auth_flags()


def _try_get_client():
    """Return Supabase client or None when URL/key are missing or invalid at startup."""
    try:
        return get_client()
    except Exception as exc:
        _log.debug("Supabase client unavailable during auth bootstrap: %s", exc)
        return None


def _try_hydrate_auth_from_supabase_client() -> bool:
    """
    If the Supabase Python client already has a session (e.g. right after sign-in),
    copy it into ``st.session_state`` without a browser reload.
    """
    if is_authenticated():
        return True
    client = _try_get_client()
    if client is None:
        return False
    user: Any = None
    try:
        gu = client.auth.get_user()
        user = getattr(gu, "user", None)
        if user is None and isinstance(gu, dict):
            user = gu.get("user")
    except Exception:
        return False
    if not user:
        return False
    try:
        _apply_user_and_profile_from_auth_user(user)
        return True
    except Exception:
        return False


def bootstrap_auth_at_startup() -> None:
    """
    Single startup auth restore (cookies + Supabase client). Call once from ``main.py``.

    Does not write browser cookies; use :func:`persist_auth_cookies_if_pending` after the login gate.
    """
    process_auth_browser_sign_out()
    try_restore_supabase_session_from_cookies()
    _try_hydrate_auth_from_supabase_client()
    sync_auth_flags()
    st.session_state["auth_checked"] = True
    log_auth_state("bootstrap")


def try_restore_supabase_session_from_cookies() -> None:
    """
    If the browser sent saved Supabase tokens, call ``set_session`` and load the profile.

    Skips when already logged in. Clears invalid cookie pairs by scheduling a clear bridge.
    """
    if is_authenticated():
        return
    try:
        cookies = st.context.cookies
    except Exception:
        return
    at = urllib.parse.unquote(str(cookies.get(_COOKIE_ACCESS) or "").strip())
    rt = urllib.parse.unquote(str(cookies.get(_COOKIE_REFRESH) or "").strip())
    if not at or not rt:
        return
    client = _try_get_client()
    if client is None:
        return
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


def _js_cookie_set_reload(*, access_token: str, refresh_token: str, remember_device: bool, secure: bool) -> str:
    sec_js = "true" if secure else "false"
    ma = "2592000" if remember_device else ""
    at_lit = json.dumps(access_token)
    rt_lit = json.dumps(refresh_token)
    ma_lit = json.dumps(ma)
    rem_lit = "true" if remember_device else "false"
    return f"""
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
  window.parent.location.reload();
}})();
"""


def process_auth_browser_sign_out() -> None:
    """Clear browser auth cookies after sign-out (full reload is intentional here)."""
    if st.session_state.pop("_ips_auth_clear_pending", False):
        st.info("Signing out — refreshing the page…")
        script = _js_cookie_clear_reload(secure=_cookie_secure_flag())
        components_html(f"<script>{script}</script>", height=8, width=1)
        st.stop()


def persist_auth_cookies_if_pending() -> None:
    """
    Write Supabase tokens to browser cookies after the user is authenticated.

    Never triggers a full-page reload — reloads were clearing Streamlit session and causing
    a second login prompt.
    """
    pending = st.session_state.pop("_ips_auth_persist_pending", None)
    if not pending:
        return
    at = str(pending.get("access_token") or "").strip()
    rt = str(pending.get("refresh_token") or "").strip()
    remember = bool(pending.get("remember_device"))
    if not at or not rt:
        return
    if not is_authenticated():
        _try_hydrate_auth_from_supabase_client()
    if not is_authenticated():
        # Re-queue for a later run after login succeeds (do not reload the page).
        st.session_state["_ips_auth_persist_pending"] = pending
        log_auth_state("persist_deferred_not_authenticated")
        return
    _silent_write_auth_cookies(at, rt, remember_device=remember)
    log_auth_state("persist_cookies_written")


def run_auth_browser_cookie_effects() -> None:
    """Back-compat: sign-out clear + cookie persist. Prefer explicit bootstrap/persist calls."""
    process_auth_browser_sign_out()
    persist_auth_cookies_if_pending()


def sign_in(email: str, password: str, *, remember_device: bool = False) -> None:
    try:
        from app.config import validate_supabase_public_config
    except ImportError:
        from config import validate_supabase_public_config  # type: ignore

    cfg_err = validate_supabase_public_config()
    if cfg_err:
        raise RuntimeError(cfg_err)

    try:
        client = get_client()
    except RuntimeError:
        raise
    except Exception as exc:
        low = str(exc).lower()
        if "invalid api key" in low:
            raise RuntimeError(
                "Supabase API key was rejected. Use the **anon public** key from "
                "Supabase Dashboard → Project Settings → API in `.streamlit/secrets.toml` "
                "or `.env` as SUPABASE_PUBLISHABLE_KEY (not the service_role key)."
            ) from exc
        raise RuntimeError(f"Sign in failed: {exc!r}") from exc

    try:
        resp = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:
        low = str(exc).lower()
        if "invalid api key" in low:
            raise RuntimeError(
                "Supabase API key was rejected. Use the **anon public** key from "
                "Supabase Dashboard → Project Settings → API."
            ) from exc
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
            "Confirm SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in `.streamlit/secrets.toml` "
            "or environment variables, then restart the app."
        ) from exc
    user = getattr(resp, "user", None)
    if not user:
        raise RuntimeError("Login failed: no user returned from Supabase.")

    _apply_user_and_profile_from_auth_user(user, email_hint=email)

    try:
        from app.db import clear_streamlit_db_read_cache
    except ImportError:
        from db import clear_streamlit_db_read_cache  # type: ignore

    clear_streamlit_db_read_cache()

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

    try:
        from app.db import clear_streamlit_db_read_cache
    except ImportError:
        from db import clear_streamlit_db_read_cache  # type: ignore

    clear_streamlit_db_read_cache()

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
    st.session_state["user"] = None
    st.session_state["user_email"] = None
    st.session_state["auth_user"] = None
    st.session_state["auth_session"] = None
    st.session_state["auth_profile"] = None
    st.session_state["auth_employee"] = None
    st.session_state["authenticated"] = False
    st.session_state["is_authenticated"] = False
    # Keep auth_checked True so bootstrap does not re-show login during sign-out reload.
    st.session_state["auth_checked"] = True
    st.session_state["_ips_auth_clear_pending"] = True
    try:
        from app.db import clear_streamlit_db_read_cache
    except ImportError:
        from db import clear_streamlit_db_read_cache  # type: ignore

    clear_streamlit_db_read_cache()


def require_login() -> bool:
    """Deprecated alias for :func:`is_authenticated`. Do not use for page gating."""
    return is_authenticated()


def current_profile() -> dict:
    return st.session_state.get("auth_profile") or {}


def current_role() -> str:
    """
    Normalized app role for permissions checks.

    Supported roles: admin, supervisor, project manager, employee, viewer.
    """
    raw = str(current_profile().get("role", "viewer") or "viewer").strip().lower()
    aliases = {
        "admin": "admin",
        "supervisor": "supervisor",
        "manager": "project manager",
        "pm": "project manager",
        "project manager": "project manager",
        "project_manager": "project manager",
        "estimator": "project manager",
        "employee": "employee",
        "viewer": "viewer",
    }
    return aliases.get(raw, "viewer")


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
