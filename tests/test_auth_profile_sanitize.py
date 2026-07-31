"""Auth profile session sanitization tests."""

from __future__ import annotations

import unittest

import streamlit as st

from app.auth import coerce_profile_dict, sanitize_auth_session_profiles


class TestAuthProfileSanitize(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_coerce_profile_dict_rejects_user_object(self) -> None:
        class _FakeUser:
            id = "u1"

        self.assertEqual(coerce_profile_dict(_FakeUser()), {})
        self.assertEqual(coerce_profile_dict({"id": "p1"}), {"id": "p1"})

    def test_sanitize_auth_session_profiles_clears_user_object(self) -> None:
        class _FakeUser:
            id = "u1"

        st.session_state["auth_profile"] = _FakeUser()
        st.session_state["current_user_profile"] = {"id": "p1"}
        sanitize_auth_session_profiles()
        self.assertNotIn("auth_profile", st.session_state)
        self.assertEqual(st.session_state["current_user_profile"]["id"], "p1")


if __name__ == "__main__":
    unittest.main()
