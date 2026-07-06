"""Post-assignment hooks that auto-create rental equipment inspections."""

from __future__ import annotations

import logging
from typing import Any

try:
    from app.services.rental_equipment_inspection_service import create_auto_inspection, is_rental_equipment
    from app.services.repository import fetch_by_id
except ImportError:
    from services.rental_equipment_inspection_service import create_auto_inspection, is_rental_equipment  # type: ignore
    from services.repository import fetch_by_id  # type: ignore

_LOG = logging.getLogger(__name__)


def _customer_id_for_job(job_id: str | None) -> str | None:
    jid = str(job_id or "").strip()
    if not jid:
        return None
    job = fetch_by_id("jobs", jid)
    if not isinstance(job, dict):
        return None
    cid = str(job.get("customer_id") or "").strip()
    return cid or None


def notify_rental_equipment_assigned(
    asset: dict[str, Any] | None,
    *,
    job_id: str | None = None,
) -> None:
    """Create a checkout inspection draft when rental equipment is assigned to a job."""
    if not asset or not is_rental_equipment(asset):
        return
    aid = str(asset.get("id") or "").strip()
    jid = str(job_id or asset.get("assigned_job_id") or "").strip() or None
    if not aid or not jid:
        return
    try:
        create_auto_inspection(
            asset_id=aid,
            inspection_type="checkout",
            job_id=jid,
            customer_id=_customer_id_for_job(jid),
        )
    except Exception as exc:
        _LOG.warning("checkout inspection auto-create failed: %s", exc)


def notify_rental_equipment_returned(
    asset: dict[str, Any] | None,
    *,
    job_id: str | None = None,
) -> None:
    """Create a return inspection draft when rental equipment is returned."""
    if not asset or not is_rental_equipment(asset):
        return
    aid = str(asset.get("id") or "").strip()
    if not aid:
        return
    jid = str(job_id or asset.get("assigned_job_id") or "").strip() or None
    try:
        create_auto_inspection(
            asset_id=aid,
            inspection_type="return",
            job_id=jid,
            customer_id=_customer_id_for_job(jid),
        )
    except Exception as exc:
        _LOG.warning("return inspection auto-create failed: %s", exc)


def notify_asset_job_assignment_changed(
    asset_id: str,
    *,
    previous_job_id: str | None,
    new_job_id: str | None,
) -> None:
    """Fire checkout/return drafts when assigned_job_id changes on a rental asset."""
    aid = str(asset_id or "").strip()
    if not aid:
        return
    asset = fetch_by_id("assets", aid)
    if not isinstance(asset, dict):
        return
    prev = str(previous_job_id or "").strip() or None
    new = str(new_job_id or "").strip() or None
    if prev == new:
        return
    if new and new != prev:
        notify_rental_equipment_assigned(asset, job_id=new)
    if prev and not new:
        notify_rental_equipment_returned({**asset, "assigned_job_id": prev}, job_id=prev)
