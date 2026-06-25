"""Pricing Guide seed data for socket weld fittings."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

SOCKET_WELD_FITTINGS_CATEGORY = "Socket Weld Fittings"
# Default fitting unit when source data does not specify a unit.
SOCKET_WELD_FITTINGS_UNIT = "EA"
SOCKET_WELD_CONNECTION_TYPE = "Socket Weld"

_ITEM_CODE_PREFIX = "SWF"

_SUBCATEGORY_BY_GROUP: dict[str, str] = {
    "Stainless Steel": "Stainless Steel",
    "Carbon Steel": "Carbon Steel",
}

# (
#   description,
#   material_group,
#   grade,
#   fitting_type,
#   nominal_size,
#   run_size,
#   branch_size,
#   pressure_class,
#   price or None,
#   item_code_suffix,
#   requires_price_review,
# )
_SOCKET_WELD_SOURCE: tuple[tuple[Any, ...], ...] = (
    ('1" S.W. TEE #3000 (304 S.S.)', "Stainless Steel", "304", "Tee", '1"', None, None, "3000", "18.20", "SS304-TEE-1-3000", False),
    ('1-1/2" S.W. TEE (304 S.S.)', "Stainless Steel", "304", "Tee", '1-1/2"', None, None, None, "40.68", "SS304-TEE-1-12", False),
    ('1-1/2" S.W. TEE (316 S.S.)', "Stainless Steel", "316", "Tee", '1-1/2"', None, None, None, "51.91", "SS316-TEE-1-12", False),
    ('1" S.W. 90 ELBOW, #3000 (304 S.S.)', "Stainless Steel", "304", "90-Degree Elbow", '1"', None, None, "3000", "13.75", "SS304-EL90-1-3000", False),
    ('2" S.W. 90 ELBOW, #3000 (304 S.S.)', "Stainless Steel", "304", "90-Degree Elbow", '2"', None, None, "3000", "42.16", "SS304-EL90-2-3000", False),
    ('1/2" S.W. 90 ELBOW, #3000 (304 S.S.)', "Stainless Steel", "304", "90-Degree Elbow", '1/2"', None, None, "3000", "28.18", "SS304-EL90-12-3000", False),
    ('1" CAP, #3000, S.W. (304 S.S.)', "Stainless Steel", "304", "Cap", '1"', None, None, "3000", "6.05", "SS304-CAP-1-3000", False),
    ('2" CAP, #3000, S.W. (304 S.S.)', "Stainless Steel", "304", "Cap", '2"', None, None, "3000", "24.45", "SS304-CAP-2-3000", False),
    ('1" COLLAR/COUPLING S.W. (316 S.S.)', "Stainless Steel", "316", "Collar/Coupling", '1"', None, None, None, "6.41", "SS316-CPL-1", False),
    ('2" S.W. TEE (316 S.S.)', "Stainless Steel", "316", "Tee", '2"', None, None, None, None, "SS316-TEE-2", True),
    ('2"X1" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '2"', '1"', "3000", "14.32", "CS-SOCK-2X1-3000", False),
    ('4"X3/4" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '4"', '3/4"', "3000", "12.92", "CS-SOCK-4X34-3000", False),
    ('4"X1-1/2" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '4"', '1-1/2"', "3000", "23.92", "CS-SOCK-4X1-12-3000", False),
    ('4"X1" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '4"', '1"', "3000", "14.32", "CS-SOCK-4X1-3000", False),
    ('6"X3/4" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '6"', '3/4"', "3000", "12.92", "CS-SOCK-6X34-3000", False),
    ('4"X2" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '4"', '2"', "3000", "27.18", "CS-SOCK-4X2-3000", False),
    ('6"X1" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '6"', '1"', "3000", "14.32", "CS-SOCK-6X1-3000", False),
    ('6"X2" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '6"', '2"', "3000", "27.18", "CS-SOCK-6X2-3000", False),
    ('8"X3/4" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '8"', '3/4"', "3000", "12.92", "CS-SOCK-8X34-3000", False),
    ('10"X3/4" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '10"', '3/4"', "3000", "12.92", "CS-SOCK-10X34-3000", False),
    ('10"X1" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '10"', '1"', "3000", "14.32", "CS-SOCK-10X1-3000", False),
    ('10"X1-1/2" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '10"', '1-1/2"', "3000", "23.92", "CS-SOCK-10X1-12-3000", False),
    ('12"X1" SOCKOLET, #3000, S.W. (C.S.)', "Carbon Steel", None, "Sockolet", None, '12"', '1"', "3000", "14.32", "CS-SOCK-12X1-3000", False),
    ('3/4" TEE, #3000, S.W. (C.S.)', "Carbon Steel", None, "Tee", '3/4"', None, None, "3000", "8.45", "CS-TEE-34-3000", False),
    ('1" TEE, #3000, S.W. (C.S.)', "Carbon Steel", None, "Tee", '1"', None, None, "3000", "11.47", "CS-TEE-1-3000", False),
    ('3/4" ELBOW 90, #3000, S.W. (C.S.)', "Carbon Steel", None, "90-Degree Elbow", '3/4"', None, None, "3000", "5.81", "CS-EL90-34-3000", False),
    ('1" ELBOW 90, #3000, S.W. (C.S.)', "Carbon Steel", None, "90-Degree Elbow", '1"', None, None, "3000", "7.45", "CS-EL90-1-3000", False),
    ('1-1/2" ELBOW 90, #3000, S.W. (C.S.)', "Carbon Steel", None, "90-Degree Elbow", '1-1/2"', None, None, "3000", "16.64", "CS-EL90-1-12-3000", False),
    ('2" ELBOW 90, #3000, S.W. (C.S.)', "Carbon Steel", None, "90-Degree Elbow", '2"', None, None, "3000", "24.48", "CS-EL90-2-3000", False),
)

SOCKET_WELD_FITTINGS_SOURCE_ROW_COUNT = len(_SOCKET_WELD_SOURCE)

_PRICE_REVIEW_NOTE = (
    "Import review: price not supplied in source data — item inactive until catalog price is entered. "
    "Database default_cost is not an estimate price."
)


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _item_code(suffix: str) -> str:
    return f"{_ITEM_CODE_PREFIX}-{suffix}"


def _material_grade(*, material_group: str, grade: str | None) -> str:
    if grade == "304":
        return "304 Stainless Steel"
    if grade == "316":
        return "316 Stainless Steel"
    if material_group == "Carbon Steel":
        return "Carbon Steel"
    return ""


def _product_type(fitting_type: str) -> str:
    if fitting_type == "Collar/Coupling":
        return "Coupling"
    return fitting_type


def _base_notes(*, fitting_type: str) -> str:
    notes = (
        f"Socket weld fitting catalog item; unit {SOCKET_WELD_FITTINGS_UNIT} "
        f"(default fitting unit; unit not supplied in source data). "
        f"Connection: {SOCKET_WELD_CONNECTION_TYPE}."
    )
    if fitting_type == "Collar/Coupling":
        notes = (
            f"{notes} Source term: COLLAR/COUPLING. "
            f"Searchable as Collar or Coupling; subtype stored as Coupling."
        )
    return notes


def socket_weld_fittings_requires_price_review() -> list[dict[str, Any]]:
    """Source rows with no supplied price — inactive in catalog until priced."""
    return [
        {
            "item_code": item["item_code"],
            "description": item["description"],
            "material_group": item["subcategory"],
            "grade": item.get("material_grade"),
            "requires_price_review": True,
        }
        for item in socket_weld_fittings_catalog_items()
        if item.get("_requires_price_review")
    ]


def socket_weld_fittings_active_catalog_items() -> list[dict[str, Any]]:
    """Priced, active socket weld fitting rows available to the estimate builder."""
    return [
        item for item in socket_weld_fittings_catalog_items() if item.get("is_active") is not False
    ]


def socket_weld_fittings_catalog_items() -> list[dict[str, Any]]:
    """29 catalog rows; one inactive row has no supplied source price."""
    out: list[dict[str, Any]] = []
    for (
        description,
        material_group,
        grade,
        fitting_type,
        nominal_size,
        run_size,
        branch_size,
        pressure_class,
        price_raw,
        suffix,
        requires_price_review,
    ) in _SOCKET_WELD_SOURCE:
        notes = _base_notes(fitting_type=fitting_type)
        if requires_price_review:
            notes = f"{notes} {_PRICE_REVIEW_NOTE}"

        if fitting_type == "Sockolet":
            pipe_size = str(run_size or "")
            dash_size = str(branch_size or "")
        else:
            pipe_size = str(nominal_size or "")
            dash_size = ""

        row: dict[str, Any] = {
            "item_code": _item_code(suffix),
            "item_type": "Material",
            "item_class": "Non-Inventory",
            "description": description,
            "category": SOCKET_WELD_FITTINGS_CATEGORY,
            "subcategory": _SUBCATEGORY_BY_GROUP[material_group],
            "unit": SOCKET_WELD_FITTINGS_UNIT,
            "taxable": True,
            "is_active": not requires_price_review,
            "product_type": _product_type(fitting_type),
            "connection_type": SOCKET_WELD_CONNECTION_TYPE,
            "pipe_size": pipe_size,
            "dash_size": dash_size,
            "pressure_class": str(pressure_class or ""),
            "material_grade": _material_grade(material_group=material_group, grade=grade),
            "notes": notes.strip(),
            "_requires_price_review": requires_price_review,
            "_fitting_type": fitting_type,
            "_material_group": material_group,
        }
        if price_raw is not None and not requires_price_review:
            price = _decimal_price(price_raw)
            row["default_cost"] = _price_to_float(price)
            row["default_markup_percent"] = 0.0
            row["default_sell_price"] = _price_to_float(price)
        out.append(row)
    return out


def socket_weld_fittings_source_row_count() -> int:
    return SOCKET_WELD_FITTINGS_SOURCE_ROW_COUNT
