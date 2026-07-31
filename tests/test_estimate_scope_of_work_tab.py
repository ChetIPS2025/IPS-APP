"""Scope of Work tab sync helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.pages import estimate_builder_ui as ui


class TestEstimateScopeOfWorkTab(unittest.TestCase):
    def test_scope_form_fingerprint_tracks_saved_text(self) -> None:
        est = {
            "id": "e1",
            "scope_of_work": "Install fire pump skid",
            "customer_responsibilities": "Provide crane access",
        }
        fp = ui._scope_form_fingerprint(est)
        self.assertIn("Install fire pump skid", fp)
        self.assertIn("Provide crane access", fp)

    def test_seed_scope_form_reloads_when_estimate_scope_changes(self) -> None:
        est = {
            "id": "e1",
            "scope_of_work": "Saved scope text",
            "customer_responsibilities": "",
        }
        session: dict = {
            ui._scope_form_sync_key("e1"): "\0",
            "est_sow_text_e1": "",
            "est_sow_cr_e1": "",
        }
        with patch.object(ui.st, "session_state", session, create=True):
            ui._seed_scope_form_from_estimate(est)
        self.assertEqual(session["est_sow_text_e1"], "Saved scope text")
        self.assertEqual(session[ui._scope_form_sync_key("e1")], ui._scope_form_fingerprint(est))

    def test_seed_scope_form_skips_when_fingerprint_unchanged(self) -> None:
        est = {
            "id": "e1",
            "scope_of_work": "Keep my draft",
            "customer_responsibilities": "",
        }
        fp = ui._scope_form_fingerprint(est)
        session = {
            ui._scope_form_sync_key("e1"): fp,
            "est_sow_text_e1": "User typed this before save",
            "est_sow_cr_e1": "",
        }
        with patch.object(ui.st, "session_state", session, create=True):
            ui._seed_scope_form_from_estimate(est)
        self.assertEqual(session["est_sow_text_e1"], "User typed this before save")


if __name__ == "__main__":
    unittest.main()
