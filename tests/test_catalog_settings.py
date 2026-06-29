"""Phase 5: pricing catalog fail-loud, lookup SSOT, company settings."""

from __future__ import annotations

from app.services.company_settings_service import save_app_settings
from app.services.lookup_service import load_lookup_entries, supabase_is_configured
from app.services.pricing_guide_service import fetch_pricing_guide_catalog


def test_fetch_pricing_no_legacy_fallback_in_production(monkeypatch):
    monkeypatch.setattr("app.services.pricing_guide_service._allow_legacy_pricing_fallback", lambda: False)

    def fake_fetch(table, **kwargs):
        if table == "pricing_guide_items":
            raise RuntimeError("relation missing")
        return []

    monkeypatch.setattr("app.services.pricing_guide_service._load_lookup_maps", lambda: ({}, {}, {}, {}, {}, {}))

    result = fetch_pricing_guide_catalog(
        fetch_table=fake_fetch,
        fetch_table_admin=fake_fetch,
    )
    assert result.rows == []
    assert result.fetch_failed is True
    assert result.warning
    assert "estimate_materials" in result.warning


def test_fetch_pricing_legacy_allowed_in_development(monkeypatch):
    monkeypatch.setattr("app.services.pricing_guide_service._allow_legacy_pricing_fallback", lambda: True)
    monkeypatch.setattr("app.services.pricing_guide_service._load_lookup_maps", lambda: ({}, {}, {}, {}, {}, {}))

    def fake_fetch(table, **kwargs):
        if table == "pricing_guide_items":
            return []
        if table == "estimate_materials":
            return [{"id": "m1", "item_key": "BOLT", "description": "Bolt", "is_active": True}]
        return []

    result = fetch_pricing_guide_catalog(
        fetch_table=fake_fetch,
        fetch_table_admin=fake_fetch,
    )
    assert len(result.rows) == 1
    assert result.source == "estimate_materials"
    assert result.rows[0].get("_source") == "estimate_materials"


def test_load_lookup_skips_constants_when_supabase_configured(monkeypatch):
    monkeypatch.setattr("app.services.lookup_service.supabase_is_configured", lambda: True)
    monkeypatch.setattr("app.services.repository.fetch_rows", lambda table, **kwargs: ([], None))
    entries, source = load_lookup_entries("crews")
    assert entries == []
    assert source == "empty"


def test_load_lookup_uses_constants_when_offline(monkeypatch):
    monkeypatch.setattr("app.services.lookup_service.supabase_is_configured", lambda: False)
    monkeypatch.setattr("app.services.repository.fetch_rows", lambda table, **kwargs: ([], None))
    entries, source = load_lookup_entries("crews")
    assert entries
    assert source == "constants"


def test_save_company_settings_updates_existing_row(monkeypatch):
    updates: list[tuple[dict, dict]] = []

    def fake_fetch_rows(table, **kwargs):
        assert table == "company_settings"
        return ([{"id": "cfg-1", "timezone": "UTC"}], None)

    def fake_update_row(table, payload, match):
        updates.append((payload, match))
        class R:
            ok = True
            error = None
        return R()

    monkeypatch.setattr("app.services.repository.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.services.repository.update_row", fake_update_row)

    ok, msg = save_app_settings(
        default_landing_page="Jobs",
        date_format="ISO",
        timezone_name="America/New_York",
        email_notifications_enabled=False,
    )
    assert ok is True
    assert "saved" in msg.lower()
    assert updates[0][0]["default_landing_page"] == "Jobs"
    assert updates[0][0]["email_notifications_enabled"] is False
    assert updates[0][1]["id"] == "cfg-1"


def test_supabase_is_configured_respects_validator(monkeypatch):
    monkeypatch.setattr("app.config.validate_supabase_public_config", lambda: None)
    assert supabase_is_configured() is True
    monkeypatch.setattr("app.config.validate_supabase_public_config", lambda: "missing")
    assert supabase_is_configured() is False
