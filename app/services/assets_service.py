"""

Assets module — Supabase reads/writes.



Schema assumptions: ``assets`` with asset_id, asset_name, category, location, department,

status, serial_number, manufacturer, model, notes, current_value, image fields, qr_token.

"""



from __future__ import annotations



import secrets

from datetime import datetime, timezone

from typing import Any

from urllib.parse import quote



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

from app.services.repository import ServiceResult, clear_all_data_caches, fetch_rows, insert_row, update_row



try:

    from app.config import settings

except ImportError:

    from config import settings  # type: ignore



_ASSET_TABLE = "assets"

_INSPECTIONS_TABLE = "asset_inspections"

_ISSUES_TABLE = "asset_issues"

_DOCS_TABLE = "documents_hub"



_DOCUMENT_TYPE_GROUPS: dict[str, tuple[str, ...]] = {

    "Manual": ("Manual", "manual"),

    "Parts Manual": ("Parts Manual", "parts manual", "PartsManual"),

    "Safety Sheet": ("Safety Sheet", "safety sheet", "Safety"),

    "Maintenance Document": ("Maintenance Document", "Maintenance", "maintenance document", "Maintenance Docs"),

    "Other": ("Other", "Warranty", "Registration", "Inspection Form"),

}



__all__ = [

    "clear_assets_cache",

    "create_asset_inspection",

    "create_asset_issue",

    "delete_asset",

    "ensure_asset_qr_tokens",

    "generate_asset_qr_value",

    "get_asset",

    "get_asset_by_qr",

    "get_asset_document_view_url",

    "get_asset_documents",

    "get_asset_image_url",

    "get_asset_inspections",

    "get_asset_issues",

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





def generate_asset_qr_token() -> str:

    return secrets.token_urlsafe(24)





def _asset_mobile_scan_url(*, asset_id: str, qr_token: str) -> str:

    base = str(getattr(settings, "app_base_url", "") or "").strip().rstrip("/")

    aid = quote(str(asset_id or "").strip(), safe="")

    token = quote(str(qr_token or "").strip(), safe="")

    if not base or not aid or not token:

        return ""

    return f"{base}/?scan=asset&asset_id={aid}&token={token}"





def _ensure_asset_qr_token(row: dict[str, Any]) -> str:

    token = str(row.get("qr_token") or "").strip()

    if token:

        return token

    iid = str(row.get("id") or "").strip()

    if not iid:

        return ""

    token = generate_asset_qr_token()

    scan_url = _asset_mobile_scan_url(asset_id=iid, qr_token=token)

    payload: dict[str, Any] = {"qr_token": token}

    if scan_url:

        payload["qr_value"] = scan_url

        payload["qr_code_value"] = scan_url

    try:

        from app.pages._core._crud import is_demo_id

    except ImportError:

        from pages._core._crud import is_demo_id  # type: ignore

    if not is_demo_id(iid):

        update_row(_ASSET_TABLE, payload, {"id": iid})

        clear_assets_cache()

    return token





def generate_asset_qr_value(asset: dict[str, Any]) -> str:

    """Build mobile scan URL using APP_BASE_URL, asset id, and qr_token."""

    row = dict(asset or {})

    iid = str(row.get("id") or "").strip()

    if not row.get("qr_token"):

        row["qr_token"] = _ensure_asset_qr_token(row)

    token = str(row.get("qr_token") or "").strip()

    cached = str(row.get("qr_value") or "").strip()

    if cached.startswith("http") and "scan=asset" in cached:

        return cached

    if iid and token:

        url = _asset_mobile_scan_url(asset_id=iid, qr_token=token)

        if url:

            return url

    legacy = str(row.get("qr_code_value") or "").strip()

    return legacy





def ensure_asset_qr_tokens(assets: list[dict[str, Any]] | None = None) -> ServiceResult:

    """Generate and persist missing qr_token values without rotating existing tokens."""

    rows = assets if assets is not None else get_assets()

    updated = 0

    for row in rows:

        iid = str(row.get("id") or "").strip()

        if not iid or str(row.get("qr_token") or "").strip():

            continue

        token = generate_asset_qr_token()

        norm = normalize_asset({**row, "qr_token": token})

        scan_url = generate_asset_qr_value(norm)

        payload: dict[str, Any] = {"qr_token": token}

        if scan_url:

            payload["qr_value"] = scan_url

            payload["qr_code_value"] = scan_url

        try:

            from app.pages._core._crud import is_demo_id

        except ImportError:

            from pages._core._crud import is_demo_id  # type: ignore

        if is_demo_id(iid):

            continue

        result = update_row(_ASSET_TABLE, payload, {"id": iid})

        if result.ok:

            updated += 1

    if updated:

        clear_assets_cache()

    return ServiceResult(ok=True, data={"updated": updated})





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

        rid = str(row.get("id") or "").strip()

        num = str(row.get("asset_number") or "").strip()

        if aid == rid or aid.upper() == num.upper():

            return row

    return _fetch_asset_from_db(aid)





def _fetch_asset_from_db(match: str) -> dict[str, Any] | None:

    try:

        from app.db import fetch_by_match_admin

    except ImportError:

        from db import fetch_by_match_admin  # type: ignore

    val = str(match or "").strip()

    if not val:

        return None

    for key in ("id", "asset_id"):

        rows = fetch_by_match_admin(_ASSET_TABLE, {key: val}, limit=3) or []

        if len(rows) == 1:

            return normalize_asset(rows[0])

    return None





def _db_fetch_by_match(table: str, match: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:

    try:

        from app.db import fetch_by_match_admin

    except ImportError:

        from db import fetch_by_match_admin  # type: ignore

    try:

        return fetch_by_match_admin(table, match, limit=limit) or []

    except Exception:

        return []





def get_asset_by_qr(

    *,

    asset_id: str | None = None,

    asset_number: str | None = None,

    token: str | None = None,

) -> ServiceResult:

    """Resolve asset from QR params; validate qr_token when present."""

    iid = str(asset_id or "").strip()

    num = str(asset_number or "").strip()

    token_s = str(token or "").strip()

    rows: list[dict[str, Any]] = []



    if iid:

        rows = _db_fetch_by_match(_ASSET_TABLE, {"id": iid}, limit=3)

        if not rows:

            cached = get_asset(iid)

            if cached:

                rows = [cached]

    elif num:

        rows = _db_fetch_by_match(_ASSET_TABLE, {"asset_id": num}, limit=5)

        if len(rows) != 1:

            all_rows, _ = fetch_rows(_ASSET_TABLE, limit=8000, alt_tables=("asset_database",))

            matches = [

                r for r in all_rows

                if str(r.get("asset_id") or r.get("asset_number") or "").strip().upper() == num.upper()

            ]

            if len(matches) == 1:

                rows = matches

            elif len(matches) > 1:

                return ServiceResult(ok=False, error="Ambiguous asset number.")

    else:

        return ServiceResult(ok=False, error="Missing asset identifier.")



    if not rows:

        return ServiceResult(ok=False, error="Asset not found.")

    if len(rows) > 1:

        return ServiceResult(ok=False, error="Ambiguous asset match.")



    item = normalize_asset(rows[0])

    stored_token = str(item.get("qr_token") or "").strip()

    try:

        from app.pages._core._crud import is_demo_id

    except ImportError:

        from pages._core._crud import is_demo_id  # type: ignore

    is_demo = is_demo_id(str(item.get("id") or ""))



    if stored_token and token_s and token_s != stored_token:

        return ServiceResult(ok=False, error="Invalid asset QR code.")

    if stored_token and not token_s:

        return ServiceResult(ok=False, error="Invalid asset QR code.")

    if not stored_token and not is_demo:

        item["qr_token"] = _ensure_asset_qr_token(item)

        if token_s and token_s != item.get("qr_token"):

            return ServiceResult(ok=False, error="Invalid asset QR code.")

    elif not stored_token and is_demo and token_s:

        item["qr_token"] = token_s



    return ServiceResult(ok=True, data=item)





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





def _normalize_doc_row(row: dict[str, Any]) -> dict[str, Any]:

    return {

        "id": str(row.get("id") or ""),

        "file_name": str(row.get("file_name") or row.get("name") or ""),

        "doc_type": str(row.get("doc_type") or row.get("document_type") or ""),

        "linked_module": str(row.get("linked_module") or ""),

        "linked_record_id": str(row.get("linked_record_id") or ""),

        "linked_ref": str(row.get("linked_ref") or ""),

        "storage_path": str(row.get("storage_path") or ""),

        "file_url": str(row.get("file_url") or row.get("attachment_url") or ""),

        "is_restricted": bool(row.get("is_restricted")),

        "uploaded_by": str(row.get("uploaded_by") or ""),

        "created_at": str(row.get("created_at") or row.get("upload_date") or "")[:19],

    }





def get_asset_document_view_url(doc: dict[str, Any], *, expires_in: int = 3600) -> str | None:

    public = str(doc.get("file_url") or doc.get("attachment_url") or "").strip()

    if public.startswith("http"):

        return public

    path = str(doc.get("storage_path") or "").strip()

    if not path:

        return None

    try:

        from app.db import create_signed_url

    except ImportError:

        from db import create_signed_url  # type: ignore

    try:

        signed = create_signed_url(path, expires_in=expires_in)

        return str(signed or "").strip() or None

    except Exception:

        return None





def get_asset_documents(asset_id: str, *, include_restricted: bool = False) -> list[dict[str, Any]]:

    """Documents linked to an asset via documents_hub."""

    aid = str(asset_id or "").strip()

    if not aid:

        return []

    asset = get_asset(aid) or {}

    asset_num = str(asset.get("asset_number") or "").strip()

    rows, _ = fetch_rows(_DOCS_TABLE, limit=5000, order_by="upload_date", alt_tables=("documents",))

    out: list[dict[str, Any]] = []

    for row in rows:

        mod = str(row.get("linked_module") or "").strip().lower()

        if mod not in {"assets", "asset"}:

            continue

        linked_id = str(row.get("linked_record_id") or "").strip()

        linked_ref = str(row.get("linked_ref") or "").strip()

        if linked_id and linked_id != aid:

            continue

        if not linked_id and linked_ref and asset_num and linked_ref != asset_num:

            continue

        doc = _normalize_doc_row(row)

        if doc["is_restricted"] and not include_restricted:

            continue

        doc["view_url"] = get_asset_document_view_url(doc)

        out.append(doc)

    out.sort(key=lambda d: str(d.get("created_at") or ""), reverse=True)

    return out





def get_asset_documents_grouped(asset_id: str, *, include_restricted: bool = False) -> dict[str, list[dict[str, Any]]]:

    docs = get_asset_documents(asset_id, include_restricted=include_restricted)

    grouped: dict[str, list[dict[str, Any]]] = {k: [] for k in _DOCUMENT_TYPE_GROUPS}

    grouped["Other Attachments"] = []

    for doc in docs:

        dtype = str(doc.get("doc_type") or "").strip()

        placed = False

        for group, variants in _DOCUMENT_TYPE_GROUPS.items():

            if any(dtype.lower() == v.lower() for v in variants):

                grouped[group].append(doc)

                placed = True

                break

        if not placed:

            grouped["Other Attachments"].append(doc)

    return grouped





def get_asset_inspections(asset_id: str, *, limit: int = 100) -> list[dict[str, Any]]:

    aid = str(asset_id or "").strip()

    if not aid:

        return []

    rows = _db_fetch_by_match(_INSPECTIONS_TABLE, {"asset_id": aid}, limit=limit)

    if not rows:

        rows, _ = fetch_rows(_INSPECTIONS_TABLE, limit=limit, order_by="inspection_date")

        rows = [r for r in rows if str(r.get("asset_id") or "") == aid]

    out = []

    for row in rows:

        out.append({

            "id": str(row.get("id") or ""),

            "asset_id": aid,

            "inspector_name": str(row.get("inspector_name") or row.get("inspector") or "—"),

            "inspector_phone": str(row.get("inspector_phone") or ""),

            "inspection_date": str(row.get("inspection_date") or row.get("created_at") or "")[:19],

            "condition": str(row.get("condition") or row.get("status") or "Good"),

            "notes": str(row.get("notes") or row.get("issues_found") or ""),

            "location": str(row.get("location") or ""),

            "hours_miles": row.get("hours_miles"),

        })

    out.sort(key=lambda r: str(r.get("inspection_date") or ""), reverse=True)

    return out





def get_asset_issues(asset_id: str, *, limit: int = 100) -> list[dict[str, Any]]:

    aid = str(asset_id or "").strip()

    if not aid:

        return []

    rows = _db_fetch_by_match(_ISSUES_TABLE, {"asset_id": aid}, limit=limit)

    out = []

    for row in rows:

        out.append({

            "id": str(row.get("id") or ""),

            "severity": str(row.get("severity") or "Medium"),

            "description": str(row.get("description") or ""),

            "reported_by_name": str(row.get("reported_by_name") or ""),

            "reported_by_phone": str(row.get("reported_by_phone") or ""),

            "status": str(row.get("status") or "Open"),

            "created_at": str(row.get("created_at") or "")[:19],

        })

    out.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)

    return out





def create_asset_inspection(asset_id: str, data: dict[str, Any]) -> ServiceResult:

    aid = str(asset_id or "").strip()

    if not aid:

        return ServiceResult(ok=False, error="Asset is required.")

    now = datetime.now(timezone.utc)

    condition = str(data.get("condition") or "Good").strip()

    inspector_name = str(data.get("inspector_name") or "").strip()

    if not inspector_name:

        return ServiceResult(ok=False, error="Inspector name is required.")



    payload: dict[str, Any] = {

        "asset_id": aid,

        "inspection_type": str(data.get("inspection_type") or "Field Inspection"),

        "inspection_date": str(data.get("inspection_date") or now.date().isoformat()),

        "inspector": inspector_name,

        "inspector_name": inspector_name,

        "inspector_phone": str(data.get("inspector_phone") or "")[:50] or None,

        "inspector_user_id": data.get("inspector_user_id"),

        "inspector_employee_id": data.get("inspector_employee_id"),

        "status": condition,

        "condition": condition,

        "hours_miles": data.get("hours_miles"),

        "location": str(data.get("location") or "")[:500] or None,

        "visual_damage": bool(data.get("visual_damage")),

        "safety_guards_ok": bool(data.get("safety_guards_ok", True)),

        "leaks_present": bool(data.get("leaks_present")),

        "tires_wheels_ok": bool(data.get("tires_wheels_ok", True)),

        "controls_working": bool(data.get("controls_working", True)),

        "emergency_stop_working": bool(data.get("emergency_stop_working", True)),

        "labels_present": bool(data.get("labels_present", True)),

        "clean_usable": bool(data.get("clean_usable", True)),

        "notes": str(data.get("notes") or "")[:2000],

        "issues_found": str(data.get("notes") or "")[:2000],

        "photo_path": str(data.get("photo_path") or "") or None,

        "photo_url": str(data.get("photo_url") or "") or None,

    }

    try:

        from app.pages._core._crud import is_demo_id

    except ImportError:

        from pages._core._crud import is_demo_id  # type: ignore

    if is_demo_id(aid):

        return ServiceResult(ok=True, data={"id": "demo-inspection", **payload})



    result = insert_row(_INSPECTIONS_TABLE, payload)

    if result.ok:

        clear_assets_cache()

    return result





def create_asset_issue(asset_id: str, data: dict[str, Any]) -> ServiceResult:

    aid = str(asset_id or "").strip()

    description = str(data.get("description") or "").strip()

    if not aid:

        return ServiceResult(ok=False, error="Asset is required.")

    if not description:

        return ServiceResult(ok=False, error="Description is required.")



    payload: dict[str, Any] = {

        "asset_id": aid,

        "severity": str(data.get("severity") or "Medium"),

        "description": description[:4000],

        "reported_by_name": str(data.get("reported_by_name") or "")[:500] or None,

        "reported_by_phone": str(data.get("reported_by_phone") or "")[:50] or None,

        "photo_path": str(data.get("photo_path") or "") or None,

        "photo_url": str(data.get("photo_url") or "") or None,

        "status": "Open",

    }

    try:

        from app.pages._core._crud import is_demo_id

    except ImportError:

        from pages._core._crud import is_demo_id  # type: ignore

    if is_demo_id(aid):

        return ServiceResult(ok=True, data={"id": "demo-issue", **payload})



    result = insert_row(_ISSUES_TABLE, payload)

    if result.ok:

        clear_assets_cache()

    return result


