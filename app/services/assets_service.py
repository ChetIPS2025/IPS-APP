"""
Assets module — Supabase reads/writes.

Schema assumptions: ``assets`` with asset_id, asset_name, category, location, department,
status, serial_number, manufacturer, model, notes, current_value, image fields.
"""

from __future__ import annotations

from typing import Any

from app.services.asset_images import (
    clear_asset_image_url_cache,
    get_asset_image_url as _get_asset_image_url,
    upload_asset_image as _upload_asset_image_storage,
)
from app.services.phase2_modules_service import (
    delete_asset,
    list_assets,
    normalize_asset,
    save_asset,
)
from app.services.repository import ServiceResult, clear_all_data_caches

__all__ = [
    "clear_assets_cache",
    "delete_asset",
    "get_asset",
    "get_asset_image_url",
    "get_assets",
    "list_assets",
    "normalize_asset",
    "save_asset",
    "update_asset",
    "upload_asset_image",
]


def clear_assets_cache() -> None:
    clear_all_data_caches()
    clear_asset_image_url_cache()


def get_assets() -> list[dict[str, Any]]:
    try:
        from app.pages._core._data import _DEMO_ASSETS
    except ImportError:
        from pages._core._data import _DEMO_ASSETS  # type: ignore
    rows, _ = list_assets(demo=list(_DEMO_ASSETS))
    return rows


def get_asset(asset_id: str) -> dict[str, Any] | None:
    aid = str(asset_id or "").strip()
    if not aid:
        return None
    for row in get_assets():
        if str(row.get("id") or "") == aid:
            return row
    return None


def update_asset(asset_id: str, data: dict[str, Any]) -> ServiceResult:
    result = save_asset(data, row_id=str(asset_id or "").strip())
    if result.ok:
        clear_assets_cache()
    return result


def get_asset_image_url(asset: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    return _get_asset_image_url(asset, expires_in=expires_in)


def upload_asset_image(
    asset_id: str,
    uploaded_file: Any,
    *,
    uploaded_by: str | None = None,
) -> ServiceResult:
    result = _upload_asset_image_storage(asset_id, uploaded_file, uploaded_by=uploaded_by)
    if result.ok:
        clear_assets_cache()
    return result
