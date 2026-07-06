"""Unit tests for rental equipment inspection service."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.rental_equipment_inspection_service import (
    is_rental_equipment,
    rental_inspection_dashboard_status,
    validate_for_complete,
)
from app.services.rental_equipment_inspection_specs import default_checklist, normalize_checklist


class TestRentalEquipmentInspection(unittest.TestCase):
    def test_is_rental_equipment_by_category(self) -> None:
        self.assertTrue(is_rental_equipment({"category": "Rental Equipment"}))
        self.assertFalse(is_rental_equipment({"category": "Tool"}))

    def test_is_rental_equipment_by_rentable_flag(self) -> None:
        self.assertTrue(is_rental_equipment({"is_rentable": True}))
        self.assertTrue(is_rental_equipment({"is_rental": True}))

    def test_validate_requires_photos_for_checkout(self) -> None:
        data = {
            "inspection_type": "checkout",
            "general_condition": "Good",
            "checklist": {k: "Good" for k in default_checklist()},
            "photo_attachments": [],
            "signatures": {
                "ips_employee": {"signer_name": "A", "signature_data": "data:image/png;base64,abc"},
                "customer": {"signer_name": "B", "signature_data": "data:image/png;base64,def"},
            },
        }
        errs = validate_for_complete(data)
        self.assertTrue(any("Photo required" in e for e in errs))

    def test_validate_missing_damage_fields(self) -> None:
        data = {
            "inspection_type": "return",
            "general_condition": "Damaged",
            "checklist": {k: "Damaged" for k in default_checklist()},
            "photo_attachments": [{"slot": s, "photo_path": f"x/{s}.jpg"} for s in (
                "front", "back", "left_side", "right_side", "serial_plate",
                "hour_meter", "engine", "existing_damage", "accessories",
            )],
            "damage_reported": True,
            "signatures": {
                "ips_employee": {"signer_name": "A", "signature_data": "sig"},
                "customer": {"signer_name": "B", "signature_data": "sig"},
            },
        }
        errs = validate_for_complete(data)
        self.assertTrue(any("Damage description" in e for e in errs))

    def test_dashboard_status_awaiting_open_draft(self) -> None:
        asset = {"id": "a1", "assigned_job_id": "j1"}
        inspections = [{"inspection_type": "checkout", "status": "draft"}]
        self.assertEqual(rental_inspection_dashboard_status(asset, inspections), "Awaiting Inspection")

    def test_normalize_checklist(self) -> None:
        merged = normalize_checklist({"body_damage": "Fair"})
        self.assertEqual(merged["body_damage"], "Fair")
        self.assertEqual(merged["paint"], "")


if __name__ == "__main__":
    unittest.main()
