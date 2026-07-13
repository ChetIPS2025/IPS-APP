"""Auth session identity sync for dashboard greeting."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import streamlit as st

from app.auth import (
    AUTH_ACCESS_TOKEN_KEY,
    AUTH_REFRESH_TOKEN_KEY,
    AUTH_USER_ID_KEY,
    CURRENT_USER_ID_KEY,
    CURRENT_USER_PROFILE_KEY,
    IPS_CURRENT_USER_FULL_NAME_KEY,
    _clear_cached_identity_keys,
    _persist_auth_tokens,
    _sync_current_user_snapshot,
    current_user_display_name,
    ensure_authenticated_user_identity,
    sign_out,
    try_restore_supabase_session_from_cookies,
    verify_identity_binding_or_stop,
)


class TestAuthUserSession(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_sync_current_user_snapshot_stores_auth_user_id(self) -> None:
        _sync_current_user_snapshot(
            {
                "id": "user-amanda",
                "email": "amanda@example.com",
                "full_name": "Amanda M. Robicheaux",
                "role": "admin",
            },
            auth_user_id="auth-amanda",
        )
        self.assertEqual(st.session_state[AUTH_USER_ID_KEY], "auth-amanda")
        self.assertEqual(st.session_state[CURRENT_USER_ID_KEY], "auth-amanda")
        self.assertEqual(
            st.session_state[IPS_CURRENT_USER_FULL_NAME_KEY],
            "Amanda M. Robicheaux",
        )
        self.assertEqual(
            st.session_state[CURRENT_USER_PROFILE_KEY]["full_name"],
            "Amanda M. Robicheaux",
        )

    def test_clear_cached_identity_keys_removes_profile_and_snapshot(self) -> None:
        st.session_state["auth_profile"] = {"id": "chet", "full_name": "Chet Breaux"}
        st.session_state[IPS_CURRENT_USER_FULL_NAME_KEY] = "Chet Breaux"
        st.session_state[CURRENT_USER_ID_KEY] = "chet"
        _clear_cached_identity_keys(preserve_auth_checked=True)
        self.assertIsNone(st.session_state.get("auth_profile"))
        self.assertIsNone(st.session_state.get(IPS_CURRENT_USER_FULL_NAME_KEY))
        self.assertIsNone(st.session_state.get(CURRENT_USER_ID_KEY))

    @patch("app.auth._live_auth_user_from_client")
    @patch("app.auth._fetch_profile_for_auth_user_id")
    def test_ensure_identity_reloads_when_current_user_id_differs(
        self,
        fetch_profile_mock,
        live_user_mock,
    ) -> None:
        st.session_state["auth_user"] = SimpleNamespace(id="auth-chet", email="chet@example.com")
        st.session_state[CURRENT_USER_ID_KEY] = "auth-amanda"
        st.session_state["auth_profile"] = {
            "id": "auth-amanda",
            "full_name": "Amanda M. Robicheaux",
            "role": "admin",
            "is_active": True,
        }
        live_user_mock.return_value = SimpleNamespace(id="auth-chet", email="chet@example.com")
        fetch_profile_mock.return_value = {
            "id": "auth-chet",
            "full_name": "Chet Breaux",
            "email": "chet@example.com",
            "role": "admin",
            "is_active": True,
        }

        self.assertTrue(ensure_authenticated_user_identity())
        self.assertEqual(st.session_state[CURRENT_USER_ID_KEY], "auth-chet")
        self.assertEqual(st.session_state["auth_profile"]["full_name"], "Chet Breaux")
        self.assertEqual(st.session_state[IPS_CURRENT_USER_FULL_NAME_KEY], "Chet Breaux")

    @patch("app.auth.ensure_authenticated_user_identity")
    def test_current_user_display_name_uses_loaded_profile_only(
        self,
        ensure_mock,
    ) -> None:
        st.session_state["auth_user"] = SimpleNamespace(id="auth-chet")
        st.session_state[CURRENT_USER_ID_KEY] = "auth-chet"
        st.session_state[IPS_CURRENT_USER_FULL_NAME_KEY] = "Amanda M. Robicheaux"
        st.session_state["auth_profile"] = {
            "id": "auth-chet",
            "full_name": "Chet Breaux",
            "email": "chet@example.com",
        }

        self.assertEqual(current_user_display_name(), "Chet Breaux")
        ensure_mock.assert_called()

    def test_sign_out_clears_user_snapshot(self) -> None:
        st.session_state["auth_user"] = SimpleNamespace(id="auth-amanda")
        st.session_state[IPS_CURRENT_USER_FULL_NAME_KEY] = "Amanda M. Robicheaux"
        st.session_state[CURRENT_USER_ID_KEY] = "auth-amanda"
        with patch("app.auth.get_client") as client_mock:
            client_mock.return_value.auth.sign_out.return_value = None
            sign_out()
        self.assertIsNone(st.session_state.get("auth_user"))
        self.assertIsNone(st.session_state.get(IPS_CURRENT_USER_FULL_NAME_KEY))
        self.assertIsNone(st.session_state.get(CURRENT_USER_ID_KEY))

    @patch("app.auth._invalidate_stale_auth_cookies")
    @patch("app.auth._try_get_client")
    @patch("app.auth.is_authenticated", return_value=False)
    def test_failed_cookie_restore_clears_silently_without_reload_pending(
        self,
        _auth_mock,
        get_client_mock,
        invalidate_mock,
    ) -> None:
        client = SimpleNamespace()
        client.auth = SimpleNamespace(
            set_session=Mock(side_effect=RuntimeError("expired")),
        )
        get_client_mock.return_value = client
        cookies = {"ips_auth_at": "old-access", "ips_auth_rt": "old-refresh"}
        mock_context = SimpleNamespace(cookies=cookies)

        with patch("app.auth.st.context", mock_context):
            try_restore_supabase_session_from_cookies()

        invalidate_mock.assert_called_once()
        self.assertFalse(st.session_state.get("_ips_auth_clear_pending"))

    def test_persist_auth_tokens_stores_explicit_session_keys(self) -> None:
        _persist_auth_tokens("access-1", "refresh-1")
        self.assertEqual(st.session_state[AUTH_ACCESS_TOKEN_KEY], "access-1")
        self.assertEqual(st.session_state[AUTH_REFRESH_TOKEN_KEY], "refresh-1")

    @patch("app.auth.st.stop")
    @patch("app.auth.ensure_authenticated_user_identity")
    @patch("app.auth._live_auth_user_from_client")
    @patch("app.auth.is_authenticated", return_value=True)
    def test_verify_identity_binding_stops_on_profile_mismatch(
        self,
        _auth_mock,
        live_user_mock,
        ensure_mock,
        stop_mock,
    ) -> None:
        live_user_mock.return_value = SimpleNamespace(id="auth-chet", email="chet@example.com")
        st.session_state["auth_user"] = SimpleNamespace(id="auth-chet", email="chet@example.com")
        st.session_state[AUTH_USER_ID_KEY] = "auth-chet"
        st.session_state["auth_profile"] = {
            "id": "auth-amanda",
            "full_name": "Amanda M. Robicheaux",
        }
        verify_identity_binding_or_stop()
        stop_mock.assert_called_once()


class TestPerSessionSupabaseClient(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    @patch("app.db._create_public_supabase_client")
    def test_get_client_uses_per_streamlit_session_instance(self, create_mock) -> None:
        from app.db import _IPS_USER_SUPABASE_CLIENT_KEY, get_client

        client_a = SimpleNamespace(auth=SimpleNamespace(get_session=lambda: None))
        client_b = SimpleNamespace(auth=SimpleNamespace(get_session=lambda: None))
        create_mock.side_effect = [client_a, client_b]

        st.session_state[AUTH_ACCESS_TOKEN_KEY] = "token-a"
        st.session_state[AUTH_REFRESH_TOKEN_KEY] = "refresh-a"
        first = get_client()
        st.session_state.clear()
        st.session_state[AUTH_ACCESS_TOKEN_KEY] = "token-b"
        st.session_state[AUTH_REFRESH_TOKEN_KEY] = "refresh-b"
        second = get_client()

        self.assertIs(first, client_a)
        self.assertIs(second, client_b)
        self.assertIsNot(first, second)
        self.assertEqual(st.session_state.get(_IPS_USER_SUPABASE_CLIENT_KEY), client_b)


if __name__ == "__main__":
    unittest.main()
