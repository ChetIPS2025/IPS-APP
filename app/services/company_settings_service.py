"""Company-wide application settings (``company_settings`` table)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_DEFAULTS: dict[str, Any] = {
    "company_name": "Industrial Plant Solutions",
    "timezone": "America/Chicago",
    "default_landing_page": "Dashboard",
    "date_format": "MM/DD/YYYY",
    "email_notifications_enabled": True,
    "timekeeping_weekend_counts_toward_40": False,
}

_LANDING_PAGES = ("Dashboard", "Jobs", "Timekeeping")
_DATE_FORMATS = ("MM/DD/YYYY", "DD/MM/YYYY", "ISO")
_TIMEZONES = ("America/Chicago", "America/New_York", "UTC")


def load_app_settings() -> dict[str, Any]:
    """Return merged defaults plus the first ``company_settings`` row when present."""
    out = {**_DEFAULTS, "id": None, "from_db": False}
    from app.services.repository import fetch_rows
    rows, err = fetch_rows("company_settings", limit=1)
    if err or not rows:
        return out

    row = rows[0]
    out["from_db"] = True
    out["id"] = row.get("id")
    for key in _DEFAULTS:
        if row.get(key) is not None:
            out[key] = row.get(key)
    return out


def save_app_settings(
    *,
    default_landing_page: str,
    date_format: str,
    timezone_name: str,
    email_notifications_enabled: bool,
    timekeeping_weekend_counts_toward_40: bool = False,
) -> tuple[bool, str]:
    landing = str(default_landing_page or "Dashboard").strip()
    if landing not in _LANDING_PAGES:
        landing = "Dashboard"
    fmt = str(date_format or "MM/DD/YYYY").strip()
    if fmt not in _DATE_FORMATS:
        fmt = "MM/DD/YYYY"
    tz = str(timezone_name or "America/Chicago").strip()
    if tz not in _TIMEZONES:
        tz = "America/Chicago"

    payload: dict[str, Any] = {
        "default_landing_page": landing,
        "date_format": fmt,
        "timezone": tz,
        "email_notifications_enabled": bool(email_notifications_enabled),
        "timekeeping_weekend_counts_toward_40": bool(timekeeping_weekend_counts_toward_40),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    from app.services.repository import fetch_rows, insert_row, update_row
    rows, err = fetch_rows("company_settings", limit=1)
    if err:
        return False, err

    if rows and rows[0].get("id"):
        res = update_row("company_settings", payload, {"id": rows[0]["id"]})
    else:
        payload["company_name"] = _DEFAULTS["company_name"]
        res = insert_row("company_settings", payload)

    if not res.ok:
        return False, res.error or "Could not save settings."
    return True, "Settings saved to company_settings."
