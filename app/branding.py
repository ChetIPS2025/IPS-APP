from __future__ import annotations

import base64
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
        body {
            background-color: #0F2A4A;
        }

        .stApp {
            background: linear-gradient(180deg, #0F2A4A 0%, #0C2345 100%);
            color: #ffffff;
        }

        section[data-testid="stSidebar"] {
            background: #102A4A;
        }

        .ips-topbar {
            display: none;
        }

        .ips-page-title {
            color: #f8fafc;
            font-size: 1.45rem;
            font-weight: 750;
            letter-spacing: -0.02em;
            margin: 2px 0 2px 0;
            line-height: 1.2;
        }

        .ips-page-subtitle {
            color: #C0CAD8;
            font-size: 0.8125rem;
            margin-bottom: 0.45rem;
            line-height: 1.45;
        }

        .ips-page-help {
            color: #C0CAD8;
            font-size: 0.8125rem;
            line-height: 1.45;
            margin: 0 0 0.55rem 0;
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
) -> None:
    logo_path = _find_wide_logo()

    if logo_path and logo_path.exists():
        ext = logo_path.suffix.lower().replace(".", "") or "png"
        encoded = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
        st.markdown(
            f"""
            <div class="ips-topbar">
                <img src="data:image/{ext};base64,{encoded}" alt="IPS Logo" />
            </div>
            """,
            unsafe_allow_html=True,
        )

    if title:
        st.markdown(f'<div class="ips-page-title">{html.escape(title)}</div>', unsafe_allow_html=True)

    if subtitle:
        st.markdown(f'<div class="ips-page-subtitle">{html.escape(subtitle)}</div>', unsafe_allow_html=True)

    if help_text:
        st.markdown(f'<p class="ips-page-help">{html.escape(help_text)}</p>', unsafe_allow_html=True)