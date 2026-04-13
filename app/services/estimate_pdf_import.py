"""
Extract IPS estimate-shaped data from PDF text via OpenAI (JSON output).
IPS quote PDFs often use headings like Quote #, Proposal, Scope of Work, Exclusions, etc.
"""
from __future__ import annotations

import difflib
import json
import re
from typing import Any

try:
    from config import settings
except ImportError:
    from app.config import settings  # type: ignore

from openai import OpenAI

MAX_PDF_TEXT_CHARS = 240_000

# IPS-oriented extraction: labels often appear near quote / proposal blocks.
_ESTIMATE_JSON_INSTRUCTIONS = """
You are parsing text from an IPS-style construction **quote or proposal PDF**.

Look for common patterns, including (when present):
- Quote / proposal identifiers: "Quote", "Quote #", "Quote Number", "Proposal", "Revision", "REV", "IPS"
- Customer: "Customer", "Bill To", "Sold To", "Company", "Attention", "Attn"
- Job / project: "Job", "Project", "Site", "Location", "Job Name"
- Narrative sections: "Scope of Work", "Scope", "Work Included", "Description"
- "Exclusions", "Not Included", "Additional Charges", "Alternates"
- "Customer Responsibilities", "Owner Responsibilities", "Responsibilities"
- Line items for materials, labor, equipment; mileage / travel; subtotals, tax, **Proposal Total** / **Grand Total**

Return ONE JSON object with:

A) Standard estimate fields (same keys as the IPS app estimate_json):
{
  "quote_number": "",
  "customer_id": null,
  "job_id": null,
  "status": "draft",
  "controls": { "material_markup_pct": 0.20, "overhead_pct": 0.05, "profit_pct": 0.15, "contingency_pct": 0.05, "sales_tax_pct": 0.0 },
  "materials": [ { "item": "catalog item_key or short label from PDF", "qty": 1.0 } ],
  "labor": [ { "classification": "labor class or label", "headcount": 1.0, "st_hours_per_day": 8.0, "ot_hours_per_day": 0.0, "days": 1.0 } ],
  "equipment": [ { "equipment_item": "asset name matching Asset Database → Category Equipment (for pricing)", "qty": 1.0, "basis": "Day", "duration": 1.0 } ],
  "travel": {
    "round_trip_miles": 0.0, "mileage_rate": 0.0, "per_diem_per_person_per_day": 0.0,
    "hotel_nights": 0.0, "hotel_rate_per_room_per_night": 0.0
  },
  "scope_of_work": "",
  "exclusions": "",
  "additional_charges": "",
  "customer_responsibilities": "",
  "job_received": false,
  "po_number": "",
  "po_date": "",
  "po_amount": 0.0
}

B) Extraction hints (for matching in the app — NOT database IDs unless the PDF explicitly shows a UUID):
Also include these string keys (use "" if unknown):
- "_extracted_customer_name": primary customer / company name from the document
- "_extracted_attention": attention / contact line if separate from company name
- "_extracted_job_name": job name, site, or project title from the document
- "_extracted_project": secondary project / phase label if distinct from job name

Rules:
- customer_id and job_id in the standard fields: use null unless the PDF explicitly contains a UUID matching app records.
- Prefer copying narrative text into scope_of_work / exclusions / additional_charges / customer_responsibilities verbatim when reasonable.
- For materials/labor, map lines to catalog-style keys when obvious; otherwise use concise labels from the PDF.
- For equipment, use **asset names** that match **Equipment** category assets (rental rates apply when names match).
- Equipment "basis" must be one of: Day, Week, Month.
- Numbers must be JSON numbers.
- Output valid JSON only, no markdown.
"""


def _client() -> OpenAI:
    api_key = settings.openai_api_key.strip()
    if not api_key or api_key == "your_openai_api_key":
        raise RuntimeError("OPENAI_API_KEY is missing from .env")
    return OpenAI(api_key=api_key)


def _model_name() -> str:
    return settings.openai_model.strip() or "gpt-5"


def extract_text_from_pdf_bytes(raw: bytes) -> str:
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
        raise ValueError("No extractable text in this PDF (scanned images need OCR outside this app).")
    return text[:MAX_PDF_TEXT_CHARS]


def _strip_json_fence(content: str) -> str:
    s = content.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _normalize_ids(data: dict[str, Any]) -> dict[str, Any]:
    for key in ("customer_id", "job_id"):
        v = data.get(key)
        if v is None:
            continue
        if isinstance(v, str) and v.strip().lower() in ("", "null", "none"):
            data[key] = None
            continue
        if isinstance(v, str):
            data[key] = v.strip() or None
    return data


_EXTRACTED_PREFIX = "_extracted_"


def split_pdf_extraction(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Separate `_extracted_*` hints from estimate fields (hints are not persisted in estimate_json)."""
    est: dict[str, Any] = {}
    hints: dict[str, Any] = {}
    for k, v in raw.items():
        if isinstance(k, str) and k.startswith(_EXTRACTED_PREFIX):
            hints[k] = v
        else:
            est[k] = v
    return est, hints


def normalize_pdf_estimate_fields(est: dict[str, Any]) -> dict[str, Any]:
    """Light cleanup before coalesce: whitespace, list types, travel/controls dicts."""
    out = dict(est)
    if "quote_number" in out and out["quote_number"] is not None:
        out["quote_number"] = str(out["quote_number"]).strip()
    for text_key in (
        "scope_of_work",
        "exclusions",
        "additional_charges",
        "customer_responsibilities",
        "po_number",
        "po_date",
    ):
        if text_key in out and out[text_key] is not None:
            out[text_key] = str(out[text_key]).strip()
    if not isinstance(out.get("materials"), list):
        out["materials"] = []
    if not isinstance(out.get("labor"), list):
        out["labor"] = []
    if not isinstance(out.get("equipment"), list):
        out["equipment"] = []
    trav = out.get("travel")
    if not isinstance(trav, dict):
        out["travel"] = {
            "round_trip_miles": 0.0,
            "mileage_rate": 0.0,
            "per_diem_per_person_per_day": 0.0,
            "hotel_nights": 0.0,
            "hotel_rate_per_room_per_night": 0.0,
        }
    ctrl = out.get("controls")
    if not isinstance(ctrl, dict):
        out["controls"] = {}
    return _normalize_ids(out)


def _norm_match(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def suggest_customer_and_job(
    hints: dict[str, Any],
    merged_estimate: dict[str, Any],
) -> dict[str, Any]:
    """
    Best-effort fuzzy match to customers / jobs. Does NOT modify the estimate dict.
    Returns metadata for UI; caller decides whether to apply customer_id / job_id.
    """
    try:
        from db import fetch_table
    except ImportError:
        from app.db import fetch_table  # type: ignore

    customers = fetch_table("customers", columns="id,customer_name", limit=3000, order_by="customer_name")
    jobs = fetch_table("jobs", columns="id,job_name,customer_id,job_number", limit=3000, order_by="job_number")

    cust_guess = str(hints.get("_extracted_customer_name") or "").strip()
    attn = str(hints.get("_extracted_attention") or "").strip()
    if not cust_guess and attn:
        cust_guess = attn
    combined_cust = " ".join(x for x in (cust_guess, attn) if x).strip()

    job_guess = str(hints.get("_extracted_job_name") or "").strip()
    proj = str(hints.get("_extracted_project") or "").strip()
    if not job_guess and proj:
        job_guess = proj
    combined_job = " ".join(x for x in (job_guess, proj) if x).strip()

    best_c: dict[str, Any] | None = None
    best_c_score = 0.0
    nc = _norm_match(combined_cust)
    for c in customers:
        name = str(c.get("customer_name") or "")
        if not nc:
            break
        score = difflib.SequenceMatcher(None, nc, _norm_match(name)).ratio()
        if score > best_c_score:
            best_c_score = score
            best_c = c

    sug_cust_id = str(best_c["id"]) if best_c and best_c_score >= 0.52 else None
    sug_cust_name = str(best_c["customer_name"]) if best_c else ""

    existing_cid = merged_estimate.get("customer_id")
    filter_cid = str(existing_cid) if existing_cid else (sug_cust_id if sug_cust_id else None)

    job_pool = jobs
    if filter_cid:
        filtered = [j for j in jobs if str(j.get("customer_id") or "") == filter_cid]
        if filtered:
            job_pool = filtered

    best_j: dict[str, Any] | None = None
    best_j_score = 0.0
    nj = _norm_match(combined_job)
    for j in job_pool:
        jn = str(j.get("job_name") or "")
        jnum = str(j.get("job_number") or "")
        if not nj:
            break
        candidates = [x for x in (jn, jnum, f"{jnum} {jn}".strip(), f"{jn} {jnum}".strip()) if str(x).strip()]
        if not candidates:
            continue
        score = max(difflib.SequenceMatcher(None, nj, _norm_match(c)).ratio() for c in candidates)
        if score > best_j_score:
            best_j_score = score
            best_j = j

    sug_job_id = str(best_j["id"]) if best_j and best_j_score >= 0.48 else None
    sug_job_name = str(best_j["job_name"]) if best_j else ""

    def _note(score: float, kind: str) -> str:
        if not score:
            return f"No close {kind} match in the database (similarity below threshold or missing text)."
        pct = int(round(score * 100))
        return f"Similarity ~{pct}% — review before accepting."

    return {
        "customer_guess": combined_cust or cust_guess,
        "job_guess": combined_job or job_guess,
        "suggested_customer_id": sug_cust_id,
        "suggested_customer_name": sug_cust_name,
        "customer_score": round(best_c_score, 4),
        "customer_note": _note(best_c_score, "customer") if combined_cust else "No customer text extracted from PDF.",
        "suggested_job_id": sug_job_id,
        "suggested_job_name": sug_job_name,
        "job_score": round(best_j_score, 4),
        "job_note": _note(best_j_score, "job") if combined_job else "No job / project text extracted from PDF.",
    }


def estimate_dict_from_pdf_text(text: str) -> dict[str, Any]:
    """
    Call OpenAI to turn PDF-extracted text into a dict (includes `_extracted_*` hints).
    Use split_pdf_extraction() before coalesce_imported_estimate().
    """
    client = _client()
    model = _model_name()
    user_msg = _ESTIMATE_JSON_INSTRUCTIONS + "\n\n--- DOCUMENT TEXT ---\n\n" + text

    kwargs: dict[str, Any] = dict(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract structured IPS estimate data from construction quote PDFs. "
                    "Reply with JSON only."
                ),
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
    if isinstance(data.get("estimate"), dict):
        inner = dict(data["estimate"])
        for k, v in data.items():
            if k == "estimate":
                continue
            inner.setdefault(k, v)
        data = inner
    return _normalize_ids(data)
