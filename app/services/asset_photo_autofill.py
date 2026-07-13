from __future__ import annotations

"""
Asset photo / PDF-page extraction via the OpenAI Responses API only.

Uses ``from openai import OpenAI`` and ``client = OpenAI()`` (SDK reads ``OPENAI_API_KEY``
from the environment). Set ``OPENAI_MODEL`` in the environment for a non-default model
(default ``gpt-5``). Requires ``openai>=1.30.0`` with ``client.responses``.
"""

import base64
import json
import os
import re
from typing import Any

import openai
from openai import OpenAI

from app.services.asset_autofill_media import pdf_extracted_text_hints, prepare_asset_autofill_inputs
from app.services.asset_constants import ASSET_CONDITIONS, ASSET_TYPES
# Single, module-level client (required pattern)
try:
    client = OpenAI()
except Exception as exc:
    # OpenAI SDK raises if OPENAI_API_KEY is missing; give an actionable message.
    raise RuntimeError(
        "OPENAI_API_KEY is not set in the environment. "
        "Add it via .env (local) or Render → Environment (production)."
    ) from exc

# Hard runtime validation (diagnose Render mismatch / shadowed import)
if not hasattr(client, "responses"):
    raise RuntimeError(
        f"OpenAI SDK mismatch: version={openai.__version__}, client_type={type(client)}, "
        f"has_responses={hasattr(client, 'responses')}. Render is likely running an older SDK or a shadowed import."
    )

# Fields that get per-field confidence + review flags (aligned with extraction output)
_FIELD_KEYS = [
    "asset_name",
    "asset_type",
    "manufacturer",
    "model",
    "serial_number",
    "condition",
    "notes",
    "hour_meter",
    "mileage",
    "location",
]

_IMAGE_ROLES = ("overview", "serial_tag", "meter", "mixed", "unknown")

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5").strip() or "gpt-5"


def _guess_mime_type(file_name: str) -> str:
    lower = file_name.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".jpeg") or lower.endswith(".jpg"):
        return "image/jpeg"
    return "image/jpeg"


def _to_data_url(file_bytes: bytes, file_name: str) -> str:
    mime = _guess_mime_type(file_name)
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def clean_asset_code(text: str) -> str:
    text = str(text).strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text)
    return text.strip("-")


def next_asset_id(rows: list[dict[str, Any]]) -> str:
    nums = []
    for r in rows:
        value = str(r.get("asset_id", "")).strip().upper()
        if value.startswith("AST-"):
            try:
                nums.append(int(value.replace("AST-", "")))
            except Exception:
                pass
    next_num = max(nums) + 1 if nums else 1
    return f"AST-{next_num:03d}"


def make_unique_asset_name(base_value: str, rows: list[dict[str, Any]]) -> str:
    existing = {str(r.get("asset_name", "")).strip().upper() for r in rows}
    if base_value.upper() not in existing:
        return base_value

    i = 2
    while True:
        candidate = f"{base_value}_{i}"
        if candidate.upper() not in existing:
            return candidate
        i += 1


def _extraction_json_schema(num_images: int) -> dict[str, Any]:
    fc_props = {k: {"type": "number", "minimum": 0, "maximum": 1} for k in _FIELD_KEYS}
    fr_props = {k: {"type": "array", "items": {"type": "string"}} for k in _FIELD_KEYS}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "asset_name": {"type": "string"},
            "asset_type": {"type": "string", "enum": list(ASSET_TYPES)},
            "manufacturer": {"type": "string"},
            "model": {"type": "string"},
            "serial_number": {"type": "string"},
            "location": {"type": "string"},
            "condition": {"type": "string", "enum": list(ASSET_CONDITIONS)},
            "notes": {"type": "string"},
            "hour_meter": {"type": "number"},
            "mileage": {"type": "number"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "review_flags": {"type": "array", "items": {"type": "string"}},
            "field_confidence": {
                "type": "object",
                "additionalProperties": False,
                "properties": fc_props,
                "required": list(_FIELD_KEYS),
            },
            "field_review_flags": {
                "type": "object",
                "additionalProperties": False,
                "properties": fr_props,
                "required": list(_FIELD_KEYS),
            },
            "per_image_role": {
                "type": "array",
                "minItems": num_images,
                "maxItems": num_images,
                "items": {
                    "type": "string",
                    "enum": list(_IMAGE_ROLES),
                },
            },
        },
        "required": [
            "asset_name",
            "asset_type",
            "manufacturer",
            "model",
            "serial_number",
            "location",
            "condition",
            "notes",
            "hour_meter",
            "mileage",
            "confidence",
            "review_flags",
            "field_confidence",
            "field_review_flags",
            "per_image_role",
        ],
    }


def _response_text_format(num_images: int) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": "asset_photo_extraction",
        "strict": True,
        "schema": _extraction_json_schema(num_images),
    }


def _instructions(num_images: int) -> str:
    return f"""
You are a field equipment analyst. You will receive {num_images} image(s) of industrial equipment, tools, or vehicles (order matches image order below).

## Image roles (set per_image_role, one entry per image, same order)
- **overview**: full unit, brand decals, model plates on body, general condition.
- **serial_tag**: close-up of serial / PIN / VIN / compliance plate — **prefer this for serial_number** when present.
- **meter**: hour meter, odometer, or digital display clearly showing hours or miles.
- **mixed**: more than one of the above in one frame.
- **unknown**: unusable or unclear.

## Evidence rules (critical)
1. **serial_number**: Prefer text read from a **serial_tag** or legible nameplate. Do **not** invent a serial from a blurry overview. If only overview is available, transcribe only what is clearly visible; else leave empty and flag.
2. **hour_meter / mileage**: Extract numeric readings **only** when a meter/LCD/gauge is clearly visible (often in a **meter** or **mixed** image). Use **hour_meter** for engine/hobbs-style hours, **mileage** for distance odometers. If the display is unreadable, use 0 and flag.
3. **manufacturer / model**: Prefer decals/nameplates; reconcile conflicts; note conflicts in field_review_flags and review_flags.
4. **asset_type**: Choose the best enum match from visible shape and context.
5. **condition**: Choose exactly one enum — Excellent / Good / Fair / Poor / Needs Repair — from visible paint, rust, cracks, leaks, tire wear, cable damage, etc.
6. **notes**: Include: (a) concise visible damage/wear, (b) safety-relevant issues, (c) unreadable areas. Do not repeat the enum condition word-for-word only; describe what you see.
7. **asset_name**: Short practical label (e.g. "Genie telehandler" / "Miller welder").

## Confidence
- **field_confidence**: 0–1 per field for how trustworthy that field is given the images.
- **field_review_flags**: short strings per field (e.g. serial_number: "plate glare", hour_meter: "digits partially cut off").
- **confidence**: overall 0–1 (you may set roughly the mean of important fields, slightly lower if images conflict).
- **review_flags**: global issues (e.g. "low light", "only one angle provided").

Use empty strings only where unknown; use **0** for hour_meter/mileage when no reading is visible.
"""


def _merge_review_lists(parsed: dict[str, Any]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    fr = parsed.get("field_review_flags")
    if isinstance(fr, dict):
        for field, flags in fr.items():
            if not isinstance(flags, list):
                continue
            for item in flags:
                s = str(item).strip()
                if not s:
                    continue
                line = f"[{field}] {s}"
                if line not in seen:
                    seen.add(line)
                    merged.append(line)
    top = parsed.get("review_flags")
    if isinstance(top, list):
        for item in top:
            s = str(item).strip()
            if s and s not in seen:
                seen.add(s)
                merged.append(s)
    return merged


def _overall_confidence(parsed: dict[str, Any]) -> float:
    fc = parsed.get("field_confidence")
    if isinstance(fc, dict) and fc:
        nums: list[float] = []
        for k in _FIELD_KEYS:
            v = fc.get(k)
            try:
                if v is not None:
                    nums.append(float(v))
            except (TypeError, ValueError):
                pass
        if nums:
            return max(0.0, min(1.0, sum(nums) / len(nums)))
    try:
        return max(0.0, min(1.0, float(parsed.get("confidence", 0))))
    except (TypeError, ValueError):
        return 0.0


def _normalize_field_confidence(parsed: dict[str, Any]) -> None:
    fc = parsed.get("field_confidence")
    if not isinstance(fc, dict):
        parsed["field_confidence"] = {k: 0.0 for k in _FIELD_KEYS}
        return
    out: dict[str, float] = {}
    for k in _FIELD_KEYS:
        try:
            out[k] = max(0.0, min(1.0, float(fc.get(k, 0))))
        except (TypeError, ValueError):
            out[k] = 0.0
    parsed["field_confidence"] = out


def _normalize_field_review_flags(parsed: dict[str, Any]) -> None:
    fr = parsed.get("field_review_flags")
    if not isinstance(fr, dict):
        parsed["field_review_flags"] = {k: [] for k in _FIELD_KEYS}
        return
    out: dict[str, list[str]] = {}
    for k in _FIELD_KEYS:
        raw = fr.get(k, [])
        if not isinstance(raw, list):
            out[k] = []
        else:
            out[k] = [str(x).strip() for x in raw if str(x).strip()]
    parsed["field_review_flags"] = out


def _normalize_parsed(parsed: dict[str, Any], num_images: int) -> dict[str, Any]:
    for key in [
        "asset_name",
        "asset_type",
        "manufacturer",
        "model",
        "serial_number",
        "location",
        "condition",
        "notes",
    ]:
        parsed[key] = str(parsed.get(key, "") or "").strip()

    try:
        parsed["hour_meter"] = float(parsed.get("hour_meter", 0) or 0)
    except (TypeError, ValueError):
        parsed["hour_meter"] = 0.0
    try:
        parsed["mileage"] = float(parsed.get("mileage", 0) or 0)
    except (TypeError, ValueError):
        parsed["mileage"] = 0.0

    if parsed.get("asset_type") not in ASSET_TYPES:
        parsed["asset_type"] = "Other"

    if parsed.get("condition") not in ASSET_CONDITIONS:
        parsed["condition"] = "Good" if "Good" in ASSET_CONDITIONS else ASSET_CONDITIONS[0]

    _normalize_field_confidence(parsed)
    _normalize_field_review_flags(parsed)

    roles = parsed.get("per_image_role")
    if not isinstance(roles, list) or len(roles) != num_images:
        parsed["per_image_role"] = ["unknown"] * num_images
    else:
        fixed = []
        for r in roles[:num_images]:
            s = str(r).strip()
            fixed.append(s if s in _IMAGE_ROLES else "unknown")
        while len(fixed) < num_images:
            fixed.append("unknown")
        parsed["per_image_role"] = fixed[:num_images]

    parsed["review_flags"] = _merge_review_lists(parsed)
    parsed["confidence"] = _overall_confidence(parsed)

    # Backward compatibility with Asset Photo Auto-Fill page (condition_notes)
    parsed["condition_notes"] = parsed.get("notes", "")

    return parsed


def _default_condition() -> str:
    return "Good" if "Good" in ASSET_CONDITIONS else ASSET_CONDITIONS[0]


def _fallback_parsed(num_images: int, *, reason: str) -> dict[str, Any]:
    """Minimal valid structure when the model output cannot be parsed as JSON."""
    return {
        "asset_name": "",
        "asset_type": "Other",
        "manufacturer": "",
        "model": "",
        "serial_number": "",
        "location": "",
        "condition": _default_condition(),
        "notes": reason,
        "hour_meter": 0.0,
        "mileage": 0.0,
        "confidence": 0.0,
        "review_flags": [reason],
        "field_confidence": {k: 0.0 for k in _FIELD_KEYS},
        "field_review_flags": {k: [] for k in _FIELD_KEYS},
        "per_image_role": ["unknown"] * num_images,
    }


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    """
    Parse a single JSON object from model output.
    Handles optional whitespace, markdown fences, or extra prose.
    """
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Empty model output.")

    try:
        val = json.loads(text)
        if isinstance(val, dict):
            return val
        raise ValueError("JSON root is not an object.")
    except json.JSONDecodeError:
        pass

    m = _JSON_FENCE_RE.search(text)
    if m:
        inner = m.group(1).strip()
        try:
            val = json.loads(inner)
            if isinstance(val, dict):
                return val
        except json.JSONDecodeError:
            pass

    # Last resort: first balanced {...} slice
    start = text.find("{")
    if start < 0:
        raise ValueError("No JSON object found in model output.")
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                chunk = text[start : i + 1]
                val = json.loads(chunk)
                if isinstance(val, dict):
                    return val
                raise ValueError("Extracted JSON is not an object.")
    raise ValueError("Unbalanced braces in model output.")


def _call_responses_api(client: OpenAI, *, num_images: int, content: list[dict[str, Any]]) -> str:
    """Run ``client.responses.create`` and return assistant text output."""
    try:
        response = client.responses.create(
            model=_model_name(),
            input=[
                {
                    "type": "message",
                    "role": "user",
                    "content": content,
                }
            ],
            text={"format": _response_text_format(num_images)},
        )
    except Exception as exc:
        raise RuntimeError(
            f"OpenAI Responses API request failed ({exc.__class__.__name__}): {exc}"
        ) from exc

    raw = getattr(response, "output_text", None)
    if raw is None or not str(raw).strip():
        raise RuntimeError(
            "OpenAI returned no text output (output_text empty). Check OPENAI_MODEL and API access."
        )
    return str(raw)


def extract_asset_from_photos(photos: list[tuple[bytes, str]]) -> dict[str, Any]:
    """
    One or more equipment photos → structured fields for review.
    Uses the same enum lists as Asset Intake (asset_constants).

    Accepts raster images (JPG/PNG/WEBP), HEIC (converted to PNG), and PDF (pages rendered to PNG)
    via prepare_asset_autofill_inputs.

    Returned dict always includes: confidence, review_flags, field_confidence,
    field_review_flags, per_image_role, hour_meter, mileage, condition_notes (alias of notes).
    """
    if not photos:
        raise ValueError("At least one photo is required.")

    originals = list(photos)
    photos = prepare_asset_autofill_inputs(photos)

    n = len(photos)

    instructions = _instructions(n)
    pdf_hint = pdf_extracted_text_hints(originals)
    if pdf_hint:
        instructions += (
            "\n\n## Supplemental text from uploaded PDF(s)\n"
            "Use together with the rendered page images below. Prefer visible image evidence for "
            "plates and meters; use this text for model/serial strings when clearly matching.\n\n"
            + pdf_hint
        )

    content: list[dict[str, Any]] = [{"type": "input_text", "text": instructions}]
    for idx, (file_bytes, file_name) in enumerate(photos):
        data_url = _to_data_url(file_bytes, file_name)
        content.append(
            {
                "type": "input_text",
                "text": f"Image {idx + 1} of {n} (filename hint: {file_name})",
            }
        )
        content.append({"type": "input_image", "image_url": data_url, "detail": "high"})

    raw = _call_responses_api(client, num_images=n, content=content)

    fallback_note = (
        "Automatic extraction could not parse the model response as JSON; "
        "defaults were applied. Re-run or check OPENAI_MODEL / API logs."
    )

    try:
        parsed = _parse_json_object(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        fb = _fallback_parsed(n, reason=f"{fallback_note} ({exc})")
        return _normalize_parsed(fb, n)

    if not isinstance(parsed, dict):
        fb = _fallback_parsed(n, reason=fallback_note + " (root was not an object).")
        return _normalize_parsed(fb, n)

    try:
        return _normalize_parsed(parsed, n)
    except Exception as exc:
        fb = _fallback_parsed(n, reason=f"{fallback_note} (normalize: {exc})")
        return _normalize_parsed(fb, n)


def extract_asset_from_photo(file_bytes: bytes, file_name: str) -> dict[str, Any]:
    """Single-image wrapper for existing callers."""
    return extract_asset_from_photos([(file_bytes, file_name)])
