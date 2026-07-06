"""Unit tests for asset QR label PNG export."""

from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from app.services.asset_qr import (
    _asset_number_display,
    load_asset_primary_photo_bytes,
    qr_label_download_basename,
    qr_label_png_bytes,
)

_SAMPLE_ASSET = {
    "id": "ast-test-1",
    "asset_id": "AST-000421",
    "asset_number": "AST-000421",
    "asset_name": "Miller Syncrowave 250 TIG Welder",
    "category": "Welding Equipment",
    "location": "Shop Yard 2",
    "serial_number": "MW-88421",
    "qr_code_value": "IPS-AST-000421",
}


class TestAssetQrLabels(unittest.TestCase):
    def test_basename_and_number_display(self) -> None:
        self.assertEqual(qr_label_download_basename(_SAMPLE_ASSET), "AST-000421_qr_label")
        self.assertEqual(_asset_number_display(_SAMPLE_ASSET), "AST-000421")

    @patch("app.services.asset_qr.load_asset_primary_photo_bytes", return_value=None)
    def test_label_png_sizes_use_print_ready_dimensions(self, _photo) -> None:
        from PIL import Image

        subject = "https://app.example.com/?scan=asset&token=abc"
        png_1x4 = qr_label_png_bytes(_SAMPLE_ASSET, subject, size="1x4")
        png_2x6 = qr_label_png_bytes(_SAMPLE_ASSET, subject, size="2x6")
        self.assertTrue(png_1x4.startswith(b"\x89PNG"))
        self.assertTrue(png_2x6.startswith(b"\x89PNG"))
        self.assertEqual(Image.open(io.BytesIO(png_1x4)).size, (1200, 300))
        self.assertEqual(Image.open(io.BytesIO(png_2x6)).size, (1800, 600))

    @patch("app.services.asset_qr.load_asset_primary_photo_bytes", return_value=None)
    def test_label_png_non_empty_without_photo(self, _photo) -> None:
        png = qr_label_png_bytes(_SAMPLE_ASSET, "https://example.com/?scan=asset", size="1x4")
        self.assertGreater(len(png), 500)

    def test_load_primary_photo_returns_none_without_image(self) -> None:
        self.assertIsNone(load_asset_primary_photo_bytes({"id": "x", "asset_name": "No photo"}))


if __name__ == "__main__":
    unittest.main()
