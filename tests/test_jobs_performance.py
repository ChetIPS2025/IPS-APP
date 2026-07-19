"""Jobs module performance and lazy-loading regressions."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components.jobs_directory_table import job_detail_href
from app.components.jobs_list_table import build_jobs_html_table, job_list_link_html
from app.pages import jobs as jobs_page
from app.services.jobs_directory_service import JobsPage, list_jobs_page


class TestJobsDirectoryService(unittest.TestCase):
    def test_list_jobs_page_returns_only_requested_slice(self) -> None:
        rows = [{"id": f"j-{i}", "job_number": f"J{i}", "status": "Active", "customer": "Acme"} for i in range(30)]

        with patch("app.services.jobs_directory_service.load_jobs", return_value=rows):
            with patch("app.services.jobs_directory_service.load_jobs_filter_options", return_value={"customer": ["Acme"], "supervisor": [], "status": ["Active"]}):
                with patch("app.services.jobs_directory_service._load_subjob_counts_safe", return_value={}):
                    page = list_jobs_page(view="All Jobs", page=2, page_size=10, table_key="jobs_test")

        assert page.total_count == 30
        assert len(page.rows) == 10
        assert page.rows[0]["id"] == "j-10"


class TestJobsNativeLinks(unittest.TestCase):
    def test_job_list_link_html_uses_native_anchor(self) -> None:
        html_out = job_list_link_html("j-123", "J26015", extra_class="ips-jobs-number-link")
        assert '<a ' in html_out
        assert 'class="ips-jobs-open-link"' in html_out or "ips-jobs-open-link" in html_out
        assert 'target="_self"' in html_out
        assert "job_detail=j-123" in html_out or "job_detail=j-123" in job_detail_href("j-123")
        assert "ips_nav=jobs" in html_out or "ips_nav=jobs" in job_detail_href("j-123")
        assert '<button type="button"' not in html_out
        assert "J26015" in html_out

    def test_job_detail_href_encodes_tab(self) -> None:
        href = job_detail_href("id/with space", tab="financial")
        assert "job_detail=id%2Fwith+space" in href or "job_detail=id%2Fwith%20space" in href
        assert "job_tab=financial" in href


class TestJobsDetailFastPath(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_detail_pending_skips_directory_fragment(self) -> None:
        st.session_state[jobs_page.SHOW_MODAL_KEY] = True
        st.session_state[jobs_page._JOBS_MODAL_KEY] = "j-1"

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(jobs_page, "_render_jobs_catalog_fragment") as catalog_mock:
                with patch.object(jobs_page, "show_modal_if_pending") as modal_mock:
                    with patch.object(jobs_page, "_capture_job_detail_query"):
                        with patch.object(jobs_page, "inject_jobs_module_css"):
                            with patch.object(jobs_page, "inject_jobs_page_layout_css"):
                                with patch("app.ui.page_header.render_page_header"):
                                    with patch.object(jobs_page.st, "markdown"):
                                        jobs_page.render()

        catalog_mock.assert_not_called()
        modal_mock.assert_called()


class TestJobsConditionalTabs(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_overview_does_not_load_tasks(self) -> None:
        job = {"id": "j-1", "job_number": "J1", "job_name": "Proj", "status": "Active", "customer": "Acme"}
        st.session_state["ips_job_detail_active_tab"] = "Overview"

        with patch("app.components.tabs.render_tabs", return_value="Overview"):
            with patch("app.pages.tasks.render_job_linked_tasks_tab") as tasks_mock:
                with patch("app.components.job_detail_layout.render_job_detail_overview_section"):
                    from app.components.job_detail_tabs import render_job_detail_tabs

                    render_job_detail_tabs(job)

        tasks_mock.assert_not_called()

    def test_cost_summary_not_loaded_on_overview(self) -> None:
        job = {"id": "j-1", "job_number": "J1", "status": "Active"}
        st.session_state["ips_job_detail_active_tab"] = "Overview"

        with patch("app.components.tabs.render_tabs", return_value="Overview"):
            with patch("app.services.job_cost_transaction_service.load_job_cost_detail_snapshot") as cost_mock:
                with patch("app.components.job_detail_layout.render_job_detail_overview_section"):
                    from app.components.job_detail_tabs import render_job_detail_tabs

                    render_job_detail_tabs(job)

        cost_mock.assert_not_called()


class TestJobsListFinancials(unittest.TestCase):
    def test_list_cost_fields_use_stored_columns(self) -> None:
        job = {
            "id": "j-1",
            "awarded_amount": 1000,
            "estimated_cost": 800,
            "actual_cost": 200,
        }
        with patch("app.services.job_financial_ui.job_table_list_financials_from_row") as heavy_mock:
            fin = jobs_page._job_list_cost_fields(job)
        heavy_mock.assert_not_called()
        assert fin["contract_value"] == 1000
        assert fin["actual_cost"] == 200


if __name__ == "__main__":
    unittest.main()
