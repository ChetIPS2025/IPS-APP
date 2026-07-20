"""Paginated Users/Employees directory list and filter metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from app.components.table_filters import apply_column_filters, get_column_filter_values
from app.pages._core.page_data_cache import page_data_cache_get
from app.services.phase2_modules_service import normalize_employee

__all__ = [
    "PeoplePage",
    "PeoplePermissions",
    "build_people_permissions",
    "invalidate_people_directory_cache",
    "list_people_page",
    "load_people_filter_options",
]

_PEOPLE_LIST_COLUMNS = (
    "id,name,full_name,email,phone,phone_number,mobile,cell,contact_phone,"
    "employee_number,trade,billing_class,role,permission_role,is_employee,"
    "status,is_active,last_login,deleted_at,is_deleted,created_at,department,"
    "position,hire_date,username,member_since,notes"
)

_TABLE_KEY = "employees_list"
_FILTER_FIELDS = ("billing_class", "permission_role", "employee_type", "status")
_SEARCH_KEY = "employees_list_search"


@dataclass(frozen=True)
class PeoplePermissions:
    role: str
    can_manage_actions: bool
    can_edit_profile: bool
    can_view_hr_documents: bool
    can_manage_auth_login: bool


@dataclass(frozen=True)
class PeoplePage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    filter_options: dict[str, list[str]]
    is_live: bool
    warning: str | None = None


def build_people_permissions(*, role: str) -> PeoplePermissions:
    from app.services.users_service import can_edit_employee_profile, can_manage_user_actions
    from app.utils.permissions import can_view_hr_documents, normalize_role

    role_norm = normalize_role(role)
    can_manage = can_manage_user_actions()
    return PeoplePermissions(
        role=role_norm,
        can_manage_actions=can_manage,
        can_edit_profile=can_edit_employee_profile(),
        can_view_hr_documents=can_view_hr_documents(role_norm),
        can_manage_auth_login=can_manage,
    )


def invalidate_people_directory_cache() -> None:
    from app.pages._core._data import _bump_employees_catalog_data_version
    from app.pages._core.page_data_cache import clear_page_data_cache_prefix

    _bump_employees_catalog_data_version()
    clear_page_data_cache_prefix("people_")


def _normalize_user_status(raw: object) -> str:
    s = str(raw or "").strip().lower()
    if s in ("", "active", "enabled"):
        return "Active"
    if s in ("inactive", "disabled"):
        return "Inactive"
    if s in ("deleted", "archived"):
        return "Deleted"
    if s in ("locked", "blocked"):
        return "Locked"
    if s in ("pending", "invited"):
        return "Pending"
    label = str(raw or "").strip()
    return label if label else "Active"


def user_is_deleted(user: dict[str, Any]) -> bool:
    if user.get("is_deleted") is True:
        return True
    if str(user.get("deleted_at") or "").strip():
        return True
    return _normalize_user_status(user.get("status")) == "Deleted"


def user_filter_status(user: dict[str, Any]) -> str:
    if user_is_deleted(user):
        return "Deleted"
    return _normalize_user_status(user.get("status"))


def filter_users_by_deleted_visibility(
    rows: list[dict[str, Any]],
    *,
    status_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    selected = [str(v).strip() for v in (status_filter or []) if str(v).strip()]
    if not selected:
        return [row for row in rows if not user_is_deleted(row)]
    if "Deleted" in selected:
        return list(rows)
    return [row for row in rows if not user_is_deleted(row)]


def employee_type_label(user: dict[str, Any]) -> str:
    return "Employee" if user.get("is_employee") is not False else "System User"


def display_billing_class(user: dict[str, Any]) -> str:
    billing = str(user.get("billing_class") or user.get("trade") or "").strip()
    return billing if billing and billing not in {"—", "None", "-"} else "—"


def display_permission_role(user: dict[str, Any]) -> str:
    role = str(user.get("permission_role") or user.get("role") or user.get("role_name") or "").strip()
    return role if role else "—"


USER_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("billing_class", display_billing_class),
    ("permission_role", display_permission_role),
    ("employee_type", employee_type_label),
    ("status", user_filter_status),
]


def _employee_sort_key(row: dict[str, Any]) -> tuple[int, str]:
    deleted = 1 if user_is_deleted(row) else 0
    name = str(row.get("name") or row.get("full_name") or "").casefold()
    return (deleted, name)


def _search_match(row: dict[str, Any], query: str) -> bool:
    q = str(query or "").strip().casefold()
    if not q:
        return True
    haystack = " ".join(
        str(row.get(key) or "")
        for key in (
            "name",
            "full_name",
            "email",
            "phone",
            "employee_number",
            "billing_class",
            "trade",
            "permission_role",
            "role",
            "status",
        )
    ).casefold()
    return q in haystack


def filter_people_rows(rows: list[dict[str, Any]], *, search: str = "") -> list[dict[str, Any]]:
    status_filter = get_column_filter_values(_TABLE_KEY, "status")
    visible = filter_users_by_deleted_visibility(rows, status_filter=status_filter)
    if search.strip():
        visible = [row for row in visible if _search_match(row, search)]
    visible = apply_column_filters(visible, _TABLE_KEY, USER_COLUMN_FILTER_SPECS)
    visible.sort(key=_employee_sort_key)
    return visible


def _load_list_projection_uncached() -> tuple[list[dict[str, Any]], bool]:
    from app.pages._core._data import _DEMO_EMPLOYEES
    from app.services.repository import fetch_rows, fetch_rows_admin

    rows, err = fetch_rows(
        "employees",
        columns=_PEOPLE_LIST_COLUMNS,
        limit=10000,
        order_by="name",
    )
    if rows:
        return [normalize_employee(r) for r in rows], True

    admin_rows, admin_err = fetch_rows_admin(
        "employees",
        columns=_PEOPLE_LIST_COLUMNS,
        limit=10000,
        order_by="name",
    )
    if admin_rows:
        return [normalize_employee(r) for r in admin_rows if r], True

    if err or admin_err:
        st.session_state["_ips_people_list_warning"] = "User list is temporarily unavailable."
    demo = [normalize_employee(r) for r in _DEMO_EMPLOYEES]
    return demo, False


def _cached_list_projection() -> tuple[list[dict[str, Any]], bool]:
    from app.pages._core._data import employees_catalog_data_version

    cache_key = f"people_list_projection:{employees_catalog_data_version()}"
    return page_data_cache_get(cache_key, _load_list_projection_uncached)


def load_people_filter_options() -> dict[str, list[str]]:
    from app.components.table_filters import build_filter_options
    from app.pages._core._data import employees_catalog_data_version
    from app.perf_debug import perf_span

    def _load() -> dict[str, list[str]]:
        rows, _live = _cached_list_projection()
        return build_filter_options(rows, USER_COLUMN_FILTER_SPECS)

    cache_key = f"people_filter_options:{employees_catalog_data_version()}"
    with perf_span("people.filter_options"):
        return page_data_cache_get(cache_key, _load)


def list_people_page(
    *,
    search: str = "",
    billing_classes: list[str] | None = None,
    permission_roles: list[str] | None = None,
    employee_types: list[str] | None = None,
    statuses: list[str] | None = None,
    page: int | None = None,
    page_size: int | None = None,
    include_deleted: bool = False,
) -> PeoplePage:
    from app.components.table_pagination import pagination_meta
    from app.perf_debug import perf_span

    del billing_classes, permission_roles, employee_types, statuses, include_deleted

    with perf_span("people.list_query"):
        rows, is_live = _cached_list_projection()
        warning = st.session_state.pop("_ips_people_list_warning", None)
        filtered = filter_people_rows(rows, search=search)
        total = len(filtered)
        resolved_page, resolved_size, _total_pages = pagination_meta(total, _TABLE_KEY)
        safe_page = int(page or resolved_page)
        safe_size = int(page_size or resolved_size)
        start = (safe_page - 1) * safe_size
        page_rows = filtered[start : start + safe_size]
        filter_options = load_people_filter_options()
        for row in page_rows:
            from app.services.employee_detail_service import cache_person_modal

            cache_person_modal(row)
        return PeoplePage(
            rows=page_rows,
            total_count=total,
            page=safe_page,
            page_size=safe_size,
            filter_options=filter_options,
            is_live=is_live,
            warning=str(warning) if warning else None,
        )
