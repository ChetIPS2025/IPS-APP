"""Billing classification vs app permission role for employees."""

from __future__ import annotations

from typing import Any

try:
    from app.services.lookup_service import load_lookup_values
    from app.services.repository import fetch_rows
    from app.utils.constants import ROLES
    from app.utils.permissions import normalize_role
except ImportError:
    from services.lookup_service import load_lookup_values  # type: ignore
    from services.repository import fetch_rows  # type: ignore
    from utils.constants import ROLES  # type: ignore
    from utils.permissions import normalize_role  # type: ignore

_PERMISSION_LABELS: frozenset[str] = frozenset(ROLES)
_PERMISSION_ALIASES: dict[str, str] = {
    "admin": "Admin",
    "administrator": "Admin",
    "supervisor": "Supervisor",
    "project manager": "Project Manager",
    "project_manager": "Project Manager",
    "pm": "Project Manager",
    "manager": "Project Manager",
    "estimator": "Project Manager",
    "employee": "Employee",
    "viewer": "Viewer",
}

_FALLBACK_BILLING_CLASSES = (
    "General Laborer",
    "Welder",
    "Pipefitter",
    "Foreman",
    "Superintendent",
)


def permission_role_options() -> list[str]:
    opts, _ = load_lookup_values("user_roles")
    return list(opts) if opts else list(ROLES)


def is_permission_role_label(raw: object) -> bool:
    return bool(canonical_permission_label(str(raw or "")))


def canonical_permission_label(raw: str) -> str:
    text = str(raw or "").strip()
    if not text or text in {"—", "None", "-"}:
        return ""
    alias = _PERMISSION_ALIASES.get(text.casefold())
    if alias:
        return alias
    for label in _PERMISSION_LABELS:
        if label.casefold() == text.casefold():
            return label
    return ""


def resolve_employee_roles(row: dict[str, Any]) -> tuple[str, str]:
    """Return (permission_role_label, billing_class) from a raw employees row."""
    role_raw = str(row.get("role") or "").strip()
    trade_raw = str(row.get("trade") or "").strip()
    position_raw = str(row.get("position") or "").strip()

    if is_permission_role_label(role_raw):
        perm = canonical_permission_label(role_raw) or "Employee"
        billing = _clean_billing_label(trade_raw)
        if not billing and position_raw and not is_permission_role_label(position_raw):
            billing = _clean_billing_label(position_raw)
        return perm, billing or "—"

    if role_raw and role_raw not in {"—", "None", "-"}:
        billing = _clean_billing_label(trade_raw) or role_raw
        return "Employee", billing

    billing = _clean_billing_label(trade_raw)
    return "Employee", billing or "—"


def _clean_billing_label(raw: str) -> str:
    text = str(raw or "").strip()
    if not text or text in {"—", "None", "-"}:
        return ""
    return text


def options_with_current(options: list[str], current: object) -> list[str]:
    cur = _clean_billing_label(str(current or ""))
    if not cur:
        return list(options)
    if any(cur.casefold() == opt.casefold() for opt in options):
        return list(options)
    return [cur, *options]


def billing_classification_options() -> list[str]:
    seen: set[str] = set()
    options: list[str] = []

    def add(value: object) -> None:
        label = _clean_billing_label(str(value or ""))
        if not label:
            return
        key = label.casefold()
        if key in seen:
            return
        seen.add(key)
        options.append(label)

    try:
        rows, _ = fetch_rows("labor_rates", order_by="classification")
        for row in rows:
            add(row.get("classification"))
    except Exception:
        pass

    try:
        emp_rows, _ = fetch_rows("employees", limit=500, order_by="name")
        for row in emp_rows:
            add(row.get("trade"))
            role_raw = str(row.get("role") or "").strip()
            if role_raw and not is_permission_role_label(role_raw):
                add(role_raw)
    except Exception:
        pass

    for label in _FALLBACK_BILLING_CLASSES:
        add(label)

    return sorted(options, key=str.casefold)


def auth_role_from_permission_label(permission_role: str) -> str:
    """Map UI permission label to profiles/auth role slug."""
    role_norm = normalize_role(str(permission_role or "employee"))
    if role_norm in {"pm", "estimator", "project manager", "supervisor"}:
        return "manager"
    if role_norm in {"admin", "viewer", "employee", "manager"}:
        return role_norm
    return "employee"


def sync_linked_profile_permission_role(
    employee_id: str,
    permission_role: str,
    *,
    email: str = "",
) -> str | None:
    """Update linked profile role when employee permission changes. Returns warning or None."""
    try:
        from app.db import update_rows_admin
        from app.services.repository import clear_all_data_caches, filter_payload_to_table
        from app.services.users_service import _find_profile_for_employee
    except ImportError:
        from db import update_rows_admin  # type: ignore
        from services.repository import clear_all_data_caches, filter_payload_to_table  # type: ignore
        from services.users_service import _find_profile_for_employee  # type: ignore

    eid = str(employee_id or "").strip()
    if not eid:
        return None

    profile = _find_profile_for_employee(eid, email=str(email or "").strip())
    if not profile or not profile.get("id"):
        return None

    auth_role = auth_role_from_permission_label(permission_role)
    payload = filter_payload_to_table("profiles", {"role": auth_role})
    try:
        update_rows_admin("profiles", payload, {"id": str(profile["id"])})
        clear_all_data_caches()
    except Exception as exc:
        return f"User saved, but login permission update failed: {exc}"
    return None


__all__ = [
    "auth_role_from_permission_label",
    "billing_classification_options",
    "canonical_permission_label",
    "is_permission_role_label",
    "options_with_current",
    "permission_role_options",
    "resolve_employee_roles",
    "sync_linked_profile_permission_role",
]
