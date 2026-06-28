"""Handwritten vendor material quote — source line items (May 2026 import)."""

from __future__ import annotations

from typing import Any, TypedDict


class HandwrittenQuoteLineSource(TypedDict, total=False):
    qty: str
    qty_unit: str
    description: str
    spec: str
    unit_price: str
    price_basis: str
    line_total: str
    pricing_qty: str
    pricing_unit: str
    note: str
    requires_review: bool
    review_note: str


HANDWRITTEN_MATERIAL_QUOTE_ID = "handwritten-material-quote-2026-05"

HANDWRITTEN_MATERIAL_QUOTE_NOTES: dict[str, str] = {
    "lead_time": "Lead time appears to be 2–3 days (handwritten).",
    "stock_length": "Handwritten note references 20 ft stock/stick length.",
    "subtotal_disclaimer": (
        "Preliminary material subtotal — some handwritten prices or price bases require review."
    ),
}

HANDWRITTEN_MATERIAL_QUOTE_LINES: tuple[HandwrittenQuoteLineSource, ...] = (
    {
        "qty": "20",
        "qty_unit": "ft",
        "description": '1-1/4" SCH. 80 SMLS PIPE',
        "spec": "316 SS",
        "unit_price": "28.93",
        "price_basis": "per ft",
        "line_total": "578.60",
    },
    {
        "qty": "32",
        "qty_unit": "ea",
        "description": '1-1/4" SCH. 80 180° LR PIPE RETURNS',
        "spec": "A-234",
        "unit_price": "46.78",
        "price_basis": "each",
        "line_total": "1496.96",
    },
    {
        "qty": "40",
        "qty_unit": "ft",
        "description": '1/2" SQUARE STOCK',
        "spec": "A-36",
        "unit_price": "14.24",
        "price_basis": "per 20 ft stick",
        "pricing_qty": "2",
        "pricing_unit": "stick",
        "line_total": "28.48",
        "note": "Handwritten note appears to say price is per 20 ft stick.",
    },
    {
        "qty": "40",
        "qty_unit": "ft",
        "description": '1" SCH. 40 PIPE',
        "spec": "A-106",
        "unit_price": "3.94",
        "price_basis": "per ft",
        "line_total": "157.60",
        "requires_review": True,
        "review_note": "Handwritten unit price appears to be $3.94/ft, but verify before finalizing.",
    },
    {
        "qty": "20",
        "qty_unit": "ft",
        "description": '3/8" x 3" Flat Bar',
        "spec": "A-36",
        "unit_price": "67.20",
        "price_basis": "unclear, likely per 20 ft stick",
        "line_total": "67.20",
        "requires_review": True,
        "review_note": "Price basis is not clearly written. Source shows $67.20, likely for one 20 ft stick.",
    },
    {
        "qty": "2",
        "qty_unit": "ea",
        "description": '1-1/4" 300# RF SO FLANGE',
        "spec": "A-105",
        "unit_price": "18.88",
        "price_basis": "each",
        "line_total": "37.76",
    },
    {
        "qty": "320",
        "qty_unit": "ft",
        "description": '1-1/4" SCH. 80 SMLS PIPE',
        "spec": "A-106",
        "unit_price": "9.84",
        "price_basis": "per ft",
        "line_total": "3148.80",
        "requires_review": True,
        "review_note": "Handwritten unit price appears to be $9.84/ft; verify before finalizing.",
    },
    {
        "qty": "2",
        "qty_unit": "ea",
        "description": '1-1/4" SCH. 80 90° LR EL',
        "spec": "A-234",
        "unit_price": "12.21",
        "price_basis": "each",
        "line_total": "24.42",
    },
    {
        "qty": "20",
        "qty_unit": "ft",
        "description": '2" SCH. 40 PIPE',
        "spec": "A-106",
        "unit_price": "6.32",
        "price_basis": "per ft",
        "line_total": "126.40",
    },
    {
        "qty": "20",
        "qty_unit": "ft",
        "description": '1-1/4" SCH. 80 SMLS PIPE',
        "spec": "316 SS",
        "unit_price": "28.93",
        "price_basis": "per ft",
        "line_total": "578.60",
    },
)


def handwritten_material_quote_source_rows() -> list[dict[str, Any]]:
    """Return a mutable copy of source rows for import pipelines."""
    return [dict(row) for row in HANDWRITTEN_MATERIAL_QUOTE_LINES]
