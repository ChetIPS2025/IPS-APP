"""Employee Portal certification summaries and open action."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import urlencode

import streamlit as st

from app.services.certification_helpers import cert_status_pill_html
from app.services.employee_portal_detail_service import get_employee_certification_open_target
from app.services.employee_portal_service import EmployeePortalContext
from app.ui.streamlit_perf import fragment, fragment_rerun
from app.utils.formatting import fmt_date

_NAV_QUERY = "ips_nav"
_CERT_QUERY = "portal_certificate"


def portal_certificate_query_key() -> str:
    return _CERT_QUERY


def portal_certificate_href(certification_id: str) -> str:
    return "?" + urlencode({_NAV_QUERY: "employee_portal", _CERT_QUERY: str(certification_id or "").strip()})


def build_certifications_cards_html(certs: list[dict[str, Any]]) -> str:
    if not certs:
        return ""
    parts: list[str] = []
    for cert in certs:
        cid = str(cert.get("id") or "")
        name = html.escape(str(cert.get("cert_type") or "Certification"))
        exp_raw = str(cert.get("expiration_date") or "")[:10]
        exp = html.escape(fmt_date(exp_raw) if exp_raw else "No expiration")
        status = str(cert.get("status") or "Active")
        attach = " · Document attached" if cert.get("has_attachment") else ""
        href = html.escape(portal_certificate_href(cid), quote=True) if cert.get("has_attachment") else ""
        open_link = (
            f' <a class="ips-ep-open-link" href="{href}" target="_self">Open</a>' if href else ""
        )
        parts.append(
            f"""
<div class="ips-ep-card ips-ep-cert-card">
  <div class="ips-ep-card-head"><strong>{name}</strong>{cert_status_pill_html(status)}</div>
  <p class="ips-ep-meta">Expires: {exp}{html.escape(attach)}{open_link}</p>
</div>
"""
        )
    return "".join(parts)


@fragment
def render_certifications_section(ctx: EmployeePortalContext, certs: list[dict[str, Any]]) -> None:
    from app.perf_debug import perf_span

    st.markdown('<h3 class="ips-ep-section-title">My Certifications</h3>', unsafe_allow_html=True)
    if not certs:
        st.markdown('<p class="ips-ep-empty">No certifications on file.</p>', unsafe_allow_html=True)
        return
    with perf_span("employee_portal.cards_html"):
        st.markdown(build_certifications_cards_html(certs), unsafe_allow_html=True)


def capture_portal_certificate_query(ctx: EmployeePortalContext) -> None:
    cid = str(st.query_params.get(_CERT_QUERY) or "").strip()
    if not cid:
        return
    from app.perf_debug import perf_span

    with perf_span("employee_portal.cert_open"):
        result = get_employee_certification_open_target(cid, employee_id=ctx.employee_id)
    if _CERT_QUERY in st.query_params:
        del st.query_params[_CERT_QUERY]
    if not result.ok:
        st.info(str(result.error or "Could not open this certification."))
        return
    data = result.data if isinstance(result.data, dict) else {}
    url = str(data.get("url") or "").strip()
    if url:
        st.link_button("Open certificate document", url, use_container_width=True)
    if st.button("Close", key="ep_cert_close", use_container_width=True):
        fragment_rerun()
