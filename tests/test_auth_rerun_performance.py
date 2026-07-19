"""Auth rerun performance: cached verification and local profile lookups."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import streamlit as st

from app.auth import (
    AUTH_USER_ID_KEY,
    CURRENT_USER_ID_KEY,
    CURRENT_USER_PROFILE_KEY,
    _AUTH_LAST_VERIFIED_AT_KEY,
    _AUTH_LAST_VERIFIED_UID_KEY,
    _mark_auth_verified,
    bootstrap_auth_at_startup,
    current_profile,
    current_role,
    current_user_display_name,
    ensure_authenticated_user_identity,
    render_auth_identity_debug_panel,
    sign_out,
    verify_identity_binding_or_stop,
)


def _seed_authenticated_session(
    *,
    uid: str = "auth-chet",
    full_name: str = "Chet Breaux",
    role: str = "admin",
    mark_verified: bool = True,
) -> None:
    profile = {
        "id": uid,
        "user_id": uid,
        "full_name": full_name,
        "email": "chet@example.com",
        "role": role,
        "is_active": True,
    }
    st.session_state["auth_user"] = SimpleNamespace(id=uid, email="chet@example.com")
    st.session_state["auth_profile"] = profile
    st.session_state[CURRENT_USER_PROFILE_KEY] = profile
    st.session_state[AUTH_USER_ID_KEY] = uid
    st.session_state[CURRENT_USER_ID_KEY] = uid
    st.session_state["authenticated"] = True
    st.session_state["is_authenticated"] = True
    if mark_verified:
        _mark_auth_verified(uid)


class TestAuthRerunPerformance(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    @patch("app.auth.ensure_authenticated_user_identity")
    @patch("app.auth._try_hydrate_auth_from_supabase_client")
    @patch("app.auth.try_restore_supabase_session_from_cookies")
    @patch("app.auth.process_auth_browser_sign_out")
    @patch("app.auth._live_auth_user_from_client")
    def test_bootstrap_performs_at_most_one_live_user_lookup(
        self,
        live_mock,
        _sign_out_mock,
        restore_mock,
        hydrate_mock,
        ensure_mock,
    ) -> None:
        _seed_authenticated_session()
        restore_mock.return_value = None
        hydrate_mock.return_value = False
        ensure_mock.return_value = True

        bootstrap_auth_at_startup()

        live_mock.assert_not_called()
        ensure_mock.assert_called_once()

    @patch("app.auth._live_auth_user_from_client")
    def test_repeated_current_profile_does_not_call_get_user(self, live_mock) -> None:
        _seed_authenticated_session()
        first = current_profile()
        second = current_profile()
        self.assertEqual(first["full_name"], "Chet Breaux")
        self.assertEqual(second["full_name"], "Chet Breaux")
        live_mock.assert_not_called()

    @patch("app.auth._live_auth_user_from_client")
    def test_repeated_current_role_does_not_call_get_user(self, live_mock) -> None:
        _seed_authenticated_session()
        self.assertEqual(current_role(), "admin")
        self.assertEqual(current_role(), "admin")
        live_mock.assert_not_called()

    @patch("app.auth._live_auth_user_from_client")
    def test_current_user_display_name_does_not_call_get_user(self, live_mock) -> None:
        _seed_authenticated_session()
        self.assertEqual(current_user_display_name(), "Chet Breaux")
        live_mock.assert_not_called()

    @patch("app.auth._live_auth_user_from_client")
    def test_ensure_reuses_recent_verification(self, live_mock) -> None:
        _seed_authenticated_session()
        self.assertTrue(ensure_authenticated_user_identity())
        self.assertTrue(ensure_authenticated_user_identity())
        live_mock.assert_not_called()

    @patch("app.auth._fetch_profile_for_auth_user_id")
    @patch("app.auth._live_auth_user_from_client")
    def test_force_live_verification_performs_lookup(
        self,
        live_mock,
        fetch_mock,
    ) -> None:
        _seed_authenticated_session()
        live_mock.return_value = SimpleNamespace(id="auth-chet", email="chet@example.com")
        fetch_mock.return_value = st.session_state["auth_profile"]

        ensure_authenticated_user_identity(force_live_verification=True)

        live_mock.assert_called_once()

    @patch("app.auth._live_auth_user_from_client")
    def test_changing_user_ids_invalidates_verification_cache(self, live_mock) -> None:
        _seed_authenticated_session(uid="auth-amanda")
        st.session_state[CURRENT_USER_ID_KEY] = "auth-chet"
        live_mock.return_value = SimpleNamespace(id="auth-chet", email="chet@example.com")
        with patch("app.auth._fetch_profile_for_auth_user_id") as fetch_mock:
            fetch_mock.return_value = {
                "id": "auth-chet",
                "user_id": "auth-chet",
                "full_name": "Chet Breaux",
                "role": "admin",
                "is_active": True,
            }
            self.assertTrue(ensure_authenticated_user_identity())
        live_mock.assert_called_once()

    def test_sign_out_clears_verification_state(self) -> None:
        _seed_authenticated_session()
        with patch("app.auth.get_client") as client_mock:
            client_mock.return_value.auth.sign_out.return_value = None
            sign_out()
        self.assertIsNone(st.session_state.get(_AUTH_LAST_VERIFIED_AT_KEY))
        self.assertIsNone(st.session_state.get(_AUTH_LAST_VERIFIED_UID_KEY))

    @patch("app.auth.st.stop")
    @patch("app.auth.ensure_authenticated_user_identity")
    @patch("app.auth.is_authenticated", return_value=True)
    def test_verify_identity_binding_no_duplicate_live_lookups(
        self,
        _auth_mock,
        ensure_mock,
        stop_mock,
    ) -> None:
        _seed_authenticated_session()
        ensure_mock.side_effect = [True, True]
        st.session_state["auth_profile"] = {
            "id": "auth-amanda",
            "full_name": "Amanda M. Robicheaux",
        }
        verify_identity_binding_or_stop()
        stop_mock.assert_called_once()
        self.assertEqual(ensure_mock.call_count, 2)
        ensure_mock.assert_any_call(
            force_profile_reload=True,
            force_live_verification=True,
        )

    @patch("app.auth.st.expander")
    @patch("app.auth.current_role", return_value="admin")
    @patch("app.auth._auth_debug_enabled", return_value=False)
    def test_auth_debug_panel_no_work_when_disabled(
        self,
        _debug_mock,
        _role_mock,
        expander_mock,
    ) -> None:
        render_auth_identity_debug_panel()
        expander_mock.assert_not_called()

    def test_loading_indicator_includes_failsafe_timeout(self) -> None:
        from pathlib import Path

        source = Path("app/ui/page_loading_indicator.py").read_text(encoding="utf-8")
        self.assertIn("MAX_LOADING_MS = 10000", source)
        self.assertIn("failSafeTimer", source)


if __name__ == "__main__":
    unittest.main()
