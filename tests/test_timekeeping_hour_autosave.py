"""Tests for timekeeping list-view hour autosave debouncing."""

from __future__ import annotations

import unittest

import streamlit as st

from app.pages import timekeeping as tk


class TestHourAutosaveIsDue(unittest.TestCase):
    def test_not_due_without_pending(self) -> None:
        self.assertFalse(
            tk.hour_autosave_is_due(pending_at=0.0, flushed_at=0.0, now=10.0)
        )

    def test_not_due_when_already_flushed(self) -> None:
        self.assertFalse(
            tk.hour_autosave_is_due(pending_at=5.0, flushed_at=5.0, now=10.0)
        )
        self.assertFalse(
            tk.hour_autosave_is_due(pending_at=5.0, flushed_at=6.0, now=10.0)
        )

    def test_not_due_before_debounce_elapses(self) -> None:
        self.assertFalse(
            tk.hour_autosave_is_due(
                pending_at=9.0,
                flushed_at=0.0,
                now=9.5,
                debounce_sec=1.0,
            )
        )

    def test_due_after_debounce_elapses(self) -> None:
        self.assertTrue(
            tk.hour_autosave_is_due(
                pending_at=9.0,
                flushed_at=0.0,
                now=10.0,
                debounce_sec=1.0,
            )
        )

    def test_default_debounce_matches_module_constant(self) -> None:
        pending = 100.0
        self.assertFalse(
            tk.hour_autosave_is_due(
                pending_at=pending,
                flushed_at=0.0,
                now=pending + tk._TK_HOUR_AUTOSAVE_DEBOUNCE_SEC - 0.01,
            )
        )
        self.assertTrue(
            tk.hour_autosave_is_due(
                pending_at=pending,
                flushed_at=0.0,
                now=pending + tk._TK_HOUR_AUTOSAVE_DEBOUNCE_SEC,
            )
        )


class TestEmployeeHasPendingHourAutosave(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_false_without_session_keys(self) -> None:
        self.assertFalse(tk._employee_has_pending_hour_autosave("emp-1", "2026-07-06"))

    def test_true_when_pending_not_flushed(self) -> None:
        st.session_state[tk._hour_pending_autosave_key("emp-1", "2026-07-06", 2)] = 42.0
        self.assertTrue(tk._employee_has_pending_hour_autosave("emp-1", "2026-07-06"))

    def test_false_when_pending_matches_flushed(self) -> None:
        st.session_state[tk._hour_pending_autosave_key("emp-1", "2026-07-06", 2)] = 42.0
        st.session_state[tk._hour_flushed_autosave_key("emp-1", "2026-07-06", 2)] = 42.0
        self.assertFalse(tk._employee_has_pending_hour_autosave("emp-1", "2026-07-06"))


if __name__ == "__main__":
    unittest.main()
