"""
Mobile-first checkout / check-in for reusable tools (assets.is_checkout_item).

Schema (see sql/029_tool_checkout.sql):
- assets: asset_name (tool name), asset_id (tag), serial_number, qr_code_value, status,
  assigned_job_id (current job), current_holder_employee_id, last_checkout_at, last_checkin_at,
  assigned_employee (display name, synced on checkout), is_checkout_item
- tool_transactions: tool_id -> assets.id, transaction_type CHECK_OUT | CHECK_IN,
  employee_id, job_id, notes, created_at

Does NOT touch inventory_items or inventory_transactions (consumables only).
"""
from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import streamlit as st

try:
    from mobile_ui import ensure_narrow_viewport_detected
except ImportError:
    from app.mobile_ui import ensure_narrow_viewport_detected  # type: ignore

try:
    from app.auth import current_role
    from app.branding import render_header
    from app.db import fetch_by_match_admin, fetch_table, fetch_table_admin, insert_row_admin, update_rows_admin
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
except ImportError:
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import fetch_by_match_admin, fetch_table, fetch_table_admin, insert_row_admin, update_rows_admin  # type: ignore
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore

_ASSETS = "assets"
_TXN = "tool_transactions"
_OVERDUE_DAYS = 14


def _inject_tool_co_mobile_css() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlock"]:has(span.ips-tool-co-scope) label {
            font-size: 1rem !important;
        }
        div[data-testid="stVerticalBlock"]:has(span.ips-tool-co-scope) input {
            min-height: 48px !important;
            font-size: 1.05rem !important;
        }
        div[data-testid="stVerticalBlock"]:has(span.ips-tool-co-scope) button {
            min-height: 48px !important;
            font-size: 1rem !important;
        }
        div[data-testid="stVerticalBlock"]:has(span.ips-tool-co-scope) [data-baseweb="select"] > div {
            min-height: 48px !important;
        }
        .ips-tool-co-banner {
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


def _parse_ts(v: Any) -> datetime | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _fmt_ts(v: Any) -> str:
    dt = _parse_ts(v)
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


def _lookup_tool(code: str) -> tuple[list[dict], str]:
    raw = str(code or "").strip()
    if not raw:
        return [], "empty"
    by_qr = fetch_by_match_admin(_ASSETS, {"qr_code_value": raw}, limit=5)
    if len(by_qr) == 1:
        return by_qr, ""
    if len(by_qr) > 1:
        return by_qr, "ambiguous"
    by_tag = fetch_by_match_admin(_ASSETS, {"asset_id": raw}, limit=5)
    if len(by_tag) == 1:
        return by_tag, ""
    if len(by_tag) > 1:
        return by_tag, "ambiguous"
    return [], "none"


def render() -> None:
    ensure_narrow_viewport_detected()
    render_header("Tool Checkout")
    _inject_tool_co_mobile_css()
    st.markdown('<span class="ips-tool-co-scope" aria-hidden="true"></span>', unsafe_allow_html=True)

    can_use = current_role() in {"admin", "pm", "employee"}
    if not can_use:
        st.info("Sign in as **admin**, **pm**, or **employee** to check tools in or out.")
        return

    try:
        fetch_table_admin(_ASSETS, columns="id,asset_name,qr_code_value,is_checkout_item", limit=1)
    except Exception:
        st.warning("Could not read **assets**.")
        return

    txn_ok = True
    try:
        fetch_table_admin(_TXN, columns="id", limit=1)
    except Exception:
        txn_ok = False
        st.warning("Run migration **`sql/029_tool_checkout.sql`** to enable **tool_transactions** logging.")

    try:
        emps = fetch_table("employees", columns="id,name", limit=4000, order_by="name")
    except Exception:
        emps = []
    emp_labels = [f"{e.get('name') or '—'} ({str(e.get('id'))[:8]}…)" for e in emps if e.get("id")]
    emp_label_to_id = {
        f"{e.get('name') or '—'} ({str(e.get('id'))[:8]}…)": str(e["id"])
        for e in emps
        if e.get("id")
    }
    emp_id_to_name = {str(e["id"]): str(e.get("name") or "").strip() or "—" for e in emps if e.get("id")}

    try:
        jobs = sort_jobs_by_number_then_name(fetch_table("jobs", limit=5000))
    except Exception:
        jobs = []
    job_labels = [job_row_select_label(j) for j in jobs if j.get("id") and job_row_select_label(j) != "—"]
    job_label_to_id = {job_row_select_label(j): str(j["id"]) for j in jobs if j.get("id")}

    st.caption(
        "Scan **QR** or **asset tag** — reusable tools only (**Checkout tool** in Asset Database). "
        "Manager view: sidebar **Who Has What**."
    )

    with st.form("tool_co_lookup", clear_on_submit=False):
        scan = st.text_input("Scan tool", key="tool_co_scan", placeholder="QR or asset tag")
        c1, c2 = st.columns(2, gap="small")
        with c1:
            find = st.form_submit_button("Find", type="primary", use_container_width=True)
        with c2:
            reset = st.form_submit_button("Scan again", type="secondary", use_container_width=True)

    if reset:
        for k in ("tool_co_scan", "tool_co_loaded", "tool_co_pick_ix"):
            st.session_state.pop(k, None)
        st.rerun()

    loaded: dict[str, Any] | None = st.session_state.get("tool_co_loaded")

    if find:
        rows, reason = _lookup_tool(str(scan or ""))
        if reason == "empty":
            st.warning("Enter a scan code.")
        elif reason == "none":
            st.error("Tool not found.")
            st.session_state.pop("tool_co_loaded", None)
            st.rerun()
        elif reason == "ambiguous":
            st.session_state["tool_co_loaded"] = {"_choices": rows}
            st.rerun()
        else:
            st.session_state["tool_co_loaded"] = rows[0]
            st.rerun()

    if isinstance(loaded, dict) and loaded.get("_choices"):
        choices: list[dict] = loaded["_choices"]
        st.warning("Multiple matches — pick one.")
        labels = [
            f"{html.escape(str(c.get('asset_name') or '?'))} · tag `{html.escape(str(c.get('asset_id') or '—'))}`"
            for c in choices
        ]
        ix = st.selectbox("Pick tool", range(len(labels)), format_func=lambda i: labels[i], key="tool_co_pick_ix")
        if st.button("Use selected", type="primary", use_container_width=True, key="tool_co_use_pick"):
            st.session_state["tool_co_loaded"] = choices[int(ix)]
            st.session_state.pop("tool_co_pick_ix", None)
            st.rerun()
        return

    if not loaded or not isinstance(loaded, dict) or loaded.get("_choices"):
        _reporting_section(emp_id_to_name, txn_ok)
        return

    tool = loaded
    if not _is_truthy(tool.get("is_checkout_item")):
        st.error("This asset is not flagged as a **checkout tool**. Enable **Checkout tool** in **Asset Database** edit.")
        if st.button("Clear", use_container_width=True, key="tool_co_clear_non"):
            st.session_state.pop("tool_co_loaded", None)
            st.rerun()
        _reporting_section(emp_id_to_name, txn_ok)
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
        f'<div class="ips-tool-co-banner">{html.escape(name)}</div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(f"**Asset tag:** `{html.escape(tag)}`")
        st.markdown(f"**Serial:** {html.escape(sn)}")
        st.markdown(f"**QR:** `{html.escape(qr)}`")
        st.markdown(f"**Status:** {html.escape(status)}")
        st.markdown(f"**Current holder:** {html.escape(holder)}")
        st.markdown(f"**Current job:** {html.escape(job_disp)}")
        st.caption(f"Last checkout: {_fmt_ts(tool.get('last_checkout_at'))} · Last check-in: {_fmt_ts(tool.get('last_checkin_at'))}")

    tid = str(tool.get("id") or "")
    ts = datetime.now(timezone.utc).isoformat()

    if status == "Available":
        if not emp_labels:
            st.error("No **employees** loaded — add employees first.")
        else:
            with st.form("tool_co_out", clear_on_submit=False):
                emp_pick = st.selectbox("Employee (required)", emp_labels, key="tool_co_out_emp")
                job_opts = ["— No job —"] + job_labels
                job_pick = st.selectbox("Job (optional)", job_opts, key="tool_co_out_job")
                notes = st.text_area("Notes", key="tool_co_out_notes", height=72)
                go = st.form_submit_button("Check Out Tool", type="primary", use_container_width=True)
            if go:
                fresh = fetch_by_match_admin(_ASSETS, {"id": tid}, limit=1)
                if not fresh or str(fresh[0].get("status") or "").strip() != "Available":
                    st.error("This tool is no longer **Available** — scan again.")
                    st.session_state.pop("tool_co_loaded", None)
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
                            _TXN,
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
                st.session_state.pop("tool_co_loaded", None)
                st.success("Tool checked out.")
                st.rerun()

    elif status == "Checked Out":
        st.info("This tool is **checked out** — check it in when it returns to the shop.")
        with st.form("tool_co_in", clear_on_submit=False):
            ret_labels = ["— Same as holder —"] + [lbl for lbl in emp_labels if emp_label_to_id.get(lbl) != holder_id]
            ret_pick = st.selectbox("Returned by (optional)", ret_labels, key="tool_co_in_ret")
            notes = st.text_area("Notes", key="tool_co_in_notes", height=72)
            gin = st.form_submit_button("Check In Tool", type="primary", use_container_width=True)
        if gin:
            fresh = fetch_by_match_admin(_ASSETS, {"id": tid}, limit=1)
            if not fresh or str(fresh[0].get("status") or "").strip() != "Checked Out":
                st.error("This tool is not **Checked Out** anymore — scan again.")
                st.session_state.pop("tool_co_loaded", None)
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
                        _TXN,
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
            st.session_state.pop("tool_co_loaded", None)
            st.success("Tool checked in.")
            st.rerun()
    else:
        st.warning(
            f"Status is **{html.escape(status)}** — use **Asset Database** to move to **Available** before checkout, "
            "or check in only when status is **Checked Out**."
        )
        if st.button("Clear", use_container_width=True, key="tool_co_clear_stat"):
            st.session_state.pop("tool_co_loaded", None)
            st.rerun()

    _reporting_section(emp_id_to_name, txn_ok)


def _reporting_section(emp_id_to_name: dict[str, str], txn_ok: bool) -> None:
    st.divider()
    st.subheader("Reporting")

    try:
        assets = fetch_table(_ASSETS, limit=8000, order_by="asset_name")
    except Exception:
        st.caption("Could not load assets for reports.")
        return

    tools = [a for a in assets if _is_truthy(a.get("is_checkout_item"))]
    if not tools:
        st.caption("No **checkout tools** yet — mark assets in **Asset Database**.")
        return

    out_rows = [
        t
        for t in tools
        if str(t.get("status") or "").strip() == "Checked Out"
    ]
    st.markdown(f"**Currently checked out:** {len(out_rows)}")

    cutoff = datetime.now(timezone.utc) - timedelta(days=_OVERDUE_DAYS)
    overdue: list[dict] = []
    for t in out_rows:
        co = _parse_ts(t.get("last_checkout_at"))
        if co and co.tzinfo is None:
            co = co.replace(tzinfo=timezone.utc)
        if co and co < cutoff:
            overdue.append(t)
    if overdue:
        st.warning(f"**Long checkout (>{_OVERDUE_DAYS}d):** {len(overdue)} tool(s) still out.")
        odf = pd.DataFrame(
            [
                {
                    "Tool": str(x.get("asset_name") or ""),
                    "Asset tag": str(x.get("asset_id") or ""),
                    "Holder": emp_id_to_name.get(str(x.get("current_holder_employee_id") or ""), str(x.get("assigned_employee") or "")),
                    "Checked out": _fmt_ts(x.get("last_checkout_at")),
                }
                for x in overdue[:50]
            ]
        )
        st.dataframe(odf, use_container_width=True, hide_index=True)

    if out_rows and not overdue:
        st.caption(f"No tools over {_OVERDUE_DAYS} days out (based on **last_checkout_at**).")

    cur_df = pd.DataFrame(
        [
            {
                "Tool": str(x.get("asset_name") or ""),
                "Asset tag": str(x.get("asset_id") or ""),
                "Holder": emp_id_to_name.get(str(x.get("current_holder_employee_id") or ""), str(x.get("assigned_employee") or "")),
                "Checked out": _fmt_ts(x.get("last_checkout_at")),
                "Status": str(x.get("status") or ""),
            }
            for x in out_rows[:80]
        ]
    )
    if not cur_df.empty:
        st.caption("Out now (up to 80 rows)")
        st.dataframe(cur_df, use_container_width=True, hide_index=True)

    if not txn_ok:
        return
    try:
        txns = fetch_table_admin(_TXN, limit=800)
    except Exception:
        return
    txns.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    txns = txns[:120]
    if not txns:
        st.caption("No transactions yet.")
        return
    aid_to = {str(a.get("id")): str(a.get("asset_name") or "") for a in assets if a.get("id")}
    rows = []
    for r in txns:
        tid = str(r.get("tool_id") or "")
        rows.append(
            {
                "When": _fmt_ts(r.get("created_at")),
                "Tool": aid_to.get(tid, tid[:8] + "…"),
                "Type": str(r.get("transaction_type") or ""),
                "Employee": emp_id_to_name.get(str(r.get("employee_id") or ""), "—"),
                "Notes": (str(r.get("notes") or "")[:80] + "…") if len(str(r.get("notes") or "")) > 80 else str(r.get("notes") or ""),
            }
        )
    st.caption("Recent tool transactions")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
