"""Portrait IPS Coupling Inspection PDF export (V7 layout)."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from app.branding import get_header_logo_path
    from app.services.coupling_inspection_service import (
        PHOTO_SLOT_LABELS,
        normalize_inspection_results,
        normalize_signatures_meta,
        photo_view_url,
    )
    from app.services.coupling_inspection_specs import (
        BOLT_COUNT,
        CLOCK_POSITION_ANGLES,
        FORM_VERSION,
        INSPECTION_RESULT_ITEMS,
        TORQUE_CLOCK_SEQUENCE,
        normalize_torque_rows,
        torque_pass_labels,
        torque_sequence_caption,
    )
except ImportError:
    from branding import get_header_logo_path  # type: ignore
    from services.coupling_inspection_service import (  # type: ignore
        PHOTO_SLOT_LABELS,
        normalize_inspection_results,
        normalize_signatures_meta,
        photo_view_url,
    )
    from services.coupling_inspection_specs import (  # type: ignore
        BOLT_COUNT,
        CLOCK_POSITION_ANGLES,
        FORM_VERSION,
        INSPECTION_RESULT_ITEMS,
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


def _logo_flowable(*, width: float = 0.85 * inch, height: float = 0.55 * inch) -> RLImage | None:
    path = get_header_logo_path()
    if not path or not Path(path).is_file():
        return None
    try:
        return RLImage(str(path), width=width, height=height)
    except Exception:
        return None


def _checkmark(checked: bool) -> str:
    return "✓" if checked else ""


def _result_label(item: dict[str, Any]) -> str:
    if item.get("pass"):
        return "Pass"
    if item.get("fail"):
        return "Fail"
    if item.get("na"):
        return "N/A"
    return "—"


def _format_field_value(item: dict[str, Any], kind: str) -> str:
    val = item.get("value")
    if kind == "bool":
        return "Yes" if val else "No"
    if val in (None, ""):
        return "—"
    return str(val)


def _torque_pattern_drawing(*, size: float = 150) -> Drawing:
    import math

    d = Drawing(size, size)
    cx = cy = size / 2
    r = size / 2 - 22
    d.add(Circle(cx, cy, r + 5, fillColor=colors.HexColor("#f8fafc"), strokeColor=colors.HexColor("#cbd5e1")))
    d.add(Circle(cx, cy, r, fillColor=None, strokeColor=colors.HexColor("#94a3b8"), strokeDashArray=[3, 2]))
    points: list[tuple[float, float, int, str]] = []
    for i, clock in enumerate(TORQUE_CLOCK_SEQUENCE, start=1):
        deg = CLOCK_POSITION_ANGLES.get(clock, 0.0)
        rad = math.radians(deg)
        x = cx + r * math.cos(rad)
        y = cy + r * math.sin(rad)
        points.append((x, y, i, clock))
    for a, b in ((0, 4), (1, 5), (2, 6), (3, 7)):
        x1, y1, _, _ = points[a]
        x2, y2, _, _ = points[b]
        d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#2563eb"), strokeWidth=1.1))
    for x, y, num, clock in points:
        d.add(Circle(x, y, 8, fillColor=colors.HexColor("#2563eb"), strokeColor=colors.white, strokeWidth=1))
        d.add(String(x - 2, y - 3, str(num), fontSize=7, fillColor=colors.white))
        d.add(String(x - 9, y - 14, clock, fontSize=5, fillColor=colors.HexColor("#475569")))
    return d


def build_coupling_inspection_pdf_bytes(record: dict[str, Any]) -> bytes:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CouplingTitle",
        parent=styles["Title"],
        fontSize=15,
        spaceAfter=4,
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
    fields = normalize_inspection_results(record.get("inspection_fields"))
    sig_meta = normalize_signatures_meta(record)
    rows = normalize_torque_rows(
        list(record.get("torque_rows") or []),
        model_key=str(record.get("coupling_model") or "1030G20"),
    )
    p1_lbl, p2_lbl, pf_lbl = torque_pass_labels(specs)
    status = str(record.get("status") or "draft").title()
    if status.lower() == "complete":
        status = "Completed"

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
    )
    story: list[Any] = []

    logo = _logo_flowable()
    header_row: list[Any] = []
    if logo:
        header_row.append(logo)
    header_row.append(
        Paragraph(
            f"<b>IPS Coupling Inspection &amp; Torque Verification</b><br/>"
            f"Industrial Plant Services — {FORM_VERSION} · Status: {status}",
            title_style,
        )
    )
    header_table = Table([header_row], colWidths=[0.9 * inch, 5.7 * inch])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(header_table)
    story.append(Spacer(1, 0.1 * inch))

    meta = [
        ["Customer", str(hdr.get("customer") or "—")],
        ["Job #", str(hdr.get("job_number") or "—")],
        ["Work Order #", str(hdr.get("work_order_number") or "—")],
        ["Equipment", str(hdr.get("equipment_name") or "—")],
        ["Asset #", str(hdr.get("asset_number") or "—")],
        ["Location", str(hdr.get("location") or "—")],
        ["Date", str(hdr.get("inspection_date") or "—")],
        ["Technician", str(hdr.get("technician") or "—")],
        ["Supervisor", str(hdr.get("supervisor") or "—")],
        ["Customer Representative", str(hdr.get("customer_representative") or "—")],
        ["Coupling Model", str(record.get("coupling_model") or "—")],
    ]
    meta_table = Table(meta, colWidths=[1.45 * inch, 5.15 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#64748b")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#f1f5f9")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Coupling Specifications", styles["Heading3"]))
    gap = specs.get("standard_hub_gap_in")
    lb = specs.get("lubricant_quantity_lb")
    oz = specs.get("lubricant_quantity_oz")
    spec_rows = [
        ["Coupling Type", str(specs.get("coupling_type") or "—")],
        ["Flange Bolts", str(specs.get("flange_bolts") or "—")],
        ["Bolt Count", str(specs.get("bolt_count") or BOLT_COUNT)],
        ["Final Torque", f"{specs.get('final_torque_ft_lb', '—')} ft-lb / {specs.get('final_torque_nm', '—')} Nm"],
        ["Standard Hub Gap", f"{gap:g} in" if gap is not None else "—"],
        ["Lubricant Type", str(specs.get("lubricant_type_default") or "—")],
        ["Lubricant Quantity", f"{lb:g} lb / {oz:g} oz" if lb is not None else "—"],
    ]
    spec_table = Table(spec_rows, colWidths=[1.5 * inch, 5.1 * inch])
    spec_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ]
        )
    )
    story.append(spec_table)
    story.append(Spacer(1, 0.08 * inch))
    story.append(_torque_pattern_drawing())
    story.append(Paragraph(torque_sequence_caption(), sub_style))
    story.append(Spacer(1, 0.08 * inch))

    story.append(Paragraph("Torque Verification Chart", styles["Heading3"]))
    torque_header = ["#", "Clock", p1_lbl, p2_lbl, pf_lbl, "Witness", "P/F", "Notes"]
    torque_data = [torque_header]
    for row in rows[:BOLT_COUNT]:
        initials = str(row.get("witness_initials") or "").strip()
        pf = row.get("pass_fail")
        pf_txt = "Pass" if pf == "pass" else ("Fail" if pf == "fail" else "")
        torque_data.append(
            [
                str(row.get("order") or ""),
                str(row.get("clock_position") or ""),
                _checkmark(bool(row.get("pass1_checked"))),
                _checkmark(bool(row.get("pass2_checked"))),
                _checkmark(bool(row.get("final_checked"))),
                initials,
                pf_txt,
                str(row.get("notes") or ""),
            ]
        )
    torque_table = Table(
        torque_data,
        colWidths=[0.3 * inch, 0.65 * inch, 0.7 * inch, 0.7 * inch, 0.7 * inch, 0.65 * inch, 0.45 * inch, 1.35 * inch],
        repeatRows=1,
    )
    torque_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ]
        )
    )
    story.append(torque_table)
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Inspection Results", styles["Heading3"]))
    insp_data = [["Item", "Value", "Result", "Notes"]]
    for field_key, label, kind in INSPECTION_RESULT_ITEMS:
        item = fields.get(field_key) or {}
        insp_data.append(
            [
                label,
                _format_field_value(item, kind),
                _result_label(item),
                str(item.get("notes") or ""),
            ]
        )
    insp_table = Table(insp_data, colWidths=[1.55 * inch, 1.35 * inch, 0.75 * inch, 2.55 * inch], repeatRows=1)
    insp_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ]
        )
    )
    story.append(insp_table)
    story.append(Spacer(1, 0.1 * inch))

    photos = list(record.get("photo_attachments") or [])
    if photos:
        story.append(Paragraph("Photo Attachments", styles["Heading3"]))
        for att in photos[:8]:
            slot = str(att.get("slot") or att.get("category") or "")
            label = PHOTO_SLOT_LABELS.get(slot, slot or "Photo")
            caption = str(att.get("caption") or label)
            uploaded = str(att.get("uploaded_at") or "")[:19]
            by = str(att.get("uploaded_by") or "")
            meta_line = " · ".join(x for x in (caption, by, uploaded) if x)
            story.append(Paragraph(meta_line, styles["Heading4"]))
            url = photo_view_url(att)
            if url:
                try:
                    import urllib.request

                    with urllib.request.urlopen(url, timeout=8) as resp:
                        img_bytes = resp.read()
                    img = RLImage(BytesIO(img_bytes), width=2.6 * inch, height=1.95 * inch)
                    story.append(img)
                except Exception:
                    story.append(Paragraph(str(att.get("file_name") or "Photo on file"), styles["Normal"]))
            story.append(Spacer(1, 0.05 * inch))

    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph("Signatures", styles["Heading3"]))
    sig_rows: list[list[Any]] = []
    role_labels = {
        "technician": "Technician",
        "supervisor": "Supervisor",
        "customer_representative": "Customer Representative",
    }
    for role, label in role_labels.items():
        entry = sig_meta.get(role) or {}
        name = str(entry.get("signer_name") or "").strip()
        signed_at = str(entry.get("signed_at") or "")[:19]
        img = _rl_image_from_sig(str(entry.get("signature_image") or ""), width=2.0 * inch, height=0.5 * inch)
        detail = "<br/>".join(x for x in (name, signed_at) if x) or "—"
        sig_rows.append([label, img if img else Paragraph("—", styles["Normal"]), Paragraph(detail, sub_style)])
    sig_table = Table(sig_rows, colWidths=[1.35 * inch, 2.5 * inch, 2.35 * inch])
    sig_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ]
        )
    )
    story.append(sig_table)
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(f"Generated {FORM_VERSION} report — Status: {status}", sub_style))

    doc.build(story)
    return buf.getvalue()
