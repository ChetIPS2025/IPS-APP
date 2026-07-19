"""Users/Employees module performance and wrapper tests."""

from __future__ import annotations

import inspect
from pathlib import Path

import streamlit as st

from app.components.people_directory_table import build_people_directory_table, user_detail_href
from app.pages import employees as emp_mod
from app.pages import users
from app.services.people_directory_service import filter_people_rows, list_people_page


def test_users_render_is_employees_render():
    assert users.render is emp_mod.render


def test_users_wrapper_has_no_streamlit_logic():
    source = Path("app/pages/users.py").read_text(encoding="utf-8")
    assert "st." not in source
    assert "load_employees" not in source
    assert "persist_employee" not in source


def test_user_detail_href_contains_nav_and_query():
    href = user_detail_href("user-123")
    assert "ips_nav=employees" in href
    assert "user_detail=user-123" in href


def test_people_directory_table_uses_native_anchor_links():
    html_out = build_people_directory_table(
        [
            {
                "id": "u-1",
                "name": "Alice Admin",
                "email": "alice@example.com",
                "permission_role": "Admin",
                "status": "Active",
            }
        ],
    )
    assert '<a class="ips-users-open-link' in html_out
    assert 'href="?ips_nav=employees&amp;user_detail=u-1"' in html_out
    assert 'role="button"' not in html_out


def test_render_puts_header_before_list_query():
    source = inspect.getsource(emp_mod.render)
    header_idx = source.index("render_page_brand_header")
    list_idx = source.index("_render_users_catalog_fragment")
    assert header_idx < list_idx
    assert "load_employees()" not in source


def test_detail_fast_path_skips_catalog_fragment():
    source = inspect.getsource(emp_mod.render)
    assert "_detail_pending()" in source
    fast_block = source.split("if _detail_pending()")[1].split("if st.session_state.get(\"ips_emp_form\")")[0]
    assert "_render_users_catalog_fragment" not in fast_block


def test_list_people_page_returns_only_one_page():
    rows = [
        {"id": f"u-{i}", "name": f"User {i}", "status": "Active", "is_employee": True}
        for i in range(40)
    ]
    st.session_state.clear()
    st.session_state["ips_pg_page_employees_list"] = 1
    st.session_state["ips_pg_size_employees_list"] = 25

    import app.services.people_directory_service as svc

    original = svc._cached_list_projection
    svc._cached_list_projection = lambda: (rows, True)
    try:
        page = list_people_page(search="")
    finally:
        svc._cached_list_projection = original

    assert len(page.rows) == 25
    assert page.total_count == 40


def test_filter_people_rows_search_is_scoped():
    rows = [
        {"id": "1", "name": "Alice", "email": "a@x.com", "status": "Active", "is_employee": True},
        {"id": "2", "name": "Bob", "email": "b@x.com", "status": "Active", "is_employee": True},
    ]
    st.session_state.clear()
    assert len(filter_people_rows(rows, search="alice")) == 1
    assert len(filter_people_rows(rows, search="")) == 2


def test_employees_source_has_no_hidden_open_buttons():
    source = Path("app/pages/employees.py").read_text(encoding="utf-8")
    assert "render_users_table_open_buttons" not in source
    assert "render_users_table_bridge_legacy" not in source


def test_lazy_tabs_use_render_tabs_not_st_tabs():
    source = inspect.getsource(emp_mod._render_employee_detail_tabs)
    assert "render_employee_detail_tabs" in source
    tabs_source = Path("app/components/employee_detail_tabs.py").read_text(encoding="utf-8")
    assert "st.tabs(" not in tabs_source
    assert "render_tabs(" in tabs_source


def test_login_panel_lazy_in_component():
    source = Path("app/components/employee_login_admin.py").read_text(encoding="utf-8")
    assert "Manage Login" in source
    assert "resolve_employee_auth_login" in source
    detail_source = Path("app/components/employee_detail_tabs.py").read_text(encoding="utf-8")
    assert "resolve_employee_auth_login" not in detail_source
