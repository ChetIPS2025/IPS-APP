"""Users page filter and load helpers."""

from __future__ import annotations

import streamlit as st

from app.components.table_filters import (
    apply_column_filters,
    get_column_filter_values,
    has_active_column_filters,
    sanitize_column_filters,
)
from app.pages.employees import _USER_COLUMN_FILTER_SPECS, _filter_employees
from app.services.repository import fetch_rows, get_last_fetch_error


def test_filter_employees_search_only_applies_when_user_types():
    rows = [
        {
            "id": "1",
            "name": "Alice Admin",
            "email": "alice@example.com",
            "billing_class": "Foreman",
            "permission_role": "Admin",
            "is_employee": True,
            "status": "Active",
        },
        {
            "id": "2",
            "name": "Bob Builder",
            "email": "bob@example.com",
            "billing_class": "Welder",
            "permission_role": "Employee",
            "is_employee": True,
            "status": "Active",
        },
    ]
    assert len(_filter_employees(rows, search="")) == 2
    assert len(_filter_employees(rows, search="alice")) == 1
    assert _filter_employees(rows, search="alice")[0]["name"] == "Alice Admin"


def test_sanitize_column_filters_drops_stale_values():
    table_key = "employees_list"
    field = "permission_role"
    session_key = f"{table_key}_{field}_filter"
    st.session_state[session_key] = ["Legacy Role"]
    options = {"permission_role": ["Admin", "Employee"]}
    changed = sanitize_column_filters(table_key, options, filter_fields=["permission_role"])
    assert changed is True
    assert get_column_filter_values(table_key, field) == []


def test_apply_column_filters_defaults_to_all_when_none_selected():
    rows = [
        {"billing_class": "Welder", "permission_role": "Employee", "is_employee": True, "status": "Active"},
        {"billing_class": "Foreman", "permission_role": "Admin", "is_employee": False, "status": "Inactive"},
    ]
    filtered = apply_column_filters(rows, "employees_list", _USER_COLUMN_FILTER_SPECS)
    assert len(filtered) == 2


def test_has_active_column_filters_detects_session_values():
    table_key = "employees_list"
    st.session_state[f"{table_key}_status_filter"] = ["Active"]
    assert has_active_column_filters(table_key, ["status"]) is True
    st.session_state.pop(f"{table_key}_status_filter", None)
    assert has_active_column_filters(table_key, ["status"]) is False


def test_fetch_rows_records_last_error(monkeypatch):
    calls: list[str | None] = []

    class _FakeDb:
        def fetch_table(self, table_name, *, columns=None, limit=500, order_by=None):
            calls.append(order_by)
            if order_by == "name":
                raise RuntimeError("order failed")
            return [{"id": "1", "name": "Test User"}]

    monkeypatch.setattr("app.services.repository._db", lambda: _FakeDb())
    rows, err = fetch_rows("employees", order_by="name")
    assert err is None
    assert len(rows) == 1
    assert calls == ["name", None]
    assert get_last_fetch_error("employees") is None


def test_list_employees_falls_back_to_admin_when_user_scoped_empty(monkeypatch):
    from app.services.phase2_modules_service import list_employees

    monkeypatch.setattr(
        "app.services.phase2_modules_service.fetch_list",
        lambda *args, **kwargs: ([], False),
    )
    monkeypatch.setattr(
        "app.services.phase2_modules_service.fetch_rows_admin",
        lambda *args, **kwargs: (
            [{"id": "1", "name": "Test User", "email": "t@example.com", "is_active": True}],
            None,
        ),
    )
    rows, used = list_employees(demo=[])
    assert len(rows) == 1
    assert rows[0]["name"] == "Test User"
    assert used is False
