from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import streamlit as st

from app import auth


class AuthSessionStateTest(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_init_session_promotes_existing_user_to_authenticated(self) -> None:
        st.session_state["auth_user"] = {"id": "u-1"}

        auth.init_session()

        self.assertIs(st.session_state["authenticated"], True)
        self.assertIs(auth.require_login(), True)

    def test_apply_user_profile_sets_canonical_auth_state(self) -> None:
        user = SimpleNamespace(id="u-1", email="field@example.com")
        profile = {"id": "u-1", "email": "field@example.com", "role": "pm", "is_active": True}

        with patch.object(auth, "fetch_one", side_effect=[profile]):
            auth._apply_user_and_profile_from_auth_user(user)

        self.assertIs(st.session_state["authenticated"], True)
        self.assertIs(st.session_state["user"], user)
        self.assertIs(st.session_state["auth_user"], user)
        self.assertEqual(st.session_state["auth_profile"], profile)
        self.assertEqual(st.session_state["user_email"], "field@example.com")
        self.assertEqual(st.session_state["role"], "manager")
        self.assertIs(auth.require_login(), True)

    def test_require_login_uses_authenticated_as_source_of_truth(self) -> None:
        st.session_state["authenticated"] = False
        st.session_state["user"] = {"id": "stale-user"}
        st.session_state["auth_user"] = {"id": "stale-auth-user"}

        self.assertIs(auth.require_login(), False)

    def test_sign_out_is_the_auth_state_clear_path(self) -> None:
        st.session_state.update(
            {
                "authenticated": True,
                "user": {"id": "u-1"},
                "user_email": "field@example.com",
                "role": "admin",
                "auth_user": {"id": "u-1"},
                "auth_profile": {"id": "u-1"},
                "auth_employee": {"id": "e-1"},
                "_ips_auth_persist_pending": {"access_token": "a", "refresh_token": "r"},
            }
        )

        with patch.object(auth, "get_client") as get_client:
            get_client.return_value.auth.sign_out.return_value = None
            auth.sign_out()

        self.assertIs(st.session_state["authenticated"], False)
        self.assertIsNone(st.session_state["user"])
        self.assertIsNone(st.session_state["user_email"])
        self.assertIsNone(st.session_state["role"])
        self.assertIsNone(st.session_state["auth_user"])
        self.assertIsNone(st.session_state["auth_profile"])
        self.assertIsNone(st.session_state["auth_employee"])
        self.assertNotIn("_ips_auth_persist_pending", st.session_state)
        self.assertIs(st.session_state["_ips_auth_clear_pending"], True)


if __name__ == "__main__":
    unittest.main()
