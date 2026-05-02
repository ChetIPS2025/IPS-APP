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
            /* IPS field palette: clean light surfaces for tablet readability */
            --ips-bg-main: #f5f7fa;
            --ips-bg-secondary: #ffffff; /* card / section */
            --ips-bg-card: #ffffff;      /* alternate sections */
            --ips-bg-sidebar: #ffffff;
            --ips-bg-hover: #f1f5f9;

            --ips-text: #0f172a;
            --ips-text-secondary: #475569;
            --ips-text-muted: #64748b;

            --ips-border: #e2e8f0;
            --ips-border-strong: #cbd5e1;
            --ips-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
            --ips-surface: #ffffff;
            /* Button system (main content) — dense pages override with more specific rules */
            --ips-btn-height: 2.75rem;
            --ips-btn-pad-y: 0.625rem;
            --ips-btn-pad-x: 1rem;
            --ips-btn-fs: 0.875rem;
            --ips-btn-fw: 500;
            --ips-btn-fw-strong: 600;
            --ips-btn-radius: 8px;
            /* Form controls (main) — dense pages override with more specific selectors */
            --ips-ctrl-fs: 0.875rem;
            --ips-ctrl-lh: 1.32;
            --ips-ctrl-radius: 8px;
            --ips-ctrl-pad-y: 0.5rem;
            --ips-ctrl-pad-x: 0.75rem;
            --ips-ctrl-h: 2.65rem;
            --ips-ctrl-border: #e2e8f0;
            --ips-ctrl-bg: #ffffff;
            --ips-ctrl-fg: var(--ips-text);
            --ips-ctrl-ph: #94a3b8;
            --ips-label-fs: 0.76rem;
            --ips-label-color: var(--ips-text-muted);
            --ips-widget-gap: 0.28rem;
        }

        /* ----- App background + default text ----- */
        section[data-testid="stMain"] {
            background: var(--ips-bg-main) !important;
            color: var(--ips-text) !important;
        }
        section[data-testid="stMain"] .stMarkdown,
        section[data-testid="stMain"] .stMarkdown p {
            color: var(--ips-text-secondary) !important;
        }

        /* ----- Main block: consistent horizontal padding & max readable width ----- */
        section[data-testid="stMain"] > div {
            max-width: 1680px;
            margin-left: auto;
            margin-right: auto;
        }
        section[data-testid="stMain"] .block-container {
            padding-top: 0.4rem !important;
            padding-bottom: 1rem !important;
        }

        /* ----- Typography hierarchy (Streamlit markdown + headers) ----- */
        section[data-testid="stMain"] h1 {
            color: var(--ips-text) !important;
            font-size: 1.55rem !important;
            font-weight: 750 !important;
            letter-spacing: -0.02em;
            margin: 0.1rem 0 0.28rem 0 !important;
        }
        section[data-testid="stMain"] h2,
        section[data-testid="stMain"] h3 {
            color: var(--ips-text) !important;
            font-size: 1.05rem !important;
            font-weight: 650 !important;
            margin: 0.45rem 0 0.28rem 0 !important;
        }
        section[data-testid="stMain"] h4,
        section[data-testid="stMain"] h5 {
            color: var(--ips-text-secondary) !important;
            font-size: 0.92rem !important;
            font-weight: 600 !important;
            margin: 0.4rem 0 0.22rem 0 !important;
        }
        section[data-testid="stMain"] .stMarkdown p,
        section[data-testid="stMain"] [data-testid="stCaptionContainer"] {
            color: var(--ips-text-muted);
        }

        /* ----- Dividers ----- */
        section[data-testid="stMain"] hr {
            margin: 0.5rem 0 !important;
            border: none !important;
            border-top: 1px solid var(--ips-border) !important;
        }

        /* ----- Tabs (Materials / Labor / Estimate editor tabs) ----- */
        section[data-testid="stMain"] [data-testid="stTabs"] [role="tablist"] {
            gap: 0.25rem !important;
            border-bottom: 1px solid var(--ips-border) !important;
            padding-bottom: 2px !important;
        }
        section[data-testid="stMain"] [data-testid="stTabs"] [role="tab"] {
            border-radius: var(--ips-radius) var(--ips-radius) 0 0 !important;
            padding: 0.4rem 0.75rem !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
            min-height: 2.2rem !important;
            color: var(--ips-text-secondary) !important;
        }
        section[data-testid="stMain"] [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            color: var(--ips-text) !important;
            font-weight: 600 !important;
            background: #ffffff !important;
            border: 1px solid var(--ips-border) !important;
            border-bottom-color: transparent !important;
        }

        /* ----- Expanders ----- */
        section[data-testid="stMain"] [data-testid="stExpander"] details {
            border: 1px solid var(--ips-border) !important;
            border-radius: var(--ips-radius-lg) !important;
            background: var(--ips-bg-card) !important;
            box-shadow: var(--ips-shadow) !important;
        }
        section[data-testid="stMain"] [data-testid="stExpander"] summary {
            font-weight: 600 !important;
            font-size: 0.9rem !important;
        }

        /* ----- Cards / containers (Streamlit "border=True") ----- */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px !important;
            border: 1px solid var(--ips-border) !important;
            background: var(--ips-bg-secondary) !important;
            box-shadow: var(--ips-shadow) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 10px 12px !important;
        }

        /* ----- IPS button system (main): primary / secondary / tertiary + downloads + link buttons ----- */
        section[data-testid="stMain"] .stButton > button,
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button {
            border-radius: var(--ips-btn-radius) !important;
            min-height: var(--ips-btn-height) !important;
            min-width: 100px !important;
            width: auto !important;
            height: auto !important;
            font-size: var(--ips-btn-fs) !important;
            font-weight: var(--ips-btn-fw) !important;
            padding: 10px 16px !important;
            line-height: 1.25 !important;
            box-sizing: border-box !important;
            white-space: nowrap !important;
        }
        section[data-testid="stMain"] .stButton > button p,
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button p {
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
            margin: 0 !important;
            line-height: 1.25 !important;
        }
        section[data-testid="stMain"] .stButton > button[kind="primary"],
        section[data-testid="stMain"] .stButton > button[data-testid="baseButton-primary"],
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button[kind="primary"],
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button[data-testid="baseButton-primary"],
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="primary"],
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[data-testid="baseButton-primary"] {
            font-weight: var(--ips-btn-fw-strong) !important;
            color: #ffffff !important;
            background: #2563eb !important;
            border: 1px solid #2563eb !important;
            box-shadow: 0 1px 2px rgba(37, 99, 235, 0.18) !important;
        }
        section[data-testid="stMain"] .stButton > button[kind="primary"]:hover,
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button[kind="primary"]:hover {
            background: #1d4ed8 !important;
            border-color: #1d4ed8 !important;
        }
        section[data-testid="stMain"] .stButton > button[kind="secondary"],
        section[data-testid="stMain"] .stButton > button[data-testid="baseButton-secondary"],
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button[kind="secondary"],
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="secondary"] {
            color: var(--ips-text) !important;
            border-color: var(--ips-border) !important;
            background: #f1f5f9 !important;
            font-weight: var(--ips-btn-fw) !important;
        }
        section[data-testid="stMain"] .stButton > button[kind="secondary"]:hover,
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="secondary"]:hover {
            background: #e2e8f0 !important;
            border-color: #cbd5e1 !important;
            color: var(--ips-text) !important;
        }
        section[data-testid="stMain"] .stLinkButton > a {
            border-radius: var(--ips-btn-radius) !important;
            min-height: var(--ips-btn-height) !important;
            font-size: var(--ips-btn-fs) !important;
            font-weight: var(--ips-btn-fw) !important;
            padding: var(--ips-btn-pad-y) var(--ips-btn-pad-x) !important;
            line-height: 1.25 !important;
            box-sizing: border-box !important;
            white-space: nowrap !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button {
            border-radius: var(--ips-btn-radius) !important;
            min-height: var(--ips-btn-height) !important;
            min-width: 100px !important;
            width: auto !important;
            height: auto !important;
            font-size: var(--ips-btn-fs) !important;
            font-weight: var(--ips-btn-fw) !important;
            padding: 10px 16px !important;
            line-height: 1.25 !important;
            box-sizing: border-box !important;
            white-space: nowrap !important;
        }
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button p {
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
            margin: 0 !important;
            line-height: 1.25 !important;
        }

        /* ----- Data tables / editors: calmer chrome ----- */
        section[data-testid="stMain"] [data-testid="stDataFrame"],
        section[data-testid="stMain"] [data-testid="stDataEditor"] {
            border-radius: var(--ips-radius-lg) !important;
            border: 1px solid var(--ips-border) !important;
            overflow: hidden;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"],
        section[data-testid="stMain"] [data-testid="stTable"],
        section[data-testid="stMain"] [data-testid="stDataEditor"] {
            background: #122F52 !important;
            color: var(--ips-text-secondary) !important;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] {
            background: transparent !important;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] tbody tr:hover {
            background: var(--ips-bg-hover) !important;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] th,
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] td {
            border-color: rgba(120, 150, 200, 0.25) !important;
            padding-top: 10px !important;
            padding-bottom: 10px !important;
        }

        /* ----- IPS form controls (main + sidebar): labels + fields ----- */
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stWidgetLabel"] label,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stWidgetLabel"] span {
            font-size: var(--ips-label-fs) !important;
            color: var(--ips-label-color) !important;
            font-weight: 500 !important;
            line-height: 1.25 !important;
            margin-bottom: 0.1rem !important;
            letter-spacing: 0.01em;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stElementContainer"] {
            margin-bottom: var(--ips-widget-gap) !important;
        }

        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stTextInput"] input {
            border-radius: var(--ips-ctrl-radius) !important;
            min-height: var(--ips-ctrl-h) !important;
            height: auto !important;
            padding: var(--ips-ctrl-pad-y) var(--ips-ctrl-pad-x) !important;
            font-size: var(--ips-ctrl-fs) !important;
            line-height: var(--ips-ctrl-lh) !important;
            background: var(--ips-ctrl-bg) !important;
            border: 1px solid var(--ips-ctrl-border) !important;
            color: var(--ips-ctrl-fg) !important;
            box-sizing: border-box !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stTextInput"] input::placeholder,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stNumberInput"] input::placeholder,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stTextArea"] textarea::placeholder {
            color: var(--ips-ctrl-ph) !important;
        }

        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stTextArea"] textarea {
            border-radius: var(--ips-ctrl-radius) !important;
            min-height: 3rem !important;
            padding: 0.32rem 0.5rem !important;
            font-size: var(--ips-ctrl-fs) !important;
            line-height: var(--ips-ctrl-lh) !important;
            background: var(--ips-ctrl-bg) !important;
            border: 1px solid var(--ips-ctrl-border) !important;
            color: var(--ips-ctrl-fg) !important;
            box-sizing: border-box !important;
        }

        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stNumberInput"] input {
            border-radius: var(--ips-ctrl-radius) !important;
            min-height: var(--ips-ctrl-h) !important;
            font-size: var(--ips-ctrl-fs) !important;
            padding: var(--ips-ctrl-pad-y) var(--ips-ctrl-pad-x) !important;
            background: var(--ips-ctrl-bg) !important;
            border: 1px solid var(--ips-ctrl-border) !important;
            color: var(--ips-ctrl-fg) !important;
            box-sizing: border-box !important;
        }

        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stSelectbox"] [data-baseweb="select"] > div {
            min-height: var(--ips-ctrl-h) !important;
            font-size: var(--ips-ctrl-fs) !important;
            line-height: var(--ips-ctrl-lh) !important;
            border-radius: var(--ips-ctrl-radius) !important;
            background: var(--ips-ctrl-bg) !important;
            border-color: var(--ips-ctrl-border) !important;
            color: var(--ips-ctrl-fg) !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
            min-height: var(--ips-ctrl-h) !important;
            font-size: var(--ips-ctrl-fs) !important;
            border-radius: var(--ips-ctrl-radius) !important;
            background: var(--ips-ctrl-bg) !important;
            border-color: var(--ips-ctrl-border) !important;
        }

        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stDateInput"] input,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stDateInput"] [data-baseweb="input"] {
            min-height: var(--ips-ctrl-h) !important;
            font-size: var(--ips-ctrl-fs) !important;
            border-radius: var(--ips-ctrl-radius) !important;
            background: var(--ips-ctrl-bg) !important;
            border: 1px solid var(--ips-ctrl-border) !important;
            color: var(--ips-ctrl-fg) !important;
            padding: var(--ips-ctrl-pad-y) var(--ips-ctrl-pad-x) !important;
            box-sizing: border-box !important;
        }

        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stCheckbox"] label,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stCheckbox"] span {
            font-size: var(--ips-ctrl-fs) !important;
            color: #cbd5e1 !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stRadio"] label,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stRadio"] span {
            font-size: var(--ips-ctrl-fs) !important;
            color: #cbd5e1 !important;
        }

        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stFileUploader"] {
            border-radius: var(--ips-ctrl-radius) !important;
            border: 1px dashed rgba(100, 116, 139, 0.5) !important;
            background: rgba(15, 23, 42, 0.35) !important;
            padding: 0.28rem 0.4rem !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stFileUploader"] section {
            padding: 0 !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stFileUploader"] small,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stFileUploader"] [data-testid="stCaptionContainer"] {
            font-size: 0.75rem !important;
        }

        /* ----- Sidebar: slightly tighter on all sizes ----- */
        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.5rem !important;
        }

        section[data-testid="stMain"] .stMetric {
            background: #ffffff;
            border: 1px solid var(--ips-border);
            border-radius: var(--ips-radius-lg);
            padding: 0.55rem 0.65rem !important;
            box-shadow: var(--ips-shadow);
        }
        section[data-testid="stMain"] [data-testid="stMetricLabel"] {
            font-size: 0.72rem !important;
        }
        section[data-testid="stMain"] [data-testid="stMetricValue"] {
            font-size: 1.05rem !important;
        }

        /* ----- Dashboard / summary strips ----- */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-dash-metrics) {
            padding: 6px 8px 8px 8px !important;
            margin-bottom: 8px !important;
            background: #ffffff !important;
            border-color: var(--ips-border) !important;
        }

        /* ----- Estimate editor: totals strip + document-style proposal surface ----- */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-estimate-metrics-strip) {
            padding: 6px 8px 8px 8px !important;
            margin-bottom: 0.45rem !important;
            background: #ffffff !important;
            border-color: var(--ips-border) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-proposal-doc-surface) {
            background: #ffffff !important;
            border-color: #e2e8f0 !important;
            padding: 10px 12px 12px 12px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-proposal-doc-surface) .stMarkdown p,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-proposal-doc-surface) [data-testid="stCaptionContainer"] {
            color: #475569 !important;
        }

        /* Destructive / danger (Streamlit tertiary) */
        section[data-testid="stMain"] .stButton > button[kind="tertiary"],
        section[data-testid="stMain"] .stButton > button[data-testid="baseButton-tertiary"],
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="tertiary"],
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[data-testid="baseButton-tertiary"],
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button[kind="tertiary"],
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button[data-testid="baseButton-tertiary"] {
            color: #991b1b !important;
            border-color: #fecaca !important;
            background: #fee2e2 !important;
            font-weight: var(--ips-btn-fw) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
