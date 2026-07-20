"""Tests for timekeeping native day-link navigation."""

from __future__ import annotations

import inspect
import unittest
from datetime import date
from unittest.mock import patch

import streamlit as st

from app.pages import timekeeping as tk


class _QueryParams(dict):
    def get(self, key, default=None):
        return dict.get(self, key, default)

    def __contains__(self, key):
        return dict.__contains__(self, key)

    def __delitem__(self, key):
        dict.__delitem__(self, key)


class TestTimekeepingDayLinks(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()
        tk.clear_timekeeping_list_caches()

    def test_timekeeping_day_href_contains_required_params(self) -> None:
        href = tk._timekeeping_day_href(
            employee_id="emp-42",
            work_date=date(2026, 7, 20),
            timecard_id="tc-99",
        )
        self.assertIn("ips_nav=timekeeping", href)
        self.assertIn("tk_employee=emp-42", href)
        self.assertIn("tk_date=2026-07-20", href)
        self.assertIn("tk_timecard=tc-99", href)
        self.assertTrue(href.startswith("?"))

    def test_timekeeping_day_href_url_encodes_values(self) -> None:
        href = tk._timekeeping_day_href(
            employee_id="emp id/with&chars",
            work_date=date(2026, 7, 20),
            timecard_id="tc+1",
        )
        self.assertIn("tk_employee=emp+id%2Fwith%26chars", href)
        self.assertIn("tk_timecard=tc%2B1", href)

    def test_clickable_day_cell_html_uses_native_link(self) -> None:
        html_out = tk._clickable_list_day_cell_html(
            day_d=date(2026, 7, 20),
            day_ix=0,
            day_row={"status": "Draft", "st": 8, "ot": 0},
            eid="emp-1",
            timecard_id="tc-1",
        )
        self.assertIn('<a class="timekeeping-day-native-link"', html_out)
        self.assertIn('href="?', html_out)
        self.assertIn('target="_self"', html_out)
        self.assertIn('aria-label="Open', html_out)

    def test_collapsed_day_cells_no_streamlit_button(self) -> None:
        cell_source = inspect.getsource(tk._render_clickable_list_day_cell)
        collapsed_source = inspect.getsource(tk._render_timekeeping_employee_row_collapsed)
        self.assertNotIn("st.button", cell_source)
        self.assertNotIn("st.button", collapsed_source)
        self.assertIn("_clickable_list_day_cell_html", cell_source)

    @patch("app.pages.timekeeping._open_day_time_editor")
    def test_capture_timekeeping_day_query_opens_editor(self, open_mock) -> None:
        st.session_state[tk._WEEK_KEY] = date(2026, 7, 6)
        st.query_params = _QueryParams(
            {
                "ips_nav": "timekeeping",
                "tk_employee": "emp-1",
                "tk_date": "2026-07-08",
                "tk_timecard": "tc-1",
            }
        )
        with patch.object(st, "rerun") as rerun_mock:
            tk._capture_timekeeping_day_query()
        open_mock.assert_called_once_with(
            eid="emp-1",
            work_date=date(2026, 7, 8),
            timecard_id="tc-1",
            week_start_d=date(2026, 7, 6),
        )
        rerun_mock.assert_not_called()

    @patch("app.pages.timekeeping._open_day_time_editor")
    def test_capture_invalid_date_does_not_crash(self, open_mock) -> None:
        st.query_params = _QueryParams(
            {
                "tk_employee": "emp-1",
                "tk_date": "not-a-date",
            }
        )
        tk._capture_timekeeping_day_query()
        open_mock.assert_not_called()

    def test_clear_day_modal_removes_only_timekeeping_day_query_keys(self) -> None:
        st.session_state[tk.TIMEKEEPING_MODAL_EMPLOYEE_ID_KEY] = "emp-1"
        st.session_state[tk.TIMEKEEPING_MODAL_DATE_KEY] = "2026-07-08"
        st.query_params = _QueryParams(
            {
                "ips_nav": "timekeeping",
                "tk_employee": "emp-1",
                "tk_date": "2026-07-08",
                "tk_timecard": "tc-1",
                "foo": "bar",
            }
        )
        tk._clear_day_time_modal()
        self.assertNotIn("tk_employee", st.query_params)
        self.assertNotIn("tk_date", st.query_params)
        self.assertNotIn("tk_timecard", st.query_params)
        self.assertEqual(st.query_params.get("ips_nav"), "timekeeping")
        self.assertEqual(st.query_params.get("foo"), "bar")

    def test_render_fast_path_skips_employee_list(self) -> None:
        render_source = inspect.getsource(tk.render)
        fast_idx = render_source.index("_is_day_editor_active()")
        snapshot_idx = render_source.index("load_weekly_timekeeping_page(")
        self.assertLess(fast_idx, snapshot_idx)
        self.assertIn("_capture_timekeeping_day_query()", render_source)
        self.assertIn("_render_timekeeping_table_area", render_source)

    def test_desktop_panel_and_mobile_dialog_remain_wired(self) -> None:
        render_source = inspect.getsource(tk.render)
        self.assertIn("_render_day_time_entry_panel", render_source)
        self.assertIn("show_modal_if_pending(SHOW_TIMEKEEPING_DAY_MODAL_KEY", render_source)
        self.assertIn("@st.dialog", inspect.getsource(tk._show_day_time_dialog))

    def test_loading_indicator_skips_timekeeping_day_links(self) -> None:
        from app.ui import page_loading_indicator as pli

        src = inspect.getsource(pli.inject_page_loading_indicator)
        self.assertIn("timekeeping-day-native-link", src)


if __name__ == "__main__":
    unittest.main()
