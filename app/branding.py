from __future__ import annotations

import html
from pathlib import Path

import streamlit as st


def _find_wide_logo() -> Path | None:
    search_paths = [
        Path(__file__).resolve().parents[1] / "assets" / "ips_logo_wide.png",
        Path(__file__).resolve().parents[1] / "assets" / "IPS LOGO WIDE.png",
    ]
    for path in search_paths:
        if path.exists():
            return path
    return None


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