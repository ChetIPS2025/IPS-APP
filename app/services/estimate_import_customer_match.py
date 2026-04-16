"""
Customer / vendor name matching for imported estimates (JSON or PDF-derived).

Pure helpers — no Streamlit. Callers render UI and pass ``chosen_label`` from a selectbox.
"""
from __future__ import annotations

import difflib
import re
from typing import Any

PLACEHOLDER = "— Select customer —"
IMPORT_CUSTOMER_CLOSE_SCORE = 0.74
IMPORT_CUSTOMER_TOP_SCORED = 40


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def extract_import_customer_vendor_hints(merged: dict[str, Any]) -> str:
    """Collect likely customer or vendor labels from import metadata and extraction hints."""
    parts: list[str] = []
    meta = merged.get("import_meta") if isinstance(merged.get("import_meta"), dict) else {}
    for key in (
        "vendor_name",
        "vendor",
        "customer_name",
        "customer",
        "bill_to",
        "sold_to",
        "company_name",
    ):
        val = meta.get(key)
        if val is not None and str(val).strip():
            parts.append(str(val).strip())
    for key in ("_extracted_customer_name", "_extracted_attention"):
        val = merged.get(key)
        if val is not None and str(val).strip():
            parts.append(str(val).strip())
    return " ".join(parts).strip()


def classify_import_customer_matches(
    merged: dict[str, Any],
    customers: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Decide how the UI should treat customer selection for one merged estimate dict.

    Returns keys:
      - resolution: valid_existing | auto_single | choose_ambiguous | choose_open | choose_required
      - customer_id: set when valid_existing or auto_single (database id string)
      - hint: combined hint text from the import
      - close_matches: list of {id, customer_name, score} with score >= threshold (may be empty)
      - scored_sample: top scored rows for messaging / ordering (each id, customer_name, score)
      - message: user-facing explanation
    """
    valid_ids = {str(c["id"]) for c in customers if c.get("id") is not None}
    hint = extract_import_customer_vendor_hints(merged)

    existing = merged.get("customer_id")
    if existing is not None and str(existing).strip():
        eid = str(existing).strip()
        if eid in valid_ids:
            name = next((str(c.get("customer_name") or "") for c in customers if str(c.get("id")) == eid), "")
            return {
                "resolution": "valid_existing",
                "customer_id": eid,
                "hint": hint,
                "close_matches": [],
                "scored_sample": [],
                "message": (
                    f"The import already includes customer **{name or eid}**. "
                    "You can keep it or choose a different customer below."
                ),
            }

    scored: list[dict[str, Any]] = []
    nh = _norm(hint)
    for c in customers:
        name = str(c.get("customer_name") or "")
        cid = str(c.get("id") or "")
        if not cid:
            continue
        score = difflib.SequenceMatcher(None, nh, _norm(name)).ratio() if nh else 0.0
        scored.append({"id": cid, "customer_name": name, "score": round(score, 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)

    close = [x for x in scored if x["score"] >= IMPORT_CUSTOMER_CLOSE_SCORE]
    sample = scored[:IMPORT_CUSTOMER_TOP_SCORED]

    if not customers:
        return {
            "resolution": "choose_required",
            "customer_id": None,
            "hint": hint,
            "close_matches": [],
            "scored_sample": [],
            "message": "No customers exist in the database yet. Add a customer before saving imports.",
        }

    if not hint:
        return {
            "resolution": "choose_required",
            "customer_id": None,
            "hint": "",
            "close_matches": [],
            "scored_sample": sample,
            "message": (
                "No customer or vendor name was found in this import. "
                f"Choose who this quote belongs to using **{PLACEHOLDER}** below."
            ),
        }

    if len(close) == 1:
        c0 = close[0]
        pct = int(round(float(c0["score"]) * 100))
        return {
            "resolution": "auto_single",
            "customer_id": c0["id"],
            "hint": hint,
            "close_matches": close,
            "scored_sample": sample,
            "message": (
                f"Import text matches **{c0['customer_name']}** (~{pct}% similarity). "
                "Review the selection below — change it if this is not the right customer."
            ),
        }

    if len(close) > 1:
        bits = ", ".join(f"{m['customer_name']} (~{int(round(float(m['score']) * 100))}%)" for m in close[:8])
        if len(close) > 8:
            bits += ", …"
        return {
            "resolution": "choose_ambiguous",
            "customer_id": None,
            "hint": hint,
            "close_matches": close,
            "scored_sample": sample,
            "message": (
                f"Several customers match **{hint!r}**: {bits}. "
                "Pick the correct customer in the list below."
            ),
        }

    best = scored[0] if scored else None
    if best and best["score"] >= 0.52:
        return {
            "resolution": "choose_open",
            "customer_id": None,
            "hint": hint,
            "close_matches": [],
            "scored_sample": sample,
            "message": (
                f"No strong automatic match for **{hint!r}** (best ~{int(round(float(best['score']) * 100))}% on "
                f"**{best['customer_name']}**). Choose the correct customer from your directory below."
            ),
        }

    return {
        "resolution": "choose_open",
        "customer_id": None,
        "hint": hint,
        "close_matches": [],
        "scored_sample": sample,
        "message": (
            f"Could not closely match **{hint!r}** to an existing customer. "
            "Select the customer this estimate should be saved under."
        ),
    }


def resolve_picked_customer_id(
    *,
    chosen_label: str | None,
    name_to_id: dict[str, str],
    placeholder: str = PLACEHOLDER,
) -> str | None:
    """
    Map the selectbox label to a customer id.

    Only a real directory name counts as selected: **placeholder** means “not chosen” and
    blocks save, even when the import metadata suggested a single match (the UI pre-fills the
    selectbox to that name instead).
    """
    if chosen_label and str(chosen_label).strip() and str(chosen_label) != placeholder:
        return name_to_id.get(str(chosen_label).strip())
    return None


def build_sorted_customer_names(customers: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {str(c.get("customer_name") or "").strip() for c in customers if str(c.get("customer_name") or "").strip()}
    )


def name_to_customer_id_map(customers: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in customers:
        n = str(c.get("customer_name") or "").strip()
        cid = str(c.get("id") or "").strip()
        if n and cid:
            out[n] = cid
    return out
