"""Central IPS UI stylesheet injection — shared component library."""

from __future__ import annotations

import streamlit as st

IPS_UI_STYLES_KEY = "ips_ui_styles_v1"


def inject_ips_ui_styles() -> None:
    """Inject shared IPS UI styles once per session."""
    if st.session_state.get(IPS_UI_STYLES_KEY):
        return
    st.session_state[IPS_UI_STYLES_KEY] = True

    try:
        from app.styles import inject_global_css
    except ImportError:
        from styles import inject_global_css  # type: ignore
    inject_global_css()

    st.markdown(
        """
<style id="ips-ui-library-v1">
.ips-page-content {
  padding: 16px 22px 28px 22px;
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
}
.ips-toolbar {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 14px;
  margin: 0 0 14px 0;
  box-sizing: border-box;
  width: 100%;
}
.ips-toolbar-marker {
  display: none;
}
.st-key-ips_detail_header:has(.ips-detail-header-marker) {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 18px;
  margin: 0 0 12px 0;
}
.st-key-ips_action_toolbar:has(.ips-toolbar-marker) {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 14px;
  margin: 0 0 14px 0;
  box-sizing: border-box;
  width: 100%;
}
.st-key-ips_action_toolbar:has(.ips-toolbar-marker) [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  gap: 10px !important;
  flex-wrap: wrap !important;
}
.ips-metric-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 16px;
  min-height: 86px;
  box-sizing: border-box;
}
.ips-metric-card-accent {
  border-left: 3px solid #3158e6;
}
.ips-metric-card-label {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
}
.ips-metric-card-value {
  margin: 0.15rem 0 0;
  font-size: 1.35rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.2;
}
.ips-metric-card-delta {
  margin: 4px 0 0;
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
}
.ips-status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
  border: 1px solid transparent;
}
.ips-detail-header {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 18px;
  margin: 0 0 12px 0;
}
.ips-detail-header-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
}
.ips-detail-header-subtitle {
  margin: 4px 0 0;
  font-size: 0.8125rem;
  color: #64748b;
}
.ips-detail-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin-top: 12px;
}
.ips-detail-meta-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
}
.ips-detail-meta-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
}
.ips-detail-meta-value {
  margin-top: 2px;
  font-size: 0.875rem;
  font-weight: 600;
  color: #0f172a;
}
.ips-table {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  width: 100%;
  box-sizing: border-box;
}
.ips-table-scroll {
  overflow-x: auto;
  width: 100%;
}
.ips-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}
.ips-mobile-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  width: 100%;
}
@media (max-width: 768px) {
  .ips-page-content {
    padding: 12px 14px 20px 14px;
  }
  .ips-toolbar {
    padding: 8px 10px;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


__all__ = ["inject_ips_ui_styles", "IPS_UI_STYLES_KEY"]
