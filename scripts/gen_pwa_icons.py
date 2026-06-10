from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _load_font(px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_paths = [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, px)
            except Exception:
                pass
    return ImageFont.load_default()


def _make_icon(sz: int, *, maskable: bool = False) -> Image.Image:
    # IPS dark theme + accent
    bg = (11, 18, 32, 255)  # #0b1220
    fg = (248, 250, 252, 255)  # #f8fafc
    acc = (37, 99, 235, 200)  # #2563eb

    im = Image.new("RGBA", (sz, sz), bg)
    draw = ImageDraw.Draw(im)

    pad = int(sz * (0.18 if maskable else 0.08))
    ring_w = max(2, sz // 28)
    draw.ellipse([pad, pad, sz - pad - 1, sz - pad - 1], outline=acc, width=ring_w)

    text = "IPS"
    font = _load_font(int(sz * (0.28 if maskable else 0.32)))
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (sz - tw) // 2
    ty = (sz - th) // 2 - int(sz * 0.02)
    draw.text((tx, ty), text, font=font, fill=fg)

    bar_h = max(2, sz // 40)
    bar_w = int(sz * (0.36 if maskable else 0.42))
    bx = (sz - bar_w) // 2
    by = ty + th + int(sz * 0.06)
    draw.rounded_rectangle([bx, by, bx + bar_w, by + bar_h], radius=bar_h, fill=acc)

    return im


def main() -> None:
    """Deprecated: regenerate from the IPS branding source instead."""
    root = Path(__file__).resolve().parents[1]
    generate = root / "scripts" / "generate_app_icons.py"
    if generate.is_file():
        import runpy

        runpy.run_path(str(generate), run_name="__main__")
        return
    print("Run scripts/generate_app_icons.py to build icons from assets/branding/ips_app_icon_source.jpg")


if __name__ == "__main__":
    main()

