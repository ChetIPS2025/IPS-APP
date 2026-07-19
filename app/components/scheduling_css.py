"""Scheduling module CSS."""

from __future__ import annotations

import streamlit as st

from app.ui.css_inject import inject_css_once

SCHEDULING_CSS = """
.st-key-scheduling_page_wrap {
  min-width: 0;
}
.ips-scheduling-week-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(140px, 1fr));
  gap: 0.5rem;
  overflow-x: auto;
  padding-bottom: 0.5rem;
}
.ips-scheduling-day-col {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  min-height: 180px;
  padding: 0.45rem;
}
.ips-scheduling-day-head {
  font-size: 0.72rem;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.35rem;
}
.ips-scheduling-day-date {
  font-size: 0.85rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.45rem;
}
.ips-scheduling-event-card {
  display: block;
  width: 100%;
  text-align: left;
  background: #f8fafc;
  border: 1px solid #dbeafe;
  border-left: 3px solid #2563eb;
  border-radius: 8px;
  padding: 0.4rem 0.45rem;
  margin-bottom: 0.35rem;
  cursor: pointer;
  font-family: inherit;
}
.ips-scheduling-event-card.status-confirmed { border-left-color: #059669; }
.ips-scheduling-event-card.status-in_progress { border-left-color: #d97706; }
.ips-scheduling-event-card.status-cancelled { border-left-color: #94a3b8; opacity: 0.75; }
.ips-scheduling-event-card.has-conflict { border-color: #fca5a5; background: #fff7ed; }
.ips-scheduling-event-title {
  font-size: 0.78rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.25;
}
.ips-scheduling-event-meta {
  font-size: 0.7rem;
  color: #64748b;
  line-height: 1.3;
  margin-top: 0.15rem;
}
.ips-scheduling-conflict-icon {
  color: #dc2626;
  font-weight: 800;
}
.ips-scheduling-crew-table-wrap {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
}
.ips-scheduling-crew-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 960px;
}
.ips-scheduling-crew-table th,
.ips-scheduling-crew-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 0.45rem 0.5rem;
  font-size: 0.78rem;
  vertical-align: top;
}
.ips-scheduling-crew-table th {
  background: #f8fafc;
  font-weight: 800;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.ips-scheduling-day-cell-btn {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  font: inherit;
  color: #2563eb;
}
@media (max-width: 900px) {
  .ips-scheduling-week-grid {
    grid-template-columns: repeat(7, minmax(120px, 1fr));
  }
}
"""


def inject_scheduling_css() -> None:
    inject_css_once("ips-scheduling-css-v1")
    with st.sidebar:
        st.markdown(
            f'<style id="ips-scheduling-css-v1">\n{SCHEDULING_CSS}\n</style>',
            unsafe_allow_html=True,
        )
