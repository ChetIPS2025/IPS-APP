"""Jobs list native navigation links."""

from __future__ import annotations

from urllib.parse import urlencode

_JOB_DETAIL_QUERY_KEY = "job_detail"
_JOB_TAB_QUERY_KEY = "job_tab"
_NAV_QUERY_KEY = "ips_nav"


def job_detail_query_key() -> str:
    return _JOB_DETAIL_QUERY_KEY


def job_detail_href(job_id: str, *, tab: str = "") -> str:
    """Same-app URL to open Job Details (?ips_nav=jobs&job_detail=<id>)."""
    jid = str(job_id or "").strip()
    params: dict[str, str] = {_NAV_QUERY_KEY: "jobs", _JOB_DETAIL_QUERY_KEY: jid}
    tab_val = str(tab or "").strip()
    if tab_val:
        params[_JOB_TAB_QUERY_KEY] = tab_val
    return "?" + urlencode(params)
