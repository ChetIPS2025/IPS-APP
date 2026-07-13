from __future__ import annotations

import json
import re

import streamlit as st

from app.auth import current_profile, current_role
from app.db import fetch_table, fetch_table_admin

from app.estimate.calculations import _is_missing_number

FINAL_STATUSES = frozenset({"approved", "awarded"})


def blank_estimate() -> dict:
    out = {
        "quote_number": "",
        "customer_id": None,
        "customer_location_id": None,
        "customer_contact_id": None,
        "contact_name": "",
        "estimate_description": "",
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
        "scope_fields_updated_at": "",
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
    cache_key = "_ips_estimates_physical_columns_v2"
    cached = st.session_state.get(cache_key)
    if isinstance(cached, frozenset):
        return cached
    try:
        from app.db_table_columns import SCHEMA_INTROSPECTION_COLUMNS
    except ImportError:
        from db_table_columns import SCHEMA_INTROSPECTION_COLUMNS  # type: ignore
    try:
        rows = fetch_table_admin("estimates", columns=SCHEMA_INTROSPECTION_COLUMNS, limit=1)
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


_NARRATIVE_SCALAR_KEYS: tuple[str, ...] = (
    "scope_of_work",
    "exclusions",
    "additional_charges",
    "customer_responsibilities",
)


def merge_estimate_narrative_scalars_from_row(row: dict, loaded: dict) -> None:
    """
    Merge long narrative text fields into the in-memory estimate dict.

    Prefer non-empty values from denormalized row columns; when a column is null or blank,
    keep the value already present on ``loaded`` (typically from ``estimate_json``).
    """
    if not isinstance(loaded, dict):
        return
    for key in _NARRATIVE_SCALAR_KEYS:
        rv = row.get(key)
        jv = loaded.get(key)
        if rv is not None and str(rv).strip():
            loaded[key] = str(rv)
        elif jv is not None and str(jv).strip():
            loaded[key] = str(jv)
        else:
            loaded[key] = ""


def merge_estimate_row_scalar_fields_into_editor(row: dict, loaded: dict) -> None:
    """Overlay denormalized estimate row columns after ``estimate_json`` is merged."""
    if "estimate_description" in row:
        v = row.get("estimate_description")
        loaded["estimate_description"] = "" if v is None else str(v).strip()
    if "prepared_by_name" in row:
        v = row.get("prepared_by_name")
        loaded["prepared_by_name"] = "" if v is None else str(v).strip()
    if "prepared_by_id" in row:
        v = row.get("prepared_by_id")
        loaded["prepared_by_id"] = _normalize_prepared_by_id_value("" if v is None else str(v))
    if "customer_location_id" in row:
        v = row.get("customer_location_id")
        if v is None or str(v).strip() == "":
            loaded["customer_location_id"] = None
        else:
            loaded["customer_location_id"] = str(v).strip()


def _payload_customer_location_for_db(est: dict) -> dict:
    """Subset of ``estimates`` row when ``customer_location_id`` exists."""
    cols = _estimate_table_column_names()
    if "customer_location_id" not in cols:
        return {}
    raw = est.get("customer_location_id")
    if raw is None or str(raw).strip() == "":
        return {"customer_location_id": None}
    return {"customer_location_id": str(raw).strip()}


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

