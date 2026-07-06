"""Rental equipment inspection form constants."""

from __future__ import annotations

from typing import Any

INSPECTION_TYPES: tuple[str, ...] = ("checkout", "daily", "return")
INSPECTION_TYPE_LABELS: dict[str, str] = {
    "checkout": "Checkout Inspection",
    "daily": "Daily Inspection",
    "return": "Return Inspection",
}

GENERAL_CONDITIONS: tuple[str, ...] = ("Excellent", "Good", "Fair", "Damaged")
CHECKLIST_CONDITIONS: tuple[str, ...] = ("Excellent", "Good", "Fair", "Damaged", "N/A")
YES_NO: tuple[str, ...] = ("Yes", "No", "N/A")
LEVEL_OPTIONS: tuple[str, ...] = ("Full", "OK", "Low", "Empty", "N/A")

CHECKLIST_ITEMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("body_damage", "Body Damage", CHECKLIST_CONDITIONS),
    ("paint", "Paint", CHECKLIST_CONDITIONS),
    ("leaks", "Leaks", CHECKLIST_CONDITIONS),
    ("hydraulics", "Hydraulics", CHECKLIST_CONDITIONS),
    ("electrical", "Electrical", CHECKLIST_CONDITIONS),
    ("controls", "Controls", CHECKLIST_CONDITIONS),
    ("safety_devices", "Safety Devices", CHECKLIST_CONDITIONS),
    ("tires", "Tires", CHECKLIST_CONDITIONS),
    ("fuel_level", "Fuel Level", LEVEL_OPTIONS),
    ("oil_level", "Oil Level", LEVEL_OPTIONS),
    ("coolant", "Coolant", LEVEL_OPTIONS),
    ("battery", "Battery", CHECKLIST_CONDITIONS),
    ("accessories_present", "Accessories Present", YES_NO),
    ("decals", "Decals", CHECKLIST_CONDITIONS),
    ("hour_meter", "Hour Meter", YES_NO),
    ("operational_test", "Operational Test", YES_NO),
)

REQUIRED_PHOTO_SLOTS: tuple[str, ...] = (
    "front",
    "back",
    "left_side",
    "right_side",
    "serial_plate",
    "hour_meter",
    "engine",
    "existing_damage",
    "accessories",
)

PHOTO_SLOT_LABELS: dict[str, str] = {
    "front": "Front",
    "back": "Back",
    "left_side": "Left Side",
    "right_side": "Right Side",
    "serial_plate": "Serial Number Plate",
    "hour_meter": "Hour Meter / Odometer",
    "engine": "Engine / Power Unit",
    "existing_damage": "Existing Damage",
    "accessories": "Accessories Included",
    "damage_photo": "Damage Photo",
}

SIGNATURE_ROLES: tuple[str, ...] = ("ips_employee", "customer")
SIGNATURE_ROLE_LABELS: dict[str, str] = {
    "ips_employee": "IPS Employee Signature",
    "customer": "Customer Signature",
}


def default_checklist() -> dict[str, str]:
    return {key: "" for key, _, _ in CHECKLIST_ITEMS}


def normalize_checklist(raw: Any) -> dict[str, str]:
    base = default_checklist()
    if isinstance(raw, dict):
        for key in base:
            base[key] = str(raw.get(key) or "").strip()
    return base
