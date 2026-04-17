"""
Shared IPS dark-theme layout for CRUD list pages (Customers, Labor, Employees): toolbar + side panel.

- Toolbar marker: ``<div class="ips-crud-toolbar-root"></div>`` inside ``st.container(border=True)``
- Side panel marker: ``<span class="ips-crud-side-anchor"></span>`` inside bordered panel
- Page split: :data:`IPS_CRUD_LIST_PAGE_SPLIT` + :data:`IPS_CRUD_LIST_PAGE_GAP` for main vs side columns
- Modal / ``st.dialog``: :func:`inject_ips_modal_styles` (also invoked from :func:`inject_ips_crud_list_styles`)

Call :func:`inject_ips_crud_list_styles` once per page render (or rely on first toolbar render).
"""

from __future__ import annotations

import streamlit as st

IPS_CRUD_LIST_STYLES_KEY = "ips_crud_list_styles_injected"
IPS_MODAL_STYLES_KEY = "ips_modal_styles_injected"

# Main grid vs side panel — use everywhere (Customers, Labor, Employees) so widths stay identical.
IPS_CRUD_LIST_PAGE_SPLIT: tuple[float, float] = (2.35, 1.0)
IPS_CRUD_LIST_PAGE_GAP = "medium"


def inject_ips_modal_styles() -> None:
    """IPS visual system for ``st.dialog`` modals: navy shell, soft border, compact controls, button roles."""
    if st.session_state.get(IPS_MODAL_STYLES_KEY):
        return
    st.session_state[IPS_MODAL_STYLES_KEY] = True
    st.markdown(
        """
        <style>
        /* ----- IPS modal / Streamlit st.dialog ----- */
        div[data-testid="stBackdrop"] {
            background: rgba(2, 6, 23, 0.78) !important;
            backdrop-filter: blur(6px) !important;
        }
        div[data-testid="stDialog"] {
            max-width: min(480px, 94vw) !important;
        }
        div[data-testid="stDialog"] > div {
            background: linear-gradient(165deg, #111c33 0%, #0b1224 52%, #0a0f1c 100%) !important;
            border: 1px solid rgba(71, 85, 105, 0.55) !important;
            border-radius: 14px !important;
            box-shadow:
                0 28px 56px rgba(0, 0, 0, 0.55),
                inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
            overflow: hidden !important;
        }
        div[data-testid="stDialog"] h1,
        div[data-testid="stDialog"] h2,
        div[data-testid="stDialog"] h3 {
            color: #f1f5f9 !important;
            font-size: 1.125rem !important;
            font-weight: 650 !important;
            letter-spacing: -0.02em;
            margin: 0 0 0.35rem 0 !important;
            padding: 0 !important;
            border: none !important;
        }
        p.ips-modal-subtitle {
            color: #94a3b8 !important;
            font-size: 0.8125rem !important;
            line-height: 1.45 !important;
            margin: 0 0 0.65rem 0 !important;
        }
        p.ips-modal-hint {
            color: #64748b !important;
            font-size: 0.75rem !important;
            line-height: 1.35 !important;
            margin: 0.25rem 0 0.5rem 0 !important;
        }
        div[data-testid="stDialog"] hr {
            margin: 0.55rem 0 !important;
            border: none !important;
            border-top: 1px solid rgba(71, 85, 105, 0.45) !important;
        }
        div[data-testid="stDialog"] [data-baseweb="input"],
        div[data-testid="stDialog"] input,
        div[data-testid="stDialog"] textarea {
            background: rgba(15, 23, 42, 0.72) !important;
            border: 1px solid rgba(71, 85, 105, 0.5) !important;
            border-radius: 8px !important;
            color: #f8fafc !important;
            font-size: 0.875rem !important;
        }
        div[data-testid="stDialog"] label,
        div[data-testid="stDialog"] [data-testid="stWidgetLabel"] {
            color: #cbd5e1 !important;
            font-size: 0.8125rem !important;
        }
        div[data-testid="stDialog"] [data-testid="stCheckbox"] label {
            color: #e2e8f0 !important;
            font-size: 0.8125rem !important;
        }
        div[data-testid="stDialog"] [data-baseweb="select"] > div {
            border-radius: 8px !important;
            border-color: rgba(71, 85, 105, 0.55) !important;
            background: rgba(15, 23, 42, 0.72) !important;
        }
        /* Primary = strong; secondary = muted (Cancel) */
        div[data-testid="stDialog"] button[kind="primary"],
        div[data-testid="stDialog"] button[data-testid="baseButton-primary"] {
            background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%) !important;
            border: 1px solid rgba(59, 130, 246, 0.65) !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            min-height: 2.35rem !important;
            box-shadow: 0 2px 10px rgba(37, 99, 235, 0.38) !important;
        }
        div[data-testid="stDialog"] button[kind="primary"]:hover:not(:disabled),
        div[data-testid="stDialog"] button[data-testid="baseButton-primary"]:hover:not(:disabled) {
            background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%) !important;
            border-color: rgba(96, 165, 250, 0.85) !important;
        }
        div[data-testid="stDialog"] button[kind="secondary"] {
            background: rgba(30, 41, 59, 0.92) !important;
            border: 1px solid rgba(100, 116, 139, 0.42) !important;
            color: #94a3b8 !important;
            font-weight: 500 !important;
            border-radius: 8px !important;
            min-height: 2.35rem !important;
        }
        div[data-testid="stDialog"] button[kind="secondary"]:hover:not(:disabled) {
            background: rgba(51, 65, 85, 0.95) !important;
            border-color: rgba(148, 163, 184, 0.45) !important;
            color: #cbd5e1 !important;
        }
        /* Alerts inside modal */
        div[data-testid="stDialog"] [data-testid="stAlert"] {
            border-radius: 8px !important;
            font-size: 0.8125rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_ips_crud_list_styles() -> None:
    inject_ips_modal_styles()
    if st.session_state.get(IPS_CRUD_LIST_STYLES_KEY):
        return
    st.session_state[IPS_CRUD_LIST_STYLES_KEY] = True
    st.markdown(
        """
        <style>
        /* ----- Page subtitle (under render_header) ----- */
        p.ips-crud-page-subtitle {
            color: #94a3b8;
            font-size: 0.9rem;
            line-height: 1.45;
            margin: 0 0 1rem 0;
            padding: 0;
        }

        /* ----- Search + Status row: match column rhythm ----- */
        div[data-testid="stHorizontalBlock"]:has(.ips-crud-filter-row-start) {
            gap: 0.75rem !important;
            align-items: flex-end !important;
            margin-bottom: 0.35rem !important;
        }

        /* ----- Action toolbar (Add / Edit / Deactivate / Delete) ----- */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-toolbar-root) {
            padding: 6px 8px 8px 8px !important;
            margin-bottom: 8px !important;
        }
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] {
            align-items: center;
            gap: 0.35rem;
        }
        /* Selection count vertically centered with buttons */
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) {
            display: flex !important;
            align-items: center !important;
            min-height: 2.25rem;
        }
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) .ips-ta-summary {
            line-height: 1.35;
        }
        /* All action buttons: same min-height (Materials-style) */
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"] button {
            min-height: 2.25rem !important;
            border-radius: 8px !important;
        }
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(4) button:not(:disabled) {
            background: rgba(234, 179, 8, 0.14) !important;
            border-color: rgba(250, 204, 21, 0.55) !important;
            color: #fde68a !important;
        }
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(4) button:not(:disabled):hover {
            background: rgba(234, 179, 8, 0.22) !important;
            border-color: rgba(253, 224, 71, 0.75) !important;
        }
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(5) button:not(:disabled) {
            background: rgba(220, 38, 38, 0.18) !important;
            border-color: rgba(248, 113, 113, 0.75) !important;
            color: #fecaca !important;
        }
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(5) button:not(:disabled):hover {
            background: rgba(220, 38, 38, 0.28) !important;
            border-color: rgba(252, 165, 165, 0.9) !important;
        }

        /* ----- Side panel (add / edit) ----- */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-side-anchor) {
            background: rgba(15, 23, 42, 0.72) !important;
            border-color: rgba(71, 85, 105, 0.55) !important;
            border-radius: 10px !important;
            padding: 12px 14px 14px 14px !important;
            margin-bottom: 8px !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-side-anchor) h3 {
            color: #e2e8f0 !important;
            font-size: 1.05rem !important;
            font-weight: 650 !important;
            margin: 0 0 10px 0 !important;
            padding-bottom: 8px !important;
            border-bottom: 1px solid rgba(100, 116, 139, 0.35) !important;
        }
        /* Side panel: Save / Cancel / Close — match toolbar button height and radius */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-side-anchor) button {
            min-height: 2.25rem !important;
            border-radius: 8px !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-side-anchor)
            button[data-testid="baseButton-primary"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-side-anchor) button[kind="primary"] {
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_crud_list_subtitle(text: str) -> None:
    """Same subtitle spacing/styling for Employees, Customers, etc."""
    import html

    inject_ips_crud_list_styles()
    st.markdown(
        f'<p class="ips-crud-page-subtitle">{html.escape(text)}</p>',
        unsafe_allow_html=True,
    )
