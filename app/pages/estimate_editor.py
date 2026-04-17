from __future__ import annotations

import base64
import json
import re
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
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
    fetch_by_match_admin,
    fetch_one,
    fetch_table,
    fetch_table_admin,
    fetch_table_with_order_fallback,
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


_D0 = Decimal("0")
_CENT = Decimal("0.01")


def _dec(v) -> Decimal:
    """
    Decimal-safe conversion for money math.
    - always uses Decimal(str(v)) to avoid binary float artifacts
    - treats None/"" as 0
    """
    if v is None or v == "":
        return _D0
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _q2(v) -> Decimal:
    """Quantize to cents with HALF_UP rounding."""
    return _dec(v).quantize(_CENT, rounding=ROUND_HALF_UP)


def money_db(v) -> str:
    """DB-safe numeric string with exactly 2 decimals (Postgres numeric accepts strings)."""
    return f"{_q2(v):.2f}"


def money_str(v) -> str:
    """Two decimal places, no currency symbol (for tables/captions that add their own prefix)."""
    return f"{_q2(v):.2f}"


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


def _materials_rows_for_editor(rows: list | None, *, materials_options: list[str]) -> list[dict]:
    """
    Build rows with only ``item`` + ``qty`` for ``st.data_editor``.

    Imports and legacy JSON often add ``quantity``, ``unit_price``, ``description``, etc.
    Those extra keys became extra dataframe columns, so users had to fill Qty twice
    (or fight duplicate-looking columns).
    """
    out: list[dict] = []
    for raw in rows or []:
        if not isinstance(raw, dict):
            continue
        item = raw.get("item") if raw.get("item") is not None else raw.get("item_key")
        item_s = str(item or "").strip()
        q = raw.get("qty")
        if _is_missing_number(q) and not _is_missing_number(raw.get("quantity")):
            try:
                q = float(raw.get("quantity") or 0)
            except (TypeError, ValueError):
                q = 0.0
        try:
            qf = float(q or 0)
        except (TypeError, ValueError):
            qf = 0.0
        out.append({"item": item_s, "qty": qf})
    if not out and materials_options:
        return [{"item": materials_options[0], "qty": 0.0}]
    if not out:
        return [{"item": "", "qty": 0.0}]
    return out


def _labor_rows_for_editor(rows: list | None, *, labor_options: list[str]) -> list[dict]:
    """
    Build rows with only the five labor editor columns.

    Legacy rows may include a single ``hours`` field or other keys that created
    extra columns next to ST/OT hrs per day.
    """
    keys_num = ("headcount", "st_hours_per_day", "ot_hours_per_day", "days")
    out: list[dict] = []
    for raw in rows or []:
        if not isinstance(raw, dict):
            continue
        d = {k: _num0(raw.get(k)) for k in keys_num}
        d["classification"] = str(raw.get("classification") or "").strip()
        if (
            d["headcount"] == 0.0
            and d["st_hours_per_day"] == 0.0
            and d["ot_hours_per_day"] == 0.0
            and d["days"] == 0.0
            and not _is_missing_number(raw.get("hours"))
        ):
            try:
                h = float(raw.get("hours") or 0)
            except (TypeError, ValueError):
                h = 0.0
            if h > 0.0:
                d["headcount"] = 1.0
                d["st_hours_per_day"] = h
                d["days"] = 1.0
        out.append(d)
    if not out and labor_options:
        return [
            {
                "classification": labor_options[0],
                "headcount": 0.0,
                "st_hours_per_day": 0.0,
                "ot_hours_per_day": 0.0,
                "days": 0.0,
            }
        ]
    if not out:
        return [
            {
                "classification": "",
                "headcount": 0.0,
                "st_hours_per_day": 0.0,
                "ot_hours_per_day": 0.0,
                "days": 0.0,
            }
        ]
    return out


def _norm_name_key(name: str) -> str:
    return " ".join(str(name or "").strip().split()).casefold()


def _fetch_customers_for_editor() -> list[dict]:
    """Same customer list source as the Customers tab (RLS-aware)."""
    admin_read = current_role() in {"admin", "estimator"}
    if admin_read:
        try:
            return fetch_table_admin(
                "customers",
                columns="id,customer_name",
                limit=5000,
                order_by="customer_name",
            )
        except Exception:
            return fetch_table_admin("customers", columns="id,customer_name", limit=5000, order_by=None)
    return fetch_table_with_order_fallback(
        "customers",
        columns="id,customer_name",
        limit=5000,
        order_by="customer_name",
    )


def _fetch_customer_row_by_id_for_editor(cid: str) -> dict | None:
    """Fetch a single customer row for dropdowns (admin read when the editor uses admin reads)."""
    admin_read = current_role() in {"admin", "estimator"}
    try:
        if admin_read:
            rows = fetch_by_match_admin("customers", {"id": cid}, columns="id,customer_name", limit=1)
        else:
            rows = fetch_by_match("customers", {"id": cid}, columns="id,customer_name", limit=1)
        return rows[0] if rows else None
    except Exception:
        return None


def _fetch_customer_row_for_proposal(cid: str) -> dict | None:
    """Full customer row (address fields) for proposal placeholders."""
    admin_read = current_role() in {"admin", "estimator"}
    try:
        if admin_read:
            rows = fetch_by_match_admin("customers", {"id": cid}, columns="*", limit=1)
        else:
            rows = fetch_by_match("customers", {"id": cid}, columns="*", limit=1)
        return rows[0] if rows else None
    except Exception:
        return None


def _format_customer_location_line(row: dict | None) -> str:
    """Single-line location for {{CUSTOMER_LOCATION}} (matches Customers tab field names)."""
    if not row:
        return ""

    def _first(keys: tuple[str, ...]) -> str:
        for k in keys:
            v = row.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()
        return ""

    addr = _first(("address", "street_address", "address_line1", "line1"))
    city = _first(("city",))
    state = _first(("state", "region", "province"))
    z = _first(("zip", "zip_code", "postal_code", "postcode"))
    parts: list[str] = []
    if addr:
        parts.append(addr)
    cs = ", ".join(p for p in (city, state) if p)
    if cs:
        parts.append(cs)
    if z:
        parts.append(z)
    return ", ".join(parts)


def _lookup_prepared_by_phone(est: dict) -> str:
    """Estimator phone for {{PREPARED_BY_PHONE}} when ``profiles.phone`` exists."""
    pid = _normalize_prepared_by_id_value(str(est.get("prepared_by_id") or ""))
    if not pid.startswith("p:"):
        return ""
    uid = pid[2:].strip()
    if not uid:
        return ""
    try:
        row = fetch_one("profiles", {"id": uid}, columns="id,phone")
        if row and str(row.get("phone") or "").strip():
            return str(row.get("phone") or "").strip()
    except Exception:
        pass
    return ""


def _proposal_export_kwargs(est: dict, customer_name_by_id: dict, jobs: list) -> dict:
    """Shared context for Word/PDF proposal generation (placeholders + PDF layout)."""
    cid = str(est.get("customer_id") or "").strip()
    cust_row = _fetch_customer_row_for_proposal(cid) if cid else None
    location = _format_customer_location_line(cust_row)
    cust_name = customer_name_by_id.get(cid, "") or (
        str(cust_row.get("customer_name") or "").strip() if cust_row else ""
    )
    jid = est.get("job_id")
    job_name = ""
    for j in jobs:
        if j.get("id") == jid:
            job_name = str(j.get("job_name") or "").strip()
            break
    contact_name = ""
    ccid = str(est.get("customer_contact_id") or "").strip()
    if ccid:
        try:
            crow = fetch_one("customer_contacts", {"id": ccid}, columns="id,contact_name")
            if crow:
                contact_name = str(crow.get("contact_name") or "").strip()
        except Exception:
            pass
    phone = _lookup_prepared_by_phone(est)
    return {
        "customer_name": cust_name,
        "job_name": job_name,
        "customer_location": location,
        "contact_name": contact_name,
        "prepared_by_phone": phone,
    }


def _fetch_contacts_for_estimate_editor(customer_id: str) -> list[dict]:
    """Contacts for the selected customer only; same read pattern as the Customers tab (RLS-aware)."""
    admin_read = current_role() in {"admin", "estimator"}
    cid = str(customer_id or "").strip()
    if not cid:
        return []
    try:
        if admin_read:
            rows = fetch_by_match_admin("customer_contacts", {"customer_id": cid}, limit=500)
        else:
            rows = fetch_by_match("customer_contacts", {"customer_id": cid}, limit=500)
    except Exception:
        return []
    rows = list(rows or [])
    rows = [r for r in rows if bool(r.get("is_active", True))]

    def _sort_key(r: dict) -> tuple:
        prim = 0 if r.get("is_primary") else 1
        name = str(r.get("contact_name") or "").strip().lower()
        return (prim, name)

    rows.sort(key=_sort_key)
    return rows


def _customer_dropdown_labels(rows: list[dict]) -> tuple[list[str], dict[str, str]]:
    """Return sorted customer ids and display labels (disambiguate duplicate names)."""
    valid = [r for r in rows if r.get("id")]
    by_name_lower: dict[str, list[str]] = {}
    for r in valid:
        nm = str(r.get("customer_name") or "").strip() or "(no name)"
        cid = str(r["id"])
        by_name_lower.setdefault(nm.lower(), []).append(cid)
    sorted_rows = sorted(valid, key=lambda r: str(r.get("customer_name") or "").strip().lower())
    id_to_label: dict[str, str] = {}
    for r in sorted_rows:
        cid = str(r["id"])
        nm = str(r.get("customer_name") or "").strip() or "(no name)"
        dups = by_name_lower.get(nm.lower(), [])
        label = nm if len(dups) <= 1 else f"{nm} ({cid[:8]}…)"
        id_to_label[cid] = label
    ordered_ids = [str(r["id"]) for r in sorted_rows]
    return ordered_ids, id_to_label


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
    out = {
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
        "prepared_by_id": "",
        "prepared_by_name": "",
    }
    _apply_default_prepared_by_from_profile(out)
    return out


_UUID_LOOSE = re.compile(r"^[0-9a-fA-F-]{36}$")


def _estimate_table_column_names() -> frozenset[str]:
    """Best-effort column set for ``public.estimates`` (cached per session)."""
    cache_key = "_ips_estimates_physical_columns_v1"
    cached = st.session_state.get(cache_key)
    if isinstance(cached, frozenset):
        return cached
    try:
        rows = fetch_table_admin("estimates", limit=1)
        cols = frozenset(rows[0].keys()) if rows else frozenset()
    except Exception:
        cols = frozenset()
    st.session_state[cache_key] = cols
    return cols


def _prepared_by_use_admin_fetch() -> bool:
    return current_role() in {"admin", "estimator"}


def _fetch_prepared_by_choices() -> list[tuple[str, str]]:
    """
    Roster for **Estimate Prepared By**: login profiles plus employees.

    Keys are ``p:<profile_uuid>`` or ``e:<employee_uuid>`` so references stay unambiguous.
    """
    cache_key = "_est_prepared_by_roster_v1"
    hit = st.session_state.get(cache_key)
    if isinstance(hit, list):
        return hit

    def _profiles() -> list[dict]:
        if _prepared_by_use_admin_fetch():
            return fetch_table_admin(
                "profiles",
                columns="id,full_name,email,is_active",
                limit=2000,
                order_by="full_name",
            )
        return fetch_table(
            "profiles",
            columns="id,full_name,email,is_active",
            limit=2000,
            order_by="full_name",
        )

    def _employees() -> list[dict]:
        if _prepared_by_use_admin_fetch():
            return fetch_table_admin(
                "employees",
                columns="id,name,is_active",
                limit=2000,
                order_by="name",
            )
        return fetch_table(
            "employees",
            columns="id,name,is_active",
            limit=2000,
            order_by="name",
        )

    out: list[tuple[str, str]] = []
    for p in _profiles() or []:
        if not p.get("is_active", True):
            continue
        uid = str(p.get("id") or "").strip()
        if not uid:
            continue
        nm = str(p.get("full_name") or "").strip() or str(p.get("email") or "").strip()
        label = f"{nm} (account)" if nm else uid
        out.append((f"p:{uid}", label))
    for e in _employees() or []:
        if not e.get("is_active", True):
            continue
        eid = str(e.get("id") or "").strip()
        nm = str(e.get("name") or "").strip()
        if not eid or not nm:
            continue
        out.append((f"e:{eid}", f"{nm} (employee)"))
    out.sort(key=lambda t: t[1].lower())
    st.session_state[cache_key] = out
    return out


def _normalize_prepared_by_id_value(raw: str) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    if s.startswith("p:") or s.startswith("e:"):
        return s
    if _UUID_LOOSE.match(s):
        return f"p:{s}"
    return s


def merge_estimate_row_scalar_fields_into_editor(row: dict, loaded: dict) -> None:
    """Overlay denormalized estimate row columns after ``estimate_json`` is merged."""
    if "prepared_by_name" in row:
        v = row.get("prepared_by_name")
        loaded["prepared_by_name"] = "" if v is None else str(v).strip()
    if "prepared_by_id" in row:
        v = row.get("prepared_by_id")
        loaded["prepared_by_id"] = _normalize_prepared_by_id_value("" if v is None else str(v))


def _payload_prepared_by_for_db(est: dict) -> dict:
    """Subset of ``estimates`` row fields, compatible with older schemas."""
    cols = _estimate_table_column_names()
    name = str(est.get("prepared_by_name") or "").strip()
    pid = _normalize_prepared_by_id_value(str(est.get("prepared_by_id") or "").strip())
    has_n = "prepared_by_name" in cols
    has_i = "prepared_by_id" in cols
    out: dict = {}
    if has_n and has_i:
        out["prepared_by_name"] = name[:500] if name else None
        out["prepared_by_id"] = pid[:200] if pid else None
    elif has_n:
        out["prepared_by_name"] = name[:500] if name else None
    elif has_i:
        # Single text slot: keep human-readable (name wins over opaque id).
        slot = (name or pid)[:500] if (name or pid) else None
        out["prepared_by_id"] = slot
    return out


def _apply_default_prepared_by_from_profile(est: dict) -> None:
    prof = current_profile()
    uid = str(prof.get("id") or "").strip()
    if not uid:
        return
    label = str(prof.get("full_name") or "").strip() or str(prof.get("email") or "").strip()
    if not label:
        label = uid
    est["prepared_by_id"] = f"p:{uid}"
    est["prepared_by_name"] = f"{label} (account)"


def ensure_state():
    st.session_state.setdefault("estimate_editor_state", blank_estimate())
    st.session_state.setdefault("loaded_estimate_id", None)
    st.session_state.setdefault("estimate_editor_quote_ready", False)
    st.session_state.setdefault("est_eq_rental_only", True)
    # Editing indices for line-item row-card forms (avoid re-entry / widget resets)
    st.session_state.setdefault("est_material_edit_idx", None)
    st.session_state.setdefault("est_labor_edit_idx", None)
    st.session_state.setdefault("est_equipment_edit_idx", None)
    st.session_state.setdefault("est_travel_edit_kind", None)
    # Quick-add defaults (remember last used)
    st.session_state.setdefault("est_material_last_category", "All")
    st.session_state.setdefault("est_material_last_item", "")
    st.session_state.setdefault("est_material_last_qty", 1.0)
    st.session_state.setdefault("est_labor_last_classification", "")
    st.session_state.setdefault("est_labor_last_headcount", 1.0)
    st.session_state.setdefault("est_labor_last_st_hours", 8.0)
    st.session_state.setdefault("est_labor_last_ot_hours", 0.0)
    st.session_state.setdefault("est_labor_last_days", 1.0)
    st.session_state.setdefault("est_equipment_last_item", "")
    st.session_state.setdefault("est_equipment_last_qty", 1.0)
    st.session_state.setdefault("est_equipment_last_basis", "Day")
    st.session_state.setdefault("est_equipment_last_duration", 1.0)
    st.session_state.setdefault("est_travel_last_kind", "Mileage")
    st.session_state.setdefault("est_travel_last_amount", 0.0)
    st.session_state.setdefault("est_travel_last_miles", 0.0)
    st.session_state.setdefault("est_travel_last_mileage_rate", 0.0)
    st.session_state.setdefault("est_travel_last_hotel_nights", 0.0)
    st.session_state.setdefault("est_travel_last_hotel_rate", 0.0)
    # Pending uploads (kept stable across reruns; uploaded on Save)
    st.session_state.setdefault("est_pending_quote_attachments", [])
    st.session_state.setdefault("est_pending_po_attachment", None)
    st.session_state.setdefault("est_revision_note", "")
    est0 = st.session_state["estimate_editor_state"]
    # Legacy widget keys from the old free-text customer field (avoid stale session state).
    st.session_state.pop("est_customer_query", None)
    st.session_state.pop("est_customer_match_pick", None)
    # Defensive defaults: some imported legacy payloads may omit keys or set them to null.
    est0.setdefault("materials", [])
    est0.setdefault("labor", [])
    est0.setdefault("equipment", [])
    est0.setdefault("travel", {})
    est0.setdefault("controls", {})
    ensure_numeric_defaults(est0)
    est0.setdefault("prepared_by_id", "")
    est0.setdefault("prepared_by_name", "")
    est0["prepared_by_id"] = _normalize_prepared_by_id_value(str(est0.get("prepared_by_id") or ""))
    # Quote numbers must never change on rerun. We only allocate a new number at commit time
    # (Save / Submit / Approve / Award) for brand-new estimates when quote_number is blank.
    qn = str(est0.get("quote_number", "") or "").strip()
    st.session_state["estimate_editor_quote_ready"] = bool(qn)


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


def money(v) -> str:
    """Display formatter: always 2 decimals, comma grouped."""
    return f"${_q2(v):,.2f}"


def _truthy_rental(val) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("true", "1", "yes", "t")


def _safe_rate(val) -> Decimal:
    try:
        if val is None or val == "":
            return _D0
        return _dec(val)
    except Exception:
        return _D0


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
    material_markup = _dec(controls.get("material_markup_pct", 0) or 0)
    overhead_pct = _dec(controls.get("overhead_pct", 0) or 0)
    profit_pct = _dec(controls.get("profit_pct", 0) or 0)
    contingency_pct = _dec(controls.get("contingency_pct", 0) or 0)
    sales_tax_pct = _dec(controls.get("sales_tax_pct", 0) or 0)

    material_sell_basis = _D0
    for row in est.get("materials", []):
        item = material_map.get(row.get("item"))
        if not item:
            continue
        qty = _dec(row.get("qty", 0) or 0)
        purchase = _dec(item.get("purchase_price", 0) or 0)
        sell = _dec(item.get("sell_price", 0) or 0)
        base_sell = sell if sell > _D0 else purchase * (Decimal("1") + material_markup)
        material_sell_basis += qty * base_sell

    labor_total = _D0
    for row in est.get("labor", []):
        item = labor_map.get(row.get("classification"))
        if not item:
            continue
        headcount = _dec(row.get("headcount", 0) or 0)
        st_hrs = _dec(row.get("st_hours_per_day", 0) or 0)
        ot_hrs = _dec(row.get("ot_hours_per_day", 0) or 0)
        days = _dec(row.get("days", 0) or 0)
        st_rate = _dec(item.get("st_rate", 0) or 0)
        ot_rate = _dec(item.get("ot_rate", 0) or 0)
        labor_total += headcount * days * ((st_hrs * st_rate) + (ot_hrs * ot_rate))

    equipment_total = _D0
    for row in est.get("equipment", []):
        item = equipment_map.get(row.get("equipment_item"))
        if not item:
            continue
        qty = _dec(row.get("qty", 0) or 0)
        basis = row.get("basis", "Day")
        duration = _dec(row.get("duration", 0) or 0)
        rate = {
            "Day": _dec(item.get("daily_rate", 0) or 0),
            "Week": _dec(item.get("weekly_rate", 0) or 0),
            "Month": _dec(item.get("monthly_rate", 0) or 0),
        }.get(basis, _D0)
        equipment_total += qty * duration * rate

    travel = est.get("travel", {})
    miles_total = _dec(travel.get("round_trip_miles")) * _dec(travel.get("mileage_rate"))
    per_diem_total = _dec(travel.get("per_diem_per_person_per_day"))
    hotel_total = _dec(travel.get("hotel_nights")) * _dec(travel.get("hotel_rate_per_room_per_night"))
    travel_total = (
        miles_total
        + per_diem_total
        + hotel_total
        + _dec(travel.get("airfare"))
        + _dec(travel.get("rental_car"))
        + _dec(travel.get("fuel"))
    )
    lt = _dec(travel.get("line_total"))
    if lt > _D0 and travel_total <= _D0:
        travel_total = lt

    direct_sell = material_sell_basis + labor_total + equipment_total + travel_total
    overhead_total = direct_sell * overhead_pct
    contingency_total = direct_sell * contingency_pct
    subtotal_before_profit = direct_sell + overhead_total + contingency_total
    profit_total = subtotal_before_profit * profit_pct
    sales_tax_total = material_sell_basis * sales_tax_pct
    final_bid = subtotal_before_profit + profit_total + sales_tax_total
    final_bid_q = _q2(final_bid)
    # Proposal total matches final bid (cent-quantized); no rounding to whole dollars.
    proposal_total = final_bid_q

    return {
        "material_sell_basis": _q2(material_sell_basis),
        "labor_total": _q2(labor_total),
        "equipment_total": _q2(equipment_total),
        "travel_total": _q2(travel_total),
        "overhead_total": _q2(overhead_total),
        "profit_total": _q2(profit_total),
        "contingency_total": _q2(contingency_total),
        "sales_tax_total": _q2(sales_tax_total),
        "final_bid": final_bid_q,
        "proposal_total": _q2(proposal_total),
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
    payload = {**payload, **_payload_prepared_by_for_db(est)}
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


_PREP_NONE = "__prep_none__"
_LEGACY_UNLISTED = "__legacy_unlisted__"


def _render_estimate_prepared_by_field(est: dict, *, is_locked: bool) -> None:
    """Compact select for **Estimate Prepared By** (profiles + employees)."""
    roster = _fetch_prepared_by_choices()
    label_by_key: dict[str, str] = {_PREP_NONE: "—"}
    for k, lab in roster:
        label_by_key[k] = lab
    keys: list[str] = [_PREP_NONE] + [k for k, _ in roster]

    cur_id = _normalize_prepared_by_id_value(str(est.get("prepared_by_id") or "").strip())
    cur_name = str(est.get("prepared_by_name") or "").strip()

    if cur_id and cur_id not in label_by_key:
        keys.insert(1, cur_id)
        label_by_key[cur_id] = cur_name or cur_id or "(saved preparer)"
    if not cur_id and cur_name:
        keys.insert(1, _LEGACY_UNLISTED)
        label_by_key[_LEGACY_UNLISTED] = cur_name

    if cur_id and cur_id in label_by_key:
        sel = cur_id
    elif cur_id:
        sel = cur_id
    elif cur_name:
        sel = _LEGACY_UNLISTED
    else:
        sel = _PREP_NONE

    try:
        default_idx = keys.index(sel)
    except ValueError:
        default_idx = 0

    chosen = st.selectbox(
        "Estimate Prepared By",
        options=keys,
        index=min(default_idx, len(keys) - 1),
        format_func=lambda k: label_by_key.get(k, k),
        disabled=is_locked,
        key="est_prepared_by_select_main",
        help="Shown on proposals and reports. Pulled from Users (profiles) and Employees.",
    )
    if chosen == _PREP_NONE:
        est["prepared_by_id"] = ""
        est["prepared_by_name"] = ""
    elif chosen == _LEGACY_UNLISTED:
        est["prepared_by_id"] = ""
        est["prepared_by_name"] = cur_name
    else:
        est["prepared_by_id"] = chosen
        est["prepared_by_name"] = str(label_by_key.get(chosen, "") or "").strip()


def _imported_estimate_missing_customer(est: dict, *, pending_pdf_import: bool) -> bool:
    """True when editor state is an import that still needs a real ``customer_id``."""
    if est.get("customer_id"):
        return False
    if pending_pdf_import:
        return True
    meta = est.get("import_meta") if isinstance(est.get("import_meta"), dict) else {}
    if meta.get("vendor_quote"):
        return True
    return False


def render_estimate_editor(*, embedded: bool = False) -> None:
    ensure_state()
    est = st.session_state["estimate_editor_state"]

    customers = _fetch_customers_for_editor()
    cur_cust_id = str(est.get("customer_id") or "").strip()
    ids_have = {str(c["id"]) for c in customers if c.get("id")}
    if cur_cust_id and cur_cust_id not in ids_have:
        extra = _fetch_customer_row_by_id_for_editor(cur_cust_id)
        if extra and extra.get("id"):
            customers = [extra] + list(customers)
        elif cur_cust_id:
            customers = [
                {"id": cur_cust_id, "customer_name": "[Customer not found — check Customers tab]"},
            ] + list(customers)

    jobs = fetch_table("jobs", columns="id,job_name,customer_id,job_number", limit=1000, order_by="job_number")
    materials_catalog = fetch_table("materials_catalog", limit=3000, order_by="item_key")
    labor_rates = fetch_table("labor_rates", limit=1000, order_by="classification")
    equipment_pricing = load_estimate_equipment_from_assets()
    existing_estimates = fetch_table("estimates", columns="id,quote_number,status,updated_at,revision_number", limit=1000, order_by="updated_at")

    customer_name_by_id = {str(c["id"]): str(c.get("customer_name") or "").strip() for c in customers if c.get("id")}
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
                    merge_estimate_row_scalar_fields_into_editor(row, loaded)
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
            can_generate_qn = not st.session_state.get("loaded_estimate_id") and not str(
                est.get("quote_number", "") or ""
            ).strip()
            if st.button("Generate Quote Number", use_container_width=True, disabled=not can_generate_qn):
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
            can_generate_qn = not st.session_state.get("loaded_estimate_id") and not str(
                est.get("quote_number", "") or ""
            ).strip()
            if st.button(
                "Generate Quote Number",
                use_container_width=True,
                key="est_embed_gen_qn",
                disabled=not can_generate_qn,
            ):
                est["quote_number"] = next_quote_number()
                st.rerun()

    totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
    m1, m2, m3, m4, m5 = st.columns(5, gap="small")
    m1.metric("Materials", money(totals["material_sell_basis"]))
    m2.metric("Labor", money(totals["labor_total"]))
    m3.metric("Equipment", money(totals["equipment_total"]))
    m4.metric("Travel", money(totals["travel_total"]))
    m5.metric("Proposal", money(totals["proposal_total"]))

    if embedded:
        _pe = _proposal_export_kwargs(est, customer_name_by_id, jobs)
        pdf_toolbar = build_proposal_pdf(est, totals, **_pe)
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

    if _imported_estimate_missing_customer(
        est,
        pending_pdf_import=bool(st.session_state.get("estimate_pending_import_pdf")),
    ):
        st.warning(
            "This imported estimate is not linked to a customer yet. "
            "Select a saved customer from the list below (add one in the **Customers** tab if needed), then save."
        )

    # Row 1: Quote | Status | Customer — single compact row (no full-width fields).
    q_col, stat_col, cust_col = st.columns([0.9, 1.0, 2.5], gap="small")
    quote_locked_after_save = bool(
        str(st.session_state.get("loaded_estimate_id") or "").strip()
        and str(est.get("quote_number", "") or "").strip()
    )
    with q_col:
        est["quote_number"] = st.text_input(
            "Quote Number",
            value=est.get("quote_number", ""),
            disabled=(is_locked or quote_locked_after_save),
        )
        if quote_locked_after_save and not is_locked:
            st.caption("Locked after first save.")

    with stat_col:
        statuses = ["draft", "submitted", "approved", "awarded"]
        est["status"] = st.selectbox(
            "Status",
            statuses,
            index=statuses.index(est.get("status", "draft")) if est.get("status", "draft") in statuses else 0,
            disabled=is_locked,
        )

    with cust_col:
        _EMPTY_CUSTOMER = "__est_no_customer__"
        rows_for_ui = [r for r in customers if r.get("id")]
        if not rows_for_ui:
            st.warning(
                "No customers in the database. Add a customer from the **Customers** tab, then return here and select it."
            )
            if not is_locked:
                est["customer_id"] = None
        else:
            ordered_ids, id_to_label = _customer_dropdown_labels(rows_for_ui)
            options = [_EMPTY_CUSTOMER] + ordered_ids

            def _fmt_customer(cid: str) -> str:
                if cid == _EMPTY_CUSTOMER:
                    return "— Select customer —"
                return id_to_label.get(cid, cid)

            cur_sel = str(est.get("customer_id") or "").strip()
            default_idx = options.index(cur_sel) if cur_sel in options else 0
            sel = st.selectbox(
                "Customer",
                options=options,
                index=default_idx,
                format_func=_fmt_customer,
                disabled=is_locked,
                key="est_customer_select_id",
                help="Only saved customers from the Customers tab. Add new companies there first.",
            )
            if sel == _EMPTY_CUSTOMER:
                if not is_locked:
                    est["customer_id"] = None
            else:
                est["customer_id"] = sel

    # After customer is chosen: clear contact when customer changes (same run as the selectbox).
    prev_cust = st.session_state.get("_est_prev_customer_id")
    cur_cust = est.get("customer_id")
    if prev_cust is not None and cur_cust != prev_cust:
        est["customer_contact_id"] = None
    st.session_state["_est_prev_customer_id"] = cur_cust

    matching_jobs = jobs_by_customer.get(est.get("customer_id"), []) if est.get("customer_id") else jobs
    job_names = [str(j.get("job_name") or "").strip() for j in matching_jobs if str(j.get("job_name") or "").strip()]
    job_id_by_norm: dict[str, str] = {}
    for j in matching_jobs:
        nm = str(j.get("job_name") or "").strip()
        if not nm:
            continue
        job_id_by_norm[_norm_name_key(nm)] = str(j.get("id") or "")

    # Row 2: Contact | Job | Prepared by — second compact row.
    row2_contact, row2_job, row2_prep = st.columns([1, 1.15, 1.1], gap="small")
    est.setdefault("customer_contact_id", None)
    with row2_contact:
        if est.get("customer_id"):
            try:
                from services.customer_contacts import (
                    contact_none_option_label,
                    contact_option_label,
                    inject_contact_picker_styles,
                    render_contact_detail_preview,
                    render_contact_quick_add_when_empty,
                )
            except ImportError:
                from app.services.customer_contacts import (  # type: ignore
                    contact_none_option_label,
                    contact_option_label,
                    inject_contact_picker_styles,
                    render_contact_detail_preview,
                    render_contact_quick_add_when_empty,
                )

            inject_contact_picker_styles()
            cid_key = str(est.get("customer_id") or "").strip()
            contacts = _fetch_contacts_for_estimate_editor(cid_key)
            if not contacts:
                st.caption("No contacts found for this customer.")
                st.selectbox(
                    "Contact",
                    options=[0],
                    index=0,
                    format_func=lambda _: contact_none_option_label(),
                    disabled=is_locked,
                    key=f"est_contact_sel_empty_{cid_key}",
                    help="Optional: add contacts for this customer on the Customers tab.",
                )
                est["customer_contact_id"] = None
                render_contact_quick_add_when_empty(
                    customer_id=cid_key,
                    key_prefix="est",
                    disabled=is_locked,
                )
            else:
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
                    idx = ids.index(chosen_id) if chosen_id is not None else 0
                except ValueError:
                    idx = 0
                idx = min(max(idx, 0), len(labels) - 1)
                ci = st.selectbox(
                    "Contact",
                    options=list(range(len(labels))),
                    index=idx,
                    format_func=lambda i: labels[i],
                    disabled=is_locked,
                    key=f"est_contact_sel_{cid_key}",
                    help="Only contacts linked to the selected customer. Optional for this quote.",
                )
                est["customer_contact_id"] = ids[int(ci)]

                render_contact_detail_preview(by_id.get(str(est.get("customer_contact_id") or "")))
        else:
            st.caption("Select a customer to choose a contact.")
            est["customer_contact_id"] = None

    with row2_job:
        selected_job_name = next(
            (str(j.get("job_name") or "").strip() for j in matching_jobs if j.get("id") == est.get("job_id")), ""
        )
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

    with row2_prep:
        _render_estimate_prepared_by_field(est, is_locked=is_locked)

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
        # Materials row cards + form-based add/edit to avoid "enter twice" UX.
        est.setdefault("materials", [])
        controls = est.get("controls", {}) or {}
        material_markup_dec = _dec(controls.get("material_markup_pct", 0) or 0)
        material_map = {m.get("item_key"): m for m in materials_catalog if isinstance(m, dict) and m.get("item_key")}

        # Optional category filter (resilient to schema differences).
        categories = sorted(
            {
                str(m.get("category") or "").strip()
                for m in materials_catalog
                if isinstance(m, dict) and str(m.get("category") or "").strip()
            }
        )
        cat_options = ["All"] + categories if categories else ["All"]

        st.caption("Category (narrow) → material → qty → add.")

        with st.form(key="est_material_add_form", clear_on_submit=True):
            # Remember last-used category when available.
            last_cat = str(st.session_state.get("est_material_last_category") or "All")
            cat_index = cat_options.index(last_cat) if last_cat in cat_options else 0
            ma1, ma2, ma3, ma4 = st.columns([0.65, 2.35, 0.4, 0.45], gap="small")
            with ma1:
                selected_cat = st.selectbox(
                    "Category",
                    options=cat_options,
                    index=cat_index,
                    disabled=is_locked,
                    key="est_material_add_category",
                    help="Optional filter. If your materials table has no category column, this stays as All.",
                )

            if selected_cat != "All":
                filtered_items = [
                    str(m.get("item_key") or "").strip()
                    for m in materials_catalog
                    if isinstance(m, dict)
                    and str(m.get("item_key") or "").strip()
                    and str(m.get("category") or "").strip() == selected_cat
                ]
            else:
                filtered_items = materials_options
            filtered_items = [x for x in filtered_items if x]
            if not filtered_items:
                filtered_items = [""]

            last_item = str(st.session_state.get("est_material_last_item") or "").strip()
            item_index = filtered_items.index(last_item) if last_item in filtered_items else 0
            with ma2:
                mat_add_item = st.selectbox(
                    "Material",
                    options=filtered_items,
                    index=item_index,
                    disabled=is_locked,
                    key="est_material_add_item",
                )
            with ma3:
                mat_add_qty = st.number_input(
                    "Qty",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_material_last_qty") or 1.0),
                    key="est_material_add_qty",
                )
            with ma4:
                st.markdown("")
                mat_add_submit = st.form_submit_button("Add", disabled=is_locked)

            if mat_add_submit:
                if not str(mat_add_item or "").strip():
                    st.error("Select a Material.")
                    st.stop()
                st.session_state["est_material_last_category"] = str(selected_cat)
                st.session_state["est_material_last_item"] = str(mat_add_item).strip()
                st.session_state["est_material_last_qty"] = float(mat_add_qty or 0.0) or 1.0
                est["materials"] = (est.get("materials") or []) + [{"item": str(mat_add_item).strip(), "qty": float(mat_add_qty or 0.0)}]
                st.session_state["est_material_edit_idx"] = None
                st.rerun()

        # Edit form (only one row at a time)
        mat_edit_idx = st.session_state.get("est_material_edit_idx")
        if mat_edit_idx is not None:
            try:
                mat_edit_idx = int(mat_edit_idx)
            except Exception:
                mat_edit_idx = None
            if mat_edit_idx is None or mat_edit_idx < 0 or mat_edit_idx >= len(est.get("materials") or []):
                st.session_state["est_material_edit_idx"] = None
            else:
                cur = (est.get("materials") or [])[mat_edit_idx] or {}
                cur_item = str(cur.get("item") or "").strip()
                cur_qty = float(cur.get("qty", 0) or 0)
                with st.form(key=f"est_material_edit_form_{mat_edit_idx}", clear_on_submit=True):
                    st.caption(f"Editing material line #{mat_edit_idx + 1}")
                    me1, me2, me3, me4 = st.columns([2.0, 0.42, 0.55, 0.55], gap="small")
                    with me1:
                        mat_edit_item = st.selectbox(
                            "Material",
                            options=materials_options if materials_options else [""],
                            index=(materials_options.index(cur_item) if cur_item in materials_options else 0),
                            disabled=is_locked,
                            key=f"est_material_edit_item_{mat_edit_idx}",
                        )
                    with me2:
                        mat_edit_qty = st.number_input(
                            "Qty",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_qty,
                            key=f"est_material_edit_qty_{mat_edit_idx}",
                        )
                    with me3:
                        mat_edit_submit = st.form_submit_button(
                            "Save", disabled=is_locked, key=f"est_material_edit_save_{mat_edit_idx}"
                        )
                    with me4:
                        mat_edit_cancel = st.form_submit_button(
                            "Cancel", disabled=is_locked, key=f"est_material_edit_cancel_{mat_edit_idx}"
                        )
                    if mat_edit_cancel:
                        st.session_state["est_material_edit_idx"] = None
                        st.rerun()
                    if mat_edit_submit:
                        if not str(mat_edit_item or "").strip():
                            st.error("Select a Material.")
                            st.stop()
                        est["materials"][mat_edit_idx] = {"item": str(mat_edit_item).strip(), "qty": float(mat_edit_qty or 0.0)}
                        st.session_state["est_material_edit_idx"] = None
                        st.rerun()

        # Render existing lines
        mat_lines = est.get("materials") or []
        if not mat_lines:
            st.info("No materials added yet.")
        else:
            for idx, line in enumerate(mat_lines):
                if not isinstance(line, dict):
                    continue
                item_key = str(line.get("item") or "").strip()
                qty_d = _dec(line.get("qty", 0) or 0)
                m = material_map.get(item_key)
                purchase_d = _dec((m or {}).get("purchase_price", 0) or 0)
                sell_d = _dec((m or {}).get("sell_price", 0) or 0)
                base_sell = sell_d if sell_d > _D0 else purchase_d * (Decimal("1") + material_markup_dec)
                subtotal = _q2(qty_d * base_sell)

                with st.container(border=True):
                    left, right = st.columns([1.65, 1], gap="small")
                    with left:
                        st.markdown(f"**{item_key or 'Unknown material'}**")
                        st.caption(f"Qty: {money_str(qty_d)}")
                    with right:
                        st.metric(label="Line subtotal", value=money(subtotal))
                    c_edit, c_rem = st.columns([1, 1], gap="small")
                    with c_edit:
                        if st.button("Edit", disabled=is_locked, key=f"est_material_edit_btn_{idx}"):
                            st.session_state["est_material_edit_idx"] = idx
                            st.rerun()
                    with c_rem:
                        if st.button("Remove", disabled=is_locked, key=f"est_material_remove_btn_{idx}"):
                            est["materials"] = [x for j, x in enumerate(mat_lines) if j != idx]
                            if st.session_state.get("est_material_edit_idx") == idx:
                                st.session_state["est_material_edit_idx"] = None
                            st.rerun()

    with tabs[1]:
        # Labor row cards + form-based add/edit to avoid "enter twice" UX.
        est.setdefault("labor", [])
        labor_map = {r.get("classification"): r for r in labor_rates if isinstance(r, dict) and r.get("classification")}

        st.caption("Quick add: classification + rates — last-used values are remembered.")

        with st.form(key="est_labor_add_form", clear_on_submit=True):
            last_class = str(st.session_state.get("est_labor_last_classification") or "").strip()
            class_opts = labor_options if labor_options else [""]
            class_index = class_opts.index(last_class) if last_class in class_opts else 0
            la1, la2, la3, la4, la5, la6 = st.columns([1.35, 0.62, 0.62, 0.62, 0.62, 0.52], gap="small")
            with la1:
                labor_add_class = st.selectbox(
                    "Class",
                    options=class_opts,
                    index=class_index,
                    disabled=is_locked,
                    key="est_labor_add_class",
                )
            with la2:
                labor_add_headcount = st.number_input(
                    "Headcount",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_labor_last_headcount") or 1.0),
                    key="est_labor_add_headcount",
                )
            with la3:
                labor_add_st_hrs = st.number_input(
                    "ST Hrs/Day",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_labor_last_st_hours") or 8.0),
                    key="est_labor_add_st_hours",
                )
            with la4:
                labor_add_ot_hrs = st.number_input(
                    "OT Hrs/Day",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_labor_last_ot_hours") or 0.0),
                    key="est_labor_add_ot_hours",
                )
            with la5:
                labor_add_days = st.number_input(
                    "Days",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_labor_last_days") or 1.0),
                    key="est_labor_add_days",
                )
            with la6:
                st.markdown("")
                labor_add_submit = st.form_submit_button("Add", disabled=is_locked)

            if labor_add_submit:
                if not str(labor_add_class or "").strip():
                    st.error("Select a Labor Classification.")
                    st.stop()
                st.session_state["est_labor_last_classification"] = str(labor_add_class).strip()
                st.session_state["est_labor_last_headcount"] = float(labor_add_headcount or 0.0) or 1.0
                st.session_state["est_labor_last_st_hours"] = float(labor_add_st_hrs or 0.0) or 8.0
                st.session_state["est_labor_last_ot_hours"] = float(labor_add_ot_hrs or 0.0)
                st.session_state["est_labor_last_days"] = float(labor_add_days or 0.0) or 1.0
                est["labor"] = (est.get("labor") or []) + [
                    {
                        "classification": str(labor_add_class).strip(),
                        "headcount": float(labor_add_headcount or 0.0),
                        "st_hours_per_day": float(labor_add_st_hrs or 0.0),
                        "ot_hours_per_day": float(labor_add_ot_hrs or 0.0),
                        "days": float(labor_add_days or 0.0),
                    }
                ]
                st.session_state["est_labor_edit_idx"] = None
                st.rerun()

        labor_edit_idx = st.session_state.get("est_labor_edit_idx")
        if labor_edit_idx is not None:
            try:
                labor_edit_idx = int(labor_edit_idx)
            except Exception:
                labor_edit_idx = None
            if labor_edit_idx is None or labor_edit_idx < 0 or labor_edit_idx >= len(est.get("labor") or []):
                st.session_state["est_labor_edit_idx"] = None
            else:
                cur = (est.get("labor") or [])[labor_edit_idx] or {}
                cur_class = str(cur.get("classification") or "").strip()
                cur_headcount = float(cur.get("headcount", 0) or 0)
                cur_st = float(cur.get("st_hours_per_day", 0) or 0)
                cur_ot = float(cur.get("ot_hours_per_day", 0) or 0)
                cur_days = float(cur.get("days", 0) or 0)
                with st.form(key=f"est_labor_edit_form_{labor_edit_idx}", clear_on_submit=True):
                    st.caption(f"Editing labor line #{labor_edit_idx + 1}")
                    le1, le2, le3, le4, le5 = st.columns([1.4, 0.62, 0.62, 0.62, 0.62], gap="small")
                    with le1:
                        labor_edit_class = st.selectbox(
                            "Class",
                            options=labor_options if labor_options else [""],
                            index=(labor_options.index(cur_class) if cur_class in labor_options else 0),
                            disabled=is_locked,
                            key=f"est_labor_edit_class_{labor_edit_idx}",
                        )
                    with le2:
                        labor_edit_headcount = st.number_input(
                            "Headcount",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_headcount,
                            key=f"est_labor_edit_headcount_{labor_edit_idx}",
                        )
                    with le3:
                        labor_edit_st = st.number_input(
                            "ST Hrs/Day",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_st,
                            key=f"est_labor_edit_st_hours_{labor_edit_idx}",
                        )
                    with le4:
                        labor_edit_ot = st.number_input(
                            "OT Hrs/Day",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_ot,
                            key=f"est_labor_edit_ot_hours_{labor_edit_idx}",
                        )
                    with le5:
                        labor_edit_days = st.number_input(
                            "Days",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_days,
                            key=f"est_labor_edit_days_{labor_edit_idx}",
                        )
                    leb1, leb2 = st.columns([1, 1], gap="small")
                    with leb1:
                        labor_edit_submit = st.form_submit_button(
                            "Save", disabled=is_locked, key=f"est_labor_edit_save_{labor_edit_idx}"
                        )
                    with leb2:
                        labor_edit_cancel = st.form_submit_button(
                            "Cancel", disabled=is_locked, key=f"est_labor_edit_cancel_{labor_edit_idx}"
                        )
                    if labor_edit_cancel:
                        st.session_state["est_labor_edit_idx"] = None
                        st.rerun()
                    if labor_edit_submit:
                        if not str(labor_edit_class or "").strip():
                            st.error("Select a Labor Classification.")
                            st.stop()
                        est["labor"][labor_edit_idx] = {
                            "classification": str(labor_edit_class).strip(),
                            "headcount": float(labor_edit_headcount or 0.0),
                            "st_hours_per_day": float(labor_edit_st or 0.0),
                            "ot_hours_per_day": float(labor_edit_ot or 0.0),
                            "days": float(labor_edit_days or 0.0),
                        }
                        st.session_state["est_labor_edit_idx"] = None
                        st.rerun()

        labor_lines = est.get("labor") or []
        if not labor_lines:
            st.info("No labor lines added yet.")
        else:
            for idx, line in enumerate(labor_lines):
                if not isinstance(line, dict):
                    continue
                classification = str(line.get("classification") or "").strip()
                headcount = _dec(line.get("headcount", 0) or 0)
                st_hrs = _dec(line.get("st_hours_per_day", 0) or 0)
                ot_hrs = _dec(line.get("ot_hours_per_day", 0) or 0)
                days = _dec(line.get("days", 0) or 0)
                lr = labor_map.get(classification)
                st_rate = _dec((lr or {}).get("st_rate", 0) or 0)
                ot_rate = _dec((lr or {}).get("ot_rate", 0) or 0)
                subtotal = _q2(headcount * days * ((st_hrs * st_rate) + (ot_hrs * ot_rate)))

                with st.container(border=True):
                    left, right = st.columns([1.65, 1], gap="small")
                    with left:
                        st.markdown(f"**{classification or 'Unknown labor'}**")
                        st.caption(f"Headcount: {headcount:.2f} · Days: {days:.2f} · ST {st_hrs:.2f}h/Day · OT {ot_hrs:.2f}h/Day")
                    with right:
                        st.metric(label="Line subtotal", value=money(subtotal))
                    c_edit, c_rem = st.columns([1, 1], gap="small")
                    with c_edit:
                        if st.button("Edit", disabled=is_locked, key=f"est_labor_edit_btn_{idx}"):
                            st.session_state["est_labor_edit_idx"] = idx
                            st.rerun()
                    with c_rem:
                        if st.button("Remove", disabled=is_locked, key=f"est_labor_remove_btn_{idx}"):
                            est["labor"] = [x for j, x in enumerate(labor_lines) if j != idx]
                            if st.session_state.get("est_labor_edit_idx") == idx:
                                st.session_state["est_labor_edit_idx"] = None
                            st.rerun()

    with tabs[2]:
        st.caption("Search → pick equipment → qty / basis / duration → add. Edit or remove from cards below.")
        eq_top1, eq_top2 = st.columns([3.0, 0.95], gap="small")
        with eq_top1:
            eq_search = st.text_input(
                "Search equipment",
                key="est_eq_equipment_search",
                placeholder="Name, manufacturer, model, serial…",
                disabled=is_locked,
                help="Matches every word you type (case-insensitive). Lines already on this estimate stay available even if filtered.",
            )
        with eq_top2:
            st.checkbox(
                "Rent-to-customer only",
                key="est_eq_rental_only",
                help="When checked, the picker lists only assets marked Rent to Customer. "
                "Uncheck to list all Equipment assets (rates may be zero).",
            )
        rental_only = st.session_state.get("est_eq_rental_only", True)

        option_labels, label_to_name, _name_to_label, _asset_id_to_label = build_equipment_picker_maps(
            equipment_pricing,
            rental_only=rental_only,
            search_query=eq_search,
            estimate_equipment_rows=est.get("equipment", []),
        )
        eq_opts = option_labels if option_labels else [""]
        equipment_map = {e["equipment_item"]: e for e in equipment_pricing}

        if not option_labels:
            st.warning(
                "No equipment assets match this filter. Add **Equipment** assets in the Asset Database, "
                "adjust search, or turn off “rent-to-customer only”."
            )

        est.setdefault("equipment", [])

        with st.form(key="est_equipment_add_form", clear_on_submit=True):
            last_item = str(st.session_state.get("est_equipment_last_item") or "").strip()
            item_index = eq_opts.index(last_item) if last_item in eq_opts else 0
            ea0, ea1, ea2, ea3, ea4 = st.columns([1.85, 0.48, 0.52, 0.52, 0.42], gap="small")
            with ea0:
                eq_add_item = st.selectbox(
                    "Equipment",
                    options=eq_opts,
                    index=item_index,
                    disabled=is_locked,
                    key="est_equipment_add_item",
                    help="Items include rate preview. Choose an asset-based equipment item when possible.",
                )
            basis_opts = ["Day", "Week", "Month"]
            last_basis = str(st.session_state.get("est_equipment_last_basis") or "Day")
            basis_index = basis_opts.index(last_basis) if last_basis in basis_opts else 0
            with ea1:
                eq_add_qty = st.number_input(
                    "Qty",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_equipment_last_qty") or 1.0),
                    key="est_equipment_add_qty",
                )
            with ea2:
                eq_add_basis = st.selectbox(
                    "Basis",
                    options=basis_opts,
                    index=basis_index,
                    disabled=is_locked,
                    key="est_equipment_add_basis",
                )
            with ea3:
                eq_add_duration = st.number_input(
                    "Dur.",
                    min_value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_locked,
                    value=float(st.session_state.get("est_equipment_last_duration") or 1.0),
                    key="est_equipment_add_duration",
                    help="Duration in selected basis (days/weeks/months).",
                )
            with ea4:
                st.markdown("")
                eq_add_submit = st.form_submit_button("Add", disabled=is_locked)
            if eq_add_submit:
                if not str(eq_add_item or "").strip():
                    st.error("Select an equipment item.")
                    st.stop()
                st.session_state["est_equipment_last_item"] = str(eq_add_item).strip()
                st.session_state["est_equipment_last_qty"] = float(eq_add_qty or 0.0) or 1.0
                st.session_state["est_equipment_last_basis"] = str(eq_add_basis)
                st.session_state["est_equipment_last_duration"] = float(eq_add_duration or 0.0) or 1.0

                new_row = {
                    "equipment_item": str(eq_add_item).strip(),
                    "qty": float(eq_add_qty or 0.0),
                    "basis": str(eq_add_basis),
                    "duration": float(eq_add_duration or 0.0),
                }
                # Normalize picker label → canonical asset name and attach metadata.
                enriched = enrich_equipment_rows_from_assets([new_row], equipment_pricing, picker_label_to_name=label_to_name)
                est["equipment"] = (est.get("equipment") or []) + enriched
                st.session_state["est_equipment_edit_idx"] = None
                st.rerun()

        eq_edit_idx = st.session_state.get("est_equipment_edit_idx")
        if eq_edit_idx is not None:
            try:
                eq_edit_idx = int(eq_edit_idx)
            except Exception:
                eq_edit_idx = None
            if eq_edit_idx is None or eq_edit_idx < 0 or eq_edit_idx >= len(est.get("equipment") or []):
                st.session_state["est_equipment_edit_idx"] = None
            else:
                cur = (est.get("equipment") or [])[eq_edit_idx] or {}
                cur_name = str(cur.get("equipment_item") or "").strip()
                cur_qty = float(cur.get("qty", 0) or 0.0)
                cur_basis = str(cur.get("basis") or "Day")
                cur_duration = float(cur.get("duration", 0) or 0.0)

                # Try to map canonical name → a current picker option label.
                cur_pick = next((lab for lab, nm in label_to_name.items() if nm == cur_name), cur_name)
                if cur_pick not in eq_opts and eq_opts:
                    cur_pick = eq_opts[0]
                with st.form(key=f"est_equipment_edit_form_{eq_edit_idx}", clear_on_submit=True):
                    st.caption(f"Editing equipment line #{eq_edit_idx + 1}")
                    ee0, ee1, ee2, ee3 = st.columns([1.75, 0.48, 0.52, 0.52], gap="small")
                    with ee0:
                        eq_edit_item = st.selectbox(
                            "Equipment",
                            options=eq_opts,
                            index=(eq_opts.index(cur_pick) if cur_pick in eq_opts else 0),
                            disabled=is_locked,
                            key=f"est_equipment_edit_item_{eq_edit_idx}",
                        )
                    with ee1:
                        eq_edit_qty = st.number_input(
                            "Qty",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_qty,
                            key=f"est_equipment_edit_qty_{eq_edit_idx}",
                        )
                    with ee2:
                        eq_edit_basis = st.selectbox(
                            "Basis",
                            options=basis_opts,
                            index=(basis_opts.index(cur_basis) if cur_basis in basis_opts else 0),
                            disabled=is_locked,
                            key=f"est_equipment_edit_basis_{eq_edit_idx}",
                        )
                    with ee3:
                        eq_edit_duration = st.number_input(
                            "Dur.",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=cur_duration,
                            key=f"est_equipment_edit_duration_{eq_edit_idx}",
                        )
                    eeb1, eeb2 = st.columns(2, gap="small")
                    with eeb1:
                        eq_edit_submit = st.form_submit_button(
                            "Save", disabled=is_locked, key=f"est_equipment_edit_save_{eq_edit_idx}"
                        )
                    with eeb2:
                        eq_edit_cancel = st.form_submit_button(
                            "Cancel", disabled=is_locked, key=f"est_equipment_edit_cancel_{eq_edit_idx}"
                        )
                    if eq_edit_cancel:
                        st.session_state["est_equipment_edit_idx"] = None
                        st.rerun()
                    if eq_edit_submit:
                        if not str(eq_edit_item or "").strip():
                            st.error("Select an equipment item.")
                            st.stop()
                        new_row = {
                            "equipment_item": str(eq_edit_item).strip(),
                            "qty": float(eq_edit_qty or 0.0),
                            "basis": str(eq_edit_basis),
                            "duration": float(eq_edit_duration or 0.0),
                        }
                        enriched = enrich_equipment_rows_from_assets([new_row], equipment_pricing, picker_label_to_name=label_to_name)[0]
                        # Preserve any stored notes/asset_id if still valid (enricher will drop if no match).
                        est["equipment"][eq_edit_idx] = {**cur, **enriched}
                        st.session_state["est_equipment_edit_idx"] = None
                        st.rerun()

        eq_lines = est.get("equipment") or []
        if not eq_lines:
            st.info("No equipment lines added yet.")
        else:
            for idx, line in enumerate(eq_lines):
                if not isinstance(line, dict):
                    continue
                name = str(line.get("equipment_item") or "").strip()
                qty_d = _dec(line.get("qty", 0) or 0)
                basis = str(line.get("basis") or "Day")
                duration_d = _dec(line.get("duration", 0) or 0)
                meta = equipment_map.get(name) or {}
                rate = {
                    "Day": _dec(meta.get("daily_rate", 0) or 0),
                    "Week": _dec(meta.get("weekly_rate", 0) or 0),
                    "Month": _dec(meta.get("monthly_rate", 0) or 0),
                }.get(basis, _D0)
                subtotal = _q2(qty_d * duration_d * rate)
                with st.container(border=True):
                    left, right = st.columns([1.65, 1], gap="small")
                    with left:
                        st.markdown(f"**{name or 'Unknown equipment'}**")
                        st.caption(
                            f"Qty: {money_str(qty_d)} · Basis: {basis} · Duration: {money_str(duration_d)} · Rate: {money(rate)}"
                        )
                    with right:
                        st.metric(label="Line subtotal", value=money(subtotal))
                    c_edit, c_rem = st.columns([1, 1], gap="small")
                    with c_edit:
                        if st.button("Edit", disabled=is_locked, key=f"est_equipment_edit_btn_{idx}"):
                            st.session_state["est_equipment_edit_idx"] = idx
                            st.rerun()
                    with c_rem:
                        if st.button("Remove", disabled=is_locked, key=f"est_equipment_remove_btn_{idx}"):
                            est["equipment"] = [x for j, x in enumerate(eq_lines) if j != idx]
                            if st.session_state.get("est_equipment_edit_idx") == idx:
                                st.session_state["est_equipment_edit_idx"] = None
                            st.rerun()

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
        st.caption("Quick add travel charges, then edit/remove from cards below.")
        travel = est.get("travel", {}) or {}
        est["travel"] = travel

        TRAVEL_KINDS = ["Mileage", "Per diem", "Hotel", "Airfare", "Rental car", "Fuel", "Override"]

        with st.form(key="est_travel_add_form", clear_on_submit=True):
            last_kind = str(st.session_state.get("est_travel_last_kind") or "Mileage")
            kind_index = TRAVEL_KINDS.index(last_kind) if last_kind in TRAVEL_KINDS else 0
            tk_type, tk_vals = st.columns([0.85, 2.65], gap="small")
            with tk_type:
                kind = st.selectbox(
                    "Type",
                    options=TRAVEL_KINDS,
                    index=kind_index,
                    disabled=is_locked,
                    key="est_travel_add_kind",
                )
            with tk_vals:
                if kind == "Mileage":
                    c1, c2 = st.columns(2, gap="small")
                    miles = c1.number_input(
                        "Round Trip Miles",
                        min_value=0.0,
                        step=10.0,
                        disabled=is_locked,
                        value=float(st.session_state.get("est_travel_last_miles") or _num0(travel.get("round_trip_miles"))),
                        key="est_travel_add_miles",
                    )
                    rate = c2.number_input(
                        "Mileage Rate",
                        min_value=0.0,
                        step=0.1,
                        format="%.2f",
                        disabled=is_locked,
                        value=float(
                            st.session_state.get("est_travel_last_mileage_rate") or _num0(travel.get("mileage_rate"))
                        ),
                        key="est_travel_add_mileage_rate",
                    )
                elif kind == "Hotel":
                    c1, c2 = st.columns(2, gap="small")
                    nights = c1.number_input(
                        "Hotel Nights",
                        min_value=0.0,
                        step=1.0,
                        disabled=is_locked,
                        value=float(
                            st.session_state.get("est_travel_last_hotel_nights") or _num0(travel.get("hotel_nights"))
                        ),
                        key="est_travel_add_hotel_nights",
                    )
                    nightly = c2.number_input(
                        "Hotel Rate / Night",
                        min_value=0.0,
                        step=10.0,
                        format="%.2f",
                        disabled=is_locked,
                        value=float(
                            st.session_state.get("est_travel_last_hotel_rate")
                            or _num0(travel.get("hotel_rate_per_room_per_night"))
                        ),
                        key="est_travel_add_hotel_rate",
                    )
                else:
                    ta1, ta2 = st.columns([0.9, 1.1], gap="small")
                    with ta1:
                        amt = st.number_input(
                            "Amount",
                            min_value=0.0,
                            step=25.0,
                            format="%.2f",
                            disabled=is_locked,
                            value=float(st.session_state.get("est_travel_last_amount") or 0.0),
                            key="est_travel_add_amount",
                        )

            subc, _ = st.columns([0.75, 3.25])
            with subc:
                submit = st.form_submit_button("Apply", disabled=is_locked)
            if submit:
                st.session_state["est_travel_last_kind"] = str(kind)
                if kind == "Mileage":
                    travel["round_trip_miles"] = float(miles or 0.0)
                    travel["mileage_rate"] = float(rate or 0.0)
                    st.session_state["est_travel_last_miles"] = float(miles or 0.0)
                    st.session_state["est_travel_last_mileage_rate"] = float(rate or 0.0)
                elif kind == "Per diem":
                    travel["per_diem_per_person_per_day"] = float(amt or 0.0)
                    st.session_state["est_travel_last_amount"] = float(amt or 0.0)
                elif kind == "Hotel":
                    travel["hotel_nights"] = float(nights or 0.0)
                    travel["hotel_rate_per_room_per_night"] = float(nightly or 0.0)
                    st.session_state["est_travel_last_hotel_nights"] = float(nights or 0.0)
                    st.session_state["est_travel_last_hotel_rate"] = float(nightly or 0.0)
                elif kind == "Airfare":
                    travel["airfare"] = float(amt or 0.0)
                    st.session_state["est_travel_last_amount"] = float(amt or 0.0)
                elif kind == "Rental car":
                    travel["rental_car"] = float(amt or 0.0)
                    st.session_state["est_travel_last_amount"] = float(amt or 0.0)
                elif kind == "Fuel":
                    travel["fuel"] = float(amt or 0.0)
                    st.session_state["est_travel_last_amount"] = float(amt or 0.0)
                elif kind == "Override":
                    travel["line_total"] = float(amt or 0.0)
                    st.session_state["est_travel_last_amount"] = float(amt or 0.0)
                est["travel"] = travel
                st.rerun()

        # Draft cards (edit/remove)
        def _travel_cards() -> list[tuple[str, str, Decimal]]:
            miles_total = _dec(travel.get("round_trip_miles")) * _dec(travel.get("mileage_rate"))
            hotel_total = _dec(travel.get("hotel_nights")) * _dec(travel.get("hotel_rate_per_room_per_night"))
            items: list[tuple[str, str, Decimal]] = [
                ("Mileage", f'{_num0(travel.get("round_trip_miles")):.2f} mi × {money(_dec(travel.get("mileage_rate")))}', miles_total),
                ("Per diem", "", _dec(travel.get("per_diem_per_person_per_day"))),
                ("Hotel", f'{_num0(travel.get("hotel_nights")):.2f} nights × {money(_dec(travel.get("hotel_rate_per_room_per_night")))}', hotel_total),
                ("Airfare", "", _dec(travel.get("airfare"))),
                ("Rental car", "", _dec(travel.get("rental_car"))),
                ("Fuel", "", _dec(travel.get("fuel"))),
                ("Override", "If set (>0) and computed travel is 0, totals use this.", _dec(travel.get("line_total"))),
            ]
            # Show only non-zero-ish items (but always show mileage/hotel if either field is set).
            out: list[tuple[str, str, Decimal]] = []
            for k, d, v in items:
                if k in ("Mileage", "Hotel"):
                    if _num0(travel.get("round_trip_miles")) > 0 or _num0(travel.get("mileage_rate")) > 0 or k == "Hotel" and (_num0(travel.get("hotel_nights")) > 0 or _num0(travel.get("hotel_rate_per_room_per_night")) > 0):
                        out.append((k, d, v))
                else:
                    if _q2(v) != _D0:
                        out.append((k, d, _q2(v)))
            return out

        cards = _travel_cards()
        if not cards:
            st.info("No travel charges set yet.")
        else:
            for k, detail, val in cards:
                with st.container(border=True):
                    left, right = st.columns([1.65, 1], gap="small")
                    with left:
                        st.markdown(f"**{k}**")
                        if detail:
                            st.caption(detail)
                    with right:
                        st.metric(label="Amount", value=money(val))
                    c1, c2 = st.columns(2, gap="small")
                    with c1:
                        if st.button("Edit", disabled=is_locked, key=f"est_travel_edit_{k}"):
                            st.session_state["est_travel_last_kind"] = k
                            st.rerun()
                    with c2:
                        if st.button("Remove", disabled=is_locked, key=f"est_travel_remove_{k}"):
                            if k == "Mileage":
                                travel["round_trip_miles"] = 0.0
                                travel["mileage_rate"] = 0.0
                            elif k == "Per diem":
                                travel["per_diem_per_person_per_day"] = 0.0
                            elif k == "Hotel":
                                travel["hotel_nights"] = 0.0
                                travel["hotel_rate_per_room_per_night"] = 0.0
                            elif k == "Airfare":
                                travel["airfare"] = 0.0
                            elif k == "Rental car":
                                travel["rental_car"] = 0.0
                            elif k == "Fuel":
                                travel["fuel"] = 0.0
                            elif k == "Override":
                                travel["line_total"] = 0.0
                            est["travel"] = travel
                            st.rerun()

        st.markdown("---")
        st.caption("Estimate controls (markup, overhead, profit, contingency, tax) — submit once.")
        controls = est.get("controls", {}) or {}
        with st.form(key="est_controls_form", clear_on_submit=False):
            pc1, pc2, pc3, pc4, pc5 = st.columns(5, gap="small")
            material_markup_pct = pc1.number_input(
                "Material Markup %",
                min_value=0.0,
                value=_num0(controls.get("material_markup_pct")),
                step=0.01,
                format="%.2f",
                disabled=is_locked,
                key="est_ctrl_material_markup_pct",
            )
            overhead_pct = pc2.number_input(
                "Overhead %",
                min_value=0.0,
                value=_num0(controls.get("overhead_pct")),
                step=0.01,
                format="%.2f",
                disabled=is_locked,
                key="est_ctrl_overhead_pct",
            )
            profit_pct = pc3.number_input(
                "Profit %",
                min_value=0.0,
                value=_num0(controls.get("profit_pct")),
                step=0.01,
                format="%.2f",
                disabled=is_locked,
                key="est_ctrl_profit_pct",
            )
            contingency_pct = pc4.number_input(
                "Contingency %",
                min_value=0.0,
                value=_num0(controls.get("contingency_pct")),
                step=0.01,
                format="%.2f",
                disabled=is_locked,
                key="est_ctrl_contingency_pct",
            )
            sales_tax_pct = pc5.number_input(
                "Sales Tax %",
                min_value=0.0,
                value=_num0(controls.get("sales_tax_pct")),
                step=0.01,
                format="%.2f",
                disabled=is_locked,
                key="est_ctrl_sales_tax_pct",
            )
            if st.form_submit_button("Save controls", disabled=is_locked):
                est["controls"] = {
                    **controls,
                    "material_markup_pct": float(material_markup_pct or 0.0),
                    "overhead_pct": float(overhead_pct or 0.0),
                    "profit_pct": float(profit_pct or 0.0),
                    "contingency_pct": float(contingency_pct or 0.0),
                    "sales_tax_pct": float(sales_tax_pct or 0.0),
                }
                st.rerun()

    with tabs[4]:
        st.caption(
            "Edit **Scope of Work** and **Customer Responsibilities** in one submit to avoid rerun/reset issues."
        )
        with st.form(key="est_scope_form", clear_on_submit=False):
            scope_of_work = st.text_area(
                "Scope of Work",
                value=str(est.get("scope_of_work") or ""),
                height=160,
                disabled=is_locked,
                key="est_scope_scope_of_work",
            )
            customer_responsibilities = st.text_area(
                "Customer Responsibilities",
                value=str(est.get("customer_responsibilities") or ""),
                height=160,
                disabled=is_locked,
                key="est_scope_customer_responsibilities",
            )
            if st.form_submit_button("Save scope sections", disabled=is_locked):
                est["scope_of_work"] = str(scope_of_work or "")
                est["customer_responsibilities"] = str(customer_responsibilities or "")
                st.rerun()

    with tabs[5]:
        st.caption("Add attachments to the draft (they upload when you Save/Submit/Approve/Award).")

        # Quote attachments (pending)
        pending_quotes: list[dict] = list(st.session_state.get("est_pending_quote_attachments") or [])
        with st.form(key="est_quote_attach_add_form", clear_on_submit=True):
            up_files = st.file_uploader(
                "Quote Attachments",
                type=["pdf", "jpg", "jpeg", "png"],
                accept_multiple_files=True,
                disabled=is_locked,
                key="est_quote_attach_uploader",
                help="Files are staged in the draft until you Save.",
            )
            if st.form_submit_button("Add attachment(s) to draft", disabled=is_locked):
                if not up_files:
                    st.warning("Choose one or more files first.")
                    st.stop()
                for f in up_files:
                    pending_quotes.append(
                        {
                            "file_name": f.name,
                            "bytes": f.getvalue(),
                            "content_type": f.type or "application/octet-stream",
                        }
                    )
                st.session_state["est_pending_quote_attachments"] = pending_quotes
                st.rerun()

        if pending_quotes:
            st.markdown("**Pending quote attachments**")
            for i, f in enumerate(pending_quotes):
                nm = str(f.get("file_name") or "file")
                with st.container(border=True):
                    st.markdown(f"**{nm}**")
                    if st.button("Remove", disabled=is_locked, key=f"est_quote_attach_remove_{i}"):
                        st.session_state["est_pending_quote_attachments"] = [
                            x for j, x in enumerate(pending_quotes) if j != i
                        ]
                        st.rerun()
        else:
            st.caption("No pending quote attachments.")

        st.markdown("---")
        with st.form(key="est_po_form", clear_on_submit=False):
            job_received = st.checkbox(
                "Job Received / Awarded",
                value=bool(est.get("job_received", False)),
                disabled=is_locked,
                key="est_po_job_received",
            )
            pc1, pc2, pc3 = st.columns(3)
            po_number = pc1.text_input(
                "PO Number", value=str(est.get("po_number") or ""), disabled=is_locked, key="est_po_number"
            )
            po_date = pc2.text_input(
                "PO Date", value=str(est.get("po_date") or ""), disabled=is_locked, key="est_po_date"
            )
            po_amount = pc3.number_input(
                "PO Amount",
                min_value=0.0,
                value=float(est.get("po_amount", 0) or 0),
                step=100.0,
                disabled=is_locked,
                key="est_po_amount",
            )
            po_file = st.file_uploader(
                "PO Attachment",
                type=["pdf", "jpg", "jpeg", "png"],
                key="est_po_file_uploader",
                disabled=is_locked,
                help="Staged in the draft until you Save.",
            )
            if st.form_submit_button("Save P.O. fields to draft", disabled=is_locked):
                est["job_received"] = bool(job_received)
                est["po_number"] = str(po_number or "")
                est["po_date"] = str(po_date or "")
                est["po_amount"] = float(po_amount or 0.0)
                if po_file is not None:
                    st.session_state["est_pending_po_attachment"] = {
                        "file_name": po_file.name,
                        "bytes": po_file.getvalue(),
                        "content_type": po_file.type or "application/octet-stream",
                    }
                st.rerun()

        if st.session_state.get("est_pending_po_attachment"):
            po = st.session_state["est_pending_po_attachment"] or {}
            st.markdown("**Pending PO attachment**")
            with st.container(border=True):
                st.markdown(f"**{po.get('file_name') or 'po'}**")
                if st.button("Remove PO attachment", disabled=is_locked, key="est_po_remove_pending"):
                    st.session_state["est_pending_po_attachment"] = None
                    st.rerun()

    with tabs[6]:
        _pe = _proposal_export_kwargs(est, customer_name_by_id, jobs)
        tpl_uploader = st.file_uploader(
            "Proposal Word template (.docx)",
            type=["docx"],
            accept_multiple_files=False,
            key="est_proposal_tpl_uploader",
            help="Upload the IPS .docx template (default layout when set). Messy tokens like {{ Customer Name}} are normalized to {{CUSTOMER_NAME}} before fill.",
        )
        if tpl_uploader is not None:
            st.session_state["ips_proposal_template_bytes"] = tpl_uploader.getvalue()
        tpl_bytes = st.session_state.get("ips_proposal_template_bytes")
        if tpl_bytes and st.button("Clear uploaded Word template", key="est_proposal_tpl_clear"):
            st.session_state.pop("ips_proposal_template_bytes", None)
            st.rerun()

        docx_bytes = build_proposal_docx(est, totals, **_pe, template_bytes=tpl_bytes)
        pdf_bytes = build_proposal_pdf(est, totals, **_pe)

        # Top action card: downloads + (optional) save-to-storage.
        with st.container(border=True):
            st.caption(
                "Exports use the current draft. Word uses your uploaded template, else **assets/proposal_template.docx**, "
                "else the built-in layout. Placeholder labels are normalized to **{{CUSTOMER_NAME}}**, **{{SCOPE_OF_WORK}}**, etc., then filled. "
                "Save-to-storage requires a saved estimate."
            )
            d1, d2 = st.columns(2)
            with d1:
                st.download_button(
                    "Download Word Proposal",
                    data=docx_bytes,
                    file_name=f"{est.get('quote_number') or 'proposal'}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            with d2:
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
        with st.container(border=True):
            rc1, rc2, rc3, rc4 = st.columns(4)
            rc1.metric("Final Bid", money(totals["final_bid"]))
            rc2.metric("Overhead", money(totals["overhead_total"]))
            rc3.metric("Profit", money(totals["profit_total"]))
            rc4.metric("Sales Tax", money(totals["sales_tax_total"]))

            with st.form(key="est_revision_note_form", clear_on_submit=False):
                revision_note = st.text_input(
                    "Revision Note",
                    value=str(st.session_state.get("est_revision_note") or ""),
                    key="est_revision_note_input",
                )
                if st.form_submit_button("Update revision note"):
                    st.session_state["est_revision_note"] = str(revision_note or "")
                    st.rerun()

        customer_name = customer_name_by_id.get(str(est.get("customer_id") or "").strip(), "")
        loaded_id = st.session_state.get("loaded_estimate_id")
        qn_now = str(est.get("quote_number", "") or "").strip()
        if not qn_now:
            if loaded_id:
                st.warning("This estimate is missing a Quote Number.")
            else:
                st.info("Quote Number will be assigned on first save if left blank.")
        elif not customer_name:
            st.warning("Select a customer before saving.")

        save_cols = st.columns(4)
        can_save = bool(
            bool(est.get("customer_id"))
            and (qn_now or not loaded_id)
        )

        def _resolve_customer_job_on_commit() -> list[str]:
            msgs: list[str] = []
            # Job (requires customer_id when creating)
            job_typed = " ".join(str(st.session_state.get("est_job_query") or "").strip().split())
            if job_typed:
                if not est.get("customer_id"):
                    st.error("Select a customer before creating a new job.")
                    st.stop()
                jid, created = create_or_get_job_by_name(job_typed, customer_id=str(est.get("customer_id")))
                if jid:
                    est["job_id"] = jid
                    if created:
                        msgs.append(f"Created new job: {job_typed}")
            return msgs

        if save_cols[0].button("Save Estimate", use_container_width=True, disabled=(is_locked or not can_save)):
            # Allocate quote number only for brand-new estimates when blank.
            loaded_id = st.session_state.get("loaded_estimate_id")
            if not loaded_id and not str(est.get("quote_number", "") or "").strip():
                est["quote_number"] = next_quote_number()

            dup_msg = _duplicate_quote_message(str(est.get("quote_number", "") or "").strip(), loaded_id)
            if dup_msg:
                st.error(dup_msg)
            else:
                created_msgs = _resolve_customer_job_on_commit()
                totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
                payload = {
                    "quote_number": str(est.get("quote_number", "") or "").strip(),
                    "customer_id": est.get("customer_id"),
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
                    "estimate_json": est,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                estimate_id = persist_estimate(payload, est, str(st.session_state.get("est_revision_note") or ""))
                attach_pending_pdf_import_source(estimate_id)
                pending_quotes = list(st.session_state.get("est_pending_quote_attachments") or [])
                for f in pending_quotes:
                    fn = str(f.get("file_name") or "file")
                    storage_path = f"quotes/{estimate_id}/attachments/{Path(fn).name}"
                    upload_bytes(storage_path, f.get("bytes") or b"", f.get("content_type") or "application/octet-stream")
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": estimate_id,
                            "category": "quote_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(f.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                pending_po = st.session_state.get("est_pending_po_attachment")
                if isinstance(pending_po, dict) and pending_po.get("bytes") is not None:
                    fn = str(pending_po.get("file_name") or "po")
                    storage_path = f"quotes/{estimate_id}/po/{Path(fn).name}"
                    upload_bytes(
                        storage_path,
                        pending_po.get("bytes") or b"",
                        pending_po.get("content_type") or "application/octet-stream",
                    )
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": estimate_id,
                            "category": "po_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(pending_po.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                # Clear pending uploads after commit so reruns don't re-upload.
                st.session_state["est_pending_quote_attachments"] = []
                st.session_state["est_pending_po_attachment"] = None
                if created_msgs:
                    for m in created_msgs:
                        st.info(m)
                st.success("Estimate saved to Supabase.")
                st.session_state.pop("estimate_pdf_suggestions", None)

        if save_cols[1].button("Submit for Approval", use_container_width=True, disabled=(is_locked or not can_save)):
            loaded_id = st.session_state.get("loaded_estimate_id")
            if not loaded_id and not str(est.get("quote_number", "") or "").strip():
                est["quote_number"] = next_quote_number()

            dup_msg = _duplicate_quote_message(str(est.get("quote_number", "") or "").strip(), loaded_id)
            if dup_msg:
                st.error(dup_msg)
            else:
                created_msgs = _resolve_customer_job_on_commit()
                totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
                payload = {
                    "quote_number": str(est.get("quote_number", "") or "").strip(),
                    "customer_id": est.get("customer_id"),
                    "customer_contact_id": est.get("customer_contact_id"),
                    "job_id": est.get("job_id"),
                    "estimator_user_id": current_profile().get("id"),
                    "status": "submitted",
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
                    "estimate_json": est,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                est["status"] = "submitted"
                eid = persist_estimate(payload, est, "Submitted for approval")
                attach_pending_pdf_import_source(eid)
                pending_quotes = list(st.session_state.get("est_pending_quote_attachments") or [])
                for f in pending_quotes:
                    fn = str(f.get("file_name") or "file")
                    storage_path = f"quotes/{eid}/attachments/{Path(fn).name}"
                    upload_bytes(storage_path, f.get("bytes") or b"", f.get("content_type") or "application/octet-stream")
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": eid,
                            "category": "quote_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(f.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                pending_po = st.session_state.get("est_pending_po_attachment")
                if isinstance(pending_po, dict) and pending_po.get("bytes") is not None:
                    fn = str(pending_po.get("file_name") or "po")
                    storage_path = f"quotes/{eid}/po/{Path(fn).name}"
                    upload_bytes(
                        storage_path,
                        pending_po.get("bytes") or b"",
                        pending_po.get("content_type") or "application/octet-stream",
                    )
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": eid,
                            "category": "po_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(pending_po.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                st.session_state["est_pending_quote_attachments"] = []
                st.session_state["est_pending_po_attachment"] = None
                if created_msgs:
                    for m in created_msgs:
                        st.info(m)
                st.success("Estimate submitted for approval.")
                st.session_state.pop("estimate_pdf_suggestions", None)
                st.rerun()

        if save_cols[2].button("Approve", use_container_width=True, disabled=(current_role() != "admin" or not can_save)):
            loaded_id = st.session_state.get("loaded_estimate_id")
            if not loaded_id and not str(est.get("quote_number", "") or "").strip():
                est["quote_number"] = next_quote_number()

            dup_msg = _duplicate_quote_message(str(est.get("quote_number", "") or "").strip(), loaded_id)
            if dup_msg:
                st.error(dup_msg)
            else:
                created_msgs = _resolve_customer_job_on_commit()
                totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
                payload = {
                    "quote_number": str(est.get("quote_number", "") or "").strip(),
                    "customer_id": est.get("customer_id"),
                    "customer_contact_id": est.get("customer_contact_id"),
                    "job_id": est.get("job_id"),
                    "estimator_user_id": current_profile().get("id"),
                    "status": "approved",
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
                    "estimate_json": est,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                est["status"] = "approved"
                eid = persist_estimate(payload, est, "Approved")
                attach_pending_pdf_import_source(eid)
                pending_quotes = list(st.session_state.get("est_pending_quote_attachments") or [])
                for f in pending_quotes:
                    fn = str(f.get("file_name") or "file")
                    storage_path = f"quotes/{eid}/attachments/{Path(fn).name}"
                    upload_bytes(storage_path, f.get("bytes") or b"", f.get("content_type") or "application/octet-stream")
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": eid,
                            "category": "quote_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(f.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                pending_po = st.session_state.get("est_pending_po_attachment")
                if isinstance(pending_po, dict) and pending_po.get("bytes") is not None:
                    fn = str(pending_po.get("file_name") or "po")
                    storage_path = f"quotes/{eid}/po/{Path(fn).name}"
                    upload_bytes(
                        storage_path,
                        pending_po.get("bytes") or b"",
                        pending_po.get("content_type") or "application/octet-stream",
                    )
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": eid,
                            "category": "po_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(pending_po.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                st.session_state["est_pending_quote_attachments"] = []
                st.session_state["est_pending_po_attachment"] = None
                if created_msgs:
                    for m in created_msgs:
                        st.info(m)
                st.success("Estimate approved and locked.")
                st.session_state.pop("estimate_pdf_suggestions", None)
                st.rerun()

        if save_cols[3].button("Mark Awarded", use_container_width=True, disabled=(current_role() != "admin" or not can_save)):
            loaded_id = st.session_state.get("loaded_estimate_id")
            if not loaded_id and not str(est.get("quote_number", "") or "").strip():
                est["quote_number"] = next_quote_number()

            dup_msg = _duplicate_quote_message(str(est.get("quote_number", "") or "").strip(), loaded_id)
            if dup_msg:
                st.error(dup_msg)
            else:
                created_msgs = _resolve_customer_job_on_commit()
                totals = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
                payload = {
                    "quote_number": str(est.get("quote_number", "") or "").strip(),
                    "customer_id": est.get("customer_id"),
                    "customer_contact_id": est.get("customer_contact_id"),
                    "job_id": est.get("job_id"),
                    "estimator_user_id": current_profile().get("id"),
                    "status": "awarded",
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
                pending_quotes = list(st.session_state.get("est_pending_quote_attachments") or [])
                for f in pending_quotes:
                    fn = str(f.get("file_name") or "file")
                    storage_path = f"quotes/{eid}/attachments/{Path(fn).name}"
                    upload_bytes(storage_path, f.get("bytes") or b"", f.get("content_type") or "application/octet-stream")
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": eid,
                            "category": "quote_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(f.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                pending_po = st.session_state.get("est_pending_po_attachment")
                if isinstance(pending_po, dict) and pending_po.get("bytes") is not None:
                    fn = str(pending_po.get("file_name") or "po")
                    storage_path = f"quotes/{eid}/po/{Path(fn).name}"
                    upload_bytes(
                        storage_path,
                        pending_po.get("bytes") or b"",
                        pending_po.get("content_type") or "application/octet-stream",
                    )
                    insert_row_admin(
                        "attachments",
                        {
                            "estimate_id": eid,
                            "category": "po_attachment",
                            "file_name": fn,
                            "storage_path": storage_path,
                            "file_type": str(pending_po.get("content_type") or ""),
                            "uploaded_by": current_profile().get("id"),
                        },
                    )
                st.session_state["est_pending_quote_attachments"] = []
                st.session_state["est_pending_po_attachment"] = None
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

    # Persistent estimate summary/totals panel (stays visible while editing).
    # This is intentionally rendered outside the tab bodies so it runs regardless of
    # which editor tab is active.
    try:
        totals_preview = compute_totals(est, materials_catalog, labor_rates, equipment_pricing)
    except Exception as exc:
        totals_preview = None
        st.sidebar.error(
            "Could not compute totals for the current draft. "
            "Check your line items and try again."
        )
        st.sidebar.caption(str(exc))

    with st.sidebar:
        st.markdown("### Estimate Summary")
        st.caption(
            f"Quote: {est.get('quote_number') or '—'} · Status: {est.get('status') or 'draft'}"
        )
        customer_name = customer_name_by_id.get(str(est.get("customer_id") or "").strip(), "") if "customer_name_by_id" in locals() else ""
        if customer_name:
            st.caption(f"Customer: {customer_name}")

        if totals_preview:
            st.metric("Final Bid", money(totals_preview.get("final_bid", 0.0)))
            st.metric("Proposal Total", money(totals_preview.get("proposal_total", 0.0)))
            st.metric("Overhead", money(totals_preview.get("overhead_total", 0.0)))
            st.metric("Profit", money(totals_preview.get("profit_total", 0.0)))
            st.metric("Sales Tax", money(totals_preview.get("sales_tax_total", 0.0)))

            st.caption(
                "Breakdown: "
                f"Materials {money(totals_preview.get('material_sell_basis', 0))} · "
                f"Labor {money(totals_preview.get('labor_total', 0))} · "
                f"Equipment {money(totals_preview.get('equipment_total', 0))} · "
                f"Travel {money(totals_preview.get('travel_total', 0))}"
            )

        # Line-item counts for quick context (no inputs).
        mats_n = len(est.get("materials", []) or [])
        labor_n = len(est.get("labor", []) or [])
        eq_n = len(est.get("equipment", []) or [])
        st.caption(f"Lines: Materials {mats_n} · Labor {labor_n} · Equipment {eq_n}")


def render() -> None:
    render_estimate_editor(embedded=False)
    # COMPACT ESTIMATE EDITOR LAYOUT

    # We use the same render_estimate_editor, so to compact the editor,
    # we need to override the default rendering by patching or monkeypatching container/layouts here.
    # But since we control this file, just re-implement the core editor form here
    # with stricter/compact Streamlit column layouts.
    #
    # Most logic is in render_estimate_editor - let's assume the logical sub-functions
    # (compute_totals, money, etc.) are accessible in this scope if needed.

    from streamlit import session_state as ss

    # Load initial data
    # Try to reuse the same variable names, business logic, and session key usage

    # Fetch working draft estimate from session or scratch
    estimate = ss.get("estimate_draft")
    if not estimate:
        st.warning("No estimate loaded.")
        return

    # Helper for spacing
    def col_pad(width=0.03):
        """Spacer column for compact layouts (no border)."""
        return st.columns([width, 1, width])[0]

    # --- Compact Top Row: Quote, Status, Contact, Job, Customer ---

    st.markdown("### Estimate Details")

    col1, col2, col3, col4 = st.columns([1.2, 1, 1.3, 1.5])
    # Quote Number ~1/4 width
    with col1:
        qnum = st.text_input(
            "Quote #",
            value=estimate.get("quote_number", ""),
            key="est_quote_number",
            max_chars=16,
            help="Quote or estimate identifier.",
            label_visibility="visible",
        )
    # Status - compact select or radio
    with col2:
        status_options = ["draft", "pending", "approved", "awarded", "archived"]
        status_val = st.selectbox(
            "Status",
            status_options,
            index=status_options.index(estimate.get("status", "draft"))
            if estimate.get("status", "draft") in status_options else 0,
            key="est_status",
        )
    # Contact - compact text
    with col3:
        contact_val = st.text_input(
            "Contact",
            value=estimate.get("contact", ""),
            key="est_contact",
            max_chars=32,
            help="Customer contact name.",
        )
    # Job - compact text
    with col4:
        job_val = st.text_input(
            "Job",
            value=estimate.get("job_name", ""),
            key="est_job_name",
            max_chars=32,
            help="Job short name or code.",
        )

    # Second row: Customer (wider but not 100%) — saved customers only (same source as Customers tab).
    cust_col, = st.columns([2.75])
    with cust_col:
        _EMPTY_CUSTOMER_COMPACT = "__est_no_customer__"
        customers_compact = _fetch_customers_for_editor()
        cur_cid = str(estimate.get("customer_id") or "").strip()
        ids_h = {str(c["id"]) for c in customers_compact if c.get("id")}
        if cur_cid and cur_cid not in ids_h:
            extra = _fetch_customer_row_by_id_for_editor(cur_cid)
            if extra and extra.get("id"):
                customers_compact = [extra] + list(customers_compact)
            elif cur_cid:
                customers_compact = [
                    {"id": cur_cid, "customer_name": "[Customer not found — check Customers tab]"},
                ] + list(customers_compact)
        rows_c = [r for r in customers_compact if r.get("id")]
        if not rows_c:
            st.warning(
                "No customers in the database. Add a customer from the **Customers** tab, then return here and select it."
            )
            estimate["customer_id"] = None
        else:
            ordered_ids_c, id_to_label_c = _customer_dropdown_labels(rows_c)
            options_c = [_EMPTY_CUSTOMER_COMPACT] + ordered_ids_c

            def _fmt_customer_compact(cid: str) -> str:
                if cid == _EMPTY_CUSTOMER_COMPACT:
                    return "— Select customer —"
                return id_to_label_c.get(cid, cid)

            cur_s = str(estimate.get("customer_id") or "").strip()
            default_idx_c = options_c.index(cur_s) if cur_s in options_c else 0
            sel_c = st.selectbox(
                "Customer",
                options=options_c,
                index=default_idx_c,
                format_func=_fmt_customer_compact,
                key="est_customer_compact_select_id",
                help="Only saved customers from the Customers tab.",
            )
            if sel_c == _EMPTY_CUSTOMER_COMPACT:
                estimate["customer_id"] = None
            else:
                estimate["customer_id"] = sel_c

    # --- Tabs for Materials, Labor, Equipment, Travel ---

    st.markdown("### Estimate Items")

    tabs = st.tabs(["Materials", "Labor", "Equipment", "Travel"])

    # --- MATERIALS TAB ---
    with tabs[0]:
        st.caption("Add materials to the estimate")

        mats_list = estimate.get("materials", []) or []
        mat_cols = st.columns([1.2, 2.1, 0.9, 0.7, 0.9])
        # Category
        with mat_cols[0]:
            new_mat_cat = st.text_input(
                "Category", value=ss.get("new_mat_cat", ""), key="new_mat_cat", max_chars=16
            )
        # Material
        with mat_cols[1]:
            new_mat_name = st.text_input(
                "Material", value=ss.get("new_mat_name", ""), key="new_mat_name", max_chars=32
            )
        # Qty
        with mat_cols[2]:
            new_mat_qty = st.number_input(
                "Qty", min_value=0.0, value=float(ss.get("new_mat_qty", 0)), step=1.0, key="new_mat_qty"
            )
        # Unit (choose from list or text if available)
        with mat_cols[3]:
            mat_units = ["ea", "ft", "m", "box", "hr"]
            new_mat_unit = st.selectbox(
                "Unit", mat_units, index=0, key="new_mat_unit"
            )
        # Add Button
        with mat_cols[4]:
            if st.button("➕", use_container_width=True, key="add_material_btn"):
                mats_list.append({
                    "category": new_mat_cat,
                    "name": new_mat_name,
                    "quantity": new_mat_qty,
                    "unit": new_mat_unit,
                })
                estimate["materials"] = mats_list
                st.success(f"Added {new_mat_name} ({new_mat_qty} {new_mat_unit})")

        # Materials table - compact
        if mats_list:
            matdf = pd.DataFrame(mats_list)
            st.dataframe(matdf, use_container_width=True, hide_index=True, height=min(300, 38*len(matdf)+22))
        else:
            st.info("No materials added.")

    # --- LABOR TAB ---
    with tabs[1]:
        st.caption("Add labor tasks to the estimate")

        labor_list = estimate.get("labor", []) or []
        labor_cols = st.columns([1.7, 2.1, 0.8, 0.8])
        # Role/Type
        with labor_cols[0]:
            new_labor_role = st.text_input(
                "Type/Role", value=ss.get("new_labor_role", ""), key="new_labor_role", max_chars=20
            )
        # Description
        with labor_cols[1]:
            new_labor_desc = st.text_input(
                "Desc.", value=ss.get("new_labor_desc", ""), key="new_labor_desc", max_chars=32
            )
        # Hours
        with labor_cols[2]:
            new_labor_hours = st.number_input(
                "Hours", min_value=0.0, value=float(ss.get("new_labor_hours", 0)), step=1.0, key="new_labor_hours"
            )
        # Add Button
        with labor_cols[3]:
            if st.button("➕", use_container_width=True, key="add_labor_btn"):
                labor_list.append({
                    "role": new_labor_role,
                    "desc": new_labor_desc,
                    "hours": new_labor_hours,
                })
                estimate["labor"] = labor_list
                st.success(f"Added {new_labor_role} ({new_labor_hours} hrs)")

        # Labor table
        if labor_list:
            laboredf = pd.DataFrame(labor_list)
            st.dataframe(laboredf, use_container_width=True, hide_index=True, height=min(300, 38*len(laboredf)+22))
        else:
            st.info("No labor added.")

    # --- EQUIPMENT TAB ---
    with tabs[2]:
        st.caption("Add equipment to the estimate")

        equip_list = estimate.get("equipment", []) or []
        equip_cols = st.columns([2.0, 1.5, 0.8, 0.8])
        # Equipment (type)
        with equip_cols[0]:
            new_eq_type = st.text_input(
                "Equipment", value=ss.get("new_eq_type", ""), key="new_eq_type", max_chars=24
            )
        # Usage desc
        with equip_cols[1]:
            new_eq_desc = st.text_input(
                "Desc.", value=ss.get("new_eq_desc", ""), key="new_eq_desc", max_chars=28
            )
        # Hours/Units
        with equip_cols[2]:
            new_eq_units = st.number_input(
                "Qty/Hrs", min_value=0.0, value=float(ss.get("new_eq_units", 0)), step=1.0, key="new_eq_units"
            )
        # Add Button
        with equip_cols[3]:
            if st.button("➕", use_container_width=True, key="add_equipment_btn"):
                equip_list.append({
                    "type": new_eq_type,
                    "desc": new_eq_desc,
                    "qty": new_eq_units,
                })
                estimate["equipment"] = equip_list
                st.success(f"Added {new_eq_type} ({new_eq_units})")

        if equip_list:
            eqdf = pd.DataFrame(equip_list)
            st.dataframe(eqdf, use_container_width=True, hide_index=True, height=min(300, 38*len(eqdf)+22))
        else:
            st.info("No equipment added.")

    # --- TRAVEL TAB ---
    with tabs[3]:
        st.caption("Add travel costs to the estimate")

        travel_list = estimate.get("travel", []) or []
        travel_cols = st.columns([2.0, 0.9, 0.8, 0.8])
        # Travel type/desc
        with travel_cols[0]:
            new_travel_type = st.text_input(
                "Travel Type", value=ss.get("new_travel_type", ""), key="new_travel_type", max_chars=24
            )
        # Distance/Units
        with travel_cols[1]:
            new_travel_amt = st.number_input(
                "Miles", min_value=0.0, value=float(ss.get("new_travel_amt", 0)), step=1.0, key="new_travel_amt"
            )
        # Flat or per-mile?
        with travel_cols[2]:
            new_travel_mode = st.selectbox(
                "Mode", ["flat", "per-mile"], index=0, key="new_travel_mode"
            )
        # Add Button
        with travel_cols[3]:
            if st.button("➕", use_container_width=True, key="add_travel_btn"):
                travel_list.append({
                    "type": new_travel_type,
                    "amount": new_travel_amt,
                    "mode": new_travel_mode,
                })
                estimate["travel"] = travel_list
                st.success(f"Added {new_travel_type} ({new_travel_amt} {new_travel_mode})")

        if travel_list:
            tdf = pd.DataFrame(travel_list)
            st.dataframe(tdf, use_container_width=True, hide_index=True, height=min(300, 38*len(tdf)+22))
        else:
            st.info("No travel costs added.")

    # --- Save/Submit Row, Compact ---
    save_col, review_col, pad_col = st.columns([1, 1, 0.6])
    with save_col:
        if st.button("💾 Save", use_container_width=True, key="save_estimate_btn"):
            # Commit 'estimate' draft back to session and trigger save routine as in original flow
            ss["estimate_draft"] = estimate
            st.success("Draft saved.")
    with review_col:
        if st.button("🔍 Review", use_container_width=True, key="review_estimate_btn"):
            ss["estimate_draft"] = estimate
            st.info("Review triggered (implement as needed).")
            # Further compact this estimate editor UI per requirements.

            # --- COMPACT LAYOUT OF HEADER FIELDS ---

            with st.container():
                # Row 1: Quote # | Status | Customer
                col_qn, col_stat, col_cust = st.columns([1.0, 1.0, 2.0])
                with col_qn:
                    quote_number = st.text_input(
                        "Quote #",
                        value=estimate.get("quote_number", ""),
                        key="quote_number",
                        max_chars=12,
                    )
                with col_stat:
                    status = st.selectbox(
                        "Status",
                        options=["draft", "pending", "approved", "awarded"],
                        index=["draft", "pending", "approved", "awarded"].index(estimate.get("status", "draft")),
                        key="status",
                    )
                with col_cust:
                    _EMPTY_R = "__est_no_customer__"
                    rows_r = _fetch_customers_for_editor()
                    cur_r = str(estimate.get("customer_id") or "").strip()
                    ids_r = {str(c["id"]) for c in rows_r if c.get("id")}
                    if cur_r and cur_r not in ids_r:
                        ex = _fetch_customer_row_by_id_for_editor(cur_r)
                        if ex and ex.get("id"):
                            rows_r = [ex] + list(rows_r)
                        elif cur_r:
                            rows_r = [
                                {"id": cur_r, "customer_name": "[Customer not found — check Customers tab]"},
                            ] + list(rows_r)
                    rows_rf = [r for r in rows_r if r.get("id")]
                    if not rows_rf:
                        st.warning("No customers in the database. Add one from the **Customers** tab.")
                    else:
                        oid, lbl = _customer_dropdown_labels(rows_rf)
                        opt = [_EMPTY_R] + oid

                        def _fmt_r(cid: str) -> str:
                            if cid == _EMPTY_R:
                                return "— Select customer —"
                            return lbl.get(cid, cid)

                        idx_r = opt.index(cur_r) if cur_r in opt else 0
                        sel_r = st.selectbox(
                            "Customer",
                            options=opt,
                            index=idx_r,
                            format_func=_fmt_r,
                            key="est_customer_review_header",
                            help="Only saved customers from the Customers tab.",
                        )
                        estimate["customer_id"] = None if sel_r == _EMPTY_R else sel_r

                # Row 2: Contact | Job
                col_contact, col_job = st.columns([2.5, 2.5])
                with col_contact:
                    contact = st.text_input(
                        "Contact",
                        value=estimate.get("contact", ""),
                        key="contact",
                        max_chars=50,
                    )
                with col_job:
                    # Optionally, use a job picker if jobs are available; else fallback to text input.
                    job_value = estimate.get("job", "")
                    job_display = job_row_select_label(job_value) if callable(job_row_select_label) and job_value else job_value
                    job = st.text_input(
                        "Job",
                        value=job_display,
                        key="job",
                        max_chars=50,
                    )

            st.markdown("---")

            # --- MATERIALS TAB (COMPACT) ---
            # Find the Materials tab index for proper context
            materials_tab_idx = 0
            with tabs[materials_tab_idx]:
                st.caption("Add materials required for this estimate")
                materials_list = estimate.get("materials", []) or []

                mat_cols = st.columns([1.1, 2.0, 0.8, 0.4])
                # Category (narrow)
                with mat_cols[0]:
                    new_material_cat = st.text_input(
                        "Category", value=ss.get("new_material_cat", ""), key="new_material_cat", max_chars=18
                    )
                # Material (medium)
                with mat_cols[1]:
                    new_material_name = st.text_input(
                        "Material", value=ss.get("new_material_name", ""), key="new_material_name", max_chars=32
                    )
                # Quantity (very narrow)
                with mat_cols[2]:
                    new_material_qty = st.number_input(
                        "Qty", min_value=0.0, value=float(ss.get("new_material_qty", 0)), step=1.0, key="new_material_qty"
                    )
                # Add button (small)
                with mat_cols[3]:
                    if st.button("➕", use_container_width=True, key="add_material_btn"):
                        materials_list.append({
                            "category": new_material_cat,
                            "name": new_material_name,
                            "quantity": new_material_qty,
                        })
                        estimate["materials"] = materials_list
                        st.success(f"Added {new_material_name} x{new_material_qty}")

                if materials_list:
                    mdf = pd.DataFrame(materials_list)
                    st.dataframe(mdf, use_container_width=True, hide_index=True, height=min(300, 38*len(mdf)+22))
                else:
                    st.info("No materials added.")

            # --- LABOR TAB (COMPACT) ---
            with tabs[1]:
                st.caption("Add labor to the estimate")
                labor_list = estimate.get("labor", []) or []
                labor_cols = st.columns([1.2, 2.0, 0.8, 0.4])
                # Role (narrow)
                with labor_cols[0]:
                    new_labor_role = st.text_input(
                        "Role", value=ss.get("new_labor_role", ""), key="new_labor_role", max_chars=18
                    )
                # Description (medium)
                with labor_cols[1]:
                    new_labor_desc = st.text_input(
                        "Description", value=ss.get("new_labor_desc", ""), key="new_labor_desc", max_chars=32
                    )
                # Hours (very narrow)
                with labor_cols[2]:
                    new_labor_hours = st.number_input(
                        "Hours", min_value=0.0, value=float(ss.get("new_labor_hours", 0)), step=1.0, key="new_labor_hours"
                    )
                # Add button (small)
                with labor_cols[3]:
                    if st.button("➕", use_container_width=True, key="add_labor_btn"):
                        labor_list.append({
                            "role": new_labor_role,
                            "desc": new_labor_desc,
                            "hours": new_labor_hours,
                        })
                        estimate["labor"] = labor_list
                        st.success(f"Added {new_labor_role} ({new_labor_hours} hrs)")

                if labor_list:
                    ldf = pd.DataFrame(labor_list)
                    st.dataframe(ldf, use_container_width=True, hide_index=True, height=min(300, 38*len(ldf)+22))
                else:
                    st.info("No labor added.")

            # --- EQUIPMENT TAB (COMPACT) ---
            with tabs[2]:
                st.caption("Add equipment needed for the estimate")
                equipment_list = estimate.get("equipment", []) or []
                eq_cols = st.columns([1.2, 2.0, 0.8, 0.4])
                # Type (narrow)
                with eq_cols[0]:
                    new_equipment_type = st.text_input(
                        "Type", value=ss.get("new_equipment_type", ""), key="new_equipment_type", max_chars=18
                    )
                # Description (medium)
                with eq_cols[1]:
                    new_equipment_desc = st.text_input(
                        "Description", value=ss.get("new_equipment_desc", ""), key="new_equipment_desc", max_chars=32
                    )
                # Qty (very narrow)
                with eq_cols[2]:
                    new_equipment_qty = st.number_input(
                        "Qty", min_value=0.0, value=float(ss.get("new_equipment_qty", 0)), step=1.0, key="new_equipment_qty"
                    )
                # Add button (small)
                with eq_cols[3]:
                    if st.button("➕", use_container_width=True, key="add_equipment_btn"):
                        equipment_list.append({
                            "type": new_equipment_type,
                            "desc": new_equipment_desc,
                            "qty": new_equipment_qty,
                        })
                        estimate["equipment"] = equipment_list
                        st.success(f"Added {new_equipment_type} x{new_equipment_qty}")

                if equipment_list:
                    edf = pd.DataFrame(equipment_list)
                    st.dataframe(edf, use_container_width=True, hide_index=True, height=min(300, 38*len(edf)+22))
                else:
                    st.info("No equipment added.")

            # --- TRAVEL TAB (COMPACT) ---
            with tabs[3]:
                st.caption("Add travel costs to the estimate")

                travel_list = estimate.get("travel", []) or []
                travel_cols = st.columns([1.4, 0.9, 1.1, 0.4])
                # Travel type/desc (narrow)
                with travel_cols[0]:
                    new_travel_type = st.text_input(
                        "Travel Type", value=ss.get("new_travel_type", ""), key="new_travel_type", max_chars=24
                    )
                # Distance/Units (very narrow)
                with travel_cols[1]:
                    new_travel_amt = st.number_input(
                        "Miles", min_value=0.0, value=float(ss.get("new_travel_amt", 0)), step=1.0, key="new_travel_amt"
                    )
                # Flat or per-mile? (medium)
            