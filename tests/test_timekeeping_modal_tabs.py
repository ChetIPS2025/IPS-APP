"""Tests for lazy timecard modal tabs and permission snapshots."""

from __future__ import annotations

import inspect
import unittest
from datetime import date
from unittest.mock import patch

import streamlit as st

from app.pages import timekeeping as tk


class TestTimekeepingModalTabs(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()
        tk.clear_timekeeping_list_caches()
        tk.clear_timekeeping_permissions_snapshot()

    def test_view_tabs_use_render_tabs_not_streamlit_tabs(self) -> None:
        source = inspect.getsource(tk._render_timekeeping_view_tabs)
        self.assertIn("render_tabs", source)
        self.assertNotIn("st.tabs", source)
        self.assertIn('_TIMEKEEPING_DETAIL_TAB_KEY', source)

    def test_weekly_tab_does_not_call_daily_entries(self) -> None:
        source = inspect.getsource(tk._render_timekeeping_view_tabs)
        weekly_block = source.split('if active_tab == "Weekly Timecard"')[1].split("elif active_tab")[0]
        self.assertNotIn("_render_daily_entries_tab", weekly_block)
        self.assertNotIn("_render_weekly_grid_edit", weekly_block)
        self.assertNotIn("_assignment_options_for_timekeeping", weekly_block)

    def test_approval_tab_does_not_render_daily_grid(self) -> None:
        source = inspect.getsource(tk._render_timekeeping_view_tabs)
        approval_block = source.split('elif active_tab == "Approval"')[1].split("elif active_tab")[0]
        self.assertNotIn("_render_weekly_grid_edit", approval_block)
        self.assertNotIn("_render_daily_entries_tab", approval_block)

    def test_notes_and_activity_tabs_skip_allocation(self) -> None:
        source = inspect.getsource(tk._render_timekeeping_view_tabs)
        notes_block = source.split('elif active_tab == "Notes"')[1].split("elif active_tab")[0]
        activity_block = source.split('elif active_tab == "Activity"')[1].split("def render_timekeeping_detail_dialog")[0]
        for block in (notes_block, activity_block):
            self.assertNotIn("_ensure_allocation_state", block)
            self.assertNotIn("_assignment_options_for_timekeeping", block)

    @patch.object(tk, "_render_daily_entries_tab")
    @patch.object(tk, "_render_approval_tab")
    @patch("app.components.tabs.render_tabs", return_value="Weekly Timecard")
    def test_only_selected_tab_renderer_runs(
        self,
        _tabs_mock,
        approval_mock,
        daily_mock,
    ) -> None:
        emp = {"id": "emp-1", "employee_id": "emp-1", "employee_name": "Pat"}
        tk._render_timekeeping_view_tabs(emp, date(2026, 7, 6))
        daily_mock.assert_not_called()
        approval_mock.assert_not_called()

    @patch.object(tk, "_render_weekly_grid_edit")
    @patch("app.components.tabs.render_tabs", return_value="Daily Entries")
    def test_daily_entries_tab_selected_runs_daily_only(self, _tabs_mock, grid_mock) -> None:
        emp = {"id": "emp-1", "employee_id": "emp-1", "employee_name": "Pat"}
        with patch.object(tk, "_render_approval_tab") as approval_mock:
            with patch.object(tk, "_resolved_week_status", return_value="Draft"):
                with patch.object(tk, "_render_daily_entries_tab") as daily_mock:
                    tk._render_timekeeping_view_tabs(emp, date(2026, 7, 6))
                    daily_mock.assert_called_once()
        approval_mock.assert_not_called()
        grid_mock.assert_not_called()

    @patch("app.auth.effective_role", return_value="supervisor")
    @patch("app.utils.permissions.can_submit_timekeeping", return_value=True)
    @patch("app.utils.permissions.can_approve_timekeeping", return_value=True)
    @patch("app.utils.permissions.can_admin_edit_approved_timekeeping", return_value=False)
    @patch("app.utils.permissions.role_can_access_page", return_value=True)
    @patch("app.utils.permissions.normalize_role", return_value="supervisor")
    def test_permission_snapshot_calculated_once(
        self,
        _norm_mock,
        _jobs_mock,
        _admin_mock,
        _approve_mock,
        _submit_mock,
        role_mock,
    ) -> None:
        with patch.object(tk, "_load_weekend_counts_toward_40", return_value=False):
            tk._init_timekeeping_render_context()
        self.assertEqual(role_mock.call_count, 1)
        _ = tk._can_submit_timekeeping()
        _ = tk._can_approve_timekeeping()
        _ = tk._can_admin_edit_approved_timekeeping()
        self.assertEqual(role_mock.call_count, 1)

    def test_collapsed_row_does_not_call_effective_role(self) -> None:
        source = inspect.getsource(tk._render_timekeeping_employee_row_collapsed)
        self.assertNotIn("effective_role", source)
        self.assertNotIn("_can_submit_timekeeping", source)

    def test_current_user_id_does_not_call_auth_get_user(self) -> None:
        source = inspect.getsource(tk._current_user_id)
        self.assertNotIn("get_user", source)
        self.assertNotIn("current_profile", source)
        self.assertNotIn("ensure_authenticated", source)

    @patch("app.services.company_settings_service.load_app_settings")
    def test_weekend_setting_cached_per_render(self, settings_mock) -> None:
        settings_mock.return_value = {"timekeeping_weekend_counts_toward_40": True}
        st.session_state.clear()
        tk.clear_timekeeping_permissions_snapshot()
        with patch.object(tk, "_timekeeping_permissions") as perms_mock:
            perms_mock.return_value = tk.TimekeepingPermissions(
                role="admin",
                can_submit=True,
                can_approve=True,
                can_edit_approved=True,
                can_override_overtime=True,
                can_access_jobs=True,
            )
            tk._init_timekeeping_render_context()
        self.assertEqual(settings_mock.call_count, 1)
        self.assertTrue(tk._weekend_counts_toward_40())
        self.assertTrue(tk._weekend_counts_toward_40())
        self.assertEqual(settings_mock.call_count, 1)

    def test_modal_fast_path_skips_table_before_summaries(self) -> None:
        render_src = inspect.getsource(tk.render)
        modal_idx = render_src.index("_timecard_detail_modal_pending()")
        summaries_idx = render_src.index("summaries = _filter_summaries_for_field_user")
        self.assertLess(modal_idx, summaries_idx)

    def test_closing_modal_clears_selection(self) -> None:
        st.session_state[tk.SELECTED_TIMECARD_KEY] = "emp-1_2026-07-06"
        st.session_state[tk.SHOW_TIMECARD_MODAL_KEY] = True
        tk._clear_timecard_modal()
        self.assertIsNone(st.session_state.get(tk.SELECTED_TIMECARD_KEY))
        self.assertFalse(st.session_state.get(tk.SHOW_TIMECARD_MODAL_KEY))

    def test_opening_different_timecard_resets_tab(self) -> None:
        st.session_state[tk._TIMEKEEPING_DETAIL_TAB_KEY] = "Daily Entries"
        st.session_state[tk._TK_DETAIL_TAB_EMP_KEY] = "emp-1_2026-07-06"
        tk._prepare_timecard_detail_modal("emp-2_2026-07-06")
        self.assertEqual(st.session_state[tk._TIMEKEEPING_DETAIL_TAB_KEY], "Weekly Timecard")


if __name__ == "__main__":
    unittest.main()
