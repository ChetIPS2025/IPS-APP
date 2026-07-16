"""Tests for small hand tool photo upload and catalog image resolution."""

from __future__ import annotations

import unittest
from unittest.mock import patch


class TestSmallHandToolImages(unittest.TestCase):
    def test_owned_image_url_returns_none_without_metadata(self) -> None:
        from app.services.small_hand_tool_images import get_small_hand_tool_owned_image_url

        self.assertIsNone(get_small_hand_tool_owned_image_url({"id": "t1", "tool_name": "Hammer"}))

    @patch("app.services.small_hand_tool_images.resolve_image_url_by_field_priority")
    @patch("app.services.small_hand_tool_images.has_owned_stored_item_image", return_value=True)
    def test_owned_image_url_when_metadata_present(
        self,
        _mock_owned,
        mock_resolve,
    ) -> None:
        from app.services.small_hand_tool_images import get_small_hand_tool_owned_image_url

        mock_resolve.return_value = "https://example.com/tool.jpg"
        tool = {"id": "t1", "image_path": "assets/item_images/small_hand_tools/t1/x.jpg"}
        self.assertEqual(get_small_hand_tool_owned_image_url(tool), "https://example.com/tool.jpg")

    def test_preview_record_strips_fallback_fields(self) -> None:
        from app.services.item_images import IMAGE_STATUS_MISSING
        from app.services.small_hand_tool_images import small_hand_tool_photo_preview_record

        preview = small_hand_tool_photo_preview_record({"id": "t1", "tool_name": "Pliers"})
        self.assertEqual(preview.get("image_status"), IMAGE_STATUS_MISSING)
        self.assertEqual(preview.get("image_path"), "")

    @patch("app.services.small_hand_tool_images.get_small_hand_tool_owned_image_url")
    def test_catalog_resolver_prefers_owned_photo(self, mock_owned) -> None:
        from app.services.catalog_images import get_catalog_image_url

        mock_owned.return_value = "https://example.com/owned.jpg"
        record = {"id": "t1", "tool_name": "Wrench", "row_type": "hand_tool"}
        url = get_catalog_image_url(record, kind="small_tool")
        self.assertEqual(url, "https://example.com/owned.jpg")
        mock_owned.assert_called_once()


if __name__ == "__main__":
    unittest.main()
