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
        self.assertTrue(perms.can_delete)

    def test_delete_permission_by_role(self) -> None:
        cases = {
            "admin": True,
            "manager": True,
            "supervisor": False,
            "office": False,
            "employee": False,
        }
        for role, expected in cases.items():
            with self.subTest(role=role):
                st.session_state.clear()
                st.session_state[CURRENT_USER_PROFILE_KEY] = {
                    "id": f"user-{role}",
                    "full_name": role.title(),
                    "email": f"{role}@example.com",
                    "role": role,
                }
                perms = load_customer_permissions()
                self.assertEqual(perms.can_delete, expected)


if __name__ == "__main__":
    unittest.main()
