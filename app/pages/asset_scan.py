"""Mobile asset QR scan page (?scan=asset&asset_id=…&token=…)."""

from __future__ import annotations

import html
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any

import streamlit as st

try:
    from app.auth import current_profile, current_role, is_authenticated
    from app.services.assets_service import (
        create_asset_inspection,
        create_asset_issue,
        generate_asset_qr_value,
        get_asset_by_qr,
        get_asset_document_view_url,
        get_asset_documents_grouped,
        get_asset_image_url,
        get_asset_inspections,
        get_asset_issues,
        upload_asset_image,
    )
    from app.utils.formatting import fmt_date
    from app.services.asset_kits_service import asset_is_kit
    from app.pages.trailer_dashboard import render_trailer_dashboard
    from app.services.rental_equipment_inspection_service import is_rental_equipment
    from app.pages.rental_equipment_dashboard import render_rental_equipment_dashboard
except ImportError:
    from auth import current_profile, current_role, is_authenticated  # type: ignore
    from services.assets_service import (  # type: ignore
        create_asset_inspection,
        create_asset_issue,
        generate_asset_qr_value,
        get_asset_by_qr,
        get_asset_document_view_url,
        get_asset_documents_grouped,
        get_asset_image_url,
        get_asset_inspections,
        get_asset_issues,
        upload_asset_image,
    )
    from utils.formatting import fmt_date  # type: ignore
    from services.asset_kits_service import asset_is_kit  # type: ignore
    from pages.trailer_dashboard import render_trailer_dashboard  # type: ignore
    from services.rental_equipment_inspection_service import is_rental_equipment  # type: ignore
    from pages.rental_equipment_dashboard import render_rental_equipment_dashboard  # type: ignore

_SCAN_SESSION_KEY = "_ips_asset_scan_page"
_SUCCESS_KEY = "asset_scan_success_payload"
_VIEW_KEY = "asset_scan_view"

_CONDITION_OPTS = ["Good", "Needs Attention", "Unsafe / Remove from Service"]
_SEVERITY_OPTS = ["Low", "Medium", "High", "Critical"]

_DOC_SECTION_LABELS = {
    "Manual": "View Manual",
    "Parts Manual": "View Parts Manual",
    "Safety Sheet": "View Safety Sheet",
    "Maintenance Document": "View Maintenance Docs",
    "Other Attachments": "View Attachment",
}


def _first_query_param(name: str) -> str:
    try:
        v = st.query_params.get(name)
    except Exception:
        return ""
    if isinstance(v, list):
        return str(v[0]).strip() if v else ""
    return str(v or "").strip()


def _qp(name: str) -> str | None:
    """Read one query param (Streamlit may return str or list)."""
    value = _first_query_param(name)
    return value if value else None


def _debug_qr_enabled() -> bool:
    try:
        from app.config import settings
    except ImportError:
        from config import settings  # type: ignore
    flag = str(getattr(settings, "debug_qr", "") or "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    import os
    return str(os.environ.get("DEBUG_QR") or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_scan_url_params(raw: str) -> dict[str, str]:
    """Extract scan=asset params from a full URL or query string fragment."""
    out: dict[str, str] = {}
    s = str(raw or "").strip()
    if not s:
        return out
    try:
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(s if "://" in s else f"https://local.invalid/?{s.lstrip('?')}")
        qs = parse_qs(parsed.query)
        for key in (
            "scan",
            "asset_id",
            "asset_number",
            "asset_tag",
            "tag",
            "qr",
            "token",
            "page",
            "asset",
        ):
            vals = qs.get(key) or []
            if vals and str(vals[0]).strip():
                out[key] = str(vals[0]).strip()
    except Exception:
        pass
    return out


def _collect_asset_scan_params() -> dict[str, str]:
    """Merge session, query params, and embedded URL fragments for asset scan."""
    params: dict[str, str] = {}
    for key in (
        "scan",
        "asset_id",
        "asset_number",
        "asset_tag",
        "tag",
        "qr",
        "code",
        "token",
        "page",
        "asset",
    ):
        val = _qp(key)
        if val:
            params[key] = val

    if params.get("code") and not params.get("qr"):
        params["qr"] = params["code"]

    for sess_key, out_key in (
        ("_ips_scan_ast_id", "asset_id"),
        ("_ips_scan_ast_num", "asset_number"),
        ("_ips_scan_ast_tag", "asset_tag"),
        ("_ips_scan_ast_token", "token"),
        ("_ips_scan_ast_qr", "qr"),
    ):
        val = str(st.session_state.get(sess_key) or "").strip()
        if val and not params.get(out_key):
            params[out_key] = val

    embedded = _parse_scan_url_params(params.get("qr") or "")
    for key, val in embedded.items():
        if val and not params.get(key):
            params[key] = val

    if not params.get("scan"):
        page = (params.get("page") or "").lower()
        if params.get("asset") or params.get("asset_tag") or params.get("tag"):
            params["scan"] = "asset"
        elif "asset_card" in page:
            params["scan"] = "asset"

    if params.get("asset") and not params.get("asset_tag"):
        params["asset_tag"] = params["asset"]
    if params.get("tag") and not params.get("asset_tag"):
        params["asset_tag"] = params["tag"]

    if not params.get("scan") and _looks_like_asset_identifier(
        params.get("qr") or params.get("code") or ""
    ):
        params["scan"] = "asset"
        if params.get("code") and not params.get("qr"):
            params["qr"] = params["code"]

    return params


def _looks_like_asset_identifier(raw: str) -> bool:
    """True when a bare scanned value is likely an asset tag (not inventory)."""
    s = str(raw or "").strip()
    if not s or s.lower() == "inventory":
        return False
    if "://" in s or "scan=" in s.lower() or "asset_id=" in s.lower():
        embedded = _parse_scan_url_params(s)
        return bool(
            embedded.get("scan") == "asset"
            or embedded.get("asset_id")
            or embedded.get("asset_tag")
            or embedded.get("asset")
            or embedded.get("qr")
        )
    low = s.lower()
    if low.startswith("ips-"):
        return True
    if re.match(r"^[a-z]{2,12}-[a-f0-9]{6,}$", low):
        return True
    return len(s) >= 8 and "-" in s


def capture_asset_scan_from_query() -> None:
    """Persist asset scan params before auth / legacy asset routing."""
    params = _collect_asset_scan_params()
    scan = params.get("scan") or _qp("scan")
    if scan != "asset" and not (params.get("asset") or params.get("asset_tag") or params.get("tag")):
        page = (params.get("page") or _qp("page") or "").lower()
        if "asset_card" not in page and not _looks_like_asset_identifier(
            params.get("qr") or params.get("code") or _qp("qr") or _qp("code") or ""
        ):
            return
    st.session_state[_SCAN_SESSION_KEY] = True
    for key, sess_key in (
        ("asset_id", "_ips_scan_ast_id"),
        ("asset_number", "_ips_scan_ast_num"),
        ("asset_tag", "_ips_scan_ast_tag"),
        ("token", "_ips_scan_ast_token"),
        ("qr", "_ips_scan_ast_qr"),
    ):
        if params.get(key):
            st.session_state[sess_key] = params[key]
    if params.get("code") and not st.session_state.get("_ips_scan_ast_qr"):
        st.session_state["_ips_scan_ast_qr"] = params["code"]


def asset_scan_route_active() -> bool:
    if st.session_state.get(_SCAN_SESSION_KEY):
        return True
    if _qp("scan") == "asset":
        return True
    if _qp("asset") or _qp("asset_tag") or _qp("tag"):
        return True
    page = (_qp("page") or "").lower()
    if "asset_card" in page:
        return True
    if _looks_like_asset_identifier(_qp("qr") or _qp("code") or ""):
        return True
    return False


def _profile_name() -> str:
    prof = current_profile() or {}
    return str(prof.get("full_name") or prof.get("name") or prof.get("email") or "").strip()


def _profile_phone() -> str:
    prof = current_profile() or {}
    for key in ("phone_number", "phone", "mobile"):
        val = str(prof.get(key) or "").strip()
        if val:
            return val
    return ""


def _profile_user_id() -> str | None:
    uid = str((current_profile() or {}).get("id") or "").strip()
    return uid or None


def _profile_employee_id() -> str | None:
    uid = str((current_profile() or {}).get("employee_id") or "").strip()
    return uid or None


def _can_view_restricted_docs() -> bool:
    if not is_authenticated():
        return False
    return str(current_role() or "").lower() in {"admin", "supervisor", "manager"}


def _load_scan_asset() -> tuple[dict[str, Any] | None, str, dict[str, str]]:
    params = _collect_asset_scan_params()
    result = get_asset_by_qr(
        asset_id=params.get("asset_id"),
        asset_number=params.get("asset_number"),
        asset_tag=params.get("asset_tag"),
        qr=params.get("qr"),
        token=params.get("token"),
        allow_legacy=True,
    )
    if not result.ok:
        return None, str(result.error or "Asset not found for this QR code."), params
    return result.data, "", params


def _asset_status_pill_html(status: str) -> str:
    safe = html.escape(status or "—")
    return f'<span class="ips-asset-scan-status">{safe}</span>'


def _render_asset_hero(asset: dict[str, Any]) -> None:
    image_url = get_asset_image_url(asset)
    name = str(asset.get("asset_name") or "—")
    num = str(asset.get("asset_number") or "—")
    status = str(asset.get("status") or "—")

    if image_url:
        st.markdown(
            f'<img class="ips-asset-scan-hero-img" src="{html.escape(image_url, quote=True)}" alt="Asset photo" />',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="ips-asset-scan-hero-placeholder">No photo</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="ips-asset-scan-title">{html.escape(name)}</div>'
        f'<div class="ips-asset-scan-tag">{html.escape(num)}</div>'
        f'{_asset_status_pill_html(status)}',
        unsafe_allow_html=True,
    )


def _render_asset_summary(asset: dict[str, Any]) -> None:
    rows = [
        ("Category", asset.get("category")),
        ("Location", asset.get("location")),
        ("Department", asset.get("department")),
        ("Assigned To", asset.get("operator")),
        ("Condition", asset.get("condition")),
        ("Next Service Due", asset.get("next_service_due") or "—"),
        ("Serial Number", asset.get("serial_number")),
        ("Manufacturer / Model", f"{asset.get('manufacturer') or '—'} / {asset.get('model') or '—'}"),
    ]
    parts = ['<div class="ips-asset-scan-info">']
    for label, val in rows:
        parts.append(
            f'<div class="ips-asset-scan-info-row">'
            f'<span class="ips-asset-scan-info-label">{html.escape(label)}</span>'
            f'<span class="ips-asset-scan-info-value">{html.escape(str(val or "—"))}</span>'
            f"</div>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def _render_document_buttons(asset: dict[str, Any]) -> None:
    include_restricted = _can_view_restricted_docs()
    grouped = get_asset_documents_grouped(str(asset.get("id") or ""), include_restricted=include_restricted)
    has_any = any(grouped.get(k) for k in grouped)
    st.markdown("#### Documents")
    if not has_any:
        st.caption("No documents attached to this asset.")
        return

    for section, docs in grouped.items():
        if not docs:
            continue
        label_base = _DOC_SECTION_LABELS.get(section, f"View {section}")
        for doc in docs:
            fname = str(doc.get("file_name") or "Document")
            btn_label = f"{label_base} — {fname}" if len(docs) > 1 or section == "Other Attachments" else label_base
            view_url = doc.get("view_url") or get_asset_document_view_url(doc)
            key = f"ast_doc_{doc.get('id') or fname}_{section}"
            if doc.get("is_restricted") and not include_restricted:
                st.caption("Restricted document.")
                continue
            if view_url:
                st.link_button(btn_label, view_url, use_container_width=True, key=key)
            else:
                st.button(btn_label, key=key, disabled=True, use_container_width=True)


def _render_inspection_form(asset: dict[str, Any]) -> None:
    aid = str(asset.get("id") or "")
    prof_name = _profile_name()
    prof_phone = _profile_phone()

    if st.button("← Back to Asset Card", key="ast_scan_back_from_insp"):
        st.session_state[_VIEW_KEY] = "card"
        st.rerun()

    st.markdown("### Start Inspection")
    with st.form("asset_inspection_form", clear_on_submit=False):
        inspector = st.text_input(
            "Inspector name",
            value=prof_name,
            disabled=bool(prof_name and is_authenticated()),
        )
        phone = st.text_input("Inspector phone", value=prof_phone, placeholder="(337) 555-0100")
        st.caption(
            "Phone comes from your profile or manual entry — browsers cannot read the device phone number automatically."
        )
        insp_dt = st.text_input(
            "Inspection date/time",
            value=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        )
        condition = st.selectbox("Condition", _CONDITION_OPTS)
        hours_miles = st.number_input("Hours/miles reading", min_value=0.0, value=0.0, step=0.1)
        location = st.text_input("Location", value=str(asset.get("location") or ""))
        st.markdown("**Checklist**")
        visual_damage = st.checkbox("Visual damage?", value=False)
        safety_guards_ok = st.checkbox("Safety guards in place?", value=True)
        leaks_present = st.checkbox("Leaks?", value=False)
        tires_wheels_ok = st.checkbox("Tires/wheels/tracks okay?", value=True)
        controls_working = st.checkbox("Controls working?", value=True)
        emergency_stop_working = st.checkbox("Emergency stop working?", value=True)
        labels_present = st.checkbox("Warning labels present?", value=True)
        clean_usable = st.checkbox("Clean and usable?", value=True)
        notes = st.text_area("Notes", height=80)
        photo = st.file_uploader("Upload photo (optional)", type=["png", "jpg", "jpeg", "webp"])
        submit = st.form_submit_button("Submit Inspection", type="primary", use_container_width=True)

    if not submit:
        return

    try:
        from app.utils.phone_helpers import format_phone_display, is_valid_phone, normalize_phone
    except ImportError:
        from utils.phone_helpers import format_phone_display, is_valid_phone, normalize_phone  # type: ignore

    actor = prof_name if (prof_name and is_authenticated()) else str(inspector or "").strip()
    if not actor:
        st.error("Inspector name is required.")
        st.stop()
    phone_norm = normalize_phone(phone or prof_phone)
    if not is_valid_phone(phone_norm):
        st.error("Enter a valid phone number.")
        st.stop()

    photo_path = ""
    photo_url = ""
    if photo is not None:
        upload_result = upload_asset_image(aid, photo, uploaded_by=_profile_user_id())
        if upload_result.ok and isinstance(upload_result.data, dict):
            photo_path = str(upload_result.data.get("image_path") or "")
            photo_url = str(upload_result.data.get("image_url") or "")

    result = create_asset_inspection(
        aid,
        {
            "inspector_name": actor,
            "inspector_phone": phone_norm,
            "inspector_user_id": _profile_user_id(),
            "inspector_employee_id": _profile_employee_id(),
            "inspection_date": insp_dt,
            "condition": condition,
            "hours_miles": hours_miles or None,
            "location": location,
            "visual_damage": visual_damage,
            "safety_guards_ok": safety_guards_ok,
            "leaks_present": leaks_present,
            "tires_wheels_ok": tires_wheels_ok,
            "controls_working": controls_working,
            "emergency_stop_working": emergency_stop_working,
            "labels_present": labels_present,
            "clean_usable": clean_usable,
            "notes": notes,
            "photo_path": photo_path,
            "photo_url": photo_url,
        },
    )
    if not result.ok:
        st.error(result.error or "Could not save inspection.")
        st.stop()

    st.session_state[_SUCCESS_KEY] = {
        "asset_name": asset.get("asset_name"),
        "asset_number": asset.get("asset_number"),
        "inspector": actor,
        "phone_display": format_phone_display(phone_norm),
        "condition": condition,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "notes": notes,
        "kind": "inspection",
    }
    st.session_state[_VIEW_KEY] = "success"
    st.rerun()


def _render_issue_form(asset: dict[str, Any]) -> None:
    aid = str(asset.get("id") or "")
    prof_name = _profile_name()
    prof_phone = _profile_phone()

    if st.button("← Back to Asset Card", key="ast_scan_back_from_issue"):
        st.session_state[_VIEW_KEY] = "card"
        st.rerun()

    st.markdown("### Report Issue")
    with st.form("asset_issue_form", clear_on_submit=False):
        severity = st.selectbox("Issue severity", _SEVERITY_OPTS, index=1)
        description = st.text_area("Description", height=100)
        reporter = st.text_input(
            "Reported by name",
            value=prof_name,
            disabled=bool(prof_name and is_authenticated()),
        )
        phone = st.text_input("Reported by phone", value=prof_phone, placeholder="(337) 555-0100")
        photo = st.file_uploader("Photo (optional)", type=["png", "jpg", "jpeg", "webp"], key="ast_issue_photo")
        submit = st.form_submit_button("Submit Issue", type="primary", use_container_width=True)

    if not submit:
        return

    try:
        from app.utils.phone_helpers import format_phone_display, is_valid_phone, normalize_phone
    except ImportError:
        from utils.phone_helpers import format_phone_display, is_valid_phone, normalize_phone  # type: ignore

    actor = prof_name if (prof_name and is_authenticated()) else str(reporter or "").strip()
    if not actor:
        st.error("Name is required.")
        st.stop()
    if not str(description or "").strip():
        st.error("Description is required.")
        st.stop()
    phone_norm = normalize_phone(phone or prof_phone)
    if not is_valid_phone(phone_norm):
        st.error("Enter a valid phone number.")
        st.stop()

    photo_path = ""
    photo_url = ""
    if photo is not None:
        upload_result = upload_asset_image(aid, photo, uploaded_by=_profile_user_id())
        if upload_result.ok and isinstance(upload_result.data, dict):
            photo_path = str(upload_result.data.get("image_path") or "")
            photo_url = str(upload_result.data.get("image_url") or "")

    result = create_asset_issue(
        aid,
        {
            "severity": severity,
            "description": description,
            "reported_by_name": actor,
            "reported_by_phone": phone_norm,
            "photo_path": photo_path,
            "photo_url": photo_url,
        },
    )
    if not result.ok:
        st.error(result.error or "Could not save issue.")
        st.stop()

    st.session_state[_SUCCESS_KEY] = {
        "asset_name": asset.get("asset_name"),
        "asset_number": asset.get("asset_number"),
        "inspector": actor,
        "phone_display": format_phone_display(phone_norm),
        "condition": severity,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "notes": description,
        "kind": "issue",
    }
    st.session_state[_VIEW_KEY] = "success"
    st.rerun()


def _render_maintenance_history(asset: dict[str, Any]) -> None:
    aid = str(asset.get("id") or "")
    if st.button("← Back to Asset Card", key="ast_scan_back_from_maint"):
        st.session_state[_VIEW_KEY] = "card"
        st.rerun()

    st.markdown("### Maintenance History")
    inspections = get_asset_inspections(aid)
    issues = get_asset_issues(aid)
    if not inspections and not issues:
        st.caption("No inspections or issues recorded yet.")
        return

    if inspections:
        st.markdown("**Inspections**")
        for row in inspections[:20]:
            st.markdown(
                f"- **{html.escape(fmt_date(row.get('inspection_date')))}** — "
                f"{html.escape(str(row.get('condition') or '—'))} · "
                f"{html.escape(str(row.get('inspector_name') or '—'))}"
            )
    if issues:
        st.markdown("**Reported Issues**")
        for row in issues[:20]:
            st.markdown(
                f"- **{html.escape(str(row.get('severity') or '—'))}** — "
                f"{html.escape(str(row.get('description') or '')[:120])}"
            )


def _render_success() -> None:
    payload = st.session_state.get(_SUCCESS_KEY) or {}
    kind = str(payload.get("kind") or "inspection")
    st.success("Inspection recorded." if kind == "inspection" else "Issue reported.")
    st.markdown(
        f"**Asset:** {html.escape(str(payload.get('asset_name') or '—'))} "
        f"({html.escape(str(payload.get('asset_number') or '—'))})  \n"
        f"**{'Inspector' if kind == 'inspection' else 'Reported by'}:** "
        f"{html.escape(str(payload.get('inspector') or '—'))}  \n"
        f"**{'Condition' if kind == 'inspection' else 'Severity'}:** "
        f"{html.escape(str(payload.get('condition') or '—'))}  \n"
        f"**Time:** {html.escape(str(payload.get('timestamp') or '—'))}  \n"
        f"**Notes:** {html.escape(str(payload.get('notes') or '—'))}"
    )
    b1, b2 = st.columns(2, gap="small")
    with b1:
        if st.button("Back to Asset Card", key="ast_scan_success_back", use_container_width=True):
            st.session_state.pop(_SUCCESS_KEY, None)
            st.session_state[_VIEW_KEY] = "card"
            st.rerun()
    with b2:
        if st.button("Start Another Inspection", key="ast_scan_success_again", use_container_width=True):
            st.session_state.pop(_SUCCESS_KEY, None)
            st.session_state[_VIEW_KEY] = "inspection"
            st.rerun()


def _render_asset_card(asset: dict[str, Any]) -> None:
    if asset_is_kit(asset):
        render_trailer_dashboard(asset)
        return

    if is_rental_equipment(asset):
        render_rental_equipment_dashboard(asset)
        return

    _render_asset_hero(asset)
    st.markdown("---")
    if st.button("Start Inspection", type="primary", use_container_width=True, key="ast_scan_start_insp"):
        st.session_state[_VIEW_KEY] = "inspection"
        st.rerun()
    if st.button("Report Issue", use_container_width=True, key="ast_scan_report_issue"):
        st.session_state[_VIEW_KEY] = "issue"
        st.rerun()
    if st.button("View Maintenance History", use_container_width=True, key="ast_scan_view_maint"):
        st.session_state[_VIEW_KEY] = "maintenance"
        st.rerun()
    _render_document_buttons(asset)
    st.markdown("---")
    st.markdown("#### Asset Info")
    _render_asset_summary(asset)


def _render_qr_debug(params: dict[str, str]) -> None:
    if not _debug_qr_enabled():
        return
    token_present = bool(params.get("token"))
    with st.expander("QR debug (DEBUG_QR)", expanded=False):
        st.write(
            {
                "asset_id": params.get("asset_id"),
                "asset_number": params.get("asset_number"),
                "asset_tag": params.get("asset_tag"),
                "qr": params.get("qr"),
                "token_present": token_present,
            }
        )


def render_asset_scan_page() -> None:
    """Dedicated mobile asset card — no sidebar, no dashboard routing."""
    try:
        from app.mobile_ui import ensure_narrow_viewport_detected
    except ImportError:
        from app.mobile_ui import ensure_narrow_viewport_detected  # type: ignore
    try:
        from app.styles import inject_asset_qr_scan_css
    except ImportError:
        from styles import inject_asset_qr_scan_css  # type: ignore

    ensure_narrow_viewport_detected()
    inject_asset_qr_scan_css()
    st.markdown('<span class="ips-asset-qr-scan-scope" aria-hidden="true"></span>', unsafe_allow_html=True)

    params = _collect_asset_scan_params()
    _render_qr_debug(params)

    view = str(st.session_state.get(_VIEW_KEY) or "card")
    if view == "success" and st.session_state.get(_SUCCESS_KEY):
        _render_success()
        return

    asset, err, _params = _load_scan_asset()
    if err or not asset:
        st.error(err or "Asset not found for this QR code.")
        scanned = (
            _params.get("qr")
            or _params.get("asset_tag")
            or _params.get("asset_number")
            or _params.get("asset_id")
            or ""
        )
        if scanned:
            st.caption(f"Scanned value: {html.escape(scanned)}")
        st.stop()

    warning = str(asset.pop("_qr_scan_warning", "") or "").strip()
    if asset.pop("_qr_scan_legacy", False) and not warning:
        warning = "Legacy QR label detected. Reprint this label when convenient."
    if warning:
        st.warning(warning)

    if asset_is_kit(asset):
        render_trailer_dashboard(asset)
        return

    if is_rental_equipment(asset):
        render_rental_equipment_dashboard(asset)
        return

    st.markdown("## IPS Asset Card")

    if view == "inspection":
        _render_inspection_form(asset)
    elif view == "issue":
        _render_issue_form(asset)
    elif view == "maintenance":
        _render_maintenance_history(asset)
    else:
        _render_asset_card(asset)
