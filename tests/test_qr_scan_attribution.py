"""Tests for QR scan history attribution and summary formatting."""

from __future__ import annotations

from app.services.qr_scan_event_service import list_qr_scan_events, qr_scan_summary_line


def test_qr_scan_summary_line_formats_actor_job_and_item():
    summary = qr_scan_summary_line(
        scanned_by_name="Amanda",
        scanned_at="2026-07-08T17:05:00+00:00",
        job_shop="J26101 — I/E Labor",
        item_name="Welding wire",
    )
    assert summary.startswith("Amanda • 2026-07-08 17:05 • ")
    assert "J26101 — I/E Labor — Welding wire" in summary


def test_qr_scan_summary_line_without_job():
    summary = qr_scan_summary_line(
        scanned_by_name="Amanda",
        scanned_at="2026-07-08T17:05:00+00:00",
        job_shop="—",
        item_name="Welding wire",
    )
    assert summary == "Amanda • 2026-07-08 17:05 • Welding wire"


def test_list_qr_scan_events_skips_opened_and_uses_saved_scanner(monkeypatch):
    rows = [
        {
            "created_at": "2026-07-08T18:00:00+00:00",
            "qr_value": "INV-1",
            "item_type": "inventory",
            "item_name": "Opened item",
            "result": "opened",
            "scanned_by_name": "Chet Breaux",
            "job_id": None,
            "destination_type": None,
            "source": "inventory_scan_desktop",
        },
        {
            "created_at": "2026-07-08T17:05:00+00:00",
            "qr_value": "INV-2",
            "item_type": "inventory",
            "item_name": "Welding wire",
            "result": "success",
            "scanned_by_name": "Amanda",
            "scanned_by_user_id": "user-amanda",
            "device_label": "iPhone",
            "job_id": "job-1",
            "destination_type": "job",
            "action_taken": "Use on job",
            "source": "mobile_qr_scan",
        },
    ]

    def fake_fetch_rows(table, **_kwargs):
        if table == "qr_scan_events":
            return rows, None
        if table == "jobs":
            return [
                {
                    "id": "job-1",
                    "job_number": "J26101",
                    "job_name": "I/E Labor",
                }
            ], None
        return [], None

    monkeypatch.setattr("app.services.repository.fetch_rows", fake_fetch_rows)

    out = list_qr_scan_events(limit=10)
    assert len(out) == 1
    assert out[0]["scanned_by"] == "Amanda"
    assert out[0]["scanned_by_user_id"] == "user-amanda"
    assert out[0]["device_label"] == "iPhone"
    assert "Amanda" in out[0]["summary"]
    assert "J26101 — I/E Labor" in out[0]["summary"]
    assert "Welding wire" in out[0]["summary"]
