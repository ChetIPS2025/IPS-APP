"""Estimate expiration date rules — default +30 days from estimate date."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

ESTIMATE_EXPIRATION_DAYS = 30
_EXPIRATION_MANUAL_JSON_KEY = "expiration_manual_override"


def _coerce_date(value: object) -> date | None:
    if isinstance(value, date) and not hasattr(value, "hour"):
        return value
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_estimate_json(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            import json

            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def estimate_date_for_expiration(row: dict[str, Any]) -> date | None:
    """Estimate date used for default expiration (matches list/detail display fallbacks)."""
    for key in ("estimate_date", "created_at"):
        parsed = _coerce_date(row.get(key))
        if parsed:
            return parsed
    return None


def default_expiration_date(estimate_date: object) -> date | None:
    est_d = _coerce_date(estimate_date)
    if not est_d:
        return None
    return est_d + timedelta(days=ESTIMATE_EXPIRATION_DAYS)


def expiration_is_manual_override(row: dict[str, Any]) -> bool:
    ej = _parse_estimate_json(row.get("estimate_json"))
    return bool(ej.get(_EXPIRATION_MANUAL_JSON_KEY))


def stored_expiration_date(row: dict[str, Any]) -> date | None:
    for key in ("expiration_date", "valid_through"):
        parsed = _coerce_date(row.get(key))
        if parsed:
            return parsed
    return None


def effective_expiration_date(row: dict[str, Any]) -> date | None:
    stored = stored_expiration_date(row)
    if stored:
        return stored
    return default_expiration_date(estimate_date_for_expiration(row))


def effective_expiration_iso(row: dict[str, Any]) -> str:
    resolved = effective_expiration_date(row)
    return resolved.isoformat() if resolved else ""


def _format_date_display(value: date | object | None) -> str:
    if not value:
        return "—"
    try:
        from app.utils.formatting import fmt_date
    except ImportError:
        from utils.formatting import fmt_date  # type: ignore
    return fmt_date(value)


def format_estimate_date(row: dict[str, Any]) -> str:
    return _format_date_display(estimate_date_for_expiration(row))


def format_effective_expiration(row: dict[str, Any]) -> str:
    return _format_date_display(effective_expiration_date(row))


def with_effective_expiration(row: dict[str, Any]) -> dict[str, Any]:
    """Return estimate dict with resolved expiration_date for exports and previews."""
    out = dict(row)
    exp = effective_expiration_date(row)
    if exp:
        out["expiration_date"] = exp.isoformat()
    est_d = estimate_date_for_expiration(row)
    if est_d:
        out.setdefault("estimate_date", est_d.isoformat())
    return out


def format_proposal_long_date(value: date | object | None) -> str:
    """Long US date for customer proposal documents."""
    parsed = _coerce_date(value)
    if not parsed:
        return ""
    return parsed.strftime("%B %d, %Y")


def resolve_expiration_for_save(
    *,
    estimate_date: object,
    expiration_date: object,
    manual_override: bool,
) -> tuple[str | None, bool]:
    """Return persisted expiration ISO date and manual-override flag."""
    est_d = _coerce_date(estimate_date)
    exp_d = _coerce_date(expiration_date)
    manual = bool(manual_override)

    if not manual and est_d:
        exp_d = default_expiration_date(est_d)
    elif exp_d is None and est_d:
        exp_d = default_expiration_date(est_d)

    exp_iso = exp_d.isoformat() if exp_d else None
    return exp_iso, manual


def ensure_estimate_expiration_persisted(estimate_id: str) -> bool:
    """Backfill missing expiration_date in DB from estimate_date + 30 days."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return False
    try:
        from app.services.repository import fetch_by_id, update_row
    except ImportError:
        from services.repository import fetch_by_id, update_row  # type: ignore

    row = fetch_by_id("estimates", eid)
    if not row:
        return False
    if stored_expiration_date(row):
        return False
    est_d = estimate_date_for_expiration(row)
    if not est_d:
        return False
    exp_d = default_expiration_date(est_d)
    if not exp_d:
        return False
    result = update_row("estimates", {"expiration_date": exp_d.isoformat()}, {"id": eid})
    return bool(result.ok)
