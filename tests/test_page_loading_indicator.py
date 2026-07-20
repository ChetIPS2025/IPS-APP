"""Tests for global page loading indicator settle behavior."""

from __future__ import annotations

import inspect
import unittest

from app.ui import page_loading_indicator as pli


class TestPageLoadingIndicator(unittest.TestCase):
    def test_recognizes_page_ready_marker(self) -> None:
        source = inspect.getsource(pli.inject_page_loading_indicator)
        self.assertIn("isPageReady", source)
        self.assertIn(".ips-page-ready", source)

    def test_weekly_day_link_skips_loading_on_click(self) -> None:
        source = inspect.getsource(pli.inject_page_loading_indicator)
        self.assertIn("timekeeping-weekly-day-link", source)

    def test_spinner_detection_is_visibility_aware(self) -> None:
        source = inspect.getsource(pli.inject_page_loading_indicator)
        self.assertIn("function elementIsVisible", source)
        self.assertIn("!el.isConnected", source)
        self.assertIn("getBoundingClientRect()", source)
        self.assertNotIn("classList.contains(\"stSpinner\")", source)

    def test_has_running_spinner_uses_visible_nodes_only(self) -> None:
        source = inspect.getsource(pli.inject_page_loading_indicator)
        self.assertIn("function hasRunningSpinner", source)
        self.assertIn("elementIsVisible(spinners[i])", source)

    def test_mutation_observer_does_not_restart_fail_safe(self) -> None:
        source = inspect.getsource(pli.inject_page_loading_indicator)
        self.assertIn("showLoading({ restartFailSafe: false })", source)
        self.assertIn("showLoading({ restartFailSafe: true })", source)
        self.assertIn("function startFailSafe", source)

    def test_page_ready_marker_hides_loading_immediately(self) -> None:
        source = inspect.getsource(pli.inject_page_loading_indicator)
        self.assertIn("if (isPageReady())", source)
        self.assertIn("hideLoadingNow()", source)

    def test_schedule_hide_uses_visible_spinner_check(self) -> None:
        source = inspect.getsource(pli.inject_page_loading_indicator)
        self.assertIn("if (!hasRunningSpinner())", source)

    def test_dev_loading_diagnostics(self) -> None:
        source = inspect.getsource(pli.inject_page_loading_indicator)
        self.assertIn("page_loading.show", source)
        self.assertIn("page_loading.hide", source)
        self.assertIn("visible_spinner_count", source)
        self.assertIn("page_loading.fail_safe", source)

    def test_render_page_ready_marker_helper(self) -> None:
        source = inspect.getsource(pli.render_page_ready_marker)
        self.assertIn("ips-page-ready", source)
        self.assertIn("ips-{slug}-page-ready", source)


if __name__ == "__main__":
    unittest.main()
