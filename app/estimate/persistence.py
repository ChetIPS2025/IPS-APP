from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from auth import current_profile
from db import (
    fetch_by_match_admin,
    fetch_one,
    fetch_table,
    insert_row_admin,
    next_quote_number,
    quote_number_in_use,
    update_rows_admin,
    upload_bytes,
)

from app.estimate.calculations import _D0, _q2, compute_totals, money_db
from app.estimate.defaults import (
    _apply_default_prepared_by_from_profile,
    _normalize_prepared_by_id_value,
    _payload_customer_location_for_db,
    _payload_prepared_by_for_db,
)
from app.estimate.equipment import load_estimate_equipment_from_assets


def save_revision(estimate_id: str, revision_number: int, snapshot_json: dict, note: str = "") -> None:
    insert_row_admin(
        "estimate_revisions",
        {
            "estimate_id": estimate_id,
            "revision_number": revision_number,
            "snapshot_json": snapshot_json,
            "saved_by": current_profile().get("id"),
            "change_note": note,
        },
    )


def persist_estimate(payload: dict, est: dict, revision_note: str = "") -> str:
    payload = {**payload, **_payload_prepared_by_for_db(est), **_payload_customer_location_for_db(est)}
    current_id = st.session_state.get("loaded_estimate_id")
    if current_id:
        current_row = fetch_one("estimates", {"id": current_id}, columns="revision_number")
        next_rev = int((current_row or {}).get("revision_number", 0) or 0) + 1
        payload["revision_number"] = next_rev
        update_rows_admin("estimates", payload, {"id": current_id})
        estimate_id = current_id
    else:
        payload["revision_number"] = 1
        inserted = insert_row_admin("estimates", payload)
        estimate_id = inserted.get("id")
        st.session_state["loaded_estimate_id"] = estimate_id
        next_rev = 1

    save_revision(estimate_id, next_rev, est, revision_note)
    return estimate_id


def attach_pending_pdf_import_source(estimate_id) -> None:
    """Store PDF from Estimates → PDF import when user saves (or submits) the first time."""
    pending_pdf = st.session_state.pop("estimate_pending_import_pdf", None)
    if not pending_pdf:
        return
    eid = str(estimate_id)
    safe_name = Path(pending_pdf["file_name"]).name
    storage_path = f"quotes/{eid}/imports/{safe_name}"
    upload_bytes(storage_path, pending_pdf["bytes"], "application/pdf")
    insert_row_admin(
        "attachments",
        {
            "estimate_id": eid,
            "category": "import_source",
            "file_name": safe_name,
            "storage_path": storage_path,
            "file_type": "application/pdf",
            "uploaded_by": current_profile().get("id"),
        },
    )


def upload_generated_export(estimate_id: str, file_name: str, data: bytes, content_type: str, category: str):
    storage_path = f"quotes/{estimate_id}/exports/{file_name}"
    upload_bytes(storage_path, data, content_type)
    insert_row_admin(
        "attachments",
        {
            "estimate_id": estimate_id,
            "category": category,
            "file_name": file_name,
            "storage_path": storage_path,
            "file_type": content_type,
            "uploaded_by": current_profile().get("id"),
        },
    )


def _duplicate_quote_message(quote: str, loaded_estimate_id: str | None) -> str | None:
    q = str(quote or "").strip()
    if not q:
        return None
    if quote_number_in_use(q, loaded_estimate_id):
        return (
            f"Quote number {q!r} is already used by another estimate. "
            "Enter a unique number or use Generate Quote Number."
        )
    return None


def _sanitize_estimate_json_for_storage(est: dict) -> dict:
    """Drop extraction / UI helper keys that must not be persisted on ``estimate_json``."""
    out = dict(est)
    for k in list(out.keys()):
        if isinstance(k, str) and (k.startswith("_extracted_") or k.startswith("_import_")):
            out.pop(k, None)
    return out


def validate_import_customer_id(customer_id) -> str:
    """Require a real customer row before persisting an imported estimate."""
    cid = str(customer_id or "").strip()
    if not cid:
        raise ValueError(
            "Choose a customer from your directory before saving this import. "
            "Estimates must be linked to a real customer record, not free text."
        )
    rows = fetch_by_match_admin("customers", {"id": cid}, limit=1)
    if not rows:
        raise ValueError(
            "The selected customer is not valid or could not be found. Pick a customer from the list and try again."
        )
    return cid


def insert_imported_estimate(
    est: dict,
    source_file_name: str,
    source_bytes: bytes,
    *,
    source_content_type: str = "application/json",
) -> tuple[str, str]:
    """
    Insert a new estimate row from imported JSON (or PDF processed elsewhere), revision 1, source attachment.
    Returns (estimate_id, note_suffix) where note_suffix describes quote# reassignment if any.
    """
    est = dict(est)
    materials_catalog = fetch_table("materials_catalog", limit=3000, order_by="item_key")
    labor_rates = fetch_table("labor_rates", limit=1000, order_by="classification")
    equipment_pricing = load_estimate_equipment_from_assets()
    totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
    meta = est.get("import_meta") if isinstance(est.get("import_meta"), dict) else {}
    if meta.get("vendor_quote"):
        try:
            vt = _q2(meta.get("total") or 0)
            if vt > _D0:
                totals = {
                    **totals,
                    "proposal_total": vt,
                    "final_bid": vt,
                }
        except Exception:
            pass

    qn = str(est.get("quote_number", "") or "").strip()
    note_suffix = ""
    if not qn:
        qn = next_quote_number()
        est["quote_number"] = qn
    elif quote_number_in_use(qn, None):
        old = qn
        qn = next_quote_number()
        est["quote_number"] = qn
        note_suffix = f" Quote number was {old!r} (in use); assigned {qn!r}."

    cid = validate_import_customer_id(est.get("customer_id"))
    est["customer_id"] = cid
    est.setdefault("prepared_by_id", "")
    est.setdefault("prepared_by_name", "")
    if not str(est.get("prepared_by_id") or "").strip() and not str(est.get("prepared_by_name") or "").strip():
        _apply_default_prepared_by_from_profile(est)
    est["prepared_by_id"] = _normalize_prepared_by_id_value(str(est.get("prepared_by_id") or ""))
    est_for_storage = _sanitize_estimate_json_for_storage(est)

    payload = {
        "quote_number": qn.strip(),
        "customer_id": cid,
        "customer_contact_id": est.get("customer_contact_id"),
        "job_id": est.get("job_id"),
        "estimator_user_id": current_profile().get("id"),
        "status": est.get("status", "draft"),
        "proposal_total": money_db(totals["proposal_total"]),
        "final_bid": money_db(totals["final_bid"]),
        "material_sell_basis": money_db(totals["material_sell_basis"]),
        "labor_total": money_db(totals["labor_total"]),
        "equipment_total": money_db(totals["equipment_total"]),
        "travel_total": money_db(totals["travel_total"]),
        "overhead_total": money_db(totals["overhead_total"]),
        "profit_total": money_db(totals["profit_total"]),
        "contingency_total": money_db(totals["contingency_total"]),
        "sales_tax_total": money_db(totals["sales_tax_total"]),
        "scope_of_work": est.get("scope_of_work", ""),
        "exclusions": est.get("exclusions", ""),
        "additional_charges": est.get("additional_charges", ""),
        "customer_responsibilities": est.get("customer_responsibilities", ""),
        "job_received": bool(est.get("job_received", False)),
        "po_number": est.get("po_number", ""),
        "po_date": est.get("po_date") or None,
        "po_amount": float(est.get("po_amount", 0) or 0),
        "estimate_json": est_for_storage,
        "revision_number": 1,
        "updated_at": datetime.utcnow().isoformat(),
    }
    payload.update(_payload_prepared_by_for_db(est))
    payload.update(_payload_customer_location_for_db(est))
    inserted = insert_row_admin("estimates", payload)
    estimate_id = str(inserted.get("id", ""))
    save_revision(estimate_id, 1, est_for_storage, f"Imported from {source_file_name}.{note_suffix}")

    safe_name = Path(source_file_name).name
    storage_path = f"quotes/{estimate_id}/imports/{safe_name}"
    upload_bytes(storage_path, source_bytes, source_content_type)
    insert_row_admin(
        "attachments",
        {
            "estimate_id": estimate_id,
            "category": "import_source",
            "file_name": safe_name,
            "storage_path": storage_path,
            "file_type": source_content_type,
            "uploaded_by": current_profile().get("id"),
        },
    )
    return estimate_id, note_suffix

