"""Portrait IPS Coupling Inspection PDF export (V6 layout)."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Any

from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from app.services.coupling_inspection_service import PHOTO_SLOT_LABELS, photo_view_url
    from app.services.coupling_inspection_specs import (
        BOLT_COUNT,
        CLOCK_POSITION_ANGLES,
        TORQUE_CLOCK_SEQUENCE,
        normalize_torque_rows,
        torque_pass_labels,
        torque_sequence_caption,
    )
except ImportError:
    from services.coupling_inspection_service import PHOTO_SLOT_LABELS, photo_view_url  # type: ignore
    from services.coupling_inspection_specs import (  # type: ignore
        BOLT_COUNT,
        CLOCK_POSITION_ANGLES,
        TORQUE_CLOCK_SEQUENCE,
        normalize_torque_rows,
        torque_pass_labels,
        torque_sequence_caption,
    )


def _sig_png_bytes(signature_data: str) -> bytes | None:
    s = str(signature_data or "").strip()
    if not s:
        return None
    if s.startswith("data:image"):
        try:
            return base64.b64decode(s.split(",", 1)[1])
        except Exception:
            return None
    try:
        return base64.b64decode(s)
    except Exception:
        return None


def _rl_image_from_sig(signature_data: str, *, width: float, height: float) -> RLImage | None:
    raw = _sig_png_bytes(signature_data)
    if not raw:
        return None
    try:
        return RLImage(BytesIO(raw), width=width, height=height)
    except Exception:
        return None


def _checkmark(checked: bool) -> str:
    return "✓" if checked else ""


def _torque_pattern_drawing(*, size: float = 170) -> Drawing:
    """8-bolt crisscross/star flange pattern."""
    import math

    d = Drawing(size, size)
    cx = cy = size / 2
    r = size / 2 - 24
    d.add(Circle(cx, cy, r + 6, fillColor=colors.HexColor("#f8fafc"), strokeColor=colors.HexColor("#cbd5e1")))
    d.add(Circle(cx, cy, r, fillColor=None, strokeColor=colors.HexColor("#94a3b8"), strokeDashArray=[3, 2]))

    points: list[tuple[float, float, int, str]] = []
    for i, clock in enumerate(TORQUE_CLOCK_SEQUENCE, start=1):
        deg = CLOCK_POSITION_ANGLES.get(clock, 0.0)
        rad = math.radians(deg)
        x = cx + r * math.cos(rad)
        y = cy + r * math.sin(rad)  # reportlab y-up
        points.append((x, y, i, clock))

    for a, b in ((0, 4), (1, 5), (2, 6), (3, 7)):
        x1, y1, _, _ = points[a]
        x2, y2, _, _ = points[b]
        d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#2563eb"), strokeWidth=1.2))

    for i in range(len(points)):
        x1, y1, _, _ = points[i]
        x2, y2, _, _ = points[(i + 1) % len(points)]
        d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#64748b"), strokeWidth=0.8, strokeDashArray=[2, 2]))

    for x, y, num, clock in points:
        d.add(Circle(x, y, 9, fillColor=colors.HexColor("#2563eb"), strokeColor=colors.white, strokeWidth=1))
        d.add(String(x - 3, y - 3, str(num), fontSize=8, fillColor=colors.white))
        d.add(String(x - 10, y - 16, clock, fontSize=6, fillColor=colors.HexColor("#475569")))
    return d


def build_coupling_inspection_pdf_bytes(record: dict[str, Any]) -> bytes:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CouplingTitle",
        parent=styles["Title"],
        fontSize=16,
        spaceAfter=6,
        textColor=colors.HexColor("#0f172a"),
    )
    sub_style = ParagraphStyle(
        "CouplingSub",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#475569"),
    )
    hdr = record.get("header") or {}
    specs = record.get("specs") or {}
    fields = record.get("inspection_fields") or {}
    rows = normalize_torque_rows(
        list(record.get("torque_rows") or []),
        model_key=str(record.get("coupling_model") or "1030G20"),
    )
    p1_lbl, p2_lbl, pf_lbl = torque_pass_labels(specs)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )
    story: list[Any] = []

    story.append(Paragraph("IPS Coupling Inspection &amp; Torque Verification", title_style))
    story.append(Paragraph("Industrial Plant Services — V6 Coupling Report", sub_style))
    story.append(Spacer(1, 0.12 * inch))

    meta = [
        ["Customer", str(hdr.get("customer") or "—")],
        ["Job #", str(hdr.get("job_number") or "—")],
        ["Work Order #", str(hdr.get("work_order_number") or "—")],
        ["Equipment", str(hdr.get("equipment_name") or "—")],
        ["Asset #", str(hdr.get("asset_number") or "—")],
        ["Location", str(hdr.get("location") or "—")],
        ["Date", str(hdr.get("inspection_date") or "—")],
        ["Technician", str(hdr.get("technician") or "—")],
        ["Coupling Model", str(record.get("coupling_model") or "—")],
        ["Status", str(record.get("status") or "draft").title()],
    ]
    meta_table = Table(meta, colWidths=[1.35 * inch, 5.0 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#64748b")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#f1f5f9")),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 0.14 * inch))

    story.append(Paragraph("Coupling Specifications", styles["Heading3"]))
    spec_rows = [
        ["Coupling Type", str(specs.get("coupling_type") or "—")],
        ["Flange Bolts", str(specs.get("flange_bolts") or "—")],
        ["Final Torque", f"{specs.get('final_torque_ft_lb', '—')} ft-lb / {specs.get('final_torque_nm', '—')} Nm"],
        ["Standard Hub Gap", f"{specs.get('standard_hub_gap_in', '—')} in"],
        [
            "Lubricant Quantity",
            f"{specs.get('lubricant_quantity_lb', '—')} lb / {specs.get('lubricant_quantity_oz', '—')} oz",
        ],
    ]
    spec_table = Table(spec_rows, colWidths=[1.5 * inch, 4.85 * inch])
    spec_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ]
        )
    )
    story.append(spec_table)
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Torque Sequence Pattern (8-bolt crisscross)", styles["Heading4"]))
    story.append(_torque_pattern_drawing())
    story.append(Spacer(1, 0.06 * inch))
    story.append(Paragraph(torque_sequence_caption(), styles["Normal"]))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Torque Verification Chart", styles["Heading3"]))
    torque_header = ["#", "Clock", p1_lbl, p2_lbl, pf_lbl, "Witness", "Initial"]
    torque_data = [torque_header]
    for row in rows[:BOLT_COUNT]:
        init_sig = "Signed" if str(row.get("initial_signature") or "").strip() else ""
        torque_data.append(
            [
                str(row.get("order") or ""),
                str(row.get("clock_position") or ""),
                _checkmark(bool(row.get("pass1_checked"))),
                _checkmark(bool(row.get("pass2_checked"))),
                _checkmark(bool(row.get("final_checked"))),
                _checkmark(bool(row.get("witness_mark_checked"))),
                init_sig,
            ]
        )
    torque_table = Table(
        torque_data,
        colWidths=[0.35 * inch, 0.75 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 0.65 * inch, 0.75 * inch],
        repeatRows=1,
    )
    torque_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    story.append(torque_table)
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Inspection Results", styles["Heading3"]))
    insp_rows = [
        ["Actual Hub Gap (in)", str(fields.get("actual_hub_gap_in") or "—")],
        ["Lubricant Type", str(fields.get("lubricant_type") or "—")],
        ["Lubricant Qty Added", str(fields.get("lubricant_quantity_added") or "—")],
        ["Coupling Teeth", str(fields.get("coupling_teeth_condition") or "—")],
        ["Grease Condition", str(fields.get("grease_condition") or "—")],
        ["Seal Condition", str(fields.get("seal_condition") or "—")],
        ["Cover Installed", "Yes" if fields.get("cover_installed") else "No"],
        ["Fasteners Witness Marked", "Yes" if fields.get("fasteners_witness_marked") else "No"],
        ["Guard Installed", "Yes" if fields.get("guard_installed") else "No"],
    ]
    insp_table = Table(insp_rows, colWidths=[1.75 * inch, 4.6 * inch])
    insp_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ]
        )
    )
    story.append(insp_table)
    notes = str(fields.get("notes") or "").strip()
    if notes:
        story.append(Spacer(1, 0.08 * inch))
        story.append(Paragraph("Notes / Comments", styles["Heading4"]))
        story.append(Paragraph(notes.replace("\n", "<br/>"), styles["Normal"]))

    photos = list(record.get("photo_attachments") or [])
    if photos:
        story.append(Spacer(1, 0.12 * inch))
        story.append(Paragraph("Photo Attachments", styles["Heading3"]))
        for att in photos[:6]:
            slot = str(att.get("slot") or "")
            label = PHOTO_SLOT_LABELS.get(slot, slot or "Photo")
            story.append(Paragraph(label, styles["Heading4"]))
            url = photo_view_url(att)
            if url:
                try:
                    import urllib.request

                    with urllib.request.urlopen(url, timeout=8) as resp:
                        img_bytes = resp.read()
                    img = RLImage(BytesIO(img_bytes), width=2.8 * inch, height=2.1 * inch)
                    story.append(img)
                except Exception:
                    story.append(Paragraph(str(att.get("file_name") or "Photo on file"), styles["Normal"]))
            else:
                story.append(Paragraph(str(att.get("file_name") or "Photo on file"), styles["Normal"]))
            story.append(Spacer(1, 0.06 * inch))

    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph("Signatures", styles["Heading3"]))
    sig_rows: list[list[Any]] = []
    for label, key in (
        ("Technician", "technician_signature"),
        ("Supervisor", "supervisor_signature"),
        ("Customer Representative", "customer_signature"),
    ):
        img = _rl_image_from_sig(str(record.get(key) or ""), width=2.2 * inch, height=0.55 * inch)
        sig_rows.append([label, img if img else Paragraph("—", styles["Normal"])])
    sig_table = Table(sig_rows, colWidths=[1.4 * inch, 4.95 * inch])
    sig_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(sig_table)

    doc.build(story)
    return buf.getvalue()
