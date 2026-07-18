"""Unit tests for tool trailer dashboard service."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.trailer_dashboard_service import (
    audit_item_requires_missing_note,
    audit_item_requires_photo,
    map_spot_audit_condition,
    normalize_audit_item_status,
    select_spot_audit_items,
    validate_audit_item_line,
)


class TestTrailerDashboardService(unittest.TestCase):
    def test_map_spot_audit_condition(self) -> None:
        self.assertEqual(map_spot_audit_condition("Excellent"), ("Good", "Present"))
        self.assertEqual(map_spot_audit_condition("Replace"), ("Needs Repair", "Needs Replacement"))

    def test_audit_photo_rules(self) -> None:
        self.assertTrue(audit_item_requires_photo("Present"))
        self.assertTrue(audit_item_requires_photo("Damaged"))
        self.assertTrue(audit_item_requires_photo("Needs Repair"))
        self.assertFalse(audit_item_requires_photo("Missing"))
        self.assertTrue(audit_item_requires_missing_note("Missing"))

    def test_validate_audit_item_line(self) -> None:
        self.assertIsNotNone(
            validate_audit_item_line({"status": "Present", "photo_path": ""}, item_label="Hammer")
        )
        self.assertIsNone(
            validate_audit_item_line(
                {"status": "Present", "photo_path": "assets/x.jpg"},
                item_label="Hammer",
            )
        )
        self.assertIsNotNone(
            validate_audit_item_line({"status": "Missing", "notes": ""}, item_label="Hammer")
        )
        self.assertIsNone(
            validate_audit_item_line(
                {"status": "Missing", "notes": "Checked bin A — not found"},
                item_label="Hammer",
            )
        )

    def test_normalize_audit_item_status(self) -> None:
        self.assertEqual(normalize_audit_item_status("Needs Repair"), "Needs Replacement")

    @patch("app.services.trailer_dashboard_service.get_trailer_inventory_items")
    def test_select_spot_audit_items_caps_at_pool_size(self, items_mock) -> None:
        items_mock.return_value = [{"id": f"i{n}", "item_name": f"Tool {n}"} for n in range(3)]
        sample = select_spot_audit_items("trailer-1", count=5, seed=42)
        self.assertEqual(len(sample), 3)

    @patch("app.services.trailer_dashboard_service.get_trailer_inventory_items")
    def test_select_spot_audit_items_returns_five_when_available(self, items_mock) -> None:
        items_mock.return_value = [{"id": f"i{n}", "item_name": f"Tool {n}"} for n in range(8)]
        sample = select_spot_audit_items("trailer-1", count=5, seed=7)
        self.assertEqual(len(sample), 5)
        ids = {str(i.get("id")) for i in sample}
        self.assertEqual(len(ids), 5)


if __name__ == "__main__":
    unittest.main()
