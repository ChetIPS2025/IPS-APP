"""Employee Portal performance and behavior regression tests."""

from __future__ import annotations

import inspect
import unittest
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components.employee_portal.jobs import build_job_list_html, portal_job_href
from app.components.employee_portal.updates import build_updates_cards_html, portal_update_href
from app.pages import employee_portal as portal_page
from app.services.employee_portal_detail_service import (
    get_employee_certification_open_target,
    get_employee_portal_job_detail,
    get_employee_portal_update_detail,
)
from app.services.employee_portal_service import (
    list_employee_portal_updates,
    list_employee_upcoming_schedule,
    list_portal_certification_summaries,
    list_portal_dashboard_jobs,
    load_employee_portal_snapshot,
)


class TestGetEmployeeImport(unittest.TestCase):
    def test_portal_imports_get_employee(self) -> None:
        src = inspect.getsource(portal_page)
        assert "from app.services.employees_service import get_employee" in src
        assert "get_employee(employee_id)" in src

    def test_render_does_not_raise_name_error(self) -> None:
        st.session_state.clear()
        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(portal_page, "inject_employee_portal_css"):
                with patch.object(portal_page, "current_profile", return_value={"id": "u1", "full_name": "Pat"}):
                    with patch.object(portal_page, "effective_role", return_value="employee"):
                        with patch(
                            "app.pages.employee_portal.resolve_logged_in_employee_id",
                            return_value="emp-1",
                        ):
                            with patch(
                                "app.pages.employee_portal.get_employee",
                                return_value={"id": "emp-1", "full_name": "Pat"},
                            ):
                                with patch.object(portal_page, "build_employee_portal_context") as ctx_mock:
                                    ctx_mock.return_value = MagicMock(
                                        role="employee",
                                        user_id="u1",
                                        employee_id="emp-1",
                                        employee_name="Pat",
                                        profile={},
                                        employee={"id": "emp-1"},
                                        view_as_mode="employee",
                                        today=__import__("datetime").date.today(),
                                        can_view_timekeeping=False,
                                        can_view_resources=True,
                                        can_scan_assets=True,
                                    )
                                    with patch.object(portal_page, "render_welcome_card"):
                                        with patch.object(portal_page, "_active_detail_query", return_value=None):
                                            with patch.object(portal_page, "_portal_view_is_jobs", return_value=False):
                                                with patch.object(portal_page, "load_employee_portal_snapshot") as snap:
                                                    snap.return_value = MagicMock(
                                                        updates=[],
                                                        certifications=[],
                                                        recent_jobs=[],
                                                        upcoming_schedule=[],
                                                        warnings=[],
                                                    )
                                                    with patch.object(portal_page, "_render_dashboard_sections"):
                                                        with patch.object(portal_page.st, "markdown"):
                                                            portal_page.render()


class TestWelcomeBeforeSnapshot(unittest.TestCase):
    def test_render_source_welcome_before_snapshot(self) -> None:
        src = inspect.getsource(portal_page.render)
        welcome_idx = src.index("render_welcome_card(ctx)")
        snapshot_idx = src.index("load_employee_portal_snapshot")
        assert welcome_idx < snapshot_idx


class TestNoLoadJobsInPortal(unittest.TestCase):
    def test_portal_does_not_import_load_jobs(self) -> None:
        src = inspect.getsource(portal_page)
        assert "load_jobs" not in src

    def test_schedule_service_does_not_use_load_jobs(self) -> None:
        src = inspect.getsource(list_employee_upcoming_schedule)
        assert "load_jobs" not in src


class TestUpdatesLimited(unittest.TestCase):
    def test_updates_service_applies_limit(self) -> None:
        rows = [
            {"id": f"u{i}", "title": f"U{i}", "body": "x", "status": "Published", "is_active": True, "audience": "All"}
            for i in range(20)
        ]
        with patch("app.pages._core._data.load_company_updates", return_value=rows):
            with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                out = list_employee_portal_updates(role="employee", limit=8)
        assert len(out) == 8


class TestRecentJobsLimited(unittest.TestCase):
    def test_dashboard_jobs_limited_to_four(self) -> None:
        with patch(
            "app.services.employee_portal_service.list_assigned_job_ids_for_employee",
            return_value=["j1", "j2", "j3", "j4", "j5"],
        ):
            with patch(
                "app.services.employee_portal_service._fetch_jobs_by_ids",
                return_value={
                    f"j{i}": {"id": f"j{i}", "job_name": f"J{i}", "status": "Active"}
                    for i in range(1, 6)
                },
            ):
                with patch("app.services.employee_portal_service._iter_active_job_rows", return_value=[]):
                    with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                        rows = list_portal_dashboard_jobs("emp-1", limit=4)
        assert len(rows) == 4


class TestNativeLinks(unittest.TestCase):
    def test_update_cards_use_native_href(self) -> None:
        html_out = build_updates_cards_html(
            [{"id": "u1", "title": "News", "snippet": "Hi", "date": "2026-07-19", "is_unread": True}]
        )
        assert portal_update_href("u1").replace("&", "&amp;") in html_out or "portal_update=u1" in html_out
        assert "st.button" not in html_out

    def test_job_rows_use_native_href(self) -> None:
        html_out = build_job_list_html([{"id": "j1", "job_name": "Job", "customer": "C", "status": "Active"}])
        assert "portal_job=j1" in html_out


class TestSecurity(unittest.TestCase):
    def test_admin_update_hidden_from_employee(self) -> None:
        rows = [
            {"id": "a1", "title": "Admin", "body": "x", "audience": "Admin", "status": "Published", "is_active": True},
        ]
        with patch("app.pages._core._data.load_company_updates", return_value=rows):
            detail = get_employee_portal_update_detail("a1", employee_id="e1", role="employee", user_id="u1")
        assert detail is None

    def test_job_detail_strips_financials(self) -> None:
        with patch(
            "app.services.repository.fetch_by_id",
            return_value={
                "id": "j1",
                "job_name": "Job",
                "status": "Active",
                "awarded_amount": 50000,
                "estimated_cost": 10000,
            },
        ):
            with patch(
                "app.services.employee_portal_detail_service._employee_can_view_job",
                return_value=True,
            ):
                with patch(
                    "app.services.employee_portal_detail_service.list_assigned_job_ids_for_employee",
                    return_value=["j1"],
                ):
                    detail = get_employee_portal_job_detail("j1", employee_id="e1", role="employee")
        assert detail is not None
        assert "awarded_amount" not in detail


class TestCertificationLazyUrl(unittest.TestCase):
    def test_cert_summaries_have_no_url(self) -> None:
        with patch(
            "app.pages._core._data.load_certifications",
            return_value=[
                {
                    "id": "c1",
                    "employee_id": "e1",
                    "cert_type": "OSHA",
                    "expiration_date": "2027-01-01",
                    "attachment_path": "path/file.pdf",
                }
            ],
        ):
            with patch(
                "app.services.certification_helpers.certification_visible_to_user",
                return_value=True,
            ):
                with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                    rows = list_portal_certification_summaries("e1")
        assert rows[0]["has_attachment"] is True
        assert "url" not in rows[0]

    def test_open_target_validates_ownership(self) -> None:
        with patch("app.pages._core._data.load_certifications", return_value=[]):
            result = get_employee_certification_open_target("c1", employee_id="e1")
        assert result.ok is False


class TestSnapshotIsolation(unittest.TestCase):
    def test_snapshot_collects_warnings_without_blank(self) -> None:
        with patch(
            "app.services.employee_portal_service.list_employee_portal_updates",
            side_effect=RuntimeError("boom"),
        ):
            with patch("app.services.employees_service.get_employee", return_value={"id": "e1"}):
                with patch("app.services.employee_portal_service.list_portal_certification_summaries", return_value=[]):
                    with patch("app.services.employee_portal_service.list_portal_dashboard_jobs", return_value=[]):
                        with patch(
                            "app.services.employee_portal_service.list_employee_upcoming_schedule",
                            return_value=[],
                        ):
                            with patch(
                                "app.pages._core.page_data_cache.page_data_cache_get",
                                side_effect=lambda _k, fn: fn(),
                            ):
                                snap = load_employee_portal_snapshot(
                                    employee_id="e1",
                                    role="employee",
                                    user_id="u1",
                                )
        assert snap.updates == []
        assert any("updates" in w.lower() for w in snap.warnings)


class TestWidgetReduction(unittest.TestCase):
    def test_portal_page_no_per_record_open_buttons(self) -> None:
        src = inspect.getsource(portal_page)
        assert 'key=f"ep_upd_' not in src
        assert 'key=f"ep_job_' not in src
        assert 'key=f"ep_cert_' not in src


if __name__ == "__main__":
    unittest.main()
