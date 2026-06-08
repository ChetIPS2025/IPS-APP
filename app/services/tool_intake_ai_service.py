"""Tool photo vision, receipt OCR, and image search for Quick Add Tool."""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Any

try:
    from app.config import settings
except ImportError:
    from config import settings  # type: ignore

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

_TOOL_KINDS = frozenset({"serialized", "small", "inventory"})


@dataclass(frozen=True)
class ToolAIConfig:
    vision_provider: str
    vision_api_key: str
    ocr_provider: str
    ocr_api_key: str
    image_search_provider: str
    image_search_api_key: str

    @property
    def vision_ready(self) -> bool:
        return bool(self.vision_api_key) and self.vision_provider not in {"", "none", "disabled"}

    @property
    def ocr_ready(self) -> bool:
        return bool(self.ocr_api_key) and self.ocr_provider not in {"", "none", "disabled"}

    @property
    def image_search_ready(self) -> bool:
        return bool(self.image_search_api_key) and self.image_search_provider not in {"", "none", "disabled"}


def load_tool_ai_config() -> ToolAIConfig:
    openai_fallback = (getattr(settings, "openai_api_key", "") or os.getenv("OPENAI_API_KEY", "")).strip()
    return ToolAIConfig(
        vision_provider=(getattr(settings, "tool_vision_provider", "") or "openai").strip().casefold(),
        vision_api_key=(getattr(settings, "tool_vision_api_key", "") or openai_fallback).strip(),
        ocr_provider=(getattr(settings, "tool_ocr_provider", "") or "openai").strip().casefold(),
        ocr_api_key=(getattr(settings, "tool_ocr_api_key", "") or openai_fallback).strip(),
        image_search_provider=(getattr(settings, "tool_image_search_provider", "") or "openai").strip().casefold(),
        image_search_api_key=(getattr(settings, "tool_image_search_api_key", "") or openai_fallback).strip(),
    )


def tool_ai_status() -> dict[str, Any]:
    cfg = load_tool_ai_config()
    return {
        "vision": {"provider": cfg.vision_provider, "ready": cfg.vision_ready},
        "ocr": {"provider": cfg.ocr_provider, "ready": cfg.ocr_ready},
        "image_search": {"provider": cfg.image_search_provider, "ready": cfg.image_search_ready},
    }


def _guess_mime(file_name: str) -> str:
    low = file_name.casefold()
    if low.endswith(".png"):
        return "image/png"
    if low.endswith(".webp"):
        return "image/webp"
    if low.endswith(".pdf"):
        return "application/pdf"
    if low.endswith(".heif"):
        return "image/heif"
    if low.endswith(".heic"):
        return "image/heic"
    return "image/jpeg"


def _to_data_url(file_bytes: bytes, file_name: str) -> str:
    mime = _guess_mime(file_name)
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Empty model output.")
    try:
        val = json.loads(text)
        if isinstance(val, dict):
            return val
    except json.JSONDecodeError:
        pass
    match = _JSON_FENCE_RE.search(text)
    if match:
        val = json.loads(match.group(1).strip())
        if isinstance(val, dict):
            return val
    start = text.find("{")
    if start < 0:
        raise ValueError("No JSON object in model output.")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                val = json.loads(text[start : i + 1])
                if isinstance(val, dict):
                    return val
    raise ValueError("Could not parse JSON from model output.")


def _openai_client(api_key: str):
    from openai import OpenAI

    if not api_key:
        raise RuntimeError("API key is not configured.")
    return OpenAI(api_key=api_key)


def _openai_vision_extract(
    *,
    api_key: str,
    file_bytes: bytes,
    file_name: str,
    instructions: str,
    schema: dict[str, Any],
    schema_name: str,
) -> dict[str, Any]:
    try:
        from app.services.asset_autofill_media import pdf_extracted_text_hints
        from app.services.upload_media_strategy import vision_inputs_from_upload
    except ImportError:
        from services.asset_autofill_media import pdf_extracted_text_hints  # type: ignore
        from services.upload_media_strategy import vision_inputs_from_upload  # type: ignore

    originals = [(file_bytes, file_name)]
    images = vision_inputs_from_upload(file_bytes, file_name)
    prompt = instructions
    pdf_hint = pdf_extracted_text_hints(originals)
    if pdf_hint:
        prompt += (
            "\n\n## Supplemental text from uploaded PDF(s)\n"
            "Use together with the rendered page images below.\n\n"
            + pdf_hint
        )

    client = _openai_client(api_key)
    if not hasattr(client, "responses"):
        raise RuntimeError("OpenAI SDK does not support the Responses API.")

    model = (getattr(settings, "openai_model", "") or os.getenv("OPENAI_MODEL", "gpt-5")).strip() or "gpt-5"
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    for idx, (img_bytes, img_name) in enumerate(images):
        if len(images) > 1:
            content.append(
                {
                    "type": "input_text",
                    "text": f"Image {idx + 1} of {len(images)} (filename hint: {img_name})",
                }
            )
        content.append(
            {"type": "input_image", "image_url": _to_data_url(img_bytes, img_name), "detail": "high"}
        )
    response = client.responses.create(
        model=model,
        input=[{"type": "message", "role": "user", "content": content}],
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        },
    )
    raw = str(getattr(response, "output_text", "") or "").strip()
    if not raw:
        raise RuntimeError("Vision model returned no text.")
    return _parse_json_object(raw)


def _tool_extraction_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "tool_name": {"type": "string"},
            "manufacturer": {"type": "string"},
            "model": {"type": "string"},
            "serial_number": {"type": "string"},
            "tool_kind": {"type": "string", "enum": ["serialized", "small", "inventory"]},
            "category": {"type": "string"},
            "quantity": {"type": "number"},
            "unit_cost": {"type": "number"},
            "notes": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": [
            "tool_name",
            "manufacturer",
            "model",
            "serial_number",
            "tool_kind",
            "category",
            "quantity",
            "unit_cost",
            "notes",
            "confidence",
        ],
    }


def _normalize_tool_fields(parsed: dict[str, Any], *, default_kind: str = "") -> dict[str, Any]:
    kind = str(parsed.get("tool_kind") or default_kind or "serialized").strip().casefold()
    if kind not in _TOOL_KINDS:
        kind = "serialized" if str(parsed.get("serial_number") or "").strip() else "small"
    try:
        qty = float(parsed.get("quantity") or 1)
    except (TypeError, ValueError):
        qty = 1.0
    try:
        cost = float(parsed.get("unit_cost") or 0)
    except (TypeError, ValueError):
        cost = 0.0
    try:
        conf = float(parsed.get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    return {
        "tool_name": str(parsed.get("tool_name") or "").strip(),
        "manufacturer": str(parsed.get("manufacturer") or "").strip(),
        "model": str(parsed.get("model") or "").strip(),
        "serial_number": str(parsed.get("serial_number") or "").strip(),
        "tool_kind": kind,
        "category": str(parsed.get("category") or "").strip(),
        "quantity": max(0.0, qty),
        "unit_cost": max(0.0, cost),
        "notes": str(parsed.get("notes") or "").strip(),
        "confidence": max(0.0, min(1.0, conf)),
    }


def extract_tool_from_photo(
    file_bytes: bytes,
    file_name: str,
    *,
    kind_hint: str = "",
) -> dict[str, Any]:
    """Identify a tool from a photo using TOOL_VISION_PROVIDER / TOOL_VISION_API_KEY."""
    cfg = load_tool_ai_config()
    if not cfg.vision_ready:
        raise RuntimeError(
            "Tool vision is not configured. Set TOOL_VISION_API_KEY (and optionally TOOL_VISION_PROVIDER=openai)."
        )
    if cfg.vision_provider != "openai":
        raise RuntimeError(f"Tool vision provider '{cfg.vision_provider}' is not supported yet. Use openai.")

    hint = kind_hint.strip().casefold()
    instructions = f"""
You analyze photos of jobsite tools and consumables for inventory intake.

Classify each item into exactly one bucket:
- **serialized**: individual cordless/power tools with a readable serial number (Milwaukee, DeWalt, etc.)
- **small**: quantity hand tools without serial numbers (wrenches, pliers, sockets, screwdrivers)
- **inventory**: consumables (cut-off wheels, drill bits, blades, gloves, fasteners)

Read serial numbers only when clearly visible on a nameplate. Do not invent serials.
Suggested bucket hint from user: {hint or "none"}.

Return practical field values for Quick Add Tool.
"""
    parsed = _openai_vision_extract(
        api_key=cfg.vision_api_key,
        file_bytes=file_bytes,
        file_name=file_name,
        instructions=instructions,
        schema=_tool_extraction_schema(),
        schema_name="tool_photo_extraction",
    )
    return _normalize_tool_fields(parsed, default_kind=hint)


def ocr_tool_receipt(file_bytes: bytes, file_name: str) -> dict[str, Any]:
    """Read a purchase receipt using TOOL_OCR_PROVIDER / TOOL_OCR_API_KEY."""
    cfg = load_tool_ai_config()
    if not cfg.ocr_ready:
        raise RuntimeError(
            "Tool OCR is not configured. Set TOOL_OCR_API_KEY (and optionally TOOL_OCR_PROVIDER=openai)."
        )
    if cfg.ocr_provider != "openai":
        raise RuntimeError(f"Tool OCR provider '{cfg.ocr_provider}' is not supported yet. Use openai.")

    instructions = """
You read purchase receipts for tools and consumables.
Extract the primary line item name, quantity purchased, unit price if visible, and vendor.
Classify tool_kind as serialized (single serial-tracked tool), small (hand tool), or inventory (consumable).
If multiple line items, use the largest tool line and mention others in notes.
"""
    parsed = _openai_vision_extract(
        api_key=cfg.ocr_api_key,
        file_bytes=file_bytes,
        file_name=file_name,
        instructions=instructions,
        schema=_tool_extraction_schema(),
        schema_name="tool_receipt_ocr",
    )
    return _normalize_tool_fields(parsed)


def search_tool_by_image(file_bytes: bytes, file_name: str) -> dict[str, Any]:
    """Suggest tool identity from image search provider (OpenAI vision fallback)."""
    cfg = load_tool_ai_config()
    if not cfg.image_search_ready:
        raise RuntimeError(
            "Tool image search is not configured. Set TOOL_IMAGE_SEARCH_API_KEY "
            "(and optionally TOOL_IMAGE_SEARCH_PROVIDER=openai)."
        )
    if cfg.image_search_provider != "openai":
        raise RuntimeError(
            f"Image search provider '{cfg.image_search_provider}' is not supported yet. Use openai."
        )

    instructions = """
Identify the tool or consumable in this image. Return the best matching commercial product name,
manufacturer, model if visible, and the correct tool_kind bucket (serialized, small, or inventory).
This is a visual product match, not a web search.
"""
    parsed = _openai_vision_extract(
        api_key=cfg.image_search_api_key,
        file_bytes=file_bytes,
        file_name=file_name,
        instructions=instructions,
        schema=_tool_extraction_schema(),
        schema_name="tool_image_search",
    )
    result = _normalize_tool_fields(parsed)
    result["search_provider"] = cfg.image_search_provider
    return result


__all__ = [
    "ToolAIConfig",
    "extract_tool_from_photo",
    "load_tool_ai_config",
    "ocr_tool_receipt",
    "search_tool_by_image",
    "tool_ai_status",
]
