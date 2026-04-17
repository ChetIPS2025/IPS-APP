from __future__ import annotations

import re
import subprocess
import tempfile
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from datetime import datetime
from pathlib import Path

from docx import Document

_D0 = Decimal("0")
_CENT = Decimal("0.01")

# Canonical Word tokens ({{TOKEN}}) after normalization + value fill.
_DOCX_CANONICAL_TOKENS: tuple[str, ...] = (
    "JOB_NAME",
    "QUOTE_NUMBER",
    "CUSTOMER_NAME",
    "CUSTOMER_LOCATION",
    "CONTACT_NAME",
    "PROPOSAL_AMOUNT",
    "SCOPE_OF_WORK",
    "PREPARED_BY",
    "DATE",
    "PREPARED_BY_PHONE",
)

ESTIMATE_PROPOSAL_TEMPLATE_FILENAME = "estimate_template_autofill_logo_updated.docx"

# Shown when LibreOffice / Word PDF conversion is not available (UI may prepend context).
PROPOSAL_PDF_UNAVAILABLE_MSG = (
    "PDF export is not available in this environment (Word could not be converted to PDF). "
    "You can still use **Download Word Proposal** and save or print to PDF locally. "
    "To enable server PDFs, install **LibreOffice** so `soffice` is on PATH, or on Windows use **Microsoft Word** with the **docx2pdf** package."
)


def _dec(v) -> Decimal:
    if v is None or v == "":
        return _D0
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _q2(v) -> Decimal:
    return _dec(v).quantize(_CENT, rounding=ROUND_HALF_UP)


def _money(v) -> str:
    """Format as $X,XXX.XX (always two decimals)."""
    return f"${_q2(v):,.2f}"


def _s(v) -> str:
    """Safe string for placeholders; never None."""
    if v is None:
        return ""
    return str(v).strip() if isinstance(v, str) else str(v)


def _pdf_prepared_by(est: dict) -> str:
    try:
        from auth import current_profile

        prof = current_profile()
        name = _s(prof.get("full_name"))
        if name:
            return name
        email = _s(prof.get("email"))
        if email:
            return email
    except Exception:
        pass
    return _s(est.get("prepared_by_name") or est.get("prepared_by"))


def _proposal_prepared_by_display(est: dict) -> str:
    n = _s(est.get("prepared_by_name"))
    if n:
        return n
    return _pdf_prepared_by(est)


def proposal_values(
    est: dict,
    totals: dict,
    customer_name: str = "",
    job_name: str = "",
    *,
    customer_location: str = "",
    contact_name: str = "",
    prepared_by_phone: str = "",
) -> dict[str, str]:
    """
    Placeholder values for the estimate proposal DOCX (and PDF derived from it).

    Money: $X,XXX.XX. Date: full US month name. Missing fields -> empty string (or sensible default for title).
    """
    cust = _s(customer_name or est.get("customer_name"))
    pt = _money(totals.get("proposal_total", 0) or 0)
    prepared = _proposal_prepared_by_display(est)
    jn = _s(job_name or est.get("job_name"))
    if not jn:
        jn = "Project Quote"
    return {
        "JOB_NAME": jn,
        "QUOTE_NUMBER": _s(est.get("quote_number")),
        "CUSTOMER_NAME": cust,
        "CUSTOMER_LOCATION": _s(customer_location),
        "CONTACT_NAME": _s(contact_name),
        "PROPOSAL_AMOUNT": pt,
        "SCOPE_OF_WORK": _s(est.get("scope_of_work")),
        "DATE": datetime.now().strftime("%B %d, %Y"),
        "PREPARED_BY": _s(prepared),
        "PREPARED_BY_PHONE": _s(prepared_by_phone),
    }


def _default_estimate_proposal_template_path() -> Path:
    """IPS APP/assets/estimate_template_autofill_logo_updated.docx"""
    return Path(__file__).resolve().parents[1] / "assets" / ESTIMATE_PROPOSAL_TEMPLATE_FILENAME


def _resolve_proposal_template_bytes(
    template_bytes: bytes | None,
    template_path: str | None,
) -> bytes:
    """
    Order: session/uploaded bytes, explicit path, then packaged assets template.
    Raises FileNotFoundError if nothing usable is found.
    """
    if template_bytes:
        return template_bytes
    if template_path:
        p = Path(template_path)
        if p.is_file():
            return p.read_bytes()
    default = _default_estimate_proposal_template_path()
    if default.is_file():
        return default.read_bytes()
    raise FileNotFoundError(
        f"Proposal template not found. Add {ESTIMATE_PROPOSAL_TEMPLATE_FILENAME} under the project "
        f"**assets** folder ({default.parent}), or upload a .docx in the estimate editor."
    )


def _normalize_placeholder_tokens(text: str) -> str:
    if not text:
        return text
    s = text
    explicit: list[tuple[str, str]] = [
        (r"\{\{\s*Customer\s+Name\s*\}\}", "{{CUSTOMER_NAME}}"),
        (r"\{\{\s*Customer\s+Location\s*\}\}", "{{CUSTOMER_LOCATION}}"),
        (r"\{\{\s*Scope\s+of\s+Work\s*\}\}", "{{SCOPE_OF_WORK}}"),
        (r"\{\{\s*Job\s*Name\s*\}\}", "{{JOB_NAME}}"),
        (r"\{\{\s*Quote\s*Number\s*\}\}", "{{QUOTE_NUMBER}}"),
        (r"\{\{\s*Contact\s*Name\s*\}\}", "{{CONTACT_NAME}}"),
        (r"\{\{\s*Proposal\s*Amount\s*\}\}", "{{PROPOSAL_AMOUNT}}"),
        (r"\{\{\s*Prepared\s*By\s*\}\}", "{{PREPARED_BY}}"),
        (r"\{\{\s*Prepared\s*By\s*Phone\s*\}\}", "{{PREPARED_BY_PHONE}}"),
        (r"\{\{\s*Prepared\s*By\s*Phone\s*Number\s*\}\}", "{{PREPARED_BY_PHONE}}"),
        (r"\{\{\s*Date\s*\}\}", "{{DATE}}"),
    ]
    for pat, repl in explicit:
        s = re.sub(pat, repl, s, flags=re.IGNORECASE)

    for tok in _DOCX_CANONICAL_TOKENS:
        s = re.sub(
            r"\{\{\s*" + re.escape(tok) + r"\s*\}\}",
            "{{" + tok + "}}",
            s,
            flags=re.IGNORECASE,
        )
    return s


def _docx_placeholder_replacements(vals: dict[str, str]) -> dict[str, str]:
    repl: dict[str, str] = {}
    for k in _DOCX_CANONICAL_TOKENS:
        repl["{{" + k + "}}"] = _s(vals.get(k, ""))
    return repl


def _set_paragraph_text_merged(p, new_text: str) -> None:
    """Replace paragraph text while tolerating multi-run paragraphs (common in Word)."""
    if not p.runs:
        p.add_run(new_text)
        return
    p.runs[0].text = new_text
    for r in p.runs[1:]:
        r.text = ""


def _apply_to_paragraph_text(doc: Document, fn) -> None:
    def apply_paragraph(p) -> None:
        parts = [r.text for r in p.runs] if p.runs else []
        text = "".join(parts) if parts else (p.text or "")
        if not text:
            return
        new = fn(text)
        if new != text:
            _set_paragraph_text_merged(p, new)

    def walk_table(table) -> None:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    apply_paragraph(p)
                for tbl in cell.tables:
                    walk_table(tbl)

    for p in doc.paragraphs:
        apply_paragraph(p)
    for tbl in doc.tables:
        walk_table(tbl)

    for section in doc.sections:
        for part in (section.header, section.footer):
            for p in part.paragraphs:
                apply_paragraph(p)
            for tbl in getattr(part, "tables", []) or []:
                walk_table(tbl)


def _normalize_docx_placeholders(doc: Document) -> None:
    _apply_to_paragraph_text(doc, _normalize_placeholder_tokens)


def _replace_placeholders_doc(doc: Document, replacements: dict[str, str]) -> None:
    def replace(text: str) -> str:
        new = text
        for k, v in replacements.items():
            if k in new:
                new = new.replace(k, v)
        return new

    _apply_to_paragraph_text(doc, replace)


def _fill_proposal_docx_from_bytes(raw: bytes, vals: dict[str, str]) -> bytes:
    repl = _docx_placeholder_replacements(vals)
    doc = Document(BytesIO(raw))
    _normalize_docx_placeholders(doc)
    _replace_placeholders_doc(doc, repl)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()


def _convert_docx_bytes_to_pdf(docx_bytes: bytes) -> bytes:
    """
    Convert filled .docx to PDF using LibreOffice/soffice (any OS) or docx2pdf (Windows + Word).
    """
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        src = tdir / "proposal.docx"
        src.write_bytes(docx_bytes)
        pdf_out = tdir / "proposal.pdf"
        for exe in ("soffice", "libreoffice"):
            try:
                subprocess.run(
                    [exe, "--headless", "--convert-to", "pdf", "--outdir", str(tdir), str(src)],
                    check=True,
                    timeout=180,
                    capture_output=True,
                    text=True,
                )
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                continue
            if pdf_out.is_file():
                return pdf_out.read_bytes()

        try:
            from docx2pdf import convert  # type: ignore

            convert(str(src.resolve()))
            win_pdf = src.with_suffix(".pdf")
            if win_pdf.is_file():
                return win_pdf.read_bytes()
        except Exception:
            pass

    raise RuntimeError(
        "Could not convert the proposal Word file to PDF. Install **LibreOffice** (command `soffice` or "
        "`libreoffice` on PATH), or on Windows install **Microsoft Word** and run `pip install docx2pdf`."
    )


def try_convert_proposal_docx_to_pdf(docx_bytes: bytes) -> tuple[bytes | None, str]:
    """
    Convert a filled proposal .docx to PDF without raising.

    Returns ``(pdf_bytes, "")`` on success, or ``(None, short_user_message)`` on failure.
    """
    try:
        return _convert_docx_bytes_to_pdf(docx_bytes), ""
    except RuntimeError as e:
        msg = str(e).strip() or PROPOSAL_PDF_UNAVAILABLE_MSG
        return None, msg
    except Exception as e:
        return None, f"{PROPOSAL_PDF_UNAVAILABLE_MSG} ({type(e).__name__}: {e})"


def try_build_proposal_pdf(
    est: dict,
    totals: dict,
    customer_name: str = "",
    job_name: str = "",
    *,
    customer_location: str = "",
    contact_name: str = "",
    prepared_by_phone: str = "",
    template_path: str | None = None,
    template_bytes: bytes | None = None,
    docx_bytes: bytes | None = None,
) -> tuple[bytes | None, str]:
    """
    Build proposal PDF from the same filled DOCX pipeline, without raising on conversion failure.

    If ``docx_bytes`` is provided, skips rebuilding the DOCX (caller already built it).

    Returns ``(pdf_bytes, "")`` on success, or ``(None, error_message)`` if the Word file could not be
    built or PDF conversion failed. Word-only failures return a message about the template/build step.
    """
    if docx_bytes is None:
        try:
            docx_bytes = build_proposal_docx(
                est,
                totals,
                customer_name=customer_name,
                job_name=job_name,
                customer_location=customer_location,
                contact_name=contact_name,
                prepared_by_phone=prepared_by_phone,
                template_path=template_path,
                template_bytes=template_bytes,
            )
        except FileNotFoundError as e:
            return None, str(e)
        except Exception as e:
            return None, f"Could not build the Word proposal: {type(e).__name__}: {e}"

    pdf, err = try_convert_proposal_docx_to_pdf(docx_bytes)
    if pdf is None and not err:
        return None, PROPOSAL_PDF_UNAVAILABLE_MSG
    return pdf, err


def build_proposal_docx(
    est: dict,
    totals: dict,
    customer_name: str = "",
    job_name: str = "",
    *,
    customer_location: str = "",
    contact_name: str = "",
    prepared_by_phone: str = "",
    template_path: str | None = None,
    template_bytes: bytes | None = None,
) -> bytes:
    """
    Build the proposal .docx from **estimate_template_autofill_logo_updated.docx** (or uploaded bytes),
    replacing all {{PLACEHOLDER}} tokens. This is the only proposal layout.
    """
    vals = proposal_values(
        est,
        totals,
        customer_name=customer_name,
        job_name=job_name,
        customer_location=customer_location,
        contact_name=contact_name,
        prepared_by_phone=prepared_by_phone,
    )
    raw = _resolve_proposal_template_bytes(template_bytes, template_path)
    return _fill_proposal_docx_from_bytes(raw, vals)


def build_proposal_pdf(
    est: dict,
    totals: dict,
    customer_name: str = "",
    job_name: str = "",
    *,
    customer_location: str = "",
    contact_name: str = "",
    prepared_by_phone: str = "",
    template_path: str | None = None,
    template_bytes: bytes | None = None,
) -> bytes:
    """
    Build the proposal PDF from the **same** filled DOCX as downloads/preview (template + placeholders).

    Raises ``RuntimeError`` (or ``FileNotFoundError`` from the DOCX step) if PDF conversion is unavailable;
    for non-throwing behavior use :func:`try_build_proposal_pdf` or :func:`try_convert_proposal_docx_to_pdf`.
    """
    pdf, err = try_build_proposal_pdf(
        est,
        totals,
        customer_name=customer_name,
        job_name=job_name,
        customer_location=customer_location,
        contact_name=contact_name,
        prepared_by_phone=prepared_by_phone,
        template_path=template_path,
        template_bytes=template_bytes,
        docx_bytes=None,
    )
    if pdf is None:
        if err and "Proposal template not found" in err:
            raise FileNotFoundError(err)
        raise RuntimeError(err or PROPOSAL_PDF_UNAVAILABLE_MSG)
    return pdf
