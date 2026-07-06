"""Tests for company update banner uploads and display."""

from __future__ import annotations

from app.components.company_updates_feed import connecteam_feed_card_compact_html
from app.services.company_update_banner_service import (
    enrich_company_update_banner,
    has_company_update_banner,
    resolve_company_update_banner_url,
    validate_banner_upload,
)


class _FakeUpload:
    def __init__(self, name: str, data: bytes, mime: str = "image/png") -> None:
        self.name = name
        self.type = mime
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def test_validate_banner_upload_accepts_png():
    upload = _FakeUpload("notice.png", b"x" * 32, "image/png")
    result = validate_banner_upload(upload)
    assert isinstance(result, tuple)
    assert result[1] == "notice.png"


def test_validate_banner_upload_rejects_large_file():
    upload = _FakeUpload("big.jpg", b"x" * (5 * 1024 * 1024 + 1), "image/jpeg")
    assert "5 MB" in str(validate_banner_upload(upload))


def test_validate_banner_upload_rejects_bad_type():
    upload = _FakeUpload("notes.pdf", b"pdf", "application/pdf")
    assert "Unsupported" in str(validate_banner_upload(upload))


def test_resolve_company_update_banner_url_uses_demo_url():
    row = {"banner_view_url": "https://example.com/banner.webp"}
    assert resolve_company_update_banner_url(row) == "https://example.com/banner.webp"
    assert has_company_update_banner(row)


def test_enrich_company_update_banner_keeps_existing_url():
    row = enrich_company_update_banner({"banner_view_url": "https://example.com/a.jpg"})
    assert row["banner_view_url"] == "https://example.com/a.jpg"


def test_compact_feed_card_renders_banner():
    html_out = connecteam_feed_card_compact_html(
        {
            "id": "x2",
            "title": "Plant Shutdown",
            "body": "No work Saturday.",
            "category": "General",
            "date": "2026-05-29",
            "created_by_name": "Ops",
            "priority": "Important",
            "banner_view_url": "https://example.com/shutdown.jpg",
        }
    )
    assert "ips-cu-banner" in html_out
    assert "ips-cu-has-banner" in html_out
    assert "shutdown.jpg" in html_out
    assert "Plant Shutdown" in html_out
