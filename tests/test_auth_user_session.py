"""Auth session identity sync for dashboard greeting."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import streamlit as st

from app.auth import (
    IPS_CURRENT_USER_FULL_NAME_KEY,
    IPS_CURRENT_USER_ID_KEY,
    _clear_stale_user_identity,
    _sync_current_user_snapshot,
    current_user_display_name,
    sign_out,
    sync_authenticated_user,
)


class TestAuthUserSession(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_sync_current_user_snapshot_stores_full_name(self) -> None:
        _sync_current_user_snapshot(
            {
                "id": "user-amanda",
                "email": "amanda@example.com",
                "full_name": "Amanda M. Robicheaux",
                "role": "admin",
            }
        )
        self.assertEqual(st.session_state[IPS_CURRENT_USER_ID_KEY], "user-amanda")
        self.assertEqual(
            st.session_state[IPS_CURRENT_USER_FULL_NAME_KEY],
            "Amanda M. Robicheaux",
        )

    def test_clear_stale_user_identity_removes_cached_profile(self) -> None:
        st.session_state["auth_profile"] = {"id": "chet", "full_name": "Chet Breaux"}
        st.session_state[IPS_CURRENT_USER_FULL_NAME_KEY] = "Chet Breaux"
        _clear_stale_user_identity()
        self.assertIsNone(st.session_state.get("auth_profile"))
        self.assertIsNone(st.session_state.get(IPS_CURRENT_USER_FULL_NAME_KEY))

    @patch("app.auth._live_auth_user_from_client")
    @patch("app.auth._reload_profile_for_user_id")
    def test_sync_authenticated_user_reloads_mismatched_profile(
        self,
        reload_mock,
        live_user_mock,
    ) -> None:
        st.session_state["auth_user"] = SimpleNamespace(id="user-amanda")
        st.session_state["auth_profile"] = {
            "id": "user-chet",
            "full_name": "Chet Breaux",
            "role": "admin",
            "is_active": True,
        }
        live_user_mock.return_value = SimpleNamespace(id="user-amanda")
        reload_mock.return_value = {
            "id": "user-amanda",
            "full_name": "Amanda M. Robicheaux",
            "email": "amanda@example.com",
            "role": "admin",
            "is_active": True,
        }

        self.assertTrue(sync_authenticated_user(force_profile_reload=True))
        self.assertEqual(st.session_state["auth_profile"]["id"], "user-amanda")
        self.assertEqual(
            st.session_state[IPS_CURRENT_USER_FULL_NAME_KEY],
            "Amanda M. Robicheaux",
        )

    def test_current_user_display_name_uses_snapshot_not_stale_profile(self) -> None:
        st.session_state["auth_user"] = SimpleNamespace(id="user-amanda")
        st.session_state[IPS_CURRENT_USER_ID_KEY] = "user-amanda"
        st.session_state[IPS_CURRENT_USER_FULL_NAME_KEY] = "Amanda M. Robicheaux"
        st.session_state["auth_profile"] = {
            "id": "user-chet",
            "full_name": "Chet Breaux",
        }

        self.assertEqual(current_user_display_name(), "Amanda M. Robicheaux")

    def test_sign_out_clears_user_snapshot(self) -> None:
        st.session_state["auth_user"] = SimpleNamespace(id="user-amanda")
        st.session_state[IPS_CURRENT_USER_FULL_NAME_KEY] = "Amanda M. Robicheaux"
        with patch("app.auth.get_client") as client_mock:
            client_mock.return_value.auth.sign_out.return_value = None
            sign_out()
        self.assertIsNone(st.session_state.get("auth_user"))
        self.assertIsNone(st.session_state.get(IPS_CURRENT_USER_FULL_NAME_KEY))


if __name__ == "__main__":
    unittest.main()
