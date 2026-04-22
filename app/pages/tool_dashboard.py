"""
Who Has What — dashboard for checkout tools (assets.is_checkout_item).

Schema (sql/029_tool_checkout.sql):
- assets: asset_name, asset_id, serial_number, status, assigned_job_id, current_holder_employee_id,
  last_checkout_at, notes, is_checkout_item
- tool_transactions: tool_id, transaction_type, employee_id, job_id, notes, created_at
- jobs: job_number, job_name (labels via job_row_select_label)
- employees: id, name

Change overdue threshold: ``OVERDUE_THRESHOLD_DAYS`` below (default 7).
Does not modify consumable inventory or job costing tables.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
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
    from app.ui import IPS_NAV_PENDING_KEY
except ImportError:
    from auth import current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import fetch_by_match_admin, fetch_table, fetch_table_admin, insert_row_admin, update_rows_admin  # type: ignore
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore
    from ui import IPS_NAV_PENDING_KEY  # type: ignore

_ASSETS = "assets"
_TXN = "tool_transactions"

# --- Tweak overdue definition here (days since last_checkout_at for Checked Out tools) ---
OVERDUE_THRESHOLD_DAYS = 7


def _inject_tool_dash_css() -> None:
    st.markdown(
        """
<style>
div[data-testid="stVerticalBlock"]:has(span.ips-tool-dash-scope) .ips-td-metric-row div[data-testid="stMetric"] {
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(71, 85, 105, 0.55);
  border-radius: 10px;
  padding: 8px 10px;
}
.ips-td-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.ips-td-b-avail { color: #86efac; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(74, 222, 128, 0.35); }
.ips-td-b-out { color: #fdba74; background: rgba(251, 146, 60, 0.12); border: 1px solid rgba(251, 191, 36, 0.4); }
.ips-td-b-maint { color: #93c5fd; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(96, 165, 250, 0.4); }
.ips-td-b-lost { color: #fca5a5; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(248, 113, 113, 0.45); }
.ips-td-b-od { color: #fecaca; background: rgba(220, 38, 38, 0.22); border: 1px solid rgba(248, 113, 113, 0.55); }
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
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _is_checkout_flag(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "t", "yes")


def _days_out_value(last_co: Any) -> float | None:
    dt = _parse_ts(last_co)
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 86400.0)


def _days_out_label(last_co: Any) -> str:
    d = _days_out_value(last_co)
    if d is None:
        return "—"
    if d < 1.0:
        return f"{d:.1f} d"
    return f"{int(d)} d"


def _status_badge_html(status: str) -> str:
    stt = str(status or "").strip()
    if stt == "Available":
        cls, lab = "ips-td-b-avail", "Available"
    elif stt == "Checked Out":
        cls, lab = "ips-td-b-out", "Checked Out"
    elif stt == "Maintenance":
        cls, lab = "ips-td-b-maint", "Maintenance"
    elif stt == "Lost":
        cls, lab = "ips-td-b-lost", "Lost"
    else:
        cls = "ips-td-b-out"
        lab = html.escape(stt or "—")
    return f'<span class="ips-td-badge {cls}">{lab}</span>'


def _attention_badge_html(status: str, last_co: Any) -> str:
    stt = str(status or "").strip()
    if stt == "Lost":
        return '<span class="ips-td-badge ips-td-b-lost">Lost</span>'
    if stt == "Maintenance":
        return '<span class="ips-td-badge ips-td-b-maint">Maintenance</span>'
    if stt == "Checked Out":
        dv = _days_out_value(last_co)
        if dv is not None and dv > OVERDUE_THRESHOLD_DAYS:
            return '<span class="ips-td-badge ips-td-b-od">Overdue</span>'
    return ""


def _perform_checkin(tool_id: str, *, txn_ok: bool) -> tuple[bool, str]:
    ts = datetime.now(timezone.utc).isoformat()
    fresh = fetch_by_match_admin(_ASSETS, {"id": tool_id}, limit=1)
    if not fresh or str(fresh[0].get("status") or "").strip() != "Checked Out":
        return False, "Tool is not checked out anymore — refresh the page."
    holder_id = str(fresh[0].get("current_holder_employee_id") or "").strip() or None
    payload = {
        "status": "Available",
        "current_holder_employee_id": None,
        "assigned_job_id": None,
        "assigned_employee": None,
        "last_checkin_at": ts,
        "updated_at": ts,
    }
    try:
        update_rows_admin(_ASSETS, payload, {"id": tool_id})
    except Exception as exc:
        return False, str(exc)
    if txn_ok:
        try:
            insert_row_admin(
                _TXN,
                {
                    "tool_id": tool_id,
                    "transaction_type": "CHECK_IN",
                    "employee_id": holder_id,
                    "job_id": None,
                    "notes": "Quick check-in from Who Has What dashboard",
                },
            )
        except Exception:
            pass
    return True, ""


def render() -> None:
    ensure_narrow_viewport_detected()
    render_header("Who Has What")
    _inject_tool_dash_css()
    st.markdown('<span class="ips-tool-dash-scope" aria-hidden="true"></span>', unsafe_allow_html=True)

    st.caption(
        "Checkout tools only — possession on **assets** / **tool_transactions**. "
        "For scan workflow use **Tool Checkout**."
    )

    if current_role() not in {"admin", "pm", "employee", "viewer"}:
        st.error("You do not have access to this page.")
        return

    can_write = current_role() in {"admin", "pm"}

    try:
        all_assets = fetch_table(_ASSETS, limit=8000, order_by="asset_name")
    except Exception:
        st.warning("Could not load **assets**.")
        return

    tools = [a for a in all_assets if _is_checkout_flag(a.get("is_checkout_item"))]
    if not tools:
        st.info("No checkout tools yet — enable **Checkout tool** on assets in **Asset Database**.")
        return

    txn_ok = True
    try:
        fetch_table_admin(_TXN, columns="id", limit=1)
    except Exception:
        txn_ok = False
        st.info("**tool_transactions** unavailable — run **`sql/029_tool_checkout.sql`** for full history.")

    try:
        emps = fetch_table("employees", columns="id,name", limit=4000, order_by="name")
    except Exception:
        emps = []
    emp_id_to_name = {str(e["id"]): str(e.get("name") or "").strip() for e in emps if e.get("id")}

    try:
        jobs = sort_jobs_by_number_then_name(fetch_table("jobs", limit=5000))
    except Exception:
        jobs = []
    job_by_id = {str(j.get("id")): j for j in jobs if j.get("id")}

    def job_label(jid: Any) -> str:
        if not jid:
            return "—"
        s = str(jid).strip()
        return job_row_select_label(job_by_id[s]) if s in job_by_id else "—"

    # --- Quick check-in queue (button triggers) ---
    qid = st.session_state.pop("_td_quick_in_id", None)
    if qid and can_write and txn_ok:
        ok, err = _perform_checkin(str(qid), txn_ok=txn_ok)
        if ok:
            st.success("Tool checked in.")
        else:
            st.error(err or "Check-in failed.")
        st.rerun()

    n_avail = sum(1 for t in tools if str(t.get("status") or "").strip() == "Available")
    n_out = sum(1 for t in tools if str(t.get("status") or "").strip() == "Checked Out")
    n_maint = sum(1 for t in tools if str(t.get("status") or "").strip() == "Maintenance")
    n_lost = sum(1 for t in tools if str(t.get("status") or "").strip() == "Lost")
    n_od = 0
    for t in tools:
        if str(t.get("status") or "").strip() != "Checked Out":
            continue
        dv = _days_out_value(t.get("last_checkout_at"))
        if dv is not None and dv > OVERDUE_THRESHOLD_DAYS:
            n_od += 1

    narrow = st.session_state.get("ips_viewport_narrow") is True
    st.markdown('<div class="ips-td-metric-row"></div>', unsafe_allow_html=True)
    if narrow:
        r1 = st.columns(2)
        r1[0].metric("Available tools", f"{n_avail:,}")
        r1[1].metric("Checked out", f"{n_out:,}")
        r2 = st.columns(2)
        r2[0].metric("In maintenance", f"{n_maint:,}")
        r2[1].metric("Lost / missing", f"{n_lost:,}")
        st.metric(f"Overdue (>{OVERDUE_THRESHOLD_DAYS}d out)", f"{n_od:,}")
    else:
        m1, m2, m3, m4, m5 = st.columns(5, gap="small")
        m1.metric("Available tools", f"{n_avail:,}")
        m2.metric("Checked out", f"{n_out:,}")
        m3.metric("In maintenance", f"{n_maint:,}")
        m4.metric("Lost / missing", f"{n_lost:,}")
        m5.metric(f"Overdue (>{OVERDUE_THRESHOLD_DAYS}d)", f"{n_od:,}")

    # --- Filters ---
    all_statuses = sorted({str(t.get("status") or "").strip() for t in tools if str(t.get("status") or "").strip()})
    priority = ["Checked Out", "Maintenance", "Lost"]
    default_sel = [s for s in priority if s in all_statuses]
    if not default_sel:
        default_sel = [s for s in all_statuses if s != "Available"] or all_statuses[:]

    if narrow:
        st.multiselect("Status (tools to list)", all_statuses, default=default_sel, key="td_f_status")
        st.text_input("Search (name / tag / serial)", key="td_f_search")
        holders = sorted({emp_id_to_name.get(str(t.get("current_holder_employee_id") or ""), "").strip() or str(t.get("assigned_employee") or "").strip() for t in tools if str(t.get("status") or "").strip() != "Available"})  # noqa: E501
        holders = [h for h in holders if h]
        st.selectbox("Holder", ["All"] + holders, key="td_f_holder")
        job_opts = sorted({job_label(t.get("assigned_job_id")) for t in tools if t.get("assigned_job_id")})
        job_opts = [j for j in job_opts if j and j != "—"]
        st.selectbox("Job", ["All"] + job_opts, key="td_f_job")
    else:
        fc1, fc2, fc3, fc4 = st.columns(4, gap="small")
        fc1.multiselect("Status", all_statuses, default=default_sel, key="td_f_status")
        fc2.text_input("Search", key="td_f_search", placeholder="Name, asset tag, serial")
        holders = sorted(
            {
                emp_id_to_name.get(str(t.get("current_holder_employee_id") or ""), "").strip()
                or str(t.get("assigned_employee") or "").strip()
                for t in tools
                if str(t.get("status") or "").strip() != "Available"
            }
        )
        holders = [h for h in holders if h]
        fc3.selectbox("Holder", ["All"] + holders, key="td_f_holder")
        job_opts = sorted({job_label(t.get("assigned_job_id")) for t in tools if t.get("assigned_job_id")})
        job_opts = [j for j in job_opts if j and j != "—"]
        fc4.selectbox("Job", ["All"] + job_opts, key="td_f_job")

    sel_status = st.session_state.get("td_f_status", default_sel)
    search = str(st.session_state.get("td_f_search", "") or "").strip().lower()
    sel_holder = st.session_state.get("td_f_holder", "All")
    sel_job = st.session_state.get("td_f_job", "All")

    def enrich_row(t: dict) -> dict:
        eid = str(t.get("current_holder_employee_id") or "").strip()
        h = emp_id_to_name.get(eid) or str(t.get("assigned_employee") or "").strip() or "—"
        jid = t.get("assigned_job_id")
        jl = job_label(jid)
        return {
            "id": str(t.get("id") or ""),
            "Tool": str(t.get("asset_name") or "—"),
            "Asset tag": str(t.get("asset_id") or "—"),
            "Serial": str(t.get("serial_number") or "").strip() or "—",
            "Status": str(t.get("status") or "").strip(),
            "Holder": h,
            "Job": jl,
            "Checked out at": _parse_ts(t.get("last_checkout_at")),
            "Days out": _days_out_label(t.get("last_checkout_at")),
            "Notes": (str(t.get("notes") or "").strip()[:120] + "…")
            if len(str(t.get("notes") or "")) > 120
            else str(t.get("notes") or "").strip(),
            "_raw": t,
        }

    df_all = pd.DataFrame([enrich_row(t) for t in tools])

    df = df_all.copy()
    if sel_status:
        df = df[df["Status"].isin(sel_status)]
    else:
        df = df.iloc[0:0]

    if search:
        mask = (
            df["Tool"].str.lower().str.contains(search, na=False)
            | df["Asset tag"].str.lower().str.contains(search, na=False)
            | df["Serial"].str.lower().str.contains(search, na=False)
        )
        df = df[mask]

    if sel_holder and sel_holder != "All":
        df = df[df["Holder"].astype(str) == sel_holder]

    if sel_job and sel_job != "All":
        df = df[df["Job"].astype(str) == sel_job]

    status_order = {"Checked Out": 0, "Maintenance": 1, "Lost": 2}
    df["_so"] = df["Status"].map(lambda s: status_order.get(str(s), 9))
    df["_dv"] = df["Checked out at"].apply(lambda x: _days_out_value(x) if pd.notna(x) else None)
    df = df.sort_values(by=["_so", "_dv"], ascending=[True, False], na_position="last")
    df = df.drop(columns=["_so", "_dv"], errors="ignore")

    # --- Attention (all checkout tools — ignores status multiselect) ---
    st.subheader("Needs attention")
    att_parts: list[pd.DataFrame] = []
    base = df_all
    lost_df = base[base["Status"] == "Lost"] if not base.empty else base
    maint_df = base[base["Status"] == "Maintenance"] if not base.empty else base
    od_mask = pd.Series([False] * len(base), index=base.index)
    if not base.empty and "Checked out at" in base.columns:
        od_mask = (base["Status"] == "Checked Out") & base["Checked out at"].notna()
        od_vals = base["Checked out at"].apply(_days_out_value)
        od_mask = od_mask & od_vals.notna() & (od_vals > float(OVERDUE_THRESHOLD_DAYS))
    overdue_df = base[od_mask] if not base.empty else base
    if not lost_df.empty:
        att_parts.append(lost_df.assign(_why="Lost"))
    if not maint_df.empty:
        att_parts.append(maint_df.assign(_why="Maintenance"))
    if not overdue_df.empty:
        att_parts.append(overdue_df.assign(_why="Overdue"))
    if att_parts:
        att = pd.concat(att_parts, ignore_index=True)
        att = att.drop_duplicates(subset=["id"])
        st.dataframe(
            att[["Tool", "Asset tag", "Status", "Holder", "Job", "Days out", "_why"]].rename(columns={"_why": "Flag"}),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No lost, maintenance, or overdue checkout tools in the current filter.")

    # --- Main table ---
    st.subheader("Who has what (detail)")
    if df.empty:
        st.info("No rows match filters — widen **Status** or clear search.")
    elif narrow:
        for i, rec in enumerate(df.to_dict("records")):
            with st.container(border=True):
                raw = rec.get("_raw") or {}
                st.markdown(
                    f"**{html.escape(str(rec.get('Tool') or ''))}** · `{html.escape(str(rec.get('Asset tag') or ''))}`",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"{_status_badge_html(str(rec.get('Status') or ''))} {_attention_badge_html(str(rec.get('Status') or ''), raw.get('last_checkout_at'))}",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Serial: {html.escape(str(rec.get('Serial') or ''))} · Holder: {html.escape(str(rec.get('Holder') or ''))} · "
                    f"Job: {html.escape(str(rec.get('Job') or ''))} · Out: {html.escape(str(rec.get('Days out') or ''))}"
                )
                b1, b2, b3 = st.columns(3)
                with b1:
                    if can_write and str(rec.get("Status") or "") == "Checked Out":
                        if st.button("Check in", key=f"td_m_qin_{rec.get('id')}_{i}", use_container_width=True):
                            st.session_state["_td_quick_in_id"] = rec.get("id")
                            st.rerun()
                with b2:
                    if st.button("Open asset", key=f"td_m_op_{rec.get('id')}_{i}", use_container_width=True):
                        st.session_state["asset_detail_id"] = str(rec.get("id"))
                        st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
                        st.rerun()
                with b3:
                    if st.button("Tool checkout", key=f"td_m_tc_{rec.get('id')}_{i}", use_container_width=True):
                        st.session_state[IPS_NAV_PENDING_KEY] = "Tool Checkout"
                        st.rerun()
    else:
        disp = df.drop(columns=["_raw"], errors="ignore").copy()
        if "id" in disp.columns:
            disp = disp.drop(columns=["id"])
        if "Checked out at" in disp.columns:
            disp["Checked out at"] = disp["Checked out at"].apply(
                lambda x: x.strftime("%Y-%m-%d %H:%M") if pd.notna(x) and hasattr(x, "strftime") else "—"
            )
        st.dataframe(disp, use_container_width=True, hide_index=True)
        if not df.empty:
            st.markdown("**Quick actions**")
            _max_qa = 30
            _rows_qa = df.to_dict("records")[:_max_qa]
            for i, rec in enumerate(_rows_qa):
                c1, c2, c3 = st.columns([3.2, 1, 1])
                with c1:
                    st.caption(
                        f"{rec.get('Tool')} · {rec.get('Status')} · {rec.get('Holder')} · "
                        f"{rec.get('Days out')} out · {rec.get('Job')}"
                    )
                with c2:
                    if can_write and str(rec.get("Status") or "") == "Checked Out":
                        if st.button("Check in", key=f"td_qin_row_{rec.get('id')}_{i}"):
                            st.session_state["_td_quick_in_id"] = str(rec.get("id"))
                            st.rerun()
                with c3:
                    if st.button("Open asset", key=f"td_op_row_{rec.get('id')}_{i}"):
                        st.session_state["asset_detail_id"] = str(rec.get("id"))
                        st.session_state[IPS_NAV_PENDING_KEY] = "Asset Detail"
                        st.rerun()
            if len(df) > _max_qa:
                st.caption(f"Showing actions for first {_max_qa} of {len(df)} rows — tighten filters if needed.")

    st.divider()
    st.subheader("Recent tool activity")
    if not txn_ok:
        st.caption("Transaction log not available.")
    else:
        try:
            txns = fetch_table_admin(_TXN, limit=600)
        except Exception:
            txns = []
        txns.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
        txns = txns[:25]
        aid_to_name = {str(a.get("id")): str(a.get("asset_name") or "") for a in all_assets if a.get("id")}
        act_rows = []
        for r in txns:
            tid = str(r.get("tool_id") or "")
            jid = r.get("job_id")
            act_rows.append(
                {
                    "When": str(r.get("created_at") or "")[:19],
                    "Tool": aid_to_name.get(tid, tid[:8] + "…"),
                    "Type": str(r.get("transaction_type") or ""),
                    "Employee": emp_id_to_name.get(str(r.get("employee_id") or ""), "—"),
                    "Job": job_label(jid),
                    "Notes": (str(r.get("notes") or "")[:100] + "…")
                    if len(str(r.get("notes") or "")) > 100
                    else str(r.get("notes") or ""),
                }
            )
        st.dataframe(pd.DataFrame(act_rows), use_container_width=True, hide_index=True)
