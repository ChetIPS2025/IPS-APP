"""Paginated Serialized Tools directory — focused kit items and reference hydration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.components.table_filters import apply_column_filters, has_active_column_filters
from app.pages._core._data import assets_catalog_data_version
from app.pages._core.page_data_cache import clear_page_data_cache_prefix, page_data_cache_get
from app.services.asset_classification_service import is_serialized_tab_asset
from app.services.asset_kits_service import _cached_kit_item_rows, normalize_kit_item
from app.services.asset_reference_service import get_job_labels_by_ids, get_people_labels_by_ids
from app.services.serialized_tool_service import is_serialized_tool_asset, serialized_tool_view
from app.services.status_maps import normalize_asset_status

_SERIALIZED_DIR_PREFIX = "assets_serialized_dir:"
_SERIALIZED_FILTER_PREFIX = "assets_serialized_filter_options:"
_SERIALIZED_TABLE_KEY = "assets_small_tools_list"
_PLACEHOLDER_SERIAL = frozenset({"—", "-", "none", "null", ""})


def _kit_catalog_version() -> int:
    try:
        from app.pages._core._data import assets_catalog_data_version as assets_ver

        return assets_ver()
    except Exception:
        return 0


def _clean_serial(raw: object) -> str:
    serial = str(raw or "").strip()
    return "" if serial.casefold() in _PLACEHOLDER_SERIAL else serial


def _kit_item_has_serial(item: dict[str, Any]) -> bool:
    return bool(_clean_serial(item.get("serial_number")))


def _serialized_row_id(row: dict[str, Any]) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        return f"kititem_{row.get('id') or ''}"
    return str(row.get("id") or "")


def _serialized_asset_number(row: dict[str, Any]) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        serial = _clean_serial(row.get("serial_number"))
        return serial or "—"
    for key in ("asset_number", "asset_id", "asset_no"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _serialized_name(row: dict[str, Any]) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        return str(row.get("item_name") or "—").strip() or "—"
    for key in ("asset_name", "name", "description"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _serialized_status(row: dict[str, Any]) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        return str(row.get("status") or "Present").strip() or "Present"
    return normalize_asset_status(row.get("status"))


def _serialized_model(row: dict[str, Any], *, view: dict[str, Any] | None = None) -> str:
    v = view or {}
    val = str(v.get("model_number") or v.get("model") or "").strip()
    if val and val != "—":
        return val
    val = str(row.get("model_number") or row.get("model") or "").strip()
    return val if val else "—"


def _serialized_trailer_label(row: dict[str, Any], *, view: dict[str, Any] | None = None) -> str:
    v = view or {}
    label = str(v.get("current_container_label") or "").strip()
    if label:
        return label
    if str(row.get("row_type") or "") == "kit_item":
        parent = str(row.get("parent_asset_name") or "—").strip() or "—"
        number = str(row.get("parent_asset_number") or "").strip()
        if number and number != "—":
            return f"{number} · {parent}"
        return parent
    return "—"


def _serialized_job_label(row: dict[str, Any], *, view: dict[str, Any] | None = None) -> str:
    v = view or {}
    return str(v.get("current_job_label") or "").strip() or "—"


def _serialized_condition(row: dict[str, Any], *, view: dict[str, Any] | None = None) -> str:
    v = view or {}
    return str(v.get("condition") or row.get("condition") or "Good").strip() or "Good"


def _serialized_serial(row: dict[str, Any], *, view: dict[str, Any] | None = None) -> str:
    v = view or {}
    serial = str(v.get("serial_number") or "").strip()
    if serial:
        return serial
    if str(row.get("row_type") or "") == "kit_item":
        return _serialized_asset_number(row)
    return _clean_serial(row.get("serial_number")) or "—"


def _filter_specs() -> list[tuple[str, Callable[[dict[str, Any]], str]]]:
    return [
        ("model_number", lambda r: str(r.get("_display_model") or "—")),
        ("trailer", lambda r: str(r.get("_display_trailer") or "—")),
        ("job", lambda r: str(r.get("_display_job") or "—")),
        ("status", lambda r: str(r.get("_display_status") or "—")),
        ("condition", lambda r: str(r.get("_display_condition") or "Good")),
    ]


@dataclass(frozen=True)
class SerializedToolsPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    filter_options: dict[str, list[str]]
    is_live: bool
    warning: str | None = None


def list_serialized_eligible_kit_items(
    *,
    serialized_asset_ids: set[str],
    parent_assets_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return kit items eligible for the Serialized Tools tab."""
    from app.perf_debug import perf_span

    version = _kit_catalog_version()

    def _build() -> list[dict[str, Any]]:
        with perf_span("assets.serialized.kit_items"):
            out: list[dict[str, Any]] = []
            for raw in _cached_kit_item_rows():
                item = normalize_kit_item(raw)
                child_id = str(item.get("child_asset_id") or "").strip()
                if child_id and child_id in serialized_asset_ids:
                    continue
                if not _kit_item_has_serial(item) and not child_id:
                    continue
                pid = str(item.get("parent_asset_id") or "").strip()
                parent = parent_assets_by_id.get(pid) or {}
                out.append(
                    {
                        **item,
                        "row_type": "kit_item",
                        "parent_asset_name": str(parent.get("asset_name") or parent.get("name") or "—").strip() or "—",
                        "parent_asset_number": str(parent.get("asset_number") or parent.get("asset_id") or "—").strip() or "—",
                        "parent_location": str(parent.get("location") or "—").strip() or "—",
                    }
                )
            return out

    return page_data_cache_get(f"{_SERIALIZED_DIR_PREFIX}kit_items:{version}", _build)


def _load_serialized_asset_rows() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    from app.perf_debug import perf_span
    from app.services.assets_service import list_assets

    version = assets_catalog_data_version()

    def _build() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
        with perf_span("assets.serialized.list_query"):
            rows, used = list_assets()
            serialized_assets: list[dict[str, Any]] = []
            assets_by_id: dict[str, dict[str, Any]] = {}
            parent_assets_by_id: dict[str, dict[str, Any]] = {}
            for row in rows:
                if not isinstance(row, dict):
                    continue
                aid = str(row.get("id") or "").strip()
                if not aid:
                    continue
                assets_by_id[aid] = row
                if is_serialized_tab_asset(row) or is_serialized_tool_asset(row):
                    serialized_assets.append({**row, "row_type": "asset"})
                elif str(row.get("parent_asset_id") or row.get("current_container_asset_id") or "").strip():
                    parent_assets_by_id[aid] = row
                else:
                    parent_assets_by_id[aid] = row
            tool_asset_ids = {str(a.get("id") or "").strip() for a in serialized_assets}
            kit_items = list_serialized_eligible_kit_items(
                serialized_asset_ids=tool_asset_ids,
                parent_assets_by_id={**assets_by_id, **parent_assets_by_id},
            )
            unified = serialized_assets + kit_items
            unified.sort(
                key=lambda r: (
                    _serialized_trailer_label(r).lower(),
                    _serialized_name(r).lower(),
                )
            )
            return unified, assets_by_id, not used

    return page_data_cache_get(f"{_SERIALIZED_DIR_PREFIX}catalog:{version}", _build)


def build_serialized_tool_display_row(
    row: dict[str, Any],
    *,
    assets_by_id: dict[str, dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
    jobs_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Normalize one serialized-tool row once for table display."""
    view = serialized_tool_view(
        row,
        assets_by_id=assets_by_id,
        employees_by_id=employees_by_id,
        jobs_by_id=jobs_by_id,
    )
    row_id = _serialized_row_id(row)
    thumb_asset = row
    if str(row.get("row_type") or "") == "kit_item":
        child_id = str(row.get("child_asset_id") or "").strip()
        if child_id and child_id in assets_by_id:
            thumb_asset = assets_by_id[child_id]
    elif str(row.get("row_type") or "") == "asset":
        thumb_asset = row
    return {
        **row,
        "_row_id": row_id,
        "_display_name": _serialized_name(row),
        "_display_model": _serialized_model(row, view=view),
        "_display_serial": _serialized_serial(row, view=view),
        "_display_trailer": _serialized_trailer_label(row, view=view),
        "_display_job": _serialized_job_label(row, view=view),
        "_display_status": _serialized_status(row) if str(row.get("row_type") or "") == "kit_item" else str(view.get("status") or _serialized_status(row)),
        "_display_condition": _serialized_condition(row, view=view),
        "_thumb_asset": thumb_asset,
        "_detail_asset_id": _detail_asset_id(row),
        "_detail_tab": _detail_tab(row),
    }


def _detail_asset_id(row: dict[str, Any]) -> str:
    if str(row.get("row_type") or "") == "kit_item":
        child_id = str(row.get("child_asset_id") or "").strip()
        if child_id:
            return child_id
        return str(row.get("parent_asset_id") or "").strip()
    return str(row.get("id") or "").strip()


def _detail_tab(row: dict[str, Any]) -> str:
    if str(row.get("row_type") or "") == "kit_item" and not str(row.get("child_asset_id") or "").strip():
        return "kit"
    return ""


def _collect_reference_ids(rows: list[dict[str, Any]]) -> tuple[set[str], set[str], set[str]]:
    employee_ids: set[str] = set()
    job_ids: set[str] = set()
    asset_ids: set[str] = set()
    for row in rows:
        for key in (
            "current_holder_employee_id",
            "current_employee_id",
            "assigned_to_employee_id",
        ):
            eid = str(row.get(key) or "").strip()
            if eid:
                employee_ids.add(eid)
        for key in ("assigned_job_id", "current_job_id", "job_id"):
            jid = str(row.get(key) or "").strip()
            if jid:
                job_ids.add(jid)
        for key in ("id", "parent_asset_id", "child_asset_id", "current_container_asset_id"):
            aid = str(row.get(key) or "").strip()
            if aid:
                asset_ids.add(aid)
    return employee_ids, job_ids, asset_ids


def _hydrate_page_rows(
    page_rows: list[dict[str, Any]],
    *,
    base_assets_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    from app.perf_debug import perf_span

    with perf_span("assets.serialized.row_hydration"):
        employee_ids, job_ids, asset_ids = _collect_reference_ids(page_rows)
        employees_by_id = get_people_labels_by_ids(sorted(employee_ids))
        jobs_by_id = get_job_labels_by_ids(sorted(job_ids))
        assets_by_id = dict(base_assets_by_id)
        missing_asset_ids = [aid for aid in sorted(asset_ids) if aid not in assets_by_id]
        if missing_asset_ids:
            from app.services.repository import fetch_by_id

            for aid in missing_asset_ids:
                row = fetch_by_id("assets", aid)
                if isinstance(row, dict):
                    assets_by_id[aid] = row
        return [
            build_serialized_tool_display_row(
                row,
                assets_by_id=assets_by_id,
                employees_by_id=employees_by_id,
                jobs_by_id=jobs_by_id,
            )
            for row in page_rows
        ]


def load_serialized_tools_filter_options() -> dict[str, list[str]]:
    version = assets_catalog_data_version()
    cache_key = f"{_SERIALIZED_FILTER_PREFIX}{version}"

    def _build() -> dict[str, list[str]]:
        from app.perf_debug import perf_span

        with perf_span("assets.serialized.filter_options"):
            catalog, assets_by_id, _ = _load_serialized_asset_rows()
            display_rows = _hydrate_page_rows(catalog, base_assets_by_id=assets_by_id)
            models: set[str] = set()
            trailers: set[str] = set()
            jobs: set[str] = set()
            statuses: set[str] = set()
            conditions: set[str] = set()
            for row in display_rows:
                model = str(row.get("_display_model") or "").strip()
                if model and model != "—":
                    models.add(model)
                trailer = str(row.get("_display_trailer") or "").strip()
                if trailer and trailer != "—":
                    trailers.add(trailer)
                job = str(row.get("_display_job") or "").strip()
                if job and job != "—":
                    jobs.add(job)
                statuses.add(str(row.get("_display_status") or "—"))
                conditions.add(str(row.get("_display_condition") or "Good"))
            return {
                "model_number": sorted(models),
                "trailer": sorted(trailers),
                "job": sorted(jobs),
                "status": sorted(statuses),
                "condition": sorted(conditions),
            }

    return page_data_cache_get(cache_key, _build)


def _apply_raw_filters(
    catalog: list[dict[str, Any]],
    *,
    search: str = "",
    statuses: list[str] | None = None,
    trailers: list[str] | None = None,
) -> list[dict[str, Any]]:
    out = list(catalog)
    query = str(search or "").strip()
    if query:
        ql = query.lower()
        out = [
            r
            for r in out
            if ql in _serialized_name(r).lower()
            or ql in str(r.get("serial_number") or r.get("model_number") or r.get("model") or "").lower()
            or ql in str(r.get("parent_asset_name") or "").lower()
            or ql in str(r.get("asset_number") or "").lower()
        ]
    status_val = statuses[0] if statuses and len(statuses) == 1 else None
    if status_val and str(status_val).strip() not in {"", "All Statuses"}:
        wanted = str(status_val).strip()
        out = [r for r in out if _serialized_status(r) == wanted]
    trailer_val = trailers[0] if trailers and len(trailers) == 1 else None
    if trailer_val and str(trailer_val).strip() not in {"", "All Trailers", "All Kits"}:
        wanted = str(trailer_val).strip()
        out = [
            r
            for r in out
            if _serialized_trailer_label(r) == wanted
            or str(r.get("parent_asset_name") or "").strip() == wanted
        ]
    return out


def list_serialized_tools_page(
    *,
    search: str = "",
    statuses: list[str] | None = None,
    trailers: list[str] | None = None,
    jobs: list[str] | None = None,
    conditions: list[str] | None = None,
    models: list[str] | None = None,
    page: int = 1,
    page_size: int = 25,
) -> SerializedToolsPage:
    from app.perf_debug import perf_span

    pg = max(1, int(page or 1))
    size = max(1, min(200, int(page_size or 25)))

    with perf_span("assets.serialized.list_query"):
        catalog, assets_by_id, is_live = _load_serialized_asset_rows()
        filter_options = load_serialized_tools_filter_options()
        filtered_raw = _apply_raw_filters(
            catalog,
            search=search,
            statuses=statuses,
            trailers=trailers,
        )
        filter_specs = _filter_specs()
        needs_column_filters = bool(models or jobs or conditions) or has_active_column_filters(
            _SERIALIZED_TABLE_KEY,
            [field for field, _ in filter_specs],
        )
        if needs_column_filters:
            hydrated = _hydrate_page_rows(filtered_raw, base_assets_by_id=assets_by_id)
            filtered_display = apply_column_filters(hydrated, _SERIALIZED_TABLE_KEY, filter_specs)
            total = len(filtered_display)
            start = (pg - 1) * size
            page_rows = filtered_display[start : start + size]
        else:
            total = len(filtered_raw)
            start = (pg - 1) * size
            page_raw = filtered_raw[start : start + size]
            page_rows = _hydrate_page_rows(page_raw, base_assets_by_id=assets_by_id)
        return SerializedToolsPage(
            rows=page_rows,
            total_count=total,
            page=pg,
            page_size=size,
            filter_options=filter_options,
            is_live=is_live,
            warning=None,
        )


def invalidate_serialized_tools_directory_cache() -> None:
    clear_page_data_cache_prefix(_SERIALIZED_DIR_PREFIX)
    clear_page_data_cache_prefix(_SERIALIZED_FILTER_PREFIX)


__all__ = [
    "SerializedToolsPage",
    "build_serialized_tool_display_row",
    "invalidate_serialized_tools_directory_cache",
    "list_serialized_eligible_kit_items",
    "list_serialized_tools_page",
    "load_serialized_tools_filter_options",
]
