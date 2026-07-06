"""Unit tests for inventory QR label export (PDF/PNG/CSV/ZIP)."""

from __future__ import annotations

import csv
import io
import unittest
import zipfile
from unittest.mock import patch

from app.services.inventory_qr_labels import (
    build_inventory_labels_csv,
    build_inventory_labels_zip,
    inventory_item_description,
    inventory_label_download_basename,
    inventory_label_for_download,
    inventory_label_pdf_bytes,
    inventory_label_png_bytes,
    inventory_qr_subject,
)


_SAMPLE_ITEM = {
    "id": "inv-test-1",
    "sku": "PIPE-2IN",
    "name": "2 inch schedule 40 pipe",
    "qr_code_value": "inv:PIPE-2IN",
}


class TestInventoryQrLabels(unittest.TestCase):
    @patch("app.services.inventory_qr_labels.load_inventory_thumbnail_bytes", return_value=None)
    @patch(
        "app.services.inventory_service.generate_inventory_qr_value",
        return_value="https://app.example.com/?scan=inventory&token=abc",
    )
    def test_inventory_qr_subject_prefers_http_url(self, _gen, _thumb) -> None:
        self.assertEqual(
            inventory_qr_subject(_SAMPLE_ITEM),
            "https://app.example.com/?scan=inventory&token=abc",
        )

    def test_inventory_item_description_and_basename(self) -> None:
        self.assertEqual(inventory_item_description(_SAMPLE_ITEM), "2 inch schedule 40 pipe")
        self.assertEqual(inventory_label_download_basename(_SAMPLE_ITEM), "PIPE-2IN_inv_label")

    @patch("app.services.inventory_qr_labels.load_inventory_thumbnail_bytes", return_value=None)
    def test_label_pdf_and_png_non_empty(self, _thumb) -> None:
        subject = "https://app.example.com/?scan=inventory&token=abc"
        pdf = inventory_label_pdf_bytes(_SAMPLE_ITEM, subject)
        png = inventory_label_png_bytes(_SAMPLE_ITEM, subject)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertTrue(png.startswith(b"\x89PNG"))

    @patch("app.services.inventory_qr_labels.load_inventory_thumbnail_bytes", return_value=None)
    def test_label_png_sizes_use_print_ready_dimensions(self, _thumb) -> None:
        from PIL import Image

        subject = "https://app.example.com/?scan=inventory&token=abc"
        png_1x4 = inventory_label_png_bytes(_SAMPLE_ITEM, subject, size="1x4")
        png_2x6 = inventory_label_png_bytes(_SAMPLE_ITEM, subject, size="2x6")
        self.assertEqual(Image.open(io.BytesIO(png_1x4)).size, (300, 1200))
        self.assertEqual(Image.open(io.BytesIO(png_2x6)).size, (600, 1800))

    @patch("app.services.inventory_qr_labels.load_inventory_thumbnail_bytes", return_value=None)
    def test_label_for_download_returns_pdf(self, _thumb) -> None:
        subject = "https://app.example.com/?scan=inventory&token=abc"
        data, mime, name = inventory_label_for_download(_SAMPLE_ITEM, subject)
        self.assertEqual(mime, "application/pdf")
        self.assertTrue(name.endswith(".pdf"))
        self.assertTrue(data.startswith(b"%PDF"))

    @patch("app.services.inventory_qr_labels.load_inventory_thumbnail_bytes", return_value=None)
    @patch(
        "app.services.inventory_qr_labels.inventory_qr_subject",
        return_value="https://app.example.com/?scan=inventory&token=abc",
    )
    @patch(
        "app.services.inventory_qr_labels.resolve_inventory_qr_value",
        return_value="inv:PIPE-2IN",
    )
    def test_csv_headers_and_row(self, _qr_val, _subject, _thumb) -> None:
        text = build_inventory_labels_csv([_SAMPLE_ITEM])
        rows = list(csv.reader(io.StringIO(text)))
        self.assertEqual(
            rows[0],
            ["sku", "description", "scan_url", "qr_code_value", "image_file", "label_pdf"],
        )
        self.assertEqual(rows[1][0], "PIPE-2IN")
        self.assertIn("labels/PIPE-2IN_inv_label.pdf", rows[1][5])

    @patch("app.services.inventory_qr_labels.load_inventory_thumbnail_bytes", return_value=None)
    @patch(
        "app.services.inventory_qr_labels.inventory_qr_subject",
        return_value="https://app.example.com/?scan=inventory&token=abc",
    )
    def test_zip_contains_csv_and_label_files(self, _subject, _thumb) -> None:
        blob = build_inventory_labels_zip([_SAMPLE_ITEM])
        self.assertTrue(blob)
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            names = set(zf.namelist())
        self.assertIn("inventory_labels.csv", names)
        self.assertIn("labels/PIPE-2IN_inv_label.pdf", names)
        self.assertIn("qr/PIPE-2IN_inv_label_qr.png", names)


if __name__ == "__main__":
    unittest.main()
