"""
User profiles and auth-linked employee records.

Identity model — keep two IDs separate for every user:

**App employee / user ID** (``employees.id``)
    Workforce record: roles, permissions, timekeeping, phone, billing class, status.
    Use for all in-app business data. Never pass to Supabase Auth admin APIs.

**Supabase Auth user ID** (``auth.users.id``)
    Login identity only: email, password, invites, session.
    Cached on the employee as ``employees.auth_user_id``. Always resolve via
    :func:`resolve_employee_auth_login` before password or invite actions — do not
    assume ``employees.id`` or a stale ``auth_user_id`` without verification.

**Profile** (``profiles``)
    App mirror of the auth user (``profiles.id`` == ``auth.users.id``), linked to the
    workforce row via ``profiles.employee_id``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

try:
    from app.db import (
        delete_auth_user_admin,
        fetch_by_match,
        fetch_by_match_admin,
        fetch_one,
        resolve_auth_user_id,
        set_login_password_admin,
        update_rows_admin,
    )
    from app.services.phase2_modules_service import delete_employee as delete_employee_row, normalize_employee
    from app.services.repository import (
        ServiceResult,
        clear_data_cache_for_table,
        fetch_by_id,
        fetch_rows,
        filter_payload_to_table,
        update_row,
    )
except ImportError:
    from db import (  # type: ignore
        delete_auth_user_admin,
        fetch_by_match,
        fetch_by_match_admin,
        fetch_one,
        resolve_auth_user_id,
        set_login_password_admin,
        update_rows_admin,
    )
    from services.phase2_modules_service import delete_employee as delete_employee_row, normalize_employee  # type: ignore
    from services.repository import (  # type: ignore
        ServiceResult,
        clear_data_cache_for_table,
        fetch_by_id,
        fetch_rows,
        filter_payload_to_table,
        update_row,
    )


def get_profile_by_user_id(user_id: str) -> dict[str, Any] | None:
    """Fetch ``profiles`` row for the authenticated user (auth.users id)."""
    if not user_id:
        return None
    return fetch_one("profiles", {"id": user_id})


def list_profiles(*, limit: int = 200) -> list[dict[str, Any]]:
    rows, _ = fetch_rows("profiles", limit=limit, order_by="full_name")
    return rows


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_profile_for_employee(employee_id: str, *, email: str = "") -> dict[str, Any] | None:
    """Admin-backed lookup so login resolution works under RLS and legacy schemas."""
    eid = str(employee_id or "").strip()
    em = str(email or "").strip().lower()
    if em:
        try:
            rows = fetch_by_match_admin("profiles", {"email": em}, limit=2) or []
            if len(rows) == 1:
                return rows[0]
            if rows:
                for row in rows:
                    if eid and str(row.get("employee_id") or "").strip() == eid:
                        return row
                return rows[0]
        except Exception:
            try:
                row = fetch_one("profiles", {"email": em})
                if row:
                    return row
            except Exception:
                pass
    if eid:
        try:
            rows = fetch_by_match_admin("profiles", {"employee_id": eid}, limit=1) or []
            if rows:
                return rows[0]
        except Exception:
            pass
    return None


def _employee_row(user_id: str) -> dict[str, Any] | None:
    return fetch_by_id("employees", user_id, normalize=normalize_employee)


def _count_time_entries(employee_id: str) -> int:
    eid = str(employee_id or "").strip()
    if not eid:
        return 0
    rows, err = fetch_rows("time_entries", limit=5000)
    if err:
        return 0
    return sum(1 for r in rows if str(r.get("employee_id") or "") == eid)


def _is_admin_role(role: object) -> bool:
    return str(role or "").strip().lower() in {"admin", "administrator"}


def _count_active_admins(*, exclude_employee_id: str = "") -> int:
    rows, _ = fetch_rows("profiles", limit=500)
    count = 0
    ex = str(exclude_employee_id or "").strip()
    for row in rows:
        if not _is_admin_role(row.get("role")):
            continue
        if row.get("is_active") is False:
            continue
        if str(row.get("status") or "Active").strip().lower() == "inactive":
            continue
        emp_id = str(row.get("employee_id") or "").strip()
        if ex and emp_id == ex:
            continue
        count += 1
    return count


@dataclass
class DeleteUserCheck:
    allowed: bool
    reason: str | None = None
    warnings: list[str] = field(default_factory=list)
    employee: dict[str, Any] | None = None
    profile: dict[str, Any] | None = None
    has_login: bool = False
    employee_linked: bool = False
    time_entry_count: int = 0


def resolve_employee_auth_login(
    employee_id: str,
    *,
    employee: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Resolve the Supabase Auth login for a workforce user.

    Returns both IDs explicitly so callers never confuse them:
    ``employee_id`` for app data; ``auth_user_id`` for login/password/invite only.
    """
    eid = str(employee_id or "").strip()
    employee_row = _employee_row(eid) or {}
    if not employee_row and isinstance(employee, dict):
        employee_row = dict(employee)
    profile = _find_profile_for_employee(
        eid,
        email=str(employee_row.get("email") or employee_row.get("work_email") or ""),
    )
    profile_row = profile or {}
    email = str(
        employee_row.get("email")
        or employee_row.get("work_email")
        or profile_row.get("email")
        or ""
    ).strip().lower()
    profile_id = str(profile_row.get("id") or "")
    stored_auth_id = str(employee_row.get("auth_user_id") or "").strip()
    auth_user_id = resolve_auth_user_id(
        email=email,
        auth_user_id=stored_auth_id,
        profile_id=profile_id,
        employee_id=eid,
    )
    profile_exists = bool(profile)
    auth_candidate = ""
    if email and not auth_user_id:
        try:
            from app.db import _find_auth_user_id_by_email
        except ImportError:
            from db import _find_auth_user_id_by_email  # type: ignore
        auth_candidate = _find_auth_user_id_by_email(email)
    auth_unlinked = bool(not auth_user_id and (profile_exists or auth_candidate))
    return {
        "employee_id": eid,
        "email": email,
        "auth_user_id": auth_user_id or auth_candidate,
        "profile_id": profile_id,
        "has_login": bool(auth_user_id),
        "stored_auth_user_id": stored_auth_id,
        "auth_link_stale": bool(
            stored_auth_id and auth_user_id and stored_auth_id != auth_user_id
        ),
        "auth_unlinked": auth_unlinked,
        "profile_exists": profile_exists,
    }


def get_user_delete_context(user_id: str) -> dict[str, Any]:
    """Summary fields for delete confirmation UI."""
    employee = _employee_row(user_id) or {}
    profile = _find_profile_for_employee(user_id, email=str(employee.get("email") or ""))
    login = resolve_employee_auth_login(user_id)
    email = login.get("email") or str(employee.get("email") or profile.get("email") or "")
    return {
        "user_id": user_id,
        "employee_id": str(user_id or "").strip(),
        "name": str(employee.get("name") or profile.get("full_name") or "—"),
        "role": str(employee.get("role") or profile.get("role") or "—"),
        "email": email or "—",
        "employee_linked": bool(employee.get("id")),
        "has_login": bool(login.get("has_login")),
        "last_login": str(employee.get("last_login") or "—"),
        "time_entry_count": _count_time_entries(user_id),
        "profile_id": str(login.get("profile_id") or ""),
        "auth_user_id": str(login.get("auth_user_id") or ""),
        "auth_link_stale": bool(login.get("auth_link_stale")),
    }


def can_delete_user(user_id: str, current_user: dict[str, Any] | None = None) -> DeleteUserCheck:
    """Whether deactivate/delete is allowed and any warnings to show."""
    uid = str(user_id or "").strip()
    if not uid:
        return DeleteUserCheck(allowed=False, reason="User id is required.")

    if uid.startswith("emp-"):
        return DeleteUserCheck(allowed=False, reason="Demo users cannot be deleted.")

    employee = _employee_row(uid)
    if not employee:
        return DeleteUserCheck(allowed=False, reason="User record not found.")

    profile = _find_profile_for_employee(uid, email=str(employee.get("email") or ""))
    warnings: list[str] = []

    actor = current_user or {}
    actor_profile_id = str(actor.get("id") or "").strip()
    actor_employee_id = str(actor.get("employee_id") or "").strip()
    if actor_profile_id and profile and str(profile.get("id") or "") == actor_profile_id:
        return DeleteUserCheck(allowed=False, reason="You cannot delete your own account.")
    if actor_employee_id and actor_employee_id == uid:
        return DeleteUserCheck(allowed=False, reason="You cannot delete your own account.")

    if profile and _is_admin_role(profile.get("role")) and profile.get("is_active") is not False:
        if _count_active_admins(exclude_employee_id=uid) == 0:
            return DeleteUserCheck(
                allowed=False,
                reason="Cannot deactivate the last active administrator.",
            )

    if profile and profile.get("is_active") is False:
        warnings.append("Login profile is already inactive.")

    if str(employee.get("status") or "").strip().lower() == "inactive":
        warnings.append("Employee record is already inactive.")

    if profile:
        warnings.append("Linked login profile will lose app access.")
    else:
        warnings.append("No login profile linked; only the employee record will be updated.")

    te_count = _count_time_entries(uid)
    if te_count:
        warnings.append(f"{te_count} time entry record(s) will be preserved.")

    return DeleteUserCheck(
        allowed=True,
        warnings=warnings,
        employee=employee,
        profile=profile,
        has_login=bool(profile and profile.get("id")),
        employee_linked=True,
        time_entry_count=te_count,
    )


def admin_reset_employee_password(
    employee_id: str,
    password: str,
    *,
    employee: dict[str, Any] | None = None,
    role: str = "employee",
    allowed_email_domain: str = "",
) -> ServiceResult:
    """
    Admin sets or resets another user's app login password via Supabase Auth Admin API.

    This is not for the signed-in user changing their own password.
    """
    if not can_manage_user_actions():
        return ServiceResult(ok=False, error="You do not have permission to reset user passwords.")

    eid = str(employee_id or "").strip()
    if not eid:
        return ServiceResult(ok=False, error="Employee id is required.")

    emp = employee if employee is not None else (_employee_row(eid) or {})
    login = resolve_employee_auth_login(eid)
    email = str(login.get("email") or emp.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return ServiceResult(ok=False, error="Add a valid work email before resetting the password.")
    if "indfustrial" in email:
        return ServiceResult(ok=False, error="Check spelling of company domain (found 'indfustrial').")

    allow = str(allowed_email_domain or "").strip().lower()
    if allow:
        dom = email.split("@", 1)[1] if "@" in email else ""
        if dom != allow:
            return ServiceResult(ok=False, error="Email domain is not allowed for app login.")

    pw = str(password or "").strip()
    if len(pw) < 6:
        return ServiceResult(ok=False, error="Password must be at least 6 characters.")

    had_login = bool(login.get("has_login"))
    try:
        auth_id = set_login_password_admin(
            email=email,
            password=pw,
            auth_user_id=str(login.get("auth_user_id") or ""),
            profile_id=str(login.get("profile_id") or ""),
            employee_id=eid,
            full_name=str(emp.get("name") or "").strip(),
            role=role,
        )
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc).strip() or "Could not reset this user's password.")

    clear_data_cache_for_table("users")
    return ServiceResult(
        ok=True,
        data={
            "email": email,
            "auth_user_id": auth_id,
            "created_login": not had_login,
            "reset_password": had_login,
        },
    )


def can_manage_user_actions(actor: dict[str, Any] | None = None) -> bool:
    """Admin or supervisor may activate, deactivate, or archive users."""
    try:
        from app.auth import current_role
        from app.utils.permissions import normalize_role
    except ImportError:
        from auth import current_role  # type: ignore
        from utils.permissions import normalize_role  # type: ignore
    _ = actor
    role = normalize_role(current_role())
    return role in {"admin", "supervisor"}


def can_edit_employee_profile(actor: dict[str, Any] | None = None) -> bool:
    """Roles allowed to update employee/user profile fields (including hire date)."""
    try:
        from app.auth import current_role
        from app.utils.permissions import normalize_role
    except ImportError:
        from auth import current_role  # type: ignore
        from utils.permissions import normalize_role  # type: ignore
    _ = actor
    role = normalize_role(current_role())
    return role in {"admin", "supervisor", "project manager"}


def activate_user(
    user_id: str,
    *,
    activated_by: str | None = None,
    actor: dict[str, Any] | None = None,
) -> ServiceResult:
    """Restore an inactive or deleted user to Active status."""
    _ = actor
    uid = str(user_id or "").strip()
    if not uid:
        return ServiceResult(ok=False, error="User id is required.")
    if uid.startswith("emp-"):
        return ServiceResult(ok=False, error="Demo users cannot be modified.")

    employee = _employee_row(uid)
    if not employee:
        return ServiceResult(ok=False, error="User record not found.")

    profile = _find_profile_for_employee(uid, email=str(employee.get("email") or ""))
    activated_by_id = str(activated_by or "").strip() or None

    emp_payload: dict[str, Any] = {
        "is_active": True,
        "status": "Active",
        "deleted_at": None,
        "deactivation_reason": None,
    }
    if activated_by_id:
        emp_payload["deleted_by"] = None
    emp_result = update_row("employees", emp_payload, {"id": uid})
    if not emp_result.ok:
        return emp_result

    auth_warning: str | None = None
    if profile and profile.get("id"):
        prof_payload: dict[str, Any] = {
            "is_active": True,
            "status": "Active",
            "deleted_at": None,
            "deactivation_reason": None,
        }
        prof_payload = filter_payload_to_table("profiles", prof_payload)
        try:
            update_rows_admin("profiles", prof_payload, {"id": str(profile["id"])})
        except Exception as exc:
            auth_warning = f"User activated, but profile update failed: {exc}"

    clear_data_cache_for_table("users")
    data: dict[str, Any] = {"employee_id": uid}
    if auth_warning:
        data["warning"] = auth_warning
    return ServiceResult(ok=True, data=data)


def soft_delete_user(
    user_id: str,
    *,
    reason: str | None = None,
    deleted_by: str | None = None,
    actor: dict[str, Any] | None = None,
) -> ServiceResult:
    """Archive a user (soft delete). Historical records are preserved."""
    check = can_delete_user(user_id, current_user=actor)
    if not check.allowed:
        return ServiceResult(ok=False, error=check.reason or "Cannot delete user.")

    uid = str(user_id or "").strip()
    now = _utc_now_iso()
    reason_text = str(reason or "Deleted by administrator").strip() or None
    deleted_by_id = str(deleted_by or "").strip() or None
    profile = check.profile

    emp_payload: dict[str, Any] = {
        "is_active": False,
        "status": "Deleted",
        "deleted_at": now,
        "deactivation_reason": reason_text,
    }
    if deleted_by_id:
        emp_payload["deleted_by"] = deleted_by_id

    emp_result = update_row("employees", emp_payload, {"id": uid})
    if not emp_result.ok:
        return emp_result

    auth_warning: str | None = None
    if profile and profile.get("id"):
        prof_payload: dict[str, Any] = {
            "is_active": False,
            "status": "Deleted",
            "deleted_at": now,
            "deactivation_reason": reason_text,
        }
        if deleted_by_id:
            prof_payload["deleted_by"] = deleted_by_id
        prof_payload = filter_payload_to_table("profiles", prof_payload)
        try:
            update_rows_admin("profiles", prof_payload, {"id": str(profile["id"])})
        except Exception as exc:
            auth_warning = f"User archived, but profile update failed: {exc}"

    clear_data_cache_for_table("users")
    data: dict[str, Any] = {
        "employee_id": uid,
        "profile_id": str(profile.get("id") or "") if profile else "",
    }
    if auth_warning:
        data["warning"] = auth_warning
    return ServiceResult(ok=True, data=data)


def deactivate_user(
    user_id: str,
    *,
    reason: str | None = None,
    deleted_by: str | None = None,
    actor: dict[str, Any] | None = None,
) -> ServiceResult:
    """Soft-delete: deactivate employee + linked profile; preserve historical data."""
    check = can_delete_user(user_id, current_user=actor)
    if not check.allowed:
        return ServiceResult(ok=False, error=check.reason or "Cannot deactivate user.")

    uid = str(user_id or "").strip()
    now = _utc_now_iso()
    reason_text = str(reason or "Deactivated by administrator").strip() or None
    deleted_by_id = str(deleted_by or "").strip() or None

    profile = check.profile

    emp_payload: dict[str, Any] = {
        "is_active": False,
        "status": "Inactive",
        "deleted_at": now,
        "deactivation_reason": reason_text,
    }
    if deleted_by_id:
        emp_payload["deleted_by"] = deleted_by_id

    emp_result = update_row("employees", emp_payload, {"id": uid})
    if not emp_result.ok:
        return emp_result

    auth_warning: str | None = None
    if profile and profile.get("id"):
        prof_payload: dict[str, Any] = {
            "is_active": False,
            "status": "Inactive",
            "deleted_at": now,
            "deactivation_reason": reason_text,
        }
        if deleted_by_id:
            prof_payload["deleted_by"] = deleted_by_id
        prof_payload = filter_payload_to_table("profiles", prof_payload)
        try:
            update_rows_admin("profiles", prof_payload, {"id": str(profile["id"])})
        except Exception as exc:
            auth_warning = f"Employee deactivated, but profile update failed: {exc}"

    clear_data_cache_for_table("users")
    data: dict[str, Any] = {
        "employee_id": uid,
        "profile_id": str(profile.get("id") or "") if profile else "",
    }
    if auth_warning:
        data["warning"] = auth_warning
    elif profile:
        data["warning"] = (
            "Supabase auth user still exists but app access is disabled via inactive profile."
        )
    return ServiceResult(ok=True, data=data)


def hard_delete_user(
    user_id: str,
    *,
    delete_employee: bool = False,
    deleted_by: str | None = None,
    actor: dict[str, Any] | None = None,
) -> ServiceResult:
    """Admin-only permanent delete of login profile/auth user; employee optional."""
    del deleted_by  # reserved for audit if hard-delete logging is added later
    uid = str(user_id or "").strip()
    if not uid:
        return ServiceResult(ok=False, error="User id is required.")
    if uid.startswith("emp-"):
        return ServiceResult(ok=False, error="Demo users cannot be deleted.")

    check = can_delete_user(user_id, current_user=actor)
    if not check.allowed:
        return ServiceResult(ok=False, error=check.reason or "Cannot delete user.")

    profile = check.profile
    employee = check.employee or {}
    auth_deleted = False
    auth_warning: str | None = None

    resolved_auth_id = str(resolve_employee_auth_login(uid).get("auth_user_id") or "").strip()
    if resolved_auth_id:
        profile_id = resolved_auth_id
        try:
            delete_auth_user_admin(user_id=profile_id)
            auth_deleted = True
        except Exception as exc:
            auth_warning = str(exc)
            try:
                update_rows_admin(
                    "profiles",
                    {"is_active": False, "status": "Inactive", "deleted_at": _utc_now_iso()},
                    {"id": profile_id},
                )
            except Exception:
                pass

    if delete_employee:
        result = delete_employee_row(uid)
        if not result.ok:
            msg = result.error or "Could not delete employee record."
            if auth_deleted:
                msg = f"Login removed, but employee delete failed: {msg}"
            return ServiceResult(ok=False, error=msg, data={"auth_deleted": auth_deleted})

    clear_data_cache_for_table("users")
    warnings: list[str] = []
    if auth_warning:
        warnings.append(
            f"Auth user could not be removed: {auth_warning}. Profile marked inactive instead."
        )
    if not delete_employee and check.employee:
        warnings.append("Employee workforce record was preserved.")
    return ServiceResult(
        ok=True,
        data={
            "auth_deleted": auth_deleted,
            "employee_deleted": delete_employee,
            "warnings": warnings,
        },
    )


__all__ = [
    "DeleteUserCheck",
    "activate_user",
    "can_delete_user",
    "can_edit_employee_profile",
    "can_manage_user_actions",
    "deactivate_user",
    "get_profile_by_user_id",
    "get_user_delete_context",
    "hard_delete_user",
    "admin_reset_employee_password",
    "resolve_employee_auth_login",
    "list_profiles",
    "soft_delete_user",
]
