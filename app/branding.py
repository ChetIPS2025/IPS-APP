from __future__ import annotations

from pathlib import Path
import base64
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
        .stApp {
            background: linear-gradient(90deg, #020817 0%, #04132f 70%, #031338 100%);
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #111827 0%, #1f2937 100%);
        }

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

        .ips-page-title {
            color: #f8fafc;
            font-size: 1.45rem;
            font-weight: 750;
            letter-spacing: -0.02em;
            margin: 4px 0 2px 0;
            line-height: 1.2;
        }

        .ips-page-subtitle {
            color: #94a3b8;
            font-size: 0.8125rem;
            margin-bottom: 0.65rem;
            line-height: 1.45;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(title: str = "", subtitle: str = "Industrial Plant Solutions, LLC") -> None:
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
        st.markdown(f'<div class="ips-page-title">{title}</div>', unsafe_allow_html=True)

    if subtitle:
        st.markdown(f'<div class="ips-page-subtitle">{subtitle}</div>', unsafe_allow_html=True)