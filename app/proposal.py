from __future__ import annotations

from io import BytesIO
from datetime import datetime
from textwrap import wrap
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as pdf_canvas

IPS_BLUE = (46, 102, 165)
IPS_DARK = (20, 20, 20)
IPS_GRAY = (140, 140, 140)

# IPS Quote PDF (matches unified quote layout; DOCX path unchanged)
PDF_QUOTE_OPENING = (
    "Industrial Plant Solutions, LLC (IPS) proposes to perform the following scope of work..."
)

IPS_QUOTE_CONTACT_LINES = (
    "Industrial Plant Solutions, LLC",
    "For questions regarding this quote, please contact IPS.",
)

# Tighter vertical rhythm (IPS quote letterhead)
PDF_PAGE_TOP = 0.48 * inch
PDF_BAR_H = 0.44 * inch
PDF_BAR_PAD = 0.05 * inch
PDF_AFTER_BLUE_BAR = 0.12 * inch
PDF_ATTN_ROW = 0.14 * inch
PDF_AFTER_RULE = 0.20 * inch
PDF_BODY_LINE = 0.118 * inch
PDF_AFTER_OPENING = 0.10 * inch
PDF_SECTION_GAP = 0.10 * inch
PDF_TITLE_TO_BODY = 0.14 * inch
PDF_AFTER_SECTION_BODY = 0.035 * inch
PDF_EMPTY_SECTION_TAIL = 0.045 * inch
PDF_FOOTER_TOP_PAD = 0.08 * inch
PDF_FOOTER_LINE = 0.13 * inch
PDF_CONTACT_LINE = 0.12 * inch


def _find_logo() -> Path | None:
    search_paths = [
        Path(__file__).resolve().parents[1] / "assets" / "ips_logo.png",
        Path(__file__).resolve().parents[1] / "assets" / "IPS LOGO.png",
        Path(__file__).resolve().parents[1] / "assets" / "ips_logo.jpg",
        Path(__file__).resolve().parents[1] / "assets" / "ips_logo.jpeg",
        Path(__file__).resolve().parents[1] / "assets" / "ips_logo.webp",
    ]
    for p in search_paths:
        if p.exists():
            return p
    return None


def proposal_values(est: dict, totals: dict, customer_name: str = "", job_name: str = "") -> dict:
    return {
        "JOB_NAME": job_name or est.get("job_name", "") or "Project Quote",
        "QUOTE_NUMBER": est.get("quote_number", ""),
        "CUSTOMER": customer_name or est.get("customer_name", "") or "",
        "TOTAL": f"${float(totals.get('proposal_total', 0) or 0):,.2f}",
        "DATE": datetime.now().strftime("%m/%d/%Y"),
        "SCOPE_OF_WORK": est.get("scope_of_work", ""),
        "EXCLUSIONS": est.get("exclusions", ""),
        "ADDITIONAL_CHARGES": est.get("additional_charges", ""),
        "CUSTOMER_RESPONSIBILITIES": est.get("customer_responsibilities", ""),
        "MATERIALS_TOTAL": f"${float(totals.get('material_sell_basis', 0) or 0):,.2f}",
        "LABOR_TOTAL": f"${float(totals.get('labor_total', 0) or 0):,.2f}",
        "EQUIPMENT_TOTAL": f"${float(totals.get('equipment_total', 0) or 0):,.2f}",
        "TRAVEL_TOTAL": f"${float(totals.get('travel_total', 0) or 0):,.2f}",
        "FINAL_BID": f"${float(totals.get('final_bid', 0) or 0):,.2f}",
    }


def _replace_placeholders_doc(doc, replacements: dict):
    for paragraph in doc.paragraphs:
        for key, value in replacements.items():
            if key in paragraph.text:
                paragraph.text = paragraph.text.replace(key, str(value))
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for key, value in replacements.items():
                    if key in cell.text:
                        cell.text = cell.text.replace(key, str(value))


def _default_intro(vals: dict) -> str:
    return (
        f"Industrial Plant Solutions (IPS) proposes to perform the following scope of work for "
        f"{vals['JOB_NAME']}."
    )


def _clean_lines(text: str) -> list[str]:
    lines = []
    for raw in (text or "").splitlines():
        s = raw.strip()
        if s:
            lines.append(s)
    return lines


def _pdf_prepared_by(est: dict) -> str:
    """Prefer logged-in profile name/email when Streamlit session is available."""
    try:
        from auth import current_profile

        prof = current_profile()
        name = str(prof.get("full_name") or "").strip()
        if name:
            return name
        email = str(prof.get("email") or "").strip()
        if email:
            return email
    except Exception:
        pass
    return str(est.get("prepared_by") or est.get("prepared_by_name") or "").strip()


def _pdf_draw_wrapped(
    c: pdf_canvas.Canvas,
    text: str,
    *,
    left: float,
    right: float,
    y: float,
    height: float,
    font: str = "Times-Roman",
    size: int = 11,
    line_step: float | None = None,
) -> float:
    """Draw wrapped paragraph text; return updated y (baseline)."""
    step = line_step if line_step is not None else PDF_BODY_LINE
    chars_per_line = 96
    c.setFont(font, size)
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            y -= step * 0.5
            continue
        for sub in wrap(s, width=chars_per_line):
            if y < 0.75 * inch:
                c.showPage()
                y = height - 0.7 * inch
                c.setFont(font, size)
            c.drawString(left, y, sub)
            y -= step
    return y


def _pdf_draw_section(
    c: pdf_canvas.Canvas,
    title: str,
    body: str,
    *,
    left: float,
    right: float,
    y: float,
    height: float,
    section_gap: float,
) -> float:
    """Bold section title + plain body block(s). Empty body still draws the title."""
    if y < 1.0 * inch:
        c.showPage()
        y = height - 0.75 * inch

    y -= section_gap
    c.setFont("Times-Bold", 12)
    c.drawString(left, y, title)
    y -= PDF_TITLE_TO_BODY

    body_stripped = (body or "").strip()
    if not body_stripped:
        y -= PDF_EMPTY_SECTION_TAIL
        return y

    y = _pdf_draw_wrapped(
        c,
        body_stripped,
        left=left,
        right=right,
        y=y,
        height=height,
        font="Times-Roman",
        size=11,
        line_step=PDF_BODY_LINE,
    )
    y -= PDF_AFTER_SECTION_BODY
    return y


def build_proposal_docx(est: dict, totals: dict, customer_name: str = "", job_name: str = "", template_path: str | None = None) -> bytes:
    vals = proposal_values(est, totals, customer_name=customer_name, job_name=job_name)

    if template_path:
        try:
            doc = Document(template_path)
            replacements = {
                "{{JOB_NAME}}": vals["JOB_NAME"],
                "{{QUOTE_NUMBER}}": vals["QUOTE_NUMBER"],
                "{{CUSTOMER}}": vals["CUSTOMER"],
                "{{TOTAL}}": vals["TOTAL"],
                "{{DATE}}": vals["DATE"],
                "{{SCOPE_OF_WORK}}": vals["SCOPE_OF_WORK"],
                "{{EXCLUSIONS}}": vals["EXCLUSIONS"],
                "{{ADDITIONAL_CHARGES}}": vals["ADDITIONAL_CHARGES"],
                "{{CUSTOMER_RESPONSIBILITIES}}": vals["CUSTOMER_RESPONSIBILITIES"],
            }
            _replace_placeholders_doc(doc, replacements)
            bio = BytesIO()
            doc.save(bio)
            return bio.getvalue()
        except Exception:
            pass

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(0.35)
    sec.bottom_margin = Inches(0.45)
    sec.left_margin = Inches(0.55)
    sec.right_margin = Inches(0.55)

    logo = _find_logo()
    if logo:
        try:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.add_run().add_picture(str(logo), width=Inches(4.8))
        except Exception:
            pass

    # Blue title bar
    title_tbl = doc.add_table(rows=2, cols=1)
    title_tbl.autofit = False
    title_tbl.columns[0].width = Inches(6.8)
    for cell in [title_tbl.cell(0,0), title_tbl.cell(1,0)]:
        tc_pr = cell._tc.get_or_add_tcPr()
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        shd = OxmlElement('w:shd')
        shd.set(qn('w:fill'), "2E66A5")
        tc_pr.append(shd)

    p = title_tbl.cell(0,0).paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"{vals['JOB_NAME']} – Quote")
    r.bold = True
    r.font.size = Pt(16)
    r.font.color.rgb = RGBColor(255,255,255)

    p = title_tbl.cell(1,0).paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"Quote #: {vals['QUOTE_NUMBER']}")
    r.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = RGBColor(255,255,255)

    meta = doc.add_table(rows=1, cols=2)
    meta.columns[0].width = Inches(3.2)
    meta.columns[1].width = Inches(3.6)
    p = meta.cell(0,0).paragraphs[0]
    r = p.add_run(f"Attn: {vals['CUSTOMER']}")
    r.bold = True
    r.font.italic = True
    p = meta.cell(0,1).paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run(f"Quote Amt: {vals['TOTAL']}")
    r.bold = True

    # Divider
    p = doc.add_paragraph()
    p.add_run("―" * 55).bold = True

    doc.add_paragraph(_default_intro(vals))

    p = doc.add_paragraph()
    r = p.add_run("Work Included")
    r.bold = True
    r.font.size = Pt(20)

    p = doc.add_paragraph()
    p.add_run("―" * 55)

    scope_lines = _clean_lines(vals["SCOPE_OF_WORK"])
    if not scope_lines:
        scope_lines = [
            "Provide supervision and labor required to execute the quoted scope.",
            "Furnish materials identified in the estimate.",
            "Provide listed tools, trailers, and rental equipment as required.",
            "Mobilization, travel, per diem, and lodging as included in the estimate.",
            "Complete the described work in accordance with the selected estimate assumptions and scope.",
        ]

    for line in scope_lines:
        p = doc.add_paragraph(style=None)
        p.paragraph_format.left_indent = Inches(0.25)
        r = p.add_run(f"•  {line}")
        r.bold = False

    if vals["EXCLUSIONS"]:
        p = doc.add_paragraph()
        r = p.add_run("Exclusions")
        r.bold = True
        r.font.size = Pt(16)
        for line in _clean_lines(vals["EXCLUSIONS"]):
            doc.add_paragraph(f"•  {line}")

    if vals["ADDITIONAL_CHARGES"]:
        p = doc.add_paragraph()
        r = p.add_run("Additional Charges")
        r.bold = True
        r.font.size = Pt(16)
        for line in _clean_lines(vals["ADDITIONAL_CHARGES"]):
            doc.add_paragraph(f"•  {line}")

    if vals["CUSTOMER_RESPONSIBILITIES"]:
        p = doc.add_paragraph()
        r = p.add_run("Customer Responsibilities")
        r.bold = True
        r.font.size = Pt(16)
        doc.add_paragraph("Customer will provide:")
        for line in _clean_lines(vals["CUSTOMER_RESPONSIBILITIES"]):
            doc.add_paragraph(f"•  {line}")

    doc.add_paragraph("")
    doc.add_paragraph(f"Prepared By: {est.get('prepared_by', '')}")
    doc.add_paragraph(f"Date: {vals['DATE']}")
    doc.add_paragraph("If you have any questions regarding this Quote, please contact IPS.")

    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()


def build_proposal_pdf(est: dict, totals: dict, customer_name: str = "", job_name: str = "") -> bytes:
    """IPS quote PDF: header (Quote / # / Attn / Amt), body sections, footer. Signature unchanged for callers."""
    vals = proposal_values(est, totals, customer_name=customer_name, job_name=job_name)

    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 0.7 * inch
    left = margin
    right = width - margin
    y = height - PDF_PAGE_TOP

    # HEADER: title "Quote", quote #, Attn, Quote Amt
    bar_h = PDF_BAR_H
    c.setFillColorRGB(*(v / 255 for v in IPS_BLUE))
    c.rect(left, y - bar_h + PDF_BAR_PAD, right - left, bar_h, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString((left + right) / 2, y - 0.10 * inch, "Quote")
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString((left + right) / 2, y - 0.28 * inch, f"Quote #: {vals['QUOTE_NUMBER']}")
    y -= bar_h + PDF_AFTER_BLUE_BAR

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-BoldOblique", 12)
    c.drawString(left, y, f"Attn: {vals['CUSTOMER']}")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(right, y, f"Quote Amt: {vals['TOTAL']}")
    y -= PDF_ATTN_ROW

    c.setLineWidth(1.0)
    c.setStrokeColorRGB(*(v / 255 for v in IPS_GRAY))
    c.line(left, y, right, y)
    c.setStrokeColorRGB(0, 0, 0)
    y -= PDF_AFTER_RULE

    # BODY: opening + sections (text blocks, not tables)
    y = _pdf_draw_wrapped(
        c,
        PDF_QUOTE_OPENING,
        left=left,
        right=right,
        y=y,
        height=height,
        font="Times-Roman",
        size=11,
        line_step=PDF_BODY_LINE,
    )
    y -= PDF_AFTER_OPENING

    gap = PDF_SECTION_GAP
    y = _pdf_draw_section(
        c, "Scope of Work", vals["SCOPE_OF_WORK"], left=left, right=right, y=y, height=height, section_gap=gap
    )
    y = _pdf_draw_section(
        c, "Exclusions", vals["EXCLUSIONS"], left=left, right=right, y=y, height=height, section_gap=gap
    )
    y = _pdf_draw_section(
        c,
        "Additional Charges",
        vals["ADDITIONAL_CHARGES"],
        left=left,
        right=right,
        y=y,
        height=height,
        section_gap=gap,
    )
    y = _pdf_draw_section(
        c,
        "Orion Responsibilities",
        vals["CUSTOMER_RESPONSIBILITIES"],
        left=left,
        right=right,
        y=y,
        height=height,
        section_gap=gap,
    )

    # FOOTER: Prepared By, Date, contact
    if y < 1.05 * inch:
        c.showPage()
        y = height - 0.78 * inch

    y -= PDF_FOOTER_TOP_PAD
    c.setFont("Times-Roman", 11)
    c.drawString(left, y, f"Prepared By: {_pdf_prepared_by(est)}")
    y -= PDF_FOOTER_LINE
    c.drawString(left, y, f"Date: {vals['DATE']}")
    y -= PDF_FOOTER_LINE
    for contact_line in IPS_QUOTE_CONTACT_LINES:
        if y < 0.65 * inch:
            c.showPage()
            y = height - 0.72 * inch
            c.setFont("Times-Roman", 11)
        c.drawString(left, y, contact_line)
        y -= PDF_CONTACT_LINE

    c.save()
    return buffer.getvalue()
