"""Unit tests for rental equipment inspection service."""

from __future__ import annotations

import unittest

from app.services.rental_equipment_inspection_service import (
    is_rental_equipment,
    rental_inspection_dashboard_status,
    validate_for_complete,
)
from app.services.rental_equipment_inspection_specs import (
    default_checklist,
    normalize_checklist,
    required_photo_slots_for_checklist,
)


def _full_checklist() -> dict[str, str]:
    cl = default_checklist()
    cl["fuel_battery_level"] = "Full"
    cl["tires_tracks"] = "Good"
    cl["safety_equipment"] = "Good"
    cl["accessories_present"] = "Yes"
    cl["hour_meter_applies"] = "No"
    return cl


def _core_photos() -> list[dict[str, str]]:
    return [{"slot": s, "photo_path": f"x/{s}.jpg"} for s in (
        "front", "back", "left_side", "right_side", "serial_plate",
    )]


def _signatures() -> dict[str, dict[str, str]]:
    return {
        "ips_employee": {"signer_name": "Supervisor", "signature_data": "sig"},
        "customer": {"signer_name": "Customer", "signature_data": "sig"},
    }


class TestRentalEquipmentInspection(unittest.TestCase):
    def test_is_rental_equipment_by_category(self) -> None:
        self.assertTrue(is_rental_equipment({"category": "Rental Equipment"}))
        self.assertFalse(is_rental_equipment({"category": "Tool"}))

    def test_is_rental_equipment_by_rentable_flag(self) -> None:
        self.assertTrue(is_rental_equipment({"is_rentable": True}))
        self.assertTrue(is_rental_equipment({"is_rental": True}))

    def test_required_photo_slots_include_hour_meter_when_applicable(self) -> None:
        cl = _full_checklist()
        cl["hour_meter_applies"] = "Yes"
        slots = required_photo_slots_for_checklist(cl)
        self.assertIn("hour_meter", slots)
        cl["hour_meter_applies"] = "No"
        self.assertNotIn("hour_meter", required_photo_slots_for_checklist(cl))

    def test_validate_requires_photos_for_checkout(self) -> None:
        data = {
            "inspection_type": "checkout",
            "general_condition": "Good",
            "checklist": _full_checklist(),
            "photo_attachments": [],
            "signatures": _signatures(),
        }
        errs = validate_for_complete(data)
        self.assertTrue(any("Photo required" in e for e in errs))

    def test_validate_return_damaged_requires_description_and_photo(self) -> None:
        data = {
            "inspection_type": "return",
            "general_condition": "Damaged",
            "checklist": _full_checklist(),
            "photo_attachments": _core_photos(),
            "signatures": _signatures(),
        }
        errs = validate_for_complete(data)
        self.assertTrue(any("Damage description" in e for e in errs))
        self.assertTrue(any("Damage photo" in e for e in errs))

    def test_validate_damage_report(self) -> None:
        data = {
            "inspection_type": "damage",
            "damage_location": "Hydraulics",
            "damage_description": "Leaking hose",
            "photo_attachments": [],
        }
        errs = validate_for_complete(data)
        self.assertTrue(any("Damage photo" in e for e in errs))

    def test_validate_damage_report_complete(self) -> None:
        data = {
            "inspection_type": "damage",
            "damage_location": "Hydraulics",
            "damage_description": "Leaking hose",
            "photo_attachments": [{"slot": "damage_photo", "photo_path": "x/damage.jpg"}],
        }
        self.assertEqual(validate_for_complete(data), [])

    def test_dashboard_status_awaiting_open_draft(self) -> None:
        asset = {"id": "a1", "assigned_job_id": "j1"}
        inspections = [{"inspection_type": "checkout", "status": "draft"}]
        self.assertEqual(rental_inspection_dashboard_status(asset, inspections), "Awaiting Inspection")

    def test_normalize_checklist(self) -> None:
        merged = normalize_checklist({"fuel_battery_level": "Low"})
        self.assertEqual(merged["fuel_battery_level"], "Low")
        self.assertEqual(merged["tires_tracks"], "")


if __name__ == "__main__":
    unittest.main()
