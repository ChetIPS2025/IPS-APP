"""Coastal-style dashboard chrome (IPS branding, light SaaS layout)."""

from __future__ import annotations

import streamlit as st

COASTAL_THEME_KEY = "ips_coastal_dashboard_theme_v1"
COASTAL_MARKER_CLASS = "ips-coastal-dashboard"


def inject_coastal_theme() -> None:
    if st.session_state.get(COASTAL_THEME_KEY):
        return
    st.session_state[COASTAL_THEME_KEY] = True
    st.markdown(
        f"""
        <style>
        /* Page canvas */
        .stApp:has(.{COASTAL_MARKER_CLASS}),
        .stApp:has(.{COASTAL_MARKER_CLASS}) [data-testid="stAppViewContainer"] {{
          background: #f8fafc !important;
        }}
        section[data-testid="stMain"]:has(.{COASTAL_MARKER_CLASS}) {{
          background: #f8fafc !important;
        }}
        section[data-testid="stMain"]:has(.{COASTAL_MARKER_CLASS}) .block-container {{
          padding: 1.25rem 1.5rem 1.5rem !important;
          max-width: 1680px !important;
        }}
        section[data-testid="stMain"]:has(.{COASTAL_MARKER_CLASS}) [data-testid="stVerticalBlock"] > div {{
          gap: 0.65rem !important;
        }}
        section[data-testid="stMain"]:has(.{COASTAL_MARKER_CLASS}) [data-testid="stVerticalBlockBorderWrapper"] {{
          border: 1px solid #e5eaf2 !important;
          border-radius: 16px !important;
          background: #ffffff !important;
          box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
          padding: 0.85rem 1rem !important;
        }}

        /* Sidebar — coastal light nav when dashboard is open */
        .stApp:has(.{COASTAL_MARKER_CLASS}) section[data-testid="stSidebar"] {{
          background: #ffffff !important;
          border-right: 1px solid #e5eaf2 !important;
        }}
        .stApp:has(.{COASTAL_MARKER_CLASS}) section[data-testid="stSidebar"] > div {{
          background: #ffffff !important;
        }}
        .stApp:has(.{COASTAL_MARKER_CLASS}) section[data-testid="stSidebar"] div.stButton > button {{
          font-size: 14px !important;
          border-radius: 10px !important;
          min-height: 2.35rem !important;
          background: transparent !important;
          border: 1px solid transparent !important;
          color: #334155 !important;
        }}
        .stApp:has(.{COASTAL_MARKER_CLASS}) section[data-testid="stSidebar"] div.stButton > button:hover:not(:disabled) {{
          background: #f1f5f9 !important;
        }}
        .stApp:has(.{COASTAL_MARKER_CLASS}) section[data-testid="stSidebar"] button[kind="primary"],
        .stApp:has(.{COASTAL_MARKER_CLASS}) section[data-testid="stSidebar"] button[data-testid="baseButton-primary"] {{
          background: #eff6ff !important;
          border: 1px solid #bfdbfe !important;
          color: #1d4ed8 !important;
          font-weight: 600 !important;
        }}
        .stApp:has(.{COASTAL_MARKER_CLASS}) section[data-testid="stSidebar"] button[kind="primary"] p,
        .stApp:has(.{COASTAL_MARKER_CLASS}) section[data-testid="stSidebar"] button[data-testid="baseButton-primary"] p {{
          color: #1d4ed8 !important;
        }}

        /* KPI / cards (HTML) */
        .ips-coastal-kpi {{
          background: #fff;
          border: 1px solid #e5eaf2;
          border-radius: 16px;
          padding: 1rem 1.1rem;
          box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
          min-height: 108px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }}
        .ips-coastal-kpi-top {{
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 0.5rem;
        }}
        .ips-coastal-kpi-icon {{
          width: 40px;
          height: 40px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.1rem;
          flex-shrink: 0;
        }}
        .ips-coastal-kpi-label {{
          font-size: 0.8rem;
          color: #64748b;
          font-weight: 500;
          margin: 0;
        }}
        .ips-coastal-kpi-value {{
          font-size: 1.45rem;
          font-weight: 700;
          color: #0f172a;
          letter-spacing: -0.02em;
          margin: 0.35rem 0 0.15rem 0;
          line-height: 1.2;
        }}
        .ips-coastal-kpi-trend {{
          font-size: 0.75rem;
          font-weight: 600;
          margin: 0;
        }}
        .ips-coastal-kpi-trend.up {{ color: #059669; }}
        .ips-coastal-kpi-trend.down {{ color: #dc2626; }}
        .ips-coastal-kpi-trend.flat {{ color: #94a3b8; }}

        .ips-coastal-card-title {{
          font-size: 0.95rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0 0 0.65rem 0;
        }}
        .ips-coastal-card-head {{
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 0.5rem;
        }}
        .ips-coastal-link {{
          font-size: 0.8rem;
          color: #2563eb;
          font-weight: 600;
          text-decoration: none;
        }}

        .ips-coastal-activity-item {{
          display: flex;
          gap: 0.65rem;
          align-items: flex-start;
          padding: 0.55rem 0;
          border-bottom: 1px solid #f1f5f9;
        }}
        .ips-coastal-activity-item:last-child {{ border-bottom: none; }}
        .ips-coastal-act-icon {{
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.85rem;
          flex-shrink: 0;
        }}
        .ips-coastal-act-title {{
          font-size: 0.82rem;
          font-weight: 600;
          color: #0f172a;
          margin: 0;
          line-height: 1.3;
        }}
        .ips-coastal-act-meta {{
          font-size: 0.72rem;
          color: #94a3b8;
          margin: 0.15rem 0 0 0;
        }}

        .ips-coastal-deadline {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 0;
          border-bottom: 1px solid #f1f5f9;
        }}
        .ips-coastal-deadline:last-child {{ border-bottom: none; }}
        .ips-coastal-badge {{
          display: inline-block;
          font-size: 0.68rem;
          font-weight: 700;
          padding: 0.2rem 0.45rem;
          border-radius: 6px;
          white-space: nowrap;
        }}
        .ips-coastal-badge-urgent {{ background: #fee2e2; color: #b91c1c; }}
        .ips-coastal-badge-soon {{ background: #ffedd5; color: #c2410c; }}
        .ips-coastal-badge-ok {{ background: #dcfce7; color: #166534; }}

        .ips-coastal-aging-row {{
          display: grid;
          grid-template-columns: 1fr 2.5fr auto;
          gap: 0.65rem;
          align-items: center;
          margin-bottom: 0.55rem;
          font-size: 0.8rem;
        }}
        .ips-coastal-aging-bar {{
          height: 8px;
          background: #f1f5f9;
          border-radius: 99px;
          overflow: hidden;
        }}
        .ips-coastal-aging-fill {{
          height: 100%;
          background: #3b82f6;
          border-radius: 99px;
        }}

        .ips-coastal-qa-btn {{
          background: #fff;
          border: 1px solid #e5eaf2;
          border-radius: 12px;
          padding: 0.65rem 0.4rem;
          text-align: center;
          min-height: 72px;
          box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }}
        .ips-coastal-qa-icon {{ font-size: 1.25rem; display: block; margin-bottom: 0.25rem; }}
        .ips-coastal-qa-label {{
          font-size: 0.72rem;
          font-weight: 600;
          color: #334155;
          line-height: 1.2;
        }}

        .ips-coastal-donut-wrap {{
          display: flex;
          align-items: center;
          gap: 1rem;
          flex-wrap: wrap;
        }}
        .ips-coastal-donut-legend {{
          flex: 1;
          min-width: 140px;
          font-size: 0.78rem;
          color: #475569;
        }}
        .ips-coastal-donut-legend div {{
          display: flex;
          justify-content: space-between;
          padding: 0.2rem 0;
        }}

        .ips-coastal-status-pill {{
          display: inline-block;
          padding: 0.15rem 0.5rem;
          border-radius: 99px;
          font-size: 0.7rem;
          font-weight: 700;
        }}

        @media (max-width: 900px) {{
          section[data-testid="stMain"]:has(.{COASTAL_MARKER_CLASS}) .block-container {{
            padding: 0.85rem !important;
          }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
