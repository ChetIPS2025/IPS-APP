from __future__ import annotations

import difflib

import streamlit as st

from auth import current_role
from db import (
    fetch_by_match,
    fetch_by_match_admin,
    fetch_one,
    fetch_table,
    fetch_table_admin,
    fetch_table_with_order_fallback,
    insert_row_admin,
)

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

