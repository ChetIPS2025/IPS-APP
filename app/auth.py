from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
from typing import Any

import streamlit as st
from streamlit.components.v1 import html as components_html

from app.db import fetch_one, get_client
from app.config import settings
# Browser cookie names (Supabase access / refresh JWTs; HttpOnly not available from Streamlit JS bridge).
_COOKIE_ACCESS = "ips_auth_at"
_COOKIE_REFRESH = "ips_auth_rt"
_COOKIE_PERSIST = "ips_auth_persist"  # "1" when user chose "Remember this device"

_log = logging.getLogger(__name__)

IPS_CURRENT_USER_ID_KEY = "ips_current_user_id"
IPS_CURRENT_USER_EMAIL_KEY = "ips_current_user_email"
IPS_CURRENT_USER_FULL_NAME_KEY = "ips_current_user_full_name"
IPS_CURRENT_USER_ROLE_KEY = "ips_current_user_role"

# Canonical session keys (also cleared on login/logout/user change).
AUTH_ACCESS_TOKEN_KEY = "auth_access_token"
AUTH_REFRESH_TOKEN_KEY = "auth_refresh_token"
AUTH_USER_ID_KEY = "auth_user_id"
AUTH_EMAIL_KEY = "auth_email"
CURRENT_USER_PROFILE_KEY = "current_user_profile"
CURRENT_USER_ID_KEY = "current_user_id"
CURRENT_USER_KEY = "current_user"
USER_PROFILE_KEY = "user_profile"
DISPLAY_NAME_KEY = "display_name"
FULL_NAME_KEY = "full_name"
ROLE_KEY = "role"
PREVIEW_ROLE_KEY = "preview_role"
PREVIEW_MODE_KEY = "preview_mode"

_CACHED_IDENTITY_KEYS: tuple[str, ...] = (
    CURRENT_USER_KEY,
    CURRENT_USER_ID_KEY,
    CURRENT_USER_PROFILE_KEY,
    USER_PROFILE_KEY,
    FULL_NAME_KEY,
    DISPLAY_NAME_KEY,
    ROLE_KEY,
    PREVIEW_ROLE_KEY,
    PREVIEW_MODE_KEY,
    AUTH_ACCESS_TOKEN_KEY,
    AUTH_REFRESH_TOKEN_KEY,
    AUTH_USER_ID_KEY,
    AUTH_EMAIL_KEY,
    IPS_CURRENT_USER_ID_KEY,
    IPS_CURRENT_USER_EMAIL_KEY,
    IPS_CURRENT_USER_FULL_NAME_KEY,
    IPS_CURRENT_USER_ROLE_KEY,
    "auth_user",
    "auth_profile",
    "auth_employee",
    "auth_session",
    "user",
    "user_email",
    "user_profile",
    "employee_id",
    "selected_employee",
    "selected_user",
    "preview_employee_id",
)

_AUTH_LAST_VERIFIED_AT_KEY = "_ips_auth_last_verified_at"
_AUTH_LAST_VERIFIED_UID_KEY = "_ips_auth_last_verified_uid"
_AUTH_LIVE_GET_USER_COUNT_KEY = "_ips_auth_live_get_user_count"


def _auth_verification_ttl_seconds() -> float:
    try:
        return max(
            5.0,
            float(
                os.getenv(
                    "IPS_AUTH_VERIFY_TTL_SECONDS",
                    "60",
                )
            ),
        )
    except (TypeError, ValueError):
        return 60.0


def _recent_auth_verification_valid() -> bool:
    expected_uid = str(
        st.session_state.get(AUTH_USER_ID_KEY)
        or st.session_state.get(CURRENT_USER_ID_KEY)
        or ""
    ).strip()
    verified_uid = str(
        st.session_state.get(
            _AUTH_LAST_VERIFIED_UID_KEY
        )
        or ""
    ).strip()
    if not expected_uid or expected_uid != verified_uid:
        return False
    try:
        checked_at = float(
            st.session_state.get(
                _AUTH_LAST_VERIFIED_AT_KEY
            )
            or 0
        )
    except (TypeError, ValueError):
        return False
    return (
        time.monotonic() - checked_at
        < _auth_verification_ttl_seconds()
    )


def _mark_auth_verified(uid: str) -> None:
    value = str(uid or "").strip()
    if not value:
        return
    st.session_state[
        _AUTH_LAST_VERIFIED_UID_KEY
    ] = value
    st.session_state[
        _AUTH_LAST_VERIFIED_AT_KEY
    ] = time.monotonic()


def _clear_auth_verification_cache() -> None:
    st.session_state.pop(_AUTH_LAST_VERIFIED_AT_KEY, None)
    st.session_state.pop(_AUTH_LAST_VERIFIED_UID_KEY, None)


def _reset_live_auth_counter() -> None:
    st.session_state[_AUTH_LIVE_GET_USER_COUNT_KEY] = 0


def _increment_live_auth_counter() -> None:
    st.session_state[_AUTH_LIVE_GET_USER_COUNT_KEY] = (
        int(st.session_state.get(_AUTH_LIVE_GET_USER_COUNT_KEY) or 0) + 1
    )


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
        AUTH_ACCESS_TOKEN_KEY: None,
        AUTH_REFRESH_TOKEN_KEY: None,
        AUTH_USER_ID_KEY: None,
        AUTH_EMAIL_KEY: None,
        CURRENT_USER_PROFILE_KEY: None,
        IPS_CURRENT_USER_ID_KEY: None,
        IPS_CURRENT_USER_EMAIL_KEY: None,
        IPS_CURRENT_USER_FULL_NAME_KEY: None,
        IPS_CURRENT_USER_ROLE_KEY: None,
        CURRENT_USER_ID_KEY: None,
        CURRENT_USER_KEY: None,
        USER_PROFILE_KEY: None,
        FULL_NAME_KEY: None,
        DISPLAY_NAME_KEY: None,
        ROLE_KEY: None,
        PREVIEW_ROLE_KEY: None,
        PREVIEW_MODE_KEY: None,
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


def _persist_auth_tokens(access_token: str, refresh_token: str) -> None:
    at = str(access_token or "").strip()
    rt = str(refresh_token or "").strip()
    if at:
        st.session_state[AUTH_ACCESS_TOKEN_KEY] = at
    if rt:
        st.session_state[AUTH_REFRESH_TOKEN_KEY] = rt


def _sync_auth_session_from_client(client: Any) -> None:
    """Store Supabase auth session on ``st.session_state`` (used after login / restore)."""
    try:
        raw = client.auth.get_session()
    except Exception:
        st.session_state["auth_session"] = None
        return
    sess: Any = getattr(raw, "session", raw)
    st.session_state["auth_session"] = sess
    toks = _auth_session_tokens(client)
    if toks:
        _persist_auth_tokens(toks[0], toks[1])


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


def _auth_user_id(user: Any = None) -> str:
    u = user if user is not None else st.session_state.get("auth_user")
    if u is None:
        return ""
    uid = getattr(u, "id", None)
    if uid is None and isinstance(u, dict):
        uid = u.get("id")
    return str(uid or "").strip()


def _auth_user_email(user: Any = None) -> str:
    u = user if user is not None else st.session_state.get("auth_user")
    if u is None:
        return str(st.session_state.get("user_email") or "").strip()
    email = getattr(u, "email", None)
    if email is None and isinstance(u, dict):
        email = u.get("email")
    return str(email or st.session_state.get("user_email") or "").strip()


def _clear_cached_identity_keys(*, preserve_auth_checked: bool = False) -> None:
    auth_checked = bool(st.session_state.get("auth_checked")) if preserve_auth_checked else False
    for key in _CACHED_IDENTITY_KEYS:
        st.session_state.pop(key, None)
    _clear_auth_verification_cache()
    from app.utils.view_as import clear_view_as
    clear_view_as()
    from app.db import clear_streamlit_db_read_cache, clear_user_supabase_client
    clear_user_supabase_client()
    clear_streamlit_db_read_cache()
    st.session_state["authenticated"] = False
    st.session_state["is_authenticated"] = False
    if preserve_auth_checked:
        st.session_state["auth_checked"] = auth_checked


def _clear_current_user_snapshot() -> None:
    for key in (
        CURRENT_USER_ID_KEY,
        IPS_CURRENT_USER_ID_KEY,
        IPS_CURRENT_USER_EMAIL_KEY,
        IPS_CURRENT_USER_FULL_NAME_KEY,
        IPS_CURRENT_USER_ROLE_KEY,
        CURRENT_USER_KEY,
        USER_PROFILE_KEY,
        FULL_NAME_KEY,
        DISPLAY_NAME_KEY,
        ROLE_KEY,
    ):
        st.session_state.pop(key, None)


def _coerce_profile_dict(raw: Any) -> dict[str, Any]:
    """Return a profile mapping; ignore Supabase auth User objects stored by mistake."""
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _loaded_session_profile() -> dict[str, Any]:
    """First valid profile dict from session keys (auth profile, then cached snapshots)."""
    for key in ("auth_profile", CURRENT_USER_PROFILE_KEY, USER_PROFILE_KEY):
        coerced = _coerce_profile_dict(st.session_state.get(key))
        if coerced:
            return coerced
    return {}


def _auth_profile_session_corrupt() -> bool:
    raw = st.session_state.get("auth_profile")
    return raw is not None and not isinstance(raw, dict)


def _profile_matches_auth_user(profile: dict[str, Any], auth_user_id: str) -> bool:
    if not isinstance(profile, dict):
        return False
    uid = str(auth_user_id or "").strip()
    if not uid:
        return False
    pid = str(profile.get("id") or "").strip()
    linked = str(profile.get("user_id") or "").strip()
    return pid == uid or linked == uid


def _sync_current_user_snapshot(profile: dict[str, Any], *, auth_user_id: str) -> None:
    uid = str(auth_user_id or "").strip()
    email = str(profile.get("email") or _auth_user_email() or "").strip()
    full_name = str(profile.get("full_name") or profile.get("name") or "").strip()
    role = str(profile.get("role") or "viewer").strip()
    st.session_state[AUTH_USER_ID_KEY] = uid or None
    st.session_state[AUTH_EMAIL_KEY] = email or None
    st.session_state[CURRENT_USER_ID_KEY] = uid or None
    st.session_state[IPS_CURRENT_USER_ID_KEY] = uid or None
    st.session_state[IPS_CURRENT_USER_EMAIL_KEY] = email or None
    st.session_state[IPS_CURRENT_USER_FULL_NAME_KEY] = full_name or None
    st.session_state[IPS_CURRENT_USER_ROLE_KEY] = role or None
    profile_copy = dict(profile)
    st.session_state[CURRENT_USER_KEY] = profile_copy
    st.session_state[USER_PROFILE_KEY] = profile_copy
    st.session_state[CURRENT_USER_PROFILE_KEY] = profile_copy
    st.session_state[FULL_NAME_KEY] = full_name or None
    st.session_state[DISPLAY_NAME_KEY] = full_name or None
    st.session_state[ROLE_KEY] = role or None


def _clear_stale_user_identity() -> None:
    """Drop cached profile/employee identity before binding a new authenticated user."""
    _clear_cached_identity_keys(preserve_auth_checked=True)
    from app.db import clear_streamlit_db_read_cache
    clear_streamlit_db_read_cache()


def _bind_auth_session_from_client(client: Any) -> None:
    """Persist JWT + auth session on Streamlit state before profile lookups."""
    _sync_auth_session_from_client(client)
    toks = _auth_session_tokens(client)
    if toks:
        _persist_auth_tokens(toks[0], toks[1])


def _live_auth_user_from_client() -> Any | None:
    client = _try_get_client()
    if client is None:
        return None
    try:
        from app.perf_debug import perf_span

        with perf_span("auth.live_get_user"):
            gu = client.auth.get_user()
        _increment_live_auth_counter()
        user = getattr(gu, "user", None)
        if user is None and isinstance(gu, dict):
            user = gu.get("user")
        return user
    except Exception:
        return None


def _fetch_profile_for_auth_user_id(uid: str) -> dict[str, Any] | None:
    """Load the profile row for the authenticated Supabase user id."""
    auth_uid = str(uid or "").strip()
    if not auth_uid:
        return None
    from app.db import clear_streamlit_db_read_cache, fetch_by_match_admin, fetch_one
    clear_streamlit_db_read_cache()

    profile = fetch_one("profiles", {"id": auth_uid})
    if profile and _profile_matches_auth_user(profile, auth_uid):
        return profile

    from app.services.repository import table_column_names
    cols = table_column_names("profiles")
    if cols and "user_id" in cols:
        profile = fetch_one("profiles", {"user_id": auth_uid})
        if profile and _profile_matches_auth_user(profile, auth_uid):
            return profile

    emp_rows = fetch_by_match_admin(
        "employees",
        {"auth_user_id": auth_uid},
        columns="id,email,name,role,profile_id,auth_user_id",
        limit=1,
    )
    if emp_rows:
        emp = emp_rows[0]
        profile_id = str(emp.get("profile_id") or "").strip()
        if profile_id:
            linked = fetch_one("profiles", {"id": profile_id})
            if linked and _profile_matches_auth_user(linked, auth_uid):
                return linked
        return {
            "id": auth_uid,
            "user_id": auth_uid,
            "email": str(emp.get("email") or "").strip(),
            "full_name": str(emp.get("name") or "").strip(),
            "name": str(emp.get("name") or "").strip(),
            "role": str(emp.get("role") or "employee").strip(),
            "employee_id": str(emp.get("id") or "").strip(),
            "is_active": True,
        }
    return None


def _reload_profile_for_user_id(uid: str) -> dict[str, Any] | None:
    return _fetch_profile_for_auth_user_id(uid)


def _attach_employee_for_profile(profile: dict[str, Any]) -> None:
    st.session_state["auth_employee"] = None
    emp_id = str(profile.get("employee_id") or "").strip()
    if not emp_id:
        return
    try:
        emp = fetch_one("employees", {"id": emp_id})
        if emp:
            st.session_state["auth_employee"] = emp
    except Exception:
        st.session_state["auth_employee"] = None


def ensure_authenticated_user_identity(
    *,
    force_profile_reload: bool = False,
    force_live_verification: bool = False,
) -> bool:
    """
    Bind session identity to the Supabase auth user.

    Reuses a recent live verification when session profile matches; otherwise
    fetches ``auth.get_user()`` and reloads the profile when needed.
    """
    from app.perf_debug import perf_span

    with perf_span("auth.profile_lookup"):
        auth_user = st.session_state.get("auth_user")
        auth_uid = str(
            st.session_state.get(AUTH_USER_ID_KEY)
            or _auth_user_id()
            or ""
        ).strip()
        prof = _loaded_session_profile()
        profile_corrupt = _auth_profile_session_corrupt()

        session_usable = (
            auth_user is not None
            and bool(auth_uid)
            and bool(prof)
            and not profile_corrupt
            and _profile_matches_auth_user(prof, auth_uid)
        )
        stored_uid = str(st.session_state.get(CURRENT_USER_ID_KEY) or "").strip()
        session_uid = _auth_user_id()
        local_identity_mismatch = (
            (stored_uid and stored_uid != auth_uid)
            or (session_uid and session_uid != auth_uid)
        )

        need_live = (
            force_live_verification
            or not session_usable
            or local_identity_mismatch
            or not _recent_auth_verification_valid()
        )

        if not need_live and not force_profile_reload:
            sync_auth_flags()
            return True

        live_user: Any = auth_user
        live_uid = auth_uid
        if need_live:
            live_user = _live_auth_user_from_client()
            live_uid = _auth_user_id(live_user)
            if not live_uid:
                if is_authenticated() or st.session_state.get(CURRENT_USER_ID_KEY):
                    _clear_cached_identity_keys(preserve_auth_checked=True)
                return False
            _mark_auth_verified(live_uid)

        stored_uid = str(st.session_state.get(CURRENT_USER_ID_KEY) or "").strip()
        session_uid = _auth_user_id()
        identity_changed = stored_uid != live_uid or session_uid != live_uid
        profile_stale = (
            force_profile_reload
            or profile_corrupt
            or not prof
            or not _profile_matches_auth_user(prof, live_uid)
        )

        if identity_changed or profile_stale:
            if identity_changed:
                _clear_cached_identity_keys(preserve_auth_checked=True)
                _clear_auth_verification_cache()
                _mark_auth_verified(live_uid)
                from app.db import clear_streamlit_db_read_cache, clear_user_supabase_client
                clear_user_supabase_client()
                clear_streamlit_db_read_cache()

            profile = _fetch_profile_for_auth_user_id(live_uid)
            if not profile:
                _clear_auth_verification_cache()
                return False
            if not bool(profile.get("is_active", True)):
                _clear_auth_verification_cache()
                return False

            st.session_state["auth_user"] = live_user
            st.session_state["user"] = live_user
            st.session_state["auth_profile"] = profile
            user_email = _auth_user_email(live_user) or str(profile.get("email") or "").strip()
            st.session_state["user_email"] = user_email or None
            _attach_employee_for_profile(profile)
            _sync_current_user_snapshot(profile, auth_user_id=live_uid)
            try:
                client = _try_get_client()
                if client is not None:
                    _sync_auth_session_from_client(client)
            except Exception:
                pass
            sync_auth_flags()
            return True

        st.session_state["auth_user"] = live_user
        st.session_state["user"] = live_user
        _sync_current_user_snapshot(prof, auth_user_id=live_uid)
        sync_auth_flags()
        return True


def sync_authenticated_user(
    *,
    force_profile_reload: bool = False,
    force_live_verification: bool = False,
) -> bool:
    """Backward-compatible alias for :func:`ensure_authenticated_user_identity`."""
    return ensure_authenticated_user_identity(
        force_profile_reload=force_profile_reload,
        force_live_verification=force_live_verification,
    )


def _apply_user_and_profile_from_auth_user(user: Any, *, email_hint: str = "", phone_hint: str = "") -> None:
    user_id = getattr(user, "id", None)
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    uid = str(user_id or "").strip()
    if not uid:
        raise RuntimeError("Login failed: Supabase returned a user without an id.")

    from app.db import clear_streamlit_db_read_cache
    clear_streamlit_db_read_cache()

    profile = _fetch_profile_for_auth_user_id(uid)
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
    if not _profile_matches_auth_user(profile, uid):
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
    _sync_current_user_snapshot(profile, auth_user_id=uid)

    # Optional employee link (does not gate login)
    _attach_employee_for_profile(profile)

    try:
        _sync_auth_session_from_client(get_client())
    except Exception:
        st.session_state["auth_session"] = None

    _mark_auth_verified(uid)
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
    user = _live_auth_user_from_client()
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
    from app.perf_debug import perf_enabled, perf_span

    _reset_live_auth_counter()
    with perf_span("auth.bootstrap"):
        process_auth_browser_sign_out()
        if not is_authenticated():
            try_restore_supabase_session_from_cookies()
        if not is_authenticated():
            _try_hydrate_auth_from_supabase_client()
        if is_authenticated():
            ensure_authenticated_user_identity()
        sync_auth_flags()
        st.session_state["auth_checked"] = True
        log_auth_state("bootstrap")
    if perf_enabled():
        _log.warning(
            "[perf] auth.live_get_user_count: %d",
            int(st.session_state.get(_AUTH_LIVE_GET_USER_COUNT_KEY) or 0),
        )


def try_restore_supabase_session_from_cookies() -> None:
    """
    If the browser sent saved Supabase tokens, call ``set_session`` and load the profile.

    Skips cookie restore when already logged in; bootstrap owns final verification.
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
        _invalidate_stale_auth_cookies()
        return
    user = getattr(sr, "user", None) if sr is not None else None
    if user is None and sr is not None:
        sess = getattr(sr, "session", None)
        if sess is not None:
            user = getattr(sess, "user", None)
            if user is None and isinstance(sess, dict):
                user = sess.get("user")
    if not user:
        user = _live_auth_user_from_client()
    if not user:
        _invalidate_stale_auth_cookies()
        return
    try:
        _apply_user_and_profile_from_auth_user(user)
    except Exception:
        _invalidate_stale_auth_cookies()
        return

    toks = _auth_session_tokens(client)
    if not toks:
        _invalidate_stale_auth_cookies()
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


def _silent_clear_auth_cookies() -> None:
    """Drop invalid saved tokens without reloading the page (keeps login form state)."""
    secure = _cookie_secure_flag()
    sec_js = "true" if secure else "false"
    script = f"""
(function() {{
  var base = "Path=/; SameSite=Lax" + ({sec_js} ? "; Secure" : "");
  document.cookie = "{_COOKIE_ACCESS}=; " + base + "; Max-Age=0";
  document.cookie = "{_COOKIE_REFRESH}=; " + base + "; Max-Age=0";
  document.cookie = "{_COOKIE_PERSIST}=; " + base + "; Max-Age=0";
}})();
"""
    components_html(f"<script>{script}</script>", height=0, width=0)


def _invalidate_stale_auth_cookies() -> None:
    """Clear expired browser tokens on the login screen without a full page reload."""
    _silent_clear_auth_cookies()


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
    from app.config import validate_supabase_public_config
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

    _clear_stale_user_identity()

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

    _bind_auth_session_from_client(client)
    _apply_user_and_profile_from_auth_user(user, email_hint=email)

    from app.db import clear_streamlit_db_read_cache
    clear_streamlit_db_read_cache()

    toks = _auth_session_tokens(client)
    if toks:
        at, rt = toks
        _persist_auth_tokens(at, rt)
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
    _clear_stale_user_identity()
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
        user = _live_auth_user_from_client()
    if not user:
        raise RuntimeError("Login failed: no user returned from Supabase.")

    _bind_auth_session_from_client(client)
    _apply_user_and_profile_from_auth_user(user, phone_hint=ph)

    from app.db import clear_streamlit_db_read_cache
    clear_streamlit_db_read_cache()

    toks = _auth_session_tokens(client)
    if toks:
        at, rt = toks
        _persist_auth_tokens(at, rt)
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
    _clear_cached_identity_keys(preserve_auth_checked=True)
    # Keep auth_checked True so bootstrap does not re-show login during sign-out reload.
    st.session_state["auth_checked"] = True
    st.session_state["_ips_auth_clear_pending"] = True
    from app.db import clear_streamlit_db_read_cache
    clear_streamlit_db_read_cache()


def current_profile() -> dict:
    from app.perf_debug import perf_span

    with perf_span("auth.profile_lookup"):
        profile = _loaded_session_profile()
        if profile:
            return profile
        if is_authenticated():
            ensure_authenticated_user_identity()
        return _loaded_session_profile()


def verify_identity_binding_or_stop() -> None:
    """Abort the run when the loaded profile does not match the authenticated user."""
    from app.perf_debug import perf_span

    with perf_span("auth.verify_binding"):
        if not is_authenticated():
            return
        if not ensure_authenticated_user_identity():
            _clear_cached_identity_keys(preserve_auth_checked=True)
            st.error("Your account profile could not be verified. Please sign in again.")
            st.stop()

        authenticated_id = str(
            st.session_state.get(AUTH_USER_ID_KEY)
            or _auth_user_id()
            or ""
        ).strip()
        if not authenticated_id:
            return

        session_user_id = _auth_user_id()
        if session_user_id and session_user_id != authenticated_id:
            _log.error(
                "Identity mismatch: session auth_user=%s stored auth_user_id=%s",
                session_user_id,
                authenticated_id,
            )
            if not ensure_authenticated_user_identity(
                force_profile_reload=True,
                force_live_verification=True,
            ):
                _clear_cached_identity_keys(preserve_auth_checked=True)
                st.error("Your account profile could not be verified. Please sign in again.")
                st.stop()
            authenticated_id = str(
                st.session_state.get(AUTH_USER_ID_KEY)
                or _auth_user_id()
                or ""
            ).strip()

        prof = _loaded_session_profile()
        profile_auth_id = str(prof.get("id") or prof.get("user_id") or "").strip()
        if profile_auth_id and profile_auth_id != authenticated_id:
            _log.error(
                "Identity mismatch: authenticated user %s loaded profile %s",
                authenticated_id,
                profile_auth_id,
            )
            if not ensure_authenticated_user_identity(
                force_profile_reload=True,
                force_live_verification=True,
            ):
                _clear_cached_identity_keys(preserve_auth_checked=True)
                st.error("Your account profile could not be verified. Please sign in again.")
                st.stop()
            prof = _loaded_session_profile()
            profile_auth_id = str(prof.get("id") or prof.get("user_id") or "").strip()
            if profile_auth_id and profile_auth_id != authenticated_id:
                _clear_cached_identity_keys(preserve_auth_checked=True)
                st.error("Your account profile could not be verified. Please sign in again.")
                st.stop()

        st.session_state[AUTH_USER_ID_KEY] = authenticated_id
        email = _auth_user_email() or str(prof.get("email") or "").strip()
        if email:
            st.session_state[AUTH_EMAIL_KEY] = email


def current_user_display_name() -> str:
    """Display name for greetings — always the authenticated profile, never preview/employee cache."""
    prof = _loaded_session_profile()
    nm = str(prof.get("full_name") or prof.get("name") or "").strip()
    if nm:
        return nm
    email = str(
        prof.get("email")
        or st.session_state.get(IPS_CURRENT_USER_EMAIL_KEY)
        or st.session_state.get(AUTH_EMAIL_KEY)
        or st.session_state.get("user_email")
        or _auth_user_email()
        or ""
    ).strip()
    if email and "@" in email:
        return email.split("@")[0]
    return "there"


def render_auth_identity_debug_panel() -> None:
    """Temporary admin-only diagnostics for authenticated user/profile binding."""
    if not _auth_debug_enabled():
        return
    if current_role() != "admin":
        return
    session_uid = _auth_user_id()
    stored_uid = str(st.session_state.get(CURRENT_USER_ID_KEY) or "").strip()
    prof = _loaded_session_profile()
    prof_name = str(prof.get("full_name") or prof.get("name") or "").strip() or "—"
    auth_email = _auth_user_email() or str(st.session_state.get(AUTH_EMAIL_KEY) or "—")
    from app.utils.view_as import is_view_as_active, view_as_display_label
    preview_label = view_as_display_label() if is_view_as_active() else "—"
    display_name = str(prof.get("full_name") or prof.get("name") or "").strip()
    if not display_name:
        email = str(
            prof.get("email")
            or st.session_state.get(IPS_CURRENT_USER_EMAIL_KEY)
            or st.session_state.get(AUTH_EMAIL_KEY)
            or st.session_state.get("user_email")
            or ""
        ).strip()
        if email and "@" in email:
            display_name = email.split("@")[0]
        else:
            display_name = "there"
    with st.expander("Auth identity debug (admin)", expanded=False):
        st.code(
            "\n".join(
                [
                    f"Authenticated user ID: {session_uid or stored_uid or '—'}",
                    f"Authenticated email: {auth_email}",
                    f"Session auth_user_id: {str(st.session_state.get(AUTH_USER_ID_KEY) or stored_uid or '—')}",
                    f"Loaded profile ID: {str(prof.get('id') or '—')}",
                    f"Loaded profile name: {prof_name}",
                    f"Loaded profile auth user ID: {str(prof.get('id') or prof.get('user_id') or '—')}",
                    f"Preview mode: {preview_label}",
                    f"Greeting display name: {display_name}",
                ]
            )
        )


def current_role() -> str:
    """
    Normalized app role for permissions checks.

    Supported roles: admin, supervisor, project manager, employee, viewer.
    """
    prof = _loaded_session_profile()
    raw = str(prof.get("role", "viewer") or "viewer").strip().lower()
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


def effective_role() -> str:
    """UI/navigation role (admin View As preview overrides visibility only)."""
    from app.utils.view_as import ui_role
    return ui_role()


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
        from app.services.repository import update_row_admin
        try:
            update_row_admin("profiles", {"must_reset_password": False}, {"id": pid})
            st.session_state["auth_profile"] = {**prof, "must_reset_password": False}
        except Exception:
            # If RLS blocks it, user can still proceed; admin can clear later.
            st.session_state["auth_profile"] = {**prof, "must_reset_password": False}


SESSION_EXPIRED_USER_MESSAGE = "Session expired, please log in again."


def is_jwt_expired_error(exc: BaseException) -> bool:
    low = str(exc or "").casefold()
    return (
        "pgrst303" in low
        or "jwt expired" in low
        or "jwt has expired" in low
        or "token is expired" in low
    )


def friendly_auth_error_message(exc: BaseException, *, operation: str = "save") -> str:
    if is_jwt_expired_error(exc):
        return SESSION_EXPIRED_USER_MESSAGE
    op = str(operation or "save").strip() or "save"
    return f"Could not complete your {op}. Please try again."


def try_refresh_supabase_session() -> bool:
    """
    Refresh the Supabase access token using the refresh token.

    Uses in-memory client session first, then browser auth cookies. Queues updated
    tokens for :func:`persist_auth_cookies_if_pending` without forcing a page reload.
    """
    client = _try_get_client()
    if client is None:
        return False

    refresh_token = ""
    toks = _auth_session_tokens(client)
    if toks:
        refresh_token = toks[1]
    if not refresh_token:
        try:
            cookies = st.context.cookies
            refresh_token = urllib.parse.unquote(str(cookies.get(_COOKIE_REFRESH) or "").strip())
        except Exception:
            refresh_token = ""

    if not refresh_token:
        return False

    try:
        client.auth.refresh_session(refresh_token)
    except Exception as exc:
        _log.warning("Supabase session refresh failed: %s", exc)
        return False

    _sync_auth_session_from_client(client)
    fresh = _auth_session_tokens(client)
    if not fresh:
        return False

    at, rt = fresh
    remember = False
    try:
        remember = str(st.context.cookies.get(_COOKIE_PERSIST) or "").strip() == "1"
    except Exception:
        remember = False
    st.session_state["_ips_auth_persist_pending"] = {
        "access_token": at,
        "refresh_token": rt,
        "remember_device": remember,
    }
    if is_authenticated():
        persist_auth_cookies_if_pending()
    return True
