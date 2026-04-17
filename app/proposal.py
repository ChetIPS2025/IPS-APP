from __future__ import annotations

import html
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


def _paragraph_heading_level(paragraph) -> int:
    """Map Word paragraph style to a rough heading level for HTML preview."""
    try:
        name = (paragraph.style.name or "").strip().lower()
    except Exception:
        name = ""
    if name in ("title",):
        return 1
    if name in ("subtitle",):
        return 2
    if name.startswith("heading"):
        parts = name.split()
        if len(parts) >= 2 and parts[1].isdigit():
            return min(max(int(parts[1]), 1), 4)
        return 2
    return 0


def _iter_document_body_blocks(document: Document):
    """Yield (``'p'``, paragraph) or (``'t'``, table) in document body order."""
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    body = document.element.body
    for el in body.iterchildren():
        if isinstance(el, CT_P):
            yield "p", Paragraph(el, document)
        elif isinstance(el, CT_Tbl):
            yield "t", Table(el, document)


def _cell_plain_text(cell) -> str:
    parts: list[str] = []
    for p in cell.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    return " ".join(parts).strip()


def _table_to_preview_html(table) -> str:
    rows_out: list[list[str]] = []
    for row in table.rows:
        row_cells = [_cell_plain_text(c) for c in row.cells]
        if any(row_cells):
            rows_out.append(row_cells)
    if not rows_out:
        return ""
    ncol = max(len(r) for r in rows_out)
    trs: list[str] = []
    for r in rows_out:
        padded = r + [""] * (ncol - len(r))
        tds = "".join(
            f"<td style='border:1px solid #ddd;padding:0.35rem 0.45rem;vertical-align:top;'>{html.escape(c)}</td>"
            for c in padded
        )
        trs.append(f"<tr>{tds}</tr>")
    return (
        "<table style='width:100%;border-collapse:collapse;margin:0.55em 0;font-size:0.95em;'>"
        "<tbody>" + "".join(trs) + "</tbody></table>"
    )


def _first_header_preview_html(document: Document) -> str:
    """Optional letterhead lines from the first section header (text only)."""
    try:
        hdr = document.sections[0].header
    except Exception:
        return ""
    lines: list[str] = []
    for p in hdr.paragraphs:
        t = (p.text or "").strip()
        if t:
            lines.append(html.escape(t))
    if not lines:
        return ""
    inner = "<br/>".join(lines)
    return (
        f'<div style="font-size:0.88em;color:#444;line-height:1.35;margin-bottom:0.75rem;padding-bottom:0.55rem;'
        f'border-bottom:1px solid #e6e6e6;">{inner}</div>'
    )


def filled_proposal_docx_to_preview_html(docx_bytes: bytes) -> str:
    """
    Build a readable HTML preview from the **filled** proposal .docx (same bytes as download).

    Uses ``python-docx`` body order (paragraphs + tables). No PDF/LibreOffice. Best-effort only:
    complex shapes, text boxes, and heavy formatting may not match Word exactly.
    """
    doc = Document(BytesIO(docx_bytes))
    chunks: list[str] = []
    hf = _first_header_preview_html(doc)
    if hf:
        chunks.append(hf)
    for kind, block in _iter_document_body_blocks(doc):
        if kind == "p":
            text = (block.text or "").replace("\x07", "").strip()
            if not text:
                continue
            esc = html.escape(text).replace("\n", "<br/>")
            lev = _paragraph_heading_level(block)
            if lev == 1:
                chunks.append(f'<h3 style="margin:0.55em 0 0.25em 0;font-weight:650;">{esc}</h3>')
            elif lev == 2:
                chunks.append(f'<h4 style="margin:0.45em 0 0.2em 0;font-weight:600;">{esc}</h4>')
            elif lev >= 3:
                chunks.append(f'<h5 style="margin:0.35em 0 0.15em 0;font-weight:600;">{esc}</h5>')
            else:
                chunks.append(f'<p style="margin:0.22em 0;line-height:1.52;">{esc}</p>')
        else:
            th = _table_to_preview_html(block)
            if th:
                chunks.append(th)
    inner = "\n".join(chunks)
    if not inner.strip():
        return ""
    return (
        '<div class="ips-proposal-docx-preview" style="max-height:min(720px,78vh);overflow:auto;'
        "padding:1rem 1.15rem;border:1px solid #e4e4e4;border-radius:10px;background:#fafafa;"
        'font-family:Georgia,\"Times New Roman\",serif;">'
        f"{inner}</div>"
    )


def proposal_values_preview_html(vals: dict[str, str]) -> str:
    """Field-based preview (same placeholder map as the DOCX) when body extraction is sparse."""
    order: tuple[tuple[str, str], ...] = (
        ("JOB_NAME", "Job / title"),
        ("QUOTE_NUMBER", "Quote #"),
        ("CUSTOMER_NAME", "Customer"),
        ("CUSTOMER_LOCATION", "Location"),
        ("CONTACT_NAME", "Contact"),
        ("PROPOSAL_AMOUNT", "Proposal amount"),
        ("DATE", "Date"),
        ("PREPARED_BY", "Prepared by"),
        ("PREPARED_BY_PHONE", "Phone"),
        ("SCOPE_OF_WORK", "Scope of work"),
    )
    trs: list[str] = []
    for key, label in order:
        raw = _s(vals.get(key, ""))
        if not raw and key != "SCOPE_OF_WORK":
            continue
        lab_esc = html.escape(label)
        val_esc = html.escape(raw) if raw else "—"
        trs.append(
            "<tr>"
            f"<td style='padding:0.4rem 0.65rem;font-weight:600;vertical-align:top;width:10.5rem;"
            "border-bottom:1px solid #eee;'>{lab_esc}</td>"
            f"<td style='padding:0.4rem 0.65rem;vertical-align:top;border-bottom:1px solid #eee;"
            "white-space:pre-wrap;'>{val_esc}</td>"
            "</tr>"
        )
    body = "".join(trs)
    return (
        '<div class="ips-proposal-fields-preview" style="max-height:min(720px,78vh);overflow:auto;'
        "padding:1rem 1.1rem;border:1px solid #e4e4e4;border-radius:10px;background:#fafafa;"
        'font-size:0.96em;font-family:system-ui,-apple-system,sans-serif;">'
        f"<table style='width:100%;border-collapse:collapse;'>{body}</table></div>"
    )


def proposal_combined_preview_html(docx_bytes: bytes | None, *, fallback_vals: dict[str, str]) -> str:
    """
    Prefer HTML extracted from the filled DOCX; if that is empty, show the mapped key-field table.

    ``fallback_vals`` should be :func:`proposal_values` for the same estimate context as the DOCX.
    """
    if docx_bytes:
        doc_html = filled_proposal_docx_to_preview_html(docx_bytes)
        plain = re.sub(r"<[^>]+>", "", doc_html or "")
        if plain.strip():
            return doc_html
    return proposal_values_preview_html(fallback_vals)


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
