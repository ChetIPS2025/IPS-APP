"""
IPS design system — tokens, density, and global CSS injection.

Call :func:`apply_global_app_styles` once per authenticated session from ``main``.
"""

from __future__ import annotations

import streamlit as st

IPS_THEME_CSS_KEY = "ips_theme_global_v2"
IPS_GLOBAL_APP_STYLES_KEY = "ips_global_app_styles_v2"
IPS_DENSITY_KEY = "ips_display_density"

DENSITY_CHOICES = ("compact", "comfortable", "spacious")
DEFAULT_DENSITY = "compact"

# Global canvas tokens (single source of truth for app background)
APP_BG = "#FFFFFF"
SIDEBAR_BG = "#FFFFFF"
CARD_BG = "#FFFFFF"
BORDER_COLOR = "#E5EAF2"
HOVER_BG = "#F8FAFC"

# Design tokens (industrial SaaS)
COLORS = {
    "bg_app": APP_BG,
    "bg_surface": CARD_BG,
    "bg_muted": "#FFFFFF",
    "border": BORDER_COLOR,
    "border_strong": "#CBD5E1",
    "text": "#0F172A",
    "text_secondary": "#334155",
    "text_muted": "#64748B",
    "primary": "#2563eb",
    "primary_hover": "#1d4ed8",
    "success": "#059669",
    "warning": "#d97706",
    "danger": "#dc2626",
}


def get_density() -> str:
    d = str(st.session_state.get(IPS_DENSITY_KEY) or DEFAULT_DENSITY).strip().lower()
    return d if d in DENSITY_CHOICES else DEFAULT_DENSITY


def set_density(value: str) -> None:
    v = str(value or "").strip().lower()
    st.session_state[IPS_DENSITY_KEY] = v if v in DENSITY_CHOICES else DEFAULT_DENSITY


def apply_global_app_styles() -> None:
    """Inject unified white app canvas, surfaces, tables, tabs, dialogs (once per session)."""
    if st.session_state.get(IPS_GLOBAL_APP_STYLES_KEY):
        return
    st.session_state[IPS_GLOBAL_APP_STYLES_KEY] = True

    st.markdown(
        f"""
        <style>
        :root {{
            --ips-bg-main: {APP_BG};
            --ips-bg-sidebar: {SIDEBAR_BG};
            --ips-bg-card: {CARD_BG};
            --ips-bg-hover: {HOVER_BG};
            --ips-border: {BORDER_COLOR};
            --ips-text: {COLORS["text"]};
            --ips-text-secondary: {COLORS["text_secondary"]};
            --ips-text-muted: {COLORS["text_muted"]};
        }}

        html, body, .stApp {{
            background: {APP_BG} !important;
            background-color: {APP_BG} !important;
        }}
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        section[data-testid="stMain"],
        section[data-testid="stMain"] > div,
        section.main,
        main,
        .block-container {{
            background: {APP_BG} !important;
            background-color: {APP_BG} !important;
        }}

        div[data-testid="stVerticalBlock"],
        div[data-testid="stHorizontalBlock"],
        [data-testid="stVerticalBlock"],
        [data-testid="stHorizontalBlock"] {{
            background: {APP_BG} !important;
            background-color: {APP_BG} !important;
        }}

        section[data-testid="stMain"] {{
            color: var(--ips-text) !important;
        }}
        section[data-testid="stMain"] .block-container {{
            padding-top: 0.35rem !important;
            padding-bottom: 0.85rem !important;
            max-width: 1680px !important;
        }}

        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div,
        [data-testid="stSidebar"] {{
            background: {SIDEBAR_BG} !important;
            background-color: {SIDEBAR_BG} !important;
            border-right: 1px solid var(--ips-border) !important;
            color: var(--ips-text) !important;
        }}
        section[data-testid="stSidebar"] .block-container {{
            background: {SIDEBAR_BG} !important;
        }}

        /* Cards, panels, bordered wrappers */
        div[data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stForm"],
        [data-testid="stMetric"],
        div[data-testid="metric-container"] {{
            background: {CARD_BG} !important;
            background-color: {CARD_BG} !important;
        }}

        /* Tables */
        [data-testid="stDataFrame"],
        [data-testid="stDataEditor"],
        [data-testid="stTable"],
        [data-testid="stDataFrame"] > div,
        [data-testid="stDataEditor"] > div {{
            background: {CARD_BG} !important;
            background-color: {CARD_BG} !important;
        }}
        [data-testid="stDataFrame"] [data-testid="stTable"] thead tr th,
        [data-testid="stDataEditor"] [data-testid="stTable"] thead tr th {{
            background: {CARD_BG} !important;
            border-bottom: 1px solid {BORDER_COLOR} !important;
        }}
        [data-testid="stDataFrame"] [data-testid="stTable"] tbody tr td,
        [data-testid="stDataEditor"] [data-testid="stTable"] tbody tr td {{
            background: {CARD_BG} !important;
        }}
        [data-testid="stDataFrame"] [data-testid="stTable"] tbody tr:nth-child(even) td,
        [data-testid="stDataEditor"] [data-testid="stTable"] tbody tr:nth-child(even) td {{
            background: {CARD_BG} !important;
        }}
        [data-testid="stDataFrame"] [data-testid="stTable"] tbody tr:hover td,
        [data-testid="stDataEditor"] [data-testid="stTable"] tbody tr:hover td {{
            background: {HOVER_BG} !important;
        }}

        /* Tabs */
        [data-testid="stTabs"],
        [data-testid="stTabs"] [data-baseweb="tab-list"],
        [data-testid="stTabs"] [data-baseweb="tab-panel"],
        [data-testid="stTabs"] [role="tablist"],
        [data-testid="stTabs"] [role="tabpanel"] {{
            background: {CARD_BG} !important;
            background-color: {CARD_BG} !important;
        }}

        /* Expanders */
        [data-testid="stExpander"] details,
        [data-testid="stExpander"] summary {{
            background: {CARD_BG} !important;
            background-color: {CARD_BG} !important;
        }}

        /* Dialogs / modals */
        div[data-testid="stDialog"],
        div[data-testid="stDialog"] > div,
        div[data-testid="stModal"],
        [data-testid="stDialog"] [data-testid="stVerticalBlockBorderWrapper"] {{
            background: {CARD_BG} !important;
            background-color: {CARD_BG} !important;
        }}

        /* Top bar sticky wrap — no gray gradient */
        .ips-topbar-wrap {{
            background: {APP_BG} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_force_white_final_override() -> None:
    """Last CSS in the cascade — wins over page-specific background rules."""
    st.markdown(
        """
        <style id="ips-force-white-final">
        html,
        body,
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        [data-testid="stVerticalBlock"],
        [data-testid="stHorizontalBlock"],
        section.main,
        main,
        .block-container,
        .ips-page,
        .ips-shell,
        .page-shell,
        .content-shell {
            background-color: #FFFFFF !important;
            background: #FFFFFF !important;
        }
        div[class*="page"],
        div[class*="shell"],
        div[class*="container"],
        div[class*="wrapper"] {
            background-color: #FFFFFF !important;
            background: #FFFFFF !important;
        }
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div,
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            background: #FFFFFF !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_global_css() -> None:
    """Inject IPS global theme (layout, tables, topbar, density, toasts)."""
    apply_global_app_styles()

    density = get_density()
    st.markdown(
        f'<div class="ips-density-root ips-density-{density}" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )

    try:
        from app.ui.page_shell import inject_ips_dashboard_layout
    except ImportError:
        from ui.page_shell import inject_ips_dashboard_layout  # type: ignore
    inject_ips_dashboard_layout()

    try:
        from app.ips_app_shell import inject_ips_app_shell_styles
    except ImportError:
        from ips_app_shell import inject_ips_app_shell_styles  # type: ignore
    inject_ips_app_shell_styles()

    if not st.session_state.get(IPS_THEME_CSS_KEY):
        st.session_state[IPS_THEME_CSS_KEY] = True
        st.markdown(
        f"""
        <style>
        /* ----- Display density ----- */
        .ips-density-compact {{
            --ips-row-pad: 5px 8px;
            --ips-card-pad: 0.38rem 0.5rem;
            --ips-ctrl-h: 2.125rem;
            --ips-btn-h: 2.25rem;
        }}
        .ips-density-comfortable {{
            --ips-row-pad: 7px 10px;
            --ips-card-pad: 0.5rem 0.65rem;
            --ips-ctrl-h: 2.35rem;
            --ips-btn-h: 2.5rem;
        }}
        .ips-density-spacious {{
            --ips-row-pad: 9px 12px;
            --ips-card-pad: 0.62rem 0.78rem;
            --ips-ctrl-h: 2.5rem;
            --ips-btn-h: 2.75rem;
        }}

        /* ----- Professional tables ----- */
        section[data-testid="stMain"] .ips-table-surface [data-testid="stDataFrame"],
        section[data-testid="stMain"] .ips-table-surface [data-testid="stDataEditor"],
        section[data-testid="stMain"] [data-testid="stDataFrame"],
        section[data-testid="stMain"] [data-testid="stDataEditor"] {{
            border: 1px solid {COLORS["border"]} !important;
            border-radius: 8px !important;
            overflow: hidden !important;
        }}
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] thead tr th {{
            position: sticky !important;
            top: 0 !important;
            z-index: 3 !important;
            background: {CARD_BG} !important;
            color: {COLORS["text"]} !important;
            font-size: 0.74rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.03em !important;
            padding: var(--ips-row-pad, 5px 8px) !important;
            border-bottom: 1px solid {BORDER_COLOR} !important;
        }}
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] tbody tr:nth-child(even) td {{
            background: {CARD_BG} !important;
        }}
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] tbody tr:hover td {{
            background: {HOVER_BG} !important;
        }}
        section[data-testid="stMain"] [data-testid="stDataFrame"] [data-testid="stTable"] td {{
            font-size: 0.8125rem !important;
            padding: var(--ips-row-pad, 5px 8px) !important;
            max-width: 280px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: {COLORS["text_secondary"]} !important;
        }}

        /* ----- KPI cards ----- */
        .ips-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
            gap: 0.45rem;
            margin: 0.2rem 0 0.45rem 0;
        }}
        .ips-kpi-card {{
            background: #ffffff;
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
            padding: 0.45rem 0.55rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05);
            transition: border-color 0.12s ease, box-shadow 0.12s ease;
            cursor: default;
        }}
        .ips-kpi-card.ips-kpi-clickable:hover {{
            border-color: {COLORS["primary"]};
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.12);
        }}
        .ips-kpi-label {{
            font-size: 0.72rem;
            font-weight: 600;
            color: {COLORS["text_muted"]};
            margin: 0 0 0.15rem 0;
            line-height: 1.2;
        }}
        .ips-kpi-value {{
            font-size: 1.28rem;
            font-weight: 700;
            color: {COLORS["text"]};
            line-height: 1.15;
            letter-spacing: -0.02em;
        }}
        .ips-kpi-sub {{
            font-size: 0.68rem;
            color: {COLORS["text_muted"]};
            margin-top: 0.12rem;
        }}

        /* ----- Empty states ----- */
        .ips-empty-state {{
            text-align: center;
            padding: 1.25rem 0.75rem;
            border: 1px dashed {COLORS["border_strong"]};
            border-radius: 8px;
            background: {CARD_BG};
            margin: 0.35rem 0;
        }}
        .ips-empty-icon {{
            font-size: 1.75rem;
            line-height: 1;
            margin-bottom: 0.35rem;
            opacity: 0.85;
        }}
        .ips-empty-title {{
            font-size: 0.95rem;
            font-weight: 700;
            color: {COLORS["text"]};
            margin: 0 0 0.2rem 0;
        }}
        .ips-empty-msg {{
            font-size: 0.8125rem;
            color: {COLORS["text_secondary"]};
            margin: 0 0 0.55rem 0;
            max-width: 420px;
            margin-left: auto;
            margin-right: auto;
        }}

        /* ----- Skeleton loading ----- */
        @keyframes ips-shimmer {{
            0% {{ background-position: -200% 0; }}
            100% {{ background-position: 200% 0; }}
        }}
        .ips-skeleton-row {{
            height: 2rem;
            border-radius: 6px;
            margin-bottom: 0.35rem;
            background: linear-gradient(90deg, #e5e7eb 25%, #f3f4f6 50%, #e5e7eb 75%);
            background-size: 200% 100%;
            animation: ips-shimmer 1.2s ease-in-out infinite;
        }}

        /* ----- Badges ----- */
        .ips-badge {{
            display: inline-flex;
            align-items: center;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            padding: 0.12rem 0.45rem;
            border-radius: 999px;
            border: 1px solid transparent;
            white-space: nowrap;
            line-height: 1.2;
        }}
        .ips-badge-neutral {{ background: #f1f5f9; color: #475569; border-color: #e2e8f0; }}
        .ips-badge-primary {{ background: #dbeafe; color: #1e40af; border-color: #93c5fd; }}
        .ips-badge-success {{ background: #d1fae5; color: #065f46; border-color: #6ee7b7; }}
        .ips-badge-warning {{ background: #fef3c7; color: #92400e; border-color: #fcd34d; }}
        .ips-badge-danger {{ background: #fee2e2; color: #991b1b; border-color: #fca5a5; }}

        /* ----- Top bar ----- */
        .ips-topbar-wrap {{
            position: sticky;
            top: 0;
            z-index: 50;
            margin: -0.35rem 0 0.45rem 0;
            padding: 0.35rem 0;
            background: {APP_BG} !important;
        }}
        .ips-topbar {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
            background: #ffffff;
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
            padding: 0.32rem 0.5rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }}
        .ips-topbar-crumb {{
            font-size: 0.78rem;
            font-weight: 600;
            color: {COLORS["text_muted"]};
            white-space: nowrap;
            margin-right: 0.25rem;
        }}
        .ips-topbar-crumb strong {{
            color: {COLORS["text"]};
            font-weight: 700;
        }}
        .ips-topbar-spacer {{ flex: 1 1 auto; min-width: 0.5rem; }}
        .ips-topbar-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
            color: {COLORS["text_secondary"]};
            padding: 0.2rem 0.45rem;
            border-radius: 6px;
            background: {CARD_BG};
            border: 1px solid {COLORS["border"]};
        }}
        .ips-topbar-pill .ips-dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: {COLORS["primary"]};
        }}
        .ips-topbar-pill.ips-has-alert .ips-dot {{
            background: {COLORS["danger"]};
        }}

        /* Streamlit toast polish */
        [data-testid="stToast"] {{
            border-radius: 8px !important;
            border: 1px solid {COLORS["border"]} !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1) !important;
        }}

        /* Hide default Streamlit chrome noise on main */
        section[data-testid="stMain"] header[data-testid="stHeader"] {{
            background: {APP_BG} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
        )

    try:
        from app.ui.clean_table import inject_clean_table_css
    except ImportError:
        from ui.clean_table import inject_clean_table_css  # type: ignore
    inject_clean_table_css()

    inject_force_white_final_override()
