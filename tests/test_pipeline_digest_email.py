"""Pipeline attention digest email tests."""

from __future__ import annotations

from unittest.mock import patch

from app.services.email_notifications import (
    _pipeline_digest_bodies,
    run_pipeline_attention_digest,
)


def test_pipeline_digest_bodies_include_hint():
    text, html = _pipeline_digest_bodies(
        [
            {
                "quote_number": "Q26001",
                "job_number": "—",
                "customer": "Acme",
                "stale_hint": "Sent 20d ago — no response",
                "value": 1200,
            }
        ]
    )
    assert "Q26001" in text
    assert "no response" in text.lower()
    assert "Q26001" in html


@patch("app.services.email_notifications._send_email")
@patch("app.services.email_notifications._pipeline_attention_rows")
@patch("app.services.email_notifications.pipeline_digest_recipients")
def test_run_pipeline_attention_digest_sends(mock_recipients, mock_rows, mock_send):
    mock_rows.return_value = [{"quote_number": "Q1", "stale_hint": "Stale", "value": 0}]
    mock_recipients.return_value = ["ops@example.com"]
    result = run_pipeline_attention_digest()
    assert result["sent"] == 1
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["notification_type"] == "pipeline_attention_digest"


@patch("app.services.email_notifications.pipeline_digest_recipients")
@patch("app.services.email_notifications._pipeline_attention_rows")
def test_run_pipeline_attention_digest_skips_when_empty(mock_rows, mock_recipients):
    mock_rows.return_value = []
    mock_recipients.return_value = ["ops@example.com"]
    assert run_pipeline_attention_digest() == {"sent": 0, "skipped": 1, "failed": 0}
