"""Pricing option search helpers."""

from __future__ import annotations

from app.services.estimate_builder_helpers import filter_pricing_option_labels


def test_filter_pricing_option_labels_matches_description_sku_and_label():
    options = [
        ("12PK 75/25 — Consumable", {"description": "12PK 75/25", "category": "Consumable"}),
        ("1in Ball Valve — Material", {"description": '1" BALL VALVE', "sku": "BV-100"}),
    ]
    assert filter_pricing_option_labels(options, "ball") == ["1in Ball Valve — Material"]
    assert filter_pricing_option_labels(options, "12pk") == ["12PK 75/25 — Consumable"]
    assert filter_pricing_option_labels(options, "bv-100") == ["1in Ball Valve — Material"]
    assert filter_pricing_option_labels(options, "") == [label for label, _ in options]
