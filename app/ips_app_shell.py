"""
IPS application shell: one cohesive visual system for Streamlit main content.

- White canvas (#FFFFFF), white sidebar/cards, high-contrast text, 48px touch buttons
- Intended to be injected once per session from ``main`` after :func:`branding.apply_branding`

Does not replace page-specific markers (``ips-crud-toolbar-root``, ``ips-list-top-anchor``, etc.);
those layers stack on top of this base.
"""

from __future__ import annotations

import streamlit as st

IPS_APP_SHELL_CSS_KEY = "ips_app_shell_styles_injected_v13"


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
            --ips-bg-main: #FFFFFF;
            --ips-bg-secondary: #ffffff;
            --ips-bg-card: #ffffff;
            --ips-bg-sidebar: #ffffff;
            --ips-bg-hover: #F8FAFC;

            --ips-text: #0F172A;
            --ips-text-secondary: #334155;
            --ips-text-muted: #64748B;

            --ips-border: #E5EAF2;
            --ips-border-strong: #CBD5E1;
            --ips-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
            --ips-radius: 8px;
            --ips-radius-lg: 10px;
            --ips-surface: #ffffff;
            /* Buttons: 48px touch target, semibold */
            --ips-btn-height: 3rem;
            --ips-btn-pad-y: 0.625rem;
            --ips-btn-pad-x: 1rem;
            --ips-btn-fs: 0.875rem;
            --ips-btn-fw: 600;
            --ips-btn-fw-strong: 600;
            --ips-btn-radius: 10px;
            /* Form controls */
            --ips-ctrl-fs: 0.875rem;
            --ips-ctrl-lh: 1.32;
            --ips-ctrl-radius: 10px;
            --ips-ctrl-pad-y: 0.28rem;
            --ips-ctrl-pad-x: 0.55rem;
            --ips-ctrl-h: 2.125rem;
            --ips-ctrl-border: #9ca3af;
            --ips-ctrl-bg: #ffffff;
            --ips-ctrl-fg: var(--ips-text);
            --ips-ctrl-ph: #4b5563;
            --ips-label-fs: 0.875rem;
            --ips-label-color: #111827;
            --ips-widget-gap: 0.12rem;
        }

        /* App canvas: theme.apply_global_app_styles() */
        section[data-testid="stMain"] {
            color: var(--ips-text) !important;
            font-weight: 500 !important;
        }
        section[data-testid="stMain"],
        section[data-testid="stMain"] .block-container {
            overflow-x: hidden !important;
        }
        section[data-testid="stMain"] .stMarkdown,
        section[data-testid="stMain"] .stMarkdown p,
        section[data-testid="stMain"] .stMarkdown li {
            color: var(--ips-text-secondary) !important;
            font-weight: 500 !important;
        }
        section[data-testid="stMain"] .stMarkdown strong,
        section[data-testid="stMain"] .stMarkdown b {
            color: var(--ips-text) !important;
            font-weight: 700 !important;
        }

        /* ----- Main block: consistent horizontal padding & max readable width ----- */
        section[data-testid="stMain"] > div {
            max-width: 1680px;
            margin-left: auto;
            margin-right: auto;
        }
        section[data-testid="stMain"] .block-container {
            padding-bottom: 0.75rem !important;
        }
        section[data-testid="stMain"] [data-testid="stVerticalBlock"] > div {
            gap: 0.35rem !important;
        }
        /* Collapse zero-height shell iframes (Streamlit 1.56 stIFrame / legacy components). */
        body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has([data-testid="stIFrame"]),
        body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(iframe.stIFrame),
        body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has([data-testid="stCustomComponentV1"]),
        body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(iframe[title="streamlit_components_v1.iframe"]),
        body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has([data-testid="stIFrame"][height="0"]),
        body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(iframe.stIFrame[height="0"]),
        body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has([data-testid="stCustomComponentV1"][height="0"]) {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
        }

        /* Dashboard: tighter vertical rhythm between cards */
        section[data-testid="stMain"]:has(.ips-dashboard-page) [data-testid="stVerticalBlockBorderWrapper"] {
            margin-bottom: 0.35rem !important;
        }
        section[data-testid="stMain"]:has(.ips-dashboard-page) [data-testid="stElementContainer"] {
            margin-bottom: 0.18rem !important;
        }
        section[data-testid="stMain"]:has(.ips-dashboard-page) h5 {
            margin: 0.2rem 0 0.15rem 0 !important;
        }

        /* ----- Typography hierarchy (Streamlit markdown + headers) ----- */
        section[data-testid="stMain"] h1 {
            color: var(--ips-text) !important;
            font-size: 1.55rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
            margin: 0 0 0.2rem 0 !important;
        }
        section[data-testid="stMain"] h2,
        section[data-testid="stMain"] h3 {
            color: var(--ips-text) !important;
            font-size: 1.05rem !important;
            font-weight: 700 !important;
            margin: 0.3rem 0 0.2rem 0 !important;
        }
        section[data-testid="stMain"] h4,
        section[data-testid="stMain"] h5 {
            color: var(--ips-text-secondary) !important;
            font-size: 0.92rem !important;
            font-weight: 600 !important;
            margin: 0.4rem 0 0.22rem 0 !important;
        }
        section[data-testid="stMain"] [data-testid="stCaptionContainer"],
        section[data-testid="stMain"] [data-testid="stCaptionContainer"] p {
            color: var(--ips-text-secondary) !important;
            font-weight: 500 !important;
        }

        /* ----- Dividers ----- */
        section[data-testid="stMain"] hr {
            margin: 0.35rem 0 !important;
            border: none !important;
            border-top: 1px solid var(--ips-border) !important;
        }

        /* ----- Tabs (light field theme) ----- */
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
            min-height: 2.5rem !important;
            color: var(--ips-text-secondary) !important;
        }
        section[data-testid="stMain"] [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            color: var(--ips-text) !important;
            font-weight: 600 !important;
            background: #ffffff !important;
            border: 1px solid var(--ips-border) !important;
            border-bottom-color: #ffffff !important;
        }

        /* ----- Expanders ----- */
        section[data-testid="stMain"] [data-testid="stExpander"] details {
            border: 1px solid var(--ips-border) !important;
            border-radius: var(--ips-radius) !important;
            background: var(--ips-bg-card) !important;
            box-shadow: none !important;
        }
        section[data-testid="stMain"] [data-testid="stExpander"] summary {
            font-weight: 600 !important;
            font-size: 0.9rem !important;
        }

        /* ----- Cards / containers (Streamlit "border=True") ----- */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: var(--ips-radius) !important;
            border: 1px solid var(--ips-border) !important;
            background: #ffffff !important;
            box-shadow: var(--ips-shadow) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 8px 10px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-flat-section),
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-action-bar-anchor) {
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
            border-radius: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-flat-section) > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-action-bar-anchor) > div {
            padding: 0 0 0.15rem 0 !important;
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
            color: #fff !important;
            background: #2563eb !important;
            border: 1px solid #2563eb !important;
            box-shadow: none !important;
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
            color: #111827 !important;
            border: 1px solid #9ca3af !important;
            background: #ffffff !important;
            font-weight: 600 !important;
        }
        section[data-testid="stMain"] .stButton > button[kind="secondary"]:hover,
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="secondary"]:hover {
            background: #F8FAFC !important;
            border-color: #9ca3af !important;
            color: #111827 !important;
        }
        section[data-testid="stMain"] .stLinkButton > a {
            border-radius: var(--ips-btn-radius) !important;
            min-height: var(--ips-btn-height) !important;
            font-size: var(--ips-btn-fs) !important;
            font-weight: 600 !important;
            padding: var(--ips-btn-pad-y) var(--ips-btn-pad-x) !important;
            line-height: 1.25 !important;
            box-sizing: border-box !important;
            white-space: nowrap !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            color: #111827 !important;
            border: 1px solid var(--ips-ctrl-border) !important;
            background: #ffffff !important;
        }
        section[data-testid="stMain"] .stLinkButton > a[data-testid="stLinkButton-primary"] {
            background: #2563eb !important;
            border-color: #2563eb !important;
            color: #ffffff !important;
            font-weight: 600 !important;
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
            background: #ffffff !important;
            color: var(--ips-text) !important;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] {
            background: transparent !important;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] tbody tr:hover {
            background: var(--ips-bg-hover) !important;
        }
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] th,
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] td {
            border-color: var(--ips-border) !important;
            padding-top: 10px !important;
            padding-bottom: 10px !important;
        }

        /* ----- IPS form controls (main + sidebar): labels + fields ----- */
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stWidgetLabel"] label,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stWidgetLabel"] span {
            font-size: var(--ips-label-fs) !important;
            color: var(--ips-label-color) !important;
            font-weight: 600 !important;
            line-height: 1.25 !important;
            margin-bottom: 0.05rem !important;
            letter-spacing: 0.01em;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stElementContainer"] {
            margin-bottom: var(--ips-widget-gap) !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stHorizontalBlock"] {
            gap: 0.4rem !important;
            align-items: flex-end !important;
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
            min-height: 2.25rem !important;
            padding: 0.28rem 0.5rem !important;
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

        /*
         * BaseWeb select / multiselect: single full-width field — border only on [data-baseweb="select"].
         * Strip nested white “bubbles” from inner div/span/input (Streamlit/BaseWeb defaults).
         */
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stSelectbox"] [data-baseweb="select"],
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stMultiSelect"] [data-baseweb="select"] {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border: 1px solid #9ca3af !important;
            border-radius: 8px !important;
            box-shadow: none !important;
            min-height: var(--ips-ctrl-h) !important;
            max-width: min(350px, 100%) !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            outline: none !important;
            min-height: var(--ips-ctrl-h) !important;
            padding: 0.28rem 0.55rem !important;
            font-size: var(--ips-ctrl-fs) !important;
            line-height: var(--ips-ctrl-lh) !important;
            color: #111827 !important;
            align-items: center !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stSelectbox"] [data-baseweb="select"] > div > div,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stMultiSelect"] [data-baseweb="select"] > div > div {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stSelectbox"] [data-baseweb="select"] span,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stMultiSelect"] [data-baseweb="select"] span {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            color: #111827 !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stSelectbox"] [data-baseweb="select"] input,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stMultiSelect"] [data-baseweb="select"] input {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            outline: none !important;
            color: #111827 !important;
            min-height: auto !important;
            height: auto !important;
            padding: 0 !important;
            margin: 0 !important;
            font-size: var(--ips-ctrl-fs) !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stSelectbox"] [data-baseweb="select"] [role="combobox"],
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stMultiSelect"] [data-baseweb="select"] [role="combobox"] {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding: 0 !important;
            min-height: auto !important;
            color: #111827 !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stSelectbox"] [data-baseweb="select"] svg,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stMultiSelect"] [data-baseweb="select"] svg {
            color: #374151 !important;
            fill: #374151 !important;
            opacity: 1 !important;
            flex-shrink: 0 !important;
        }
        /* Multiselect: tag chips only — no full-height white slabs inside the control */
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stMultiSelect"] [data-baseweb="select"] ul {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            gap: 6px !important;
            min-height: 0 !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"])
            [data-testid="stMultiSelect"] [data-baseweb="select"] [data-baseweb="tag"] {
            background: #e5e7eb !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 6px !important;
            color: #111827 !important;
            box-shadow: none !important;
            min-height: 0 !important;
            margin: 0 !important;
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
            color: var(--ips-text) !important;
            font-weight: 500 !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stRadio"] label,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stRadio"] span {
            font-size: var(--ips-ctrl-fs) !important;
            color: var(--ips-text) !important;
            font-weight: 500 !important;
        }

        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stFileUploader"] {
            border-radius: var(--ips-ctrl-radius) !important;
            border: 1px dashed #9ca3af !important;
            background: #ffffff !important;
            padding: 0.28rem 0.4rem !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stFileUploader"] section {
            padding: 0 !important;
        }
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stFileUploader"] small,
        :is(section[data-testid="stMain"], section[data-testid="stSidebar"]) [data-testid="stFileUploader"] [data-testid="stCaptionContainer"] {
            font-size: 0.75rem !important;
        }

        /* ----- Sidebar: white panel ----- */
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div,
        [data-testid="stSidebar"] {
            background: var(--ips-bg-sidebar) !important;
            background-color: var(--ips-bg-sidebar) !important;
            color: #111827 !important;
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.5rem !important;
            background: transparent !important;
        }
        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] .stMarkdown p,
        section[data-testid="stSidebar"] .stMarkdown li,
        section[data-testid="stSidebar"] .stMarkdown h1,
        section[data-testid="stSidebar"] .stMarkdown h2,
        section[data-testid="stSidebar"] .stMarkdown h3,
        section[data-testid="stSidebar"] .stMarkdown h4,
        section[data-testid="stSidebar"] .stMarkdown h5,
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
            color: #111827 !important;
            font-weight: 500 !important;
        }
        section[data-testid="stSidebar"] .stMarkdown h1,
        section[data-testid="stSidebar"] .stMarkdown h2,
        section[data-testid="stSidebar"] .stMarkdown h3 {
            font-weight: 700 !important;
        }
        section[data-testid="stSidebar"] .stMarkdown h4,
        section[data-testid="stSidebar"] .stMarkdown h5 {
            font-weight: 600 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] span {
            color: #111827 !important;
            font-weight: 600 !important;
        }

        section[data-testid="stMain"] .stMetric {
            background: #ffffff;
            border: 1px solid var(--ips-border);
            border-radius: var(--ips-radius-lg);
            padding: 0.55rem 0.65rem !important;
            box-shadow: var(--ips-shadow);
        }
        section[data-testid="stMain"] [data-testid="stMetricLabel"] {
            font-size: 0.75rem !important;
            color: #1f2937 !important;
            font-weight: 600 !important;
        }
        section[data-testid="stMain"] [data-testid="stMetricValue"] {
            font-size: 1.05rem !important;
            color: #111827 !important;
            font-weight: 700 !important;
        }

        /* ----- Dashboard / summary strips ----- */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-dash-metrics) {
            padding: 0.12rem 0 0.28rem 0 !important;
            margin-bottom: 0.3rem !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            border-radius: 0 !important;
        }

        /* ----- Estimate editor: totals strip + document-style proposal surface ----- */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-estimate-metrics-strip) {
            padding: 0.32rem 0.45rem 0.38rem !important;
            margin-bottom: 0.32rem !important;
            background: #ffffff !important;
            border: 1px solid rgba(15, 23, 42, 0.08) !important;
            box-shadow: none !important;
            border-radius: 8px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-proposal-doc-surface) {
            background: #ffffff !important;
            border-color: var(--ips-border) !important;
            padding: 10px 12px 12px 12px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-proposal-doc-surface) .stMarkdown p,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(span.ips-proposal-doc-surface) [data-testid="stCaptionContainer"] {
            color: var(--ips-text-secondary) !important;
        }

        /* Destructive / danger (Streamlit tertiary) — readable on light grey app chrome */
        section[data-testid="stMain"] .stButton > button[kind="tertiary"],
        section[data-testid="stMain"] .stButton > button[data-testid="baseButton-tertiary"],
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="tertiary"],
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[data-testid="baseButton-tertiary"],
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button[kind="tertiary"],
        section[data-testid="stMain"] [data-testid="stDownloadButton"] button[data-testid="baseButton-tertiary"] {
            color: #991b1b !important;
            border-color: #f87171 !important;
            background: #fecaca !important;
            font-weight: 600 !important;
        }

        @media (max-width: 768px) {
            section[data-testid="stMain"] > div {
                max-width: 100% !important;
                margin-left: 0 !important;
                margin-right: 0 !important;
                min-width: 0 !important;
                width: 100% !important;
            }
            section[data-testid="stMain"] .block-container {
                width: 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
                margin-left: 0 !important;
                padding-left: 12px !important;
                padding-right: 12px !important;
                box-sizing: border-box !important;
            }
            section[data-testid="stMain"] .stButton > button,
            section[data-testid="stMain"] [data-testid="stDownloadButton"] button {
                min-width: 0 !important;
                max-width: 100% !important;
            }
            section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                max-width: 100% !important;
                min-width: 0 !important;
            }
            section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                min-width: 0 !important;
                max-width: 100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
