"""Tests for CSS injection helper."""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path
from unittest.mock import patch

from app.ui.css_inject import css_inject_key, inject_css_once

_ROOT = Path(__file__).resolve().parents[1]
_APP = _ROOT / "app"


class CssInjectTests(unittest.TestCase):
    def test_css_inject_key_normalizes_style_id(self) -> None:
        self.assertEqual(
            css_inject_key("ips-global-styles-v19"),
            "ips_css_injected_ips-global-styles-v19",
        )

    @patch("app.ui.css_inject.st.session_state", new_callable=dict)
    def test_inject_css_once_always_allows_injection(self, session_state: dict) -> None:
        """Each rerun must re-emit style tags — guard must not block second call."""
        first = inject_css_once("ips-test-style-v1")
        second = inject_css_once("ips-test-style-v1")

        self.assertTrue(first)
        self.assertTrue(second)
        self.assertTrue(session_state[css_inject_key("ips-test-style-v1")])

    @patch("app.ui.css_inject.st.session_state", new_callable=dict)
    def test_inject_css_once_tracks_per_style_id(self, session_state: dict) -> None:
        self.assertTrue(inject_css_once("ips-a-v1"))
        self.assertTrue(inject_css_once("ips-b-v1"))
        self.assertTrue(inject_css_once("ips-a-v1"))
        self.assertTrue(session_state[css_inject_key("ips-a-v1")])
        self.assertTrue(session_state[css_inject_key("ips-b-v1")])

    def test_inject_global_css_called_only_from_main(self) -> None:
        callers: list[str] = []
        for path in _APP.rglob("*.py"):
            rel = path.relative_to(_ROOT).as_posix()
            if rel in {"app/styles.py", "app/ui/styles.py", "app/components/tables.py"}:
                continue
            src = path.read_text(encoding="utf-8")
            if "inject_global_css(" in src:
                callers.append(rel)
        self.assertEqual(callers, ["app/main.py"])

    def test_main_calls_inject_global_css_once(self) -> None:
        from app import main as app_main

        src = inspect.getsource(app_main.main)
        self.assertEqual(src.count("inject_global_css("), 1)


if __name__ == "__main__":
    unittest.main()
