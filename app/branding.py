from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path

import streamlit as st

_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def _find_wide_logo() -> Path | None:
    search_paths = [
        _ASSETS_DIR / "ips_logo_wide.png",
        _ASSETS_DIR / "IPS LOGO WIDE.png",
    ]
    for path in search_paths:
        if path.exists():
            return path
    return None


def get_header_logo_path() -> Path | None:
    """Compact logo for page header bars (square / icon variants)."""
    for name in (
        "ips_logo_header.png",
        "IPS Icon.png",
        "company_logo.png",
        "ips_logo_round.png",
    ):
        path = _ASSETS_DIR / name
        if path.is_file():
            return path
    return None


@lru_cache(maxsize=4)
def _logo_data_uri(path_str: str) -> str:
    path = Path(path_str)
    mime = "image/png"
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif path.suffix.lower() == ".webp":
        mime = "image/webp"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def header_logo_html(*, height: int = 40, alt: str = "IPS") -> str:
    """Inline logo markup for compact page headers."""
    path = get_header_logo_path()
    if not path:
        return ""
    src = _logo_data_uri(str(path))
    return (
        f'<span class="ips-page-header-logo-wrap">'
        f'<img class="ips-page-header-logo" src="{src}" alt="{html.escape(alt)}" '
        f'height="{int(height)}" />'
        f"</span>"
    )


def apply_branding() -> None:
    st.markdown(
        """
        <style>
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
            color: #111827;
            font-size: 1.45rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin: 0 0 0.12rem 0;
            line-height: 1.15;
        }

        .ips-page-subtitle {
            color: #1f2937;
            font-size: 0.875rem;
            font-weight: 600;
            margin-bottom: 0.28rem;
            line-height: 1.35;
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