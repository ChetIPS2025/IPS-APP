"""Rental equipment inspection form constants."""

from __future__ import annotations

from typing import Any

INSPECTION_TYPES: tuple[str, ...] = ("checkout", "daily", "return", "damage")
INSPECTION_TYPE_LABELS: dict[str, str] = {
    "checkout": "Checkout Inspection",
    "daily": "Daily Inspection",
    "return": "Return Inspection",
    "damage": "Damage Report",
}

GENERAL_CONDITIONS: tuple[str, ...] = ("Excellent", "Good", "Fair", "Damaged")
CHECKLIST_CONDITIONS: tuple[str, ...] = ("Excellent", "Good", "Fair", "Damaged", "N/A")
YES_NO: tuple[str, ...] = ("Yes", "No", "N/A")
LEVEL_OPTIONS: tuple[str, ...] = ("Full", "OK", "Low", "Empty", "N/A")

CHECKLIST_ITEMS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("fuel_battery_level", "Fuel/Battery Level", LEVEL_OPTIONS),
    ("tires_tracks", "Tires/Tracks", CHECKLIST_CONDITIONS),
    ("safety_equipment", "Safety Equipment", CHECKLIST_CONDITIONS),
    ("accessories_present", "Accessories Present", YES_NO),
    ("hour_meter_applies", "Hour Meter Applies", YES_NO),
)

REQUIRED_PHOTO_SLOTS: tuple[str, ...] = (
    "front",
    "back",
    "left_side",
    "right_side",
    "serial_plate",
)

CONDITIONAL_PHOTO_SLOTS: tuple[str, ...] = ("hour_meter",)

PHOTO_SLOT_LABELS: dict[str, str] = {
    "front": "Front",
    "back": "Rear",
    "left_side": "Left Side",
    "right_side": "Right Side",
    "serial_plate": "Serial Number",
    "hour_meter": "Hour Meter",
    "damage_photo": "Damage Photo",
}

DAMAGE_ITEM_OPTIONS: tuple[str, ...] = (
    "Body / Frame",
    "Engine / Motor",
    "Hydraulics",
    "Electrical",
    "Tires / Tracks",
    "Controls",
    "Safety Equipment",
    "Accessories",
    "Other",
)

SIGNATURE_ROLES: tuple[str, ...] = ("ips_employee", "customer")
SIGNATURE_ROLE_LABELS: dict[str, str] = {
    "ips_employee": "IPS Supervisor Signature",
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


def required_photo_slots_for_checklist(checklist: dict[str, str] | None) -> tuple[str, ...]:
    """Core photos plus hour meter when applicable."""
    slots = list(REQUIRED_PHOTO_SLOTS)
    cl = normalize_checklist(checklist)
    if cl.get("hour_meter_applies") == "Yes":
        slots.append("hour_meter")
    return tuple(slots)
