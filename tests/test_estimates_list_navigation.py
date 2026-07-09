"""Tests for Estimates list navigation helpers."""

from __future__ import annotations

import unittest

import streamlit as st

from app.components.estimates_list_table import (
    ESTIMATES_MODE_KEY,
    ESTIMATES_SELECTED_ID_KEY,
    open_estimate_detail,
)


class TestEstimatesListNavigation(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_open_estimate_detail_sets_inline_detail_mode(self) -> None:
        open_estimate_detail("est-42")
        self.assertEqual(st.session_state[ESTIMATES_SELECTED_ID_KEY], "est-42")
        self.assertEqual(st.session_state[ESTIMATES_MODE_KEY], "detail")
        self.assertFalse(st.session_state["show_estimate_detail_modal"])

    def test_open_estimate_detail_ignores_blank_id(self) -> None:
        open_estimate_detail("")
        self.assertNotIn(ESTIMATES_SELECTED_ID_KEY, st.session_state)
        self.assertNotIn(ESTIMATES_MODE_KEY, st.session_state)


if __name__ == "__main__":
    unittest.main()
