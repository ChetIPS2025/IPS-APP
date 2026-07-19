"""Employee document persistence and estimate materials helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.estimate_materials_page_service import prepare_material_export_bytes
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
    def test_material_export_bytes_includes_header(self) -> None:
        from app.services.estimate_costing_service import normalize_material_line

        rows = [
            normalize_material_line(
                {
                    "item_number": "A1",
                    "description": "Valve",
                    "category": "Valves",
                    "qty": 2,
                    "unit": "EA",
                    "unit_cost": 10,
                    "total_cost": 20,
                },
                "e-100",
            )
        ]
        with patch("app.services.estimate_materials_page_service.get_estimate_materials", return_value=(rows, False)):
            with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                data = prepare_material_export_bytes("e-100")
        text = data.decode("utf-8")
        self.assertIn("item_number", text)
        self.assertIn("Valve", text)

    def test_inventory_search_skips_inactive(self) -> None:
        with patch(
            "app.services.pricing_guide_service.cached_pricing_guide_rows",
            return_value=[{"id": "p1", "description": "Live", "item_type": "Material", "is_active": True, "sku": "INV-1"}],
        ):
            with patch(
                "app.services.pricing_guide_service.pricing_item_to_estimate_option",
                side_effect=lambda r: {**r, "unit_cost": 1.0, "markup_pct": 0, "pricing_item_id": r["id"]},
            ):
                with patch("app.services.repository.fetch_rows", return_value=([], None)):
                    with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                        from app.services.estimate_material_reference_service import search_estimate_inventory_options

                        out = search_estimate_inventory_options(limit=10)
        self.assertEqual(len(out), 1)
        self.assertIn("INV-1", out[0]["sku"])


if __name__ == "__main__":
    unittest.main()
