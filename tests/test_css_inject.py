"""Tests for session-guarded CSS injection helper."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.ui.css_inject import css_inject_key, inject_css_once


class CssInjectTests(unittest.TestCase):
    def test_css_inject_key_normalizes_style_id(self) -> None:
        self.assertEqual(
            css_inject_key("ips-global-styles-v19"),
            "ips_css_injected_ips-global-styles-v19",
        )

    @patch("app.ui.css_inject.st.session_state", new_callable=dict)
    def test_inject_css_once_returns_true_only_first_time(self, session_state: dict) -> None:
        first = inject_css_once("ips-test-style-v1")
        second = inject_css_once("ips-test-style-v1")

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertTrue(session_state[css_inject_key("ips-test-style-v1")])

    @patch("app.ui.css_inject.st.session_state", new_callable=dict)
    def test_inject_css_once_isolated_per_style_id(self, session_state: dict) -> None:
        self.assertTrue(inject_css_once("ips-a-v1"))
        self.assertTrue(inject_css_once("ips-b-v1"))
        self.assertFalse(inject_css_once("ips-a-v1"))


if __name__ == "__main__":
    unittest.main()
