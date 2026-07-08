"""
Mobile-first field scan: inventory_items (consumable use) + reusable tools on public.assets (checkout).

Schema assumptions (see sql/015, 027, 028):
- inventory_items: id, item_name, sku, qr_code_value, quantity_on_hand, reorder_point,
  unit_cost, storage_location, vendor, is_active, …
- inventory_transactions: inventory_item_id, qty (negative = issue), txn_type,
  job_id, employee_id, profile_id, created_by, notes, created_at,
  scanned_by_user_id, scanned_by_name, device_label (sql/030_inventory_txn_scan_audit.sql)
- job_materials: job_id, inventory_item_id, item_name, quantity, unit_cost, line_total, notes
- assets / tool_transactions: reusable tool checkout (sql/029_tool_checkout.sql)
"""
from __future__ import annotations

import html
import io
import urllib.parse
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
from typing import Any

import streamlit as st

try:
    from mobile_ui import ensure_narrow_viewport_detected
except ImportError:
    from app.mobile_ui import ensure_narrow_viewport_detected  # type: ignore

try:
    from app.device_label import (
        device_family_from_user_agent,
        ensure_inventory_device_suffix_initialized,
        format_device_label,
        persist_device_label_to_browser,
        request_user_agent,
    )
except ImportError:
    from device_label import (  # type: ignore
        device_family_from_user_agent,
        ensure_inventory_device_suffix_initialized,
        format_device_label,
        persist_device_label_to_browser,
        request_user_agent,
    )

try:
    from app.auth import current_profile, current_role, is_authenticated
    from app.ui.page_shell import render_page_header
    from app.ui import role_can_open_page
    from app.db import (
        create_signed_url,
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from app.services.job_service import (
        build_job_dropdown_label_maps,
        job_row_select_label,
        sort_jobs_by_number_then_name,
    )
    from app.ui.streamlit_perf import fragment
except ImportError:
    from auth import current_profile, current_role, is_authenticated  # type: ignore
    from branding import render_header  # type: ignore
    from ui import role_can_open_page  # type: ignore
    from db import (  # type: ignore
        create_signed_url,
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from services.job_service import (  # type: ignore
        build_job_dropdown_label_maps,
        job_row_select_label,
        sort_jobs_by_number_then_name,
    )
    from ui.streamlit_perf import fragment  # type: ignore

_INV = "inventory_items"
_TXN = "inventory_transactions"
_JM = "job_materials"
_ASSETS = "assets"
_TOOL_TXN = "tool_transactions"

try:
    from app.services.tracking_terminology import (
        INVENTORY_ADJUST_LABEL,
        INVENTORY_USE_IN_SHOP_LABEL,
        INVENTORY_USE_ON_JOB_LABEL,
        inventory_action_label,
        serialized_tool_action_label,
    )
except ImportError:
    from services.tracking_terminology import (  # type: ignore
        INVENTORY_ADJUST_LABEL,
        INVENTORY_USE_IN_SHOP_LABEL,
        INVENTORY_USE_ON_JOB_LABEL,
        inventory_action_label,
        serialized_tool_action_label,
    )

try:
    from app.utils.formatting import fmt_money
except ImportError:
    from utils.formatting import fmt_money  # type: ignore

_ISSUE_TYPES = (INVENTORY_USE_ON_JOB_LABEL, INVENTORY_ADJUST_LABEL, INVENTORY_USE_IN_SHOP_LABEL)
_TXN_MAP = {
    INVENTORY_USE_ON_JOB_LABEL: "TO_JOB",
    INVENTORY_ADJUST_LABEL: "ADJUST",
    INVENTORY_USE_IN_SHOP_LABEL: "SHOP",
}


def _inject_inv_scan_mobile_css() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlock"]:has(span.ips-inv-scan-scope) label {
            font-size: 1rem !important;
        }
        div[data-testid="stVerticalBlock"]:has(span.ips-inv-scan-scope) input {
            min-height: 48px !important;
            font-size: 1.05rem !important;
        }
        div[data-testid="stVerticalBlock"]:has(span.ips-inv-scan-scope) button {
            min-height: 48px !important;
            font-size: 1rem !important;
        }
        div[data-testid="stVerticalBlock"]:has(span.ips-inv-scan-scope) [data-testid="stNumberInput"] input {
            min-height: 48px !important;
        }
        div[data-testid="stVerticalBlock"]:has(span.ips-inv-scan-scope) [data-baseweb="select"] > div {
            min-height: 48px !important;
        }
        div[data-testid="stVerticalBlock"]:has(span.ips-inv-qr-scan-scope) label {
            font-size: 1rem !important;
            font-weight: 700 !important;
        }
        div[data-testid="stVerticalBlock"]:has(span.ips-inv-qr-scan-scope) input {
            min-height: 48px !important;
            font-size: 1.1rem !important;
            text-align: center !important;
        }
        div[data-testid="stVerticalBlock"]:has(span.ips-inv-qr-scan-scope) [data-baseweb="select"] > div {
            min-height: 48px !important;
            font-size: 1rem !important;
        }
        div[data-testid="stVerticalBlock"]:has(span.ips-inv-qr-scan-scope) button {
            min-height: 48px !important;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
        }
        div[data-testid="stVerticalBlock"]:has(span.ips-inv-qr-scan-scope) button[kind="primary"] {
            margin-top: 0.35rem !important;
        }
        .ips-inv-low-banner {
            background: rgba(251, 191, 36, 0.12);
            border: 1px solid rgba(251, 191, 36, 0.45);
            border-radius: 10px;
            padding: 10px 12px;
            margin: 8px 0;
            color: #fcd34d;
            font-weight: 600;
        }
        .ips-tool-scan-banner {
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid rgba(56, 189, 248, 0.45);
            border-radius: 10px;
            padding: 10px 12px;
            margin: 8px 0;
            color: #7dd3fc;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _qty_on_hand(row: dict) -> int:
    try:
        from app.utils.inventory_quantity import read_inventory_quantity
    except ImportError:
        from utils.inventory_quantity import read_inventory_quantity  # type: ignore
    return read_inventory_quantity(row, "quantity_on_hand", "qty_on_hand", "quantity")


def _reorder(row: dict) -> int:
    try:
        from app.utils.inventory_quantity import parse_inventory_quantity
    except ImportError:
        from utils.inventory_quantity import parse_inventory_quantity  # type: ignore
    try:
        return parse_inventory_quantity(row.get("reorder_point"), allow_zero=True, field_name="Reorder point")
    except ValueError:
        return 0


def _is_low_stock(row: dict) -> bool:
    return _qty_on_hand(row) <= _reorder(row)


def _profile_employee_id() -> str | None:
    prof = current_profile()
    em = str(prof.get("email") or "").strip().lower()
    if not em:
        return None
    try:
        rows = fetch_table_admin("employees", columns="id,email", limit=5000)
    except Exception:
        return None
    for r in rows:
        if str(r.get("email") or "").strip().lower() == em:
            return str(r.get("id") or "") or None
    return None


def _profile_uuid() -> str | None:
    uid = str(current_profile().get("id") or "").strip()
    return uid or None


def _created_by_label() -> str:
    p = current_profile()
    return str(p.get("email") or p.get("id") or "").strip()


def _auth_user_id_str() -> str | None:
    u = st.session_state.get("auth_user")
    if u is None:
        return None
    uid = getattr(u, "id", None)
    if uid is None and isinstance(u, dict):
        uid = u.get("id")
    s = str(uid or "").strip()
    return s or None


_QR_SCAN_ACTOR_SESSION_KEY = "ips_qr_scan_actor_session"


def _pin_qr_scan_actor_session() -> dict[str, Any]:
    """Capture scanner identity once per scan workflow (field phone or office scan page)."""
    existing = st.session_state.get(_QR_SCAN_ACTOR_SESSION_KEY)
    if isinstance(existing, dict) and str(existing.get("scanned_by_name") or "").strip():
        return existing
    ua = request_user_agent()
    suf = str(st.session_state.get("ips_inv_device_suffix") or "")
    device = str(st.session_state.get("inv_scan_device_display") or "").strip()
    if not device:
        device = format_device_label(device_family_from_user_agent(ua), suf)
    name = _scan_profile_name() or str(st.session_state.get("inv_scan_manual_actor") or "").strip()
    actor = {
        "scanned_by_user_id": _scan_profile_user_id() or _auth_user_id_str(),
        "scanned_by_name": name or "Field scanner",
        "employee_id": _profile_employee_id(),
        "device_label": device,
    }
    st.session_state[_QR_SCAN_ACTOR_SESSION_KEY] = actor
    return actor


def _scan_audit_fields(*, device_label: str, manual_actor: str) -> dict[str, Any]:
    """
    Payload keys for sql/030 scan audit columns. Omitted keys are not sent.
    If no profile/auth id, require manual_actor (trimmed) for scanned_by_name.
    """
    prof = current_profile()
    pid = str(prof.get("id") or "").strip() or None
    aid = _auth_user_id_str()
    scanned_uid = pid or aid
    name = (
        str(prof.get("full_name") or "").strip()
        or str(prof.get("email") or "").strip()
        or str(manual_actor or "").strip()
    )
    if not name.strip():
        name = str(aid or "Unknown")[:500]
    out: dict[str, Any] = {}
    nm = name.strip() or str(manual_actor or "").strip() or "Unknown"
    out["scanned_by_name"] = nm[:500]
    if scanned_uid:
        out["scanned_by_user_id"] = scanned_uid[:200]
    dv = str(device_label or "").strip()
    if dv:
        out["device_label"] = dv[:200]
    return out


def _qr_scan_logging_context() -> dict[str, Any]:
    pinned = st.session_state.get(_QR_SCAN_ACTOR_SESSION_KEY)
    if isinstance(pinned, dict):
        return {
            "scanned_by_user_id": pinned.get("scanned_by_user_id"),
            "scanned_by_name": pinned.get("scanned_by_name"),
            "employee_id": pinned.get("employee_id"),
            "device_label": pinned.get("device_label"),
        }
    ua = request_user_agent()
    suf = str(st.session_state.get("ips_inv_device_suffix") or "")
    device = str(st.session_state.get("inv_scan_device_display") or "").strip()
    if not device:
        device = format_device_label(device_family_from_user_agent(ua), suf)
    return {
        "scanned_by_user_id": _scan_profile_user_id() or _auth_user_id_str(),
        "scanned_by_name": _scan_profile_name() or _created_by_label(),
        "employee_id": _profile_employee_id(),
        "device_label": device,
    }


def _inventory_qr_display_value(item: dict[str, Any], *, fallback: str = "") -> str:
    try:
        from app.services.inventory_display_helpers import resolve_inventory_qr_value
    except ImportError:
        from services.inventory_display_helpers import resolve_inventory_qr_value  # type: ignore
    return resolve_inventory_qr_value(item) or fallback


def _asset_qr_display_value(asset: dict[str, Any], *, fallback: str = "") -> str:
    return str(asset.get("qr_code_value") or asset.get("asset_id") or fallback or "").strip()


def _log_qr_scan_event(**kwargs: Any) -> None:
    try:
        from app.services.qr_scan_event_service import record_qr_scan_event
    except ImportError:
        from services.qr_scan_event_service import record_qr_scan_event  # type: ignore
    ctx = _qr_scan_logging_context()
    merged = {**ctx, **kwargs}
    for key in ("scanned_by_user_id", "scanned_by_name", "scanned_by_phone", "employee_id", "device_label"):
        if kwargs.get(key):
            merged[key] = kwargs[key]
    record_qr_scan_event(**merged)


def _log_qr_scan_opened_once(
    *,
    qr_value: str,
    item_type: str,
    item_name: str,
    inventory_item_id: str | None = None,
    asset_id: str | None = None,
    source: str = "qr_scan",
) -> None:
    """Dedupe page-view opens locally; do not write browse events to scan history."""
    dedupe = f"_ips_qr_evt_open_{item_type}_{inventory_item_id or asset_id or qr_value}"
    st.session_state[dedupe] = True


def _inv_item_thumb_display(item: dict) -> None:
    """Small item photo or placeholder (scan screen)."""
    try:
        from app.services.inventory_images import render_inventory_item_thumbnail
    except ImportError:
        from services.inventory_images import render_inventory_item_thumbnail  # type: ignore
    render_inventory_item_thumbnail(item, width=80)


def _item_model_line(item: dict[str, Any], sku: str) -> str:
    for key in ("model", "model_number", "part_number", "manufacturer_part"):
        val = str(item.get(key) or "").strip()
        if val:
            return val
    return sku if sku and sku != "—" else ""


def _render_mobile_use_inventory_header() -> None:
    """IPS logo, page title, and subtitle for the mobile use-inventory scan page."""
    try:
        from app.branding import wording_logo_html
    except ImportError:
        from branding import wording_logo_html  # type: ignore
    try:
        from app.components.headers import render_page_brand_header
    except ImportError:
        from components.headers import render_page_brand_header  # type: ignore

    ot, ct = "d" + "iv", "/" + "d" + "iv"
    logo = wording_logo_html(height=56)
    st.markdown(
        f'<{ot} class="ips-inv-qr-mobile-header">'
        f'<{ot} class="ips-inv-qr-mobile-logo">{logo}</{ct}>'
        f"</{ct}>",
        unsafe_allow_html=True,
    )
    render_page_brand_header(
        "Use Inventory",
        "Consumable materials — enter quantity and where used (Use on Job or Use in Shop).",
    )


def _render_mobile_item_summary(item: dict[str, Any], *, qoh: float) -> None:
    """Item thumbnail and summary card for mobile QR use form."""
    try:
        from app.services.inventory_images import inventory_thumbnail_html
    except ImportError:
        from services.inventory_images import inventory_thumbnail_html  # type: ignore

    try:
        from app.services.catalog_stock_policy_service import derive_inventory_stock_status
    except ImportError:
        from services.catalog_stock_policy_service import derive_inventory_stock_status  # type: ignore

    name = str(item.get("name") or item.get("item_name") or "—")
    sku = str(item.get("sku") or "—")
    unit = str(item.get("unit") or "EA")
    location = str(item.get("location") or item.get("storage_location") or "—")
    status = derive_inventory_stock_status({**item, "quantity_on_hand": qoh, "qty_on_hand": qoh})
    model_line = _item_model_line(item, sku)
    thumb = inventory_thumbnail_html(
        item,
        css_class="ips-inv-qr-thumb-img",
        cell_class="ips-inv-qr-thumb-cell",
    )
    ot, ct = "d" + "iv", "/" + "d" + "iv"
    model_html = (
        f'<{ot} class="ips-inv-qr-item-model">{html.escape(model_line)}</{ct}>'
        if model_line
        else ""
    )
    st.markdown(
        f'<{ot} class="ips-inv-qr-item-panel">'
        f'<{ot} class="ips-inv-qr-thumb-wrap">{thumb}</{ct}>'
        f'<{ot} class="ips-inv-qr-item-card">'
        f'<{ot} class="ips-inv-qr-item-title">{html.escape(name)}</{ct}>'
        f"{model_html}"
        f'<{ot} class="ips-inv-qr-item-meta">SKU: {html.escape(sku)} · Unit: {html.escape(unit)}</{ct}>'
        f'<{ot} class="ips-inv-qr-item-meta">Location: {html.escape(location)} · Status: {html.escape(status)}</{ct}>'
        f'<{ot} class="ips-inv-qr-item-meta ips-inv-qr-item-onhand"><strong>On hand: {qoh:g}</strong></{ct}>'
        f"</{ct}></{ct}>",
        unsafe_allow_html=True,
    )


def _lookup_sku_case_insensitive(raw: str) -> list[dict]:
    raw_l = str(raw or "").strip().lower()
    if not raw_l:
        return []
    try:
        rows = fetch_table_admin(
            _INV,
            columns="id,item_name,sku,qr_code_value,quantity_on_hand,is_active,image_url",
            limit=8000,
        )
    except Exception:
        try:
            rows = fetch_table_admin(
                _INV,
                columns="id,item_name,qr_code_value,quantity_on_hand,is_active,image_url",
                limit=8000,
            )
        except Exception:
            return []
    return [r for r in rows if str(r.get("sku") or "").strip().lower() == raw_l]


def _lookup_qr_case_insensitive(raw: str) -> list[dict]:
    raw_l = str(raw or "").strip().lower()
    if not raw_l:
        return []
    try:
        rows = fetch_table_admin(
            _INV,
            columns="id,item_name,sku,qr_code_value,quantity_on_hand,is_active,image_url",
            limit=8000,
        )
    except Exception:
        try:
            rows = fetch_table_admin(
                _INV,
                columns="id,item_name,qr_code_value,quantity_on_hand,is_active,image_url",
                limit=8000,
            )
        except Exception:
            return []
    return [r for r in rows if str(r.get("qr_code_value") or "").strip().lower() == raw_l]


def _first_query_param(name: str) -> str:
    """Return the first string value for a query param (Streamlit may return str or list)."""
    try:
        v = st.query_params.get(name)
    except Exception:
        return ""
    if isinstance(v, list):
        return str(v[0]).strip() if v else ""
    return str(v or "").strip()


def _normalize_scan_input(raw: str) -> str:
    """Accept raw ``INV-*``, ``?code=``, or a pasted app URL with ``page=`` + ``code=``."""
    s = str(raw or "").strip()
    if not s:
        return ""
    low = s.lower()
    if "code=" in low and ("://" in s or s.startswith("/") or s.startswith("?")):
        try:
            u = urlparse(s if "://" in s else f"https://placeholder.local{s if s.startswith('/') else '/' + s}")
            vals = parse_qs(u.query).get("code") or []
            if vals:
                return str(vals[0]).strip()
        except Exception:
            return s
    return s


def _capture_scan_page_from_query() -> None:
    """If ``?page=Scan%20Inventory`` (or similar) is present, flag navigation in ``main``."""
    pg = _first_query_param("page")
    if not pg:
        return
    decoded = urllib.parse.unquote_plus(pg).strip().lower()
    if decoded == "scan inventory":
        st.session_state["_ips_query_wants_scan_inventory"] = True


def _merge_inv_scan_code_from_query() -> None:
    """Persist ``?code=`` from the URL so login / navigation can resume the scan."""
    raw = _first_query_param("code")
    if not raw:
        return
    extracted = _normalize_scan_input(raw)
    if not extracted:
        return
    st.session_state["_ips_inv_scan_deeplink_code"] = extracted
    st.session_state["pending_scan_code"] = extracted


def merge_inventory_scan_deeplink_from_query() -> None:
    """Public entry so ``main`` can capture ``?page=`` / ``?code=`` before the scan page renders."""
    _merge_inv_scan_code_from_query()
    _capture_scan_page_from_query()


def _lookup_inventory(code: str) -> tuple[list[dict], str]:
    """Returns (rows, reason). reason empty if ok; 'none' or 'ambiguous'."""
    raw = _normalize_scan_input(str(code or "").strip())
    if not raw:
        return [], "empty"
    by_qr = fetch_by_match_admin(_INV, {"qr_code_value": raw}, limit=5)
    if len(by_qr) == 1:
        return by_qr, ""
    if len(by_qr) > 1:
        return by_qr, "ambiguous"
    ci_qr = _lookup_qr_case_insensitive(raw)
    if len(ci_qr) == 1:
        return ci_qr, ""
    if len(ci_qr) > 1:
        return ci_qr, "ambiguous"
    # SKU fallback (exact match)
    by_sku = fetch_by_match_admin(_INV, {"sku": raw}, limit=5)
    if len(by_sku) == 1:
        return by_sku, ""
    if len(by_sku) > 1:
        return by_sku, "ambiguous"
    ci = _lookup_sku_case_insensitive(raw)
    if len(ci) == 1:
        return ci, ""
    if len(ci) > 1:
        return ci, "ambiguous"
    return [], "none"


def _parse_tool_ts(v: Any) -> datetime | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _fmt_tool_ts(v: Any) -> str:
    dt = _parse_tool_ts(v)
    if not dt:
        return "—"
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def _is_truthy(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in ("true", "1", "t", "yes")


def _lookup_asset_tool(code: str) -> tuple[list[dict], str]:
    raw = _normalize_scan_input(str(code or "").strip())
    if not raw:
        return [], "empty"
    try:
        by_qr = fetch_by_match_admin(_ASSETS, {"qr_code_value": raw}, limit=5)
    except Exception:
        return [], "none"
    if len(by_qr) == 1:
        return by_qr, ""
    if len(by_qr) > 1:
        return by_qr, "ambiguous"
    try:
        by_tag = fetch_by_match_admin(_ASSETS, {"asset_id": raw}, limit=5)
    except Exception:
        return [], "none"
    if len(by_tag) == 1:
        return by_tag, ""
    if len(by_tag) > 1:
        return by_tag, "ambiguous"
    return [], "none"


def _resolve_unified_scan(norm: str) -> tuple[str, list[dict]]:
    """After inventory lookup, fall back to assets. Outcomes: empty|none|inv_one|inv_amb|asset_one|asset_amb."""
    n0 = str(norm or "").strip()
    n = _normalize_scan_input(n0) or n0
    if not n.strip():
        return "empty", []
    inv_rows, inv_reason = _lookup_inventory(n)
    if inv_reason == "":
        return "inv_one", inv_rows
    if inv_reason == "ambiguous":
        return "inv_amb", inv_rows
    if inv_reason == "empty":
        return "empty", []
    a_rows, a_reason = _lookup_asset_tool(n)
    if a_reason == "":
        return "asset_one", a_rows
    if a_reason == "ambiguous":
        return "asset_amb", a_rows
    if a_reason == "empty":
        return "empty", []
    return "none", []


def _render_inv_scan_asset_panel(
    tool: dict[str, Any],
    *,
    jobs: list[dict],
    job_labels: list[str],
    job_label_to_id: dict[str, str],
    emps: list[dict],
    txn_ok: bool,
) -> None:
    emp_labels = [f"{e.get('name') or '—'} ({str(e.get('id'))[:8]}…)" for e in emps if e.get("id")]
    emp_label_to_id = {
        f"{e.get('name') or '—'} ({str(e.get('id'))[:8]}…)": str(e["id"])
        for e in emps
        if e.get("id")
    }
    emp_id_to_name = {str(e["id"]): str(e.get("name") or "").strip() or "—" for e in emps if e.get("id")}

    if not _is_truthy(tool.get("is_checkout_item")):
        st.error(
            "This asset is not flagged as a **checkout tool**. Enable **Checkout tool** in **Asset Database**."
        )
        if st.button("Clear", use_container_width=True, key="inv_scan_asset_clear_non"):
            st.session_state.pop("inv_scan_asset", None)
            st.rerun()
        return

    name = str(tool.get("asset_name") or "—").strip()
    tag = str(tool.get("asset_id") or "—").strip()
    sn = str(tool.get("serial_number") or "").strip() or "—"
    qr = str(tool.get("qr_code_value") or "").strip() or "—"
    status = str(tool.get("status") or "").strip() or "—"
    holder_id = str(tool.get("current_holder_employee_id") or "").strip()
    holder = emp_id_to_name.get(holder_id, str(tool.get("assigned_employee") or "").strip() or "—")
    jid = tool.get("assigned_job_id")
    job_disp = "—"
    if jid and jobs:
        m = {str(j.get("id")): job_row_select_label(j) for j in jobs}
        job_disp = m.get(str(jid), "—")

    st.markdown(
        f'<div class="ips-tool-scan-banner">{html.escape(name)}</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Tool / asset")
    with st.container(border=True):
        st.markdown(f"**Asset tag:** `{html.escape(tag)}`")
        st.markdown(f"**Serial:** {html.escape(sn)}")
        st.markdown(f"**QR:** `{html.escape(qr)}`")
        st.markdown(f"**Status:** {html.escape(status)}")
        st.markdown(f"**Current holder:** {html.escape(holder)}")
        st.markdown(f"**Current job:** {html.escape(job_disp)}")
        st.caption(
            f"Last checkout: {_fmt_tool_ts(tool.get('last_checkout_at'))} · "
            f"Last check-in: {_fmt_tool_ts(tool.get('last_checkin_at'))}"
        )

    tid = str(tool.get("id") or "")
    ts = datetime.now(timezone.utc).isoformat()

    if status == "Available":
        if not emp_labels:
            st.error("No **employees** loaded — add employees first.")
        else:
            with st.form("inv_scan_tool_out", clear_on_submit=False):
                emp_pick = st.selectbox("Employee (required)", emp_labels, key="inv_scan_tool_out_emp")
                job_opts = ["— No job —"] + job_labels
                job_pick = st.selectbox("Job (optional)", job_opts, key="inv_scan_tool_out_job")
                notes = st.text_area("Notes", key="inv_scan_tool_out_notes", height=72)
                go = st.form_submit_button("Check Out", type="primary", use_container_width=True)
            if go:
                fresh = fetch_by_match_admin(_ASSETS, {"id": tid}, limit=1)
                if not fresh or str(fresh[0].get("status") or "").strip() != "Available":
                    st.error("This tool is no longer **Available** — scan again.")
                    st.session_state.pop("inv_scan_asset", None)
                    st.stop()
                eid = emp_label_to_id.get(str(emp_pick or ""))
                if not eid:
                    st.error("Select an employee.")
                    st.stop()
                raw_job = str(job_pick or "").strip()
                new_jid: str | None = None
                if raw_job and not raw_job.startswith("—"):
                    new_jid = job_label_to_id.get(raw_job)
                ename = emp_id_to_name.get(eid, "")
                payload = {
                    "status": "Checked Out",
                    "current_holder_employee_id": eid,
                    "assigned_job_id": new_jid,
                    "assigned_employee": ename[:500] if ename else None,
                    "last_checkout_at": ts,
                    "updated_at": ts,
                }
                try:
                    update_rows_admin(_ASSETS, payload, {"id": tid})
                except Exception as exc:
                    st.error(f"Could not check out: {exc}")
                    st.stop()
                tool_txn_id: str | None = None
                if txn_ok:
                    try:
                        txn_ins = insert_row_admin(
                            _TOOL_TXN,
                            {
                                "tool_id": tid,
                                "transaction_type": "CHECK_OUT",
                                "employee_id": eid,
                                "job_id": new_jid,
                                "notes": str(notes or "").strip()[:2000],
                            },
                        )
                        if isinstance(txn_ins, dict):
                            tool_txn_id = str(txn_ins.get("id") or "") or None
                    except Exception as exc:
                        st.warning(f"Checked out but log failed: {exc}")
                _log_qr_scan_event(
                    qr_value=_asset_qr_display_value(tool),
                    result="success",
                    item_type="asset",
                    item_name=name,
                    asset_id=tid,
                    action_taken=serialized_tool_action_label("CHECK_OUT"),
                    job_id=new_jid,
                    destination_type="job" if new_jid else None,
                    tool_transaction_id=tool_txn_id,
                    source="inventory_scan_desktop",
                )
                st.session_state.pop("inv_scan_asset", None)
                st.success("Tool checked out.")
                st.rerun()

    elif status == "Checked Out":
        st.info("This tool is **checked out** — check it in when it returns to the shop.")
        with st.form("inv_scan_tool_in", clear_on_submit=False):
            ret_labels = ["— Same as holder —"] + [lbl for lbl in emp_labels if emp_label_to_id.get(lbl) != holder_id]
            ret_pick = st.selectbox("Returned by (optional)", ret_labels, key="inv_scan_tool_in_ret")
            notes = st.text_area("Notes", key="inv_scan_tool_in_notes", height=72)
            gin = st.form_submit_button("Check In", type="primary", use_container_width=True)
        if gin:
            fresh = fetch_by_match_admin(_ASSETS, {"id": tid}, limit=1)
            if not fresh or str(fresh[0].get("status") or "").strip() != "Checked Out":
                st.error("This tool is not **Checked Out** anymore — scan again.")
                st.session_state.pop("inv_scan_asset", None)
                st.stop()
            ret_eid: str | None = holder_id or None
            if str(ret_pick or "").startswith("—"):
                ret_eid = holder_id or None
            else:
                ret_eid = emp_label_to_id.get(str(ret_pick or "")) or holder_id
            payload = {
                "status": "Available",
                "current_holder_employee_id": None,
                "assigned_job_id": None,
                "assigned_employee": None,
                "last_checkin_at": ts,
                "updated_at": ts,
            }
            try:
                update_rows_admin(_ASSETS, payload, {"id": tid})
            except Exception as exc:
                st.error(f"Could not check in: {exc}")
                st.stop()
            tool_txn_id: str | None = None
            if txn_ok:
                try:
                    txn_ins = insert_row_admin(
                        _TOOL_TXN,
                        {
                            "tool_id": tid,
                            "transaction_type": "CHECK_IN",
                            "employee_id": ret_eid,
                            "job_id": None,
                            "notes": str(notes or "").strip()[:2000],
                        },
                    )
                    if isinstance(txn_ins, dict):
                        tool_txn_id = str(txn_ins.get("id") or "") or None
                except Exception as exc:
                    st.warning(f"Checked in but log failed: {exc}")
            _log_qr_scan_event(
                qr_value=_asset_qr_display_value(tool),
                result="success",
                item_type="asset",
                item_name=name,
                asset_id=tid,
                action_taken=serialized_tool_action_label("CHECK_IN"),
                tool_transaction_id=tool_txn_id,
                source="inventory_scan_desktop",
            )
            st.session_state.pop("inv_scan_asset", None)
            st.success("Tool checked in.")
            st.rerun()

        with st.expander("Assign to Job", expanded=False):
            with st.form("inv_scan_tool_assign_job", clear_on_submit=True):
                job_opts2 = ["— No job —"] + job_labels
                cur_lbl = job_disp if job_disp != "—" else "— No job —"
                try:
                    ix0 = job_opts2.index(cur_lbl)
                except ValueError:
                    ix0 = 0
                jp = st.selectbox("Job", job_opts2, index=min(ix0, len(job_opts2) - 1), key="inv_scan_tool_aj_job")
                sj = st.form_submit_button("Save job assignment", type="primary", use_container_width=True)
            if sj:
                raw_j = str(jp or "").strip()
                new_jid2: str | None = None
                if raw_j and not raw_j.startswith("—"):
                    new_jid2 = job_label_to_id.get(raw_j)
                try:
                    update_rows_admin(
                        _ASSETS,
                        {"assigned_job_id": new_jid2, "updated_at": ts},
                        {"id": tid},
                    )
                except Exception as exc:
                    st.error(f"Could not update job: {exc}")
                    st.stop()
                st.success("Job assignment updated.")
                st.session_state.pop("inv_scan_asset", None)
                st.rerun()

        if emp_labels:
            with st.expander("Assign to Employee", expanded=False):
                with st.form("inv_scan_tool_assign_emp", clear_on_submit=True):
                    def_ix = 0
                    if holder_id:
                        holder_lbl = next(
                            (lbl for lbl, eid in emp_label_to_id.items() if eid == holder_id),
                            None,
                        )
                        if holder_lbl and holder_lbl in emp_labels:
                            def_ix = emp_labels.index(holder_lbl)
                    ep = st.selectbox("Employee", emp_labels, index=def_ix, key="inv_scan_tool_ae_emp")
                    se = st.form_submit_button("Save holder", type="primary", use_container_width=True)
                if se:
                    neid = emp_label_to_id.get(str(ep or ""))
                    if not neid:
                        st.error("Select an employee.")
                        st.stop()
                    ename2 = emp_id_to_name.get(neid, "")
                    try:
                        update_rows_admin(
                            _ASSETS,
                            {
                                "current_holder_employee_id": neid,
                                "assigned_employee": ename2[:500] if ename2 else None,
                                "updated_at": ts,
                            },
                            {"id": tid},
                        )
                    except Exception as exc:
                        st.error(f"Could not update holder: {exc}")
                        st.stop()
                    st.success("Holder updated.")
                    st.session_state.pop("inv_scan_asset", None)
                    st.rerun()
    else:
        st.warning(
            f"Status is **{html.escape(status)}** — use **Asset Database** to move to **Available** before checkout, "
            "or check in only when status is **Checked Out**."
        )
        if st.button("Clear", use_container_width=True, key="inv_scan_asset_clear_stat"):
            st.session_state.pop("inv_scan_asset", None)
            st.rerun()


def render() -> None:
    st.title("Scan")
    try:
        _render_inventory_scan_inner()
    except Exception as exc:
        st.error(f"Scan page could not load: {exc!s}")
        st.exception(exc)


def _render_inventory_scan_inner() -> None:
    """Full Scan Inventory workflow — action types, notes, device, admin overrides (office)."""
    ensure_narrow_viewport_detected()
    _pin_qr_scan_actor_session()
    render_page_header("Scan Inventory", "Consume materials or check out serialized tools via QR scan.")
    _inject_inv_scan_mobile_css()
    st.markdown('<span class="ips-inv-scan-scope" aria-hidden="true"></span>', unsafe_allow_html=True)

    _merge_inv_scan_code_from_query()

    can_use = role_can_open_page(current_role(), "Scan Inventory")
    if not can_use:
        st.info(
            "You do not have access to this page. Ask an admin to enable **Scan Inventory** "
            "(material use + tool checkout)."
        )
        return

    try:
        fetch_table_admin(_INV, columns="id,item_name,quantity_on_hand", limit=1)
    except Exception as exc:
        st.warning("Inventory table is unavailable.")
        st.caption(str(exc))
        return

    txn_ok = True
    try:
        fetch_table_admin(_TOOL_TXN, columns="id", limit=1)
    except Exception:
        txn_ok = False
        st.warning("Run migration **`sql/029_tool_checkout.sql`** to enable **tool_transactions** logging for tools.")

    assets_scan_ok = True
    try:
        fetch_table_admin(_ASSETS, columns="id,asset_name,qr_code_value,is_checkout_item", limit=1)
    except Exception:
        assets_scan_ok = False

    # Deep link / camera: resolve inventory first, then checkout tools on ``assets``.
    _dl = (
        str(st.session_state.get("_ips_inv_scan_deeplink_code") or "").strip()
        or str(st.session_state.get("pending_scan_code") or "").strip()
    )
    if _dl and not st.session_state.get("inv_scan_loaded") and not st.session_state.get("inv_scan_asset"):
        out_dl, rows_dl = _resolve_unified_scan(_normalize_scan_input(_dl))
        if out_dl == "inv_one":
            st.session_state["inv_scan_loaded"] = rows_dl[0]
            st.session_state.pop("inv_scan_asset", None)
            st.session_state.pop("_ips_inv_scan_deeplink_code", None)
            st.session_state.pop("pending_scan_code", None)
        elif out_dl == "inv_amb":
            st.session_state["inv_scan_loaded"] = {"_choices": rows_dl}
            st.session_state.pop("inv_scan_asset", None)
            st.session_state.pop("_ips_inv_scan_deeplink_code", None)
            st.session_state.pop("pending_scan_code", None)
        elif out_dl == "asset_one" and assets_scan_ok:
            st.session_state["inv_scan_asset"] = rows_dl[0]
            st.session_state.pop("inv_scan_loaded", None)
            st.session_state.pop("_ips_inv_scan_deeplink_code", None)
            st.session_state.pop("pending_scan_code", None)
        elif out_dl == "asset_amb" and assets_scan_ok:
            st.session_state["inv_scan_asset"] = {"_choices": rows_dl}
            st.session_state.pop("inv_scan_loaded", None)
            st.session_state.pop("_ips_inv_scan_deeplink_code", None)
            st.session_state.pop("pending_scan_code", None)
        elif out_dl == "none":
            _log_qr_scan_event(
                qr_value=_dl,
                result="unknown_item",
                item_type="unknown",
                item_name="Unknown item",
                error_message="No inventory or asset matched deeplink",
                source="inventory_scan_deeplink",
            )
            st.error(
                f"Nothing found for `{html.escape(_dl)}` — try **Inventory** list, **Asset Database**, "
                "or manual entry below."
            )
            st.session_state.pop("_ips_inv_scan_deeplink_code", None)
            st.session_state.pop("pending_scan_code", None)
        elif out_dl in ("asset_one", "asset_amb") and not assets_scan_ok:
            st.error("**assets** table unavailable — cannot load tools from this link.")
            st.session_state.pop("_ips_inv_scan_deeplink_code", None)
            st.session_state.pop("pending_scan_code", None)

    ensure_inventory_device_suffix_initialized()
    ua = request_user_agent()
    suf = str(st.session_state.get("ips_inv_device_suffix") or "")
    auto_device = format_device_label(device_family_from_user_agent(ua), suf)
    if st.session_state.get("_ips_inv_disp_bindings") != suf:
        st.session_state["inv_scan_device_display"] = auto_device
        st.session_state["_ips_inv_disp_bindings"] = suf
    elif "inv_scan_device_display" not in st.session_state or not str(
        st.session_state.get("inv_scan_device_display") or ""
    ).strip():
        st.session_state["inv_scan_device_display"] = auto_device

    try:
        jobs = sort_jobs_by_number_then_name(fetch_table_admin("jobs", limit=5000))
    except Exception:
        jobs = []
    job_labels = [job_row_select_label(j) for j in jobs if j.get("id") and job_row_select_label(j) != "—"]
    job_label_to_id = {job_row_select_label(j): str(j["id"]) for j in jobs if j.get("id")}

    try:
        emps = fetch_table("employees", columns="id,name", limit=4000, order_by="name")
    except Exception:
        emps = []

    st.caption(
        "Paste **inventory** QR / SKU (consumable use) or **serialized tool** QR / asset tag (check out / check in), "
        "then **Find**. Checked-out tools are also in **Who Has What**."
    )

    with st.form("inv_scan_lookup_form", clear_on_submit=False):
        scan_code = st.text_input(
            "Scan item",
            key="inv_scan_code_input",
            placeholder="QR or SKU",
            label_visibility="visible",
        )
        c1, c2 = st.columns(2, gap="small")
        with c1:
            find = st.form_submit_button("Find", type="primary", use_container_width=True)
        with c2:
            reset = st.form_submit_button("Scan again", type="secondary", use_container_width=True)

    if reset:
        st.session_state.pop("inv_scan_code_input", None)
        st.session_state.pop("inv_scan_loaded", None)
        st.session_state.pop("inv_scan_asset", None)
        st.session_state.pop("inv_scan_pick_ix", None)
        st.session_state.pop("inv_scan_asset_pick_ix", None)
        st.session_state.pop("_ips_inv_scan_deeplink_code", None)
        st.session_state.pop("pending_scan_code", None)
        st.session_state.pop("_ips_query_wants_scan_inventory", None)
        try:
            for k in ("code", "page"):
                if k in st.query_params:
                    del st.query_params[k]
        except Exception:
            pass
        st.rerun()

    loaded: dict[str, Any] | None = st.session_state.get("inv_scan_loaded")
    asset_loaded: dict[str, Any] | None = st.session_state.get("inv_scan_asset")

    if find:
        norm = _normalize_scan_input(str(scan_code or ""))
        outcome, rows = _resolve_unified_scan(norm)
        if outcome == "empty":
            st.warning("Enter a scan code.")
        elif outcome == "none":
            shown = norm or str(scan_code or "").strip() or "—"
            _log_qr_scan_event(
                qr_value=shown,
                result="unknown_item",
                item_type="unknown",
                item_name="Unknown item",
                error_message="Manual scan lookup returned no match",
                source="inventory_scan_lookup",
            )
            st.error(f"Nothing found: `{html.escape(shown)}`")
            st.session_state.pop("inv_scan_loaded", None)
            st.session_state.pop("inv_scan_asset", None)
            st.session_state.pop("inv_scan_pick_ix", None)
            st.session_state.pop("inv_scan_asset_pick_ix", None)
            st.rerun()
        elif outcome == "inv_amb":
            st.session_state["inv_scan_loaded"] = {"_choices": rows}
            st.session_state.pop("inv_scan_asset", None)
            st.session_state.pop("inv_scan_pick_ix", None)
            st.session_state.pop("inv_scan_asset_pick_ix", None)
            st.rerun()
        elif outcome == "inv_one":
            st.session_state["inv_scan_loaded"] = rows[0]
            st.session_state.pop("inv_scan_asset", None)
            st.session_state.pop("inv_scan_pick_ix", None)
            st.session_state.pop("inv_scan_asset_pick_ix", None)
            st.rerun()
        elif outcome in ("asset_one", "asset_amb") and not assets_scan_ok:
            st.error("**assets** table unavailable — cannot look up tools.")
            st.session_state.pop("inv_scan_asset", None)
            st.session_state.pop("inv_scan_loaded", None)
            st.rerun()
        elif outcome == "asset_amb":
            st.session_state["inv_scan_asset"] = {"_choices": rows}
            st.session_state.pop("inv_scan_loaded", None)
            st.session_state.pop("inv_scan_pick_ix", None)
            st.session_state.pop("inv_scan_asset_pick_ix", None)
            st.rerun()
        elif outcome == "asset_one":
            st.session_state["inv_scan_asset"] = rows[0]
            st.session_state.pop("inv_scan_loaded", None)
            st.session_state.pop("inv_scan_pick_ix", None)
            st.session_state.pop("inv_scan_asset_pick_ix", None)
            st.rerun()

    # Re-resolve asset choices UI
    if isinstance(asset_loaded, dict) and asset_loaded.get("_choices"):
        choices_a: list[dict] = asset_loaded["_choices"]
        st.warning("Multiple tools matched — pick one.")
        labels_a = [
            f"{html.escape(str(c.get('asset_name') or '?'))} · tag `{html.escape(str(c.get('asset_id') or '—'))}`"
            for c in choices_a
        ]
        ix_a = st.selectbox(
            "Pick tool",
            range(len(labels_a)),
            format_func=lambda i: labels_a[i],
            key="inv_scan_asset_pick_ix",
        )
        if st.button("Use selected tool", type="primary", key="inv_scan_asset_use_choice", use_container_width=True):
            st.session_state["inv_scan_asset"] = choices_a[int(ix_a)]
            st.session_state.pop("inv_scan_asset_pick_ix", None)
            st.rerun()
        return

    if isinstance(asset_loaded, dict) and asset_loaded and not asset_loaded.get("_choices"):
        _log_qr_scan_opened_once(
            qr_value=_asset_qr_display_value(asset_loaded),
            item_type="asset",
            item_name=str(asset_loaded.get("asset_name") or "Tool"),
            asset_id=str(asset_loaded.get("id") or "") or None,
            source="inventory_scan_desktop",
        )
        _render_inv_scan_asset_panel(
            asset_loaded,
            jobs=jobs,
            job_labels=job_labels,
            job_label_to_id=job_label_to_id,
            emps=emps,
            txn_ok=txn_ok,
        )
        return

    # Re-resolve choices UI
    if isinstance(loaded, dict) and loaded.get("_choices"):
        choices: list[dict] = loaded["_choices"]
        st.warning("Multiple items matched — pick one.")
        labels = [
            f"{html.escape(str(c.get('item_name') or '?'))} — SKU {html.escape(str(c.get('sku') or '—'))} — id {str(c.get('id'))[:8]}…"
            for c in choices
        ]
        ix = st.selectbox("Pick item", range(len(labels)), format_func=lambda i: labels[i], key="inv_scan_pick_ix")
        if st.button("Use selected item", type="primary", key="inv_scan_use_choice", use_container_width=True):
            st.session_state["inv_scan_loaded"] = choices[int(ix)]
            st.session_state.pop("inv_scan_pick_ix", None)
            st.rerun()
        return

    if not loaded or not isinstance(loaded, dict) or loaded.get("_choices"):
        return

    item = loaded
    if not bool(item.get("is_active", True)):
        st.error("This item is inactive.")
        return

    iid = str(item.get("id") or "")
    _log_qr_scan_opened_once(
        qr_value=_inventory_qr_display_value(item, fallback=str(item.get("sku") or "")),
        item_type="inventory",
        item_name=str(item.get("item_name") or item.get("name") or "Inventory item"),
        inventory_item_id=iid or None,
        source="inventory_scan_desktop",
    )
    name = str(item.get("item_name") or "—").strip()
    sku = str(item.get("sku") or "").strip() or "—"
    qoh = _qty_on_hand(item)
    uc_raw = item.get("unit_cost")
    try:
        unit_cost = float(uc_raw) if uc_raw is not None and str(uc_raw).strip() != "" else 0.0
    except (TypeError, ValueError):
        unit_cost = 0.0
    loc = str(item.get("storage_location") or "").strip() or "—"
    vendor = str(item.get("vendor") or "").strip() or "—"

    if _is_low_stock(item):
        st.markdown(
            '<div class="ips-inv-low-banner">Low stock — reorder soon.</div>',
            unsafe_allow_html=True,
        )

    st.subheader("Item")
    with st.container(border=True):
        col1, col2 = st.columns([1, 2], gap="small")
        with col1:
            _inv_item_thumb_display(item)
        with col2:
            st.markdown(f"**{html.escape(name)}**")
            st.caption(f"Qty on hand: **{qoh:g}**")
            st.markdown(f"SKU: `{html.escape(sku)}`")
            qrv = str(item.get("qr_code_value") or "").strip()
            if qrv:
                st.markdown(f"QR value: `{html.escape(qrv)}`")
                try:
                    from app.config import settings
                    from app.services.qr_codes import generate_qr_png_bytes, inventory_scan_link_url
                except ImportError:
                    from config import settings  # type: ignore
                    from services.qr_codes import generate_qr_png_bytes, inventory_scan_link_url  # type: ignore
                try:
                    subj = inventory_scan_link_url(
                        qr_code_value=qrv,
                        app_base_url=getattr(settings, "app_base_url", "") or "",
                    )
                    st.image(io.BytesIO(generate_qr_png_bytes(subj)), width=160)
                except Exception:
                    try:
                        subj = inventory_scan_link_url(
                            qr_code_value=qrv,
                            app_base_url=getattr(settings, "app_base_url", "") or "",
                        )
                        enc = urllib.parse.quote(subj, safe="")
                    except Exception:
                        enc = urllib.parse.quote(qrv, safe="")
                    st.markdown(
                        f'<img src="https://api.qrserver.com/v1/create-qr-code/?size=160x160&data={enc}" width="160" height="160" alt="QR"/>',
                        unsafe_allow_html=True,
                    )
            st.markdown(f"**Unit cost:** {fmt_money(unit_cost, empty='—', zero_as_empty=True)}")
            st.caption(f"Location: {html.escape(loc)} · Vendor: {html.escape(vendor)}")

    st.subheader("Record use")
    prof = current_profile()
    has_login_actor = bool(str(prof.get("id") or "").strip() or _auth_user_id_str())
    manual_actor = ""
    if not has_login_actor:
        manual_actor = str(
            st.text_input(
                "Your name / device (required to log this issue)",
                key="inv_scan_manual_actor",
                placeholder="e.g. Field tablet, J. Smith",
            )
            or ""
        )

    allow_neg = False
    if current_role() == "admin":
        allow_neg = st.checkbox("Allow issue over on-hand (admin)", key="inv_scan_allow_neg")

    with st.form("inv_scan_issue_form", clear_on_submit=True):
        st.text_input(
            "Device name",
            key="inv_scan_device_display",
            placeholder=auto_device,
            help="Auto-detected for this browser; you can rename it. Stored on each transaction (sql/030).",
        )
        st.caption(
            "Auto-detected for this device. You can rename it — "
            "a stable id is kept in this browser (localStorage) when supported."
        )
        qty = st.number_input("Quantity", min_value=1, value=1, step=1, format="%d", key="inv_scan_qty")
        issue_type = st.selectbox("Use type", _ISSUE_TYPES, key="inv_scan_issue_type")
        job_opts = ["— No job —"] + job_labels
        job_pick = st.selectbox("Job", job_opts, key="inv_scan_job")
        notes = st.text_area("Notes", key="inv_scan_notes", height=88, placeholder="Optional")
        submit = st.form_submit_button("Record use", type="primary", use_container_width=True)

    if not submit:
        return

    if not has_login_actor and not str(manual_actor or "").strip():
        st.error("Enter **Your name / device** so we can record who issued this.")
        st.stop()

    qv = int(qty or 0)
    if qv <= 0:
        st.error("Quantity must be greater than zero.")
        st.stop()

    if not allow_neg and qv > qoh:
        st.error("Quantity cannot exceed quantity on hand.")
        st.stop()

    itype = str(issue_type or INVENTORY_USE_IN_SHOP_LABEL)
    txn_type = _TXN_MAP.get(itype, "SHOP")
    raw_job = str(job_pick or "").strip()
    jid: str | None = None
    if itype == INVENTORY_USE_ON_JOB_LABEL:
        if not raw_job or raw_job.startswith("—"):
            st.error(f"Select a job for **{INVENTORY_USE_ON_JOB_LABEL}**.")
            st.stop()
        jid = job_label_to_id.get(raw_job)
        if not jid:
            st.error("Invalid job selection.")
            st.stop()

    note_s = str(notes or "").strip()
    emp_id = _profile_employee_id()
    prof_id = _profile_uuid()
    actor = _pin_qr_scan_actor_session()
    cb = str(actor.get("scanned_by_name") or _scan_profile_name() or "").strip()
    scan_user_id = str(actor.get("scanned_by_user_id") or prof_id or "").strip() or None
    scan_device = str(actor.get("device_label") or "").strip()

    if itype == INVENTORY_USE_ON_JOB_LABEL and jid:
        try:
            from app.services.job_materials_service import issue_inventory_to_job
        except ImportError:
            from services.job_materials_service import issue_inventory_to_job  # type: ignore
        ua_sub = request_user_agent()
        suf_sub = str(st.session_state.get("ips_inv_device_suffix") or "")
        auto_device_submit = format_device_label(device_family_from_user_agent(ua_sub), suf_sub)
        final_device = str(st.session_state.get("inv_scan_device_display") or "").strip() or auto_device_submit
        persist_device_label_to_browser(final_device)
        scan_extra = _scan_audit_fields(device_label=final_device, manual_actor=str(manual_actor or ""))
        result = issue_inventory_to_job(
            job_id=jid,
            inventory_item_id=iid,
            quantity=qv,
            transaction_type="consume_on_job",
            notes=note_s,
            employee_id=emp_id,
            usage_source="qr_scan",
            allow_overdraw=allow_neg,
            scanned_by_user_id=scan_user_id,
            scanned_by_name=cb or str(manual_actor or "").strip() or None,
            scanned_by_employee_id=emp_id,
            source="inventory_scan_desktop",
        )
        if not result.ok:
            st.error(result.error or "Could not issue inventory to job.")
            st.stop()
        txn_row = result.data.get("transaction") if isinstance(result.data, dict) else {}
        txn_id = str((txn_row or {}).get("id") or "").strip() or None
        _log_qr_scan_event(
            qr_value=_inventory_qr_display_value(item, fallback=sku),
            result="success",
            item_type="inventory",
            item_name=name,
            inventory_item_id=iid,
            action_taken=inventory_action_label("consume_on_job"),
            job_id=jid,
            destination_type="job",
            quantity=qv,
            unit=str(item.get("unit") or "EA"),
            inventory_transaction_id=txn_id,
            scanned_by_user_id=scan_user_id,
            scanned_by_name=cb or str(manual_actor or "").strip() or None,
            employee_id=emp_id,
            device_label=scan_device or final_device,
            source="inventory_scan_desktop",
        )
        st.session_state.pop("inv_scan_loaded", None)
        st.success("Material consumed on job. Stock and job costing updated.")
        st.rerun()

    try:
        from app.services.inventory_service import record_shop_inventory_consumption
    except ImportError:
        from services.inventory_service import record_shop_inventory_consumption  # type: ignore
    ua_sub = request_user_agent()
    suf_sub = str(st.session_state.get("ips_inv_device_suffix") or "")
    auto_device_submit = format_device_label(device_family_from_user_agent(ua_sub), suf_sub)
    final_device = str(st.session_state.get("inv_scan_device_display") or "").strip() or auto_device_submit
    persist_device_label_to_browser(final_device)
    scan_extra = _scan_audit_fields(device_label=final_device, manual_actor=str(manual_actor or ""))
    shop_result = record_shop_inventory_consumption(
        {
            "inventory_item_id": iid,
            "quantity": qv,
            "allow_overdraw": allow_neg,
            "notes": note_s[:2000] or f"{INVENTORY_USE_IN_SHOP_LABEL} (desktop scan)",
            "scanned_by_user_id": prof_id,
            "scanned_by_employee_id": emp_id,
            "scanned_by_name": cb or str(manual_actor or "").strip() or scan_extra.get("scanned_by_name"),
            "source": "inventory_scan_desktop",
            "unit": str(item.get("unit") or "EA"),
            **scan_extra,
        }
    )
    if not shop_result.ok:
        st.error(shop_result.error or "Could not record shop use.")
        st.stop()

    _log_qr_scan_event(
        qr_value=_inventory_qr_display_value(item, fallback=sku),
        result="success",
        item_type="inventory",
        item_name=name,
        inventory_item_id=iid,
        action_taken=inventory_action_label("consume_in_shop"),
        job_id=None,
        destination_type="shop",
        quantity=qv,
        unit=str(item.get("unit") or "EA"),
        scanned_by_user_id=scan_user_id,
        scanned_by_name=cb or str(manual_actor or "").strip() or scan_extra.get("scanned_by_name"),
        employee_id=emp_id,
        device_label=scan_device or final_device,
        source="inventory_scan_desktop",
    )
    st.session_state.pop("inv_scan_loaded", None)
    st.success("Material consumed.")
    st.rerun()


# ---------------------------------------------------------------------------
# Mobile inventory QR scan page (?scan=inventory&sku=…&token=…)
# ---------------------------------------------------------------------------

_REMEMBERED_PHONE_KEY = "_ips_remembered_scanner_phone"
_SCAN_SESSION_KEY = "_ips_inventory_scan_page"
_MOBILE_SCAN_SHOP_LABEL = INVENTORY_USE_IN_SHOP_LABEL


def _parse_inventory_scan_deeplink(raw: str) -> dict[str, str]:
    """Extract ``scan=inventory`` params from a pasted URL or query string."""
    s = str(raw or "").strip()
    if not s:
        return {}
    try:
        if "://" in s or s.startswith("/") or s.startswith("?"):
            u = urlparse(s if "://" in s else f"https://placeholder.local{s if s.startswith('/') else '/' + s}")
            q = parse_qs(u.query)
        elif "scan=inventory" in s.lower() or "item_id=" in s.lower() or "token=" in s.lower():
            q = parse_qs(s.lstrip("?"))
        else:
            return {}
        out: dict[str, str] = {}
        for key in ("sku", "token", "item_id", "code"):
            vals = q.get(key) or []
            if vals:
                out[key] = str(vals[0]).strip()
        scan_vals = q.get("scan") or []
        if scan_vals and str(scan_vals[0]).strip().lower() == "inventory":
            out["scan"] = "inventory"
        return out
    except Exception:
        return {}


def _apply_inventory_scan_params(
    *,
    sku: str = "",
    token: str = "",
    item_id: str = "",
    legacy_code: str = "",
) -> None:
    """Persist scan identifiers in session for mobile inventory use form."""
    st.session_state[_SCAN_SESSION_KEY] = True
    if sku:
        st.session_state["_ips_scan_inv_sku"] = sku
    if token:
        st.session_state["_ips_scan_inv_token"] = token
    if item_id:
        st.session_state["_ips_scan_inv_item_id"] = item_id
    if legacy_code:
        st.session_state["_ips_scan_legacy_code"] = _normalize_scan_input(legacy_code)


def capture_inventory_scan_from_query() -> None:
    """Persist inventory scan params before auth / asset routing."""
    scan = _first_query_param("scan")
    legacy_qr = _first_query_param("qr")
    pg = urllib.parse.unquote_plus(_first_query_param("page")).strip().lower()
    legacy_page = pg in {"scan inventory", "inventory scan"}
    if scan != "inventory" and legacy_qr != "inventory" and not legacy_page:
        return
    sku = _first_query_param("sku")
    token = _first_query_param("token")
    item_id = _first_query_param("item_id")
    legacy_code = _first_query_param("code")
    _apply_inventory_scan_params(
        sku=sku,
        token=token,
        item_id=item_id,
        legacy_code=legacy_code,
    )
    if legacy_code:
        parsed = _parse_inventory_scan_deeplink(legacy_code)
        if parsed.get("scan") == "inventory":
            _apply_inventory_scan_params(
                sku=parsed.get("sku", ""),
                token=parsed.get("token", ""),
                item_id=parsed.get("item_id", ""),
            )


def inventory_scan_route_active() -> bool:
    if st.session_state.get(_SCAN_SESSION_KEY):
        return True
    if _first_query_param("scan") == "inventory":
        return True
    if _first_query_param("qr") == "inventory":
        return True
    pg = urllib.parse.unquote_plus(_first_query_param("page")).strip().lower()
    if pg in {"scan inventory", "inventory scan"}:
        return True
    return False


def _load_scan_item_legacy(code: str) -> tuple[dict[str, Any] | None, str]:
    rows, reason = _lookup_inventory(code)
    if reason == "" and rows:
        return rows[0], ""
    if reason == "ambiguous":
        return None, "Multiple inventory items matched this code."
    return None, "Invalid inventory QR code."


def _scan_profile_name() -> str:
    prof = current_profile() or {}
    return str(prof.get("full_name") or prof.get("name") or prof.get("email") or "").strip()


def _scan_profile_phone() -> str:
    prof = current_profile() or {}
    for key in ("phone_number", "phone", "mobile"):
        val = str(prof.get(key) or "").strip()
        if val:
            return val
    return ""


def _scan_profile_user_id() -> str | None:
    prof = current_profile() or {}
    uid = str(prof.get("id") or "").strip()
    return uid or None


def _scan_default_phone() -> str:
    prof_phone = _scan_profile_phone()
    if prof_phone:
        return prof_phone
    remembered = str(st.session_state.get(_REMEMBERED_PHONE_KEY) or "").strip()
    return remembered


def _load_scan_item() -> tuple[dict[str, Any] | None, str]:
    try:
        from app.services.inventory_service import get_inventory_item_by_qr
    except ImportError:
        from services.inventory_service import get_inventory_item_by_qr  # type: ignore
    sku = _first_query_param("sku") or str(st.session_state.get("_ips_scan_inv_sku") or "")
    token = _first_query_param("token") or str(st.session_state.get("_ips_scan_inv_token") or "")
    item_id = _first_query_param("item_id") or str(st.session_state.get("_ips_scan_inv_item_id") or "")
    legacy = str(st.session_state.get("_ips_scan_legacy_code") or _first_query_param("code") or "").strip()
    if legacy:
        parsed = _parse_inventory_scan_deeplink(legacy)
        if parsed.get("scan") == "inventory":
            sku = sku or parsed.get("sku", "")
            token = token or parsed.get("token", "")
            item_id = item_id or parsed.get("item_id", "")
        elif not sku and not item_id and not token:
            return _load_scan_item_legacy(legacy)
    if not sku and not item_id and not token:
        return None, "Missing inventory identifier. Scan a QR code or enter an item code below."
    result = get_inventory_item_by_qr(sku=sku or None, item_id=item_id or None, token=token or None)
    if not result.ok:
        return None, str(result.error or "Invalid inventory QR code.")
    return result.data, ""


def _render_scan_manual_lookup(*, err: str = "") -> None:
    """Manual lookup when QR params are missing or the item could not be resolved."""
    if err:
        st.error(err)
    st.markdown("### Find item")
    st.caption("Enter SKU, scan code, or paste the scan link from the inventory detail page.")
    with st.form("inv_mobile_scan_lookup", clear_on_submit=False):
        code = st.text_input(
            "Item code or link",
            key="inv_mobile_scan_lookup_code",
            placeholder="SKU, INV-…, or scan URL",
        )
        submit = st.form_submit_button("Find item", type="primary", use_container_width=True)
    if not submit:
        return
    raw = str(code or "").strip()
    if not raw:
        st.warning("Enter an item code or link.")
        return
    parsed = _parse_inventory_scan_deeplink(raw)
    if parsed.get("scan") == "inventory" or parsed.get("item_id") or parsed.get("token"):
        _apply_inventory_scan_params(
            sku=parsed.get("sku", ""),
            token=parsed.get("token", ""),
            item_id=parsed.get("item_id", ""),
        )
        try:
            for qp, val in (
                ("scan", "inventory"),
                ("sku", parsed.get("sku", "")),
                ("token", parsed.get("token", "")),
                ("item_id", parsed.get("item_id", "")),
            ):
                if val:
                    st.query_params[qp] = val
        except Exception:
            pass
        st.rerun()
    norm = _normalize_scan_input(raw)
    item, legacy_err = _load_scan_item_legacy(norm or raw)
    if item:
        _apply_inventory_scan_params(
            item_id=str(item.get("id") or ""),
            token=str(item.get("qr_token") or ""),
            sku=str(item.get("sku") or ""),
        )
        st.session_state.pop("_ips_scan_legacy_code", None)
        st.rerun()
    _log_qr_scan_event(
        qr_value=norm or raw,
        result="unknown_item",
        item_type="unknown",
        item_name="Unknown item",
        error_message=legacy_err or "Nothing found for that code.",
        source="mobile_qr_scan_lookup",
    )
    st.error(legacy_err or "Nothing found for that code.")


def _resolve_mobile_scan_destination(
    job_pick: str,
    job_map: dict[str, str],
) -> tuple[str, str | None, str]:
    """Return ``destination_type`` (shop|job), ``job_id``, and display label."""
    label = str(job_pick or "").strip()
    if label == _MOBILE_SCAN_SHOP_LABEL:
        return "shop", None, _MOBILE_SCAN_SHOP_LABEL
    return "job", job_map.get(label), label


def _scan_mobile_job_options() -> tuple[list[str], dict[str, str]]:
    """All jobs (any status) plus Use in Shop — for the simplified mobile QR scan form."""
    try:
        jobs = sort_jobs_by_number_then_name(fetch_table_admin("jobs", limit=5000))
    except Exception:
        jobs = []
    _, label_to_id, labels = build_job_dropdown_label_maps(jobs)
    return [_MOBILE_SCAN_SHOP_LABEL, *labels], label_to_id


def _record_mobile_shop_use(
    *,
    item: dict[str, Any],
    qty: float,
    qoh: float,
    allow_over: bool,
) -> tuple[bool, str]:
    """Use in Shop from mobile QR scan — routed through inventory_service audit."""
    try:
        from app.services.inventory_service import record_shop_inventory_consumption
    except ImportError:
        from services.inventory_service import record_shop_inventory_consumption  # type: ignore

    iid = str(item.get("id") or "")
    qv = int(qty or 0)
    if qv <= 0:
        return False, "Quantity must be greater than zero."
    if qv > qoh and not allow_over:
        return False, "Quantity exceeds quantity on hand."

    actor_name, phone_norm, _, phone_verified = _mobile_scan_actor_defaults()
    actor = _pin_qr_scan_actor_session()
    result = record_shop_inventory_consumption(
        {
            "inventory_item_id": iid,
            "quantity": qv,
            "allow_overdraw": allow_over,
            "notes": f"{INVENTORY_USE_IN_SHOP_LABEL} (mobile QR scan)",
            "scanned_by_user_id": actor.get("scanned_by_user_id"),
            "scanned_by_name": actor_name[:500],
            "scanned_by_phone": phone_norm or None,
            "scanned_by_employee_id": actor.get("employee_id") or _profile_employee_id(),
            "phone_verified": phone_verified,
            "source": "qr_scan",
            "device_label": actor.get("device_label"),
            "unit": str(item.get("unit") or "EA"),
        }
    )
    if not result.ok:
        return False, result.error or "Could not record transaction."
    return True, ""


def _scan_can_submit() -> bool:
    if not is_authenticated():
        return True
    return str(current_role() or "viewer").lower() != "viewer"


def _mobile_scan_qty_step(delta: int) -> None:
    cur = int(float(st.session_state.get("inv_scan_qty") or 1))
    st.session_state["inv_scan_qty"] = max(1, cur + int(delta))


def _mobile_scan_actor_defaults() -> tuple[str, str, str, bool]:
    """Name, normalized phone, display phone, and phone_verified from pinned scan session."""
    try:
        from app.utils.phone_helpers import format_phone_display, is_valid_phone, normalize_phone
    except ImportError:
        from utils.phone_helpers import format_phone_display, is_valid_phone, normalize_phone  # type: ignore

    actor = _pin_qr_scan_actor_session()
    prof_name = str(actor.get("scanned_by_name") or "").strip() or _scan_profile_name()
    prof_phone = _scan_profile_phone()
    default_phone = _scan_default_phone()
    actor_name = prof_name or ("Mobile scanner" if not is_authenticated() else "Scanner")
    phone_raw = prof_phone or default_phone
    phone_norm = normalize_phone(phone_raw) if phone_raw else ""
    if phone_norm and not is_valid_phone(phone_norm):
        phone_norm = ""
    phone_verified = bool(
        prof_phone and phone_norm and normalize_phone(prof_phone) == phone_norm and is_authenticated()
    )
    phone_display = format_phone_display(phone_norm) if phone_norm else "—"
    return actor_name, phone_norm, phone_display, phone_verified


def _submit_mobile_inventory_scan(
    *,
    item: dict[str, Any],
    qty: float,
    job_pick: str,
    job_map: dict[str, str],
    qoh: float,
    unit: str,
) -> None:
    """Consume scanned inventory on the selected job or in shop (mobile QR form)."""
    try:
        from app.services.job_materials_service import issue_inventory_to_job
    except ImportError:
        from services.job_materials_service import issue_inventory_to_job  # type: ignore

    action = "consume_on_job"
    iid = str(item.get("id") or "")
    qv = int(qty or 0)
    if qv <= 0:
        st.error("Quantity must be greater than zero.")
        st.stop()

    destination_type, job_id, destination_label = _resolve_mobile_scan_destination(job_pick, job_map)
    if not destination_label:
        st.error(f"Select {INVENTORY_USE_IN_SHOP_LABEL} or a job.")
        st.stop()

    actor_name, phone_norm, phone_display, phone_verified = _mobile_scan_actor_defaults()
    actor = _pin_qr_scan_actor_session()
    device_label = str(actor.get("device_label") or "").strip()
    scan_user_id = str(actor.get("scanned_by_user_id") or "").strip() or None
    employee_id = str(actor.get("employee_id") or "").strip() or _profile_employee_id()
    allow_over = str(current_role() or "").lower() == "admin"

    if destination_type == "shop":
        ok, err = _record_mobile_shop_use(item=item, qty=qv, qoh=qoh, allow_over=allow_over)
        if not ok:
            st.error(err or "Could not record shop use.")
            st.stop()
        _log_qr_scan_event(
            qr_value=_inventory_qr_display_value(item, fallback=str(item.get("sku") or "")),
            result="success",
            item_type="inventory",
            item_name=str(item.get("name") or item.get("item_name") or "Inventory item"),
            inventory_item_id=iid,
            action_taken=inventory_action_label("SHOP"),
            destination_type="shop",
            quantity=qv,
            unit=unit,
            scanned_by_user_id=scan_user_id,
            scanned_by_name=actor_name,
            scanned_by_phone=phone_norm or None,
            employee_id=employee_id,
            device_label=device_label or None,
            source="mobile_qr_scan",
        )
        st.session_state["inv_scan_success_payload"] = {
            "item": item,
            "action": "shop_use",
            "quantity": qv,
            "unit": unit,
            "destination_type": "shop",
            "job_id": None,
            "job_label": _MOBILE_SCAN_SHOP_LABEL,
            "name": actor_name,
            "phone_display": phone_display,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
        st.rerun()

    if not job_id:
        st.error("Invalid job selection.")
        st.stop()

    if qv > qoh and not allow_over:
        st.error("Quantity exceeds quantity on hand.")
        st.stop()

    result = issue_inventory_to_job(
        job_id=job_id,
        inventory_item_id=iid,
        quantity=qv,
        transaction_type=action,
        notes="",
        employee_id=employee_id,
        usage_source="qr_scan",
        allow_overdraw=allow_over,
        scanned_by_user_id=scan_user_id,
        scanned_by_name=actor_name,
        scanned_by_phone=phone_norm or None,
        scanned_by_employee_id=employee_id,
        phone_verified=phone_verified,
        source="qr_scan",
        unit=unit,
    )
    if not result.ok:
        st.error(result.error or "Could not record transaction.")
        st.stop()

    txn_row = result.data.get("transaction") if isinstance(result.data, dict) else {}
    txn_id = str((txn_row or {}).get("id") or "").strip() or None
    _log_qr_scan_event(
        qr_value=_inventory_qr_display_value(item, fallback=str(item.get("sku") or "")),
        result="success",
        item_type="inventory",
        item_name=str(item.get("name") or item.get("item_name") or "Inventory item"),
        inventory_item_id=iid,
        action_taken=inventory_action_label(action),
        job_id=job_id,
        destination_type="job",
        quantity=qv,
        unit=unit,
        scanned_by_user_id=scan_user_id,
        scanned_by_name=actor_name,
        scanned_by_phone=phone_norm or None,
        employee_id=employee_id,
        device_label=device_label or None,
        inventory_transaction_id=txn_id,
        source="mobile_qr_scan",
    )
    st.session_state["inv_scan_success_payload"] = {
        "item": item,
        "action": action,
        "quantity": qv,
        "unit": unit,
        "destination_type": "job",
        "job_id": job_id,
        "job_label": destination_label,
        "name": actor_name,
        "phone_display": phone_display,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    st.rerun()


def _render_scan_success(item: dict[str, Any], payload: dict[str, Any]) -> None:
    dest_type = str(payload.get("destination_type") or "").strip().lower()
    dest_label = str(payload.get("job_label") or "—")
    st.success("Material consumed.")
    st.markdown(
        f"**Item:** {html.escape(str(item.get('name') or item.get('item_name') or '—'))}  \n"
        f"**Use:** {html.escape(inventory_action_label(str(payload.get('action') or '')))}  \n"
        f"**Quantity:** {float(payload.get('quantity') or 0):g} {html.escape(str(payload.get('unit') or 'EA'))}  \n"
        f"**Destination:** {html.escape(dest_label)}"
        + (f" ({html.escape(dest_type)})" if dest_type else "")
        + "  \n"
        f"**Name:** {html.escape(str(payload.get('name') or '—'))}  \n"
        f"**Phone:** {html.escape(str(payload.get('phone_display') or '—'))}  \n"
        f"**Time:** {html.escape(str(payload.get('timestamp') or '—'))}"
    )
    b1, b2 = st.columns(2, gap="small")
    with b1:
        if st.button("Record another use for this item", key="inv_scan_success_again", use_container_width=True):
            st.session_state.pop("inv_scan_success_payload", None)
            st.rerun()
    with b2:
        if st.button("Back to Inventory", key="inv_scan_success_inventory", use_container_width=True):
            st.session_state.pop("inv_scan_success_payload", None)
            st.session_state.pop(_SCAN_SESSION_KEY, None)
            for key in ("_ips_scan_inv_sku", "_ips_scan_inv_token", "_ips_scan_inv_item_id", "_ips_scan_legacy_code"):
                st.session_state.pop(key, None)
            try:
                for qp in ("scan", "sku", "token", "item_id", "qr", "code", "page"):
                    if qp in st.query_params:
                        del st.query_params[qp]
                st.query_params["page"] = "Inventory"
            except Exception:
                pass
            st.rerun()


@fragment
def _render_inventory_scan_entry_fragment(
    item: dict[str, Any],
    *,
    qoh: float,
    unit: str,
    job_labels: list[str],
    job_map: dict[str, str],
) -> None:
    """Qty/job scan form — local reruns for +/- and submit."""
    if "inv_scan_qty" not in st.session_state:
        st.session_state["inv_scan_qty"] = 1

    with st.form("inv_mobile_scan_form", clear_on_submit=False):
        st.markdown('<span class="ips-inv-qr-form-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
        st.markdown('<p class="ips-inv-qr-field-label">Qty</p>', unsafe_allow_html=True)
        qty_minus_col, qty_col, qty_plus_col = st.columns([1, 2.4, 1], gap="small")
        with qty_minus_col:
            qty_dec = st.form_submit_button("−", use_container_width=True)
        with qty_col:
            qty = st.number_input(
                "Qty",
                min_value=1,
                step=1,
                format="%d",
                key="inv_scan_qty",
                label_visibility="collapsed",
            )
        with qty_plus_col:
            qty_inc = st.form_submit_button("+", use_container_width=True)
        st.markdown('<p class="ips-inv-qr-qty-hint">Whole numbers only.</p>', unsafe_allow_html=True)
        st.markdown('<p class="ips-inv-qr-field-label ips-inv-qr-field-label-spaced">Where used</p>', unsafe_allow_html=True)
        job_pick = st.selectbox(
            "Where used",
            job_labels,
            key="inv_scan_job_pick",
            label_visibility="collapsed",
        )
        submit = st.form_submit_button("Enter", type="primary", use_container_width=True)

    if qty_dec:
        _mobile_scan_qty_step(-1)
        st.rerun()
    if qty_inc:
        _mobile_scan_qty_step(1)
        st.rerun()
    if not submit:
        return

    _submit_mobile_inventory_scan(
        item=item,
        qty=int(qty or 0),
        job_pick=job_pick,
        job_map=job_map,
        qoh=qoh,
        unit=unit,
    )


def render_inventory_scan_page() -> None:
    """Mobile QR scan workflow — Qty + Job + Enter only (field speed). No sidebar."""
    ensure_narrow_viewport_detected()
    _pin_qr_scan_actor_session()
    try:
        from app.styles import inject_inventory_qr_scan_css
    except ImportError:
        from styles import inject_inventory_qr_scan_css  # type: ignore
    inject_inventory_qr_scan_css()
    _inject_inv_scan_mobile_css()
    st.markdown('<span class="ips-inv-qr-scan-scope" aria-hidden="true"></span>', unsafe_allow_html=True)
    _render_mobile_use_inventory_header()

    success = st.session_state.get("inv_scan_success_payload")
    if success and isinstance(success, dict):
        item_ok = success.get("item") or {}
        _render_scan_success(item_ok, success)
        return

    item, err = _load_scan_item()
    if err or not item:
        qr_attempt = (
            _first_query_param("sku")
            or _first_query_param("token")
            or _first_query_param("item_id")
            or str(st.session_state.get("_ips_scan_legacy_code") or "")
        )
        if qr_attempt and err:
            actor = _pin_qr_scan_actor_session()
            _log_qr_scan_event(
                qr_value=qr_attempt,
                result="failed" if "missing" in err.casefold() else "unknown_item",
                item_type="unknown",
                item_name="Unknown item",
                error_message=err,
                scanned_by_user_id=actor.get("scanned_by_user_id"),
                scanned_by_name=actor.get("scanned_by_name"),
                employee_id=actor.get("employee_id"),
                device_label=actor.get("device_label"),
                source="mobile_qr_scan",
            )
        _render_scan_manual_lookup(err=err or "Invalid inventory QR code.")
        return

    _log_qr_scan_opened_once(
        qr_value=_inventory_qr_display_value(item, fallback=str(item.get("sku") or "")),
        item_type="inventory",
        item_name=str(item.get("name") or item.get("item_name") or "Inventory item"),
        inventory_item_id=str(item.get("id") or "") or None,
        source="mobile_qr_scan",
    )

    if not _scan_can_submit():
        st.error("Your role cannot record inventory use.")
        st.stop()

    unit = str(item.get("unit") or "EA")
    qoh = _qty_on_hand(item)

    _render_mobile_item_summary(item, qoh=qoh)

    job_labels, job_map = _scan_mobile_job_options()
    _render_inventory_scan_entry_fragment(
        item,
        qoh=qoh,
        unit=unit,
        job_labels=job_labels,
        job_map=job_map,
    )
