"""Certification status calculation and display helpers."""

from __future__ import annotations

import html
from datetime import date, datetime
from typing import Any

CERT_TYPES_NO_EXPIRATION = (
    "Site Orientation",
    "Fire Watch",
    "Hot Work",
)

CERT_STATUS_VALUES = (
    "Active",
    "Expiring Soon",
    "Expired",
    "Missing",
    "Not Required",
)


def _parse_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def compute_certification_status(row: dict[str, Any]) -> str:
    """Derive compliance status from expiration unless manually set to Not Required."""
    stored = str(row.get("status") or "").strip()
    if stored == "Not Required":
        return "Not Required"

    cert_type = str(row.get("cert_type") or row.get("certification_type") or "").strip()
    exp_raw = row.get("expiration_date")
    exp = _parse_date(exp_raw)

    if exp is None:
        if cert_type in CERT_TYPES_NO_EXPIRATION:
            return "Not Required"
        return "Missing"

    today = date.today()
    if exp < today:
        return "Expired"
    if (exp - today).days <= 30:
        return "Expiring Soon"
    return "Active"


def days_until_expiration(value: object) -> str:
    exp = _parse_date(value)
    if exp is None:
        return "—"
    delta = (exp - date.today()).days
    if delta < 0:
        return f"Expired {abs(delta)} day(s) ago"
    if delta == 0:
        return "Expires today"
    return f"{delta} day(s) remaining"


def cert_status_pill_html(status: str) -> str:
    cls_map = {
        "Active": "ips-cert-status-active",
        "Expiring Soon": "ips-cert-status-expiring-soon",
        "Expired": "ips-cert-status-expired",
        "Missing": "ips-cert-status-missing",
        "Not Required": "ips-cert-status-not-required",
    }
    label = str(status or "—").strip() or "—"
    cls = cls_map.get(label, "ips-cert-status-not-required")
    return (
        f'<span class="ips-cert-status-pill {cls}">{html.escape(label)}</span>'
    )


def certification_alerts_counts(certs: list[dict[str, Any]]) -> tuple[int, int]:
    expired = 0
    expiring = 0
    for cert in certs:
        status = compute_certification_status(cert)
        if status == "Expired":
            expired += 1
        elif status == "Expiring Soon":
            expiring += 1
    return expired, expiring
