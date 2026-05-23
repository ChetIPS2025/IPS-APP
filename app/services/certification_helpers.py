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
    return coerce_date(value)


def coerce_date(value: object) -> date | None:
    if value is None or value == "" or value == "—":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%b %d, %Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
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


def cert_document_pill_html(attached: bool) -> str:
    if attached:
        return '<span class="ips-cert-doc-pill ips-cert-doc-attached">Attached</span>'
    return '<span class="ips-cert-doc-empty">—</span>'


def can_view_certification_attachment(
    role: str,
    cert: dict[str, Any],
    *,
    current_employee_id: str = "",
) -> bool:
    """Gate attachment view/download by role until storage RLS is fully enforced."""
    try:
        from app.utils.permissions import can_view_field_certifications, normalize_role
    except ImportError:
        from utils.permissions import can_view_field_certifications, normalize_role  # type: ignore

    norm = normalize_role(role)
    if norm == "admin":
        return True
    if norm == "viewer":
        return False
    if can_view_field_certifications(role):
        return True
    if norm == "employee":
        cert_emp = str(cert.get("employee_id") or "").strip()
        viewer_emp = str(current_employee_id or "").strip()
        return bool(cert_emp and viewer_emp and cert_emp == viewer_emp)
    return False
