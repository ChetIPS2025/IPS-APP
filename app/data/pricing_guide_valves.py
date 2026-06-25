"""Pricing Guide seed data for valves and Y-strainers."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

VALVES_CATEGORY = "Valves"
# Default valve/fitting unit when source data does not specify a unit.
VALVES_UNIT = "EA"

_ITEM_CODE_PREFIX = "VAL"

_SUBCATEGORY_BY_GROUP: dict[str | None, str] = {
    "Stainless Steel": "Stainless Steel",
    "Carbon Steel": "Carbon Steel",
    None: "Unspecified",
}

# (
#   source_row,
#   description,
#   material_group,
#   grade,
#   product_type,
#   nominal_size,
#   connection_type,
#   pressure_designation,
#   face,
#   end_designation,
#   port_type,
#   operation_type,
#   wedge_type,
#   bonnet_type,
#   stem_design,
#   cover_type,
#   api_standard,
#   anti_blowout,
#   antistatic,
#   manufacturer,
#   price,
#   item_code_suffix,
# )
_VALVE_SOURCE: tuple[tuple[Any, ...], ...] = (
    (1, '1/2" THREADED BALL VALVE #2000 (316 S.S.)', "Stainless Steel", "316", "Ball Valve", '1/2"', "Threaded", "#2000", None, None, None, None, None, None, None, None, None, False, False, None, "22.35", "SS316-BV-12-THR-2000"),
    (2, '2" #150 FLANGED CHECK VALVE (SWING) S.S.', "Stainless Steel", None, "Check Valve", '2"', "Flanged", "#150", None, None, None, "Swing", None, None, None, None, None, False, False, None, "333.38", "SS-CV-2-FLG-150-SWING"),
    (3, '1-1/2" CHECK VALVE #800 FULL PORT S.W. (C.S.)', "Carbon Steel", None, "Check Valve", '1-1/2"', "Socket Weld", "#800", None, None, "Full Port", None, None, None, None, None, None, False, False, None, "105.85", "CS-CV-1-12-SW-800-FP"),
    (4, '1" #150 FLANGED BALL VALVE (S.S.)', "Stainless Steel", None, "Ball Valve", '1"', "Flanged", "#150", None, None, None, None, None, None, None, None, None, False, False, None, "119.35", "SS-BV-1-FLG-150"),
    (5, '1-1/2" GATE VALVE, FULL PORT, 800lb, S.W. (C.S.)', "Carbon Steel", None, "Gate Valve", '1-1/2"', "Socket Weld", "800lb", None, None, "Full Port", None, None, None, None, None, None, False, False, None, "123.75", "CS-GV-1-12-SW-800-FP"),
    (6, '3" Y-STRAINERS #150 RF, FE, (S.S.)', "Stainless Steel", None, "Y-Strainer", '3"', None, "#150", "Raised Face", "FE", None, None, None, None, None, None, None, False, False, None, "924.75", "SS-YS-3-150-RF-FE"),
    (7, '3" GLOBE VALVE #150 RF, FE, (S.S.)', "Stainless Steel", None, "Globe Valve", '3"', None, "#150", "Raised Face", "FE", None, None, None, None, None, None, None, False, False, None, "875.00", "SS-GV-3-150-RF-FE"),
    (8, '1" FLANGED BALL VALVE FULL BORE, RF, #150, (304 S.S.)', "Stainless Steel", "304", "Ball Valve", '1"', "Flanged", "#150", "Raised Face", None, "Full Bore", None, None, None, None, None, None, False, False, None, "257.00", "SS304-BV-1-FLG-150-FB"),
    (9, '2" FLANGED BALL VALVE FULL BORE, RF, #150, (304 S.S.)', "Stainless Steel", "304", "Ball Valve", '2"', "Flanged", "#150", "Raised Face", None, "Full Bore", None, None, None, None, None, None, False, False, None, "455.50", "SS304-BV-2-FLG-150-FB"),
    (10, '2" FLANGED BALL VALVE FULL BORE, RF, #300, (304 S.S.)', "Stainless Steel", "304", "Ball Valve", '2"', "Flanged", "#300", "Raised Face", None, "Full Bore", None, None, None, None, None, None, False, False, None, "625.50", "SS304-BV-2-FLG-300-FB"),
    (11, '2" BALL VALVE S.W. (S.S.)', "Stainless Steel", None, "Ball Valve", '2"', "Socket Weld", None, None, None, None, None, None, None, None, None, None, False, False, None, "125.00", "SS-BV-2-SW"),
    (12, '1" GATE VALVE, FULL PORT, 800lb, S.W. (C.S.)', "Carbon Steel", None, "Gate Valve", '1"', "Socket Weld", "800lb", None, None, "Full Port", None, None, None, None, None, None, False, False, None, "159.00", "CS-GV-1-SW-800-FP"),
    (13, '1-1/2" GATE VALVE, VELAN, 1500lb, S.W. (C.S.)', "Carbon Steel", None, "Gate Valve", '1-1/2"', "Socket Weld", "1500lb", None, None, None, None, None, None, None, None, None, False, False, "Velan", "594.00", "CS-GV-1-12-SW-1500-VELAN"),
    (14, '2" GLOBE VALVE, BB, OS&Y, #150, RF', None, None, "Globe Valve", '2"', "Flanged", "#150", "Raised Face", None, None, None, None, "BB", "OS&Y", None, None, False, False, None, "745.20", "UNSP-GLO-2-FLG-150"),
    (15, '4" CHECK VALVE, BC, SWING TYPE, #150, RF', None, None, "Check Valve", '4"', "Flanged", "#150", "Raised Face", None, None, "Swing Type", None, None, None, "BC", None, False, False, None, "446.40", "UNSP-CV-4-FLG-150-SWING"),
    (16, '6" CHECK VALVE, BC, SWING TYPE, #150, RF', None, None, "Check Valve", '6"', "Flanged", "#150", "Raised Face", None, None, "Swing Type", None, None, None, "BC", None, False, False, None, "657.00", "UNSP-CV-6-FLG-150-SWING"),
    (17, '6" GATE VALVE, SOLID WEDGE, BB, OS&Y, #150, RF, API600', None, None, "Gate Valve", '6"', "Flanged", "#150", "Raised Face", None, None, None, "Solid Wedge", "BB", "OS&Y", None, "API 600", False, False, None, "738.00", "UNSP-GV-6-FLG-150-API600"),
    (18, '8" GATE VALVE, SOLID WEDGE, BB, OS&Y, #150, RF, API600', None, None, "Gate Valve", '8"', "Flanged", "#150", "Raised Face", None, None, None, "Solid Wedge", "BB", "OS&Y", None, "API 600", False, False, None, "1081.80", "UNSP-GV-8-FLG-150-API600"),
    (19, '10" GATE VALVE, SOLID WEDGE, BB, OS&Y, #150, RF, API600', None, None, "Gate Valve", '10"', "Flanged", "#150", "Raised Face", None, None, None, "Solid Wedge", "BB", "OS&Y", None, "API 600", False, False, None, "1639.80", "UNSP-GV-10-FLG-150-API600"),
    (20, '12" GATE VALVE, SOLID WEDGE, BB, OS&Y, #150, RF, API600', None, None, "Gate Valve", '12"', "Flanged", "#150", "Raised Face", None, None, None, "Solid Wedge", "BB", "OS&Y", None, "API 600", False, False, None, "2395.80", "UNSP-GV-12-FLG-150-API600"),
    (21, '1" BALL VALVE, FULL BORE, #150, RF, ANTIBLOWOUT, ANTISTATIC, API608', None, None, "Ball Valve", '1"', "Flanged", "#150", "Raised Face", None, "Full Bore", None, None, None, None, None, "API 608", True, True, None, "309.15", "UNSP-BV-1-FLG-150-API608"),
    (22, '1" GATE VALVE, SOLID WEDGE, BB, OS&Y, #150, RF, API602', None, None, "Gate Valve", '1"', "Flanged", "#150", "Raised Face", None, None, None, "Solid Wedge", "BB", "OS&Y", None, "API 602", False, False, None, "267.30", "UNSP-GV-1-FLG-150-API602"),
    (23, '3/4" GATE VALVE, SOLID WEDGE, BB, OS&Y, #150, RF, API602', None, None, "Gate Valve", '3/4"', "Flanged", "#150", "Raised Face", None, None, None, "Solid Wedge", "BB", "OS&Y", None, "API 602", False, False, None, "189.00", "UNSP-GV-34-FLG-150-API602"),
)

VALVES_SOURCE_ROW_COUNT = len(_VALVE_SOURCE)


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _item_code(suffix: str) -> str:
    return f"{_ITEM_CODE_PREFIX}-{suffix}"


def _material_grade(*, material_group: str | None, grade: str | None) -> str:
    if grade == "304":
        return "304 Stainless Steel"
    if grade == "316":
        return "316 Stainless Steel"
    if material_group == "Carbon Steel":
        return "Carbon Steel"
    return ""


def _body_shape(
    *,
    face: str | None,
    port_type: str | None,
    operation_type: str | None,
    wedge_type: str | None,
) -> str:
    if face:
        return str(face)
    if port_type:
        return str(port_type)
    if operation_type:
        return str(operation_type)
    if wedge_type:
        return str(wedge_type)
    return ""


def _dash_size(*, api_standard: str | None, end_designation: str | None) -> str:
    if api_standard:
        return str(api_standard)
    if end_designation:
        return str(end_designation)
    return ""


def _normalized_feature_notes(
    *,
    port_type: str | None,
    operation_type: str | None,
    wedge_type: str | None,
    bonnet_type: str | None,
    stem_design: str | None,
    cover_type: str | None,
    end_designation: str | None,
    anti_blowout: bool,
    antistatic: bool,
    manufacturer: str | None,
) -> str:
    parts: list[str] = []
    if port_type:
        parts.append(f"Port: {port_type}")
    if operation_type:
        parts.append(f"Operation: {operation_type}")
    if wedge_type:
        parts.append(f"Wedge: {wedge_type}")
    if bonnet_type:
        parts.append(f"Bonnet: Bolted Bonnet (BB)")
    if stem_design:
        parts.append(f"Stem: Outside Screw and Yoke (OS&Y)")
    if cover_type:
        parts.append(f"Cover: Bolted Cover (BC)")
    if end_designation:
        parts.append(f"End designation: {end_designation}")
    if anti_blowout:
        parts.append("Feature: Anti-Blowout")
    if antistatic:
        parts.append("Feature: Antistatic")
    if manufacturer:
        parts.append(f"Manufacturer: {manufacturer}")
    return "; ".join(parts)


def _base_notes(*, material_group: str | None, grade: str | None) -> str:
    notes = (
        f"Valve catalog item; unit {VALVES_UNIT} "
        f"(default valve/fitting unit; unit not supplied in source data)."
    )
    if material_group is None:
        notes = f"{notes} Material not specified in source data."
    elif material_group == "Stainless Steel" and grade is None:
        notes = f"{notes} Stainless steel grade not specified in source data."
    return notes


def valves_active_catalog_items() -> list[dict[str, Any]]:
    """Active valve rows available to the estimate builder."""
    return [item for item in valves_catalog_items() if item.get("is_active") is not False]


def valves_catalog_items() -> list[dict[str, Any]]:
    """23 priced valve and Y-strainer catalog rows."""
    out: list[dict[str, Any]] = []
    for (
        _source_row,
        description,
        material_group,
        grade,
        product_type,
        nominal_size,
        connection_type,
        pressure_designation,
        face,
        end_designation,
        port_type,
        operation_type,
        wedge_type,
        bonnet_type,
        stem_design,
        cover_type,
        api_standard,
        anti_blowout,
        antistatic,
        manufacturer,
        price_raw,
        suffix,
    ) in _VALVE_SOURCE:
        price = _decimal_price(price_raw)
        notes = _base_notes(material_group=material_group, grade=grade)
        feature_notes = _normalized_feature_notes(
            port_type=port_type,
            operation_type=operation_type,
            wedge_type=wedge_type,
            bonnet_type=bonnet_type,
            stem_design=stem_design,
            cover_type=cover_type,
            end_designation=end_designation,
            anti_blowout=bool(anti_blowout),
            antistatic=bool(antistatic),
            manufacturer=manufacturer,
        )
        if feature_notes:
            notes = f"{notes} {feature_notes}"

        row: dict[str, Any] = {
            "item_code": _item_code(suffix),
            "item_type": "Material",
            "item_class": "Non-Inventory",
            "description": description,
            "category": VALVES_CATEGORY,
            "subcategory": _SUBCATEGORY_BY_GROUP[material_group],
            "unit": VALVES_UNIT,
            "default_cost": _price_to_float(price),
            "default_markup_percent": 0.0,
            "default_sell_price": _price_to_float(price),
            "taxable": True,
            "is_active": True,
            "product_type": product_type,
            "connection_type": str(connection_type or ""),
            "pipe_size": nominal_size,
            "pressure_class": str(pressure_designation or ""),
            "body_shape": _body_shape(
                face=face,
                port_type=port_type,
                operation_type=operation_type,
                wedge_type=wedge_type,
            ),
            "dash_size": _dash_size(api_standard=api_standard, end_designation=end_designation),
            "material_grade": _material_grade(material_group=material_group, grade=grade),
            "notes": notes.strip(),
        }
        if manufacturer:
            row["vendor"] = manufacturer
        out.append(row)
    return out


def valves_source_row_count() -> int:
    return VALVES_SOURCE_ROW_COUNT
