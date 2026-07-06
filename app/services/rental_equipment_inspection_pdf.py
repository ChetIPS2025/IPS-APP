"""PDF export for rental equipment inspections."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from app.branding import get_header_logo_path
    from app.services.rental_equipment_inspection_service import (
        get_rental_equipment_dashboard_summary,
        inspection_type_label,
        photo_view_url,
    )
    from app.services.repository import fetch_by_id
    from app.services.rental_equipment_inspection_specs import (
        CHECKLIST_ITEMS,
        PHOTO_SLOT_LABELS,
        SIGNATURE_ROLE_LABELS,
        SIGNATURE_ROLES,
    )
except ImportError:
    from branding import get_header_logo_path  # type: ignore
    from services.rental_equipment_inspection_service import (  # type: ignore
        get_rental_equipment_dashboard_summary,
        inspection_type_label,
        photo_view_url,
    )
    from services.repository import fetch_by_id  # type: ignore
    from services.rental_equipment_inspection_specs import (  # type: ignore
        CHECKLIST_ITEMS,
        PHOTO_SLOT_LABELS,
        SIGNATURE_ROLE_LABELS,
        SIGNATURE_ROLES,
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


def _logo_flowable(*, width: float = 0.85 * inch, height: float = 0.55 * inch) -> RLImage | None:
    path = get_header_logo_path()
    if not path or not Path(path).is_file():
        return None
    try:
        return RLImage(str(path), width=width, height=height)
    except Exception:
        return None


def build_rental_inspection_pdf_bytes(record: dict[str, Any]) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=14, spaceAfter=8)
    body = styles["BodyText"]
    story: list[Any] = []

    logo = _logo_flowable()
    if logo:
        story.append(logo)
        story.append(Spacer(1, 0.1 * inch))

    itype = inspection_type_label(str(record.get("inspection_type") or ""))
    story.append(Paragraph(f"Rental Equipment {itype}", title_style))
    story.append(Paragraph(f"Status: {record.get('status') or 'draft'}", body))
    completed_at = str(record.get("completed_at") or record.get("signed_at") or "—")[:19]
    story.append(Paragraph(f"Date/Time: {completed_at}", body))
    story.append(Spacer(1, 0.1 * inch))

    asset = fetch_by_id("assets", str(record.get("asset_id") or "")) if record.get("asset_id") else None
    summary = get_rental_equipment_dashboard_summary(asset) if isinstance(asset, dict) else {}
    equip_rows = [
        ["Equipment", str(summary.get("asset_name") or "—")],
        ["Asset Number", str(summary.get("asset_number") or "—")],
        ["Customer", str(summary.get("customer_name") or "—")],
        ["Job", str(summary.get("job_label") or "—")],
    ]
    etbl = Table(equip_rows, colWidths=[1.6 * inch, 4.6 * inch])
    etbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e2e8f0")),
            ]
        )
    )
    story.append(etbl)
    story.append(Spacer(1, 0.15 * inch))

    info = [
        ["Overall Condition", str(record.get("general_condition") or "—")],
        ["Notes", str(record.get("notes") or "—")],
    ]
    if record.get("damage_reported"):
        info.extend(
            [
                ["Damage Description", str(record.get("damage_description") or "—")],
                ["Damage Location", str(record.get("damage_location") or "—")],
                ["Repair Recommendation", str(record.get("repair_recommendation") or "—")],
            ]
        )
    tbl = Table(info, colWidths=[1.6 * inch, 4.6 * inch])
    tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 0.15 * inch))

    checklist = record.get("checklist") if isinstance(record.get("checklist"), dict) else {}
    rows = [["Item", "Result"]]
    for key, label, _opts in CHECKLIST_ITEMS:
        rows.append([label, str(checklist.get(key) or "—")])
    ctbl = Table(rows, colWidths=[2.4 * inch, 3.8 * inch])
    ctbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ]
        )
    )
    story.append(Paragraph("Inspection Checklist", styles["Heading3"]))
    story.append(ctbl)
    story.append(Spacer(1, 0.15 * inch))

    photos = record.get("photo_attachments") or []
    if photos:
        story.append(Paragraph("Inspection Photos", styles["Heading3"]))
        for p in photos:
            if not isinstance(p, dict):
                continue
            slot = str(p.get("slot") or "")
            label = PHOTO_SLOT_LABELS.get(slot, slot)
            url = str(p.get("photo_url") or photo_view_url(str(p.get("photo_path") or "")))
            story.append(Paragraph(f"• {label}", body))
            if url.startswith("http"):
                try:
                    import urllib.request

                    with urllib.request.urlopen(url, timeout=20) as resp:
                        raw = resp.read()
                    img = RLImage(BytesIO(raw), width=2.2 * inch, height=1.65 * inch)
                    story.append(img)
                except Exception:
                    pass
        story.append(Spacer(1, 0.1 * inch))

    sigs = record.get("signatures") if isinstance(record.get("signatures"), dict) else {}
    if str(record.get("inspection_type") or "") != "damage":
        story.append(Paragraph("Signatures", styles["Heading3"]))
        for role in SIGNATURE_ROLES:
            entry = sigs.get(role) if isinstance(sigs.get(role), dict) else {}
            name = str((entry or {}).get("signer_name") or "—")
            signed = str((entry or {}).get("signed_at") or "—")[:19]
            story.append(Paragraph(f"{SIGNATURE_ROLE_LABELS.get(role, role)}: {name} ({signed})", body))
            sig_img = _sig_png_bytes(str((entry or {}).get("signature_data") or ""))
            if sig_img:
                try:
                    story.append(RLImage(BytesIO(sig_img), width=2.5 * inch, height=0.75 * inch))
                except Exception:
                    pass

    doc.build(story)
    return buf.getvalue()
