"""Tasks module performance and behavior regression tests."""

from __future__ import annotations

import inspect
import unittest
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components.tasks_directory_table import build_tasks_html_table, task_detail_href, task_title_link_html
from app.pages import tasks as tasks_page
from app.services.tasks_directory_service import list_tasks_page


class TestHeaderBeforeDirectory(unittest.TestCase):
    def test_render_source_has_header_before_list_query(self) -> None:
        src = inspect.getsource(tasks_page.render)
        header_idx = src.index("render_page_brand_header")
        list_idx = src.index("_render_tasks_directory_fragment")
        assert header_idx < list_idx

    def test_render_does_not_load_all_assignees_upfront(self) -> None:
        src = inspect.getsource(tasks_page.render)
        assert "_build_assignee_lookup()" not in src
        assert "get_job_options(include_all=True)" not in src


class TestPaginatedDirectory(unittest.TestCase):
    def test_list_tasks_page_returns_slice(self) -> None:
        rows = [
            {
                "id": f"t{i}",
                "title": f"Task {i}",
                "status": "Open",
                "priority": "Medium",
                "assigned_to": "user-1",
                "due_date": "2026-07-19",
                "created_at": "2026-01-01",
            }
            for i in range(40)
        ]
        with patch("app.services.tasks_service.get_tasks", return_value=rows):
            with patch(
                "app.services.tasks_directory_service.resolve_task_assignee_labels",
                return_value={"user-1": "Alice"},
            ):
                with patch("app.services.tasks_directory_service.resolve_task_job_labels", return_value={}):
                    with patch(
                        "app.services.task_reference_service.load_task_filter_options",
                        return_value={"priority_display": [], "assigned_to_display": [], "job_display": []},
                    ):
                        with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                            page = list_tasks_page(page=2, page_size=10)
        assert page.total_count == 40
        assert len(page.rows) == 10
        assert page.page == 2


class TestNativeLinks(unittest.TestCase):
    def test_task_title_link_is_anchor(self) -> None:
        html_out = task_title_link_html("task-1", "Fix valve")
        assert "<a " in html_out
        assert 'target="_self"' in html_out
        assert "task_detail=task-1" in html_out
        assert "ips_nav=tasks" in html_out

    def test_detail_href_encodes_tab(self) -> None:
        href = task_detail_href("id/with space", tab="assignment")
        assert "task_detail=" in href
        assert "task_tab=assignment" in href


class TestWidgetFreeOfficeTable(unittest.TestCase):
    def test_office_table_source_has_no_checkbox(self) -> None:
        src = inspect.getsource(tasks_page._render_tasks_directory_fragment)
        assert "st.checkbox" not in src
        assert "st.selectbox" not in src
        assert "build_tasks_html_table" in src

    def test_render_custom_table_not_used_in_render(self) -> None:
        src = inspect.getsource(tasks_page.render)
        assert "_render_custom_task_table(" not in src


class TestDetailFastPath(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_detail_pending_skips_directory(self) -> None:
        st.session_state[tasks_page.SHOW_MODAL_KEY] = True
        st.session_state[tasks_page.SELECTED_TASK_KEY] = "t-1"
        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(tasks_page, "_render_tasks_directory_fragment") as dir_mock:
                with patch.object(tasks_page, "_show_task_modal") as modal_mock:
                    with patch.object(tasks_page, "render_page_brand_header"):
                        with patch.object(tasks_page, "load_task_permissions") as perm_mock:
                            perm_mock.return_value = MagicMock(is_field_employee=False, employee_match_ids=())
                            with patch.object(tasks_page.st, "markdown"):
                                tasks_page.render()
        dir_mock.assert_not_called()
        modal_mock.assert_called_once()


class TestFieldPanelFocused(unittest.TestCase):
    def test_field_panel_does_not_load_global_catalogs(self) -> None:
        src = inspect.getsource(tasks_page.render_field_tasks_panel)
        assert "_build_assignee_lookup()" not in src
        assert "get_job_options" not in src
        assert "list_field_tasks_panel" in src


class TestFieldVisibility(unittest.TestCase):
    def test_employee_filter_in_service(self) -> None:
        rows = [
            {"id": "t1", "title": "Mine", "status": "Open", "priority": "High", "assigned_to": "alice", "job_id": "j1", "due_date": "2026-07-19", "created_at": ""},
            {"id": "t2", "title": "Other", "status": "Open", "priority": "Low", "assigned_to": "bob", "job_id": "j1", "due_date": "2026-07-19", "created_at": ""},
        ]
        with patch("app.services.tasks_service.get_tasks", return_value=rows):
            with patch("app.services.tasks_directory_service.resolve_task_assignee_labels", return_value={"alice": "Alice", "bob": "Bob"}):
                with patch("app.services.tasks_directory_service.resolve_task_job_labels", return_value={"j1": "J1"}):
                    with patch("app.services.task_reference_service.load_task_filter_options", return_value={"priority_display": [], "assigned_to_display": [], "job_display": []}):
                        with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                            page = list_tasks_page(
                                view="Open To-Dos",
                                field_job_id="j1",
                                current_user_match_ids=["alice"],
                                is_field_employee=True,
                                page_size=50,
                            )
        assert page.total_count == 1
        assert page.rows[0]["id"] == "t1"


class TestHtmlTableEscape(unittest.TestCase):
    def test_table_escapes_html(self) -> None:
        html_out = build_tasks_html_table(
            [
                {
                    "id": "t1",
                    "title": "<script>",
                    "status": "Open",
                    "priority": "High",
                    "assigned_to_display": "A & B",
                    "job_display": "J",
                    "due_date": "2026-07-19",
                }
            ]
        )
        assert "<script>" not in html_out
        assert "&lt;script&gt;" in html_out
        assert "A &amp; B" in html_out


class TestSubjobsService(unittest.TestCase):
    def test_list_job_subjobs_filters_by_job(self) -> None:
        from app.services.job_subjobs_service import list_job_subjobs

        with patch(
            "app.services.tasks_service.get_tasks_by_job",
            return_value=[
                {"id": "s1", "title": "Sub", "status": "Open", "priority": "Medium", "assigned_to": "u1", "due_date": ""},
            ],
        ):
            with patch("app.services.job_subjobs_service.resolve_task_assignee_labels", return_value={"u1": "User"}):
                with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                    page = list_job_subjobs("job-1", view="Open")
        assert page.total_count == 1


if __name__ == "__main__":
    unittest.main()
