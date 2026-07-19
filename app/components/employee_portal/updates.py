"""Employee Portal company updates cards and detail."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlencode

import streamlit as st

from app.components.company_updates_feed import _mark_dashboard_update_read
from app.services.employee_portal_detail_service import get_employee_portal_update_detail
from app.services.employee_portal_service import EmployeePortalContext
from app.ui.streamlit_perf import fragment, fragment_rerun
from app.utils.formatting import fmt_date

_NAV_QUERY = "ips_nav"
_UPDATE_QUERY = "portal_update"


def portal_update_query_key() -> str:
    return _UPDATE_QUERY


def portal_update_href(update_id: str) -> str:
    return "?" + urlencode({_NAV_QUERY: "employee_portal", _UPDATE_QUERY: str(update_id or "").strip()})


def _status_pill(label: str, tone: str = "neutral") -> str:
    text = html.escape(str(label or "—"))
    return f'<span class="ips-ep-status ips-ep-status-{tone}">{text}</span>'


def build_updates_cards_html(updates: list[dict[str, Any]]) -> str:
    if not updates:
        return ""
    parts: list[str] = []
    for row in updates:
        uid = str(row.get("id") or "")
        unread = bool(row.get("is_unread"))
        badge = _status_pill("New", "warn") if unread else _status_pill("Read", "neutral")
        title = html.escape(str(row.get("title") or "Untitled"))
        snippet = html.escape(str(row.get("snippet") or row.get("body") or "")[:140])
        posted = html.escape(fmt_date(str(row.get("date") or row.get("created_at") or "")[:10]))
        href = html.escape(portal_update_href(uid), quote=True)
        parts.append(
            f"""
<div class="ips-ep-card ips-ep-update-card">
  <div class="ips-ep-card-head"><strong><a class="ips-ep-open-link" href="{href}" target="_self">{title}</a></strong>{badge}</div>
  <p class="ips-ep-muted">{snippet}</p>
  <p class="ips-ep-meta">{posted}</p>
</div>
"""
        )
    return "".join(parts)


@fragment
def render_updates_section(ctx: EmployeePortalContext, updates: list[dict[str, Any]]) -> None:
    from app.perf_debug import perf_span

    st.markdown('<h3 class="ips-ep-section-title">Company Updates</h3>', unsafe_allow_html=True)
    if not updates:
        st.markdown('<p class="ips-ep-empty">No company updates right now.</p>', unsafe_allow_html=True)
        return
    with perf_span("employee_portal.cards_html"):
        st.markdown(build_updates_cards_html(updates), unsafe_allow_html=True)


def capture_portal_update_query(ctx: EmployeePortalContext) -> dict[str, Any] | None:
    uid = str(st.query_params.get(_UPDATE_QUERY) or "").strip()
    if not uid:
        return None
    from app.perf_debug import perf_span

    with perf_span("employee_portal.update_detail"):
        detail = get_employee_portal_update_detail(
            uid,
            employee_id=ctx.employee_id,
            role=ctx.role,
            user_id=ctx.user_id,
        )
    if detail:
        _mark_dashboard_update_read(uid)
    if _UPDATE_QUERY in st.query_params:
        del st.query_params[_UPDATE_QUERY]
    return detail


def render_update_detail(detail: dict[str, Any]) -> None:
    st.markdown(f"### {html.escape(str(detail.get('title') or 'Update'))}")
    st.markdown(str(detail.get("body") or ""))
    posted = fmt_date(str(detail.get("date") or detail.get("created_at") or "")[:10])
    if posted:
        st.caption(posted)
    if st.button("← Back to Dashboard", key="ep_update_back", use_container_width=True):
        fragment_rerun()


def render_update_detail_panel(detail: dict[str, Any] | None) -> bool:
    if not detail:
        st.error("This update is not available.")
        if st.button("← Back to Dashboard", key="ep_update_back_missing", use_container_width=True):
            return True
        return False
    render_update_detail(detail)
    return False
