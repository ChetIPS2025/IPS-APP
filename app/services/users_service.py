"""
User profiles and auth-linked employee records.

Users page rows are primarily ``employees`` records; login access lives on ``profiles``
linked via ``profiles.employee_id``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

try:
    from app.db import delete_auth_user_admin, fetch_by_match, fetch_one, update_rows_admin
    from app.services.phase2_modules_service import delete_employee as delete_employee_row, normalize_employee
    from app.services.repository import (
        ServiceResult,
        clear_all_data_caches,
        fetch_by_id,
        fetch_rows,
        filter_payload_to_table,
        update_row,
    )
except ImportError:
    from db import delete_auth_user_admin, fetch_by_match, fetch_one, update_rows_admin  # type: ignore
    from services.phase2_modules_service import delete_employee as delete_employee_row, normalize_employee  # type: ignore
    from services.repository import (  # type: ignore
        ServiceResult,
        clear_all_data_caches,
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
    eid = str(employee_id or "").strip()
    if eid:
        try:
            rows = fetch_by_match("profiles", {"employee_id": eid}, limit=1) or []
            if rows:
                return rows[0]
        except Exception:
            pass
    em = str(email or "").strip().lower()
    if em:
        try:
            row = fetch_one("profiles", {"email": em})
            if row:
                return row
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


def get_user_delete_context(user_id: str) -> dict[str, Any]:
    """Summary fields for delete confirmation UI."""
    employee = _employee_row(user_id) or {}
    profile = _find_profile_for_employee(user_id, email=str(employee.get("email") or ""))
    return {
        "user_id": user_id,
        "name": str(employee.get("name") or profile.get("full_name") or "—"),
        "role": str(employee.get("role") or profile.get("role") or "—"),
        "email": str(employee.get("email") or profile.get("email") or "—"),
        "employee_linked": bool(employee.get("id")),
        "has_login": bool(profile and profile.get("id")),
        "last_login": str(employee.get("last_login") or "—"),
        "time_entry_count": _count_time_entries(user_id),
        "profile_id": str(profile.get("id") or "") if profile else "",
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

    clear_all_data_caches()
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

    clear_all_data_caches()
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

    clear_all_data_caches()
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
    auth_deleted = False
    auth_warning: str | None = None

    if profile and profile.get("id"):
        profile_id = str(profile["id"])
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

    clear_all_data_caches()
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
    "can_manage_user_actions",
    "deactivate_user",
    "get_profile_by_user_id",
    "get_user_delete_context",
    "hard_delete_user",
    "list_profiles",
    "soft_delete_user",
]
