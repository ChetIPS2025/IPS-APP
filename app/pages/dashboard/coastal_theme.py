"""Coastal Builders dashboard visual system (IPS-branded)."""

from __future__ import annotations

import streamlit as st

COASTAL_MARKER = "ips-coastal-dashboard"
THEME_KEY = "ips_coastal_theme_v5"


def inject_coastal_theme() -> None:
    if st.session_state.get(THEME_KEY):
        return
    st.session_state[THEME_KEY] = True
    c = COASTAL_MARKER
    st.markdown(
        f"""
        <style>
        /* ============================================================
           IPS Coastal Dashboard – visual system
           All rules scoped with :has(.{c}) beat the global
           ips_app_shell rules (higher specificity + !important).
        ============================================================ */

        /* App canvas */
        section[data-testid="stMain"]:has(.{c}) .block-container {{
          padding: 1.25rem 1.75rem 2rem !important;
          max-width: 100% !important;
          background: #f8fafc !important;
        }}
        section[data-testid="stMain"]:has(.{c}) [data-testid="stVerticalBlock"] > div {{
          gap: 0.65rem !important;
        }}

        /* ── CRITICAL: reset the global ".stMarkdown p" color override ──
           The app shell forces color:#334155 !important on all stMarkdown p.
           This scoped rule has higher specificity and sets our custom
           elements back to their own color values. */
        section[data-testid="stMain"]:has(.{c}) .stMarkdown p,
        section[data-testid="stMain"]:has(.{c}) .stMarkdown li,
        section[data-testid="stMain"]:has(.{c}) .stMarkdown span {{
          color: inherit !important;
          font-weight: inherit !important;
        }}

        /* Bordered Streamlit cards */
        section[data-testid="stMain"]:has(.{c}) [data-testid="stVerticalBlockBorderWrapper"] {{
          border: 1px solid #e5eaf2 !important;
          border-radius: 14px !important;
          background: #ffffff !important;
          box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06) !important;
          padding: 1rem 1.1rem 1.05rem !important;
        }}

        /* Cards */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-card-wrap {{
          border: 1px solid #e5eaf2 !important;
          border-radius: 14px !important;
          background: #ffffff !important;
          box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06) !important;
          padding: 1rem 1.15rem 1.1rem !important;
        }}
        section[data-testid="stMain"]:has(.{c}) [data-testid="stVerticalBlockBorderWrapper"]:has(.ips-coastal-inner) {{
          border: none !important;
          box-shadow: none !important;
          background: #ffffff !important;
          padding: 0 !important;
        }}

        /* Sidebar — Coastal style */
        .stApp:has(.{c}) section[data-testid="stSidebar"],
        .stApp:has(.{c}) section[data-testid="stSidebar"] > div {{
          background: #ffffff !important;
          border-right: 1px solid #e8edf4 !important;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] .block-container {{
          padding-top: 0.5rem !important;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] div.stButton > button {{
          font-size: 14px !important;
          font-weight: 500 !important;
          border-radius: 8px !important;
          min-height: 2.25rem !important;
          padding: 0.35rem 0.65rem !important;
          background: #ffffff !important;
          border: none !important;
          color: #475569 !important;
          box-shadow: none !important;
          text-align: left !important;
          justify-content: flex-start !important;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] div.stButton > button:hover {{
          background: #ffffff !important;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] button[kind="primary"] {{
          background: #eff6ff !important;
          border-left: 3px solid #2563eb !important;
          border-radius: 0 8px 8px 0 !important;
          color: #1d4ed8 !important;
          font-weight: 600 !important;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] button[kind="primary"] p {{
          color: #1d4ed8 !important;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] .ips-coastal-sidebar-head {{
          margin: 0.15rem 0 0.85rem 0.2rem;
          padding-bottom: 0.65rem;
          border-bottom: 1px solid #e8edf4;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] .ips-coastal-sidebar-title {{
          font-size: 0.95rem;
          font-weight: 800;
          letter-spacing: 0.04em;
          color: #0f172a;
          margin: 0;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] .ips-coastal-sidebar-sub {{
          font-size: 0.62rem;
          font-weight: 700;
          letter-spacing: 0.08em;
          color: #64748b;
          margin: 0.12rem 0 0;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] .ips-coastal-profile {{
          border-top: 1px solid #e8edf4;
          margin-top: 1rem;
          padding: 0.75rem 0.35rem 0.35rem;
          display: flex;
          align-items: center;
          gap: 0.55rem;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] .ips-coastal-profile-avatar {{
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: #dbeafe;
          color: #1d4ed8;
          font-size: 0.72rem;
          font-weight: 800;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] .ips-coastal-collapse-hint {{
          font-size: 0.72rem;
          color: #94a3b8;
          margin: 0.35rem 0 0.5rem 0.35rem;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] .ips-coastal-profile-name {{
          font-weight: 700;
          color: #0f172a;
          margin: 0;
        }}
        .stApp:has(.{c}) section[data-testid="stSidebar"] .ips-coastal-profile-role {{
          color: #64748b;
          font-size: 0.75rem;
          margin: 0;
        }}

        /* Header */
        .ips-coastal-dash-title {{
          font-size: 1.65rem !important;
          font-weight: 700 !important;
          color: #0f172a !important;
          margin: 0 !important;
          line-height: 1.2 !important;
        }}
        .ips-coastal-dash-sub {{
          color: #64748b !important;
          font-size: 0.9rem !important;
          margin: 0.15rem 0 0 !important;
        }}

        /* KPI */
        .ips-coastal-kpi {{
          background: #fff;
          border: 1px solid #e5eaf2;
          border-radius: 16px;
          padding: 1rem 1.05rem 0.85rem;
          box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.05);
          min-height: 118px;
          height: 100%;
        }}
        .ips-coastal-kpi-top {{
          display: flex;
          align-items: flex-start;
          gap: 0.75rem;
        }}
        .ips-coastal-kpi-icon {{
          width: 42px;
          height: 42px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.15rem;
          flex-shrink: 0;
        }}
        .ips-coastal-kpi-body {{ flex: 1; min-width: 0; }}
        .ips-coastal-kpi-label {{
          font-size: 0.78rem;
          color: #64748b;
          font-weight: 500;
          margin: 0;
        }}
        .ips-coastal-kpi-value {{
          font-size: 1.38rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0.2rem 0 0;
          letter-spacing: -0.02em;
          line-height: 1.15;
        }}
        .ips-coastal-kpi-trend {{
          font-size: 0.72rem;
          font-weight: 600;
          margin: 0;
        }}
        .ips-coastal-kpi-trend.up {{ color: #059669; }}
        .ips-coastal-kpi-trend.down {{ color: #dc2626; }}
        .ips-coastal-kpi-trend.bad-up {{ color: #dc2626; }}
        .ips-coastal-kpi-trend.good-down {{ color: #059669; }}

        /* Card headers */
        .ips-coastal-card-head {{
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 0.65rem;
        }}
        .ips-coastal-card-title {{
          font-size: 0.92rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0;
        }}
        .ips-coastal-view-link {{
          font-size: 0.78rem;
          font-weight: 600;
          color: #2563eb;
        }}

        /* Activity */
        .ips-coastal-activity-row {{
          display: flex;
          gap: 0.65rem;
          align-items: flex-start;
          padding: 0.55rem 0;
          border-bottom: 1px solid #f1f5f9;
        }}
        .ips-coastal-activity-row:last-child {{ border-bottom: none; }}
        .ips-coastal-act-icon {{
          width: 34px; height: 34px; border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          font-size: 0.9rem; flex-shrink: 0;
        }}
        .ips-coastal-act-body {{ flex: 1; min-width: 0; }}
        .ips-coastal-act-title {{
          font-size: 0.8rem; font-weight: 600; color: #0f172a; margin: 0; line-height: 1.3;
        }}
        .ips-coastal-act-desc {{
          font-size: 0.72rem; color: #94a3b8; margin: 0.12rem 0 0;
        }}
        .ips-coastal-act-time {{
          font-size: 0.72rem; color: #94a3b8; white-space: nowrap; flex-shrink: 0;
          padding-top: 0.1rem;
        }}

        /* Deadlines */
        .ips-coastal-deadline-row {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 0;
          border-bottom: 1px solid #f1f5f9;
        }}
        .ips-coastal-deadline-row:last-child {{ border-bottom: none; }}
        .ips-coastal-deadline-title {{
          font-size: 0.8rem; font-weight: 600; color: #0f172a; margin: 0;
        }}
        .ips-coastal-deadline-date {{
          font-size: 0.72rem; color: #94a3b8; margin: 0.1rem 0 0;
        }}
        .ips-coastal-pill {{
          font-size: 0.68rem; font-weight: 700;
          padding: 0.2rem 0.5rem; border-radius: 6px; white-space: nowrap;
        }}
        .ips-coastal-pill-red {{ background: #fee2e2; color: #b91c1c; }}
        .ips-coastal-pill-orange {{ background: #ffedd5; color: #c2410c; }}
        .ips-coastal-pill-blue {{ background: #dbeafe; color: #1d4ed8; }}
        .ips-coastal-pill-green {{ background: #dcfce7; color: #166534; }}

        /* Aging */
        .ips-coastal-aging-row {{
          display: grid;
          grid-template-columns: 5.5rem 1fr 5.5rem;
          gap: 0.65rem;
          align-items: center;
          margin-bottom: 0.55rem;
          font-size: 0.78rem;
          color: #334155;
        }}
        .ips-coastal-aging-bar {{
          height: 10px; background: #eef2f7; border-radius: 99px; overflow: hidden;
        }}
        .ips-coastal-aging-fill {{ height: 100%; background: #3b82f6; border-radius: 99px; }}
        .ips-coastal-aging-amt {{ text-align: right; font-weight: 600; color: #0f172a; }}

        /* Status pills in table area */
        .ips-status-pill {{
          display: inline-block;
          padding: 0.15rem 0.55rem;
          border-radius: 99px;
          font-size: 0.68rem;
          font-weight: 700;
          white-space: nowrap;
        }}

        /* Quick actions */
        section[data-testid="stMain"]:has(.{c}) .ips-qa-grid div.stButton > button {{
          background: #fff !important;
          border: 1px solid #e5eaf2 !important;
          border-radius: 12px !important;
          min-height: 4.5rem !important;
          height: 4.5rem !important;
          color: #334155 !important;
          font-size: 0.72rem !important;
          font-weight: 600 !important;
          box-shadow: 0 1px 2px rgba(16,24,40,.04) !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-qa-grid div.stButton > button:hover {{
          border-color: #bfdbfe !important;
          background: #ffffff !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-qa-grid div.stButton > button p {{
          font-size: 0.72rem !important;
        }}

        .ips-coastal-date-pill {{
          font-size: 0.8rem;
          font-weight: 600;
          color: #334155;
          background: #fff;
          border: 1px solid #e5eaf2;
          border-radius: 10px;
          padding: 0.45rem 0.75rem;
          margin: 0 0 0.35rem;
          text-align: right;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-view-all-wrap div.stButton > button {{
          background: #ffffff !important;
          border: none !important;
          color: #2563eb !important;
          font-size: 0.78rem !important;
          font-weight: 600 !important;
          box-shadow: none !important;
          min-height: 1.75rem !important;
          padding: 0 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-view-all-wrap div.stButton > button:hover {{
          text-decoration: underline !important;
          background: #ffffff !important;
        }}

        /* Date / customize controls */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-controls [data-testid="stDateInput"] > div {{
          border-radius: 10px !important;
          border: 1px solid #e5eaf2 !important;
          background: #fff !important;
          min-height: 2.5rem !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-controls div.stButton > button {{
          border-radius: 10px !important;
          border: 1px solid #e5eaf2 !important;
          background: #fff !important;
          color: #334155 !important;
          font-weight: 600 !important;
        }}

        /* Donut legend */
        .ips-coastal-donut-legend {{
          font-size: 0.75rem;
          color: #334155;
          padding: 0.35rem 0;
          border-bottom: 1px solid #f8fafc;
        }}
        .ips-coastal-donut-legend > div {{
          display: flex;
          justify-content: space-between;
          gap: 0.5rem;
        }}

        /* Jobs table */
        .ips-coastal-jobs-table {{
          width: 100%;
          border-collapse: collapse;
          font-size: 0.74rem;
        }}
        .ips-coastal-jobs-table th {{
          text-align: left;
          color: #94a3b8;
          font-weight: 600;
          font-size: 0.68rem;
          letter-spacing: 0.04em;
          padding: 0.35rem 0.5rem 0.55rem;
          border-bottom: 1px solid #e8edf4;
        }}
        .ips-coastal-jobs-table td {{
          padding: 0.55rem 0.5rem;
          border-bottom: 1px solid #f1f5f9;
          color: #334155;
          vertical-align: middle;
        }}
        .ips-coastal-progress-wrap {{
          display: flex;
          align-items: center;
          gap: 0.45rem;
          min-width: 5.5rem;
        }}
        .ips-coastal-progress-bar {{
          flex: 1;
          height: 6px;
          background: #e8edf4;
          border-radius: 99px;
          overflow: hidden;
        }}
        .ips-coastal-progress-bar > div {{
          height: 100%;
          background: #2563eb;
          border-radius: 99px;
        }}
        .ips-coastal-progress-wrap > span {{
          font-size: 0.68rem;
          font-weight: 600;
          color: #64748b;
          min-width: 2rem;
        }}

        /* Chart legend */
        .ips-coastal-chart-legend {{
          display: flex; gap: 1rem; justify-content: flex-end;
          font-size: 0.72rem; color: #64748b; margin-bottom: 0.35rem;
        }}
        .ips-coastal-legend-dot {{
          display: inline-block; width: 10px; height: 10px;
          border-radius: 2px; margin-right: 0.35rem; vertical-align: middle;
        }}

        .ips-coastal-alerts {{
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin: 0.15rem 0 0.35rem;
        }}
        .ips-coastal-alert-chip {{
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          font-size: 0.75rem;
          font-weight: 600;
          padding: 0.35rem 0.65rem;
          border-radius: 8px;
          border: 1px solid #e5eaf2;
          background: #fff;
        }}
        .ips-coastal-alert-chip.warn {{
          border-color: #fed7aa;
          background: #fff7ed;
          color: #c2410c;
        }}
        .ips-coastal-alert-chip.info {{
          border-color: #bfdbfe;
          background: #eff6ff;
          color: #1d4ed8;
        }}

        /* ============================================================
           SCOPED TEXT OVERRIDES
           Wins over global "section .stMarkdown p { color !important }"
           by using the :has(.{c}) ancestor selector (higher specificity).
        ============================================================ */

        /* Dashboard header */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-dash-title,
        section[data-testid="stMain"]:has(.{c}) .stMarkdown .ips-coastal-dash-title {{
          color: #0f172a !important;
          font-size: 1.65rem !important;
          font-weight: 700 !important;
          line-height: 1.2 !important;
          margin: 0 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-dash-sub,
        section[data-testid="stMain"]:has(.{c}) .stMarkdown .ips-coastal-dash-sub {{
          color: #64748b !important;
          font-size: 0.9rem !important;
          font-weight: 400 !important;
          margin: 0.15rem 0 0 !important;
        }}

        /* KPI card labels, values, trends */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-kpi-label {{
          color: #64748b !important;
          font-size: 0.78rem !important;
          font-weight: 500 !important;
          margin: 0 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-kpi-value {{
          color: #0f172a !important;
          font-size: 1.38rem !important;
          font-weight: 700 !important;
          letter-spacing: -0.02em !important;
          line-height: 1.15 !important;
          margin: 0.2rem 0 0 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-kpi-trend {{
          font-size: 0.72rem !important;
          font-weight: 600 !important;
          margin: 0 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-kpi-trend.up {{
          color: #059669 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-kpi-trend.down {{
          color: #dc2626 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-kpi-trend.bad-up {{
          color: #dc2626 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-kpi-trend.good-down {{
          color: #059669 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-kpi-trend.flat {{
          color: #94a3b8 !important;
        }}

        /* Card headers */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-card-title {{
          color: #0f172a !important;
          font-size: 0.92rem !important;
          font-weight: 700 !important;
          margin: 0 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-view-link {{
          color: #2563eb !important;
          font-size: 0.78rem !important;
          font-weight: 600 !important;
        }}

        /* Activity rows */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-act-title {{
          color: #0f172a !important;
          font-size: 0.8rem !important;
          font-weight: 600 !important;
          margin: 0 !important;
          line-height: 1.3 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-act-desc {{
          color: #94a3b8 !important;
          font-size: 0.72rem !important;
          font-weight: 400 !important;
          margin: 0.12rem 0 0 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-act-time {{
          color: #94a3b8 !important;
          font-size: 0.72rem !important;
          font-weight: 400 !important;
        }}

        /* Deadline rows */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-deadline-title {{
          color: #0f172a !important;
          font-size: 0.8rem !important;
          font-weight: 600 !important;
          margin: 0 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-deadline-date {{
          color: #94a3b8 !important;
          font-size: 0.72rem !important;
          font-weight: 400 !important;
          margin: 0.1rem 0 0 !important;
        }}

        /* Aging rows */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-aging-row {{
          color: #334155 !important;
          font-size: 0.78rem !important;
          font-weight: 500 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-aging-amt {{
          color: #0f172a !important;
          font-weight: 600 !important;
        }}

        /* Pills */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-pill-red {{
          background: #fee2e2 !important;
          color: #b91c1c !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-pill-orange {{
          background: #ffedd5 !important;
          color: #c2410c !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-pill-blue {{
          background: #dbeafe !important;
          color: #1d4ed8 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-pill-green {{
          background: #dcfce7 !important;
          color: #166534 !important;
        }}

        /* Chart legend & date pill */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-chart-legend,
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-chart-legend span {{
          color: #64748b !important;
          font-size: 0.72rem !important;
          font-weight: 500 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-date-pill {{
          color: #334155 !important;
          font-size: 0.8rem !important;
          font-weight: 600 !important;
        }}

        /* Donut legend text */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-donut-legend,
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-donut-legend span {{
          color: #334155 !important;
          font-size: 0.75rem !important;
          font-weight: 400 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-donut-legend strong {{
          color: #0f172a !important;
          font-weight: 700 !important;
        }}

        /* Jobs table */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-jobs-table th {{
          color: #94a3b8 !important;
          font-weight: 600 !important;
          font-size: 0.68rem !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-jobs-table td {{
          color: #334155 !important;
          font-size: 0.74rem !important;
          font-weight: 400 !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-progress-wrap > span {{
          color: #64748b !important;
          font-size: 0.68rem !important;
          font-weight: 600 !important;
        }}

        /* Alert chips */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-alert-chip.warn {{
          color: #c2410c !important;
        }}
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-alert-chip.info {{
          color: #1d4ed8 !important;
        }}

        /* Sidebar text overrides */
        .stApp:has(.{c}) .ips-coastal-sidebar-title {{
          color: #0f172a !important;
          font-size: 0.95rem !important;
          font-weight: 800 !important;
        }}
        .stApp:has(.{c}) .ips-coastal-sidebar-sub {{
          color: #64748b !important;
          font-size: 0.62rem !important;
          font-weight: 700 !important;
        }}
        .stApp:has(.{c}) .ips-coastal-profile-name {{
          color: #0f172a !important;
          font-weight: 700 !important;
          margin: 0 !important;
        }}
        .stApp:has(.{c}) .ips-coastal-profile-role {{
          color: #64748b !important;
          font-size: 0.75rem !important;
          font-weight: 400 !important;
          margin: 0 !important;
        }}
        .stApp:has(.{c}) .ips-coastal-collapse-hint {{
          color: #94a3b8 !important;
          font-size: 0.72rem !important;
          font-weight: 400 !important;
        }}

        /* Quick-action button text */
        section[data-testid="stMain"]:has(.{c}) .ips-qa-grid div.stButton > button p {{
          color: #334155 !important;
          font-size: 0.72rem !important;
          font-weight: 600 !important;
        }}

        /* ── Additional polish ── */

        /* KPI card background must stay white even when stVerticalBlock is #f8fafc */
        section[data-testid="stMain"]:has(.{c}) .ips-coastal-kpi {{
          background: #ffffff !important;
        }}

        /* Ensure chart area backgrounds stay white */
        section[data-testid="stMain"]:has(.{c}) .stPlotlyChart,
        section[data-testid="stMain"]:has(.{c}) .stPyplotChart {{
          background: transparent !important;
        }}

        @media (max-width: 1100px) {{
          .ips-coastal-kpi-value {{ font-size: 1.15rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
