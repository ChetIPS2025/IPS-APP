"""
Import vendor quote PDFs: hybrid text + table extraction, OpenAI + heuristic fallback,
currency normalization, confidence scores, and estimate_json mapping.
"""
from __future__ import annotations

import io
import json
import re
from typing import Any

try:
    from config import settings
except ImportError:
    from app.config import settings  # type: ignore

from openai import OpenAI

MAX_PDF_TEXT_CHARS = 240_000

# ---------------------------------------------------------------------------
# OpenAI prompt — structured output + per-field confidence (0.0–1.0)
# ---------------------------------------------------------------------------

_VENDOR_QUOTE_SCHEMA_INSTRUCTIONS = """
You are parsing a **vendor / supplier quote or proposal PDF**. Text may be noisy, multi-column, or OCR-like.

Return ONE JSON object:

{
  "vendor_name": "",
  "quote_number": "",
  "quote_date": "",
  "line_items": [
    {
      "description": "",
      "qty": 0.0,
      "unit_price": 0.0,
      "line_total": 0.0
    }
  ],
  "subtotal": 0.0,
  "tax": 0.0,
  "total": 0.0,
  "notes": "",
  "confidence": {
    "overall": 0.0,
    "vendor_name": 0.0,
    "line_items": 0.0,
    "totals": 0.0
  }
}

Rules:
- **vendor_name**: Company/supplier on letterhead or title block (first page top). Not the buyer/customer unless no vendor found.
- **line_items**: Every priced product/service row; merge wrapped description lines into one description when clearly one item.
- If qty/unit/extended are missing, infer: qty=1, line_total from amount column, unit_price = line_total/qty.
- **subtotal / tax / total**: Map labels: Subtotal, Net, Tax, GST, HST, VAT, Sales Tax, Shipping (put notable freight in notes), **Total**, Grand Total, Amount Due, Balance.
- Use 0 for unknown numeric fields; use "" for unknown strings.
- **confidence**: Your subjective 0.0–1.0 scores: how sure you are about the whole parse, vendor name, line items block, and money totals.
- Numbers must be JSON numbers, not strings.
- Output JSON only, no markdown.
"""


def _client() -> OpenAI:
    api_key = settings.openai_api_key.strip()
    if not api_key or api_key == "your_openai_api_key":
        raise RuntimeError("OPENAI_API_KEY is missing from .env")
    return OpenAI(api_key=api_key)


def _model_name() -> str:
    return settings.openai_model.strip() or "gpt-5"


# ---------------------------------------------------------------------------
# PDF text: PyMuPDF + optional pdfplumber tables
# ---------------------------------------------------------------------------


def extract_pdf_text_pymupdf(raw: bytes) -> str:
    """Extract plain text from a PDF using PyMuPDF (fitz)."""
    import fitz

    if not raw:
        raise ValueError("Empty PDF file.")
    doc = fitz.open(stream=raw, filetype="pdf")
    try:
        parts: list[str] = []
        for page in doc:
            parts.append(page.get_text())
    finally:
        doc.close()
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError(
            "No extractable text in this PDF. Try a text-based PDF; scanned images need OCR elsewhere."
        )
    return text[:MAX_PDF_TEXT_CHARS]


def extract_pdfplumber_table_text(raw: bytes) -> str:
    """Detect tabular rows via pdfplumber (best-effort). Returns '' if unavailable."""
    try:
        import pdfplumber
    except ImportError:
        return ""

    lines: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    for row in table:
                        if not row:
                            continue
                        cells = [str(c or "").strip() for c in row]
                        if not any(cells):
                            continue
                        line = " | ".join(cells)
                        lines.append(line)
    except Exception:
        return ""

    return "\n".join(lines)[: MAX_PDF_TEXT_CHARS // 2]


def extract_combined_text_for_parsing(raw: bytes) -> str:
    """PyMuPDF body text plus auto-detected table rows for richer line-item detection."""
    base = extract_pdf_text_pymupdf(raw)
    tbl = extract_pdfplumber_table_text(raw)
    if tbl.strip():
        return (
            base
            + "\n\n--- AUTO-DETECTED TABLE ROWS (from PDF layout) ---\n"
            + tbl
        )
    return base


def extract_pdf_text(raw: bytes) -> str:
    """Public alias (combined extraction)."""
    return extract_combined_text_for_parsing(raw)


# ---------------------------------------------------------------------------
# Currency / number normalization
# ---------------------------------------------------------------------------

_RE_NUMBER_LOOSE = re.compile(r"-?\$?\s*([\d,]+(?:\.\d+)?)\s*")


def parse_currency_number(value: Any) -> float:
    """
    Normalize currency strings: $1,234.56, (1,234.56) accounting negatives, €1.234,56 → float.
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).strip()
    if not raw:
        return 0.0
    neg = "(" in raw and ")" in raw
    s = raw.replace("$", "").replace("€", "").replace("£", "").replace("¥", "")
    s = s.replace("(", "").replace(")", "").strip()
    s = re.sub(r"[^\d,.\-]", "", s)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s and "." not in s:
        parts = s.split(",")
        if len(parts[-1]) == 2 and len(parts) > 1:
            s = ".".join(parts[:-1]) + "." + parts[-1]
        else:
            s = s.replace(",", "")
    try:
        v = float(s)
        return -abs(v) if neg else v
    except ValueError:
        m = _RE_NUMBER_LOOSE.search(raw)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return 0.0


def _f(x: Any, default: float = 0.0) -> float:
    return parse_currency_number(x) if x not in (None, "") else default


# ---------------------------------------------------------------------------
# Heuristic fallback (no LLM)
# ---------------------------------------------------------------------------

_RE_TOTAL = re.compile(
    r"(?:^|\n)\s*(?:Sub[-\s]?total|Subtotal|Net\s*amount)\s*[:#]?\s*\$?\s*([\d,]+\.?\d*)",
    re.I,
)
_RE_TAX = re.compile(
    r"(?:^|\n)\s*(?:Tax|GST|HST|PST|VAT|Sales\s*tax)\s*[:#]?\s*\$?\s*([\d,]+\.?\d*)",
    re.I,
)
_RE_GRAND = re.compile(
    r"(?:^|\n)\s*(?:Grand\s*total|Total\s*amount|Amount\s*due|Invoice\s*total|Total)\s*[:#]?\s*\$?\s*([\d,]+\.?\d*)",
    re.I,
)
_RE_QUOTE = re.compile(
    r"(?:Quote|Quotation|Proposal|Estimate)\s*#?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/_]*)",
    re.I,
)
_RE_SKIP_LINE = re.compile(
    r"^(page\s*\d+|confidential|proprietary)\b",
    re.I,
)


def _header_vendor_guess(lines: list[str]) -> tuple[str, float]:
    """Pick likely vendor from first screen of text; return (name, confidence)."""
    candidates: list[tuple[str, float]] = []
    for i, line in enumerate(lines[:40]):
        s = line.strip()
        if len(s) < 3 or len(s) > 120:
            continue
        if _RE_SKIP_LINE.match(s):
            continue
        low = s.lower()
        if low in ("date", "to:", "from:", "bill to", "ship to", "attention"):
            continue
        score = 0.35
        if re.search(r"\b(inc|llc|ltd|corp|co\.|company|supply|electrical|plumbing|hvac|materials)\b", s, re.I):
            score += 0.35
        if s.isupper() and 5 <= len(s) <= 60:
            score += 0.15
        if i < 8:
            score += 0.15
        candidates.append((s, min(1.0, score)))
    if not candidates:
        return "", 0.0
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0], candidates[0][1]


def _parse_totals_from_text(text: str) -> tuple[float, float, float, float]:
    """Return (subtotal, tax, total, confidence_for_totals)."""
    sub = tax = tot = 0.0
    m = _RE_TOTAL.search(text)
    if m:
        sub = parse_currency_number(m.group(1))
    m = _RE_TAX.search(text)
    if m:
        tax = parse_currency_number(m.group(1))
    m = _RE_GRAND.search(text)
    if m:
        tot = parse_currency_number(m.group(1))
    if tot <= 0 and sub > 0:
        tot = sub + tax
    conf = 0.25
    if tot > 0:
        conf += 0.35
    if sub > 0:
        conf += 0.2
    if tax > 0 or re.search(r"tax|gst|hst|vat", text, re.I):
        conf += 0.1
    return sub, tax, tot, min(1.0, conf)


_RE_LINE_ITEM = re.compile(
    r"^(.+?)\s+(\d+(?:\.\d+)?)\s+[$\u20ac£]?\s*([\d,]+\.?\d*)\s+[$\u20ac£]?\s*([\d,]+\.?\d*)\s*$"
)
_RE_LINE_SIMPLE = re.compile(
    r"^(.+?)\s+[$\u20ac£]?\s*([\d,]+\.?\d*)\s*$"
)


def _parse_line_items_from_text(text: str) -> tuple[list[dict[str, Any]], float]:
    rows: list[dict[str, Any]] = []
    conf = 0.2
    for line in text.splitlines():
        s = line.strip()
        if len(s) < 5:
            continue
        if re.match(r"^(subtotal|tax|total|grand|description|qty|item)\b", s, re.I):
            continue
        if "|" in s and s.count("|") >= 2:
            cells = [c.strip() for c in s.split("|")]
            nums: list[float] = []
            desc_parts: list[str] = []
            for c in cells:
                if not c:
                    continue
                cv = parse_currency_number(c)
                looks_num = bool(re.match(r"^[\s$\-]?[\d,]+\.?\d*\s*$", c))
                if looks_num and cv >= 0:
                    nums.append(cv if cv > 0 else 0.0)
                elif not looks_num:
                    desc_parts.append(c)
            desc = " ".join(desc_parts).strip() or (cells[0] if cells else "")
            nums = [n for n in nums if n > 0]
            if desc and len(nums) >= 1:
                lt = nums[-1]
                up = nums[-2] if len(nums) >= 2 else lt
                qty = nums[0] if len(nums) >= 3 and nums[0] < 1e6 else 1.0
                rows.append(
                    {
                        "description": desc[:500],
                        "qty": qty if qty > 0 else 1.0,
                        "unit_price": up,
                        "line_total": lt,
                    }
                )
                conf = max(conf, 0.5)
            continue
        m = _RE_LINE_ITEM.match(s)
        if m:
            desc, qty_s, up, lt = m.groups()
            rows.append(
                {
                    "description": desc.strip()[:500],
                    "qty": _f(qty_s),
                    "unit_price": _f(up),
                    "line_total": _f(lt),
                }
            )
            conf = max(conf, 0.55)
            continue
        m2 = _RE_LINE_SIMPLE.match(s)
        if m2 and not re.search(r"total|tax|sub", m2.group(1), re.I):
            lt = _f(m2.group(2))
            if lt > 0:
                rows.append(
                    {
                        "description": m2.group(1).strip()[:500],
                        "qty": 1.0,
                        "unit_price": lt,
                        "line_total": lt,
                    }
                )
                conf = max(conf, 0.4)
    if len(rows) >= 3:
        conf = min(1.0, conf + 0.15)
    return rows, conf


def parse_vendor_quote_fallback(text: str) -> dict[str, Any]:
    """Rule-based parse when OpenAI is unavailable or low-confidence."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    vendor, vconf = _header_vendor_guess(lines)
    sub, tax, tot, tconf = _parse_totals_from_text(text)
    items, iconf = _parse_line_items_from_text(text)

    qn = ""
    mq = _RE_QUOTE.search(text)
    if mq:
        qn = mq.group(1).strip()

    overall = (vconf * 0.25 + tconf * 0.35 + iconf * 0.4)

    return {
        "vendor_name": vendor,
        "quote_number": qn,
        "quote_date": "",
        "line_items": items,
        "subtotal": sub,
        "tax": tax,
        "total": tot,
        "notes": "",
        "confidence": {
            "overall": round(min(1.0, overall), 3),
            "vendor_name": round(vconf, 3),
            "line_items": round(iconf, 3),
            "totals": round(tconf, 3),
        },
        "parse_method": "fallback",
    }


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


def _strip_json_fence(content: str) -> str:
    s = content.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def parse_vendor_quote_with_openai(text: str) -> dict[str, Any]:
    """Structured extraction via OpenAI JSON mode."""
    client = _client()
    model = _model_name()
    user_msg = _VENDOR_QUOTE_SCHEMA_INSTRUCTIONS + "\n\n--- PDF TEXT ---\n\n" + text

    kwargs: dict[str, Any] = dict(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You extract vendor quote data from messy PDF text. Reply with JSON only.",
            },
            {"role": "user", "content": user_msg},
        ],
    )
    try:
        resp = client.chat.completions.create(
            **kwargs,
            response_format={"type": "json_object"},
        )
    except Exception:
        resp = client.chat.completions.create(**kwargs)

    content = (resp.choices[0].message.content or "").strip()
    content = _strip_json_fence(content)
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("Model returned non-object JSON")
    data["parse_method"] = "openai"
    return normalize_vendor_quote_dict(data)


def _clamp01(x: Any) -> float:
    try:
        v = float(x)
        return max(0.0, min(1.0, v))
    except (TypeError, ValueError):
        return 0.0


def normalize_vendor_quote_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize types, line items, and confidence block."""
    out: dict[str, Any] = {}
    out["vendor_name"] = str(data.get("vendor_name") or "").strip()
    out["quote_number"] = str(data.get("quote_number") or "").strip()
    out["quote_date"] = str(data.get("quote_date") or "").strip()
    out["subtotal"] = _f(data.get("subtotal"))
    out["tax"] = _f(data.get("tax"))
    out["total"] = _f(data.get("total"))
    out["notes"] = str(data.get("notes") or "").strip()

    raw_conf = data.get("confidence") if isinstance(data.get("confidence"), dict) else {}
    out["confidence"] = {
        "overall": _clamp01(raw_conf.get("overall", data.get("confidence_overall", 0.7))),
        "vendor_name": _clamp01(raw_conf.get("vendor_name", 0.5)),
        "line_items": _clamp01(raw_conf.get("line_items", 0.5)),
        "totals": _clamp01(raw_conf.get("totals", 0.5)),
    }

    lines: list[dict[str, Any]] = []
    raw_lines = data.get("line_items")
    if not isinstance(raw_lines, list):
        raw_lines = []
    for row in raw_lines:
        if not isinstance(row, dict):
            continue
        desc = str(row.get("description") or "").strip()
        if not desc:
            continue
        lines.append(
            {
                "description": desc,
                "qty": _f(row.get("qty"), 0.0),
                "unit_price": _f(row.get("unit_price"), 0.0),
                "line_total": _f(row.get("line_total"), 0.0),
            }
        )
    out["line_items"] = lines

    if out["total"] <= 0 and out["subtotal"] > 0:
        out["total"] = out["subtotal"] + out["tax"]

    if "parse_method" in data:
        out["parse_method"] = str(data["parse_method"])
    return out


def merge_openai_and_fallback(ai: dict[str, Any], fb: dict[str, Any]) -> dict[str, Any]:
    """
    Prefer high-confidence AI fields; fill gaps from fallback.
    Sets parse_method to 'merged' when both contribute.
    """
    ac = ai.get("confidence") or {}
    merged = dict(ai)
    used_fb = False

    if ac.get("vendor_name", 1) < 0.5 and fb.get("vendor_name"):
        merged["vendor_name"] = fb["vendor_name"]
        used_fb = True
    if not str(merged.get("quote_number") or "").strip() and fb.get("quote_number"):
        merged["quote_number"] = fb["quote_number"]
        used_fb = True
    if ac.get("line_items", 1) < 0.45 and len(fb.get("line_items") or []) > len(merged.get("line_items") or []):
        merged["line_items"] = fb["line_items"]
        used_fb = True
    elif ac.get("line_items", 1) < 0.4 and not merged.get("line_items") and fb.get("line_items"):
        merged["line_items"] = fb["line_items"]
        used_fb = True
    if ac.get("totals", 1) < 0.45:
        if _f(fb.get("total")) > 0 and _f(merged.get("total")) <= 0:
            merged["subtotal"] = fb["subtotal"]
            merged["tax"] = fb["tax"]
            merged["total"] = fb["total"]
            used_fb = True
        elif _f(fb.get("total")) > _f(merged.get("total")) > 0 and ac.get("totals", 0) < 0.35:
            merged["subtotal"] = fb["subtotal"]
            merged["tax"] = fb["tax"]
            merged["total"] = fb["total"]
            used_fb = True

    merged["parse_method"] = "merged" if used_fb else str(ai.get("parse_method") or "openai")
    oc = merged.get("confidence") or {}
    fb_c = fb.get("confidence") or {}
    merged["confidence"] = {
        "overall": round(max(_clamp01(oc.get("overall")), _clamp01(fb_c.get("overall"))) * (0.95 if used_fb else 1.0), 3),
        "vendor_name": max(_clamp01(oc.get("vendor_name")), _clamp01(fb_c.get("vendor_name"))),
        "line_items": max(_clamp01(oc.get("line_items")), _clamp01(fb_c.get("line_items"))),
        "totals": max(_clamp01(oc.get("totals")), _clamp01(fb_c.get("totals"))),
    }
    return merged


def compute_missing_fields(vq: dict[str, Any]) -> list[str]:
    """Human-readable list of fields that look incomplete."""
    missing: list[str] = []
    if not str(vq.get("vendor_name") or "").strip():
        missing.append("vendor_name")
    if not str(vq.get("quote_number") or "").strip():
        missing.append("quote_number")
    if not (vq.get("line_items") or []):
        missing.append("line_items")
    sub, tax, tot = _f(vq.get("subtotal")), _f(vq.get("tax")), _f(vq.get("total"))
    if tot <= 0 and sub <= 0:
        missing.append("totals")
    elif tot <= 0 and sub > 0:
        missing.append("grand_total")
    return missing


# ---------------------------------------------------------------------------
# Scope / estimate_json
# ---------------------------------------------------------------------------


def _format_scope_and_charges(vq: dict[str, Any]) -> tuple[str, str]:
    vendor = vq.get("vendor_name") or "Vendor"
    lines = vq.get("line_items") or []
    parts_scope: list[str] = [f"**Vendor quote:** {vendor}"]
    if vq.get("quote_number"):
        parts_scope.append(f"Quote #: {vq['quote_number']}")
    if vq.get("quote_date"):
        parts_scope.append(f"Date: {vq['quote_date']}")
    parts_scope.append("")
    parts_scope.append("**Line items**")
    for i, row in enumerate(lines, 1):
        parts_scope.append(
            f"{i}. {row.get('description','')} — "
            f"Qty {row.get('qty', 0):g} × "
            f"${row.get('unit_price', 0):,.2f} = "
            f"${row.get('line_total', 0):,.2f}"
        )
    scope = "\n".join(parts_scope)

    sub = _f(vq.get("subtotal"))
    tax = _f(vq.get("tax"))
    tot = _f(vq.get("total"))
    chg = [
        f"Subtotal: ${sub:,.2f}",
        f"Tax: ${tax:,.2f}",
        f"Total: ${tot:,.2f}",
    ]
    if vq.get("notes"):
        chg.append(f"Notes: {vq['notes']}")
    additional = "\n".join(chg)

    return scope, additional


def vendor_quote_to_estimate_json(vq: dict[str, Any]) -> dict[str, Any]:
    """Build estimate_json-compatible dict for Supabase."""
    scope, additional = _format_scope_and_charges(vq)
    total = _f(vq.get("total"))
    qn = str(vq.get("quote_number") or "").strip()
    conf = vq.get("confidence") or {}
    missing = compute_missing_fields(vq)

    est: dict[str, Any] = {
        "quote_number": qn,
        "customer_id": None,
        "customer_contact_id": None,
        "job_id": None,
        "status": "draft",
        "controls": {
            "material_markup_pct": 0.20,
            "overhead_pct": 0.05,
            "profit_pct": 0.15,
            "contingency_pct": 0.05,
            "sales_tax_pct": 0.00,
        },
        "materials": [],
        "labor": [],
        "equipment": [],
        "travel": {
            "round_trip_miles": 0.0,
            "mileage_rate": 0.0,
            "per_diem_per_person_per_day": 0.0,
            "hotel_nights": 0.0,
            "hotel_rate_per_room_per_night": 0.0,
        },
        "scope_of_work": scope,
        "exclusions": "",
        "additional_charges": additional,
        "customer_responsibilities": "",
        "job_received": False,
        "po_number": str(vq.get("quote_number") or "").strip(),
        "po_date": str(vq.get("quote_date") or "").strip(),
        "po_amount": total if total > 0 else 0.0,
        "import_meta": {
            "vendor_quote": True,
            "vendor_name": vq.get("vendor_name"),
            "line_items": vq.get("line_items"),
            "subtotal": vq.get("subtotal"),
            "tax": vq.get("tax"),
            "total": vq.get("total"),
            "notes": vq.get("notes"),
            "parse_confidence": conf,
            "parse_method": vq.get("parse_method", "unknown"),
            "missing_fields": missing,
        },
    }
    return est


def process_vendor_quote_pdf_bytes(raw: bytes) -> tuple[dict[str, Any], dict[str, Any], str]:
    """
    Extract text (+ tables), OpenAI parse, merge with fallback if needed, build estimate_json.

    Returns (vendor_quote_dict, estimate_json_partial, extracted_text_for_preview).
    """
    text = extract_combined_text_for_parsing(raw)
    fb = parse_vendor_quote_fallback(text)

    try:
        ai = parse_vendor_quote_with_openai(text)
        oc = ai.get("confidence") or {}
        overall = _clamp01(oc.get("overall", 0.75))
        if overall < 0.38:
            vq = normalize_vendor_quote_dict({**fb, "parse_method": "fallback"})
        else:
            vq = merge_openai_and_fallback(ai, fb)
            vq = normalize_vendor_quote_dict(vq)
    except Exception:
        vq = normalize_vendor_quote_dict(fb)

    if not str(vq.get("parse_method") or "").strip():
        vq["parse_method"] = "fallback"

    est = vendor_quote_to_estimate_json(vq)
    return vq, est, text


def render_vendor_pdf_quote_section() -> None:
    """Streamlit: vendor PDF heading + uploader (Estimates → Import)."""
    import streamlit as st

    try:
        from db import fetch_table
    except ImportError:
        from app.db import fetch_table  # type: ignore

    try:
        from pages.estimate_editor import insert_imported_estimate
    except ImportError:
        from app.pages.estimate_editor import insert_imported_estimate  # type: ignore

    st.write("PDF MODULE FILE:", __file__)
    st.write("🔥 PDF SECTION FUNCTION ACTIVE")

    with st.container(border=True):
        st.markdown("### 📄 Upload PDF Quote (Vendor)")

        st.caption("Upload a vendor quote PDF to extract estimate data")

        uploaded_file = st.file_uploader(
            "Select PDF file",
            type=["pdf"],
            key="vendor_pdf_upload",
        )

        if not uploaded_file:
            st.session_state.pop("vendor_pdf_import_sig", None)
            st.session_state.pop("vendor_pdf_import_cache", None)
        else:
            raw_bytes = uploaded_file.getvalue()
            sig = (uploaded_file.name, len(raw_bytes))
            if st.session_state.get("vendor_pdf_import_sig") != sig:
                try:
                    vq, est, extracted_text = process_vendor_quote_pdf_bytes(raw_bytes)
                    st.session_state["vendor_pdf_import_sig"] = sig
                    st.session_state["vendor_pdf_import_cache"] = {
                        "vq": vq,
                        "est": est,
                        "extracted_text": extracted_text,
                        "raw_bytes": raw_bytes,
                        "file_name": uploaded_file.name,
                    }
                except Exception as e:
                    st.session_state.pop("vendor_pdf_import_sig", None)
                    st.session_state.pop("vendor_pdf_import_cache", None)
                    st.error(f"PDF processing failed: {e}")

            cache = st.session_state.get("vendor_pdf_import_cache")
            if cache and cache.get("vq") is not None:
                vq = cache["vq"]
                est = cache["est"]
                extracted_text = cache["extracted_text"]
                raw_bytes = cache["raw_bytes"]
                file_name = cache["file_name"]

                st.markdown("### 📄 Extracted Text")
                st.text(extracted_text[:2000])

                st.markdown("### 📊 Parsed Vendor Quote")
                st.json(vq)

                st.markdown("### 🧾 Estimate Preview")
                st.json(est)

                customers = fetch_table(
                    "customers", columns="id,customer_name", limit=1000, order_by="customer_name"
                )
                selected_customer_id = None
                if customers:
                    name_to_id = {c["customer_name"]: c["id"] for c in customers}
                    names_sorted = sorted(name_to_id.keys())
                    chosen = st.selectbox(
                        "Customer for this estimate",
                        names_sorted,
                        key="vendor_pdf_save_customer",
                    )
                    selected_customer_id = name_to_id[chosen]
                else:
                    st.warning("Add a customer before saving an imported estimate.")

                if st.button("Save as Estimate", key="save_pdf_estimate"):
                    try:
                        if not selected_customer_id:
                            raise ValueError("Select a customer before saving.")
                        est_save = {**est, "customer_id": selected_customer_id}
                        estimate_id, note_suffix = insert_imported_estimate(
                            est_save,
                            file_name,
                            raw_bytes,
                            source_content_type="application/pdf",
                        )
                        msg = f"Saved estimate {estimate_id}."
                        if note_suffix:
                            msg += note_suffix
                        st.success(msg)
                        st.session_state["estimates_view"] = "list"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Save failed: {e}")

    st.markdown("---")
