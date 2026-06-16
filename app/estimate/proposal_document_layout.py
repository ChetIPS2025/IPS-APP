"""Shared proposal view model + Word-style HTML preview (matches export field order, no customer location)."""
from __future__ import annotations

import base64
import html
import mimetypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Keep in sync with ``proposal.COMPANY_LOGO_CANDIDATE_FILENAMES`` (same search order).
_LOGO_FILENAMES: tuple[str, ...] = (
    "company_logo.png",
    "company_logo.jpg",
    "company_logo.jpeg",
    "ips_logo_wide.png",
    "IPS LOGO WIDE.png",
)

_ESTIMATE_TEMPLATE = "estimate_template_autofill_logo_updated.docx"

# Default footer phone when estimator profile has none (IPS quote letterhead).
_DEFAULT_QUOTE_FOOTER_PHONE = "(337) 577-3944"


def _assets_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "assets"


def _fmt_money(v) -> str:
    from decimal import ROUND_HALF_UP, Decimal

    d0 = Decimal("0")
    cent = Decimal("0.01")

    def _dec(x) -> Decimal:
        if x is None or x == "":
            return d0
        if isinstance(x, Decimal):
            return x
        return Decimal(str(x))

    q = _dec(v).quantize(cent, rounding=ROUND_HALF_UP)
    return f"${q:,.2f}"


def _s(v) -> str:
    if v is None:
        return ""
    return str(v).strip() if isinstance(v, str) else str(v)


def _s_contact(v) -> str:
    s = _s(v)
    if not s:
        return ""
    if s.lower() in ("none", "null"):
        return ""
    return s


def _logo_data_uri() -> str | None:
    root = _assets_dir()
    for name in _LOGO_FILENAMES:
        p = root / name
        if not p.is_file():
            continue
        data = p.read_bytes()
        mime, _ = mimetypes.guess_type(p.name)
        if not mime:
            mime = "image/png"
        b64 = base64.standard_b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64}"
    return None


def _estimate_description_for_title(est: dict) -> str:
    """Prefer denormalized column, then ``estimate_json`` (same text as editor Estimate Description)."""
    ed = _s(est.get("estimate_description"))
    if ed:
        return ed
    ej = est.get("estimate_json")
    if isinstance(ej, dict):
        return _s(ej.get("estimate_description"))
    return ""


@dataclass(frozen=True)
class ProposalViewModel:
    """Canonical proposal fields shared by Word fill and HTML preview (excludes customer location)."""

    # Project line before en-dash Quote (maps to {{JOB_NAME}}): estimate description, else job name, else Project.
    job_title_token: str
    quote_number: str
    customer_name: str
    contact_name: str
    proposal_amount: str
    scope_of_work: str
    customer_responsibilities: str
    prepared_by: str
    prepared_by_phone: str
    date_display: str
    estimate_date_display: str
    expiration_display: str


def build_proposal_view_model(
    est: dict,
    totals: dict,
    *,
    customer_name: str,
    job_name: str,
    contact_name: str,
    prepared_by_phone: str,
) -> ProposalViewModel:
    """
    Build the canonical view model (same inputs as legacy ``proposal.proposal_values`` kwargs
    minus customer location).
    """
    from proposal import _proposal_prepared_by_display
    try:
        from app.services.proposal_pdf_service import _stored_estimate_price
    except ImportError:
        from services.proposal_pdf_service import _stored_estimate_price  # type: ignore

    cust = _s(customer_name or est.get("customer_name"))
    pt = _fmt_money(
        totals.get("proposal_total")
        or totals.get("customer_price")
        or totals.get("total")
        or _stored_estimate_price(est)
        or 0
    )
    prepared = _proposal_prepared_by_display(est)
    # Quote title line: Estimate Description – Quote (Word {{JOB_NAME}} – Quote); fall back to job name.
    desc = _estimate_description_for_title(est)
    jn = desc or _s(job_name or est.get("job_name"))
    if not jn:
        jn = "Project"
    job_title_token = jn
    phone = _s(prepared_by_phone)
    if not phone:
        phone = _DEFAULT_QUOTE_FOOTER_PHONE
    try:
        from app.services.estimate_expiration_service import (
            effective_expiration_date,
            estimate_date_for_expiration,
            format_proposal_long_date,
        )
    except ImportError:
        from services.estimate_expiration_service import (  # type: ignore
            effective_expiration_date,
            estimate_date_for_expiration,
            format_proposal_long_date,
        )
    est_d = estimate_date_for_expiration(est)
    exp_d = effective_expiration_date(est)
    return ProposalViewModel(
        job_title_token=job_title_token,
        quote_number=_s(est.get("quote_number")),
        customer_name=cust,
        contact_name=_s_contact(contact_name),
        proposal_amount=pt,
        scope_of_work=_s(est.get("scope_of_work")),
        customer_responsibilities=_s(est.get("customer_responsibilities")),
        prepared_by=_s(prepared),
        prepared_by_phone=phone,
        date_display=datetime.now().strftime("%B %d, %Y"),
        estimate_date_display=format_proposal_long_date(est_d),
        expiration_display=format_proposal_long_date(exp_d),
    )


def proposal_placeholder_map_from_view_model(vm: ProposalViewModel) -> dict[str, str]:
    """Map view model to ``{{TOKEN}}`` keys consumed by ``proposal.build_proposal_docx``."""
    return {
        "JOB_NAME": vm.job_title_token,
        "QUOTE_NUMBER": vm.quote_number,
        "CUSTOMER_NAME": vm.customer_name,
        "CONTACT_NAME": vm.contact_name,
        "PROPOSAL_AMOUNT": vm.proposal_amount,
        "SCOPE_OF_WORK": vm.scope_of_work,
        "CUSTOMER_RESPONSIBILITIES": vm.customer_responsibilities,
        "DATE": vm.date_display,
        "PREPARED_BY": vm.prepared_by,
        "PREPARED_BY_PHONE": vm.prepared_by_phone,
        "ESTIMATE_DATE": vm.estimate_date_display,
        "VALID_THROUGH": vm.expiration_display,
        "EXPIRATION_DATE": vm.expiration_display,
    }


def _esc_body(text: str) -> str:
    return html.escape(text or "", quote=False).replace("\n", "<br/>")


def render_proposal_preview_page_html(vm: ProposalViewModel | None) -> str:
    """
    Full preview shell (desk + letter page) with Word-aligned blocks.
    ``None`` renders the missing-template / empty model message inside the same chrome.
    """
    desk = '<div class="ips-proposal-preview-root ips-proposal-preview-desk">'
    page_open = '<div class="ips-proposal-preview-page ips-proposal-docx-preview ips-proposal-template-page ips-proposal-page">'
    page_close = "</div></div>"

    if vm is None:
        inner = (
            '<div class="ips-proposal-page-inner">'
            '<p class="ips-proposal-preview-error"><strong>No proposal preview available.</strong> '
            f"Confirm <strong>assets/{_ESTIMATE_TEMPLATE}</strong> is present and proposal fields are filled, "
            "then reopen the <strong>Proposal</strong> tab.</p></div>"
        )
        return f"{desk}{page_open}{inner}{page_close}"

    title_line = f"{html.escape(vm.job_title_token)} \u2013 Quote"
    qn = html.escape(vm.quote_number)
    attn = html.escape(vm.contact_name) if vm.contact_name else "\u2014"
    amt = html.escape(vm.proposal_amount)
    scope_html = _esc_body(vm.scope_of_work) or "\u2014"
    resp_body = _esc_body(vm.customer_responsibilities)
    prep = html.escape(vm.prepared_by)
    dt = html.escape(vm.date_display)
    est_dt = html.escape(vm.estimate_date_display) if vm.estimate_date_display else "\u2014"
    exp_dt = html.escape(vm.expiration_display) if vm.expiration_display else "\u2014"
    phone = html.escape(vm.prepared_by_phone)
    footer_contact = html.escape(vm.prepared_by)
    footer_phone = html.escape(vm.prepared_by_phone or _DEFAULT_QUOTE_FOOTER_PHONE)

    logo = _logo_data_uri()
    logo_block = (
        f'<div class="ips-ph-logo-wrap"><img class="ips-ph-logo-img" src="{logo}" alt="Industrial Plant Solutions" /></div>'
        if logo
        else '<div class="ips-ph-logo-missing"></div>'
    )

    resp_section = ""
    if resp_body:
        resp_section = (
            '<div class="ips-ph-section-spacer" aria-hidden="true"></div>'
            '<div class="ips-ph-resp-heading">Exclusions</div>'
            f'<div class="ips-ph-resp-body">{resp_body}</div>'
        )

    inner = f"""
<div class="ips-proposal-page-inner ips-quote-doc">
{logo_block}
<div class="proposal-header">
<div class="proposal-header-title">{title_line}</div>
<div class="proposal-header-subtitle"><span class="ips-ph-quote-lbl">Quote #:</span> {qn}</div>
</div>
<div class="ips-ph-customer-block">
<div class="ips-ph-attn-line">
  <span><span class="ips-ph-meta-k">Attn:</span> {attn}</span>
  <span class="ips-ph-quote-amt"><span class="ips-ph-meta-k">Quote Amt:</span> {amt}</span>
</div>
</div>
<div class="ips-ph-grow-block">
<div class="ips-ph-scope">{scope_html}</div>
{resp_section}
</div>
<div class="ips-ph-close-block">
<div class="ips-ph-prep-line"><span class="ips-ph-meta-k">Prepared By:</span> {prep}</div>
<div class="ips-ph-est-date-line"><span class="ips-ph-meta-k">Estimate Date:</span> {est_dt}</div>
<div class="ips-ph-exp-date-line"><span class="ips-ph-meta-k">Valid Through:</span> {exp_dt}</div>
<div class="ips-ph-date-line"><span class="ips-ph-meta-k">Date:</span> {dt}</div>
</div>
<div class="ips-ph-footer-rule" aria-hidden="true"></div>
<p class="ips-ph-footer">If you have any questions regarding this Quote, please contact {footer_contact} at {footer_phone}</p>
</div>
""".strip()
    return f"{desk}{page_open}{inner}{page_close}"
