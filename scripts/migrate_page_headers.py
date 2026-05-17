"""One-off: migrate render_header -> render_page_header on remaining pages."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "pages"

MIGRATIONS: list[tuple[str, str, str]] = [
    ("asset_dashboard.py", "Asset Dashboard", "Fleet activity, maintenance, and status."),
    ("asset_detail.py", "Asset Detail", "Asset profile, assignments, and documents."),
    ("asset_inspections.py", "Asset Inspections", "Inspection history and checklists."),
    ("asset_assignments.py", "Asset Assignments", "Who has which assets assigned."),
    ("asset_documents.py", "Asset Documents", "Files linked to assets."),
    ("asset_maintenance.py", "Asset Maintenance", "Maintenance records and schedules."),
    ("asset_intake.py", "Asset Intake", "Add new assets to the database."),
    ("asset_scanner.py", "Asset Scanner", "Scan asset QR codes in the field."),
    ("tool_trailer_audits.py", "Tool Trailer Audits", "Trailer audits and reconciliation."),
    ("material_quote_import.py", "Material Quote Import", "Import vendor quotes into materials."),
    ("inventory_scan.py", "Scan Inventory", "Issue or receive stock via QR scan."),
    ("tool_trailer_audits.py", "Tool Trailer Audits", "Trailer audits and reconciliation."),
]

IMPORT_SNIPPET = """
try:
    from app.ui.page_shell import render_page_header
except ImportError:
    from ui.page_shell import render_page_header  # type: ignore
""".strip()


def migrate_file(path: Path, title: str, subtitle: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if "render_page_header" in text:
        return False
    if "render_page_header" not in text and "from app.ui.page_shell" not in text:
        if "from app.branding import render_header" in text:
            text = text.replace(
                "from app.branding import render_header",
                IMPORT_SNIPPET + "\nfrom app.branding import render_header",
            )
        elif "from branding import render_header" in text:
            text = text.replace(
                "from branding import render_header",
                IMPORT_SNIPPET + "\nfrom branding import render_header",
            )
    pat = rf'render_header\(\s*"{re.escape(title)}"\s*(?:,\s*subtitle\s*=\s*[^)]+)?\s*\)'
    repl = f'render_page_header("{title}", "{subtitle}")'
    new, n = re.subn(pat, repl, text, count=1)
    if n == 0 and title == "Scan Inventory":
        new, n = re.subn(
            r'render_header\(\s*""\s*,\s*subtitle\s*=\s*"[^"]*"\s*\)',
            repl,
            text,
            count=1,
        )
    if n == 0:
        return False
  # Remove following st.caption that duplicates subtitle (one line)
    new = re.sub(
        r'\n\s*st\.caption\("[^"]{8,120}"\)\s*\n',
        "\n",
        new,
        count=1,
    )
    path.write_text(new, encoding="utf-8")
    return True


def main() -> None:
    seen: set[str] = set()
    for fn, title, sub in MIGRATIONS:
        if fn in seen:
            continue
        seen.add(fn)
        p = ROOT / fn
        if p.exists() and migrate_file(p, title, sub):
            print("updated", fn)


if __name__ == "__main__":
    main()
