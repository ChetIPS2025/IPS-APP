"""Employee document persistence and estimate materials helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.pages.estimate_materials import _inventory_picker_options, _materials_csv_bytes
from app.services.employee_documents_service import save_employee_document


class TestEmployeeDocumentsService(unittest.TestCase):
    @patch("app.services.employee_documents_service.upload_employee_document_file")
    @patch("app.services.employee_documents_service._save_row")
    @patch("app.services.employee_documents_service.clear_data_cache_for_table")
    def test_save_new_document_uploads_file(self, _cache, save_row, upload_mock) -> None:
        save_row.return_value = MagicMock(ok=True, data={"id": "doc-1"})
        upload_mock.return_value = MagicMock(ok=True, data={"storage_path": "employee-documents/doc-1/x.pdf"})

        uploaded = MagicMock(name="license.pdf", type="application/pdf")
        uploaded.getvalue.return_value = b"pdf-bytes"

        result = save_employee_document(
            {
                "employee_id": "550e8400-e29b-41d4-a716-446655440000",
                "doc_type": "Driver's License",
                "file_name": "license.pdf",
                "is_restricted": False,
            },
            uploaded_file=uploaded,
        )

        self.assertTrue(result.ok)
        save_row.assert_called_once()
        upload_mock.assert_called_once_with("doc-1", uploaded)


class TestEstimateMaterialsHelpers(unittest.TestCase):
    def test_materials_csv_bytes_includes_header(self) -> None:
        data = _materials_csv_bytes(
            [{"item_number": "A1", "description": "Valve", "category": "Valves", "qty": 2, "unit": "EA", "unit_cost": 10, "total_cost": 20}],
            estimate_number="E-100",
        )
        text = data.decode("utf-8")
        self.assertIn("item_number", text)
        self.assertIn("Valve", text)

    def test_inventory_picker_skips_demo_ids(self) -> None:
        labels, by_label = _inventory_picker_options(
            [
                {"id": "demo-1", "sku": "X", "name": "Demo"},
                {"id": "550e8400-e29b-41d4-a716-446655440000", "sku": "INV-1", "name": "Live"},
            ]
        )
        self.assertEqual(len(labels), 1)
        self.assertIn("INV-1", labels[0])
        self.assertIn(labels[0], by_label)


if __name__ == "__main__":
    unittest.main()
