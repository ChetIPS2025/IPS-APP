"""Pricing Guide seed data for angle iron and related structural shapes."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

ANGLE_IRON_CATEGORY = "Angle Iron"
# Default material unit when source data does not specify a unit.
ANGLE_IRON_UNIT = "EA"

_SUBCATEGORY_BY_GROUP: dict[str, str] = {
    "Stainless Steel": "Stainless Steel",
    "Aluminum": "Aluminum",
    "Aluminium": "Aluminum",
    "Carbon Steel": "Carbon Steel",
}

_ITEM_CODE_PREFIX = "ANGL"

# (description, material_group, price|None, suffix, requires_price_review, body_shape, finish, source_description)
_ANGLE_IRON_SOURCE: tuple[tuple[str, str, str | None, str, bool, str, str, str], ...] = (
    ('L3x3x1/2" ANGLE (C.S.)', "Carbon Steel", "159.53", "CS-L3X3-12", False, "Angle", "", ""),
    ('L3x3x3/8" ANGLE (C.S.)', "Carbon Steel", "159.53", "CS-L3X3-38", False, "Angle", "", ""),
    ('L3-1/2"x3-1/2"x3/8" ANGLE (C.S.)', "Carbon Steel", "299.50", "CS-L3-12-X3-12-38", False, "Angle", "", ""),
    ('L4"x3"x1/4" ANGLE (C.S.)', "Carbon Steel", "101.19", "CS-L4X3-14", False, "Angle", "", ""),
    ('L2-1/2"x2-1/2"x1/4" ANGLE (C.S.)', "Carbon Steel", "69.52", "CS-L2-12-X2-12-14", False, "Angle", "", ""),
    ('L2"X2"X3/8" (GALVANIZED) ANGLE', "Carbon Steel", "84.98", "CS-L2X2-38-GALV", False, "Angle", "Galvanized", ""),
    ('L2"X2"X1/4" (C.S.) ANGLE', "Carbon Steel", "49.90", "CS-L2X2-14", False, "Angle", "", ""),
    ('L4"x2"x1/4" ANGLE (C.S.)', "Carbon Steel", None, "CS-L4X2-14", True, "Angle", "", ""),
    ('L3x3x3/16" ANGLE (C.S.)', "Carbon Steel", "62.86", "CS-L3X3-316", False, "Angle", "", ""),
    ('L4"x3-1/2"x5/16" ANGLE (C.S.)', "Carbon Steel", "316.66", "CS-L4X3-12-516", False, "Angle", "", ""),
    (
        '2"X2"X1/4" STRUCTURAL T-BEAM (ALUMINUM)',
        "Aluminum",
        "131.25",
        "AL-TBEAM-2X2-14",
        False,
        "T-Beam",
        "",
        '2"X2"X1/4" STRUCTUAL T-BEAM(ALUMINUM)',
    ),
    ('L2"X2"X1/4" (ALUM.) ANGLE', "Aluminum", "100.73", "AL-L2X2-14", False, "Angle", "", ""),
    ('L2"X2"X1/8" (ALUM.) ANGLE', "Aluminum", "52.64", "AL-L2X2-18", False, "Angle", "", ""),
    ('L1"X1"X1/8" (ALUM.) ANGLE', "Aluminum", "28.35", "AL-L1X1-18", False, "Angle", "", ""),
    ('L2"X2"X3/16" (ALUM.) ANGLE', "Aluminum", "88.09", "AL-L2X2-316", False, "Angle", "", ""),
    ('L1"X1"X1/8" ANGLE (316 S.S.)', "Stainless Steel", "86.34", "SS-L1X1-18-316", False, "Angle", "", ""),
    ('L3"X3"X3/8" (316 S.S.) ANGLE IRON', "Stainless Steel", "747.90", "SS-L3X3-38-316", False, "Angle", "", ""),
)

ANGLE_IRON_SOURCE_ROW_COUNT = len(_ANGLE_IRON_SOURCE)

_PRICE_REVIEW_NOTE = (
    "Import review: price not supplied in source data — item inactive until catalog price is entered. "
    "Database default_cost is not an estimate price."
)


def _material_grade(description: str, material_group: str) -> str:
    if "316 S.S." in description or "(316" in description:
        return "316 Stainless Steel"
    if "ALUM." in description.upper() or "ALUMINUM" in description.upper():
        return "Aluminum"
    if "(C.S.)" in description or "C.S." in description or "GALVANIZED" in description.upper():
        return "Carbon Steel"
    return _SUBCATEGORY_BY_GROUP.get(material_group, material_group)


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _item_code(suffix: str) -> str:
    return f"{_ITEM_CODE_PREFIX}-{suffix}"


def _base_notes() -> str:
    return (
        f"Angle iron catalog item; unit {ANGLE_IRON_UNIT} "
        f"(default material unit; length not supplied in source data)."
    )


def angle_iron_requires_price_review() -> list[dict[str, Any]]:
    """Source rows with no supplied price — inactive in catalog until priced."""
    return [
        {
            "item_code": item["item_code"],
            "description": item["description"],
            "material_group": item["subcategory"],
            "requires_price_review": True,
        }
        for item in angle_iron_catalog_items()
        if item.get("_requires_price_review")
    ]


def angle_iron_active_catalog_items() -> list[dict[str, Any]]:
    """Priced, active angle iron rows available to the estimate builder."""
    return [item for item in angle_iron_catalog_items() if item.get("is_active") is not False]


def angle_iron_catalog_items() -> list[dict[str, Any]]:
    """17 catalog rows; one inactive row has no supplied source price."""
    out: list[dict[str, Any]] = []
    for (
        description,
        material_group,
        price_raw,
        suffix,
        requires_price_review,
        body_shape,
        finish,
        source_description,
    ) in _ANGLE_IRON_SOURCE:
        subcategory = _SUBCATEGORY_BY_GROUP[material_group]
        grade = _material_grade(description, material_group)
        notes_parts = [_base_notes()]
        if finish:
            notes_parts.append(f"Finish: {finish}.")
        if source_description:
            notes_parts.append(f"Source description: {source_description}.")
        if requires_price_review:
            notes_parts.append(_PRICE_REVIEW_NOTE)

        product_type = "T-Beam" if body_shape == "T-Beam" else "Angle Iron"
        row: dict[str, Any] = {
            "item_code": _item_code(suffix),
            "item_type": "Material",
            "item_class": "Non-Inventory",
            "description": description,
            "category": ANGLE_IRON_CATEGORY,
            "subcategory": subcategory,
            "unit": ANGLE_IRON_UNIT,
            "taxable": True,
            "is_active": not requires_price_review,
            "product_type": product_type,
            "body_shape": body_shape,
            "material_grade": grade,
            "notes": " ".join(notes_parts).strip(),
            "_requires_price_review": requires_price_review,
        }
        if price_raw is not None and not requires_price_review:
            price = _decimal_price(price_raw)
            row["default_cost"] = _price_to_float(price)
            row["default_markup_percent"] = 0.0
            row["default_sell_price"] = _price_to_float(price)
        out.append(row)
    return out


def angle_iron_source_row_count() -> int:
    return ANGLE_IRON_SOURCE_ROW_COUNT
