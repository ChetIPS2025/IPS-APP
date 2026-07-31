"""Tests for Estimate Materials permission loading."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.components.estimate_materials.permissions import load_estimate_materials_permissions


class TestEstimateMaterialsPermissions(unittest.TestCase):
    @patch("app.components.estimate_materials.permissions.current_profile")
    @patch("app.components.estimate_materials.permissions.current_role")
    def test_load_permissions_uses_profile_dict_not_auth_user_object(
        self,
        role_mock,
        profile_mock,
    ) -> None:
        role_mock.return_value = "estimator"
        profile_mock.return_value = {
            "id": "profile-1",
            "full_name": "Pat Estimator",
            "email": "pat@example.com",
        }

        perms = load_estimate_materials_permissions()

        self.assertEqual(perms.user_id, "profile-1")
        self.assertEqual(perms.user_name, "Pat Estimator")
        self.assertTrue(perms.can_edit)


if __name__ == "__main__":
    unittest.main()
