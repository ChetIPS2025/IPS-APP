"""Auth session identity sync for dashboard greeting."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import streamlit as st

from app.auth import (
    CURRENT_USER_ID_KEY,
    IPS_CURRENT_USER_FULL_NAME_KEY,
    _clear_cached_identity_keys,
    _sync_current_user_snapshot,
    current_user_display_name,
    ensure_authenticated_user_identity,
    sign_out,
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
        self.assertEqual(st.session_state[CURRENT_USER_ID_KEY], "auth-amanda")
        self.assertEqual(
            st.session_state[IPS_CURRENT_USER_FULL_NAME_KEY],
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


if __name__ == "__main__":
    unittest.main()
