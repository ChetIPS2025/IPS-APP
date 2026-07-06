"""Navigation icon glyphs for collapsed sidebar mode."""

from __future__ import annotations

NAV_SLUG_ICONS: dict[str, str] = {
    "dashboard": "⌂",
    "pipeline": "⎇",
    "jobs": "💼",
    "customers": "🏢",
    "estimates": "📄",
    "pricing_guide": "📖",
    "inventory": "📦",
    "assets": "🚜",
    "rental_equipment": "📋",
    "timekeeping": "⏱",
    "tasks": "☑",
    "reports": "📊",
    "employees": "👥",
    "admin": "⚙",
    "settings": "🎚",
    "field_dashboard": "🏠",
    "field_day": "📅",
    "field_daily_reports": "📝",
    "field_crew_time": "👷",
    "scan_inventory": "📷",
    "scan_asset": "🔍",
    "employee_certifications": "🎓",
    "employee_portal": "🏠",
    "employee_qr_scan": "📷",
    "employee_resources": "📁",
    "employee_profile": "👤",
    "coupling_inspection": "🔗",
    "company_updates": "📣",
    "documents": "📁",
    "weekly_timesheets": "🗓",
    "employee_documents": "📎",
    "estimate_materials": "🧱",
}


def nav_icon_for_slug(slug: str) -> str:
    return NAV_SLUG_ICONS.get(str(slug or "").strip(), "•")
