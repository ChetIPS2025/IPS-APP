"""Lazy-loaded reference catalogs for kit forms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.pages._core._data import (
    assets_catalog_data_version,
    jobs_catalog_data_version,
    load_assets,
    load_employees,
    load_inventory,
    load_jobs,
)
from app.pages._core.page_data_cache import page_data_cache_get


@dataclass(frozen=True)
class KitReferenceOptions:
    employees: tuple[tuple[str, dict[str, Any]], ...]
    jobs: tuple[tuple[str, str], ...]
    assets: tuple[tuple[str, dict[str, Any]], ...]
    inventory: tuple[tuple[str, dict[str, Any]], ...]


_EMPTY = KitReferenceOptions((), (), (), ())


def _employee_options() -> tuple[tuple[str, dict[str, Any]], ...]:
    out: list[tuple[str, dict[str, Any]]] = [("— None —", {})]
    for e in load_employees():
        name = str(e.get("name") or "").strip()
        if name:
            out.append((name, e))
    return tuple(out)


def _job_options() -> tuple[tuple[str, str], ...]:
    opts: list[tuple[str, str]] = [("— None —", "")]
    for j in load_jobs():
        label = f"{j.get('job_number') or ''} — {j.get('job_name') or ''}".strip(" —")
        jid = str(j.get("id") or "")
        if jid:
            opts.append((label or jid, jid))
    return tuple(opts)


def _asset_options(exclude_asset_id: str) -> tuple[tuple[str, dict[str, Any]], ...]:
    out: list[tuple[str, dict[str, Any]]] = [("— None —", {})]
    for a in load_assets():
        aid = str(a.get("id") or "")
        if aid == exclude_asset_id:
            continue
        label = f"{a.get('asset_number') or ''} — {a.get('asset_name') or ''}".strip(" —")
        out.append((label or aid, a))
    return tuple(out)


def _inventory_options() -> tuple[tuple[str, dict[str, Any]], ...]:
    out: list[tuple[str, dict[str, Any]]] = [("— Select inventory item —", {})]
    for row in load_inventory():
        name = str(row.get("item_name") or row.get("name") or "").strip()
        if name:
            out.append((name, row))
    return tuple(out)


def get_kit_reference_options(
    *,
    include_employees: bool = False,
    include_jobs: bool = False,
    include_assets: bool = False,
    include_inventory: bool = False,
    exclude_asset_id: str = "",
) -> KitReferenceOptions:
    from app.perf_debug import perf_span

    if not any((include_employees, include_jobs, include_assets, include_inventory)):
        return _EMPTY

    version_parts = []
    if include_employees:
        version_parts.append(f"emp{len(load_employees())}")
    if include_jobs:
        version_parts.append(f"job{jobs_catalog_data_version()}")
    if include_assets:
        version_parts.append(f"ast{assets_catalog_data_version()}")
    if include_inventory:
        version_parts.append(f"inv{len(load_inventory())}")
    cache_key = f"kit_ref_{'_'.join(version_parts)}_{exclude_asset_id}"

    def _load() -> KitReferenceOptions:
        with perf_span("asset_kit.reference_options"):
            return KitReferenceOptions(
                employees=_employee_options() if include_employees else (),
                jobs=_job_options() if include_jobs else (),
                assets=_asset_options(exclude_asset_id) if include_assets else (),
                inventory=_inventory_options() if include_inventory else (),
            )

    return page_data_cache_get(cache_key, _load)
