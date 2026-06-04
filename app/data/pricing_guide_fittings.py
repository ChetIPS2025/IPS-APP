"""Pricing Guide seed data for hydraulic fittings (threaded unions, etc.)."""

from __future__ import annotations

from typing import Any

# Stable item_code prefix for threaded NPT female 3000 hex unions.
_UNION_ITEM_CODE_PREFIX = "UNION-TU-NPTF"

# Pipe size, dash (string), max pressure @ temp, 304 part/steam/each, 316 part/steam/each
_THREADED_UNION_NPT_FEMALE_3000_SIZES: tuple[tuple[str, ...], ...] = (
    ("1/8", "02", "2,900 psi @ 72°F", "45525K591", "1,900 psi @ 350°F", "73.82", "4443K691", "2,000 psi @ 350°F", "94.73"),
    ("1/4", "04", "2,900 psi @ 72°F", "45525K592", "1,900 psi @ 350°F", "79.07", "4443K692", "2,000 psi @ 350°F", "113.26"),
    ("3/8", "06", "2,900 psi @ 72°F", "45525K593", "1,900 psi @ 350°F", "84.55", "4443K693", "2,000 psi @ 350°F", "131.17"),
    ("1/2", "08", "2,900 psi @ 72°F", "45525K594", "1,900 psi @ 350°F", "84.55", "4443K694", "2,000 psi @ 350°F", "131.35"),
    ("3/4", "12", "2,900 psi @ 72°F", "45525K595", "1,900 psi @ 350°F", "103.65", "4443K695", "2,000 psi @ 350°F", "171.30"),
    ("1", "16", "2,900 psi @ 72°F", "45525K596", "1,900 psi @ 350°F", "159.59", "4443K696", "2,000 psi @ 350°F", "248.63"),
    ("1 1/4", "20", "2,900 psi @ 72°F", "45525K597", "1,900 psi @ 350°F", "289.36", "4443K697", "2,000 psi @ 350°F", "402.29"),
    ("1 1/2", "24", "2,900 psi @ 72°F", "45525K598", "1,900 psi @ 350°F", "326.51", "4443K698", "2,000 psi @ 350°F", "479.35"),
    ("2", "32", "2,900 psi @ 72°F", "45525K599", "1,900 psi @ 350°F", "436.54", "4443K699", "2,000 psi @ 350°F", "609.46"),
)

FITTING_CATALOG_FIELD_NAMES: tuple[str, ...] = (
    "product_type",
    "connection_type",
    "pipe_size",
    "dash_size",
    "pressure_class",
    "body_shape",
    "material_grade",
    "max_pressure_temp",
    "max_steam_pressure_temp",
)


def _material_row(
    *,
    pipe_size: str,
    dash_size: str,
    max_pressure_temp: str,
    material_grade: str,
    part_number: str,
    max_steam_pressure_temp: str,
    unit_cost: str,
) -> dict[str, Any]:
    mat_slug = "304SS" if material_grade.startswith("304") else "316SS"
    item_code = f"{_UNION_ITEM_CODE_PREFIX}-{dash_size}-{mat_slug}"
    return {
        "item_code": item_code,
        "item_type": "Material",
        "item_class": "Non-Inventory",
        "description": (
            f"Threaded Union, NPT Female, {pipe_size}, Dash {dash_size} — {material_grade}"
        ),
        "category": "Unions",
        "subcategory": "Threaded Unions",
        "unit": "EA",
        "default_cost": float(unit_cost),
        "default_markup_percent": 0.0,
        "default_sell_price": float(unit_cost),
        "model_number": part_number,
        "item_number": part_number,
        "sku": part_number,
        "taxable": True,
        "is_active": True,
        "product_type": "Union",
        "connection_type": "NPT Female",
        "pipe_size": pipe_size,
        "dash_size": dash_size,
        "pressure_class": "3000",
        "body_shape": "Hex",
        "material_grade": material_grade,
        "max_pressure_temp": max_pressure_temp,
        "max_steam_pressure_temp": max_steam_pressure_temp,
        "notes": (
            f"Threaded union; {material_grade}; part {part_number}; "
            f"max {max_pressure_temp}; steam {max_steam_pressure_temp}."
        ),
    }


def threaded_npt_female_3000_union_items() -> list[dict[str, Any]]:
    """18 pricing rows: 9 pipe sizes × (304 SS, 316 SS)."""
    out: list[dict[str, Any]] = []
    for row in _THREADED_UNION_NPT_FEMALE_3000_SIZES:
        (
            pipe_size,
            dash_size,
            max_pressure_temp,
            part_304,
            steam_304,
            cost_304,
            part_316,
            steam_316,
            cost_316,
        ) = row
        out.append(
            _material_row(
                pipe_size=pipe_size,
                dash_size=dash_size,
                max_pressure_temp=max_pressure_temp,
                material_grade="304 Stainless Steel",
                part_number=part_304,
                max_steam_pressure_temp=steam_304,
                unit_cost=cost_304,
            )
        )
        out.append(
            _material_row(
                pipe_size=pipe_size,
                dash_size=dash_size,
                max_pressure_temp=max_pressure_temp,
                material_grade="316 Stainless Steel",
                part_number=part_316,
                max_steam_pressure_temp=steam_316,
                unit_cost=cost_316,
            )
        )
    return out
