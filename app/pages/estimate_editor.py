from __future__ import annotations

import base64
import json
from collections import Counter
from datetime import datetime
import difflib
from pathlib import Path

import pandas as pd
import streamlit as st
from branding import render_header

from auth import current_profile, current_role
from db import (
    create_signed_url,
    fetch_by_match,
    fetch_one,
    fetch_table,
    insert_row_admin,
    next_quote_number,
    quote_number_in_use,
    update_rows_admin,
    upload_bytes,
)
from proposal import build_proposal_docx, build_proposal_pdf

try:
    from services.job_service import job_number_display, job_row_select_label
except ImportError:
    from app.services.job_service import job_number_display, job_row_select_label  # type: ignore

FINAL_STATUSES = {"approved", "awarded"}


def resolve_estimate_linked_job(
    est: dict,
    jobs: list[dict],
    loaded_estimate_id: str | None,
) -> tuple[str | None, dict | None]:
    """
    Return ``(job_id, job_row)`` when this estimate is linked to a job via ``estimate.job_id``
    or ``jobs.estimate_id``. ``job_row`` may be ``None`` if the job exists but was not in
    ``jobs`` (e.g. list capped) — caller may :func:`fetch_one` by id.
    """
    jid = est.get("job_id")
    if jid:
        sj = str(jid)
        for j in jobs:
            if str(j.get("id")) == sj:
                return sj, j
        row = fetch_one("jobs", {"id": sj}, columns="id,job_number,job_name")
        return (sj, row) if row else (sj, None)
    leid = str(loaded_estimate_id or "").strip()
    if leid:
        rows = fetch_by_match(
            "jobs",
            {"estimate_id": leid},
            columns="id,job_number,job_name",
            limit=5,
        )
        if rows:
            r = rows[0]
            return str(r.get("id")), r
    return None, None


def _is_missing_number(v) -> bool:
    return v is None or v == ""


def _num0(v) -> float:
    try:
        if _is_missing_number(v):
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def ensure_numeric_defaults(est: dict) -> dict:
    """
    Normalize estimate_json in-place (and return it):
    - only fills missing/None numeric values with 0
    - does not overwrite existing non-empty values
    - ensures required dict/list containers exist
    """
    if not isinstance(est, dict):
        return {}

    est.setdefault("controls", {})
    if not isinstance(est.get("controls"), dict):
        est["controls"] = {}
    ctrl = est["controls"]
    for k in (
        "material_markup_pct",
        "overhead_pct",
        "profit_pct",
        "contingency_pct",
        "sales_tax_pct",
    ):
        if _is_missing_number(ctrl.get(k)):
            ctrl[k] = 0.0

    est.setdefault("travel", {})
    if not isinstance(est.get("travel"), dict):
        est["travel"] = {}
    trav = est["travel"]
    for k in (
        "round_trip_miles",
        "mileage_rate",
        "per_diem_per_person_per_day",
        "hotel_nights",
        "hotel_rate_per_room_per_night",
        "airfare",
        "rental_car",
        "fuel",
        "line_total",
    ):
        if _is_missing_number(trav.get(k)):
            trav[k] = 0.0

    for list_key in ("materials", "labor", "equipment"):
        if list_key not in est or est[list_key] is None:
            est[list_key] = []
        if not isinstance(est.get(list_key), list):
            est[list_key] = []

    # Materials: support either catalog-style (item+qty) or explicit price fields.
    for row in est.get("materials", []) or []:
        if not isinstance(row, dict):
            continue
        for k in ("qty", "unit_price", "line_total"):
            if _is_missing_number(row.get(k)):
                row[k] = 0.0

    # Labor: support editor fields + generic explicit price fields.
    for row in est.get("labor", []) or []:
        if not isinstance(row, dict):
            continue
        for k in (
            "headcount",
            "st_hours_per_day",
            "ot_hours_per_day",
            "days",
            "hours",
            "rate",
            "line_total",
        ):
            if _is_missing_number(row.get(k)):
                row[k] = 0.0

    # Equipment: support editor fields + explicit rates + totals.
    for row in est.get("equipment", []) or []:
        if not isinstance(row, dict):
            continue
        for k in (
            "qty",
            "duration",
            "daily_rate",
            "weekly_rate",
            "monthly_rate",
            "line_total",
        ):
            if _is_missing_number(row.get(k)):
                row[k] = 0.0

    # Summary-like fields (some exports/imports may include these).
    for k in (
        "material_total",
        "labor_total",
        "equipment_total",
        "travel_total",
        "subtotal",
        "tax",
        "proposal_total",
        "final_bid",
        "po_amount",
    ):
        if k in est and _is_missing_number(est.get(k)):
            est[k] = 0.0

    if _is_missing_number(est.get("po_amount")):
        est["po_amount"] = 0.0

    return est


def _norm_name_key(name: str) -> str:
    return " ".join(str(name or "").strip().split()).casefold()


def _top_matches(query: str, options: list[str], *, limit: int = 8) -> list[str]:
    q = " ".join(str(query or "").strip().split())
    if not q:
        return []
    ql = q.casefold()
    scored: list[tuple[float, str]] = []
    for opt in options:
        o = " ".join(str(opt or "").strip().split())
        if not o:
            continue
        ol = o.casefold()
        score = 0.0
        if ql == ol:
            score = 10.0
        elif ql in ol:
            score = 6.0 + (len(ql) / max(1, len(ol)))
        else:
            score = difflib.SequenceMatcher(None, ql, ol).ratio()
        scored.append((score, o))
    scored.sort(key=lambda x: x[0], reverse=True)

    out: list[str] = []
    seen: set[str] = set()
    for s, o in scored:
        if len(out) >= limit:
            break
        key = _norm_name_key(o)
        if key in seen:
            continue
        if s < 0.35 and len(options) > 25:
            continue
        seen.add(key)
        out.append(o)
    return out


def create_or_get_customer_by_name(name: str) -> tuple[str | None, bool]:
    """
    Resolve a customer_id by name (case-insensitive, trimmed).
    Creates a new row when no match exists.
    Returns (customer_id, created).
    """
    nm = " ".join(str(name or "").strip().split())
    if not nm:
        return None, False
    key = _norm_name_key(nm)
    try:
        rows = fetch_table("customers", columns="id,customer_name", limit=5000, order_by="customer_name")
        for r in rows:
            if _norm_name_key(r.get("customer_name") or "") == key:
                return str(r.get("id") or ""), False
        inserted = insert_row_admin(
            "customers",
            {
                "customer_name": nm,
                "is_active": True,
            },
        )
        return str(inserted.get("id") or ""), True
    except Exception as exc:
        st.error(f"Could not create customer {nm!r}: {exc}")
        return None, False


def create_or_get_job_by_name(name: str, *, customer_id: str | None) -> tuple[str | None, bool]:
    """
    Resolve a job_id by name (case-insensitive, trimmed).
    Creates a new row when no match exists. If customer_id is provided, match is scoped to that customer.
    Returns (job_id, created).
    """
    nm = " ".join(str(name or "").strip().split())
    if not nm:
        return None, False
    if customer_id is None or str(customer_id).strip() == "":
        st.error("Customer is required to create a new job.")
        return None, False
    key = _norm_name_key(nm)
    try:
        rows = fetch_table("jobs", columns="id,job_name,customer_id", limit=5000, order_by="job_name")
        for r in rows:
            if customer_id and str(r.get("customer_id") or "") != str(customer_id):
                continue
            if _norm_name_key(r.get("job_name") or "") == key:
                return str(r.get("id") or ""), False
        payload: dict = {
            "job_name": nm,
            # Use a known Job Database status to avoid schema surprises.
            "status": "Draft",
        }
        payload["customer_id"] = customer_id
        inserted = insert_row_admin("jobs", payload)
        return str(inserted.get("id") or ""), True
    except Exception as exc:
        st.error(f"Could not create job {nm!r}: {exc}")
        return None, False


def blank_estimate() -> dict:
    return {
        "quote_number": "",
        "customer_id": None,
        "customer_contact_id": None,
        "job_id": None,
        "status": "draft",
        "controls": {
            "material_markup_pct": 0.0,
            "overhead_pct": 0.0,
            "profit_pct": 0.0,
            "contingency_pct": 0.0,
            "sales_tax_pct": 0.0,
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
            "airfare": 0.0,
            "rental_car": 0.0,
            "fuel": 0.0,
            "line_total": 0.0,
        },
        "scope_of_work": "",
        "exclusions": "",
        "additional_charges": "",
        "customer_responsibilities": "",
        "job_received": False,
        "po_number": "",
        "po_date": "",
        "po_amount": 0.0,
    }


def ensure_state():
    st.session_state.setdefault("estimate_editor_state", blank_estimate())
    st.session_state.setdefault("loaded_estimate_id", None)
    st.session_state.setdefault("estimate_editor_quote_ready", False)
    st.session_state.setdefault("est_eq_rental_only", True)
    est0 = st.session_state["estimate_editor_state"]
    ensure_numeric_defaults(est0)
    if not st.session_state.get("loaded_estimate_id"):
        qn = str(est0.get("quote_number", "") or "").strip()
        if qn:
            st.session_state["estimate_editor_quote_ready"] = True
        elif not st.session_state["estimate_editor_quote_ready"]:
            est0["quote_number"] = next_quote_number()
            st.session_state["estimate_editor_quote_ready"] = True


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


def money(v: float) -> str:
    return f"${float(v or 0):,.2f}"


def _truthy_rental(val) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("true", "1", "yes", "t")


def _safe_rate(val) -> float:
    try:
        if val is None or val == "":
            return 0.0
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def load_estimate_equipment_from_assets() -> list[dict]:
    """
    Single source of truth for estimate equipment: ``assets`` with **category** = Equipment (case-insensitive).

    Shapes rows for :func:`compute_totals` (``equipment_item``, ``daily_rate``, …) plus ``asset_id`` and ``notes``
    for linking and display. Legacy ``equipment_catalog`` table is not used.
    """
    raw = fetch_table("assets", limit=5000, order_by="asset_name")
    out: list[dict] = []
    for a in raw:
        if str(a.get("category") or "").strip().lower() != "equipment":
            continue
        name = str(a.get("asset_name") or "").strip()
        if not name:
            continue
        rn = str(a.get("rental_notes") or "").strip()
        gn = str(a.get("notes") or "").strip()
        notes = rn if rn else gn
        aid = str(a.get("id") or "").strip()
        out.append(
            {
                "equipment_item": name,
                "daily_rate": _safe_rate(a.get("rental_daily_rate")),
                "weekly_rate": _safe_rate(a.get("rental_weekly_rate")),
                "monthly_rate": _safe_rate(a.get("rental_monthly_rate")),
                "is_rental": _truthy_rental(a.get("is_rental")),
                "asset_id": aid,
                "notes": notes,
                "manufacturer": str(a.get("manufacturer") or "").strip(),
                "model": str(a.get("model") or "").strip(),
                "serial_number": str(a.get("serial_number") or "").strip(),
            }
        )
    return out


def _equipment_search_haystack(r: dict) -> str:
    return " ".join(
        [
            str(r.get("equipment_item") or ""),
            str(r.get("manufacturer") or ""),
            str(r.get("model") or ""),
            str(r.get("serial_number") or ""),
        ]
    ).lower()


def _equipment_matches_search(r: dict, search_q: str) -> bool:
    q = (search_q or "").strip().lower()
    if not q:
        return True
    hay = _equipment_search_haystack(r)
    for token in q.split():
        if token and token not in hay:
            return False
    return True


def _format_equipment_picker_label(r: dict, *, duplicate_name: bool) -> str:
    name = r["equipment_item"]
    rental_badge = " [RENTAL]" if r.get("is_rental") else ""
    d, w, m = r["daily_rate"], r["weekly_rate"], r["monthly_rate"]
    rates = f"D {money(d)} · W {money(w)} · M {money(m)}"
    mfg = str(r.get("manufacturer") or "").strip()
    mod = str(r.get("model") or "").strip()
    ser = str(r.get("serial_number") or "").strip()
    tail_bits = [x for x in [mfg, mod, ser] if x]
    tail = f" · {' · '.join(tail_bits)}" if tail_bits else ""
    base = f"{name}{rental_badge} — {rates}{tail}"
    if duplicate_name:
        aid = str(r.get("asset_id") or "").strip()
        if len(aid) >= 8:
            base = f"{base} — id:{aid[:8]}"
    return base


def build_equipment_picker_maps(
    pricing_rows: list[dict],
    *,
    rental_only: bool,
    search_query: str,
    estimate_equipment_rows: list | None,
) -> tuple[list[str], dict[str, str], dict[str, str], dict[str, str]]:
    """
    Build rich picker labels and lookups for the equipment grid.

    Returns:
        option_labels — sorted selectbox options (display strings)
        label_to_name — maps each option to canonical ``equipment_item`` (asset name)
        name_to_label — maps asset name → display label when the name is unique in the filtered set
        asset_id_to_label — maps asset id → display label (stable when names collide)
    """
    active_names: set[str] = set()
    for row in estimate_equipment_rows or []:
        ei = str(row.get("equipment_item") or "").strip()
        if ei:
            active_names.add(ei)

    filtered: list[dict] = []
    for r in pricing_rows:
        name = str(r.get("equipment_item") or "").strip()
        passes_rental = (not rental_only) or bool(r.get("is_rental"))
        keep_for_line = name in active_names
        if not passes_rental and not keep_for_line:
            continue
        if not _equipment_matches_search(r, search_query) and not keep_for_line:
            continue
        filtered.append(r)

    counts = Counter(str(r.get("equipment_item") or "") for r in filtered)
    label_to_name: dict[str, str] = {}
    name_to_label: dict[str, str] = {}
    asset_id_to_label: dict[str, str] = {}
    labels: list[str] = []

    for r in filtered:
        dup = counts[str(r.get("equipment_item") or "")] > 1
        label = _format_equipment_picker_label(r, duplicate_name=dup)
        base = label
        n = 0
        while label in label_to_name:
            n += 1
            label = f"{base} ({n})"
        labels.append(label)
        label_to_name[label] = r["equipment_item"]
        aid = str(r.get("asset_id") or "").strip()
        if aid:
            asset_id_to_label[aid] = label
        nm = str(r.get("equipment_item") or "").strip()
        if nm and counts[nm] == 1:
            name_to_label[nm] = label

    seen_names = set(label_to_name.values())
    for row in estimate_equipment_rows or []:
        ei = str(row.get("equipment_item") or "").strip()
        if ei and ei not in seen_names:
            labels.append(ei)
            label_to_name[ei] = ei
            seen_names.add(ei)

    labels_sorted = sorted(labels, key=str.casefold)
    return labels_sorted, label_to_name, name_to_label, asset_id_to_label


def enrich_equipment_rows_from_assets(
    rows: list[dict],
    pricing_rows: list[dict],
    *,
    picker_label_to_name: dict[str, str] | None = None,
) -> list[dict]:
    """
    Attach ``asset_id`` and ``equipment_notes`` when the line's ``equipment_item`` matches an Equipment asset name.
    Legacy text-only lines (no match) keep stored text; ``asset_id`` is omitted if unknown.

    ``picker_label_to_name`` maps grid cell values (rich labels) to canonical asset names when present.
    """
    by_name = {r["equipment_item"]: r for r in pricing_rows}
    lmap = picker_label_to_name or {}
    out: list[dict] = []
    for row in rows:
        r = dict(row)
        raw_cell = str(r.get("equipment_item") or "").strip()
        name = lmap.get(raw_cell, raw_cell)
        r["equipment_item"] = name
        meta = by_name.get(name)
        if meta and meta.get("asset_id"):
            r["asset_id"] = str(meta["asset_id"])
        else:
            r.pop("asset_id", None)
        if meta and meta.get("notes"):
            r["equipment_notes"] = str(meta["notes"])[:2000]
        else:
            r.pop("equipment_notes", None)
        out.append(r)
    return out


def _equipment_rows_core_for_editor(rows: list[dict] | None) -> list[dict]:
    """Only columns edited in the grid (metadata added back after save)."""
    keys = ("equipment_item", "qty", "basis", "duration")
    if not rows:
        return []
    return [{k: row.get(k) for k in keys} for row in rows]


def _equipment_core_with_picker_labels(
    rows_raw: list[dict],
    rows_core: list[dict],
    *,
    label_to_name: dict[str, str],
    name_to_label: dict[str, str],
    asset_id_to_label: dict[str, str],
) -> list[dict]:
    """Map stored canonical names / asset ids to rich selectbox labels for the current picker."""
    out: list[dict] = []
    for i, rc in enumerate(rows_core):
        rc = dict(rc)
        meta = rows_raw[i] if i < len(rows_raw) else {}
        ei = str(rc.get("equipment_item") or "").strip()
        aid = str(meta.get("asset_id") or "").strip()
        if aid and aid in asset_id_to_label:
            rc["equipment_item"] = asset_id_to_label[aid]
        elif ei in label_to_name:
            rc["equipment_item"] = ei
        elif ei in name_to_label:
            rc["equipment_item"] = name_to_label[ei]
        else:
            match = next((lab for lab, nm in label_to_name.items() if nm == ei), None)
            rc["equipment_item"] = match if match is not None else ei
        out.append(rc)
    return out


def compute_totals(est: dict, materials_catalog: list[dict], labor_rates: list[dict], equipment_pricing: list[dict]) -> dict:
    ensure_numeric_defaults(est)
    material_map = {m["item_key"]: m for m in materials_catalog}
    labor_map = {r["classification"]: r for r in labor_rates}
    equipment_map = {e["equipment_item"]: e for e in equipment_pricing}

    controls = est.get("controls", {})
    material_markup = float(controls.get("material_markup_pct", 0) or 0)
    overhead_pct = float(controls.get("overhead_pct", 0) or 0)
    profit_pct = float(controls.get("profit_pct", 0) or 0)
    contingency_pct = float(controls.get("contingency_pct", 0) or 0)
    sales_tax_pct = float(controls.get("sales_tax_pct", 0) or 0)

    material_sell_basis = 0.0
    for row in est.get("materials", []):
        item = material_map.get(row.get("item"))
        if not item:
            continue
        qty = float(row.get("qty", 0) or 0)
        purchase = float(item.get("purchase_price", 0) or 0)
        sell = float(item.get("sell_price", 0) or 0)
        base_sell = sell if sell > 0 else purchase * (1 + material_markup)
        material_sell_basis += qty * base_sell

    labor_total = 0.0
    for row in est.get("labor", []):
        item = labor_map.get(row.get("classification"))
        if not item:
            continue
        headcount = float(row.get("headcount", 0) or 0)
        st_hrs = float(row.get("st_hours_per_day", 0) or 0)
        ot_hrs = float(row.get("ot_hours_per_day", 0) or 0)
        days = float(row.get("days", 0) or 0)
        st_rate = float(item.get("st_rate", 0) or 0)
        ot_rate = float(item.get("ot_rate", 0) or 0)
        labor_total += headcount * days * ((st_hrs * st_rate) + (ot_hrs * ot_rate))

    equipment_total = 0.0
    for row in est.get("equipment", []):
        item = equipment_map.get(row.get("equipment_item"))
        if not item:
            continue
        qty = float(row.get("qty", 0) or 0)
        basis = row.get("basis", "Day")
        duration = float(row.get("duration", 0) or 0)
        rate = {
            "Day": float(item.get("daily_rate", 0) or 0),
            "Week": float(item.get("weekly_rate", 0) or 0),
            "Month": float(item.get("monthly_rate", 0) or 0),
        }.get(basis, 0.0)
        equipment_total += qty * duration * rate

    travel = est.get("travel", {})
    miles_total = _num0(travel.get("round_trip_miles")) * _num0(travel.get("mileage_rate"))
    per_diem_total = _num0(travel.get("per_diem_per_person_per_day"))
    hotel_total = _num0(travel.get("hotel_nights")) * _num0(travel.get("hotel_rate_per_room_per_night"))
    travel_total = (
        miles_total
        + per_diem_total
        + hotel_total
        + _num0(travel.get("airfare"))
        + _num0(travel.get("rental_car"))
        + _num0(travel.get("fuel"))
    )
    lt = _num0(travel.get("line_total"))
    if lt > 0 and travel_total <= 0:
        travel_total = lt

    direct_sell = material_sell_basis + labor_total + equipment_total + travel_total
    overhead_total = direct_sell * overhead_pct
    contingency_total = direct_sell * contingency_pct
    subtotal_before_profit = direct_sell + overhead_total + contingency_total
    profit_total = subtotal_before_profit * profit_pct
    sales_tax_total = material_sell_basis * sales_tax_pct
    final_bid = subtotal_before_profit + profit_total + sales_tax_total
    proposal_total = round(final_bid / 100.0) * 100.0 if final_bid else 0.0

    return {
        "material_sell_basis": material_sell_basis,
        "labor_total": labor_total,
        "equipment_total": equipment_total,
        "travel_total": travel_total,
        "overhead_total": overhead_total,
        "profit_total": profit_total,
        "contingency_total": contingency_total,
        "sales_tax_total": sales_tax_total,
        "final_bid": final_bid,
        "proposal_total": proposal_total,
    }


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


def coalesce_imported_estimate(data: dict) -> dict:
    """Merge uploaded JSON over blank_estimate() defaults."""
    base = blank_estimate()
    base.update(data)
    return base


def parse_estimate_json_bytes(raw: bytes) -> dict:
    """Parse IPS estimate JSON (raw export or wrapped)."""
    text = raw.decode("utf-8-sig")
    data = json.loads(text)
    if isinstance(data, dict):
        if "estimate_json" in data and isinstance(data["estimate_json"], dict):
            return data["estimate_json"]
        if "estimate" in data and isinstance(data["estimate"], dict):
            return data["estimate"]
    if isinstance(data, dict):
        return data
    raise ValueError("JSON root must be an object")


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
    materials_catalog = fetch_table("materials_catalog", limit=3000, order_by="item_key")
    labor_rates = fetch_table("labor_rates", limit=1000, order_by="classification")
    equipment_pricing = load_estimate_equipment_from_assets()
    totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
    meta = est.get("import_meta") if isinstance(est.get("import_meta"), dict) else {}
    if meta.get("vendor_quote"):
        try:
            vt = float(meta.get("total") or 0)
            if vt > 0:
                totals = {
                    **totals,
                    "proposal_total": vt,
                    "final_bid": vt,
                }
        except (TypeError, ValueError):
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

    if not est.get("customer_id"):
        raise ValueError("Imported estimate must include customer_id")

    payload = {
        "quote_number": qn.strip(),
        "customer_id": est.get("customer_id"),
        "customer_contact_id": est.get("customer_contact_id"),
        "job_id": est.get("job_id"),
        "estimator_user_id": current_profile().get("id"),
        "status": est.get("status", "draft"),
        "proposal_total": totals["proposal_total"],
        "final_bid": totals["final_bid"],
        "material_sell_basis": totals["material_sell_basis"],
        "labor_total": totals["labor_total"],
        "equipment_total": totals["equipment_total"],
        "travel_total": totals["travel_total"],
        "overhead_total": totals["overhead_total"],
        "profit_total": totals["profit_total"],
        "contingency_total": totals["contingency_total"],
        "sales_tax_total": totals["sales_tax_total"],
        "scope_of_work": est.get("scope_of_work", ""),
        "exclusions": est.get("exclusions", ""),
        "additional_charges": est.get("additional_charges", ""),
        "customer_responsibilities": est.get("customer_responsibilities", ""),
        "job_received": bool(est.get("job_received", False)),
        "po_number": est.get("po_number", ""),
        "po_date": est.get("po_date") or None,
        "po_amount": float(est.get("po_amount", 0) or 0),
        "estimate_json": est,
        "revision_number": 1,
        "updated_at": datetime.utcnow().isoformat(),
    }
    inserted = insert_row_admin("estimates", payload)
    estimate_id = str(inserted.get("id", ""))
    save_revision(estimate_id, 1, est, f"Imported from {source_file_name}.{note_suffix}")

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


def render_estimate_editor(*, embedded: bool = False) -> None:
    ensure_state()
    est = st.session_state["estimate_editor_state"]

    customers = fetch_table("customers", columns="id,customer_name", limit=1000, order_by="customer_name")
    jobs = fetch_table("jobs", columns="id,job_name,customer_id,job_number", limit=1000, order_by="job_number")
    materials_catalog = fetch_table("materials_catalog", limit=3000, order_by="item_key")
    labor_rates = fetch_table("labor_rates", limit=1000, order_by="classification")
    equipment_pricing = load_estimate_equipment_from_assets()
    existing_estimates = fetch_table("estimates", columns="id,quote_number,status,updated_at,revision_number", limit=1000, order_by="updated_at")

    customer_map = {c["customer_name"]: c["id"] for c in customers}
    customer_name_by_id = {c["id"]: c["customer_name"] for c in customers}
    jobs_by_customer = {}
    for j in jobs:
        jobs_by_customer.setdefault(j.get("customer_id"), []).append(j)
    materials_options = [m["item_key"] for m in materials_catalog]
    labor_options = [r["classification"] for r in labor_rates]

    if not embedded:
        render_header("Estimate Editor")
        st.caption(
            "Supabase-backed estimator logic with proposal export and approval workflow."
        )
    else:
        # Estimates page already called render_header; avoid duplicate logo/title.
        st.caption(
            "Edit estimate lines, proposal export, and approval. Use the list to open other quotes."
        )
        st.markdown('<span class="ips-estimate-editor-root"></span>', unsafe_allow_html=True)

    current_status = est.get("status", "draft")
    is_locked = current_status in FINAL_STATUSES and current_role() != "admin"
    if is_locked:
        st.warning(f"This estimate is locked because status is '{current_status}'. Admin can still edit it.")

    if not embedded:
        open_col, new_col, gen_col = st.columns([2, 1, 1])
        with open_col:
            choices = ["-- New Estimate --"] + [f'{e["quote_number"]} | {e.get("status","")} | rev {e.get("revision_number",0)}' for e in existing_estimates]
            selected_quote = st.selectbox("Open Existing Estimate", choices)
            if selected_quote != "-- New Estimate --" and st.button("Load Selected Estimate", use_container_width=True):
                selected_id = next(e["id"] for e in existing_estimates if f'{e["quote_number"]} | {e.get("status","")} | rev {e.get("revision_number",0)}' == selected_quote)
                row = fetch_one("estimates", {"id": selected_id})
                if row:
                    loaded = row.get("estimate_json") or {}
                    loaded.update({
                        "quote_number": row.get("quote_number", ""),
                        "customer_id": row.get("customer_id"),
                        "customer_contact_id": row.get("customer_contact_id"),
                        "job_id": row.get("job_id"),
                        "status": row.get("status", "draft"),
                        "scope_of_work": row.get("scope_of_work", ""),
                        "exclusions": row.get("exclusions", ""),
                        "additional_charges": row.get("additional_charges", ""),
                        "customer_responsibilities": row.get("customer_responsibilities", ""),
                        "job_received": row.get("job_received", False),
                        "po_number": row.get("po_number", ""),
                        "po_date": str(row.get("po_date") or ""),
                        "po_amount": float(row.get("po_amount", 0) or 0),
                    })
                    ensure_numeric_defaults(loaded)
                    st.session_state["estimate_editor_state"] = loaded
                    st.session_state["loaded_estimate_id"] = selected_id
                    st.session_state["estimate_editor_quote_ready"] = True
                    st.rerun()
        with new_col:
            if st.button("New Blank Estimate", use_container_width=True):
                st.session_state["estimate_editor_state"] = ensure_numeric_defaults(blank_estimate())
                st.session_state["loaded_estimate_id"] = None
                st.session_state["estimate_editor_quote_ready"] = False
                st.rerun()
        with gen_col:
            if st.button("Generate Quote Number", use_container_width=True):
                est["quote_number"] = next_quote_number()
                st.rerun()
    else:
        if st.session_state.get("estimate_pending_import_pdf"):
            st.info(
                "PDF import — edit **Materials**, **Labor**, and **Equipment** in the tabs below, "
                "then **Review / Save → Save Estimate**."
            )
        sug = st.session_state.get("estimate_pdf_suggestions") or {}
        if sug:
            st.markdown("##### PDF import — customer & job suggestions")
            st.caption(
                "Fuzzy matches from your PDF text. Nothing is saved until you **Accept** a suggestion "
                "or choose a **Customer** / **Job** below, then **Save Estimate**."
            )
            g1, g2 = st.columns(2)
            with g1:
                st.text_input(
                    "Extracted customer (from PDF)",
                    value=str(sug.get("customer_guess") or ""),
                    disabled=True,
                    key="est_pdf_guess_cust",
                )
                sid = sug.get("suggested_customer_id")
                if sid and not sug.get("customer_dismissed"):
                    st.markdown(
                        f"**Suggested customer:** {sug.get('suggested_customer_name') or ''}  \n"
                        f"{sug.get('customer_note') or ''}"
                    )
                    ac1, ac2 = st.columns(2)
                    if ac1.button("Accept customer", key="est_pdf_accept_customer"):
                        est["customer_id"] = sid
                        ns = dict(sug)
                        ns["customer_applied"] = True
                        st.session_state["estimate_pdf_suggestions"] = ns
                        st.rerun()
                    if ac2.button("Dismiss suggestion", key="est_pdf_dismiss_customer"):
                        ns = dict(sug)
                        ns["customer_dismissed"] = True
                        st.session_state["estimate_pdf_suggestions"] = ns
                        st.rerun()
                elif sid and sug.get("customer_dismissed"):
                    st.caption("Customer suggestion dismissed — use the **Customer** field below.")
                elif not sid:
                    st.caption(sug.get("customer_note") or "No customer match.")
            with g2:
                st.text_input(
                    "Extracted job / project (from PDF)",
                    value=str(sug.get("job_guess") or ""),
                    disabled=True,
                    key="est_pdf_guess_job",
                )
                jid = sug.get("suggested_job_id")
                if jid and not sug.get("job_dismissed"):
                    st.markdown(
                        f"**Suggested job:** {sug.get('suggested_job_name') or ''}  \n"
                        f"{sug.get('job_note') or ''}"
                    )
                    aj1, aj2 = st.columns(2)
                    if aj1.button("Accept job", key="est_pdf_accept_job"):
                        est["job_id"] = jid
                        ns = dict(sug)
                        ns["job_applied"] = True
                        st.session_state["estimate_pdf_suggestions"] = ns
                        st.rerun()
                    if aj2.button("Dismiss job suggestion", key="est_pdf_dismiss_job"):
                        ns = dict(sug)
                        ns["job_dismissed"] = True
                        st.session_state["estimate_pdf_suggestions"] = ns
                        st.rerun()
                elif jid and sug.get("job_dismissed"):
                    st.caption("Job suggestion dismissed — use the **Job** field below.")
                elif not jid:
                    st.caption(sug.get("job_note") or "No job match.")
        g1, g2 = st.columns([4, 1])
        with g2:
            if st.button("Generate Quote Number", use_container_width=True, key="est_embed_gen_qn"):
                est["quote_number"] = next_quote_number()
                st.rerun()

    totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Materials", money(totals["material_sell_basis"]))
    m2.metric("Labor", money(totals["labor_total"]))
    m3.metric("Equipment", money(totals["equipment_total"]))
    m4.metric("Travel", money(totals["travel_total"]))
    m5.metric("Proposal", money(totals["proposal_total"]))

    if embedded:
        _cust = customer_name_by_id.get(est.get("customer_id"), "")
        _job = next((j["job_name"] for j in jobs if j["id"] == est.get("job_id")), "")
        pdf_toolbar = build_proposal_pdf(est, totals, customer_name=_cust, job_name=_job)
        ep1, ep2, ep3 = st.columns([1, 1, 4])
        with ep1:
            if st.button("Preview Proposal", use_container_width=True, key="est_embed_preview_btn"):
                st.session_state["est_embed_pdf_preview"] = True
        with ep2:
            if st.button("Export PDF", use_container_width=True, key="est_embed_export_btn"):
                eid = st.session_state.get("loaded_estimate_id")
                if not eid:
                    st.warning("Save the estimate first (Review / Save tab) to store the PDF on this quote.")
                else:
                    upload_generated_export(
                        str(eid),
                        f"{est.get('quote_number') or 'proposal'}.pdf",
                        pdf_toolbar,
                        "application/pdf",
                        "generated_pdf",
                    )
                    st.success("PDF saved to storage and linked to this estimate.")
        if st.session_state.get("est_embed_pdf_preview"):
            with st.expander("Proposal preview", expanded=True):
                b64 = base64.b64encode(pdf_toolbar).decode()
                st.markdown(
                    f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="780px"></iframe>',
                    unsafe_allow_html=True,
                )
            if st.button("Hide preview", key="est_embed_hide_preview"):
                st.session_state["est_embed_pdf_preview"] = False
                st.rerun()

    prev_cust = st.session_state.get("_est_prev_customer_id")
    cur_cust = est.get("customer_id")
    if prev_cust is not None and cur_cust != prev_cust:
        est["customer_contact_id"] = None
    st.session_state["_est_prev_customer_id"] = cur_cust

    c1, c2, c3 = st.columns(3)
    est["quote_number"] = c1.text_input("Quote Number", value=est.get("quote_number", ""), disabled=is_locked)
    selected_customer_name = customer_name_by_id.get(est.get("customer_id"), "")
    customer_names = list(customer_map.keys())
    cust_id_by_norm = {_norm_name_key(nm): str(customer_map.get(nm) or "") for nm in customer_names}

    cust_initial = selected_customer_name or str(st.session_state.get("est_customer_query") or "")
    cust_query = c2.text_input(
        "Customer",
        value=cust_initial,
        disabled=is_locked,
        key="est_customer_query",
        placeholder="Search or type a new customer…",
        help="Type to search. If no exact match exists, a new customer will be created when you Save / Submit / Approve / Award.",
    )
    cust_norm = _norm_name_key(cust_query)
    cust_exact_id = cust_id_by_norm.get(cust_norm) if cust_norm else None
    if cust_exact_id:
        est["customer_id"] = cust_exact_id
        c2.caption("Matched existing customer.")
    elif cust_norm:
        est["customer_id"] = None
        c2.caption("New customer will be created on save.")

    cust_matches = _top_matches(cust_query, customer_names, limit=7)
    if cust_matches and not cust_exact_id:
        cust_pick = c2.selectbox(
            "Close matches",
            [""] + cust_matches,
            index=0,
            disabled=is_locked,
            key="est_customer_match_pick",
            help="Pick an existing customer to avoid creating a duplicate.",
        )
        if cust_pick:
            st.session_state["est_customer_query"] = cust_pick
            st.rerun()

    est.setdefault("customer_contact_id", None)
    if est.get("customer_id"):
        try:
            from services.customer_contacts import (
                contact_none_option_label,
                contact_option_label,
                fetch_contacts_for_customer,
                inject_contact_picker_styles,
                render_contact_detail_preview,
                render_contact_quick_add_when_empty,
            )
        except ImportError:
            from app.services.customer_contacts import (  # type: ignore
                contact_none_option_label,
                contact_option_label,
                fetch_contacts_for_customer,
                inject_contact_picker_styles,
                render_contact_detail_preview,
                render_contact_quick_add_when_empty,
            )

        inject_contact_picker_styles()
        contacts = fetch_contacts_for_customer(str(est.get("customer_id")), include_inactive=False)
        if not contacts:
            st.caption("No contacts found for this customer.")
            render_contact_quick_add_when_empty(
                customer_id=str(est.get("customer_id")),
                key_prefix="est",
                disabled=is_locked,
            )
            est["customer_contact_id"] = None
        else:
            # Default selection: keep current if valid; else primary; else only contact when exactly one.
            cur = str(est.get("customer_contact_id") or "").strip()
            by_id = {str(c.get("id") or ""): c for c in contacts}
            chosen_id: str | None = cur if cur in by_id else None
            if chosen_id is None:
                primary = next((c for c in contacts if c.get("is_primary")), None)
                if primary and primary.get("id"):
                    chosen_id = str(primary["id"])
                elif len(contacts) == 1 and contacts[0].get("id"):
                    chosen_id = str(contacts[0]["id"])

            labels = [contact_none_option_label()] + [contact_option_label(c) for c in contacts]
            ids: list[str | None] = [None] + [str(c["id"]) for c in contacts]
            try:
                idx = ids.index(str(chosen_id)) if chosen_id else 0
            except ValueError:
                idx = 0
                chosen_id = None
            idx = min(max(idx, 0), max(len(labels) - 1, 0))
            ci = st.selectbox(
                "Contact",
                options=list(range(len(labels))),
                index=idx,
                format_func=lambda i: labels[i],
                disabled=is_locked,
                key=f"est_contact_sel_{est.get('customer_id')}",
                help="Optional: contact person for this quote.",
            )
            est["customer_contact_id"] = ids[int(ci)]

            render_contact_detail_preview(by_id.get(str(est.get("customer_contact_id") or "")))
    else:
        est["customer_contact_id"] = None

    statuses = ["draft", "submitted", "approved", "awarded"]
    est["status"] = c3.selectbox("Status", statuses, index=statuses.index(est.get("status", "draft")) if est.get("status", "draft") in statuses else 0, disabled=is_locked)

    matching_jobs = jobs_by_customer.get(est.get("customer_id"), []) if est.get("customer_id") else jobs
    job_names = [str(j.get("job_name") or "").strip() for j in matching_jobs if str(j.get("job_name") or "").strip()]
    job_id_by_norm: dict[str, str] = {}
    for j in matching_jobs:
        nm = str(j.get("job_name") or "").strip()
        if not nm:
            continue
        job_id_by_norm[_norm_name_key(nm)] = str(j.get("id") or "")

    selected_job_name = next((str(j.get("job_name") or "").strip() for j in matching_jobs if j.get("id") == est.get("job_id")), "")
    job_initial = selected_job_name or str(st.session_state.get("est_job_query") or "")
    job_query = st.text_input(
        "Job",
        value=job_initial,
        disabled=is_locked,
        key="est_job_query",
        placeholder="Search or type a new job…",
        help="Type to search within the selected customer (when set). If no exact match exists, a new job will be created when you Save / Submit / Approve / Award.",
    )
    job_norm = _norm_name_key(job_query)
    job_exact_id = job_id_by_norm.get(job_norm) if job_norm else None
    if job_exact_id:
        est["job_id"] = job_exact_id
        st.caption("Matched existing job.")
    elif job_norm:
        est["job_id"] = None
        st.caption("New job will be created on save.")

    job_matches = _top_matches(job_query, job_names, limit=7)
    if job_matches and not job_exact_id:
        job_pick = st.selectbox(
            "Close matches",
            [""] + job_matches,
            index=0,
            disabled=is_locked,
            key="est_job_match_pick",
            help="Pick an existing job to avoid creating a duplicate.",
        )
        if job_pick:
            st.session_state["est_job_query"] = job_pick
            st.rerun()

    try:
        from table_actions import inject_table_action_styles
    except ImportError:
        from app.table_actions import inject_table_action_styles  # type: ignore

    inject_table_action_styles()

    _loaded_eid = str(st.session_state.get("loaded_estimate_id") or "").strip() or None
    linked_job_id, linked_job_row = resolve_estimate_linked_job(est, jobs, _loaded_eid)
    if linked_job_id and linked_job_row is None:
        linked_job_row = fetch_one("jobs", {"id": linked_job_id}, columns="id,job_number,job_name")

    if linked_job_id:
        _jn = job_number_display((linked_job_row or {}).get("job_number"))
        _jnm = str((linked_job_row or {}).get("job_name") or "").strip()
        with st.container(border=True):
            st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
            _parts = ["**Linked job**"]
            if _jn:
                _parts.append(f"**{_jn}**")
            if _jnm:
                _parts.append(_jnm)
            st.markdown(" · ".join(_parts), unsafe_allow_html=True)

    tabs = st.tabs(["Materials", "Labor", "Equipment", "Travel", "Job Scope", "Attachments / P.O.", "Proposal", "Review / Save"])

    with tabs[0]:
        rows = est.get("materials", []) or ([{"item": materials_options[0], "qty": 0.0}] if materials_options else [])
        df = pd.DataFrame(rows if rows else [{"item": "", "qty": 0.0}])
        edited = st.data_editor(
            df, num_rows="dynamic", use_container_width=True, hide_index=True, key="materials_editor_db",
            disabled=is_locked,
            column_config={
                "item": st.column_config.SelectboxColumn("Item", options=materials_options, required=True),
                "qty": st.column_config.NumberColumn("Qty", min_value=0.0, step=1.0, format="%.2f"),
            },
        )
        if "qty" in edited.columns:
            edited["qty"] = edited["qty"].fillna(0.0)
        if "item" in edited.columns:
            edited["item"] = edited["item"].fillna("")
        est["materials"] = edited.to_dict("records")

    with tabs[1]:
        rows = est.get("labor", []) or (
            [{"classification": labor_options[0], "headcount": 0.0, "st_hours_per_day": 0.0, "ot_hours_per_day": 0.0, "days": 0.0}]
            if labor_options
            else []
        )
        df = pd.DataFrame(
            rows if rows else [{"classification": "", "headcount": 0.0, "st_hours_per_day": 0.0, "ot_hours_per_day": 0.0, "days": 0.0}]
        )
        edited = st.data_editor(
            df, num_rows="dynamic", use_container_width=True, hide_index=True, key="labor_editor_db",
            disabled=is_locked,
            column_config={
                "classification": st.column_config.SelectboxColumn("Classification", options=labor_options, required=True),
                "headcount": st.column_config.NumberColumn("Headcount", min_value=0.0, step=1.0, format="%.2f"),
                "st_hours_per_day": st.column_config.NumberColumn("ST Hrs/Day", min_value=0.0, step=1.0, format="%.2f"),
                "ot_hours_per_day": st.column_config.NumberColumn("OT Hrs/Day", min_value=0.0, step=1.0, format="%.2f"),
                "days": st.column_config.NumberColumn("Days", min_value=0.0, step=1.0, format="%.2f"),
            },
        )
        for col in ("headcount", "st_hours_per_day", "ot_hours_per_day", "days"):
            if col in edited.columns:
                edited[col] = edited[col].fillna(0.0)
        if "classification" in edited.columns:
            edited["classification"] = edited["classification"].fillna("")
        est["labor"] = edited.to_dict("records")

    with tabs[2]:
        st.caption(
            "Only **Category = Equipment** assets are listed. Each row shows name, **[RENTAL]** when rent-to-customer, "
            "and D/W/M rate preview. Search matches name, manufacturer, model, or serial number."
        )
        eq_search = st.text_input(
            "Search equipment",
            key="est_eq_equipment_search",
            placeholder="Name, manufacturer, model, serial…",
            disabled=is_locked,
            help="Matches every word you type (case-insensitive). Lines already on this estimate stay available even if filtered.",
        )
        st.checkbox(
            "Show only rent-to-customer equipment",
            key="est_eq_rental_only",
            help="When checked, the picker lists only assets marked Rent to Customer. "
            "Uncheck to list all Equipment assets (rates may be zero).",
        )
        rental_only = st.session_state.get("est_eq_rental_only", True)
        rows_raw = est.get("equipment", []) or []
        option_labels, label_to_name, name_to_label, asset_id_to_label = build_equipment_picker_maps(
            equipment_pricing,
            rental_only=rental_only,
            search_query=eq_search,
            estimate_equipment_rows=est.get("equipment", []),
        )
        if not option_labels:
            st.warning(
                "No equipment assets match this filter. Add **Equipment** assets in the Asset Database, "
                "adjust search, or turn off “rent-to-customer only”."
            )
        rows_core = _equipment_rows_core_for_editor(rows_raw)
        rows_core = _equipment_core_with_picker_labels(
            rows_raw,
            rows_core,
            label_to_name=label_to_name,
            name_to_label=name_to_label,
            asset_id_to_label=asset_id_to_label,
        )
        if not rows_core and option_labels:
            rows_core = [{"equipment_item": option_labels[0], "qty": 0.0, "basis": "Day", "duration": 0.0}]
        elif not rows_core:
            rows_core = [{"equipment_item": "", "qty": 0.0, "basis": "Day", "duration": 0.0}]
        df = pd.DataFrame(rows_core if rows_core else [{"equipment_item": "", "qty": 0.0, "basis": "Day", "duration": 0.0}])
        eq_opts = option_labels if option_labels else [""]
        edited = st.data_editor(
            df, num_rows="dynamic", use_container_width=True, hide_index=True, key="equipment_editor_db",
            disabled=is_locked,
            column_config={
                "equipment_item": st.column_config.SelectboxColumn("Equipment (asset + rates)", options=eq_opts, required=True),
                "qty": st.column_config.NumberColumn("Qty", min_value=0.0, step=1.0, format="%.2f"),
                "basis": st.column_config.SelectboxColumn("Basis", options=["Day", "Week", "Month"], required=True),
                "duration": st.column_config.NumberColumn("Duration", min_value=0.0, step=1.0, format="%.2f"),
            },
        )
        for col in ("qty", "duration"):
            if col in edited.columns:
                edited[col] = edited[col].fillna(0.0)
        for col in ("equipment_item", "basis"):
            if col in edited.columns:
                edited[col] = edited[col].fillna("")
        raw_eq = edited.to_dict("records")
        est["equipment"] = enrich_equipment_rows_from_assets(
            raw_eq, equipment_pricing, picker_label_to_name=label_to_name
        )

        with st.expander("Rental rates (reference for lines above)", expanded=False):
            ref_rows = []
            for row in est.get("equipment", []) or []:
                name = str(row.get("equipment_item") or "").strip()
                if not name:
                    continue
                m = next((x for x in equipment_pricing if x["equipment_item"] == name), None)
                if m:
                    ref_rows.append(
                        {
                            "Equipment": name,
                            "Day": money(m["daily_rate"]),
                            "Week": money(m["weekly_rate"]),
                            "Month": money(m["monthly_rate"]),
                            "Rent to customer": "Yes" if m.get("is_rental") else "No",
                        }
                    )
            if ref_rows:
                st.dataframe(pd.DataFrame(ref_rows), hide_index=True, use_container_width=True)
            else:
                st.caption("Select equipment with a name that matches an Asset Database **Equipment** row to see rates.")

    with tabs[3]:
        travel = est.get("travel", {})
        tc1, tc2, tc3, tc4 = st.columns(4)
        travel["round_trip_miles"] = tc1.number_input("Round Trip Miles", min_value=0.0, value=_num0(travel.get("round_trip_miles")), step=10.0, disabled=is_locked)
        travel["mileage_rate"] = tc2.number_input("Mileage Rate", min_value=0.0, value=_num0(travel.get("mileage_rate")), step=0.1, format="%.2f", disabled=is_locked)
        travel["per_diem_per_person_per_day"] = tc3.number_input("Per Diem", min_value=0.0, value=_num0(travel.get("per_diem_per_person_per_day")), step=10.0, format="%.2f", disabled=is_locked)
        travel["hotel_nights"] = tc4.number_input("Hotel Nights", min_value=0.0, value=_num0(travel.get("hotel_nights")), step=1.0, disabled=is_locked)
        travel["hotel_rate_per_room_per_night"] = st.number_input(
            "Hotel Rate / Night",
            min_value=0.0,
            value=_num0(travel.get("hotel_rate_per_room_per_night")),
            step=10.0,
            format="%.2f",
            disabled=is_locked,
        )
        tc5, tc6, tc7, tc8 = st.columns(4)
        travel["airfare"] = tc5.number_input("Airfare", min_value=0.0, value=_num0(travel.get("airfare")), step=50.0, format="%.2f", disabled=is_locked)
        travel["rental_car"] = tc6.number_input("Rental Car", min_value=0.0, value=_num0(travel.get("rental_car")), step=50.0, format="%.2f", disabled=is_locked)
        travel["fuel"] = tc7.number_input("Fuel", min_value=0.0, value=_num0(travel.get("fuel")), step=25.0, format="%.2f", disabled=is_locked)
        travel["line_total"] = tc8.number_input("Travel Line Total (override)", min_value=0.0, value=_num0(travel.get("line_total")), step=50.0, format="%.2f", disabled=is_locked)
        est["travel"] = travel

        controls = est.get("controls", {})
        pc1, pc2, pc3, pc4, pc5 = st.columns(5)
        controls["material_markup_pct"] = pc1.number_input("Material Markup %", min_value=0.0, value=_num0(controls.get("material_markup_pct")), step=0.01, format="%.2f", disabled=is_locked)
        controls["overhead_pct"] = pc2.number_input("Overhead %", min_value=0.0, value=_num0(controls.get("overhead_pct")), step=0.01, format="%.2f", disabled=is_locked)
        controls["profit_pct"] = pc3.number_input("Profit %", min_value=0.0, value=_num0(controls.get("profit_pct")), step=0.01, format="%.2f", disabled=is_locked)
        controls["contingency_pct"] = pc4.number_input("Contingency %", min_value=0.0, value=_num0(controls.get("contingency_pct")), step=0.01, format="%.2f", disabled=is_locked)
        controls["sales_tax_pct"] = pc5.number_input("Sales Tax %", min_value=0.0, value=_num0(controls.get("sales_tax_pct")), step=0.01, format="%.2f", disabled=is_locked)
        est["controls"] = controls

    with tabs[4]:
        est["scope_of_work"] = st.text_area("Scope of Work", value=est.get("scope_of_work", ""), height=140, disabled=is_locked)
        est["exclusions"] = st.text_area("Exclusions", value=est.get("exclusions", ""), height=110, disabled=is_locked)
        est["additional_charges"] = st.text_area("Additional Charges", value=est.get("additional_charges", ""), height=110, disabled=is_locked)
        est["customer_responsibilities"] = st.text_area("Customer Responsibilities", value=est.get("customer_responsibilities", ""), height=110, disabled=is_locked)

    with tabs[5]:
        quote_files = st.file_uploader("Quote Attachments", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True, disabled=is_locked)
        est["job_received"] = st.checkbox("Job Received / Awarded", value=bool(est.get("job_received", False)), disabled=is_locked)
        pc1, pc2, pc3 = st.columns(3)
        est["po_number"] = pc1.text_input("PO Number", value=est.get("po_number", ""), disabled=is_locked)
        est["po_date"] = pc2.text_input("PO Date", value=est.get("po_date", ""), disabled=is_locked)
        est["po_amount"] = pc3.number_input("PO Amount", min_value=0.0, value=float(est.get("po_amount", 0) or 0), step=100.0, disabled=is_locked)
        po_file = st.file_uploader("PO Attachment", type=["pdf", "jpg", "jpeg", "png"], key="po_file_db", disabled=is_locked)

    with tabs[6]:
        customer_name = customer_name_by_id.get(est.get("customer_id"), "")
        job_name = next((j["job_name"] for j in jobs if j["id"] == est.get("job_id")), "")
        docx_bytes = build_proposal_docx(est, totals, customer_name=customer_name, job_name=job_name)
        pdf_bytes = build_proposal_pdf(est, totals, customer_name=customer_name, job_name=job_name)

        st.download_button(
            "Download Word Proposal",
            data=docx_bytes,
            file_name=f"{est.get('quote_number') or 'proposal'}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
        st.download_button(
            "Download PDF Proposal",
            data=pdf_bytes,
            file_name=f"{est.get('quote_number') or 'proposal'}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        if st.session_state.get("loaded_estimate_id"):
            save_export_cols = st.columns(2)
            if save_export_cols[0].button("Save Word Proposal to Supabase", use_container_width=True):
                upload_generated_export(
                    st.session_state["loaded_estimate_id"],
                    f"{est.get('quote_number') or 'proposal'}.docx",
                    docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "generated_docx",
                )
                st.success("Word proposal saved to Supabase Storage.")
            if save_export_cols[1].button("Save PDF Proposal to Supabase", use_container_width=True):
                upload_generated_export(
                    st.session_state["loaded_estimate_id"],
                    f"{est.get('quote_number') or 'proposal'}.pdf",
                    pdf_bytes,
                    "application/pdf",
                    "generated_pdf",
                )
                st.success("PDF proposal saved to Supabase Storage.")
        else:
            st.info("Save the estimate first, then you can save proposal exports to Supabase Storage.")

    with tabs[7]:
        totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Final Bid", money(totals["final_bid"]))
        rc2.metric("Overhead", money(totals["overhead_total"]))
        rc3.metric("Profit", money(totals["profit_total"]))
        rc4.metric("Sales Tax", money(totals["sales_tax_total"]))
        revision_note = st.text_input("Revision Note", value="")
        st.code(json.dumps(est, indent=2), language="json")

        customer_name = customer_name_by_id.get(est.get("customer_id"), "")
        if not est.get("quote_number", "").strip():
            st.warning("Generate or enter a Quote Number before saving.")
        elif not (customer_name or str(st.session_state.get("est_customer_query") or "").strip()):
            st.warning("Select a customer before saving.")

        save_cols = st.columns(4)
        can_save = bool(
            est.get("quote_number", "").strip()
            and (est.get("customer_id") or str(st.session_state.get("est_customer_query") or "").strip())
        )
        loaded_id = st.session_state.get("loaded_estimate_id")
        dup_msg = _duplicate_quote_message(est.get("quote_number", "").strip(), loaded_id)

        try:
            from ui import IPS_NAV_PENDING_KEY
        except ImportError:
            from app.ui import IPS_NAV_PENDING_KEY  # type: ignore

        st.markdown("##### Job from estimate")
        can_create_job_ui = current_role() in {"admin", "estimator"}
        do_create = False

        if linked_job_id:
            with st.container(border=True):
                st.markdown('<span class="ips-list-top-anchor"></span>', unsafe_allow_html=True)
                _rjn = job_number_display((linked_job_row or {}).get("job_number"))
                _rjm = str((linked_job_row or {}).get("job_name") or "").strip()
                _hdr_parts = ["**Linked job**"]
                if _rjn:
                    _hdr_parts.append(f"**{_rjn}**")
                if _rjm:
                    _hdr_parts.append(_rjm)
                st.markdown(" · ".join(_hdr_parts), unsafe_allow_html=True)
                st.caption("This estimate is already linked. Use **Open Job** to view or edit it in Job Database.")
                if can_create_job_ui:
                    if st.button("Open Job", type="primary", use_container_width=True, key="est_review_open_job"):
                        st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
                        st.session_state["job_mode"] = "edit"
                        st.session_state["job_edit_id"] = str(linked_job_id)
                        st.rerun()
        else:
            try:
                from services.job_from_estimate import (
                    create_job_from_estimate,
                    estimate_status_allows_job_creation,
                )
            except ImportError:
                from app.services.job_from_estimate import (  # type: ignore
                    create_job_from_estimate,
                    estimate_status_allows_job_creation,
                )
            create_job_disabled_reason: str | None = None
            if not loaded_id:
                create_job_disabled_reason = "Save the estimate first so it has an id in the database."
            elif not can_create_job_ui:
                create_job_disabled_reason = "Only admin or estimator can create jobs."
            elif not (est.get("customer_id") or str(st.session_state.get("est_customer_query") or "").strip()):
                create_job_disabled_reason = "Select a customer on this estimate before creating a job."
            elif not estimate_status_allows_job_creation(str(est.get("status") or "")):
                create_job_disabled_reason = (
                    "Estimate status is not allowed for job creation (see job_from_estimate settings)."
                )
            if create_job_disabled_reason:
                st.caption(create_job_disabled_reason)
            cj1, cj2, cj3 = st.columns([1, 1, 2])
            with cj1:
                do_create = st.button(
                    "Create Job from Estimate",
                    use_container_width=True,
                    disabled=bool(create_job_disabled_reason),
                    key="est_review_create_job",
                )
            with cj2:
                st.checkbox(
                    "After create, open Job Database",
                    value=True,
                    key="est_create_job_open_job_db",
                )
            with cj3:
                st.caption("Creates a new **J#####** job and links it to this quote.")

        if not linked_job_id and do_create:
            res = create_job_from_estimate(str(loaded_id))
            if res.ok and res.job:
                jid = str(res.job.get("id") or "")
                if jid:
                    est["job_id"] = jid
                st.success(res.message)
                if st.session_state.get("est_create_job_open_job_db", True) and jid and can_create_job_ui:
                    st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
                    st.session_state["job_mode"] = "edit"
                    st.session_state["job_edit_id"] = jid
                    st.rerun()
            elif res.message:
                if res.error_code == "duplicate" and res.job and res.job.get("id"):
                    est["job_id"] = str(res.job.get("id"))
                if res.error_code == "duplicate":
                    st.warning(res.message)
                else:
                    st.error(res.message)

        def _resolve_customer_job_on_commit() -> list[str]:
            msgs: list[str] = []
            # Customer
            cust_typed = " ".join(str(st.session_state.get("est_customer_query") or "").strip().split())
            if cust_typed:
                cid, created = create_or_get_customer_by_name(cust_typed)
                if cid:
                    est["customer_id"] = cid
                    if created:
                        msgs.append(f"Created new customer: {cust_typed}")
            # Job (requires customer_id when creating)
            job_typed = " ".join(str(st.session_state.get("est_job_query") or "").strip().split())
            if job_typed:
                if not est.get("customer_id"):
                    st.error("Select or type a customer before creating a new job.")
                    st.stop()
                jid, created = create_or_get_job_by_name(job_typed, customer_id=str(est.get("customer_id")))
                if jid:
                    est["job_id"] = jid
                    if created:
                        msgs.append(f"Created new job: {job_typed}")
            return msgs

        if save_cols[0].button("Save Estimate", use_container_width=True, disabled=(is_locked or not can_save)):
            if dup_msg:
                st.error(dup_msg)
            else:
                created_msgs = _resolve_customer_job_on_commit()
                totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
                payload = {
                    "quote_number": est.get("quote_number", "").strip(),
                    "customer_id": est.get("customer_id"),
                    "customer_contact_id": est.get("customer_contact_id"),
                    "job_id": est.get("job_id"),
                    "estimator_user_id": current_profile().get("id"),
                    "status": est.get("status", "draft"),
                    "proposal_total": totals["proposal_total"],
                    "final_bid": totals["final_bid"],
                    "material_sell_basis": totals["material_sell_basis"],
                    "labor_total": totals["labor_total"],
                    "equipment_total": totals["equipment_total"],
                    "travel_total": totals["travel_total"],
                    "overhead_total": totals["overhead_total"],
                    "profit_total": totals["profit_total"],
                    "contingency_total": totals["contingency_total"],
                    "sales_tax_total": totals["sales_tax_total"],
                    "scope_of_work": est.get("scope_of_work", ""),
                    "exclusions": est.get("exclusions", ""),
                    "additional_charges": est.get("additional_charges", ""),
                    "customer_responsibilities": est.get("customer_responsibilities", ""),
                    "job_received": bool(est.get("job_received", False)),
                    "po_number": est.get("po_number", ""),
                    "po_date": est.get("po_date") or None,
                    "po_amount": float(est.get("po_amount", 0) or 0),
                    "estimate_json": est,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                estimate_id = persist_estimate(payload, est, revision_note)
                attach_pending_pdf_import_source(estimate_id)
                for f in quote_files or []:
                    storage_path = f"quotes/{estimate_id}/attachments/{Path(f.name).name}"
                    upload_bytes(storage_path, f.getvalue(), f.type or "application/octet-stream")
                    insert_row_admin("attachments", {
                        "estimate_id": estimate_id,
                        "category": "quote_attachment",
                        "file_name": f.name,
                        "storage_path": storage_path,
                        "file_type": f.type or "",
                        "uploaded_by": current_profile().get("id"),
                    })
                if po_file is not None:
                    storage_path = f"quotes/{estimate_id}/po/{Path(po_file.name).name}"
                    upload_bytes(storage_path, po_file.getvalue(), po_file.type or "application/octet-stream")
                    insert_row_admin("attachments", {
                        "estimate_id": estimate_id,
                        "category": "po_attachment",
                        "file_name": po_file.name,
                        "storage_path": storage_path,
                        "file_type": po_file.type or "",
                        "uploaded_by": current_profile().get("id"),
                    })
                if created_msgs:
                    for m in created_msgs:
                        st.info(m)
                st.success("Estimate saved to Supabase.")
                st.session_state.pop("estimate_pdf_suggestions", None)

        if save_cols[1].button("Submit for Approval", use_container_width=True, disabled=(is_locked or not can_save)):
            if dup_msg:
                st.error(dup_msg)
            else:
                created_msgs = _resolve_customer_job_on_commit()
                totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
                payload = {
                    "quote_number": est.get("quote_number", "").strip(),
                    "customer_id": est.get("customer_id"),
                    "customer_contact_id": est.get("customer_contact_id"),
                    "job_id": est.get("job_id"),
                    "estimator_user_id": current_profile().get("id"),
                    "status": "submitted",
                    "proposal_total": totals["proposal_total"],
                    "final_bid": totals["final_bid"],
                    "material_sell_basis": totals["material_sell_basis"],
                    "labor_total": totals["labor_total"],
                    "equipment_total": totals["equipment_total"],
                    "travel_total": totals["travel_total"],
                    "overhead_total": totals["overhead_total"],
                    "profit_total": totals["profit_total"],
                    "contingency_total": totals["contingency_total"],
                    "sales_tax_total": totals["sales_tax_total"],
                    "scope_of_work": est.get("scope_of_work", ""),
                    "exclusions": est.get("exclusions", ""),
                    "additional_charges": est.get("additional_charges", ""),
                    "customer_responsibilities": est.get("customer_responsibilities", ""),
                    "job_received": bool(est.get("job_received", False)),
                    "po_number": est.get("po_number", ""),
                    "po_date": est.get("po_date") or None,
                    "po_amount": float(est.get("po_amount", 0) or 0),
                    "estimate_json": est,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                est["status"] = "submitted"
                eid = persist_estimate(payload, est, "Submitted for approval")
                attach_pending_pdf_import_source(eid)
                if created_msgs:
                    for m in created_msgs:
                        st.info(m)
                st.success("Estimate submitted for approval.")
                st.session_state.pop("estimate_pdf_suggestions", None)
                st.rerun()

        if save_cols[2].button("Approve", use_container_width=True, disabled=(current_role() != "admin" or not can_save)):
            if dup_msg:
                st.error(dup_msg)
            else:
                created_msgs = _resolve_customer_job_on_commit()
                totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
                payload = {
                    "quote_number": est.get("quote_number", "").strip(),
                    "customer_id": est.get("customer_id"),
                    "customer_contact_id": est.get("customer_contact_id"),
                    "job_id": est.get("job_id"),
                    "estimator_user_id": current_profile().get("id"),
                    "status": "approved",
                    "proposal_total": totals["proposal_total"],
                    "final_bid": totals["final_bid"],
                    "material_sell_basis": totals["material_sell_basis"],
                    "labor_total": totals["labor_total"],
                    "equipment_total": totals["equipment_total"],
                    "travel_total": totals["travel_total"],
                    "overhead_total": totals["overhead_total"],
                    "profit_total": totals["profit_total"],
                    "contingency_total": totals["contingency_total"],
                    "sales_tax_total": totals["sales_tax_total"],
                    "scope_of_work": est.get("scope_of_work", ""),
                    "exclusions": est.get("exclusions", ""),
                    "additional_charges": est.get("additional_charges", ""),
                    "customer_responsibilities": est.get("customer_responsibilities", ""),
                    "job_received": bool(est.get("job_received", False)),
                    "po_number": est.get("po_number", ""),
                    "po_date": est.get("po_date") or None,
                    "po_amount": float(est.get("po_amount", 0) or 0),
                    "estimate_json": est,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                est["status"] = "approved"
                eid = persist_estimate(payload, est, "Approved")
                attach_pending_pdf_import_source(eid)
                if created_msgs:
                    for m in created_msgs:
                        st.info(m)
                st.success("Estimate approved and locked.")
                st.session_state.pop("estimate_pdf_suggestions", None)
                st.rerun()

        if save_cols[3].button("Mark Awarded", use_container_width=True, disabled=(current_role() != "admin" or not can_save)):
            if dup_msg:
                st.error(dup_msg)
            else:
                created_msgs = _resolve_customer_job_on_commit()
                totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
                payload = {
                    "quote_number": est.get("quote_number", "").strip(),
                    "customer_id": est.get("customer_id"),
                    "customer_contact_id": est.get("customer_contact_id"),
                    "job_id": est.get("job_id"),
                    "estimator_user_id": current_profile().get("id"),
                    "status": "awarded",
                    "proposal_total": totals["proposal_total"],
                    "final_bid": totals["final_bid"],
                    "material_sell_basis": totals["material_sell_basis"],
                    "labor_total": totals["labor_total"],
                    "equipment_total": totals["equipment_total"],
                    "travel_total": totals["travel_total"],
                    "overhead_total": totals["overhead_total"],
                    "profit_total": totals["profit_total"],
                    "contingency_total": totals["contingency_total"],
                    "sales_tax_total": totals["sales_tax_total"],
                    "scope_of_work": est.get("scope_of_work", ""),
                    "exclusions": est.get("exclusions", ""),
                    "additional_charges": est.get("additional_charges", ""),
                    "customer_responsibilities": est.get("customer_responsibilities", ""),
                    "job_received": True,
                    "po_number": est.get("po_number", ""),
                    "po_date": est.get("po_date") or None,
                    "po_amount": float(est.get("po_amount", 0) or 0),
                    "estimate_json": est,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                est["status"] = "awarded"
                est["job_received"] = True
                eid = persist_estimate(payload, est, "Marked awarded")
                attach_pending_pdf_import_source(eid)
                if created_msgs:
                    for m in created_msgs:
                        st.info(m)
                st.success("Estimate marked awarded.")
                st.session_state.pop("estimate_pdf_suggestions", None)
                st.rerun()

        if st.session_state.get("loaded_estimate_id"):
            attachments = fetch_by_match("attachments", {"estimate_id": st.session_state["loaded_estimate_id"]}, columns="category,file_name,storage_path,uploaded_at", limit=200)
            if attachments:
                st.markdown("### Saved Files")
                for att in attachments:
                    signed = create_signed_url(att["storage_path"])
                    if signed:
                        st.markdown(f'- **{att["category"]}**: [{att["file_name"]}]({signed})')


def render() -> None:
    render_estimate_editor(embedded=False)
