"""Pricing Guide seed data for I-beam and related structural steel shapes."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

I_BEAM_CATEGORY = "I-Beam"
# Default material unit when source data does not specify a unit.
I_BEAM_UNIT = "EA"

_ITEM_CODE_PREFIX = "IBEAM"

# (description, price, suffix, body_shape, finish, fabrication, requires_price_review, alias_note)
_I_BEAM_SOURCE: tuple[tuple[str, str, str, str, str, str, bool, str], ...] = (
    ("W8x28 (C.S.) I-BEAM", "609.40", "CS-W8X28-IBEAM", "I-Beam", "", "", False, ""),
    ("W6x15 (C.S.) BEAM", "646.80", "CS-W6X15-BEAM", "Beam", "", "", False, ""),
    ("W8x10 (C.S.) BEAM", "217.28", "CS-W8X10-BEAM", "Beam", "", "", False, ""),
    (
        "W8x21 (C.S.) BEAM",
        "850.80",
        "CS-W8X21-BEAM",
        "Beam",
        "",
        "",
        False,
        "Alternate source wording: W8x21 (C.S.) I-BEAM (same shape/price; separate catalog record IBEAM-CS-W8X21-IBEAM).",
    ),
    ("W12x26 (C.S.) BEAM", "960.51", "CS-W12X26-BEAM", "Beam", "", "", False, ""),
    (
        "W6x20 (C.S.) BEAM",
        "704.60",
        "CS-W6X20-BEAM",
        "Beam",
        "",
        "",
        False,
        "Alternate source wording: W6x20 (C.S.) I-BEAM (same shape/price; separate catalog record IBEAM-CS-W6X20-IBEAM).",
    ),
    ("W6x16 GALVANIZED BEAM", "1164.80", "CS-W6X16-GALV-BEAM", "Galvanized Beam", "Galvanized", "", False, ""),
    (
        "W6x20 (C.S.) I-BEAM",
        "704.60",
        "CS-W6X20-IBEAM",
        "I-Beam",
        "",
        "",
        False,
        "Alternate source wording: W6x20 (C.S.) BEAM (same shape/price; separate catalog record IBEAM-CS-W6X20-BEAM).",
    ),
    ("W6x20 GALVANIZED BEAM", "703.40", "CS-W6X20-GALV-BEAM", "Galvanized Beam", "Galvanized", "", False, ""),
    (
        "W8x21 (C.S.) I-BEAM",
        "850.80",
        "CS-W8X21-IBEAM",
        "I-Beam",
        "",
        "",
        False,
        "Alternate source wording: W8x21 (C.S.) BEAM (same shape/price; separate catalog record IBEAM-CS-W8X21-BEAM).",
    ),
    ("W8x21 GALVANIZED BEAM", "737.20", "CS-W8X21-GALV-BEAM", "Galvanized Beam", "Galvanized", "", False, ""),
    ("W10x39 (C.S.) BEAM", "39.00", "CS-W10X39-BEAM", "Beam", "", "", True, ""),
    ("W10x45 GALVANIZED BEAM", "1334.00", "CS-W10X45-GALV-BEAM", "Galvanized Beam", "Galvanized", "", False, ""),
    ("W8x35 GALVANIZED BEAM", "2490.56", "CS-W8X35-GALV-BEAM", "Galvanized Beam", "Galvanized", "", False, ""),
    ("W12X45 GALVANIZED BEAM", "1668.45", "CS-W12X45-GALV-BEAM", "Galvanized Beam", "Galvanized", "", False, ""),
    (
        "W14X9 GALVANIZED T-BAR(STITCH CUT)",
        "1200.00",
        "CS-W14X9-GALV-TBAR",
        "Galvanized T-Bar (Stitch Cut)",
        "Galvanized",
        "Stitch Cut",
        False,
        "",
    ),
    ("W8x35 C.S. I-Beam", "39.38", "CS-W8X35-IBEAM", "I-Beam", "", "", True, ""),
)

I_BEAM_SOURCE_ROW_COUNT = len(_I_BEAM_SOURCE)

_PRICE_VERIFY_NOTE = (
    "Import review: verify catalog price — unusually low compared with neighboring records; "
    "active price preserved as supplied."
)


def _decimal_price(raw: str) -> Decimal:
    return Decimal(str(raw).strip())


def _price_to_float(price: Decimal) -> float:
    return float(price.quantize(Decimal("0.01")))


def _item_code(suffix: str) -> str:
    return f"{_ITEM_CODE_PREFIX}-{suffix}"


def _product_type(body_shape: str) -> str:
    if body_shape.startswith("Galvanized T-Bar"):
        return "T-Bar"
    if body_shape == "I-Beam":
        return "I-Beam"
    if body_shape == "Galvanized Beam":
        return "Beam"
    return "Beam"


def _base_notes() -> str:
    return (
        f"I-beam catalog item; unit {I_BEAM_UNIT} "
        f"(default material unit; length/weight basis not supplied in source data)."
    )


def i_beam_alias_pairs() -> list[dict[str, Any]]:
    """Source rows with BEAM/I-BEAM alternate wording preserved as separate catalog records."""
    items = {r["item_code"]: r for r in i_beam_catalog_items()}
    pairs = [
        ("IBEAM-CS-W6X20-BEAM", "IBEAM-CS-W6X20-IBEAM"),
        ("IBEAM-CS-W8X21-BEAM", "IBEAM-CS-W8X21-IBEAM"),
    ]
    out: list[dict[str, Any]] = []
    for beam_code, ibeam_code in pairs:
        beam = items[beam_code]
        ibeam = items[ibeam_code]
        out.append(
            {
                "shape_key": beam_code.replace("IBEAM-CS-", "").replace("-BEAM", ""),
                "beam_item_code": beam_code,
                "ibeam_item_code": ibeam_code,
                "beam_description": beam["description"],
                "ibeam_description": ibeam["description"],
                "price": beam["default_cost"],
            }
        )
    return out


def i_beam_price_review_items() -> list[dict[str, Any]]:
    """Active items flagged for manual price verification."""
    return [
        {
            "item_code": item["item_code"],
            "description": item["description"],
            "active_price": item["default_cost"],
        }
        for item in i_beam_catalog_items()
        if item.get("_requires_price_review")
    ]


def i_beam_catalog_items() -> list[dict[str, Any]]:
    """17 catalog rows — one per source record (BEAM/I-BEAM pairs kept as separate items)."""
    out: list[dict[str, Any]] = []
    for (
        description,
        price_raw,
        suffix,
        body_shape,
        finish,
        fabrication,
        requires_price_review,
        alias_note,
    ) in _I_BEAM_SOURCE:
        price = _decimal_price(price_raw)
        notes_parts = [_base_notes()]
        if finish:
            notes_parts.append(f"Finish: {finish}.")
        if fabrication:
            notes_parts.append(f"Fabrication: {fabrication}.")
        if alias_note:
            notes_parts.append(alias_note)
        if requires_price_review:
            notes_parts.append(_PRICE_VERIFY_NOTE)

        out.append(
            {
                "item_code": _item_code(suffix),
                "item_type": "Material",
                "item_class": "Non-Inventory",
                "description": description,
                "category": I_BEAM_CATEGORY,
                "subcategory": "Carbon Steel",
                "unit": I_BEAM_UNIT,
                "default_cost": _price_to_float(price),
                "default_markup_percent": 0.0,
                "default_sell_price": _price_to_float(price),
                "taxable": True,
                "is_active": True,
                "product_type": _product_type(body_shape),
                "body_shape": body_shape,
                "material_grade": "Carbon Steel",
                "notes": " ".join(notes_parts).strip(),
                "_requires_price_review": requires_price_review,
            }
        )
    return out


def i_beam_source_row_count() -> int:
    return I_BEAM_SOURCE_ROW_COUNT
