"""Tests for pricing guide inline quantity on hand."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.catalog_stock_policy_service import (
    linked_inventory_quantity,
    save_pricing_stock_settings,
)


class TestCatalogStockPolicyQuantity(unittest.TestCase):
    @patch("app.services.catalog_stock_policy_service.get_inventory_item")
    def test_linked_inventory_quantity(self, get_mock) -> None:
        get_mock.return_value = {"quantity_on_hand": 12.0}
        qty = linked_inventory_quantity({"linked_inventory_id": "inv-1"})
        self.assertEqual(qty, 12.0)

    @patch("app.services.catalog_stock_policy_service._apply_quantity_on_hand_to_inventory")
    @patch("app.services.catalog_stock_policy_service.apply_pricing_stock_settings_to_inventory")
    @patch("app.services.catalog_stock_policy_service._ensure_inventory_link_for_policy")
    @patch("app.services.repository.update_row_admin")
    @patch("app.services.pricing_guide_service.cached_pricing_guide_rows")
    @patch("app.services.catalog_stock_policy_service.clear_pricing_guide_cache")
    def test_save_optional_creates_inventory_when_qty_set(
        self,
        _cache_mock,
        rows_mock,
        upd_mock,
        ensure_mock,
        sync_mock,
        qty_mock,
    ) -> None:
        pg_row = {"id": "pg-1", "stock_policy": "none"}
        fresh = {"id": "pg-1", "stock_policy": "optional", "linked_inventory_id": "inv-9"}
        rows_mock.return_value = [fresh]
        upd_mock.return_value = MagicMock(ok=True)
        ensure_mock.return_value = (fresh, ["Inventory record created for optional extras item."], None)
        sync_mock.return_value = MagicMock(ok=True, data={})
        qty_mock.return_value = (["Quantity on hand set to 5."], None)

        result = save_pricing_stock_settings(
            pg_row,
            stock_policy="optional",
            default_reorder_point=0.0,
            quantity_on_hand=5.0,
        )

        self.assertTrue(result.ok)
        ensure_mock.assert_called_once()
        qty_mock.assert_called_once_with(fresh, 5.0)
        self.assertIn("Quantity on hand set to 5.", str(result.data.get("message")))


if __name__ == "__main__":
    unittest.main()
