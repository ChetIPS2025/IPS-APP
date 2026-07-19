"""Company Updates module performance and lazy-loading regressions."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components.company_updates_directory_table import (
    build_company_updates_html_table,
    company_update_detail_href,
)
from app.pages import company_updates as cu_page
from app.services.company_updates_directory_service import (
    CompanyUpdatesPage,
    list_company_updates_page,
    resolve_update_author_labels,
    _parse_ts,
    _sort_rows,
)


class TestCompanyUpdatesDirectoryService(unittest.TestCase):
    def test_list_company_updates_page_returns_only_requested_slice(self) -> None:
        rows = [
            {
                "id": f"cu-{i}",
                "title": f"Update {i}",
                "category": "General",
                "created_at": f"2025-01-{i + 1:02d}",
            }
            for i in range(30)
        ]

        with patch("app.services.company_updates_directory_service._load_catalog_rows", return_value=(rows, True)):
            with patch(
                "app.services.company_updates_directory_service.load_company_updates_filter_options",
                return_value={"category": ["General"], "audience": ["All"], "status": ["Published"]},
            ):
                with patch(
                    "app.services.company_updates_directory_service.resolve_update_author_labels",
                    return_value={},
                ):
                    page = list_company_updates_page(page=2, page_size=10, sort="Oldest First")

        self.assertEqual(page.total_count, 30)
        self.assertEqual(len(page.rows), 10)
        self.assertEqual(page.rows[0]["id"], "cu-10")

    def test_newest_sort_uses_raw_timestamps(self) -> None:
        rows = [
            {"id": "1", "title": "A", "created_at": "2024-12-31T12:00:00"},
            {"id": "2", "title": "B", "created_at": "2025-01-15T12:00:00"},
            {"id": "3", "title": "C", "created_at": "2023-06-01T12:00:00"},
        ]
        sorted_rows = _sort_rows(rows, "Newest First")
        self.assertEqual([r["id"] for r in sorted_rows], ["2", "1", "3"])
        self.assertGreater(_parse_ts("2025-01-15"), _parse_ts("2024-12-31"))


class TestCompanyUpdatesAuthorResolution(unittest.TestCase):
    def test_resolve_update_author_labels_does_not_load_full_employees_catalog(self) -> None:
        with patch("app.services.repository.fetch_by_id", return_value={"name": "Jane Doe"}):
            with patch("app.pages._core._data.load_employees") as load_mock:
                labels = resolve_update_author_labels(["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"])
        load_mock.assert_not_called()
        self.assertEqual(labels["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"], "Jane Doe")

    def test_unknown_uuid_does_not_display_raw_uuid(self) -> None:
        from app.services.company_updates_directory_service import _resolve_created_by

        row = {"created_by": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}
        display = _resolve_created_by(row, {})
        self.assertEqual(display, "Unknown user")
        self.assertNotIn("aaaaaaaa", display)


class TestCompanyUpdatesNativeLinks(unittest.TestCase):
    def test_title_link_html_uses_native_anchor(self) -> None:
        from app.components.company_updates_directory_table import company_update_title_link_html

        html_out = company_update_title_link_html("cu-1", "Safety Meeting", is_pinned=False)
        self.assertIn("<a ", html_out)
        self.assertIn('class="ips-company-update-open-link', html_out)
        self.assertIn('target="_self"', html_out)
        self.assertIn("update_detail=cu-1", html_out)
        self.assertIn("ips_nav=company_updates", html_out)
        self.assertNotIn("checkbox", html_out.lower())

    def test_detail_href_encodes_tab(self) -> None:
        href = company_update_detail_href("id/with space", tab="attachments")
        self.assertIn("update_detail=", href)
        self.assertIn("update_tab=attachments", href)

    def test_html_table_has_no_checkbox(self) -> None:
        html_out = build_company_updates_html_table(
            [
                {
                    "id": "cu-1",
                    "title": "Test",
                    "category": "General",
                    "audience": "All",
                    "status": "Published",
                    "event_date_display": "—",
                    "created_by_display": "Admin",
                    "created_display": "Jan 1",
                    "is_pinned": False,
                }
            ]
        )
        self.assertIn("ips-company-update-open-link", html_out)
        self.assertNotIn("stCheckbox", html_out)
        self.assertNotIn("<input", html_out)


class TestCompanyUpdatesDetailFastPath(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_detail_pending_skips_directory_fragment(self) -> None:
        st.session_state[cu_page.SHOW_UPDATE_MODAL_KEY] = True
        st.session_state[cu_page._MODAL_KEY] = "cu-1"

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(cu_page, "_render_company_updates_directory_fragment") as directory_mock:
                with patch.object(cu_page, "show_modal_if_pending") as modal_mock:
                    with patch.object(cu_page, "_capture_company_update_detail_query"):
                        with patch.object(cu_page, "load_company_updates_permissions") as perm_mock:
                            perm_mock.return_value = MagicMock(can_create=False)
                            with patch.object(cu_page, "inject_updates_module_css"):
                                with patch.object(cu_page, "render_page_brand_header"):
                                    with patch.object(cu_page.st, "markdown"):
                                        cu_page.render()

        directory_mock.assert_not_called()
        modal_mock.assert_called()


class TestCompanyUpdatesHeaderBeforeList(unittest.TestCase):
    def test_render_page_header_before_directory_query(self) -> None:
        calls: list[str] = []

        def _header(*args, **kwargs):
            calls.append("header")

        def _directory_fragment(*args, **kwargs):
            calls.append("directory")

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(cu_page, "render_page_brand_header", side_effect=_header):
                with patch.object(cu_page, "_capture_company_update_detail_query"):
                    with patch.object(cu_page, "_company_updates_detail_pending", return_value=False):
                        with patch.object(
                            cu_page,
                            "_render_company_updates_directory_fragment",
                            side_effect=_directory_fragment,
                        ):
                            with patch.object(cu_page, "load_company_updates_permissions") as perm_mock:
                                perm_mock.return_value = MagicMock(can_create=False)
                                with patch.object(cu_page, "inject_updates_module_css"):
                                    with patch.object(cu_page.st, "markdown"):
                                        cu_page.render()

        self.assertEqual(calls[0], "header")
        self.assertEqual(calls[1], "directory")

    def test_render_source_has_no_pre_header_employee_lookup(self) -> None:
        import inspect

        source = inspect.getsource(cu_page.render)
        self.assertNotIn("load_employees", source)
        self.assertNotIn("_user_name_lookup", source)


class TestCompanyUpdatesConditionalTabs(unittest.TestCase):
    def test_attachments_only_render_on_attachments_tab(self) -> None:
        update = {
            "id": "cu-1",
            "title": "T",
            "body": "Body",
            "category": "General",
            "status": "Published",
            "attachment_url": "https://example.com/file.pdf",
            "attachment_file_name": "file.pdf",
            "created_by_display": "Admin",
            "created_display": "Jan 1",
        }
        from app.components.company_update_detail_tabs import render_company_update_detail_tabs
        from app.components.company_updates_permissions import CompanyUpdatesPermissions

        perms = CompanyUpdatesPermissions(
            role="admin",
            user_id="u1",
            user_name="Admin",
            can_manage=True,
            can_create=True,
            can_edit=True,
            can_delete=True,
            can_view_read_receipts=True,
        )

        with patch("app.components.company_update_detail_tabs.render_tabs", return_value="Overview"):
            with patch.object(st, "markdown") as md_mock:
                render_company_update_detail_tabs(update, permissions=perms)
        overview_html = " ".join(str(call) for call in md_mock.call_args_list)
        self.assertNotIn("example.com", overview_html)

        st.session_state.clear()
        with patch("app.components.company_update_detail_tabs.render_tabs", return_value="Attachments"):
            with patch.object(st, "markdown") as md_mock:
                render_company_update_detail_tabs(update, permissions=perms)
        attachments_html = " ".join(str(call) for call in md_mock.call_args_list)
        self.assertIn("example.com", attachments_html)


if __name__ == "__main__":
    unittest.main()
