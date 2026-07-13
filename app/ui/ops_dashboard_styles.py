"""Authoritative CSS for the IPS Operations Dashboard layout."""

from __future__ import annotations

import streamlit as st

IPS_OPS_DASHBOARD_STYLES_KEY = "ips_ops_dashboard_styles_v32"


def inject_ops_dashboard_styles() -> None:
    """Inject operations dashboard layout styles once per session."""
    if st.session_state.get(IPS_OPS_DASHBOARD_STYLES_KEY):
        return
    st.session_state[IPS_OPS_DASHBOARD_STYLES_KEY] = True
    st.markdown(
        """
<style id="ips-ops-dashboard-v32">
.stApp:has(.ips-ops-dashboard-marker) section[data-testid="stMain"] {
  background: #f1f5f9 !important;
}
section[data-testid="stMain"]:has(.ips-ops-dashboard-marker) [data-testid="stElementContainer"]:has(style#ips-ops-dashboard-v32) {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}
.st-key-dashboard_root,
.st-key-dashboard_root * {
  box-sizing: border-box;
}
.st-key-dashboard_root {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  padding: 14px 16px 24px !important;
  margin: 0 !important;
  margin-left: 0 !important;
  transform: none !important;
  overflow: visible !important;
}
.st-key-dashboard_root [data-testid="stVerticalBlock"] {
  gap: 12px !important;
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}
.st-key-dashboard_root [data-testid="stElementContainer"] {
  margin: 0 !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
}

.dashboard-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  margin: 0 0 14px;
  padding: 0;
  overflow: visible;
  box-sizing: border-box;
}
.dashboard-header-left {
  flex: 1 1 auto;
  min-width: 0;
  overflow: visible;
}
.dashboard-header-right {
  flex: 0 0 auto;
  display: flex;
  align-items: flex-end;
  gap: 10px;
}
.dashboard-header h1,
.dashboard-header h2,
.dashboard-header p {
  margin-top: 0;
  overflow: visible;
}
.dashboard-header-greet {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
}
.dashboard-header-meta {
  margin: 0.35rem 0 0;
  font-size: 0.8125rem;
  color: #64748b;
  line-height: 1.35;
}

.dashboard-kpi-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
  margin: 0 0 10px;
  padding: 0;
}
.dashboard-kpi-card {
  position: relative;
  min-width: 0;
  min-height: 78px;
  height: auto;
  padding: 12px 14px;
  margin: 0;
  overflow: visible;
  box-sizing: border-box;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 11px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.55rem;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
  transition: box-shadow 0.15s ease, border-color 0.12s ease;
}
.dashboard-kpi-card:hover {
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.14);
  border-color: #bfdbfe;
}
.dashboard-kpi-grid .dashboard-kpi-card:nth-child(4) .dashboard-kpi-value {
  color: #ea580c;
}
.dashboard-kpi-grid .dashboard-kpi-card:nth-child(5) .dashboard-kpi-value,
.dashboard-kpi-grid .dashboard-kpi-card:nth-child(6) .dashboard-kpi-value {
  color: #15803d;
}
.dashboard-kpi-icon-ring {
  width: 2.25rem;
  height: 2.25rem;
  min-width: 2.25rem;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.65);
  flex-shrink: 0;
}
.dashboard-kpi-text {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.dashboard-kpi-value {
  font-size: 1.12rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  line-height: 1.15;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dashboard-kpi-label {
  font-size: 0.68rem;
  font-weight: 600;
  color: #64748b;
  margin: 0.1rem 0 0;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dashboard-value-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
  margin: 0 0 12px;
  padding: 0;
}
.dashboard-value-card {
  position: relative;
  min-width: 0;
  min-height: 72px;
  height: auto;
  padding: 12px 14px;
  margin: 0;
  box-sizing: border-box;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 11px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.55rem;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}
.dashboard-value-icon-ring {
  width: 2.25rem;
  height: 2.25rem;
  min-width: 2.25rem;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.65);
  flex-shrink: 0;
}
.dashboard-value-text {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.dashboard-value-amount {
  font-size: 1.12rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  line-height: 1.15;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dashboard-value-label {
  font-size: 0.68rem;
  font-weight: 600;
  color: #64748b;
  margin: 0.1rem 0 0;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dashboard-main-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: stretch;
  gap: 16px;
  width: 100%;
  margin: 0;
  padding: 0;
}
.dashboard-main-card {
  position: relative;
  min-width: 0;
  height: auto;
  min-height: 315px;
  padding: 16px;
  margin: 0;
  overflow: hidden;
  box-sizing: border-box;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 11px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
}
.dashboard-main-card .ips-dash-ops-panel-title {
  margin: 0 0 14px;
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.2;
  flex-shrink: 0;
}
.dashboard-main-card .ips-dash-status-list,
.dashboard-main-card .ips-dash-activity-list {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}
.dashboard-main-card .ips-dash-ops-panel-link {
  flex-shrink: 0;
  margin-top: 14px;
}
.ips-dash-status-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ips-dash-status-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ips-dash-status-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ips-dash-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  flex-shrink: 0;
}
.ips-dash-status-label {
  flex: 1 1 auto;
  font-size: 0.8125rem;
  font-weight: 600;
  color: #334155;
}
.ips-dash-status-count {
  font-size: 0.8125rem;
  font-weight: 800;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}
.ips-dash-status-track {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: #eef2f7;
  overflow: hidden;
}
.ips-dash-status-bar {
  height: 100%;
  border-radius: 999px;
  min-width: 4px;
  transition: width 0.2s ease;
}
.ips-dash-activity-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 180px;
}
.ips-dash-activity-item {
  display: grid;
  grid-template-columns: 30px 1fr auto;
  gap: 10px;
  align-items: center;
}
.ips-dash-activity-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  font-size: 0.95rem;
}
.ips-dash-activity-text {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.35;
  min-width: 0;
}
.ips-dash-activity-time {
  font-size: 0.75rem;
  font-weight: 600;
  color: #94a3b8;
  white-space: nowrap;
}
.ips-dash-activity-empty {
  margin: 0;
  font-size: 0.8125rem;
  color: #94a3b8;
  font-style: italic;
}
.ips-dash-ops-panel-link {
  display: inline-block;
  font-size: 0.8125rem;
  font-weight: 700;
  color: #2563eb;
  text-decoration: none;
}
.ips-dash-ops-panel-link:hover,
.ips-dash-ops-panel-link:focus {
  color: #1d4ed8;
  text-decoration: underline;
}

@media (max-width: 1500px) {
  .dashboard-kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 900px) {
  .dashboard-main-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 800px) {
  .dashboard-kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 700px) {
  .dashboard-value-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 500px) {
  .dashboard-kpi-grid {
    grid-template-columns: 1fr;
  }
  .st-key-dashboard_root {
    padding-left: 12px !important;
    padding-right: 12px !important;
  }
  .dashboard-header-greet {
    font-size: 1rem;
    word-break: break-word;
  }
  .dashboard-header-meta {
    word-break: break-word;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )
