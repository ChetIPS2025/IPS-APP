"""
IPS application shell: one cohesive visual system for Streamlit main content.

- Typography rhythm, spacing, tabs, inputs, and primary/secondary/destructive buttons
- Intended to be injected once per session from ``main`` after :func:`branding.apply_branding`

Does not replace page-specific markers (``ips-crud-toolbar-root``, ``ips-list-top-anchor``, etc.);
those layers stack on top of this base.
"""

from __future__ import annotations

import streamlit as st

IPS_APP_SHELL_CSS_KEY = "ips_app_shell_styles_injected"


def inject_ips_app_shell_styles() -> None:
    """Inject global IPS chrome for main app content (safe to call multiple times)."""
    if st.session_state.get(IPS_APP_SHELL_CSS_KEY):
        return
    st.session_state[IPS_APP_SHELL_CSS_KEY] = True
    st.markdown(
        """
        <style>
        :root {
            --ips-space-xs: 0.25rem;
            --ips-space-sm: 0.45rem;
            --ips-space-md: 0.65rem;
            --ips-space-lg: 0.9rem;
            --ips-radius: 8px;
            --ips-radius-lg: 10px;
            --ips-border: rgba(71, 85, 105, 0.45);
            --ips-text-muted: #94a3b8;
            --ips-surface: rgba(15, 23, 42, 0.35);
        }

        /* ----- Main block: consistent horizontal padding & max readable width ----- */
        section[data-testid="stMain"] > div {
            max-width: 1680px;
            margin-left: auto;
            margin-right: auto;
        }
        section[data-testid="stMain"] .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 2rem !important;
        }

        /* ----- Typography hierarchy (Streamlit markdown + headers) ----- */
        section[data-testid="stMain"] h1 {
            color: #f8fafc !important;
            font-size: 1.65rem !important;
            font-weight: 750 !important;
            letter-spacing: -0.02em;
            margin: 0.15rem 0 0.35rem 0 !important;
        }
        section[data-testid="stMain"] h2,
        section[data-testid="stMain"] h3 {
            color: #e2e8f0 !important;
            font-size: 1.12rem !important;
            font-weight: 650 !important;
            margin: 0.65rem 0 0.4rem 0 !important;
        }
        section[data-testid="stMain"] h4,
        section[data-testid="stMain"] h5 {
            color: #cbd5e1 !important;
            font-size: 0.98rem !important;
            font-weight: 600 !important;
            margin: 0.5rem 0 0.3rem 0 !important;
        }
        section[data-testid="stMain"] .stMarkdown p,
        section[data-testid="stMain"] [data-testid="stCaptionContainer"] {
            color: var(--ips-text-muted);
        }

        /* ----- Dividers ----- */
        section[data-testid="stMain"] hr {
            margin: 0.65rem 0 !important;
            border: none !important;
            border-top: 1px solid var(--ips-border) !important;
        }

        /* ----- Tabs (Materials / Labor / Estimate editor tabs) ----- */
        section[data-testid="stMain"] [data-testid="stTabs"] [role="tablist"] {
            gap: 0.25rem !important;
            border-bottom: 1px solid rgba(51, 65, 85, 0.65) !important;
            padding-bottom: 2px !important;
        }
        section[data-testid="stMain"] [data-testid="stTabs"] [role="tab"] {
            border-radius: var(--ips-radius) var(--ips-radius) 0 0 !important;
            padding: 0.4rem 0.75rem !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
            min-height: 2.35rem !important;
            color: #94a3b8 !important;
        }
        section[data-testid="stMain"] [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            color: #f1f5f9 !important;
            font-weight: 600 !important;
            background: rgba(30, 41, 59, 0.65) !important;
            border: 1px solid rgba(100, 116, 139, 0.45) !important;
            border-bottom-color: transparent !important;
        }

        /* ----- Expanders ----- */
        section[data-testid="stMain"] [data-testid="stExpander"] details {
            border: 1px solid rgba(71, 85, 105, 0.4) !important;
            border-radius: var(--ips-radius-lg) !important;
            background: var(--ips-surface) !important;
        }
        section[data-testid="stMain"] [data-testid="stExpander"] summary {
            font-weight: 600 !important;
            font-size: 0.9rem !important;
        }

        /* ----- Main-area buttons (not sidebar): size + role ----- */
        section[data-testid="stMain"] .stButton > button {
            border-radius: var(--ips-radius) !important;
            min-height: 2.35rem !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
        }
        section[data-testid="stMain"] .stButton > button[kind="primary"],
        section[data-testid="stMain"] .stButton > button[data-testid="baseButton-primary"] {
            font-weight: 600 !important;
            box-shadow: 0 1px 6px rgba(37, 99, 235, 0.25) !important;
        }
        section[data-testid="stMain"] .stButton > button[kind="secondary"] {
            color: #cbd5e1 !important;
            border-color: rgba(100, 116, 139, 0.45) !important;
            background: rgba(30, 41, 59, 0.55) !important;
        }

        /* ----- Data tables / editors: calmer chrome ----- */
        section[data-testid="stMain"] [data-testid="stDataFrame"],
        section[data-testid="stMain"] [data-testid="stDataEditor"] {
            border-radius: var(--ips-radius-lg) !important;
            border: 1px solid rgba(51, 65, 85, 0.55) !important;
            overflow: hidden;
        }

        /* ----- Inputs (main only) ----- */
        section[data-testid="stMain"] [data-testid="stTextInput"] input,
        section[data-testid="stMain"] [data-testid="stTextArea"] textarea,
        section[data-testid="stMain"] [data-testid="stNumberInput"] input {
            border-radius: var(--ips-radius) !important;
        }
        section[data-testid="stMain"] [data-testid="stWidgetLabel"] label {
            font-size: 0.8125rem !important;
            color: #cbd5e1 !important;
        }

        /* ----- Sidebar: slightly tighter on all sizes ----- */
        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.5rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
