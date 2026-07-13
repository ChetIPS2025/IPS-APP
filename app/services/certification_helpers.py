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

TWIC_CERT_TYPE = "TWIC"
TWIC_VALIDITY_YEARS = 5

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


def date_to_iso(value: object) -> str | None:
    """Serialize UI/date values for Supabase JSON payloads."""
    parsed = coerce_date(value)
    return parsed.isoformat() if parsed else None


def is_twic_certification_type(cert_type: object) -> bool:
    return str(cert_type or "").strip().upper() == TWIC_CERT_TYPE


def subtract_years(value: date, years: int) -> date:
    """Subtract calendar years, falling back to Feb 28 for invalid leap-day targets."""
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, month=2, day=28)


def twic_issue_date_from_expiration(expiration: object) -> date | None:
    """TWIC cards are valid for five years; derive issue date from expiration."""
    exp = coerce_date(expiration)
    if exp is None:
        return None
    return subtract_years(exp, TWIC_VALIDITY_YEARS)


def normalize_certification_ui_dates(ui: dict[str, Any]) -> dict[str, Any]:
    """Apply certification-type-specific date rules before persistence."""
    cert_type = ui.get("cert_type") or ui.get("certification_type")
    if not is_twic_certification_type(cert_type):
        return ui
    out = dict(ui)
    issue = twic_issue_date_from_expiration(out.get("expiration_date"))
    if issue is not None:
        out["issue_date"] = issue
    return out


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


def resolve_logged_in_employee_id(profile: dict[str, Any] | None = None) -> str:
    """Workforce id for the signed-in user (profile link, then email match)."""
    prof = profile if isinstance(profile, dict) else {}
    eid = str(prof.get("employee_id") or "").strip()
    if eid:
        return eid
    email = str(prof.get("email") or "").strip().lower()
    if not email:
        return ""
    from app.pages._core._data import load_employees
    for emp in load_employees():
        if str(emp.get("email") or "").strip().lower() == email:
            return str(emp.get("id") or "").strip()
    return ""


def can_manage_employee_certifications(role: str) -> bool:
    """Admin/supervisor/PM may view and edit all employee certifications."""
    from app.utils.permissions import can_view_field_certifications
    return can_view_field_certifications(role)


def can_delete_employee_certifications(role: str) -> bool:
    """Only administrators may delete employee certification records."""
    from app.utils.permissions import normalize_role
    return normalize_role(role) == "admin"


def certification_visible_to_user(
    cert: dict[str, Any],
    *,
    role: str,
    viewer_employee_id: str = "",
) -> bool:
    """True when the signed-in user may see this certification row."""
    if can_manage_employee_certifications(role):
        return True
    cert_emp = str(cert.get("employee_id") or "").strip()
    viewer_emp = str(viewer_employee_id or "").strip()
    return bool(cert_emp and viewer_emp and cert_emp == viewer_emp)


def can_view_certification_attachment(
    role: str,
    cert: dict[str, Any],
    *,
    current_employee_id: str = "",
) -> bool:
    """Gate attachment view/download by role until storage RLS is fully enforced."""
    from app.utils.permissions import can_view_field_certifications, normalize_role
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
