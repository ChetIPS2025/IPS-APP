"""Import handwritten / structured vendor material quotes into estimate line items."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.data.handwritten_material_quote_source import (
    HANDWRITTEN_MATERIAL_QUOTE_ID,
    HANDWRITTEN_MATERIAL_QUOTE_LINES,
    HANDWRITTEN_MATERIAL_QUOTE_NOTES,
    handwritten_material_quote_source_rows,
)
from app.estimate.calculations import _D0, _dec, _q2, money_db, money_str
from app.services.pricing_guide_service import cached_pricing_guide_rows
_PER_FT = frozenset({"per ft", "per foot", "/ft", "ft"})
_PER_EACH = frozenset({"each", "per ea", "ea", "/ea"})
_PER_STICK = frozenset({"per 20 ft stick", "per stick", "stick"})
_UNCLEAR_BASIS = frozenset({"unclear, likely per 20 ft stick"})

_UNIT_MAP = {
    "ft": "FT",
    "foot": "FT",
    "feet": "FT",
    "ea": "EA",
    "each": "EA",
    "stick": "EA",
    "sticks": "EA",
}


@dataclass
class MaterialQuoteImportLine:
    line_number: int
    description: str
    spec: str
    ordered_qty: Decimal
    ordered_unit: str
    quantity: Decimal
    unit: str
    unit_cost: Decimal
    total_cost: Decimal
    price_basis: str
    category: str
    notes: str
    requires_review: bool
    review_note: str
    pricing_item_id: str | None = None
    catalog_match_description: str | None = None
    catalog_match_score: float = 0.0
    used_catalog_unit_cost: bool = False


@dataclass
class MaterialQuoteImportBundle:
    template_id: str
    title: str
    estimate_notes: str
    review_flags: list[str] = field(default_factory=list)
    lines: list[MaterialQuoteImportLine] = field(default_factory=list)
    preliminary_subtotal: Decimal = _D0
    subtotal_is_preliminary: bool = True
    source_row_count: int = 0


def _normalize_text(value: str) -> str:
    text = str(value or "").upper()
    text = text.replace("SCH.", "SCH").replace("SMLS", "SEAMLESS")
    text = text.replace('"', " ").replace("'", " ")
    text = re.sub(r"[^A-Z0-9/ ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: str) -> set[str]:
    return {tok for tok in _normalize_text(value).split() if tok}


def _normalize_unit(raw: str) -> str:
    key = str(raw or "").strip().lower()
    return _UNIT_MAP.get(key, key.upper() or "EA")


def _decimal_money(raw: Any) -> Decimal:
    text = str(raw or "").strip().replace("$", "").replace(",", "")
    if not text:
        return _D0
    return _q2(_dec(text))


def _infer_category(description: str) -> str:
    upper = description.upper()
    if "FLANGE" in upper:
        return "Flanges"
    if any(word in upper for word in ("EL", "ELBOW", "RETURN", "TEE", "COUPLING", "FITTING")):
        return "Fittings"
    if "PIPE" in upper:
        return "Pipe"
    if any(word in upper for word in ("FLAT BAR", "SQUARE STOCK", "BAR", "BEAM", "CHANNEL", "PLATE")):
        return "Structural"
    return "Material"


def _price_basis_kind(price_basis: str) -> str:
    basis = str(price_basis or "").strip().lower()
    if basis in _UNCLEAR_BASIS or "unclear" in basis:
        return "unclear"
    if any(token in basis for token in _PER_STICK) or "stick" in basis:
        return "stick"
    if any(token in basis for token in _PER_FT):
        return "per_ft"
    if any(token in basis for token in _PER_EACH):
        return "each"
    return "unknown"


def _compose_notes(
    *,
    spec: str,
    price_basis: str,
    ordered_qty: Decimal,
    ordered_unit: str,
    source_note: str,
    review_note: str,
    requires_review: bool,
    pricing_qty: Decimal | None = None,
    pricing_unit: str = "",
) -> str:
    parts: list[str] = []
    if spec:
        parts.append(f"Spec: {spec}")
    parts.append(f"Price basis: {price_basis}")
    parts.append(f"Ordered qty: {money_str(ordered_qty).rstrip('0').rstrip('.') if ordered_qty == ordered_qty.to_integral() else ordered_qty} {ordered_unit}")
    if pricing_qty is not None and pricing_qty > _D0:
        parts.append(f"Pricing qty: {pricing_qty.normalize()} {pricing_unit or 'stick'}")
    if source_note:
        parts.append(source_note)
    if requires_review:
        parts.append("REVIEW REQUIRED")
    if review_note:
        parts.append(review_note)
    return " | ".join(part for part in parts if part)


def _resolve_quantities(
    row: dict[str, Any],
    *,
    unit_price: Decimal,
    line_total: Decimal,
    basis_kind: str,
    requires_review: bool,
) -> tuple[Decimal, str, Decimal, Decimal]:
    ordered_qty = _dec(row.get("qty"))
    ordered_unit = _normalize_unit(str(row.get("qty_unit") or "EA"))
    pricing_qty_raw = str(row.get("pricing_qty") or "").strip()

    if basis_kind == "stick":
        pricing_qty = _dec(pricing_qty_raw) if pricing_qty_raw else _q2(ordered_qty / Decimal("20"))
        unit = "EA"
        quantity = pricing_qty
        unit_cost = unit_price
        total_cost = _q2(quantity * unit_cost)
        return quantity, unit, unit_cost, total_cost

    if basis_kind == "unclear" or (requires_review and basis_kind == "unknown"):
        # Preserve handwritten line total; do not multiply ordered qty by ambiguous unit price.
        return Decimal("1"), "EA", line_total, line_total

    if basis_kind == "per_ft":
        quantity = ordered_qty
        unit = "FT"
        unit_cost = unit_price
        total_cost = _q2(quantity * unit_cost)
        return quantity, unit, unit_cost, total_cost

    if basis_kind == "each":
        quantity = ordered_qty
        unit = "EA"
        unit_cost = unit_price
        total_cost = _q2(quantity * unit_cost)
        return quantity, unit, unit_cost, total_cost

    # Unknown basis — preserve line total when provided.
    if line_total > _D0:
        return Decimal("1"), "EA", line_total, line_total
    quantity = ordered_qty
    unit = ordered_unit
    unit_cost = unit_price
    total_cost = _q2(quantity * unit_cost)
    return quantity, unit, unit_cost, total_cost


def _catalog_score(source: dict[str, Any], catalog_row: dict[str, Any]) -> float:
    description = str(source.get("description") or "")
    spec = str(source.get("spec") or "")
    catalog_text = " ".join(
        [
            str(catalog_row.get("description") or ""),
            str(catalog_row.get("material_grade") or ""),
            str(catalog_row.get("category") or ""),
            str(catalog_row.get("product_type") or ""),
            str(catalog_row.get("pipe_size") or ""),
            str(catalog_row.get("pressure_class") or ""),
        ]
    )
    src_tokens = _tokens(description)
    cat_tokens = _tokens(catalog_text)
    if not src_tokens or not cat_tokens:
        return 0.0
    overlap = len(src_tokens & cat_tokens)
    score = overlap / len(src_tokens)
    spec = str(source.get("spec") or "").upper()
    cat_grade = str(catalog_row.get("material_grade") or "").upper()
    if "316" in spec and "316" not in _normalize_text(catalog_text):
        score -= 0.35
    if "A-106" in spec and "(C.S.)" not in catalog_text.upper() and "CARBON STEEL" not in _normalize_text(catalog_text):
        score -= 0.25
    if "A-36" in spec and "(C.S.)" not in catalog_text.upper() and "CARBON STEEL" not in _normalize_text(catalog_text):
        score -= 0.15
    if "FLANGE" in description.upper() and "FLANGE" not in catalog_text.upper():
        score -= 0.4
    if "RETURN" in description.upper() and "RETURN" not in catalog_text.upper():
        score -= 0.4
    return max(0.0, min(score, 1.0))


def match_catalog_item(
    row: dict[str, Any],
    catalog_rows: list[dict[str, Any]] | None = None,
    *,
    min_score: float = 0.65,
) -> dict[str, Any] | None:
    rows = catalog_rows if catalog_rows is not None else cached_pricing_guide_rows(include_inactive=False)
    best: dict[str, Any] | None = None
    best_score = 0.0
    for catalog_row in rows:
        score = _catalog_score(row, catalog_row)
        if score > best_score:
            best_score = score
            best = catalog_row
    if best is not None and best_score >= min_score:
        return best
    return None


def build_material_quote_line(
    row: dict[str, Any],
    *,
    line_number: int,
    catalog_rows: list[dict[str, Any]] | None = None,
) -> MaterialQuoteImportLine:
    description = str(row.get("description") or "").strip()
    spec = str(row.get("spec") or "").strip()
    price_basis = str(row.get("price_basis") or "").strip()
    basis_kind = _price_basis_kind(price_basis)
    requires_review = bool(row.get("requires_review"))
    review_note = str(row.get("review_note") or "").strip()
    source_note = str(row.get("note") or "").strip()
    unit_price = _decimal_money(row.get("unit_price"))
    line_total = _decimal_money(row.get("line_total"))
    ordered_qty = _dec(row.get("qty"))
    ordered_unit = _normalize_unit(str(row.get("qty_unit") or "EA"))

    quantity, unit, unit_cost, total_cost = _resolve_quantities(
        row,
        unit_price=unit_price,
        line_total=line_total,
        basis_kind=basis_kind,
        requires_review=requires_review,
    )

    if not requires_review and line_total > _D0 and total_cost != line_total:
        requires_review = True
        review_note = review_note or (
            f"Computed total {money_str(total_cost)} differs from source line total {money_str(line_total)}."
        )
        total_cost = line_total

    pricing_qty = _dec(row.get("pricing_qty")) if row.get("pricing_qty") not in (None, "") else None
    notes = _compose_notes(
        spec=spec,
        price_basis=price_basis,
        ordered_qty=ordered_qty,
        ordered_unit=ordered_unit,
        source_note=source_note,
        review_note=review_note,
        requires_review=requires_review,
        pricing_qty=pricing_qty,
        pricing_unit=str(row.get("pricing_unit") or "stick"),
    )

    catalog_match = match_catalog_item(row, catalog_rows)
    pricing_item_id = None
    catalog_description = None
    catalog_score = 0.0
    if catalog_match:
        pricing_item_id = str(catalog_match.get("id") or "") or None
        catalog_description = str(catalog_match.get("description") or "").strip() or None
        catalog_score = _catalog_score(row, catalog_match)

    full_description = f"{description} ({spec})" if spec else description

    return MaterialQuoteImportLine(
        line_number=line_number,
        description=full_description,
        spec=spec,
        ordered_qty=ordered_qty,
        ordered_unit=ordered_unit,
        quantity=quantity,
        unit=unit,
        unit_cost=_q2(unit_cost),
        total_cost=_q2(total_cost),
        price_basis=price_basis,
        category=_infer_category(description),
        notes=notes,
        requires_review=requires_review,
        review_note=review_note,
        pricing_item_id=pricing_item_id,
        catalog_match_description=catalog_description,
        catalog_match_score=catalog_score,
    )


def build_material_quote_import_bundle(
    rows: list[dict[str, Any]] | None = None,
    *,
    catalog_rows: list[dict[str, Any]] | None = None,
    template_id: str = HANDWRITTEN_MATERIAL_QUOTE_ID,
) -> MaterialQuoteImportBundle:
    source_rows = rows if rows is not None else handwritten_material_quote_source_rows()
    lines = [
        build_material_quote_line(row, line_number=index + 1, catalog_rows=catalog_rows)
        for index, row in enumerate(source_rows)
    ]
    preliminary_subtotal = _q2(sum((line.total_cost for line in lines), _D0))
    review_flags = [
        f"Line {line.line_number}: {line.review_note or line.description}"
        for line in lines
        if line.requires_review
    ]
    estimate_notes = " | ".join(
        [
            HANDWRITTEN_MATERIAL_QUOTE_NOTES["lead_time"],
            HANDWRITTEN_MATERIAL_QUOTE_NOTES["stock_length"],
            HANDWRITTEN_MATERIAL_QUOTE_NOTES["subtotal_disclaimer"],
        ]
    )
    return MaterialQuoteImportBundle(
        template_id=template_id,
        title="Handwritten Material Quote Import",
        estimate_notes=estimate_notes,
        review_flags=review_flags,
        lines=lines,
        preliminary_subtotal=preliminary_subtotal,
        subtotal_is_preliminary=bool(review_flags),
        source_row_count=len(source_rows),
    )


def material_quote_line_to_estimate_payload(line: MaterialQuoteImportLine) -> dict[str, Any]:
    return {
        "description": line.description,
        "category": line.category,
        "quantity": float(line.quantity),
        "unit": line.unit,
        "unit_cost": float(line.unit_cost),
        "markup_percent": 0.0,
        "taxable": False,
        "notes": line.notes,
        "pricing_item_id": line.pricing_item_id,
        "sku": "",
        "item_number": "",
    }


def material_quote_lines_to_estimate_payloads(
    bundle: MaterialQuoteImportBundle,
) -> list[dict[str, Any]]:
    return [material_quote_line_to_estimate_payload(line) for line in bundle.lines]


def material_quote_bundle_to_template(bundle: MaterialQuoteImportBundle) -> dict[str, Any]:
    return {
        "template_id": bundle.template_id,
        "template_type": "estimate_material_quote",
        "title": bundle.title,
        "estimate_notes": bundle.estimate_notes,
        "preliminary_subtotal": money_db(bundle.preliminary_subtotal),
        "subtotal_is_preliminary": bundle.subtotal_is_preliminary,
        "review_flags": list(bundle.review_flags),
        "source_row_count": bundle.source_row_count,
        "lines": [
            {
                "line_number": line.line_number,
                "description": line.description,
                "spec": line.spec,
                "ordered_qty": str(line.ordered_qty),
                "ordered_unit": line.ordered_unit,
                "quantity": str(line.quantity),
                "unit": line.unit,
                "unit_cost": money_db(line.unit_cost),
                "total_cost": money_db(line.total_cost),
                "price_basis": line.price_basis,
                "category": line.category,
                "notes": line.notes,
                "requires_review": line.requires_review,
                "review_note": line.review_note,
                "pricing_item_id": line.pricing_item_id,
                "catalog_match_description": line.catalog_match_description,
                "catalog_match_score": line.catalog_match_score,
            }
            for line in bundle.lines
        ],
    }


def build_handwritten_material_quote_template_json(*, indent: int = 2) -> str:
    bundle = build_material_quote_import_bundle()
    return json.dumps(material_quote_bundle_to_template(bundle), indent=indent)


def apply_material_quote_to_estimate(
    estimate_id: str,
    bundle: MaterialQuoteImportBundle,
) -> tuple[bool, str, dict[str, Any]]:
    from app.services.estimate_costing_service import add_estimate_material_batch
    from app.services.repository import update_row_admin
    payloads = material_quote_lines_to_estimate_payloads(bundle)
    result = add_estimate_material_batch(estimate_id, payloads)
    if not result.ok:
        return False, str(result.error or "Import failed."), {"saved": 0}

    update_row_admin("estimates", {"notes": bundle.estimate_notes}, {"id": estimate_id})
    return True, "Imported handwritten material quote lines.", {
        "saved": len(payloads),
        "preliminary_subtotal": money_db(bundle.preliminary_subtotal),
        "review_flags": bundle.review_flags,
    }


def create_estimate_for_material_quote(
    bundle: MaterialQuoteImportBundle,
    *,
    quote_number: str = "",
) -> tuple[bool, str, str | None]:
    from app.db import insert_row_admin
    from app.services.shared_sequence import ensure_quote_number_for_save
    qn = str(quote_number or "").strip()
    if not qn:
        qn = ensure_quote_number_for_save("", year=None)
    payload = {
        "quote_number": qn,
        "status": "draft",
        "project_name": bundle.title,
        "description": bundle.title,
        "notes": bundle.estimate_notes,
        "material_cost": money_db(bundle.preliminary_subtotal),
        "total_cost": money_db(bundle.preliminary_subtotal),
        "customer_price": money_db(bundle.preliminary_subtotal),
        "default_material_markup_pct": 0,
    }
    try:
        row = insert_row_admin("estimates", payload)
    except Exception as exc:
        return False, str(exc), None
    estimate_id = str(row.get("id") or "") or None
    if not estimate_id:
        return False, "Estimate row was not created.", None
    ok, msg, meta = apply_material_quote_to_estimate(estimate_id, bundle)
    if not ok:
        return False, msg, estimate_id
    return True, msg, estimate_id
