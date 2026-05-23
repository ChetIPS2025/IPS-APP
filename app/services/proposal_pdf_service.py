"""Customer-facing estimate proposal PDF generation (ReportLab, in-memory bytes)."""

from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.estimate_costing_service import get_default_terms
from app.utils.estimate_calculations import calc_totals
from app.utils.formatting import fmt_currency, fmt_date


def _money(val: Any) -> str:
    return fmt_currency(val)


def _text(val: Any, default: str = "—") -> str:
    s = str(val or "").strip()
    return s if s else default


def generate_estimate_proposal_pdf(
    estimate: dict[str, Any],
    line_items: dict[str, list[dict[str, Any]]] | None = None,
    *,
    company_profile: dict[str, Any] | None = None,
    terms_text: str | None = None,
) -> bytes:
    """Build a customer-facing proposal PDF (no internal cost/margin by default)."""
    profile = company_profile or {}
    company_name = _text(profile.get("company_name") or profile.get("name"), "Industrial Plant Solutions, LLC")
    lines = line_items or {}
    materials = lines.get("materials") or []
    labor = lines.get("labor") or []
    equipment = lines.get("equipment") or []
    travel = lines.get("travel") or []
    subcontractors = lines.get("subcontractors") or []
    other_costs = lines.get("other_costs") or []

    totals = calc_totals(
        materials,
        labor,
        equipment,
        subcontractors,
        other_costs,
        travel=travel,
        tax_rate=estimate.get("tax_rate") or 0,
    )

    show_line_items = bool(estimate.get("proposal_show_line_items"))
    show_categories = estimate.get("proposal_show_category_totals", True)
    show_final_only = bool(estimate.get("proposal_show_final_price_only"))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=f"{_text(estimate.get('estimate_number'), 'Proposal')} Proposal",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ProposalTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ProposalSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14,
    )
    section_style = ParagraphStyle(
        "SectionHead",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
    )
    right_style = ParagraphStyle(
        "Right",
        parent=body_style,
        alignment=TA_RIGHT,
    )

    story: list[Any] = []
    story.append(Paragraph(company_name, title_style))
    story.append(Paragraph("Project Proposal / Estimate", subtitle_style))

    meta_rows = [
        ["Estimate #", _text(estimate.get("estimate_number"))],
        ["Estimate Date", fmt_date(estimate.get("estimate_date"))],
        ["Valid Through", fmt_date(estimate.get("expiration_date"))],
        ["Project", _text(estimate.get("project_name"))],
        ["Customer", _text(estimate.get("customer") or estimate.get("customer_name"))],
        ["Location", _text(estimate.get("location_name"))],
        ["Contact", _text(estimate.get("contact_name"))],
        ["Status", _text(estimate.get("status"), "Draft")],
    ]
    meta_table = Table(meta_rows, colWidths=[1.4 * inch, 5.0 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 0.15 * inch))

    scope = _text(estimate.get("description") or estimate.get("scope_of_work"), "")
    if scope and scope != "—":
        story.append(Paragraph("Scope of Work", section_style))
        story.append(Paragraph(scope.replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 0.1 * inch))

    if not show_final_only:
        if show_line_items:
            story.append(Paragraph("Line Item Summary", section_style))
            li_rows = [["Description", "Qty", "Unit", "Amount"]]
            for row in materials:
                li_rows.append(
                    [
                        _text(row.get("description")),
                        str(row.get("quantity") or row.get("qty") or ""),
                        _text(row.get("unit")),
                        _money(row.get("price_total")),
                    ]
                )
            for row in labor:
                li_rows.append(
                    [
                        _text(row.get("description") or row.get("role_name")),
                        f"ST {row.get('st_hours', 0)} / OT {row.get('ot_hours', 0)}",
                        "HR",
                        _money(row.get("price_total")),
                    ]
                )
            for row in equipment:
                li_rows.append(
                    [
                        _text(row.get("equipment_name")),
                        str(row.get("quantity") or 1),
                        _text(row.get("duration_unit")),
                        _money(row.get("price_total")),
                    ]
                )
            for row in travel:
                li_rows.append([_text(row.get("description") or row.get("travel_type")), "1", "Travel", _money(row.get("price_total"))])
            for row in subcontractors:
                li_rows.append([_text(row.get("description")), "1", "LS", _money(row.get("price_total"))])
            for row in other_costs:
                li_rows.append([_text(row.get("description")), "1", "EA", _money(row.get("price_total"))])

            if len(li_rows) > 1:
                li_table = Table(li_rows, colWidths=[3.2 * inch, 0.8 * inch, 0.7 * inch, 1.0 * inch])
                li_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                        ]
                    )
                )
                story.append(li_table)
                story.append(Spacer(1, 0.12 * inch))

        if show_categories:
            story.append(Paragraph("Pricing Summary", section_style))
            cat_rows = [
                ["Category", "Amount"],
                ["Materials", _money(totals["material_cost"] + totals["material_markup"])],
                ["Labor", _money(totals["labor_cost"] + totals["labor_markup"])],
                ["Equipment", _money(totals["equipment_cost"] + totals["equipment_markup"])],
            ]
            travel_customer = totals["travel_cost"] + totals["travel_markup"]
            if travel_customer > 0:
                cat_rows.append(["Travel", _money(travel_customer)])
            cat_rows.extend(
                [
                ["Subcontractors", _money(totals["subcontractor_cost"] + totals["subcontractor_markup"])],
                ["Other", _money(totals["other_cost"] + totals["other_markup"])],
                ]
            )
            if totals["tax_amount"] > 0:
                cat_rows.append(["Sales Tax", _money(totals["tax_amount"])])
            cat_table = Table(cat_rows, colWidths=[4.5 * inch, 1.4 * inch])
            cat_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ]
                )
            )
            story.append(cat_table)
            story.append(Spacer(1, 0.08 * inch))

    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph(f"<b>Total Proposal Price:</b> {_money(totals['customer_price'])}", right_style))

    terms = terms_text or get_default_terms()
    story.append(Spacer(1, 0.18 * inch))
    story.append(Paragraph("Terms & Conditions", section_style))
    story.append(Paragraph(terms.replace("\n", "<br/>"), body_style))

    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("Acceptance", section_style))
    sig_rows = [
        ["Authorized Signature", "________________________________________"],
        ["Printed Name", "________________________________________"],
        ["Title", "________________________________________"],
        ["Date", "________________________________________"],
    ]
    sig_table = Table(sig_rows, colWidths=[1.5 * inch, 4.4 * inch])
    sig_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(sig_table)
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        Paragraph(
            f"Generated {date.today().strftime('%B %d, %Y')} · {company_name}",
            ParagraphStyle("Footer", parent=body_style, fontSize=8, textColor=colors.HexColor("#94a3b8")),
        )
    )

    doc.build(story)
    return buffer.getvalue()


def generate_estimate_proposal_pdf_by_id(estimate_id: str, estimate: dict[str, Any]) -> bytes:
    from app.services.estimate_costing_service import get_estimate_bundle

    bundle = get_estimate_bundle(estimate_id)
    return generate_estimate_proposal_pdf(estimate, bundle)
