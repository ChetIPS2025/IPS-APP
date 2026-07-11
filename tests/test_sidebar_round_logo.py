"""Tests for transparent round IPS sidebar logo branding."""

from __future__ import annotations

from pathlib import Path

from app.branding import get_sidebar_round_logo_path, sidebar_round_logo_html


def test_sidebar_round_logo_asset_is_transparent_png():
    path = get_sidebar_round_logo_path()
    assert path is not None
    assert path.name == "ips_logo_round.png"
    try:
        from PIL import Image
    except ImportError:
        return
    with Image.open(path) as im:
        assert im.mode == "RGBA"
        assert im.getpixel((0, 0))[3] == 0


def test_sidebar_round_logo_html_preserves_transparency_styles():
    html = sidebar_round_logo_html(size_px=40, css_class="sidebar-logo-icon")
    assert "sidebar-logo navigation-logo app-logo sidebar-logo-icon" in html
    assert "object-fit:contain" in html
    assert "background:transparent" in html
    assert 'width="40"' in html
    assert "data:image/png;base64," in html


def test_sidebar_round_logo_path_lives_in_assets():
    path = get_sidebar_round_logo_path()
    assert path is not None
    assert path.parent.name == "assets"
    assert Path("assets/ips_logo_round.png").resolve() == path.resolve()
