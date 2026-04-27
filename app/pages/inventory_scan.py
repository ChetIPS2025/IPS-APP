"""
Mobile-first field scan: inventory_items (issue) + reusable tools on public.assets (checkout).

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
    from app.auth import current_profile, current_role
    from app.branding import render_header
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
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from auth import current_profile, current_role  # type: ignore
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
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore

_INV = "inventory_items"
_TXN = "inventory_transactions"
_JM = "job_materials"
_ASSETS = "assets"
_TOOL_TXN = "tool_transactions"

_ISSUE_TYPES = ("To Job", "Stock Adjustment", "Shop Use")
_TXN_MAP = {"To Job": "TO_JOB", "Stock Adjustment": "ADJUST", "Shop Use": "SHOP"}


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


def _qty_on_hand(row: dict) -> float:
    return float(row.get("quantity_on_hand") or 0)


def _reorder(row: dict) -> float:
    try:
        return float(row.get("reorder_point") or 0)
    except (TypeError, ValueError):
        return 0.0


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


def _inv_item_thumb_display(item: dict) -> None:
    """Small item photo or 📦 placeholder (scan screen)."""
    raw = str(item.get("image_url") or "").strip()
    if not raw:
        st.markdown('<p style="font-size:2.5rem;margin:0;line-height:1;">📦</p>', unsafe_allow_html=True)
        return
    if raw.startswith("http://") or raw.startswith("https://"):
        st.image(raw, width=80)
        return
    try:
        url = create_signed_url(raw, expires_in=3600)
    except Exception:
        url = ""
    if url:
        st.image(url, width=80)
    else:
        st.markdown('<p style="font-size:2.5rem;margin:0;line-height:1;">📦</p>', unsafe_allow_html=True)


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
                if txn_ok:
                    try:
                        insert_row_admin(
                            _TOOL_TXN,
                            {
                                "tool_id": tid,
                                "transaction_type": "CHECK_OUT",
                                "employee_id": eid,
                                "job_id": new_jid,
                                "notes": str(notes or "").strip()[:2000],
                            },
                        )
                    except Exception as exc:
                        st.warning(f"Checked out but log failed: {exc}")
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
            if txn_ok:
                try:
                    insert_row_admin(
                        _TOOL_TXN,
                        {
                            "tool_id": tid,
                            "transaction_type": "CHECK_IN",
                            "employee_id": ret_eid,
                            "job_id": None,
                            "notes": str(notes or "").strip()[:2000],
                        },
                    )
                except Exception as exc:
                    st.warning(f"Checked in but log failed: {exc}")
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
            st.caption("Add employees to reassign the holder from this screen.")

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
    ensure_narrow_viewport_detected()
    render_header("", subtitle="Industrial Plant Solutions, LLC")
    _inject_inv_scan_mobile_css()
    st.markdown('<span class="ips-inv-scan-scope" aria-hidden="true"></span>', unsafe_allow_html=True)

    _merge_inv_scan_code_from_query()

    can_use = role_can_open_page(current_role(), "Scan Inventory")
    if not can_use:
        st.info(
            "You do not have access to this page. Ask an admin to enable **Scan Inventory** "
            "(inventory issue + tool checkout)."
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
        "Paste **inventory** QR / SKU or **tool** QR / asset tag, then **Find**. "
        "Checkout tools are also in **Who Has What**."
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
            st.markdown(f"**Unit cost:** {_fmt_money(unit_cost)}")
            st.caption(f"Location: {html.escape(loc)} · Vendor: {html.escape(vendor)}")

    st.subheader("Issue")
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
        qty = st.number_input("Quantity", min_value=0.0, value=1.0, step=0.25, format="%.4f", key="inv_scan_qty")
        issue_type = st.selectbox("Issue type", _ISSUE_TYPES, key="inv_scan_issue_type")
        job_opts = ["— No job —"] + job_labels
        job_pick = st.selectbox("Job", job_opts, key="inv_scan_job")
        notes = st.text_area("Notes", key="inv_scan_notes", height=88, placeholder="Optional")
        submit = st.form_submit_button("Issue Inventory", type="primary", use_container_width=True)

    if not submit:
        return

    if not has_login_actor and not str(manual_actor or "").strip():
        st.error("Enter **Your name / device** so we can record who issued this.")
        st.stop()

    qv = float(qty or 0)
    if qv <= 0:
        st.error("Quantity must be greater than zero.")
        st.stop()

    if not allow_neg and qv > qoh:
        st.error("Quantity cannot exceed quantity on hand.")
        st.stop()

    itype = str(issue_type or "Shop Use")
    txn_type = _TXN_MAP.get(itype, "SHOP")
    raw_job = str(job_pick or "").strip()
    jid: str | None = None
    if itype == "To Job":
        if not raw_job or raw_job.startswith("—"):
            st.error("Select a job for **To Job** issues.")
            st.stop()
        jid = job_label_to_id.get(raw_job)
        if not jid:
            st.error("Invalid job selection.")
            st.stop()

    note_s = str(notes or "").strip()
    emp_id = _profile_employee_id()
    prof_id = _profile_uuid()
    cb = _created_by_label()
    ts = datetime.now(timezone.utc).isoformat()
    new_qoh = qoh - qv

    try:
        update_rows_admin(
            _INV,
            {"quantity_on_hand": float(new_qoh), "updated_at": ts},
            {"id": iid},
        )
    except Exception as exc:
        st.error(f"Could not update stock: {exc}")
        st.stop()

    jm_row: dict | None = None
    if itype == "To Job" and jid:
        line_total = round(qv * unit_cost, 2)
        try:
            jm_row = insert_row_admin(
                _JM,
                {
                    "job_id": jid,
                    "inventory_item_id": iid,
                    "item_name": name[:500],
                    "quantity": float(qv),
                    "unit_cost": float(unit_cost),
                    "line_total": float(line_total),
                    "notes": note_s[:2000],
                },
            )
        except Exception as exc:
            try:
                update_rows_admin(_INV, {"quantity_on_hand": float(qoh), "updated_at": ts}, {"id": iid})
            except Exception:
                pass
            st.error(f"Job costing line failed; stock restored. {exc}")
            st.stop()

    txn_payload: dict[str, Any] = {
        "inventory_item_id": iid,
        "qty": float(-qv),
        "txn_type": txn_type,
        "job_id": jid,
        "employee_id": emp_id,
        "profile_id": prof_id,
        "notes": note_s[:2000],
    }
    if cb:
        txn_payload["created_by"] = cb[:500]
    ua_sub = request_user_agent()
    suf_sub = str(st.session_state.get("ips_inv_device_suffix") or "")
    auto_device_submit = format_device_label(device_family_from_user_agent(ua_sub), suf_sub)
    final_device = str(st.session_state.get("inv_scan_device_display") or "").strip() or auto_device_submit
    persist_device_label_to_browser(final_device)
    scan_extra = _scan_audit_fields(device_label=final_device, manual_actor=str(manual_actor or ""))
    txn_payload.update(scan_extra)

    pl: dict[str, Any] = dict(txn_payload)
    exc: Exception | None = None
    for _ in range(5):
        try:
            insert_row_admin(_TXN, pl)
            exc = None
            break
        except Exception as e:
            exc = e
            low = str(e).lower()
            if "scanned_by" in low or "device_label" in low:
                pl.pop("scanned_by_user_id", None)
                pl.pop("scanned_by_name", None)
                pl.pop("device_label", None)
            elif "created_by" in low:
                pl.pop("created_by", None)
            else:
                break
    if exc is not None:
        if jm_row and jm_row.get("id"):
            try:
                delete_rows_admin(_JM, {"id": str(jm_row["id"])})
            except Exception:
                pass
        try:
            update_rows_admin(_INV, {"quantity_on_hand": float(qoh), "updated_at": ts}, {"id": iid})
        except Exception:
            pass
        st.error(f"Transaction log failed; changes rolled back. {exc}")
        st.stop()

    st.session_state.pop("inv_scan_loaded", None)
    st.success("Inventory issued.")
    st.rerun()


def _fmt_money(v: float) -> str:
    if v is None or v == 0:
        return "—"
    return f"${float(v):,.2f}"
