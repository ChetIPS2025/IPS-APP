"""Employee Resources performance, security, and behavior regression tests."""

from __future__ import annotations

import inspect
import unittest
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components.employee_resource_form import seed_employee_resource_form
from app.components.employee_resources_admin_table import build_employee_resources_admin_html_table
from app.components.employee_resources_directory import build_resource_cards_html, open_resource_href
from app.pages import employee_resources as er_page
from app.services.employee_resources_cache import (
    employee_resources_data_version,
    invalidate_employee_resources_cache,
)
from app.services.employee_resources_service import (
    _DEMO_RESOURCES,
    get_employee_resource_open_target,
    is_safe_resource_url,
    list_employee_resources_admin_page,
    list_employee_resources_page,
    normalize_resource,
    resource_open_url,
    resource_visible_to_role,
    save_employee_resource,
    validate_employee_resource_payload,
)


def _demo_rows(count: int | None = None) -> list[dict]:
    rows = [normalize_resource(dict(r)) for r in _DEMO_RESOURCES]
    if count is not None:
        return rows[:count]
    return rows


class TestHeaderBeforeDirectory(unittest.TestCase):
    def test_render_source_has_header_before_list_query(self) -> None:
        src = inspect.getsource(er_page.render)
        header_idx = src.index("render_page_header")
        list_idx = src.index("render_employee_resources_directory")
        assert header_idx < list_idx

    def test_admin_resources_view_uses_single_employee_query(self) -> None:
        src = inspect.getsource(er_page.render)
        assert "list_employee_resources(" not in src
        assert "list_all_employee_resources_admin(" not in src

    def test_admin_manage_uses_admin_page_only(self) -> None:
        src = inspect.getsource(er_page._render_admin_directory_fragment)
        assert "list_employee_resources_admin_page" in src
        assert "list_employee_resources_page" not in src


class TestPaginatedDirectory(unittest.TestCase):
    def test_list_page_returns_slice(self) -> None:
        with patch(
            "app.services.employee_resources_service._load_catalog_rows",
            return_value=(_demo_rows(), True),
        ):
            with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                page = list_employee_resources_page(role="employee", page=2, page_size=5)
        assert page.total_count == len(_DEMO_RESOURCES)
        assert len(page.rows) == 5
        assert page.page == 2

    def test_admin_page_includes_inactive(self) -> None:
        rows = _demo_rows()
        rows[0] = dict(rows[0])
        rows[0]["is_active"] = False
        with patch(
            "app.services.employee_resources_service._load_catalog_rows",
            return_value=(rows, True),
        ):
            with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                admin = list_employee_resources_admin_page(statuses=["inactive"], page_size=50)
                employee = list_employee_resources_page(role="employee", page_size=50)
        assert admin.total_count == 1
        assert employee.total_count == len(_DEMO_RESOURCES) - 1

    def test_search_reaches_service(self) -> None:
        with patch(
            "app.services.employee_resources_service._load_catalog_rows",
            return_value=(_demo_rows(), True),
        ):
            with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                page = list_employee_resources_page(role="admin", search="handbook", page_size=50)
        assert page.total_count == 1
        assert "Handbook" in page.rows[0]["title"]

    def test_sort_order_stable(self) -> None:
        with patch(
            "app.services.employee_resources_service._load_catalog_rows",
            return_value=(_demo_rows(), True),
        ):
            with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                page = list_employee_resources_page(role="admin", page_size=50)
        orders = [r["sort_order"] for r in page.rows]
        assert orders == sorted(orders)


class TestVisibilitySecurity(unittest.TestCase):
    def test_admin_only_hidden_from_employee(self) -> None:
        row = normalize_resource(
            {
                "id": "r1",
                "title": "Admin doc",
                "category": "Document",
                "resource_type": "link",
                "url": "https://example.com/a",
                "visible_to_roles": "admin",
                "is_active": True,
                "sort_order": 1,
            }
        )
        assert resource_visible_to_role(row, "employee") is False
        assert resource_visible_to_role(row, "admin") is True

    def test_supervisor_visibility(self) -> None:
        row = normalize_resource(
            {
                "id": "r2",
                "title": "Supervisor doc",
                "category": "Document",
                "resource_type": "link",
                "url": "https://example.com/s",
                "visible_to_roles": "supervisor",
                "is_active": True,
                "sort_order": 1,
            }
        )
        assert resource_visible_to_role(row, "supervisor") is True
        assert resource_visible_to_role(row, "employee") is False

    def test_empty_visibility_defaults_all_roles(self) -> None:
        row = normalize_resource(
            {
                "id": "r3",
                "title": "Everyone",
                "category": "Document",
                "resource_type": "link",
                "url": "https://example.com/e",
                "visible_to_roles": "",
                "is_active": True,
                "sort_order": 1,
            }
        )
        assert resource_visible_to_role(row, "employee") is True
        assert resource_visible_to_role(row, "project manager") is True

    def test_inactive_hidden_from_employees(self) -> None:
        row = normalize_resource(
            {
                "id": "r4",
                "title": "Hidden",
                "category": "Document",
                "resource_type": "link",
                "url": "https://example.com/h",
                "visible_to_roles": "employee",
                "is_active": False,
                "sort_order": 1,
            }
        )
        assert resource_visible_to_role(row, "employee") is False

    def test_unauthorized_open_rejected(self) -> None:
        row = normalize_resource(
            {
                "id": "secret",
                "title": "Secret",
                "category": "Document",
                "resource_type": "link",
                "url": "https://example.com/secret",
                "visible_to_roles": "admin",
                "is_active": True,
                "sort_order": 1,
            }
        )
        with patch("app.services.employee_resources_service._find_resource_by_id", return_value=row):
            result = get_employee_resource_open_target("secret", role="employee", user_id="u1")
        assert result.ok is False

    def test_cache_keys_differ_by_role(self) -> None:
        keys: list[str] = []

        def _capture(key: str, loader):  # type: ignore[no-untyped-def]
            keys.append(key)
            return loader()

        with patch(
            "app.services.employee_resources_service._load_catalog_rows",
            return_value=(_demo_rows(), True),
        ):
            with patch("app.services.employee_resources_service.page_data_cache_get", side_effect=_capture):
                list_employee_resources_page(role="admin", page_size=5)
                list_employee_resources_page(role="employee", page_size=5)
        page_keys = [k for k in keys if k.startswith("employee_resources:page:")]
        assert len(page_keys) == 2
        assert page_keys[0] != page_keys[1]


class TestUrlHandling(unittest.TestCase):
    def test_safe_https_url(self) -> None:
        assert is_safe_resource_url("https://example.com/doc") is True

    def test_unsafe_javascript_rejected(self) -> None:
        assert is_safe_resource_url("javascript:alert(1)") is False

    def test_unsafe_data_rejected(self) -> None:
        assert is_safe_resource_url("data:text/html,hi") is False

    def test_list_does_not_sign_file_urls(self) -> None:
        row = {
            "id": "f1",
            "title": "Manual",
            "category": "Document",
            "resource_type": "file",
            "file_path": "employee-resources/manual.pdf",
            "description": "",
            "sort_order": 1,
            "updated_at": "",
        }
        with patch("app.db.create_signed_url") as sign_mock:
            assert resource_open_url(row) is None
            sign_mock.assert_not_called()

    def test_open_target_signs_only_on_request(self) -> None:
        row = normalize_resource(
            {
                "id": "f2",
                "title": "Manual",
                "category": "Document",
                "resource_type": "file",
                "file_path": "employee-resources/manual.pdf",
                "visible_to_roles": "employee",
                "is_active": True,
                "sort_order": 1,
            }
        )
        with patch("app.services.employee_resources_service._find_resource_by_id", return_value=row):
            with patch(
                "app.services.employee_resources_service._resolve_signed_url",
                return_value="https://signed.example/file",
            ):
                result = get_employee_resource_open_target("f2", role="employee", user_id="u1")
        assert result.ok is True
        assert result.data["kind"] == "signed"

    def test_employee_list_row_omits_storage_path(self) -> None:
        with patch(
            "app.services.employee_resources_service._load_catalog_rows",
            return_value=(
                [
                    normalize_resource(
                        {
                            "id": "f3",
                            "title": "File doc",
                            "category": "Document",
                            "resource_type": "file",
                            "file_path": "secret/path.pdf",
                            "visible_to_roles": "employee",
                            "is_active": True,
                            "sort_order": 1,
                        }
                    )
                ],
                True,
            ),
        ):
            with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                page = list_employee_resources_page(role="employee", page_size=10)
        assert "file_path" not in page.rows[0]

    def test_cards_use_open_href_for_files(self) -> None:
        html_out = build_resource_cards_html(
            [
                {
                    "id": "f4",
                    "title": "Manual",
                    "category": "Document",
                    "resource_type": "file",
                    "description": "Read me",
                }
            ]
        )
        assert "er_open=f4" in html_out
        assert "secret" not in html_out


class TestAdminLaziness(unittest.TestCase):
    def test_no_expander_in_page(self) -> None:
        src = inspect.getsource(er_page)
        assert "st.expander" not in src

    def test_form_in_dialog(self) -> None:
        src = inspect.getsource(er_page)
        assert "@st.dialog" in src
        assert "render_employee_resource_form" in src

    def test_admin_table_has_no_edit_buttons(self) -> None:
        html_out = build_employee_resources_admin_html_table(
            [{"id": "r1", "title": "Doc", "category": "Form", "visible_to_roles": "employee", "is_active": True, "sort_order": 1, "updated_at": "2026-01-01"}]
        )
        assert "st.button" not in html_out
        assert "er_edit_" not in html_out
        assert "ips-er-admin-select-link" in html_out


class TestFormState(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_switching_resources_reseeds(self) -> None:
        a = {"id": "a", "title": "A", "category": "Form", "resource_type": "link", "url": "https://a", "visible_to_roles": "employee", "sort_order": 1, "is_active": True}
        b = {"id": "b", "title": "B", "category": "HR", "resource_type": "file", "file_path": "path/b.pdf", "visible_to_roles": "admin", "sort_order": 2, "is_active": False}
        seed_employee_resource_form(a)
        assert st.session_state["ips_er_form_a_title"] == "A"
        assert st.session_state["ips_er_form_a_delivery"] == "Link"
        seed_employee_resource_form(b)
        assert st.session_state["ips_er_form_b_title"] == "B"
        assert st.session_state["ips_er_form_b_delivery"] == "File path (storage key)"
        assert "ips_er_form_a_title" not in st.session_state

    def test_link_file_delivery_labels(self) -> None:
        link = {"id": "l1", "title": "L", "category": "Link", "resource_type": "link", "url": "https://l", "visible_to_roles": "employee", "sort_order": 0, "is_active": True}
        file = {"id": "f1", "title": "F", "category": "Document", "resource_type": "file", "file_path": "x/y.pdf", "visible_to_roles": "employee", "sort_order": 0, "is_active": True}
        seed_employee_resource_form(link)
        assert st.session_state["ips_er_form_l1_delivery"] == "Link"
        st.session_state.clear()
        seed_employee_resource_form(file)
        assert st.session_state["ips_er_form_f1_delivery"] == "File path (storage key)"


class TestValidation(unittest.TestCase):
    def test_missing_title_rejected(self) -> None:
        errors = validate_employee_resource_payload({"title": "", "category": "Form", "resource_type": "link", "url": "https://x"})
        assert errors

    def test_invalid_url_rejected(self) -> None:
        errors = validate_employee_resource_payload(
            {"title": "X", "category": "Form", "resource_type": "link", "url": "javascript:bad", "sort_order": 0}
        )
        assert any("safe scheme" in e for e in errors)

    def test_missing_storage_path_rejected(self) -> None:
        errors = validate_employee_resource_payload(
            {"title": "X", "category": "Document", "resource_type": "file", "file_path": "", "sort_order": 0}
        )
        assert errors

    def test_valid_payload_passes(self) -> None:
        errors = validate_employee_resource_payload(
            {
                "title": "OK",
                "category": "Form",
                "resource_type": "link",
                "url": "https://example.com",
                "visible_to_roles": "employee",
                "sort_order": 0,
            }
        )
        assert not errors


class TestCacheInvalidation(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_invalidate_bumps_version(self) -> None:
        before = employee_resources_data_version()
        invalidate_employee_resources_cache("r1")
        after = employee_resources_data_version()
        assert after == before + 1

    def test_save_invalidates_cache(self) -> None:
        with patch("app.services.repository.insert_row") as insert_mock:
            insert_mock.return_value = MagicMock(ok=True, data={"id": "new-id"})
            with patch("app.services.employee_resources_service.finalize_employee_resource_write") as fin_mock:
                result = save_employee_resource(
                    {
                        "title": "New",
                        "category": "Form",
                        "resource_type": "link",
                        "url": "https://example.com/new",
                        "visible_to_roles": "employee",
                        "sort_order": 0,
                        "is_active": True,
                    }
                )
        assert result.ok
        fin_mock.assert_called_once()


class TestAdminSingleQuery(unittest.TestCase):
    def test_admin_resources_tab_does_not_call_admin_list(self) -> None:
        src = inspect.getsource(er_page.render)
        assert "list_employee_resources_admin_page" not in src.split("render_employee_resources_directory")[0]

    def test_admin_manage_tab_does_not_call_employee_list(self) -> None:
        src = inspect.getsource(er_page.render)
        manage_block = src.split('"Manage Resources"')[1]
        assert "list_employee_resources_page" not in manage_block


if __name__ == "__main__":
    unittest.main()
