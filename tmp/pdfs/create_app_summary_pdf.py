from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Frame, Paragraph
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output" / "pdf"
OUTPUT_PATH = OUTPUT_DIR / "app_summary_one_page.pdf"


TITLE = "App Summary"
SUBTITLE = "Industrial Plant Solutions - Streamlit estimating and operations app"

SECTIONS = [
    (
        "What it is",
        [
            "A Streamlit web app for Industrial Plant Solutions that manages estimating, jobs, time, expenses, users, and assets against a Supabase backend.",
            "The repo also includes proposal export plus AI-assisted material quote import and asset photo autofill features.",
        ],
    ),
    (
        "Who it's for",
        [
            "Primary persona: internal IPS estimators and admins; viewer users are also supported in auth/session role handling.",
        ],
    ),
    (
        "What it does",
        [
            "Builds estimates with materials, labor, equipment, travel, markup, overhead, profit, and tax controls.",
            "Saves revisions, submits estimates for approval, locks final statuses, and marks awarded work.",
            "Generates proposal exports as DOCX and PDF, and stores exports and attachments in Supabase Storage.",
            "Maintains customer and job records, including linked estimates, status, PM/supervisor fields, and awarded amounts.",
            "Tracks employee time entries with approval status and job/customer context.",
            "Tracks PO and expense records by category, vendor, job, and status.",
            "Manages assets, assignments, maintenance, inspections, documents, and AI-assisted photo/quote intake.",
        ],
    ),
    (
        "How it works",
        [
            "UI layer: `app/main.py` registers Streamlit pages and `app/ui.py` renders custom sidebar navigation.",
            "Auth/session: `app/auth.py` signs users in through Supabase Auth, loads `profiles`, and gates admin-only pages by role.",
            "Data access: `app/db.py` wraps Supabase table CRUD, admin writes, signed URLs, storage upload, and quote number generation.",
            "Feature pages: estimating, jobs, time, expenses, materials, labor, equipment, users, and asset pages read/write Supabase tables directly.",
            "Services: `app/services/material_quote_import.py` and `app/services/asset_photo_autofill.py` call OpenAI for structured extraction from uploaded files/photos.",
            "Schema evidence: `sql/001_asset_module_tables.sql` defines asset tables; other non-asset table DDL was not found in repo.",
        ],
    ),
    (
        "How to run",
        [
            "From the project root, create `.env` values for `SUPABASE_URL` plus either publishable/anon and secret/service-role keys; `OPENAI_API_KEY` is also needed for AI features.",
            "Install Python dependencies: Not found in repo (`requirements.txt` / top-level `pyproject.toml` not found).",
            "Start the app with `streamlit run app/main.py`.",
        ],
    ),
]


def build_styles(base_size: float) -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=20,
            textColor=colors.HexColor("#183153"),
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor("#4F5D75"),
            spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=base_size + 1.2,
            leading=base_size + 3.0,
            textColor=colors.HexColor("#1F4E79"),
            spaceBefore=2,
            spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=base_size,
            leading=base_size + 2.0,
            alignment=TA_LEFT,
            textColor=colors.black,
            spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=base_size,
            leading=base_size + 1.8,
            leftIndent=10,
            firstLineIndent=-7,
            textColor=colors.black,
            spaceAfter=1.5,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=7.2,
            leading=8.5,
            textColor=colors.HexColor("#6B7280"),
        ),
    }


def build_story(styles: dict[str, ParagraphStyle]) -> list[Paragraph]:
    story: list[Paragraph] = [
        Paragraph(TITLE, styles["title"]),
        Paragraph(SUBTITLE, styles["subtitle"]),
    ]
    for heading, items in SECTIONS:
        story.append(Paragraph(heading, styles["section"]))
        for index, item in enumerate(items):
            style_name = "body" if heading in {"What it is", "Who it's for"} else "bullet"
            bullet = "&bull; " if style_name == "bullet" else ""
            story.append(Paragraph(f"{bullet}{item}", styles[style_name]))
    story.append(
        Paragraph(
            "Source basis: repo files only. Visual PNG rendering was not available in this environment because `pdftoppm` was not installed.",
            styles["footer"],
        )
    )
    return story


def fits_one_page(page_width: float, page_height: float, styles: dict[str, ParagraphStyle]) -> bool:
    top = page_height - 0.55 * inch
    bottom = 0.45 * inch
    gutter = 0.28 * inch
    column_width = (page_width - 0.7 * inch - gutter) / 2
    column_height = top - bottom
    x_positions = [0.35 * inch, 0.35 * inch + column_width + gutter]

    current_column = 0
    y = top
    for flowable in build_story(styles):
        width, height = flowable.wrap(column_width, column_height)
        if y - height < bottom:
            current_column += 1
            if current_column >= 2:
                return False
            y = top
        y -= height
    return True


def draw_pdf(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = letter

    chosen_styles: dict[str, ParagraphStyle] | None = None
    for font_size in [9.0, 8.7, 8.4, 8.1, 7.8, 7.5]:
        candidate = build_styles(font_size)
        if fits_one_page(page_width, page_height, candidate):
            chosen_styles = candidate
            break

    if chosen_styles is None:
        raise RuntimeError("Could not fit summary on one page.")

    c = canvas.Canvas(str(output_path), pagesize=letter)
    c.setTitle("App Summary")
    c.setAuthor("OpenAI Codex")
    c.setPageCompression(0)

    c.setFillColor(colors.HexColor("#EAF2FB"))
    c.rect(0, page_height - 0.9 * inch, page_width, 0.9 * inch, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#D9E6F5"))
    c.rect(0, 0, page_width, 0.28 * inch, stroke=0, fill=1)

    top = page_height - 0.55 * inch
    bottom = 0.45 * inch
    gutter = 0.28 * inch
    column_width = (page_width - 0.7 * inch - gutter) / 2
    column_height = top - bottom

    frames = [
        Frame(0.35 * inch, bottom, column_width, column_height, showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
        Frame(0.35 * inch + column_width + gutter, bottom, column_width, column_height, showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
    ]
    remaining = build_story(chosen_styles)
    for frame in frames:
        frame.addFromList(remaining, c)
    c.save()


if __name__ == "__main__":
    draw_pdf(OUTPUT_PATH)
    print(OUTPUT_PATH)
