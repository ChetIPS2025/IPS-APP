"""Unit tests for tool trailer dashboard service."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.trailer_dashboard_service import (
    map_spot_audit_condition,
    select_spot_audit_items,
)


class TestTrailerDashboardService(unittest.TestCase):
    def test_map_spot_audit_condition(self) -> None:
        self.assertEqual(map_spot_audit_condition("Excellent"), ("Good", "Present"))
        self.assertEqual(map_spot_audit_condition("Replace"), ("Needs Repair", "Needs Replacement"))

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
