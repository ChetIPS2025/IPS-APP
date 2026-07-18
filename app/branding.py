from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path

import streamlit as st

from app.ui.css_inject import inject_css_once

_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
IPS_BRANDING_STYLE_ID = "ips-branding-styles-v1"


def _find_wide_logo() -> Path | None:
    search_paths = [
        _ASSETS_DIR / "ips_logo_wide.png",
        _ASSETS_DIR / "IPS LOGO WIDE.png",
    ]
    for path in search_paths:
        if path.exists():
            return path
    return None


def get_sidebar_round_logo_path() -> Path | None:
    """Circular IPS logo for navigation sidebar branding."""
    for name in (
        "ips_logo_round.png",
        "IPS LOGO ROUND.png",
        "IPS Icon.png",
    ):
        path = _ASSETS_DIR / name
        if path.is_file():
            return path
    return None


def get_header_logo_path() -> Path | None:
    """Compact logo for page header bars (square / icon variants)."""
    branding_icon = _ASSETS_DIR / "branding" / "ips_app_icon.png"
    if branding_icon.is_file():
        return branding_icon
    for name in (
        "ips_logo_header.png",
        "IPS Icon.png",
        "ips_logo_round.png",
    ):
        path = _ASSETS_DIR / name
        if path.is_file():
            return path
    return None


def get_wording_logo_path() -> Path | None:
    """Horizontal Industrial Plant Solutions wording logo for the main content header bar."""
    for name in (
        "ips_wording_logo.png",
        "IPS Wording Logo.png",
        "ips_logo_wide.png",
        "IPS LOGO WIDE.png",
    ):
        path = _ASSETS_DIR / name
        if path.is_file():
            return path
    pdf = _ASSETS_DIR / "IPS Wording Logo.pdf"
    if pdf.is_file():
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf)
            page = doc.load_page(0)
            pix = page.get_pixmap(alpha=True, dpi=200)
            out = _ASSETS_DIR / "ips_wording_logo.png"
            pix.save(str(out))
            doc.close()
            if out.is_file():
                return out
        except Exception:
            pass
    return _find_wide_logo()


@lru_cache(maxsize=8)
def _logo_data_uri(path_str: str, mtime_ns: int) -> str:
    path = Path(path_str)
    mime = "image/png"
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif path.suffix.lower() == ".webp":
        mime = "image/webp"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _logo_src(path: Path) -> str:
    return _logo_data_uri(str(path), path.stat().st_mtime_ns)


def wording_logo_html(
    *,
    height: int = 46,
    alt: str = "Industrial Plant Solutions",
    css_class: str = "ips-main-header-logo",
) -> str:
    """Inline wording logo for the light-gray main content header bar."""
    path = get_wording_logo_path()
    if not path:
        return (
            f'<span class="ips-main-header-logo-fallback">{html.escape(alt)}</span>'
        )
    src = _logo_src(path)
    return (
        f'<img class="{html.escape(css_class, quote=True)}" src="{src}" alt="{html.escape(alt)}" '
        f'height="{int(height)}" style="height:{int(height)}px;" />'
    )


def sidebar_round_logo_html(
    *,
    size_px: int,
    css_class: str = "sidebar-logo-icon",
    alt: str = "IPS",
) -> str:
    """Inline round IPS logo for sidebar navigation."""
    path = get_sidebar_round_logo_path()
    if not path:
        return (
            f'<span class="{html.escape(css_class, quote=True)} '
            f'{html.escape(css_class, quote=True)}-fallback">{html.escape(alt)}</span>'
        )
    src = _logo_src(path)
    px = int(size_px)
    classes = f"sidebar-logo navigation-logo app-logo {css_class}".strip()
    return (
        f'<img class="{html.escape(classes, quote=True)}" src="{src}" '
        f'alt="{html.escape(alt)}" width="{px}" height="{px}" '
        f'style="width:{px}px;height:{px}px;object-fit:contain;background:transparent;border:none;box-shadow:none;" />'
    )


def header_logo_html(*, height: int = 40, alt: str = "IPS") -> str:
    """Inline logo markup for compact page headers."""
    path = get_header_logo_path()
    if not path:
        return ""
    src = _logo_src(path)
    return (
        f'<span class="ips-page-header-logo-wrap">'
        f'<img class="ips-page-header-logo" src="{src}" alt="{html.escape(alt)}" '
        f'height="{int(height)}" />'
        f"</span>"
    )


def apply_branding() -> None:
    if not inject_css_once(IPS_BRANDING_STYLE_ID):
        return
    st.markdown(
        """
        <style id="ips-branding-styles-v1">
        /* App/sidebar background: theme.apply_global_app_styles() */

        .ips-topbar {
            padding: 8px 0 14px 0;
            margin-bottom: 6px;
        }

        .ips-topbar img {
            width: 100%;
            max-width: 1600px;
            height: auto;
            display: block;
        }

        section[data-testid="stMain"] [data-testid="stImage"] {
            margin: 0 0 0.1rem 0 !important;
        }
        section[data-testid="stMain"] [data-testid="stImage"] img {
            margin: 0 !important;
        }

        .ips-page-title {
            /* Title sizing lives in app/styles.py inject_global_css */
        }

        .ips-page-subtitle {
            /* Subtitle sizing lives in app/styles.py inject_global_css */
        }

        .ips-page-help {
            color: #1f2937;
            font-size: 0.875rem;
            font-weight: 500;
            line-height: 1.4;
            margin: 0 0 0.35rem 0;
            max-width: 920px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(
    title: str = "",
    subtitle: str = "Industrial Plant Solutions, LLC",
    *,
    help_text: str | None = None,
    logo_width: int = 180,
) -> None:
    logo_path = _find_wide_logo()

    if logo_path and logo_path.exists():
        st.image(str(logo_path), width=int(logo_width))

    if title:
        st.markdown(f'<div class="ips-page-title">{html.escape(title)}</div>', unsafe_allow_html=True)

    if subtitle:
        st.markdown(f'<div class="ips-page-subtitle">{html.escape(subtitle)}</div>', unsafe_allow_html=True)

    if help_text:
        st.markdown(f'<p class="ips-page-help">{html.escape(help_text)}</p>', unsafe_allow_html=True)