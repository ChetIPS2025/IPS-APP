from __future__ import annotations

import base64
import io
import json
from typing import Any

import pandas as pd
from openai import OpenAI

try:
    from config import settings
except ImportError:
    from app.config import settings  # type: ignore


DEFAULT_MARKUP_PCT = 0.25


def _client() -> OpenAI:
    api_key = settings.openai_api_key.strip()
    if not api_key or api_key == "your_openai_api_key":
        raise RuntimeError("OPENAI_API_KEY is missing from .env")
    return OpenAI(api_key=api_key)


def _model_name() -> str:
    return settings.openai_model.strip() or "gpt-5"


def _guess_mime_type(file_name: str) -> str:
    lower = file_name.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".pdf"):
        return "application/pdf"
    return "image/jpeg"


def _to_data_url(file_bytes: bytes, file_name: str) -> str:
    mime = _guess_mime_type(file_name)
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        text = str(value).strip().replace("$", "").replace(",", "")
        if text == "":
            return default
        return float(text)
    except Exception:
        return default


def compute_sell_price(unit_cost: float, markup_pct: float = DEFAULT_MARKUP_PCT) -> float:
    return round(float(unit_cost or 0) * (1 + markup_pct), 2)


def _quote_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "vendor_name": {"type": "string"},
            "quote_number": {"type": "string"},
            "quote_date": {"type": "string"},
            "quote_total": {"type": "number"},
            "shipping_total": {"type": "number"},
            "tax_total": {"type": "number"},
            "notes": {"type": "string"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "item_description": {"type": "string"},
                        "vendor_item_number": {"type": "string"},
                        "category": {"type": "string"},
                        "subgroup": {"type": "string"},
                        "unit": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_cost": {"type": "number"},
                        "extended_cost": {"type": "number"},
                        "notes": {"type": "string"},
                    },
                    "required": [
                        "item_description",
                        "vendor_item_number",
                        "category",
                        "subgroup",
                        "unit",
                        "quantity",
                        "unit_cost",
                        "extended_cost",
                        "notes",
                    ],
                },
            },
            "confidence": {"type": "number"},
            "review_flags": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "vendor_name",
            "quote_number",
            "quote_date",
            "quote_total",
            "shipping_total",
            "tax_total",
            "notes",
            "items",
            "confidence",
            "review_flags",
        ],
    }


def _response_text_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": "material_quote_extraction",
        "strict": True,
        "schema": _quote_json_schema(),
    }


def _normalize_result(parsed: dict[str, Any], source_label: str = "") -> dict[str, Any]:
    parsed["vendor_name"] = str(parsed.get("vendor_name", "") or "").strip()
    parsed["quote_number"] = str(parsed.get("quote_number", "") or "").strip()
    parsed["quote_date"] = str(parsed.get("quote_date", "") or "").strip()
    parsed["notes"] = str(parsed.get("notes", "") or "").strip()
    parsed["quote_total"] = round(to_float(parsed.get("quote_total", 0)), 2)
    parsed["shipping_total"] = round(to_float(parsed.get("shipping_total", 0)), 2)
    parsed["tax_total"] = round(to_float(parsed.get("tax_total", 0)), 2)

    try:
        parsed["confidence"] = float(parsed.get("confidence", 0))
    except Exception:
        parsed["confidence"] = 0.0

    if not isinstance(parsed.get("review_flags"), list):
        parsed["review_flags"] = []

    cleaned_items: list[dict[str, Any]] = []
    for item in parsed.get("items", []):
        description = str(item.get("item_description", "") or "").strip()
        if not description:
            continue

        quantity = to_float(item.get("quantity", 0), 0.0)
        unit_cost = round(to_float(item.get("unit_cost", 0), 0.0), 2)
        extended_cost = round(
            to_float(item.get("extended_cost", quantity * unit_cost), quantity * unit_cost),
            2,
        )

        cleaned_items.append(
            {
                "item_description": description,
                "vendor_item_number": str(item.get("vendor_item_number", "") or "").strip(),
                "category": str(item.get("category", "") or "").strip(),
                "subgroup": str(item.get("subgroup", "") or "").strip(),
                "unit": str(item.get("unit", "") or "").strip() or "EA",
                "quantity": quantity,
                "unit_cost": unit_cost,
                "extended_cost": extended_cost,
                "notes": str(item.get("notes", "") or "").strip(),
                "source_page": source_label,
            }
        )

    parsed["items"] = cleaned_items
    return parsed


def _extract_from_image(file_bytes: bytes, file_name: str, page_label: str = "") -> dict[str, Any]:
    client = _client()
    data_url = _to_data_url(file_bytes, file_name)

    prompt = """
You are extracting vendor material quote data from an image.

Return only JSON matching the schema.

Rules:
- Parse as many line items as possible.
- Keep numbers numeric.
- item_description must be readable and useful.
- Use empty string for unknown text values.
- Use 0 for unknown numeric values.
- review_flags should be short warnings like:
  - quote number unclear
  - date unclear
  - some line items unreadable
  - totals not visible
  - low image quality
"""

    response = client.responses.create(
        model=_model_name(),
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url, "detail": "high"},
                ],
            }
        ],
        text={"format": _response_text_format()},
    )

    parsed = json.loads(response.output_text)
    return _normalize_result(parsed, source_label=page_label or "image")


def _extract_from_document(file_bytes: bytes, file_name: str) -> dict[str, Any]:
    client = _client()

    prompt = """
Extract vendor quote information from the attached document.

Return only JSON matching the schema.
Use empty string for unknown text and 0 for unknown numeric values.
"""

    response = client.responses.create(
        model=_model_name(),
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_file",
                        "filename": file_name,
                        "file_data": _to_data_url(file_bytes, file_name),
                    },
                ],
            }
        ],
        text={"format": _response_text_format()},
    )

    parsed = json.loads(response.output_text)
    return _normalize_result(parsed, source_label="document")


def parse_quote_spreadsheet(file_bytes: bytes, file_name: str) -> dict[str, Any]:
    ext = file_name.lower().rsplit(".", 1)[-1]

    if ext == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        df = pd.read_excel(io.BytesIO(file_bytes))

    rename_map = {
        "description": "item_description",
        "qty": "quantity",
        "price": "unit_cost",
        "unit price": "unit_cost",
        "ext price": "extended_cost",
        "extended price": "extended_cost",
        "part": "vendor_item_number",
        "part number": "vendor_item_number",
        "item number": "vendor_item_number",
    }

    canonical = {}
    for col in df.columns:
        lower = str(col).strip().lower()
        canonical[col] = rename_map.get(lower, lower.replace(" ", "_"))
    df = df.rename(columns=canonical)

    items = []
    for _, row in df.fillna("").iterrows():
        description = str(row.get("item_description", "")).strip()
        if not description:
            continue

        quantity = to_float(row.get("quantity", 0))
        unit_cost = round(to_float(row.get("unit_cost", 0)), 2)
        extended_cost = round(to_float(row.get("extended_cost", quantity * unit_cost), quantity * unit_cost), 2)

        items.append(
            {
                "item_description": description,
                "vendor_item_number": str(row.get("vendor_item_number", "")).strip(),
                "category": str(row.get("category", "")).strip(),
                "subgroup": str(row.get("subgroup", "")).strip(),
                "unit": str(row.get("unit", "EA")).strip() or "EA",
                "quantity": quantity,
                "unit_cost": unit_cost,
                "extended_cost": extended_cost,
                "notes": str(row.get("notes", "")).strip(),
                "source_page": "spreadsheet",
            }
        )

    total = round(sum(item["extended_cost"] for item in items), 2)

    return {
        "vendor_name": "",
        "quote_number": "",
        "quote_date": "",
        "quote_total": total,
        "shipping_total": 0.0,
        "tax_total": 0.0,
        "notes": "Imported from spreadsheet.",
        "items": items,
        "confidence": 0.95 if items else 0.0,
        "review_flags": [] if items else ["no spreadsheet items detected"],
        "source_file_name": file_name,
        "source_kind": "spreadsheet",
    }


def extract_material_quote(file_bytes: bytes, file_name: str) -> dict[str, Any]:
    lower = file_name.lower()

    if lower.endswith(".csv") or lower.endswith(".xlsx") or lower.endswith(".xls"):
        return parse_quote_spreadsheet(file_bytes, file_name)

    if lower.endswith(".pdf"):
        result = _extract_from_document(file_bytes, file_name)
        result["source_file_name"] = file_name
        result["source_kind"] = "pdf"
        return result

    if lower.endswith(".jpg") or lower.endswith(".jpeg") or lower.endswith(".png") or lower.endswith(".webp"):
        result = _extract_from_image(file_bytes, file_name)
        result["source_file_name"] = file_name
        result["source_kind"] = "image"
        return result

    raise RuntimeError("Unsupported file type. Upload PDF, image, CSV, or Excel.")


# -----------------------------
# BACKWARD-COMPATIBLE FUNCTIONS
# -----------------------------

def extract_material_quote_from_photo(file_bytes: bytes, file_name: str) -> dict[str, Any]:
    result = _extract_from_image(file_bytes, file_name, page_label="image")
    result["source_file_name"] = file_name
    result["source_kind"] = "image"
    return result


def extract_material_quote_from_pdf(file_bytes: bytes, file_name: str) -> dict[str, Any]:
    result = _extract_from_document(file_bytes, file_name)
    result["source_file_name"] = file_name
    result["source_kind"] = "pdf"
    return result