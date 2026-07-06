"""Tests for cross-module navigation handoffs."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import streamlit as st

from app.navigation import (
    INVENTORY_SCAN_EMBED_KEY,
    JC_FOCUS_JOB_KEY,
    JOBS_DETAIL_FOCUS_TAB_KEY,
    TK_PREFILL_JOB_KEY,
    TK_PREFILL_WEEK_KEY,
    WJT_PREFILL_JOB_KEY,
    WJT_PREFILL_WEEK_KEY,
    navigate_to_estimate_detail,
    navigate_to_estimate_materials,
    navigate_to_timekeeping,
    navigate_to_weekly_timesheet,
    normalize_nav_slug,
    open_jobs_job_costing,
    set_nav_slug,
)


class TestNavigationHandoffs(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    @patch("app.navigation.set_nav_slug")
    def test_open_jobs_job_costing_sets_modal_context(self, nav_mock) -> None:
        open_jobs_job_costing(job_id="job-42")
        self.assertEqual(st.session_state[JC_FOCUS_JOB_KEY], "job-42")
        self.assertEqual(st.session_state["selected_job_id"], "job-42")
        self.assertTrue(st.session_state["show_job_detail_modal"])
        self.assertEqual(st.session_state[JOBS_DETAIL_FOCUS_TAB_KEY], "Job Costing")
        nav_mock.assert_called_once_with("jobs")

    def test_navigate_to_estimate_materials(self) -> None:
        navigate_to_estimate_materials("est-9")
        self.assertEqual(st.session_state["ips_active_estimate_id"], "est-9")
        self.assertEqual(st.session_state["ips_nav_page"], "estimates")

    def test_navigate_to_estimate_detail(self) -> None:
        navigate_to_estimate_detail("est-77")
        self.assertEqual(st.session_state["ips_active_estimate_id"], "est-77")
        self.assertEqual(st.session_state["selected_estimate_id"], "est-77")
        self.assertTrue(st.session_state["show_estimate_detail_modal"])
        self.assertEqual(st.session_state["ips_nav_page"], "estimates")

    def test_navigate_to_weekly_timesheet_prefill(self) -> None:
        navigate_to_weekly_timesheet(job_id="job-1", week_start="2026-05-26")
        self.assertEqual(st.session_state[WJT_PREFILL_JOB_KEY], "job-1")
        self.assertEqual(st.session_state[WJT_PREFILL_WEEK_KEY], "2026-05-26")
        self.assertEqual(st.session_state["ips_nav_page"], "weekly_timesheets")

    def test_navigate_to_timekeeping_prefill(self) -> None:
        navigate_to_timekeeping(job_id="job-9", week_start="2026-05-26")
        self.assertEqual(st.session_state[TK_PREFILL_JOB_KEY], "job-9")
        self.assertEqual(st.session_state[TK_PREFILL_WEEK_KEY], "2026-05-26")
        self.assertEqual(st.session_state["ips_field_job_id"], "job-9")
        self.assertEqual(st.session_state["ips_nav_page"], "timekeeping")

    def test_scan_inventory_uses_embedded_inventory_module(self) -> None:
        set_nav_slug("scan_inventory")
        self.assertEqual(st.session_state["ips_nav_page"], "inventory")
        self.assertTrue(st.session_state[INVENTORY_SCAN_EMBED_KEY])

    def test_normalize_unknown_slug_falls_back_to_dashboard(self) -> None:
        self.assertEqual(normalize_nav_slug("asset_detail"), "dashboard")
        self.assertEqual(normalize_nav_slug("scan_inventory"), "inventory")
        self.assertEqual(normalize_nav_slug(""), "dashboard")

    def test_normalize_unknown_slug_falls_back_to_field_dashboard(self) -> None:
        st.session_state["ips_field_mode"] = True
        self.assertEqual(normalize_nav_slug("not_a_real_page"), "field_dashboard")


if __name__ == "__main__":
    unittest.main()
