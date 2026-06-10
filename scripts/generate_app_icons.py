#!/usr/bin/env python3
"""Generate favicon, PWA, Streamlit, and desktop icons from the IPS branding source."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.app_icon import (  # noqa: E402
    APP_STATIC_DIR,
    BRANDING_DIR,
    DESKTOP_STATIC_DIR,
    STREAMLIT_STATIC_DIR,
    app_icon_source_path,
)

_PWA_SIZES = (72, 96, 128, 144, 152, 180, 192, 384, 512)
_FAVICON_SIZES = (16, 32, 48)
_ICO_SIZES = (16, 32, 48, 64, 128, 256)


def _load_source() -> Image.Image:
    source = app_icon_source_path()
    if not source:
        raise FileNotFoundError(
            "Missing IPS app icon source. Add assets/branding/ips_app_icon_source.jpg "
            "or assets/IPS Icon.png."
        )
    return Image.open(source).convert("RGBA")


def _crop_icon_square(im: Image.Image) -> Image.Image:
    """Use the square IPS icon only — crop letterboxed art or phone screenshots."""
    w, h = im.size
    aspect = h / max(w, 1)

    # Square / landscape source, or portrait asset with centered icon on black bars.
    if aspect <= 1.8:
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        return im.crop((left, top, left + side, top + side))

    # Tall phone screenshot: first iOS home-screen icon (top row, left column).
    side = int(w * 0.205)
    left = int(w * 0.075)
    top = int(h * 0.155)
    return im.crop((left, top, left + side, top + side))


def _resize(im: Image.Image, size: int) -> Image.Image:
    return im.resize((size, size), Image.Resampling.LANCZOS)


def _write_png(im: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="PNG", optimize=True)


def main() -> int:
    square = _crop_icon_square(_load_source())

    BRANDING_DIR.mkdir(parents=True, exist_ok=True)
    source_copy = BRANDING_DIR / "ips_app_icon_source.jpg"
    square.convert("RGB").save(source_copy, format="JPEG", quality=95)
    _write_png(_resize(square, 512), BRANDING_DIR / "ips_app_icon.png")

    APP_STATIC_DIR.mkdir(parents=True, exist_ok=True)
    STREAMLIT_STATIC_DIR.mkdir(parents=True, exist_ok=True)
    DESKTOP_STATIC_DIR.mkdir(parents=True, exist_ok=True)

    for size in _PWA_SIZES:
        _write_png(_resize(square, size), APP_STATIC_DIR / f"icon-{size}.png")

    favicon_png = _resize(square, 32)
    _write_png(favicon_png, APP_STATIC_DIR / "favicon.png")
    _write_png(_resize(square, 180), APP_STATIC_DIR / "apple-touch-icon.png")

    _write_png(favicon_png, STREAMLIT_STATIC_DIR / "favicon.png")
    _write_png(_resize(square, 192), STREAMLIT_STATIC_DIR / "icon-192.png")
    _write_png(_resize(square, 512), STREAMLIT_STATIC_DIR / "icon-512.png")

    ico_images = [_resize(square, size) for size in _ICO_SIZES]
    ico_images[0].save(
        APP_STATIC_DIR / "favicon.ico",
        format="ICO",
        sizes=[(s, s) for s in _ICO_SIZES],
        append_images=ico_images[1:],
    )
    ico_images[0].save(
        DESKTOP_STATIC_DIR / "ips_app.ico",
        format="ICO",
        sizes=[(s, s) for s in _ICO_SIZES],
        append_images=ico_images[1:],
    )

    print(f"Source: {app_icon_source_path()}")
    print(f"Wrote branding copy: {source_copy}")
    print(f"Wrote PWA + favicon assets under {APP_STATIC_DIR}")
    print(f"Wrote Streamlit static icons under {STREAMLIT_STATIC_DIR}")
    print(f"Wrote desktop ICO: {DESKTOP_STATIC_DIR / 'ips_app.ico'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
