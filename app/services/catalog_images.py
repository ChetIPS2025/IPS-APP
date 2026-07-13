"""
Unified catalog image resolver — one entry point for every list/detail thumbnail.

Domains:
  - Equipment / Serialized Tools (assets)
  - Small Tools (small_hand_tools / kit_item rows)
  - Inventory
  - Pricing Guide

UI: ``get_catalog_image_url`` → ``catalog_thumbnail_html`` / ``render_catalog_thumbnail``.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Any, Literal

import streamlit as st

CatalogRecordKind = Literal[
    "auto",
    "asset",
    "equipment",
    "serialized",
    "small_tool",
    "inventory",
    "pricing_guide",
]

_ASSET_PLACEHOLDER = "—"


@dataclass
class CatalogImageContext:
    """Optional lookup maps for small-tool name fallbacks."""

    assets_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    inventory_by_name: dict[str, dict[str, Any]] = field(default_factory=dict)
    pricing_by_name: dict[str, dict[str, Any]] = field(default_factory=dict)


def _clean_text(raw: object) -> str:
    return str(raw or "").strip()


def _name_key(raw: object) -> str:
    return _clean_text(raw).casefold()


def infer_catalog_record_kind(record: dict[str, Any]) -> str:
    """Best-effort record classification for image resolution."""
    row_type = _clean_text(record.get("row_type")).casefold()
    if row_type in {"hand_tool", "kit_item"}:
        return "small_tool"
    if _clean_text(record.get("source_asset_id")):
        return "small_tool"
    if _clean_text(record.get("tool_name")) and "quantity_on_hand" in record and not _clean_text(
        record.get("asset_name")
    ):
        return "small_tool"
    if _clean_text(record.get("sku")):
        return "inventory"
    if any(
        _clean_text(record.get(k))
        for k in ("item_key", "item_class", "linked_inventory_id", "linked_asset_id", "pricing_item_id")
    ) and not _clean_text(record.get("asset_name")):
        return "pricing_guide"
    if _clean_text(record.get("asset_name")) or record.get("tracking_type") is not None:
        return "asset"
    if _clean_text(record.get("name")) and record.get("qty_on_hand") is not None:
        return "inventory"
    return "asset"


def build_catalog_image_context(
    *,
    assets_by_id: dict[str, dict[str, Any]] | None = None,
    inventory_rows: list[dict[str, Any]] | None = None,
) -> CatalogImageContext:
    """Build shared name indexes used by small-tool image fallback."""
    inventory_by_name: dict[str, dict[str, Any]] = {}
    pricing_by_name: dict[str, dict[str, Any]] = {}
    from app.services.inventory_images import get_inventory_image_url
    if inventory_rows is None:
        from app.pages._core._data import load_inventory
        inventory_rows = load_inventory()
    for item in inventory_rows or []:
        key = _name_key(item.get("name") or item.get("item_name"))
        if key and key not in inventory_by_name and get_inventory_image_url(item):
            inventory_by_name[key] = item
    from app.services.pricing_guide_images import get_pricing_guide_image_url
    from app.services.pricing_guide_service import cached_pricing_guide_rows
    for row in cached_pricing_guide_rows(include_inactive=True) or []:
        key = _name_key(row.get("item_name") or row.get("name"))
        if key and key not in pricing_by_name and get_pricing_guide_image_url(row):
            pricing_by_name[key] = row
    if assets_by_id is None:
        from app.pages._core._data import load_assets
        assets_by_id = {
            str(a.get("id") or "").strip(): a
            for a in load_assets()
            if str(a.get("id") or "").strip()
        }
    return CatalogImageContext(
        assets_by_id=dict(assets_by_id or {}),
        inventory_by_name=inventory_by_name,
        pricing_by_name=pricing_by_name,
    )


def _resolve_small_tool_image_url(
    record: dict[str, Any],
    ctx: CatalogImageContext,
    *,
    thumbnail: bool,
    expires_in: int,
) -> str | None:
    from app.services.asset_images import get_asset_image_url, get_asset_thumbnail_url
    from app.services.inventory_images import get_inventory_image_url
    from app.services.pricing_guide_images import get_pricing_guide_image_url
    asset_url = get_asset_thumbnail_url if thumbnail else get_asset_image_url

    sid = _clean_text(record.get("source_asset_id"))
    if sid:
        url = asset_url(ctx.assets_by_id.get(sid) or {}, expires_in=expires_in)
        if url:
            return url

    name_key = _name_key(record.get("tool_name"))
    if name_key and name_key in ctx.inventory_by_name:
        url = get_inventory_image_url(ctx.inventory_by_name[name_key], expires_in=expires_in)
        if url:
            return url
    if name_key and name_key in ctx.pricing_by_name:
        url = get_pricing_guide_image_url(ctx.pricing_by_name[name_key], expires_in=expires_in)
        if url:
            return url
    if name_key:
        for asset in ctx.assets_by_id.values():
            if _name_key(asset.get("asset_name")) == name_key:
                url = asset_url(asset, expires_in=expires_in)
                if url:
                    return url
    return None


def get_catalog_image_url(
    record: dict[str, Any],
    *,
    kind: CatalogRecordKind = "auto",
    context: CatalogImageContext | None = None,
    thumbnail: bool = True,
    expires_in: int = 3600,
) -> str | None:
    """
    Resolve the best browser-safe image URL for any catalog row.

    Delegates to domain resolvers; small tools also use name/asset fallbacks via ``context``.
    """
    if not record:
        return None
    resolved_kind = infer_catalog_record_kind(record) if kind == "auto" else kind
    ctx = context or CatalogImageContext()

    from app.services.asset_images import get_asset_image_url, get_asset_thumbnail_url
    from app.services.inventory_images import get_inventory_image_url
    from app.services.pricing_guide_images import get_pricing_guide_image_url
    if resolved_kind == "inventory":
        return get_inventory_image_url(record, expires_in=expires_in)
    if resolved_kind == "pricing_guide":
        return get_pricing_guide_image_url(record, expires_in=expires_in)
    if resolved_kind == "small_tool":
        return _resolve_small_tool_image_url(record, ctx, thumbnail=thumbnail, expires_in=expires_in)

    asset_fn = get_asset_thumbnail_url if thumbnail else get_asset_image_url
    return asset_fn(record, expires_in=expires_in)


def catalog_thumbnail_html(
    record: dict[str, Any],
    *,
    kind: CatalogRecordKind = "auto",
    context: CatalogImageContext | None = None,
    css_class: str = "ips-asset-thumb-img",
    cell_class: str = "ips-asset-thumb-cell",
    alt: str = "Item image",
) -> str:
    """HTML thumbnail cell — asset-style dash placeholder or inventory 📦."""
    image_url = get_catalog_image_url(record, kind=kind, context=context)
    if image_url:
        return (
            f'<span class="{html.escape(cell_class)}">'
            f'<img class="{html.escape(css_class)}" '
            f'src="{html.escape(image_url, quote=True)}" alt="{html.escape(alt)}" />'
            f"</span>"
        )
    resolved_kind = infer_catalog_record_kind(record) if kind == "auto" else kind
    if resolved_kind == "inventory":
        from app.services.inventory_images import inventory_image_placeholder_html
        placeholder = inventory_image_placeholder_html()
    else:
        placeholder = f'<span class="ips-asset-thumb-placeholder">{_ASSET_PLACEHOLDER}</span>'
    return f'<span class="{html.escape(cell_class)}">{placeholder}</span>'


def render_catalog_thumbnail(
    record: dict[str, Any],
    *,
    kind: CatalogRecordKind = "auto",
    context: CatalogImageContext | None = None,
    width: int = 80,
) -> None:
    """Streamlit thumbnail using the unified resolver."""
    image_url = get_catalog_image_url(record, kind=kind, context=context)
    if image_url:
        st.image(image_url, width=width)
        return
    st.markdown(catalog_thumbnail_html(record, kind=kind, context=context), unsafe_allow_html=True)


__all__ = [
    "CatalogImageContext",
    "CatalogRecordKind",
    "build_catalog_image_context",
    "catalog_thumbnail_html",
    "get_catalog_image_url",
    "infer_catalog_record_kind",
    "render_catalog_thumbnail",
]
