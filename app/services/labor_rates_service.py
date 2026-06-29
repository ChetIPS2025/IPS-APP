"""Default labor rate CRUD for estimates and job costing (no Streamlit)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    from app.services.repository import (
        ServiceResult,
        fetch_rows,
        insert_row,
        update_row,
    )
except ImportError:
    from services.repository import (  # type: ignore
        ServiceResult,
        fetch_rows,
        insert_row,
        update_row,
    )

_TABLE = "labor_rates"
OT_MULTIPLIER = 1.5


def _str(value: Any) -> str:
    return str(value or "").strip()


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_classification(name: str) -> str:
    return _str(name)


def _classification_key(name: str) -> str:
    return _normalize_classification(name).upper()


def list_labor_rates(*, active_only: bool = False) -> list[dict[str, Any]]:
    rows, _ = fetch_rows(_TABLE, limit=5000, order_by="classification")
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if active_only and row.get("is_active") is False:
            continue
        out.append(normalize_labor_rate_row(row))
    return out


def normalize_labor_rate_row(row: dict[str, Any]) -> dict[str, Any]:
    st_rate = _num(row.get("st_rate"))
    ot_rate = _num(row.get("ot_rate"))
    if not ot_rate and st_rate:
        ot_rate = st_rate * OT_MULTIPLIER
    return {
        "id": _str(row.get("id")),
        "classification": _str(row.get("classification")),
        "role_name": _str(row.get("role_name") or row.get("classification")),
        "st_rate": st_rate,
        "ot_rate": ot_rate,
        "is_active": row.get("is_active") is not False,
        "updated_at": row.get("updated_at"),
    }


def find_labor_rate_by_classification(classification: str) -> dict[str, Any] | None:
    key = _classification_key(classification)
    if not key:
        return None
    for row in list_labor_rates():
        if _classification_key(row.get("classification")) == key:
            return row
    return None


def make_unique_classification(base_value: str, existing_rows: list[dict[str, Any]]) -> str:
    base = _normalize_classification(base_value)
    existing = {_classification_key(r.get("classification")) for r in existing_rows}
    if _classification_key(base) not in existing:
        return base
    i = 2
    while True:
        candidate = f"{base}_{i}"
        if _classification_key(candidate) not in existing:
            return candidate
        i += 1


def save_labor_rate(
    *,
    classification: str,
    st_rate: float,
    ot_rate: float | None = None,
    is_active: bool = True,
    rate_id: str | None = None,
) -> ServiceResult:
    """Create or update a default labor rate by id or classification."""
    name = _normalize_classification(classification)
    if not name:
        return ServiceResult(ok=False, error="Labor classification is required.")
    st = _num(st_rate)
    ot = _num(ot_rate) if ot_rate is not None else (st * OT_MULTIPLIER if st else 0.0)
    payload = {
        "classification": name,
        "st_rate": st,
        "ot_rate": ot,
        "is_active": bool(is_active),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    rid = _str(rate_id)
    if rid:
        return update_row(_TABLE, payload, {"id": rid})

    existing = find_labor_rate_by_classification(name)
    if existing and existing.get("id"):
        return update_row(_TABLE, payload, {"id": existing["id"]})

    return insert_row(_TABLE, payload)


def upsert_default_labor_rate(
    classification: str,
    st_rate: float,
    ot_rate: float,
    *,
    is_active: bool = True,
) -> ServiceResult:
    """Update the default rate for a role; used when saving from Estimate Cost Builder."""
    return save_labor_rate(
        classification=classification,
        st_rate=st_rate,
        ot_rate=ot_rate,
        is_active=is_active,
    )


def save_default_rates_from_lines(lines: list[dict[str, Any]]) -> ServiceResult:
    """Persist default rates for one or more roles (future estimates only)."""
    if not lines:
        return ServiceResult(ok=True, data={"saved": 0})
    saved = 0
    last_err = ""
    for line in lines:
        role = _str(line.get("role_name") or line.get("classification") or line.get("labor_type"))
        if not role:
            continue
        result = upsert_default_labor_rate(
            role,
            _num(line.get("st_rate")),
            _num(line.get("ot_rate")),
        )
        if not result.ok:
            last_err = str(result.error or "Save failed.")
            break
        saved += 1
    if saved < len(lines) and last_err:
        return ServiceResult(
            ok=False,
            error=last_err,
            data={"saved": saved},
        )
    return ServiceResult(ok=True, data={"saved": saved})
