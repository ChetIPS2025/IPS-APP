"""Coupling model specifications and torque verification defaults (IPS V7)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

FORM_VERSION = "V7"

COUPLING_MODEL_OPTIONS: tuple[str, ...] = (
    "1030G20",
    "1035G20",
    "Manual/Custom Coupling",
)

BOLT_COUNT = 8

TORQUE_CLOCK_SEQUENCE: tuple[str, ...] = (
    "12:00",
    "6:00",
    "3:00",
    "9:00",
    "1:30",
    "7:30",
    "4:30",
    "10:30",
)

# Degrees from 3:00 position, counter-clockwise (for torque pattern graphic).
CLOCK_POSITION_ANGLES: dict[str, float] = {
    "12:00": 90.0,
    "6:00": -90.0,
    "3:00": 0.0,
    "9:00": 180.0,
    "1:30": 45.0,
    "7:30": -135.0,
    "4:30": -45.0,
    "10:30": 135.0,
}

_MODEL_SPECS: dict[str, dict[str, Any]] = {
    "1030G20": {
        "coupling_type": "Falk Lifelign 1030G20 Gear Coupling",
        "flange_bolts": "8 bolts, 1/2-20 x 2.0 in",
        "bolt_count": BOLT_COUNT,
        "pass1_torque_ft_lb": 75,
        "pass2_torque_ft_lb": 112,
        "final_torque_ft_lb": 150,
        "final_torque_nm": 203,
        "standard_hub_gap_in": 0.188,
        "lubricant_quantity_lb": 0.80,
        "lubricant_quantity_oz": 12.8,
        "lubricant_type_default": "Falk LTG-10 or approved equivalent",
    },
    "1035G20": {
        "coupling_type": "Falk Lifelign 1035G20 / 1035G20 Gear Coupling",
        "flange_bolts": "8 bolts, 1/2-20 x 2.0 in",
        "bolt_count": BOLT_COUNT,
        "pass1_torque_ft_lb": 90,
        "pass2_torque_ft_lb": 135,
        "final_torque_ft_lb": 180,
        "final_torque_nm": 244,
        "standard_hub_gap_in": 0.188,
        "lubricant_quantity_lb": 0.95,
        "lubricant_quantity_oz": 15.2,
        "lubricant_type_default": "Falk LTG-10 or approved equivalent",
    },
    "Manual/Custom Coupling": {
        "coupling_type": "",
        "flange_bolts": "",
        "bolt_count": BOLT_COUNT,
        "pass1_torque_ft_lb": 75,
        "pass2_torque_ft_lb": 112,
        "final_torque_ft_lb": 150,
        "final_torque_nm": 203,
        "standard_hub_gap_in": None,
        "lubricant_quantity_lb": None,
        "lubricant_quantity_oz": None,
        "lubricant_type_default": "",
    },
}


def default_torque_rows(model_key: str | None = None) -> list[dict[str, Any]]:
    specs = specs_for_model(model_key or "1030G20")
    return [
        {
            "order": i + 1,
            "clock_position": pos,
            "pass1_checked": False,
            "pass2_checked": False,
            "final_checked": False,
            "witness_initials": "",
            "pass_fail": None,
            "notes": "",
            "pass1_torque_ft_lb": specs.get("pass1_torque_ft_lb"),
            "pass2_torque_ft_lb": specs.get("pass2_torque_ft_lb"),
            "final_torque_ft_lb": specs.get("final_torque_ft_lb"),
        }
        for i, pos in enumerate(TORQUE_CLOCK_SEQUENCE)
    ]


def normalize_torque_rows(rows: list[dict[str, Any]] | None, *, model_key: str | None = None) -> list[dict[str, Any]]:
    """Ensure exactly eight bolt rows in sequence order (never twelve)."""
    defaults = default_torque_rows(model_key)
    if not rows:
        return defaults
    by_clock = {str(r.get("clock_position") or ""): dict(r) for r in rows if isinstance(r, dict)}
    out: list[dict[str, Any]] = []
    for i, template in enumerate(defaults):
        pos = template["clock_position"]
        merged = dict(template)
        existing = by_clock.get(pos)
        if existing:
            merged.update(existing)
            merged["order"] = i + 1
            merged["clock_position"] = pos
            # V7: migrate legacy V6 fields
            if not merged.get("witness_initials") and merged.get("initial_signature"):
                merged["witness_initials"] = ""
            merged.pop("initial_signature", None)
            merged.pop("witness_mark_checked", None)
        out.append(merged)
    return out


def torque_sequence_caption() -> str:
    return " → ".join(TORQUE_CLOCK_SEQUENCE)


def torque_pattern_svg(*, width: int = 220, height: int = 220) -> str:
    """8-bolt crisscross/star pattern for UI and documentation."""
    import math

    cx, cy, r = width / 2, height / 2, min(width, height) / 2 - 28
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'class="ips-coupling-torque-pattern" role="img" aria-label="8-bolt torque pattern">',
        f'<circle cx="{cx}" cy="{cy}" r="{r + 8}" fill="#f8fafc" stroke="#cbd5e1" stroke-width="2"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4 3"/>',
    ]
    points: list[tuple[float, float, int, str]] = []
    for i, clock in enumerate(TORQUE_CLOCK_SEQUENCE, start=1):
        deg = CLOCK_POSITION_ANGLES.get(clock, 0.0)
        rad = math.radians(deg)
        x = cx + r * math.cos(rad)
        y = cy - r * math.sin(rad)
        points.append((x, y, i, clock))
    # Crisscross: connect opposite bolt pairs (star/diamond).
    cross_pairs = ((0, 4), (1, 5), (2, 6), (3, 7))
    for a, b in cross_pairs:
        x1, y1, _, _ = points[a]
        x2, y2, _, _ = points[b]
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#2563eb" stroke-width="1.5" opacity="0.55"/>'
        )
    # Sequence ring (torque order).
    for i in range(len(points)):
        x1, y1, _, _ = points[i]
        x2, y2, _, _ = points[(i + 1) % len(points)]
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#64748b" stroke-width="1" stroke-dasharray="3 2" opacity="0.7"/>'
        )
    for x, y, num, clock in points:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="#2563eb" stroke="#ffffff" stroke-width="2"/>')
        parts.append(
            f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" font-size="10" '
            f'font-weight="700" fill="#ffffff">{num}</text>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y + 18:.1f}" text-anchor="middle" font-size="8" '
            f'fill="#475569">{clock}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def specs_for_model(model_key: str) -> dict[str, Any]:
    key = str(model_key or "").strip()
    if key not in _MODEL_SPECS:
        key = "Manual/Custom Coupling"
    return deepcopy(_MODEL_SPECS[key])


def model_label(model_key: str) -> str:
    key = str(model_key or "").strip()
    if key == "1030G20":
        return "Falk Lifelign 1030G20"
    if key == "1035G20":
        return "Falk Lifelign 1035G20"
    return "Manual/Custom Coupling"


def torque_pass_labels(specs: dict[str, Any]) -> tuple[str, str, str]:
    p1 = specs.get("pass1_torque_ft_lb")
    p2 = specs.get("pass2_torque_ft_lb")
    pf = specs.get("final_torque_ft_lb")
    return (
        f"{p1:g} ft-lb" if p1 is not None else "Pass 1",
        f"{p2:g} ft-lb" if p2 is not None else "Pass 2",
        f"{pf:g} ft-lb" if pf is not None else "Final",
    )


INSPECTION_RESULT_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("actual_hub_gap_in", "Actual Hub Gap", "number"),
    ("lubricant_type", "Lubricant Type", "text"),
    ("lubricant_quantity_added", "Lubricant Qty Added", "text"),
    ("coupling_teeth_condition", "Coupling Teeth Condition", "text"),
    ("grease_condition", "Grease Condition", "text"),
    ("seal_condition", "Seal Condition", "text"),
    ("cover_installed", "Cover Installed", "bool"),
    ("fasteners_witness_marked", "Fasteners Witness Marked", "bool"),
    ("guard_installed", "Guard Installed", "bool"),
    ("final_inspection_complete", "Final Inspection Complete", "bool"),
)


def default_inspection_results() -> dict[str, Any]:
    return {
        key: {"value": "" if kind != "bool" else False, "pass": False, "fail": False, "na": False, "notes": ""}
        for key, _, kind in INSPECTION_RESULT_ITEMS
    }
