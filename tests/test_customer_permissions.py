"""Customer permissions snapshot tests."""

from __future__ import annotations

import unittest

import streamlit as st

from app.auth import CURRENT_USER_PROFILE_KEY
from app.components.customer_permissions import load_customer_permissions


class TestCustomerPermissions(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_load_customer_permissions_ignores_supabase_user_in_session(self) -> None:
        class UserObj:
            id = "auth-amanda"
            email = "amanda@example.com"

        st.session_state["user"] = UserObj()
        st.session_state[CURRENT_USER_PROFILE_KEY] = {
            "id": "auth-amanda",
            "full_name": "Amanda M. Robicheaux",
            "email": "amanda@example.com",
            "role": "admin",
        }

        perms = load_customer_permissions()

        self.assertEqual(perms.user_id, "auth-amanda")
        self.assertEqual(perms.user_name, "Amanda M. Robicheaux")
        self.assertTrue(perms.can_create)


if __name__ == "__main__":
    unittest.main()
