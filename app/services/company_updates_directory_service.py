"""Paginated Company Updates directory — list projection, filters, and sorting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.company_updates_cache import company_updates_data_version

COMPANY_UPDATES_DEFAULT_PAGE_SIZE = 25
_LIST_TABLE_KEY = "company_updates_list"

_CATEGORY_NORMALIZER: Callable[[object], str] | None = None
_STATUS_NORMALIZER: Callable[[object], str] | None = None
_AUDIENCE_NORMALIZER: Callable[[object], str] | None = None


def _norm_category(raw: object) -> str:
    s = str(raw or "").strip().lower()
    if s in ("", "general"):
        return "General"
    if "announcement" in s:
        return "Announcement"
    if "safety" in s:
        return "Safety Alert"
    if "event" in s:
        return "Event"
    if "hr" in s:
        return "HR Update"
    if "project" in s:
        return "Project Update"
    return "General"


def _norm_status(raw: object, *, is_active: object = None) -> str:
    s = str(raw or "").strip().lower()
    if s in ("published", "active"):
        return "Published"
    if s == "draft":
        return "Draft"
    if s == "scheduled":
        return "Scheduled"
    if s in ("archived", "inactive"):
        return "Archived"
    if is_active is False:
        return "Archived"
    return "Published"


def _norm_audience(raw: object) -> str:
    s = str(raw or "").strip()
    if not s:
        return "All"
    known = {
        "all": "All",
        "admin": "Admin",
        "supervisors": "Supervisors",
        "supervisor": "Supervisors",
        "employees": "Employees",
        "employee": "Employees",
        "field crew": "Field Crew",
        "field": "Field Crew",
        "office": "Office",
        "management": "Management",
    }
    return known.get(s.lower(), s)


def normalize_update_category(raw: object) -> str:
    return _norm_category(raw)


def normalize_update_status(raw: object, *, is_active: object = None) -> str:
    return _norm_status(raw, is_active=is_active)


def normalize_update_audience(raw: object) -> str:
    return _norm_audience(raw)


def _parse_ts(raw: object) -> float:
    text = str(raw or "").strip()
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        pass
    for fmt, length in (("%Y-%m-%dT%H:%M:%S", 19), ("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(text[:length], fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def _fmt_event_date(row: dict[str, Any]) -> str:
    from app.utils.formatting import fmt_date, fmt_datetime

    raw = row.get("event_date") or row.get("event_at") or row.get("event_datetime")
    if not raw and _norm_category(row.get("category")) == "Event":
        raw = row.get("date")
    if not raw:
        return "—"
    text = str(raw).strip()
    if "T" in text or " " in text:
        return fmt_datetime(text)
    return fmt_date(text)


def _fmt_created_date(row: dict[str, Any]) -> str:
    from app.utils.formatting import fmt_date

    return fmt_date(row.get("created_at") or row.get("created_date") or row.get("date"))


def resolve_update_author_labels(author_ids: list[str]) -> dict[str, str]:
    """Resolve display names for author IDs on the current page only."""
    from app.perf_debug import perf_span

    unique = sorted({str(i).strip() for i in author_ids if str(i).strip()})
    if not unique:
        return {}

    try:
        from app.pages._core._data import employees_catalog_data_version

        emp_ver = employees_catalog_data_version()
    except Exception:
        emp_ver = 0

    cache_key = f"cu_authors:{emp_ver}:{','.join(unique)}"

    def _build() -> dict[str, str]:
        with perf_span("company_updates.author_lookup"):
            from app.services.repository import fetch_by_id

            lookup: dict[str, str] = {}
            for aid in unique:
                if aid in lookup:
                    continue
                if len(aid) >= 32 and aid.count("-") >= 4:
                    row = fetch_by_id("employees", aid) or fetch_by_id("user_profiles", aid)
                    if row:
                        name = str(row.get("name") or row.get("full_name") or "").strip()
                        if name:
                            lookup[aid] = name
                    continue
                if "@" in aid:
                    continue
                lookup[aid] = aid
            return lookup

    return page_data_cache_get(cache_key, _build)


def _resolve_created_by(row: dict[str, Any], lookup: dict[str, str]) -> str:
    raw = row.get("created_by_name") or row.get("created_by") or row.get("author") or row.get("author_name")
    if raw is None:
        return "Unknown user"
    text = str(raw).strip()
    if not text:
        return "Unknown user"
    if text in lookup:
        return lookup[text]
    if len(text) >= 32 and text.count("-") >= 4:
        return lookup.get(text, "Unknown user")
    return text


def to_list_row(row: dict[str, Any], *, author_lookup: dict[str, str]) -> dict[str, Any]:
    category = _norm_category(row.get("category"))
    status = _norm_status(row.get("status"), is_active=row.get("is_active"))
    audience = _norm_audience(row.get("audience") or row.get("visibility"))
    is_pinned = bool(row.get("pinned") or row.get("is_pinned"))
    return {
        "id": str(row.get("id") or ""),
        "title": str(row.get("title") or row.get("subject") or "Untitled Update"),
        "category": category,
        "audience": audience,
        "status": status,
        "priority": str(row.get("priority") or "Normal"),
        "is_pinned": is_pinned,
        "event_date": str(row.get("event_date") or "")[:10],
        "event_date_display": _fmt_event_date(row),
        "created_at": str(row.get("created_at") or row.get("date") or ""),
        "created_display": _fmt_created_date(row),
        "created_by": str(row.get("created_by") or row.get("posted_by") or ""),
        "created_by_name": str(row.get("created_by_name") or row.get("posted_by_name") or ""),
        "created_by_display": _resolve_created_by(row, author_lookup),
        "is_active": row.get("is_active") is not False,
    }


def _load_catalog_rows() -> tuple[list[dict[str, Any]], bool]:
    from app.services.updates_service import list_company_updates

    try:
        from app.pages._core._data import _DEMO_COMPANY_UPDATES
    except ImportError:
        _DEMO_COMPANY_UPDATES = []

    return list_company_updates(category="All Updates", demo=list(_DEMO_COMPANY_UPDATES))


def _sort_rows(rows: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    out = list(rows)
    if sort == "Oldest First":
        return sorted(out, key=lambda r: (_parse_ts(r.get("created_at")), str(r.get("title") or "").lower()))
    if sort == "Title A–Z":
        return sorted(out, key=lambda r: str(r.get("title") or "").lower())
    return sorted(
        out,
        key=lambda r: (_parse_ts(r.get("created_at")), str(r.get("title") or "").lower()),
        reverse=True,
    )


def _apply_search(rows: list[dict[str, Any]], search: str) -> list[dict[str, Any]]:
    q = str(search or "").strip().lower()
    if not q:
        return rows
    out: list[dict[str, Any]] = []
    for r in rows:
        hay = " ".join(
            str(r.get(k) or "")
            for k in ("title", "category", "audience", "status", "created_by_display")
        ).lower()
        if q in hay:
            out.append(r)
    return out


def _apply_column_filters(
    rows: list[dict[str, Any]],
    *,
    categories: list[str] | None,
    audiences: list[str] | None,
    statuses: list[str] | None,
) -> list[dict[str, Any]]:
    out = rows
    cats = [c for c in (categories or []) if c and c != "All"]
    if cats:
        out = [r for r in out if r.get("category") in cats]
    auds = [a for a in (audiences or []) if a and a != "All"]
    if auds:
        out = [r for r in out if r.get("audience") in auds]
    stats = [s for s in (statuses or []) if s and s != "All"]
    if stats:
        out = [r for r in out if r.get("status") in stats]
    return out


@dataclass(frozen=True)
class CompanyUpdatesPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    filter_options: dict[str, list[str]]
    is_live: bool
    warning: str | None = None


def load_company_updates_filter_options() -> dict[str, list[str]]:
    version = company_updates_data_version()

    def _build() -> dict[str, list[str]]:
        from app.perf_debug import perf_span

        with perf_span("company_updates.filter_options"):
            raw_rows, _ = _load_catalog_rows()
            list_rows = [to_list_row(r, author_lookup={}) for r in raw_rows]
            categories = sorted({str(r.get("category") or "") for r in list_rows if r.get("category")})
            audiences = sorted({str(r.get("audience") or "") for r in list_rows if r.get("audience")})
            statuses = sorted({str(r.get("status") or "") for r in list_rows if r.get("status")})
            return {"category": categories, "audience": audiences, "status": statuses}

    return page_data_cache_get(f"company_updates:filter_opts:v{version}", _build)


def list_company_updates_page(
    *,
    search: str = "",
    categories: list[str] | None = None,
    audiences: list[str] | None = None,
    statuses: list[str] | None = None,
    sort: str = "Newest First",
    page: int = 1,
    page_size: int = COMPANY_UPDATES_DEFAULT_PAGE_SIZE,
) -> CompanyUpdatesPage:
    from app.perf_debug import perf_span

    version = company_updates_data_version()
    cache_key = (
        f"company_updates:page:v{version}:s{search}:c{categories}:a{audiences}:"
        f"st{statuses}:sort{sort}:p{page}:sz{page_size}"
    )

    def _build() -> CompanyUpdatesPage:
        with perf_span("company_updates.list_query"):
            raw_rows, is_live = _load_catalog_rows()
            list_rows = [to_list_row(r, author_lookup={}) for r in raw_rows]
            filtered = _apply_column_filters(
                _apply_search(list_rows, search),
                categories=categories,
                audiences=audiences,
                statuses=statuses,
            )
            sorted_rows = _sort_rows(filtered, sort)
            total = len(sorted_rows)
            pg = max(1, int(page or 1))
            size = max(1, min(200, int(page_size or COMPANY_UPDATES_DEFAULT_PAGE_SIZE)))
            start = (pg - 1) * size
            page_rows = [dict(r) for r in sorted_rows[start : start + size]]
            page_author_ids: list[str] = []
            for row in page_rows:
                if str(row.get("created_by_name") or "").strip():
                    continue
                cid = str(row.get("created_by") or "").strip()
                if cid:
                    page_author_ids.append(cid)
            if page_author_ids:
                author_lookup = resolve_update_author_labels(page_author_ids)
                for row in page_rows:
                    row["created_by_display"] = _resolve_created_by(row, author_lookup)
            filter_options = load_company_updates_filter_options()
            warning = None if is_live else "Showing sample updates — connect Supabase for live data."
            return CompanyUpdatesPage(
                rows=page_rows,
                total_count=total,
                page=pg,
                page_size=size,
                filter_options=filter_options,
                is_live=is_live,
                warning=warning,
            )

    return page_data_cache_get(cache_key, _build)
